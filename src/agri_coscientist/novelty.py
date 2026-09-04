from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Iterable, Mapping
import json
import re

from .literature import LiteratureRecord, LiteratureSearchResult, PublicationKind, deduplicate_records


class NoveltyVerdict(str, Enum):
    DIRECT_PRIOR_FOUND = "direct_prior_found"
    STRONGLY_THREATENED = "strongly_threatened"
    NO_DIRECT_PRIOR_WITHIN_SCOPE = "no_direct_prior_found_within_frozen_search_scope"
    INSUFFICIENT_COVERAGE = "insufficient_search_coverage"


@dataclass(frozen=True)
class ConceptOntology:
    """Frozen candidate ontology supplied before literature outcome review."""

    dimensions: Mapping[str, tuple[str, ...]]
    required_direct_dimensions: tuple[str, ...]

    def __post_init__(self):
        if not self.dimensions:
            raise ValueError("concept ontology cannot be empty")
        if not self.required_direct_dimensions:
            raise ValueError("required direct-overlap dimensions cannot be empty")
        unknown = set(self.required_direct_dimensions) - set(self.dimensions)
        if unknown:
            raise ValueError(f"required dimensions missing from ontology: {sorted(unknown)}")
        for name, terms in self.dimensions.items():
            if not terms or any(not str(term).strip() for term in terms):
                raise ValueError(f"ontology dimension {name!r} has empty terms")


@dataclass(frozen=True)
class SearchRun:
    family: str
    result: LiteratureSearchResult


@dataclass(frozen=True)
class PriorAssessment:
    record: LiteratureRecord
    matched_dimensions: tuple[str, ...]
    direct_required_match: bool
    strong_overlap: bool


@dataclass(frozen=True)
class NoveltyReport:
    verdict: NoveltyVerdict
    providers: tuple[str, ...]
    query_families: tuple[str, ...]
    unique_records: int
    direct_priors: tuple[PriorAssessment, ...]
    strong_priors: tuple[PriorAssessment, ...]
    contextual_records: tuple[PriorAssessment, ...]
    search_snapshot_sha256: str
    interpretation: str


@dataclass(frozen=True)
class CoveragePolicy:
    required_providers: tuple[str, ...] = ("europe_pmc", "crossref")
    required_query_families: tuple[str, ...] = (
        "exact_question", "mechanism", "crop_system", "adjacent_concept"
    )
    min_unique_records: int = 8
    min_records_with_abstract: int = 3


def _contains_term(text: str, term: str) -> bool:
    text = text.lower()
    term = term.lower().strip()
    if not term:
        return False
    # Phrase/identifier terms should match literally; single words are bounded so
    # short biological tokens do not accidentally match inside unrelated words.
    if " " in term or any(ch in term for ch in ("-", "+", "/")):
        return term in text
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None


def assess_record(record: LiteratureRecord, ontology: ConceptOntology) -> PriorAssessment:
    text = record.searchable_text
    matched = tuple(sorted(
        name for name, terms in ontology.dimensions.items()
        if any(_contains_term(text, term) for term in terms)
    ))
    required = set(ontology.required_direct_dimensions)
    direct = required.issubset(matched)
    strong_threshold = max(2, len(required) - 1)
    strong = len(required.intersection(matched)) >= strong_threshold
    return PriorAssessment(
        record=record,
        matched_dimensions=matched,
        direct_required_match=direct,
        strong_overlap=strong,
    )


