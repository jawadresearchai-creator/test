from __future__ import annotations

from dataclasses import replace
import json

from agri_coscientist.data_fitness import DataFitnessGrade, DataUseRole
from agri_coscientist.dataset_freeze import (
    AssetRole,
    DataOrigin,
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


def build_design():
    physical = PhysicalDesign(
        experimental_unit="one independently grown wheat pot containing one receiver plant",
        analysis_unit_matches_experimental_unit=True,
        independent_units_total=12,
        independent_units_per_group=(6, 6),
        replication_rationale="independent pots estimate between-unit biological variation",
        precision_or_power_plan="final n frozen before acquisition using precision/effect planning",
        treatments=("mechanical-cue exposure",),
        controls=("mock cue exposure",),
        manipulated_exposure=True,
        allocation_method=AllocationMethod.BLOCK_RANDOMIZED,
        randomization_plan="seeded allocation within predeclared bench-position blocks",
        nuisance_gradient_expected=True,
        blocking_factors=("bench_position",),
        blocking_plan="construct blocks before treatment and preserve block IDs",
        subsamples_per_unit=2,
        subsamples_treated_as_technical=True,
        repeated_measures=False,
        repeated_measure_unit_id_preserved=True,
        destructive_sampling=False,
        independent_units_per_destructive_timepoint=True,
        sampling_schedule=("baseline", "30 min after cue", "post-challenge"),
        required_methods=("extracellular ATP assay", "root phenotyping", "antioxidant enzyme assay"),
        unavailable_methods=("qPCR", "RT-qPCR", "RNA-seq", "new wet-lab transcriptomics"),
        blinding_feasible=True,
        blinded_outcome_assessment=True,
        blinding_plan="coded samples/images through measurement and QC",
    )
    public = PublicDatasetDesign(
        dataset_id="public_wheat_root_mechanical_context",
        role=DataUseRole.MECHANISTIC_SUPPORT,
        layered_data_fitness=DataFitnessGrade.PASS,
        source_design_understood=True,
        source_experimental_or_sampling_unit="independent root biological sample",
        sample_independence_known=True,
        planned_use_or_contrast="prespecified root mechanical-stress contrast for mechanistic context only",
        supports_causal_identification=False,
    )
    design = StudyDesign(
        design_id="wheat_hybrid_dataset_freeze_capability_v1",
        question="Does randomized mechanical-cue exposure prime receiver wheat against later compaction, with public omics used only as independent mechanistic context?",
        hypotheses=("cue exposure changes the prespecified post-challenge injury outcome",),
        mode=StudyMode.HYBRID,
        inference_intent=InferenceIntent.CAUSAL,
        confirmatory=True,
        outcomes=(
            OutcomeSpec("challenge oxidative injury", OutcomeTier.PRIMARY, "lipid peroxidation assay", "post-challenge"),
            OutcomeSpec("receiver root growth", OutcomeTier.SECONDARY, "image root phenotyping", "post-challenge"),
            OutcomeSpec("extracellular ATP", OutcomeTier.MECHANISTIC, "luciferase ATP assay", "30 min after cue"),
        ),
        covariates=("initial plant size",),
        metadata_fields=("pot_id", "block_id", "treatment_code", "sampling_time", "assay_batch"),
        exclusion_criteria=("catastrophic independent-unit loss before treatment",),
        quality_controls=("assay blanks", "spike recovery", "coded image QC"),
        physical=physical,
        public_datasets=(public,),
        notes=("public omics remains mechanistic support only",),
    )
    return design, build_design_freeze(design, design_court(design))


def physical_asset():
    return FrozenDataAsset(
        asset_id="physical-acquisition-table",
        origin=DataOrigin.PROJECT_GENERATED,
        role=AssetRole.DATA,
        sha256="1" * 64,
        bytes=48192,
        locator="drive://project/wheat_physical_acquisition.csv",
        representation="csv",
        schema_fields=(
            "challenge oxidative injury", "receiver root growth", "extracellular ATP",
            "initial plant size", "pot_id", "block_id", "treatment_code",
            "sampling_time", "assay_batch", "bench_position",
        ),
        sample_ids=tuple(f"pot-{i:02d}" for i in range(1, 13)),
    )


def public_asset(dataset_id="public_wheat_root_mechanical_context", version="GEO-accession+asset-sha256-v1"):
    return FrozenDataAsset(
        asset_id=f"public-omics-{dataset_id}",
        origin=DataOrigin.PUBLIC_REUSED,
        role=AssetRole.DATA,
        sha256="2" * 64,
        bytes=993280,
        locator="https://example.invalid/frozen-public-asset",
        representation="featurecounts_integer_counts",
        source_dataset_id=dataset_id,
        source_version=version,
        sample_ids=("pub-1", "pub-2", "pub-3", "pub-4", "pub-5", "pub-6"),
    )


def main():
    design, design_freeze = build_design()
    retained = tuple(f"pot-{i:02d}" for i in range(1, 13))
    plan = DatasetFreezePlan(
        freeze_id="wheat-hybrid-dataset-freeze-v1",
        design_freeze_sha256=design_freeze.design_freeze_sha256,
        mode=StudyMode.HYBRID,
        assets=(physical_asset(), public_asset()),
        retained_independent_unit_ids=retained,
        outcome_values_inspected_before_freeze=False,
        notes=("byte hashing and schema/sample identity only before confirmatory outcome analysis",),
    )
    result = dataset_freeze_court(plan, design_freeze)
    frozen = build_dataset_freeze(plan, design_freeze, result)

    attacks = {}
    attacks["outcome_peeking"] = dataset_freeze_court(
        replace(plan, outcome_values_inspected_before_freeze=True), design_freeze
    ).status.value
    attacks["missing_public_dataset"] = dataset_freeze_court(
        replace(plan, assets=(physical_asset(),)), design_freeze
    ).status.value
    attacks["undeclared_public_dataset"] = dataset_freeze_court(
        replace(plan, assets=(physical_asset(), public_asset("undeclared-public"))), design_freeze
    ).status.value
    attacks["missing_public_version"] = dataset_freeze_court(
        replace(plan, assets=(physical_asset(), public_asset(version=""))), design_freeze
    ).status.value
    attacks["unit_accounting_mismatch"] = dataset_freeze_court(
        replace(plan, retained_independent_unit_ids=retained[:-1]), design_freeze
    ).status.value
    attacks["posthoc_exclusion"] = dataset_freeze_court(
        replace(
            plan,
            retained_independent_unit_ids=retained[:-1],
            exclusions=(ExclusionRecord(retained[-1], "excluded after seeing an extreme outcome"),),
        ),
        design_freeze,
    ).status.value
    attacks["missing_prespecified_schema_field"] = dataset_freeze_court(
        replace(plan, assets=(replace(physical_asset(), schema_fields=("pot_id", "block_id")), public_asset())),
        design_freeze,
    ).status.value
    attacks["missing_blocking_factor_schema_field"] = dataset_freeze_court(
        replace(
            plan,
            assets=(
                replace(
                    physical_asset(),
                    schema_fields=tuple(x for x in physical_asset().schema_fields if x != "bench_position"),
                ),
                public_asset(),
            ),
        ),
        design_freeze,
    ).status.value
    attacks["wrong_design_binding"] = dataset_freeze_court(
        replace(plan, design_freeze_sha256="3" * 64), design_freeze
    ).status.value

    state = ProjectState("dataset-freeze-capability")
    state.stage = Stage.DESIGN_FROZEN
    state_freeze = freeze_project_dataset(state, plan, design_freeze, result)
    direct_analysis_lock_blocked = False
    try:
        state.transition(Stage.ANALYSIS_LOCKED, "illegal skip")
    except ValueError:
        direct_analysis_lock_blocked = True

    payload = {
        "scenario": "v101_general_project_dataset_freeze_blocking_factor_repair",
        "court_status": result.status.value,
        "advancement_allowed": result.advancement_allowed,
        "design_freeze_sha256": design_freeze.design_freeze_sha256,
        "dataset_freeze_sha256": frozen.dataset_freeze_sha256,
        "deterministic_hash": frozen.dataset_freeze_sha256 == build_dataset_freeze(plan, design_freeze, result).dataset_freeze_sha256,
        "route": plan.mode.value,
        "assets": {
            "project_generated": 1,
            "public_reused": 1,
            "public_role": "mechanistic_support_only_not_direct_validation",
            "frozen_blocking_factors": ["bench_position"],
        },
        "independent_units": {"planned": 12, "retained": 12, "excluded": 0},
        "confirmatory_outcome_blind": frozen.confirmatory_outcome_blind,
        "analysis_specification_locked": frozen.analysis_specification_locked,
        "analysis_model_locked": frozen.analysis_model_locked,
        "state_after_freeze": state.stage.value,
        "direct_dataset_frozen_to_analysis_locked_blocked": direct_analysis_lock_blocked,
        "next_explicit_state": Stage.ANALYSIS_SPECIFICATION.value,
        "attacks": attacks,
        "claim_boundary": "dataset_identity_and_executable_design_field_provenance_only_not_analysis_or_biological_validation",
        "state_freeze_hash_matches": state_freeze.dataset_freeze_sha256 == frozen.dataset_freeze_sha256,
    }
    with open("dataset_freeze_capability.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
