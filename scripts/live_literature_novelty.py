from __future__ import annotations

import json
from pathlib import Path

from agri_coscientist.literature import (
    CrossrefAdapter,
    EuropePMCAdapter,
    OpenAlexAdapter,
    deduplicate_records,
)
from agri_coscientist.novelty import (
    ConceptOntology,
    NoveltyVerdict,
    SearchRun,
    evolution_actions,
    novelty_court,
)


OUT = Path("live_literature_novelty.json")
FROM_YEAR = 2024
TO_YEAR = 2026

# Capability scenario only. The ontology and search families are frozen before
# retrieved records are interpreted by the novelty court.
ONTOLOGY = ConceptOntology(
    dimensions={
        "crop": ("wheat", "triticum aestivum"),
        "tissue": ("root", "roots"),
        "exposure": (
            "soil compaction", "mechanical impedance", "mechanical stress",
            "mechanostimulation", "mechanical stimulation",
        ),
        "signal": ("extracellular atp", "eatp", "purinergic"),
        "receiver": ("neighbor", "neighbour", "plant-plant", "interplant"),
        "outcome": ("priming", "stress memory", "antioxidant", "oxidative stress"),
        "mechanism": ("calcium", "mapk", "p2k1", "feronia", "ros"),
    },
    required_direct_dimensions=("crop", "tissue", "exposure", "signal", "receiver"),
)

QUERY_FAMILIES = {
    "exact_question": 'wheat root "extracellular ATP" "soil compaction" neighbor priming',
    "mechanism": 'FERONIA P2K1 "extracellular ATP" root',
    "crop_system": 'wheat root "soil compaction" signaling priming',
    "adjacent_concept": 'root mechanostimulation "extracellular ATP" calcium ROS',
}

KNOWN_EATP_DOI = "10.1080/15592324.2024.2370706"


def serialize_assessment(a):
    return {
        "identity": a.record.identity,
        "title": a.record.title,
        "year": a.record.year,
        "doi": a.record.doi,
        "provider": a.record.provider,
        "kind": a.record.kind.value,
        "retracted": a.record.is_retracted,
        "matched_dimensions": list(a.matched_dimensions),
    }


def main() -> None:
    epmc = EuropePMCAdapter()
    openalex = OpenAlexAdapter()
    crossref = CrossrefAdapter()
    adapters = {
        "europe_pmc": epmc,
        "openalex": openalex,
        "crossref": crossref,
    }

    # Europe PMC sentinel proves the live provider can recover a known recent
    # eATP/root article by exact DOI. OpenAlex and Crossref are independently
    # exercised below for every frozen query family.
    sentinel = epmc.search(
        f"DOI:{KNOWN_EATP_DOI}", from_year=FROM_YEAR, to_year=TO_YEAR, rows=10
    )
    sentinel_dois = {r.doi for r in sentinel.records if r.doi}
    if KNOWN_EATP_DOI not in sentinel_dois:
        raise RuntimeError(
            f"Europe PMC sentinel DOI not recovered: {KNOWN_EATP_DOI}; got {sorted(sentinel_dois)}"
        )

    runs: list[SearchRun] = []
    per_run = []
    for family, query in QUERY_FAMILIES.items():
        for provider, adapter in adapters.items():
            if provider == "openalex":
                result = adapter.search(
                    query, from_year=FROM_YEAR, to_year=TO_YEAR,
                    rows=100, max_records=1000,
                )
            else:
                result = adapter.search(
                    query, from_year=FROM_YEAR, to_year=TO_YEAR, rows=100
                )
            runs.append(SearchRun(family=family, result=result))
            per_run.append({
                "family": family,
                "provider": provider,
                "query": result.query,
                "total_hits": result.total_hits,
                "retrieved": result.retrieved,
                "negative_evidence_eligible": result.negative_evidence_eligible,
                "exhaustive_for_query": result.exhaustive_for_query,
                "supports_absence_inference": result.supports_absence_inference,
            })

    all_records = deduplicate_records(r for run in runs for r in run.result.records)
    for provider in adapters:
        if not any(r.provider == provider for r in all_records):
            raise RuntimeError(f"live discovery returned no {provider} records")

    report = novelty_court(runs, ONTOLOGY)
    if report.verdict == NoveltyVerdict.INSUFFICIENT_COVERAGE:
        failed = [
            row for row in report.negative_evidence_coverage
            if not row["supports_absence_inference"]
        ]
        raise RuntimeError(
            "live novelty search failed absence-evidence coverage policy: "
            f"providers={report.providers}, families={report.query_families}, "
            f"unique_records={report.unique_records}, failed={failed}"
        )

    payload = {
        "scenario": "wheat_root_mechanical_eatp_neighbor_priming_capability",
        "capability_only": True,
        "date_window": {"from_year": FROM_YEAR, "to_year": TO_YEAR},
        "query_families": QUERY_FAMILIES,
        "providers": list(report.providers),
        "provider_sentinel": {
            "doi": KNOWN_EATP_DOI,
            "europe_pmc_recovered": True,
            "records": [r.identity for r in sentinel.records],
        },
        "search_runs": per_run,
        "negative_evidence_coverage": list(report.negative_evidence_coverage),
        "unique_records": report.unique_records,
        "records_with_abstract": sum(bool(r.abstract) for r in all_records),
        "publication_kinds": {
            kind: sum(r.kind.value == kind for r in all_records)
            for kind in ("original", "review", "preprint", "other")
        },
        "verdict": report.verdict.value,
        "interpretation": report.interpretation,
        "search_snapshot_sha256": report.search_snapshot_sha256,
        "direct_priors": [serialize_assessment(a) for a in report.direct_priors[:20]],
        "strong_priors": [serialize_assessment(a) for a in report.strong_priors[:20]],
        "evolution_actions": list(evolution_actions(report, ONTOLOGY)),
        "claim_boundary": {
            "allowed": "scoped novelty-screen result within the frozen providers/query families/date window",
            "prohibited": [
                "absolute novelty proven by absence of hits",
                "using truncated Crossref results as negative novelty evidence",
                "treating a review as an original empirical prior",
                "ignoring a matching preprint as prior disclosure",
                "advancing a direct-prior candidate without evolution and rerun",
            ],
        },
        "status": "PASS",
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
