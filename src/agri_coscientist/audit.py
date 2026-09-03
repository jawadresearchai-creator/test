from __future__ import annotations
from .gates import OmicsFitness
from .claims import EvidenceStrength


def audit_omics_claim(fitness: OmicsFitness, proposed_strength: EvidenceStrength) -> list[str]:
    issues=[]
    if fitness in {OmicsFitness.C, OmicsFitness.D} and proposed_strength in {
        EvidenceStrength.DIRECT_CAUSAL, EvidenceStrength.CONVERGENT
    }:
        issues.append("overclaim: mechanistic/contextual public omics cannot be presented as direct causal or convergent validation")
    if fitness is OmicsFitness.E:
        issues.append("incompatible dataset must not support the claim")
    return issues
