from dataclasses import replace

import pytest

from agri_coscientist.blockers import Blocker, BlockerClass, BlockerGate, PhaseBlockedError
from agri_coscientist.data_fitness import DataFitnessGrade, DataUseRole
from agri_coscientist.dataset_freeze import (
    AssetRole,
    DataOrigin,
    DatasetFreezeStatus,
    DatasetFreezePlan,
    ExclusionRecord,
    FrozenDataAsset,
    build_dataset_freeze,
    dataset_freeze_court,
    freeze_project_dataset,
)
from agri_coscientist.design import (
    AllocationMethod,
    InferenceIntent,
    OutcomeSpec,
    OutcomeTier,
    PhysicalDesign,
    PublicDatasetDesign,
    StudyDesign,
    build_design_freeze,
    design_court,
)
from agri_coscientist.state import ProjectState, Stage, StudyMode


def physical_design():
    return PhysicalDesign(
        experimental_unit="one independently grown wheat pot",
        analysis_unit_matches_experimental_unit=True,
        independent_units_total=4,
        independent_units_per_group=(2, 2),
        replication_rationale="independent pots estimate biological variation",
        precision_or_power_plan="freeze final n before acquisition from precision planning",
        treatments=("cue",),
        controls=("mock",),
        manipulated_exposure=True,
        allocation_method=AllocationMethod.BLOCK_RANDOMIZED,
        randomization_plan="seeded allocation within bench blocks",
        nuisance_gradient_expected=True,
        blocking_factors=("bench_position",),
        blocking_plan="predefine bench blocks before randomized allocation",
        subsamples_per_unit=1,
        subsamples_treated_as_technical=True,
        repeated_measures=False,
        repeated_measure_unit_id_preserved=True,
        destructive_sampling=False,
        independent_units_per_destructive_timepoint=True,
        sampling_schedule=("post-challenge",),
        required_methods=("root phenotyping",),
        unavailable_methods=("qPCR", "RNA-seq"),
        blinding_feasible=True,
        blinded_outcome_assessment=True,
        blinding_plan="coded samples",
    )


def public_design(dataset_id="PUB1"):
    return PublicDatasetDesign(
        dataset_id=dataset_id,
        role=DataUseRole.MECHANISTIC_SUPPORT,
        layered_data_fitness=DataFitnessGrade.PASS,
        source_design_understood=True,
        source_experimental_or_sampling_unit="independent root sample",
        sample_independence_known=True,
        planned_use_or_contrast="mechanistic context only",
        supports_causal_identification=False,
    )


def study(mode=StudyMode.HYBRID):
    physical = physical_design() if mode in {StudyMode.PHYSICAL, StudyMode.HYBRID} else None
    public = (public_design(),) if mode in {StudyMode.PUBLIC_DATA, StudyMode.HYBRID} else ()
    return StudyDesign(
        design_id=f"design-{mode.value}",
        question="Does the randomized cue alter the primary injury outcome?",
        hypotheses=("cue changes primary injury",),
        mode=mode,
        inference_intent=InferenceIntent.CAUSAL if physical else InferenceIntent.ASSOCIATIONAL,
        confirmatory=True,
        outcomes=(
            OutcomeSpec("primary injury", OutcomeTier.PRIMARY, "assay", "post-challenge"),
            OutcomeSpec("root length", OutcomeTier.SECONDARY, "image", "post-challenge"),
        ),
        covariates=("initial size",),
        metadata_fields=("unit_id", "block_id", "treatment_code"),
        exclusion_criteria=("catastrophic unit loss before treatment",),
        quality_controls=("coded outcome QC",),
        physical=physical,
        public_datasets=public,
    )


def design_freeze(mode=StudyMode.HYBRID):
    d = study(mode)
    return build_design_freeze(d, design_court(d))


def asset(asset_id, origin, role=AssetRole.DATA, **overrides):
    values = dict(
        asset_id=asset_id,
        origin=origin,
        role=role,
        sha256=("a" if origin is DataOrigin.PROJECT_GENERATED else "b") * 64,
        bytes=1234,
        locator=f"frozen://{asset_id}",
        representation="csv" if origin is DataOrigin.PROJECT_GENERATED else "featurecounts_integer_counts",
        source_dataset_id=None if origin is DataOrigin.PROJECT_GENERATED else "PUB1",
        source_version=None if origin is DataOrigin.PROJECT_GENERATED else "release-1",
        schema_fields=(),
        sample_ids=(),
    )
    values.update(overrides)
    return FrozenDataAsset(**values)


def hybrid_plan(df=None, **overrides):
    df = df or design_freeze()
    project = asset(
        "physical-data",
        DataOrigin.PROJECT_GENERATED,
        schema_fields=("primary injury", "root length", "initial size", "unit_id", "block_id", "treatment_code", "bench_position"),
        sample_ids=("u1", "u2", "u3", "u4"),
    )
    public = asset("public-counts", DataOrigin.PUBLIC_REUSED, sample_ids=("s1", "s2", "s3", "s4"))
    values = dict(
        freeze_id="hybrid-freeze-v1",
        design_freeze_sha256=df.design_freeze_sha256,
        mode=StudyMode.HYBRID,
        assets=(project, public),
        retained_independent_unit_ids=("u1", "u2", "u3", "u4"),
        exclusions=(),
        outcome_values_inspected_before_freeze=False,
    )
    values.update(overrides)
    return DatasetFreezePlan(**values)


