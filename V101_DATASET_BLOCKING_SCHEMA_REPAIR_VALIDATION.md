# v1.0.1 Dataset Freeze Blocking-Factor Schema Repair — Immutable Validation Record

## Authority and blocker

- Repository: `jawadresearchai-creator/test`
- Previous authoritative baseline: `cbd78149b9708ecc8c58a2462581be1fde263814` (v1.0 Analysis Specification Court + Analysis Lock)
- Blocking issue: #10 — `BLOCKING: Dataset Freeze does not require Design-Freeze blocking-factor fields`
- Repair pull request: #11 — `v1.0.1 blocker repair: freeze Design blocking-factor fields`
- Validated repair head: `27a5b8a19300e1519664d1d79f4dee4e88a3c0e6`
- Merge commit: `dd31e6bec5d53a6d11f6042ab20ac7549a87b10f`
- Authoritative repair PR workflow run: `33870081311`

This record is deliberately committed after the repair merge. The commit containing this file is the candidate v1.0.1 repair provenance head and must itself pass a fresh ordinary `main` CI run before issue #10 can be closed and downstream Research Computation can resume.

## Defect proved by post-v1.0 audit

The frozen Study Design declared `bench_position` as a physical blocking factor. The v1.0 Analysis Specification correctly required `bench_position` in the locked confirmatory model and adjustment terms. However, the v0.9 Dataset Freeze field-contract helper required only outcomes, covariates, and metadata fields; it did not add `physical.blocking_factors`.

Consequently, a Dataset Freeze and Analysis Lock could both receive ADVANCE verdicts even when the exact blocking variable required by the locked model was absent from every frozen project-data schema. Such a state is scientifically and computationally non-executable and violated the intended reproducibility contract.

No downstream Analysis Execution code was advanced after discovery. Issue #10 became the sole OPEN `BLOCKING` issue and work was restricted to diagnosis, repair, and verification.

## Repair

The general Dataset Freeze field contract now includes every Design-Freeze physical blocking factor in the required frozen project-data fields. The capability/test fixtures now freeze `bench_position`, and a dedicated adversarial case removes that field and requires the Dataset Freeze court to BLOCK.

This repair does not select or execute a statistical model. It makes the frozen dataset contract sufficient to contain the design fields that a later valid Analysis Specification may require.

## Exact-head CI evidence

Workflow run `33870081311` executed on exact repair head `27a5b8a19300e1519664d1d79f4dee4e88a3c0e6`.

Passed ordinary jobs:

- `python-kernel`
- `dataset-freeze-court`
- `analysis-specification-lock-court`
- `study-design-freeze-court`
- `general-data-fitness-court`
- `feasibility-route-court`
- `literature-novelty-live`
- `annotation-enrichment-live`
- `r-omics`
- `public-data-live`

`v04-real-public-omics` was skipped as intended for ordinary execution.

## Retained repair artifact

- Artifact ID: `9935517408`
- Artifact name: `dataset-freeze-capability-evidence`
- Artifact ZIP SHA256: `ff9eb1efbc5c54cf3b6ae5a6ffbb7e8c1c6a199724c6e9fa8b27e51a90d242e1`
- Extracted `dataset_freeze_capability.json` SHA256: `fbf41ee17d66bfa79b9b7345456c40b15d936b868a5f3c443d8929b4f886601f`
- Design Freeze SHA256: `980b52eb573499fcbbc5c2e0c30422a9949bdcfdba74f42fa2b13b9a7c5edc90`
- Repaired Dataset Freeze SHA256: `45e1c33a587d1f0f9df69f7ae6da7616545b3df885855d3c5624fcfc8c57a2be`

The downloaded artifact ZIP independently matched GitHub's recorded artifact digest.

## Repair capability verdict

The retained artifact reported:

- `court_status = advance`
- `advancement_allowed = true`
- deterministic Dataset Freeze hash = true
- confirmatory outcome blind = true
- planned physical independent units = 12
- retained physical independent units = 12
- excluded physical independent units = 0
- frozen blocking factors include `bench_position`
- public reused data remains `mechanistic_support_only_not_direct_validation`
- state after Dataset Freeze = `dataset_frozen`
- direct `DATASET_FROZEN -> ANALYSIS_LOCKED` skipping remains blocked

## Adversarial coverage

All Dataset Freeze attacks in the repair artifact were blocked, including the new execution-critical case:

- `missing_blocking_factor_schema_field`
- `missing_prespecified_schema_field`
- `missing_public_dataset`
- `missing_public_version`
- `outcome_peeking`
- `posthoc_exclusion`
- `undeclared_public_dataset`
- `unit_accounting_mismatch`
- `wrong_design_binding`

The new `missing_blocking_factor_schema_field` attack specifically proves that removing `bench_position` from the frozen project schema prevents Dataset Freeze advancement.

## Scientific boundary

This repair establishes dataset identity and executable design-field provenance only. It does not claim Analysis Execution, statistical result correctness, or biological validation.

The public-data boundary is unchanged: public omics or other reused datasets may provide appropriately qualified mechanistic/contextual support but are not direct validation of physical experimental units.

No unavailable qPCR, RT-qPCR, new wet-lab RNA-seq/transcriptomics, or other gene-expression-dependent physical experimental pathway is introduced by this repair.

## Merge protection

PR #11 was merged only against expected repair head:

`27a5b8a19300e1519664d1d79f4dee4e88a3c0e6`

Merge commit:

`dd31e6bec5d53a6d11f6042ab20ac7549a87b10f`

Issue #10 intentionally remains OPEN at the moment this record is created.

## Final closure gate

The v1.0.1 repair becomes authoritative/evidence-closed only after all of the following occur on the exact commit containing this validation record:

1. Canonical Google Drive state is reconciled to the merge and candidate provenance head.
2. A fresh ordinary push CI run executes on that exact `main` SHA.
3. All ordinary jobs pass, including Dataset Freeze and Analysis Specification/Lock courts.
4. `v04-real-public-omics` remains skipped unless explicitly invoked under its dedicated trigger contract.
5. Issue #10 is closed only after the exact-main CI proof succeeds.
6. The repository then contains zero OPEN issues labeled `BLOCKING`.

If the fresh `main` run fails, issue #10 remains the sole blocker; downstream Research Computation must remain paused while the defect is repaired and revalidated.
