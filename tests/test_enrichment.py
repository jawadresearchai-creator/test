import json
import pytest

from agri_coscientist.annotation import WHEAT_REFSEQ_V2
from agri_coscientist.enrichment import (
    GProfilerAdapter,
    benjamini_hochberg,
    overrepresentation,
)


class FakeResponse:
    def __init__(self, value): self.payload = json.dumps(value).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.payload


def test_bh_fdr_is_bounded_and_monotone_by_rank():
    p = [0.001, 0.01, 0.04, 0.2]
    q = benjamini_hochberg(p)
    assert all(0 <= value <= 1 for value in q)
    ranked = sorted(zip(p, q))
    assert [x[1] for x in ranked] == sorted(x[1] for x in ranked)


def test_local_ora_requires_explicit_background_and_fdr():
    background = [f"g{i}" for i in range(1, 101)]
    query = [f"g{i}" for i in range(1, 11)]
    associations = {
        "GO:MECH": [f"g{i}" for i in range(1, 9)] + ["g50", "g51"],
        "GO:BROAD": [f"g{i}" for i in range(1, 31)],
    }
    results = overrepresentation(query, background, associations)
    assert results[0].term_id == "GO:MECH"
    assert results[0].intersection_size == 8
    assert results[0].background_size == 100
    assert results[0].q_value <= results[1].q_value


def test_local_ora_rejects_query_gene_outside_universe():
    with pytest.raises(ValueError):
        overrepresentation(["g1", "gX"], ["g1", "g2"], {"GO:X": ["g1"]})


def test_gprofiler_uses_custom_background_and_fdr():
    captured = {}
    response = {
        "result": [{
            "native": "GO:0006950",
            "name": "response to stress",
            "source": "GO:BP",
            "p_value": 0.02,
            "query_size": 2,
            "effective_domain_size": 4,
            "term_size": 3,
            "intersection_size": 2,
            "intersections": ["g1", "g2"],
        }]
    }
    def opener(req, timeout=60):
        captured["body"] = json.loads(req.data.decode())
        return FakeResponse(response)
    adapter = GProfilerAdapter(opener=opener)
    results = adapter.profile(["g1", "g2"], ["g1", "g2", "g3", "g4"], WHEAT_REFSEQ_V2)
    body = captured["body"]
    assert body["organism"] == "tarefseqv2"
    assert body["domain_scope"] == "custom"
    assert body["significance_threshold_method"] == "fdr"
    assert body["background"] == ["g1", "g2", "g3", "g4"]
    assert results[0].q_value == 0.02


def test_gprofiler_refuses_query_outside_background():
    adapter = GProfilerAdapter(opener=lambda *args, **kwargs: None)
    with pytest.raises(ValueError):
        adapter.profile(["gX"], ["g1"], WHEAT_REFSEQ_V2)
