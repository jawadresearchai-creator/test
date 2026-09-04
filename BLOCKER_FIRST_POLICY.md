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

## Current blocker

`RUNNER_UNAVAILABLE`

- Class: `BLOCKING`
- State: `OPEN`
- Evidence: recent GitHub Actions attempts create jobs with no assigned runner and zero executed steps.
- Current resolution attempt: change `jawadresearchai-creator/test` from private to public so standard GitHub-hosted runners no longer consume the private-repository Actions minute quota.
- Resolution criterion: a fresh authoritative workflow job receives a GitHub-hosted runner and executes at least one workflow step.
- Verification method: inspect the GitHub Actions job evidence through the connected GitHub API.

Until this resolution criterion passes, v0.4 must not advance to v0.5 or another downstream phase.
