import pytest

from agri_coscientist.blockers import (
    Blocker,
    BlockerClass,
    BlockerGate,
    PhaseBlockedError,
)
from agri_coscientist.data_fitness import (
    DataDomain,
    DataFitnessDimension,
    DataFitnessGrade,
    DataFitnessPolicy,
    DataFitnessProfile,
    DataFitnessStatus,
    DataUseRole,
    data_fitness_court,
    evaluate_general_data_fitness,
    evaluate_layered_data_fitness,
)
from agri_coscientist.gates import OmicsFitness, OmicsMetadata
from agri_coscientist.state import ProjectState, Stage


def profile(**overrides):
    data = dict(
        dataset_id="d1",
        domain=DataDomain.GENERIC,
        use_role=DataUseRole.PRIMARY_TEST,
        legal_reuse_permitted=True,
        provenance_traceable=True,
        source_identity_known=True,
        reproducible_acquisition=True,
        source_versioned_or_freezeable=True,
        population_fit=True,
        geography_fit=True,
        temporal_fit=True,
        construct_valid=True,
        measurement_valid=True,
        quality_documented=True,
        critical_qc_pass=True,
        required_fields_present=True,
        coverage_fraction=0.99,
        missing_fraction=0.01,
        missingness_characterized=True,
        missingness_strategy_available=True,
        outcome_or_key_variation_present=True,
        requires_join=False,
        stable_join_keys=True,
        join_coverage_fraction=1.0,
        target_estimand_identifiable=True,
        required_confounders_available=True,
        severe_selection_bias=False,
        selection_bias_addressable=True,
        survivorship_bias_present=False,
        survivorship_bias_addressable=True,
        sample_independence_known=True,
        units_known=True,
        units_harmonized=True,
        units_harmonizable=True,
    )
    data.update(overrides)
    return DataFitnessProfile(**data)


def dim(report, dimension):
    return next(d for d in report.dimensions if d.dimension is dimension)


def omics_meta(**overrides):
    data = dict(
        species_match=True,
        tissue_match=True,
        treatment_match=False,
        mechanistic_match=True,
        developmental_match=False,
        time_match=False,
        replicates_per_group=3,
        metadata_complete=True,
        provenance_traceable=True,
        reusable=True,
        genotype_match=False,
    )
    data.update(overrides)
    return OmicsMetadata(**data)


def test_clean_generic_primary_dataset_passes_general_g3_and_court():
    p = profile()
    grade, dimensions, repairs = evaluate_general_data_fitness(p)
    assert grade is DataFitnessGrade.PASS
    assert repairs == ()
    assert len(dimensions) == 15
    result = data_fitness_court([p])
    assert result.status is DataFitnessStatus.ADVANCE
    assert result.advancement_allowed is True
    assert result.passed_dataset_ids == ("d1",)


def test_illegal_reuse_is_hard_failure():
    report = evaluate_layered_data_fitness(profile(legal_reuse_permitted=False))
    assert report.layered_grade is DataFitnessGrade.FAIL
    assert dim(report, DataFitnessDimension.LEGAL_REUSE).grade is DataFitnessGrade.FAIL
    assert "replace:dataset_with_permitted_source" in report.repair_actions


def test_missing_provenance_or_source_identity_is_hard_failure():
    a = evaluate_layered_data_fitness(profile(provenance_traceable=False))
    b = evaluate_layered_data_fitness(profile(source_identity_known=False))
    assert a.layered_grade is DataFitnessGrade.FAIL
    assert b.layered_grade is DataFitnessGrade.FAIL
    assert dim(a, DataFitnessDimension.PROVENANCE).grade is DataFitnessGrade.FAIL


def test_primary_use_rejects_population_geography_or_temporal_mismatch():
    p = profile(population_fit=False, geography_fit=False, temporal_fit=False)
    report = evaluate_layered_data_fitness(p)
    assert report.layered_grade is DataFitnessGrade.FAIL
    assert dim(report, DataFitnessDimension.POPULATION_GEOGRAPHY).grade is DataFitnessGrade.FAIL
    assert dim(report, DataFitnessDimension.TEMPORAL_FIT).grade is DataFitnessGrade.FAIL


def test_mechanistic_support_mismatch_is_conditional_not_direct_validation():
    p = profile(
        use_role=DataUseRole.MECHANISTIC_SUPPORT,
        population_fit=False,
        geography_fit=False,
        temporal_fit=False,
    )
    report = evaluate_layered_data_fitness(p)
    assert report.layered_grade is DataFitnessGrade.CONDITIONAL
    assert "calibrate:mechanistic_scope" in report.repair_actions


def test_construct_or_measurement_failure_is_hard_failure():
    assert evaluate_layered_data_fitness(profile(construct_valid=False)).layered_grade is DataFitnessGrade.FAIL
    assert evaluate_layered_data_fitness(profile(measurement_valid=False)).layered_grade is DataFitnessGrade.FAIL


