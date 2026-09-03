import gzip
import json

from agri_coscientist.repositories import GEOAdapter

class FakeResponse:
    def __init__(self, payload: bytes): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.payload

def test_geo_adapter_search_uses_eutils_and_returns_gse():
    def opener(req, timeout=60):
        url = req.full_url
        if "esearch.fcgi" in url:
            return FakeResponse(json.dumps({"esearchresult": {"idlist": ["123"]}}).encode())
        assert "esummary.fcgi" in url
        return FakeResponse(json.dumps({"result": {"uids": ["123"], "123": {
            "accession": "GSE183508", "taxon": "Triticum aestivum", "n_samples": 4
        }}}).encode())
    records = GEOAdapter(opener=opener).search("wheat root")
    assert len(records) == 1
    assert records[0].accession == "GSE183508"
    assert records[0].sample_count == 4

def test_geo_adapter_fetches_and_parses_family_soft():
    soft = """^SERIES = GSE183508
!Series_title = Transcriptome profile of hypergravity-induced enhanced wheat root growth
!Series_relation = SRA: https://www.ncbi.nlm.nih.gov/sra?term=SRP123
!Series_supplementary_file = https://example/counts.tsv.gz
^SAMPLE = GSM1
!Sample_organism_ch1 = Triticum aestivum
!Sample_source_name_ch1 = root
!Sample_treatment_protocol_ch1 = control
^SAMPLE = GSM2
!Sample_organism_ch1 = Triticum aestivum
!Sample_source_name_ch1 = root
!Sample_treatment_protocol_ch1 = hypergravity
"""
    payload = gzip.compress(soft.encode())
    adapter = GEOAdapter(opener=lambda req, timeout=60: FakeResponse(payload))
    r = adapter.fetch_metadata("GSE183508")
    assert r.organism == "Triticum aestivum"
    assert r.tissue == "root"
    assert r.treatment is None
    assert r.sample_count == 2
    assert r.raw_available and r.processed_available
    assert r.metadata["treatments"] == ["control", "hypergravity"]
    assert r.metadata["sample_accessions"] == ["GSM1", "GSM2"]

def test_geo_family_soft_url_is_deterministic():
    assert GEOAdapter.family_soft_url("GSE183508").endswith(
        "/GSE183nnn/GSE183508/soft/GSE183508_family.soft.gz"
    )
