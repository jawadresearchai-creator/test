# R6 Historical Benchmark Harness Smoke Test Report

Date: 2026-09-08
Branch: `r6-benchmark-harness-2026-09-08`
Repository: `jawadresearchai-creator/test`

## Result

R6 core smoke-test objective is COMPLETE for pilots B06, B07, and B01 at the deterministic/hermetic oracle level.

The three pilots demonstrated the required historical property: the benchmark oracle distinguishes buggy historical source from the accepted/corrected repair while independent control behavior still passes.

## B06 — MetaMask transaction-chain polling

Workflow: `.github/workflows/r6-b06-metamask-smoke.yml`
Validated run: `34188410302`

Snapshots:
- Pre-fix: `d8e8e568340140f4e50ab9e121378cfcea41e885`
- Accepted fix: `84ca8bd1aa90363d4a3a90c5ae400bebfa225156`

Oracle:
- Bridge EVM chains: `0x1`, `0x2`
- Transaction chain: `0x89`
- Required polling chain list: `['0x1', '0x2', '0x89']`

Observed:
- Control passes on both states: existing EVM bridge chains remain `['0x1', '0x2']`, with no duplicate current chain.
- Pre-fix primary oracle fails for the intended reason: actual chain list omits `0x89`.
- Accepted fix primary oracle passes and includes `0x89`.

Harness note:
- The initial full MetaMask Jest execution proved semantically useful but suffered a post-test heap/teardown failure after the accepted regression tests passed.
- R6 therefore executes the exact historical component source in a small isolated React/Jest environment. This preserves the production logic under test while eliminating unrelated monorepo teardown cost.

Status: **VALIDATED — deterministic Linux oracle**.

## B07 — Immich offline Album View local-asset resolution

Workflow: `.github/workflows/r6-b07-immich-smoke.yml`
Validated run: `34187899803`

Snapshots:
- Pre-fix: `c5fbbee8f68e5c9099710330f9903c4648e14c58`
- First merged fix: `5116b215a240b102d6109ed39d105cad6b77b641`
- Corrected follow-up: `7d8cd05bc2113406d621cc2ed0746b5915d3d3c5`

Oracle fixture:
- Album: `album-1`
- Remote asset: `remote-1`
- Local asset: `local-1`
- Remote/local checksum: `shared-checksum`
- Album relationship: `remote-1 -> album-1`
- Expected query result: one remote asset with `localId == 'local-1'`

Observed:
- Pre-fix: one album asset is returned, but `localId` is `null`.
- First merged fix: zero album assets are returned; this is a regression in the initial maintainer repair.
- Corrected follow-up: one asset is returned and `localId == 'local-1'`.

Historical dependency note:
- The historical custom Isar package host now fails with HTTP 400.
- The harness vendors the historical Immich Isar v3 source (3.1.8) and widens only obsolete Dart SDK metadata so the historical source can resolve under the reconstructed toolchain.
- The application behavior being scored is unchanged.

Status: **VALIDATED — deterministic Flutter/Drift three-state oracle**.

### Important benchmark correction

For B07, `5116b215a240b102d6109ed39d105cad6b77b641` MUST NOT be treated as the golden repair on its own. The validated human repair sequence ends at `7d8cd05bc2113406d621cc2ed0746b5915d3d3c5`.

This establishes a permanent benchmark-design rule:

> Merged does not mean golden. The maintainer fix must be tested against the oracle too.

## B01 — Joplin Android scoped-filesystem regression

Workflow: `.github/workflows/r6-b01-joplin-smoke.yml`
Validated run: `34188332123`

Snapshots:
- Pre-fix: `134064c8296880d63b64ddc6e3743fc6dc926cf7`
- Accepted fix: `385a78dc208ab426b2a0b0abb254e7978e77d8c6`

Control oracle:
- Base path: `/var/mobile/Documents`
- RNFS returned path: `/private/var/mobile/Documents/file.md`
- Expected normalized relative path: `file.md`
- Result: PASS in both historical states.

Primary scoped-Android oracle:
- Parent URI: `content://provider/tree/root`
- Child URI: `content://provider/tree/root/file.md`
- Required returned path: `file.md`

Observed:
- Pre-fix primary oracle fails for the intended reason: received `content://provider/tree/root/file.md` instead of `file.md`.
- Accepted fix primary oracle passes and returns `file.md`.

Status: **VALIDATED — hermetic exact-source oracle**.

Extended native certification remains a separate tier:
- Android emulator / actual SAF integration
- macOS/iOS simulator preservation check
- physical-device certification when warranted

These native tiers do not invalidate the deterministic oracle; they test broader integration behavior.

## R6 conclusions

### Validated pilots

| ID | Platform / stack | Historical bug reproduced | Human/corrected fix passes | Independent control | Core status |
|---|---|---:|---:|---:|---|
| B06 | React Native / MetaMask | Yes | Yes | Yes | VALIDATED |
| B07 | Flutter / Drift / Immich | Yes | Yes | Yes | VALIDATED |
| B01 | React Native filesystem / Joplin | Yes | Yes | Yes | VALIDATED |

### New methodological findings

1. **Exact-source isolated oracles are preferable to heavyweight full-app suites when the bug boundary is narrow.** They reduce CI cost and unrelated teardown failures without replacing later integration gates.
2. **Historical dependency infrastructure can disappear.** Reproducibility sometimes requires vendoring the historical dependency source while documenting every compatibility-only adaptation.
3. **Expected-fail lanes require signature guards.** A failing setup must never be mistaken for reproduction of the historical bug.
4. **Controls are mandatory.** Every expected-fail case needs unaffected behavior that must still pass.
5. **Merged != golden.** B07 experimentally proves that a merged maintainer fix can itself contain a regression.
6. **Three-state historical oracles are valuable:** pre-fix -> incomplete/regressive fix -> corrected fix.

## R6 completion state

- Historical checkout verification: PASS
- Public GitHub Actions execution: PASS
- Exact-source/historical logic execution: PASS
- Pre-fix intended failure signatures: PASS
- Human/corrected repair pass: PASS
- Independent controls: PASS
- Machine-readable JSON evidence artifacts: PASS
- Native-device/simulator extended gates: NOT PART OF CORE R6; still available as later certification tier

## Next logical stage

**R7 — Complete the remaining historical oracle suite:** B02, B03, B04, B05, and B08.

Priority order:
1. B02 MetaMask selector/memoization
2. B03 Bluesky Esperanto locale crash
3. B04 Mattermost cross-repository parser bug
4. B05 Bluesky ALT indicator / accessibility + visual behavior
5. B08 Joplin Markdown selection / editor behavior

Only after all benchmark oracles are validated should the controlled Gemini model runs begin.
