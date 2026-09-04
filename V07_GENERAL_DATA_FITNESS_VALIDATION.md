# Agriculture CoScientist v0.7 — General G3 Data Fitness Validation

Date: 2026-09-04
Status at creation: MERGED; FINAL MAIN CLOSURE CI STILL REQUIRED

## Authority chain

- Previous authoritative baseline: v0.6 main `33d705e6ab9ce5e0377e07a03c78694d8b64ac86`
- Pull request: #6 `v0.7 General G3 data fitness court`
- Validated repaired feature head: `d5c6b88bfb525327b0cb4dbf5a8e3e987e8e121a`
- Authoritative PR validation run: `33854599881`
- Merge commit: `1a49160b6805d51d6ff6d17f21fc671397df96d3`

## Scientific purpose

v0.7 closes the mandatory state-order gap between FEASIBILITY and DESIGN. A route that survives feasibility may not enter Design merely because data exist. Every route-required existing dataset must first pass General G3 Data Fitness, and domain-specific datasets must then pass their additional domain gate.

State order remains:

`FEASIBILITY -> DATA_FITNESS -> DESIGN`

Direct `FEASIBILITY -> DESIGN` advancement is invalid.

## General G3 dimensions

The executable General G3 court evaluates:

1. legal/reuse permission
2. provenance and source identity
3. population/geography applicability
4. temporal/developmental applicability
5. construct and measurement validity
6. data quality and critical QC
7. required-field and usable-data coverage
8. missingness burden and characterization
9. informative outcome/exposure/key-variable variation
10. joinability and stable join keys
11. statistical/causal identifiability and required confounders
12. selection and survivorship bias
13. unit identity and harmonization
14. sample/experimental-unit independence
15. reproducible acquisition and source versionability/freezeability

Capability-test policy defaults are deliberately explicit and predeclared rather than hidden heuristics. They are not universal scientific constants; a project may supply stricter pre-outcome policy.

## General G3 and G3-OMICS are separate layers

General G3 never substitutes for G3-OMICS.

For an OMICS dataset:

- General G3 PASS with no G3-OMICS result remains CONDITIONAL and cannot advance.
- OmicsFitness E is a hard incompatibility failure.
- PRIMARY_TEST requires directly comparable OmicsFitness A for a clean pass; B/C/D force claim-role or dataset revision.
- MECHANISTIC_SUPPORT may pass at A/B/C; D remains too weak for mechanistic support without claim revision.
- Contextual/hypothesis-generation use is separately calibrated.

Therefore a public transcriptomic dataset graded C can support a mechanistic/contextual triangulation role after General G3 passes, but it cannot be relabeled as direct molecular validation of another experiment.

## Physical-only route rule

A physical-only route that does not yet depend on pre-existing external data does not fabricate a dummy dataset merely to satisfy General G3. It may pass the empty-existing-data Data Fitness boundary only when no upstream blocker is open; its acquisition schema belongs to the later Design Engine.

If the selected route requires existing data and no such data are available, Data Fitness is BLOCKED with a required data-discovery action.

## Blocker discovered and resolved during v0.7

The first implementation contained a blocker-first governance bypass: the empty-profile/physical-only fast path was evaluated before `BlockerGate`, so it could return ADVANCE while an upstream feasibility blocker remained OPEN.

Resolution:

- `BlockerGate.assert_can_advance(from_phase="feasibility", to_phase="data_fitness")` now executes before every Data Fitness fast path.
- `tests/test_data_fitness_blocker_fastpath.py` permanently attacks the no-existing-data bypass.
- The repaired head, not the superseded head, was used for the authoritative validation run and merge.

This blocker is RESOLVED by executable regression evidence; it was not waived.

## Adversarial contract coverage

The v0.7 contracts attack at least:

- illegal reuse
- unknown/untraceable provenance
- population/geographic/temporal mismatch
- invalid constructs or measurements
- critical QC failure
- inadequate coverage
- excessive or uncharacterized missingness
- no informative variation
- unstable joins and low join coverage
- unidentifiable estimands
- unavailable required confounders
- selection bias
- survivorship bias
- unknown/incompatible units
- unknown sample independence
- non-reproducible or unfreezeable acquisition
- General-G3-to-G3-OMICS bypass
- incompatible omics data
- grade-C direct-primary overclaim
- missing required existing data
- state-machine bypass from FEASIBILITY directly to DESIGN
- blocker-first bypass through the physical/no-existing-data fast path

## PR validation evidence

Authoritative repaired-head workflow run: `33854599881`.

Passed ordinary jobs:

- `python-kernel`
- `general-data-fitness-court`
- `feasibility-route-court`
- `literature-novelty-live`
- `r-omics`
- `public-data-live`
- `annotation-enrichment-live`

`v04-real-public-omics` was correctly skipped because this was not a v0.4 real-data execution.

## Capability artifact

- Artifact ID: `9929681418`
- Artifact name: `general-data-fitness-capability-evidence`
- GitHub artifact SHA-256: `0f6ebb2403a1eec17d4125655d23f33c4e063f215fb86845c4c228423a627990`
- `data_fitness_capability.json` SHA-256: `4fbf74d3d51759f02013dade065a42859bd3ab75624356de6fbdadff2372b290`

Capability attack results:

- selected route: `hybrid_nonmolecular_plus_public_omics`
- selected public-data role: `mechanistic_support`
- selected public-omics General G3: PASS
- selected public-omics G3-OMICS: C / mechanistically compatible
- selected layered result: PASS for mechanistic-support use only
- General G3 without G3-OMICS: CONDITIONAL
- illegal reuse: FAIL
- bad join plus unidentifiable primary analysis: FAIL
- grade-C omics used as direct primary test: CONDITIONAL
- physical route without pre-existing external data: ADVANCE only when blocker-first permits entry

Claim boundary: this is capability validation of the court. It is not biological validation of a specific future project dataset, not user-generated omics, and not direct causal or molecular validation.

## Final closure gate

This file intentionally does not declare v0.7 authoritative by itself. The newest `main` commit containing this provenance record must run the ordinary capability suite. v0.7 becomes the authoritative baseline only if all ordinary jobs pass on that exact `main` head. Any failure becomes the next OPEN blocker and must be resolved before phase advancement.
