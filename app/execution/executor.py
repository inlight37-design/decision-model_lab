"""Native execution port and explicit no-model executor."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import sys
import threading
from typing import Protocol
from core import adapters, contract, env as core_env, isolation, runner
from app.domain import ParticipantSpec

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

    SCRIPT = str(Path(__file__).resolve().parents[1] / "fake_cli.py")
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
