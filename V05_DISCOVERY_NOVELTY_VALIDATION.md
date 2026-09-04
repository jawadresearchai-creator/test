# Agriculture CoScientist — v0.5 Discovery / Novelty Court Validation

Date: 2026-09-04
Status: **VALIDATED / MERGED / EVIDENCE COMPLETE**
Repository: `jawadresearchai-creator/test`
Merged PR: #4
Merge commit: `53dbfa13c89a1dd6734e2db9f1d3df228086a694`
Validated feature head: `b0c47773e0f1b8cd107ed7fec58ebfc8126a9c2b`
Authoritative validation workflow run: `33845559947`

## Capability added

v0.5 adds an executable literature Discovery / Novelty Court with:

- Europe PMC adapter;
- OpenAlex adapter;
- Crossref adapter;
- normalized DOI/PMID/title deduplication;
- original/review/preprint/other classification;
- retraction flag retention;
- frozen date windows and query families;
- deterministic search-snapshot hashing;
- concept-ontology overlap assessment;
- direct-prior and strong-prior verdicts;
- structured evolution actions when novelty is threatened;
- explicit negative-evidence coverage semantics.

## Blocker discovered and resolved during validation

The first live v0.5 run showed that Crossref `query.bibliographic` searches could return very large relevance-ranked universes while only the top 100 records were retrieved. Example: the exact-question capability query returned more than 237,000 Crossref hits while only 100 were retrieved.

That made Crossref absence unsuitable as evidence that no prior work exists. The blocker was not waived or bypassed.

Resolution implemented:

1. Crossref remains available for **positive prior-art and metadata discovery**.
2. Crossref is explicitly `negative_evidence_eligible=false`.
3. Europe PMC and OpenAlex are the required negative-evidence providers.
4. Every required Europe PMC/OpenAlex query family must be exhaustively retrieved before a negative novelty inference is allowed.
5. Positive evidence is asymmetric: a direct original/preprint prior can block novelty even if another provider is incomplete.
6. Absence evidence is conservative: incomplete/missing/ineligible searches force `INSUFFICIENT_COVERAGE`.
7. DOI and PMID normalization moved to the `LiteratureRecord` boundary so cross-provider duplicates cannot evade deduplication through different URL/case forms.

## Frozen capability scenario

Scenario: `wheat_root_mechanical_eatp_neighbor_priming_capability`

Date window: 2024–2026

Required query families:

- `exact_question`
- `mechanism`
- `crop_system`
- `adjacent_concept`

Required providers:

- Europe PMC
- OpenAlex
- Crossref

Required negative-evidence providers:

- Europe PMC
- OpenAlex

Crossref is positive-evidence-only for absence semantics.

## Live evidence

Workflow run `33845559947` passed:

- `python-kernel`
- `literature-novelty-live`
- `r-omics`
- `public-data-live`
- `annotation-enrichment-live`

The v0.4 real-public-omics job was correctly skipped because this PR was not the v0.4 real-data execution branch.

Live literature artifact:

- artifact ID: `9926396988`
- artifact name: `live-literature-novelty-evidence`
- artifact ZIP SHA-256: `61152c49943e778a3a857fa28ff7503481e0fee0296dac1198f6eea5c7743ec9`
- `live_literature_novelty.json` SHA-256: `053072850436bbb2a2b24c538b34fe53839289f23f4af8f20928536c4e51590c`
- frozen search snapshot SHA-256: `f4a4507dad71965a0fbd32d3e1d45b10f73f0eb9acfe9362bae58826f56cf0e3`

## Negative-evidence coverage actually observed

Every required Europe PMC/OpenAlex absence-evidence search was exhaustive:

| Query family | Europe PMC | OpenAlex |
|---|---:|---:|
| exact_question | 0 / 0 | 0 / 0 |
| mechanism | 7 / 7 | 12 / 12 |
| crop_system | 12 / 12 | 172 / 172 |
| adjacent_concept | 2 / 2 | 2 / 2 |

Each cell is `retrieved / total_hits`.

All four Crossref searches were truncated and therefore correctly prohibited from absence inference:

- exact_question: 100 / 237328
- mechanism: 100 / 65008
- crop_system: 100 / 268111
- adjacent_concept: 100 / 105393

## Capability verdict

The live court returned:

`no_direct_prior_found_within_frozen_search_scope`

This means only:

> No direct prior was identified within the frozen 2024–2026 providers, query families, and exhaustively retrieved negative-evidence searches.

It does **not** mean:

- absolute novelty has been proven;
- the wheat/eATP capability scenario is automatically publishable;
- citation chasing, older literature, patents, theses, datasets, or future searches are unnecessary;
- absence in Crossref top-ranked results proves absence from Crossref;
- a real research candidate may bypass deeper novelty, feasibility, data, design, and journal-fit courts.

## Governance rule retained

OPEN blockers remain phase-stopping. A discovered blocker may leave OPEN state only after its predeclared resolution criterion is satisfied by evidence, or through an explicit human waiver with authority and reason.

## Final closure gate

After this validation record and the corrected CI step label are committed to `main`, the latest `main` ordinary capability suite must pass before v0.5 becomes the authoritative validated baseline. Any failure in that suite becomes the next OPEN blocker and must be resolved before further phase advancement.
