import json
from pathlib import Path

import pytest

from agri_coscientist.annotation import WHEAT_IWGSC_V1
from agri_coscientist.enrichment import GProfilerAdapter
from agri_coscientist.scenario import ScenarioError, validate_scenario_manifest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "scenarios" / "gse235844_rawal87_vs_sonalika_roots.json").read_text())


@pytest.mark.parametrize(
    "key,value",
    [
        ("enrichment_all_results_for_mapping_qc", False),
        ("min_query_mapping_fraction", 0.50),
        ("min_background_mapping_fraction", 0.50),
    ],
)
def test_mapping_qc_policy_cannot_be_weakened(key, value):
    bad = json.loads(json.dumps(MANIFEST))
    bad["analysis"][key] = value
    with pytest.raises(ScenarioError):
        validate_scenario_manifest(bad)


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_gprofiler_profile_response_preserves_provider_metadata_and_all_results_flag():
    captured = {}

    def opener(request, timeout=60):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response({
            "result": [
                {
                    "native": "GO:0000001",
                    "name": "example",
                    "source": "GO:BP",
                    "p_value": 0.04,
                    "query_size": 9,
                    "effective_domain_size": 95,
                    "term_size": 10,
                    "intersection_size": 2,
                    "significant": True,
                }
            ],
            "meta": {
                "genes_metadata": {
                    "failed": ["TraesCS_missing"],
                    "ambiguous": [],
                },
                "version": "test-version",
            },
        })

    adapter = GProfilerAdapter(opener=opener)
    query = [f"TraesCS1A02G{i:06d}" for i in range(10)]
    background = query + [f"TraesCS1B02G{i:06d}" for i in range(90)]
    response = adapter.profile_response(
        query,
        background,
        WHEAT_IWGSC_V1,
        all_results=True,
    )

    assert captured["body"]["all_results"] is True
    assert captured["body"]["domain_scope"] == "custom"
    assert captured["body"]["significance_threshold_method"] == "fdr"
    assert response.meta["genes_metadata"]["failed"] == ["TraesCS_missing"]
    assert response.results[0].query_size == 9
    assert response.results[0].background_size == 95


def test_gconvert_coverage_counts_only_unambiguous_mappings():
    captured = []

    def opener(request, timeout=60):
        body = json.loads(request.data.decode("utf-8"))
        captured.append(body)
        assert body["target"] == "ENSG"
        rows = []
        for gene in body["query"]:
            if gene == "G_unmapped":
                continue
            if gene == "G_ambiguous":
                rows.extend([
                    {"incoming": gene, "converted": "ENSG_A"},
                    {"incoming": gene, "converted": "ENSG_B"},
                ])
            else:
                rows.append({"incoming": gene, "converted": f"ENSG_{gene}"})
        return _Response({"result": rows})

    adapter = GProfilerAdapter(opener=opener)
    coverage = adapter.convert_coverage(
        ["G1", "G2", "G_unmapped", "G_ambiguous"],
        WHEAT_IWGSC_V1,
        chunk_size=2,
    )

    assert len(captured) == 2
    assert coverage.input_size == 4
    assert coverage.mapped_size == 2
    assert coverage.mapping_fraction == 0.5
    assert coverage.unmapped_ids == ("G_unmapped",)
    assert coverage.ambiguous_ids == ("G_ambiguous",)
    assert coverage.chunks == 2
    assert coverage.provider_result_rows == 4
