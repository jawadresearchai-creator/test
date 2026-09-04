from __future__ import annotations

from dataclasses import replace
import json

from agri_coscientist.analysis_specification import (
    AnalysisSpecificationPlan,
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
from agri_coscientist.data_fitness import DataUseRole
from agri_coscientist.dataset_freeze import DatasetFreezePlan, build_dataset_freeze, dataset_freeze_court
from agri_coscientist.state import ProjectState, Stage, StudyMode
from dataset_freeze_capability import build_design, physical_asset, public_asset


def build_dataset_freeze():
    _, design_freeze = build_design()
    retained = tuple(f"pot-{i:02d}" for i in range(1, 13))
    plan = DatasetFreezePlan(
        freeze_id="wheat-hybrid-dataset-freeze-v1",
        design_freeze_sha256=design_freeze.design_freeze_sha256,
        mode=StudyMode.HYBRID,
        assets=(physical_asset(), public_asset()),
        retained_independent_unit_ids=retained,
        outcome_values_inspected_before_freeze=False,
    )
    result = dataset_freeze_court(plan, design_freeze)
    return design_freeze, build_dataset_freeze_object(plan, design_freeze, result)


def build_dataset_freeze_object(plan, design_freeze, result):
    return build_dataset_freeze(plan, design_freeze, result)


def runtimes():
    return (
        RuntimeSpec(
            runtime_id="python-confirmatory",
            language="Python",
            language_version="3.12.14",
            packages=(PackagePin("statsmodels", "0.15.0"),),
        ),
        RuntimeSpec(
            runtime_id="r-public-omics",
            language="R",
            language_version="4.6.1",
            packages=(PackagePin("DESeq2", "1.52.0"),),
        ),
    )


def physical_primary(**overrides):
    values = dict(
        task_id="physical-primary-injury",
        component="physical",
        target_name="challenge oxidative injury",
        design_outcome="challenge oxidative injury",
        confirmatory=True,
        estimand="adjusted average cue-versus-mock effect on post-challenge oxidative injury",
        contrast="mechanical-cue exposure minus mock cue exposure",
        model_family="linear model with prespecified block adjustment",
        model_formula="challenge_oxidative_injury ~ treatment_code + bench_position",
        unit_of_analysis="one independently grown wheat pot containing one receiver plant",
        dependency_structure="independent experimental units with prespecified bench-position block adjustment",
        adjustment_terms=("bench_position",),
        transformation_rule="none on primary scale unless the prespecified diagnostic-triggered fallback is activated",
        missing_data_policy="retain Dataset-Freeze unit accounting; report outcome missingness; no significance-driven deletion or imputation",
        exclusion_policy="dataset_freeze_only",
        multiplicity_family="physical_primary",
        multiplicity_method=MultiplicityMethod.NONE,
        alpha=0.05,
        confidence_level=0.95,
        effect_measure="adjusted mean difference with 95% confidence interval",
        diagnostics=("residual distribution", "variance structure", "influence diagnostics without deletion"),
        fallback_rules=("if heteroskedasticity is detected by the prespecified diagnostic, retain the estimand/model terms and use HC3 robust covariance",),
        runtime_id="python-confirmatory",
        engine_package="statsmodels",
        implementation_entrypoint="scripts/analysis/physical_primary.py",
        execution_order=1,
    )
    values.update(overrides)
    return AnalysisTask(**values)


def public_mechanistic(**overrides):
    planned = "prespecified root mechanical-stress contrast for mechanistic context only"
    values = dict(
        task_id="public-omics-mechanistic",
        component="public_wheat_root_mechanical_context",
        target_name="prespecified public root transcriptome mechanical-stress contrast",
        design_outcome=None,
        confirmatory=False,
        estimand="source-study log2 fold change for the prespecified mechanical-stress contrast",
        contrast="mechanical stress versus source-study control",
        model_family="DESeq2 negative-binomial count model",
        model_formula="count ~ source_condition",
        unit_of_analysis="independent root biological sample",
        dependency_structure="independent source-study biological samples",
        adjustment_terms=(),
        transformation_rule="fit raw integer counts; transformed values may be used only for diagnostics/visualization",
        missing_data_policy="no sample/gene removal based on effect direction or statistical significance",
        exclusion_policy="dataset_freeze_only",
        multiplicity_family="public_omics",
        multiplicity_method=MultiplicityMethod.BH_FDR,
        alpha=0.05,
        confidence_level=0.95,
        effect_measure="log2 fold change with interval and FDR-adjusted evidence",
        diagnostics=("library-size QC", "dispersion fit", "sample-level count diagnostics"),
        fallback_rules=("model failure returns to Analysis Specification; no silent substitution of a different differential-expression method",),
        runtime_id="r-public-omics",
        engine_package="DESeq2",
        implementation_entrypoint="scripts/analysis/public_mechanistic.R",
        execution_order=2,
        public_data_role=DataUseRole.MECHANISTIC_SUPPORT,
        planned_use_binding=planned,
        direct_validation_claim=False,
    )
    values.update(overrides)
    return AnalysisTask(**values)


def main():
    design_freeze, dataset_freeze = build_dataset_freeze()
    plan = AnalysisSpecificationPlan(
        specification_id="wheat-hybrid-analysis-specification-v1",
        design_freeze_sha256=design_freeze.design_freeze_sha256,
        dataset_freeze_sha256=dataset_freeze.dataset_freeze_sha256,
        mode=StudyMode.HYBRID,
        runtimes=runtimes(),
        tasks=(physical_primary(), public_mechanistic()),
        random_seed=20260904,
        outcome_values_inspected_before_specification=False,
        notes=("public omics remains independent mechanistic support only",),
    )
    court = analysis_specification_court(plan, design_freeze, dataset_freeze)
    frozen_spec = build_analysis_specification(plan, design_freeze, dataset_freeze, court)
    lock = build_analysis_lock(frozen_spec)

    attacks = {}
    attacks["outcome_peeking"] = analysis_specification_court(
        replace(plan, outcome_values_inspected_before_specification=True), design_freeze, dataset_freeze
    ).status.value
    attacks["wrong_dataset_binding"] = analysis_specification_court(
        replace(plan, dataset_freeze_sha256="9" * 64), design_freeze, dataset_freeze
    ).status.value
    attacks["technical_unit_pseudoreplication"] = analysis_specification_court(
        replace(plan, tasks=(physical_primary(unit_of_analysis="technical assay well"), public_mechanistic())),
        design_freeze, dataset_freeze,
    ).status.value
    attacks["lost_blocking"] = analysis_specification_court(
        replace(plan, tasks=(physical_primary(adjustment_terms=()), public_mechanistic())),
        design_freeze, dataset_freeze,
    ).status.value
    attacks["postfreeze_exclusion_change"] = analysis_specification_court(
        replace(plan, tasks=(physical_primary(exclusion_policy="drop model outliers"), public_mechanistic())),
        design_freeze, dataset_freeze,
    ).status.value
    attacks["data_dependent_method_selection"] = analysis_specification_court(
        replace(plan, tasks=(physical_primary(data_dependent_method_selection=True), public_mechanistic())),
        design_freeze, dataset_freeze,
    ).status.value
    attacks["public_role_promotion"] = analysis_specification_court(
        replace(plan, tasks=(physical_primary(), public_mechanistic(public_data_role=DataUseRole.PRIMARY_TEST))),
        design_freeze, dataset_freeze,
    ).status.value
    attacks["public_direct_validation_overreach"] = analysis_specification_court(
        replace(plan, tasks=(physical_primary(), public_mechanistic(direct_validation_claim=True))),
        design_freeze, dataset_freeze,
    ).status.value
    attacks["unpinned_analysis_engine"] = analysis_specification_court(
        replace(plan, tasks=(physical_primary(engine_package="unversioned-engine"), public_mechanistic())),
        design_freeze, dataset_freeze,
    ).status.value
    attacks["missing_primary_analysis"] = analysis_specification_court(
        replace(plan, tasks=(replace(physical_primary(), confirmatory=False), public_mechanistic())),
        design_freeze, dataset_freeze,
    ).status.value

    state = ProjectState("analysis-specification-capability")
    state.stage = Stage.DATASET_FROZEN
    enter_project_analysis_specification(state, frozen_spec)
    state_after_specification = state.stage.value
    state_lock = lock_project_analysis(state, frozen_spec)

    payload = {
        "scenario": "v10_analysis_specification_and_lock_hybrid_capability",
        "court_status": court.status.value,
        "advancement_allowed": court.advancement_allowed,
        "design_freeze_sha256": design_freeze.design_freeze_sha256,
        "dataset_freeze_sha256": dataset_freeze.dataset_freeze_sha256,
        "analysis_specification_sha256": frozen_spec.specification_sha256,
        "analysis_lock_sha256": lock.analysis_lock_sha256,
        "deterministic_specification_hash": frozen_spec.specification_sha256 == build_analysis_specification(plan, design_freeze, dataset_freeze, court).specification_sha256,
        "deterministic_lock_hash": lock.analysis_lock_sha256 == build_analysis_lock(frozen_spec).analysis_lock_sha256,
        "pre_outcome": frozen_spec.pre_outcome,
        "analysis_specification_locked_before_lock": frozen_spec.analysis_specification_locked,
        "analysis_model_locked_before_lock": frozen_spec.analysis_model_locked,
        "analysis_specification_locked_after_lock": lock.analysis_specification_locked,
        "analysis_model_locked_after_lock": lock.analysis_model_locked,
        "state_after_specification": state_after_specification,
        "state_after_lock": state.stage.value,
        "state_lock_hash_matches": state_lock.analysis_lock_sha256 == lock.analysis_lock_sha256,
        "physical_primary": {
            "unit_of_analysis": physical_primary().unit_of_analysis,
            "block_adjustment": list(physical_primary().adjustment_terms),
            "engine": "statsmodels 0.15.0 / Python 3.12.14",
        },
        "public_omics": {
            "role": public_mechanistic().public_data_role.value,
            "direct_validation_claim": public_mechanistic().direct_validation_claim,
            "engine": "DESeq2 1.52.0 / R 4.6.1",
        },
        "attacks": attacks,
        "claim_boundary": "statistical_prespecification_and_lock_capability_only_not_model_execution_or_biological_validation",
    }
    with open("analysis_specification_capability.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
