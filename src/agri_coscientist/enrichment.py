from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping
from urllib.request import Request, urlopen
import json
import math

from scipy.stats import hypergeom

from .annotation import GenomeBuild


class EnrichmentError(RuntimeError):
    pass


@dataclass(frozen=True)
class EnrichmentResult:
    term_id: str
    name: str | None
    source: str | None
    p_value: float
    q_value: float
    query_size: int
    background_size: int
    term_size: int
    intersection_size: int
    intersection: tuple[str, ...]
    provider: str
    raw: dict | None = None


def benjamini_hochberg(p_values: Iterable[float]) -> list[float]:
    values = [float(p) for p in p_values]
    if any((not math.isfinite(p) or p < 0 or p > 1) for p in values):
        raise ValueError("p-values must be finite and in [0, 1]")
    m = len(values)
    if m == 0:
        return []
    order = sorted(range(m), key=values.__getitem__)
    adjusted = [1.0] * m
    running = 1.0
    for rank_index in range(m - 1, -1, -1):
        original_index = order[rank_index]
        rank = rank_index + 1
        candidate = values[original_index] * m / rank
        running = min(running, candidate)
        adjusted[original_index] = min(1.0, running)
    return adjusted


def overrepresentation(
    query: Iterable[str],
    background: Iterable[str],
    associations: Mapping[str, Iterable[str]],
    *,
    term_names: Mapping[str, str] | None = None,
) -> list[EnrichmentResult]:
    """One-sided hypergeometric ORA with explicit universe and BH-FDR.

    `associations` maps term IDs to genes annotated to each term. Query genes
    MUST be drawn from the supplied background; otherwise analysis aborts.
    """
    query_set = {str(g) for g in query}
    background_set = {str(g) for g in background}
    if not background_set:
        raise ValueError("background universe is required and cannot be empty")
    if not query_set:
        raise ValueError("query gene set cannot be empty")
    missing = query_set - background_set
    if missing:
        raise ValueError(f"query contains genes outside background: {sorted(missing)[:5]}")

    M = len(background_set)
    N = len(query_set)
    rows: list[tuple[str, int, int, float, tuple[str, ...]]] = []
    for term_id, genes in associations.items():
        term_genes = {str(g) for g in genes} & background_set
        n = len(term_genes)
        if n == 0:
            continue
        intersection = tuple(sorted(query_set & term_genes))
        k = len(intersection)
        if k == 0:
            continue
        p = float(hypergeom.sf(k - 1, M, n, N))
        rows.append((str(term_id), n, k, p, intersection))

    q_values = benjamini_hochberg(row[3] for row in rows)
    results = []
    for row, q in zip(rows, q_values):
        term_id, term_size, intersection_size, p, intersection = row
        results.append(EnrichmentResult(
            term_id=term_id,
            name=(term_names or {}).get(term_id),
            source="local-association-table",
            p_value=p,
            q_value=q,
            query_size=N,
            background_size=M,
            term_size=term_size,
            intersection_size=intersection_size,
            intersection=intersection,
            provider="Agriculture CoScientist ORA",
        ))
    return sorted(results, key=lambda r: (r.q_value, r.p_value, r.term_id))


class GProfilerAdapter:
    """g:Profiler g:GOSt adapter with mandatory custom background + FDR."""

    PROFILE_URL = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"
    VERSION_URL = "https://biit.cs.ut.ee/gprofiler/api/util/data_versions/"

    def __init__(self, *, opener: Callable = urlopen, timeout: int = 60,
                 user_agent: str = "Agriculture-CoScientist-test/0.3"):
        self.opener = opener
        self.timeout = timeout
        self.user_agent = user_agent

    def _request_json(self, request: Request) -> dict:
        with self.opener(request, timeout=self.timeout) as response:
            payload = response.read()
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EnrichmentError("g:Profiler returned invalid JSON") from exc

    def data_versions(self, build: GenomeBuild) -> dict:
        if not build.gprofiler_organism:
            raise EnrichmentError(f"no g:Profiler organism mapping for {build.assembly}")
        url = f"{self.VERSION_URL}?organism={build.gprofiler_organism}"
        return self._request_json(Request(url, headers={
            "Accept": "application/json", "User-Agent": self.user_agent,
        }))

    def profile(
        self,
        query: Iterable[str],
        background: Iterable[str],
        build: GenomeBuild,
        *,
        sources: tuple[str, ...] = ("GO:BP", "GO:MF", "GO:CC"),
        no_iea: bool = False,
    ) -> list[EnrichmentResult]:
        if not build.gprofiler_organism:
            raise EnrichmentError(f"no g:Profiler organism mapping for {build.assembly}")
        query_list = list(dict.fromkeys(map(str, query)))
        background_list = list(dict.fromkeys(map(str, background)))
        if not query_list or not background_list:
            raise ValueError("query and background are required")
        outside = set(query_list) - set(background_list)
        if outside:
            raise ValueError(f"query contains genes outside background: {sorted(outside)[:5]}")
        body = {
            "organism": build.gprofiler_organism,
            "query": query_list,
            "sources": list(sources),
            "domain_scope": "custom",
            "background": background_list,
            "significance_threshold_method": "fdr",
            "no_evidences": True,
            "no_iea": bool(no_iea),
        }
        request = Request(
            self.PROFILE_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
            method="POST",
        )
        payload = self._request_json(request)
        results = []
        for raw in payload.get("result", []):
            intersection = tuple(raw.get("intersections") or ())
            results.append(EnrichmentResult(
                term_id=str(raw.get("native")),
                name=raw.get("name"),
                source=raw.get("source"),
                p_value=float(raw.get("p_value", 1.0)),
                q_value=float(raw.get("p_value", 1.0)),  # API reports corrected p-value under chosen FDR method.
                query_size=int(raw.get("query_size") or len(query_list)),
                background_size=int(raw.get("effective_domain_size") or len(background_list)),
                term_size=int(raw.get("term_size") or 0),
                intersection_size=int(raw.get("intersection_size") or len(intersection)),
                intersection=intersection,
                provider="g:Profiler",
                raw=raw,
            ))
        return sorted(results, key=lambda r: (r.q_value, r.term_id))
