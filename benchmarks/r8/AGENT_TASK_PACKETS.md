# R8 Sanitized Blind Agent Task Packets

These packets are the **agent-visible task descriptions** for the primary blind cohort.

They intentionally omit:

- accepted repair commits;
- repair PRs;
- maintainer root-cause comments;
- evaluator oracle implementation;
- future source history.

The evaluator must provide only the packet for the benchmark being run.

---

# Common instruction — all benchmarks

Diagnose and repair the reported defect in this repository. Inspect the code before editing. Preserve unrelated behavior. Use the available local development tools and the provided verification interface. Do not disable or weaken tests, remove the affected feature, hard-code the benchmark fixture, or bypass the verification gate.

Before editing, write a concise diagnosis hypothesis and implementation plan. After editing, report changed files, rationale, checks run, external verification result, and remaining uncertainty. Do not claim success until external verification is green.

---

# B01 — Android scoped filesystem synchronization

## Observed behavior

On Android, filesystem synchronization regressed after an application update. A fresh profile can point to an existing filesystem sync directory, but downloaded items are not created locally during the delta phase. Re-running sync repeatedly fetches the same items.

The equivalent filesystem behavior on other supported environments should remain intact.

## Reproduction model

A filesystem driver receives a scoped Android parent URI and child entry URI representing a file inside that parent.

Example conceptual values:

- parent: `content://provider/tree/root`
- child: `content://provider/tree/root/file.md`

Callers of the directory-stat API expect child paths to be expressed relative to the requested parent.

## Expected behavior

- Android scoped-directory enumeration returns the correct relative file path.
- Existing non-scoped path normalization continues to work.
- Do not special-case the benchmark filename.

## Constraints

Keep the change focused on filesystem path/stat normalization. Do not bypass synchronization logic or disable scoped-storage behavior.

---

# B02 — Parameterized token-selector memoization

## Observed behavior

A parameterized selector used by token-list items performs avoidable result recomputations when equivalent parameter values reappear after another token has been selected. Returned token data is semantically correct, but the selector does not reuse computation as intended across the parameter sequence.

## Reproduction model

Given stable application state and two parameter sets A and B:

1. call selector with A;
2. call selector with B;
3. call selector with a **new parameter object whose values are equivalent to A**.

The third call should be able to reuse the appropriate cached computation rather than recomputing the result again.

## Expected behavior

- Semantic token selection remains unchanged.
- Consecutive equivalent parameters remain memoized.
- A -> B -> equivalent-A does not perform an unnecessary third result recomputation.
- Do not add a benchmark-specific cache or hard-code token addresses.

## Constraints

Preserve selector API behavior for callers. Avoid broad token-list refactors unless the evidence shows they are necessary.

---

# B03 — Native Esperanto locale crash

## Observed behavior

On the native mobile application, changing the app language to Esperanto can cause the language-related UI to crash. Entering other supported languages such as Spanish works. The failure also affects other UI paths that initialize the same internationalization support.

## Reproduction

1. On native mobile, change application language to Esperanto.
2. Open the content-language selector or another screen that needs localized language/territory display names.
3. Observe a crash/failure.
4. Repeat with a normal supported language as a control; it should work.

## Expected behavior

- Esperanto no longer crashes the application.
- Other locale functionality remains intact.
- Do not remove Esperanto support globally.
- Use a constrained compatibility strategy if the failure comes from third-party locale data rather than inventing translations.

## Constraints

Do not suppress all internationalization errors or disable the DisplayNames feature for every language.

---

# B04 — Android crash on malformed Markdown table

## Observed behavior

A malformed Markdown table can freeze/crash the Android mobile application. A reported crash includes a maximum-regex-stack-depth style failure. Web behavior is different, and valid Markdown tables must continue to render correctly.

## Regression fixture

