"""참여자 CLI에 넘길 환경과 실행 파일 찾기. 표준 라이브러리만 쓴다.

실행 코어가 조사 도구(tools/)에 기대지 않도록 여기에 둔다(경계 리뷰 R05). 방향은 한쪽이다:
tools/runtime_inventory.py가 이 모듈의 ENV_VARS로 변수가 **있는지만** 기록한다.

- ENV_VARS: 과금 경로나 설정 위치를 바꾸는 변수. 값은 읽거나 기록하지 않는다.
- fresh_environment: AI 도구가 자기 셸에 넣은 변수와 PATH를 새 터미널 기준(Windows 레지스트리)으로
  되돌린다.
- child_env: 자식에게 줄 환경. 과금 변수를 빼고, WSL의 Windows 드라이브 PATH 항목을 뺀다.
- resolve: 자식 PATH로 실행 파일의 절대 경로를 찾는다. WSL에서는 Windows 실행 파일을 거절한다.
  WSL은 기본으로 Windows PATH를 이어 붙이므로 `codex`를 찾다가 `/mnt/c/.../codex.exe`가 잡힐 수
  있다. 그러면 Linux 격리 안의 Linux CLI를 쓰려고 WSL로 옮긴 목적이 조용히 사라진다(2절 15).
"""
from __future__ import annotations

import os
from pathlib import PurePosixPath
import re
import shutil
from typing import Mapping

IS_WINDOWS = os.name == "nt"

# 값은 절대 읽지 않는다. 존재 여부만 기록한다. 과금 경로나 설정 위치를 바꾸는 변수들이다.
ENV_VARS: tuple[tuple[str, str, str], ...] = (
    ("CLAUDE_CODE_USE_BEDROCK", "claude-code", "클라우드 provider 인증이 최우선"),
    ("CLAUDE_CODE_USE_VERTEX", "claude-code", "클라우드 provider 인증이 최우선"),
    ("CLAUDE_CODE_USE_FOUNDRY", "claude-code", "클라우드 provider 인증이 최우선"),
    ("ANTHROPIC_AUTH_TOKEN", "claude-code", "구독 로그인보다 우선"),
    ("ANTHROPIC_API_KEY", "claude-code", "-p에서는 묻지 않고 사용 — API 과금"),
    ("CLAUDE_CODE_OAUTH_TOKEN", "claude-code", "장기 구독 토큰. --bare는 읽지 않음"),
    ("ANTHROPIC_PROFILE", "claude-code", "명명된 profile이 /login보다 우선"),
    ("ANTHROPIC_BASE_URL", "claude-code", "요청 대상 endpoint 변경"),
    ("CLAUDE_CONFIG_DIR", "claude-code", "설정·자격증명 위치 변경"),
    ("OPENAI_API_KEY", "codex", "API 키 로그인에 쓰일 수 있음"),
    ("CODEX_API_KEY", "codex", "exec 자동화용 API 키"),
    ("CODEX_HOME", "codex", "설정·자격증명 위치 변경"),
    ("GEMINI_API_KEY", "antigravity", "modelProvider=gemini와 함께 API 키 모드"),
    ("GOOGLE_API_KEY", "antigravity", "Google API 키 경로"),
    ("GOOGLE_GENAI_USE_VERTEXAI", "antigravity", "Vertex 경로 전환"),
)

# 자식 환경에서 뺀다: 구독 대신 API 과금이나 다른 endpoint로 바꿀 수 있는 변수. 남기는 것은
# 설정 위치(CLAUDE_CONFIG_DIR, CODEX_HOME — 빼면 로그인을 못 찾는다)와 구독 토큰뿐이다.
KEEP_VARS = frozenset({"CLAUDE_CONFIG_DIR", "CODEX_HOME", "CLAUDE_CODE_OAUTH_TOKEN"})
BILLING_VARS = frozenset(name for name, _, _ in ENV_VARS) - KEEP_VARS

# AI 도구는 자기 셸에 이런 변수를 넣는다(보조 PC의 Claude 데스크톱 앱 셸에서 26개 관측).
# 그 셸에서 잰 환경은 사용자가 새 터미널을 열었을 때의 환경이 아니다.
AI_TOOL_VARS = re.compile(r"(?i)(?:CLAUDE|ANTHROPIC|CODEX|OPENAI|GEMINI|GOOGLE_|MCP_)")

