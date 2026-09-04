from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
import re

from .blockers import BlockerGate
from .design import DesignFreeze
from .state import ProjectState, Stage, StudyMode


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class DataOrigin(str, Enum):
    PROJECT_GENERATED = "project_generated"
    PUBLIC_REUSED = "public_reused"


class AssetRole(str, Enum):
    DATA = "data"
    METADATA = "metadata"
    QC = "qc"
    COVARIATE = "covariate"


class DatasetFreezeGrade(str, Enum):
    PASS = "pass"
    CONDITIONAL = "conditional"
    FAIL = "fail"


class DatasetFreezeStatus(str, Enum):
    ADVANCE = "advance"
    REVISE = "revise"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class FrozenDataAsset:
    asset_id: str
    origin: DataOrigin
    role: AssetRole
    sha256: str
    bytes: int
    locator: str
    representation: str
    source_dataset_id: str | None = None
    source_version: str | None = None
    schema_fields: tuple[str, ...] = ()
    sample_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.asset_id.strip():
            raise ValueError("asset_id is required")
        if not _SHA256_RE.fullmatch(self.sha256):
            raise ValueError(f"{self.asset_id}: sha256 must be a lowercase 64-character digest")
        if self.bytes < 1:
            raise ValueError(f"{self.asset_id}: bytes must be >= 1")
        if not self.locator.strip():
            raise ValueError(f"{self.asset_id}: stable locator is required")
        if not self.representation.strip():
            raise ValueError(f"{self.asset_id}: representation is required")
        if len(set(self.schema_fields)) != len(self.schema_fields):
            raise ValueError(f"{self.asset_id}: duplicate schema fields")
        if len(set(self.sample_ids)) != len(self.sample_ids):
            raise ValueError(f"{self.asset_id}: duplicate sample IDs")
        if self.origin is DataOrigin.PUBLIC_REUSED and not (self.source_dataset_id or "").strip():
            raise ValueError(f"{self.asset_id}: public asset requires source_dataset_id")


@dataclass(frozen=True)
class ExclusionRecord:
    unit_id: str
    criterion: str

    def __post_init__(self) -> None:
        if not self.unit_id.strip():
            raise ValueError("excluded unit_id is required")
        if not self.criterion.strip():
            raise ValueError(f"{self.unit_id}: exclusion criterion is required")


@dataclass(frozen=True)
class DatasetFreezePlan:
    freeze_id: str
    design_freeze_sha256: str
    mode: StudyMode
    assets: tuple[FrozenDataAsset, ...]
    retained_independent_unit_ids: tuple[str, ...] = ()
    exclusions: tuple[ExclusionRecord, ...] = ()
    outcome_values_inspected_before_freeze: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.freeze_id.strip():
            raise ValueError("freeze_id is required")
        if not _SHA256_RE.fullmatch(self.design_freeze_sha256):
            raise ValueError("design_freeze_sha256 must be a lowercase 64-character digest")
        if not self.assets:
            raise ValueError("at least one frozen data asset is required")
        asset_ids = [a.asset_id for a in self.assets]
        if len(set(asset_ids)) != len(asset_ids):
            raise ValueError("asset IDs must be unique")
        if len(set(self.retained_independent_unit_ids)) != len(self.retained_independent_unit_ids):
            raise ValueError("retained independent-unit IDs must be unique")
        excluded = [e.unit_id for e in self.exclusions]
        if len(set(excluded)) != len(excluded):
            raise ValueError("excluded unit IDs must be unique")
        if set(excluded) & set(self.retained_independent_unit_ids):
            raise ValueError("an independent unit cannot be both retained and excluded")


@dataclass(frozen=True)
class DatasetFreezeIssue:
    code: str
    grade: DatasetFreezeGrade
    reason: str
    repair_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class DatasetFreezeCourtResult:
    status: DatasetFreezeStatus
    issues: tuple[DatasetFreezeIssue, ...]
    required_actions: tuple[str, ...]
    advancement_allowed: bool


@dataclass(frozen=True)
class DatasetFreeze:
    freeze_id: str
    design_freeze_sha256: str
    freeze_payload: dict
    dataset_freeze_sha256: str
    confirmatory_outcome_blind: bool
    analysis_specification_locked: bool = False
    analysis_model_locked: bool = False


def _issue(code: str, grade: DatasetFreezeGrade, reason: str, *repairs: str) -> DatasetFreezeIssue:
    return DatasetFreezeIssue(code, grade, reason, tuple(repairs))


def _design_mode(design_freeze: DesignFreeze) -> str:
    return str(design_freeze.design_payload.get("mode", ""))


def _design_confirmatory(design_freeze: DesignFreeze) -> bool:
    return bool(design_freeze.design_payload.get("confirmatory", False))


