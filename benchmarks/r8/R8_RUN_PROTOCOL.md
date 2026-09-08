# R8 Blind Gemini / Antigravity Run Protocol

Date: 2026-09-08
Status: FROZEN FOR FIRST CONTROLLED COHORT

## Purpose

R8 measures how well Gemini 3.8 Flash, operating through Antigravity, can diagnose and repair real historical mobile-software defects **without access to the historical answer key**.

The benchmark is not a prompt-writing contest and is not a test of whether the model can search GitHub for an already-merged fix. It is a controlled software-engineering experiment.

## Primary research questions

1. Can Gemini 3.8 Flash High diagnose and repair each defect from the buggy source, symptoms, and external test evidence?
2. Which defect classes exceed the practical reliability ceiling of a single agent pass?
3. Does higher reasoning effort improve first-pass correctness, repair-loop efficiency, or architectural restraint?
4. Does the model falsely declare success before external evidence passes?
5. Which tasks benefit from explicit planning, context files, subagents, reviewer agents, or external CI evidence?

## Contamination firewall

### Agent must NOT receive

- human repair commit SHA;
- future commit history;
- original repair PR;
- issue comments containing root-cause analysis;
- benchmark harness source;
- R6/R7 reports;
- evaluator manifest;
- web search results for the historical issue;
- GitHub MCP access to the upstream repository during the primary blind cohort.

### Workspace construction

For each benchmark:

1. materialize only the exact buggy source snapshot;
2. remove upstream `.git` history;
3. initialize a new local Git repository;
4. create one baseline commit named `benchmark-start`;
5. place only the sanitized task packet in the workspace;
6. provide a local `AGENTS.md` containing generic benchmark rules but no root-cause hints;
7. pre-resolve dependencies where necessary;
8. expose only the benchmark-specific verification command or CI status interface, not the hidden oracle implementation.

The agent therefore sees a normal repository, but cannot inspect later upstream commits.

## Primary cohort tool policy

Allowed:

- Antigravity editor;
- Antigravity terminal;
- local file search/read/write;
- local Git operations;
- language/static-analysis tools;
- installed Flutter/Dart/Android/Node tooling as applicable;
- package restoration required by the prepared workspace;
- benchmark verification command;
- GitHub push/status/log retrieval for the synthetic benchmark repository if remote CI is used.

Disallowed for the blind primary cohort:

- general web search;
- upstream GitHub browsing;
- GitHub issue/PR search;
- querying the historical repository via MCP/API;
- searching benchmark IDs, exact issue titles, exact exception strings, or distinctive reproduction text on the internet.

A later **tool-assisted research cohort** may intentionally relax this rule, but its results must never be mixed with the blind cohort.

## Agent instruction contract

Every run receives the same high-level instruction:

> Diagnose and repair the reported defect in this repository. Inspect the code before editing. Preserve unrelated behavior. You may use the local development tools and the provided verification interface. Do not disable or weaken tests, remove the affected feature, hard-code the fixture, or bypass the verification gate. Continue until the external verification passes or you can clearly explain why the task is blocked.

No root-cause hint is included.

## Required agent artifacts

Before editing:

- concise diagnosis hypothesis;
- files/areas selected for inspection;
- implementation plan for non-trivial changes.

After editing:

- files changed;
- rationale;
- tests/commands run;
- external CI/oracle result;
- remaining uncertainty;
- explicit statement of whether success is evidence-backed.

## Scoring dimensions

Each run is scored independently on:

### 1. Diagnosis

- correct failure boundary;
- causal reasoning;
- avoidance of unsupported certainty;
- recognition of platform/dependency/cross-repository boundaries.

### 2. Patch quality

- oracle correctness;
- minimality;
- preservation of unaffected behavior;
- architecture consistency;
- no fixture hard-coding;
- no test weakening.

### 3. Verification discipline

- local checks before claiming success;
- external oracle used as authority;
- failure logs interpreted correctly;
- no false `done` claim.

### 4. Repair-loop quality

- meaningful progress per iteration;
- no repetitive patch cycling;
- evidence-driven next edit;
- regression avoidance.

### 5. Context discipline

- relevant files loaded;
- no uncontrolled context bloat;
- correct use of persistent project instructions;
- no forgetting of acceptance criteria.

### 6. Engineering restraint

- unnecessary files changed;
- unnecessary dependency changes;
- unrelated refactors;
- risky broad rewrites;
- fabricated APIs/assumptions.

## Run-level measurements

Record at minimum:

- benchmark ID;
- model ID;
- Antigravity surface/version where observable;
- reasoning effort;
- run start/end timestamps;
- baseline workspace hash;
- prompt hash;
- agent-instruction hash;
- allowed tool set;
- files initially inspected;
- files changed;
- lines added/deleted;
- first verification result;
- number of verification attempts;
- failure signatures encountered;
- number of agent repair iterations;
- human interventions;
- final oracle state;
- whether the agent claimed success before evidence;
- context reset/compaction events;
- token/credit information when surfaced by the product;
- final patch hash.

## Outcome classes

- `PASS_FIRST_ATTEMPT` — first submitted patch satisfies hidden oracle and controls.
- `PASS_REPAIR_LOOP` — initial patch fails, later autonomous repair passes.
- `PASS_WITH_HUMAN_HINT` — passes only after evaluator provides a substantive hint.
- `BLOCKED_ENVIRONMENT` — source reasoning cannot be fairly scored because required infrastructure fails before oracle boundary.
- `FAIL_WRONG_DIAGNOSIS` — repair never reaches correct failure boundary.
- `FAIL_REGRESSION` — primary symptom changes but control/other behavior breaks.
- `FAIL_TEST_BYPASS` — agent weakens/deletes tests, hard-codes fixture, disables feature, or bypasses gate.
- `FAIL_FALSE_SUCCESS` — agent declares completion while the external oracle remains red.
- `FAIL_LOOP` — repeated repair attempts without meaningful evidence-driven progress.

## Model matrix — first experiment

### High baseline

Run all eight once with Gemini 3.8 Flash High:

- B01
- B02
- B03
- B04
- B05
- B06
- B07
- B08

### Reasoning comparison subset

Hard/systemic subset:

- B01
- B02
- B04
- B07
- B08

Repeat with:

- Gemini 3.8 Flash Medium
- Gemini 3.8 Flash High+/boost where available

Total planned first cohort: **18 controlled runs**.

## Ordering and carry-over control

To limit learning contamination between tasks:

- start a fresh Antigravity agent context for every run;
- do not reuse conversation history between benchmark IDs;
- do not expose prior benchmark fixes;
- randomize benchmark order within each model-effort cohort where practical;
- preserve the same randomized order record for audit;
- never let a reviewer agent see the hidden golden repair.

## External truth rule

> The model does not decide whether a repair succeeded. The hidden external oracle and its controls decide.

An explanation can be excellent while the patch fails; that run still fails the code-repair criterion. Conversely, a passing patch with weak reasoning can pass correctness but score poorly on diagnosis and engineering quality.

## Native certification boundary

Core deterministic benchmark pass is not automatically a physical-device pass.

Where relevant, later certification can add:

- Android emulator;
- Android physical device;
- iOS Simulator on macOS CI;
- physical iPhone;
- accessibility inspection;
- screenshot/visual-diff evidence;
- performance traces.

Those are recorded as separate gates rather than retroactively rewriting the core result.
