# Agriculture CoScientist `test` — v0.4 Validation Record

Date: 2026-09-04
Status: **VALIDATED / MERGED / EVIDENCE COMPLETE**
Repository: `jawadresearchai-creator/test`
Repository visibility during successful validation: `public`
Merged baseline commit: `9039b1408af5f02828ecdf9d56e6aaf23afd49f2`
Validation PR: #3 `v0.4 real public omics validation`
Authoritative validation run: `33838652324`

## Outcome

v0.4 passed its complete real-public-omics merge gate. The authoritative PR workflow executed five jobs, all successful:

1. `python-kernel`
2. `r-omics`
3. `public-data-live`
4. `annotation-enrichment-live`
5. `v04-real-public-omics / real-public-omics`

The real v0.4 job passed every scientific/provenance stage in order:

`frozen Python contracts -> frozen R stack -> real asset download/freeze -> pre-outcome Analysis Lock -> runtime evidence -> DESeq2 -> exact-build enrichment -> hostile audit -> evidence artifact`

## Capability scenario

Scenario: `GSE235844_Rawal87_vs_Sonalika_roots_v1`

Purpose: capability validation on genuine public RNA-seq counts. This run is not a novel wet-lab study and must not be represented as user-generated gene-expression data.

Locked comparison:

- Rawal-87 roots: GSM7510657, 3 biological count columns
- Sonalika roots: GSM7510660, 3 biological count columns
- species: *Triticum aestivum*
- tissue: root
- representation: featureCounts integer counts
- genome assembly: `IWGSC`
- assembly accession: `GCA_900519105.1`
- g:Profiler organism: `taestivum`

## Frozen public assets

Rawal-87:

- bytes: `991849`
- SHA-256: `f6a3d073d8bcae1854ed2835e45f4f709b77f99976969c7d322409f0029fff2b`
- header: `Geneid, Rawal_87_rep1_root, Rawal_87_rep2_root, Rawal_87_rep3_root, Length`

Sonalika:

- bytes: `993280`
- SHA-256: `b8283bfb2ecec07d0055a86156a5a68cc99fcb0478a095c3f9a9a2a759fa9c1a`
- header: `Geneid, Sonalika_rep1_root, Sonalika_rep2_root, Sonalika_rep3_root, Length`

`PRE_OUTCOME_LOCK_COMPLETE.json` records `count_rows_inspected=false` before outcome analysis.

## Locked differential-expression policy

- DESeq2 design: `~ genotype`
- contrast: Sonalika vs Rawal-87
- fixed prefilter: total count >= 10 across six samples
- independent filtering: disabled
- Cook's-distance result exclusion: disabled
- automatic outlier-count replacement: disabled
- `minReplicatesForReplace=Inf`
- outlier policy: report diagnostically; do not silently exclude or replace
- multiple testing: Benjamini-Hochberg
- FDR threshold: 0.05
- enrichment candidate threshold: padj <= 0.05 and |log2FC| >= 1

## Real DESeq2 result

- genes before prefilter: `120744`
- tested genes after prefilter: `66972`
- samples: `6`
- replicates/group: `3 + 3`
- enrichment candidates: `1905`
- up in Sonalika vs Rawal-87: `1198`
- down in Sonalika vs Rawal-87: `707`

These are capability-run results and are not, by themselves, a novelty or causal claim.

## Build-aware enrichment result

Identifier recognition is measured with `g:Convert -> ENSG`; statistical `effective_domain_size` is not used as an identifier-mapping metric.

- tested-background mapping: `66972 / 66972 = 1.0`
- up-query mapping: `1198 / 1198 = 1.0`
- down-query mapping: `707 / 707 = 1.0`
- significant GO terms, up: `144`
- significant GO terms, down: `61`
- exact-build sentinel: `TraesCS3B02G271600`
- observed assembly: `IWGSC`
- sentinel sequence region: `3B`

Provider version evidence:

- g:Profiler organism: `taestivum`
- g:Profiler genebuild: `IWGSC`
- organism-specific g:Profiler version: `e114_eg59_p19_27110d83`
- BioMart: EnsemblPlants 59
- GO release: `2026-01-23`

## Provenance and hostile audit

The hostile audit returned `PASS` and independently verified:

- dataset bytes and SHA-256 hashes;
- pre-outcome Analysis Lock;
- exact GitHub execution context;
- transitive code/environment hashes;
- Python and R runtime evidence;
- fixed prefilter/BH/outlier policy;
- candidate reconstruction from the full DE table;
- custom enrichment-background identity;
- g:Convert mapping coverage and partitioning;
- genome-build binding;
- g:Profiler provider metadata;
- directional enrichment integrity;
- distinction between mapping coverage and statistical domain size.

Evidence identifiers:

- PR workflow run: `33838652324`
- PR merge execution SHA: `3d1d9b600b7289ef60606d0d5b542f93c3d25a10`
- retained artifact ID: `9924199412`
- artifact name: `v04-real-public-omics-33838652324`
- GitHub artifact digest: `sha256:0a7fb68fdf0ee7eb35f8873f90eb275b73539fae167e1ebd329aecc21ced3255`
- dataset-freeze SHA-256: `a11e60ad3e7e96fec99d53aa15d09a98b6ca8ce768a6b184c534dcb6c992d082`
- Analysis-Lock SHA-256: `f8b72aba1db802ed0e54523766bc9752df8fb6934affc24efc13df4bec748a40`
- bundle SHA-256: `2e69bbcb5d4dad70868511398e4e2d6715d77ba3f8c1dde36ae2bb6fe7db6959`

The downloaded artifact was independently rehashed after retrieval; every file listed in `BUNDLE_MANIFEST.json` matched its recorded SHA-256.

## Claim boundary

Allowed:

- capability demonstration;
- exploratory genotype-associated transcriptomic differences in this public dataset;
- evidence that the CoScientist can execute the locked public-omics workflow reproducibly.

Prohibited:

- claiming the user generated these RNA-seq measurements;
- claiming this capability scenario itself is a novel study;
- causal validation from transcriptomic association alone;
- describing public omics as new wet-lab measurements.

## Infrastructure blocker closure

`RUNNER_UNAVAILABLE` is **RESOLVED**. The repository was changed from private to public with explicit user authorization. GitHub then assigned hosted runners immediately, and the complete v0.4 validation run executed successfully.

## Authoritative baseline

v0.4 is merged. `main` at merge commit `9039b1408af5f02828ecdf9d56e6aaf23afd49f2` supersedes v0.3 as the Agriculture CoScientist `test` scientific baseline, subject to the final ordinary `main` capability run after closure-document commits.
