import pytest

from agri_coscientist.blockers import (
    Blocker,
    BlockerClass,
    BlockerGate,
    PhaseBlockedError,
)
from agri_coscientist.feasibility import (
    CourtStatus,
    FeasibilityDimension,
    FeasibilityGrade,
    PublicDataRole,
    RouteProposal,
    evaluate_route,
    feasibility_court,
)
from agri_coscientist.gates import OmicsFitness
from agri_coscientist.state import StudyMode


def route(**overrides):
    data = dict(
        route_id="r1",
        mode=StudyMode.PHYSICAL,
        physical_experiment_required=True,
        core_physical_capabilities_available=True,
        compute_worker_available=True,
        required_runtime_available=True,
        primary_outcome_measurable=True,
        statistically_identifiable=True,
        independent_replication_adequate=True,
        confirmatory_intent=True,
        budget_feasible=True,
        timeline_feasible=True,
        user_constraints_satisfied=True,
        journal_scope_fit=True,
        provenance_traceable=True,
        scientific_value=3,
        execution_risk=3,
        resource_burden=3,
    )
    data.update(overrides)
    return RouteProposal(**data)


def dimension(report, name):
    return next(d for d in report.dimensions if d.dimension is name)


def test_feasible_physical_route_passes_without_unavailable_omics():
    report = evaluate_route(route())
    assert report.overall is FeasibilityGrade.PASS
    assert report.advancement_allowed is True


def test_unavailable_required_new_wetlab_omics_fails_physical_route_and_proposes_public_omics():
    report = evaluate_route(route(
        requires_new_wetlab_omics=True,
        new_wetlab_omics_available=False,
    ))
    assert report.overall is FeasibilityGrade.FAIL
    lab = dimension(report, FeasibilityDimension.LAB)
    assert lab.grade is FeasibilityGrade.FAIL
    assert "consider:public_omics_reanalysis" in report.repair_actions
    assert "consider:hybrid_nonmolecular_plus_public_omics" in report.repair_actions


def test_unavailable_wetlab_omics_does_not_kill_valid_public_data_route():
    public = route(
        route_id="public",
        mode=StudyMode.PUBLIC_DATA,
        physical_experiment_required=False,
        core_physical_capabilities_available=False,
        public_data_required=True,
        public_data_candidates_found=2,
        best_public_omics_fitness=OmicsFitness.A,
        public_data_role=PublicDataRole.DIRECT_TEST,
        scientific_value=4,
    )
    result = feasibility_court([public])
    assert result.status is CourtStatus.ADVANCE
    assert result.selected_route_id == "public"


def test_hybrid_route_can_use_feasible_nonmolecular_experiment_plus_public_omics():
    hybrid = route(
        route_id="hybrid",
        mode=StudyMode.HYBRID,
        physical_experiment_required=True,
        core_physical_capabilities_available=True,
        requires_new_wetlab_omics=False,
        new_wetlab_omics_available=False,
        public_data_required=True,
        public_data_candidates_found=3,
        best_public_omics_fitness=OmicsFitness.C,
        public_data_role=PublicDataRole.MECHANISTIC_SUPPORT,
        scientific_value=5,
        execution_risk=2,
        resource_burden=3,
    )
    report = evaluate_route(hybrid)
    assert report.overall is FeasibilityGrade.PASS
    assert dimension(report, FeasibilityDimension.DATA).grade is FeasibilityGrade.PASS


def test_direct_public_data_claim_requires_directly_comparable_grade_for_clean_pass():
    proposal = route(
        route_id="public-b",
        mode=StudyMode.PUBLIC_DATA,
        physical_experiment_required=False,
        public_data_required=True,
        public_data_candidates_found=1,
        best_public_omics_fitness=OmicsFitness.B,
        public_data_role=PublicDataRole.DIRECT_TEST,
    )
    report = evaluate_route(proposal)
    assert report.overall is FeasibilityGrade.CONDITIONAL
    assert "calibrate:public_data_claim_role" in report.repair_actions


def test_contextual_public_data_can_be_feasible_at_grade_d():
    proposal = route(
        route_id="context",
        mode=StudyMode.PUBLIC_DATA,
        physical_experiment_required=False,
        public_data_required=True,
        public_data_candidates_found=2,
        best_public_omics_fitness=OmicsFitness.D,
        public_data_role=PublicDataRole.CONTEXTUAL,
    )
    assert evaluate_route(proposal).overall is FeasibilityGrade.PASS


def test_incompatible_public_data_hard_fails_required_data_route():
    proposal = route(
        route_id="bad-data",
        mode=StudyMode.PUBLIC_DATA,
        physical_experiment_required=False,
        public_data_required=True,
        public_data_candidates_found=5,
        best_public_omics_fitness=OmicsFitness.E,
        public_data_role=PublicDataRole.HYPOTHESIS_GENERATION,
    )
    report = evaluate_route(proposal)
    assert report.overall is FeasibilityGrade.FAIL
    assert "discover:alternative_dataset" in report.repair_actions


