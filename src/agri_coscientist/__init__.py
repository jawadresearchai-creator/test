"""Agriculture CoScientist isolated test kernel."""
from .state import ProjectState, Stage, StudyMode
from .gates import OmicsMetadata, OmicsFitness, grade_omics_fitness
from .provenance import freeze_manifest, verify_manifest, analysis_lock
from .claims import EvidenceStrength, claim_verb
from .feasibility import (
    CourtStatus,
    FeasibilityDimension,
    FeasibilityGrade,
    PublicDataRole,
    RouteProposal,
    evaluate_route,
    feasibility_court,
)
from .data_fitness import (
    DataDomain,
    DataFitnessCourtResult,
    DataFitnessDimension,
    DataFitnessGrade,
    DataFitnessPolicy,
    DataFitnessProfile,
    DataFitnessStatus,
    DataUseRole,
    DatasetFitnessReport,
    data_fitness_court,
    evaluate_general_data_fitness,
    evaluate_layered_data_fitness,
)
from .design import (
    AllocationMethod,
    DesignCourtResult,
    DesignFreeze,
    DesignGrade,
    DesignStatus,
    InferenceIntent,
    OutcomeSpec,
    OutcomeTier,
    PhysicalDesign,
    PublicDatasetDesign,
    StudyDesign,
    build_design_freeze,
    design_court,
    freeze_project_design,
)

__all__ = [
    "ProjectState", "Stage", "StudyMode", "OmicsMetadata", "OmicsFitness",
    "grade_omics_fitness", "freeze_manifest", "verify_manifest", "analysis_lock",
    "EvidenceStrength", "claim_verb", "CourtStatus", "FeasibilityDimension",
    "FeasibilityGrade", "PublicDataRole", "RouteProposal", "evaluate_route",
    "feasibility_court", "DataDomain", "DataFitnessCourtResult",
    "DataFitnessDimension", "DataFitnessGrade", "DataFitnessPolicy",
    "DataFitnessProfile", "DataFitnessStatus", "DataUseRole",
    "DatasetFitnessReport", "data_fitness_court", "evaluate_general_data_fitness",
    "evaluate_layered_data_fitness", "AllocationMethod", "DesignCourtResult",
    "DesignFreeze", "DesignGrade", "DesignStatus", "InferenceIntent",
    "OutcomeSpec", "OutcomeTier", "PhysicalDesign", "PublicDatasetDesign",
    "StudyDesign", "build_design_freeze", "design_court", "freeze_project_design"
]
