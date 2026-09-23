"""A1 controller — 상태를 가진 유일한 곳. 모델을 부르지 않는 모의 모드부터 만든다(인계 4절 1).

한 줄 흐름: 고정 입력 manifest → 시도 예약 → 실행 → 결과 수용 관문 → 초안 봉인 → controller가 공개.

지키는 규칙
- 결과 수용: interpret()의 ok, 입력 전달 complete, 자손 전체 종료 확인(tree_confirmed_empty is True)을 모두
  본다. 종료를 확인하지 못한 시도는 unknown이고 초안을 받지 않으며 실행 자리를 풀지 않는다. 다시 부르지
  않는다. 예산은 돌려주지 않는다.
- 공개: 화면에 공개 버튼이 없다. 남은 참여자가 모두 끝났고 정족수가 있을 때 controller가 연다. 누가 빠졌으면
  남은 사람으로 자동 진행하지 않고 사용자의 축소 승인을 기다린다(Ledger BlindBarrier).
- 봉인: 공개 전에는 초안의 내용·길이·digest를 화면 쪽으로 넘기지 않는다. 제출됐다는 사실만 넘긴다.
- 수동 참여자(원본 앱): 사용자가 질문을 원본 앱에 옮기고 답을 붙여 넣는다. 입력 digest가 이 실행의 것과
  같아야 받는다 — 다른 실행에 잘못 넣는 것을 막을 뿐, 원본 앱에 그 질문을 넣었는지는 사용자의 확인에 기댄다.
  늦게 온 답과 중복 제출은 받지 않고 기록한다. blind·사용량은 "관측 안 됨"이다.
- 정리되지 않은 시도(unknown + runner.lingering())가 상한에 닿으면 새 시도를 시작하지 않는다.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import uuid
from typing import Any, Protocol

from app.store import Store, events
from core import adapters, env as core_env, isolation, membership as m, runner

CLI, MANUAL = "cli", "manual"
QUEUED, RUNNING, AWAITING_USER = "queued", "running", "awaiting_user"
ACCEPTED, REJECTED, UNKNOWN = "accepted", "rejected", "unknown"
DONE = (ACCEPTED, REJECTED)

PROMPT = ("다음 질문에, 다른 참여자의 답을 보지 않은 상태로 독립적으로 답하라. "
          "결론, 근거, 그리고 결론을 뒤집을 조건을 쓴다.\n\n질문:\n{question}\n")

SEALED_RESULT_KEYS = frozenset({"usage", "duration_ms", "reported_models"})

CONTAMINATION = {
    MANUAL: ("원본 앱의 메모리·다른 대화·프로젝트 지시문을 통제하지 못함", "사용량·시간 관측 안 됨"),
}


@dataclass(frozen=True)
class ParticipantSpec:
    pid: str
    label: str
    provider: str
    transport: str                  # CLI | MANUAL
    adapter_id: str | None = None   # CLI만
    model: str | None = None
    behavior: str = "ok"            # 모의 CLI의 행동(fake_cli.py)


class Executor(Protocol):
    name: str

    def execute(self, spec: ParticipantSpec, prompt: str, work_dir: str,
                timeout: float) -> tuple[runner.RunResult, adapters.Outcome]: ...


class MockExecutor:
    """가짜 CLI를 실제 실행 경로로 돌린다. Windows는 job object(runner.run), Linux는 bubblewrap(isolation.run).
    bubblewrap을 못 쓰는 Linux에서는 프로세스 그룹뿐이라 종료를 확인하지 못하고, 결과는 unknown이 된다."""

    SCRIPT = str(Path(__file__).with_name("fake_cli.py"))
    FLAVOR = {"claude-code": "claude", "codex": "codex"}

    def __init__(self, never: tuple[str, ...] = ()) -> None:
        self.never = never
        self.isolated = sys.platform == "linux" and _bwrap_trusted()
        self.name = "bubblewrap" if self.isolated else ("job_object" if runner.IS_WINDOWS else "process_group")

    def execute(self, spec, prompt, work_dir, timeout):
        flavor = self.FLAVOR[spec.adapter_id]
        if self.isolated:
            box = isolation.Sandbox(work_dir=work_dir, home=work_dir + "-home",
                                    read_only=(os.path.dirname(self.SCRIPT),), env={"LANG": "C.UTF-8"},
                                    never=self.never)
            result = isolation.run(["/usr/bin/python3", self.SCRIPT, flavor, spec.behavior], box,
                                   timeout=timeout, stdin_text=prompt)
        else:
            child, _ = core_env.child_env(os.environ)
            child["PYTHONUTF8"] = "1"
            result = runner.run([sys.executable, self.SCRIPT, flavor, spec.behavior], cwd=work_dir, env=child,
                                timeout=timeout, stdin_text=prompt)
        return result, adapters.interpret(spec.adapter_id, result, requested_model=spec.model or "")


def _bwrap_trusted() -> bool:
    try:
        isolation._trusted_bwrap()
        return True
    except isolation.IsolationError:
        return False


def _roster_json(roster: m.Roster) -> str:
    data = asdict(roster)
    data["active"], data["unknown"] = sorted(roster.active), sorted(roster.unknown)
    return json.dumps(data, ensure_ascii=False)


def _roster(text: str) -> m.Roster:
    d = json.loads(text)
    return m.Roster(tuple(d["requested"]), d["min_independent"], d["phase"], frozenset(d["active"]),
                    tuple(d["alternates"]), tuple(tuple(x) for x in d["dropped"]), frozenset(d["unknown"]))


class ControllerError(ValueError):
    """요청을 받지 않았다. 상태는 바뀌지 않았다."""


class Controller:
    def __init__(self, store: Store, executor: Executor, *, max_parallel: int = 2, unsettled_limit: int = 2,
                 timeout: float = 60.0, work_root: str | None = None) -> None:
        self.store, self.executor = store, executor
        self.max_parallel, self.unsettled_limit, self.timeout = max_parallel, unsettled_limit, timeout
        self.work_root = work_root or os.path.join(tempfile.gettempdir(), "dml-work")
        self.lock = threading.RLock()
        self.threads: list[threading.Thread] = []
        self._recover()

    # ---- 만들기와 예약 -------------------------------------------------------------------------
    def create_run(self, question: str, participants: list[ParticipantSpec], *, min_independent: int) -> str:
        question = question.strip()
        if not question:
            raise ControllerError("question is empty")
        if len({p.pid for p in participants}) != len(participants) or not participants:
            raise ControllerError("participants must be unique and non-empty")
        for p in participants:
            if p.transport not in (CLI, MANUAL) or (p.transport == CLI and p.adapter_id not in MockExecutor.FLAVOR):
                raise ControllerError(f"unsupported participant {p.pid!r}")
        prompt = PROMPT.format(question=question)
        data = prompt.encode("utf-8")
        try:
            roster = m.advance(m.start(tuple(p.pid for p in participants), min_independent=min_independent),
                               m.DRAFTING)
        except m.MembershipError as exc:
            raise ControllerError(str(exc)) from None
        run_id = f"r{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"
        with self.lock, self.store.tx() as tx:
            tx.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)", run_id, time.time(), question,
                       prompt, hashlib.sha256(data).hexdigest(), len(data), min_independent, _roster_json(roster))
            for p in participants:
                tx.execute("INSERT INTO participants VALUES (?, ?, ?, ?, NULL, NULL, NULL)", run_id, p.pid,
                           json.dumps(asdict(p), ensure_ascii=False), QUEUED if p.transport == CLI else AWAITING_USER)
            tx.event(run_id, "run_created", input_sha256=hashlib.sha256(data).hexdigest(), input_bytes=len(data),
                     participants=[p.pid for p in participants], min_independent=min_independent)
            tx.event(run_id, "drafting_started")
        self.pump()
        return run_id

    def _slots_used(self) -> int:
        return self.store.row("SELECT COUNT(*) AS n FROM participants WHERE state IN (?, ?)", RUNNING, UNKNOWN)["n"]

    def unsettled(self) -> int:
        unknown = self.store.row("SELECT COUNT(*) AS n FROM participants WHERE state = ?", UNKNOWN)["n"]
        return unknown + runner.lingering()

    def pump(self) -> None:
        """자리와 상한이 허락하는 만큼 대기 중인 시도를 시작한다. 한 참여자에 한 번만 — 다시 부르지 않는다."""
        with self.lock:
            if self.unsettled() >= self.unsettled_limit:
                return
            queued = self.store.rows("SELECT p.run_id, p.pid, p.spec FROM participants p JOIN runs r USING (run_id) "
                                     "WHERE p.state = ? ORDER BY r.created_at, p.rowid", QUEUED)
            for row in queued:
                if self._slots_used() >= self.max_parallel:
                    return
                if _roster(self._run(row["run_id"])["roster"]).phase != m.DRAFTING:
                    continue
                spec = ParticipantSpec(**json.loads(row["spec"]))
                attempt = uuid.uuid4().hex[:8]
                work = os.path.join(self.work_root, row["run_id"], spec.pid)
                os.makedirs(work, exist_ok=True)
                with self.store.tx() as tx:
                    tx.execute("UPDATE participants SET state = ?, detail = ? WHERE run_id = ? AND pid = ?",
                               RUNNING, f"attempt {attempt}", row["run_id"], spec.pid)
                    tx.event(row["run_id"], "attempt_started", pid=spec.pid, attempt=attempt,
                             executor=self.executor.name, behavior=spec.behavior)
                prompt = self._run(row["run_id"])["prompt"]
                thread = threading.Thread(target=self._attempt, args=(row["run_id"], spec, attempt, prompt, work),
                                          daemon=True)
                self.threads.append(thread)
                thread.start()

    def _attempt(self, run_id: str, spec: ParticipantSpec, attempt: str, prompt: str, work: str) -> None:
        try:
            result, outcome = self.executor.execute(spec, prompt, work, self.timeout)
        except Exception as exc:  # 실행기 자체의 실패도 기록하고 넘어간다. 종료는 확인하지 못했다
            result, outcome = None, None
            detail = f"executor error: {type(exc).__name__}"
        else:
            detail = None
        self._finish(run_id, spec.pid, attempt, result, outcome, detail)

    # ---- 결과 수용 관문 ------------------------------------------------------------------------
    def _finish(self, run_id, pid, attempt, result, outcome, detail=None) -> None:
        with self.lock:
            summary = None if result is None else {
                "state": result.state, "exit_code": result.exit_code, "containment": result.containment,
                "tree_confirmed_empty": result.tree_confirmed_empty, "input_delivery": result.input_delivery,
                "duration_ms": result.duration_ms, "notes": list(result.notes),
                "status": outcome.status, "ok": outcome.ok, "detail": outcome.detail, "usage": outcome.usage,
                "reported_models": list(outcome.reported_models), "model_match": outcome.model_match}
            roster = _roster(self._run(run_id)["roster"])
            with self.store.tx() as tx:
                if result is None or result.tree_confirmed_empty is not True:
                    state, status = UNKNOWN, "unknown"
                    if pid in roster.active:
                        roster = m.decide(roster, "cancel_unconfirmed", pid).roster
                    tx.event(run_id, "attempt_unknown", pid=pid, attempt=attempt, result=summary, detail=detail)
                elif outcome.ok and result.input_delivery in (None, runner.INPUT_COMPLETE):
                    state, status = ACCEPTED, outcome.status
                    text = outcome.text or ""
                    tx.execute("INSERT OR REPLACE INTO drafts VALUES (?, ?, ?, ?, ?, ?)", run_id, pid, text,
                               hashlib.sha256(text.encode("utf-8")).hexdigest(), CLI, time.time())
                    tx.event(run_id, "draft_sealed", pid=pid, attempt=attempt, result=summary)
                else:
                    state, status = REJECTED, outcome.status
                    roster = m.decide(roster, "unavailable", pid).roster
                    tx.event(run_id, "attempt_rejected", pid=pid, attempt=attempt, result=summary)
                tx.execute("UPDATE participants SET state = ?, status = ?, detail = ?, result = ? "
                           "WHERE run_id = ? AND pid = ?", state, status,
                           detail or (outcome.detail if outcome else None),
                           json.dumps(summary, ensure_ascii=False), run_id, pid)
                tx.execute("UPDATE runs SET roster = ? WHERE run_id = ?", _roster_json(roster), run_id)
            self._maybe_reveal(run_id)
        self.pump()

    def _maybe_reveal(self, run_id: str) -> None:
        """남은 참여자가 모두 끝났고 정족수가 있으면 연다. 빠진 사람이 있으면 축소 승인이 먼저다."""
        run = self._run(run_id)
        roster = _roster(run["roster"])
        states = [r["state"] for r in self.store.rows("SELECT state FROM participants WHERE run_id = ?", run_id)]
        if roster.phase != m.DRAFTING or any(s not in DONE for s in states):
            return
        note = None
        if roster.dropped and not run["reduction_approved"]:
            note = f"요청한 {len(roster.requested)}인 구성이 완료되지 않았습니다. 남은 참여자로 진행하려면 축소 승인이 필요합니다."
        elif not m.quorum_met(roster):
            note = (f"독립 참여자 {len(roster.active - roster.unknown)}명 — 최소 {roster.min_independent}명이 필요합니다. "
                    "유료로 채우지 않습니다.")
        with self.store.tx() as tx:
            if note:
                tx.execute("UPDATE runs SET note = ? WHERE run_id = ?", note, run_id)
                tx.event(run_id, "reveal_held", note=note)
            else:
                tx.execute("UPDATE runs SET roster = ?, note = NULL WHERE run_id = ?",
                           _roster_json(m.advance(roster, m.REVEALED)), run_id)
                tx.event(run_id, "revealed", drafts=len([s for s in states if s == ACCEPTED]))

    # ---- 사용자 행동 ---------------------------------------------------------------------------
    def submit_manual(self, run_id: str, pid: str, text: str, input_sha256: str) -> None:
        with self.lock:
            run, part = self._run(run_id), self._part(run_id, pid)
            spec = ParticipantSpec(**json.loads(part["spec"]))
            reason = None
            if spec.transport != MANUAL:
                reason = "not a manual participant"
            elif _roster(run["roster"]).phase != m.DRAFTING:
                reason = "late: drafts were already revealed or the run ended"
            elif part["state"] != AWAITING_USER:
                reason = "duplicate: this participant already has a result"
            elif input_sha256 != run["input_sha256"]:
                reason = "different input: the answer was made for another question"
            elif not text.strip():
                reason = "empty answer"
            if reason:
                with self.store.tx() as tx:
                    tx.event(run_id, "manual_refused", pid=pid, reason=reason)
                raise ControllerError(reason)
            with self.store.tx() as tx:
                tx.execute("INSERT OR REPLACE INTO drafts VALUES (?, ?, ?, ?, ?, ?)", run_id, pid, text,
                           hashlib.sha256(text.encode("utf-8")).hexdigest(), MANUAL, time.time())
                tx.execute("UPDATE participants SET state = ?, status = ? WHERE run_id = ? AND pid = ?",
                           ACCEPTED, "manual", run_id, pid)
                tx.event(run_id, "draft_sealed", pid=pid, source=MANUAL)
            self._maybe_reveal(run_id)

    def withdraw_manual(self, run_id: str, pid: str) -> None:
        """사용자가 원본 앱에서 답을 받지 못했다. 그 참여자를 빼고, 빈자리는 채우지 않는다."""
        with self.lock:
            part = self._part(run_id, pid)
            if part["state"] != AWAITING_USER:
                raise ControllerError("only a participant waiting for the user can be withdrawn")
            roster = m.decide(_roster(self._run(run_id)["roster"]), "unavailable", pid).roster
            with self.store.tx() as tx:
                tx.execute("UPDATE participants SET state = ?, status = ? WHERE run_id = ? AND pid = ?",
                           REJECTED, "withdrawn", run_id, pid)
                tx.execute("UPDATE runs SET roster = ? WHERE run_id = ?", _roster_json(roster), run_id)
                tx.event(run_id, "manual_withdrawn", pid=pid)
            self._maybe_reveal(run_id)

    def approve_reduction(self, run_id: str) -> None:
        with self.lock:
            with self.store.tx() as tx:
                tx.execute("UPDATE runs SET reduction_approved = 1 WHERE run_id = ?", run_id)
                tx.event(run_id, "reduction_approved")
            self._maybe_reveal(run_id)

    def acknowledge_unknown(self, run_id: str, pid: str) -> None:
        """사용자가 그 시도의 종료를 직접 확인했다고 알린다. 자리는 풀지만 예산은 돌려주지 않고, 초안도 받지 않는다."""
        with self.lock:
            if self._part(run_id, pid)["state"] != UNKNOWN:
                raise ControllerError("only an unknown attempt can be acknowledged")
            roster = _roster(self._run(run_id)["roster"])
            if pid in roster.active:
                roster = m.decide(roster, "unavailable", pid).roster
            with self.store.tx() as tx:
                tx.execute("UPDATE participants SET state = ?, status = ? WHERE run_id = ? AND pid = ?",
                           REJECTED, "unknown_acknowledged", run_id, pid)
                tx.execute("UPDATE runs SET roster = ? WHERE run_id = ?", _roster_json(roster), run_id)
                tx.event(run_id, "unknown_acknowledged", pid=pid)
            self._maybe_reveal(run_id)
        self.pump()

    # ---- 다시 시작 ------------------------------------------------------------------------------
    def _recover(self) -> None:
        """이전 controller가 돌리던 시도는 종료를 확인할 수 없다. unknown으로 두고 다시 부르지 않는다."""
        for row in self.store.rows("SELECT run_id, pid FROM participants WHERE state = ?", RUNNING):
            roster = _roster(self._run(row["run_id"])["roster"])
            if row["pid"] in roster.active:
                roster = m.decide(roster, "cancel_unconfirmed", row["pid"]).roster
            with self.store.tx() as tx:
                tx.execute("UPDATE participants SET state = ?, status = ?, detail = ? WHERE run_id = ? AND pid = ?",
                           UNKNOWN, "unknown", "controller restarted; termination not confirmed",
                           row["run_id"], row["pid"])
                tx.execute("UPDATE runs SET roster = ? WHERE run_id = ?", _roster_json(roster), row["run_id"])
                tx.event(row["run_id"], "attempt_unknown", pid=row["pid"], detail="controller restarted")

    # ---- 화면용 투영 ---------------------------------------------------------------------------
    def view(self) -> dict[str, Any]:
        """화면에 넘기는 것. 공개 전에는 초안의 내용·길이·digest를 넣지 않는다."""
        with self.lock:
            runs = []
            for run in self.store.rows("SELECT * FROM runs ORDER BY created_at DESC"):
                roster = _roster(run["roster"])
                revealed = roster.phase in (m.REVEALED, m.SYNTHESIS)
                parts, calls = [], {"succeeded": 0, "failed": 0, "unknown": 0}
                for p in self.store.rows("SELECT * FROM participants WHERE run_id = ? ORDER BY rowid", run["run_id"]):
                    spec = ParticipantSpec(**json.loads(p["spec"]))
                    result = json.loads(p["result"]) if p["result"] else None
                    if result and not revealed:
                        # 토큰 수와 걸린 시간은 답의 길이를 짐작하게 한다. 공개 전에는 넘기지 않는다
                        result = {k: v for k, v in result.items() if k not in SEALED_RESULT_KEYS}
                    if spec.transport == CLI and p["state"] in (ACCEPTED, REJECTED, UNKNOWN):
                        calls[{"accepted": "succeeded", "rejected": "failed", "unknown": "unknown"}[p["state"]]] += 1
                    item = {"pid": spec.pid, "label": spec.label, "provider": spec.provider,
                            "transport": spec.transport, "behavior": spec.behavior if spec.transport == CLI else None,
                            "state": p["state"], "status": p["status"], "detail": p["detail"],
                            "contamination": list(CONTAMINATION.get(spec.transport, ("모의 CLI — 모델 호출 없음",))),
                            "result": result, "dropped": any(d[0] == spec.pid for d in roster.dropped)}
                    if revealed and p["state"] == ACCEPTED:
                        draft = self.store.row("SELECT text, source FROM drafts WHERE run_id = ? AND pid = ?",
                                               run["run_id"], spec.pid)
                        item["draft"] = draft["text"] if draft else None
                    parts.append(item)
                cli_total = sum(1 for p in parts if p["transport"] == CLI)
                runs.append({"run_id": run["run_id"], "created_at": run["created_at"], "question": run["question"],
                             "prompt": run["prompt"], "input_sha256": run["input_sha256"],
                             "input_bytes": run["input_bytes"], "phase": roster.phase,
                             "min_independent": roster.min_independent, "note": run["note"],
                             "reduction_approved": bool(run["reduction_approved"]),
                             "budget": {"used": sum(calls.values()) + sum(1 for p in parts if p["state"] == RUNNING),
                                        "cap": cli_total, "breakdown": calls,
                                        "manual": sum(1 for p in parts if p["transport"] == MANUAL)},
                             "participants": parts,
                             "events": [e["kind"] for e in events(self.store, run["run_id"])][-12:]})
            return {"executor": self.executor.name, "slots": {"used": self._slots_used(), "cap": self.max_parallel},
                    "unsettled": {"count": self.unsettled(), "limit": self.unsettled_limit}, "runs": runs}

    # ---- 내부 ---------------------------------------------------------------------------------
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
            if not any(t.is_alive() for t in self.threads):
                return True
            time.sleep(0.05)
        return False
