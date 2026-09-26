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
from app.roles import freeze as freeze_roles, task_projection
from app.report import build_report
from app.synthesis import (LABEL_ORDER, SynthesisError, check_model_synthesis, mock_synthesize, model_prompt,
                           model_unavailable, unavailable)
from app.state import (CLI, MANUAL, QUEUED, RUNNING, AWAITING_USER, ACCEPTED, REJECTED, UNKNOWN,
                       DONE, INDEPENDENT_ONLY, INCLUDE_UNVERIFIED, QUORUM_POLICIES, RunGate, gate, confirmed, synthesis_attempts)
from core import adapters, contract, env as core_env, isolation, membership as m, runner

# _source_dir가 원장의 질문 본문을 이 두 문구로 다시 만들어 맞춘다. 문구를 바꾸면 그 전에 만든 대기 실행은
# 재개 때 호출 없이 거절된다.
PROMPT = ("다음 질문에, 다른 참여자의 답을 보지 않은 상태로 독립적으로 답하라. "
          "결론, 근거, 그리고 결론을 뒤집을 조건을 쓴다.\n\n질문:\n{question}\n")
# 공통 자료(P0). 모든 참여자가 같은 질문 본문을 받으므로 목록·해시는 질문에 넣어 입력 digest에 묶는다.
PROMPT_SOURCES = ("\n참고 자료 {count}개가 읽기 전용 폴더 {folder}에 있다. 자료에서 가져온 내용은 파일 이름을 밝히고, "
                  "자료에 없는 판단은 자료 밖의 판단이라고 표시한다.\n{listing}\n")
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
    if part["state"] == QUEUED or part["status"] in ("cancelled_before_start", "process_failed_to_start"):
        return NOT_RUN
    return CONTAMINATION.get(part["kind"], UNRECORDED)

