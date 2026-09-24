"""오프라인 UI 경계 실험. 인증·MCP 서버·프로세스 제어·진실 판정이 아니다.

입력은 신뢰된 controller/adapter가 제공해야 한다. 모델 출력에 이 함수를
적용했다고 그 출력이 신뢰된 관측으로 바뀌지 않는다. v0.2/v0.4 계약과 별개다.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
import re
from typing import Any


class BoundaryError(ValueError):
    """화면으로 내보내기 전에 확인해야 하는 경계 위반."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise BoundaryError(message)


def identifier(value: Any) -> str:
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value) is not None,
            "invalid identifier")
    return value


STATES = ("reserved", "running", "cancel_requested", "unknown", "exited")
EVENTS = ("started", "cancel_requested", "connection_lost", "reconciled_running", "process_exited")


@dataclass(frozen=True)
class Event:
    attempt_id: str
    epoch: str
    seq: int
    kind: str
    exit_code: int | None = None


@dataclass(frozen=True)
class Attempt:
    """한 invocation의 예약된 예산 슬롯. 재시도는 반드시 새 ID로 만든다."""
    attempt_id: str
    epoch: str
    state: str = "reserved"
    cancellation_requested: bool = False
    last_event: Event | None = None
    exit_code: int | None = None


def advance(attempt: Attempt, event: Event) -> Attempt:
    """순서·세대가 확인된 이벤트만 반영한다. exit 0을 작업 성공으로 승격하지 않는다."""
    require(isinstance(attempt, Attempt) and isinstance(event, Event), "typed input required")
    identifier(attempt.attempt_id)
    identifier(attempt.epoch)
    require(attempt.state in STATES, "invalid state")
    require(type(attempt.cancellation_requested) is bool, "invalid cancellation flag")
    require((event.attempt_id, event.epoch) == (attempt.attempt_id, attempt.epoch), "stale attempt or epoch")
    require(type(event.seq) is int and event.seq > 0, "invalid sequence")
    require(event.kind in EVENTS, "invalid event")
    require((event.kind == "process_exited" and type(event.exit_code) is int)
            or (event.kind != "process_exited" and event.exit_code is None), "invalid exit observation")
    if attempt.last_event == event:
        return attempt  # 같은 전달의 재생은 예산이나 상태를 다시 바꾸지 않는다.
    previous = attempt.last_event.seq if attempt.last_event else 0
    require(event.seq == previous + 1, "event gap or conflicting replay; reconcile first")
    require(attempt.state != "exited", "terminal attempt is immutable")
    state, cancelled, code = attempt.state, attempt.cancellation_requested, None
    if event.kind == "started":
        require(state == "reserved", "start requires a reserved attempt")
        state = "running"
    elif event.kind == "cancel_requested":
        cancelled = True
        state = "unknown" if state == "unknown" else "cancel_requested"
    elif event.kind == "connection_lost":
        state = "unknown"
    elif event.kind == "reconciled_running":
        require(state == "unknown", "reconciliation requires unknown state")
        state = "cancel_requested" if cancelled else "running"
    elif event.kind == "process_exited":
        state, code = "exited", event.exit_code
    return replace(attempt, state=state, cancellation_requested=cancelled,
                   last_event=event, exit_code=code)


def budget_projection(attempts: list[Attempt], cap: int) -> dict[str, Any]:
    """실패·UNKNOWN·미시작 예약까지 슬롯을 점유한다. 금액/토큰/진척률이 아니다."""
    require(type(cap) is int and cap > 0, "invalid cap")
    require(isinstance(attempts, list) and all(isinstance(a, Attempt) for a in attempts), "attempt list required")
    ids = [identifier(a.attempt_id) for a in attempts]
    require(len(set(ids)) == len(ids), "duplicate attempt")
    require(len(ids) <= cap, "budget exceeded")
    require(all(a.state in STATES for a in attempts), "invalid state")
    return {"unit": "invocation_slot", "used": len(ids), "cap": cap,
            "remaining": cap - len(ids),
            "breakdown": {s: sum(a.state == s for a in attempts) for s in STATES}}


def sealed_projection(participants: list[dict[str, Any]], *, audience: str,
                      own_id: str | None = None) -> dict[str, Any]:
    """봉인 중 allowlist 투영. 서버의 인증/권한 검사를 대신하지 않는다.

    operator는 제출 상태만, participant는 자신의 제출 상태만 받는다.
    새로운 내부 필드가 생겨도 자동 전송하지 않는다. 길이·토큰·원문·경로는 없다.
    """
    require(audience in ("operator", "participant"), "unknown audience")
    require(isinstance(participants, list) and bool(participants), "participants required")
    visible, ids = [], set()
    for p in participants:
        require(isinstance(p, dict), "participant object required")
        pid = identifier(p.get("id"))
        require(pid not in ids, "duplicate participant")
        ids.add(pid)
        status = p.get("submission")
        require(status in ("pending", "submitted", "failed", "denied"), "invalid submission")
        if audience == "operator" or pid == own_id:
            visible.append({"id": pid, "submission": status})
    if audience == "participant":
        require(own_id in ids, "participant identity required")
    return {"schema": "sealed-view-experiment/0", "sealed": True, "participants": visible}


def quota_projection(payload: dict[str, Any] | None, *, observed_at: int,
                     now: int, max_age_s: int = 120) -> dict[str, Any]:
    """Compatibility wrapper; runtime owns the validated projection."""
    from core.quota import quota_projection as project
    try:
        return project(payload, observed_at=observed_at, now=now, max_age_s=max_age_s)
    except ValueError as exc:
        raise BoundaryError(str(exc)) from None
