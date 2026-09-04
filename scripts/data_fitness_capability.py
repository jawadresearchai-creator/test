from __future__ import annotations

import json
from pathlib import Path

from agri_coscientist.data_fitness import (
    DataDomain,
    DataFitnessDimension,
    DataFitnessGrade,
    DataFitnessProfile,
    DataFitnessStatus,
    DataUseRole,
    data_fitness_court,
    evaluate_layered_data_fitness,
)
from agri_coscientist.gates import OmicsFitness, OmicsMetadata


def base_profile(**overrides):
    values = dict(
        dataset_id="public_wheat_root_omics",
        domain=DataDomain.OMICS,
        use_role=DataUseRole.MECHANISTIC_SUPPORT,
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
        missing_fraction=0.0,
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
    values.update(overrides)
    return DataFitnessProfile(**values)


def mechanistic_omics_metadata():
    return OmicsMetadata(
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


def dimension_map(report):
    return {d.dimension.value: d.grade.value for d in report.dimensions}


def main() -> None:
    selected = base_profile()

    # General G3 alone must not authorize an omics dataset.
    without_omics = evaluate_layered_data_fitness(selected)
    assert without_omics.general_grade is DataFitnessGrade.PASS
    assert without_omics.layered_grade is DataFitnessGrade.CONDITIONAL
    assert "run:g3_omics" in without_omics.repair_actions

    # The selected v0.6 hybrid-route public omics role is mechanistic support.
    # A mechanistically compatible C grade is sufficient for that calibrated
    # role after General G3 passes, but is not direct validation.
    court = data_fitness_court(
        [selected],
        omics_metadata_by_dataset={selected.dataset_id: mechanistic_omics_metadata()},
    )
    assert court.status is DataFitnessStatus.ADVANCE
    assert court.advancement_allowed is True
    report = court.reports[0]
    assert report.general_grade is DataFitnessGrade.PASS
    assert report.omics_fitness is OmicsFitness.C
    assert report.layered_grade is DataFitnessGrade.PASS

    # Adversarial attack 1: legal/reuse failure must override otherwise good data.
    illegal = evaluate_layered_data_fitness(
        base_profile(dataset_id="illegal", legal_reuse_permitted=False),
        omics_fitness=OmicsFitness.C,
    )
    assert illegal.layered_grade is DataFitnessGrade.FAIL
    assert next(d for d in illegal.dimensions if d.dimension is DataFitnessDimension.LEGAL_REUSE).grade is DataFitnessGrade.FAIL

    # Adversarial attack 2: an omics C dataset cannot be relabeled as a direct
    # primary test merely because the general data layer is clean.
    overclaim = evaluate_layered_data_fitness(
        base_profile(dataset_id="overclaim", use_role=DataUseRole.PRIMARY_TEST),
        omics_fitness=OmicsFitness.C,
    )
    assert overclaim.general_grade is DataFitnessGrade.PASS
    assert overclaim.layered_grade is DataFitnessGrade.CONDITIONAL
    assert "calibrate:omics_claim_role" in overclaim.repair_actions

    # Adversarial attack 3: a direct primary dataset with an unidentifiable
    # estimand and incomplete join cannot be rescued by good provenance.
    bad_primary = evaluate_layered_data_fitness(base_profile(
        dataset_id="bad_primary",
        domain=DataDomain.GENERIC,
        use_role=DataUseRole.PRIMARY_TEST,
        requires_join=True,
        stable_join_keys=True,
        join_coverage_fraction=0.80,
        target_estimand_identifiable=False,
    ))
    assert bad_primary.layered_grade is DataFitnessGrade.FAIL

    # Physical-only routes with no pre-existing external data do not fabricate a
    # dataset to satisfy G3; their acquisition schema is handled in Design.
    physical_no_existing = data_fitness_court([], route_requires_existing_data=False)
    assert physical_no_existing.status is DataFitnessStatus.ADVANCE

    payload = {
        "scenario_id": "v07_general_g3_hybrid_route_capability",
        "capability_only": True,
        "selected_route": "hybrid_nonmolecular_plus_public_omics",
        "selected_public_data_role": selected.use_role.value,
        "general_g3_dimensions": [d.value for d in DataFitnessDimension if d is not DataFitnessDimension.DOMAIN_GATE],
        "selected_dataset": {
            "dataset_id": report.dataset_id,
            "general_grade": report.general_grade.value,
            "omics_grade": report.omics_fitness.value if report.omics_fitness else None,
            "layered_grade": report.layered_grade.value,
            "dimension_grades": dimension_map(report),
            "claim_boundary": "mechanistic_support_only_not_direct_validation",
        },
        "attacks": {
            "general_g3_without_g3_omics": without_omics.layered_grade.value,
            "illegal_reuse": illegal.layered_grade.value,
            "omics_c_direct_overclaim": overclaim.layered_grade.value,
            "bad_join_and_unidentifiable_primary": bad_primary.layered_grade.value,
            "physical_route_without_existing_data": physical_no_existing.status.value,
        },
        "court_status": court.status.value,
        "advancement_allowed": court.advancement_allowed,
        "next_gate": "design",
    }
    Path("data_fitness_capability.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