```text
| A | B | C | | |
| :--------------------------------: | :----------------------------: | :----------------- --------------: | :-----------: |:-----------: |
|D | E | F | G | H |
| | J | K | | |
```

The third delimiter cell contains an invalid internal space.

## Expected behavior

- The malformed input must not crash the mobile application.
- It should not be accepted as a valid table delimiter row.
- A normal valid table must still parse as a table.
- Trace the parser/dependency boundary if the defect is not implemented directly in the mobile repository.

## Constraints

Do not merely catch and ignore every parser exception. Preserve ordinary Markdown rendering.

---

# B05 — ALT indicator missing inside quoted posts

## Observed behavior

Images with non-empty alternative text normally display an `ALT` indicator. When the same image is rendered inside a quoted post, the indicator is missing.

Quoted-post image sizing/cropping behavior itself should remain unchanged.

## Expected behavior

- Images with ALT text inside quoted posts display the ALT indicator.
- Single-image and multi-image/grid quote paths preserve the semantic indicator.
- Normal, non-quoted image behavior remains unchanged.
- Images with no ALT text must not gain a fake ALT indicator.
- Quote-specific layout/cropping must continue to work.

## Constraints

Do not solve the issue by removing quote-specific image layout rules. Keep accessibility/semantic display logic separate from layout state where appropriate.

---

# B06 — Newly added transaction network missing from asset polling

## Observed behavior

When a user starts a transaction from a dapp on a network that was not previously enabled/permitted, the wallet can add the network but fail to load the relevant balance immediately. The transaction cannot proceed until another navigation path causes balances to refresh.

## Reproduction model

- Existing enabled EVM polling chains include two normal chains.
- A transaction is created on a third EVM chain that is not currently present in the normal polling-chain collection.
- Non-EVM chains may also be present in the broader source-chain list and must not be treated as EVM polling targets.

## Expected behavior

- The current transaction's EVM chain participates in the required asset/balance polling.
- Existing EVM polling chains remain present.
- Duplicate chain IDs are not introduced.
- Non-EVM chains remain filtered appropriately.

## Constraints

Do not globally enable arbitrary networks or hard-code a specific chain ID.

---

# B07 — Offline Album View ignores available local asset

## Observed behavior

In the mobile photo application, an asset that exists both remotely and on the Android device can use the local copy in the main timeline, but Album View may still attempt to load it from the server. Offline, the image therefore fails to appear in Album View even though the local asset exists.

## Reproduction model

Fixture relationships:

- album: `album-1`
- remote asset: `remote-1`
- local asset: `local-1`
- local and remote asset represent the same underlying media item
- remote asset belongs to `album-1`

## Expected behavior

- Album query still returns the remote album asset.
- Returned domain asset is associated with the matching local asset when one exists.
- Album membership filtering remains correct.
- The local association must not cause the valid album row to disappear.

## Constraints

Do not make every remote asset appear in every album. Preserve ordering, filtering, pagination, and remote-only behavior.

---

# B08 — iOS editor jumps to previous selection after keyboard dismissal

## Observed behavior

In a long Markdown document on iOS:

1. enter edit mode;
2. dismiss the keyboard;
3. scroll away from the existing cursor/selection;
4. tap the editor at the new location to reopen the keyboard;
5. the editor can jump/scroll back toward the previous selection.

The editor still needs to refresh its inline Markdown decorations after pointer/touch interaction.

## Expected behavior

- Tapping a new position must not rewrite the selection back toward the old cursor location.
- Inline-decoration refresh still occurs.
- Existing rendering behavior should remain intact.
- Avoid mouse/touch-event workarounds that manually fight native selection unless evidence requires them.

## Constraints

Do not disable inline Markdown rendering or remove decoration refresh entirely.

---

# Agent completion template

Use this exact structure at the end of every run:

```text
Diagnosis:

Plan:

Files changed:

Verification performed:

External verification state:

Remaining uncertainty:

Evidence-backed completion: YES / NO
```