def test_critical_qc_failure_blocks_but_missing_quality_documentation_requires_revision():
    failed = evaluate_layered_data_fitness(profile(critical_qc_pass=False))
    conditional = evaluate_layered_data_fitness(profile(quality_documented=False))
    assert failed.layered_grade is DataFitnessGrade.FAIL
    assert conditional.layered_grade is DataFitnessGrade.CONDITIONAL
    assert "document:quality_evidence" in conditional.repair_actions


def test_primary_coverage_and_missingness_thresholds_are_predeclared_and_enforced():
    low_coverage = evaluate_layered_data_fitness(profile(coverage_fraction=0.90))
    high_missing = evaluate_layered_data_fitness(profile(missing_fraction=0.15))
    assert low_coverage.layered_grade is DataFitnessGrade.FAIL
    assert high_missing.layered_grade is DataFitnessGrade.FAIL


def test_supporting_data_can_be_conditional_above_missingness_threshold_with_strategy():
    p = profile(
        use_role=DataUseRole.MECHANISTIC_SUPPORT,
        missing_fraction=0.30,
        missingness_strategy_available=True,
    )
    report = evaluate_layered_data_fitness(p)
    assert report.layered_grade is DataFitnessGrade.CONDITIONAL
    assert dim(report, DataFitnessDimension.MISSINGNESS).grade is DataFitnessGrade.CONDITIONAL


def test_uncharacterized_nonzero_missingness_requires_revision_even_below_threshold():
    report = evaluate_layered_data_fitness(profile(missing_fraction=0.03, missingness_characterized=False))
    assert report.layered_grade is DataFitnessGrade.CONDITIONAL
    assert "characterize:missingness" in report.repair_actions


def test_no_informative_variation_hard_fails():
    report = evaluate_layered_data_fitness(profile(outcome_or_key_variation_present=False))
    assert report.layered_grade is DataFitnessGrade.FAIL
    assert dim(report, DataFitnessDimension.VARIATION).grade is DataFitnessGrade.FAIL


def test_unstable_join_keys_or_low_primary_join_coverage_hard_fail():
    unstable = profile(requires_join=True, stable_join_keys=False, join_coverage_fraction=0.99)
    low = profile(requires_join=True, stable_join_keys=True, join_coverage_fraction=0.80)
    assert evaluate_layered_data_fitness(unstable).layered_grade is DataFitnessGrade.FAIL
    assert evaluate_layered_data_fitness(low).layered_grade is DataFitnessGrade.FAIL


def test_primary_estimand_requires_identifiability_and_required_confounders():
    unidentifiable = evaluate_layered_data_fitness(profile(target_estimand_identifiable=False))
    confounded = evaluate_layered_data_fitness(profile(required_confounders_available=False))
    assert unidentifiable.layered_grade is DataFitnessGrade.FAIL
    assert confounded.layered_grade is DataFitnessGrade.FAIL
    assert "calibrate:noncausal_claim" in confounded.repair_actions


def test_selection_and_survivorship_bias_are_not_silently_ignored():
    primary = profile(severe_selection_bias=True, selection_bias_addressable=False)
    support = profile(
        use_role=DataUseRole.MECHANISTIC_SUPPORT,
        survivorship_bias_present=True,
        survivorship_bias_addressable=False,
    )
    assert evaluate_layered_data_fitness(primary).layered_grade is DataFitnessGrade.FAIL
    assert evaluate_layered_data_fitness(support).layered_grade is DataFitnessGrade.CONDITIONAL


def test_units_must_be_known_and_harmonized_or_harmonizable():
    unknown = evaluate_layered_data_fitness(profile(units_known=False))
    fixable = evaluate_layered_data_fitness(profile(units_harmonized=False, units_harmonizable=True))
    impossible = evaluate_layered_data_fitness(profile(units_harmonized=False, units_harmonizable=False))
    assert unknown.layered_grade is DataFitnessGrade.FAIL
    assert fixable.layered_grade is DataFitnessGrade.CONDITIONAL
    assert impossible.layered_grade is DataFitnessGrade.FAIL


def test_primary_sample_independence_must_be_established():
    report = evaluate_layered_data_fitness(profile(sample_independence_known=False))
    assert report.layered_grade is DataFitnessGrade.FAIL
    assert dim(report, DataFitnessDimension.INDEPENDENCE).grade is DataFitnessGrade.FAIL


def test_source_must_be_reacquirable_and_versioned_or_freezeable():
    reacquire = evaluate_layered_data_fitness(profile(reproducible_acquisition=False))
    freeze = evaluate_layered_data_fitness(profile(source_versioned_or_freezeable=False))
    assert reacquire.layered_grade is DataFitnessGrade.FAIL
    assert freeze.layered_grade is DataFitnessGrade.FAIL


