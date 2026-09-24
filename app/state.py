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


def confirmed(spec) -> bool:
    """원장에 저장한 등급만 사용한다. 예전 strict-only CLI 행은 필드가 없으며 기존 의미를 유지한다."""
    return spec.get("transport") == CLI and spec.get("context_unverified", False) is False


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
    independent = sum(confirmed(json.loads(p["spec"])) for p in live)
    unverified = len(live) - independent
    counted = independent if run["quorum_policy"] == INDEPENDENT_ONLY else independent + unverified
    quorum = {"policy": run["quorum_policy"], "min": run["min_independent"], "confirmed": independent,
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
        if run["quorum_policy"] == INDEPENDENT_ONLY:
            note = (f"독립성이 확인된 참여자 {independent}명 — 최소 {quorum['min']}명이 필요합니다. "
                    f"미확인 답 {unverified}개는 정족수에 세지 않습니다. 유료로 채우지 않습니다.")
        else:
            note = (f"답을 낸 참여자 {counted}명(독립성 미확인 {unverified}명 포함) — "
                    f"최소 {quorum['min']}명이 필요합니다. 유료로 채우지 않습니다.")
    else:
        status = "ready"
    return RunGate(status, accepting, revealed, settled, quorum, requested, dropped, note)


def synthesis_attempts(rows, active=()) -> dict[tuple[str, str], dict[str, Any]]:
    """시작·결과·사용자 종료 확인을 시도별로 투영한다. 별도 상태 표/캐시는 만들지 않는다.

    결과 없는 시작이나 종료 미확인은 자리를 유지한다. 모의 합성과 다른 시도의 결과로 풀지 않는다.
    예전 코드가 한 실행에서 여러 번 합성한 원장도 시도마다 보존한다. 사용자 확인은 사실 검증이 아니다.
    rows는 실행별 사건 순서여야 하며 active는 현재 controller가 소유한 (run_id, attempt)다.
    """
    attempts = {}
    for row in rows:
        payload = json.loads(row["payload"])
        attempt = payload.get("attempt")
        if not isinstance(attempt, str) or not attempt:
            continue   # 모의 합성은 모델 시도 ID가 없다.
        key = (row["run_id"], attempt)
        if row["kind"] == "synthesis_started":
            attempts.setdefault(key, {"status": UNKNOWN, "result": {}})
        elif key in attempts and attempts[key]["status"] != "acknowledged":
            if row["kind"] == "synthesis_unknown_acknowledged":
                attempts[key]["status"] = "acknowledged"
            elif row["kind"] in ("synthesis_completed", "synthesis_failed"):
                result = payload.get("result") or {}
                meta = result.get("synthesizer") or {}
                ended = meta.get("tree_confirmed_empty") is True or meta.get("started") is False
                attempts[key] = {"status": ("completed" if result.get("status") == "completed" else "failed")
                                if ended else UNKNOWN, "result": result}
    for key in active:
        if key in attempts:
            attempts[key]["status"] = RUNNING
    return attempts