def _public_dataset_ids(design_freeze: DesignFreeze) -> set[str]:
    return {
        str(row.get("dataset_id", "")).strip()
        for row in design_freeze.design_payload.get("public_datasets", [])
        if str(row.get("dataset_id", "")).strip()
    }


def _required_project_fields(design_freeze: DesignFreeze) -> set[str]:
    payload = design_freeze.design_payload
    required = {
        str(row.get("name", "")).strip()
        for row in payload.get("outcomes", [])
        if str(row.get("name", "")).strip()
    }
    required.update(str(x).strip() for x in payload.get("covariates", []) if str(x).strip())
    required.update(str(x).strip() for x in payload.get("metadata_fields", []) if str(x).strip())
    physical = payload.get("physical") or {}
    required.update(str(x).strip() for x in physical.get("blocking_factors", []) if str(x).strip())
    return required


def dataset_freeze_court(
    plan: DatasetFreezePlan,
    design_freeze: DesignFreeze,
    *,
    blocker_gate: BlockerGate | None = None,
) -> DatasetFreezeCourtResult:
    """Validate exact acquired/reused data identity before outcome analysis.

    This court freezes bytes, schema/sample identity and prespecified attrition. It
    deliberately does not select statistical models, software, multiplicity policy,
    transformations or execution order; those belong to Analysis Specification/Lock.
    """
    if blocker_gate is not None:
        blocker_gate.assert_can_advance(from_phase="design_frozen", to_phase="dataset_freeze")

    issues: list[DatasetFreezeIssue] = []

    if plan.design_freeze_sha256 != design_freeze.design_freeze_sha256:
        issues.append(_issue(
            "design_freeze_binding_mismatch",
            DatasetFreezeGrade.FAIL,
            "dataset freeze plan is not bound to the supplied Design Freeze",
            "rebuild:dataset_freeze_from_exact_design_freeze",
        ))

    if plan.mode.value != _design_mode(design_freeze):
        issues.append(_issue(
            "route_mode_mismatch",
            DatasetFreezeGrade.FAIL,
            "dataset freeze route does not match the frozen study design",
            "repair:route_binding",
        ))

    if _design_confirmatory(design_freeze) and plan.outcome_values_inspected_before_freeze:
        issues.append(_issue(
            "pre_freeze_outcome_access",
            DatasetFreezeGrade.FAIL,
            "confirmatory outcome values were inspected before Dataset Freeze",
            "reclassify:exploratory",
            "restart:independent_confirmatory_dataset",
        ))

    if _design_confirmatory(design_freeze) and not design_freeze.pre_outcome:
        issues.append(_issue(
            "design_not_pre_outcome",
            DatasetFreezeGrade.FAIL,
            "confirmatory Dataset Freeze cannot be based on a Design Freeze created after outcome access",
            "reclassify:exploratory",
            "restart:confirmatory_design",
        ))

    physical_mode = plan.mode in {StudyMode.PHYSICAL, StudyMode.HYBRID}
    public_mode = plan.mode in {StudyMode.PUBLIC_DATA, StudyMode.HYBRID}

    project_data = [a for a in plan.assets if a.origin is DataOrigin.PROJECT_GENERATED and a.role is AssetRole.DATA]
    public_assets = [a for a in plan.assets if a.origin is DataOrigin.PUBLIC_REUSED]

    if physical_mode and not project_data:
        issues.append(_issue(
            "project_generated_data_missing",
            DatasetFreezeGrade.FAIL,
            "physical/hybrid route has no frozen project-generated data asset",
            "acquire_and_freeze:project_generated_data",
        ))
    if not physical_mode and project_data:
        issues.append(_issue(
            "unexpected_project_generated_data",
            DatasetFreezeGrade.FAIL,
            "public-data-only route contains undeclared project-generated outcome data",
            "return:design",
            "remove:undeclared_project_data",
        ))

    declared_public = _public_dataset_ids(design_freeze)
    observed_public = {str(a.source_dataset_id) for a in public_assets if a.source_dataset_id}
    if public_mode:
        missing = sorted(declared_public - observed_public)
        if missing:
            issues.append(_issue(
                "declared_public_dataset_missing",
                DatasetFreezeGrade.FAIL,
                "route-required public dataset(s) are absent from Dataset Freeze: " + ", ".join(missing),
                "acquire_and_freeze:declared_public_dataset",
            ))
        undeclared = sorted(observed_public - declared_public)
        if undeclared:
            issues.append(_issue(
                "undeclared_public_dataset",
                DatasetFreezeGrade.FAIL,
                "Dataset Freeze contains public dataset(s) not present in Design Freeze: " + ", ".join(undeclared),
                "return:design_for_material_change",
            ))
    elif public_assets:
        issues.append(_issue(
            "unexpected_public_dataset",
            DatasetFreezeGrade.FAIL,
            "physical-only route contains undeclared public-data assets",
            "return:design_for_material_change",
        ))

    for asset in public_assets:
        if not (asset.source_version or "").strip():
            issues.append(_issue(
                f"public:{asset.asset_id}:source_version_missing",
                DatasetFreezeGrade.FAIL,
                "public/reused asset requires a version/release/accession snapshot identity",
                "resolve:source_version",
            ))

    if physical_mode:
        physical = design_freeze.design_payload.get("physical") or {}
        planned_units = int(physical.get("independent_units_total", 0) or 0)
        retained = set(plan.retained_independent_unit_ids)
        excluded = {e.unit_id for e in plan.exclusions}
        if not retained:
            issues.append(_issue(
                "independent_unit_manifest_missing",
                DatasetFreezeGrade.FAIL,
                "physical/hybrid Dataset Freeze requires retained independent-unit identities",
                "freeze:independent_unit_manifest",
            ))
        if planned_units and len(retained | excluded) != planned_units:
            issues.append(_issue(
                "independent_unit_accounting_mismatch",
                DatasetFreezeGrade.FAIL,
                f"frozen retained+excluded unit count does not equal frozen design count ({len(retained | excluded)} vs {planned_units})",
                "reconcile:unit_accounting",
                "return:design_if_material_change",
            ))
        prespecified = set(design_freeze.design_payload.get("exclusion_criteria", []))
        invalid = sorted({e.criterion for e in plan.exclusions if e.criterion not in prespecified})
        if invalid:
            issues.append(_issue(
                "posthoc_exclusion_criterion",
                DatasetFreezeGrade.FAIL,
                "exclusion ledger uses criterion not prespecified in Design Freeze: " + "; ".join(invalid),
                "retain:unit",
                "reclassify:exploratory_if_posthoc_exclusion_required",
            ))

        observed_fields: set[str] = set()
        for asset in plan.assets:
            if asset.origin is DataOrigin.PROJECT_GENERATED:
                observed_fields.update(asset.schema_fields)
        missing_fields = sorted(_required_project_fields(design_freeze) - observed_fields)
        if missing_fields:
            issues.append(_issue(
                "design_field_missing_from_frozen_schema",
                DatasetFreezeGrade.FAIL,
                "frozen project schema is missing prespecified design field(s): " + ", ".join(missing_fields),
                "repair:data_acquisition_or_schema",
                "return:design_if_field_was_not_acquired",
            ))

    grades = {i.grade for i in issues}
    status = (
        DatasetFreezeStatus.BLOCKED if DatasetFreezeGrade.FAIL in grades
        else DatasetFreezeStatus.REVISE if DatasetFreezeGrade.CONDITIONAL in grades
        else DatasetFreezeStatus.ADVANCE
    )
    actions = tuple(dict.fromkeys(action for issue in issues for action in issue.repair_actions))
    return DatasetFreezeCourtResult(
        status=status,
        issues=tuple(issues),
        required_actions=actions,
        advancement_allowed=status is DatasetFreezeStatus.ADVANCE,
    )


