from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .blockers import BlockerGate
from .gates import OmicsFitness
from .state import StudyMode


class FeasibilityGrade(str, Enum):
    PASS = "pass"
    CONDITIONAL = "conditional"
    FAIL = "fail"


class CourtStatus(str, Enum):
    ADVANCE = "advance"
    REVISE = "revise"
    BLOCKED = "blocked"


class PublicDataRole(str, Enum):
    DIRECT_TEST = "direct_test"
    MECHANISTIC_SUPPORT = "mechanistic_support"
    CONTEXTUAL = "contextual"
    HYPOTHESIS_GENERATION = "hypothesis_generation"


class FeasibilityDimension(str, Enum):
    LAB = "laboratory"
    DATA = "data"
    COMPUTATIONAL = "computational"
    STATISTICAL = "statistical"
    RESOURCES = "resources"
    JOURNAL = "journal"
    PROVENANCE = "provenance"
    USER_CONSTRAINTS = "user_constraints"


@dataclass(frozen=True)
class RouteProposal:
    """Pre-outcome feasibility facts for one candidate execution route.

    The court does not invent these facts. The reasoning/discovery layer supplies
    them before design freeze, and the court deterministically evaluates them.
    """

    route_id: str
    mode: StudyMode

    # Laboratory / physical route facts.
    physical_experiment_required: bool
    core_physical_capabilities_available: bool
    requires_new_wetlab_omics: bool = False
    new_wetlab_omics_available: bool = False

    # Public-data route facts. Full G3/G3-OMICS still occurs downstream.
    public_data_required: bool = False
    public_data_candidates_found: int = 0
    best_public_omics_fitness: OmicsFitness | None = None
    public_data_role: PublicDataRole | None = None

    # Execution/runtime facts.
    compute_worker_available: bool = True
    required_runtime_available: bool = True

    # Statistical identifiability facts.
    primary_outcome_measurable: bool = True
    statistically_identifiable: bool = True
    independent_replication_adequate: bool = True
    confirmatory_intent: bool = True

    # Hard resource/user constraints.
    budget_feasible: bool = True
    timeline_feasible: bool = True
    user_constraints_satisfied: bool = True

    # Journal and provenance.
    journal_scope_fit: bool = True
    provenance_traceable: bool = True

    # Predeclared route-ranking inputs. Higher value is preferred; lower risk and
    # resource burden break ties. The court never fabricates these scores.
    scientific_value: int = 3
    execution_risk: int = 3
    resource_burden: int = 3

    def __post_init__(self) -> None:
        if not self.route_id.strip():
            raise ValueError("route_id is required")
        if self.public_data_candidates_found < 0:
            raise ValueError("public_data_candidates_found cannot be negative")
        for name, value in (
            ("scientific_value", self.scientific_value),
            ("execution_risk", self.execution_risk),
            ("resource_burden", self.resource_burden),
        ):
            if not 1 <= int(value) <= 5:
                raise ValueError(f"{name} must be in [1, 5]")
        if self.public_data_required and self.public_data_role is None:
            raise ValueError("public_data_role is required when public_data_required=true")
        if self.mode is StudyMode.PUBLIC_DATA and self.physical_experiment_required:
            raise ValueError("public-data-only route cannot require a physical experiment")
        if self.mode is StudyMode.PHYSICAL and self.public_data_required:
            raise ValueError("physical-only route cannot require public data")
        if self.requires_new_wetlab_omics and not self.physical_experiment_required:
            raise ValueError("new wet-lab omics can only be required by a physical component")


@dataclass(frozen=True)
class DimensionAssessment:
    dimension: FeasibilityDimension
    grade: FeasibilityGrade
    reasons: tuple[str, ...] = ()
    repair_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class RouteFeasibilityReport:
    route_id: str
    mode: StudyMode
    overall: FeasibilityGrade
    dimensions: tuple[DimensionAssessment, ...]
    repair_actions: tuple[str, ...]
    advancement_allowed: bool


@dataclass(frozen=True)
class FeasibilityCourtResult:
    status: CourtStatus
    selected_route_id: str | None
    viable_route_ids: tuple[str, ...]
    conditional_route_ids: tuple[str, ...]
    failed_route_ids: tuple[str, ...]
    reports: tuple[RouteFeasibilityReport, ...]
    required_actions: tuple[str, ...]


def _assessment(
    dimension: FeasibilityDimension,
    grade: FeasibilityGrade,
    *reasons: str,
    repairs: tuple[str, ...] = (),
) -> DimensionAssessment:
    return DimensionAssessment(
        dimension=dimension,
        grade=grade,
        reasons=tuple(r for r in reasons if r),
        repair_actions=repairs,
    )


