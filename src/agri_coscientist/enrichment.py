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


@dataclass(frozen=True)
class GProfilerProfileResponse:
    results: tuple[EnrichmentResult, ...]
    meta: dict


@dataclass(frozen=True)
class GProfilerConversionCoverage:
    input_size: int
    mapped_size: int
    mapping_fraction: float
    unmapped_ids: tuple[str, ...]
    ambiguous_ids: tuple[str, ...]
    target_namespace: str
    chunks: int
    provider_result_rows: int


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
    PROFILE_URL = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"
    VERSION_URL = "https://biit.cs.ut.ee/gprofiler/api/util/data_versions/"
    CONVERT_URL = "https://biit.cs.ut.ee/gprofiler/api/convert/convert/"

    def __init__(self, *, opener: Callable = urlopen, timeout: int = 60,
                 user_agent: str = "Agriculture-CoScientist-test/0.4"):
        self.opener = opener
        self.timeout = timeout
        self.user_agent = user_agent

    def _request_json(self, request: Request) -> dict:
        with self.opener(request, timeout=self.timeout) as response:
            payload = response.read()
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EnrichmentError("g:Profiler returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise EnrichmentError("g:Profiler returned an unexpected JSON shape")
        return decoded

    def _post_json(self, url: str, body: dict) -> dict:
        return self._request_json(Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
            method="POST",
        ))

    def data_versions(self, build: GenomeBuild) -> dict:
        if not build.gprofiler_organism:
            raise EnrichmentError(f"no g:Profiler organism mapping for {build.assembly}")
        url = f"{self.VERSION_URL}?organism={build.gprofiler_organism}"
        return self._request_json(Request(url, headers={
            "Accept": "application/json", "User-Agent": self.user_agent,
        }))

    def convert_coverage(
        self,
        genes: Iterable[str],
        build: GenomeBuild,
        *,
        target_namespace: str = "ENSG",
        chunk_size: int = 5000,
    ) -> GProfilerConversionCoverage:
        if not build.gprofiler_organism:
            raise EnrichmentError(f"no g:Profiler organism mapping for {build.assembly}")
        if chunk_size < 1:
            raise ValueError("chunk_size must be positive")
        gene_list = list(dict.fromkeys(map(str, genes)))
        if not gene_list:
            raise ValueError("gene list is required for mapping coverage")

        mapped: dict[str, set[str]] = {}
        result_rows = 0
        chunks = 0
        input_by_key = {gene.lower(): gene for gene in gene_list}
        for offset in range(0, len(gene_list), chunk_size):
            chunks += 1
            chunk = gene_list[offset: offset + chunk_size]
            payload = self._post_json(self.CONVERT_URL, {
                "organism": build.gprofiler_organism,
                "query": chunk,
                "target": target_namespace,
            })
            rows = payload.get("result") or []
            if not isinstance(rows, list):
                raise EnrichmentError("g:Convert result is not a list")
            result_rows += len(rows)
            for raw in rows:
                if not isinstance(raw, dict):
                    continue
                incoming = str(raw.get("incoming") or "").strip()
                converted = str(raw.get("converted") or "").strip()
                if not incoming or not converted or converted.upper() in {"N/A", "NA", "?", "NONE"}:
                    continue
                key = incoming.lower()
                if key not in input_by_key:
                    continue
                mapped.setdefault(key, set()).add(converted)

        mapped_keys = set(mapped)
        unmapped = tuple(gene for gene in gene_list if gene.lower() not in mapped_keys)
        ambiguous = tuple(
            input_by_key[key] for key, conversions in mapped.items() if len(conversions) > 1
        )
        mapped_size = len(mapped_keys)
        return GProfilerConversionCoverage(
            input_size=len(gene_list),
            mapped_size=mapped_size,
            mapping_fraction=mapped_size / len(gene_list),
            unmapped_ids=unmapped,
            ambiguous_ids=tuple(sorted(ambiguous)),
            target_namespace=target_namespace,
            chunks=chunks,
            provider_result_rows=result_rows,
        )

    def profile_response(
        self,
        query: Iterable[str],
        background: Iterable[str],
        build: GenomeBuild,
        *,
        sources: tuple[str, ...] = ("GO:BP", "GO:MF", "GO:CC"),
        no_iea: bool = False,
        user_threshold: float = 0.05,
        all_results: bool = False,
    ) -> GProfilerProfileResponse:
        if not build.gprofiler_organism:
            raise EnrichmentError(f"no g:Profiler organism mapping for {build.assembly}")
        if not (0.0 < float(user_threshold) <= 1.0):
            raise ValueError("user_threshold must be in (0, 1]")
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
            "user_threshold": float(user_threshold),
            "no_evidences": True,
            "no_iea": bool(no_iea),
        }
        if all_results:
            body["all_results"] = True
        payload = self._post_json(self.PROFILE_URL, body)
        results = []
        for raw in payload.get("result", []):
            intersection = tuple(raw.get("intersections") or ())
            results.append(EnrichmentResult(
                term_id=str(raw.get("native")),
                name=raw.get("name"),
                source=raw.get("source"),
                p_value=float(raw.get("p_value", 1.0)),
                q_value=float(raw.get("p_value", 1.0)),
                query_size=int(raw.get("query_size") or len(query_list)),
                background_size=int(raw.get("effective_domain_size") or len(background_list)),
                term_size=int(raw.get("term_size") or 0),
                intersection_size=int(raw.get("intersection_size") or len(intersection)),
                intersection=intersection,
                provider="g:Profiler",
                raw=raw,
            ))
        ordered = tuple(sorted(results, key=lambda r: (r.q_value, r.term_id)))
        return GProfilerProfileResponse(results=ordered, meta=payload.get("meta") or {})

    def profile(
        self,
        query: Iterable[str],
        background: Iterable[str],
        build: GenomeBuild,
        *,
        sources: tuple[str, ...] = ("GO:BP", "GO:MF", "GO:CC"),
        no_iea: bool = False,
        user_threshold: float = 0.05,
    ) -> list[EnrichmentResult]:
        return list(self.profile_response(
            query,
            background,
            build,
            sources=sources,
            no_iea=no_iea,
            user_threshold=user_threshold,
            all_results=False,
        ).results)
