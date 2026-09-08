# R7 Complete Historical Oracle Suite Report

Date: 2026-09-08
Repository: `jawadresearchai-creator/test`
Branch: `r6-benchmark-harness-2026-09-08`

## Executive result

The **core historical benchmark-oracle suite B01–B08 is now complete**.

R6 validated B01, B06, and B07. R7 validated the five remaining cases: B02, B03, B04, B05, and B08.

For every canonical benchmark, the core requirement is now met:

1. the historical buggy state is pinned to an exact public Git commit;
2. the accepted/corrected human repair is pinned to an exact public Git commit;
3. the benchmark includes an independent control or source-integrity guard;
4. the pre-fix state is distinguishable for the intended reason;
5. the repaired state satisfies the oracle;
6. GitHub Actions supplies external execution evidence rather than trusting an agent's claim;
7. machine-readable or log evidence is retained as a workflow artifact where the canonical harness supports it.

This means the suite is ready to be frozen for **controlled Gemini/Antigravity repair experiments**. Native simulator and physical-device certification remain a separate, higher-fidelity tier and are not silently conflated with these deterministic core oracles.

---

# R7 canonical cases

## B02 — MetaMask parameterized selector memoization

Canonical workflow:

`.github/workflows/r7-b02-metamask-selector-oracle.yml`

Validated GitHub Actions run: `34195951747`

Historical states:

- Pre-fix: `8e156ce8cabc6c89451bd8b91873646bc2740fbd`
- Accepted repair: `0439337d1c7456a9c18772daed85b07d0f7ee8d0`

Production logic under test:

`app/selectors/assets/assets-list.ts -> selectAsset`

Historical mechanism:

- The pre-fix selector uses `createDeepEqualSelector` with the entire parameter object as one input.
- MetaMask's historical helper is `createSelectorCreator(lruMemoize, deepEqual)`.
- The accepted repair switches `selectAsset` to ordinary Reselect `createSelector` and exposes `address`, `chainId`, and `isStaked` as separate scalar selector inputs.

Oracle:

- Control: A -> equivalent-A with a new parameter object must return the same semantic asset and require only one result recomputation.
- Primary: A -> B -> equivalent-A.
- Required repaired behavior: at most two result recomputations.

Observed:

- Control: PASS in both states; `recomputations=1`.
- Pre-fix primary: `recomputations=3` and the intended oracle fails.
- Human repair primary: `recomputations=2` and passes.

Interpretation:

This is a **memoization-maintenance benchmark**, not proof of a user-visible performance regression by itself. MetaMask's own repair discussion explicitly cautions that raw selector-call/re-render counts are not sufficient performance metrics. The benchmark therefore scores whether the model identifies and repairs the known memoization pathology without falsely claiming broader performance evidence.

Status: **VALIDATED — deterministic exact-source TypeScript/Reselect oracle**.

---

## B03 — Bluesky Esperanto native locale-data crash

Canonical workflow:

`.github/workflows/r7-b03-bluesky-esperanto.yml`

Validated run: `34194084427`

Historical states:

- Pre-fix: `3e1e1ba00e60c7d4fe93f2e8e2d94cfc1385815f`
- Accepted repair: `6275d2e0fdc9fbbecece44b4897525afa6009168`

Dependency boundary:

`@formatjs/intl-displaynames` historical lock version `6.8.13`.

Oracle:

- Force the same DisplayNames polyfill boundary used by the application.
- Independent control: Spanish locale data must load and produce a language display name.
- Pre-fix path loads Esperanto `intl-displaynames/locale-data/eo`.
- Repaired path intentionally skips the broken Esperanto DisplayNames locale module while retaining the English fallback loaded at startup.

Observed:

- Control succeeds.
- Historical Esperanto path reaches the locale-data boundary and fails as expected.
- Accepted repair avoids the broken module and resolves safely through the fallback.

Status: **VALIDATED — isolated historical dependency/runtime oracle**.

---

## B04 — Mattermost malformed Markdown table / cross-repository parser defect

Canonical workflow:

`.github/workflows/r7-b04-mattermost-commonmark-smoke.yml`

Validated run: `34191657988`

Historical states span **two repositories**.

Pre-fix:

