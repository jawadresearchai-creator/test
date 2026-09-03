# test — Agriculture CoScientist isolated capability build

This project is deliberately isolated from the existing `coscientist` repository.

## Scope of v0.1 capability tests

- sovereign project state machine with backward repair paths;
- hard rejection of gate skipping;
- public-omics data-fitness grading;
- dataset/file freezing with SHA-256 tamper detection;
- deterministic analysis-lock hashing;
- evidence/claim-strength calibration;
- explicit policy split between unavailable new wet-lab omics and legitimate public-omics reanalysis.

No scientific dataset is treated as evidence merely because it appears in a test fixture.

## Authoritative capability worker

GitHub Actions in this repository is the authoritative clean execution environment for this isolated build. The capability workflow independently tests the Python kernel, production R omics packages (DESeq2, edgeR, limma, WGCNA, GEOquery), and live retrieval of small public wheat GEO data. Large FASTQ/SRA retrieval is deliberately excluded from routine CI.
