from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import html
import json
import math
import re


class LiteratureError(RuntimeError):
    pass


class PublicationKind(str, Enum):
    ORIGINAL = "original"
    REVIEW = "review"
    PREPRINT = "preprint"
    OTHER = "other"


@dataclass(frozen=True)
class LiteratureRecord:
    provider: str
    provider_id: str
    title: str
    abstract: str | None
    year: int | None
    doi: str | None
    pmid: str | None
    journal: str | None
    kind: PublicationKind
    cited_by_count: int | None
    is_retracted: bool
    url: str | None

    @property
    def identity(self) -> str:
        if self.doi:
            return f"doi:{self.doi.lower()}"
        if self.pmid:
            return f"pmid:{self.pmid}"
        normalized = re.sub(r"\W+", " ", self.title.lower()).strip()
        return f"title:{normalized}"

    @property
    def searchable_text(self) -> str:
        return " ".join(x for x in (self.title, self.abstract or "") if x).lower()


@dataclass(frozen=True)
class LiteratureSearchResult:
    provider: str
    query: str
    from_year: int
    to_year: int
    records: tuple[LiteratureRecord, ...]
    total_hits: int
    requested_rows: int
    negative_evidence_eligible: bool = True

    @property
    def retrieved(self) -> int:
        return len(self.records)

    @property
    def exhaustive_for_query(self) -> bool:
        """True only when every provider hit is represented in the returned records.

        This is deliberately conservative: malformed/untitled provider rows that are
        skipped during normalization also prevent an absence claim from being treated
        as exhaustive.
        """
        return self.total_hits <= self.retrieved

    @property
    def supports_absence_inference(self) -> bool:
        return self.negative_evidence_eligible and self.exhaustive_for_query


def _strip_markup(value: str | None) -> str | None:
    if not value:
        return None
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return value or None


def deduplicate_records(records: Iterable[LiteratureRecord]) -> list[LiteratureRecord]:
    """Deterministically deduplicate by DOI, then PMID, then normalized title."""
    best: dict[str, LiteratureRecord] = {}
    for record in records:
        key = record.identity
        current = best.get(key)
        if current is None:
            best[key] = record
            continue
        score = lambda r: (
            int(bool(r.abstract)), int(bool(r.doi)), int(bool(r.pmid)),
            int(r.cited_by_count or 0), len(r.title or ""), r.provider,
        )
        if score(record) > score(current):
            best[key] = record
    return sorted(best.values(), key=lambda r: (-(r.year or 0), r.identity))


class _JsonAdapter:
    def __init__(self, *, opener: Callable = urlopen, timeout: int = 60,
                 user_agent: str = "Agriculture-CoScientist-test/0.5"):
        self.opener = opener
        self.timeout = timeout
        self.user_agent = user_agent

    def _json(self, request: Request) -> dict:
        with self.opener(request, timeout=self.timeout) as response:
            payload = response.read()
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LiteratureError("literature provider returned invalid JSON") from exc


class EuropePMCAdapter(_JsonAdapter):
    """Europe PMC adapter; complete small result sets may support absence inference."""

    SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    @staticmethod
    def _kind(raw: dict) -> PublicationKind:
        source = str(raw.get("source") or "").upper()
        pub_types = raw.get("pubTypeList", {}).get("pubType", [])
        if isinstance(pub_types, str):
            pub_types = [pub_types]
        labels = {str(v).lower() for v in pub_types}
        if source == "PPR" or any("preprint" in v for v in labels):
            return PublicationKind.PREPRINT
        if any("review" in v for v in labels):
            return PublicationKind.REVIEW
        if any(v in labels for v in ("journal article", "research article")):
            return PublicationKind.ORIGINAL
        return PublicationKind.OTHER

    def search(self, query: str, *, from_year: int, to_year: int,
               rows: int = 100) -> LiteratureSearchResult:
        if not query.strip():
            raise ValueError("literature query cannot be empty")
        if from_year > to_year:
            raise ValueError("from_year cannot exceed to_year")
        if not 1 <= rows <= 1000:
            raise ValueError("rows must be in [1, 1000]")
        frozen_query = f"({query}) AND FIRST_PDATE:[{from_year}-01-01 TO {to_year}-12-31]"
        params = urlencode({
            "query": frozen_query,
            "format": "json",
            "resultType": "core",
            "pageSize": rows,
        })
        payload = self._json(Request(
            f"{self.SEARCH_URL}?{params}",
            headers={"Accept": "application/json", "User-Agent": self.user_agent},
        ))
        hit_count = int(payload.get("hitCount") or 0)
        raw_records = payload.get("resultList", {}).get("result", []) or []
        records: list[LiteratureRecord] = []
        for raw in raw_records:
            year = raw.get("pubYear")
            try:
                year = int(year) if year is not None else None
            except (TypeError, ValueError):
                year = None
            if year is not None and not (from_year <= year <= to_year):
                continue
            pub_types = raw.get("pubTypeList", {}).get("pubType", [])
            if isinstance(pub_types, str):
                pub_types = [pub_types]
            retracted = bool(raw.get("isRetracted")) or any(
                "retracted" in str(v).lower() for v in pub_types
            )
            provider_id = str(raw.get("id") or raw.get("pmid") or raw.get("doi") or "")
            if not provider_id or not raw.get("title"):
                continue
            source = str(raw.get("source") or "MED")
            records.append(LiteratureRecord(
                provider="europe_pmc",
                provider_id=f"{source}:{provider_id}",
                title=_strip_markup(str(raw.get("title"))) or str(raw.get("title")),
                abstract=_strip_markup(raw.get("abstractText")),
                year=year,
                doi=_normalize_doi(raw.get("doi")),
                pmid=str(raw.get("pmid")) if raw.get("pmid") else None,
                journal=raw.get("journalTitle"),
                kind=self._kind(raw),
                cited_by_count=int(raw.get("citedByCount") or 0),
                is_retracted=retracted,
                url=f"https://europepmc.org/article/{source}/{provider_id}",
            ))
        return LiteratureSearchResult(
            provider="europe_pmc", query=frozen_query, from_year=from_year,
            to_year=to_year, records=tuple(records), total_hits=hit_count,
            requested_rows=rows, negative_evidence_eligible=True,
        )


