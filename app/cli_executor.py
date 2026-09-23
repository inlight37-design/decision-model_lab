"""실제 CLI 실행기(인계 4절 N1). **모델을 부른다 — 사용자 승인 뒤에만 쓴다.** Linux·WSL 전용(2절 15).

한 시도의 흐름: env.resolve → adapters.build_spec → isolation.run(cli_mounts, never) → adapters.interpret.
결과를 받을지는 controller의 수용 관문이 정한다(입력 전달, 빈 답, 모델 불일치, 자손 전체 종료).

- 질문은 stdin으로만 보낸다. 질문을 명령줄로 보내는 agy는 받지 않는다 — 꺼 두었고(2절 19) 그 전송의 증거를
  아직 정하지 않았다(K07).
- 실행 명세는 describe()가 ExecutionSpec.record()로 돌려주고, controller가 시도 ID와 함께 journal에 남긴다.
  질문 본문과 원문 argv는 남기지 않는다.
- 모델은 전체 이름으로 요청한다. 별칭이면 보고된 이름과 달라 model_mismatch가 된다(K43).
- 격리 안의 HOME은 실제 HOME 경로의 빈 tmpfs이고, 그 CLI 자신의 설정·인증 폴더만 쓰기로 연결한다(cli_mounts).
- 프로세스를 만들기 전에 거절하면(실행 파일 없음, 금지 옵션, 경로 충돌, 모델 이름 없음) failed_to_start로
  돌려준다. 아무것도 시작하지 않았으므로 unknown이 아니다.
- Codex의 명령 거절 표식은 보관 상한과 상관없이 stderr 전체에서 센다(K02).
- Codex에는 `--sandbox read-only` 대신 로그인 파일(`~/.codex/auth.json`)만 읽기 금지한 권한 profile을 준다(K46).
  exec에서 그 금지가 지켜지는지는 아직 관측하지 않았다.
- **실행 허가는 시도마다 계산한다(N4).** 기록(`runtime-inventory/2`)의 다섯 칸이 모두 관측됐고, 지금 설치된 버전이
  기록과 같고, 구독 로그인일 때만 부른다(core.eligibility). 기록 없이 부르는 것은 관측 도구와 시험뿐이다(unchecked).

서버(app.server)는 아직 이 실행기를 쓰지 않는다. 모의 실행기만 쓴다.
"""
from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import re
from typing import Mapping, Sequence

from core import adapters, eligibility, env as core_env, isolation, runner

SUPPORTED = ("claude-code", "codex")
# 격리 안으로 넘기는 변수. 나머지는 isolation.PASS_ENV가 거른다(W2 시험과 같은 값).
SANDBOX_ENV = {"LANG": "C.UTF-8", "NO_COLOR": "1"}
REFUSED_BEFORE_START = (adapters.AdapterError, core_env.EnvError, isolation.IsolationError, runner.RunnerError)


def installed_version(adapter_id: str, exe: str) -> str | None:
    """실행 파일의 실제 위치에서 버전을 읽는다. 프로세스를 띄우지 않는다. 공식 설치 모양을 따른다:
    Claude는 …/claude/versions/<버전>, Codex는 …/releases/<버전>-<대상>/bin/codex. 모양이 다르면 None."""
    real = os.path.realpath(exe)
    if adapter_id == "claude-code":
        name = os.path.basename(real)
    elif adapter_id == "codex":
        name = os.path.basename(os.path.dirname(os.path.dirname(real))).split("-", 1)[0]
    else:
        return None
    return name if re.fullmatch(r"\d+(?:\.\d+)+", name) else None


