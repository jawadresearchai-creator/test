# Agriculture CoScientist `test` — Capability Validation Report

Date: 2026-09-03
Status: isolated test build; existing production CoScientist is not the intended write target.

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
- Repository-adapter contract for GEO/SRA/Expression Atlas style backends.
- GEO accession stub/path planning.
- Data-representation planner that prefers raw counts over FASTQ unless read-level analysis is required.
- Package installs offline using the available local build toolchain when build isolation is disabled.
- CLI capability probe.

## Automated validation

24 tests pass in the current isolated kernel.

## Live external probes

### GEO discovery
The live search layer found public wheat-root RNA-seq datasets and processed count files. GSE235844 provides root/leaf wheat expression resources and sample-level processed count/TPM files. GSE183508, public on 2026-08-15, contains wheat-root control vs 10g hypergravity RNA-seq with two replicates per group.

For a soil-compaction/mechanical-signalling question, the kernel classifies GSE183508 as **mechanistically compatible (C)** rather than directly comparable, because species and tissue match while the treatment and developmental context do not directly match.

## Current blockers

### B1 — RESOLVED — separate GitHub repository
The isolated private repository `jawadresearchai-creator/test` now exists and is the deployment target.

### B2 — ACTIVE VALIDATION — R worker
The chat-local runtime has no R. The isolated `test` repository now provisions R in GitHub Actions and validates DESeq2, edgeR, limma, WGCNA and GEOquery there.

### B3 — MEDIUM — binary public-data download in this chat runtime
Live repository discovery and metadata retrieval work. Direct binary supplementary-file downloads are constrained by the chat/container URL-safety boundary. The production worker should perform network downloads from frozen accession-derived URLs and hash them on arrival.

### B4 — MEDIUM — production annotation/enrichment adapters not implemented
The kernel can orchestrate pathway/network stages, but production-grade wheat gene-ID harmonization and GO/pathway annotation-source adapters still need implementation and validation.

### B5 — LOW/MEDIUM — live journal-policy refresh is not yet automated
The journal gate exists and a dated PS&B scope snapshot is now included and tested. What remains is an automated retrieval/versioning adapter for official submission instructions and future policy changes.

## Infrastructure observed locally

- Python 3.13.5: available
- git: available
- R: unavailable
- numpy/pandas/scipy/statsmodels/scikit-learn/networkx/Biopython/requests/pytest: available

## Next build order

1. Bootstrap the isolated kernel into `jawadresearchai-creator/test` without touching production CoScientist.
2. Run the GitHub Actions Python/R/live-public-data capability suite.
3. Capture package/session evidence and then pin/lock the validated environment.
4. Implement real GEO/SRA/Expression Atlas metadata/download adapters.
5. Implement wheat gene-ID harmonization + GO/pathway adapters.
6. Add DESeq2/edgeR/limma production workflows and WGCNA/network validation.
7. Add live official journal-policy retrieval/versioning.
8. Add end-to-end scenario tests: public-data-only, hybrid, and physical-experiment modes.
9. Add provenance bundle generation, hostile-review court, and submission-package checks.
