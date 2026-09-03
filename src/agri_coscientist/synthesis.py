from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .claims import EvidenceStrength

class Direction(str, Enum):
    SUPPORT = "support"
    CONTRADICT = "contradict"
    NEUTRAL = "neutral"

@dataclass(frozen=True)
class ClaimEvidence:
    identifier: str
    direction: Direction
    strength: EvidenceStrength
    independent: bool = True

_WEIGHTS = {
    EvidenceStrength.DIRECT_CAUSAL: 6,
    EvidenceStrength.CONVERGENT: 5,
    EvidenceStrength.SUPPORTING: 4,
    EvidenceStrength.MECHANISTIC: 3,
    EvidenceStrength.CONTEXTUAL: 2,
    EvidenceStrength.SPECULATIVE: 1,
}


def synthesize(items: list[ClaimEvidence]) -> dict:
    support = sum(_WEIGHTS[i.strength] for i in items if i.direction is Direction.SUPPORT)
    contradict = sum(_WEIGHTS[i.strength] for i in items if i.direction is Direction.CONTRADICT)
    high_contradiction = any(i.independent and i.direction is Direction.CONTRADICT and _WEIGHTS[i.strength] >= 4 for i in items)
    if high_contradiction or (support and contradict >= 0.5*support):
        verdict = "mixed"
    elif support > contradict:
        verdict = "supports"
    elif contradict > support:
        verdict = "contradicts"
    else:
        verdict = "uncertain"
    return {"support_score":support,"contradiction_score":contradict,"verdict":verdict}
