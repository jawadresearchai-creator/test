import gzip
import io
import json
from pathlib import Path

import pytest

from agri_coscientist.annotation import WHEAT_IWGSC_V1, WHEAT_REFSEQ_V2
from agri_coscientist.scenario import (
    FrozenAsset,
    ScenarioError,
    build_analysis_lock,
    build_dataset_freeze,
    canonical_hash,
    read_gzip_header_bytes,
    validate_featurecounts_header,
    validate_scenario_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "scenarios" / "gse235844_rawal87_vs_sonalika_roots.json").read_text())


def _gz(text: str) -> bytes:
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb") as fh:
        fh.write(text.encode())
    return out.getvalue()


def _bad_analysis(key, value):
    bad = json.loads(json.dumps(MANIFEST))
    bad["analysis"][key] = value
    return bad


def test_iwgsc_v1_and_refseq_v2_are_distinct_registered_builds():
    assert WHEAT_IWGSC_V1.assembly == "IWGSC"
    assert WHEAT_IWGSC_V1.accession == "GCA_900519105.1"
    assert WHEAT_IWGSC_V1.gprofiler_organism == "taestivum"
    assert WHEAT_IWGSC_V1 != WHEAT_REFSEQ_V2


def test_real_scenario_is_capability_only_and_count_based():
    validate_scenario_manifest(MANIFEST)
    assert MANIFEST["capability_only"] is True
    assert MANIFEST["dataset"]["representation"] == "featurecounts_integer_counts"
    assert MANIFEST["analysis"]["independent_filtering"] is False
    assert MANIFEST["analysis"]["cooks_cutoff"] is False
    assert MANIFEST["analysis"]["outlier_policy"] == "report_not_exclude"


def test_normalized_expression_cannot_masquerade_as_deseq_counts():
    bad = json.loads(json.dumps(MANIFEST))
    bad["dataset"]["representation"] = "TPM"
    with pytest.raises(ScenarioError):
        validate_scenario_manifest(bad)


def test_less_than_three_replicates_is_rejected():
    bad = json.loads(json.dumps(MANIFEST))
    bad["contrast"]["groups"][0]["expected_replicates"] = 2
    with pytest.raises(ScenarioError):
        validate_scenario_manifest(bad)


@pytest.mark.parametrize(
    "key,value",
    [
        ("design", "~ 1"),
        ("prefilter_total_count", 5),
        ("independent_filtering", True),
        ("cooks_cutoff", True),
        ("outlier_policy", "exclude"),
        ("fdr_method", "bonferroni"),
        ("fdr_threshold", 0.1),
        ("effect_threshold_for_enrichment", 0.5),
        ("enrichment_direction", "combined"),
        ("enrichment_background", "all_wheat_genes"),
        ("enrichment_provider", "other"),
        ("enrichment_domain_scope", "annotated"),
        ("enrichment_correction", "bonferroni"),
    ],
)
def test_locked_analysis_policy_cannot_be_weakened(key, value):
    with pytest.raises(ScenarioError):
        validate_scenario_manifest(_bad_analysis(key, value))


def test_featurecounts_header_requires_exact_replicate_count():
    payload = _gz("Geneid\tRawal_rep1\tRawal_rep2\tRawal_rep3\tLength\nG1\t1\t2\t3\t100\n")
    header = read_gzip_header_bytes(payload)
    assert validate_featurecounts_header(header, 3, "Rawal-87") == (
        "Rawal_rep1", "Rawal_rep2", "Rawal_rep3"
    )
    with pytest.raises(ScenarioError):
        validate_featurecounts_header(header, 2, "Rawal-87")


def test_standard_featurecounts_annotation_columns_are_not_counted_as_replicates():
    payload = _gz(
        "Geneid\tChr\tStart\tEnd\tStrand\tLength\tRawal_rep1\tRawal_rep2\tRawal_rep3\n"
        "G1\t1A\t100\t200\t+\t101\t10\t12\t9\n"
    )
    header = read_gzip_header_bytes(payload)
    assert validate_featurecounts_header(header, 3, "Rawal-87") == (
        "Rawal_rep1", "Rawal_rep2", "Rawal_rep3"
    )


def test_unknown_extra_featurecounts_column_is_not_silently_ignored():
    payload = _gz(
        "Geneid\tChr\tStart\tEnd\tStrand\tLength\tUnexpected\tRawal_rep1\tRawal_rep2\tRawal_rep3\n"
        "G1\t1A\t100\t200\t+\t101\t999\t10\t12\t9\n"
    )
    header = read_gzip_header_bytes(payload)
    with pytest.raises(ScenarioError):
        validate_featurecounts_header(header, 3, "Rawal-87")


def test_dataset_freeze_and_analysis_lock_are_deterministic_and_separate():
    a = FrozenAsset("Rawal-87_roots", "https://example/a.gz", "a" * 64, 100, ("Geneid", "r1", "r2", "r3", "Length"))
    b = FrozenAsset("Sonalika_roots", "https://example/b.gz", "b" * 64, 120, ("Geneid", "s1", "s2", "s3", "Length"))
    freeze1 = build_dataset_freeze(MANIFEST, [a, b])
    freeze2 = build_dataset_freeze(MANIFEST, [a, b])
    assert freeze1 == freeze2
    lock1 = build_analysis_lock(MANIFEST, freeze1, {"de.R": "1" * 64}, {"r": "2" * 64})
    lock2 = build_analysis_lock(MANIFEST, freeze1, {"de.R": "1" * 64}, {"r": "2" * 64})
    assert lock1 == lock2
    assert lock1["dataset_freeze_sha256"] == freeze1["freeze_sha256"]
    assert lock1["analysis_lock_sha256"] != freeze1["freeze_sha256"]


def test_analysis_lock_rejects_prespecified_threshold_change():
    a = FrozenAsset("Rawal-87_roots", "https://example/a.gz", "a" * 64, 100, ("Geneid", "r1", "r2", "r3", "Length"))
    b = FrozenAsset("Sonalika_roots", "https://example/b.gz", "b" * 64, 120, ("Geneid", "s1", "s2", "s3", "Length"))
    freeze = build_dataset_freeze(MANIFEST, [a, b])
    altered = json.loads(json.dumps(MANIFEST))
    altered["analysis"]["effect_threshold_for_enrichment"] = 0.5
    with pytest.raises(ScenarioError):
        build_analysis_lock(altered, freeze, {"de.R": "1" * 64}, {"r": "2" * 64})


def test_analysis_lock_changes_when_code_hash_changes():
    a = FrozenAsset("Rawal-87_roots", "https://example/a.gz", "a" * 64, 100, ("Geneid", "r1", "r2", "r3", "Length"))
    b = FrozenAsset("Sonalika_roots", "https://example/b.gz", "b" * 64, 120, ("Geneid", "s1", "s2", "s3", "Length"))
    freeze = build_dataset_freeze(MANIFEST, [a, b])
    lock1 = build_analysis_lock(MANIFEST, freeze, {"de.R": "1" * 64}, {"r": "2" * 64})
    lock2 = build_analysis_lock(MANIFEST, freeze, {"de.R": "3" * 64}, {"r": "2" * 64})
    assert lock1["analysis_lock_sha256"] != lock2["analysis_lock_sha256"]


def test_canonical_hash_is_key_order_independent():
    assert canonical_hash({"a": 1, "b": 2}) == canonical_hash({"b": 2, "a": 1})