class CrossrefAdapter(_JsonAdapter):
    """Crossref discovery cross-check.

    `query.bibliographic` is relevance-ranked and can produce very large result
    universes. Therefore Crossref is treated as positive-prior/metadata evidence
    only; an absent match in a truncated Crossref response can never support a
    novelty/absence inference.
    """

    SEARCH_URL = "https://api.crossref.org/works"

    @staticmethod
    def _year(raw: dict) -> int | None:
        for key in ("published-online", "published-print", "published", "issued"):
            parts = (raw.get(key) or {}).get("date-parts") or []
            if parts and parts[0]:
                try:
                    return int(parts[0][0])
                except (TypeError, ValueError, IndexError):
                    pass
        return None

    @staticmethod
    def _kind(raw: dict) -> PublicationKind:
        subtype = str(raw.get("subtype") or "").lower()
        title = " ".join(raw.get("title") or []).lower()
        work_type = str(raw.get("type") or "").lower()
        if "preprint" in subtype or work_type == "posted-content":
            return PublicationKind.PREPRINT
        if "review" in subtype or " review" in title or title.startswith("review"):
            return PublicationKind.REVIEW
        if work_type in {"journal-article", "proceedings-article"}:
            return PublicationKind.ORIGINAL
        return PublicationKind.OTHER

    def search(self, query: str, *, from_year: int, to_year: int,
               rows: int = 100) -> LiteratureSearchResult:
        if not query.strip():
            raise ValueError("literature query cannot be empty")
        if from_year > to_year:
            raise ValueError("from_year cannot exceed to_year")
        if not 1 <= rows <= 1000:
            raise ValueError("rows must be in [1, 1000]")
        params = urlencode({
            "query.bibliographic": query,
            "filter": f"from-pub-date:{from_year}-01-01,until-pub-date:{to_year}-12-31",
            "rows": rows,
        })
        payload = self._json(Request(
            f"{self.SEARCH_URL}?{params}",
            headers={"Accept": "application/json", "User-Agent": self.user_agent},
        ))
        message = payload.get("message") or {}
        total = int(message.get("total-results") or 0)
        records: list[LiteratureRecord] = []
        for raw in message.get("items", []) or []:
            titles = raw.get("title") or []
            title = _strip_markup(str(titles[0])) if titles else None
            if not title:
                continue
            year = self._year(raw)
            if year is not None and not (from_year <= year <= to_year):
                continue
            doi = _normalize_doi(raw.get("DOI"))
            records.append(LiteratureRecord(
                provider="crossref",
                provider_id=doi or str(raw.get("URL") or title),
                title=title,
                abstract=_strip_markup(raw.get("abstract")),
                year=year,
                doi=doi,
                pmid=None,
                journal=(raw.get("container-title") or [None])[0],
                kind=self._kind(raw),
                cited_by_count=int(raw.get("is-referenced-by-count") or 0),
                is_retracted=False,
                url=raw.get("URL"),
            ))
        return LiteratureSearchResult(
            provider="crossref", query=query, from_year=from_year, to_year=to_year,
            records=tuple(records), total_hits=total, requested_rows=rows,
            negative_evidence_eligible=False,
        )