def codes(result):
    return {i.code for i in result.issues}


def test_valid_hybrid_dataset_freeze_advances_and_is_deterministic():
    df = design_freeze()
    plan = hybrid_plan(df)
    result = dataset_freeze_court(plan, df)
    assert result.status is DatasetFreezeStatus.ADVANCE
    first = build_dataset_freeze(plan, df, result)
    second = build_dataset_freeze(plan, df, result)
    assert first.dataset_freeze_sha256 == second.dataset_freeze_sha256
    assert first.confirmatory_outcome_blind is True
    assert first.analysis_specification_locked is False
    assert first.analysis_model_locked is False
    assert "analysis_model" not in first.freeze_payload


def test_design_freeze_binding_mismatch_blocks():
    df = design_freeze()
    plan = hybrid_plan(df, design_freeze_sha256="c" * 64)
    result = dataset_freeze_court(plan, df)
    assert result.status is DatasetFreezeStatus.BLOCKED
    assert "design_freeze_binding_mismatch" in codes(result)


def test_route_mode_mismatch_blocks():
    df = design_freeze()
    plan = hybrid_plan(df, mode=StudyMode.PHYSICAL)
    result = dataset_freeze_court(plan, df)
    assert "route_mode_mismatch" in codes(result)
    assert result.status is DatasetFreezeStatus.BLOCKED


def test_confirmatory_outcome_peeking_before_dataset_freeze_blocks():
    df = design_freeze()
    plan = hybrid_plan(df, outcome_values_inspected_before_freeze=True)
    result = dataset_freeze_court(plan, df)
    assert "pre_freeze_outcome_access" in codes(result)
    assert result.status is DatasetFreezeStatus.BLOCKED


def test_physical_or_hybrid_route_requires_project_generated_data():
    df = design_freeze()
    plan = hybrid_plan(df)
    plan = replace(plan, assets=tuple(a for a in plan.assets if a.origin is DataOrigin.PUBLIC_REUSED))
    result = dataset_freeze_court(plan, df)
    assert "project_generated_data_missing" in codes(result)


def test_all_design_declared_public_datasets_must_be_frozen():
    df = design_freeze()
    plan = hybrid_plan(df)
    plan = replace(plan, assets=tuple(a for a in plan.assets if a.origin is DataOrigin.PROJECT_GENERATED))
    result = dataset_freeze_court(plan, df)
    assert "declared_public_dataset_missing" in codes(result)
    assert result.status is DatasetFreezeStatus.BLOCKED


def test_undeclared_public_dataset_forces_return_to_design():
    df = design_freeze()
    plan = hybrid_plan(df)
    extra = asset("public-extra", DataOrigin.PUBLIC_REUSED, source_dataset_id="PUB2", source_version="v1")
    plan = replace(plan, assets=plan.assets + (extra,))
    result = dataset_freeze_court(plan, df)
    assert "undeclared_public_dataset" in codes(result)
    assert "return:design_for_material_change" in result.required_actions


def test_public_asset_requires_version_identity():
    df = design_freeze()
    plan = hybrid_plan(df)
    public = replace(plan.assets[1], source_version="")
    plan = replace(plan, assets=(plan.assets[0], public))
    result = dataset_freeze_court(plan, df)
    assert any(c.endswith("source_version_missing") for c in codes(result))


def test_independent_units_are_fully_accounted_for():
    df = design_freeze()
    plan = hybrid_plan(df, retained_independent_unit_ids=("u1", "u2", "u3"))
    result = dataset_freeze_court(plan, df)
    assert "independent_unit_accounting_mismatch" in codes(result)


def test_prespecified_exclusion_can_account_for_unit_loss():
    df = design_freeze()
    plan = hybrid_plan(
        df,
        retained_independent_unit_ids=("u1", "u2", "u3"),
        exclusions=(ExclusionRecord("u4", "catastrophic unit loss before treatment"),),
    )
    assert dataset_freeze_court(plan, df).status is DatasetFreezeStatus.ADVANCE


def test_posthoc_exclusion_criterion_blocks():
    df = design_freeze()
    plan = hybrid_plan(
        df,
        retained_independent_unit_ids=("u1", "u2", "u3"),
        exclusions=(ExclusionRecord("u4", "removed after seeing extreme outcome"),),
    )
    result = dataset_freeze_court(plan, df)
    assert "posthoc_exclusion_criterion" in codes(result)
    assert result.status is DatasetFreezeStatus.BLOCKED


