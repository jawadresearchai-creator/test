from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
import re

from .blockers import BlockerGate
from .data_fitness import DataUseRole
from .dataset_freeze import DatasetFreeze
from .design import DesignFreeze, InferenceIntent, OutcomeTier
from .state import ProjectState, Stage, StudyMode


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WILDCARD_VERSION_RE = re.compile(r"(^|[\s=<>~^])(?:latest|\*|x)(?:$|[\s.])", re.I)


class AnalysisSpecGrade(str, Enum):
    PASS = "pass"
    CONDITIONAL = "conditional"
    FAIL = "fail"


class AnalysisSpecStatus(str, Enum):
    ADVANCE = "advance"
    REVISE = "revise"
    BLOCKED = "blocked"


class MultiplicityMethod(str, Enum):
    NONE = "none"
    HOLM = "holm"
    BONFERRONI = "bonferroni"
    BH_FDR = "bh_fdr"
    HIERARCHICAL = "hierarchical"


@dataclass(frozen=True)
class PackagePin:
    name: str
    version: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("package name is required")
        if not self.version.strip():
            raise ValueError(f"{self.name}: package version is required")
        if _WILDCARD_VERSION_RE.search(self.version.strip()):
            raise ValueError(f"{self.name}: package version must be exact, not latest/wildcard")


@dataclass(frozen=True)
class RuntimeSpec:
    runtime_id: str
    language: str
    language_version: str
    packages: tuple[PackagePin, ...]

    def __post_init__(self) -> None:
        if not self.runtime_id.strip():
            raise ValueError("runtime_id is required")
        if not self.language.strip():
            raise ValueError(f"{self.runtime_id}: language is required")
        if not self.language_version.strip():
            raise ValueError(f"{self.runtime_id}: language version is required")
        if _WILDCARD_VERSION_RE.search(self.language_version.strip()):
            raise ValueError(f"{self.runtime_id}: language version must be exact")
        names = [p.name.casefold().strip() for p in self.packages]
        if len(set(names)) != len(names):
            raise ValueError(f"{self.runtime_id}: duplicate package pin")


