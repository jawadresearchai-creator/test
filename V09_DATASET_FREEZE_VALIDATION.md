# Agriculture CoScientist v0.9 — Project Dataset Freeze Validation

Date: 2026-09-04
Status at creation: MERGED; FINAL MAIN CLOSURE CI STILL REQUIRED

## Authority chain

- Previous authoritative baseline: v0.8 main `7265cc74467bb2c2267b413a0f87461cfbab5be5`
- Pull request: #8 `v0.9 project-level Dataset Freeze court`
- Validated feature head: `37dfabb4a07d58b94a458aa20be5bece726262e7`
- Authoritative PR validation run: `33866838716`
- Merge commit: `1a923f5b9ff9319821d2ae837725bc399e750f80`

## Why v0.9 was the next state-ordered subsystem

Post-v0.8 audit of the merged kernel found that the project state machine jumped directly from `DESIGN_FROZEN` to `ANALYSIS_LOCKED`. There was no general project-level `DATASET_FROZEN` or executable Dataset Freeze court. The older v0.4 public-omics helpers contained a scenario-specific dataset freeze, but that implementation deliberately assumes exactly two featureCounts assets and a fixed DESeq2 scenario and therefore was not suitable as the general project engine.

v0.9 adds the required project-level boundary without weakening or generalizing the v0.4 scenario-specific capability.

The corrected explicit state order is now:

`DESIGN_FROZEN -> DATASET_FROZEN -> ANALYSIS_SPECIFICATION -> ANALYSIS_LOCKED`

Only Dataset Freeze functionality is implemented in v0.9. `ANALYSIS_SPECIFICATION` is now an explicit state boundary so a future Analysis Specification engine cannot be silently skipped.

## Dataset Freeze scientific purpose

Dataset Freeze binds the exact acquired/reused evidence to the already-frozen scientific design before confirmatory outcome analysis. It freezes data identity and acquisition provenance; it does not choose statistical models, transformations, software packages, multiplicity methods, contrasts, or execution order.

The general engine is route-aware for:

- physical experiments,
- public-data studies,
- hybrid physical + public-data studies.

## Frozen identity and provenance requirements

Every frozen asset is bound by:

- unique asset ID,
- origin (`project_generated` or `public_reused`),
- asset role,
- SHA-256,
- byte count,
- stable locator,
- representation,
- schema fields where relevant,
- sample identities where relevant.

Public/reused assets additionally require:

- source dataset identity,
- source version/release/snapshot identity.

The complete Dataset Freeze is deterministically SHA-256-bound to the exact Dataset Freeze plan and the preceding Design Freeze hash.

## Physical-data safeguards

For physical/hybrid studies v0.9 requires:

- at least one frozen project-generated data asset,
- retained independent-unit identities,
- retained + excluded independent-unit accounting against the frozen planned independent-unit total,
- exclusions only through criteria already prespecified in the Design Freeze,
- frozen-schema coverage of prespecified outcomes, covariates, and metadata.

A post-outcome invented exclusion criterion blocks Dataset Freeze.

Technical/sample rows do not substitute for independent-unit accounting.

## Public-data safeguards

For public/hybrid studies:

- every public dataset declared in Design Freeze must be present in Dataset Freeze,
- every reused public asset must carry a source version/snapshot identity,
- an undeclared public dataset is a material design change and blocks advancement,
- public-data role/claim boundaries remain those already established by Design/Data Fitness; Dataset Freeze does not promote mechanistic/contextual public data into direct validation.

## Pre-outcome safeguard

For confirmatory studies, outcome values must not have been inspected before Dataset Freeze. Outcome peeking blocks advancement and requires exploratory reclassification or an independent confirmatory restart as appropriate.

Hashing bytes, validating schema, sample identity, metadata and integrity remains distinct from inspecting confirmatory outcome patterns.

## Analysis boundary

Dataset Freeze explicitly preserves:

- `analysis_specification_locked=false`
- `analysis_model_locked=false`

