# Agriculture CoScientist v0.8 — Study Design / Design Freeze Validation

Date: 2026-09-04
Status at creation: MERGED; FINAL MAIN CLOSURE CI STILL REQUIRED

## Authority chain

- Previous authoritative baseline: v0.7 main `41423aa0899c76cc0990f28a4f17fc9dd0d643dd`
- Pull request: #7 `v0.8 route-aware Study Design Court and Design Freeze`
- Validated feature head: `d85417afc6e813e16235af7521812da21b69ab0d`
- Authoritative PR validation run: `33855761811`
- Merge commit: `e2434fe2306c2eedeb100f7461324259811392e2`

## Scientific purpose

v0.8 implements the route-aware Study Design Court after layered Data Fitness and adds a deterministic, SHA-256-bound pre-outcome Design Freeze. It supports physical, public-data, and hybrid studies without conflating technical subsampling with independent biological replication or public-data mechanistic context with direct validation of user-generated experimental units.

State order is:

`DATA_FITNESS -> DESIGN -> DESIGN_FROZEN`

The later statistical prespecification stage remains separate:

`DESIGN_FROZEN -> DATASET_FREEZE -> ANALYSIS_SPECIFICATION -> ANALYSIS_LOCK`

Design Freeze does not lock the statistical model, software package, multiplicity method, model contrast implementation, or execution order.

## Study Design Court coverage

The executable court evaluates, where applicable:

- explicit research question, hypotheses/estimands, inference intent, confirmatory status, and route shape
- experimental unit and analysis-unit alignment
- true independent units by treatment/group
- replication rationale and precision/power planning
- treatments, controls, manipulated exposure, allocation/randomization, and reproducible randomization plan
- known nuisance gradients, blocking factors, and block construction/allocation plan
- technical subsamples, repeated-measures identity, destructive-sampling compatibility, and sampling schedule
- required versus unavailable methods
- feasible outcome-assessment blinding
- primary, secondary, mechanistic, QC, covariate, and metadata outcome hierarchy
- predeclared exclusions and quality controls
- public source-study design, sampling/experimental unit, sample independence, planned use/contrast, and layered Data Fitness
- causal-identification boundaries for public-data primary tests
- pre-freeze outcome access
- blocker-first entry and freeze advancement

## Permanent scientific safeguards

v0.8 enforces that technical or within-unit subsamples do not create independent biological replication. Confirmatory groups with only one independent unit cannot masquerade as replicated groups.

For causal physical inference, manipulated exposure plus randomized or block-randomized allocation is required in the implemented experimental route. Known nuisance gradients cannot be silently ignored.

Unavailable new wet-lab qPCR, RT-qPCR, RNA-seq, transcriptomics, and similar molecular assays cannot be reintroduced as required methods when they are explicitly unavailable. Scientifically valid public omics may still be used subject to layered Data Fitness and claim calibration.

Public transcriptomic/omics data used for mechanistic support do not inherit causal authority from the physical experiment and must not be described as direct molecular validation of experimental units that were never sequenced.

## Design Freeze boundary

A Design Freeze may be created only from a clean `ADVANCE` Study Design Court result and, for confirmatory designs, before confirmatory outcome access.

The freeze deterministically hashes the canonical scientific design payload and freezes the scientific design components while deliberately preserving:

`analysis_model_locked=false`

Analysis-method/model/software choices belong to the later Analysis Specification / Analysis Lock.

## Adversarial contract coverage

The v0.8 contracts attack at least:

- route-shape mismatch
- pseudoreplication through analysis-unit mismatch
- one independent unit per confirmatory group
- missing replication rationale or precision/power plan
- unavailable wet-lab omics reintroduced as required methods
- technical subsamples treated as biological replicates
- repeated measures without persistent unit identity
- destructive sampling masquerading as repeated measures
- causal physical claims without manipulation
- causal physical claims without randomization
- missing reproducible randomization plan
- known nuisance gradient without blocking
- declared blocking factors without a blocking plan
- feasible blinding silently omitted
- missing prespecified exclusions
- missing QC
- missing acquisition metadata
- excessive co-primary endpoint burden without revision
- public dataset without passed layered Data Fitness
- unknown public source-study design
- unknown public sample independence
- public primary causal use without causal identification
- pre-freeze confirmatory outcome access
- attempting to freeze FAIL or CONDITIONAL designs
- Design Freeze from the wrong project state
- blocker-first bypass entering Design or Design Freeze

## PR validation evidence

Authoritative exact-head workflow run: `33855761811`.

Passed ordinary jobs:

- `python-kernel`
- `study-design-freeze-court`
- `general-data-fitness-court`
- `feasibility-route-court`
- `literature-novelty-live`
- `r-omics`
- `public-data-live`
- `annotation-enrichment-live`

`v04-real-public-omics` was correctly skipped because this was not its dedicated real-data execution scenario.

## Capability artifact

- Artifact ID: `9930111085`
- Artifact name: `study-design-freeze-capability-evidence`
- GitHub artifact digest: `sha256:04c1e802a34478e93422f073a9e0bb142bc23f24593a93664d61af318bbcb833`
- Downloaded artifact ZIP SHA-256: `04c1e802a34478e93422f073a9e0bb142bc23f24593a93664d61af318bbcb833`
- Extracted `study_design_capability.json` SHA-256: `f3dc889fc6b6d4ba29220e9eeeebc7b105446064a04b380411ba70670863cf9c`
- Deterministic Design Freeze SHA-256: `17cda376dd53bccbd6f3b3b0c22f4318fbba9155678b2d7fc54cc2a84ab1bc76`

Capability verdicts:

- court status: `advance`
- advancement allowed: true
- route: hybrid
- physical independent units: 12 total, 6 + 6 by group
- allocation: `block_randomized`
- blocking factor: `bench_position`
- pseudoreplication attack: blocked
- known-gradient-without-blocking attack: blocked
- nonrandom causal claim attack: blocked
- confirmatory outcome peeking attack: blocked
- public data without layered G3 attack: blocked
- unavailable wet-lab omics-required attack: blocked
- public-data role: mechanistic support only, not direct validation
- `pre_outcome=true`
- `analysis_model_locked=false`

Claim boundary: this is capability validation of the Study Design / Design Freeze machinery. It is not biological validation of a specific future experiment, public dataset, mechanism, or publishable claim.

## Open-blocker inspection at merge gate

Repository open-issue inspection found no open standalone blocking issue; PR #7 was the only open issue-like object before merge. No OPEN BLOCKING issue was present at the merge gate.

## Final closure gate

This record intentionally does not declare v0.8 authoritative by itself. The newest `main` commit containing this provenance record must run the ordinary capability suite. v0.8 becomes the authoritative baseline only if all ordinary jobs pass on that exact `main` head. Any failure becomes the next OPEN blocker and must be diagnosed, repaired, regression-tested, and rerun before phase advancement.
