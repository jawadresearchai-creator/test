# Agriculture CoScientist `test` — v0.4 Execution Readiness

Date: 2026-09-03
Branch: `feature/v0.4-real-public-omics`
Status: **CODE COMPLETE / REAL EXECUTION PENDING**
Authoritative baseline: `main` remains validated v0.3.0 and is not modified by this branch until v0.4 passes real-data execution and audit.

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

1. Run the deterministic Python kernel + v0.4 contract suite before outcome access.
2. Verify the frozen Python and scenario-specific R environments.
3. Download the two public featureCounts assets.
4. Freeze URL, byte count, SHA-256 and header/replicate structure while inspecting no gene-level rows.
5. Preserve and hash the exact scenario manifest.
6. Hash every transitive scientific code dependency used by the run, including preparation, DESeq2, enrichment, final audit, kernel scenario/annotation/enrichment modules, `pyproject.toml`, the default capability dispatcher, and the reusable v0.4 workflow.
7. Hash the frozen Python and scenario-specific R environment locks.
8. Bind the Analysis Lock to the exact GitHub repository, commit SHA, workflow run ID/attempt, workflow/workflow ref and git ref.
9. Write `PRE_OUTCOME_LOCK_COMPLETE.json` with `count_rows_inspected=false`.
10. Record machine-readable Python and R runtime-version evidence bound to the same GitHub commit/run.
11. Only after the lock exists may the R executor read gene-level count rows.

## Correct pre-merge execution path

GitHub requires a `workflow_dispatch` workflow to exist on the default branch before it can receive manual dispatch events. Therefore the feature-only v0.4 workflow is **not used directly as the pre-merge dispatch anchor**.

The safe pre-merge path is:

1. Use the existing `.github/workflows/capability.yml`, which already exists on `main` and has `workflow_dispatch`.
2. Select branch `feature/v0.4-real-public-omics` when manually dispatching that workflow.
3. The feature-branch version of `capability.yml` skips the ordinary v0.3 Python/R/GEO/annotation jobs for this exact manual branch dispatch.
4. It calls the single reusable workflow `./.github/workflows/v04-real-public-omics.yml` from the same feature commit.
5. The reusable workflow performs the complete locked real-data execution.

This avoids duplicating the scientific workflow and lets the feature code be validated before merge while keeping `main` at v0.3.0.

After v0.4 is eventually merged, `.github/workflows/v04-real-public-omics.yml` also supports direct `workflow_dispatch` from the default branch for reproducible reruns.

## Real execution sequence

The reusable v0.4 workflow performs:

`contract tests -> environment verification -> dataset freeze -> Analysis Lock -> exact runtime evidence -> DESeq2 -> exact-build enrichment -> hostile bundle audit -> artifact upload`

The standalone v0.4 workflow has no push, pull-request, or schedule trigger. The pre-merge caller is the existing default-branch capability workflow targeted at the feature ref.

## Hostile final audit

`v04_verify_bundle.py` independently verifies:

- exact manifest bytes against the Analysis Lock;
- dataset-freeze and Analysis-Lock self-hashes;
- frozen public-file byte counts and SHA-256 hashes;
- exact GitHub execution context;
- every transitive code hash and environment-lock hash;
- machine-readable Python runtime evidence against the frozen Python environment;
- machine-readable R, DESeq2 and jsonlite runtime evidence against the frozen scenario-specific R environment;
- human-readable R `sessionInfo()` evidence;
- declared genome assembly/accession binding;
- fixed DESeq2 filtering/outlier/BH policies;
- tested-gene universe size;
- exact reconstruction of up/down enrichment candidates from the full DE table;
- custom enrichment background identity;
- enrichment query sizes;
- final artifact byte counts and SHA-256 values.

The final audit also enforces the claim boundary: this run may demonstrate capability and exploratory genotype-associated transcriptomic differences in the public dataset, but it cannot be represented as a new wet-lab gene-expression experiment, causal validation, or a novel paper by itself.

## Current blocker

GitHub-hosted runners for this private repository are currently not being assigned. Repeated probes, including a fresh single-job rerun probe, produce jobs with `runner_id=0` and zero executed steps. The code is therefore **not considered validated merely because it is written**.

The connected GitHub interface also does not currently expose a workflow-dispatch action, so even after hosted runners become available the pre-merge execution may require using GitHub's Run workflow control unless connector capabilities change.

No PR is opened for v0.4 while the runner condition remains. This prevents pull-request CI from generating additional zero-step failed jobs.

## Validation status

- validated `main` v0.3.0: 37/37 Python contracts and all four authoritative capability jobs passed before the runner block
- v0.4 deterministic contracts: written but **not yet executed**
- v0.4 real NCBI downloads: **not yet executed**
- v0.4 DESeq2 result: **not yet executed**
- v0.4 enrichment result: **not yet executed**
- v0.4 hostile final audit: **not yet executed**

## Merge gate

v0.4 may be merged only after all of the following are true:

1. manual capability workflow targeted at `feature/v0.4-real-public-omics` receives a hosted runner;
2. deterministic Python/kernel v0.4 contracts pass;
3. frozen Python/R environment checks pass;
4. both real NCBI count files download successfully;
5. dataset freeze and pre-outcome Analysis Lock complete;
6. six-sample DESeq2 execution passes;
7. exact IWGSC build sentinel validation passes;
8. custom-background directional g:Profiler enrichment executes;
9. machine-readable Python and R runtime evidence matches the locks and exact GitHub execution context;
10. hostile final audit returns `PASS`;
11. `BUNDLE_MANIFEST.json` is produced;
12. the complete workflow artifact is retained as execution evidence;
13. an eventual v0.4 PR/merge candidate passes the ordinary repository capability suite.

Until then, validated `main` v0.3.0 remains the authoritative baseline.