def _openalex_abstract(inverted: dict | None) -> str | None:
    if not inverted:
        return None
    positions: list[tuple[int, str]] = []
    for token, indexes in inverted.items():
        for index in indexes or []:
            try:
                positions.append((int(index), str(token)))
            except (TypeError, ValueError):
                continue
    if not positions:
        return None
    positions.sort()
    return " ".join(token for _, token in positions)


class OpenAlexAdapter(_JsonAdapter):
    """OpenAlex full-text works search with bounded exhaustive paging.

    OpenAlex's `search` spans work titles, abstracts, and full text and supports
    Boolean operators plus quoted phrases. We page through the full result set only
    when it is at or below `max_records`; otherwise the result remains useful for
    positive prior discovery but is explicitly ineligible as complete absence evidence.
    """

    SEARCH_URL = "https://api.openalex.org/works"

    @staticmethod
    def _kind(raw: dict) -> PublicationKind:
        work_type = str(raw.get("type") or "").lower()
        crossref_type = str(raw.get("type_crossref") or "").lower()
        title = str(raw.get("display_name") or raw.get("title") or "").lower()
        if work_type == "preprint" or crossref_type == "posted-content":
            return PublicationKind.PREPRINT
        if work_type == "review" or " review" in title or title.startswith("review"):
            return PublicationKind.REVIEW
        if work_type in {"article", "book-chapter", "proceedings-article"} or crossref_type in {
            "journal-article", "proceedings-article"
        }:
            return PublicationKind.ORIGINAL
        return PublicationKind.OTHER

    @staticmethod
    def _record(raw: dict) -> LiteratureRecord | None:
        title = _strip_markup(str(raw.get("display_name") or raw.get("title") or ""))
        if not title:
            return None
        year = raw.get("publication_year")
        try:
            year = int(year) if year is not None else None
        except (TypeError, ValueError):
            year = None
        doi = _normalize_doi(raw.get("doi"))
        ids = raw.get("ids") or {}
        pmid_raw = ids.get("pmid")
        pmid = None
        if pmid_raw:
            pmid = re.sub(r"^https?://pubmed\.ncbi\.nlm\.nih\.gov/", "", str(pmid_raw)).strip("/") or None
        primary = raw.get("primary_location") or {}
        source = primary.get("source") or {}
        provider_id = str(raw.get("id") or doi or title)
        return LiteratureRecord(
            provider="openalex",
            provider_id=provider_id,
            title=title,
            abstract=_openalex_abstract(raw.get("abstract_inverted_index")),
            year=year,
            doi=doi,
            pmid=pmid,
            journal=source.get("display_name"),
            kind=OpenAlexAdapter._kind(raw),
            cited_by_count=int(raw.get("cited_by_count") or 0),
            is_retracted=bool(raw.get("is_retracted")),
            url=raw.get("id"),
        )

    def search(self, query: str, *, from_year: int, to_year: int,
               rows: int = 100, max_records: int = 1000) -> LiteratureSearchResult:
        if not query.strip():
            raise ValueError("literature query cannot be empty")
        if from_year > to_year:
            raise ValueError("from_year cannot exceed to_year")
        if not 1 <= rows <= 100:
            raise ValueError("OpenAlex rows/per_page must be in [1, 100]")
        if max_records < rows or max_records > 10000:
            raise ValueError("max_records must be between rows and 10000")

        base = {
            "search": query,
            "filter": f"from_publication_date:{from_year}-01-01,to_publication_date:{to_year}-12-31",
            "per_page": rows,
        }
        records: list[LiteratureRecord] = []
        total: int | None = None
        max_pages = math.ceil(max_records / rows)
        for page in range(1, max_pages + 1):
            params = dict(base)
            params["page"] = page
            payload = self._json(Request(
                f"{self.SEARCH_URL}?{urlencode(params)}",
                headers={"Accept": "application/json", "User-Agent": self.user_agent},
            ))
            meta = payload.get("meta") or {}
            if total is None:
                total = int(meta.get("count") or 0)
            raw_results = payload.get("results") or []
            for raw in raw_results:
                record = self._record(raw)
                if record is not None and (record.year is None or from_year <= record.year <= to_year):
                    records.append(record)
            if not raw_results or len(records) >= (total or 0):
                break
            if total is not None and total > max_records and page * rows >= max_records:
                break

        total = int(total or 0)
        return LiteratureSearchResult(
            provider="openalex", query=query, from_year=from_year, to_year=to_year,
            records=tuple(records), total_hits=total, requested_rows=max_records,
            negative_evidence_eligible=True,
        )
