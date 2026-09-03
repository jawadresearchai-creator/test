from agri_coscientist.journal import JournalPolicy, StudySummary, journal_fit
from agri_coscientist.repositories import OmicsRecord, InMemoryAdapter


def test_journal_gate_requires_public_data_provenance():
    p=JournalPolicy('configured-target', scope_terms=('plant signaling','root signaling'))
    s=StudySummary('original_research','hybrid',('plant signaling','wheat'),False)
    ok,issues=journal_fit(p,s)
    assert not ok and any('provenance' in x for x in issues)


def test_journal_gate_passes_configured_hybrid_study():
    p=JournalPolicy('configured-target', scope_terms=('plant signaling','root signaling'))
    s=StudySummary('original_research','hybrid',('plant signaling','wheat'),True)
    assert journal_fit(p,s)[0]


def test_repository_adapter_contract():
    r=OmicsRecord('GSE183508','GEO','Triticum aestivum','root','hypergravity',4,True,True)
    a=InMemoryAdapter([r])
    assert a.search('hypergravity')[0].accession=='GSE183508'
    assert a.fetch_metadata('GSE183508').processed_available
