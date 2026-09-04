from dataclasses import replace

import pytest

from agri_coscientist.analysis_specification import (
    AnalysisSpecificationPlan,
    AnalysisSpecStatus,
    AnalysisTask,
    MultiplicityMethod,
    PackagePin,
    RuntimeSpec,
    analysis_specification_court,
    build_analysis_lock,
    build_analysis_specification,
    enter_project_analysis_specification,
    lock_project_analysis,
)
from agri_coscientist.blockers import Blocker, BlockerClass, BlockerGate, PhaseBlockedError
from agri_coscientist.data_fitness import DataFitnessGrade, DataUseRole
from agri_coscientist.dataset_freeze import (
    AssetRole,
    DataOrigin,
    DatasetFreezePlan,
    FrozenDataAsset,
    build_dataset_freeze,
    dataset_freeze_court,
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


UNIT = "one independently grown wheat pot"


def freezes(repeated=False):
    physical = PhysicalDesign(
        experimental_unit=UNIT,
        analysis_unit_matches_experimental_unit=True,
        independent_units_total=8,
        independent_units_per_group=(4, 4),
        replication_rationale="independent pots estimate biological variation",
        precision_or_power_plan="n frozen before acquisition from precision planning",
        treatments=("cue",),
        controls=("mock",),
        manipulated_exposure=True,
        allocation_method=AllocationMethod.BLOCK_RANDOMIZED,
        randomization_plan="seeded randomization within bench blocks",
        nuisance_gradient_expected=True,
        blocking_factors=("block_id",),
        blocking_plan="predeclare blocks and randomize within block",
        subsamples_per_unit=1,
        subsamples_treated_as_technical=True,
        repeated_measures=repeated,
        repeated_measure_unit_id_preserved=True,
        destructive_sampling=False,
        independent_units_per_destructive_timepoint=True,
        sampling_schedule=("post-challenge",),
        required_methods=("root phenotyping",),
        unavailable_methods=("qPCR", "RNA-seq"),
        blinding_feasible=True,
        blinded_outcome_assessment=True,
        blinding_plan="coded outcome assessment",
    )
    public = PublicDatasetDesign(
        dataset_id="PUB1",
        role=DataUseRole.MECHANISTIC_SUPPORT,
        layered_data_fitness=DataFitnessGrade.PASS,
        source_design_understood=True,
        source_experimental_or_sampling_unit="independent root biological sample",
        sample_independence_known=True,
        planned_use_or_contrast="mechanical-stress versus control root contrast for mechanistic context only",
        supports_causal_identification=False,
    )
    design = StudyDesign(
        design_id="analysis-spec-test",
        question="Does cue exposure alter post-challenge injury?",
        hypotheses=("cue changes post-challenge injury",),
        mode=StudyMode.HYBRID,
        inference_intent=InferenceIntent.CAUSAL,
        confirmatory=True,
        outcomes=(
            OutcomeSpec("primary injury", OutcomeTier.PRIMARY, "assay", "post-challenge"),
            OutcomeSpec("root length", OutcomeTier.SECONDARY, "image", "post-challenge"),
        ),
        covariates=("initial size",),
        metadata_fields=("pot_id", "block_id", "treatment_code"),
        exclusion_criteria=("catastrophic unit loss before treatment",),
        quality_controls=("coded QC",),
        physical=physical,
        public_datasets=(public,),
    )
    df = build_design_freeze(design, design_court(design))
    project = FrozenDataAsset(
        asset_id="physical",
        origin=DataOrigin.PROJECT_GENERATED,
        role=AssetRole.DATA,
        sha256="1" * 64,
        bytes=1000,
        locator="drive://physical.csv",
        representation="csv",
        schema_fields=("primary injury", "root length", "initial size", "pot_id", "block_id", "treatment_code"),
        sample_ids=tuple(f"u{i}" for i in range(1, 9)),
    )
    reused = FrozenDataAsset(
        asset_id="public",
        origin=DataOrigin.PUBLIC_REUSED,
        role=AssetRole.DATA,
        sha256="2" * 64,
        bytes=2000,
        locator="frozen://public-counts",
        representation="featurecounts_integer_counts",
        source_dataset_id="PUB1",
        source_version="accession+asset-sha-v1",
        sample_ids=("p1", "p2", "p3", "p4"),
    )
    dataset_plan = DatasetFreezePlan(
        freeze_id="dataset-freeze-v1",
        design_freeze_sha256=df.design_freeze_sha256,
        mode=StudyMode.HYBRID,
        assets=(project, reused),
        retained_independent_unit_ids=tuple(f"u{i}" for i in range(1, 9)),
    )
    dataset_result = dataset_freeze_court(dataset_plan, df)
    frozen_data = build_dataset_freeze(dataset_plan, df, dataset_result)
    return df, frozen_data


def runtime():
    return RuntimeSpec(
        runtime_id="r-runtime",
        language="R",
        language_version="4.6.1",
        packages=(
            PackagePin("lme4", "1.1-37"),
            PackagePin("DESeq2", "1.50.0"),
        ),
    )


def physical_task(**overrides):
    values = dict(
        task_id="physical-primary",
        component="physical",
        target_name="primary injury",
        design_outcome="primary injury",
        confirmatory=True,
        estimand="mean cue-versus-mock treatment effect on primary injury",
        contrast="cue minus mock",
        model_family="linear mixed model",
        model_formula="primary injury ~ treatment_code + block_id",
        unit_of_analysis=UNIT,
        dependency_structure="independent experimental units with block adjustment",
        adjustment_terms=("block_id",),
        transformation_rule="none; analyze prespecified original scale",
        missing_data_policy="report missingness; no outcome-based imputation or deletion",
        exclusion_policy="dataset_freeze_only",
        multiplicity_family="primary",
        multiplicity_method=MultiplicityMethod.NONE,
        alpha=0.05,
        confidence_level=0.95,
        effect_measure="adjusted mean difference with 95% CI",
        diagnostics=("residual distribution", "variance structure", "influence without outcome-based deletion"),
        fallback_rules=("if prespecified diagnostics fail, use robust sandwich inference without changing the estimand",),
        runtime_id="r-runtime",
        engine_package="lme4",
        implementation_entrypoint="scripts/analysis/physical_primary.R",
        execution_order=1,
    )
    values.update(overrides)
    return AnalysisTask(**values)


def public_task(**overrides):
    values = dict(
        task_id="public-mechanistic",
        component="PUB1",
        target_name="prespecified public root transcriptome contrast",
        design_outcome=None,
        confirmatory=False,
        estimand="log2 fold change for prespecified stress-versus-control contrast",
        contrast="mechanical stress versus control",
        model_family="negative-binomial count model",
        model_formula="count ~ source_condition",
        unit_of_analysis="independent root biological sample",
        dependency_structure="independent source-study biological samples",
        adjustment_terms=(),
        transformation_rule="raw integer counts for model fitting; transformed values only for visualization/QC",
        missing_data_policy="no gene/sample deletion based on observed effect direction or significance",
        exclusion_policy="dataset_freeze_only",
        multiplicity_family="public_omics",
        multiplicity_method=MultiplicityMethod.BH_FDR,
        alpha=0.05,
        confidence_level=0.95,
        effect_measure="log2 fold change with interval and FDR-adjusted evidence",
        diagnostics=("count distribution", "library-size QC", "dispersion fit"),
        fallback_rules=("if model fitting fails, stop and return to Analysis Specification; do not silently switch method",),
        runtime_id="r-runtime",
        engine_package="DESeq2",
        implementation_entrypoint="scripts/analysis/public_mechanistic.R",
        execution_order=2,
        public_data_role=DataUseRole.MECHANISTIC_SUPPORT,
        planned_use_binding="mechanical-stress versus control root contrast for mechanistic context only",
        direct_validation_claim=False,
    )
    values.update(overrides)
    return AnalysisTask(**values)


def plan(df=None, frozen_data=None, **overrides):
    df, frozen_data = (df, frozen_data) if df is not None else freezes()
    values = dict(
        specification_id="analysis-spec-v1",
        design_freeze_sha256=df.design_freeze_sha256,
        dataset_freeze_sha256=frozen_data.dataset_freeze_sha256,
        mode=StudyMode.HYBRID,
        runtimes=(runtime(),),
        tasks=(physical_task(), public_task()),
        random_seed=20260904,
        outcome_values_inspected_before_specification=False,
    )
    values.update(overrides)
    return AnalysisSpecificationPlan(**values)


def codes(result):
    return {i.code for i in result.issues}


def test_valid_hybrid_specification_and_lock_are_deterministic_and_pre_outcome():
    df, frozen_data = freezes()
    p = plan(df, frozen_data)
    result = analysis_specification_court(p, df, frozen_data)
    assert result.status is AnalysisSpecStatus.ADVANCE
    first = build_analysis_specification(p, df, frozen_data, result)
    second = build_analysis_specification(p, df, frozen_data, result)
    assert first.specification_sha256 == second.specification_sha256
    assert first.pre_outcome is True
    assert first.analysis_model_locked is False
    lock1 = build_analysis_lock(first)
    lock2 = build_analysis_lock(second)
    assert lock1.analysis_lock_sha256 == lock2.analysis_lock_sha256
    assert lock1.analysis_specification_locked is True
    assert lock1.analysis_model_locked is True


def test_wrong_design_or_dataset_binding_blocks():
    df, frozen_data = freezes()
    bad_design = plan(df, frozen_data, design_freeze_sha256="a" * 64)
    assert "design_freeze_binding_mismatch" in codes(analysis_specification_court(bad_design, df, frozen_data))
    bad_data = plan(df, frozen_data, dataset_freeze_sha256="b" * 64)
    assert "dataset_freeze_binding_mismatch" in codes(analysis_specification_court(bad_data, df, frozen_data))


def test_outcome_peeking_before_specification_blocks():
    df, frozen_data = freezes()
    p = plan(df, frozen_data, outcome_values_inspected_before_specification=True)
    result = analysis_specification_court(p, df, frozen_data)
    assert result.status is AnalysisSpecStatus.BLOCKED
    assert "pre_specification_outcome_access" in codes(result)


def test_physical_analysis_unit_must_match_experimental_unit():
    df, frozen_data = freezes()
    p = plan(df, frozen_data, tasks=(physical_task(unit_of_analysis="technical assay well"), public_task()))
    result = analysis_specification_court(p, df, frozen_data)
    assert any(c.endswith("analysis_unit_mismatch") for c in codes(result))


def test_design_blocking_factor_cannot_disappear_in_analysis():
    df, frozen_data = freezes()
    p = plan(df, frozen_data, tasks=(physical_task(adjustment_terms=()), public_task()))
    result = analysis_specification_court(p, df, frozen_data)
    assert any(c.endswith("blocking_term_missing") for c in codes(result))


def test_repeated_measures_require_dependency_structure():
    df, frozen_data = freezes(repeated=True)
    p = plan(df, frozen_data, tasks=(physical_task(dependency_structure="independent"), public_task()))
    result = analysis_specification_court(p, df, frozen_data)
    assert any(c.endswith("repeated_measure_dependency_missing") for c in codes(result))


def test_primary_outcome_requires_confirmatory_analysis():
    df, frozen_data = freezes()
    p = plan(df, frozen_data, tasks=(replace(physical_task(), confirmatory=False), public_task()))
    result = analysis_specification_court(p, df, frozen_data)
    assert "primary_outcome_analysis_missing" in codes(result)


def test_multiple_confirmatory_tests_in_family_require_multiplicity_control():
    df, frozen_data = freezes()
    secondary = physical_task(
        task_id="physical-secondary",
        target_name="root length",
        design_outcome="root length",
        multiplicity_family="primary",
        multiplicity_method=MultiplicityMethod.NONE,
        execution_order=2,
    )
    public = public_task(execution_order=3)
    p = plan(df, frozen_data, tasks=(physical_task(), secondary, public))
    result = analysis_specification_court(p, df, frozen_data)
    assert "multiplicity:primary:uncontrolled" in codes(result)


def test_public_data_role_and_planned_use_cannot_be_promoted_or_changed():
    df, frozen_data = freezes()
    promoted = public_task(public_data_role=DataUseRole.PRIMARY_TEST, direct_validation_claim=True)
    p = plan(df, frozen_data, tasks=(physical_task(), promoted))
    result = analysis_specification_court(p, df, frozen_data)
    assert any(c.endswith("public_role_mismatch") for c in codes(result))

    changed_use = public_task(planned_use_binding="new post-hoc contrast")
    p2 = plan(df, frozen_data, tasks=(physical_task(), changed_use))
    assert any(c.endswith("public_planned_use_mismatch") for c in codes(analysis_specification_court(p2, df, frozen_data)))


def test_mechanistic_public_data_cannot_claim_direct_validation():
    df, frozen_data = freezes()
    p = plan(df, frozen_data, tasks=(physical_task(), public_task(direct_validation_claim=True)))
    result = analysis_specification_court(p, df, frozen_data)
    assert any(c.endswith("public_causal_overreach") for c in codes(result))


def test_unpinned_engine_package_blocks():
    df, frozen_data = freezes()
    p = plan(df, frozen_data, tasks=(physical_task(engine_package="nlme"), public_task()))
    result = analysis_specification_court(p, df, frozen_data)
    assert any(c.endswith("engine_package_unpinned") for c in codes(result))


def test_data_dependent_method_selection_blocks():
    df, frozen_data = freezes()
    p = plan(df, frozen_data, tasks=(physical_task(data_dependent_method_selection=True), public_task()))
    result = analysis_specification_court(p, df, frozen_data)
    assert any(c.endswith("data_dependent_method_selection") for c in codes(result))


def test_analysis_cannot_invent_new_exclusion_policy():
    df, frozen_data = freezes()
    p = plan(df, frozen_data, tasks=(physical_task(exclusion_policy="remove outliers after model fit"), public_task()))
    result = analysis_specification_court(p, df, frozen_data)
    assert any(c.endswith("exclusion_policy_changed") for c in codes(result))


def test_confirmatory_tasks_require_diagnostics_and_fallback_rules():
    df, frozen_data = freezes()
    p = plan(df, frozen_data, tasks=(physical_task(diagnostics=()), public_task()))
    assert any(c.endswith("diagnostics_missing") for c in codes(analysis_specification_court(p, df, frozen_data)))
    p2 = plan(df, frozen_data, tasks=(physical_task(fallback_rules=()), public_task()))
    assert any(c.endswith("fallback_rules_missing") for c in codes(analysis_specification_court(p2, df, frozen_data)))


def test_unknown_physical_outcome_or_public_component_blocks():
    df, frozen_data = freezes()
    p = plan(df, frozen_data, tasks=(physical_task(design_outcome="not frozen"), public_task()))
    assert any(c.endswith("design_outcome_unknown") for c in codes(analysis_specification_court(p, df, frozen_data)))
    bad_public = public_task(component="PUB2")
    p2 = plan(df, frozen_data, tasks=(physical_task(), bad_public))
    assert any(c.endswith("public_component_undeclared") for c in codes(analysis_specification_court(p2, df, frozen_data)))


def test_state_requires_dataset_frozen_then_analysis_specification_then_lock():
    df, frozen_data = freezes()
    p = plan(df, frozen_data)
    result = analysis_specification_court(p, df, frozen_data)
    frozen_spec = build_analysis_specification(p, df, frozen_data, result)
    state = ProjectState("x")
    state.stage = Stage.DATASET_FROZEN
    enter_project_analysis_specification(state, frozen_spec)
    assert state.stage is Stage.ANALYSIS_SPECIFICATION
    lock = lock_project_analysis(state, frozen_spec)
    assert state.stage is Stage.ANALYSIS_LOCKED
    assert lock.analysis_model_locked is True

    wrong = ProjectState("wrong")
    wrong.stage = Stage.DESIGN_FROZEN
    with pytest.raises(ValueError):
        enter_project_analysis_specification(wrong, frozen_spec)


def test_cannot_build_specification_from_blocked_court_or_lock_post_outcome_specification():
    df, frozen_data = freezes()
    p = plan(df, frozen_data, outcome_values_inspected_before_specification=True)
    result = analysis_specification_court(p, df, frozen_data)
    with pytest.raises(ValueError):
        build_analysis_specification(p, df, frozen_data, result)

    good = plan(df, frozen_data)
    good_result = analysis_specification_court(good, df, frozen_data)
    frozen_spec = build_analysis_specification(good, df, frozen_data, good_result)
    with pytest.raises(ValueError):
        build_analysis_lock(replace(frozen_spec, pre_outcome=False))


def test_blocker_first_prevents_specification_and_lock_state_advancement():
    df, frozen_data = freezes()
    p = plan(df, frozen_data)
    gate = BlockerGate([Blocker(
        blocker_id="ANALYSIS_PRECONDITION_OPEN",
        description="dataset provenance discrepancy unresolved",
        blocker_class=BlockerClass.BLOCKING,
        resolution_criterion="reconcile exact Dataset Freeze",
        verification_method="provenance audit",
    )])
    with pytest.raises(PhaseBlockedError):
        analysis_specification_court(p, df, frozen_data, blocker_gate=gate)

    result = analysis_specification_court(p, df, frozen_data)
    frozen_spec = build_analysis_specification(p, df, frozen_data, result)
    state = ProjectState("x")
    state.stage = Stage.DATASET_FROZEN
    with pytest.raises(PhaseBlockedError):
        enter_project_analysis_specification(state, frozen_spec, blocker_gate=gate)

    state.stage = Stage.ANALYSIS_SPECIFICATION
    with pytest.raises(PhaseBlockedError):
        lock_project_analysis(state, frozen_spec, blocker_gate=gate)


def test_runtime_and_plan_constructors_reject_unpinned_or_ambiguous_execution():
    with pytest.raises(ValueError):
        PackagePin("DESeq2", "latest")
    with pytest.raises(ValueError):
        RuntimeSpec("r", "R", "latest", ())

    df, frozen_data = freezes()
    with pytest.raises(ValueError):
        AnalysisSpecificationPlan(
            specification_id="bad-order",
            design_freeze_sha256=df.design_freeze_sha256,
            dataset_freeze_sha256=frozen_data.dataset_freeze_sha256,
            mode=StudyMode.HYBRID,
            runtimes=(runtime(),),
            tasks=(physical_task(execution_order=2), public_task(execution_order=3)),
            random_seed=1,
        )
