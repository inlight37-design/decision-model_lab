"""Post-reveal synthesis commands with common input, budget and runtime contracts."""
from __future__ import annotations
from dataclasses import replace
import json
import os
import uuid
from app.report import build_report
from app.synthesis import LABEL_ORDER, SynthesisError, mock_synthesize, model_prompt, unavailable
from app.state import CLI, UNKNOWN
from core import contract
from app.domain import ParticipantSpec, ControllerError
from app.execution.executor import _check


class SynthesisService:
    def __init__(self, runtime, execution, inputs, invocations, queries, repository):
        self.runtime = runtime
        self.store = runtime.store
        self.execution = execution
        self.inputs = inputs
        self.invocations = invocations
        self.queries = queries
        self.repository = repository

    def synthesize(self, run_id: str) -> None:
        """One offline post-reveal transition. Persist once; failure keeps the draft report."""
        with self.runtime.lock, self.store.tx() as tx:
            self.repository._check_role_synthesizer(run_id)
            if not self.repository._gate(run_id).public()["can_synthesize"]:
                raise ControllerError("mock synthesis requires controller-revealed drafts")
            if self.store.row("SELECT 1 FROM events WHERE run_id = ? AND kind = 'synthesis_completed'", run_id):
                return
            report = build_report(self.queries.view(run_id), run_id)
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
        with self.runtime.lock:
            fixed = self.repository._check_role_synthesizer(run_id, adapter_id)
            if fixed is not None:
                spec = ParticipantSpec(**fixed)
            if self.runtime.closing:
                raise ControllerError("controller is shutting down")
            if not self.repository._gate(run_id).public()["can_synthesize"]:
                raise ControllerError("model synthesis requires controller-revealed drafts")
            if run_id in self.runtime.syntheses:
                raise ControllerError("a model synthesis is already running for this run")
            if any(item["status"] == UNKNOWN for item in self.invocations._synthesis_attempts(run_id).values()):
                # 끝났는지 모르는 합성이 남아 있으면 새로 부르지 않는다. 사용자가 종료를 확인하면 다시 부를 수 있다.
                raise ControllerError("an earlier synthesis attempt has unconfirmed termination; acknowledge it first; "
                                      "no new call was started")
            if self.runtime.paused or self.invocations.unsettled() >= self.runtime.unsettled_limit:
                raise ControllerError("execution is paused or has unsettled attempts; no call was started")
            if self.invocations._slots_used() >= self.runtime.max_parallel:
                raise ControllerError("parallel execution limit reached; no call was started")
            chosen = next((spec for spec in (ParticipantSpec(**json.loads(row["spec"])) for row in self.store.rows(
                "SELECT spec FROM participants WHERE run_id = ? ORDER BY rowid", run_id))
                if spec.transport == CLI and spec.adapter_id == adapter_id), None)
            if chosen is None and spec is not None and spec.transport == CLI and spec.adapter_id == adapter_id:
                chosen = spec   # 이 실행의 참여자가 아니어도 서버에 설정된 CLI provider면 합성자가 될 수 있다
            if chosen is None or adapter_id not in self.runtime.executor.adapter_ids:
                raise ControllerError("the synthesizer must be a configured CLI provider")
            report = build_report(self.queries.view(run_id), run_id)
            try:
                prompt, labels, nonce = model_prompt(report)
                prompt += self.inputs._run_memory(self.repository._run(run_id))
            except SynthesisError as exc:
                raise ControllerError(str(exc)) from None
            attempt = uuid.uuid4().hex
            work = os.path.join(self.runtime.work_root, run_id, f"synthesis-{attempt[:12]}")
            try:
                # 폴더 준비 실패도 계획 거절처럼 요청 거절로 돌려준다 — 파일 시스템 예외를 API 밖으로 흘리지 않는다(AH-02).
                os.makedirs(work, exist_ok=True)
                source = self.inputs._source_dir(run_id)
                plan = self.runtime.executor.plan(replace(chosen, pid="synthesis", label="합성"), prompt, work,
                                          **({"inputs": (source,)} if source else {}))
                _check(self.runtime.executor, plan)   # 예약 전에 격리 경로·연결을 본다(R4)
            except ControllerError:
                raise
            except Exception as exc:  # 계획 거절: 아무것도 시작하지 않았다
                raise ControllerError(f"synthesis plan refused: {type(exc).__name__}: {exc}") from None
            with self.store.tx() as tx:
                if plan.kind == contract.REAL and self.runtime.max_real_calls is not None:
                    if self.invocations._budget_exhausted(adapter_id):
                        raise ControllerError("real CLI call budget exhausted; no call was started")
                    self.invocations.reserve(tx, run_id, pid="synthesis", attempt=attempt,
                                             adapter_id=adapter_id, purpose="synthesis")
                tx.event(run_id, "synthesis_started", attempt=attempt, adapter_id=adapter_id, execution=plan.kind,
                         labels=labels, label_order=LABEL_ORDER, boundary=nonce, spec=plan.record())
            self.execution.start_synthesis(run_id, attempt, plan, report, labels)
