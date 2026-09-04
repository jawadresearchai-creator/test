import pytest

from agri_coscientist.blockers import (
    Blocker,
    BlockerClass,
    BlockerGate,
    BlockerState,
    PhaseBlockedError,
)


def _blocking() -> Blocker:
    return Blocker(
        blocker_id="RUNNER_UNAVAILABLE",
        description="GitHub-hosted runner is not assigned",
        blocker_class=BlockerClass.BLOCKING,
        resolution_criterion="A fresh workflow job is assigned a runner and executes at least one step",
        verification_method="Inspect authoritative GitHub Actions job evidence",
    )


def test_open_blocker_stops_phase_advancement():
    gate = BlockerGate([_blocking()])
    with pytest.raises(PhaseBlockedError, match="RUNNER_UNAVAILABLE"):
        gate.assert_can_advance(from_phase="v0.4 execution", to_phase="v0.5")


def test_documenting_blocker_does_not_resolve_it():
    blocker = _blocking()
    blocker.evidence.append("runner_id=0; zero steps")
    gate = BlockerGate([blocker])
    assert gate.get("RUNNER_UNAVAILABLE").state is BlockerState.OPEN
    with pytest.raises(PhaseBlockedError):
        gate.assert_can_advance(from_phase="current", to_phase="next")


def test_verified_resolution_reopens_progression():
    gate = BlockerGate([_blocking()])
    gate.resolve(
        "RUNNER_UNAVAILABLE",
        verification_evidence="workflow run 123 assigned ubuntu-latest and completed checkout step",
    )
    assert gate.get("RUNNER_UNAVAILABLE").state is BlockerState.RESOLVED
    gate.assert_can_advance(from_phase="v0.4 execution", to_phase="post-execution audit")


def test_empty_resolution_evidence_cannot_clear_blocker():
    gate = BlockerGate([_blocking()])
    with pytest.raises(ValueError):
        gate.resolve("RUNNER_UNAVAILABLE", verification_evidence="   ")
    assert gate.get("RUNNER_UNAVAILABLE").state is BlockerState.OPEN


def test_only_explicit_human_waiver_can_bypass_blocker():
    gate = BlockerGate([_blocking()])
    gate.waive(
        "RUNNER_UNAVAILABLE",
        human_authority="user",
        reason="Explicitly accept proceeding without hosted-runner execution",
    )
    blocker = gate.get("RUNNER_UNAVAILABLE")
    assert blocker.state is BlockerState.WAIVED
    assert blocker.waiver_authority == "user"
    gate.assert_can_advance(from_phase="blocked", to_phase="next")


def test_waiver_requires_human_authority_and_reason():
    gate = BlockerGate([_blocking()])
    with pytest.raises(ValueError):
        gate.waive("RUNNER_UNAVAILABLE", human_authority="", reason="go")
    with pytest.raises(ValueError):
        gate.waive("RUNNER_UNAVAILABLE", human_authority="user", reason="")


def test_non_blocking_issue_does_not_stop_progression():
    informational = Blocker(
        blocker_id="DOC_REFRESH",
        description="Journal policy snapshot could be refreshed",
        blocker_class=BlockerClass.NON_BLOCKING,
        resolution_criterion="Refresh policy snapshot",
        verification_method="Compare official journal page revision",
    )
    gate = BlockerGate([informational])
    gate.assert_can_advance(from_phase="analysis", to_phase="publication")


def test_snapshot_is_deterministic_and_preserves_resolution_fields():
    a = _blocking()
    b = Blocker(
        blocker_id="A_SECOND",
        description="Second issue",
        blocker_class=BlockerClass.NON_BLOCKING,
        resolution_criterion="criterion",
        verification_method="method",
    )
    gate = BlockerGate([a, b])
    snap = gate.snapshot()
    assert [row["blocker_id"] for row in snap] == ["A_SECOND", "RUNNER_UNAVAILABLE"]
    assert snap[1]["state"] == "OPEN"
    assert snap[1]["resolution_criterion"].startswith("A fresh workflow job")
