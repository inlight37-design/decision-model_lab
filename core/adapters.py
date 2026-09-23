"""CLI별 argv 조립·옵션 검증·출력 해석·자식 환경. 표준 라이브러리만 쓴다.

argv는 허용된 조각으로만 만든다. 호출자가 임의 플래그를 덧붙일 길은 없다. 지금 지원하는
역할은 읽기 전용 논의자(discussant) 하나다. 쓰기 역할은 conformance를 본 뒤 따로 만든다.

판정 규칙(aux-pc V04-01 관측):
- Claude는 exit code와 `is_error`를 함께 본다. 실패 결과가 `subtype: "success"`를 단다(P2).
- Codex는 JSONL에서 `turn.completed`가 있어야 끝난 것이다. 모델 이름은 알려 주지 않는다(P1).
- agy는 `--output-format`의 없는 값을 조용히 무시하고 text로 답한다(P3). 값은 여기서 고정하고,
  JSON이 아니면 형식 실패다.
- 요청한 모델과 보고된 모델이 다르면 표시한다. 조용한 강등(D18)을 넘기지 않는다.
- 과금 경로를 바꾸는 환경변수는 자식에게 넘기지 않는다. 인증은 각 CLI가 가진 로그인을 쓴다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import re
import shutil
import subprocess
from typing import Any, Iterable, Mapping

from core.runner import EXITED, RunResult
from tools.runtime_inventory import ENV_VARS, fresh_environment

DISCUSSANT = "discussant"
ROLES = (DISCUSSANT,)


@dataclass(frozen=True)
class AdapterSpec:
    adapter_id: str
    command: str
    enabled_by_default: bool
    note: str


ADAPTERS: dict[str, AdapterSpec] = {
    "claude-code": AdapterSpec("claude-code", "claude", True,
                               "구독 로그인(claude.ai). 데스크톱 앱과 같은 한도를 쓴다(E04)."),
    "codex": AdapterSpec("codex", "codex", True, "ChatGPT 로그인. exec는 기본 read-only sandbox."),
    "antigravity": AdapterSpec(
        "antigravity", "agy", False,
        "사용자가 켜야 쓴다. 약관상 제3자 소프트웨어 구동에 해당하는지 불명확(F31) — 위험은 계정 제재."),
}

# 자식 환경에서 뺀다: 구독 대신 API 과금이나 다른 endpoint로 바꿀 수 있는 변수. 남기는 것은
# 설정 위치(CLAUDE_CONFIG_DIR, CODEX_HOME — 빼면 로그인을 못 찾는다)와 구독 토큰뿐이다.
KEEP_VARS = frozenset({"CLAUDE_CONFIG_DIR", "CODEX_HOME", "CLAUDE_CODE_OAUTH_TOKEN"})
BILLING_VARS = frozenset(name for name, _, _ in ENV_VARS) - KEEP_VARS

# 조립 결과에 나타나면 안 되는 플래그와 값. 조립 코드가 넣지 않지만, 누가 고쳐도 걸리게 한 번 더 본다.
FORBIDDEN: dict[str, frozenset[str]] = {
    "claude-code": frozenset({"--dangerously-skip-permissions", "--allow-dangerously-skip-permissions",
                              "--fallback-model", "--bare", "bypassPermissions", "acceptEdits",
                              "--settings", "--mcp-config", "--setting-sources"}),
    "codex": frozenset({"--dangerously-bypass-approvals-and-sandbox", "--dangerously-bypass-hook-trust",
                        "--approve-for-me", "--full-auto", "--yolo", "--oss", "--local-provider",
                        "-p", "--profile", "-c", "--config", "--enable", "--disable",
                        "workspace-write", "danger-full-access"}),
    "antigravity": frozenset({"--dangerously-skip-permissions", "--mode", "--remote-control",
                              "accept-edits"}),
}

MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}")
AGY_EFFORT = ("low", "medium", "high")
CLAUDE_CONTEXT = ("restricted", "safe_mode")  # 어느 쪽이 blind 입력을 막는지는 V04-03에서 관측
# Windows CreateProcess 명령줄 상한은 32,767자다. 여유를 둔다.
MAX_COMMAND_LINE = 30_000


class AdapterError(ValueError):
    """조립 전에 거절한 요청. 모델 호출은 일어나지 않았다."""


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise AdapterError(message)


def child_env(base: Mapping[str, str], *, machine: Mapping[str, str] | None = None,
              user: Mapping[str, str] | None = None) -> tuple[dict[str, str], list[str]]:
    """자식에게 줄 환경과, 뺀 과금 변수 이름을 돌려준다. 값은 기록하지 않는다.

    machine/user(레지스트리 값)를 주면 AI 도구가 셸에 넣은 변수를 먼저 정리한다(새 터미널 기준).
    """
    env = dict(base)
    if machine is not None or user is not None:
        env, _ = fresh_environment(base, machine or {}, user or {})
    dropped = sorted(name for name in env if name.upper() in BILLING_VARS)
    for name in dropped:
        del env[name]
    env["NO_COLOR"] = "1"
    return env, dropped


def resolve(command: str, env: Mapping[str, str]) -> str:
    """자식이 쓸 PATH로 실행 파일을 찾아 절대 경로로 돌려준다."""
    path = shutil.which(command, path=env.get("PATH") or env.get("Path"))
    _require(path is not None, f"{command} is not on the child PATH")
    return os.path.abspath(path)


def _check(adapter_id: str, argv: list[str], user_text: Iterable[int]) -> list[str]:
    skip = set(user_text)
    for index, token in enumerate(argv):
        if index in skip:
            continue
        _require(token not in FORBIDDEN[adapter_id], f"{adapter_id}: forbidden argument {token!r}")
    _require(len(subprocess.list2cmdline(argv)) <= MAX_COMMAND_LINE,
             "command line too long; pass the material as a file instead")
    return argv


def build_argv(adapter_id: str, *, exe: str, prompt: str, model: str, role: str = DISCUSSANT,
               enabled: bool | None = None, read_dirs: Iterable[str] = (),
               claude_context: str = "restricted", effort: str | None = None) -> list[str]:
    """읽기 전용 논의자 한 번의 argv. 허용된 조각 밖의 옵션은 받지 않는다."""
    _require(adapter_id in ADAPTERS, f"unknown adapter {adapter_id!r}")
    spec = ADAPTERS[adapter_id]
    _require(spec.enabled_by_default if enabled is None else enabled is True,
             f"{adapter_id} is off; the user has to turn it on ({spec.note})")
    _require(role in ROLES, f"unsupported role {role!r}")
    _require(isinstance(exe, str) and os.path.isabs(exe), "exe must be an absolute path")
    _require(isinstance(prompt, str) and prompt.strip() != "", "prompt must be non-empty text")
    _require(isinstance(model, str) and MODEL.fullmatch(model) is not None,
             "model must be named explicitly; there is no default and no fallback")
    dirs = [str(d) for d in read_dirs]
    _require(all(os.path.isabs(d) for d in dirs), "read_dirs must be absolute paths")

    if adapter_id == "claude-code":
        _require(claude_context in CLAUDE_CONTEXT, f"claude_context must be one of {CLAUDE_CONTEXT}")
        _require(effort is None, "effort is not wired for claude-code yet")
        argv = [exe, "-p", prompt, "--output-format", "json", "--model", model,
                "--permission-mode", "dontAsk", "--no-session-persistence",
                "--strict-mcp-config", "--disable-slash-commands",
                "--restricted" if claude_context == "restricted" else "--safe-mode"]
        for d in dirs:
            argv += ["--add-dir", d]
        argv += ["--tools", "Read" if dirs else ""]
        return _check(adapter_id, argv, user_text=(2,))
    if adapter_id == "codex":
        _require(effort is None and not dirs, "codex discussant takes no effort or extra dirs yet")
        argv = [exe, "exec", "--json", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config",
                "--ignore-rules", "--sandbox", "read-only", "--model", model, prompt]
        return _check(adapter_id, argv, user_text=(len(argv) - 1,))
    _require(effort is None or effort in AGY_EFFORT, f"effort must be one of {AGY_EFFORT}")
    argv = [exe, "-p", prompt, "--output-format", "json", "--model", model, "--sandbox",
            "--disable-slash-commands"]
    for d in dirs:
        argv += ["--add-dir", d]
    if effort:
        argv += ["--effort", effort]
    return _check(adapter_id, argv, user_text=(2,))


@dataclass(frozen=True)
class Outcome:
    """한 호출의 의미 판정. ok는 '요청한 형식의 답을 오류 없이 받았다'까지만 뜻한다."""
    adapter_id: str
    ok: bool
    status: str                       # ok | cli_error | format_error | process_<runner state>
    text: str | None
    requested_model: str
    reported_models: tuple[str, ...]  # 비어 있으면 CLI가 알리지 않았다
    model_match: bool | None          # None: 비교할 보고가 없다
    usage: dict[str, Any] = field(default_factory=dict)
    permission_denials: int | None = None
    tool_events: int | None = None
    detail: str | None = None


def _usage(source: Mapping[str, Any] | None, keys: Iterable[str]) -> dict[str, Any]:
    return {k: source[k] for k in keys if isinstance(source, Mapping) and isinstance(source.get(k), (int, float))}


def _model_match(requested: str, reported: tuple[str, ...]) -> bool | None:
    return None if not reported else requested in reported


def _single_json(stdout: str) -> dict | None:
    try:
        value = json.loads(stdout.strip())
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def interpret(adapter_id: str, run: RunResult, *, requested_model: str) -> Outcome:
    """실행 결과를 의미로 바꾼다. 프로세스가 끝났다고 확인되지 않으면 답이 보여도 성공이 아니다."""
    _require(adapter_id in ADAPTERS, f"unknown adapter {adapter_id!r}")
    base = dict(adapter_id=adapter_id, requested_model=requested_model)
    if run.state != EXITED:
        return Outcome(ok=False, status=f"process_{run.state}", text=run.stdout or None,
                       reported_models=(), model_match=None, detail=run.error, **base)
    if run.stdout_truncated:
        return Outcome(ok=False, status="format_error", text=None, reported_models=(), model_match=None,
                       detail="stdout exceeded the runner limit", **base)
    if adapter_id == "claude-code":
        obj = _single_json(run.stdout)
        if obj is None or obj.get("type") != "result":
            return Outcome(ok=False, status="format_error", text=run.stdout or None, reported_models=(),
                           model_match=None, detail="expected one JSON result object", **base)
        models = tuple(sorted((obj.get("modelUsage") or {}).keys()))
        usage = _usage(obj.get("usage"), ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                                          "cache_read_input_tokens"))
        if isinstance(obj.get("total_cost_usd"), (int, float)):
            usage["client_estimate_usd"] = obj["total_cost_usd"]  # 정가 기준 추정. 청구액이 아니다
        ok = run.exit_code == 0 and obj.get("is_error") is False and isinstance(obj.get("result"), str)
        return Outcome(ok=ok, status="ok" if ok else "cli_error", text=obj.get("result"),
                       reported_models=models, model_match=_model_match(requested_model, models),
                       usage=usage, permission_denials=len(obj.get("permission_denials") or []),
                       detail=None if ok else str(obj.get("terminal_reason") or "is_error"), **base)
    if adapter_id == "codex":
        text, completed, failure, tools, usage, stray = None, False, None, 0, {}, 0
        for line in run.stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                stray += bool(line)
                continue
            try:
                event = json.loads(line)
            except ValueError:
                return Outcome(ok=False, status="format_error", text=None, reported_models=(),
                               model_match=None, detail="broken JSONL line", **base)
            kind = event.get("type")
            item = event.get("item") or {}
            if kind == "item.completed" and item.get("type") == "agent_message":
                text = item.get("text")
            elif kind == "item.completed":
                tools += 1
            elif kind == "turn.completed":
                completed = True
                usage = _usage(event.get("usage"), ("input_tokens", "cached_input_tokens", "output_tokens",
                                                    "reasoning_output_tokens"))
            elif kind in ("turn.failed", "error"):
                failure = str((event.get("error") or {}).get("message") or event.get("message") or kind)
        ok = run.exit_code == 0 and completed and failure is None and isinstance(text, str)
        if not ok and failure is None and not completed:
            status = "format_error" if run.exit_code == 0 else "cli_error"
        else:
            status = "ok" if ok else "cli_error"
        return Outcome(ok=ok, status=status, text=text, reported_models=(), model_match=None, usage=usage,
                       tool_events=tools, detail=failure or (f"{stray} non-JSON line(s)" if stray else None),
                       **base)
    obj = _single_json(run.stdout)
    if obj is None:
        return Outcome(ok=False, status="format_error", text=run.stdout or None, reported_models=(),
                       model_match=None, detail="requested JSON but got text (agy ignores bad formats, P3)",
                       **base)
    models = (obj["model"],) if isinstance(obj.get("model"), str) else ()
    ok = run.exit_code == 0 and obj.get("status") == "SUCCESS" and isinstance(obj.get("response"), str)
    return Outcome(ok=ok, status="ok" if ok else "cli_error", text=obj.get("response"),
                   reported_models=models, model_match=_model_match(requested_model, models),
                   usage=_usage(obj.get("usage"), ("input_tokens", "output_tokens", "thinking_tokens",
                                                   "cache_read_tokens")),
                   detail=None if ok else str(obj.get("status")), **base)
