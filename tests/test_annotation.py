import json
import pytest

from agri_coscientist.annotation import (
    BuildMismatchError,
    GrameneEnsemblAdapter,
    WHEAT_REFSEQ_V2,
)


class FakeResponse:
    def __init__(self, value):
        self.payload = json.dumps(value).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.payload


def test_wheat_refseq_v2_registry_is_explicit():
    assert WHEAT_REFSEQ_V2.assembly == "IWGSC_RefSeq_v2.1"
    assert WHEAT_REFSEQ_V2.accession == "GCA_018294505.1"
    assert WHEAT_REFSEQ_V2.gprofiler_organism == "tarefseqv2"


def test_annotation_lookup_accepts_exact_build():
    raw = {
        "id": "TraesCS5A03G0935400",
        "species": "triticum_aestivum",
        "assembly_name": "IWGSC_RefSeq_v2.1",
        "biotype": "protein_coding",
        "display_name": "EXAMPLE",
        "seq_region_name": "5A",
        "start": 589259335,
        "end": 589271297,
        "strand": 1,
    }
    adapter = GrameneEnsemblAdapter(opener=lambda req, timeout=30: FakeResponse(raw))
    annotation = adapter.lookup("TraesCS5A03G0935400", WHEAT_REFSEQ_V2)
    assert annotation.gene_id == "TraesCS5A03G0935400"
    assert annotation.assembly == WHEAT_REFSEQ_V2.assembly
    assert annotation.seq_region == "5A"


def test_annotation_lookup_rejects_cross_assembly_data():
    raw = {
        "id": "TraesCS5A03G0935400",
        "species": "triticum_aestivum",
        "assembly_name": "IWGSC",
    }
    adapter = GrameneEnsemblAdapter(opener=lambda req, timeout=30: FakeResponse(raw))
    with pytest.raises(BuildMismatchError):
        adapter.lookup("TraesCS5A03G0935400", WHEAT_REFSEQ_V2)
