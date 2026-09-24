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
from app.report import build_report
from app.synthesis import SynthesisError, mock_synthesize, unavailable
from app.state import (CLI, MANUAL, QUEUED, RUNNING, AWAITING_USER, ACCEPTED, REJECTED, UNKNOWN,
                       DONE, INDEPENDENT_ONLY, INCLUDE_UNVERIFIED, QUORUM_POLICIES, RunGate, gate, confirmed)
from core import adapters, contract, env as core_env, isolation, membership as m, runner

PROMPT = ("다음 질문에, 다른 참여자의 답을 보지 않은 상태로 독립적으로 답하라. "
          "결론, 근거, 그리고 결론을 뒤집을 조건을 쓴다.\n\n질문:\n{question}\n")

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

    def plan(self, spec: ParticipantSpec, prompt: str, work_dir: str) -> contract.Plan: ...

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

    def plan(self, spec, prompt, work_dir):
        python = "/usr/bin/python3" if self.isolated else sys.executable
        data = prompt.encode("utf-8")
        planned = adapters.ExecutionSpec(spec.adapter_id, (python, self.SCRIPT, self.FLAVOR[spec.adapter_id],
                                                           spec.behavior),
                                         prompt, adapters.STDIN, hashlib.sha256(data).hexdigest(), len(data))
        box = isolation.Sandbox(work_dir=work_dir, home=work_dir + "-home", read_only=(os.path.dirname(self.SCRIPT),),
                                env={"LANG": "C.UTF-8"}, never=self.never) if self.isolated else None
        tmpl = contract.template(planned, box, home=work_dir + "-home")
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
        # 진행 중인 시도의 신호만 보관한다. 끝난 스레드/질문/작업 경로를 계속 쌓지 않는다.
        self._workers: dict[str, tuple[threading.Thread, threading.Event]] = {}
        self._recover()
        # 이전 controller가 시작하지 못한 시도가 남아 있으면 사용자가 이어서 시작하라고 할 때까지 기다린다
        self.paused = self.store.row("SELECT COUNT(*) AS n FROM participants JOIN runs USING (run_id) "
                                     "WHERE state = ? AND NOT cancel_requested", QUEUED)["n"] > 0

    # ---- 만들기와 예약 -------------------------------------------------------------------------
    def create_run(self, question: str, participants: list[ParticipantSpec], *, min_independent: int,
                   quorum_policy: str = INDEPENDENT_ONLY) -> str:
        question = question.strip()
        if not question:
            raise ControllerError("question is empty")
        if len({p.pid for p in participants}) != len(participants) or not participants:
            raise ControllerError("participants must be unique and non-empty")
        for p in participants:
            if p.transport not in (CLI, MANUAL) or (p.transport == CLI and p.adapter_id not in self.executor.adapter_ids):
                raise ControllerError(f"unsupported participant {p.pid!r}")
        if quorum_policy not in QUORUM_POLICIES:
            raise ControllerError(f"quorum_policy must be one of {', '.join(QUORUM_POLICIES)}")
        # 프런트엔드가 false를 보내도 실행기의 opt-in 등급을 올려 주지 않는다. 더 낮은 등급은 보존한다.
        if getattr(self.executor, "allow_context_unverified", False):
            participants = [replace(p, context_unverified=True) if p.transport == CLI else p for p in participants]
        confirmable = sum(confirmed(asdict(p)) for p in participants)
        if quorum_policy == INDEPENDENT_ONLY and min_independent > confirmable:
            raise ControllerError(f"only {confirmable} participant(s) can be confirmed independent (CLI); lower "
                                  "min_independent or choose include_unverified to count unverified answers")
        prompt = PROMPT.format(question=question)
        data = prompt.encode("utf-8")
        try:
            m.start(tuple(p.pid for p in participants), min_independent=min_independent)
        except m.MembershipError as exc:
            raise ControllerError(str(exc)) from None
        run_id = f"r{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"
        with self.lock, self.store.tx() as tx:
            tx.execute("INSERT INTO runs (run_id, created_at, question, prompt, input_sha256, input_bytes, "
                       "min_independent, roster, quorum_policy) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       run_id, time.time(), question, prompt, hashlib.sha256(data).hexdigest(), len(data),
                       min_independent, "{}", quorum_policy)
            for p in participants:
                tx.execute("INSERT INTO participants (run_id, pid, spec, state) VALUES (?, ?, ?, ?)", run_id, p.pid,
                           json.dumps(asdict(p), ensure_ascii=False), QUEUED if p.transport == CLI else AWAITING_USER)
            tx.event(run_id, "run_created", input_sha256=hashlib.sha256(data).hexdigest(), input_bytes=len(data),
                     participants=[p.pid for p in participants], min_independent=min_independent,
                     quorum_policy=quorum_policy)
            tx.event(run_id, "drafting_started")
        self.pump()
        return run_id

    def _slots_used(self) -> int:
        return self.store.row("SELECT COUNT(*) AS n FROM participants WHERE state IN (?, ?)", RUNNING, UNKNOWN)["n"]

    def unsettled(self) -> int:
        unknown = self.store.row("SELECT COUNT(*) AS n FROM participants WHERE state = ?", UNKNOWN)["n"]
        return unknown + runner.lingering()

    def call_budget(self, adapter_id: str | None = None) -> dict[str, int | None]:
        """실제 CLI를 시작하기 전에 원장에 예약한다. 재시작·실패·취소로 환불하지 않는다(계정 잔여와 다름)."""
        if self.max_real_calls is None:
            return {"used": 0, "cap": None}
        reservations = self.store.rows("SELECT payload FROM events WHERE kind = 'live_call_reserved'")
        used = len(reservations) if adapter_id is None else sum(
            json.loads(row["payload"]).get("adapter_id") == adapter_id for row in reservations)
        return {"used": used, "cap": self.max_real_calls if adapter_id is None
                else self.provider_call_caps.get(adapter_id)}

    def pump(self) -> None:
        """자리와 상한이 허락하는 만큼 대기 중인 시도를 시작한다. 한 참여자에 한 번만 — 다시 부르지 않는다.

        queued → running은 조건부로 바꾼다. 다른 controller가 먼저 가져갔으면 건너뛴다(같은 journal을 연
        controller 둘이 같은 참여자를 두 번 부르던 문제, A1 리뷰 반영).
        """
        with self.lock:
            if self.paused or self.unsettled() >= self.unsettled_limit:
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
                    plan, refused = self.executor.plan(spec, prompt, work), None
                    if plan.context_unverified and not spec.context_unverified:
                        raise ControllerError("queued participant has a different context policy; create a new run")
                    record, kind = plan.record(), plan.kind
                except Exception as exc:  # 거절: 아무것도 시작하지 않았다
                    plan, refused = None, f"{type(exc).__name__}: {exc}"
                    record, kind = {"adapter_id": spec.adapter_id, "refused": refused}, self.executor.kind
                with self.store.tx() as tx:
                    # 같은 거래에서 검사와 예약을 한다. 병렬 pump도 마지막 한 칸을 함께 쓰지 못한다.
                    if plan is not None and plan.kind == contract.REAL and self.max_real_calls is not None:
                        budget = self.call_budget()
                        provider = self.call_budget(spec.adapter_id)
                        exhausted = budget["used"] >= budget["cap"] or (self.provider_call_caps and (
                            provider["cap"] is None or provider["used"] >= provider["cap"]))
                        if exhausted:
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
            self._finish(run_id, spec.pid, attempt, result, outcome, detail)
        finally:
            with self.lock:
                self._workers.pop(attempt, None)
                self.pump()

    # ---- 결과 수용 관문 ------------------------------------------------------------------------
    def _finish(self, run_id, pid, attempt, result, outcome, detail=None) -> None:
        with self.lock:
            summary = None if result is None else {
                "state": result.state, "exit_code": result.exit_code, "containment": result.containment,
                "tree_confirmed_empty": result.tree_confirmed_empty, "input_delivery": result.input_delivery,
                "duration_ms": result.duration_ms, "notes": list(result.notes),
                "status": outcome.status, "ok": outcome.ok, "detail": outcome.detail, "usage": outcome.usage,
                "requested_model": outcome.requested_model, "reported_models": list(outcome.reported_models),
                "model_match": outcome.model_match}
            state, status, why = acceptance(result, outcome)
            detail = detail or why or (outcome.detail if outcome else None)
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
                             "prompt": run["prompt"], "input_sha256": run["input_sha256"],
                             "input_bytes": run["input_bytes"], "phase": run["phase"],
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
            return {"executor": self.executor.name, "live_call_budget": self.call_budget(),
                    "provider_call_budgets": {aid: self.call_budget(aid) for aid in self.provider_call_caps},
                    "slots": {"used": self._slots_used(), "cap": self.max_parallel},
                    "unsettled": {"count": self.unsettled(), "limit": self.unsettled_limit},
                    "paused": self.paused, "runs": runs}

    # ---- 내부 ---------------------------------------------------------------------------------
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

    def wait_idle(self, timeout: float = 30.0) -> bool:
        """시험용: 시작한 시도가 모두 돌아올 때까지 기다린다."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self.lock:
                if not self._workers:
                    return True
            time.sleep(0.05)
        return False
