import json
from pathlib import Path
from agri_coscientist.journal import JournalPolicy, StudySummary, journal_fit


def test_psb_scope_snapshot_supports_signaling_hybrid_study():
    policy_path = Path(__file__).resolve().parents[1] / 'policies' / 'plant_signaling_behavior_2026-09-03.json'
    d=json.loads(policy_path.read_text())
    p=JournalPolicy(d['journal'], accepts_original_research=d['accepts_original_research'],
                    public_data_reanalysis_allowed=True, requires_data_provenance=True,
                    scope_terms=tuple(d['configured_scope_terms']))
    s=StudySummary('original_research','hybrid',('signal transduction','wheat','public omics'),True)
    assert journal_fit(p,s)[0]