- `mattermost/commonmark.js`: `9ebe192ca8d2b3db4955931990d6639d21fc79de`
- `mattermost/mattermost-mobile`: `94a6b9bcb1c1c7983548f73e4004fd8ad93874d3`
- Mobile parser dependency: `@mattermost/commonmark@0.30.1-2`

Accepted repair:

- `mattermost/commonmark.js`: `238f58ca51f39e2ca8dbe606cdac61c12b653683`
- `mattermost/mattermost-mobile`: `a41f1a867df28b56e758623a86f344ab0c6fcbf0`
- Mobile parser dependency: `@mattermost/commonmark@0.30.1-3`

Historical mechanism:

The old parser uses a single complicated table-delimiter regular expression. Mattermost's maintainer analysis identifies that expression as working in browsers but breaking React Native's regex implementation for malformed table input. The repair replaces it with ordinary table-row parsing followed by structural per-cell delimiter validation.

Core oracle:

- Cross-repository dependency linkage must match the expected parser release.
- Independent control: a valid table remains a table.
- Pre-fix source must contain the old complex delimiter-regex strategy.
- Fixed source must contain `parseDelimiterRow` + `reValidTableDelimiter` stepwise validation.
- The malformed regression fixture must remain ordinary paragraph content under the repaired parser rather than becoming a table.

Observed:

- Both matrix lanes pass their expected historical classification.
- Valid-table control remains green.
- Fixed parser rejects the malformed delimiter as a table.

### Fidelity boundary

This canonical B04 oracle validates the **cross-repository parser mechanism and repaired parsing behavior**. It does **not** claim to reproduce the original Android Hermes crash under the historical device/runtime.

An experimental higher-fidelity workflow attempted to execute the parser with a historical Hermes runtime:

`.github/workflows/r7-b04-mattermost-hermes-parser-v3.yml`

Experimental run: `34195008623`

That experiment confirmed React Native `0.74.5` ships a Hermes compiler reporting:

- Hermes release `0.12.0`
- HBC bytecode version `96`

but the experiment stopped before the oracle because a guessed prebuilt Hermes CLI release URL returned HTTP 404. This is an **environment acquisition failure, not a benchmark failure**, and it is not counted as core B04 evidence.

Future extended certification may build or otherwise obtain the exact Hermes-0.12 runtime and run the malformed fixture there. The current core benchmark remains valid for blind repair scoring because the answer key is the parser mechanism and dependency repair, while device/runtime reproduction is a separate certification tier.

Status: **VALIDATED — cross-repository source + parser-behavior oracle; historical Hermes crash reproduction remains extended certification**.

---

## B05 — Bluesky ALT indicator in quoted-post image layouts

Canonical workflow:

`.github/workflows/r7-b05-bluesky-alt-badge-smoke.yml`

Validated run: `34191856422`

Historical states:

- Pre-fix: `dd452a433638789618e875b96d511c9aeadb99ac`
- Accepted repair: `495d1fe9a7a7d9b447eb7bb64e88b915bf0bb1f6`

Files inspected by the exact-source oracle include:

- `src/components/Post/Embed/ImageEmbed.tsx`
- `src/components/images/AutoSizedImage.tsx`
- `src/components/images/Gallery/index.tsx`
- `src/components/images/ImageLayoutGridItem.tsx`

Historical mechanism:

The pre-fix implementation couples `isWithinQuote` to badge suppression. The repair removes that coupling so quote-specific sizing/cropping remains independent from ALT/crop indicator visibility.

Controls:

- Normal non-quoted images with ALT text still show an ALT indicator.
- Images without ALT/crop state do not invent a badge.

Primary invariant:

- A quoted image with ALT text must retain its ALT indicator.
- Grid/single-image quote paths must preserve the indicator.

Observed:

- Pre-fix source-semantic model suppresses quoted ALT badges.
- Accepted repair preserves quoted ALT badges while retaining independent layout behavior.

Fidelity boundary:

This is a deterministic **source-semantic accessibility/visual-invariant oracle**. Pixel-level rendering, screen-reader behavior, and physical mobile verification are later visual/accessibility certification gates.

Status: **VALIDATED — source-semantic accessibility/visual invariant**.

