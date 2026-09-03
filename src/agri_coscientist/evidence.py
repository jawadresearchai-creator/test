from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .claims import EvidenceStrength

class EvidenceSource(str, Enum):
    NEW_EXPERIMENT = "new_experiment"
    PUBLIC_OMICS = "public_omics"
    LITERATURE = "literature"
    PUBLIC_NON_OMICS = "public_non_omics"

@dataclass(frozen=True)
class EvidenceItem:
    source: EvidenceSource
    identifier: str
    supports_claim: bool | None
    strength: EvidenceStrength
    independent: bool
    provenance: str
