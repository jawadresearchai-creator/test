from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from .blockers import BlockerGate
from .gates import OmicsFitness, OmicsMetadata, grade_omics_fitness


class DataFitnessGrade(str, Enum):
    PASS = "pass"
    CONDITIONAL = "conditional"
    FAIL = "fail"


class DataFitnessStatus(str, Enum):
    ADVANCE = "advance"
    REVISE = "revise"
    BLOCKED = "blocked"


class DataDomain(str, Enum):
    GENERIC = "generic"
    OMICS = "omics"


class DataUseRole(str, Enum):
    PRIMARY_TEST = "primary_test"
    MECHANISTIC_SUPPORT = "mechanistic_support"
    CONTEXTUAL = "contextual"
    HYPOTHESIS_GENERATION = "hypothesis_generation"


class DataFitnessDimension(str, Enum):
    LEGAL_REUSE = "legal_reuse"
    PROVENANCE = "provenance"
    POPULATION_GEOGRAPHY = "population_geography"
    TEMPORAL_FIT = "temporal_fit"
    CONSTRUCT_VALIDITY = "construct_validity"
    QUALITY = "quality"
    COVERAGE = "coverage"
    MISSINGNESS = "missingness"
    VARIATION = "variation"
    JOINABILITY = "joinability"
    IDENTIFIABILITY = "identifiability"
    SELECTION_BIAS = "selection_bias"
    UNIT_CONSISTENCY = "unit_consistency"
    INDEPENDENCE = "sample_independence"
    REPRODUCIBILITY = "reproducibility"
    DOMAIN_GATE = "domain_gate"


@dataclass(frozen=True)
class DataFitnessPolicy:
    """Predeclared General-G3 thresholds; project policy may be stricter."""

    min_primary_coverage: float = 0.95
    min_supporting_coverage: float = 0.80
    max_primary_missing_fraction: float = 0.10
    max_supporting_missing_fraction: float = 0.25
    min_primary_join_fraction: float = 0.95
    min_supporting_join_fraction: float = 0.85

    def __post_init__(self) -> None:
        values = {
            "min_primary_coverage": self.min_primary_coverage,
            "min_supporting_coverage": self.min_supporting_coverage,
            "max_primary_missing_fraction": self.max_primary_missing_fraction,
            "max_supporting_missing_fraction": self.max_supporting_missing_fraction,
            "min_primary_join_fraction": self.min_primary_join_fraction,
            "min_supporting_join_fraction": self.min_supporting_join_fraction,
        }
        for name, value in values.items():
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.min_primary_coverage < self.min_supporting_coverage:
            raise ValueError("primary coverage threshold cannot be weaker than supporting threshold")
        if self.max_primary_missing_fraction > self.max_supporting_missing_fraction:
            raise ValueError("primary missingness threshold cannot be weaker than supporting threshold")
        if self.min_primary_join_fraction < self.min_supporting_join_fraction:
            raise ValueError("primary join threshold cannot be weaker than supporting threshold")


@dataclass(frozen=True)
class DataFitnessProfile:
    dataset_id: str
    domain: DataDomain
    use_role: DataUseRole

    legal_reuse_permitted: bool
    provenance_traceable: bool
    source_identity_known: bool
    reproducible_acquisition: bool
    source_versioned_or_freezeable: bool

    population_fit: bool
    geography_fit: bool
    temporal_fit: bool
    construct_valid: bool
    measurement_valid: bool

    quality_documented: bool
    critical_qc_pass: bool
    required_fields_present: bool
    coverage_fraction: float
    missing_fraction: float
    missingness_characterized: bool
    missingness_strategy_available: bool

    outcome_or_key_variation_present: bool
    requires_join: bool = False
    stable_join_keys: bool = True
    join_coverage_fraction: float = 1.0

    target_estimand_identifiable: bool = True
    required_confounders_available: bool = True
    severe_selection_bias: bool = False
    selection_bias_addressable: bool = True
    survivorship_bias_present: bool = False
    survivorship_bias_addressable: bool = True
    sample_independence_known: bool = True

    units_known: bool = True
    units_harmonized: bool = True
    units_harmonizable: bool = True

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise ValueError("dataset_id is required")
        for name, value in (
            ("coverage_fraction", self.coverage_fraction),
            ("missing_fraction", self.missing_fraction),
            ("join_coverage_fraction", self.join_coverage_fraction),
        ):
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if not self.requires_join and self.join_coverage_fraction != 1.0:
            raise ValueError("join_coverage_fraction must be 1.0 when requires_join=false")


