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
from agri_coscientist.dataset_freeze import (
    DatasetFreezePlan,
    build_dataset_freeze as build_dataset_freeze_object,
    dataset_freeze_court,
)
from agri_coscientist.state import ProjectState, Stage, StudyMode
from dataset_freeze_capability import build_design, physical_asset, public_asset


def build_freezes():
    _, design_freeze = build_design()
    retained = tuple(f"pot-{i:02d}" for i in range(1, 13))
    dataset_plan = DatasetFreezePlan(
        freeze_id="wheat-hybrid-dataset-freeze-v1",
        design_freeze_sha256=design_freeze.design_freeze_sha256,
        mode=StudyMode.HYBRID,
        assets=(physical_asset(), public_asset()),
        retained_independent_unit_ids=retained,
        outcome_values_inspected_before_freeze=False,
    )
    result = dataset_freeze_court(dataset_plan, design_freeze)
    return design_freeze, build_dataset_freeze_object(dataset_plan, design_freeze, result)


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
        planned_use_binding="prespecified root mechanical-stress contrast for mechanistic context only",
        direct_validation_claim=False,
    )
    values.update(overrides)
    return AnalysisTask(**values)


def base_plan(design_freeze, dataset_freeze):
    return AnalysisSpecificationPlan(
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


def main():
    design_freeze, dataset_freeze = build_freezes()
    plan = base_plan(design_freeze, dataset_freeze)
    court = analysis_specification_court(plan, design_freeze, dataset_freeze)
    frozen_spec = build_analysis_specification(plan, design_freeze, dataset_freeze, court)
    lock = build_analysis_lock(frozen_spec)

    attack_plans = {
        "outcome_peeking": replace(plan, outcome_values_inspected_before_specification=True),
        "wrong_dataset_binding": replace(plan, dataset_freeze_sha256="9" * 64),
        "technical_unit_pseudoreplication": replace(plan, tasks=(physical_primary(unit_of_analysis="technical assay well"), public_mechanistic())),
        "lost_blocking": replace(plan, tasks=(physical_primary(adjustment_terms=()), public_mechanistic())),
        "postfreeze_exclusion_change": replace(plan, tasks=(physical_primary(exclusion_policy="drop model outliers"), public_mechanistic())),
        "data_dependent_method_selection": replace(plan, tasks=(physical_primary(data_dependent_method_selection=True), public_mechanistic())),
        "public_role_promotion": replace(plan, tasks=(physical_primary(), public_mechanistic(public_data_role=DataUseRole.PRIMARY_TEST))),
        "public_direct_validation_overreach": replace(plan, tasks=(physical_primary(), public_mechanistic(direct_validation_claim=True))),
        "unpinned_analysis_engine": replace(plan, tasks=(physical_primary(engine_package="unversioned-engine"), public_mechanistic())),
        "missing_primary_analysis": replace(plan, tasks=(replace(physical_primary(), confirmatory=False), public_mechanistic())),
    }
    attacks = {
        name: analysis_specification_court(attack_plan, design_freeze, dataset_freeze).status.value
        for name, attack_plan in attack_plans.items()
    }

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
