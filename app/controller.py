"""A1 controller — 상태를 가진 유일한 곳. 모델을 부르지 않는 모의 모드부터 만든다(인계 4절 1).

한 줄 흐름: 고정 입력 manifest → 시도 예약 → 실행 → 결과 수용 관문 → 초안 봉인 → controller가 공개.

지키는 규칙
- 결과 수용: 모두 맞아야 받는다 — 자손 전체 종료 확인(tree_confirmed_empty is True), interpret()의 ok, 질문을
  stdin으로 끝까지 보낸 기록(input_delivery == complete), 비어 있지 않은 답, 보고된 모델이 요청과 다르지 않음
  (model_match가 False가 아님. 보고가 없으면 None이고 받는다 — K32). 종료를 확인하지 못한 시도는 unknown이고
  초안을 받지 않으며 실행 자리를 풀지 않는다. 다시 부르지 않는다. 예산은 돌려주지 않는다.
- 소유: 원장 하나를 여는 controller는 하나다(Store의 잠금). 시작(queued → running)과 결과 반영(running → …)은
  기대한 상태와 시도 ID가 맞을 때만 한다. 그 뒤에 온 결과는 사건으로만 남긴다(A1 리뷰 A1-03).
- 공개: 화면에 공개 버튼이 없다. 남은 참여자가 모두 끝났고 정족수가 있을 때 controller가 연다. 상태를 바꾼
  거래 안에서 판정하므로 마지막 초안의 저장과 공개 사이에서 멈추지 않는다. 누가 빠졌으면 남은 사람으로 자동
  진행하지 않고 사용자의 축소 승인을 기다린다(Ledger BlindBarrier). 승인은 그것을 기다릴 때만 받는다.
- 봉인: 공개 전 화면에는 고정된 필드만 넘긴다(허용 목록). 초안의 내용·길이·digest, 토큰 수, 걸린 시간은
  공개 뒤에, CLI가 쓴 오류 설명과 runner 메모는 모든 참여자가 끝난 뒤에 넘긴다.
- 수동 참여자(원본 앱): 사용자가 질문을 원본 앱에 옮기고 답을 붙여 넣는다. 복사하는 질문 첫 줄에 실행 표식
  `[Ledger <실행 ID> · <입력 sha256 앞 8자>]`을 넣고 답 첫 줄에 되말해 달라고 적는다. 답의 표식이 다른 실행의
  것이면 받지 않는다 — 다른 카드에 붙여 넣는 실수를 잡는다(N5). 표식이 맞아도, 없어도 약한 증거일 뿐이다.
  원본 앱에 이 질문을 넣었는지는 사용자의 확인(user_confirmed)으로 따로 남기고, 그것으로 독립성을 확인했다고
  올리지 않는다(K21). 화면 밖 요청의 digest 불일치, 공개 뒤·중복 제출, 빈 답도 받지 않는다.
- 정족수(Q6, 2절 18): 실행마다 정책을 고정한다. independent_only(기본)는 독립성이 확인된 참여자 — controller가
  고정 입력만 주고 실행한 CLI — 만 센다. 원본 앱 답은 보조 근거로 함께 공개한다. include_unverified는 원본 앱
  답도 세지만, 그 결과를 "독립 정족수 충족"으로 표시하지 않는다.
- 정리되지 않은 시도(unknown + runner.lingering())가 상한에 닿으면 새 시도를 시작하지 않는다.
- 다시 시작: running이던 시도는 unknown으로 둔다. 초안 작성 중인 실행은 공개 관문을 다시 본다. 대기 중인
  시도는 사용자가 이어서 시작하라고 할 때까지(resume) 시작하지 않는다. 실행 취소는 원장에 먼저 저장하며
  재시작해도 되돌리지 않는다. 취소 요청과 실제 자손 종료 확인은 다르다(K19).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import threading
import time
import uuid
from typing import Any, Protocol

from app.store import Store
from app import (collate as collating, cross_review as cross, memory, next_step, refine as refining, split as splitting,
                 usage as token_usage)
from app.roles import freeze as freeze_roles, task_projection
from app.report import build_report
from app.synthesis import (LABEL_ORDER, SynthesisError, _sources as synthesis_sources, check_model_synthesis,
                           label_order, mock_synthesize, model_prompt, model_unavailable, unavailable)
from app.state import (CLI, MANUAL, QUEUED, RUNNING, AWAITING_USER, ACCEPTED, REJECTED, UNKNOWN, NOT_STARTED,
                       INDEPENDENT_ONLY, INCLUDE_UNVERIFIED, QUORUM_POLICIES, ISOLATED, GENERAL, COLLECTED,
                       NO_QUORUM, RunGate, gate, confirmed, synthesis_attempts)
from core import adapters, contract, env as core_env, isolation, membership as m, runner

# _source_dir가 원장의 질문 본문을 이 두 문구로 다시 만들어 맞춘다. 문구를 바꾸면 그 전에 만든 대기 실행은
# 재개 때 호출 없이 거절된다.
PROMPT = ("다음 질문에, 다른 참여자의 답을 보지 않은 상태로 독립적으로 답하라. "
          "결론, 근거, 그리고 결론을 뒤집을 조건을 쓴다.\n\n질문:\n{question}\n")
# 공통 자료(P0). 모든 참여자가 같은 질문 본문을 받으므로 목록·해시는 질문에 넣어 입력 digest에 묶는다.
PROMPT_SOURCES = ("\n참고 자료 {count}개가 읽기 전용 폴더 {folder}에 있다. 자료에서 가져온 내용은 파일 이름을 밝히고, "
                  "자료에 없는 판단은 자료 밖의 판단이라고 표시한다.\n{listing}\n")
# 일반 팀원(카드 #125). 사람이 나눈 일을 팀원마다 따로 보낸다. 봉인·독립 판정이 없으므로 "다른 답을 보지 않고"를
# 요구하지 않는다. _member_source_dir가 원장의 목표·맡긴 일·자료 목록으로 이 문구를 다시 만들어 맞춘다 — 바꾸면 그
# 전에 만든 대기 실행은 재개 때 호출 없이 거절된다.
GENERAL_PROMPT = ("사람이 일을 나눠 너에게 한 부분을 맡겼다. 전체 목표는 참고만 하고 맡은 일만 한다. 파일을 고치지 않고 "
                  "읽기만 한다. 결과, 근거, 확인하지 못한 점을 쓴다.\n\n전체 목표:\n{question}\n\n맡은 일:\n{task}\n")
MAX_TASK_CHARS, MAX_MEMO_CHARS = 4000, 8000
# 팀원이 받은 자료의 종류(리뷰 통합 6절 C 행: 원문/기계적 지도/AI 요약/기존 답). 첫 조각은 원문 파일 전체만 받는다 —
# 요약만 받은 답을 원문 검토로 표시하지 않도록 종류를 입력에 고정해 둔다.
SOURCE_KIND_ORIGINAL, SOURCE_RANGE_WHOLE = "original", "whole"
SOURCE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
WINDOWS_DEVICES = re.compile(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?")
MAX_SOURCES, MAX_SOURCE_BYTES, MAX_SOURCES_TOTAL = 20, 256 * 1024, 1024 * 1024


def storable(text: str) -> bool:
    """UTF-8로 저장·해시할 수 있는 글인가. JSON의 올바른 이스케이프(예: "\\ud800")로 들어온 고립 surrogate는
    원장 쓰기·sha256·HTTP 출력에서 모두 실패한다(카드 #70). 정상 보충 평면 문자와 글자 그대로의 \\ud800은 된다."""
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _storable_meta(value):
    """진단 메타데이터(오류 설명·메모·보고 모델 등)의 고립 surrogate를 \\uXXXX 표기로 바꾼다. 봉인하는 초안이
    아니라서 표기를 바꿔도 digest 계약과 무관하다(외부 검토 R05). 바꿨는지는 호출한 쪽이 표시한다."""
    if isinstance(value, str):
        return value if storable(value) else value.encode("utf-8", "backslashreplace").decode("utf-8")
    if isinstance(value, dict):
        return {_storable_meta(k): _storable_meta(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_storable_meta(v) for v in value]
    return value


def _checked_sources(items) -> list[tuple[str, bytes]]:
    """(이름, 글) 목록을 검사한다. 경로 구분자·숨김 이름·장치 이름·중복(대소문자 무시)·크기 초과·NUL을 거절한다."""
    if items is None:
        return []
    if not isinstance(items, (list, tuple)) or len(items) > MAX_SOURCES:
        raise ControllerError(f"sources must be a list of at most {MAX_SOURCES} files")
    checked, seen, total = [], set(), 0
    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ControllerError("each source needs a name and a text")
        name, text = item
        if (not isinstance(name, str) or SOURCE_NAME.fullmatch(name) is None or WINDOWS_DEVICES.fullmatch(name)
                or name.endswith(".") or name.lower() in seen):
            raise ControllerError("source names use letters, digits, dot, dash or underscore and must be unique")
        if not isinstance(text, str) or "\x00" in text or not storable(text):
            raise ControllerError(f"source {name!r} must be valid Unicode text")
        data = text.encode("utf-8")
        total += len(data)
        if len(data) > MAX_SOURCE_BYTES or total > MAX_SOURCES_TOTAL:
            raise ControllerError(f"sources are limited to {MAX_SOURCE_BYTES} bytes each and {MAX_SOURCES_TOTAL} in total")
        seen.add(name.lower())
        checked.append((name, data))
    return sorted(checked)


def _bundle_digest(members: dict[str, dict[str, Any]]) -> str:
    """일반 실행 전체의 입력 해시: 팀원별 입력 전문의 sha256을 팀원 ID 순으로 묶은 것. 한 팀원의 입력이 바뀌어도 바뀐다."""
    return hashlib.sha256(json.dumps({pid: item["input_sha256"] for pid, item in members.items()},
                                     sort_keys=True).encode("utf-8")).hexdigest()


def _source_footer(folder: str, sources) -> str:
    """생성과 재개가 같은 자료 목록 형식을 쓴다. 경로도 고정 질문의 일부이므로 조용히 바꾸지 않는다."""
    return PROMPT_SOURCES.format(
        count=len(sources), folder=folder,
        listing="\n".join(f"- {item['name']} ({item['bytes']} bytes, sha256 {item['sha256']})" for item in sources))

# 공개 전 화면에 넘기는 결과 필드. 값이 정해진 것만 둔다 — 막을 것을 고르지 않고 넘길 것을 고른다(A1-01).
SEALED_VIEW_KEYS = frozenset({"state", "exit_code", "containment", "tree_confirmed_empty", "input_delivery",
                              "status", "ok", "model_match"})
# CLI가 쓴 자유 텍스트(오류 설명)와 runner 메모. 모든 참여자가 끝난 뒤에 넘긴다.
DIAGNOSTIC_KEYS = frozenset({"detail", "notes"})

# 참여자 표시. CLI는 시도 행에 저장한 실행 종류로 고른다 — 지금 붙은 실행기로 과거 시도를 짐작하지 않는다(G6).
CONTAMINATION = {
    MANUAL: ("원본 앱의 메모리·다른 대화·프로젝트 지시문을 통제하지 못함", "사용량·시간 관측 안 됨"),
    contract.MOCK: ("모의 CLI — 모델 호출 없음",),
    contract.SYNTHETIC: ("합성 실행기 — 모델 호출 없음",),
    contract.REAL: ("실제 CLI — 구독 사용량을 씀", "계정 문맥은 실행 허가의 관측 범위까지만 확인"),
}
NOT_RUN = ("실행하지 않음",)
UNRECORDED = ("실행 종류 기록 없음",)


def _flags(transport: str, part) -> tuple[str, ...]:
    """시작하지 않은 시도(대기, 시작 전 취소, 계획·프로세스 거절)는 종류와 상관없이 "실행하지 않음"이다."""
    if transport == MANUAL:
        return CONTAMINATION[MANUAL]
    if part["state"] == QUEUED or part["status"] in NOT_STARTED:
        return NOT_RUN
    return CONTAMINATION.get(part["kind"], UNRECORDED)


def _card(spec: dict) -> dict:
    """상위 칸 카드의 화면 표시 — 원장에 저장한 명세에서 네 칸만."""
    return {key: spec.get(key) for key in ("pid", "label", "adapter_id", "model")}


def _seat_result(row) -> dict:
    """상위 모델 호출 행의 결과 칸: 통과한 답, 실패 이유, 실패한 답의 원문, 관측. 결과가 없으면 모두 None."""
    record = json.loads(row["result"]) if row["result"] else {}
    return {"reply": record.get("reply"), "reason": record.get("reason"), "raw": record.get("raw"),
            "observation": record.get("observation")}

# 원본 앱에 옮기는 질문의 첫 줄과, 답에서 그것을 찾는 형식(N5)
MARKER = "[Ledger {run_id}/{pid} · {sha8}]"
MARKER_LINE = re.compile(r"^\s*\[Ledger ([^\s/]+)/(\S+) · ([0-9a-f]{8})\]\s*$")
PACKET = ("{marker}\n답의 첫 줄에 위 대괄호 줄을 그대로 옮겨 적어 주세요. 어느 실행의 답인지 확인하는 데만 씁니다.\n\n"
          "{prompt}")


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

    @property
    def match(self) -> str:
        return " AND ".join(f"{key} = ?" for key in self.keys)

    def label(self, where: dict) -> dict:
        return {key: where[key] for key in self.labels}


REFINE_SEAT = _Seat("refine_turns", ("refine_id", "turn"), ("turn",), "refine", "refine_turn_started",
                    {ACCEPTED: "refine_turn_completed", REJECTED: "refine_turn_failed", UNKNOWN: "refine_turn_unknown"},
                    "refine_result_ignored", "refine_result_not_stored", "refine_unknown_acknowledged",
                    lambda text, row: refining.check(text), "refine_id")
# 제안·모으기 사건은 그 실행의 사건으로 남긴다(실행 화면의 사건 기록에 보인다)
NEXT_SEAT = _Seat("proposals", ("proposal_id",), ("proposal_id",), "next_step", "proposal_started",
                  {ACCEPTED: "proposal_completed", REJECTED: "proposal_failed", UNKNOWN: "proposal_unknown"},
                  "proposal_result_ignored", "proposal_result_not_stored", "proposal_unknown_acknowledged",
                  lambda text, row: next_step.check(text), "run_id")
SPLIT_SEAT = _Seat("splits", ("split_id",), (), "split", "split_started",
                   {ACCEPTED: "split_completed", REJECTED: "split_failed", UNKNOWN: "split_unknown"},
                   "split_result_ignored", "split_result_not_stored", "split_unknown_acknowledged",
                   lambda text, row: splitting.check(text, json.loads(row["members"]),
                                                     [s["name"] for s in json.loads(row["sources"])]), "split_id")
COLLATE_SEAT = _Seat("collations", ("collation_id",), ("collation_id",), "collate", "collation_started",
                     {ACCEPTED: "collation_completed", REJECTED: "collation_failed", UNKNOWN: "collation_unknown"},
                     "collation_result_ignored", "collation_result_not_stored", "collation_unknown_acknowledged",
                     lambda text, row: collating.check(text, json.loads(row["drafts"])), "run_id")
# 교차검토는 답을 낸 팀원이 검토자다. 대상 답 원문은 행(targets)에 고정해 두고 그것과 인용을 대조한다
REVIEW_SEAT = _Seat("reviews", ("review_id",), ("review_id",), "cross_review", "review_started",
                    {ACCEPTED: "review_completed", REJECTED: "review_failed", UNKNOWN: "review_unknown"},
                    "review_result_ignored", "review_result_not_stored", "review_unknown_acknowledged",
                    lambda text, row: cross.check(text, {label: item["text"] for label, item
                                                         in json.loads(row["targets"]).items()}),
                    "run_id", "reviewer", "교차검토자")
SEATS = (REFINE_SEAT, NEXT_SEAT, SPLIT_SEAT, COLLATE_SEAT, REVIEW_SEAT)


@dataclass(frozen=True)
class ParticipantSpec:
    pid: str
    label: str
    provider: str
    transport: str                  # CLI | MANUAL
    adapter_id: str | None = None   # CLI만
    model: str | None = None
    behavior: str = "ok"            # 모의 CLI의 행동(fake_cli.py)
    context_unverified: bool = False  # 전송 방식이 아니라 저장된 정책으로 정족수를 계산한다.


class Executor(Protocol):
    """실행 계약(core.contract, G4). plan()이 최종 계획을 한 번 만들고 — 거절하면 예외, 아무것도 시작하지 않았다 —
    run()이 그 계획 그대로 실행한다. kind는 이 실행기가 만드는 시도의 종류, adapter_ids는 받는 CLI다. 선택으로
    check(plan)을 두면 controller가 호출을 예약하기 직전에 부른다(격리 경로·연결 검사, 구조 검토 R4)."""
    name: str
    kind: str
    adapter_ids: tuple[str, ...]

    def plan(self, spec: ParticipantSpec, prompt: str, work_dir: str, *, inputs: tuple[str, ...] = ()
             ) -> contract.Plan: ...   # inputs: 실행의 공통 자료 폴더. 자료가 있는 실행에만 넘긴다

    def run(self, plan: contract.Plan, timeout: float, *, cancel: threading.Event | None = None
            ) -> tuple[runner.RunResult, adapters.Outcome]: ...


class MockExecutor:
    """가짜 CLI를 실제 실행 경로로 돌린다. Windows는 job object(runner.run), Linux는 bubblewrap(isolation.run).
    bubblewrap을 못 쓰는 Linux에서는 프로세스 그룹뿐이라 종료를 확인하지 못하고, 결과는 unknown이 된다."""

    SCRIPT = str(Path(__file__).with_name("fake_cli.py"))
    FLAVOR = {"claude-code": "claude", "codex": "codex"}
    kind = contract.MOCK
    adapter_ids = tuple(FLAVOR)

    def __init__(self, never: tuple[str, ...] = ()) -> None:
        self.never = never
        self.isolated = sys.platform == "linux" and _bwrap_trusted()
        self.name = "bubblewrap" if self.isolated else ("job_object" if runner.IS_WINDOWS else "process_group")

    def plan(self, spec, prompt, work_dir, *, inputs=()):
        python = "/usr/bin/python3" if self.isolated else sys.executable
        data = prompt.encode("utf-8")
        # 고른 모델 이름을 넘기면 가짜 CLI가 그 이름을 보고한다 — 요청·보고 대조가 실제와 같은 길을 지난다(카드 #119)
        planned = adapters.ExecutionSpec(spec.adapter_id, (python, self.SCRIPT, self.FLAVOR[spec.adapter_id],
                                                           spec.behavior) + ((spec.model,) if spec.model else ()),
                                         prompt, adapters.STDIN, hashlib.sha256(data).hexdigest(), len(data))
        box = isolation.Sandbox(work_dir=work_dir, home=work_dir + "-home",
                                read_only=(os.path.dirname(self.SCRIPT),) + tuple(inputs),
                                env={"LANG": "C.UTF-8"}, never=self.never) if self.isolated else None
        tmpl = contract.template(planned, box, home=work_dir + "-home", inputs=inputs)
        return contract.Plan(contract.MOCK, planned, work_dir, box, spec.model or "", (), contract.revision(tmpl), tmpl)

    def run(self, plan, timeout, *, cancel=None):
        if plan.box is not None:
            result = isolation.run(list(plan.spec.argv), plan.box, timeout=timeout, stdin_text=plan.spec.stdin_text,
                                   cancel=cancel)
        else:
            child, _ = core_env.child_env(os.environ)
            child["PYTHONUTF8"] = "1"
            result = runner.run(list(plan.spec.argv), cwd=plan.work_dir, env=child, timeout=timeout,
                                stdin_text=plan.spec.stdin_text, cancel=cancel)
        return result, adapters.interpret(plan.spec.adapter_id, result, requested_model=plan.model)


def _check(executor, plan: contract.Plan) -> None:
    """실행기가 예약 직전 검사(check)를 가지면 부른다 — 실제 CLI 실행기의 격리 경로·연결 검사(구조 검토 R4).
    거절하면 예외가 난다. 아무것도 예약·시작하지 않았다. 모의·합성 실행기에는 없다."""
    check = getattr(executor, "check", None)
    if check is not None:
        check(plan)


def _not_started(spec: ParticipantSpec, error: str) -> tuple[runner.RunResult, adapters.Outcome]:
    """프로세스를 만들기 전에 끝난 시도. 아무것도 시작하지 않았으므로 unknown이 아니다."""
    result = runner.RunResult((), runner.FAILED_TO_START, None, "", "", False, False, 0, None, True, error=error)
    return result, adapters.interpret(spec.adapter_id, result, requested_model=spec.model or "")


def _bwrap_trusted() -> bool:
    try:
        isolation._trusted_bwrap()
        return True
    except isolation.IsolationError:
        return False


def packet(run_id: str, pid: str, input_sha256: str, prompt: str) -> str:
    """원본 앱에 옮길 질문. 첫 줄의 실행 표식을 답 첫 줄에 되말해 달라고 적는다(N5)."""
    return PACKET.format(marker=MARKER.format(run_id=run_id, pid=pid, sha8=input_sha256[:8]), prompt=prompt)


def _marker_echo(text: str, run_id: str, pid: str, input_sha256: str) -> tuple[str, str]:
    """답 첫 줄의 실행 표식을 본다. (matched | missing | other_run | other_participant, 표식 줄을 뺀 답).

    표식이 맞다는 것도, 없다는 것도 약한 증거일 뿐이다 — 모델이 되말했는지만 알려 준다. 다른 실행이나 다른
    참여자의 표식이면 다른 카드에 붙여 넣은 것이므로 받지 않는다.
    """
    lines = text.splitlines()
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    found = MARKER_LINE.match(lines[first]) if first is not None else None
    if found is None:
        return "missing", text
    if (found.group(1), found.group(3)) != (run_id, input_sha256[:8]):
        return "other_run", text
    if found.group(2) != pid:
        return "other_participant", text
    return "matched", "\n".join(lines[first + 1:]).strip("\n")


def acceptance(result: runner.RunResult | None, outcome: adapters.Outcome | None) -> tuple[str, str, str | None]:
    """결과 수용 관문. (상태, 상태 코드, controller가 덧붙이는 이유)를 돌려준다. 관측 도구(tools/w2/observe.py)도
    답을 받는 probe에 같은 관문을 쓴다(2026-09-24 리뷰 R03).

    interpret()는 stdin 없는 명령(--version 등)도 해석해야 해서 입력 전달 None을 허용한다. A1은 질문을 늘
    stdin으로 보내므로 끝까지 보낸 기록이 없으면 받지 않는다(A1-02). 질문을 명령줄로 보내는 CLI(agy, K07)를
    붙일 때는 None을 성공으로 넘기지 말고 그 전송 방식의 증거를 따로 정한다.
    """
    if result is None:
        return UNKNOWN, "executor_error", None
    if result.tree_confirmed_empty is not True:
        return UNKNOWN, "unknown", None
    if not outcome.ok:
        return REJECTED, outcome.status, None
    if result.input_delivery != runner.INPUT_COMPLETE:
        return REJECTED, "input_error", "no complete stdin delivery was recorded for this attempt"
    if not (outcome.text or "").strip():
        return REJECTED, "empty_answer", "the CLI returned an empty answer"
    if outcome.model_match is False:
        # 조용한 강등(D18)을 받지 않는다. 별칭으로 요청하면 보고된 전체 이름과 달라 보이므로 요청은 전체 이름으로 한다
        return REJECTED, "model_mismatch", (f"requested {outcome.requested_model}, "
                                            f"reported {', '.join(outcome.reported_models)}")
    return ACCEPTED, outcome.status, None


def _quorum_label(quorum: dict[str, Any]) -> str:
    """공개된 실행의 정족수 표시. 원본 앱 답을 센 실행은 "독립 정족수 충족"이라고 쓰지 않는다."""
    if quorum["policy"] == INDEPENDENT_ONLY:
        extra = f" · 미확인 답 {quorum['unverified']}개는 보조 근거" if quorum["unverified"] else ""
        return f"독립 정족수 충족 — 독립성이 확인된 참여자 {quorum['confirmed']}명(최소 {quorum['min']}명){extra}"
    return (f"미확인 참여 포함 정족수 — 답 {quorum['counted']}명 중 독립성 확인 {quorum['confirmed']}명"
            f"(최소 {quorum['min']}명)")


class ControllerError(ValueError):
    """요청을 받지 않았다. 상태는 바뀌지 않았다."""


class _CapReached(ControllerError):
    """실제 호출 상한에 닿아 시작하지 않았다. 교차검토 라운드는 이 이유로 남은 검토자를 닫는다."""


class Controller:
    def __init__(self, store: Store, executor: Executor, *, max_parallel: int = 2, unsettled_limit: int = 2,
                 timeout: float = 60.0, work_root: str | None = None,
                 max_real_calls: int | None = None, provider_call_caps: dict[str, int] | None = None) -> None:
        self.store, self.executor = store, executor
        self.max_parallel, self.unsettled_limit, self.timeout = max_parallel, unsettled_limit, timeout
        self.work_root = work_root or os.path.join(tempfile.gettempdir(), "dml-work")
        self.max_real_calls, self.provider_call_caps = store.bind_call_budget(max_real_calls, provider_call_caps)
        self.lock = threading.RLock()
        self._closing = False   # 종료 중인 controller는 resume으로 되돌리지 않는다. 원장의 실행 상태와는 별개다.
        # 진행 중인 시도의 신호만 보관한다. 끝난 스레드/질문/작업 경로를 계속 쌓지 않는다.
        self._workers: dict[str, tuple[threading.Thread, threading.Event]] = {}
        self._synthesis: dict[str, tuple[threading.Thread, threading.Event, str]] = {}   # run_id → 진행 중인 실제 합성
        self._supervising: dict[str, tuple[threading.Thread, threading.Event]] = {}   # 시도 ID → 진행 중인 슈퍼바이저 호출(다듬기·제안)
        self._recover()
        with self.lock:   # 앞 검토자가 종료 미확인이 된 교차검토 라운드는 남은 검토자를 바로 닫는다(부르지 않는다)
            self._advance_reviews(start=False)
        # 이전 controller가 시작하지 못한 시도가 남아 있으면 사용자가 이어서 시작하라고 할 때까지 기다린다
        # 교차검토 라운드의 시작하지 않은 검토자도 같다(카드 #140)
        self.paused = self.store.row("SELECT COUNT(*) AS n FROM participants JOIN runs USING (run_id) "
                                     "WHERE state = ? AND NOT cancel_requested", QUEUED)["n"] > 0 or bool(
            self.store.row("SELECT 1 FROM reviews WHERE state = ?", QUEUED))

    # ---- 만들기와 예약 -------------------------------------------------------------------------
    def prepare_run(self, question: str, participants: list[ParticipantSpec], *, min_independent: int,
                    quorum_policy: str = INDEPENDENT_ONLY, sources=None, task_id=None, task_title=None,
                    role_board=None, roster=None, run_id=None, assignments=None, refinement=None,
                    proposal=None, split=None, checked=None, use_memory=True) -> dict[str, Any]:
        """sources: (이름, 글) 목록. 원장에 내용·해시를 고정하고, CLI 참여자에게는 그 사본 폴더 하나를 읽기
        전용 입력으로 준다(provider별 빈 입력 폴더 대신). 입력 폴더가 하나인 것은 같으므로 계획의 판은 그대로다.
        checked: create_run이 이미 검사한 (이름, 바이트) 목록 — 있으면 sources를 다시 검사하지 않는다.

        역할판의 일반 칸을 채운 실행(카드 #125)은 assignments로 팀원마다 {task, sources: [자료 이름]}을 받는다.
        정족수 인자는 쓰지 않는다. 팀원마다 입력 전문이 다르고, 받은 자료만 든 폴더를 따로 받는다.

        다듬기 모드(카드 #130)는 refinement={id, turn}으로 승인할 차례를 받는다. question은 그 차례의 다듬은 문장과 같아야
        하고, 격리 팀원에게는 그 문장만 간다 — 원문과 다듬기 대화는 확인 명세에만 싣고 참여자 입력에 넣지 않는다.

        다음 단계 제안(카드 #133)에서 온 실행은 proposal={id}를 받는다. 같은 작업·원문 모드·제안한 질문 그대로여야 하고,
        제안은 그 실행 하나에만 묶인다."""
        question = question.strip()
        if not question:
            raise ControllerError("question is empty")
        if not storable(question):
            raise ControllerError("the question contains text that is not valid Unicode")
        checked_sources = _checked_sources(sources) if checked is None else checked
        if len({p.pid for p in participants}) != len(participants) or not participants:
            raise ControllerError("participants must be unique and non-empty")
        for p in participants:
            if p.transport not in (CLI, MANUAL) or (p.transport == CLI and p.adapter_id not in self.executor.adapter_ids):
                raise ControllerError(f"unsupported participant {p.pid!r}")
        try:
            roles = freeze_roles(role_board, participants, roster or {p.pid: p for p in participants})
        except ValueError as exc:
            raise ControllerError(str(exc)) from None
        general = bool(roles["general"])
        if not general and assignments is not None:
            raise ControllerError("맡길 일은 일반 칸의 팀원에게만 줍니다.")
        if roles["input_mode"] == "refine":
            approved = self._approved_refinement(refinement, roles, question, task_id, use_memory)
        elif refinement is not None:
            raise ControllerError("다듬기 차례는 다듬기 모드에서만 줍니다.")
        else:
            approved = None
        if not general and quorum_policy not in QUORUM_POLICIES:
            raise ControllerError(f"quorum_policy must be one of {', '.join(QUORUM_POLICIES)}")
        # 프런트엔드가 false를 보내도 실행기의 opt-in 등급을 올려 주지 않는다. 더 낮은 등급은 보존한다.
        if getattr(self.executor, "allow_context_unverified", False):
            participants = [replace(p, context_unverified=True) if p.transport == CLI else p for p in participants]
            roles["general" if general else "isolated"] = [asdict(p) for p in participants]
        if not general:
            confirmable = sum(confirmed(asdict(p)) for p in participants)
            if quorum_policy == INDEPENDENT_ONLY and min_independent > confirmable:
                raise ControllerError(f"only {confirmable} participant(s) can be confirmed independent (CLI); lower "
                                      "min_independent or choose include_unverified to count unverified answers")
            try:
                m.start(tuple(p.pid for p in participants), min_independent=min_independent)
            except m.MembershipError as exc:
                raise ControllerError(str(exc)) from None
        if proposal is not None and general:
            raise ControllerError("제안한 질문은 격리 실행으로 보냅니다.")
        if split is not None and not general:
            raise ControllerError("분담 제안은 일반 팀원 작업에만 씁니다.")
        if run_id is None:
            run_id = f"r{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"
        elif not isinstance(run_id, str) or not re.fullmatch(r"r[0-9]{4}-[0-9]{6}-[0-9a-f]{32}", run_id):
            raise ControllerError("invalid preview run ID")
        if task_id is not None:
            if not isinstance(task_id, str) or not self.store.row("SELECT 1 FROM tasks WHERE task_id = ?", task_id):
                raise ControllerError("작업을 찾을 수 없습니다.")
            if task_title is not None:
                raise ControllerError("기존 작업의 제목은 실행 생성으로 바꿀 수 없습니다.")
        elif task_title is not None and (not isinstance(task_title, str) or not task_title.strip()
                                         or len(task_title.strip()) > 120 or not storable(task_title)):
            raise ControllerError("작업 제목은 1~120자의 올바른 글이어야 합니다.")
        roles["memory"] = self._select_memory(task_id, question, use_memory)
        suggested = self._approved_proposal(proposal, roles, question, task_id) if proposal is not None else None
        if general:
            return self._general_manifest(run_id, task_id, task_title, question, participants, roles,
                                          checked_sources, assignments, split)
        prompt = PROMPT.format(question=question)
        if checked_sources:
            prompt += _source_footer(self._source_root(run_id), [
                {"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for name, data in checked_sources])
        data = prompt.encode("utf-8")
        manifest = {"run_id": run_id, "task_id": task_id, "task_title": task_title.strip() if task_title else question[:120],
                    "mode": ISOLATED, "question": question, "prompt": prompt, "input_sha256": hashlib.sha256(data).hexdigest(),
                    "input_bytes": len(data), "role_config": roles,
                    "min_independent": min_independent, "quorum_policy": quorum_policy,
                    "sources": [{"name": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
                                for name, content in checked_sources],
                    "calls": {"draft_cli": sum(p.transport == CLI for p in participants),
                              "model_calls": 0 if self.executor.kind != contract.REAL else None,
                              "live_cap": self.max_real_calls, "provider_caps": dict(self.provider_call_caps)},
                    "manual_packets": {p.pid: packet(run_id, p.pid, hashlib.sha256(data).hexdigest(), prompt)
                                       for p in participants if p.transport == MANUAL}}
        if approved is not None:
            manifest["refinement"] = approved   # 원문·승인한 차례. 참여자 입력(prompt)에는 승인한 문장만 있다
        if suggested is not None:
            manifest["proposal"] = suggested    # 이 질문을 제안한 실행과 제안. 내가 확인해 시작해야 묶인다
        manifest["confirmation"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return manifest

    def _general_manifest(self, run_id, task_id, task_title, question, participants, roles, checked_sources,
                          assignments, split=None) -> dict[str, Any]:
        """일반 실행의 확인 명세. 팀원마다 맡긴 일·입력 전문·받은 자료(이름·해시·크기·종류·범위)를 고정한다. 아무
        팀원도 받지 않는 자료는 원장에 두지 않도록 거절한다. 실행의 입력 해시는 팀원별 입력 해시를 묶은 것이다."""
        if not isinstance(assignments, dict) or set(assignments) != {p.pid for p in participants}:
            raise ControllerError("일반 팀원마다 맡길 일과 받을 자료가 필요합니다.")
        contents = dict(checked_sources)
        members, used = {}, set()
        for p in participants:
            item = assignments[p.pid]
            if not isinstance(item, dict) or set(item) != {"task", "sources"}:
                raise ControllerError(f"{p.label}: 맡길 일(task)과 받을 자료(sources)만 적습니다.")
            task = item["task"].strip() if isinstance(item["task"], str) else ""
            if not task or len(task) > MAX_TASK_CHARS or not storable(task):
                raise ControllerError(f"{p.label}: 맡길 일은 1~{MAX_TASK_CHARS}자의 올바른 글이어야 합니다.")
            names = item["sources"]
            if (not isinstance(names, list) or any(not isinstance(n, str) or n not in contents for n in names)
                    or len(set(names)) != len(names)):
                raise ControllerError(f"{p.label}: 받을 자료는 이번에 붙인 자료의 이름을 한 번씩만 적습니다.")
            used.update(names)
            listed = [{"name": n, "bytes": len(contents[n]), "sha256": hashlib.sha256(contents[n]).hexdigest(),
                       "kind": SOURCE_KIND_ORIGINAL, "range": SOURCE_RANGE_WHOLE} for n in sorted(names)]
            prompt = GENERAL_PROMPT.format(question=question, task=task)
            if listed:
                prompt += _source_footer(self._member_source_root(run_id, p.pid), listed)
            prompt += memory.footer(roles["memory"])
            data = prompt.encode("utf-8")
            members[p.pid] = {"task": task, "prompt": prompt, "input_sha256": hashlib.sha256(data).hexdigest(),
                              "input_bytes": len(data), "sources": listed}
        unused = sorted(set(contents) - used)
        if unused:
            raise ControllerError("아무 팀원도 받지 않는 자료가 있습니다: " + ", ".join(unused))
        manifest = {"run_id": run_id, "task_id": task_id, "task_title": task_title.strip() if task_title else question[:120],
                    "mode": GENERAL, "question": question, "prompt": "",
                    "input_sha256": _bundle_digest(members), "input_bytes": sum(v["input_bytes"] for v in members.values()),
                    "role_config": roles, "min_independent": 0, "quorum_policy": NO_QUORUM,
                    "sources": [{"name": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
                                for name, content in checked_sources],
                    "assignments": members,
                    "calls": {"draft_cli": len(participants),
                              "model_calls": 0 if self.executor.kind != contract.REAL else None,
                              "live_cap": self.max_real_calls, "provider_caps": dict(self.provider_call_caps)},
                    "manual_packets": {}}
        if split is not None:   # 맡길 일·자료를 검사한 뒤에 제안과 견준다(카드 #135)
            manifest["split"] = self._approved_split(split, roles, question, participants, assignments,
                                                     checked_sources, task_id)
        manifest["confirmation"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return manifest

    def create_run(self, question: str, participants: list[ParticipantSpec], *, min_independent: int,
                   quorum_policy: str = INDEPENDENT_ONLY, sources=None, task_id=None, task_title=None,
                   role_board=None, roster=None, run_id=None, confirmation=None, assignments=None,
                   refinement=None, proposal=None, split=None, use_memory=True) -> str:
        checked_sources = _checked_sources(sources)   # 한 번 검사해 확인 명세와 원장 쓰기가 같은 바이트를 쓴다
        prepared = self.prepare_run(question, participants, min_independent=min_independent,
                                    quorum_policy=quorum_policy, sources=sources, task_id=task_id, task_title=task_title,
                                    role_board=role_board, roster=roster, run_id=run_id, assignments=assignments,
                                    refinement=refinement, proposal=proposal, split=split, checked=checked_sources,
                                    use_memory=use_memory)
        if confirmation is not None and confirmation != prepared["confirmation"]:
            raise ControllerError("확인한 입력에서 바뀌었습니다. 보낼 입력을 다시 확인하세요.")
        run_id, question, prompt = prepared["run_id"], prepared["question"], prepared["prompt"]
        general = prepared["mode"] == GENERAL
        input_sha256, input_bytes = prepared["input_sha256"], prepared["input_bytes"]
        min_independent, quorum_policy = prepared["min_independent"], prepared["quorum_policy"]
        participants = [ParticipantSpec(**p) for p in prepared["role_config"]["general" if general else "isolated"]]
        with self.lock, self.store.tx() as tx:
            if self._closing:
                raise ControllerError("controller is shutting down")
            if self.store.row("SELECT 1 FROM runs WHERE run_id = ?", run_id):
                raise ControllerError("이미 시작한 실행입니다. 같은 확인으로 다시 부르지 않습니다.")
            if role_board is not None and (self.store.row(
                    "SELECT 1 FROM runs WHERE phase = 'drafting' AND NOT cancel_requested")
                    or self._slots_used() or self.unsettled()):
                raise ControllerError("진행 중이거나 종료 미확인인 실행을 먼저 정리하세요. A 단계는 동시 작업을 시작하지 않습니다.")
            if task_id is None:
                task_id = "t-" + run_id
                tx.execute("INSERT INTO tasks VALUES (?, ?, ?)", task_id, prepared["task_title"], time.time())
            for name, content in checked_sources:
                tx.execute("INSERT INTO sources (run_id, name, sha256, bytes, content) VALUES (?, ?, ?, ?, ?)",
                           run_id, name, hashlib.sha256(content).hexdigest(), len(content), content)
            tx.execute("INSERT INTO runs (run_id, created_at, question, prompt, input_sha256, input_bytes, "
                       "min_independent, roster, quorum_policy, task_id, role_config, mode) "
                       "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       run_id, time.time(), question, prompt, input_sha256, input_bytes,
                       min_independent, "{}", quorum_policy, task_id, json.dumps(prepared["role_config"], ensure_ascii=False),
                       prepared["mode"])
            if prepared.get("refinement"):
                # 다듬기는 실행 하나에만 묶인다. 같은 승인으로 두 번 부르면 여기서 거래 전체가 되돌려진다.
                chosen = prepared["refinement"]
                if not tx.execute("UPDATE refinements SET run_id = ?, approved_turn = ? WHERE refine_id = ? "
                                  "AND run_id IS NULL", run_id, chosen["turn"], chosen["refine_id"]):
                    raise ControllerError("이미 다른 실행에 쓴 다듬기입니다. 같은 승인으로 실행을 두 번 만들지 않습니다.")
                tx.event(chosen["refine_id"], "refine_approved", used_by=run_id, turn=chosen["turn"])
            if prepared.get("proposal"):
                # 제안은 실행 하나에만 묶인다. 같은 제안으로 두 번 부르면 거래 전체가 되돌려진다.
                chosen = prepared["proposal"]
                if not tx.execute("UPDATE proposals SET used_by = ? WHERE proposal_id = ? AND used_by IS NULL",
                                  run_id, chosen["proposal_id"]):
                    raise ControllerError("이미 실행에 쓴 제안입니다. 같은 제안으로 실행을 두 번 만들지 않습니다.")
                tx.event(chosen["source_run"], "proposal_used", proposal_id=chosen["proposal_id"], used_by=run_id)
            if prepared.get("split"):
                # 분담 제안도 실행 하나에만 묶인다. 제안대로였는지(as_proposed)를 함께 남긴다.
                chosen = prepared["split"]
                if not tx.execute("UPDATE splits SET used_by = ?, as_proposed = ? WHERE split_id = ? AND used_by IS NULL",
                                  run_id, int(chosen["as_proposed"]), chosen["split_id"]):
                    raise ControllerError("이미 실행에 쓴 분담 제안입니다. 같은 제안으로 실행을 두 번 만들지 않습니다.")
                tx.event(chosen["split_id"], "split_used", used_by=run_id, as_proposed=chosen["as_proposed"])
            for pid, item in (prepared.get("assignments") or {}).items():
                tx.execute("INSERT INTO assignments VALUES (?, ?, ?, ?, ?, ?, ?)", run_id, pid, item["task"],
                           item["prompt"], item["input_sha256"], item["input_bytes"],
                           json.dumps(item["sources"], ensure_ascii=False))
            for p in participants:
                tx.execute("INSERT INTO participants (run_id, pid, spec, state) VALUES (?, ?, ?, ?)", run_id, p.pid,
                           json.dumps(asdict(p), ensure_ascii=False), QUEUED if p.transport == CLI else AWAITING_USER)
            tx.event(run_id, "run_created", input_sha256=input_sha256, input_bytes=input_bytes,
                     participants=[p.pid for p in participants], min_independent=min_independent,
                     quorum_policy=quorum_policy, mode=prepared["mode"],
                     **({"refinement": {"refine_id": prepared["refinement"]["refine_id"],
                                        "turn": prepared["refinement"]["turn"],
                                        "original_sha256": hashlib.sha256(
                                            prepared["refinement"]["original"].encode("utf-8")).hexdigest()}}
                        if prepared.get("refinement") else {}),
                     sources=[{"name": name, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
                              for name, content in checked_sources],
                     **({"assignments": {pid: {"input_sha256": item["input_sha256"],
                                               "sources": [s["name"] for s in item["sources"]]}
                                         for pid, item in prepared["assignments"].items()}} if general else {}))
            tx.event(run_id, "drafting_started")
        self.pump()
        return run_id

    def _source_root(self, run_id: str) -> str:
        """참여자가 읽기 전용으로 볼 자료 폴더. 참여자의 작업 폴더(work_root/<run>/<pid>)와 겹치지 않는다."""
        return os.path.join(self.work_root, "_sources", run_id)

    def sources(self, run_id: str) -> list[dict[str, Any]]:
        """화면·보고에 보일 목록. 내용은 넘기지 않는다."""
        return [{"name": row["name"], "sha256": row["sha256"], "bytes": row["bytes"]} for row in self.store.rows(
            "SELECT name, sha256, bytes FROM sources WHERE run_id = ? ORDER BY name", run_id)]

    def _source_dir(self, run_id: str) -> str | None:
        """원장의 자료를 폴더로 두고, 시도마다 원장의 목록·크기·sha256과 다시 맞춘다. 다르면 거절한다 — 아무것도
        시작하지 않았다. 폴더는 임시 이름으로 다 쓴 뒤 한 번에 옮긴다. 시도 도중의 바꿔치기(K14)는 막지 못한다."""
        rows = self.store.rows("SELECT name, sha256, bytes, content FROM sources WHERE run_id = ? ORDER BY name", run_id)
        root = self._source_root(run_id)
        run = self._run(run_id)
        expected = PROMPT.format(question=run["question"]) + (_source_footer(root, rows) if rows else "")
        if run["prompt"] != expected:
            raise ControllerError("the fixed source manifest or folder differs from the original prompt; "
                                  "no call was started")
        return self._snapshot(root, rows) if rows else None

    def _member_source_root(self, run_id: str, pid: str) -> str:
        """일반 팀원 한 명이 받는 자료 폴더. 그 팀원이 받은 자료만 든다 — 다른 팀원의 자료 폴더는 연결하지 않는다."""
        return os.path.join(self._source_root(run_id), pid)

    def _assignment(self, run_id: str, pid: str):
        row = self.store.row("SELECT * FROM assignments WHERE run_id = ? AND pid = ?", run_id, pid)
        if row is None:
            raise ControllerError(f"no assignment for {pid!r} in {run_id!r}")
        return row

    def _member_source_dir(self, run_id: str, pid: str) -> str | None:
        """일반 팀원의 입력 전문을 원장의 목표·맡긴 일·자료 목록으로 다시 만들어 저장한 입력과 해시를 맞추고, 그 팀원이
        받은 자료만 폴더로 둔다. 다르면 거절한다 — 아무것도 시작하지 않았다. _source_dir와 같은 규칙이다."""
        run, item = self._run(run_id), self._assignment(run_id, pid)
        listed = json.loads(item["sources"])
        root = self._member_source_root(run_id, pid)
        expected = GENERAL_PROMPT.format(question=run["question"], task=item["task"]) + (
            _source_footer(root, listed) if listed else "")
        expected += self._run_memory(run)
        data = item["prompt"].encode("utf-8")
        if (item["prompt"] != expected or hashlib.sha256(data).hexdigest() != item["input_sha256"]
                or len(data) != item["input_bytes"]):
            raise ControllerError("the fixed assignment differs from its recorded input; no call was started")
        # 행 하나를 스스로 맞게(맡긴 일·입력 전문·해시·크기를 함께) 바꿔도 실행을 만들 때 묶은 입력 해시와는 다르다
        # (Codex 교차검토, PR #129).
        members = {row["pid"]: row for row in self.store.rows(
            "SELECT pid, input_sha256 FROM assignments WHERE run_id = ?", run_id)}
        if _bundle_digest(members) != run["input_sha256"]:
            raise ControllerError("the fixed assignment differs from the input bundled when the run was created; "
                                  "no call was started")
        if not listed:
            return None
        rows = [self.store.row("SELECT name, sha256, bytes, content FROM sources WHERE run_id = ? AND name = ?",
                               run_id, source["name"]) for source in listed]
        if any(row is None or (row["sha256"], row["bytes"]) != (source["sha256"], source["bytes"])
               or source.get("kind") != SOURCE_KIND_ORIGINAL for row, source in zip(rows, listed)):
            raise ControllerError("the source snapshot changed after the run was created; no call was started")
        return self._snapshot(root, rows)

    def _attempt_input(self, run_id: str, pid: str) -> tuple[str, str | None]:
        """이 참여자에게 보낼 입력 전문과 읽기 전용 자료 폴더. 격리 실행은 모두 같은 입력, 일반 실행은 팀원마다 다르다."""
        run = self._run(run_id)
        if run["mode"] == GENERAL:
            return self._assignment(run_id, pid)["prompt"], self._member_source_dir(run_id, pid)
        return run["prompt"], self._source_dir(run_id)

    def _snapshot(self, root: str, rows) -> str:
        """원장의 자료 행(이름·sha256·크기·내용)을 root 폴더로 두고 다시 맞춘다."""
        if not os.path.isdir(root):
            staging = f"{root}.{uuid.uuid4().hex}.tmp"
            os.makedirs(staging)
            for row in rows:
                path = os.path.join(staging, row["name"])
                with open(path, "xb") as handle:
                    handle.write(row["content"])
                if os.name == "posix":
                    os.chmod(path, 0o444)
            os.rename(staging, root)   # 원장은 controller 하나만 열고 계획은 self.lock 안에서만 한다 — 경쟁 없음
        if sorted(os.listdir(root)) != [row["name"] for row in rows]:
            raise ControllerError("the source snapshot changed after the run was created; no call was started")
        for row in rows:
            path = os.path.join(root, row["name"])
            if os.path.islink(path) or not os.path.isfile(path):
                raise ControllerError("the source snapshot changed after the run was created; no call was started")
            with open(path, "rb") as handle:
                data = handle.read(MAX_SOURCE_BYTES + 1)
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ControllerError("the source snapshot changed after the run was created; no call was started")
        return root

    def _synthesis_attempts(self, run_id: str | None = None) -> dict:
        """한 사건 투영을 호출 제한·자리·종료 확인·화면이 같이 사용한다. controller.lock 안에서 읽는다."""
        rows = self.store.rows("SELECT run_id, kind, payload FROM events WHERE kind IN "
                               "('synthesis_started', 'synthesis_failed', 'synthesis_completed', "
                               "'synthesis_unknown_acknowledged')" + (" AND run_id = ?" if run_id else "") +
                               " ORDER BY run_id, seq", *((run_id,) if run_id else ()))
        return synthesis_attempts(rows, ((rid, worker[2]) for rid, worker in self._synthesis.items()))

    def _seat_count(self, *states: str) -> int:
        """상위 모델 호출(SEATS의 모든 표)에서 주어진 상태인 행의 수."""
        marks = ", ".join("?" for _ in states)
        return sum(self.store.row(f"SELECT COUNT(*) AS n FROM {seat.table} WHERE state IN ({marks})", *states)["n"]
                   for seat in SEATS)

    def _slots_used(self, attempts: dict | None = None) -> int:
        """attempts: 같은 요청에서 이미 만든 전역 합성 이력(view가 한 번 만들어 넘긴다, S6). 없으면 새로 읽는다."""
        attempts = self._synthesis_attempts() if attempts is None else attempts
        return sum(item["status"] in (RUNNING, UNKNOWN) for item in attempts.values()) + self.store.row(
            "SELECT COUNT(*) AS n FROM participants WHERE state IN (?, ?)", RUNNING, UNKNOWN)["n"] + self._seat_count(
            RUNNING, UNKNOWN)

    def _budget_exhausted(self, adapter_id: str) -> bool:
        """전체·provider 상한. 거래 안에서 읽고 같은 거래에서 예약한다 — 병렬 요청이 마지막 한 칸을 함께 쓰지 못한다."""
        budget, provider = self.call_budget(), self.call_budget(adapter_id)
        return budget["used"] >= budget["cap"] or bool(self.provider_call_caps and (
            provider["cap"] is None or provider["used"] >= provider["cap"]))

    def _unknown_slots(self, attempts: dict | None = None) -> int:
        """종료를 확인하지 못해 자리를 쥔 시도: 참여자·합성·상위 모델 호출(다듬기·제안·분담·모으기·검토)."""
        attempts = self._synthesis_attempts() if attempts is None else attempts
        return (self.store.row("SELECT COUNT(*) AS n FROM participants WHERE state = ?", UNKNOWN)["n"]
                + sum(item["status"] == UNKNOWN for item in attempts.values())
                + self._seat_count(UNKNOWN))

    def unsettled(self, attempts: dict | None = None) -> int:
        with self.lock:
            return self._unknown_slots(attempts) + runner.lingering()

    def call_budget(self, adapter_id: str | None = None) -> dict[str, int | None]:
        """실제 CLI를 시작하기 전에 원장에 예약한다. 재시작·실패·취소로 환불하지 않는다(계정 잔여와 다름)."""
        if self.max_real_calls is None:
            return {"used": 0, "cap": None}
        reservations = self.store.rows("SELECT payload FROM events WHERE kind = 'live_call_reserved'")
        used = len(reservations) if adapter_id is None else sum(
            json.loads(row["payload"]).get("adapter_id") == adapter_id for row in reservations)
        return {"used": used, "cap": self.max_real_calls if adapter_id is None
                else self.provider_call_caps.get(adapter_id)}

    def claude_account_limit(self) -> dict[str, Any] | None:
        """마지막으로 끝난 실제 Claude 시도가 stream에서 받은 계정 한도(rate_limit_event)와 그 관측 시각.

        모델을 더 부르지 않는다. 봉인 중인 실행의 값은 내보내지 않는다 — 계정 비율의 변화도 아직 답하는 참여자의
        초안 길이를 짐작하게 한다(2026-09-24 리뷰 8번). 모의·합성 실행기의 시도는 계정 값이 아니므로 쓰지 않는다.
        """
        with self.lock:
            for event in self.store.rows("SELECT run_id, at, payload FROM events WHERE kind IN ('draft_sealed', "
                                         "'result_accepted', 'attempt_rejected', 'synthesis_completed', 'synthesis_failed') "
                                         "ORDER BY at DESC LIMIT 200"):
                payload = json.loads(event["payload"])
                result = payload.get("result") or {}
                if "synthesizer" in result:   # 실제 합성은 공개 뒤에만 돈다 — 봉인 중인 초안이 없다
                    limit = result["synthesizer"].get("rate_limit")
                    if limit and result["synthesizer"].get("execution") == contract.REAL:
                        return {**limit, "observed_at": int(event["at"])}
                    continue
                limit = result.get("rate_limit")
                if not limit:
                    continue
                part = self.store.row("SELECT kind FROM participants WHERE run_id = ? AND pid = ? AND attempt = ?",
                                      event["run_id"], payload.get("pid"), payload.get("attempt"))
                current = self._gate(event["run_id"])
                if part is None or part["kind"] != contract.REAL or not (current.settled or current.revealed):
                    continue
                return {**limit, "observed_at": int(event["at"])}
        return None

    def pump(self) -> None:
        """자리와 상한이 허락하는 만큼 대기 중인 시도를 시작한다. 한 참여자에 한 번만 — 다시 부르지 않는다.

        queued → running은 조건부로 바꾼다. 다른 controller가 먼저 가져갔으면 건너뛴다(같은 journal을 연
        controller 둘이 같은 참여자를 두 번 부르던 문제, A1 리뷰 반영).
        """
        with self.lock:
            if self._closing:
                return
            # 교차검토: 앞 검토자가 받지 못한 라운드는 관문과 상관없이 닫고, 관문이 열려 있으면 다음 검토자를 부른다
            held = self.paused or self.unsettled() >= self.unsettled_limit
            self._advance_reviews(start=not held)
            if held:
                return
            queued = self.store.rows("SELECT p.run_id, p.pid, p.spec FROM participants p JOIN runs r USING (run_id) "
                                     "WHERE p.state = ? AND NOT r.cancel_requested ORDER BY r.created_at, p.rowid", QUEUED)
            every = self._synthesis_attempts()   # 이 lock 안에서는 합성이 새로 시작되지 않는다 — 한 번만 읽는다
            for row in queued:
                if self._slots_used(every) >= self.max_parallel:
                    return
                spec = ParticipantSpec(**json.loads(row["spec"]))
                attempt = uuid.uuid4().hex
                work = os.path.join(self.work_root, row["run_id"], spec.pid)
                # 최종 계획을 한 번 만든다. 그 기록(질문 본문 없이)과 실행 종류를 시도 ID와 함께 저장한 뒤에만 같은
                # 계획을 실행한다(G4·G6). 저장하지 못하면 실행하지 않는다.
                try:
                    # 작업 폴더 준비도 시작 전 실패다. 여기서 빠져나가면 이 참여자가 queued로 남아 다음 pump마다
                    # 대기열 맨 앞에서 다시 멈춘다(구조 검토 AH-02). 이 참여자만 시작 전 실패로 닫고 다음으로 간다.
                    os.makedirs(work, exist_ok=True)
                    # 자료가 있는 실행은 그 사본 폴더 하나를 입력으로 준다(일반 팀원은 자기가 받은 자료만).
                    # 입력 전문·목록·해시가 다르면 여기서 거절된다.
                    prompt, source = self._attempt_input(row["run_id"], spec.pid)
                    extra = {"inputs": (source,)} if source else {}
                    plan, refused = self.executor.plan(spec, prompt, work, **extra), None
                    if plan.context_unverified and not spec.context_unverified:
                        raise ControllerError("queued participant has a different context policy; create a new run")
                    _check(self.executor, plan)   # 예약 전에 격리 경로·연결을 본다(R4)
                    record, kind = plan.record(), plan.kind
                except Exception as exc:  # 거절: 아무것도 시작하지 않았다
                    plan, refused = None, f"{type(exc).__name__}: {exc}"
                    record, kind = {"adapter_id": spec.adapter_id, "refused": refused}, self.executor.kind
                with self.store.tx() as tx:
                    # 같은 거래에서 검사와 예약을 한다. 병렬 pump도 마지막 한 칸을 함께 쓰지 못한다.
                    if plan is not None and plan.kind == contract.REAL and self.max_real_calls is not None:
                        if self._budget_exhausted(spec.adapter_id):
                            plan, refused = None, "real CLI call budget exhausted; no call was started"
                            record = {"adapter_id": spec.adapter_id, "refused": refused}
                    part = self._part(row["run_id"], spec.pid)
                    taken = (self._gate(row["run_id"]).accepting and part["state"] == QUEUED
                             and self._transition(tx, part, RUNNING, attempt=attempt, kind=kind))
                    if taken:
                        if plan is not None and plan.kind == contract.REAL and self.max_real_calls is not None:
                            tx.event(row["run_id"], "live_call_reserved", pid=spec.pid, attempt=attempt,
                                     adapter_id=spec.adapter_id, cap=self.max_real_calls)
                        tx.event(row["run_id"], "attempt_started", pid=spec.pid, attempt=attempt,
                                 executor=self.executor.name, execution=kind, behavior=spec.behavior, spec=record)
                if not taken:
                    continue
                if plan is None:
                    self._finish(row["run_id"], spec.pid, attempt, *_not_started(spec, refused))
                    continue
                cancel = threading.Event()
                thread = threading.Thread(target=self._attempt,
                                          args=(row["run_id"], spec, attempt, plan, cancel), daemon=True)
                self._workers[attempt] = (thread, cancel)
                try:
                    thread.start()
                except RuntimeError:
                    self._workers.pop(attempt)
                    self._finish(row["run_id"], spec.pid, attempt, *_not_started(spec, "worker thread did not start"))

    def resume(self) -> None:
        """다시 시작한 뒤 멈춰 둔 대기 시도를 사용자가 이어서 시작하라고 했다."""
        with self.lock:
            if self._closing:
                raise ControllerError("controller is shutting down")
            self.paused = False
        self.pump()

    def _attempt(self, run_id: str, spec: ParticipantSpec, attempt: str, plan: contract.Plan,
                 cancel: threading.Event) -> None:
        try:
            try:
                result, outcome = self.executor.run(plan, self.timeout, cancel=cancel)
            except Exception as exc:  # 실행기 자체 실패: 자손 종료는 확인하지 못했다
                result, outcome, detail = None, None, f"executor error: {type(exc).__name__}"
            else:
                detail = None
            try:
                self._finish(run_id, spec.pid, attempt, result, outcome, detail)
            except Exception as exc:  # 결과를 저장하지 못했다 — 시도를 RUNNING으로 남기지 않는다(카드 #70)
                self._finish_unstored(run_id, spec.pid, attempt, result, exc)
        finally:
            with self.lock:
                self._workers.pop(attempt, None)
                self.pump()

    # ---- 결과 수용 관문 ------------------------------------------------------------------------
    def _finish_unstored(self, run_id, pid, attempt, result, exc) -> None:
        """결과 저장이 예외로 끝난 시도를 닫는다. 자손 종료가 확인됐을 때만 rejected, 아니면 unknown이다.
        호출은 이미 시작했으므로 예산을 되돌리지 않고 자동으로 다시 부르지 않는다(외부 검토 R05)."""
        state = REJECTED if result is not None and result.tree_confirmed_empty is True else UNKNOWN
        detail = f"the result could not be stored ({type(exc).__name__}); the answer was discarded"
        with self.lock, self.store.tx() as tx:
            expected = {"run_id": run_id, "pid": pid, "state": RUNNING, "attempt": attempt}
            if self._transition(tx, expected, state, status="result_not_stored", detail=detail):
                tx.event(run_id, "attempt_result_not_stored", pid=pid, attempt=attempt, error=type(exc).__name__)
                if state == UNKNOWN:
                    tx.event(run_id, "attempt_unknown", pid=pid, attempt=attempt, result=None, detail=detail)
                self._maybe_reveal(run_id, tx)

    def _finish(self, run_id, pid, attempt, result, outcome, detail=None) -> None:
        with self.lock:
            summary = None if result is None else {
                "state": result.state, "exit_code": result.exit_code, "containment": result.containment,
                "tree_confirmed_empty": result.tree_confirmed_empty, "input_delivery": result.input_delivery,
                "duration_ms": result.duration_ms, "notes": list(result.notes),
                "status": outcome.status, "ok": outcome.ok, "detail": outcome.detail, "usage": outcome.usage,
                "requested_model": outcome.requested_model, "reported_models": list(outcome.reported_models),
                "model_match": outcome.model_match, "rate_limit": outcome.rate_limit}
            state, status, why = acceptance(result, outcome)
            detail = detail or why or (outcome.detail if outcome else None)
            if state == ACCEPTED and not storable(outcome.text):
                # 봉인할 초안은 원문 그대로여야 한다 — 표기를 바꾸지 않고 형식 오류로 받지 않는다(카드 #70).
                state, status = REJECTED, "format_error"
                detail = "the answer contains text that is not valid Unicode (a lone surrogate); it was not sealed"
            if summary is not None:
                stored = _storable_meta(summary)
                if stored != summary:
                    stored["escaped_text"] = True   # 진단 메타데이터의 표기를 바꿨다
                summary = stored
            detail = _storable_meta(detail)
            with self.store.tx() as tx:
                current_gate = self._gate(run_id)
                if not current_gate.accepting:
                    # 신호를 늦게 본 실행기의 정상 답도 끝난 실행에는 봉인/공개하지 않는다.
                    state = REJECTED if result is not None and result.tree_confirmed_empty is True else UNKNOWN
                    status = "cancelled" if state == REJECTED else "cancel_unconfirmed"
                    detail = "run no longer accepts results; answer discarded"
                # 이 시도가 아직 이 참여자의 진행 중인 시도일 때만 반영한다. 다시 시작한 controller가 unknown으로
                # 돌렸거나 사용자가 종료를 확인한 뒤에 온 결과는 사건으로만 남긴다 — 초안·명단은 그대로다.
                expected = {"run_id": run_id, "pid": pid, "state": RUNNING, "attempt": attempt}
                if not self._transition(tx, expected, state, status=status, detail=detail,
                                        result=json.dumps(summary, ensure_ascii=False)):
                    tx.event(run_id, "attempt_result_ignored", pid=pid, attempt=attempt, result=summary)
                    return
                if state == UNKNOWN:
                    tx.event(run_id, "attempt_unknown", pid=pid, attempt=attempt, result=summary, detail=detail)
                elif state == ACCEPTED:
                    tx.execute("INSERT OR REPLACE INTO drafts VALUES (?, ?, ?, ?, ?, ?)", run_id, pid, outcome.text,
                               hashlib.sha256(outcome.text.encode("utf-8")).hexdigest(), CLI, time.time())
                    # 일반 팀원의 답은 봉인하지 않는다 — 받는 즉시 화면에 보이므로 사건 이름도 따로 둔다
                    tx.event(run_id, "result_accepted" if current_gate.general else "draft_sealed",
                             pid=pid, attempt=attempt, result=summary)
                else:
                    tx.event(run_id, "attempt_rejected", pid=pid, attempt=attempt, status=status, result=summary)
                self._maybe_reveal(run_id, tx)

    def _maybe_reveal(self, run_id: str, tx) -> None:
        """남은 참여자가 모두 끝났고 정족수가 있으면 연다. 빠진 사람이 있으면 축소 승인이 먼저다.

        상태를 바꾼 거래 안에서 부른다. 거래 안의 읽기는 그 거래가 쓴 것까지 본다. 일반 실행은 공개가 아니라 모음으로
        닫는다 — 팀원이 모두 끝나면(종료 미확인 없이) 더 받지 않고 사람의 판단 차례가 된다.
        """
        current_gate = self._gate(run_id)
        if current_gate.general:
            if current_gate.can_collect and tx.execute(
                    "UPDATE runs SET phase = ? WHERE run_id = ? AND phase = ? AND NOT cancel_requested",
                    COLLECTED, run_id, m.DRAFTING):
                tx.event(run_id, "collected", accepted=len(current_gate.requested) - len(current_gate.dropped),
                         failed=list(current_gate.dropped))
            return
        if current_gate.can_reveal:
            if tx.execute("UPDATE runs SET phase = ? WHERE run_id = ? AND phase = ? AND NOT cancel_requested",
                          m.REVEALED, run_id, m.DRAFTING):
                tx.event(run_id, "revealed", drafts=len(current_gate.requested) - len(current_gate.dropped),
                         quorum=current_gate.quorum)
        elif current_gate.status in ("reduction_required", "quorum_blocked"):
            # note is derived, not a mutable copy of the policy decision. Keep only a bounded event lookup.
            prior = self.store.row("SELECT payload FROM events WHERE run_id = ? AND kind = 'reveal_held' "
                                   "ORDER BY seq DESC LIMIT 1", run_id)
            if prior is None or json.loads(prior["payload"])["note"] != current_gate.note:
                tx.event(run_id, "reveal_held", note=current_gate.note)

    # ---- 사용자 행동 ---------------------------------------------------------------------------
    def cancel_run(self, run_id: str) -> None:
        """되돌리지 않는 실행 취소. 먼저 저장하고 신호를 보낸다. 다시 눌러도 예산/사건을 중복 변경하지 않는다.

        대기 CLI·수동 제출은 시작 없이 거절한다. 진행 중인 시도는 종료 결과가 올 때까지 자리를 유지한다.
        기존 초안은 계속 봉인한다. 외부 앱 작업 자체를 중단시키거나 이미 쓴 예산을 돌려받는 기능은 아니다.
        """
        with self.lock:
            with self.store.tx() as tx:
                current_gate = self._gate(run_id)
                if not current_gate.accepting and current_gate.status != "cancelled":
                    raise ControllerError("only a drafting run can be cancelled; revealed drafts cannot be hidden again")
                if current_gate.accepting:
                    tx.execute("UPDATE runs SET cancel_requested = 1 WHERE run_id = ? AND NOT cancel_requested",
                               run_id)
                    for part in self.store.rows("SELECT * FROM participants WHERE run_id = ? AND state IN (?, ?)",
                                                run_id, QUEUED, AWAITING_USER):
                        self._transition(tx, part, REJECTED, status="cancelled_before_start")
                    tx.event(run_id, "run_cancel_requested")
            for part in self.store.rows("SELECT attempt FROM participants WHERE run_id = ? AND state = ?", run_id, RUNNING):
                worker = self._workers.get(part["attempt"])
                if worker:
                    worker[1].set()
        # 실행을 닫는 사람의 동작이다. 진행 중인 실행을 기다리던 교차검토 차례를 깨운다(Codex 교차검토, PR #144)
        self.pump()

    def submit_manual(self, run_id: str, pid: str, text: str, input_sha256: str, *,
                      user_confirmed: bool = False) -> None:
        """원본 앱의 답을 받는다. user_confirmed: 사용자가 "이 질문을 원본 앱에 넣어 받은 답"이라고 확인했다 —
        따로 남길 뿐 독립성 확인으로 올리지 않는다(K21, 2절 18)."""
        with self.lock:
            reason = None
            with self.store.tx() as tx:
                run, part = self._run(run_id), self._part(run_id, pid)
                spec = ParticipantSpec(**json.loads(part["spec"]))
                echo, body = _marker_echo(text, run_id, pid, run["input_sha256"])
                if spec.transport != MANUAL:
                    reason = "not a manual participant"
                elif not self._gate(run_id).accepting:
                    reason = "late: drafts were already revealed or the run ended"
                elif part["state"] != AWAITING_USER:
                    reason = "duplicate: this participant already has a result"
                elif input_sha256 != run["input_sha256"]:
                    reason = "different input: the answer was made for another question"
                elif echo == "other_run":
                    reason = "different run: the answer carries the marker of another run"
                elif echo == "other_participant":
                    reason = "different participant: the answer carries the marker of another participant"
                elif not body.strip():
                    reason = "empty answer"
                elif not storable(body):
                    reason = "the answer contains text that is not valid Unicode"
                result = {"source": MANUAL, "marker_echo": echo, "user_confirmed": bool(user_confirmed),
                          "independence": "unverified"}
                if reason is None and not self._transition(tx, part, ACCEPTED, status="manual", result=json.dumps(result)):
                    reason = "duplicate: this participant already has a result"
                if reason:
                    tx.event(run_id, "manual_refused", pid=pid, reason=reason)
                else:
                    tx.execute("INSERT INTO drafts VALUES (?, ?, ?, ?, ?, ?)", run_id, pid, body,
                               hashlib.sha256(body.encode("utf-8")).hexdigest(), MANUAL, time.time())
                    tx.event(run_id, "draft_sealed", pid=pid, source=MANUAL, marker_echo=echo,
                             user_confirmed=bool(user_confirmed))
                    self._maybe_reveal(run_id, tx)
            if reason:
                raise ControllerError(reason)
        # 실행을 닫는 사람의 동작이다. 진행 중인 실행을 기다리던 교차검토 차례를 깨운다(Codex 교차검토, PR #144)
        self.pump()

    def withdraw_manual(self, run_id: str, pid: str) -> None:
        """사용자가 원본 앱에서 답을 받지 못했다. 그 참여자를 빼고, 빈자리는 채우지 않는다."""
        with self.lock, self.store.tx() as tx:
            part = self._part(run_id, pid)
            if not self._gate(run_id).accepting or part["state"] != AWAITING_USER:
                raise ControllerError("only a participant waiting for the user can be withdrawn")
            if self._transition(tx, part, REJECTED, status="withdrawn"):
                tx.event(run_id, "manual_withdrawn", pid=pid)
                self._maybe_reveal(run_id, tx)
        # 실행을 닫는 사람의 동작이다. 진행 중인 실행을 기다리던 교차검토 차례를 깨운다(Codex 교차검토, PR #144)
        self.pump()

    def approve_reduction(self, run_id: str) -> None:
        """축소 승인은 controller가 그것을 기다릴 때만 받는다: 초안 작성 중이고, 모두 끝났고, 빠진 사람이 있고,
        아직 승인하지 않았다. 그 뒤로는 구성이 바뀌지 않으므로 승인은 지금 구성에 대한 것이다(A1-06)."""
        with self.lock, self.store.tx() as tx:
            current_gate = self._gate(run_id)
            if not current_gate.can_approve_reduction:
                raise ControllerError("no reduction is waiting for approval")
            tx.execute("UPDATE runs SET reduction_approved = 1 WHERE run_id = ? AND NOT reduction_approved", run_id)
            tx.event(run_id, "reduction_approved", requested=list(current_gate.requested), dropped=list(current_gate.dropped))
            self._maybe_reveal(run_id, tx)
        # 실행을 닫는 사람의 동작이다. 진행 중인 실행을 기다리던 교차검토 차례를 깨운다(Codex 교차검토, PR #144)
        self.pump()

    def acknowledge_unknown(self, run_id: str, pid: str) -> None:
        """사용자가 그 시도의 종료를 직접 확인했다고 알린다. 자리는 풀지만 예산은 돌려주지 않고, 초안도 받지 않는다."""
        with self.lock, self.store.tx() as tx:
            part = self._part(run_id, pid)
            if part["state"] != UNKNOWN:
                raise ControllerError("only an unknown attempt can be acknowledged")
            if self._transition(tx, part, REJECTED, status="unknown_acknowledged"):
                tx.event(run_id, "unknown_acknowledged", pid=pid)
                self._maybe_reveal(run_id, tx)
        self.pump()

    # ---- 다시 시작 ------------------------------------------------------------------------------
    def _recover(self) -> None:
        """이 원장을 연 controller는 이것 하나다(Store의 잠금). running으로 남은 시도는 멈춘 controller의 것이고
        종료를 확인할 수 없으므로 unknown으로 두고 다시 부르지 않는다. 그다음 초안 작성 중인 실행마다 공개 관문을
        다시 본다 — 이 수정 전의 원장은 마지막 초안 저장과 공개 사이에서 멈췄을 수 있다(A1-05). 외부 호출은 없다."""
        for row in self.store.rows("SELECT * FROM participants WHERE state = ?", RUNNING):
            with self.store.tx() as tx:
                if self._transition(tx, row, UNKNOWN, status="controller_restarted",
                                    detail="controller restarted; termination not confirmed"):
                    tx.event(row["run_id"], "attempt_unknown", pid=row["pid"], detail="controller restarted")
        for seat in SEATS:   # 상위 모델 호출도 같다: 종료를 확인할 수 없으니 종료 미확인, 다시 부르지 않는다
            for row in self.store.rows(f"SELECT * FROM {seat.table} WHERE state = ?", RUNNING):
                where = {key: row[key] for key in seat.keys}
                with self.store.tx() as tx:
                    if tx.execute(f"UPDATE {seat.table} SET state = ?, status = 'controller_restarted' WHERE "
                                  f"{seat.match} AND state = ? AND attempt = ?", UNKNOWN, *where.values(), RUNNING,
                                  row["attempt"]):
                        tx.event(row[seat.event_column], seat.done[UNKNOWN], **seat.label(where), attempt=row["attempt"],
                                 detail="controller restarted")
        for run in self.store.rows("SELECT run_id FROM runs WHERE phase = ?", m.DRAFTING):
            with self.store.tx() as tx:
                self._maybe_reveal(run["run_id"], tx)

    def synthesize(self, run_id: str) -> None:
        """One offline post-reveal transition. Persist once; failure keeps the draft report."""
        with self.lock, self.store.tx() as tx:
            self._check_role_synthesizer(run_id)
            if not self._gate(run_id).public()["can_synthesize"]:
                raise ControllerError("mock synthesis requires controller-revealed drafts")
            if self.store.row("SELECT 1 FROM events WHERE run_id = ? AND kind = 'synthesis_completed'", run_id):
                return
            report = build_report(self.view(run_id), run_id)
            try:
                result = mock_synthesize(report)
            except SynthesisError:
                result = unavailable(report)
            tx.event(run_id, "synthesis_completed", result=result)

    def synthesize_with_model(self, run_id: str, adapter_id: str, spec: ParticipantSpec | None = None) -> None:
        """공개 뒤 사용자가 켠 실제 합성 한 번(P5, K18). 같은 실행에 여러 번 할 수 있다 — 부를 때마다 호출 하나다.

        합성자는 그 실행의 CLI 참여자 provider이거나, 서버가 넘긴 설정된 CLI provider(spec)다. 참여자와 같은 계획·
        같은 격리로 부른다. 같은 초안에 합성자를 바꿔 붙일 수 있어야 합성자 계열의 영향(L1)을 볼 수 있다(사용자 결정
        2026-09-25, 인계 2절 23). 같은 원장의 전체·provider 상한 안에서 매번 예약하고, 예약과 시작 사건을 한 거래로
        쓴 뒤 백그라운드로 돈다. 시작 전 거절(공개 전·진행 중·종료 미확인 합성이 남음·설정되지 않은 provider·계획
        거절·상한 소진)은 아무것도 예약하지 않는다. 이름표 순서는 실행마다 하나라서 같은 실행의 합성은 같은 D1·D2를 본다.
        """
        with self.lock:
            fixed = self._check_role_synthesizer(run_id, adapter_id)
            if fixed is not None:
                spec = ParticipantSpec(**fixed)
            if self._closing:
                raise ControllerError("controller is shutting down")
            if not self._gate(run_id).public()["can_synthesize"]:
                raise ControllerError("model synthesis requires controller-revealed drafts")
            if run_id in self._synthesis:
                raise ControllerError("a model synthesis is already running for this run")
            if any(item["status"] == UNKNOWN for item in self._synthesis_attempts(run_id).values()):
                # 끝났는지 모르는 합성이 남아 있으면 새로 부르지 않는다. 사용자가 종료를 확인하면 다시 부를 수 있다.
                raise ControllerError("an earlier synthesis attempt has unconfirmed termination; acknowledge it first; "
                                      "no new call was started")
            if self.paused or self.unsettled() >= self.unsettled_limit:
                raise ControllerError("execution is paused or has unsettled attempts; no call was started")
            if self._slots_used() >= self.max_parallel:
                raise ControllerError("parallel execution limit reached; no call was started")
            chosen = next((spec for spec in (ParticipantSpec(**json.loads(row["spec"])) for row in self.store.rows(
                "SELECT spec FROM participants WHERE run_id = ? ORDER BY rowid", run_id))
                if spec.transport == CLI and spec.adapter_id == adapter_id), None)
            if chosen is None and spec is not None and spec.transport == CLI and spec.adapter_id == adapter_id:
                chosen = spec   # 이 실행의 참여자가 아니어도 서버에 설정된 CLI provider면 합성자가 될 수 있다
            if chosen is None or adapter_id not in self.executor.adapter_ids:
                raise ControllerError("the synthesizer must be a configured CLI provider")
            report = build_report(self.view(run_id), run_id)
            try:
                prompt, labels, nonce = model_prompt(report)
                prompt += self._run_memory(self._run(run_id))
            except SynthesisError as exc:
                raise ControllerError(str(exc)) from None
            attempt = uuid.uuid4().hex
            work = os.path.join(self.work_root, run_id, f"synthesis-{attempt[:12]}")
            try:
                # 폴더 준비 실패도 계획 거절처럼 요청 거절로 돌려준다 — 파일 시스템 예외를 API 밖으로 흘리지 않는다(AH-02).
                os.makedirs(work, exist_ok=True)
                source = self._source_dir(run_id)
                plan = self.executor.plan(replace(chosen, pid="synthesis", label="합성"), prompt, work,
                                          **({"inputs": (source,)} if source else {}))
                _check(self.executor, plan)   # 예약 전에 격리 경로·연결을 본다(R4)
            except ControllerError:
                raise
            except Exception as exc:  # 계획 거절: 아무것도 시작하지 않았다
                raise ControllerError(f"synthesis plan refused: {type(exc).__name__}: {exc}") from None
            with self.store.tx() as tx:
                if plan.kind == contract.REAL and self.max_real_calls is not None:
                    if self._budget_exhausted(adapter_id):
                        raise ControllerError("real CLI call budget exhausted; no call was started")
                    tx.event(run_id, "live_call_reserved", pid="synthesis", attempt=attempt, adapter_id=adapter_id,
                             cap=self.max_real_calls, purpose="synthesis")
                tx.event(run_id, "synthesis_started", attempt=attempt, adapter_id=adapter_id, execution=plan.kind,
                         labels=labels, label_order=LABEL_ORDER, boundary=nonce, spec=plan.record())
            cancel = threading.Event()
            thread = threading.Thread(target=self._synthesis_attempt,
                                      args=(run_id, attempt, plan, report, labels, cancel), daemon=True)
            self._synthesis[run_id] = (thread, cancel, attempt)
            try:
                thread.start()
            except RuntimeError:
                self._synthesis.pop(run_id)
                with self.store.tx() as tx:
                    tx.event(run_id, "synthesis_failed", attempt=attempt, result=model_unavailable(
                        report, {"adapter_id": adapter_id, "started": False}, "worker thread did not start"))

    def _synthesis_attempt(self, run_id: str, attempt: str, plan: contract.Plan, report: dict,
                           labels: dict[str, str], cancel: threading.Event) -> None:
        try:
            try:
                result, outcome = self.executor.run(plan, self.timeout, cancel=cancel)
            except Exception:  # 실행기 자체 실패: 자손 종료는 확인하지 못했다
                result, outcome = None, None
            state, status, why = acceptance(result, outcome)
            synthesizer = {"adapter_id": plan.spec.adapter_id, "requested_model": plan.model, "execution": plan.kind,
                           "started": result is None or result.state != runner.FAILED_TO_START,
                           "state": state, "status": status, "revision": plan.revision,
                           "reported_models": list(outcome.reported_models) if outcome else [],
                           "model_match": outcome.model_match if outcome else None,
                           "duration_ms": result.duration_ms if result else None,
                           "tree_confirmed_empty": result.tree_confirmed_empty if result else None,
                           "usage": outcome.usage if outcome else {},
                           "rate_limit": outcome.rate_limit if outcome else None}
            if state == ACCEPTED:
                try:
                    record = check_model_synthesis(outcome.text, report, labels, synthesizer)
                except SynthesisError as exc:   # 공개 뒤의 답이다 — 원인을 볼 수 있게 원문을 이유와 함께 남긴다
                    record = model_unavailable(report, synthesizer, str(exc), raw=outcome.text)
            else:
                record = model_unavailable(report, synthesizer, why or status)
            if not storable(json.dumps(record, ensure_ascii=False)):
                # 초안의 진단 메타데이터와 같은 규칙(AH-04): 고립 surrogate는 \uXXXX 표기로 바꿔 저장하고 바꿨다고 남긴다.
                # 합성은 봉인하는 원문이 아니고, 대조를 통과한 인용은 저장할 수 있는 초안에서 온 것이라 바뀌지 않는다.
                record = {**_storable_meta(record), "escaped_text": True}
            try:
                with self.lock, self.store.tx() as tx:
                    tx.event(run_id, "synthesis_completed" if record["status"] == "completed" else "synthesis_failed",
                             attempt=attempt, result=record)
            except Exception as exc:
                # 결과를 원장에 남기지 못했다. 결과 없는 시작으로 남아 종료 미확인·자리 유지다(초안의 카드 #70과 같다).
                with self.lock, self.store.tx() as tx:
                    tx.event(run_id, "synthesis_result_not_stored", attempt=attempt, error=type(exc).__name__)
        finally:
            with self.lock:
                self._synthesis.pop(run_id, None)
                self.pump()

    # ---- 다듬기(카드 #130) ---------------------------------------------------------------------
    def _select_memory(self, task_id, question, enabled):
        if task_id is not None and (not isinstance(task_id, str) or not self.store.row(
                "SELECT 1 FROM tasks WHERE task_id = ?", task_id)):
            raise ControllerError("작업을 찾을 수 없습니다.")
        try:
            with self.lock:
                return memory.select(self.store, task_id, question, enabled=enabled)
        except ValueError as exc:
            raise ControllerError(str(exc)) from None

    def _run_memory(self, run):
        try:
            return memory.footer(json.loads(run["role_config"] or "{}").get("memory"))
        except ValueError as exc:
            raise ControllerError(str(exc)) from None

    def refine(self, supervisor: ParticipantSpec, original: str | None = None, *, refine_id: str | None = None,
               note: str = "", task_id=None, use_memory=True) -> str:
        """슈퍼바이저 차례 한 번 — 호출 1회. refine_id가 없으면 original로 새 다듬기를 연다. 있으면 그 다듬기의 다음 차례다.

        격리 팀원·합성과 같은 계획·격리로 부르고, 같은 원장의 전체·provider 상한에서 예약한다(환불 없음). 차례는
        다듬기 하나에 refine.MAX_TURNS까지다. 실행에 이미 쓴 다듬기, 앞 차례가 진행 중이거나 종료 미확인인 다듬기,
        진행 중·종료 미확인 실행이 있을 때는 부르지 않는다. 원문·대화와 처음 고정한 선택적 작업 기억을 받는다.
        시작 전 거절은 아무것도 예약하지 않는다. 결과는 백그라운드에서 refine_turns에 조건부로 쓴다."""
        if not isinstance(note, str) or len(note.strip()) > refining.MAX_NOTE or not storable(note):
            raise ControllerError(f"슈퍼바이저에게 쓰는 말은 {refining.MAX_NOTE}자까지의 올바른 글이어야 합니다.")
        note = note.strip()
        with self.lock:
            if self._closing:
                raise ControllerError("controller is shutting down")
            self._cli_card(supervisor, "슈퍼바이저")
            if refine_id is None:
                original = original.strip() if isinstance(original, str) else ""
                if not original or len(original) > refining.MAX_ORIGINAL or not storable(original):
                    raise ControllerError(f"다듬을 원문은 1~{refining.MAX_ORIGINAL}자의 올바른 글이어야 합니다.")
                if note:
                    raise ControllerError("첫 차례에는 원문만 보냅니다. 답은 슈퍼바이저가 물은 뒤에 적습니다.")
                previous = []
                remembered = self._select_memory(task_id, original, use_memory)
            else:
                row = self.store.row("SELECT * FROM refinements WHERE refine_id = ?", refine_id)
                if row is None:
                    raise ControllerError("다듬기를 찾을 수 없습니다.")
                if row["run_id"]:
                    raise ControllerError("이미 실행에 쓴 다듬기입니다. 새로 다듬으세요.")
                fixed = json.loads(row["supervisor"])
                if (fixed["pid"], fixed["adapter_id"], fixed["model"]) != (supervisor.pid, supervisor.adapter_id,
                                                                           supervisor.model):
                    raise ControllerError("다듬기를 시작한 슈퍼바이저·모델과 다릅니다. 바꾸려면 새로 다듬으세요.")
                turns = self.store.rows("SELECT * FROM refine_turns WHERE refine_id = ? ORDER BY turn", refine_id)
                if any(turn["state"] in (RUNNING, UNKNOWN) for turn in turns):
                    raise ControllerError("앞 차례가 끝나지 않았거나 종료를 확인하지 못했습니다. 먼저 정리하세요.")
                if len(turns) >= refining.MAX_TURNS:
                    raise ControllerError(f"다듬기는 {refining.MAX_TURNS}차례까지입니다. 한 차례를 승인하거나 원문으로 돌아가세요.")
                original = row["original"]
                previous = [(turn["note"], json.loads(turn["result"])["reply"] if turn["state"] == ACCEPTED else None)
                            for turn in turns]
                snapshot = self.store.row("SELECT payload FROM events WHERE run_id = ? AND kind = 'memory_selected'",
                                          refine_id)
                remembered = json.loads(snapshot["payload"])["memory"] if snapshot else None
            self._upper_call_gate("다듬기는")
            key = refine_id or f"q{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"
            turn = len(previous) + 1
            text = refining.prompt(original, previous, note) + memory.footer(remembered)

            def insert(tx, attempt, kind):
                if refine_id is None:
                    tx.event(key, "memory_selected", memory=remembered)
                    tx.execute("INSERT INTO refinements (refine_id, created_at, original, supervisor) VALUES (?, ?, ?, ?)",
                               key, time.time(), original, json.dumps(asdict(supervisor), ensure_ascii=False))
                tx.execute("INSERT INTO refine_turns (refine_id, turn, note, prompt, input_sha256, attempt, kind, state) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", key, turn, note, text,
                           hashlib.sha256(text.encode("utf-8")).hexdigest(), attempt, kind, RUNNING)

            self._start_seat(REFINE_SEAT, key, {"refine_id": key, "turn": turn}, supervisor, text,
                             os.path.join(self.work_root, "_refine", key, f"turn-{turn}"), insert)
            return key

    def _start_seat(self, seat: "_Seat", event_key: str, where: dict, supervisor: ParticipantSpec, text: str,
                    work: str, insert, inputs: tuple[str, ...] = ()) -> None:
        """상위 모델 호출 하나를 시작한다 — 다듬기 차례·다음 단계 제안·분담 제안·결과 모으기가 같이 쓴다. 계획을 한 번 만들고, 같은
        거래에서 상한을 보고 예약하고 행을 넣은 뒤(insert), 그 계획을 백그라운드로 돌린다. 시작 전 거절은 아무것도 예약하지
        않는다. inputs는 읽기 전용 자료 폴더(분담 제안만 준다). 호출하는 쪽이 self.lock을 쥐고 이미 관문(한 번에 하나·
        자리·종료 미확인)을 봤다."""
        attempt = uuid.uuid4().hex
        try:
            os.makedirs(work, exist_ok=True)
            plan = self.executor.plan(replace(supervisor, pid=seat.plan_pid, label=seat.plan_label), text, work,
                                      **({"inputs": inputs} if inputs else {}))
            _check(self.executor, plan)   # 예약 전에 격리 경로·연결을 본다(R4)
        except Exception as exc:   # 계획 거절: 아무것도 시작하지 않았다
            raise ControllerError(f"supervisor plan refused: {type(exc).__name__}: {exc}") from None
        with self.store.tx() as tx:
            if plan.kind == contract.REAL and self.max_real_calls is not None:
                if self._budget_exhausted(supervisor.adapter_id):
                    raise _CapReached("real CLI call budget exhausted; no call was started")
                tx.event(event_key, "live_call_reserved", pid=seat.plan_pid, attempt=attempt,
                         adapter_id=supervisor.adapter_id, cap=self.max_real_calls, purpose=seat.purpose)
            insert(tx, attempt, plan.kind)
            tx.event(event_key, seat.started, **seat.label(where), attempt=attempt, adapter_id=supervisor.adapter_id,
                     execution=plan.kind, spec=plan.record())
        cancel = threading.Event()
        thread = threading.Thread(target=self._seat_attempt, args=(seat, event_key, where, attempt, plan, cancel),
                                  daemon=True)
        self._supervising[attempt] = (thread, cancel)
        try:
            thread.start()
        except RuntimeError:
            self._supervising.pop(attempt)
            self._settle_seat(seat, event_key, where, attempt, *_not_started(supervisor, "worker thread did not start"))

    def _seat_attempt(self, seat: "_Seat", event_key: str, where: dict, attempt: str, plan: contract.Plan,
                      cancel: threading.Event) -> None:
        try:
            try:
                result, outcome = self.executor.run(plan, self.timeout, cancel=cancel)
            except Exception:   # 실행기 자체 실패: 자손 종료는 확인하지 못했다
                result, outcome = None, None
            try:
                self._settle_seat(seat, event_key, where, attempt, result, outcome)
            except Exception as exc:   # 결과를 저장하지 못했다 — 진행 중으로 남기지 않는다(카드 #70과 같다)
                state = REJECTED if result is not None and result.tree_confirmed_empty is True else UNKNOWN
                with self.lock, self.store.tx() as tx:
                    if tx.execute(f"UPDATE {seat.table} SET state = ?, status = 'result_not_stored' WHERE "
                                  f"{seat.match} AND state = ? AND attempt = ?", state, *where.values(), RUNNING, attempt):
                        tx.event(event_key, seat.not_stored, **seat.label(where), attempt=attempt,
                                 error=type(exc).__name__)
        finally:
            with self.lock:
                self._supervising.pop(attempt, None)
                self.pump()

    def _settle_seat(self, seat: "_Seat", event_key: str, where: dict, attempt: str, result, outcome) -> None:
        """슈퍼바이저 답의 결과 관문. 참여자와 같은 수용 관문(acceptance)을 지난 뒤 형식 검사(seat.check)를 한다. 형식에
        실패한 답은 원문을 이유와 함께 남기고 쓸 수 없다. 이 호출이 아직 진행 중일 때만 반영하고, 늦은 결과는 사건으로만
        남긴다."""
        state, status, why = acceptance(result, outcome)
        observation = None if result is None else _storable_meta({
            "state": result.state, "containment": result.containment, "tree_confirmed_empty": result.tree_confirmed_empty,
            "input_delivery": result.input_delivery, "duration_ms": result.duration_ms, "status": outcome.status,
            "requested_model": outcome.requested_model, "reported_models": list(outcome.reported_models),
            "model_match": outcome.model_match, "usage": outcome.usage})
        record = {"observation": observation}
        if state == ACCEPTED:
            try:
                row = self.store.row(f"SELECT * FROM {seat.table} WHERE {seat.match}", *where.values())
                record["reply"] = seat.check(outcome.text, row)
            # RefineError·NextStepError·SplitError. 검사가 뜻밖의 모양에 걸려 다른 예외를 내도 답 원문과 이유를 남긴다 —
            # 결과 저장 실패로 빠져 증거를 잃지 않는다(Codex 교차검토, PR #136)
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                state, status = REJECTED, "format_error"
                reason = str(exc) if isinstance(exc, ValueError) else f"{type(exc).__name__}: {exc}"
                record.update(reason=reason[:300], raw=refining.rejected_reply(outcome.text))
        else:
            record["reason"] = _storable_meta(why or status)
        with self.lock, self.store.tx() as tx:
            if tx.execute(f"UPDATE {seat.table} SET state = ?, status = ?, result = ? WHERE {seat.match} "
                          "AND state = ? AND attempt = ?", state, status, json.dumps(record, ensure_ascii=False),
                          *where.values(), RUNNING, attempt):
                tx.event(event_key, seat.done[state], **seat.label(where), attempt=attempt, status=status)
            else:
                tx.event(event_key, seat.ignored, **seat.label(where), attempt=attempt)

    def _acknowledge_seat(self, seat: "_Seat", event_key: str, where: dict) -> None:
        """사람이 그 호출의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않으며 답을 받지 않는다."""
        with self.lock, self.store.tx() as tx:
            if not tx.execute(f"UPDATE {seat.table} SET state = ?, status = 'unknown_acknowledged' WHERE {seat.match} "
                              "AND state = ?", REJECTED, *where.values(), UNKNOWN):
                raise ControllerError("only an attempt with unconfirmed termination can be acknowledged")
            tx.event(event_key, seat.acknowledged, **seat.label(where))
        self.pump()

    def acknowledge_refine_unknown(self, refine_id: str, turn: int) -> None:
        """사람이 그 차례의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않으며 답을 받지 않는다."""
        if type(turn) is not int:
            raise ControllerError("turn must be an integer")
        self._acknowledge_seat(REFINE_SEAT, refine_id, {"refine_id": refine_id, "turn": turn})

    def _supervisor_busy(self) -> bool:
        """상위 모델 호출은 다듬기·제안·분담·모으기를 통틀어 한 번에 하나다. 버튼을 두 번 누르거나 창 두 개에서 불러도
        둘째를 시작하지 않는다(Codex 교차검토, PR #131). 종료 미확인도 아직 돌고 있을 수 있으므로 사람이 종료를 확인할
        때까지 다른 실행·다른 창의 상위 모델 호출까지 막는다(Codex 교차검토, PR #139)."""
        return self._seat_count(RUNNING, UNKNOWN) > 0

    def _upper_call_gate(self, what: str) -> None:
        """상위 모델 호출(다듬기·제안·분담·모으기·검토)의 공통 관문. 호출하는 쪽이 self.lock을 쥔다. 한 번에 하나 →
        멈춤·종료 미확인 → 자리 → 진행 중인 실행 순으로 본다. 여기서 거절하면 아무것도 예약하지 않았다. what은 거절
        문구의 주어("다듬기는" 처럼 조사까지)다."""
        if self._supervisor_busy():
            raise ControllerError("다른 상위 모델 호출(다듬기·제안·분담·모으기·검토)이 진행 중이거나 끝났는지 모릅니다. "
                                  "끝나거나 종료를 확인한 뒤에 다시 부르세요.")
        if self.paused or self.unsettled() >= self.unsettled_limit:
            raise ControllerError("execution is paused or has unsettled attempts; no call was started")
        if self._slots_used() >= self.max_parallel:
            raise ControllerError("parallel execution limit reached; no call was started")
        if self.store.row("SELECT 1 FROM runs WHERE phase = 'drafting' AND NOT cancel_requested"):
            raise ControllerError(f"진행 중인 실행을 먼저 정리하세요. {what} 실행이 없을 때만 부릅니다.")

    def _cli_card(self, spec: ParticipantSpec, who: str) -> None:
        """상위 칸(슈퍼바이저·오케스트레이터)의 카드는 이 실행기가 받는 CLI 카드여야 한다."""
        if spec.transport != CLI or spec.adapter_id not in self.executor.adapter_ids:
            raise ControllerError(f"{who}는 설정된 CLI 카드여야 합니다.")

    # ---- 다음 단계 제안(카드 #133) --------------------------------------------------------------
    def propose_next(self, run_id: str) -> str:
        """공개된 격리 실행을 보고 슈퍼바이저가 다음 단계("한 번 더"·"여기서 끝")를 제안한다 — 호출 1회.

        슈퍼바이저는 역할판에 고정한 카드·모델이다. 받는 것은 원래 목표(다듬기 원문 또는 질문)·보낸 질문·공개된 답이고,
        답은 합성과 같은 이름표(실행마다 섞은 순서)로 바꾼다. 봉인 중·일반 실행·슈퍼바이저 없는 실행은 부르지 않는다.
        실행 하나에 next_step.MAX_PER_RUN번까지, 슈퍼바이저 호출은 한 번에 하나, 예약·상한·종료 미확인은 다듬기와 같다.
        제안은 새 실행을 시작하지 않는다."""
        with self.lock:
            if self._closing:
                raise ControllerError("controller is shutting down")
            run = self._run(run_id)
            roles = json.loads(run["role_config"]) if run["role_config"] else {}
            supervisor = roles.get("supervisor")
            if not supervisor:
                raise ControllerError("슈퍼바이저 칸이 비어 있습니다(나). 다음 단계는 내가 정합니다.")
            current_gate = self._gate(run_id)
            if current_gate.general or not current_gate.revealed:
                raise ControllerError("다음 단계 제안은 공개된 격리 실행에만 부릅니다. 봉인 중에는 부르지 않습니다.")
            if self.store.row("SELECT COUNT(*) AS n FROM proposals WHERE run_id = ?", run_id)["n"] >= next_step.MAX_PER_RUN:
                raise ControllerError(f"다음 단계 제안은 실행 하나에 {next_step.MAX_PER_RUN}번까지입니다.")
            if self.store.row("SELECT 1 FROM proposals WHERE run_id = ? AND state = ?", run_id, UNKNOWN):
                raise ControllerError("끝났는지 모르는 제안이 있습니다. 종료를 먼저 확인하세요.")
            self._upper_call_gate("제안은")
            spec = ParticipantSpec(**supervisor)
            self._cli_card(spec, "슈퍼바이저")
            report = build_report(self.view(run_id), run_id)
            sources = synthesis_sources(report)
            labels = {f"D{index}": pid for index, pid in enumerate(label_order(run_id, sources), 1)}
            refined = self.store.row("SELECT original FROM refinements WHERE run_id = ?", run_id)
            text = next_step.prompt(refined["original"] if refined else run["question"], run["question"],
                                    [(label, sources[pid]["draft"]) for label, pid in labels.items()])
            text += self._run_memory(run)
            key = f"p{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"

            def insert(tx, attempt, kind):
                tx.execute("INSERT INTO proposals (proposal_id, run_id, created_at, supervisor, prompt, input_sha256, "
                           "labels, attempt, kind, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", key, run_id, time.time(),
                           json.dumps(supervisor, ensure_ascii=False), text,
                           hashlib.sha256(text.encode("utf-8")).hexdigest(), json.dumps(labels), attempt, kind, RUNNING)

            self._start_seat(NEXT_SEAT, run_id, {"proposal_id": key}, spec, text,
                             os.path.join(self.work_root, run_id, f"proposal-{key[-12:]}"), insert)
            return key

    def acknowledge_proposal_unknown(self, proposal_id: str) -> None:
        """사람이 그 제안 호출의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않는다."""
        row = self.store.row("SELECT run_id FROM proposals WHERE proposal_id = ?", proposal_id)
        if row is None:
            raise ControllerError("제안을 찾을 수 없습니다.")
        self._acknowledge_seat(NEXT_SEAT, row["run_id"], {"proposal_id": proposal_id})

    def _proposal_view(self, row) -> dict[str, Any]:
        return {"proposal_id": row["proposal_id"], "run_id": row["run_id"], "created_at": row["created_at"],
                "state": row["state"], "status": row["status"], "execution": row["kind"], "used_by": row["used_by"],
                "supervisor": _card(json.loads(row["supervisor"])),
                "labels": json.loads(row["labels"]), "prompt": row["prompt"], "input_sha256": row["input_sha256"],
                **_seat_result(row)}

    def _approved_proposal(self, proposal, roles, question: str, task_id) -> dict[str, Any]:
        """제안에서 온 새 실행. "한 번 더"인 통과한 제안이고, 실행에 쓰지 않았고, 같은 작업이고, 원문 모드이며, 질문이
        제안한 질문과 글자까지 같아야 한다. 고쳐 쓴 질문은 내 질문이다 — 화면이 제안을 붙이지 않는다."""
        if not isinstance(proposal, dict) or set(proposal) != {"id"} or not isinstance(proposal["id"], str):
            raise ControllerError("제안은 {id}로 줍니다.")
        row = self.store.row("SELECT * FROM proposals WHERE proposal_id = ?", proposal["id"])
        if row is None:
            raise ControllerError("제안을 찾을 수 없습니다.")
        if row["used_by"]:
            raise ControllerError("이미 실행에 쓴 제안입니다. 같은 제안으로 실행을 두 번 만들지 않습니다.")
        reply = (json.loads(row["result"]) if row["result"] else {}).get("reply")
        if row["state"] != ACCEPTED or not reply or reply["next"] != "again":
            raise ControllerError("형식 검사를 통과한 '한 번 더' 제안만 새 실행이 됩니다.")
        if roles["input_mode"] != "original":
            raise ControllerError("제안한 질문은 원문 모드로 보냅니다. 다듬으려면 제안을 붙이지 말고 새로 다듬으세요.")
        if task_id != self._run(row["run_id"])["task_id"]:
            raise ControllerError("제안은 그 제안이 나온 작업의 새 실행에만 씁니다.")
        if question != reply["question"]:
            raise ControllerError("보낼 질문이 제안한 질문과 다릅니다. 고쳐 쓴 질문은 제안 없이 보내세요.")
        return {"proposal_id": row["proposal_id"], "source_run": row["run_id"], "question": reply["question"]}

    # ---- 분담 제안(카드 #135) ------------------------------------------------------------------
    def propose_split(self, goal: str, orchestrator: ParticipantSpec, members: list[ParticipantSpec], sources=None,
                      task_id=None, use_memory=True) -> str:
        """일반 팀원 작업의 오케스트레이터 모델이 팀원마다 맡길 일과 받을 자료를 제안한다 — 호출 1회.

        오케스트레이터는 전체 목표·팀원 목록·붙인 자료 전부(읽기 전용 사본 폴더 하나)를 받는다. 제안은 실행을 시작하지
        않는다 — 화면이 팀원별 칸을 채우고, 사람이 고치거나 그대로 두고 확인해 시작하면 그때 그 실행 하나에 묶인다.
        다듬기·다음 단계 제안과 같은 관문(한 번에 하나·예약·상한·종료 미확인·재시작)을 지난다."""
        goal = goal.strip() if isinstance(goal, str) else ""
        if not goal or len(goal) > refining.MAX_ORIGINAL or not storable(goal):
            raise ControllerError(f"전체 목표는 1~{refining.MAX_ORIGINAL}자의 올바른 글이어야 합니다.")
        checked_sources = _checked_sources(sources)
        if (not members or len({p.pid for p in members}) != len(members) or any(p.transport != CLI for p in members)
                or len({p.provider for p in members}) != len(members)):
            raise ControllerError("팀원은 서로 다른 provider의 CLI 카드여야 합니다.")
        with self.lock:
            if self._closing:
                raise ControllerError("controller is shutting down")
            self._cli_card(orchestrator, "오케스트레이터")
            if task_id is not None and not self.store.row("SELECT 1 FROM tasks WHERE task_id = ?", task_id):
                raise ControllerError("작업을 찾을 수 없습니다.")
            self._upper_call_gate("분담 제안은")
            key = f"s{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"
            labels = {f"M{index}": p.pid for index, p in enumerate(members, 1)}
            rows = [{"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "content": data}
                    for name, data in checked_sources]
            listed = [{key_: row[key_] for key_ in ("name", "bytes", "sha256")} for row in rows]
            folder = None
            if rows:
                try:
                    folder = self._snapshot(self._source_root(key), rows)
                except OSError as exc:
                    raise ControllerError(f"could not prepare the source folder: {type(exc).__name__}") from None
            text = splitting.prompt(goal, {label: next(p.label for p in members if p.pid == pid)
                                           for label, pid in labels.items()}, listed, folder)
            remembered = self._select_memory(task_id, goal, use_memory)
            text += memory.footer(remembered)

            def insert(tx, attempt, kind):
                for row in rows:
                    tx.execute("INSERT INTO sources (run_id, name, sha256, bytes, content) VALUES (?, ?, ?, ?, ?)",
                               key, row["name"], row["sha256"], row["bytes"], row["content"])
                tx.event(key, "memory_selected", memory=remembered)
                tx.execute("INSERT INTO splits (split_id, task_id, created_at, goal, orchestrator, members, sources, "
                           "prompt, input_sha256, attempt, kind, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           key, task_id, time.time(), goal, json.dumps(asdict(orchestrator), ensure_ascii=False),
                           json.dumps(labels), json.dumps(listed), text,
                           hashlib.sha256(text.encode("utf-8")).hexdigest(), attempt, kind, RUNNING)

            self._start_seat(SPLIT_SEAT, key, {"split_id": key}, orchestrator, text,
                             os.path.join(self.work_root, "_split", key), insert, inputs=(folder,) if folder else ())
            return key

    # ---- 결과 모으기(카드 #137) ----------------------------------------------------------------
    def collate(self, run_id: str) -> str:
        """모두 끝난 일반 실행의 팀원 결과를 역할판의 오케스트레이터 모델이 원문 인용으로 취합한다 — 호출 1회.

        오케스트레이터는 전체 목표와 팀원마다 맡긴 일·결과 원문(이름표 T1·T2, 결과가 없으면 "결과 없음")을 받는다. 자료
        원문은 주지 않는다. 인용은 이 호출이 받은 원문과 글자 그대로 대조하고, 사실 검증은 하지 않는다. 실행 하나에
        collate.MAX_PER_RUN번까지, 다른 상위 모델 호출과 같은 관문(한 번에 하나·예약·상한·종료 미확인·재시작)을 지난다.
        판단 완료는 사람이 한다."""
        with self.lock:
            if self._closing:
                raise ControllerError("controller is shutting down")
            run = self._run(run_id)
            roles = json.loads(run["role_config"]) if run["role_config"] else {}
            orchestrator = roles.get("orchestrator")
            current_gate = self._gate(run_id)
            if not current_gate.general or not current_gate.collected:
                raise ControllerError("결과 모으기는 모두 끝난 일반 팀원 작업에만 부릅니다.")
            if not orchestrator:
                raise ControllerError("오케스트레이터 칸이 비어 있습니다(나). 결과는 내가 모읍니다.")
            if self.store.row("SELECT COUNT(*) AS n FROM collations WHERE run_id = ?", run_id)["n"] >= collating.MAX_PER_RUN:
                raise ControllerError(f"결과 모으기는 실행 하나에 {collating.MAX_PER_RUN}번까지입니다.")
            if self.store.row("SELECT 1 FROM collations WHERE run_id = ? AND state = ?", run_id, UNKNOWN):
                raise ControllerError("끝났는지 모르는 결과 모으기가 있습니다. 종료를 먼저 확인하세요.")
            self._upper_call_gate("결과 모으기는")
            spec = ParticipantSpec(**orchestrator)
            self._cli_card(spec, "오케스트레이터")
            members, labels, drafts = [], {}, {}
            for index, part in enumerate(self.store.rows(
                    "SELECT pid, spec, state FROM participants WHERE run_id = ? ORDER BY rowid", run_id), 1):
                label, member = f"T{index}", ParticipantSpec(**json.loads(part["spec"]))
                work = self._assignment(run_id, member.pid)
                draft = self.store.row("SELECT text FROM drafts WHERE run_id = ? AND pid = ?", run_id, member.pid)
                text = draft["text"] if draft and part["state"] == ACCEPTED else None
                labels[label], drafts[label] = member.pid, text
                members.append({"label": label, "name": member.label, "task": work["task"], "text": text})
            text = collating.prompt(run["question"], members)
            text += self._run_memory(run)
            key = f"c{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"

            def insert(tx, attempt, kind):
                tx.execute("INSERT INTO collations (collation_id, run_id, created_at, orchestrator, labels, drafts, prompt, "
                           "input_sha256, attempt, kind, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", key, run_id,
                           time.time(), json.dumps(orchestrator, ensure_ascii=False), json.dumps(labels),
                           json.dumps(drafts, ensure_ascii=False), text, hashlib.sha256(text.encode("utf-8")).hexdigest(),
                           attempt, kind, RUNNING)

            self._start_seat(COLLATE_SEAT, run_id, {"collation_id": key}, spec, text,
                             os.path.join(self.work_root, run_id, f"collation-{key[-12:]}"), insert)
            return key

    def acknowledge_collation_unknown(self, collation_id: str) -> None:
        """사람이 그 결과 모으기 호출의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않는다."""
        row = self.store.row("SELECT run_id FROM collations WHERE collation_id = ?", collation_id)
        if row is None:
            raise ControllerError("결과 모으기를 찾을 수 없습니다.")
        self._acknowledge_seat(COLLATE_SEAT, row["run_id"], {"collation_id": collation_id})

    def _collation_view(self, row) -> dict[str, Any]:
        return {"collation_id": row["collation_id"], "run_id": row["run_id"], "created_at": row["created_at"],
                "state": row["state"], "status": row["status"], "execution": row["kind"],
                "orchestrator": _card(json.loads(row["orchestrator"])),
                "labels": json.loads(row["labels"]), "prompt": row["prompt"], "input_sha256": row["input_sha256"],
                **_seat_result(row)}

    # ---- 공개 뒤 한 라운드 교차검토(카드 #140) ----------------------------------------------------
    def cross_review(self, run_id: str, question: str | None = None) -> list[str]:
        """공개된 격리 실행에서 교차검토 한 라운드를 연다 — 받은 답을 낸 CLI 팀원 한 명 = 호출 1회.

        검토자는 답을 낸 그 카드·모델이다(같은 관측된 계획, 읽기 전용). 자기 답(따로 표시)과 다른 팀원의 답(이름표,
        검토자마다 섞은 순서)과 검토 질문을 받는다. 원본 앱 팀원의 답은 대상으로만 들어간다. 입력은 여기서 모두 고정하고,
        검토자는 다른 상위 모델 호출처럼 한 번에 하나씩 차례로 부른다(pump). 앞 검토자가 받지 못하면(실패·종료
        미확인·상한·시작 못 함) 남은 검토자는 시작하지 않는다. 실행 하나에 한 라운드. 공개 뒤 다른 답을 본 검토라
        독립 정족수에 세지 않는다. 검토는 새 실행을 시작하지 않고, 지적의 처분은 사람이 한다."""
        question = question.strip() if isinstance(question, str) else ""
        question = question or cross.DEFAULT_QUESTION
        if len(question) > cross.MAX_QUESTION or not storable(question):
            raise ControllerError(f"검토 질문은 {cross.MAX_QUESTION}자까지의 올바른 글이어야 합니다.")
        with self.lock:
            if self._closing:
                raise ControllerError("controller is shutting down")
            run = self._run(run_id)
            current_gate = self._gate(run_id)
            if current_gate.general or not current_gate.revealed:
                raise ControllerError("교차검토는 공개된 격리 실행에만 부릅니다. 봉인 중에는 부르지 않습니다.")
            if self.store.row("SELECT 1 FROM reviews WHERE run_id = ?", run_id):
                raise ControllerError("교차검토는 실행 하나에 한 라운드입니다.")
            self._upper_call_gate("교차검토는")
            answers = {}   # pid → (명세, 답 원문, sha256). 받은 답만, 참여자 순서대로
            for part in self.store.rows("SELECT pid, spec, state FROM participants WHERE run_id = ? ORDER BY rowid",
                                        run_id):
                draft = self.store.row("SELECT text, sha256 FROM drafts WHERE run_id = ? AND pid = ?", run_id, part["pid"])
                if part["state"] == ACCEPTED and draft:
                    answers[part["pid"]] = (ParticipantSpec(**json.loads(part["spec"])), draft["text"], draft["sha256"])
            reviewers = [pid for pid, (spec, _, _) in answers.items()
                         if spec.transport == CLI and spec.adapter_id in self.executor.adapter_ids]
            if len(answers) < 2 or not reviewers:
                raise ControllerError("교차검토에는 받은 답이 둘 이상이고, 그중 설정된 CLI 팀원이 하나 이상 있어야 합니다.")
            first = answers[reviewers[0]][0]
            if (self.executor.kind == contract.REAL and self.max_real_calls is not None
                    and self._budget_exhausted(first.adapter_id)):
                raise ControllerError("real CLI call budget exhausted; no call was started")
            keys, now = [], time.time()
            with self.store.tx() as tx:
                for seq, pid in enumerate(reviewers, 1):
                    spec, own, _ = answers[pid]
                    others = [other for other in answers if other != pid]
                    labels = {f"D{index}": other for index, other in
                              enumerate(label_order(f"{run_id}\0review\0{pid}", others), 1)}
                    targets = {label: {"pid": other, "sha256": answers[other][2], "text": answers[other][1]}
                               for label, other in labels.items()}
                    text = cross.prompt(question, run["question"], own,
                                        [(label, item["text"]) for label, item in targets.items()])
                    key = f"v{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"
                    tx.execute("INSERT INTO reviews (review_id, run_id, seq, created_at, question, reviewer, labels, "
                               "targets, prompt, input_sha256, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               key, run_id, seq, now, question, json.dumps(asdict(spec), ensure_ascii=False),
                               json.dumps(labels), json.dumps(targets, ensure_ascii=False), text,
                               hashlib.sha256(text.encode("utf-8")).hexdigest(), QUEUED)
                    keys.append(key)
                tx.event(run_id, "review_round_created", reviewers=reviewers, calls=len(reviewers),
                         default_question=question == cross.DEFAULT_QUESTION)
            self._advance_reviews(start=True)
            return keys

    def _advance_reviews(self, *, start: bool) -> None:
        """교차검토 라운드를 한 걸음 진행한다. pump가 lock 안에서 부른다. 앞 검토자가 받지 못했으면(실패·종료 미확인·
        상한·시작 못 함) 남은 검토자를 시작하지 않고 그 이유로 닫는다 — 닫는 것은 관문과 상관없이 한다. start이면 관문
        (한 번에 하나·자리·진행 중인 실행 없음)이 허락할 때 다음 검토자 하나를 시작한다. 한 번에 하나만 부른다."""
        for item in self.store.rows("SELECT run_id FROM reviews WHERE state = ? GROUP BY run_id "
                                    "ORDER BY MIN(created_at)", QUEUED):
            run_id = item["run_id"]
            rows = self.store.rows("SELECT * FROM reviews WHERE run_id = ? ORDER BY seq", run_id)
            if any(row["state"] == RUNNING for row in rows):
                continue
            done = [row for row in rows if row["state"] != QUEUED]
            if done and done[-1]["state"] != ACCEPTED:
                self._close_reviews(run_id, "earlier_reviewer_not_accepted")
                continue
            if not start or self._supervisor_busy() or self._slots_used() >= self.max_parallel or self.store.row(
                    "SELECT 1 FROM runs WHERE phase = 'drafting' AND NOT cancel_requested"):
                continue
            row = next(row for row in rows if row["state"] == QUEUED)
            spec = ParticipantSpec(**json.loads(row["reviewer"]))

            def insert(tx, attempt, kind, review_id=row["review_id"]):
                if not tx.execute("UPDATE reviews SET state = ?, attempt = ?, kind = ? WHERE review_id = ? AND state = ?",
                                  RUNNING, attempt, kind, review_id, QUEUED):
                    raise ControllerError("this reviewer was already started")

            try:
                self._start_seat(REVIEW_SEAT, run_id, {"review_id": row["review_id"]}, spec, row["prompt"],
                                 os.path.join(self.work_root, run_id, f"review-{row['review_id'][-12:]}"), insert)
            except _CapReached:
                self._close_reviews(run_id, "cap_reached")
            except ControllerError as exc:   # 계획 거절 등: 이 검토자부터 시작하지 않았다
                self._close_reviews(run_id, _storable_meta(f"not_started: {exc}")[:300])
            return

    def _close_reviews(self, run_id: str, reason: str) -> None:
        """남은(대기 중인) 검토자를 시작하지 않은 채 닫는다. 검토하지 않은 관계로 보이고 호출은 쓰지 않았다."""
        with self.store.tx() as tx:
            closed = tx.execute("UPDATE reviews SET state = 'skipped', status = ? WHERE run_id = ? AND state = ?",
                                reason, run_id, QUEUED)
            if closed:
                tx.event(run_id, "review_skipped", reviewers=closed, reason=reason)

    def acknowledge_review_unknown(self, review_id: str) -> None:
        """사람이 그 검토 호출의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않는다."""
        row = self.store.row("SELECT run_id FROM reviews WHERE review_id = ?", review_id)
        if row is None:
            raise ControllerError("교차검토를 찾을 수 없습니다.")
        self._acknowledge_seat(REVIEW_SEAT, row["run_id"], {"review_id": review_id})

    def set_review_disposition(self, review_id: str, finding: int, disposition: str) -> None:
        """사람이 지적 하나의 처분을 고른다(qualified 받아들임·rejected 아님·unresolved 보류). 결과 판을 올리지 않는다 —
        사람의 판단이지 새 결과가 아니다. 모델이 동의해도 supported로 올리는 길은 없다(외부 검사 없음)."""
        if type(finding) is not int or disposition not in cross.DISPOSITIONS:
            raise ControllerError(f"처분은 {', '.join(cross.DISPOSITIONS)} 중 하나이고 지적 번호는 정수입니다.")
        with self.lock, self.store.tx() as tx:
            row = self.store.row("SELECT run_id, state, result FROM reviews WHERE review_id = ?", review_id)
            if row is None or row["state"] != ACCEPTED:
                raise ControllerError("받은 교차검토의 지적에만 처분을 고릅니다.")
            findings = json.loads(row["result"])["reply"]["findings"]
            if not 0 <= finding < len(findings):
                raise ControllerError("그런 지적이 없습니다.")
            tx.execute("INSERT INTO review_dispositions (review_id, finding, disposition, at) VALUES (?, ?, ?, ?) "
                       "ON CONFLICT (review_id, finding) DO UPDATE SET disposition = excluded.disposition, "
                       "at = excluded.at", review_id, finding, disposition, time.time())
            tx.event(row["run_id"], "review_disposition", review_id=review_id, finding=finding, disposition=disposition)

    def _cross_review_view(self, run_id: str, drafts: dict) -> dict[str, Any] | None:
        """drafts: view가 이 실행에서 이미 읽은 받은 답(pid → 행). 대상 답이 지금 답과 같은 판인지(fresh)를 본다."""
        rows = self.store.rows("SELECT * FROM reviews WHERE run_id = ? ORDER BY seq", run_id)
        if not rows:
            return None
        current = {pid: draft["sha256"] for pid, draft in drafts.items()}
        reviews, missing, reviewed = [], [], 0
        for row in rows:
            record = json.loads(row["result"]) if row["result"] else {}
            spec, targets = json.loads(row["reviewer"]), json.loads(row["targets"])
            reply = record.get("reply")
            if reply:
                chosen = {item["finding"]: item for item in self.store.rows(
                    "SELECT finding, disposition, at FROM review_dispositions WHERE review_id = ?", row["review_id"])}
                reply = {**reply, "findings": [
                    {**finding, "target_pid": targets[finding["target"]]["pid"],
                     "disposition": chosen[index]["disposition"] if index in chosen else "unresolved",
                     "disposition_at": chosen[index]["at"] if index in chosen else None}
                    for index, finding in enumerate(reply["findings"])]}
            for label, target in targets.items():
                if row["state"] == ACCEPTED:
                    reviewed += 1
                else:
                    missing.append({"reviewer": spec["pid"], "target": target["pid"],
                                    "reason": row["status"] or row["state"]})
            reviews.append({"review_id": row["review_id"], "seq": row["seq"], "state": row["state"],
                            "status": row["status"], "execution": row["kind"],
                            "reviewer": _card(spec),
                            "labels": json.loads(row["labels"]),
                            "targets": {label: {"pid": t["pid"], "sha256": t["sha256"],
                                                "fresh": current.get(t["pid"]) == t["sha256"]}
                                        for label, t in targets.items()},
                            "prompt": row["prompt"], "input_sha256": row["input_sha256"], "reply": reply,
                            "reason": record.get("reason"), "raw": record.get("raw"),
                            "observation": record.get("observation")})
        return {"question": rows[0]["question"], "created_at": rows[0]["created_at"], "reviews": reviews,
                "coverage": {"pairs": reviewed + len(missing), "reviewed": reviewed, "missing": missing},
                "independence": "post_reveal_not_independent"}

    def acknowledge_split_unknown(self, split_id: str) -> None:
        """사람이 그 분담 제안 호출의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않는다."""
        self._acknowledge_seat(SPLIT_SEAT, split_id, {"split_id": split_id})

    def _split_view(self, row) -> dict[str, Any]:
        return {"split_id": row["split_id"], "task_id": row["task_id"], "created_at": row["created_at"],
                "goal": row["goal"], "state": row["state"], "status": row["status"], "execution": row["kind"],
                "orchestrator": _card(json.loads(row["orchestrator"])),
                "members": json.loads(row["members"]), "sources": json.loads(row["sources"]),
                "prompt": row["prompt"], "input_sha256": row["input_sha256"], "used_by": row["used_by"],
                "as_proposed": None if row["as_proposed"] is None else bool(row["as_proposed"]),
                **_seat_result(row)}

    def _approved_split(self, split, roles, question, participants, assignments, checked_sources, task_id):
        """분담 제안에서 온 일반 실행. 통과했고 실행에 쓰지 않은 제안이어야 하며, 목표·팀원·자료(이름·해시)·작업·역할판의
        오케스트레이터가 제안 때와 같아야 한다. 사람이 맡길 일이나 자료를 고쳤으면 as_proposed가 거짓이다 — 거절하지 않는다."""
        if not isinstance(split, dict) or set(split) != {"id"} or not isinstance(split["id"], str):
            raise ControllerError("분담 제안은 {id}로 줍니다.")
        row = self.store.row("SELECT * FROM splits WHERE split_id = ?", split["id"])
        if row is None:
            raise ControllerError("분담 제안을 찾을 수 없습니다.")
        if row["used_by"]:
            raise ControllerError("이미 실행에 쓴 분담 제안입니다. 같은 제안으로 실행을 두 번 만들지 않습니다.")
        reply = (json.loads(row["result"]) if row["result"] else {}).get("reply")
        if row["state"] != ACCEPTED or not reply:
            raise ControllerError("검사를 통과한 분담 제안만 씁니다.")
        fixed, board = json.loads(row["orchestrator"]), roles["orchestrator"] or {}
        if (fixed["pid"], fixed["adapter_id"], fixed["model"]) != (board.get("pid"), board.get("adapter_id"),
                                                                     board.get("model")):
            raise ControllerError("분담을 제안한 오케스트레이터·모델과 역할판의 오케스트레이터가 다릅니다.")
        if list(json.loads(row["members"]).values()) != [p.pid for p in participants]:
            raise ControllerError("분담 제안 때와 팀원이 다릅니다. 다시 제안받거나 제안 없이 나누세요.")
        listed = [(s["name"], s["sha256"]) for s in json.loads(row["sources"])]
        if listed != [(name, hashlib.sha256(data).hexdigest()) for name, data in checked_sources]:
            raise ControllerError("분담 제안 때와 자료가 다릅니다. 다시 제안받거나 제안 없이 나누세요.")
        if row["goal"] != question or row["task_id"] != task_id:
            raise ControllerError("분담 제안 때와 전체 목표나 작업이 다릅니다.")
        sent = {pid: {"task": item["task"].strip(), "sources": sorted(item["sources"])}
                for pid, item in assignments.items()}
        return {"split_id": row["split_id"], "as_proposed": sent == reply["assignments"]}

    def _refinement_view(self, row) -> dict[str, Any]:
        """다듬기 한 건의 화면 투영. 원문·차례별 보낸 입력·받은 답(또는 실패 이유와 원문)·사람이 쓴 말을 그대로 보인다."""
        turns = []
        for turn in self.store.rows("SELECT * FROM refine_turns WHERE refine_id = ? ORDER BY turn", row["refine_id"]):
            turns.append({"turn": turn["turn"], "note": turn["note"], "state": turn["state"], "status": turn["status"],
                          "execution": turn["kind"], "prompt": turn["prompt"], "input_sha256": turn["input_sha256"],
                          **_seat_result(turn)})
        return {"refine_id": row["refine_id"], "created_at": row["created_at"], "original": row["original"],
                "supervisor": _card(json.loads(row["supervisor"])),
                "run_id": row["run_id"], "approved_turn": row["approved_turn"], "max_turns": refining.MAX_TURNS,
                "turns": turns}

    def _approved_refinement(self, refinement, roles, question: str, task_id=None, use_memory=True) -> dict[str, Any]:
        """다듬기 모드 실행의 승인본을 확인한다. 실행에 쓰지 않은 다듬기의, 형식 검사를 통과한 차례의 문장이어야 하고,
        역할판의 슈퍼바이저와 같은 카드·모델이 만든 것이어야 한다. 보낼 질문은 그 문장과 글자까지 같아야 한다."""
        if not isinstance(refinement, dict) or set(refinement) != {"id", "turn"} or type(refinement["turn"]) is not int:
            raise ControllerError("다듬기 모드에는 승인할 다듬기와 차례({id, turn})가 필요합니다.")
        row = self.store.row("SELECT * FROM refinements WHERE refine_id = ?", refinement["id"])
        if row is None:
            raise ControllerError("다듬기를 찾을 수 없습니다.")
        if row["run_id"]:
            raise ControllerError("이미 다른 실행에 쓴 다듬기입니다. 같은 승인으로 실행을 두 번 만들지 않습니다.")
        snapshot = self.store.row("SELECT payload FROM events WHERE run_id = ? AND kind = 'memory_selected'",
                                  row["refine_id"])
        remembered = json.loads(snapshot["payload"])["memory"] if snapshot else None
        if remembered and remembered["entries"] and (remembered["task_id"] != task_id or not use_memory):
            raise ControllerError("다듬기에 쓴 작업 기억과 설정이 다릅니다. 이 작업에서 새로 다듬으세요.")
        fixed, board = json.loads(row["supervisor"]), roles["supervisor"]
        if (fixed["pid"], fixed["adapter_id"], fixed["model"]) != (board["pid"], board["adapter_id"], board["model"]):
            raise ControllerError("다듬기를 한 슈퍼바이저·모델과 역할판의 슈퍼바이저가 다릅니다.")
        turns = self.store.rows("SELECT * FROM refine_turns WHERE refine_id = ? ORDER BY turn", row["refine_id"])
        if any(turn["state"] in (RUNNING, UNKNOWN) for turn in turns):
            raise ControllerError("끝나지 않았거나 종료를 확인하지 못한 다듬기 차례가 있습니다. 먼저 정리하세요.")
        chosen = next((turn for turn in turns if turn["turn"] == refinement["turn"]), None)
        if chosen is None or chosen["state"] != ACCEPTED:
            raise ControllerError("형식 검사를 통과한 차례만 승인할 수 있습니다.")
        approved = json.loads(chosen["result"])["reply"]["refined"]
        if question != approved:
            raise ControllerError("보낼 질문이 승인한 다듬기 문장과 다릅니다. 승인한 문장을 그대로 보냅니다.")
        return {"refine_id": row["refine_id"], "turn": chosen["turn"], "original": row["original"],
                "approved": approved, "turns": len(turns)}

    # ---- 화면용 투영 ---------------------------------------------------------------------------
    def view(self, run_id: str | None = None) -> dict[str, Any]:
        """화면에 넘기는 것. 공개 전에는 제출 여부와 실행 상태의 고정된 필드만 넘긴다(BlindBarrier 계약).

        초안의 내용·길이·digest, 토큰 수, 걸린 시간은 공개 뒤에 넘긴다. CLI가 쓴 오류 설명과 runner 메모는 모든
        참여자가 끝난 뒤에 넘긴다 — 그 전에는 그것을 본 사람이 아직 답하는 참여자(원본 앱에 질문을 옮기는
        사용자 포함)에게 영향을 줄 수 있다(A1 리뷰 A1-01).
        """
        with self.lock:
            runs = []
            # 합성 이력은 요청 하나에서 한 번만 만들어 실행별·전역 투영이 나눠 쓴다(카드 #121, S6). 같은 lock 안이라
            # 요청 사이의 캐시가 아니다 — 매 요청 새로 읽는다
            every = self._synthesis_attempts()
            query = "SELECT * FROM runs" + (" WHERE run_id = ?" if run_id is not None else "")
            for run in self.store.rows(query + " ORDER BY created_at DESC", *(() if run_id is None else (run_id,))):
                rows = self.store.rows("SELECT * FROM participants WHERE run_id = ? ORDER BY rowid", run["run_id"])
                current_gate = gate(run, rows)
                general = current_gate.general
                # 일반 팀원은 봉인하지 않는다(요청서 P6): 답·진단·실행 정보를 끝나는 대로 보인다. 다른 실행의 봉인된
                # 답은 이 실행의 투영에 들어오지 않는다 — 행을 이 실행에서만 읽는다.
                revealed, settled = current_gate.revealed, current_gate.settled or current_gate.revealed or general
                keep = SEALED_VIEW_KEYS | (DIAGNOSTIC_KEYS if settled else frozenset())
                assigned = {row["pid"]: row for row in self.store.rows(
                    "SELECT * FROM assignments WHERE run_id = ?", run["run_id"])} if general else {}
                parts, calls = [], {"succeeded": 0, "failed": 0, "unknown": 0}
                # 받은 답은 실행마다 한 번에 읽는다(참여자마다 읽지 않는다, S6). 공개 뒤·일반 실행에만 싣는다
                drafts = {d["pid"]: d for d in self.store.rows(
                    "SELECT pid, source, sha256, text FROM drafts WHERE run_id = ?", run["run_id"])}                     if revealed or general else {}
                for p in rows:
                    spec = ParticipantSpec(**json.loads(p["spec"]))
                    result = json.loads(p["result"]) if p["result"] else None
                    if result and not (revealed or general):
                        result = {k: v for k, v in result.items() if k in keep}
                    if (spec.transport == CLI and p["state"] in (ACCEPTED, REJECTED, UNKNOWN)
                            and p["status"] not in NOT_STARTED):
                        calls[{"accepted": "succeeded", "rejected": "failed", "unknown": "unknown"}[p["state"]]] += 1
                    item = {"pid": spec.pid, "label": spec.label, "provider": spec.provider,
                            "transport": spec.transport, "behavior": spec.behavior if spec.transport == CLI else None,
                            "adapter_id": spec.adapter_id if spec.transport == CLI else None,
                            "state": p["state"], "status": p["status"], "detail": p["detail"] if settled else None,
                            "contamination": list(_flags(spec.transport, p)) +
                                (["개인 문맥 미확인 — 독립 정족수에 세지 않음"]
                                 if spec.transport == CLI and spec.context_unverified and not general else []),
                            "execution": p["kind"] if spec.transport == CLI else None,
                            # 일반 팀원의 답은 blind 초안이 아니다 — 독립 라벨을 붙이지 않는다
                            "independence": "not_applicable" if general else
                                ("confirmed" if confirmed(asdict(spec)) else "unverified"),
                            "result": result, "dropped": spec.pid in current_gate.dropped}
                    if general and spec.pid in assigned:
                        work = assigned[spec.pid]
                        item["assignment"] = {"task": work["task"], "prompt": work["prompt"],
                                              "input_sha256": work["input_sha256"], "input_bytes": work["input_bytes"],
                                              "sources": json.loads(work["sources"])}
                    if current_gate.accepting and spec.transport == MANUAL and p["state"] == AWAITING_USER:
                        item["packet"] = packet(run["run_id"], spec.pid, run["input_sha256"], run["prompt"])
                    if (revealed or general) and p["state"] == ACCEPTED:
                        draft = drafts.get(spec.pid)
                        item["draft"] = draft["text"] if draft else None
                        item["draft_sha256"] = draft["sha256"] if draft else None
                    parts.append(item)
                cli_total = sum(1 for p in parts if p["transport"] == CLI)
                quorum = None if general else dict(current_gate.quorum)   # 일반 실행은 정족수를 세지 않는다
                if quorum is not None:
                    quorum["label"] = _quorum_label(quorum) if revealed else None
                revision, reviewed, memo = self._review_state(run["run_id"])
                judged = revealed or current_gate.collected   # 사람이 판단할 결과 판이 있는가
                runs.append({"run_id": run["run_id"], "created_at": run["created_at"], "question": run["question"],
                             "task_id": run["task_id"], "role_config": json.loads(run["role_config"]),
                             "mode": run["mode"],
                             "reviewed": judged and reviewed,   # 지금 결과 판을 판단 완료했는가(AH-01)
                             "review_memo": memo if judged and reviewed else None,
                             "prompt": run["prompt"], "input_sha256": run["input_sha256"],
                             "input_bytes": run["input_bytes"], "sources": self.sources(run["run_id"]),
                             "phase": run["phase"],
                             "min_independent": run["min_independent"], "note": current_gate.note,
                             "quorum": quorum, "gate": current_gate.public(),
                             "reduction_approved": bool(run["reduction_approved"]),
                             "cancel_requested": bool(run["cancel_requested"]),
                             "diagnostics_sealed": not settled,
                             "budget": {"used": sum(calls.values()) + sum(1 for p in parts if p["state"] == RUNNING),
                                        "cap": cli_total, "breakdown": calls,
                                        "not_started": sum(1 for p in parts if p["transport"] == CLI
                                                           and p["status"] in NOT_STARTED),
                                        "reserved": (self.store.row("SELECT COUNT(*) AS n FROM events WHERE run_id = ? "
                                                                    "AND kind = 'live_call_reserved'", run["run_id"])["n"]
                                                     if any(p["execution"] == contract.REAL for p in parts) else 0),
                                        "manual": sum(1 for p in parts if p["transport"] == MANUAL)},
                             "participants": parts,
                             "events": [e["kind"] for e in reversed(self.store.rows(
                                 "SELECT kind FROM events WHERE run_id = ? ORDER BY seq DESC LIMIT 12", run["run_id"]))]})
                refined = self.store.row("SELECT * FROM refinements WHERE run_id = ?", run["run_id"])
                # 원래 목표(원문)와 실제로 보낸 질문을 나란히 보이려고 싣는다(P9). 다듬기는 실행 전의 일이라 봉인과 무관하다
                runs[-1]["refinement"] = self._refinement_view(refined) if refined else None
                came = self.store.row("SELECT proposal_id, run_id FROM proposals WHERE used_by = ?", run["run_id"])
                runs[-1]["proposal"] = {"proposal_id": came["proposal_id"], "source_run": came["run_id"]} if came else None
                divided = self.store.row("SELECT * FROM splits WHERE used_by = ?", run["run_id"])
                runs[-1]["split"] = self._split_view(divided) if divided else None   # 일반 실행의 분담 제안(#135)
                if judged:
                    runs[-1]["result_revision"] = revision   # 판단 완료 버튼이 이 판을 함께 보낸다. 공개·모음 뒤에만 싣는다
                if general and current_gate.collected:
                    # 결과 모으기는 모두 끝난 일반 실행의 일이다(#137). 그 전에는 부를 수도 없고 목록도 비어 있다
                    runs[-1]["collations"] = [self._collation_view(row) for row in self.store.rows(
                        "SELECT * FROM collations WHERE run_id = ? ORDER BY created_at", run["run_id"])]
                if revealed:
                    # 다음 단계 제안은 공개 뒤의 일이다. 봉인 중에는 부를 수도 없고 목록도 비어 있다
                    runs[-1]["proposals"] = [self._proposal_view(row) for row in self.store.rows(
                        "SELECT * FROM proposals WHERE run_id = ? ORDER BY created_at", run["run_id"])]
                    # 공개 뒤 교차검토 라운드(#140). 없으면 None
                    runs[-1]["cross_review"] = self._cross_review_view(run["run_id"], drafts)
                    artifact = self.store.row("SELECT payload FROM events WHERE run_id = ? "
                                              "AND kind = 'synthesis_completed' ORDER BY seq DESC LIMIT 1", run["run_id"])
                    if artifact:
                        runs[-1]["synthesis"] = json.loads(artifact["payload"])["result"]
                    mine = {key: item for key, item in every.items() if key[0] == run["run_id"]}
                    runs[-1]["model_synthesis"] = self._model_synthesis_state(run["run_id"], mine)
                    runs[-1]["model_syntheses"] = [
                        {"attempt": attempt, "status": item["status"], "result": item["result"] or None}
                        for (_, attempt), item in mine.items()]
                # 실행의 토큰 합계(카드 #141). 봉인 중에는 싣지 않는다 — 참여자가 볼 수 있는 채널로 새지 않게
                # (2026-09-24 검토 8번). 일반 실행은 봉인이 없어 처음부터 싣는다
                runs[-1]["usage"] = token_usage.for_run(runs[-1]) if revealed or general else None
            unsettled = self.unsettled(every)
            # 대기 시도를 controller가 지금 시작하지 않고, 사람이 무언가 해야 풀리는 이유(N3). pump()가 멈추는 두 조건에
            # 더해, 종료 미확인 시도가 병렬 자리를 모두 쥔 경우도 같다 — 진행 중인 시도가 끝나서 풀리는 자리가 아니다.
            unknown_slots = self._unknown_slots(every)
            held = "paused" if self.paused else ("unsettled" if unsettled >= self.unsettled_limit or (
                unknown_slots and unknown_slots >= self.max_parallel) else None)
            tasks = task_projection(self.store.rows("SELECT * FROM tasks ORDER BY created_at DESC"), runs, held=held)
            # 실행에 쓰지 않은 다듬기: 최근 것과, 끝나지 않았거나 종료 미확인인 차례가 있는 것(오래돼도 정리할 수 있게)
            open_rows = {row["refine_id"]: row for row in self.store.rows(
                "SELECT * FROM refinements WHERE run_id IS NULL ORDER BY created_at DESC LIMIT 20")}
            open_rows.update({row["refine_id"]: row for row in self.store.rows(
                "SELECT * FROM refinements WHERE run_id IS NULL AND refine_id IN "
                "(SELECT refine_id FROM refine_turns WHERE state IN (?, ?))", RUNNING, UNKNOWN)})
            refinements = sorted((self._refinement_view(row) for row in open_rows.values()),
                                 key=lambda item: item["created_at"], reverse=True)
            # 실행에 쓰지 않은 분담 제안도 같은 규칙: 최근 것과, 끝나지 않았거나 종료 미확인인 것
            open_splits = {row["split_id"]: row for row in self.store.rows(
                "SELECT * FROM splits WHERE used_by IS NULL ORDER BY created_at DESC LIMIT 20")}
            open_splits.update({row["split_id"]: row for row in self.store.rows(
                "SELECT * FROM splits WHERE used_by IS NULL AND state IN (?, ?)", RUNNING, UNKNOWN)})
            splits = sorted((self._split_view(row) for row in open_splits.values()),
                            key=lambda item: item["created_at"], reverse=True)
            return {"executor": self.executor.name, "live_call_budget": self.call_budget(), "tasks": tasks,
                    "refinements": refinements, "splits": splits,
                    "provider_call_budgets": {aid: self.call_budget(aid) for aid in self.provider_call_caps},
                    "slots": {"used": self._slots_used(every), "cap": self.max_parallel},
                    "unsettled": {"count": unsettled, "limit": self.unsettled_limit},
                    "paused": self.paused, "runs": runs}

    # ---- 내부 ---------------------------------------------------------------------------------
    def _check_role_synthesizer(self, run_id, adapter_id=None):
        roles = json.loads(self._run(run_id)["role_config"])
        if roles["source"] != "board":
            return None  # 이전 실행의 수동 합성 선택은 그대로 둔다.
        spec = roles["orchestrator"]
        if spec is None:
            raise ControllerError("오케스트레이터는 나입니다. 원문 대조표를 직접 판단하세요. 합성은 부르지 않습니다.")
        if adapter_id is not None and spec["adapter_id"] != adapter_id:
            raise ControllerError("시작할 때 고정한 오케스트레이터와 다릅니다. 바꾸려면 새 실행을 만드세요.")
        return spec

    def _review_state(self, run_id: str) -> tuple[int, bool, str | None]:
        """(결과 판, 그 판을 판단 완료했는가, 그때 남긴 취합 메모). 판은 사람이 보는 결과를 바꾼 마지막 사건의 seq다 —
        공개, 일반 실행의 모음, 합성 완료·실패, 다음 단계 제안·결과 모으기·교차검토의 결과. 판단 완료 사건이 그보다 뒤에 있어야 그 판을 본 것이다. 새 합성이 끝나면
        판이 올라가 다시 내 차례가 된다(AH-01). 판을 싣지 않은 옛 원장의 판단 완료 사건도 같은 순서 규칙으로 읽는다."""
        row = self.store.row(
            "SELECT COALESCE(MAX(CASE WHEN kind IN ('revealed', 'collected', 'synthesis_completed', 'synthesis_failed', "
            "'proposal_completed', 'proposal_failed', 'collation_completed', 'collation_failed', "
            "'review_completed', 'review_failed', 'review_skipped', "
            # 종료 미확인도 새 결과다 — 종료 확인이 판단을 대신하지 않게 판을 올린다(Codex 교차검토, PR #144)
            "'proposal_unknown', 'collation_unknown', 'review_unknown') "
            "THEN seq END), 0) AS revision, "
            "COALESCE(MAX(CASE WHEN kind = 'human_reviewed' THEN seq END), 0) AS reviewed "
            "FROM events WHERE run_id = ?", run_id)
        memo = None
        if row["reviewed"]:
            payload = self.store.row("SELECT payload FROM events WHERE run_id = ? AND seq = ?", run_id, row["reviewed"])
            memo = json.loads(payload["payload"]).get("memo")
        return row["revision"], row["reviewed"] > row["revision"], memo

    def mark_reviewed(self, run_id: str, revision: int, memo: str | None = None) -> None:
        """사람이 공개된 원문 초안과 그때까지의 합성 결과(실패 포함) — 일반 실행이면 팀원들의 결과 — 를 판단했다. 모델
        호출 없이 내 차례를 끝내며 재시작에도 남는다. revision은 화면이 보여 준 결과 판이다 — 그 사이 새 결과가 나왔으면
        거절한다. 같은 판을 두 번 누르면 사건은 하나다(두 번째 메모는 남기지 않는다). memo는 사람이 쓴 취합 메모이며
        검증이나 합의 판정이 아니다. 합성 실패 기록을 지우거나 품질 통과로 바꾸지 않는다."""
        if type(revision) is not int:
            raise ControllerError("revision must be the integer result revision shown on screen")
        if memo is not None and (not isinstance(memo, str) or len(memo) > MAX_MEMO_CHARS or not storable(memo)):
            raise ControllerError(f"취합 메모는 {MAX_MEMO_CHARS}자까지의 올바른 글이어야 합니다.")
        with self.lock, self.store.tx() as tx:
            current_gate = self._gate(run_id)
            if current_gate.general and not current_gate.collected:
                raise ControllerError("모든 팀원이 끝난 뒤에만 판단 완료로 표시할 수 있습니다. 종료 미확인은 먼저 확인하세요.")
            if not current_gate.general and not current_gate.revealed:
                raise ControllerError("공개된 답을 확인한 뒤에만 판단 완료로 표시할 수 있습니다.")
            if any(item["status"] in (RUNNING, UNKNOWN) for item in self._synthesis_attempts(run_id).values()):
                raise ControllerError("합성의 종료를 먼저 확인하세요.")
            if self.store.row("SELECT 1 FROM proposals WHERE run_id = ? AND state IN (?, ?)", run_id, RUNNING, UNKNOWN):
                raise ControllerError("다음 단계 제안이 끝나거나 그 종료를 확인한 뒤에 판단 완료를 누르세요.")
            if self.store.row("SELECT 1 FROM collations WHERE run_id = ? AND state IN (?, ?)", run_id, RUNNING, UNKNOWN):
                raise ControllerError("결과 모으기가 끝나거나 그 종료를 확인한 뒤에 판단 완료를 누르세요.")
            if self.store.row("SELECT 1 FROM reviews WHERE run_id = ? AND state IN (?, ?, ?)",
                              run_id, QUEUED, RUNNING, UNKNOWN):
                raise ControllerError("교차검토 라운드가 끝나거나 그 종료를 확인한 뒤에 판단 완료를 누르세요.")
            current, reviewed, _ = self._review_state(run_id)
            if revision != current:
                raise ControllerError("화면에 보인 뒤 새 결과가 나왔습니다. 새 결과를 확인하고 다시 판단 완료를 누르세요.")
            if not reviewed:
                note = (memo or "").strip()
                tx.event(run_id, "human_reviewed", revision=current, **({"memo": note} if note else {}))

    def _model_synthesis_state(self, run_id: str, attempts: dict | None = None) -> dict[str, Any] | None:
        """같은 사건 투영으로 진행·실패·종료 미확인을 보인다. 과거 미확인 시도도 숨기지 않는다. attempts: 이 실행의
        합성 이력(view가 요청마다 한 번 만든 것에서 잘라 넘긴다). 없으면 새로 읽는다."""
        attempts = self._synthesis_attempts(run_id) if attempts is None else attempts
        if not attempts:
            return None
        unknown = [attempt for (_, attempt), item in attempts.items() if item["status"] == UNKNOWN]
        if unknown:
            return {"status": UNKNOWN, "attempts": unknown,
                    "message": "합성 자손의 종료를 확인하지 못했습니다. 자리는 유지하며 재호출·환불하지 않습니다."}
        if run_id in self._synthesis:
            return {"status": RUNNING}
        latest = list(attempts.values())[-1]
        if latest["status"] == "completed":
            return {"status": "completed"}
        if latest["status"] == "acknowledged":
            return {"status": "acknowledged", "message": "사용자가 종료를 확인했습니다. 재호출·환불하지 않습니다."}
        result = latest["result"]
        state = {"status": "failed", "message": result.get("message"), "reason": result.get("reason"),
                 "synthesizer": result.get("synthesizer")}
        if result.get("raw"):   # 형식 검사에 실패한 원문. 옛 사건에는 이 칸이 없다
            state["raw"] = result["raw"]
        return state

    def acknowledge_synthesis_unknown(self, run_id: str, attempt: str) -> None:
        """사용자가 특정 합성 시도의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않는다."""
        with self.lock, self.store.tx() as tx:
            self._run(run_id)
            item = self._synthesis_attempts(run_id).get((run_id, attempt))
            if item is None or item["status"] != UNKNOWN:
                raise ControllerError("only an unknown synthesis attempt can be acknowledged")
            tx.event(run_id, "synthesis_unknown_acknowledged", attempt=attempt)
        self.pump()

    def _gate(self, run_id: str) -> RunGate:
        """Read inside a Store transaction for decisions that change state."""
        return gate(self._run(run_id), self.store.rows(
            "SELECT pid, state, spec FROM participants WHERE run_id = ? ORDER BY rowid", run_id))

    @staticmethod
    def _transition(tx, expected, state: str, **changes) -> bool:
        """One participant mutation path: both the old state and attempt must still match.

        NULL is a real expected attempt for manual/queued participants, not a wildcard.
        The caller writes the corresponding event/draft only when this succeeds.
        """
        allowed = {QUEUED: (RUNNING, REJECTED), RUNNING: (ACCEPTED, REJECTED, UNKNOWN),
                   AWAITING_USER: (ACCEPTED, REJECTED), UNKNOWN: (REJECTED,)}
        if state not in allowed.get(expected["state"], ()):
            raise ControllerError(f"invalid participant transition {expected['state']} -> {state}")
        if set(changes) - {"status", "detail", "result", "attempt", "kind"}:
            raise ControllerError("invalid participant transition fields")
        updates = {"state": state, **changes}
        assignments = ", ".join(f"{name} = ?" for name in updates)
        return bool(tx.execute(f"UPDATE participants SET {assignments} "
                               "WHERE run_id = ? AND pid = ? AND state = ? AND attempt IS ?",
                               *updates.values(), expected["run_id"], expected["pid"],
                               expected["state"], expected["attempt"]))

    def _run(self, run_id: str):
        run = self.store.row("SELECT * FROM runs WHERE run_id = ?", run_id)
        if run is None:
            raise ControllerError(f"no run {run_id!r}")
        return run

    def _part(self, run_id: str, pid: str):
        part = self.store.row("SELECT * FROM participants WHERE run_id = ? AND pid = ?", run_id, pid)
        if part is None:
            raise ControllerError(f"no participant {pid!r} in {run_id!r}")
        return part

    def shutdown(self, timeout: float = runner.CLEANUP_LIMIT + 1.0) -> bool:
        """새 호출을 영구히 막고 소유한 초안·합성 실행기에 취소를 알린 뒤 결과 저장을 기다린다.

        실행 자체의 cancel_run과 다르다. 대기 시도·이미 공개한 답·예약은 보존한다. 다시 연 controller는 대기를
        사용자 resume 전까지 시작하지 않는다. True는 worker가 모두 반환했다는 뜻이지 자손 종료의 증거가 아니다.
        종료 미확인은 원장과 unsettled()에 남는다. False이면 호출자는 살아 있는 writer의 Store를 닫지 않는다.
        """
        if not math.isfinite(timeout) or timeout < 0:
            raise ValueError("shutdown timeout must be finite and non-negative")
        with self.lock:
            self._closing, self.paused = True, True
            for _, cancel in self._workers.values():
                cancel.set()
            for _, cancel, _ in self._synthesis.values():
                cancel.set()
            for _, cancel in self._supervising.values():
                cancel.set()
        # _finish와 finally가 같은 lock을 필요로 하므로 기다리는 동안 잡고 있지 않는다.
        return self.wait_idle(timeout)

    def wait_idle(self, timeout: float = 30.0) -> bool:
        """시작한 시도가 모두 반환했는지 본다. timeout=0은 기다리지 않고 현재 상태만 검사한다."""
        if not math.isfinite(timeout) or timeout < 0:
            raise ValueError("idle timeout must be finite and non-negative")
        deadline = time.monotonic() + timeout
        while True:
            with self.lock:
                if not self._workers and not self._synthesis and not self._supervising:
                    return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(0.05, remaining))