@dataclass(frozen=True)
class DimensionAssessment:
    dimension: DataFitnessDimension
    grade: DataFitnessGrade
    reasons: tuple[str, ...] = ()
    repair_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class DatasetFitnessReport:
    dataset_id: str
    domain: DataDomain
    use_role: DataUseRole
    general_grade: DataFitnessGrade
    dimensions: tuple[DimensionAssessment, ...]
    repair_actions: tuple[str, ...]
    omics_fitness: OmicsFitness | None
    layered_grade: DataFitnessGrade
    advancement_allowed: bool


@dataclass(frozen=True)
class DataFitnessCourtResult:
    status: DataFitnessStatus
    reports: tuple[DatasetFitnessReport, ...]
    passed_dataset_ids: tuple[str, ...]
    conditional_dataset_ids: tuple[str, ...]
    failed_dataset_ids: tuple[str, ...]
    required_actions: tuple[str, ...]
    advancement_allowed: bool


def _assessment(
    dimension: DataFitnessDimension,
    grade: DataFitnessGrade,
    *reasons: str,
    repairs: tuple[str, ...] = (),
) -> DimensionAssessment:
    return DimensionAssessment(
        dimension=dimension,
        grade=grade,
        reasons=tuple(r for r in reasons if r),
        repair_actions=repairs,
    )


def _role_thresholds(profile: DataFitnessProfile, policy: DataFitnessPolicy) -> tuple[float, float, float]:
    if profile.use_role is DataUseRole.PRIMARY_TEST:
        return (
            policy.min_primary_coverage,
            policy.max_primary_missing_fraction,
            policy.min_primary_join_fraction,
        )
    return (
        policy.min_supporting_coverage,
        policy.max_supporting_missing_fraction,
        policy.min_supporting_join_fraction,
    )


def _applicability(profile: DataFitnessProfile) -> tuple[DimensionAssessment, DimensionAssessment]:
    pop_reasons = tuple(
        reason for condition, reason in (
            (profile.population_fit, "population/species context does not match the intended use"),
            (profile.geography_fit, "geographic/environmental context does not match the intended use"),
        ) if not condition
    )
    time_reasons = () if profile.temporal_fit else (
        "time period or developmental/sampling window does not match the intended use",
    )

    if profile.use_role is DataUseRole.PRIMARY_TEST:
        pop_grade = DataFitnessGrade.FAIL if pop_reasons else DataFitnessGrade.PASS
        time_grade = DataFitnessGrade.FAIL if time_reasons else DataFitnessGrade.PASS
        pop_repairs = ("discover:better_population_geography_match", "evolve:claim_population_scope") if pop_reasons else ()
        time_repairs = ("discover:better_temporal_match", "evolve:claim_time_scope") if time_reasons else ()
    elif profile.use_role is DataUseRole.MECHANISTIC_SUPPORT:
        pop_grade = DataFitnessGrade.CONDITIONAL if pop_reasons else DataFitnessGrade.PASS
        time_grade = DataFitnessGrade.CONDITIONAL if time_reasons else DataFitnessGrade.PASS
        pop_repairs = ("calibrate:mechanistic_scope", "discover:closer_population_match") if pop_reasons else ()
        time_repairs = ("calibrate:temporal_scope", "discover:closer_time_match") if time_reasons else ()
    else:
        pop_grade = time_grade = DataFitnessGrade.PASS
        pop_repairs = time_repairs = ()

    return (
        _assessment(DataFitnessDimension.POPULATION_GEOGRAPHY, pop_grade, *pop_reasons, repairs=pop_repairs),
        _assessment(DataFitnessDimension.TEMPORAL_FIT, time_grade, *time_reasons, repairs=time_repairs),
    )


