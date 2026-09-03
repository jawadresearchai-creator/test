from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class StudyMode(str, Enum):
    PHYSICAL = "physical_experiment"
    PUBLIC_DATA = "public_data"
    HYBRID = "hybrid"

class Stage(str, Enum):
    INTAKE = "intake"
    DISCOVERY = "discovery"
    NOVELTY = "novelty"
    FEASIBILITY = "feasibility"
    DATA_FITNESS = "data_fitness"
    DESIGN = "design"
    DESIGN_FROZEN = "design_frozen"
    ANALYSIS_LOCKED = "analysis_locked"
    ANALYSIS = "analysis"
    SYNTHESIS = "evidence_synthesis"
    PUBLICATION = "publication"
    AUDIT = "audit"
    COMPLETE = "complete"

_ALLOWED = {
    Stage.INTAKE: {Stage.DISCOVERY},
    Stage.DISCOVERY: {Stage.NOVELTY},
    Stage.NOVELTY: {Stage.FEASIBILITY, Stage.DISCOVERY},
    Stage.FEASIBILITY: {Stage.DATA_FITNESS, Stage.DISCOVERY},
    Stage.DATA_FITNESS: {Stage.DESIGN, Stage.DISCOVERY},
    Stage.DESIGN: {Stage.DESIGN_FROZEN, Stage.DISCOVERY},
    Stage.DESIGN_FROZEN: {Stage.ANALYSIS_LOCKED, Stage.DESIGN},
    Stage.ANALYSIS_LOCKED: {Stage.ANALYSIS},
    Stage.ANALYSIS: {Stage.SYNTHESIS, Stage.DESIGN},
    Stage.SYNTHESIS: {Stage.PUBLICATION, Stage.ANALYSIS, Stage.DESIGN},
    Stage.PUBLICATION: {Stage.AUDIT},
    Stage.AUDIT: {Stage.COMPLETE, Stage.PUBLICATION, Stage.ANALYSIS, Stage.DESIGN, Stage.DISCOVERY},
    Stage.COMPLETE: set(),
}

@dataclass
class ProjectState:
    name: str
    journal: str | None = None
    mode: StudyMode | None = None
    stage: Stage = Stage.INTAKE
    history: list[tuple[str, str]] = field(default_factory=list)

    def transition(self, target: Stage, reason: str) -> None:
        if target not in _ALLOWED[self.stage]:
            raise ValueError(f"invalid transition {self.stage.value} -> {target.value}")
        self.history.append((self.stage.value, reason))
        self.stage = target