@dataclass(frozen=True)
class AnalysisTask:
    task_id: str
    component: str
    target_name: str
    design_outcome: str | None
    confirmatory: bool
    estimand: str
    contrast: str
    model_family: str
    model_formula: str
    unit_of_analysis: str
    dependency_structure: str
    adjustment_terms: tuple[str, ...]
    transformation_rule: str
    missing_data_policy: str
    exclusion_policy: str
    multiplicity_family: str
    multiplicity_method: MultiplicityMethod
    alpha: float
    confidence_level: float
    effect_measure: str
    diagnostics: tuple[str, ...]
    fallback_rules: tuple[str, ...]
    runtime_id: str
    engine_package: str
    implementation_entrypoint: str
    execution_order: int
    public_data_role: DataUseRole | None = None
    planned_use_binding: str | None = None
    direct_validation_claim: bool = False
    data_dependent_method_selection: bool = False

    def __post_init__(self) -> None:
        required = {
            "task_id": self.task_id,
            "component": self.component,
            "target_name": self.target_name,
            "estimand": self.estimand,
            "contrast": self.contrast,
            "model_family": self.model_family,
            "model_formula": self.model_formula,
            "unit_of_analysis": self.unit_of_analysis,
            "dependency_structure": self.dependency_structure,
            "transformation_rule": self.transformation_rule,
            "missing_data_policy": self.missing_data_policy,
            "exclusion_policy": self.exclusion_policy,
            "multiplicity_family": self.multiplicity_family,
            "effect_measure": self.effect_measure,
            "runtime_id": self.runtime_id,
            "engine_package": self.engine_package,
            "implementation_entrypoint": self.implementation_entrypoint,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise ValueError("analysis task missing required field(s): " + ", ".join(missing))
        if self.execution_order < 1:
            raise ValueError(f"{self.task_id}: execution_order must be >= 1")
        if not 0.0 < float(self.alpha) <= 0.10:
            raise ValueError(f"{self.task_id}: alpha must be in (0, 0.10]")
        if not 0.80 <= float(self.confidence_level) < 1.0:
            raise ValueError(f"{self.task_id}: confidence_level must be in [0.80, 1.0)")


@dataclass(frozen=True)
class AnalysisSpecificationPlan:
    specification_id: str
    design_freeze_sha256: str
    dataset_freeze_sha256: str
    mode: StudyMode
    runtimes: tuple[RuntimeSpec, ...]
    tasks: tuple[AnalysisTask, ...]
    random_seed: int
    outcome_values_inspected_before_specification: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.specification_id.strip():
            raise ValueError("specification_id is required")
        if not _SHA256_RE.fullmatch(self.design_freeze_sha256):
            raise ValueError("design_freeze_sha256 must be a lowercase 64-character digest")
        if not _SHA256_RE.fullmatch(self.dataset_freeze_sha256):
            raise ValueError("dataset_freeze_sha256 must be a lowercase 64-character digest")
        if not self.runtimes:
            raise ValueError("at least one exact runtime specification is required")
        if not self.tasks:
            raise ValueError("at least one analysis task is required")
        runtime_ids = [r.runtime_id for r in self.runtimes]
        if len(set(runtime_ids)) != len(runtime_ids):
            raise ValueError("runtime IDs must be unique")
        task_ids = [t.task_id for t in self.tasks]
        if len(set(task_ids)) != len(task_ids):
            raise ValueError("analysis task IDs must be unique")
        order = [t.execution_order for t in self.tasks]
        if len(set(order)) != len(order):
            raise ValueError("analysis execution_order values must be unique")
        if sorted(order) != list(range(1, len(order) + 1)):
            raise ValueError("analysis execution_order must be contiguous from 1..N")
        if self.random_seed < 0:
            raise ValueError("random_seed must be >= 0")


@dataclass(frozen=True)
class AnalysisSpecIssue:
    code: str
    grade: AnalysisSpecGrade
    reason: str
    repair_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnalysisSpecCourtResult:
    status: AnalysisSpecStatus
    issues: tuple[AnalysisSpecIssue, ...]
    required_actions: tuple[str, ...]
    advancement_allowed: bool


@dataclass(frozen=True)
class FrozenAnalysisSpecification:
    specification_id: str
    design_freeze_sha256: str
    dataset_freeze_sha256: str
    specification_payload: dict
    specification_sha256: str
    pre_outcome: bool
    analysis_specification_locked: bool = False
    analysis_model_locked: bool = False


@dataclass(frozen=True)
class AnalysisLock:
    specification_id: str
    design_freeze_sha256: str
    dataset_freeze_sha256: str
    specification_sha256: str
    lock_payload: dict
    analysis_lock_sha256: str
    pre_outcome: bool
    analysis_specification_locked: bool = True
    analysis_model_locked: bool = True


def _issue(code: str, grade: AnalysisSpecGrade, reason: str, *repairs: str) -> AnalysisSpecIssue:
    return AnalysisSpecIssue(code, grade, reason, tuple(repairs))


def _canonicalize(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _canonicalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(v) for v in value]
    return value


def _design_outcomes(design_freeze: DesignFreeze) -> dict[str, str]:
    return {
        str(row.get("name", "")).strip(): str(row.get("tier", "")).strip()
        for row in design_freeze.design_payload.get("outcomes", [])
        if str(row.get("name", "")).strip()
    }


def _public_designs(design_freeze: DesignFreeze) -> dict[str, dict]:
    return {
        str(row.get("dataset_id", "")).strip(): row
        for row in design_freeze.design_payload.get("public_datasets", [])
        if str(row.get("dataset_id", "")).strip()
    }


def _runtime_packages(runtime: RuntimeSpec) -> set[str]:
    return {p.name.casefold().strip() for p in runtime.packages}


def analysis_specification_court(
    plan: AnalysisSpecificationPlan,
    design_freeze: DesignFreeze,
    dataset_freeze: DatasetFreeze,
    *,
    blocker_gate: BlockerGate | None = None,
) -> AnalysisSpecCourtResult:
    """Adversarial pre-outcome statistical prespecification court.

    The court validates the statistical plan against frozen design and frozen data
    identity. It does not inspect outcomes and does not execute models.
    """
    if blocker_gate is not None:
        blocker_gate.assert_can_advance(from_phase="dataset_frozen", to_phase="analysis_specification")

    issues: list[AnalysisSpecIssue] = []

    if plan.design_freeze_sha256 != design_freeze.design_freeze_sha256:
        issues.append(_issue(
            "design_freeze_binding_mismatch", AnalysisSpecGrade.FAIL,
            "analysis specification is not bound to the supplied Design Freeze",
            "rebuild:analysis_specification_from_exact_design_freeze",
        ))
    if plan.dataset_freeze_sha256 != dataset_freeze.dataset_freeze_sha256:
        issues.append(_issue(
            "dataset_freeze_binding_mismatch", AnalysisSpecGrade.FAIL,
            "analysis specification is not bound to the supplied Dataset Freeze",
            "rebuild:analysis_specification_from_exact_dataset_freeze",
        ))

    design_mode = str(design_freeze.design_payload.get("mode", ""))
    dataset_mode = str(dataset_freeze.freeze_payload.get("mode", ""))
    if plan.mode.value != design_mode or plan.mode.value != dataset_mode:
        issues.append(_issue(
            "route_mode_mismatch", AnalysisSpecGrade.FAIL,
            "analysis specification route must match both Design Freeze and Dataset Freeze",
            "repair:route_binding",
        ))

    confirmatory_design = bool(design_freeze.design_payload.get("confirmatory", False))
    if confirmatory_design and not dataset_freeze.confirmatory_outcome_blind:
        issues.append(_issue(
            "dataset_freeze_not_outcome_blind", AnalysisSpecGrade.FAIL,
            "confirmatory analysis specification requires an outcome-blind Dataset Freeze",
            "reclassify:exploratory", "restart:independent_confirmatory_dataset",
        ))
    if confirmatory_design and plan.outcome_values_inspected_before_specification:
        issues.append(_issue(
            "pre_specification_outcome_access", AnalysisSpecGrade.FAIL,
            "confirmatory outcome values were inspected before Analysis Specification",
            "reclassify:exploratory", "restart:independent_confirmatory_analysis",
        ))

    runtimes = {r.runtime_id: r for r in plan.runtimes}
    for task in plan.tasks:
        runtime = runtimes.get(task.runtime_id)
        if runtime is None:
            issues.append(_issue(
                f"task:{task.task_id}:runtime_unknown", AnalysisSpecGrade.FAIL,
                "analysis task references a runtime that is not frozen in the specification",
                "pin:runtime",
            ))
        elif task.engine_package.casefold().strip() not in _runtime_packages(runtime):
            issues.append(_issue(
                f"task:{task.task_id}:engine_package_unpinned", AnalysisSpecGrade.FAIL,
                "analysis engine package is not pinned in the referenced runtime",
                "pin:engine_package_version",
            ))

        if task.data_dependent_method_selection:
            issues.append(_issue(
                f"task:{task.task_id}:data_dependent_method_selection", AnalysisSpecGrade.FAIL,
                "confirmatory method/model/transformation selection cannot depend on observed outcome performance",
                "prespecify:method_selection", "reclassify:data_driven_analysis_as_exploratory",
            ))
        if task.confirmatory and not task.diagnostics:
            issues.append(_issue(
                f"task:{task.task_id}:diagnostics_missing", AnalysisSpecGrade.FAIL,
                "confirmatory task requires prespecified model diagnostics",
                "specify:diagnostics",
            ))
        if task.confirmatory and not task.fallback_rules:
            issues.append(_issue(
                f"task:{task.task_id}:fallback_rules_missing", AnalysisSpecGrade.FAIL,
                "confirmatory task requires prespecified diagnostic-triggered fallback rules, including an explicit no-fallback rule if appropriate",
                "specify:fallback_rules",
            ))
        if task.exclusion_policy.strip().casefold() != "dataset_freeze_only":
            issues.append(_issue(
                f"task:{task.task_id}:exclusion_policy_changed", AnalysisSpecGrade.FAIL,
                "Analysis Specification cannot invent or alter exclusions after Dataset Freeze",
                "use:dataset_freeze_only_exclusions",
            ))

    outcomes = _design_outcomes(design_freeze)
    public = _public_designs(design_freeze)
    physical = design_freeze.design_payload.get("physical") or {}
    has_physical = bool(physical)

    for task in plan.tasks:
        if task.component == "physical":
            if not has_physical:
                issues.append(_issue(
                    f"task:{task.task_id}:physical_component_undeclared", AnalysisSpecGrade.FAIL,
                    "analysis task references a physical component absent from Design Freeze",
                    "remove:undeclared_component", "return:design_if_material_change",
                ))
                continue
            if not (task.design_outcome or "").strip() or task.design_outcome not in outcomes:
                issues.append(_issue(
                    f"task:{task.task_id}:design_outcome_unknown", AnalysisSpecGrade.FAIL,
                    "physical analysis task must bind to a Design-Freeze outcome",
                    "bind:design_outcome",
                ))
            expected_unit = str(physical.get("experimental_unit", "")).strip().casefold()
            if task.unit_of_analysis.strip().casefold() != expected_unit:
                issues.append(_issue(
                    f"task:{task.task_id}:analysis_unit_mismatch", AnalysisSpecGrade.FAIL,
                    "physical analysis unit must match the independently assigned experimental unit",
                    "repair:analysis_unit", "prevent:pseudoreplication",
                ))
            required_blocks = {str(x).strip().casefold() for x in physical.get("blocking_factors", []) if str(x).strip()}
            present_adjustments = {str(x).strip().casefold() for x in task.adjustment_terms}
            missing_blocks = sorted(required_blocks - present_adjustments)
            if missing_blocks:
                issues.append(_issue(
                    f"task:{task.task_id}:blocking_term_missing", AnalysisSpecGrade.FAIL,
                    "analysis omits Design-Freeze blocking factor(s): " + ", ".join(missing_blocks),
                    "include:blocking_terms",
                ))
            if bool(physical.get("repeated_measures", False)):
                dep = task.dependency_structure.strip().casefold()
                if dep in {"independent", "independent observations", "none", "na", "n/a"}:
                    issues.append(_issue(
                        f"task:{task.task_id}:repeated_measure_dependency_missing", AnalysisSpecGrade.FAIL,
                        "repeated-measures design requires within-unit dependence in the analysis specification",
                        "specify:repeated_measure_dependency",
                    ))
        else:
            source = public.get(task.component)
            if source is None:
                issues.append(_issue(
                    f"task:{task.task_id}:public_component_undeclared", AnalysisSpecGrade.FAIL,
                    "analysis task references a public dataset absent from Design Freeze",
                    "remove:undeclared_component", "return:design_if_material_change",
                ))
                continue
            expected_role = str(source.get("role", ""))
            observed_role = task.public_data_role.value if task.public_data_role is not None else ""
            if observed_role != expected_role:
                issues.append(_issue(
                    f"task:{task.task_id}:public_role_mismatch", AnalysisSpecGrade.FAIL,
                    "public-data analysis role must exactly preserve the Design-Freeze role",
                    "repair:public_data_role",
                ))
            planned_use = str(source.get("planned_use_or_contrast", "")).strip()
            if (task.planned_use_binding or "").strip() != planned_use:
                issues.append(_issue(
                    f"task:{task.task_id}:public_planned_use_mismatch", AnalysisSpecGrade.FAIL,
                    "public-data task is not bound to the Design-Freeze planned use/contrast",
                    "repair:planned_use_binding",
                ))
            if expected_role in {
                DataUseRole.MECHANISTIC_SUPPORT.value,
                DataUseRole.CONTEXTUAL.value,
                DataUseRole.HYPOTHESIS_GENERATION.value,
            } and task.direct_validation_claim:
                issues.append(_issue(
                    f"task:{task.task_id}:public_causal_overreach", AnalysisSpecGrade.FAIL,
                    "supporting/contextual public data cannot be specified as direct validation of experimental units it did not measure",
                    "calibrate:claim_role",
                ))

    primary_names = {name for name, tier in outcomes.items() if tier == OutcomeTier.PRIMARY.value}
    confirmatory_primary_tasks = [
        task for task in plan.tasks
        if task.confirmatory and task.design_outcome in primary_names
    ]
    if confirmatory_design:
        covered = {task.design_outcome for task in confirmatory_primary_tasks}
        missing_primary = sorted(primary_names - covered)
        if missing_primary:
            issues.append(_issue(
                "primary_outcome_analysis_missing", AnalysisSpecGrade.FAIL,
                "confirmatory primary outcome(s) lack a prespecified analysis task: " + ", ".join(missing_primary),
                "specify:primary_outcome_analysis",
            ))
        duplicates = sorted({name for name in covered if sum(t.design_outcome == name for t in confirmatory_primary_tasks) > 1})
        if duplicates:
            issues.append(_issue(
                "multiple_confirmatory_primary_models", AnalysisSpecGrade.CONDITIONAL,
                "multiple confirmatory models are declared for the same primary outcome without an explicit hierarchical interpretation: " + ", ".join(duplicates),
                "select:single_primary_model", "specify:hierarchical_primary_models",
            ))

    families: dict[str, list[AnalysisTask]] = {}
    for task in plan.tasks:
        if task.confirmatory:
            families.setdefault(task.multiplicity_family.strip().casefold(), []).append(task)
    for family, tasks in families.items():
        if len(tasks) > 1 and any(t.multiplicity_method is MultiplicityMethod.NONE for t in tasks):
            issues.append(_issue(
                f"multiplicity:{family}:uncontrolled", AnalysisSpecGrade.FAIL,
                "confirmatory multiplicity family contains multiple tests but at least one task specifies no multiplicity control",
                "specify:multiplicity_control",
            ))
        methods = {t.multiplicity_method for t in tasks}
        if len(tasks) > 1 and len(methods) > 1:
            issues.append(_issue(
                f"multiplicity:{family}:method_inconsistent", AnalysisSpecGrade.FAIL,
                "tasks in one confirmatory multiplicity family use inconsistent correction methods",
                "harmonize:multiplicity_method",
            ))

    inference_intent = str(design_freeze.design_payload.get("inference_intent", ""))
    if inference_intent == InferenceIntent.CAUSAL.value:
        causal_physical_tasks = [t for t in plan.tasks if t.component == "physical" and t.confirmatory]
        for task in causal_physical_tasks:
            if not task.contrast.strip():
                issues.append(_issue(
                    f"task:{task.task_id}:causal_contrast_missing", AnalysisSpecGrade.FAIL,
                    "causal confirmatory analysis requires an explicit treatment-versus-control contrast",
                    "specify:causal_contrast",
                ))

    grades = {i.grade for i in issues}
    status = (
        AnalysisSpecStatus.BLOCKED if AnalysisSpecGrade.FAIL in grades
        else AnalysisSpecStatus.REVISE if AnalysisSpecGrade.CONDITIONAL in grades
        else AnalysisSpecStatus.ADVANCE
    )
    actions = tuple(dict.fromkeys(action for issue in issues for action in issue.repair_actions))
    return AnalysisSpecCourtResult(status, tuple(issues), actions, status is AnalysisSpecStatus.ADVANCE)


def build_analysis_specification(
    plan: AnalysisSpecificationPlan,
    design_freeze: DesignFreeze,
    dataset_freeze: DatasetFreeze,
    court_result: AnalysisSpecCourtResult,
) -> FrozenAnalysisSpecification:
    if not court_result.advancement_allowed:
        raise ValueError("Analysis Specification requires an ADVANCE court verdict")
    if plan.design_freeze_sha256 != design_freeze.design_freeze_sha256:
        raise ValueError("Analysis Specification Design Freeze binding mismatch")
    if plan.dataset_freeze_sha256 != dataset_freeze.dataset_freeze_sha256:
        raise ValueError("Analysis Specification Dataset Freeze binding mismatch")
    payload = _canonicalize(asdict(plan))
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    digest = sha256(raw).hexdigest()
    return FrozenAnalysisSpecification(
        specification_id=plan.specification_id,
        design_freeze_sha256=design_freeze.design_freeze_sha256,
        dataset_freeze_sha256=dataset_freeze.dataset_freeze_sha256,
        specification_payload=payload,
        specification_sha256=digest,
        pre_outcome=not plan.outcome_values_inspected_before_specification,
        analysis_specification_locked=False,
        analysis_model_locked=False,
    )


def enter_project_analysis_specification(
    state: ProjectState,
    frozen_specification: FrozenAnalysisSpecification,
    *,
    blocker_gate: BlockerGate | None = None,
) -> None:
    if blocker_gate is not None:
        blocker_gate.assert_can_advance(from_phase="dataset_frozen", to_phase="analysis_specification")
    if state.stage is not Stage.DATASET_FROZEN:
        raise ValueError(f"Analysis Specification requires project stage=dataset_frozen, observed {state.stage.value}")
    state.transition(Stage.ANALYSIS_SPECIFICATION, f"Analysis Specification {frozen_specification.specification_sha256}")


def build_analysis_lock(frozen_specification: FrozenAnalysisSpecification) -> AnalysisLock:
    if not frozen_specification.pre_outcome:
        raise ValueError("Analysis Lock cannot be created from post-outcome specification")
    payload = {
        "specification_id": frozen_specification.specification_id,
        "design_freeze_sha256": frozen_specification.design_freeze_sha256,
        "dataset_freeze_sha256": frozen_specification.dataset_freeze_sha256,
        "specification_sha256": frozen_specification.specification_sha256,
        "specification_payload": frozen_specification.specification_payload,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    digest = sha256(raw).hexdigest()
    return AnalysisLock(
        specification_id=frozen_specification.specification_id,
        design_freeze_sha256=frozen_specification.design_freeze_sha256,
        dataset_freeze_sha256=frozen_specification.dataset_freeze_sha256,
        specification_sha256=frozen_specification.specification_sha256,
        lock_payload=payload,
        analysis_lock_sha256=digest,
        pre_outcome=True,
        analysis_specification_locked=True,
        analysis_model_locked=True,
    )


def lock_project_analysis(
    state: ProjectState,
    frozen_specification: FrozenAnalysisSpecification,
    *,
    blocker_gate: BlockerGate | None = None,
) -> AnalysisLock:
    if blocker_gate is not None:
        blocker_gate.assert_can_advance(from_phase="analysis_specification", to_phase="analysis_locked")
    if state.stage is not Stage.ANALYSIS_SPECIFICATION:
        raise ValueError(f"Analysis Lock requires project stage=analysis_specification, observed {state.stage.value}")
    lock = build_analysis_lock(frozen_specification)
    state.transition(Stage.ANALYSIS_LOCKED, f"Analysis Lock {lock.analysis_lock_sha256}")
    return lock
