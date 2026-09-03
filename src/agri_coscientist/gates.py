from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class OmicsFitness(str, Enum):
    A = "directly_comparable"
    B = "strongly_compatible"
    C = "mechanistically_compatible"
    D = "contextual_only"
    E = "incompatible"

@dataclass(frozen=True)
class OmicsMetadata:
    species_match: bool
    tissue_match: bool
    treatment_match: bool
    mechanistic_match: bool
    developmental_match: bool
    time_match: bool
    replicates_per_group: int
    metadata_complete: bool
    provenance_traceable: bool
    reusable: bool
    genotype_match: bool = False


def grade_omics_fitness(m: OmicsMetadata) -> OmicsFitness:
    """Conservative first-pass grade with direct-vs-mechanistic separation.

    A/B are suitable for stronger cross-study inference only when replication is >=3/group.
    C/D can still be retained for mechanistic/contextual triangulation when replication is >=2/group.
    """
    if not (m.provenance_traceable and m.reusable and m.metadata_complete):
        return OmicsFitness.E
    if m.replicates_per_group < 2:
        return OmicsFitness.E

    direct_components = sum([
        m.species_match, m.tissue_match, m.treatment_match,
        m.developmental_match, m.time_match, m.genotype_match
    ])

    if m.replicates_per_group >= 3 and direct_components == 6:
        return OmicsFitness.A
    if (m.replicates_per_group >= 3 and m.species_match and m.tissue_match
            and m.treatment_match and direct_components >= 4):
        return OmicsFitness.B
    if m.species_match and m.tissue_match and m.mechanistic_match:
        return OmicsFitness.C
    if m.species_match and (m.tissue_match or m.mechanistic_match):
        return OmicsFitness.D
    return OmicsFitness.E