def _public_data_assessment(route: RouteProposal) -> DimensionAssessment:
    if not route.public_data_required:
        return _assessment(FeasibilityDimension.DATA, FeasibilityGrade.PASS)
    if route.public_data_candidates_found == 0:
        return _assessment(
            FeasibilityDimension.DATA,
            FeasibilityGrade.FAIL,
            "route requires public data but no candidate dataset was found",
            repairs=("discover:public_data", "evolve:question_or_dataset_scope"),
        )
    grade = route.best_public_omics_fitness
    if grade is None:
        return _assessment(
            FeasibilityDimension.DATA,
            FeasibilityGrade.CONDITIONAL,
            "public data exist but preliminary biological compatibility is not yet graded",
            repairs=("grade:preliminary_public_data_compatibility",),
        )
    if grade is OmicsFitness.E:
        return _assessment(
            FeasibilityDimension.DATA,
            FeasibilityGrade.FAIL,
            "best available public dataset is incompatible with the intended use",
            repairs=("discover:alternative_dataset", "evolve:claim_or_question"),
        )

    role = route.public_data_role
    if role is PublicDataRole.DIRECT_TEST:
        if grade is OmicsFitness.A:
            return _assessment(FeasibilityDimension.DATA, FeasibilityGrade.PASS)
        return _assessment(
            FeasibilityDimension.DATA,
            FeasibilityGrade.CONDITIONAL,
            f"{grade.value} public data are insufficient for an unqualified direct-test claim",
            repairs=("calibrate:public_data_claim_role", "discover:more_direct_dataset"),
        )
    if role is PublicDataRole.MECHANISTIC_SUPPORT:
        if grade in {OmicsFitness.A, OmicsFitness.B, OmicsFitness.C}:
            return _assessment(FeasibilityDimension.DATA, FeasibilityGrade.PASS)
        return _assessment(
            FeasibilityDimension.DATA,
            FeasibilityGrade.CONDITIONAL,
            "contextual-only data cannot be treated as mechanistic support without claim revision",
            repairs=("calibrate:public_data_claim_role", "discover:mechanistically_compatible_dataset"),
        )
    if role in {PublicDataRole.CONTEXTUAL, PublicDataRole.HYPOTHESIS_GENERATION}:
        return _assessment(FeasibilityDimension.DATA, FeasibilityGrade.PASS)
    raise ValueError("public_data_role must be set for a public-data route")


