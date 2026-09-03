from enum import Enum

class EvidenceStrength(str, Enum):
    DIRECT_CAUSAL = "direct_causal"
    CONVERGENT = "convergent"
    SUPPORTING = "supporting"
    MECHANISTIC = "mechanistic_consistency"
    CONTEXTUAL = "contextual"
    SPECULATIVE = "speculative"

_VERBS = {
    EvidenceStrength.DIRECT_CAUSAL: "caused",
    EvidenceStrength.CONVERGENT: "supports",
    EvidenceStrength.SUPPORTING: "supports",
    EvidenceStrength.MECHANISTIC: "is consistent with",
    EvidenceStrength.CONTEXTUAL: "is compatible with",
    EvidenceStrength.SPECULATIVE: "may suggest",
}

def claim_verb(strength: EvidenceStrength) -> str:
    return _VERBS[strength]
