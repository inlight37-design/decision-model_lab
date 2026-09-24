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
                        "-p", "--profile", "-P", "--permission-profile", "-c", "--config", "--enable", "--disable",
                        "workspace-write", "danger-full-access"}),
    "antigravity": frozenset({"--dangerously-skip-permissions", "--mode", "--remote-control",
                              "accept-edits"}),
}

# Codex에 허용하는 설정 덮어쓰기는 두 경우뿐이고, 실행마다 그 값만 통과시킨다(_check의 config).
# Windows: --ignore-user-config는 데스크톱 앱이 사용자 설정에 적은 `[windows] sandbox = "elevated"`까지 버려서,
# 샌드박스가 없는 exec가 모든 명령을 "blocked by policy"로 거절하고도 exit 0으로 답한다(openai/codex#42172,
# 0.152부터; aux-pc 0.155.1에서 재현하고 이 덮어쓰기로 풀리는 것을 관측).
CODEX_WINDOWS_SANDBOX = 'windows.sandbox="elevated"'
# Linux(K46): read-only 샌드박스 안의 명령이 Codex 로그인 파일을 읽을 수 있었다(2026-09-24 `codex sandbox` 진단).
# 옛 `--sandbox read-only` 대신, 읽기 전용 기본 profile에 그 파일 하나의 읽기 금지를 더한 이름 있는 권한
# profile을 준다(베타, https://learn.chatgpt.com/docs/permissions — 옛 sandbox 설정과 섞지 말라고 한다).
# exec에는 `-P`가 없어서(0.156.1이 인자 오류로 거절) `default_permissions`로 고른다. `~/.codex` 전체를 막으면
# Codex의 샌드박스 보조 프로그램이 그 아래의 codex를 다시 실행하지 못한다(같은 진단).
# 참여자 실행 명세의 판은 core.contract가 최종 계획(argv·연결·변형)에서 계산한다. 손으로 올리던 이름 판
# (claude discussant-1, codex discussant-2 — `--sandbox read-only` 대신 K46 권한 profile)은 기록에만 남고,
# 새 판과의 대응은 contract.LEGACY가 정한다(2026-09-24 리뷰 R04, 구조 검사 G4).
CODEX_PROFILE = "dml-discussant"
CODEX_AUTH_FILE = ".codex/auth.json"
POSIX_HOME = re.compile(r"/[^\x00-\x1f\x7f\"\\]*")
CODEX_REJECTED = "rejected: blocked by policy"
# 실행기가 runner에 넘겨 stderr 전체에서 세게 하는 표식(K02). Linux Codex의 거절 문자열은 아직 모른다(K30, B2).
STDERR_MARKS: dict[str, tuple[str, ...]] = {"codex": (CODEX_REJECTED,)}
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
        argv = [mask if self.input_via == ARGV and hashlib.sha256(a.encode("utf-8")).hexdigest() == self.input_sha256 else a
                for a in self.argv]
        return {"adapter_id": self.adapter_id, "argv": argv, "input_via": self.input_via,
                "input_sha256": self.input_sha256, "input_bytes": self.input_bytes}

    def __repr__(self) -> str:
        return f"ExecutionSpec({self.record()!r})"


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise AdapterError(message)


def codex_permissions(home: str) -> tuple[str, str]:
    """Linux Codex 참여자에게 `-c`로 넘길 두 값: 권한 profile 정의와 그것을 기본으로 고르는 키(K46).

    home은 격리 안의 HOME(실제 경로)이다. 값이 TOML 문자열 안에 들어가므로 따옴표·백슬래시·제어 문자는 받지 않는다.
    """
    _require(isinstance(home, str) and POSIX_HOME.fullmatch(home) is not None and home.rstrip("/") != "",
             "codex_user_home must be an absolute POSIX path without quotes, backslashes or control characters")
    path = f'{home.rstrip("/")}/{CODEX_AUTH_FILE}'
    return (f'permissions.{CODEX_PROFILE}={{ extends = ":read-only", filesystem = {{ "{path}" = "deny" }} }}',
            f'default_permissions="{CODEX_PROFILE}"')


def _check(adapter_id: str, argv: list[str], user_text: Iterable[int], config: Iterable[str] = ()) -> list[str]:
    """config: 이 실행에 허용한 Codex `-c` 값. 그 밖의 `-c`는 금지 목록에 걸린다."""
    skip, config = set(user_text), frozenset(config)
    for index, token in enumerate(argv):
        if index in skip:
            continue
        if (adapter_id == "codex" and token == "-c" and index + 1 < len(argv)
                and argv[index + 1] in config):
            skip.add(index + 1)
            continue
        _require(token not in FORBIDDEN[adapter_id], f"{adapter_id}: forbidden argument {token!r}")
    _require(len(subprocess.list2cmdline(argv)) <= MAX_COMMAND_LINE, "command line too long")
    return argv