class CliExecutor:
    name = "cli"

    def __init__(self, *, never: Sequence[str], inventory: str | Path | None = None, unchecked: bool = False,
                 home: str | None = None, base_env: Mapping[str, str] | None = None,
                 max_output_bytes: int = runner.DEFAULT_MAX_OUTPUT) -> None:
        """never: 참여자에게 보이면 안 되는 경로(controller 데이터 폴더). inventory: 이 기기의 `runtime-inventory/2`
        기록 — 시도마다 다시 읽어 실행 허가를 계산한다. unchecked: 허가를 계산하지 않는다(관측 도구·시험만).
        base_env: 실행 파일을 찾을 환경."""
        if inventory is None and not unchecked:
            raise ValueError("the real CLI executor needs a runtime-inventory/2 record (inventory=...); "
                             "only observation tools and tests run it unchecked")
        self.never = tuple(never)
        self.inventory = None if inventory is None else Path(inventory)
        self.home = home or os.path.expanduser("~")
        self.child_env, _ = core_env.child_env(os.environ if base_env is None else base_env)
        self.max_output_bytes = max_output_bytes

    def _check_eligible(self, adapter_id: str, exe: str) -> None:
        if self.inventory is None:
            return
        try:
            record = eligibility.load(self.inventory)
        except (OSError, ValueError) as exc:
            raise adapters.AdapterError(f"cannot read the inventory: {type(exc).__name__}") from None
        verdict = eligibility.eligibility(record, adapter_id, enabled=True, today=date.today(),
                                          current_version=installed_version(adapter_id, exe))
        if not verdict.eligible:
            raise adapters.AdapterError("not eligible to run: " + "; ".join(verdict.reasons))

    def _plan(self, spec, prompt: str, inputs: Sequence[str] = ()) -> adapters.ExecutionSpec:
        if spec.adapter_id not in SUPPORTED:
            raise adapters.AdapterError(f"{spec.adapter_id!r} is not run by the CLI executor")
        exe = core_env.resolve(adapters.ADAPTERS[spec.adapter_id].command, self.child_env)
        self._check_eligible(spec.adapter_id, exe)
        # Claude는 읽을 폴더를 --add-dir로 알려 주고 Read 도구만 준다. Codex에는 그런 옵션을 주지 않는다 —
        # 격리 안에 읽기 전용으로 보이는 것만 읽을 수 있다. 대신 Codex의 명령이 자기 로그인 파일을 읽지 못하게
        # 권한 profile을 준다(K46). 격리 안의 HOME은 실제 경로다(isolation.plan).
        if spec.adapter_id == "claude-code":
            return adapters.build_spec(spec.adapter_id, exe=exe, prompt=prompt, model=spec.model or "",
                                       read_dirs=tuple(inputs))
        return adapters.build_spec(spec.adapter_id, exe=exe, prompt=prompt, model=spec.model or "",
                                   codex_user_home=os.path.realpath(self.home))

    def prepare(self, spec, prompt: str, work_dir: str, *,
                inputs: Sequence[str] = ()) -> tuple[adapters.ExecutionSpec, isolation.Sandbox]:
        """실행 명세와 격리 경계. inputs: 참여자에게 읽기 전용으로 보일 공통 자료 폴더(절대 경로).
        관측 도구(tools/w2/observe.py)도 이것을 써서 참여자와 같은 경로로 부른다."""
        planned = self._plan(spec, prompt, inputs)
        ro, rw = isolation.cli_mounts(spec.adapter_id, planned.argv[0], self.home)
        box = isolation.Sandbox(work_dir=work_dir, home=self.home, read_only=ro + tuple(inputs), read_write=rw,
                                env=SANDBOX_ENV, never=self.never)
        return planned, box

    def describe(self, spec, prompt: str) -> dict:
        """journal에 남길 실행 명세. 질문 본문 없이 digest와 크기만 있다. 거절되면 그 이유를 남긴다."""
        try:
            return self._plan(spec, prompt).record()
        except REFUSED_BEFORE_START as exc:
            return {"adapter_id": spec.adapter_id, "refused": f"{type(exc).__name__}: {exc}"}

    def execute(self, spec, prompt: str, work_dir: str, timeout: float):
        try:
            planned, box = self.prepare(spec, prompt, work_dir)
            result = isolation.run(list(planned.argv), box, timeout=timeout, stdin_text=planned.stdin_text,
                                   max_output_bytes=self.max_output_bytes,
                                   stderr_marks=adapters.STDERR_MARKS.get(spec.adapter_id, ()))
        except REFUSED_BEFORE_START as exc:
            result = runner.RunResult((), runner.FAILED_TO_START, None, "", "", False, False, 0, None, True,
                                      error=f"{type(exc).__name__}: {exc}")
        return result, adapters.interpret(spec.adapter_id, result, requested_model=spec.model or "")