# 원본 앱에 옮기는 질문의 첫 줄과, 답에서 그것을 찾는 형식(N5)
MARKER = "[Ledger {run_id}/{pid} · {sha8}]"
MARKER_LINE = re.compile(r"^\s*\[Ledger ([^\s/]+)/(\S+) · ([0-9a-f]{8})\]\s*$")
PACKET = ("{marker}\n답의 첫 줄에 위 대괄호 줄을 그대로 옮겨 적어 주세요. 어느 실행의 답인지 확인하는 데만 씁니다.\n\n"
          "{prompt}")


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
    run()이 그 계획 그대로 실행한다. kind는 이 실행기가 만드는 시도의 종류, adapter_ids는 받는 CLI다."""
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
        planned = adapters.ExecutionSpec(spec.adapter_id, (python, self.SCRIPT, self.FLAVOR[spec.adapter_id],
                                                           spec.behavior),
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
        self._recover()
        # 이전 controller가 시작하지 못한 시도가 남아 있으면 사용자가 이어서 시작하라고 할 때까지 기다린다
        self.paused = self.store.row("SELECT COUNT(*) AS n FROM participants JOIN runs USING (run_id) "
                                     "WHERE state = ? AND NOT cancel_requested", QUEUED)["n"] > 0

    # ---- 만들기와 예약 -------------------------------------------------------------------------
    def prepare_run(self, question: str, participants: list[ParticipantSpec], *, min_independent: int,
                    quorum_policy: str = INDEPENDENT_ONLY, sources=None, task_id=None, task_title=None,
                    role_board=None, roster=None, run_id=None) -> dict[str, Any]:
        """sources: (이름, 글) 목록. 원장에 내용·해시를 고정하고, CLI 참여자에게는 그 사본 폴더 하나를 읽기
        전용 입력으로 준다(provider별 빈 입력 폴더 대신). 입력 폴더가 하나인 것은 같으므로 계획의 판은 그대로다."""
        question = question.strip()
        if not question:
            raise ControllerError("question is empty")
        if not storable(question):
            raise ControllerError("the question contains text that is not valid Unicode")
        checked_sources = _checked_sources(sources)
        if len({p.pid for p in participants}) != len(participants) or not participants:
            raise ControllerError("participants must be unique and non-empty")
        for p in participants:
            if p.transport not in (CLI, MANUAL) or (p.transport == CLI and p.adapter_id not in self.executor.adapter_ids):
                raise ControllerError(f"unsupported participant {p.pid!r}")
        try:
            roles = freeze_roles(role_board, participants, roster or {p.pid: p for p in participants})
        except ValueError as exc:
            raise ControllerError(str(exc)) from None
        if quorum_policy not in QUORUM_POLICIES:
            raise ControllerError(f"quorum_policy must be one of {', '.join(QUORUM_POLICIES)}")
        # 프런트엔드가 false를 보내도 실행기의 opt-in 등급을 올려 주지 않는다. 더 낮은 등급은 보존한다.
        if getattr(self.executor, "allow_context_unverified", False):
            participants = [replace(p, context_unverified=True) if p.transport == CLI else p for p in participants]
            roles["isolated"] = [asdict(p) for p in participants]
        confirmable = sum(confirmed(asdict(p)) for p in participants)
        if quorum_policy == INDEPENDENT_ONLY and min_independent > confirmable:
            raise ControllerError(f"only {confirmable} participant(s) can be confirmed independent (CLI); lower "
                                  "min_independent or choose include_unverified to count unverified answers")
        try:
            m.start(tuple(p.pid for p in participants), min_independent=min_independent)
        except m.MembershipError as exc:
            raise ControllerError(str(exc)) from None
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
        prompt = PROMPT.format(question=question)
        if checked_sources:
            prompt += _source_footer(self._source_root(run_id), [
                {"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for name, data in checked_sources])
        data = prompt.encode("utf-8")
        manifest = {"run_id": run_id, "task_id": task_id, "task_title": task_title.strip() if task_title else question[:120],
                    "question": question, "prompt": prompt, "input_sha256": hashlib.sha256(data).hexdigest(),
                    "input_bytes": len(data), "role_config": roles,
                    "min_independent": min_independent, "quorum_policy": quorum_policy,
                    "sources": [{"name": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
                                for name, content in checked_sources],
                    "calls": {"draft_cli": sum(p.transport == CLI for p in participants),
                              "model_calls": 0 if self.executor.kind != contract.REAL else None,
                              "live_cap": self.max_real_calls, "provider_caps": dict(self.provider_call_caps)},
                    "manual_packets": {p.pid: packet(run_id, p.pid, hashlib.sha256(data).hexdigest(), prompt)
                                       for p in participants if p.transport == MANUAL}}
        manifest["confirmation"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return manifest

    def create_run(self, question: str, participants: list[ParticipantSpec], *, min_independent: int,
                   quorum_policy: str = INDEPENDENT_ONLY, sources=None, task_id=None, task_title=None,
                   role_board=None, roster=None, run_id=None, confirmation=None) -> str:
        prepared = self.prepare_run(question, participants, min_independent=min_independent,
                                    quorum_policy=quorum_policy, sources=sources, task_id=task_id, task_title=task_title,
                                    role_board=role_board, roster=roster, run_id=run_id)
        if confirmation is not None and confirmation != prepared["confirmation"]:
            raise ControllerError("확인한 입력에서 바뀌었습니다. 보낼 입력을 다시 확인하세요.")
        run_id, question, prompt = prepared["run_id"], prepared["question"], prepared["prompt"]
        data = prompt.encode("utf-8")
        participants = [ParticipantSpec(**p) for p in prepared["role_config"]["isolated"]]
        checked_sources = _checked_sources(sources)
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
                       "min_independent, roster, quorum_policy, task_id, role_config) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       run_id, time.time(), question, prompt, hashlib.sha256(data).hexdigest(), len(data),
                       min_independent, "{}", quorum_policy, task_id, json.dumps(prepared["role_config"], ensure_ascii=False))
            for p in participants:
                tx.execute("INSERT INTO participants (run_id, pid, spec, state) VALUES (?, ?, ?, ?)", run_id, p.pid,
                           json.dumps(asdict(p), ensure_ascii=False), QUEUED if p.transport == CLI else AWAITING_USER)
            tx.event(run_id, "run_created", input_sha256=hashlib.sha256(data).hexdigest(), input_bytes=len(data),
                     participants=[p.pid for p in participants], min_independent=min_independent,
                     quorum_policy=quorum_policy,
                     sources=[{"name": name, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
                              for name, content in checked_sources])
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
        if not rows:
            return None
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

    def _slots_used(self) -> int:
        return sum(item["status"] in (RUNNING, UNKNOWN) for item in self._synthesis_attempts().values()) + self.store.row(
            "SELECT COUNT(*) AS n FROM participants WHERE state IN (?, ?)", RUNNING, UNKNOWN)["n"]

    def _budget_exhausted(self, adapter_id: str) -> bool:
        """전체·provider 상한. 거래 안에서 읽고 같은 거래에서 예약한다 — 병렬 요청이 마지막 한 칸을 함께 쓰지 못한다."""
        budget, provider = self.call_budget(), self.call_budget(adapter_id)
        return budget["used"] >= budget["cap"] or bool(self.provider_call_caps and (
            provider["cap"] is None or provider["used"] >= provider["cap"]))

    def unsettled(self) -> int:
        with self.lock:
            unknown = self.store.row("SELECT COUNT(*) AS n FROM participants WHERE state = ?", UNKNOWN)["n"]
            return unknown + sum(item["status"] == UNKNOWN for item in self._synthesis_attempts().values()) + runner.lingering()

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
                                         "'attempt_rejected', 'synthesis_completed', 'synthesis_failed') "
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
            if self._closing or self.paused or self.unsettled() >= self.unsettled_limit:
                return
            queued = self.store.rows("SELECT p.run_id, p.pid, p.spec FROM participants p JOIN runs r USING (run_id) "
                                     "WHERE p.state = ? AND NOT r.cancel_requested ORDER BY r.created_at, p.rowid", QUEUED)
            for row in queued:
                if self._slots_used() >= self.max_parallel:
                    return
                spec = ParticipantSpec(**json.loads(row["spec"]))
                attempt = uuid.uuid4().hex
                work = os.path.join(self.work_root, row["run_id"], spec.pid)
                os.makedirs(work, exist_ok=True)
                prompt = self._run(row["run_id"])["prompt"]
                # 최종 계획을 한 번 만든다. 그 기록(질문 본문 없이)과 실행 종류를 시도 ID와 함께 저장한 뒤에만 같은
                # 계획을 실행한다(G4·G6). 저장하지 못하면 실행하지 않는다.
                try:
                    # 자료가 있는 실행은 그 사본 폴더 하나를 입력으로 준다. 목록·해시가 다르면 여기서 거절된다.
                    source = self._source_dir(row["run_id"])
                    extra = {"inputs": (source,)} if source else {}
                    plan, refused = self.executor.plan(spec, prompt, work, **extra), None
                    if plan.context_unverified and not spec.context_unverified:
                        raise ControllerError("queued participant has a different context policy; create a new run")
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
                    tx.event(run_id, "draft_sealed", pid=pid, attempt=attempt, result=summary)
                else:
                    tx.event(run_id, "attempt_rejected", pid=pid, attempt=attempt, status=status, result=summary)
                self._maybe_reveal(run_id, tx)

    def _maybe_reveal(self, run_id: str, tx) -> None:
        """남은 참여자가 모두 끝났고 정족수가 있으면 연다. 빠진 사람이 있으면 축소 승인이 먼저다.

        상태를 바꾼 거래 안에서 부른다. 거래 안의 읽기는 그 거래가 쓴 것까지 본다.
        """
        current_gate = self._gate(run_id)
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

    def withdraw_manual(self, run_id: str, pid: str) -> None:
        """사용자가 원본 앱에서 답을 받지 못했다. 그 참여자를 빼고, 빈자리는 채우지 않는다."""
        with self.lock, self.store.tx() as tx:
            part = self._part(run_id, pid)
            if not self._gate(run_id).accepting or part["state"] != AWAITING_USER:
                raise ControllerError("only a participant waiting for the user can be withdrawn")
            if self._transition(tx, part, REJECTED, status="withdrawn"):
                tx.event(run_id, "manual_withdrawn", pid=pid)
                self._maybe_reveal(run_id, tx)

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
                prompt, labels = model_prompt(report)
            except SynthesisError as exc:
                raise ControllerError(str(exc)) from None
            attempt = uuid.uuid4().hex
            work = os.path.join(self.work_root, run_id, f"synthesis-{attempt[:12]}")
            os.makedirs(work, exist_ok=True)
            source = self._source_dir(run_id)
            try:
                plan = self.executor.plan(replace(chosen, pid="synthesis", label="합성"), prompt, work,
                                          **({"inputs": (source,)} if source else {}))
            except Exception as exc:  # 계획 거절: 아무것도 시작하지 않았다
                raise ControllerError(f"synthesis plan refused: {type(exc).__name__}: {exc}") from None
            with self.store.tx() as tx:
                if plan.kind == contract.REAL and self.max_real_calls is not None:
                    if self._budget_exhausted(adapter_id):
                        raise ControllerError("real CLI call budget exhausted; no call was started")
                    tx.event(run_id, "live_call_reserved", pid="synthesis", attempt=attempt, adapter_id=adapter_id,
                             cap=self.max_real_calls, purpose="synthesis")
                tx.event(run_id, "synthesis_started", attempt=attempt, adapter_id=adapter_id, execution=plan.kind,
                         labels=labels, label_order=LABEL_ORDER, spec=plan.record())
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
            with self.lock, self.store.tx() as tx:
                tx.event(run_id, "synthesis_completed" if record["status"] == "completed" else "synthesis_failed",
                         attempt=attempt, result=record)
        finally:
            with self.lock:
                self._synthesis.pop(run_id, None)
                self.pump()

    # ---- 화면용 투영 ---------------------------------------------------------------------------
    def view(self, run_id: str | None = None) -> dict[str, Any]:
        """화면에 넘기는 것. 공개 전에는 제출 여부와 실행 상태의 고정된 필드만 넘긴다(BlindBarrier 계약).

        초안의 내용·길이·digest, 토큰 수, 걸린 시간은 공개 뒤에 넘긴다. CLI가 쓴 오류 설명과 runner 메모는 모든
        참여자가 끝난 뒤에 넘긴다 — 그 전에는 그것을 본 사람이 아직 답하는 참여자(원본 앱에 질문을 옮기는
        사용자 포함)에게 영향을 줄 수 있다(A1 리뷰 A1-01).
        """
        with self.lock:
            runs = []
            query = "SELECT * FROM runs" + (" WHERE run_id = ?" if run_id is not None else "")
            for run in self.store.rows(query + " ORDER BY created_at DESC", *(() if run_id is None else (run_id,))):
                rows = self.store.rows("SELECT * FROM participants WHERE run_id = ? ORDER BY rowid", run["run_id"])
                current_gate = gate(run, rows)
                revealed, settled = current_gate.revealed, current_gate.settled or current_gate.revealed
                keep = SEALED_VIEW_KEYS | (DIAGNOSTIC_KEYS if settled else frozenset())
                parts, calls = [], {"succeeded": 0, "failed": 0, "unknown": 0}
                for p in rows:
                    spec = ParticipantSpec(**json.loads(p["spec"]))
                    result = json.loads(p["result"]) if p["result"] else None
                    if result and not revealed:
                        result = {k: v for k, v in result.items() if k in keep}
                    if (spec.transport == CLI and p["state"] in (ACCEPTED, REJECTED, UNKNOWN)
                            and p["status"] not in ("cancelled_before_start", "process_failed_to_start")):
                        calls[{"accepted": "succeeded", "rejected": "failed", "unknown": "unknown"}[p["state"]]] += 1
                    item = {"pid": spec.pid, "label": spec.label, "provider": spec.provider,
                            "transport": spec.transport, "behavior": spec.behavior if spec.transport == CLI else None,
                            "adapter_id": spec.adapter_id if spec.transport == CLI else None,
                            "state": p["state"], "status": p["status"], "detail": p["detail"] if settled else None,
                            "contamination": list(_flags(spec.transport, p)) +
                                (["개인 문맥 미확인 — 독립 정족수에 세지 않음"]
                                 if spec.transport == CLI and spec.context_unverified else []),
                            "execution": p["kind"] if spec.transport == CLI else None,
                            "independence": "confirmed" if confirmed(asdict(spec)) else "unverified",
                            "result": result, "dropped": spec.pid in current_gate.dropped}
                    if current_gate.accepting and spec.transport == MANUAL and p["state"] == AWAITING_USER:
                        item["packet"] = packet(run["run_id"], spec.pid, run["input_sha256"], run["prompt"])
                    if revealed and p["state"] == ACCEPTED:
                        draft = self.store.row("SELECT text, source, sha256 FROM drafts WHERE run_id = ? AND pid = ?",
                                               run["run_id"], spec.pid)
                        item["draft"] = draft["text"] if draft else None
                        item["draft_sha256"] = draft["sha256"] if draft else None
                    parts.append(item)
                cli_total = sum(1 for p in parts if p["transport"] == CLI)
                quorum = dict(current_gate.quorum)
                quorum["label"] = _quorum_label(quorum) if revealed else None
                runs.append({"run_id": run["run_id"], "created_at": run["created_at"], "question": run["question"],
                             "task_id": run["task_id"], "role_config": json.loads(run["role_config"]),
                             "reviewed": self.store.row("SELECT 1 FROM events WHERE run_id = ? AND kind = 'human_reviewed'",
                                                        run["run_id"]) is not None,
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
                                        "not_started": sum(1 for p in parts if p["transport"] == CLI and p["status"]
                                                           in ("cancelled_before_start", "process_failed_to_start")),
                                        "reserved": (self.store.row("SELECT COUNT(*) AS n FROM events WHERE run_id = ? "
                                                                    "AND kind = 'live_call_reserved'", run["run_id"])["n"]
                                                     if any(p["execution"] == contract.REAL for p in parts) else 0),
                                        "manual": sum(1 for p in parts if p["transport"] == MANUAL)},
                             "participants": parts,
                             "events": [e["kind"] for e in reversed(self.store.rows(
                                 "SELECT kind FROM events WHERE run_id = ? ORDER BY seq DESC LIMIT 12", run["run_id"]))]})
                if revealed:
                    artifact = self.store.row("SELECT payload FROM events WHERE run_id = ? "
                                              "AND kind = 'synthesis_completed' ORDER BY seq DESC LIMIT 1", run["run_id"])
                    if artifact:
                        runs[-1]["synthesis"] = json.loads(artifact["payload"])["result"]
                    runs[-1]["model_synthesis"] = self._model_synthesis_state(run["run_id"])
                    runs[-1]["model_syntheses"] = [
                        {"attempt": attempt, "status": item["status"], "result": item["result"] or None}
                        for (_, attempt), item in self._synthesis_attempts(run["run_id"]).items()]
            tasks = task_projection(self.store.rows("SELECT * FROM tasks ORDER BY created_at DESC"), runs)
            return {"executor": self.executor.name, "live_call_budget": self.call_budget(), "tasks": tasks,
                    "provider_call_budgets": {aid: self.call_budget(aid) for aid in self.provider_call_caps},
                    "slots": {"used": self._slots_used(), "cap": self.max_parallel},
                    "unsettled": {"count": self.unsettled(), "limit": self.unsettled_limit},
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

    def mark_reviewed(self, run_id: str) -> None:
        """사람이 공개된 답을 판단했다. 모델 호출 없이 내 차례를 끝내며 재시작에도 남는다."""
        with self.lock, self.store.tx() as tx:
            if not self._gate(run_id).revealed:
                raise ControllerError("공개된 답을 확인한 뒤에만 판단 완료로 표시할 수 있습니다.")
            if any(item["status"] in (RUNNING, UNKNOWN) for item in self._synthesis_attempts(run_id).values()):
                raise ControllerError("합성의 종료를 먼저 확인하세요.")
            if not self.store.row("SELECT 1 FROM events WHERE run_id = ? AND kind = 'human_reviewed'", run_id):
                tx.event(run_id, "human_reviewed")

    def _model_synthesis_state(self, run_id: str) -> dict[str, Any] | None:
        """같은 사건 투영으로 진행·실패·종료 미확인을 보인다. 과거 미확인 시도도 숨기지 않는다."""
        attempts = self._synthesis_attempts(run_id)
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
        # _finish와 finally가 같은 lock을 필요로 하므로 기다리는 동안 잡고 있지 않는다.
        return self.wait_idle(timeout)

    def wait_idle(self, timeout: float = 30.0) -> bool:
        """시작한 시도가 모두 반환했는지 본다. timeout=0은 기다리지 않고 현재 상태만 검사한다."""
        if not math.isfinite(timeout) or timeout < 0:
            raise ValueError("idle timeout must be finite and non-negative")
        deadline = time.monotonic() + timeout
        while True:
            with self.lock:
                if not self._workers and not self._synthesis:
                    return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(0.05, remaining))
