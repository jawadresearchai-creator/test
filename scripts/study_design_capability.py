from __future__ import annotations

import json
from pathlib import Path

from agri_coscientist.data_fitness import DataFitnessGrade, DataUseRole
from agri_coscientist.design import (
    AllocationMethod,
    DesignStatus,
    InferenceIntent,
    OutcomeSpec,
    OutcomeTier,
    PhysicalDesign,
    PublicDatasetDesign,
    StudyDesign,
    build_design_freeze,
    design_court,
)
from agri_coscientist.state import StudyMode


def physical(**overrides):
    values = dict(
        experimental_unit="one independently grown wheat pot containing one focal receiver plant",
        analysis_unit_matches_experimental_unit=True,
        independent_units_total=12,
        independent_units_per_group=(6, 6),
        replication_rationale="independent pots represent biological experimental units; subsamples do not increase biological n",
        precision_or_power_plan="freeze final n before acquisition using pilot variance or precision around a minimally important primary-outcome effect",
        treatments=("mechanical root-cue exposure",),
        controls=("mock cue exposure",),
        manipulated_exposure=True,
        allocation_method=AllocationMethod.BLOCK_RANDOMIZED,
        randomization_plan="seeded random assignment within prespecified bench-position blocks with allocation ledger frozen before treatment",
        nuisance_gradient_expected=True,
        blocking_factors=("bench_position",),
        blocking_plan="define spatial blocks before randomization and retain block ID as acquisition metadata",
        subsamples_per_unit=2,
        subsamples_treated_as_technical=True,
        repeated_measures=False,
        repeated_measure_unit_id_preserved=True,
        destructive_sampling=False,
        independent_units_per_destructive_timepoint=True,
        sampling_schedule=("baseline", "30 min after cue", "post-compaction challenge"),
        required_methods=("extracellular ATP assay", "antioxidant enzyme assay", "root phenotyping"),
        unavailable_methods=("qPCR", "RT-qPCR", "RNA-seq", "new wet-lab transcriptomics"),
        blinding_feasible=True,
        blinded_outcome_assessment=True,
        blinding_plan="coded samples and images remain masked through primary measurement QC",
    )
    values.update(overrides)
    return PhysicalDesign(**values)


def public(**overrides):
    values = dict(
        dataset_id="public_wheat_root_mechanical_context",
        role=DataUseRole.MECHANISTIC_SUPPORT,
        layered_data_fitness=DataFitnessGrade.PASS,
        source_design_understood=True,
        source_experimental_or_sampling_unit="independent root biological sample",
        sample_independence_known=True,
        planned_use_or_contrast="prespecified mechanical-stress/root contrast for independent mechanistic context only",
        supports_causal_identification=False,
        result_level_outcomes_accessed_before_design_freeze=False,
    )
    values.update(overrides)
    return PublicDatasetDesign(**values)


def selected_design(**overrides):
    values = dict(
        design_id="v08_hybrid_nonmolecular_plus_public_omics_design",
        question="Does randomized mechanical root-cue exposure prime wheat receivers against a later compaction challenge, with public omics used only as independent mechanistic context?",
        hypotheses=(
            "randomized cue exposure changes the prespecified primary post-challenge oxidative-injury outcome",
            "public root transcriptomes may provide convergent mechanistic context but do not directly validate the experimental units",
        ),
        mode=StudyMode.HYBRID,
        inference_intent=InferenceIntent.CAUSAL,
        confirmatory=True,
        outcomes=(
            OutcomeSpec("challenge oxidative injury", OutcomeTier.PRIMARY, "lipid peroxidation assay", "post-compaction challenge", "nmol g-1 FW"),
            OutcomeSpec("receiver root growth", OutcomeTier.SECONDARY, "image-based root phenotyping", "post-compaction challenge", "cm"),
            OutcomeSpec("extracellular ATP", OutcomeTier.MECHANISTIC, "luciferase ATP assay", "30 min after cue", "relative ATP concentration"),
            OutcomeSpec("assay spike recovery", OutcomeTier.QC, "spike-recovery QC", "each assay batch", "%"),
        ),
        covariates=("initial plant size",),
        metadata_fields=("pot_id", "block_id", "treatment_code", "sampling_time", "assay_batch"),
        exclusion_criteria=("exclude only prespecified catastrophic unit loss before treatment; otherwise retain and report",),
        quality_controls=("assay blanks", "spike recovery", "coded image QC"),
        physical=physical(),
        public_datasets=(public(),),
        outcome_data_accessed_before_design_freeze=False,
        notes=("new wet-lab gene-expression assays are not required", "public omics role is mechanistic support only"),
    )
    values.update(overrides)
    return StudyDesign(**values)