def evaluate_general_data_fitness(
    profile: DataFitnessProfile,
    *,
    policy: DataFitnessPolicy | None = None,
) -> tuple[DataFitnessGrade, tuple[DimensionAssessment, ...], tuple[str, ...]]:
    """Evaluate domain-agnostic G3 without substituting for G3-OMICS."""

    policy = policy or DataFitnessPolicy()
    d: list[DimensionAssessment] = []

    d.append(
        _assessment(DataFitnessDimension.LEGAL_REUSE, DataFitnessGrade.PASS)
        if profile.legal_reuse_permitted
        else _assessment(
            DataFitnessDimension.LEGAL_REUSE,
            DataFitnessGrade.FAIL,
            "dataset use/reuse is not legally or contractually permitted",
            repairs=("replace:dataset_with_permitted_source", "obtain:reuse_authorization"),
        )
    )

    provenance_reasons = tuple(
        reason for condition, reason in (
            (profile.provenance_traceable, "dataset provenance is not traceable"),
            (profile.source_identity_known, "source/accession/origin identity is unknown"),
        ) if not condition
    )
    d.append(
        _assessment(
            DataFitnessDimension.PROVENANCE,
            DataFitnessGrade.FAIL,
            *provenance_reasons,
            repairs=("repair:source_provenance", "replace:untraceable_dataset"),
        )
        if provenance_reasons
        else _assessment(DataFitnessDimension.PROVENANCE, DataFitnessGrade.PASS)
    )

    d.extend(_applicability(profile))

    construct_reasons = tuple(
        reason for condition, reason in (
            (profile.construct_valid, "dataset variables do not validly represent the intended construct"),
            (profile.measurement_valid, "measurement method is invalid or unsuitable for the intended construct"),
        ) if not condition
    )
    d.append(
        _assessment(
            DataFitnessDimension.CONSTRUCT_VALIDITY,
            DataFitnessGrade.FAIL,
            *construct_reasons,
            repairs=("evolve:construct_or_measurement", "discover:valid_measurement_dataset"),
        )
        if construct_reasons
        else _assessment(DataFitnessDimension.CONSTRUCT_VALIDITY, DataFitnessGrade.PASS)
    )

    if not profile.critical_qc_pass:
        d.append(_assessment(
            DataFitnessDimension.QUALITY,
            DataFitnessGrade.FAIL,
            "critical data-quality checks failed",
            repairs=("repair:data_quality", "replace:failed_dataset"),
        ))
    elif not profile.quality_documented:
        d.append(_assessment(
            DataFitnessDimension.QUALITY,
            DataFitnessGrade.CONDITIONAL,
            "critical QC passed but quality methods/evidence are incompletely documented",
            repairs=("document:quality_evidence",),
        ))
    else:
        d.append(_assessment(DataFitnessDimension.QUALITY, DataFitnessGrade.PASS))

    min_coverage, max_missing, min_join = _role_thresholds(profile, policy)

    if not profile.required_fields_present:
        d.append(_assessment(
            DataFitnessDimension.COVERAGE,
            DataFitnessGrade.FAIL,
            "one or more variables required for the intended analysis are absent",
            repairs=("discover:dataset_with_required_fields", "evolve:estimand_or_analysis"),
        ))
    elif profile.coverage_fraction < min_coverage:
        grade = DataFitnessGrade.FAIL if profile.use_role is DataUseRole.PRIMARY_TEST else DataFitnessGrade.CONDITIONAL
        d.append(_assessment(
            DataFitnessDimension.COVERAGE,
            grade,
            f"usable coverage {profile.coverage_fraction:.3f} is below the predeclared {min_coverage:.3f} threshold",
            repairs=("repair:coverage", "discover:better_coverage_dataset", "calibrate:claim_scope"),
        ))
    else:
        d.append(_assessment(DataFitnessDimension.COVERAGE, DataFitnessGrade.PASS))

    if profile.missing_fraction > max_missing:
        grade = (
            DataFitnessGrade.FAIL
            if profile.use_role is DataUseRole.PRIMARY_TEST or not profile.missingness_strategy_available
            else DataFitnessGrade.CONDITIONAL
        )
        d.append(_assessment(
            DataFitnessDimension.MISSINGNESS,
            grade,
            f"missing fraction {profile.missing_fraction:.3f} exceeds the predeclared {max_missing:.3f} threshold",
            repairs=("repair:missingness_plan", "discover:lower_missingness_dataset", "calibrate:claim_scope"),
        ))
    elif profile.missing_fraction > 0 and not profile.missingness_characterized:
        d.append(_assessment(
            DataFitnessDimension.MISSINGNESS,
            DataFitnessGrade.CONDITIONAL,
            "missingness exists but its pattern/mechanism has not been characterized",
            repairs=("characterize:missingness",),
        ))
    else:
        d.append(_assessment(DataFitnessDimension.MISSINGNESS, DataFitnessGrade.PASS))

    d.append(
        _assessment(DataFitnessDimension.VARIATION, DataFitnessGrade.PASS)
        if profile.outcome_or_key_variation_present
        else _assessment(
            DataFitnessDimension.VARIATION,
            DataFitnessGrade.FAIL,
            "required outcome/exposure/key variable has insufficient variation for the intended analysis",
            repairs=("replace:noninformative_dataset", "evolve:estimand_or_sampling"),
        )
    )

    if not profile.requires_join:
        d.append(_assessment(DataFitnessDimension.JOINABILITY, DataFitnessGrade.PASS))
    elif not profile.stable_join_keys:
        d.append(_assessment(
            DataFitnessDimension.JOINABILITY,
            DataFitnessGrade.FAIL,
            "required tables cannot be joined with stable unique keys",
            repairs=("repair:join_keys", "replace:unjoinable_data"),
        ))
    elif profile.join_coverage_fraction < min_join:
        grade = DataFitnessGrade.FAIL if profile.use_role is DataUseRole.PRIMARY_TEST else DataFitnessGrade.CONDITIONAL
        d.append(_assessment(
            DataFitnessDimension.JOINABILITY,
            grade,
            f"join coverage {profile.join_coverage_fraction:.3f} is below the predeclared {min_join:.3f} threshold",
            repairs=("repair:join_coverage", "calibrate:claim_scope"),
        ))
    else:
        d.append(_assessment(DataFitnessDimension.JOINABILITY, DataFitnessGrade.PASS))

    ident_reasons = tuple(
        reason for condition, reason in (
            (profile.target_estimand_identifiable, "target estimand/question is not identifiable from these data"),
            (
                profile.required_confounders_available or profile.use_role is not DataUseRole.PRIMARY_TEST,
                "required confounders/covariates for the primary estimand are unavailable",
            ),
        ) if not condition
    )
    if ident_reasons:
        grade = DataFitnessGrade.FAIL if profile.use_role is DataUseRole.PRIMARY_TEST else DataFitnessGrade.CONDITIONAL
        d.append(_assessment(
            DataFitnessDimension.IDENTIFIABILITY,
            grade,
            *ident_reasons,
            repairs=("evolve:estimand", "discover:identifiable_dataset", "calibrate:noncausal_claim"),
        ))
    else:
        d.append(_assessment(DataFitnessDimension.IDENTIFIABILITY, DataFitnessGrade.PASS))

    bias_reasons = []
    if profile.severe_selection_bias:
        bias_reasons.append("material selection bias is present")
    if profile.survivorship_bias_present:
        bias_reasons.append("material survivorship bias is present")
    unaddressable = (
        profile.severe_selection_bias and not profile.selection_bias_addressable
    ) or (
        profile.survivorship_bias_present and not profile.survivorship_bias_addressable
    )
    if unaddressable:
        grade = DataFitnessGrade.FAIL if profile.use_role is DataUseRole.PRIMARY_TEST else DataFitnessGrade.CONDITIONAL
        repairs = ("replace:biased_dataset", "calibrate:claim_scope")
    elif bias_reasons:
        grade = DataFitnessGrade.CONDITIONAL
        repairs = ("specify:bias_adjustment_or_sensitivity",)
    else:
        grade = DataFitnessGrade.PASS
        repairs = ()
    d.append(_assessment(DataFitnessDimension.SELECTION_BIAS, grade, *bias_reasons, repairs=repairs))

    if not profile.units_known:
        d.append(_assessment(
            DataFitnessDimension.UNIT_CONSISTENCY,
            DataFitnessGrade.FAIL,
            "measurement units are unknown",
            repairs=("repair:unit_metadata", "replace:ambiguous_units_dataset"),
        ))
    elif not profile.units_harmonized:
        grade = DataFitnessGrade.CONDITIONAL if profile.units_harmonizable else DataFitnessGrade.FAIL
        d.append(_assessment(
            DataFitnessDimension.UNIT_CONSISTENCY,
            grade,
            "measurement units are not harmonized across required records/sources",
            repairs=("harmonize:units",) if profile.units_harmonizable else ("replace:incompatible_units_data",),
        ))
    else:
        d.append(_assessment(DataFitnessDimension.UNIT_CONSISTENCY, DataFitnessGrade.PASS))

    if profile.sample_independence_known:
        d.append(_assessment(DataFitnessDimension.INDEPENDENCE, DataFitnessGrade.PASS))
    else:
        grade = DataFitnessGrade.FAIL if profile.use_role is DataUseRole.PRIMARY_TEST else DataFitnessGrade.CONDITIONAL
        d.append(_assessment(
            DataFitnessDimension.INDEPENDENCE,
            grade,
            "sample/experimental-unit independence cannot be established",
            repairs=("resolve:sample_independence", "calibrate:exploratory_or_contextual_use"),
        ))

    repro_reasons = tuple(
        reason for condition, reason in (
            (profile.reproducible_acquisition, "dataset cannot be reacquired reproducibly from its declared source"),
            (profile.source_versioned_or_freezeable, "source is neither versioned nor freezeable for hash-locked provenance"),
        ) if not condition
    )
    d.append(
        _assessment(
            DataFitnessDimension.REPRODUCIBILITY,
            DataFitnessGrade.FAIL,
            *repro_reasons,
            repairs=("repair:reproducible_acquisition", "replace:unversionable_source"),
        )
        if repro_reasons
        else _assessment(DataFitnessDimension.REPRODUCIBILITY, DataFitnessGrade.PASS)
    )

    grades = {x.grade for x in d}
    overall = (
        DataFitnessGrade.FAIL if DataFitnessGrade.FAIL in grades
        else DataFitnessGrade.CONDITIONAL if DataFitnessGrade.CONDITIONAL in grades
        else DataFitnessGrade.PASS
    )
    repairs = tuple(dict.fromkeys(action for x in d for action in x.repair_actions))
    return overall, tuple(d), repairs


