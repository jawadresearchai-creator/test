from dataclasses import replace

import pytest

from agri_coscientist.blockers import Blocker, BlockerClass, BlockerGate, PhaseBlockedError
from agri_coscientist.data_fitness import DataFitnessGrade, DataUseRole
from agri_coscientist.design import (
    AllocationMethod,
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
from agri_coscientist.state import ProjectState, Stage, StudyMode


def physical(**overrides):
    values = dict(
        experimental_unit="one independently grown wheat pot containing one focal receiver plant",
        analysis_unit_matches_experimental_unit=True,
        independent_units_total=12,
        independent_units_per_group=(6, 6),
        replication_rationale="independent pots capture biological between-unit variation",
        precision_or_power_plan="choose final n before acquisition using pilot variance or a minimally important effect precision calculation",
        treatments=("mechanical-cue exposure",),
        controls=("mock cue exposure",),
        manipulated_exposure=True,
        allocation_method=AllocationMethod.BLOCK_RANDOMIZED,
        randomization_plan="within each bench-position block, assign coded pots using a seeded permutation recorded before treatment",
        nuisance_gradient_expected=True,
        blocking_factors=("bench_position",),
        blocking_plan="construct spatial blocks before random allocation and retain block IDs in metadata",
        subsamples_per_unit=2,
        subsamples_treated_as_technical=True,
        repeated_measures=False,
        repeated_measure_unit_id_preserved=True,
        destructive_sampling=False,
        independent_units_per_destructive_timepoint=True,
        sampling_schedule=("baseline", "30 min after cue", "post-challenge"),
        required_methods=("extracellular ATP assay", "antioxidant enzyme assay", "root phenotyping"),
        unavailable_methods=("qPCR", "RNA-seq"),
        blinding_feasible=True,
        blinded_outcome_assessment=True,
        blinding_plan="sample tubes and images are coded until primary QC and measurements are complete",
    )
    values.update(overrides)
    return PhysicalDesign(**values)


def public_dataset(**overrides):
    values = dict(
        dataset_id="public_wheat_root_mechanical_context",
        role=DataUseRole.MECHANISTIC_SUPPORT,
        layered_data_fitness=DataFitnessGrade.PASS,
        source_design_understood=True,
        source_experimental_or_sampling_unit="independent root biological sample",
        sample_independence_known=True,
        planned_use_or_contrast="prespecified root mechanical-stress contrast used only for convergent pathway context",
        supports_causal_identification=False,
        result_level_outcomes_accessed_before_design_freeze=False,
    )
    values.update(overrides)
    return PublicDatasetDesign(**values)


def outcomes():
    return (
        OutcomeSpec("challenge oxidative injury", OutcomeTier.PRIMARY, "lipid peroxidation assay", "post-challenge", "nmol g-1 FW"),
        OutcomeSpec("receiver root growth", OutcomeTier.SECONDARY, "image-based root phenotyping", "post-challenge", "cm"),
        OutcomeSpec("extracellular ATP", OutcomeTier.MECHANISTIC, "luciferase ATP assay", "30 min after cue", "relative ATP concentration"),
        OutcomeSpec("assay blank recovery", OutcomeTier.QC, "spike-recovery QC", "each assay batch", "%"),
    )


def hybrid_design(**overrides):
    values = dict(
        design_id="wheat_hybrid_design_v1",
        question="Does a mechanically induced root cue prime receiver wheat against a later compaction challenge, with independent public omics used only as mechanistic context?",
        hypotheses=(
            "randomized cue exposure changes the prespecified primary post-challenge oxidative-injury outcome",
            "independent public root transcriptomic data may provide convergent mechanistic context but are not direct validation of the experimental units",
        ),
        mode=StudyMode.HYBRID,
        inference_intent=InferenceIntent.CAUSAL,
        confirmatory=True,
        outcomes=outcomes(),
        covariates=("initial plant size",),
        metadata_fields=("pot_id", "block_id", "treatment_code", "sampling_time", "assay_batch"),
        exclusion_criteria=("exclude only prespecified catastrophic unit loss before treatment; otherwise retain and report",),
        quality_controls=("assay blanks", "spike recovery", "coded image QC"),
        physical=physical(),
        public_datasets=(public_dataset(),),
        outcome_data_accessed_before_design_freeze=False,
        notes=("public omics is mechanistic support only",),
    )
    values.update(overrides)
    return StudyDesign(**values)


def codes(result):
    return {i.code for i in result.issues}


def test_valid_hybrid_design_advances():
    result = design_court(hybrid_design())
    assert result.status is DesignStatus.ADVANCE
    assert result.issues == ()
    assert result.advancement_allowed is True


def test_route_shape_is_enforced_for_physical_public_and_hybrid_modes():
    bad_physical = hybrid_design(mode=StudyMode.PHYSICAL)
    bad_public = hybrid_design(mode=StudyMode.PUBLIC_DATA)
    bad_hybrid = hybrid_design(physical=None)
    assert design_court(bad_physical).status is DesignStatus.BLOCKED
    assert design_court(bad_public).status is DesignStatus.BLOCKED
    assert design_court(bad_hybrid).status is DesignStatus.BLOCKED
    assert "route_shape" in codes(design_court(bad_hybrid))


def test_analysis_unit_mismatch_blocks_pseudoreplication():
    result = design_court(hybrid_design(physical=physical(analysis_unit_matches_experimental_unit=False)))
    assert result.status is DesignStatus.BLOCKED
    assert "analysis_unit_mismatch" in codes(result)


def test_confirmatory_groups_need_independent_replication_not_technical_subsamples():
    p = physical(independent_units_total=2, independent_units_per_group=(1, 1), subsamples_per_unit=10)
    result = design_court(hybrid_design(physical=p))
    assert result.status is DesignStatus.BLOCKED
    assert "independent_replication_insufficient" in codes(result)


def test_replication_requires_rationale_and_precision_or_power_plan():
    result = design_court(hybrid_design(physical=physical(replication_rationale="", precision_or_power_plan="")))
    assert result.status is DesignStatus.BLOCKED
    assert "replication_rationale_missing" in codes(result)


def test_unavailable_wetlab_omics_cannot_reenter_as_required_method():
    p = physical(required_methods=("extracellular ATP assay", "RNA-seq"), unavailable_methods=("RNA-seq", "qPCR"))
    result = design_court(hybrid_design(physical=p))
    assert result.status is DesignStatus.BLOCKED
    assert "unavailable_method_required" in codes(result)
    assert "use:public_data_if_scientifically_valid" in result.required_actions


def test_subsamples_must_not_be_counted_as_independent_replicates():
    p = physical(subsamples_per_unit=4, subsamples_treated_as_technical=False)
    result = design_court(hybrid_design(physical=p))
    assert result.status is DesignStatus.BLOCKED
    assert "subsample_pseudoreplication" in codes(result)


def test_repeated_measures_require_persistent_unit_identity():
    p = physical(repeated_measures=True, repeated_measure_unit_id_preserved=False)
    result = design_court(hybrid_design(physical=p))
    assert "repeated_measure_identity_missing" in codes(result)
    assert result.status is DesignStatus.BLOCKED


def test_destructive_sampling_cannot_masquerade_as_repeated_measure_on_same_unit():
    p = physical(repeated_measures=True, destructive_sampling=True, independent_units_per_destructive_timepoint=False)
    result = design_court(hybrid_design(physical=p))
    assert "destructive_repeated_measure_conflict" in codes(result)
    assert result.status is DesignStatus.BLOCKED


def test_causal_physical_claim_requires_manipulation_and_randomization():
    no_manipulation = design_court(hybrid_design(physical=physical(manipulated_exposure=False)))
    nonrandom = design_court(hybrid_design(physical=physical(allocation_method=AllocationMethod.NONRANDOM)))
    assert "causal_without_manipulation" in codes(no_manipulation)
    assert "causal_without_randomization" in codes(nonrandom)
    assert no_manipulation.status is DesignStatus.BLOCKED
    assert nonrandom.status is DesignStatus.BLOCKED


def test_randomized_design_requires_reproducible_randomization_plan():
    result = design_court(hybrid_design(physical=physical(randomization_plan="")))
    assert "randomization_plan_missing" in codes(result)
    assert result.status is DesignStatus.BLOCKED


def test_known_nuisance_gradient_requires_blocking():
    p = physical(blocking_factors=(), blocking_plan="")
    result = design_court(hybrid_design(physical=p))
    assert "blocking_missing" in codes(result)
    assert result.status is DesignStatus.BLOCKED


def test_declared_blocks_require_block_construction_plan():
    result = design_court(hybrid_design(physical=physical(blocking_plan="")))
    assert "blocking_plan_missing" in codes(result)
    assert result.status is DesignStatus.BLOCKED


def test_feasible_blinding_omission_forces_revision_not_silent_pass():
    p = physical(blinded_outcome_assessment=False, blinding_plan="")
    result = design_court(hybrid_design(physical=p))
    assert result.status is DesignStatus.REVISE
    assert "blinding_not_used" in codes(result)


def test_confirmatory_design_requires_prespecified_exclusions_and_qc():
    no_exclusions = design_court(hybrid_design(exclusion_criteria=()))
    no_qc = design_court(hybrid_design(quality_controls=()))
    assert "exclusions_not_prespecified" in codes(no_exclusions)
    assert "quality_controls_missing" in codes(no_qc)
    assert no_exclusions.status is DesignStatus.BLOCKED
    assert no_qc.status is DesignStatus.BLOCKED


def test_missing_metadata_forces_revision():
    result = design_court(hybrid_design(metadata_fields=()))
    assert result.status is DesignStatus.REVISE
    assert "metadata_missing" in codes(result)


def test_many_co_primary_outcomes_require_justification_before_freeze():
    extra = (
        OutcomeSpec("p1", OutcomeTier.PRIMARY, "m", "t"),
        OutcomeSpec("p2", OutcomeTier.PRIMARY, "m", "t"),
        OutcomeSpec("p3", OutcomeTier.PRIMARY, "m", "t"),
        OutcomeSpec("p4", OutcomeTier.PRIMARY, "m", "t"),
    )
    result = design_court(hybrid_design(outcomes=extra))
    assert result.status is DesignStatus.REVISE
    assert "primary_outcome_multiplicity" in codes(result)


def test_public_component_must_have_passed_layered_data_fitness():
    d = public_dataset(layered_data_fitness=DataFitnessGrade.CONDITIONAL)
    result = design_court(hybrid_design(public_datasets=(d,)))
    assert result.status is DesignStatus.BLOCKED
    assert any(c.endswith("data_fitness_not_passed") for c in codes(result))


def test_public_source_design_and_independence_must_be_understood():
    unknown_design = design_court(hybrid_design(public_datasets=(public_dataset(source_design_understood=False),)))
    unknown_independence = design_court(hybrid_design(public_datasets=(public_dataset(sample_independence_known=False),)))
    assert unknown_design.status is DesignStatus.BLOCKED
    assert unknown_independence.status is DesignStatus.BLOCKED


def test_public_primary_causal_use_requires_causal_identification():
    public_primary = public_dataset(role=DataUseRole.PRIMARY_TEST, supports_causal_identification=False)
    result = design_court(hybrid_design(public_datasets=(public_primary,)))
    assert result.status is DesignStatus.BLOCKED
    assert any(c.endswith("causal_identification_not_supported") for c in codes(result))


def test_public_mechanistic_support_does_not_need_to_supply_causal_identification():
    result = design_court(hybrid_design(public_datasets=(public_dataset(supports_causal_identification=False),)))
    assert result.status is DesignStatus.ADVANCE


def test_confirmatory_pre_freeze_outcome_access_blocks_and_forces_exploratory_or_restart():
    top_level = design_court(hybrid_design(outcome_data_accessed_before_design_freeze=True))
    dataset_level = design_court(hybrid_design(public_datasets=(public_dataset(result_level_outcomes_accessed_before_design_freeze=True),)))
    assert top_level.status is DesignStatus.BLOCKED
    assert dataset_level.status is DesignStatus.BLOCKED
    assert "pre_freeze_outcome_access" in codes(top_level)


def test_design_freeze_is_deterministic_and_does_not_lock_analysis_model():
    design = hybrid_design()
    result = design_court(design)
    a = build_design_freeze(design, result)
    b = build_design_freeze(design, result)
    assert a.design_freeze_sha256 == b.design_freeze_sha256
    assert a.pre_outcome is True
    assert a.analysis_model_locked is False
    assert "analysis_model" not in a.design_payload


def test_material_design_change_changes_design_freeze_hash():
    design = hybrid_design()
    result = design_court(design)
    changed = replace(design, exclusion_criteria=("a different prespecified exclusion rule",))
    changed_result = design_court(changed)
    assert build_design_freeze(design, result).design_freeze_sha256 != build_design_freeze(changed, changed_result).design_freeze_sha256


def test_cannot_freeze_failed_or_conditional_design():
    bad = hybrid_design(physical=physical(analysis_unit_matches_experimental_unit=False))
    conditional = hybrid_design(metadata_fields=())
    with pytest.raises(ValueError):
        build_design_freeze(bad, design_court(bad))
    with pytest.raises(ValueError):
        build_design_freeze(conditional, design_court(conditional))


def test_freeze_project_design_advances_state_only_from_design():
    state = ProjectState(name="x")
    state.stage = Stage.DESIGN
    design = hybrid_design()
    freeze = freeze_project_design(state, design, design_court(design))
    assert state.stage is Stage.DESIGN_FROZEN
    assert freeze.design_freeze_sha256 in state.history[-1][1]

    wrong = ProjectState(name="wrong")
    wrong.stage = Stage.DATA_FITNESS
    with pytest.raises(ValueError):
        freeze_project_design(wrong, design, design_court(design))


def test_blocker_first_prevents_entry_to_design_and_design_freeze():
    gate = BlockerGate([Blocker(
        blocker_id="DATA_FITNESS_OPEN",
        description="route-required dataset has not passed G3",
        blocker_class=BlockerClass.BLOCKING,
        resolution_criterion="layered Data Fitness PASS",
        verification_method="Data Fitness evidence",
    )])
    with pytest.raises(PhaseBlockedError):
        design_court(hybrid_design(), blocker_gate=gate)

    design = hybrid_design()
    state = ProjectState(name="x")
    state.stage = Stage.DESIGN
    with pytest.raises(PhaseBlockedError):
        freeze_project_design(state, design, design_court(design), blocker_gate=gate)


def test_public_data_only_route_can_be_designed_without_fabricating_physical_experiment():
    d = StudyDesign(
        design_id="public_only",
        question="Is the prespecified public-data contrast associated with the response?",
        hypotheses=("the prespecified contrast differs in the primary outcome",),
        mode=StudyMode.PUBLIC_DATA,
        inference_intent=InferenceIntent.ASSOCIATIONAL,
        confirmatory=True,
        outcomes=(OutcomeSpec("public primary", OutcomeTier.PRIMARY, "repository count matrix", "source sampling time"),),
        covariates=("source batch",),
        metadata_fields=("sample_id", "source_group"),
        exclusion_criteria=("use only samples frozen in the eligibility manifest",),
        quality_controls=("source metadata consistency",),
        physical=None,
        public_datasets=(public_dataset(role=DataUseRole.PRIMARY_TEST),),
    )
    assert design_court(d).status is DesignStatus.ADVANCE


def test_physical_only_route_can_be_designed_without_public_dataset():
    d = hybrid_design(mode=StudyMode.PHYSICAL, public_datasets=())
    assert design_court(d).status is DesignStatus.ADVANCE


def test_constructor_guards_outcome_identity_primary_requirement_and_unit_counts():
    with pytest.raises(ValueError):
        hybrid_design(outcomes=(OutcomeSpec("x", OutcomeTier.SECONDARY, "m", "t"),))
    with pytest.raises(ValueError):
        hybrid_design(outcomes=(OutcomeSpec("x", OutcomeTier.PRIMARY, "m", "t"), OutcomeSpec("X", OutcomeTier.SECONDARY, "m", "t")))
    with pytest.raises(ValueError):
        physical(independent_units_total=10, independent_units_per_group=(6, 6))