def test_general_g3_pass_does_not_bypass_required_g3_omics():
    p = profile(
        dataset_id="omics",
        domain=DataDomain.OMICS,
        use_role=DataUseRole.MECHANISTIC_SUPPORT,
    )
    report = evaluate_layered_data_fitness(p)
    assert report.general_grade is DataFitnessGrade.PASS
    assert report.layered_grade is DataFitnessGrade.CONDITIONAL
    assert "run:g3_omics" in report.repair_actions


def test_g3_omics_incompatible_blocks_even_when_general_g3_passes():
    p = profile(dataset_id="omics", domain=DataDomain.OMICS, use_role=DataUseRole.MECHANISTIC_SUPPORT)
    report = evaluate_layered_data_fitness(p, omics_fitness=OmicsFitness.E)
    assert report.general_grade is DataFitnessGrade.PASS
    assert report.layered_grade is DataFitnessGrade.FAIL
    assert dim(report, DataFitnessDimension.DOMAIN_GATE).grade is DataFitnessGrade.FAIL


def test_mechanistically_compatible_omics_can_support_hybrid_route_after_both_layers_pass():
    p = profile(dataset_id="omics", domain=DataDomain.OMICS, use_role=DataUseRole.MECHANISTIC_SUPPORT)
    report = evaluate_layered_data_fitness(p, omics_metadata=omics_meta())
    assert report.omics_fitness is OmicsFitness.C
    assert report.general_grade is DataFitnessGrade.PASS
    assert report.layered_grade is DataFitnessGrade.PASS


def test_omics_grade_c_cannot_be_upgraded_to_primary_direct_test():
    p = profile(dataset_id="omics", domain=DataDomain.OMICS, use_role=DataUseRole.PRIMARY_TEST)
    report = evaluate_layered_data_fitness(p, omics_fitness=OmicsFitness.C)
    assert report.layered_grade is DataFitnessGrade.CONDITIONAL
    assert "calibrate:omics_claim_role" in report.repair_actions


def test_court_requires_all_route_required_datasets_to_pass():
    good = profile(dataset_id="good")
    bad = profile(dataset_id="bad", legal_reuse_permitted=False)
    result = data_fitness_court([good, bad])
    assert result.status is DataFitnessStatus.BLOCKED
    assert result.passed_dataset_ids == ("good",)
    assert result.failed_dataset_ids == ("bad",)
    assert result.advancement_allowed is False


def test_open_blocker_prevents_entry_from_feasibility_to_data_fitness():
    gate = BlockerGate([Blocker(
        blocker_id="FEASIBILITY_REPAIR_OPEN",
        description="selected route still has an unresolved feasibility failure",
        blocker_class=BlockerClass.BLOCKING,
        resolution_criterion="route re-evaluates to PASS",
        verification_method="feasibility capability evidence",
    )])
    with pytest.raises(PhaseBlockedError):
        data_fitness_court([profile()], blocker_gate=gate)


def test_physical_only_route_without_existing_data_can_advance_to_design_gate_without_fabricating_data():
    result = data_fitness_court([], route_requires_existing_data=False)
    assert result.status is DataFitnessStatus.ADVANCE
    assert result.reports == ()
    assert result.advancement_allowed is True


def test_required_existing_data_missing_is_blocked():
    result = data_fitness_court([], route_requires_existing_data=True)
    assert result.status is DataFitnessStatus.BLOCKED
    assert result.required_actions == ("discover:required_data",)


def test_state_machine_cannot_skip_data_fitness_and_jump_from_feasibility_to_design():
    state = ProjectState(name="x")
    state.stage = Stage.FEASIBILITY
    with pytest.raises(ValueError):
        state.transition(Stage.DESIGN, "attempted bypass")
    state.transition(Stage.DATA_FITNESS, "run General G3")
    state.transition(Stage.DESIGN, "all required data passed layered fitness gates")
    assert state.stage is Stage.DESIGN


def test_unknown_omics_evidence_and_incoherent_profiles_are_rejected():
    p = profile(dataset_id="known")
    with pytest.raises(ValueError):
        data_fitness_court([p], omics_fitness_by_dataset={"unknown": OmicsFitness.A})
    with pytest.raises(ValueError):
        profile(coverage_fraction=1.1)
    with pytest.raises(ValueError):
        profile(requires_join=False, join_coverage_fraction=0.9)


def test_policy_cannot_make_primary_thresholds_weaker_than_supporting_thresholds():
    with pytest.raises(ValueError):
        DataFitnessPolicy(min_primary_coverage=0.7, min_supporting_coverage=0.8)
    with pytest.raises(ValueError):
        DataFitnessPolicy(max_primary_missing_fraction=0.3, max_supporting_missing_fraction=0.2)
    with pytest.raises(ValueError):
        DataFitnessPolicy(min_primary_join_fraction=0.7, min_supporting_join_fraction=0.8)