def _omics_layer_grade(
    profile: DataFitnessProfile,
    omics_fitness: OmicsFitness | None,
) -> tuple[DataFitnessGrade, DimensionAssessment]:
    if profile.domain is not DataDomain.OMICS:
        return DataFitnessGrade.PASS, _assessment(DataFitnessDimension.DOMAIN_GATE, DataFitnessGrade.PASS)

    if omics_fitness is None:
        return DataFitnessGrade.CONDITIONAL, _assessment(
            DataFitnessDimension.DOMAIN_GATE,
            DataFitnessGrade.CONDITIONAL,
            "omics dataset passed General G3 but G3-OMICS has not been completed",
            repairs=("run:g3_omics",),
        )
    if omics_fitness is OmicsFitness.E:
        return DataFitnessGrade.FAIL, _assessment(
            DataFitnessDimension.DOMAIN_GATE,
            DataFitnessGrade.FAIL,
            "G3-OMICS classified the dataset as incompatible",
            repairs=("discover:compatible_omics_dataset", "evolve:omics_claim_role"),
        )

    if profile.use_role is DataUseRole.PRIMARY_TEST:
        if omics_fitness is OmicsFitness.A:
            return DataFitnessGrade.PASS, _assessment(DataFitnessDimension.DOMAIN_GATE, DataFitnessGrade.PASS)
        return DataFitnessGrade.CONDITIONAL, _assessment(
            DataFitnessDimension.DOMAIN_GATE,
            DataFitnessGrade.CONDITIONAL,
            f"{omics_fitness.value} omics data cannot support an unqualified primary/direct test",
            repairs=("calibrate:omics_claim_role", "discover:directly_comparable_omics_dataset"),
        )

    if profile.use_role is DataUseRole.MECHANISTIC_SUPPORT:
        if omics_fitness in {OmicsFitness.A, OmicsFitness.B, OmicsFitness.C}:
            return DataFitnessGrade.PASS, _assessment(DataFitnessDimension.DOMAIN_GATE, DataFitnessGrade.PASS)
        return DataFitnessGrade.CONDITIONAL, _assessment(
            DataFitnessDimension.DOMAIN_GATE,
            DataFitnessGrade.CONDITIONAL,
            "contextual-only omics data cannot be treated as mechanistic support",
            repairs=("calibrate:omics_claim_role", "discover:mechanistically_compatible_omics_dataset"),
        )

    return DataFitnessGrade.PASS, _assessment(DataFitnessDimension.DOMAIN_GATE, DataFitnessGrade.PASS)


