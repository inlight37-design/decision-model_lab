"""실행 중 참여자 구성이 바뀔 때의 결정(PR #4 R09, 사용자 확정 13, D18).

- 빠진 자리를 조용히 채우지 않는다. 사전에 허용한 대체(alternates)만, 동료 초안이 공개되기
  전에만 들인다. 공개 뒤에 들어온 참여자는 같은 blind 라운드의 독립 참여자가 아니다.
- 사전에 정한 최소 독립 인원(min_independent)을 못 채우면 막는다(BLOCKED). 유료 API로 넘기지 않는다.
- 종료가 확인되지 않은 호출은 UNKNOWN으로 남기고 예산 점유를 유지한다. 뺐다고 취소된 것이 아니다.
- 회복한 provider는 진행 중인 run에 다시 넣지 않는다. 다음 run의 preflight에서 넣는다.
- 합성자만 쓸 수 없으면 모은 초안과 반례를 그대로 보고한다. 합성 성공으로 표시하지 않는다.

모든 결정은 화면에 그대로 보여 줄 수 있게 note를 단다. 이 모듈은 결정만 하고 실행하지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

PREFLIGHT, DRAFTING, REVEALED, SYNTHESIS = "preflight", "drafting", "revealed", "synthesis"
PHASES = (PREFLIGHT, DRAFTING, REVEALED, SYNTHESIS)
EVENTS = ("unavailable", "quota_exhausted", "cancel_unconfirmed", "substitute_requested",
          "recovered", "synthesizer_unavailable")

PROCEED = "proceed"
PROCEED_REDUCED = "proceed_reduced"
BLOCKED = "blocked"
KEEP_UNKNOWN = "keep_unknown"
REJECT_SUBSTITUTE = "reject_substitute"
DEFER = "defer_to_next_run"
REPORT_WITHOUT_SYNTHESIS = "report_without_synthesis"


class MembershipError(ValueError):
    pass


@dataclass(frozen=True)
class Roster:
    requested: tuple[str, ...]
    min_independent: int
    phase: str
    active: frozenset[str]                        # 독립 초안을 냈거나 내는 중인 참여자
    alternates: tuple[str, ...] = ()              # 사전에 허용한 대체. 이것 말고는 들이지 않는다
    dropped: tuple[tuple[str, str], ...] = ()     # (참여자, 이유). 지우지 않고 보여 준다
    unknown: frozenset[str] = frozenset()         # 종료 불명. 예산 점유 유지


@dataclass(frozen=True)
class Decision:
    action: str
    roster: Roster
    note: str


def start(requested: tuple[str, ...], *, min_independent: int, alternates: tuple[str, ...] = ()) -> Roster:
    if not requested or len(set(requested)) != len(requested):
        raise MembershipError("requested participants must be unique and non-empty")
    if not 1 <= min_independent <= len(requested):
        raise MembershipError("min_independent must be between 1 and the requested count")
    if set(alternates) & set(requested):
        raise MembershipError("an alternate cannot also be requested")
    return Roster(tuple(requested), min_independent, PREFLIGHT, frozenset(requested), tuple(alternates))


def advance(roster: Roster, phase: str) -> Roster:
    """단계는 앞으로만 간다. 초안을 공개(REVEALED)한 뒤에는 되돌릴 수 없다."""
    if phase not in PHASES or PHASES.index(phase) <= PHASES.index(roster.phase):
        raise MembershipError(f"cannot move from {roster.phase} to {phase}")
    return replace(roster, phase=phase)


def _counted(roster: Roster) -> int:
    return len(roster.active - roster.unknown)


def _drop(roster: Roster, participant: str, reason: str) -> Decision:
    if participant not in roster.active:
        raise MembershipError(f"{participant} is not an active participant")
    changed = replace(roster, active=roster.active - {participant},
                      dropped=roster.dropped + ((participant, reason),))
    if roster.phase in (REVEALED, SYNTHESIS):
        return Decision(PROCEED_REDUCED, changed,
                        f"{participant}: {reason} after drafts were revealed; its draft stays, "
                        "the review round is reduced")
    if _counted(changed) < changed.min_independent:
        return Decision(BLOCKED, changed,
                        f"{participant}: {reason}; {_counted(changed)} independent participant(s) left, "
                        f"{changed.min_independent} required. No paid fallback")
    return Decision(PROCEED_REDUCED, changed,
                    f"{participant}: {reason}; continuing with {_counted(changed)} of "
                    f"{len(changed.requested)} requested")


def decide(roster: Roster, event: str, participant: str | None = None) -> Decision:
    if roster.phase not in PHASES:
        raise MembershipError(f"unknown phase {roster.phase!r}")
    if event not in EVENTS:
        raise MembershipError(f"unknown event {event!r}")
    if event == "synthesizer_unavailable":
        return Decision(REPORT_WITHOUT_SYNTHESIS, roster,
                        "synthesizer unavailable: report the collected drafts and counterexamples as they "
                        "are; this is not a completed synthesis")
    if participant is None:
        raise MembershipError(f"{event} needs a participant")
    if event in ("unavailable", "quota_exhausted"):
        return _drop(roster, participant, "quota exhausted" if event == "quota_exhausted" else "unavailable")
    if event == "cancel_unconfirmed":
        if participant not in roster.active:
            raise MembershipError(f"{participant} is not an active participant")
        changed = replace(roster, unknown=roster.unknown | {participant})
        return Decision(KEEP_UNKNOWN, changed,
                        f"{participant}: termination not confirmed; the call stays UNKNOWN and keeps its "
                        "budget slot")
    if event == "recovered":
        return Decision(DEFER, roster, f"{participant} recovered; membership of this run does not change")
    # substitute_requested
    if roster.phase in (REVEALED, SYNTHESIS):
        return Decision(REJECT_SUBSTITUTE, roster,
                        f"{participant} would join after drafts were revealed; start a new run instead")
    if participant not in roster.alternates:
        return Decision(REJECT_SUBSTITUTE, roster, f"{participant} is not a pre-approved alternate")
    if participant in roster.active:
        raise MembershipError(f"{participant} is already active")
    changed = replace(roster, active=roster.active | {participant},
                      alternates=tuple(a for a in roster.alternates if a != participant))
    return Decision(PROCEED, changed, f"{participant} joins as a pre-approved alternate before any draft "
                                      "was revealed (shown as a substitution)")
