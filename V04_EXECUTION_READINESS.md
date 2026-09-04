# Agriculture CoScientist `test` — v0.4 Execution Readiness

Date: 2026-09-04
Branch: `feature/v0.4-real-public-omics`
Status: **CODE HARDENED / REAL EXECUTION PENDING**
Authoritative baseline: `main` remains validated v0.3.0 at `f289cdd98d20de396ad2bc16c7b1a02c01c19a42` and is not modified by this branch until v0.4 passes real-data execution and audit.

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

NCBI GEO and current Ensembl Plants independently identify this exact IWGSC/GCA_900519105.1 wheat assembly.

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
- g:Profiler identifier-recognition QC uses **g:Convert -> ENSG**, not enrichment `effective_domain_size`
- minimum unambiguous mapping coverage: 0.90 for the tested-gene background and 0.90 for each non-empty directional candidate query
- one-to-many identifier conversions are classified as ambiguous and do not count as successfully mapped

## featureCounts ingestion hardening

The pre-outcome Python parser and R executor recognize standard featureCounts annotation columns:

`Geneid, Chr, Start, End, Strand, Length`

Only remaining columns are treated as sample-count columns. This prevents chromosome/start/end/strand fields from being misinterpreted as expression counts.

Additional safeguards:

- exactly three count columns are required in each selected file;
- unknown extra columns are not silently discarded;
- counts must be finite, non-negative integers;
- duplicate `Geneid` values are rejected;
- if Rawal-87 and Sonalika contain the same genes in different row order, the second table is deterministically aligned by `Geneid`;
- genuinely different gene universes are a hard failure.

## Pre-outcome provenance boundary

The implemented order is:

1. Run the deterministic Python kernel + v0.4 contract suite before outcome access.
2. Install and verify the exact frozen Python scientific-package versions.
3. Verify the frozen scenario-specific R environment.
4. Download the two public featureCounts assets.
5. Freeze URL, byte count, SHA-256 and header/replicate structure while inspecting no gene-level rows.
6. Preserve and hash the exact scenario manifest.
7. Hash every transitive scientific code dependency used by the run, including preparation, DESeq2, enrichment, final audit, kernel scenario/annotation/enrichment modules, `pyproject.toml`, the default capability dispatcher, and the reusable v0.4 workflow.
8. Hash the frozen Python and scenario-specific R environment locks.
9. Bind the Analysis Lock to the exact GitHub repository, commit SHA, workflow run ID/attempt, workflow/workflow ref and git ref.
10. Write `PRE_OUTCOME_LOCK_COMPLETE.json` with `count_rows_inspected=false`.
11. Record machine-readable Python and R runtime-version evidence bound to the same GitHub commit/run.
12. Only after the lock exists may the R executor read gene-level count rows.

The scientific workflow runs source code through `PYTHONPATH=src` and installs exact frozen Python dependencies directly from `python-stack-lock.json`; it does not perform an editable package build during the scientific execution. Package-build/install behavior remains part of the ordinary repository capability suite at the eventual merge gate.

## Correct pre-merge execution path

GitHub requires a `workflow_dispatch` workflow to exist on the default branch before it can receive manual dispatch events. Therefore the feature-only v0.4 workflow is **not used directly as the pre-merge dispatch anchor**.

The safe pre-merge path is:

1. Use existing `.github/workflows/capability.yml`, which exists on `main` and has `workflow_dispatch`.
2. Select branch `feature/v0.4-real-public-omics` when manually dispatching that workflow.
3. The feature-branch version of `capability.yml` skips the ordinary v0.3 jobs for this exact v0.4 manual dispatch.
4. It calls `./.github/workflows/v04-real-public-omics.yml` from the same feature commit with a required boolean `workflow_call` input.
5. The reusable workflow performs the complete locked real-data execution.

After v0.4 is eventually merged, `v04-real-public-omics.yml` may also be directly manually dispatched because it will then exist on the default branch.

## Enrichment and identifier-mapping QC

