from agri_coscientist.claims import EvidenceStrength, claim_verb

def test_claim_calibration():
    assert claim_verb(EvidenceStrength.MECHANISTIC) == "is consistent with"
    assert claim_verb(EvidenceStrength.SPECULATIVE) == "may suggest"
