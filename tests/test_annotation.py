import json
import pytest

from agri_coscientist.annotation import (
    BuildMismatchError,
    EnsemblRestAdapter,
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


def _raw(species="triticum_aestivum_refseqv2", assembly="IWGSC_RefSeq_v2.1"):
    return {
        "id": "TraesCS1D03G0909900",
        "species": species,
        "assembly_name": assembly,
        "biotype": "protein_coding",
        "display_name": "EXAMPLE",
        "seq_region_name": "1D",
        "start": 464844142,
        "end": 464845692,
        "strand": 1,
    }


def test_ensembl_rest_lookup_accepts_provider_species_and_exact_build():
    captured = {}
    def opener(req, timeout=30):
        captured["url"] = req.full_url
        return FakeResponse(_raw())
    adapter = EnsemblRestAdapter(opener=opener)
    annotation = adapter.lookup("TraesCS1D03G0909900", WHEAT_REFSEQ_V2)
    assert annotation.assembly == WHEAT_REFSEQ_V2.assembly
    assert annotation.seq_region == "1D"
    assert annotation.provider == "Ensembl REST"
    assert "species=triticum_aestivum_refseqv2" in captured["url"]


def test_gramene_lookup_accepts_common_species_name_when_build_matches():
    adapter = GrameneEnsemblAdapter(opener=lambda req, timeout=30: FakeResponse(_raw(species="triticum_aestivum")))
    annotation = adapter.lookup("TraesCS1D03G0909900", WHEAT_REFSEQ_V2)
    assert annotation.assembly == WHEAT_REFSEQ_V2.assembly


def test_annotation_lookup_rejects_cross_assembly_data():
    adapter = EnsemblRestAdapter(opener=lambda req, timeout=30: FakeResponse(_raw(assembly="IWGSC")))
    with pytest.raises(BuildMismatchError):
        adapter.lookup("TraesCS1D03G0909900", WHEAT_REFSEQ_V2)


def test_annotation_lookup_rejects_wrong_species_data():
    adapter = EnsemblRestAdapter(opener=lambda req, timeout=30: FakeResponse(_raw(species="triticum_dicoccoides")))
    with pytest.raises(BuildMismatchError):
        adapter.lookup("TraesCS1D03G0909900", WHEAT_REFSEQ_V2)
