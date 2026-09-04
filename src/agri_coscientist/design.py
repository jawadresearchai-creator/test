from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable

from .blockers import BlockerGate
from .data_fitness import DataFitnessGrade, DataUseRole
from .state import ProjectState, Stage, StudyMode


class DesignGrade(str, Enum):
    PASS = "pass"
    CONDITIONAL = "conditional"
    FAIL = "fail"


class DesignStatus(str, Enum):
    ADVANCE = "advance"
    REVISE = "revise"
    BLOCKED = "blocked"


class InferenceIntent(str, Enum):
    DESCRIPTIVE = "descriptive"
    ASSOCIATIONAL = "associational"
    CAUSAL = "causal"


class OutcomeTier(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    MECHANISTIC = "mechanistic"
    QC = "qc"
    COVARIATE = "covariate"
    METADATA = "metadata"


class AllocationMethod(str, Enum):
    RANDOMIZED = "randomized"
    BLOCK_RANDOMIZED = "block_randomized"
    NONRANDOM = "nonrandom"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class OutcomeSpec:
    name: str
    tier: OutcomeTier
    measurement_method: str
    timepoint_or_window: str
    unit: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("outcome name is required")
        if not self.measurement_method.strip():
            raise ValueError(f"{self.name}: measurement_method is required")
        if not self.timepoint_or_window.strip():
            raise ValueError(f"{self.name}: timepoint_or_window is required")


@dataclass(frozen=True)
class PhysicalDesign:
    experimental_unit: str
    analysis_unit_matches_experimental_unit: bool
    independent_units_total: int
    independent_units_per_group: tuple[int, ...]
    replication_rationale: str
    precision_or_power_plan: str

    treatments: tuple[str, ...]
    controls: tuple[str, ...]
    manipulated_exposure: bool
    allocation_method: AllocationMethod
    randomization_plan: str

    nuisance_gradient_expected: bool
    blocking_factors: tuple[str, ...]
    blocking_plan: str

    subsamples_per_unit: int
    subsamples_treated_as_technical: bool
    repeated_measures: bool
    repeated_measure_unit_id_preserved: bool
    destructive_sampling: bool
    independent_units_per_destructive_timepoint: bool

    sampling_schedule: tuple[str, ...]
    required_methods: tuple[str, ...]
    unavailable_methods: tuple[str, ...] = ()

    blinding_feasible: bool = False
    blinded_outcome_assessment: bool = False
    blinding_plan: str = ""

    def __post_init__(self) -> None:
        if not self.experimental_unit.strip():
            raise ValueError("physical design requires an explicit experimental unit")
        if self.independent_units_total < 1:
            raise ValueError("independent_units_total must be >= 1")
        if not self.independent_units_per_group or any(n < 1 for n in self.independent_units_per_group):
            raise ValueError("independent_units_per_group must contain positive counts")
        if sum(self.independent_units_per_group) != self.independent_units_total:
            raise ValueError("independent unit group counts must sum to independent_units_total")
        if self.subsamples_per_unit < 1:
            raise ValueError("subsamples_per_unit must be >= 1")


@dataclass(frozen=True)
class PublicDatasetDesign:
    dataset_id: str
    role: DataUseRole
    layered_data_fitness: DataFitnessGrade
    source_design_understood: bool
    source_experimental_or_sampling_unit: str
    sample_independence_known: bool
    planned_use_or_contrast: str
    supports_causal_identification: bool = False
    result_level_outcomes_accessed_before_design_freeze: bool = False

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise ValueError("dataset_id is required")
        if not self.source_experimental_or_sampling_unit.strip():
            raise ValueError(f"{self.dataset_id}: source experimental/sampling unit is required")
        if not self.planned_use_or_contrast.strip():
            raise ValueError(f"{self.dataset_id}: planned use/contrast is required")


@dataclass(frozen=True)
class StudyDesign:
    design_id: str
    question: str
    hypotheses: tuple[str, ...]
    mode: StudyMode
    inference_intent: InferenceIntent
    confirmatory: bool

    outcomes: tuple[OutcomeSpec, ...]
    covariates: tuple[str, ...]
    metadata_fields: tuple[str, ...]
    exclusion_criteria: tuple[str, ...]
    quality_controls: tuple[str, ...]

    physical: PhysicalDesign | None = None
    public_datasets: tuple[PublicDatasetDesign, ...] = ()

    outcome_data_accessed_before_design_freeze: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.design_id.strip():
            raise ValueError("design_id is required")
        if not self.question.strip():
            raise ValueError("research question is required")
        if not self.hypotheses:
            raise ValueError("at least one explicit hypothesis/estimand statement is required")
        if not self.outcomes:
            raise ValueError("at least one outcome is required")
        names = [o.name.casefold().strip() for o in self.outcomes]
        if len(set(names)) != len(names):
            raise ValueError("outcome names must be unique")
        if not any(o.tier is OutcomeTier.PRIMARY for o in self.outcomes):
            raise ValueError("at least one primary outcome is required")


@dataclass(frozen=True)
class DesignIssue:
    code: str
    grade: DesignGrade
    reason: str
    repair_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class DesignCourtResult:
    status: DesignStatus
    issues: tuple[DesignIssue, ...]
    required_actions: tuple[str, ...]
    advancement_allowed: bool


@dataclass(frozen=True)
class DesignFreeze:
    design_id: str
    design_payload: dict
    design_freeze_sha256: str
    pre_outcome: bool
    analysis_model_locked: bool = False


def _issue(code: str, grade: DesignGrade, reason: str, *repairs: str) -> DesignIssue:
    return DesignIssue(code=code, grade=grade, reason=reason, repair_actions=tuple(repairs))


def _check_route_shape(design: StudyDesign) -> list[DesignIssue]:
    issues: list[DesignIssue] = []
    has_physical = design.physical is not None
    has_public = bool(design.public_datasets)
    if design.mode is StudyMode.PHYSICAL and (not has_physical or has_public):
        issues.append(_issue(
            "route_shape",
            DesignGrade.FAIL,
            "physical mode requires a physical design and no route-required public dataset plan",
            "repair:route_shape",
        ))
    elif design.mode is StudyMode.PUBLIC_DATA and (has_physical or not has_public):
        issues.append(_issue(
            "route_shape",
            DesignGrade.FAIL,
            "public-data mode requires public dataset design and no physical experiment",
            "repair:route_shape",
        ))
    elif design.mode is StudyMode.HYBRID and (not has_physical or not has_public):
        issues.append(_issue(
            "route_shape",
            DesignGrade.FAIL,
            "hybrid mode requires both a physical experiment and public-data component",
            "repair:route_shape",
        ))
    return issues


def _check_outcomes(design: StudyDesign) -> list[DesignIssue]:
    issues: list[DesignIssue] = []
    primaries = [o for o in design.outcomes if o.tier is OutcomeTier.PRIMARY]
    if design.confirmatory and len(primaries) > 3:
        issues.append(_issue(
            "primary_outcome_multiplicity",
            DesignGrade.CONDITIONAL,
            "confirmatory design has more than three co-primary outcomes; multiplicity and interpretation burden must be justified before freeze",
            "justify:co_primary_outcomes",
            "reduce:primary_outcomes",
        ))
    if design.confirmatory and not design.exclusion_criteria:
        issues.append(_issue(
            "exclusions_not_prespecified",
            DesignGrade.FAIL,
            "confirmatory design requires predeclared exclusion criteria, including an explicit none-planned rule when applicable",
            "specify:exclusion_criteria",
        ))
    if not design.quality_controls:
        issues.append(_issue(
            "quality_controls_missing",
            DesignGrade.FAIL,
            "design requires explicit quality-control checks before acquisition/analysis",
            "specify:quality_controls",
        ))
    if not design.metadata_fields:
        issues.append(_issue(
            "metadata_missing",
            DesignGrade.CONDITIONAL,
            "no acquisition metadata fields are prespecified",
            "specify:metadata_fields",
        ))
    return issues


def _check_physical(design: StudyDesign) -> list[DesignIssue]:
    p = design.physical
    if p is None:
        return []
    issues: list[DesignIssue] = []

    if not p.analysis_unit_matches_experimental_unit:
        issues.append(_issue(
            "analysis_unit_mismatch",
            DesignGrade.FAIL,
            "analysis unit does not match the independently assigned experimental unit; pseudoreplication risk is unresolved",
            "repair:analysis_unit",
        ))
    if any(n < 2 for n in p.independent_units_per_group) and design.confirmatory:
        issues.append(_issue(
            "independent_replication_insufficient",
            DesignGrade.FAIL,
            "confirmatory groups require more than one independent biological/experimental unit to estimate within-group variation",
            "increase:independent_replication",
            "evolve:exploratory_design",
        ))
    if not p.replication_rationale.strip() or not p.precision_or_power_plan.strip():
        issues.append(_issue(
            "replication_rationale_missing",
            DesignGrade.FAIL,
            "independent replication requires an explicit scientific rationale and precision/power planning approach",
            "specify:replication_rationale",
            "specify:precision_or_power_plan",
        ))
    if len(p.treatments) < 1:
        issues.append(_issue("treatments_missing", DesignGrade.FAIL, "physical design has no treatment/exposure definition", "specify:treatments"))
    if len(p.controls) < 1:
        issues.append(_issue("controls_missing", DesignGrade.FAIL, "physical design has no explicit control/comparator", "specify:controls"))

    required = {m.casefold().strip() for m in p.required_methods}
    unavailable = {m.casefold().strip() for m in p.unavailable_methods}
    overlap = sorted(required & unavailable)
    if overlap:
        issues.append(_issue(
            "unavailable_method_required",
            DesignGrade.FAIL,
            "design requires method(s) explicitly unavailable to the research setting: " + ", ".join(overlap),
            "remove:unavailable_method_requirement",
            "evolve:feasible_measurement_route",
            "use:public_data_if_scientifically_valid",
        ))

    if p.subsamples_per_unit > 1 and not p.subsamples_treated_as_technical:
        issues.append(_issue(
            "subsample_pseudoreplication",
            DesignGrade.FAIL,
            "within-unit subsamples are not explicitly treated as technical/subsample observations",
            "repair:subsample_hierarchy",
        ))
    if p.repeated_measures and not p.repeated_measure_unit_id_preserved:
        issues.append(_issue(
            "repeated_measure_identity_missing",
            DesignGrade.FAIL,
            "repeated measures require persistent experimental-unit identity",
            "preserve:repeated_measure_unit_id",
        ))
    if p.repeated_measures and p.destructive_sampling and not p.independent_units_per_destructive_timepoint:
        issues.append(_issue(
            "destructive_repeated_measure_conflict",
            DesignGrade.FAIL,
            "destructive sampling cannot create repeated observations from the same destroyed unit; independent units per destructive timepoint are required",
            "repair:destructive_sampling_unit_structure",
        ))
    if not p.sampling_schedule:
        issues.append(_issue("sampling_schedule_missing", DesignGrade.FAIL, "physical design has no prespecified sampling schedule", "specify:sampling_schedule"))

    if design.inference_intent is InferenceIntent.CAUSAL:
        if not p.manipulated_exposure:
            issues.append(_issue(
                "causal_without_manipulation",
                DesignGrade.FAIL,
                "causal physical inference requires a manipulated exposure/intervention",
                "calibrate:associational_inference",
            ))
        if p.allocation_method not in {AllocationMethod.RANDOMIZED, AllocationMethod.BLOCK_RANDOMIZED}:
            issues.append(_issue(
                "causal_without_randomization",
                DesignGrade.FAIL,
                "unqualified causal physical inference requires randomized allocation in this experimental route",
                "randomize:allocation",
                "calibrate:noncausal_inference",
            ))
        if not p.randomization_plan.strip():
            issues.append(_issue(
                "randomization_plan_missing",
                DesignGrade.FAIL,
                "randomized design requires a reproducible allocation plan",
                "specify:randomization_plan",
            ))

    if p.nuisance_gradient_expected and not p.blocking_factors:
        issues.append(_issue(
            "blocking_missing",
            DesignGrade.FAIL,
            "known nuisance gradient is expected but no blocking factor is defined",
            "specify:blocking_factor",
        ))
    if p.blocking_factors and not p.blocking_plan.strip():
        issues.append(_issue(
            "blocking_plan_missing",
            DesignGrade.FAIL,
            "blocking factors are declared but the block construction/allocation plan is missing",
            "specify:blocking_plan",
        ))

    if p.blinding_feasible and not p.blinded_outcome_assessment:
        issues.append(_issue(
            "blinding_not_used",
            DesignGrade.CONDITIONAL,
            "outcome-assessment blinding is feasible but not planned",
            "blind:outcome_assessment",
            "justify:no_blinding",
        ))
    return issues


def _check_public(design: StudyDesign) -> list[DesignIssue]:
    issues: list[DesignIssue] = []
    ids = [d.dataset_id for d in design.public_datasets]
    if len(ids) != len(set(ids)):
        issues.append(_issue("duplicate_public_dataset", DesignGrade.FAIL, "public dataset IDs must be unique", "deduplicate:public_datasets"))

    for d in design.public_datasets:
        prefix = f"public:{d.dataset_id}:"
        if d.layered_data_fitness is not DataFitnessGrade.PASS:
            issues.append(_issue(
                prefix + "data_fitness_not_passed",
                DesignGrade.FAIL,
                "route-required public dataset has not passed layered General G3/domain Data Fitness",
                "return:data_fitness",
            ))
        if not d.source_design_understood:
            issues.append(_issue(
                prefix + "source_design_unknown",
                DesignGrade.FAIL,
                "source study design is not sufficiently understood for prespecified reuse",
                "resolve:source_design",
            ))
        if not d.sample_independence_known:
            issues.append(_issue(
                prefix + "sample_independence_unknown",
                DesignGrade.FAIL,
                "source sample/experimental-unit independence is unresolved",
                "resolve:sample_independence",
            ))
        if design.confirmatory and d.result_level_outcomes_accessed_before_design_freeze:
            issues.append(_issue(
                prefix + "pre_freeze_outcome_access",
                DesignGrade.FAIL,
                "confirmatory public-data outcomes were inspected before Design Freeze",
                "reclassify:exploratory",
                "restart:independent_confirmatory_dataset",
            ))
        if design.inference_intent is InferenceIntent.CAUSAL and d.role is DataUseRole.PRIMARY_TEST and not d.supports_causal_identification:
            issues.append(_issue(
                prefix + "causal_identification_not_supported",
                DesignGrade.FAIL,
                "primary public dataset does not support the proposed causal identification",
                "calibrate:associational_inference",
                "discover:causally_identifiable_dataset",
            ))
    return issues


def design_court(
    design: StudyDesign,
    *,
    blocker_gate: BlockerGate | None = None,
) -> DesignCourtResult:
    """Adversarial pre-outcome design gate; statistical model locking comes later."""

    if blocker_gate is not None:
        blocker_gate.assert_can_advance(from_phase="data_fitness", to_phase="design")

    issues: list[DesignIssue] = []
    issues.extend(_check_route_shape(design))
    issues.extend(_check_outcomes(design))
    issues.extend(_check_physical(design))
    issues.extend(_check_public(design))

    if design.confirmatory and design.outcome_data_accessed_before_design_freeze:
        issues.append(_issue(
            "pre_freeze_outcome_access",
            DesignGrade.FAIL,
            "confirmatory outcome data were accessed before Design Freeze",
            "reclassify:exploratory",
            "restart:confirmatory_design_before_outcome_access",
        ))

    grades = {i.grade for i in issues}
    status = (
        DesignStatus.BLOCKED if DesignGrade.FAIL in grades
        else DesignStatus.REVISE if DesignGrade.CONDITIONAL in grades
        else DesignStatus.ADVANCE
    )
    actions = tuple(dict.fromkeys(a for i in issues for a in i.repair_actions))
    return DesignCourtResult(
        status=status,
        issues=tuple(issues),
        required_actions=actions,
        advancement_allowed=status is DesignStatus.ADVANCE,
    )


def _canonicalize(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _canonicalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(v) for v in value]
    return value


def build_design_freeze(design: StudyDesign, court_result: DesignCourtResult) -> DesignFreeze:
    if not court_result.advancement_allowed:
        raise ValueError("Design Freeze requires an ADVANCE design-court verdict")
    if design.confirmatory and design.outcome_data_accessed_before_design_freeze:
        raise ValueError("cannot freeze a confirmatory design after outcome access")

    payload = _canonicalize(asdict(design))
    # Analysis-method/model/software choices are deliberately absent. They belong
    # to the separate Analysis Lock after Design Freeze.
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    digest = sha256(raw).hexdigest()
    return DesignFreeze(
        design_id=design.design_id,
        design_payload=payload,
        design_freeze_sha256=digest,
        pre_outcome=not design.outcome_data_accessed_before_design_freeze,
        analysis_model_locked=False,
    )


def freeze_project_design(
    state: ProjectState,
    design: StudyDesign,
    court_result: DesignCourtResult,
    *,
    blocker_gate: BlockerGate | None = None,
) -> DesignFreeze:
    if blocker_gate is not None:
        blocker_gate.assert_can_advance(from_phase="design", to_phase="design_frozen")
    if state.stage is not Stage.DESIGN:
        raise ValueError(f"Design Freeze requires project stage=design, observed {state.stage.value}")
    freeze = build_design_freeze(design, court_result)
    state.transition(Stage.DESIGN_FROZEN, f"Design Freeze {freeze.design_freeze_sha256}")
    return freeze