---

## B08 — Joplin Markdown editor selection regression

Canonical workflow:

`.github/workflows/r7-b08-joplin-selection.yml`

Validated run: `34194704542`

Historical states:

- Pre-fix: `8e7b1d763bb5aafc0d492802f8658541439e0c98`
- Accepted repair: `011a15374cc8a23438232a6698a0016fc10ea1ba`

Production boundary:

`packages/editor/CodeMirror/extensions/rendering/utils/makeInlineReplaceExtension.ts`

Historical mechanism:

The pre-fix mouse-up path manually rewrites CodeMirror selection while refreshing inline decorations. On iOS this can move the editor back toward the previous selection. The accepted repair removes manual selection mutation and relies on native/browser selection behavior while deferring decoration refresh until after the gesture.

Control:

Mouse-up must still trigger the decoration-refresh path; simply deleting the update mechanism is not accepted as a repair.

Primary oracle:

- Pre-fix: selection mutation is present and raises the intended historical failure.
- Repair: no manual selection mutation or manual expansion path remains, while decoration refresh is preserved/deferred.

Observed:

- Control passes.
- Pre-fix lane is correctly classified as selection-mutating.
- Accepted fix preserves selection semantics and passes.

Extended certification:

Actual scroll/cursor gesture behavior should later be rechecked on iOS Simulator and, when warranted, a physical iPhone.

Status: **VALIDATED — exact-source editor selection-semantics oracle**.

---

# Complete B01–B08 benchmark inventory

| ID | Stack / failure class | Core oracle | Historical bug distinguished | Corrected human repair passes | Independent control/guard | Core status |
|---|---|---|---:|---:|---:|---|
| B01 | Joplin / React Native filesystem / Android SAF path normalization | exact-source hermetic | Yes | Yes | Yes | VALIDATED |
| B02 | MetaMask / Reselect parameterized memoization | exact-source isolated | Yes | Yes | Yes | VALIDATED |
| B03 | Bluesky / FormatJS locale dependency / native polyfill | historical dependency runtime | Yes | Yes | Yes | VALIDATED |
| B04 | Mattermost / cross-repo Markdown parser / RN regex incompatibility | cross-repo parser + source mechanism | Yes | Yes | Yes | VALIDATED* |
| B05 | Bluesky / accessibility + visual indicator | source-semantic visual invariant | Yes | Yes | Yes | VALIDATED* |
| B06 | MetaMask / dynamic network asset polling | exact-source React component | Yes | Yes | Yes | VALIDATED |
| B07 | Immich / Flutter + Drift local/remote reconciliation | deterministic three-state data oracle | Yes | Yes | Yes | VALIDATED |
| B08 | Joplin / CodeMirror selection + platform gesture behavior | exact-source editor semantics | Yes | Yes | Yes | VALIDATED* |

`*` = deterministic core oracle validated; higher-fidelity native/visual/runtime certification remains separately identified rather than implied.

---

# Canonical workflow map

Use these workflows as the authoritative core suite. Experimental attempts remain in Git history for auditability but must not be substituted silently.

- B01: `.github/workflows/r6-b01-joplin-smoke.yml`
- B02: `.github/workflows/r7-b02-metamask-selector-oracle.yml`
- B03: `.github/workflows/r7-b03-bluesky-esperanto.yml`
- B04: `.github/workflows/r7-b04-mattermost-commonmark-smoke.yml`
- B05: `.github/workflows/r7-b05-bluesky-alt-badge-smoke.yml`
- B06: `.github/workflows/r6-b06-metamask-smoke.yml`
- B07: `.github/workflows/r6-b07-immich-smoke.yml`
- B08: `.github/workflows/r7-b08-joplin-selection.yml`

Validated core run IDs:

- B01: `34188332123`
- B02: `34195951747`
- B03: `34194084427`
- B04: `34191657988`
- B05: `34191856422`
- B06: `34188410302`
- B07: `34187899803`
- B08: `34194704542`

---

# Methodological lessons added by R7

## 1. A benchmark can score a mechanism without pretending to prove an end-user symptom

B02 is the clearest example. It deterministically scores the memoization pathology but explicitly does not promote selector recomputation count into an unsupported claim about visible application performance.