def court_status(design):
    return design_court(design).status.value


def main() -> None:
    design = selected_design()
    court = design_court(design)
    assert court.status is DesignStatus.ADVANCE
    freeze = build_design_freeze(design, court)
    assert freeze.pre_outcome is True
    assert freeze.analysis_model_locked is False

    # Attack 1: technical subsamples cannot create independent replication.
    p_pseudo = physical(analysis_unit_matches_experimental_unit=False, subsamples_per_unit=12)
    pseudorep = selected_design(physical=p_pseudo)
    assert design_court(pseudorep).status is DesignStatus.BLOCKED

    # Attack 2: unavailable new RNA-seq cannot be reintroduced as required wet-lab work.
    p_omics = physical(required_methods=("extracellular ATP assay", "RNA-seq"))
    unavailable = selected_design(physical=p_omics)
    assert design_court(unavailable).status is DesignStatus.BLOCKED

    # Attack 3: causal wording cannot survive nonrandom assignment.
    p_nonrandom = physical(allocation_method=AllocationMethod.NONRANDOM)
    nonrandom = selected_design(physical=p_nonrandom)
    assert design_court(nonrandom).status is DesignStatus.BLOCKED

    # Attack 4: route-required public data cannot bypass layered Data Fitness.
    weak_public = selected_design(public_datasets=(public(layered_data_fitness=DataFitnessGrade.CONDITIONAL),))
    assert design_court(weak_public).status is DesignStatus.BLOCKED

    # Attack 5: result/outcome peeking before confirmatory Design Freeze invalidates the confirmatory boundary.
    peeked = selected_design(outcome_data_accessed_before_design_freeze=True)
    assert design_court(peeked).status is DesignStatus.BLOCKED

    # Attack 6: known nuisance gradients require blocking.
    no_block = selected_design(physical=physical(blocking_factors=(), blocking_plan=""))
    assert design_court(no_block).status is DesignStatus.BLOCKED

    payload = {
        "scenario_id": "v08_study_design_freeze_capability",
        "capability_only": True,
        "route": design.mode.value,
        "inference_intent": design.inference_intent.value,
        "court_status": court.status.value,
        "advancement_allowed": court.advancement_allowed,
        "physical": {
            "experimental_unit": design.physical.experimental_unit if design.physical else None,
            "independent_units_total": design.physical.independent_units_total if design.physical else None,
            "independent_units_per_group": list(design.physical.independent_units_per_group) if design.physical else [],
            "allocation": design.physical.allocation_method.value if design.physical else None,
            "blocking_factors": list(design.physical.blocking_factors) if design.physical else [],
            "required_methods": list(design.physical.required_methods) if design.physical else [],
            "unavailable_methods": list(design.physical.unavailable_methods) if design.physical else [],
        },
        "public_data": [
            {
                "dataset_id": d.dataset_id,
                "role": d.role.value,
                "layered_data_fitness": d.layered_data_fitness.value,
                "claim_boundary": "mechanistic_support_only_not_direct_validation",
            }
            for d in design.public_datasets
        ],
        "primary_outcomes": [o.name for o in design.outcomes if o.tier is OutcomeTier.PRIMARY],
        "design_freeze": {
            "sha256": freeze.design_freeze_sha256,
            "pre_outcome": freeze.pre_outcome,
            "analysis_model_locked": freeze.analysis_model_locked,
        },
        "attacks": {
            "pseudoreplication": court_status(pseudorep),
            "unavailable_wetlab_omics_required": court_status(unavailable),
            "nonrandom_causal_claim": court_status(nonrandom),
            "public_data_without_layered_g3_pass": court_status(weak_public),
            "confirmatory_outcome_peeking": court_status(peeked),
            "known_gradient_without_blocking": court_status(no_block),
        },
        "next_gate": "analysis_specification_then_analysis_lock",
    }
    Path("study_design_capability.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
