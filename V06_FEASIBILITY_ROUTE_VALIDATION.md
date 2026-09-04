# Agriculture CoScientist — v0.6 Feasibility / Route Court Validation

Date: 2026-09-04
Status: **VALIDATED / MERGED / EVIDENCE COMPLETE — FINAL MAIN CI PENDING**
Repository: `jawadresearchai-creator/test`
Merged PR: #5
Merge commit: `38750578d7e6c9d640292d2c29d75fc31ddefa3d`
Validated feature head: `0d96385bb2127db8c91b9e975f16703710b99f9a`
Authoritative PR validation workflow run: `33846567533`

## Capability added

v0.6 adds an executable multidimensional Feasibility Court and deterministic route-selection engine. This phase is deliberately pre-design: it decides whether a novelty-surviving candidate is executable and which route can proceed to downstream Data Fitness and Design. It does not freeze treatments, endpoints, or analysis models.

Evaluated dimensions:

- laboratory / physical capability;
- preliminary public-data availability and compatibility;
- computational worker/runtime availability;
- statistical identifiability, measurable primary outcome and independent replication;
- budget and timeline;
- target-journal scope fit;
- provenance traceability;
- explicit user constraints.

Supported routes:

- physical experiment;
- public data;
- hybrid physical + public data.

## Molecular-resource rule now executable

A route that requires unavailable new wet-lab qPCR/RNA-seq/omics is a hard failure for that route only. The research candidate itself is not rejected until alternative public-data and hybrid routes have also been evaluated.

Public-omics compatibility at this phase is preliminary and cannot substitute for downstream G3/G3-OMICS. Public data used as an unqualified direct test require the strongest comparability; weaker compatibility forces claim recalibration, additional data discovery, or route revision.

## Blocker-first integration

The feasibility court accepts the sovereign `BlockerGate`. Any OPEN BLOCKING issue prevents entry from novelty to feasibility and raises the existing phase-blocked error. The court therefore cannot be used to bypass an unresolved upstream blocker.

## Adversarial contracts

The contract suite attacks at least the following failure modes:

- unavailable new wet-lab omics incorrectly killing the whole candidate;
- unavailable new wet-lab omics incorrectly passing a physical route;
- public data with no candidate dataset;
- incompatible public omics;
- strongly-compatible data being overclaimed as a direct test;
- contextual data being used only within a contextual/hypothesis role;
- confirmatory inference without adequate independent replication;
- unidentifiable estimands;
- missing compute/runtime;
- journal mismatch incorrectly advancing without revision;
- missing provenance;
- explicit user-constraint violations;
- route-ranking determinism;
- duplicate/incoherent route definitions;
- entry to feasibility with an OPEN blocker.

## Capability scenario and evidence

Scenario: `unavailable_new_wetlab_omics_route_rescue_capability`

Workflow run `33846567533` passed:

- `python-kernel`
- `feasibility-route-court`
- `literature-novelty-live`
- `r-omics`
- `public-data-live`
- `annotation-enrichment-live`

The v0.4 real-public-omics reusable job was correctly skipped because this was not the v0.4 execution branch.

Evidence artifact:

- artifact ID: `9926741542`
- artifact name: `feasibility-route-capability-evidence`
- artifact ZIP SHA-256: `36a056ca9c913f83af1ed96a98ed2c720223e2d067464c58f554302715679718`
- `feasibility_route_capability.json` SHA-256: `cbad0ae8a5ace2b52a4d922c8546afd24ee65eca19cee92a7281ea3e4d2eb4af`

Observed route verdicts:

1. `physical_with_new_rnaseq` — **FAIL**
   - failed because new wet-lab omics were required but unavailable;
   - repair actions include removing unavailable wet-lab omics, considering public-omics reanalysis, and considering a non-molecular + public-omics hybrid route.

2. `public_omics_direct_test` — **CONDITIONAL**
   - preliminary OmicsFitness B was deliberately not accepted for an unqualified direct-test claim;
   - required actions include claim-role calibration or discovery of a more directly comparable dataset.

3. `hybrid_nonmolecular_plus_public_omics` — **PASS / SELECTED**
   - feasible physical non-molecular component;
   - no unavailable new wet-lab omics requirement;
   - preliminary OmicsFitness C public data used only for mechanistic support;
   - compute, statistics, resources, journal, provenance, and user constraints passed in the capability scenario.

Court result: `advance` to downstream Data Fitness / Design using the selected hybrid route.

## Claim boundary

The feasibility court may say that a route is feasible enough to enter downstream gates. It may not say that:

- preliminary OmicsFitness replaces G3/G3-OMICS;
- the selected route is scientifically validated before downstream data-fitness/design gates;
- public omics are direct validation when their compatibility supports only mechanism/context;
- an unavailable wet-lab method should be required merely because it is scientifically familiar.

## Final closure gate

After this validation record is committed to `main`, the latest ordinary `main` capability suite must pass before v0.6 becomes the authoritative baseline. Any failure becomes the next OPEN blocker and must be resolved before further phase advancement.
