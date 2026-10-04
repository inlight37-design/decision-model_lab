"""Process coordination, lifecycle, acceptance and recovery. No UI or command facade dependency."""
from __future__ import annotations
from dataclasses import replace
import hashlib
import json
import math
import os
import threading
import time
import uuid
from app import refine as refining
from app.synthesis import SynthesisError, check_model_synthesis, model_unavailable
from app.state import CLI, MANUAL, QUEUED, RUNNING, AWAITING_USER, ACCEPTED, REJECTED, UNKNOWN, COLLECTED
from core import contract, membership as m, runner
from app.domain import ParticipantSpec, ControllerError, _CapReached, storable, _storable_meta, acceptance, _marker_echo
from app.execution.seats import SEATS
from app.execution.executor import _check, _not_started


class ExecutionCoordinator:
    def __init__(self, runtime, inputs, invocations, repository):
        self.runtime = runtime
        self.store = runtime.store
        self.inputs = inputs
        self.invocations = invocations
        self.repository = repository
        self.advance_reviews = None

    def pump(self) -> None:
        """자리와 상한이 허락하는 만큼 대기 중인 시도를 시작한다. 한 참여자에 한 번만 — 다시 부르지 않는다.

        queued → running은 조건부로 바꾼다. 다른 controller가 먼저 가져갔으면 건너뛴다(같은 journal을 연
        controller 둘이 같은 참여자를 두 번 부르던 문제, A1 리뷰 반영).
        """
        with self.runtime.lock:
            if self.runtime.closing:
                return
            # 교차검토: 앞 검토자가 받지 못한 라운드는 관문과 상관없이 닫고, 관문이 열려 있으면 다음 검토자를 부른다
            held = self.runtime.paused or self.invocations.unsettled() >= self.runtime.unsettled_limit
            if self.advance_reviews is not None:
                self.advance_reviews(start=not held)
            if held:
                return
            queued = self.store.rows("SELECT p.run_id, p.pid, p.spec FROM participants p JOIN runs r USING (run_id) "
                                     "WHERE p.state = ? AND NOT r.cancel_requested ORDER BY r.created_at, p.rowid", QUEUED)
            every = self.invocations._synthesis_attempts()   # 이 lock 안에서는 합성이 새로 시작되지 않는다 — 한 번만 읽는다
            for row in queued:
                if self.invocations._slots_used(every) >= self.runtime.max_parallel:
                    return
                spec = ParticipantSpec(**json.loads(row["spec"]))
                attempt = uuid.uuid4().hex
                work = os.path.join(self.runtime.work_root, row["run_id"], spec.pid)
                # 최종 계획을 한 번 만든다. 그 기록(질문 본문 없이)과 실행 종류를 시도 ID와 함께 저장한 뒤에만 같은
                # 계획을 실행한다(G4·G6). 저장하지 못하면 실행하지 않는다.
                try:
                    # 작업 폴더 준비도 시작 전 실패다. 여기서 빠져나가면 이 참여자가 queued로 남아 다음 pump마다
                    # 대기열 맨 앞에서 다시 멈춘다(구조 검토 AH-02). 이 참여자만 시작 전 실패로 닫고 다음으로 간다.
                    os.makedirs(work, exist_ok=True)
                    # 자료가 있는 실행은 그 사본 폴더 하나를 입력으로 준다(일반 팀원은 자기가 받은 자료만).
                    # 입력 전문·목록·해시가 다르면 여기서 거절된다.
                    prompt, source = self.inputs._attempt_input(row["run_id"], spec.pid)
                    extra = {"inputs": (source,)} if source else {}
                    plan, refused = self.runtime.executor.plan(spec, prompt, work, **extra), None
                    if plan.context_unverified and not spec.context_unverified:
                        raise ControllerError("queued participant has a different context policy; create a new run")
                    _check(self.runtime.executor, plan)   # 예약 전에 격리 경로·연결을 본다(R4)
                    record, kind = plan.record(), plan.kind
                except Exception as exc:  # 거절: 아무것도 시작하지 않았다
                    plan, refused = None, f"{type(exc).__name__}: {exc}"
                    record, kind = {"adapter_id": spec.adapter_id, "refused": refused}, self.runtime.executor.kind
                with self.store.tx() as tx:
                    # 같은 거래에서 검사와 예약을 한다. 병렬 pump도 마지막 한 칸을 함께 쓰지 못한다.
                    if plan is not None and plan.kind == contract.REAL and self.runtime.max_real_calls is not None:
                        if self.invocations._budget_exhausted(spec.adapter_id):
                            plan, refused = None, "real CLI call budget exhausted; no call was started"
                            record = {"adapter_id": spec.adapter_id, "refused": refused}
                    part = self.repository._part(row["run_id"], spec.pid)
                    taken = (self.repository._gate(row["run_id"]).accepting and part["state"] == QUEUED
                             and self.repository._transition(tx, part, RUNNING, attempt=attempt, kind=kind))
                    if taken:
                        if plan is not None and plan.kind == contract.REAL and self.runtime.max_real_calls is not None:
                            self.invocations.reserve(tx, row["run_id"], pid=spec.pid, attempt=attempt,
                                                     adapter_id=spec.adapter_id)
                        tx.event(row["run_id"], "attempt_started", pid=spec.pid, attempt=attempt,
                                 executor=self.runtime.executor.name, execution=kind, behavior=spec.behavior, spec=record)
                if not taken:
                    continue
                if plan is None:
                    self._finish(row["run_id"], spec.pid, attempt, *_not_started(spec, refused))
                    continue
                cancel = threading.Event()
                thread = threading.Thread(target=self._attempt,
                                          args=(row["run_id"], spec, attempt, plan, cancel), daemon=True)
                self.runtime.workers[attempt] = (thread, cancel)
                try:
                    thread.start()
                except RuntimeError:
                    self.runtime.workers.pop(attempt)
                    self._finish(row["run_id"], spec.pid, attempt, *_not_started(spec, "worker thread did not start"))


    def resume(self) -> None:
        """다시 시작한 뒤 멈춰 둔 대기 시도를 사용자가 이어서 시작하라고 했다."""
        with self.runtime.lock:
            if self.runtime.closing:
                raise ControllerError("controller is shutting down")
            self.runtime.paused = False
        self.pump()


    def _attempt(self, run_id: str, spec: ParticipantSpec, attempt: str, plan: contract.Plan,
                 cancel: threading.Event) -> None:
        try:
            try:
                result, outcome = self.runtime.executor.run(plan, self.runtime.timeout, cancel=cancel)
            except Exception as exc:  # 실행기 자체 실패: 자손 종료는 확인하지 못했다
                result, outcome, detail = None, None, f"executor error: {type(exc).__name__}"
            else:
                detail = None
            try:
                self._finish(run_id, spec.pid, attempt, result, outcome, detail)
            except Exception as exc:  # 결과를 저장하지 못했다 — 시도를 RUNNING으로 남기지 않는다(카드 #70)
                self._finish_unstored(run_id, spec.pid, attempt, result, exc)
        finally:
            with self.runtime.lock:
                self.runtime.workers.pop(attempt, None)
                self.pump()


    def _finish_unstored(self, run_id, pid, attempt, result, exc) -> None:
        """결과 저장이 예외로 끝난 시도를 닫는다. 자손 종료가 확인됐을 때만 rejected, 아니면 unknown이다.
        호출은 이미 시작했으므로 예산을 되돌리지 않고 자동으로 다시 부르지 않는다(외부 검토 R05)."""
        state = REJECTED if result is not None and result.tree_confirmed_empty is True else UNKNOWN
        detail = f"the result could not be stored ({type(exc).__name__}); the answer was discarded"
        with self.runtime.lock, self.store.tx() as tx:
            expected = {"run_id": run_id, "pid": pid, "state": RUNNING, "attempt": attempt}
            if self.repository._transition(tx, expected, state, status="result_not_stored", detail=detail):
                tx.event(run_id, "attempt_result_not_stored", pid=pid, attempt=attempt, error=type(exc).__name__)
                if state == UNKNOWN:
                    tx.event(run_id, "attempt_unknown", pid=pid, attempt=attempt, result=None, detail=detail)
                self._maybe_reveal(run_id, tx)


    def _finish(self, run_id, pid, attempt, result, outcome, detail=None) -> None:
        with self.runtime.lock:
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
                current_gate = self.repository._gate(run_id)
                if not current_gate.accepting:
                    # 신호를 늦게 본 실행기의 정상 답도 끝난 실행에는 봉인/공개하지 않는다.
                    state = REJECTED if result is not None and result.tree_confirmed_empty is True else UNKNOWN
                    status = "cancelled" if state == REJECTED else "cancel_unconfirmed"
                    detail = "run no longer accepts results; answer discarded"
                # 이 시도가 아직 이 참여자의 진행 중인 시도일 때만 반영한다. 다시 시작한 controller가 unknown으로
                # 돌렸거나 사용자가 종료를 확인한 뒤에 온 결과는 사건으로만 남긴다 — 초안·명단은 그대로다.
                expected = {"run_id": run_id, "pid": pid, "state": RUNNING, "attempt": attempt}
                if not self.repository._transition(tx, expected, state, status=status, detail=detail,
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
        current_gate = self.repository._gate(run_id)
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


    def cancel_run(self, run_id: str) -> None:
        """되돌리지 않는 실행 취소. 먼저 저장하고 신호를 보낸다. 다시 눌러도 예산/사건을 중복 변경하지 않는다.

        대기 CLI·수동 제출은 시작 없이 거절한다. 진행 중인 시도는 종료 결과가 올 때까지 자리를 유지한다.
        기존 초안은 계속 봉인한다. 외부 앱 작업 자체를 중단시키거나 이미 쓴 예산을 돌려받는 기능은 아니다.
        """
        with self.runtime.lock:
            with self.store.tx() as tx:
                current_gate = self.repository._gate(run_id)
                if not current_gate.accepting and current_gate.status != "cancelled":
                    raise ControllerError("only a drafting run can be cancelled; revealed drafts cannot be hidden again")
                if current_gate.accepting:
                    tx.execute("UPDATE runs SET cancel_requested = 1 WHERE run_id = ? AND NOT cancel_requested",
                               run_id)
                    for part in self.store.rows("SELECT * FROM participants WHERE run_id = ? AND state IN (?, ?)",
                                                run_id, QUEUED, AWAITING_USER):
                        self.repository._transition(tx, part, REJECTED, status="cancelled_before_start")
                    tx.event(run_id, "run_cancel_requested")
            for part in self.store.rows("SELECT attempt FROM participants WHERE run_id = ? AND state = ?", run_id, RUNNING):
                worker = self.runtime.workers.get(part["attempt"])
                if worker:
                    worker[1].set()
        # 실행을 닫는 사람의 동작이다. 진행 중인 실행을 기다리던 교차검토 차례를 깨운다(Codex 교차검토, PR #144)
        self.pump()


    def submit_manual(self, run_id: str, pid: str, text: str, input_sha256: str, *,
                      user_confirmed: bool = False) -> None:
        """원본 앱의 답을 받는다. user_confirmed: 사용자가 "이 질문을 원본 앱에 넣어 받은 답"이라고 확인했다 —
        따로 남길 뿐 독립성 확인으로 올리지 않는다(K21, 2절 18)."""
        with self.runtime.lock:
            reason = None
            with self.store.tx() as tx:
                run, part = self.repository._run(run_id), self.repository._part(run_id, pid)
                spec = ParticipantSpec(**json.loads(part["spec"]))
                echo, body = _marker_echo(text, run_id, pid, run["input_sha256"])
                if spec.transport != MANUAL:
                    reason = "not a manual participant"
                elif not self.repository._gate(run_id).accepting:
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
                if reason is None and not self.repository._transition(tx, part, ACCEPTED, status="manual", result=json.dumps(result)):
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
        with self.runtime.lock, self.store.tx() as tx:
            part = self.repository._part(run_id, pid)
            if not self.repository._gate(run_id).accepting or part["state"] != AWAITING_USER:
                raise ControllerError("only a participant waiting for the user can be withdrawn")
            if self.repository._transition(tx, part, REJECTED, status="withdrawn"):
                tx.event(run_id, "manual_withdrawn", pid=pid)
                self._maybe_reveal(run_id, tx)
        # 실행을 닫는 사람의 동작이다. 진행 중인 실행을 기다리던 교차검토 차례를 깨운다(Codex 교차검토, PR #144)
        self.pump()


    def approve_reduction(self, run_id: str) -> None:
        """축소 승인은 controller가 그것을 기다릴 때만 받는다: 초안 작성 중이고, 모두 끝났고, 빠진 사람이 있고,
        아직 승인하지 않았다. 그 뒤로는 구성이 바뀌지 않으므로 승인은 지금 구성에 대한 것이다(A1-06)."""
        with self.runtime.lock, self.store.tx() as tx:
            current_gate = self.repository._gate(run_id)
            if not current_gate.can_approve_reduction:
                raise ControllerError("no reduction is waiting for approval")
            tx.execute("UPDATE runs SET reduction_approved = 1 WHERE run_id = ? AND NOT reduction_approved", run_id)
            tx.event(run_id, "reduction_approved", requested=list(current_gate.requested), dropped=list(current_gate.dropped))
            self._maybe_reveal(run_id, tx)
        # 실행을 닫는 사람의 동작이다. 진행 중인 실행을 기다리던 교차검토 차례를 깨운다(Codex 교차검토, PR #144)
        self.pump()


    def acknowledge_unknown(self, run_id: str, pid: str) -> None:
        """사용자가 그 시도의 종료를 직접 확인했다고 알린다. 자리는 풀지만 예산은 돌려주지 않고, 초안도 받지 않는다."""
        with self.runtime.lock, self.store.tx() as tx:
            part = self.repository._part(run_id, pid)
            if part["state"] != UNKNOWN:
                raise ControllerError("only an unknown attempt can be acknowledged")
            if self.repository._transition(tx, part, REJECTED, status="unknown_acknowledged"):
                tx.event(run_id, "unknown_acknowledged", pid=pid)
                self._maybe_reveal(run_id, tx)
        self.pump()


    def _recover(self) -> None:
        """이 원장을 연 controller는 이것 하나다(Store의 잠금). running으로 남은 시도는 멈춘 controller의 것이고
        종료를 확인할 수 없으므로 unknown으로 두고 다시 부르지 않는다. 그다음 초안 작성 중인 실행마다 공개 관문을
        다시 본다 — 이 수정 전의 원장은 마지막 초안 저장과 공개 사이에서 멈췄을 수 있다(A1-05). 외부 호출은 없다."""
        for row in self.store.rows("SELECT * FROM participants WHERE state = ?", RUNNING):
            with self.store.tx() as tx:
                if self.repository._transition(tx, row, UNKNOWN, status="controller_restarted",
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


    def start_synthesis(self, run_id, attempt, plan, report, labels):
        """Launch only after the caller commits the reservation and synthesis_started.

        Called under the runtime lock; thread failure keeps the existing receipt.
        """
        cancel = threading.Event()
        thread = threading.Thread(target=self._synthesis_attempt,
                                  args=(run_id, attempt, plan, report, labels, cancel), daemon=True)
        self.runtime.syntheses[run_id] = (thread, cancel, attempt)
        try:
            thread.start()
        except RuntimeError:
            self.runtime.syntheses.pop(run_id)
            with self.store.tx() as tx:
                tx.event(run_id, "synthesis_failed", attempt=attempt, result=model_unavailable(
                    report, {"adapter_id": plan.spec.adapter_id, "started": False}, "worker thread did not start"))

    def _synthesis_attempt(self, run_id: str, attempt: str, plan: contract.Plan, report: dict,
                           labels: dict[str, str], cancel: threading.Event) -> None:
        try:
            try:
                result, outcome = self.runtime.executor.run(plan, self.runtime.timeout, cancel=cancel)
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
                with self.runtime.lock, self.store.tx() as tx:
                    tx.event(run_id, "synthesis_completed" if record["status"] == "completed" else "synthesis_failed",
                             attempt=attempt, result=record)
            except Exception as exc:
                # 결과를 원장에 남기지 못했다. 결과 없는 시작으로 남아 종료 미확인·자리 유지다(초안의 카드 #70과 같다).
                with self.runtime.lock, self.store.tx() as tx:
                    tx.event(run_id, "synthesis_result_not_stored", attempt=attempt, error=type(exc).__name__)
        finally:
            with self.runtime.lock:
                self.runtime.syntheses.pop(run_id, None)
                self.pump()


    def _start_seat(self, seat: "_Seat", event_key: str, where: dict, supervisor: ParticipantSpec, text: str,
                    work: str, insert, inputs: tuple[str, ...] = ()) -> None:
        """상위 모델 호출 하나를 시작한다 — 다듬기 차례·다음 단계 제안·분담 제안·결과 모으기가 같이 쓴다. 계획을 한 번 만들고, 같은
        거래에서 상한을 보고 예약하고 행을 넣은 뒤(insert), 그 계획을 백그라운드로 돌린다. 시작 전 거절은 아무것도 예약하지
        않는다. inputs는 읽기 전용 자료 폴더(분담 제안만 준다). 호출하는 쪽이 self.lock을 쥐고 이미 관문(한 번에 하나·
        자리·종료 미확인)을 봤다."""
        attempt = uuid.uuid4().hex
        try:
            os.makedirs(work, exist_ok=True)
            plan = self.runtime.executor.plan(replace(supervisor, pid=seat.plan_pid, label=seat.plan_label), text, work,
                                      **({"inputs": inputs} if inputs else {}))
            _check(self.runtime.executor, plan)   # 예약 전에 격리 경로·연결을 본다(R4)
        except Exception as exc:   # 계획 거절: 아무것도 시작하지 않았다
            raise ControllerError(f"supervisor plan refused: {type(exc).__name__}: {exc}") from None
        with self.store.tx() as tx:
            if plan.kind == contract.REAL and self.runtime.max_real_calls is not None:
                if self.invocations._budget_exhausted(supervisor.adapter_id):
                    raise _CapReached("real CLI call budget exhausted; no call was started")
                self.invocations.reserve(tx, event_key, pid=seat.plan_pid, attempt=attempt,
                                         adapter_id=supervisor.adapter_id, purpose=seat.purpose)
            insert(tx, attempt, plan.kind)
            tx.event(event_key, seat.started, **seat.label(where), attempt=attempt, adapter_id=supervisor.adapter_id,
                     execution=plan.kind, spec=plan.record())
        cancel = threading.Event()
        thread = threading.Thread(target=self._seat_attempt, args=(seat, event_key, where, attempt, plan, cancel),
                                  daemon=True)
        self.runtime.upper_workers[attempt] = (thread, cancel)
        try:
            thread.start()
        except RuntimeError:
            self.runtime.upper_workers.pop(attempt)
            self._settle_seat(seat, event_key, where, attempt, *_not_started(supervisor, "worker thread did not start"))


    def _seat_attempt(self, seat: "_Seat", event_key: str, where: dict, attempt: str, plan: contract.Plan,
                      cancel: threading.Event) -> None:
        try:
            try:
                result, outcome = self.runtime.executor.run(plan, self.runtime.timeout, cancel=cancel)
            except Exception:   # 실행기 자체 실패: 자손 종료는 확인하지 못했다
                result, outcome = None, None
            try:
                self._settle_seat(seat, event_key, where, attempt, result, outcome)
            except Exception as exc:   # 결과를 저장하지 못했다 — 진행 중으로 남기지 않는다(카드 #70과 같다)
                state = REJECTED if result is not None and result.tree_confirmed_empty is True else UNKNOWN
                with self.runtime.lock, self.store.tx() as tx:
                    if tx.execute(f"UPDATE {seat.table} SET state = ?, status = 'result_not_stored' WHERE "
                                  f"{seat.match} AND state = ? AND attempt = ?", state, *where.values(), RUNNING, attempt):
                        tx.event(event_key, seat.not_stored, **seat.label(where), attempt=attempt,
                                 error=type(exc).__name__)
        finally:
            with self.runtime.lock:
                self.runtime.upper_workers.pop(attempt, None)
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
        with self.runtime.lock, self.store.tx() as tx:
            if tx.execute(f"UPDATE {seat.table} SET state = ?, status = ?, result = ? WHERE {seat.match} "
                          "AND state = ? AND attempt = ?", state, status, json.dumps(record, ensure_ascii=False),
                          *where.values(), RUNNING, attempt):
                tx.event(event_key, seat.done[state], **seat.label(where), attempt=attempt, status=status)
            else:
                tx.event(event_key, seat.ignored, **seat.label(where), attempt=attempt)


    def _acknowledge_seat(self, seat: "_Seat", event_key: str, where: dict) -> None:
        """사람이 그 호출의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않으며 답을 받지 않는다."""
        with self.runtime.lock, self.store.tx() as tx:
            if not tx.execute(f"UPDATE {seat.table} SET state = ?, status = 'unknown_acknowledged' WHERE {seat.match} "
                              "AND state = ?", REJECTED, *where.values(), UNKNOWN):
                raise ControllerError("only an attempt with unconfirmed termination can be acknowledged")
            tx.event(event_key, seat.acknowledged, **seat.label(where))
        self.pump()


    def acknowledge_synthesis_unknown(self, run_id: str, attempt: str) -> None:
        """사용자가 특정 합성 시도의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않는다."""
        with self.runtime.lock, self.store.tx() as tx:
            self.repository._run(run_id)
            item = self.invocations._synthesis_attempts(run_id).get((run_id, attempt))
            if item is None or item["status"] != UNKNOWN:
                raise ControllerError("only an unknown synthesis attempt can be acknowledged")
            tx.event(run_id, "synthesis_unknown_acknowledged", attempt=attempt)
        self.pump()


    def shutdown(self, timeout: float = runner.CLEANUP_LIMIT + 1.0) -> bool:
        """새 호출을 영구히 막고 소유한 초안·합성 실행기에 취소를 알린 뒤 결과 저장을 기다린다.

        실행 자체의 cancel_run과 다르다. 대기 시도·이미 공개한 답·예약은 보존한다. 다시 연 controller는 대기를
        사용자 resume 전까지 시작하지 않는다. True는 worker가 모두 반환했다는 뜻이지 자손 종료의 증거가 아니다.
        종료 미확인은 원장과 unsettled()에 남는다. False이면 호출자는 살아 있는 writer의 Store를 닫지 않는다.
        """
        if not math.isfinite(timeout) or timeout < 0:
            raise ValueError("shutdown timeout must be finite and non-negative")
        with self.runtime.lock:
            self.runtime.closing, self.runtime.paused = True, True
            for _, cancel in self.runtime.workers.values():
                cancel.set()
            for _, cancel, _ in self.runtime.syntheses.values():
                cancel.set()
            for _, cancel in self.runtime.upper_workers.values():
                cancel.set()
        # _finish와 finally가 같은 lock을 필요로 하므로 기다리는 동안 잡고 있지 않는다.
        return self.wait_idle(timeout)


    def wait_idle(self, timeout: float = 30.0) -> bool:
        """시작한 시도가 모두 반환했는지 본다. timeout=0은 기다리지 않고 현재 상태만 검사한다."""
        if not math.isfinite(timeout) or timeout < 0:
            raise ValueError("idle timeout must be finite and non-negative")
        deadline = time.monotonic() + timeout
        while True:
            with self.runtime.lock:
                if not self.runtime.workers and not self.runtime.syntheses and not self.runtime.upper_workers:
                    return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(0.05, remaining))