def _canonicalize(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _canonicalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(v) for v in value]
    return value


def build_dataset_freeze(
    plan: DatasetFreezePlan,
    design_freeze: DesignFreeze,
    court_result: DatasetFreezeCourtResult,
) -> DatasetFreeze:
    if not court_result.advancement_allowed:
        raise ValueError("Dataset Freeze requires an ADVANCE dataset-freeze-court verdict")
    if plan.design_freeze_sha256 != design_freeze.design_freeze_sha256:
        raise ValueError("Dataset Freeze design binding mismatch")

    payload = _canonicalize(asdict(plan))
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    digest = sha256(raw).hexdigest()
    return DatasetFreeze(
        freeze_id=plan.freeze_id,
        design_freeze_sha256=design_freeze.design_freeze_sha256,
        freeze_payload=payload,
        dataset_freeze_sha256=digest,
        confirmatory_outcome_blind=not plan.outcome_values_inspected_before_freeze,
        analysis_specification_locked=False,
        analysis_model_locked=False,
    )


def freeze_project_dataset(
    state: ProjectState,
    plan: DatasetFreezePlan,
    design_freeze: DesignFreeze,
    court_result: DatasetFreezeCourtResult,
    *,
    blocker_gate: BlockerGate | None = None,
) -> DatasetFreeze:
    if blocker_gate is not None:
        blocker_gate.assert_can_advance(from_phase="dataset_freeze", to_phase="dataset_frozen")
    if state.stage is not Stage.DESIGN_FROZEN:
        raise ValueError(f"Dataset Freeze requires project stage=design_frozen, observed {state.stage.value}")
    freeze = build_dataset_freeze(plan, design_freeze, court_result)
    state.transition(Stage.DATASET_FROZEN, f"Dataset Freeze {freeze.dataset_freeze_sha256}")
    return freeze
