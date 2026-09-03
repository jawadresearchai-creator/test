from agri_coscientist.geo import geo_stub, geo_supplementary_base, DataAvailability, DataRepresentation, choose_representation
import pytest


def test_geo_stub_and_sample_url():
    assert geo_stub('GSM7510649') == 'GSM7510nnn'
    assert geo_supplementary_base('GSM7510649') == 'https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM7510nnn/GSM7510649/suppl/'


def test_geo_series_url():
    assert geo_supplementary_base('GSE183508') == 'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE183nnn/GSE183508/suppl/'


def test_invalid_accession_rejected():
    with pytest.raises(ValueError): geo_stub('ABC123')


def test_counts_preferred_when_read_level_not_needed():
    a=DataAvailability(True,True,True,3000,12,10)
    assert choose_representation(a,False) is DataRepresentation.RAW_COUNTS
    assert choose_representation(a,True) is DataRepresentation.RAW_READS
