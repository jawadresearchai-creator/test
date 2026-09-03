# Agriculture CoScientist `test` — v0.4 Execution Readiness

Date: 2026-09-03
Branch: `feature/v0.4-real-public-omics`
Status: **CODE COMPLETE / REAL EXECUTION PENDING**
Production baseline: `main` remains v0.3.0 and is not modified by this branch until v0.4 passes real-data execution and audit.

## Capability scenario

Scenario: `GSE235844_Rawal87_vs_Sonalika_roots_v1`

Purpose: exercise the complete public-omics path on genuine public RNA-seq counts without representing the capability run as a novel study or as new wet-lab data.

Locked contrast:

- Rawal-87 roots: GSM7510657, 3 biological count columns
- Sonalika roots: GSM7510660, 3 biological count columns
- species: *Triticum aestivum*
- tissue: root
- conditions: control / optimum growth conditions
- representation: featureCounts integer counts, not TPM/FPKM
- genome assembly: IWGSC
- assembly accession: GCA_900519105.1
- g:Profiler organism: `taestivum`

## Locked scientific analysis

- DESeq2 with design `~ genotype`
- contrast: Sonalika vs Rawal-87
- fixed prefilter: total count >= 10 across the six samples
- DESeq2 independent filtering: disabled
- Cook's-distance result exclusion: disabled
- outlier policy: report diagnostically, do not silently exclude
- multiple testing: Benjamini-Hochberg
- FDR threshold: 0.05
- enrichment candidate threshold: padj <= 0.05 and |log2FC| >= 1
- up- and down-regulated enrichment performed separately
- enrichment background: all genes passing the locked prefilter
- enrichment provider: g:Profiler with custom background and FDR correction
- exact-build sentinel validation through Ensembl REST before functional interpretation

## Pre-outcome provenance boundary

The implemented order is:

1. Download the two public featureCounts assets.
2. Freeze URL, byte count, SHA-256 and header/replicate structure.
3. Preserve and hash the exact scenario manifest.
4. Hash every transitive scientific code dependency used by the run, including preparation, DESeq2, enrichment, final audit, kernel scenario/annotation/enrichment modules, `pyproject.toml`, and the v0.4 workflow.
5. Hash the frozen Python and scenario-specific R environment locks.
6. Bind the Analysis Lock to the exact GitHub repository, commit SHA, workflow run ID/attempt, workflow ref and git ref.
7. Write `PRE_OUTCOME_LOCK_COMPLETE.json` with `count_rows_inspected=false`.
8. Only after the lock exists may the R executor read gene-level count rows.

## Real execution sequence

The manual-only workflow `.github/workflows/v04-real-public-omics.yml` performs:

`environment verification -> dataset freeze -> Analysis Lock -> runtime evidence -> DESeq2 -> exact-build enrichment -> R session evidence -> hostile bundle audit -> artifact upload`

It intentionally has **no push, pull-request or schedule trigger**. It runs only through `workflow_dispatch` with the explicit boolean execution input set to true.

## Hostile final audit

`v04_verify_bundle.py` independently verifies:

- exact manifest bytes against the Analysis Lock;
- dataset-freeze and Analysis-Lock self-hashes;
- frozen public-file byte counts and SHA-256 hashes;
- exact GitHub execution context;
- every transitive code hash and environment-lock hash;
- runtime Python evidence against the frozen Python environment;
- R session evidence presence;
- declared genome assembly/accession binding;
- fixed DESeq2 filtering/outlier/BH policies;
- tested-gene universe size;
- exact reconstruction of up/down enrichment candidates from the full DE table;
- custom enrichment background identity;
- enrichment query sizes;
- final artifact byte counts and SHA-256 values.

The final audit also enforces the claim boundary: this run may demonstrate capability and exploratory genotype-associated transcriptomic differences in the public dataset, but it cannot be represented as a new wet-lab gene-expression experiment, causal validation, or a novel paper by itself.

## Current blocker

GitHub-hosted runners for this private repository are currently not being assigned. Repeated probes produce jobs with `runner_id=0` and zero executed steps. The code is therefore **not considered validated merely because it is written**.

No PR is opened for v0.4 while this condition remains. This prevents the normal pull-request capability workflow from consuming or failing additional hosted-runner attempts.

## Merge gate

v0.4 may be merged only after all of the following are true:

1. manual v0.4 workflow receives a hosted runner;
2. both real NCBI count files download successfully;
3. dataset freeze and pre-outcome Analysis Lock complete;
4. six-sample DESeq2 execution passes;
5. exact IWGSC build sentinel validation passes;
6. custom-background directional g:Profiler enrichment executes;
7. hostile final audit returns `PASS`;
8. `BUNDLE_MANIFEST.json` is produced;
9. the complete workflow artifact is retained as execution evidence;
10. the ordinary repository capability suite is green on the v0.4 PR/merge candidate.

Until then, validated `main` v0.3.0 remains the authoritative baseline.
