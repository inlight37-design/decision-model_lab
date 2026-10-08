"""Typed legacy role storage descriptors. Lifecycle is owned by ExecutionCoordinator."""
from __future__ import annotations
from dataclasses import dataclass
import json
from typing import Any
from app import collate as collating, cross_review as cross, next_step, refine as refining, split as splitting
from app import revisions
from app.state import ACCEPTED, REJECTED, UNKNOWN

@dataclass(frozen=True)
class _Seat:
    """상위 모델 호출 한 종류가 원장에 앉는 자리: 표, 행을 고르는 열, 사건 이름, 답 검사. 다듬기 차례(#130)·다음 단계
    제안(#133)·분담 제안(#135)·결과 모으기(#137)·교차검토(#140)가 같은 시작·결과·종료 확인 관문을 쓰게 한다. 표 이름과 열은 코드에 박은
    값이다(사용자 입력이 아니다). 자리·종료 미확인·한 번에 하나·재시작 복구는 SEATS를 한꺼번에 본다."""
    table: str
    keys: tuple[str, ...]
    labels: tuple[str, ...]          # 사건에 싣는 열(사건의 실행 키로 이미 드러나는 열은 뺀다)
    purpose: str                     # 호출 예약 사건의 purpose
    started: str
    done: dict                       # 상태 → 끝난 사건 이름
    ignored: str
    not_stored: str
    acknowledged: str
    check: Any                       # (답 원문, 그 호출의 원장 행) → 검사한 답. 분담 제안은 행의 팀원·자료로 검사한다
    event_column: str = ""           # 사건을 남기는 키가 든 열(다듬기: refine_id, 제안·모으기: run_id, 분담: split_id)
    plan_pid: str = "supervisor"     # 계획·예약 사건에 쓰는 참여자 ID와 이름(교차검토는 검토자)
    plan_label: str = "슈퍼바이저"
    card_column: str = "supervisor"

    @property
    def match(self) -> str:
        return " AND ".join(f"{key} = ?" for key in self.keys)

    def label(self, where: dict) -> dict:
        return {key: where[key] for key in self.labels}


REFINE_SEAT = _Seat("refine_turns", ("refine_id", "turn"), ("turn",), "refine", "refine_turn_started",
                    {ACCEPTED: "refine_turn_completed", REJECTED: "refine_turn_failed", UNKNOWN: "refine_turn_unknown"},
                    "refine_result_ignored", "refine_result_not_stored", "refine_unknown_acknowledged",
                    lambda text, row: refining.check(text), "refine_id")


NEXT_SEAT = _Seat("proposals", ("proposal_id",), ("proposal_id",), "next_step", "proposal_started",
                  {ACCEPTED: "proposal_completed", REJECTED: "proposal_failed", UNKNOWN: "proposal_unknown"},
                  "proposal_result_ignored", "proposal_result_not_stored", "proposal_unknown_acknowledged",
                  lambda text, row: next_step.check(text), "run_id")


SPLIT_SEAT = _Seat("splits", ("split_id",), (), "split", "split_started",
                   {ACCEPTED: "split_completed", REJECTED: "split_failed", UNKNOWN: "split_unknown"},
                   "split_result_ignored", "split_result_not_stored", "split_unknown_acknowledged",
                   lambda text, row: splitting.check(text, json.loads(row["members"]),
                                                     [s["name"] for s in json.loads(row["sources"])]), "split_id", card_column="orchestrator")


COLLATE_SEAT = _Seat("collations", ("collation_id",), ("collation_id",), "collate", "collation_started",
                     {ACCEPTED: "collation_completed", REJECTED: "collation_failed", UNKNOWN: "collation_unknown"},
                     "collation_result_ignored", "collation_result_not_stored", "collation_unknown_acknowledged",
                     lambda text, row: collating.check(text, json.loads(row["drafts"])), "run_id", card_column="orchestrator")


REVIEW_SEAT = _Seat("reviews", ("review_id",), ("review_id",), "cross_review", "review_started",
                    {ACCEPTED: "review_completed", REJECTED: "review_failed", UNKNOWN: "review_unknown"},
                    "review_result_ignored", "review_result_not_stored", "review_unknown_acknowledged",
                    lambda text, row: cross.check(text, {label: item["text"] for label, item
                                                         in json.loads(row["targets"]).items()},
                                                  cross.GENERAL_INDEPENDENCE if row["snapshot"] is not None
                                                  else cross.ISOLATED_INDEPENDENCE),
                    "run_id", "reviewer", "교차검토자", "reviewer")

REVISION_SEAT = _Seat('answer_revisions', ('revision_id',), ('revision_id',), 'answer_revision', 'revision_started',
    {ACCEPTED: 'revision_completed', REJECTED: 'revision_failed', UNKNOWN: 'revision_unknown'},
    'revision_result_ignored', 'revision_result_not_stored', 'revision_unknown_acknowledged',
    lambda text, row: revisions.check(text, json.loads(row['snapshot'])), 'run_id', 'revision-author', '수정 작성자', 'author')

RECHECK_SEAT = _Seat('revision_checks', ('check_id',), ('check_id',), 'revision_recheck', 'recheck_started',
    {ACCEPTED: 'recheck_completed', REJECTED: 'recheck_failed', UNKNOWN: 'recheck_unknown'},
    'recheck_result_ignored', 'recheck_result_not_stored', 'recheck_unknown_acknowledged',
    lambda text, row: revisions.check_recheck(text, json.loads(row['snapshot']), row['answer']),
    'run_id', 'revision-reviewer', '수정 재검토자', 'reviewer')


SEATS = (REFINE_SEAT, NEXT_SEAT, SPLIT_SEAT, COLLATE_SEAT, REVIEW_SEAT, REVISION_SEAT, RECHECK_SEAT)