def evaluate_layered_data_fitness(
    profile: DataFitnessProfile,
    *,
    omics_metadata: OmicsMetadata | None = None,
    omics_fitness: OmicsFitness | None = None,
    policy: DataFitnessPolicy | None = None,
) -> DatasetFitnessReport:
    if omics_metadata is not None and omics_fitness is not None:
        raise ValueError("provide omics_metadata or omics_fitness, not both")
    if profile.domain is not DataDomain.OMICS and (omics_metadata is not None or omics_fitness is not None):
        raise ValueError("omics metadata/fitness can only be supplied for an OMICS dataset")
    if omics_metadata is not None:
        omics_fitness = grade_omics_fitness(omics_metadata)

    general_grade, general_dimensions, repairs = evaluate_general_data_fitness(profile, policy=policy)
    domain_grade, domain_assessment = _omics_layer_grade(profile, omics_fitness)
    all_repairs = tuple(dict.fromkeys(repairs + domain_assessment.repair_actions))
    layered = (
        DataFitnessGrade.FAIL
        if DataFitnessGrade.FAIL in {general_grade, domain_grade}
        else DataFitnessGrade.CONDITIONAL
        if DataFitnessGrade.CONDITIONAL in {general_grade, domain_grade}
        else DataFitnessGrade.PASS
    )
    return DatasetFitnessReport(
        dataset_id=profile.dataset_id,
        domain=profile.domain,
        use_role=profile.use_role,
        general_grade=general_grade,
        dimensions=general_dimensions + (domain_assessment,),
        repair_actions=all_repairs,
        omics_fitness=omics_fitness,
        layered_grade=layered,
        advancement_allowed=layered is DataFitnessGrade.PASS,
    )


