# Agriculture CoScientist `test` — Capability Validation Report

Date: 2026-09-03
Version: 0.2.0
Status: isolated test build; the production `jawadresearchai-creator/coscientist` repository is not the write target.

## Validated capabilities

- Sovereign project state machine with explicit forward and repair transitions.
- Gate-skipping rejection.
- Public-omics fitness grading with direct-treatment vs mechanistic-match distinction.
- Replication-aware A/B/C/D/E omics fitness classes.
- SHA-256 dataset/file freezing and tamper detection.
- Deterministic analysis-lock hashing.
- Evidence-strength / claim-language calibration.
- Python count-matrix QC, log-CPM, PCA and NB-GLM software smoke analysis.
- Random-effects cross-study meta-analysis.
- Correlation-based co-expression graph and hub detection smoke capability.
- Contradictory-evidence synthesis that prevents one-sided cherry-picking.
- Audit rule preventing contextual/mechanistic omics from being presented as causal validation.
- Generic journal-fit policy gate with provenance requirement.
- GEO accession stub/path and data-representation planning.
- Production read-only `GEOAdapter` inside the kernel using NCBI E-utilities plus GEO family SOFT metadata.
- Live GEO metadata retrieval through both the Python kernel adapter and independent R/GEOquery cross-check.
- Live public count-file download with immutable URL/byte-count/SHA-256/first-line provenance verification.
- Production R omics execution through DESeq2, edgeR, limma-voom and WGCNA.
- Frozen and CI-verified Python and R scientific environments.
- Package install and CLI execution from a clean GitHub checkout.

## Automated validation

**27/27 Python contract tests pass in GitHub Actions.**

The authoritative clean-checkout run `33762112967` passed all three jobs:

1. `python-kernel` — PASS
2. `r-omics` — PASS
3. `public-data-live` — PASS

## Frozen execution evidence

### Python

Validated on Python 3.12.14 with the direct scientific stack frozen in `environments/python-stack-lock.json`:

- networkx 3.6.1
- numpy 2.5.2
- pandas 3.0.5
- scipy 1.18.1
- scikit-learn 1.9.0
- statsmodels 0.15.0
- pytest 9.1.1

### R / Bioconductor

Validated on R 4.6.1 with `environments/r-stack-lock.json`:

- DESeq2 1.52.0
- edgeR 4.10.4
- limma 3.68.5
- WGCNA 1.74
- GEOquery 2.80.0
- jsonlite 2.0.0

The R smoke pipeline executed all major code paths on a deterministic synthetic count matrix rather than merely importing packages.

## Live public-omics evidence

### Immutable wheat-root count-file probe

The GitHub worker downloaded:

`GSM7510647_counts-Inquilab-91-roots.txt.gz`

Observed and frozen properties:

- bytes: 892,452
- SHA-256: `e53005a6a1d64d941609d1101512c76a3749916a1dd196498ada20394d528ccd`
- first line: `Geneid\tInquilab_91_rep1_root\tInquilab_91_rep3_root\tLength`

The live job now fails if any of these frozen provenance properties drift.

### GSE183508 live metadata

The kernel `GEOAdapter` and R/GEOquery independently resolved:

- accession: GSE183508
- organism: Triticum aestivum
- title: `Transcriptome profile of hypergravity-induced enhanced wheat root growth`
- samples: 4
- raw data available: yes
- processed data available: yes

For a soil-compaction/mechanical-signalling question this remains **C — mechanistically compatible**, not directly comparable.

## Blocker status

### B1 — RESOLVED — separate repository

The isolated private repository `jawadresearchai-creator/test` is operational.

### B2 — RESOLVED — authoritative R worker

GitHub Actions successfully executes the frozen R/Bioconductor omics stack.

### B3 — RESOLVED FOR AUTHORITATIVE WORKER — public binary retrieval

The GitHub worker can download, inspect, hash and freeze real GEO supplementary data. Chat-local URL restrictions are no longer a scientific blocker because GitHub Actions is the authoritative execution worker.

### B4 — ACTIVE — production gene-ID harmonization and enrichment

The next major capability gap is build-aware wheat gene-ID validation/harmonization and GO/pathway enrichment. Wheat has multiple assemblies/cultivars, so the system must not silently mix annotations. Annotation build identity will be mandatory project state.

### B5 — LOW/MEDIUM — live journal-policy refresh

The journal-fit gate and dated PS&B scope snapshot exist. Automatic official-policy refresh/versioning remains to be implemented.

## Next build order

1. Implement a build-aware gene annotation contract and Ensembl/Gramene adapters.
2. Make genome/annotation identity mandatory before any enrichment analysis.
3. Implement reproducible GO enrichment with an explicit background universe and multiple-testing correction.
4. Add Plant Reactome/pathway support where the exact species/build mapping is defensible.
5. Add real GEO/SRA/Expression Atlas discovery breadth beyond the first GEO adapter.
6. Add end-to-end public-data-only and hybrid-study scenario tests.
7. Add provenance bundle generation, hostile-review court, and submission-package checks.
8. Add automated journal-policy refresh/versioning.
