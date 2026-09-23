"""CLI별 argv 조립·옵션 검증·출력 해석·자식 환경. 표준 라이브러리만 쓴다.

argv는 허용된 조각으로만 만든다. 호출자가 임의 플래그를 덧붙일 길은 없다. 지금 지원하는
역할은 읽기 전용 논의자(discussant) 하나다. 쓰기 역할은 conformance를 본 뒤 따로 만든다.

판정 규칙(aux-pc V04-01 관측):
- Claude는 exit code와 `is_error`를 함께 본다. 실패 결과가 `subtype: "success"`를 단다(P2).
- Codex는 JSONL에서 `turn.completed`가 있어야 끝난 것이다. 모델 이름은 알려 주지 않는다(P1).
- agy는 `--output-format`의 없는 값을 조용히 무시하고 text로 답한다(P3). 값은 여기서 고정하고,
  JSON이 아니면 형식 실패다.
- 요청한 모델과 보고된 모델이 다르면 표시한다(model_match=False). 조용한 강등(D18)을 넘기지 않도록 A1의
  결과 수용 관문이 그 답을 받지 않는다. Claude는 전체 모델 이름을 보고했으므로(aux-pc tier 2) 별칭으로
  요청하면 달라 보일 수 있다 — 요청은 전체 이름으로 한다.
- 과금 경로를 바꾸는 환경변수는 자식에게 넘기지 않는다. 인증은 각 CLI가 가진 로그인을 쓴다
  (core/env.py).
- 질문 본문은 명령줄이 아니라 stdin으로 보낸다(ExecutionSpec, 경계 리뷰 R06). agy만 stdin 입력을
  확인하지 못해 명령줄로 보낸다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
import re
import subprocess
from typing import Any, Iterable, Mapping

from core.env import BILLING_VARS, KEEP_VARS, child_env, resolve  # noqa: F401 — 호출자가 여기서 쓴다
from core.runner import EXITED, INPUT_COMPLETE, RunResult

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

# Codex에 허용하는 설정 덮어쓰기는 이것 하나다. Windows에서 --ignore-user-config는 데스크톱 앱이
# 사용자 설정에 적은 `[windows] sandbox = "elevated"`까지 버려서, 샌드박스가 없는 exec가 모든 명령을
# "blocked by policy"로 거절하고도 exit 0으로 답한다(openai/codex#42172, 0.152부터; aux-pc 0.155.1에서
# 재현하고 이 덮어쓰기로 풀리는 것을 관측).
CODEX_WINDOWS_SANDBOX = 'windows.sandbox="elevated"'
CODEX_ALLOWED_CONFIG = frozenset({CODEX_WINDOWS_SANDBOX})
CODEX_REJECTED = "rejected: blocked by policy"
MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}")
AGY_EFFORT = ("low", "medium", "high")
CLAUDE_CONTEXT = ("restricted", "safe_mode")  # 어느 쪽이 blind 입력을 막는지는 V04-03에서 관측
# Windows CreateProcess 명령줄 상한은 32,767자다. 여유를 둔다.
MAX_COMMAND_LINE = 30_000
# Claude Code 문서: 파이프로 받는 stdin은 10MB까지이고 넘으면 비영 종료한다(2026-09-23 확인).
CLAUDE_MAX_STDIN = 10_000_000
STDIN, ARGV = "stdin", "argv"


class AdapterError(ValueError):
    """조립 전에 거절한 요청. 모델 호출은 일어나지 않았다."""


@dataclass(frozen=True)
class ExecutionSpec:
    """한 번의 실행. 질문 본문은 argv에 넣지 않고 stdin으로 보낸다(경계 리뷰 R06).

    명령줄에 넣으면 Linux는 인자 하나가 약 128KiB를 넘을 때 실행 자체가 실패하고, 같은 사용자의
    다른 프로세스가 /proc/<pid>/cmdline에서 읽을 수 있으며, `-`로 시작하는 질문이 옵션으로 읽힐 수
    있다. argv에는 옵션만 있으므로(agy 제외) 그대로 기록해도 되고, 입력은 digest와 크기만 기록한다.
    cwd·환경·격리는 controller가 정한다.
    """
    adapter_id: str
    argv: tuple[str, ...]
    stdin_text: str | None
    input_via: str        # STDIN | ARGV — agy는 stdin 입력을 확인하지 못해 ARGV다(B4)
    input_sha256: str
    input_bytes: int

    def record(self) -> dict[str, Any]:
        """기록·표시용 사본. 질문 본문은 넣지 않고 digest와 크기만 둔다(WSL2 리뷰 WM-02).

        repr()도 이것을 쓴다. dataclasses.asdict()에는 본문이 들어간다 — 기록에 쓰지 않는다. agy처럼
        질문이 argv에 있으면 그 자리를 digest 표시로 바꾼다.
        """
        mask = f"<input sha256:{self.input_sha256}>"
        argv = [mask if hashlib.sha256(a.encode("utf-8")).hexdigest() == self.input_sha256 else a
                for a in self.argv]
        return {"adapter_id": self.adapter_id, "argv": argv, "input_via": self.input_via,
                "input_sha256": self.input_sha256, "input_bytes": self.input_bytes}

    def __repr__(self) -> str:
        return f"ExecutionSpec({self.record()!r})"


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise AdapterError(message)


def _check(adapter_id: str, argv: list[str], user_text: Iterable[int]) -> list[str]:
    skip = set(user_text)
    for index, token in enumerate(argv):
        if index in skip:
            continue
        if (adapter_id == "codex" and token == "-c" and index + 1 < len(argv)
                and argv[index + 1] in CODEX_ALLOWED_CONFIG):
            skip.add(index + 1)
            continue
        _require(token not in FORBIDDEN[adapter_id], f"{adapter_id}: forbidden argument {token!r}")
    _require(len(subprocess.list2cmdline(argv)) <= MAX_COMMAND_LINE, "command line too long")
    return argv


def build_spec(adapter_id: str, *, exe: str, prompt: str, model: str, role: str = DISCUSSANT,
               enabled: bool | None = None, read_dirs: Iterable[str] = (),
               claude_context: str = "restricted", effort: str | None = None,
               codex_windows_sandbox: bool = False) -> ExecutionSpec:
    """읽기 전용 논의자 한 번의 실행 명세. 허용된 조각 밖의 옵션은 받지 않는다.

    codex_windows_sandbox: Windows에서 Codex의 elevated 샌드박스를 명시한다(`codex doctor`가
    `sandbox backend elevated`, `provisioning complete`를 보일 때). 주의: Codex의 read-only
    샌드박스는 쓰기를 막을 뿐 **작업 폴더 밖 읽기를 막지 않는다**(aux-pc 관측) — blind 격리는
    이것으로 성립하지 않는다.
    """
    _require(adapter_id in ADAPTERS, f"unknown adapter {adapter_id!r}")
    spec = ADAPTERS[adapter_id]
    _require(spec.enabled_by_default if enabled is None else enabled is True,
             f"{adapter_id} is off; the user has to turn it on ({spec.note})")
    _require(role in ROLES, f"unsupported role {role!r}")
    _require(adapter_id == "codex" or codex_windows_sandbox is False,
             "codex_windows_sandbox applies to codex only")
    _require(isinstance(exe, str) and os.path.isabs(exe), "exe must be an absolute path")
    _require(isinstance(prompt, str) and prompt.strip() != "", "prompt must be non-empty text")
    _require(isinstance(model, str) and MODEL.fullmatch(model) is not None,
             "model must be named explicitly; there is no default and no fallback")
    dirs = [str(d) for d in read_dirs]
    _require(all(os.path.isabs(d) for d in dirs), "read_dirs must be absolute paths")
    data = prompt.encode("utf-8")

    def spec(argv: list[str], via: str) -> ExecutionSpec:
        return ExecutionSpec(adapter_id, tuple(argv), prompt if via == STDIN else None, via,
                             hashlib.sha256(data).hexdigest(), len(data))

    if adapter_id == "claude-code":
        _require(claude_context in CLAUDE_CONTEXT, f"claude_context must be one of {CLAUDE_CONTEXT}")
        _require(effort is None, "effort is not wired for claude-code yet")
        _require(len(data) <= CLAUDE_MAX_STDIN, "prompt exceeds the 10MB stdin limit of claude -p")
        # 위치 인자 없이 -p만 주면 질문을 stdin에서 읽는다.
        argv = [exe, "-p", "--output-format", "json", "--model", model,
                "--permission-mode", "dontAsk", "--no-session-persistence",
                "--strict-mcp-config", "--disable-slash-commands",
                "--restricted" if claude_context == "restricted" else "--safe-mode"]
        for d in dirs:
            argv += ["--add-dir", d]
        argv += ["--tools", "Read" if dirs else ""]
        return spec(_check(adapter_id, argv, user_text=()), STDIN)
    if adapter_id == "codex":
        _require(effort is None and not dirs, "codex discussant takes no effort or extra dirs yet")
        _require(type(codex_windows_sandbox) is bool, "codex_windows_sandbox must be a boolean")
        argv = [exe, "exec", "--json", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config",
                "--ignore-rules", "--sandbox", "read-only"]
        if codex_windows_sandbox:
            argv += ["-c", CODEX_WINDOWS_SANDBOX]
        # `-`: 지시문을 stdin에서 읽는다(codex exec --help, aux-pc 0.155.1 기록).
        argv += ["--model", model, "-"]
        return spec(_check(adapter_id, argv, user_text=()), STDIN)
    _require(effort is None or effort in AGY_EFFORT, f"effort must be one of {AGY_EFFORT}")
    argv = [exe, "-p", prompt, "--output-format", "json", "--model", model, "--sandbox",
            "--disable-slash-commands"]
    for d in dirs:
        argv += ["--add-dir", d]
    if effort:
        argv += ["--effort", effort]
    return spec(_check(adapter_id, argv, user_text=(2,)), ARGV)


@dataclass(frozen=True)
class Outcome:
    """한 호출의 의미 판정. ok는 '요청한 형식의 답을 오류 없이 받았다'까지만 뜻한다."""
    adapter_id: str
    ok: bool
    status: str                       # ok | cli_error | format_error | input_error | tools_rejected | process_<runner state>
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
    """실행 결과를 의미로 바꾼다. 프로세스가 끝났다고 확인되지 않으면 답이 보여도 성공이 아니다.

    CLI 출력은 외부 입력이다. 문법이 맞는 JSON이어도 중첩 값의 타입이 다르면 예외 대신
    형식 실패로 돌려준다(경계 리뷰 R04).
    """
    _require(adapter_id in ADAPTERS, f"unknown adapter {adapter_id!r}")
    base = dict(adapter_id=adapter_id, requested_model=requested_model)
    if run.state != EXITED:
        return Outcome(ok=False, status=f"process_{run.state}", text=run.stdout or None,
                       reported_models=(), model_match=None, detail=run.error, **base)
    if run.input_delivery not in (None, INPUT_COMPLETE):
        # 질문을 다 보내지 못했다. 답이 그럴듯해도 받지 않는다(WSL2 리뷰 WM-01). 다시 부르지도 않는다.
        return Outcome(ok=False, status="input_error", text=run.stdout or None, reported_models=(),
                       model_match=None, detail=f"stdin {run.input_delivery}", **base)
    if run.stdout_truncated:
        return Outcome(ok=False, status="format_error", text=None, reported_models=(), model_match=None,
                       detail="stdout exceeded the runner limit", **base)
    try:
        return _parse(adapter_id, run, base)
    except (AttributeError, TypeError, KeyError, RecursionError, _Shape) as exc:
        # RecursionError: 문법은 맞지만 아주 깊게 중첩된 JSON(WSL2 리뷰 WM-06)
        return Outcome(ok=False, status="format_error", text=None, reported_models=(), model_match=None,
                       detail=f"unexpected output shape ({exc if isinstance(exc, _Shape) else type(exc).__name__})",
                       **base)


class _Shape(ValueError):
    """출력의 중첩 값이 예상한 타입이 아니다."""


def _typed(obj: Mapping[str, Any], key: str, kind: type, default: Any) -> Any:
    """obj[key]가 없거나 null이면 default, 있으면 kind여야 한다. 빈 값과 잘못된 타입을 구분한다."""
    value = obj.get(key)
    if value is None:
        return default
    if not isinstance(value, kind):
        raise _Shape(f"{key} is {type(value).__name__}")
    return value


def _parse(adapter_id: str, run: RunResult, base: dict[str, str]) -> Outcome:
    requested_model = base["requested_model"]
    if adapter_id == "claude-code":
        obj = _single_json(run.stdout)
        if obj is None or obj.get("type") != "result":
            return Outcome(ok=False, status="format_error", text=run.stdout or None, reported_models=(),
                           model_match=None, detail="expected one JSON result object", **base)
        models = tuple(sorted(_typed(obj, "modelUsage", Mapping, {}).keys()))
        usage = _usage(obj.get("usage"), ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                                          "cache_read_input_tokens"))
        if isinstance(obj.get("total_cost_usd"), (int, float)):
            usage["client_estimate_usd"] = obj["total_cost_usd"]  # 정가 기준 추정. 청구액이 아니다
        ok = run.exit_code == 0 and obj.get("is_error") is False and isinstance(obj.get("result"), str)
        return Outcome(ok=ok, status="ok" if ok else "cli_error", text=obj.get("result"),
                       reported_models=models, model_match=_model_match(requested_model, models),
                       usage=usage, permission_denials=len(_typed(obj, "permission_denials", list, [])),
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
            item = _typed(event, "item", Mapping, {})
            if kind == "item.completed" and item.get("type") == "agent_message":
                text = item.get("text")
            elif kind == "item.completed":
                tools += 1
            elif kind == "turn.completed":
                completed = True
                usage = _usage(event.get("usage"), ("input_tokens", "cached_input_tokens", "output_tokens",
                                                    "reasoning_output_tokens"))
            elif kind in ("turn.failed", "error"):
                error = event.get("error")
                error = error.get("message") if isinstance(error, Mapping) else error
                failure = str(error or event.get("message") or kind)
        # 명령이 거절되면 JSONL에는 흔적이 없고 stderr에만 남는다. 그래도 exit 0으로 답이 나오므로
        # (openai/codex#42172) 읽지 못한 채 쓴 답을 성공으로 넘기지 않는다. stderr가 잘렸으면
        # 거절이 없었다고 말할 수 없다(경계 리뷰 R04).
        if run.stderr_truncated:
            return Outcome(ok=False, status="format_error", text=text, reported_models=(), model_match=None,
                           usage=usage, tool_events=tools,
                           detail="stderr exceeded the runner limit; rejected commands may be hidden", **base)
        rejected = run.stderr.count(CODEX_REJECTED)
        ok = run.exit_code == 0 and completed and failure is None and isinstance(text, str) and not rejected
        if rejected:
            status, failure = "tools_rejected", f"{rejected} command(s) rejected by policy before running"
        elif not ok and failure is None and not completed:
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