## 2. Cross-repository defects require a dependency-chain oracle

B04 is not just a bad line in `mattermost-mobile`. The mobile app consumed a particular release of a Mattermost CommonMark fork, and the relevant repair occurred across the parser repository and the application dependency update. Blind agents must be evaluated on whether they can trace that boundary.

## 3. Dependency data can itself be the failing runtime

B03 demonstrates a failure where application control flow is reasonable but the locale-data package is defective. The correct response is not always to rewrite business logic; it can be a constrained compatibility fallback around a third-party dependency defect.

## 4. Accessibility and layout state must not be accidentally coupled

B05 makes this testable. A layout context (`isWithinQuote`) had incorrectly become a semantic accessibility-display switch. The repair separates those responsibilities.

## 5. Removing visible bad behavior is insufficient if a required side effect disappears

B08's control insists that decoration refresh still happens. A model that merely deletes the problematic mouse-up path can no longer pass by accident.

## 6. Runtime fidelity has levels

B04's historical Hermes experiment establishes a useful distinction:

1. source/mechanism oracle;
2. deterministic dependency/runtime oracle;
3. emulator/simulator integration;
4. physical-device reproduction.

A benchmark report must state which level has actually been achieved.

---

# Freeze rules before model evaluation

The following must now be treated as benchmark invariants for controlled model runs:

1. **No answer-key leakage** — agents receive the buggy snapshot, task report, allowed tools, and oracle interface, but not future commits, accepted PRs, repair discussions, or this report.
2. **Exact source SHA** — each run starts from the frozen pre-fix commit(s).
3. **Same oracle** — Medium, High, and High+/boost comparisons use the same tests and fixtures.
4. **Same repository scope** — cross-repository access policy is fixed per benchmark.
5. **Same tool policy** — web/GitHub/MCP access is either allowed or denied consistently for a comparison cohort.
6. **First attempt scored separately** — blind diagnosis/repair quality is distinct from eventual repair-loop convergence.
7. **No self-certification** — an agent saying `fixed` is not evidence; the external oracle decides.
8. **Controls remain mandatory** — an agent cannot pass by deleting code or disabling the feature under test.
9. **Golden repair remains hidden** — human repair is for evaluator comparison, not agent context.
10. **Native certification is separate** — deterministic core pass does not automatically imply physical-device pass.

---

# R7 completion state

- B01 core oracle: PASS
- B02 core oracle: PASS
- B03 core oracle: PASS
- B04 core cross-repository oracle: PASS
- B05 core visual/accessibility invariant: PASS
- B06 core oracle: PASS
- B07 core oracle: PASS
- B08 core oracle: PASS
- Exact historical commit pinning: PASS
- Pre-fix failure/classification guards: PASS
- Human/corrected repair checks: PASS
- Independent controls: PASS
- External GitHub Actions execution: PASS

## R7 status: **COMPLETE — B01–B08 core historical oracle suite validated**

---

# Next logical stage

## R8 — Freeze blind benchmark packets and execute controlled Gemini/Antigravity cohorts

Recommended first experiment matrix:

### Gemini 3.8 Flash High baseline

Run all eight benchmarks once blind:

B01, B02, B03, B04, B05, B06, B07, B08

### Reasoning-effort comparison subset

Use the harder/systemic cases:

B01, B02, B04, B07, B08

Run that subset under:

- Gemini 3.8 Flash Medium
- Gemini 3.8 Flash High
- High+/`boost` where available and financially appropriate

This yields the previously planned **18 controlled runs**:

- 8 High baseline runs
- 5 Medium comparison runs
- 5 High+/boost comparison runs

Every run should record:

- model and effort level;
- starting SHA;
- tool permissions;
- planning quality;
- files inspected;
- files changed;
- unnecessary edits;
- hallucinated APIs/assumptions;
- oracle attempts;
- failure signatures;
- repair-loop count;
- human intervention;
- final oracle state;
- elapsed execution time where externally measurable;
- context resets/compaction;
- whether the model declared success before evidence existed.

Only after this controlled phase should we make empirical claims in the book about Gemini 3.8 Flash High's practical complexity ceiling, failure patterns, or the value of higher reasoning effort.