def _snapshot(runs: Iterable[SearchRun], records: Iterable[LiteratureRecord]) -> str:
    payload = {
        "runs": sorted([
            {
                "family": run.family,
                "provider": run.result.provider,
                "query": run.result.query,
                "from_year": run.result.from_year,
                "to_year": run.result.to_year,
                "total_hits": run.result.total_hits,
                "retrieved": run.result.retrieved,
            }
            for run in runs
        ], key=lambda x: (x["family"], x["provider"], x["query"])),
        "records": sorted([
            {
                "identity": r.identity,
                "title": r.title,
                "year": r.year,
                "provider": r.provider,
                "kind": r.kind.value,
                "retracted": r.is_retracted,
            }
            for r in records
        ], key=lambda x: (x["identity"], x["provider"])),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return sha256(raw).hexdigest()


def _coverage_ok(runs: list[SearchRun], records: list[LiteratureRecord], policy: CoveragePolicy) -> bool:
    providers = {run.result.provider for run in runs}
    families = {run.family for run in runs}
    if not set(policy.required_providers).issubset(providers):
        return False
    if not set(policy.required_query_families).issubset(families):
        return False
    # Every required family must have been attempted through every required provider.
    attempted = {(run.family, run.result.provider) for run in runs}
    if any((family, provider) not in attempted
           for family in policy.required_query_families
           for provider in policy.required_providers):
        return False
    if len(records) < policy.min_unique_records:
        return False
    if sum(bool(r.abstract) for r in records) < policy.min_records_with_abstract:
        return False
    return True


def novelty_court(
    runs: Iterable[SearchRun],
    ontology: ConceptOntology,
    *,
    policy: CoveragePolicy = CoveragePolicy(),
) -> NoveltyReport:
    runs = list(runs)
    records = deduplicate_records(r for run in runs for r in run.result.records)
    providers = tuple(sorted({run.result.provider for run in runs}))
    families = tuple(sorted({run.family for run in runs}))
    snapshot = _snapshot(runs, records)

    if not _coverage_ok(runs, records, policy):
        return NoveltyReport(
            verdict=NoveltyVerdict.INSUFFICIENT_COVERAGE,
            providers=providers,
            query_families=families,
            unique_records=len(records),
            direct_priors=(), strong_priors=(), contextual_records=(),
            search_snapshot_sha256=snapshot,
            interpretation=(
                "Novelty cannot be evaluated because the frozen search did not satisfy "
                "the predeclared provider/query-family/evidence coverage policy."
            ),
        )

    assessments = [assess_record(record, ontology) for record in records]
    # Preprints count as prior disclosure for novelty. Retraction does not erase
    # historical disclosure, although it must not be used as reliable mechanistic evidence.
    direct = [a for a in assessments if a.direct_required_match and a.record.kind in {
        PublicationKind.ORIGINAL, PublicationKind.PREPRINT
    }]
    review_direct = [a for a in assessments if a.direct_required_match and a.record.kind == PublicationKind.REVIEW]
    strong = [a for a in assessments if a.strong_overlap and a not in direct]
    contextual = [a for a in assessments if a not in direct and a not in strong]

    sort_key = lambda a: (-(a.record.year or 0), -len(a.matched_dimensions), a.record.identity)
    direct.sort(key=sort_key)
    strong.sort(key=sort_key)
    contextual.sort(key=sort_key)

    if direct:
        verdict = NoveltyVerdict.DIRECT_PRIOR_FOUND
        interpretation = (
            "At least one original article or preprint matches every predeclared direct-overlap "
            "dimension. The current formulation must not advance as novel without evolution."
        )
    elif review_direct or strong:
        verdict = NoveltyVerdict.STRONGLY_THREATENED
        interpretation = (
            "No direct original/preprint prior was identified by the frozen lexical court, but "
            "near-prior or review-level overlap is strong enough to require deeper reference chasing "
            "and candidate evolution before a novelty claim can advance."
        )
    else:
        verdict = NoveltyVerdict.NO_DIRECT_PRIOR_WITHIN_SCOPE
        interpretation = (
            "No direct prior was found within the frozen providers, query families, date window, "
            "and retrieved records. This is a scoped search result, not proof of absolute novelty."
        )

    return NoveltyReport(
        verdict=verdict,
        providers=providers,
        query_families=families,
        unique_records=len(records),
        direct_priors=tuple(direct),
        strong_priors=tuple(strong),
        contextual_records=tuple(contextual),
        search_snapshot_sha256=snapshot,
        interpretation=interpretation,
    )


def evolution_actions(report: NoveltyReport, ontology: ConceptOntology) -> tuple[str, ...]:
    """Return structured research-design degrees of freedom when novelty is threatened.

    This deliberately does not invent a replacement study. It identifies dimensions
    that the reasoning/model layer should alter and then send back through the full
    novelty/feasibility courts.
    """
    if report.verdict not in {NoveltyVerdict.DIRECT_PRIOR_FOUND, NoveltyVerdict.STRONGLY_THREATENED}:
        return ()
    threats = list(report.direct_priors) + list(report.strong_priors)
    commonly_matched = {
        dim for dim in ontology.dimensions
        if threats and sum(dim in a.matched_dimensions for a in threats) / len(threats) >= 0.5
    }
    actions = []
    for dimension in ontology.required_direct_dimensions:
        if dimension in commonly_matched:
            actions.append(f"evolve:{dimension}")
    actions.extend((
        "consider:timing_or_dose",
        "consider:receiver_or_spatial_design",
        "consider:independent_public_data_triangulation",
    ))
    return tuple(dict.fromkeys(actions))