def test_frozen_project_schema_must_cover_prespecified_outcomes_covariates_metadata_and_blocking_factors():
    df = design_freeze()
    plan = hybrid_plan(df)
    project = replace(plan.assets[0], schema_fields=("primary injury", "root length", "initial size", "unit_id", "block_id", "treatment_code"))
    plan = replace(plan, assets=(project, plan.assets[1]))
    result = dataset_freeze_court(plan, df)
    assert "design_field_missing_from_frozen_schema" in codes(result)
    assert result.status is DatasetFreezeStatus.BLOCKED
    issue = next(i for i in result.issues if i.code == "design_field_missing_from_frozen_schema")
    assert "bench_position" in issue.reason


def test_public_only_route_needs_no_project_generated_asset_or_unit_manifest():
    df = design_freeze(StudyMode.PUBLIC_DATA)
    public = asset("public-counts", DataOrigin.PUBLIC_REUSED)
    plan = DatasetFreezePlan(
        freeze_id="public-only",
        design_freeze_sha256=df.design_freeze_sha256,
        mode=StudyMode.PUBLIC_DATA,
        assets=(public,),
    )
    assert dataset_freeze_court(plan, df).status is DatasetFreezeStatus.ADVANCE


def test_physical_only_route_rejects_undeclared_public_data():
    df = design_freeze(StudyMode.PHYSICAL)
    project = asset(
        "physical",
        DataOrigin.PROJECT_GENERATED,
        schema_fields=("primary injury", "root length", "initial size", "unit_id", "block_id", "treatment_code", "bench_position"),
    )
    public = asset("public", DataOrigin.PUBLIC_REUSED)
    plan = DatasetFreezePlan(
        freeze_id="physical-only",
        design_freeze_sha256=df.design_freeze_sha256,
        mode=StudyMode.PHYSICAL,
        assets=(project, public),
        retained_independent_unit_ids=("u1", "u2", "u3", "u4"),
    )
    result = dataset_freeze_court(plan, df)
    assert "unexpected_public_dataset" in codes(result)


def test_material_asset_change_changes_dataset_freeze_hash():
    df = design_freeze()
    plan = hybrid_plan(df)
    result = dataset_freeze_court(plan, df)
    first = build_dataset_freeze(plan, df, result)
    changed_asset = replace(plan.assets[0], sha256="d" * 64)
    changed_plan = replace(plan, assets=(changed_asset, plan.assets[1]))
    changed_result = dataset_freeze_court(changed_plan, df)
    second = build_dataset_freeze(changed_plan, df, changed_result)
    assert first.dataset_freeze_sha256 != second.dataset_freeze_sha256


def test_cannot_build_freeze_from_blocked_court():
    df = design_freeze()
    plan = hybrid_plan(df, outcome_values_inspected_before_freeze=True)
    with pytest.raises(ValueError):
        build_dataset_freeze(plan, df, dataset_freeze_court(plan, df))


def test_project_state_requires_design_frozen_and_preserves_analysis_specification_boundary():
    df = design_freeze()
    plan = hybrid_plan(df)
    result = dataset_freeze_court(plan, df)
    state = ProjectState("x")
    state.stage = Stage.DESIGN_FROZEN
    frozen = freeze_project_dataset(state, plan, df, result)
    assert state.stage is Stage.DATASET_FROZEN
    assert frozen.dataset_freeze_sha256 in state.history[-1][1]

    with pytest.raises(ValueError):
        state.transition(Stage.ANALYSIS_LOCKED, "must not skip Analysis Specification")
    state.transition(Stage.ANALYSIS_SPECIFICATION, "enter analysis specification")
    assert state.stage is Stage.ANALYSIS_SPECIFICATION

    wrong = ProjectState("wrong")
    wrong.stage = Stage.DESIGN
    with pytest.raises(ValueError):
        freeze_project_dataset(wrong, plan, df, result)


def test_blocker_first_prevents_dataset_freeze_entry_and_state_advance():
    df = design_freeze()
    plan = hybrid_plan(df)
    gate = BlockerGate([Blocker(
        blocker_id="ACQUISITION_OPEN",
        description="route-required data acquisition is incomplete",
        blocker_class=BlockerClass.BLOCKING,
        resolution_criterion="all route-required assets acquired and hashed",
        verification_method="Dataset Freeze evidence",
    )])
    with pytest.raises(PhaseBlockedError):
        dataset_freeze_court(plan, df, blocker_gate=gate)

    state = ProjectState("x")
    state.stage = Stage.DESIGN_FROZEN
    result = dataset_freeze_court(plan, df)
    with pytest.raises(PhaseBlockedError):
        freeze_project_dataset(state, plan, df, result, blocker_gate=gate)


def test_asset_constructor_rejects_bad_digest_duplicate_samples_and_public_without_dataset_id():
    with pytest.raises(ValueError):
        asset("bad", DataOrigin.PROJECT_GENERATED, sha256="not-a-digest")
    with pytest.raises(ValueError):
        asset("dup", DataOrigin.PROJECT_GENERATED, sample_ids=("s1", "s1"))
    with pytest.raises(ValueError):
        asset("public", DataOrigin.PUBLIC_REUSED, source_dataset_id="")