def test_confirmatory_route_fails_without_independent_replication():
    report = evaluate_route(route(independent_replication_adequate=False))
    assert report.overall is FeasibilityGrade.FAIL
    stat = dimension(report, FeasibilityDimension.STATISTICAL)
    assert "confirmatory route lacks adequate independent replication" in stat.reasons


def test_exploratory_route_with_weak_replication_is_conditional_not_confirmatory():
    report = evaluate_route(route(
        independent_replication_adequate=False,
        confirmatory_intent=False,
    ))
    assert report.overall is FeasibilityGrade.CONDITIONAL
    assert "label:exploratory" in report.repair_actions


def test_unidentifiable_estimand_hard_fails_even_with_data_and_compute():
    report = evaluate_route(route(statistically_identifiable=False))
    assert report.overall is FeasibilityGrade.FAIL
    assert dimension(report, FeasibilityDimension.STATISTICAL).grade is FeasibilityGrade.FAIL


def test_missing_compute_runtime_blocks_route():
    report = evaluate_route(route(required_runtime_available=False))
    assert report.overall is FeasibilityGrade.FAIL
    assert "provision:authoritative_compute_or_runtime" in report.repair_actions


def test_journal_mismatch_requires_revision_but_does_not_fake_feasibility_pass():
    report = evaluate_route(route(journal_scope_fit=False))
    assert report.overall is FeasibilityGrade.CONDITIONAL
    assert report.advancement_allowed is False
    assert "evolve:target_journal_or_question_framing" in report.repair_actions


def test_provenance_or_user_constraint_failure_is_hard_failure():
    assert evaluate_route(route(provenance_traceable=False)).overall is FeasibilityGrade.FAIL
    assert evaluate_route(route(user_constraints_satisfied=False)).overall is FeasibilityGrade.FAIL


def test_court_prefers_highest_scientific_value_then_lower_risk_and_burden():
    a = route(route_id="a", scientific_value=4, execution_risk=3, resource_burden=2)
    b = route(route_id="b", scientific_value=5, execution_risk=4, resource_burden=4)
    c = route(route_id="c", scientific_value=5, execution_risk=2, resource_burden=4)
    result = feasibility_court([a, b, c])
    assert result.status is CourtStatus.ADVANCE
    assert result.selected_route_id == "c"
    assert set(result.viable_route_ids) == {"a", "b", "c"}


def test_failed_physical_omics_route_can_be_rescued_by_hybrid_route():
    physical = route(
        route_id="physical-rnaseq",
        requires_new_wetlab_omics=True,
        new_wetlab_omics_available=False,
        scientific_value=5,
    )
    hybrid = route(
        route_id="hybrid-public-omics",
        mode=StudyMode.HYBRID,
        requires_new_wetlab_omics=False,
        new_wetlab_omics_available=False,
        public_data_required=True,
        public_data_candidates_found=2,
        best_public_omics_fitness=OmicsFitness.C,
        public_data_role=PublicDataRole.MECHANISTIC_SUPPORT,
        scientific_value=4,
        execution_risk=2,
    )
    result = feasibility_court([physical, hybrid])
    assert result.status is CourtStatus.ADVANCE
    assert result.selected_route_id == "hybrid-public-omics"
    assert result.failed_route_ids == ("physical-rnaseq",)


def test_only_conditional_routes_force_revision_before_advancement():
    conditional = route(route_id="conditional", journal_scope_fit=False)
    result = feasibility_court([conditional])
    assert result.status is CourtStatus.REVISE
    assert result.selected_route_id is None
    assert result.conditional_route_ids == ("conditional",)
    assert result.required_actions


def test_all_failed_routes_block_and_return_repair_actions():
    a = route(route_id="a", budget_feasible=False)
    b = route(route_id="b", statistically_identifiable=False)
    result = feasibility_court([a, b])
    assert result.status is CourtStatus.BLOCKED
    assert result.selected_route_id is None
    assert set(result.failed_route_ids) == {"a", "b"}
    assert "evolve:scope_cost_or_timeline" in result.required_actions
    assert "redesign:estimand_replication_or_outcome" in result.required_actions


def test_open_blocker_prevents_entry_to_feasibility_court():
    gate = BlockerGate([Blocker(
        blocker_id="NOVELTY_SEARCH_INCOMPLETE",
        description="novelty search coverage incomplete",
        blocker_class=BlockerClass.BLOCKING,
        resolution_criterion="all required searches complete",
        verification_method="inspect search snapshot",
    )])
    with pytest.raises(PhaseBlockedError):
        feasibility_court([route()], blocker_gate=gate)


def test_route_invariants_reject_incoherent_mode_requirements():
    with pytest.raises(ValueError):
        route(mode=StudyMode.PUBLIC_DATA, physical_experiment_required=True)
    with pytest.raises(ValueError):
        route(public_data_required=True, public_data_role=None)
    with pytest.raises(ValueError):
        route(requires_new_wetlab_omics=True, physical_experiment_required=False)
