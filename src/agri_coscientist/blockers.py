from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class BlockerState(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    WAIVED = "WAIVED"


class BlockerClass(str, Enum):
    BLOCKING = "BLOCKING"
    NON_BLOCKING = "NON_BLOCKING"


class PhaseBlockedError(RuntimeError):
    """Raised when downstream phase advancement is attempted with open blockers."""


@dataclass
class Blocker:
    blocker_id: str
    description: str
    blocker_class: BlockerClass
    resolution_criterion: str
    verification_method: str
    state: BlockerState = BlockerState.OPEN
    evidence: list[str] = field(default_factory=list)
    waiver_authority: str | None = None
    waiver_reason: str | None = None

    @property
    def blocks_advance(self) -> bool:
        return self.blocker_class is BlockerClass.BLOCKING and self.state is BlockerState.OPEN


class BlockerGate:
    """Sovereign blocker-first progression gate.

    A project with any OPEN BLOCKING issue may diagnose, repair and verify that
    blocker, but may not advance to a downstream scientific/development phase.
    A blocker leaves the gate only by verified resolution or an explicit human
    waiver. Merely documenting or classifying the blocker never counts as
    resolution.
    """

    def __init__(self, blockers: Iterable[Blocker] | None = None):
        self._blockers: dict[str, Blocker] = {}
        for blocker in blockers or ():
            self.add(blocker)

    def add(self, blocker: Blocker) -> None:
        if not blocker.blocker_id.strip():
            raise ValueError("blocker_id is required")
        if blocker.blocker_id in self._blockers:
            raise ValueError(f"duplicate blocker_id: {blocker.blocker_id}")
        if not blocker.description.strip():
            raise ValueError("blocker description is required")
        if not blocker.resolution_criterion.strip():
            raise ValueError("resolution criterion is required")
        if not blocker.verification_method.strip():
            raise ValueError("verification method is required")
        self._blockers[blocker.blocker_id] = blocker

    def get(self, blocker_id: str) -> Blocker:
        try:
            return self._blockers[blocker_id]
        except KeyError as exc:
            raise KeyError(f"unknown blocker: {blocker_id}") from exc

    def open_blockers(self) -> tuple[Blocker, ...]:
        return tuple(b for b in self._blockers.values() if b.state is BlockerState.OPEN)

    def unresolved_blocking(self) -> tuple[Blocker, ...]:
        return tuple(b for b in self._blockers.values() if b.blocks_advance)

    def assert_can_advance(self, *, from_phase: str, to_phase: str) -> None:
        blocking = self.unresolved_blocking()
        if not blocking:
            return
        ids = ", ".join(b.blocker_id for b in blocking)
        raise PhaseBlockedError(
            f"cannot advance {from_phase!r} -> {to_phase!r}; unresolved blocking issue(s): {ids}. "
            "Allowed work is limited to diagnosis, repair, and verification of those blockers unless a human explicitly waives one."
        )

    def resolve(self, blocker_id: str, *, verification_evidence: str) -> None:
        blocker = self.get(blocker_id)
        if blocker.state is not BlockerState.OPEN:
            raise ValueError(f"blocker {blocker_id} is already {blocker.state.value}")
        evidence = verification_evidence.strip()
        if not evidence:
            raise ValueError("verified resolution requires non-empty verification evidence")
        blocker.evidence.append(evidence)
        blocker.state = BlockerState.RESOLVED

    def waive(self, blocker_id: str, *, human_authority: str, reason: str) -> None:
        blocker = self.get(blocker_id)
        if blocker.state is not BlockerState.OPEN:
            raise ValueError(f"blocker {blocker_id} is already {blocker.state.value}")
        authority = human_authority.strip()
        waiver_reason = reason.strip()
        if not authority or not waiver_reason:
            raise ValueError("explicit human authority and waiver reason are required")
        blocker.waiver_authority = authority
        blocker.waiver_reason = waiver_reason
        blocker.state = BlockerState.WAIVED

    def snapshot(self) -> list[dict]:
        return [
            {
                "blocker_id": b.blocker_id,
                "description": b.description,
                "class": b.blocker_class.value,
                "resolution_criterion": b.resolution_criterion,
                "verification_method": b.verification_method,
                "state": b.state.value,
                "evidence": list(b.evidence),
                "waiver_authority": b.waiver_authority,
                "waiver_reason": b.waiver_reason,
            }
            for b in sorted(self._blockers.values(), key=lambda x: x.blocker_id)
        ]