def evaluate_route(route: RouteProposal) -> RouteFeasibilityReport:
    dimensions: list[DimensionAssessment] = []

    if route.physical_experiment_required and not route.core_physical_capabilities_available:
        dimensions.append(_assessment(
            FeasibilityDimension.LAB,
            FeasibilityGrade.FAIL,
            "required core physical experiment cannot be executed with available facilities",
            repairs=("evolve:physical_protocol", "consider:public_data_route"),
        ))
    elif route.requires_new_wetlab_omics and not route.new_wetlab_omics_available:
        dimensions.append(_assessment(
            FeasibilityDimension.LAB,
            FeasibilityGrade.FAIL,
            "route requires new wet-lab omics that are unavailable",
            repairs=(
                "remove:unavailable_wetlab_omics_requirement",
                "consider:public_omics_reanalysis",
                "consider:hybrid_nonmolecular_plus_public_omics",
            ),
        ))
    else:
        dimensions.append(_assessment(FeasibilityDimension.LAB, FeasibilityGrade.PASS))

    dimensions.append(_public_data_assessment(route))

    if not route.compute_worker_available or not route.required_runtime_available:
        missing = []
        if not route.compute_worker_available:
            missing.append("authoritative compute worker unavailable")
        if not route.required_runtime_available:
            missing.append("required analysis runtime/toolchain unavailable")
        dimensions.append(_assessment(
            FeasibilityDimension.COMPUTATIONAL,
            FeasibilityGrade.FAIL,
            "; ".join(missing),
            repairs=("provision:authoritative_compute_or_runtime",),
        ))
    else:
        dimensions.append(_assessment(FeasibilityDimension.COMPUTATIONAL, FeasibilityGrade.PASS))

    statistical_reasons = []
    if not route.primary_outcome_measurable:
        statistical_reasons.append("primary outcome is not measurably operationalized")
    if not route.statistically_identifiable:
        statistical_reasons.append("target estimand/question is not statistically identifiable")
    if route.confirmatory_intent and not route.independent_replication_adequate:
        statistical_reasons.append("confirmatory route lacks adequate independent replication")
    if statistical_reasons:
        dimensions.append(_assessment(
            FeasibilityDimension.STATISTICAL,
            FeasibilityGrade.FAIL,
            *statistical_reasons,
            repairs=("redesign:estimand_replication_or_outcome",),
        ))
    elif not route.confirmatory_intent and not route.independent_replication_adequate:
        dimensions.append(_assessment(
            FeasibilityDimension.STATISTICAL,
            FeasibilityGrade.CONDITIONAL,
            "replication is inadequate for confirmatory inference; exploratory use only",
            repairs=("label:exploratory", "increase:independent_replication"),
        ))
    else:
        dimensions.append(_assessment(FeasibilityDimension.STATISTICAL, FeasibilityGrade.PASS))

    resource_reasons = []
    if not route.budget_feasible:
        resource_reasons.append("route exceeds the hard budget/resource limit")
    if not route.timeline_feasible:
        resource_reasons.append("route exceeds the available execution timeline")
    if resource_reasons:
        dimensions.append(_assessment(
            FeasibilityDimension.RESOURCES,
            FeasibilityGrade.FAIL,
            *resource_reasons,
            repairs=("evolve:scope_cost_or_timeline",),
        ))
    else:
        dimensions.append(_assessment(FeasibilityDimension.RESOURCES, FeasibilityGrade.PASS))

    if route.journal_scope_fit:
        dimensions.append(_assessment(FeasibilityDimension.JOURNAL, FeasibilityGrade.PASS))
    else:
        dimensions.append(_assessment(
            FeasibilityDimension.JOURNAL,
            FeasibilityGrade.CONDITIONAL,
            "current target-journal scope fit is inadequate",
            repairs=("evolve:target_journal_or_question_framing",),
        ))

    if route.provenance_traceable:
        dimensions.append(_assessment(FeasibilityDimension.PROVENANCE, FeasibilityGrade.PASS))
    else:
        dimensions.append(_assessment(
            FeasibilityDimension.PROVENANCE,
            FeasibilityGrade.FAIL,
            "route cannot preserve required data/method provenance",
            repairs=("repair:provenance_path",),
        ))

    if route.user_constraints_satisfied:
        dimensions.append(_assessment(FeasibilityDimension.USER_CONSTRAINTS, FeasibilityGrade.PASS))
    else:
        dimensions.append(_assessment(
            FeasibilityDimension.USER_CONSTRAINTS,
            FeasibilityGrade.FAIL,
            "route violates an explicit user/resource constraint",
            repairs=("evolve:route_to_user_constraints",),
        ))

    grades = {d.grade for d in dimensions}
    if FeasibilityGrade.FAIL in grades:
        overall = FeasibilityGrade.FAIL
    elif FeasibilityGrade.CONDITIONAL in grades:
        overall = FeasibilityGrade.CONDITIONAL
    else:
        overall = FeasibilityGrade.PASS

    repairs = tuple(dict.fromkeys(
        repair for dimension in dimensions for repair in dimension.repair_actions
    ))
    return RouteFeasibilityReport(
        route_id=route.route_id,
        mode=route.mode,
        overall=overall,
        dimensions=tuple(dimensions),
        repair_actions=repairs,
        advancement_allowed=overall is FeasibilityGrade.PASS,
    )


def feasibility_court(
    routes: Iterable[RouteProposal],
    *,
    blocker_gate: BlockerGate | None = None,
) -> FeasibilityCourtResult:
    routes = list(routes)
    if not routes:
        raise ValueError("at least one feasibility route is required")
    route_ids = [r.route_id for r in routes]
    if len(set(route_ids)) != len(route_ids):
        raise ValueError("route_id values must be unique")

    if blocker_gate is not None:
        blocker_gate.assert_can_advance(from_phase="novelty", to_phase="feasibility")

    reports = [evaluate_route(route) for route in routes]
    by_id = {route.route_id: route for route in routes}
    viable = [r for r in reports if r.overall is FeasibilityGrade.PASS]
    conditional = [r for r in reports if r.overall is FeasibilityGrade.CONDITIONAL]
    failed = [r for r in reports if r.overall is FeasibilityGrade.FAIL]

    if viable:
        selected = min(
            viable,
            key=lambda report: (
                -by_id[report.route_id].scientific_value,
                by_id[report.route_id].execution_risk,
                by_id[report.route_id].resource_burden,
                report.route_id,
            ),
        )
        status = CourtStatus.ADVANCE
        required_actions: tuple[str, ...] = ()
        selected_route_id = selected.route_id
    elif conditional:
        status = CourtStatus.REVISE
        selected_route_id = None
        required_actions = tuple(dict.fromkeys(
            action for report in conditional for action in report.repair_actions
        ))
    else:
        status = CourtStatus.BLOCKED
        selected_route_id = None
        required_actions = tuple(dict.fromkeys(
            action for report in failed for action in report.repair_actions
        ))

    return FeasibilityCourtResult(
        status=status,
        selected_route_id=selected_route_id,
        viable_route_ids=tuple(r.route_id for r in viable),
        conditional_route_ids=tuple(r.route_id for r in conditional),
        failed_route_ids=tuple(r.route_id for r in failed),
        reports=tuple(reports),
        required_actions=required_actions,
    )