def data_fitness_court(
    profiles: Iterable[DataFitnessProfile],
    *,
    omics_metadata_by_dataset: Mapping[str, OmicsMetadata] | None = None,
    omics_fitness_by_dataset: Mapping[str, OmicsFitness] | None = None,
    policy: DataFitnessPolicy | None = None,
    blocker_gate: BlockerGate | None = None,
    route_requires_existing_data: bool = True,
) -> DataFitnessCourtResult:
    """Require every route-required dataset to pass General G3 and domain gates."""

    if blocker_gate is not None:
        blocker_gate.assert_can_advance(from_phase="feasibility", to_phase="data_fitness")

    profiles = list(profiles)
    if not profiles:
        status = DataFitnessStatus.BLOCKED if route_requires_existing_data else DataFitnessStatus.ADVANCE
        return DataFitnessCourtResult(
            status=status,
            reports=(),
            passed_dataset_ids=(),
            conditional_dataset_ids=(),
            failed_dataset_ids=(),
            required_actions=("discover:required_data",) if route_requires_existing_data else (),
            advancement_allowed=status is DataFitnessStatus.ADVANCE,
        )

    ids = [p.dataset_id for p in profiles]
    if len(set(ids)) != len(ids):
        raise ValueError("dataset_id values must be unique")
    if omics_metadata_by_dataset is not None and omics_fitness_by_dataset is not None:
        raise ValueError("provide omics metadata map or omics fitness map, not both")

    omics_metadata_by_dataset = omics_metadata_by_dataset or {}
    omics_fitness_by_dataset = omics_fitness_by_dataset or {}
    unknown = (set(omics_metadata_by_dataset) | set(omics_fitness_by_dataset)) - set(ids)
    if unknown:
        raise ValueError(f"omics evidence supplied for unknown dataset(s): {sorted(unknown)}")

    reports = tuple(
        evaluate_layered_data_fitness(
            p,
            omics_metadata=omics_metadata_by_dataset.get(p.dataset_id),
            omics_fitness=omics_fitness_by_dataset.get(p.dataset_id),
            policy=policy,
        )
        for p in profiles
    )
    passed = tuple(r.dataset_id for r in reports if r.layered_grade is DataFitnessGrade.PASS)
    conditional = tuple(r.dataset_id for r in reports if r.layered_grade is DataFitnessGrade.CONDITIONAL)
    failed = tuple(r.dataset_id for r in reports if r.layered_grade is DataFitnessGrade.FAIL)

    status = (
        DataFitnessStatus.BLOCKED if failed
        else DataFitnessStatus.REVISE if conditional
        else DataFitnessStatus.ADVANCE
    )
    actions = tuple(dict.fromkeys(action for r in reports for action in r.repair_actions))
    return DataFitnessCourtResult(
        status=status,
        reports=reports,
        passed_dataset_ids=passed,
        conditional_dataset_ids=conditional,
        failed_dataset_ids=failed,
        required_actions=actions,
        advancement_allowed=status is DataFitnessStatus.ADVANCE,
    )