Identifier mapping and statistical enrichment are deliberately separate concepts.

Before GO interpretation:

1. g:Convert maps the complete tested-gene background to Ensembl genes in chunks.
2. Only one-to-one/unambiguous mappings count as successful.
3. mapped + unmapped + ambiguous categories must exactly partition the input list.
4. unambiguous mapping fraction must be >= 0.90.
5. each non-empty up/down candidate query receives the same g:Convert check and >=0.90 threshold.
6. hashes and examples of unmapped/ambiguous identifiers are retained in run evidence.
7. g:GOSt is then run with the original locked background, `domain_scope=custom`, FDR correction, and `all_results=true` for provider metadata/QC.
8. `effective_domain_size` is retained only as a hypergeometric statistical-domain diagnostic and is never used as an identifier-mapping coverage metric.

This correction was made after checking current g:Profiler documentation, which explicitly defines `effective_domain_size` as a hypergeometric universe parameter and g:Convert as the identifier mapping service.

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
- g:Convert background and directional query coverage;
- exact partitioning into unambiguous, unmapped and ambiguous ID categories;
- provider metadata retention;
- proof that enrichment-domain size was not used as the mapping metric;
- directional enrichment result counts and FDR thresholds;
- final artifact byte counts and SHA-256 values.

The final audit also enforces the claim boundary: this run may demonstrate capability and exploratory genotype-associated transcriptomic differences in the public dataset, but it cannot be represented as a new wet-lab gene-expression experiment, causal validation, or a novel paper by itself.

## Validation completed without the blocked worker

Static/targeted checks completed while GitHub-hosted runners are unavailable:

- earlier v0.4-specific offline Python regression slice passed 22/22 before the newest mapping-QC additions;
- standard featureCounts annotation-column handling was subsequently tested in a focused local parser check;
- g:Convert classification logic was subsequently tested in a focused local logic check: two unambiguous mappings, one unmapped ID, and one ambiguous one-to-many ID were classified correctly;
- current NCBI GEO records confirm both selected count files are featureCounts-generated root RNA-seq count files with three biological replicates and IWGSC/GCA_900519105.1;
- current Ensembl Plants release 63 independently confirms `Triticum_aestivum` assembly IWGSC / GCA_900519105.1.

These targeted checks do **not** substitute for branch CI or the real six-sample workflow.

## Current blocker

GitHub-hosted runners for this private repository are still not being assigned as of 2026-09-04. A fresh rerun probe again produced jobs with no executed steps. This proves no scientific code was run in those attempts.

The connected GitHub interface does not expose the private account-side diagnostic explaining the rejection. Private-repository Actions allowance/billing/budget or an Actions policy restriction remain plausible leading causes, but are not confirmed from available tool evidence.

The chat/container cannot substitute as the authoritative R worker: R/Rscript, conda/mamba and cached apt R packages are absent, and managed retrieval of the exact NCBI binary supplementary URLs is restricted.

No PR is opened for v0.4 while this condition remains.

## Validation status

- validated `main` v0.3.0: 37/37 Python contracts and all four authoritative capability jobs passed before the runner block
- newest v0.4 deterministic contracts, including g:Convert mapping tests: **written but not yet executed as branch CI**
- v0.4 real NCBI downloads: **not yet executed in the locked workflow**
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
6. actual featureCounts structure/replicate checks pass;
7. six-sample DESeq2 execution passes;
8. exact IWGSC build sentinel validation passes;
9. g:Convert background and directional query mapping coverage pass the locked 0.90 thresholds;
10. custom-background directional g:Profiler enrichment executes;
11. machine-readable Python and R runtime evidence matches the locks and exact GitHub execution context;
12. hostile final audit returns `PASS`;
13. `BUNDLE_MANIFEST.json` is produced;
14. the complete workflow artifact is retained as execution evidence;
15. an eventual v0.4 PR/merge candidate passes the ordinary repository capability suite.

Until then, validated `main` v0.3.0 remains the authoritative baseline.
