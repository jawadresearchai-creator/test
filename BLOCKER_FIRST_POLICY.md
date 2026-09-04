# Agriculture CoScientist — Blocker-First Progression Policy

Status: governing policy for the isolated `test` CoScientist.

## Rule

When a condition is classified as **BLOCKING**, the CoScientist must not advance to a downstream scientific or development phase merely because other work remains possible.

While a blocking issue is OPEN, allowed autonomous work is limited to:

1. diagnose the blocker;
2. identify the root cause;
3. implement a repair or alternate resolution;
4. verify the resolution against explicit evidence;
5. rerun the exact blocked step.

Downstream phase advancement is prohibited until either:

- the blocker is marked **RESOLVED** with verification evidence satisfying its predeclared resolution criterion; or
- the user/human scientific authority explicitly marks it **WAIVED** and records the reason.

Merely documenting, classifying, commenting on, or working around a blocker does **not** resolve it.

## Required blocker record

Every blocking issue must carry:

- stable blocker ID;
- description;
- root-cause hypothesis/evidence;
- resolution criterion;
- verification method;
- current state: `OPEN`, `RESOLVED`, or `WAIVED`;
- resolution evidence, or explicit human waiver authority and reason.

## Resolved blocker record — RUNNER_UNAVAILABLE

- Class: `BLOCKING`
- State: `RESOLVED`
- Original evidence: while `jawadresearchai-creator/test` was private, repeated GitHub Actions attempts created jobs with no assigned runner and zero executed steps.
- Resolution action: the user explicitly authorized and performed the repository visibility change from private to public on 2026-09-04.
- Resolution criterion: a fresh authoritative workflow job must receive a GitHub-hosted runner and execute at least one workflow step.
- Verification evidence: repository visibility was confirmed as `public`; rerun job `100915918034` immediately received a runner and executed setup/checkout/Python steps; PR #3 workflow run `33838652324` subsequently assigned runners to all five jobs and completed every job successfully, including the real v0.4 public-omics workflow.
- Scientific verification: the real v0.4 job downloaded/froze the public count assets, created the pre-outcome Analysis Lock, executed DESeq2, executed exact-build g:Profiler enrichment, passed the hostile audit, and uploaded the retained evidence artifact.
- Resolution conclusion: `RUNNER_UNAVAILABLE` is resolved. It must not be reopened merely because an individual future job fails for a code, provider, or scientific reason; those require their own blocker records.

## Current blocking state

No blocking issue is currently OPEN as of the v0.4 merge closure. Any newly discovered blocking issue must be registered before downstream phase advancement.