The state machine rejects direct `DATASET_FROZEN -> ANALYSIS_LOCKED` advancement. The next explicit state is `ANALYSIS_SPECIFICATION`.

## Adversarial contract coverage

v0.9 tests attack at least:

- wrong Design Freeze hash binding,
- route/mode mismatch,
- confirmatory outcome peeking before Dataset Freeze,
- physical/hybrid route without project-generated data,
- missing Design-Freeze-declared public dataset,
- undeclared public dataset,
- missing public source version identity,
- incomplete independent-unit accounting,
- post-hoc exclusion criteria,
- missing prespecified outcome/covariate/metadata fields from frozen project schema,
- public-only route contamination by undeclared project-generated outcome data,
- physical-only route contamination by undeclared public data,
- material asset hash drift,
- trying to build a Dataset Freeze from a blocked court,
- wrong project state,
- direct Dataset Freeze -> Analysis Lock skipping,
- blocker-first bypass,
- malformed SHA-256/sample identity/public-source declarations.

## PR validation evidence

Authoritative exact-head workflow run: `33866838716`.

Passed ordinary jobs:

- `python-kernel`
- `dataset-freeze-court`
- `study-design-freeze-court`
- `general-data-fitness-court`
- `feasibility-route-court`
- `literature-novelty-live`
- `r-omics`
- `public-data-live`
- `annotation-enrichment-live`

`v04-real-public-omics` was correctly skipped because this was not its dedicated real-data execution scenario.

## Capability artifact

- Artifact ID: `9934294104`
- Artifact name: `dataset-freeze-capability-evidence`
- GitHub artifact digest: `sha256:67c860faff74a05beebddb8d7f35acdf1d85e4c1004cec9ff3f3f1d54d3ed016`
- Downloaded artifact ZIP SHA-256: `67c860faff74a05beebddb8d7f35acdf1d85e4c1004cec9ff3f3f1d54d3ed016`
- Extracted `dataset_freeze_capability.json` SHA-256: `d63689757a3680dd29b0dcc516433f62638fc5d224e00dd1b0b561e68830136d`
- Capability Dataset Freeze SHA-256: `09fb13792e5fbfeb38c41b4596ff7146164bb0a1485950112d13e540fcc49c6e`
- Bound Design Freeze SHA-256: `980b52eb573499fcbbc5c2e0c30422a9949bdcfdba74f42fa2b13b9a7c5edc90`

Capability verdicts:

- court status: `advance`
- advancement allowed: true
- route: hybrid
- physical independent units: 12 planned, 12 retained, 0 excluded
- one project-generated frozen asset
- one declared public-reused frozen asset
- public role remains mechanistic support only, not direct validation
- confirmatory outcome blind: true
- deterministic Dataset Freeze hash: true
- wrong Design Freeze binding attack: blocked
- outcome peeking attack: blocked
- missing public dataset attack: blocked
- undeclared public dataset attack: blocked
- missing public version attack: blocked
- unit-accounting mismatch attack: blocked
- post-hoc exclusion attack: blocked
- missing prespecified schema field attack: blocked
- state after freeze: `dataset_frozen`
- direct `dataset_frozen -> analysis_locked`: blocked
- next explicit state: `analysis_specification`
- `analysis_specification_locked=false`
- `analysis_model_locked=false`

Claim boundary: this is capability validation of project-level Dataset Freeze and provenance/state safeguards. It is not biological validation, statistical analysis, or evidence that any future project dataset supports a scientific claim.

## Open-blocker inspection at merge gate

Open BLOCKING issue search returned zero before merge. No OPEN BLOCKING issue was present at the merge gate.

## Final closure gate

This record intentionally does not declare v0.9 authoritative by itself. The newest `main` commit containing this provenance record must run the ordinary capability suite. v0.9 becomes the authoritative baseline only if all ordinary jobs, including `dataset-freeze-court`, pass on that exact provenance head. Any failure becomes the sole OPEN blocker and must be diagnosed, repaired, regression-tested and rerun before phase advancement.
