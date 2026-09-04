from agri_coscientist.literature import (
    LiteratureRecord,
    LiteratureSearchResult,
    PublicationKind,
    deduplicate_records,
)
from agri_coscientist.novelty import (
    ConceptOntology,
    CoveragePolicy,
    NoveltyVerdict,
    SearchRun,
    evolution_actions,
    novelty_court,
)


def rec(i, text, *, provider="europe_pmc", kind=PublicationKind.ORIGINAL,
        abstract=True, doi=None, retracted=False):
    return LiteratureRecord(
        provider=provider,
        provider_id=f"{provider}:{i}",
        title=text,
        abstract=f"Detailed abstract about {text}." if abstract else None,
        year=2025,
        doi=doi or f"10.1234/{i}",
        pmid=str(1000 + i) if provider == "europe_pmc" else None,
        journal="Test Journal",
        kind=kind,
        cited_by_count=i,
        is_retracted=retracted,
        url=f"https://example/{i}",
    )


ONTOLOGY = ConceptOntology(
    dimensions={
        "crop": ("wheat", "triticum aestivum"),
        "tissue": ("root", "roots"),
        "exposure": ("soil compaction", "mechanical impedance", "mechanical stress"),
        "signal": ("extracellular atp", "eatp", "purinergic"),
        "receiver": ("neighbor", "neighbour", "plant-plant"),
        "outcome": ("priming", "stress memory", "antioxidant"),
    },
    required_direct_dimensions=("crop", "tissue", "exposure", "signal", "receiver"),
)


FAMILIES = ("exact_question", "mechanism", "crop_system", "adjacent_concept")
PROVIDERS = ("europe_pmc", "crossref")


def runs_with(records):
    out = []
    for family in FAMILIES:
        for provider in PROVIDERS:
            provider_records = tuple(
                r for r in records if r.provider == provider
            )
            out.append(SearchRun(
                family=family,
                result=LiteratureSearchResult(
                    provider=provider,
                    query=f"{family} query",
                    from_year=2024,
                    to_year=2026,
                    records=provider_records,
                    total_hits=len(provider_records),
                    requested_rows=100,
                ),
            ))
    return out


def filler_records(n=8):
    records = []
    for i in range(n):
        provider = PROVIDERS[i % 2]
        records.append(rec(i + 1, f"plant signaling context {i}", provider=provider))
    return records


def test_dedup_prefers_richer_record_for_same_doi():
    a = rec(1, "same paper", provider="crossref", abstract=False, doi="10.1/same")
    b = rec(2, "same paper", provider="europe_pmc", abstract=True, doi="https://doi.org/10.1/SAME")
    deduped = deduplicate_records([a, b])
    assert len(deduped) == 1
    assert deduped[0].abstract is not None
    assert deduped[0].identity == "doi:10.1/same"


def test_missing_provider_blocks_novelty_verdict():
    records = filler_records()
    runs = [r for r in runs_with(records) if r.result.provider == "europe_pmc"]
    report = novelty_court(runs, ONTOLOGY)
    assert report.verdict == NoveltyVerdict.INSUFFICIENT_COVERAGE


def test_missing_query_family_blocks_novelty_verdict():
    records = filler_records()
    runs = [r for r in runs_with(records) if r.family != "adjacent_concept"]
    report = novelty_court(runs, ONTOLOGY)
    assert report.verdict == NoveltyVerdict.INSUFFICIENT_COVERAGE


def test_direct_original_prior_blocks_advancement_as_novel():
    records = filler_records()
    records.append(rec(
        99,
        "Wheat root soil compaction extracellular ATP neighbor signaling",
        provider="europe_pmc",
        kind=PublicationKind.ORIGINAL,
    ))
    report = novelty_court(runs_with(records), ONTOLOGY)
    assert report.verdict == NoveltyVerdict.DIRECT_PRIOR_FOUND
    assert report.direct_priors
    assert "must not advance as novel" in report.interpretation
    assert evolution_actions(report, ONTOLOGY)


def test_direct_preprint_counts_as_prior_disclosure():
    records = filler_records()
    records.append(rec(
        100,
        "Wheat roots under mechanical stress use eATP for neighbour communication",
        provider="crossref",
        kind=PublicationKind.PREPRINT,
    ))
    report = novelty_court(runs_with(records), ONTOLOGY)
    assert report.verdict == NoveltyVerdict.DIRECT_PRIOR_FOUND
    assert report.direct_priors[0].record.kind == PublicationKind.PREPRINT


def test_retracted_direct_prior_still_threatens_novelty_as_historical_disclosure():
    records = filler_records()
    records.append(rec(
        101,
        "Wheat root mechanical stress extracellular ATP neighbor response",
        provider="europe_pmc",
        kind=PublicationKind.ORIGINAL,
        retracted=True,
    ))
    report = novelty_court(runs_with(records), ONTOLOGY)
    assert report.verdict == NoveltyVerdict.DIRECT_PRIOR_FOUND
    assert report.direct_priors[0].record.is_retracted is True


def test_review_only_direct_overlap_is_strong_threat_not_original_prior():
    records = filler_records()
    records.append(rec(
        102,
        "Review of wheat root mechanical stress extracellular ATP neighbor signaling",
        provider="europe_pmc",
        kind=PublicationKind.REVIEW,
    ))
    report = novelty_court(runs_with(records), ONTOLOGY)
    assert report.verdict == NoveltyVerdict.STRONGLY_THREATENED
    assert report.direct_priors == ()
    assert report.strong_priors


def test_no_direct_prior_language_is_scoped_not_absolute_novelty_claim():
    records = filler_records()
    report = novelty_court(runs_with(records), ONTOLOGY)
    assert report.verdict == NoveltyVerdict.NO_DIRECT_PRIOR_WITHIN_SCOPE
    assert "within the frozen providers" in report.interpretation
    assert "not proof of absolute novelty" in report.interpretation
    assert evolution_actions(report, ONTOLOGY) == ()


def test_minimum_evidence_volume_is_enforced():
    policy = CoveragePolicy(min_unique_records=20, min_records_with_abstract=3)
    report = novelty_court(runs_with(filler_records()), ONTOLOGY, policy=policy)
    assert report.verdict == NoveltyVerdict.INSUFFICIENT_COVERAGE


def test_search_snapshot_is_deterministic():
    records = filler_records()
    a = novelty_court(runs_with(records), ONTOLOGY)
    b = novelty_court(list(reversed(runs_with(list(reversed(records))))), ONTOLOGY)
    assert a.search_snapshot_sha256 == b.search_snapshot_sha256
