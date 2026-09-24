"""Participant rows are the membership authority; a run gate is a disposable projection.

The stored phase only records the irreversible reveal boundary. No active/dropped/unknown
roster cache is synchronized alongside participant transitions. The app's quorum policy
also distinguishes original-app answers, so it owns this gate instead of discarding the
action returned by the separate core.membership contract.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

CLI, MANUAL = "cli", "manual"
QUEUED, RUNNING, AWAITING_USER = "queued", "running", "awaiting_user"
ACCEPTED, REJECTED, UNKNOWN = "accepted", "rejected", "unknown"
DONE = (ACCEPTED, REJECTED)
INDEPENDENT_ONLY, INCLUDE_UNVERIFIED = "independent_only", "include_unverified"
QUORUM_POLICIES = (INDEPENDENT_ONLY, INCLUDE_UNVERIFIED)


@dataclass(frozen=True)
class RunGate:
    status: str
    accepting: bool
    revealed: bool
    settled: bool
    quorum: dict[str, Any]
    requested: tuple[str, ...]
    dropped: tuple[str, ...]
    note: str | None

    @property
    def can_reveal(self) -> bool:
        return self.status == "ready"

    @property
    def can_approve_reduction(self) -> bool:
        return self.status == "reduction_required"

    def public(self) -> dict[str, Any]:
        return {"status": self.status, "can_start": self.accepting, "can_submit": self.accepting,
                "can_cancel": self.accepting, "can_approve_reduction": self.can_approve_reduction,
                "can_reveal": self.can_reveal, "can_synthesize": self.revealed,
                "can_report": self.revealed, "revealed": self.revealed, "settled": self.settled,
                "note": self.note}


def gate(run, rows) -> RunGate:
    """Derive all permissions from one snapshot; pending participants count only as potential quorum."""
    revealed = run["phase"] in ("revealed", "synthesis")
    accepting = run["phase"] == "drafting" and not run["cancel_requested"]
    settled = all(p["state"] in DONE for p in rows)
    requested = tuple(p["pid"] for p in rows)
    dropped = tuple(p["pid"] for p in rows if p["state"] == REJECTED)
    live = [p for p in rows if p["state"] not in (REJECTED, UNKNOWN)]
    confirmed = sum(json.loads(p["spec"])["transport"] == CLI for p in live)
    unverified = sum(json.loads(p["spec"])["transport"] == MANUAL for p in live)
    counted = confirmed if run["quorum_policy"] == INDEPENDENT_ONLY else confirmed + unverified
    quorum = {"policy": run["quorum_policy"], "min": run["min_independent"], "confirmed": confirmed,
              "unverified": unverified, "counted": counted, "met": counted >= run["min_independent"]}
    note = None
    if run["cancel_requested"]:
        status = "cancelled"
        note = "취소를 요청했습니다. 새 시도·수동 제출·공개는 막았습니다. 진행 중인 작업의 종료는 별도 확인합니다."
    elif revealed:
        status = "revealed"
    elif not accepting or not settled:
        status = "waiting"
    elif dropped and not run["reduction_approved"]:
        status = "reduction_required"
        note = f"요청한 {len(requested)}인 구성이 완료되지 않았습니다. 남은 참여자로 진행하려면 축소 승인이 필요합니다."
    elif not quorum["met"]:
        status = "quorum_blocked"
        if quorum["policy"] == INDEPENDENT_ONLY:
            note = (f"독립성이 확인된 참여자 {confirmed}명 — 최소 {quorum['min']}명이 필요합니다. "
                    f"원본 앱 답 {unverified}개는 정족수에 세지 않습니다. 유료로 채우지 않습니다.")
        else:
            note = (f"답을 낸 참여자 {counted}명(독립성 미확인 {unverified}명 포함) — "
                    f"최소 {quorum['min']}명이 필요합니다. 유료로 채우지 않습니다.")
    else:
        status = "ready"
    return RunGate(status, accepting, revealed, settled, quorum, requested, dropped, note)