# WSL이 Windows 드라이브를 붙이는 기본 위치(/mnt/c 등).
WINDOWS_MOUNT = re.compile(r"^/mnt/[A-Za-z](?:/|$)")


class EnvError(ValueError):
    """실행 전에 거절한 환경. 모델 호출은 일어나지 않았다."""


def fresh_environment(base: Mapping[str, str], machine: Mapping[str, str],
                      user: Mapping[str, str]) -> tuple[dict[str, str], list[str]]:
    """AI 도구 변수와 PATH만 새 터미널 기준으로 맞춘 환경과, 지운 변수 이름을 돌려준다.
    설정은 바꾸지 않는다. Windows 레지스트리 값(machine, user)을 받는다.

    AI 접두사 변수는 시스템·사용자 설정의 값으로 다시 만든다(같은 이름이면 사용자 설정이
    이긴다). 그래서 설정에 없는 변수는 지워지고, 셸이 같은 이름에 다른 값을 넣었으면 설정
    값으로 돌아가고, 셸이 뜬 뒤 설정에 새로 생긴 변수는 추가된다. PATH는 시스템 + 사용자
    설정이다. 나머지 변수(proxy 등)는 base 그대로이므로 새 터미널과 같다고 쓰지 않는다.
    """
    persistent: dict[str, tuple[str, str]] = {}
    for scope in (machine, user):
        for name, value in scope.items():
            if AI_TOOL_VARS.match(name):
                persistent[name.upper()] = (name, value)
    removed = sorted(name for name in base
                     if AI_TOOL_VARS.match(name) and name.upper() not in persistent)
    env = {name: value for name, value in base.items()
           if not AI_TOOL_VARS.match(name) and name.upper() != "PATH"}
    env.update(dict(persistent.values()))
    upper = lambda values: {k.upper(): v for k, v in values.items()}  # noqa: E731
    paths = [upper(scope).get("PATH", "") for scope in (machine, user)]
    env["PATH"] = ";".join(p.strip(";") for p in paths if p)
    return env, removed


def is_windows_binary(path: str) -> bool:
    """WSL 안에서 본 Windows 실행 파일인가: Windows 드라이브 아래이거나 .exe다."""
    return bool(WINDOWS_MOUNT.match(path)) or PurePosixPath(path).suffix.lower() == ".exe"


def child_env(base: Mapping[str, str], *, machine: Mapping[str, str] | None = None,
              user: Mapping[str, str] | None = None) -> tuple[dict[str, str], list[str]]:
    """자식에게 줄 환경과, 뺀 과금 변수 이름을 돌려준다. 값은 기록하지 않는다.

    machine/user(레지스트리 값)를 주면 AI 도구가 셸에 넣은 변수를 먼저 정리한다(새 터미널 기준).
    POSIX에서는 PATH의 Windows 드라이브 항목(/mnt/c/...)을 뺀다 — 자식이 WSL interop로 Windows
    도구를 부르지 못하게 한다.
    """
    env = dict(base)
    if machine is not None or user is not None:
        env, _ = fresh_environment(base, machine or {}, user or {})
    dropped = sorted(name for name in env if name.upper() in BILLING_VARS)
    for name in dropped:
        del env[name]
    if not IS_WINDOWS and "PATH" in env:
        env["PATH"] = ":".join(p for p in env["PATH"].split(":") if p and not WINDOWS_MOUNT.match(p))
    env["NO_COLOR"] = "1"
    return env, dropped


def resolve(command: str, env: Mapping[str, str]) -> str:
    """자식이 쓸 PATH로 실행 파일을 찾아 절대 경로로 돌려준다."""
    path = shutil.which(command, path=env.get("PATH") or env.get("Path"))
    if path is None:
        raise EnvError(f"{command} is not on the child PATH")
    path = os.path.abspath(path)
    if not IS_WINDOWS and is_windows_binary(path):
        raise EnvError(f"{command} resolved to a Windows executable ({path}); install the Linux CLI")
    return path