def build_spec(adapter_id: str, *, exe: str, prompt: str, model: str, role: str = DISCUSSANT,
               enabled: bool | None = None, read_dirs: Iterable[str] = (),
               claude_context: str = "restricted", effort: str | None = None,
               codex_windows_sandbox: bool = False, codex_user_home: str | None = None) -> ExecutionSpec:
    """읽기 전용 논의자 한 번의 실행 명세. 허용된 조각 밖의 옵션은 받지 않는다.

    codex_windows_sandbox: Windows에서 Codex의 elevated 샌드박스를 명시한다(`codex doctor`가
    `sandbox backend elevated`, `provisioning complete`를 보일 때). 주의: Codex의 read-only
    샌드박스는 쓰기를 막을 뿐 **작업 폴더 밖 읽기를 막지 않는다**(aux-pc 관측) — blind 격리는
    이것으로 성립하지 않는다.
    codex_user_home: Linux에서 격리 안의 HOME. 주면 `--sandbox read-only` 대신 그 HOME의 `.codex/auth.json`만
    읽기 금지하는 권한 profile을 준다(K46). 실제 실행기(app.cli_executor)는 늘 준다. 없으면 옛 read-only 샌드박스다
    (동결한 Windows 경로).
    """
    _require(adapter_id in ADAPTERS, f"unknown adapter {adapter_id!r}")
    spec = ADAPTERS[adapter_id]
    _require(spec.enabled_by_default if enabled is None else enabled is True,
             f"{adapter_id} is off; the user has to turn it on ({spec.note})")
    _require(role in ROLES, f"unsupported role {role!r}")
    _require(adapter_id == "codex" or (codex_windows_sandbox is False and codex_user_home is None),
             "codex_windows_sandbox and codex_user_home apply to codex only")
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
        argv = [exe, "-p", "--output-format", "stream-json", "--verbose", "--model", model,
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
        _require(not (codex_windows_sandbox and codex_user_home is not None),
                 "the Windows sandbox and the Linux permission profile do not go together")
        argv = [exe, "exec", "--json", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config",
                "--ignore-rules"]
        if codex_user_home is None:
            config: tuple[str, ...] = (CODEX_WINDOWS_SANDBOX,) if codex_windows_sandbox else ()
            argv += ["--sandbox", "read-only"]
        else:
            config = codex_permissions(codex_user_home)
        for value in config:
            argv += ["-c", value]
        # `-`: 지시문을 stdin에서 읽는다(codex exec --help, aux-pc 0.155.1 기록).
        argv += ["--model", model, "-"]
        return spec(_check(adapter_id, argv, user_text=(), config=config), STDIN)
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


def interpret(adapter_id: str, run: RunResult, *, requested_model: str,
              claude_tools: tuple[str, ...] | None = None) -> Outcome:
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
        if adapter_id == "claude-code" and claude_tools is not None:
            init, _result, used = claude_stream(run.stdout)
            if (init.get("tools") != list(claude_tools) or init.get("permissionMode") != "dontAsk"
                    or init.get("mcp_servers") != [] or any(name not in claude_tools for name in used)):
                return Outcome(ok=False, status="permission_mismatch", text=None, reported_models=(),
                               model_match=None, detail="Claude reported an unexpected tool or permission surface", **base)
        return _parse(adapter_id, run, base)
    except (AttributeError, TypeError, KeyError, RecursionError, _Shape) as exc:
        # RecursionError: 문법은 맞지만 아주 깊게 중첩된 JSON(WSL2 리뷰 WM-06)
        return Outcome(ok=False, status="format_error", text=None, reported_models=(), model_match=None,
                       detail=f"unexpected output shape ({exc if isinstance(exc, _Shape) else type(exc).__name__})",
                       **base)


class _Shape(ValueError):
    """출력의 중첩 값이 예상한 타입이 아니다."""


def claude_stream(stdout: str) -> tuple[dict, dict, list[str]]:
    """Require one init and one terminal result; malformed/trailing output is not success."""
    init = result = None
    used = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            raise _Shape("broken Claude JSONL") from None
        if not isinstance(event, dict) or result is not None:
            raise _Shape("invalid event or data after Claude result")
        if event.get("type") == "system" and event.get("subtype") == "init":
            if init is not None:
                raise _Shape("duplicate Claude init")
            init = event
        elif event.get("type") == "result":
            result = event
        elif event.get("type") == "assistant":
            message = _typed(event, "message", Mapping, {})
            for block in _typed(message, "content", list, []):
                if not isinstance(block, dict):
                    raise _Shape("invalid Claude content block")
                if block.get("type") == "tool_use":
                    if not isinstance(block.get("name"), str):
                        raise _Shape("missing Claude tool name")
                    used.append(block["name"])
    if init is None or result is None:
        raise _Shape("expected Claude init and terminal result")
    return init, result, used


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
        tools = None
        if obj is None:
            _init, obj, used = claude_stream(run.stdout)
            tools = len(used)
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
                       tool_events=tools,
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
        # (openai/codex#42172) 읽지 못한 채 쓴 답을 성공으로 넘기지 않는다. runner가 stderr 전체에서 센
        # 값이 있으면 그것을 쓴다(K02). 없는데 stderr가 잘렸으면 거절이 없었다고 말할 수 없다(경계 리뷰 R04).
        counted = (run.stderr_counts or {}).get(CODEX_REJECTED)
        if counted is None and run.stderr_truncated:
            return Outcome(ok=False, status="format_error", text=text, reported_models=(), model_match=None,
                           usage=usage, tool_events=tools,
                           detail="stderr exceeded the runner limit; rejected commands may be hidden", **base)
        rejected = counted if counted is not None else run.stderr.count(CODEX_REJECTED)
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
