"""새 컴퓨터가 이 저장소를 쓸 준비가 됐는지 본다. 설치·설정 변경·모델 호출을 하지 않는다.

Windows에서는 저장소 검사와 협업에 필요한 도구(Python·jsonschema·Git·GitHub CLI·Node·commit hook)와 WSL
배포판을, Linux·WSL에서는 실제 CLI 실행에 필요한 것(bubblewrap 격리·Codex·Claude Code·구독 로그인)을 본다.
로그인은 `codex login status`와 `claude auth status`의 결과에서 로그인 여부와 방식만 읽고 계정 식별 값은
출력하지 않는다. 과금 경로를 바꾸는 환경변수는 이름만 본다(core.env.ENV_VARS — 값은 읽지 않는다).

종료 코드: 필수 항목이 모두 ok면 0, 필수 항목이 하나라도 missing이면 1. warn·info는 종료 코드와 무관하다.
"준비됨"은 도구 설치와 구독 로그인까지다 — 이 기기의 관측과 strict 허가는 준비 조회(--check-config)가 따로 정한다.
설치는 setup.ps1(원터치)·setup-wsl.sh가, 순서와 사람이 할 일은 docs/SETUP.md가 맡는다.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.env import ENV_VARS  # noqa: E402

# 지금 참여자 계획을 관측한 기록(E2). 설치판 버전의 기준이며, 이 기록은 aux-pc-wsl 한 곳에서 만들었다.
OBSERVED = ROOT / "docs" / "reviews" / "2026-09-25-context-independence" / "manifest.v2.json"
# CI와 같은 최소 bubblewrap 실행. 실패하면 격리 시험과 실제 참여자 실행을 할 수 없다.
BWRAP_PROBE = ("--unshare-all", "--share-net", "--die-with-parent", "--ro-bind", "/usr", "/usr",
               "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
               "--proc", "/proc", "--", "/usr/bin/true")
CLAUDE_STORE = ("Packages", "Claude_pzs8sxrjxfjjc", "LocalCache", "Local")
# CLI가 보고하는 판. 부분 문자열로 비교하면 0.156.10이 0.156.1과 같아 보인다(2026-09-25 외부 검토 R04).
VERSION_TEXT = r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?"
VERSION = re.compile(r"\b(" + VERSION_TEXT + r")\b")
REQUIRED_ADAPTERS = ("codex", "claude-code")

Run = Callable[[Sequence[str]], "tuple[int, str] | None"]
Which = Callable[[str], "str | None"]


@dataclass
class Row:
    name: str
    status: str            # ok · missing · warn · info
    detail: str
    fix: str = ""
    required: bool = True


def run_command(argv: Sequence[str], timeout: float = 30) -> tuple[int, str] | None:
    """명령을 실행해 (종료 코드, stdout+stderr)를 돌려준다. 없거나 시간을 넘기면 None."""
    try:
        done = subprocess.run(list(argv), capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.returncode, decode(done.stdout + done.stderr)


def decode(data: bytes) -> str:
    """wsl.exe의 목록은 UTF-16LE로 나온다. 나머지는 UTF-8로 읽는다."""
    if data[:2] == b"\xff\xfe" or (len(data) > 1 and data[1:2] == b"\x00"):
        return data.decode("utf-16-le", errors="replace").lstrip("﻿")
    return data.decode("utf-8", errors="replace")


def first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def observed_versions(path: Path = OBSERVED) -> dict[str, str]:
    """관측 기록의 설치판 버전(adapter_id → version). 기록이 없거나 모양이 다르면 빈 사전."""
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    versions = {}
    for adapter in manifest.get("adapters", []):
        installed = adapter.get("installed") or {}
        if isinstance(installed, dict) and isinstance(installed.get("version"), str):
            versions[adapter.get("adapter_id")] = installed["version"]
    return versions


def observed_host(path: Path = OBSERVED) -> str | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("host", {}).get("label")
    except (OSError, ValueError, AttributeError):
        return None


# ---- 공통 --------------------------------------------------------------------------------------
def common_rows(run: Run, which: Which, *, windows: bool) -> list[Row]:
    rows = []
    version = sys.version_info
    rows.append(Row("Python", "ok" if version >= (3, 12) else "missing", f"{version.major}.{version.minor}.{version.micro}",
                    "Python 3.12 이상을 설치한다"))
    try:
        import jsonschema  # noqa: F401
        rows.append(Row("jsonschema", "ok", "가져오기 성공"))
    except ImportError:
        fix = ("python -m pip install -r requirements-design.txt" if windows
               else "sudo apt-get install -y python3-jsonschema")
        rows.append(Row("jsonschema", "missing", "없으면 스키마 시험이 skip된다(skip은 통과가 아니다)", fix))
    rows.append(tool_row(run, which, "Git", "git", ("--version",), "Git을 설치한다(tools/setup/setup.ps1 또는 apt)"))
    hooks = run(("git", "-C", str(ROOT), "config", "core.hooksPath")) if which("git") else None
    if hooks and hooks[0] == 0 and hooks[1].strip().replace("\\", "/").rstrip("/").endswith(".githooks"):
        rows.append(Row("commit hook", "ok", "core.hooksPath = .githooks", required=False))
    else:
        rows.append(Row("commit hook", "warn", "인코딩 검사 hook이 꺼져 있다(CI가 뒤에서 잡는다)",
                        "git config core.hooksPath .githooks", required=False))
    gh = tool_row(run, which, "GitHub CLI", "gh", ("--version",), "GitHub CLI를 설치한다", required=windows)
    rows.append(gh)
    if gh.status == "ok":
        auth = run(("gh", "auth", "status"))
        rows.append(Row("GitHub 로그인", "ok" if auth and auth[0] == 0 else "missing",
                        "로그인됨" if auth and auth[0] == 0 else "로그인 안 됨(PR·카드 보드에 필요)",
                        "gh auth login", required=windows))
    node = tool_row(run, which, "Node", "node", ("--version",),
                    "Node LTS를 설치하면 화면 JavaScript 시험이 로컬에서도 돈다(없으면 skip, CI는 돈다)", required=False)
    if node.status == "missing":
        node.status = "warn"
    rows.append(node)
    return rows


def tool_row(run: Run, which: Which, name: str, exe: str, args: Sequence[str], fix: str, *,
             required: bool = True) -> Row:
    path = which(exe)
    if not path:
        return Row(name, "missing", "PATH에 없다", fix, required)
    out = run((path, *args))
    if out is None or out[0] != 0:
        return Row(name, "missing", f"{path} 실행 실패", fix, required)
    return Row(name, "ok", first_line(out[1]), required=required)


# ---- Windows -----------------------------------------------------------------------------------
def windows_rows(run: Run, which: Which, env: Mapping[str, str]) -> list[Row]:
    rows = []
    wsl = which("wsl")
    listed = run((wsl, "--list", "--quiet")) if wsl else None
    distros = [line.strip() for line in (listed[1] if listed and listed[0] == 0 else "").splitlines() if line.strip()]
    ubuntu = [name for name in distros if name.lower().startswith("ubuntu")]
    if ubuntu:
        rows.append(Row("WSL", "ok", ", ".join(ubuntu), required=False))
    else:
        rows.append(Row("WSL", "warn", "Ubuntu 배포판이 없다 — 실제 CLI 실행은 WSL에서만 한다(오프라인 검사는 된다)",
                        "관리자 PowerShell: wsl --install -d Ubuntu-24.04 (재부팅 뒤 Linux 사용자 만들기)", required=False))
    local = env.get("LOCALAPPDATA")
    store = Path(local, *CLAUDE_STORE) if local else None
    if store and store.is_dir():
        hidden = sorted(p.name for p in store.iterdir() if p.is_dir() and p.name not in ("Claude", "Microsoft"))
        if hidden:
            rows.append(Row("Claude 앱 전용 AppData", "warn",
                            "앱 안에서 만든 폴더가 사용자 터미널에서는 안 보인다: " + ", ".join(hidden),
                            "AppData 밖에 설치하고 tools/v04-01/check-versions.ps1로 확인한다", required=False))
    return rows


# ---- Linux·WSL ---------------------------------------------------------------------------------
def linux_rows(run: Run, which: Which, env: Mapping[str, str], home: Path, *,
               observed: Mapping[str, str], host: str | None, bwrap: Path = Path("/usr/bin/bwrap")) -> list[Row]:
    rows = []
    fix_bwrap = "sudo apt-get install -y bubblewrap"
    if not bwrap.exists():
        rows.append(Row("bubblewrap", "missing", f"{bwrap} 없음 — 격리 시험 skip, 실제 참여자 실행 불가", fix_bwrap))
    else:
        owner = bwrap.stat().st_uid
        probe = run((str(bwrap), *BWRAP_PROBE))
        if owner != 0:
            rows.append(Row("bubblewrap", "missing", f"{bwrap}가 root 소유가 아니다(core.isolation이 거절한다)", fix_bwrap))
        elif probe is None or probe[0] != 0:
            rows.append(Row("bubblewrap", "missing", "최소 격리 실행이 실패했다 — user namespace가 막혔을 수 있다",
                            "docs/SETUP.md의 bubblewrap 항목(AppArmor 제한은 사용자가 판단한다)"))
        else:
            rows.append(Row("bubblewrap", "ok", "최소 격리 실행 성공"))
    for adapter_id, exe, name in (("codex", "codex", "Codex CLI"), ("claude-code", "claude", "Claude Code")):
        rows.append(cli_row(run, which, adapter_id, exe, name, observed.get(adapter_id)))
    rows.append(codex_login_row(run, which))
    rows.append(claude_login_row(run, which))
    codex_home = Path(env["CODEX_HOME"]) if env.get("CODEX_HOME") else home / ".codex"
    if (codex_home / "AGENTS.md").exists():
        rows.append(Row("Codex 전역 AGENTS.md", "warn", f"{codex_home / 'AGENTS.md'}가 있으면 Codex 참여자 계획이 거절된다(E2)",
                        "그 파일을 옮기거나 지운다(사용자 판단)", required=False))
    present = [name for name, _, _ in ENV_VARS if name in env]
    if present:
        rows.append(Row("과금 환경변수", "warn", "있음: " + ", ".join(present) + " — 구독 대신 API 과금으로 갈 수 있다",
                        "이 셸에서 빼고 실행한다(앱의 자식 환경은 이미 뺀다)", required=False))
    rows.append(Row("관측 기록", "info",
                    f"지금 참여자 계획의 관측(E2)은 '{host or '?'}'에서 만들었다. 실제 모드는 이 기기에 등록된 기록만 쓴다 — "
                    "다른 기기에서는 V04-01·E2 관측을 새로 하고 그 기기에서 등록한다(python3 -m app.registration)", required=False))
    return rows


def cli_row(run: Run, which: Which, adapter_id: str, exe: str, name: str, recorded: str | None) -> Row:
    path = which(exe)
    fix = "bash tools/setup/setup-wsl.sh (로그인 셸에서: bash -lc)"
    if not path:
        return Row(name, "missing", "PATH에 없다(로그인 셸의 ~/.local/bin 확인)", fix)
    if path.startswith("/mnt/"):
        return Row(name, "missing", f"Windows 실행 파일이 먼저 잡힌다({path}) — core.env가 거절한다", fix)
    out = run((path, "--version"))
    if out is None or out[0] != 0:
        return Row(name, "missing", f"{path} --version 실패", fix)
    text = first_line(out[1])
    found = VERSION.search(text)
    if not found:
        return Row(name, "missing", f"판을 읽지 못했다: {text[:80]}", fix)
    if recorded and found.group(1) != recorded:
        return Row(name, "info", f"{found.group(1)} — 관측 기록의 판은 {recorded}. 준비 조회가 다시 관측하기 전까지 거절한다",
                   f"같은 판을 원하면 setup-wsl.sh(기본이 관측 판 고정), 새 판이면 V04-01·E2 관측을 다시 한다", required=False)
    return Row(name, "ok", text)


def codex_login_row(run: Run, which: Which) -> Row:
    path = which("codex")
    out = run((path, "login", "status")) if path else None
    text = out[1] if out else ""
    if out and out[0] == 0 and "ChatGPT" in text:
        return Row("Codex 로그인", "ok", "ChatGPT 로그인(구독)")
    if out and out[0] == 0 and "API key" in text:   # 이 저장소는 구독 CLI만 쓴다 — 준비되지 않은 것으로 센다(R04)
        return Row("Codex 로그인", "missing", "API 키 로그인 — 구독이 아니라 API 과금이다", "codex logout 뒤 codex login")
    return Row("Codex 로그인", "missing", "로그인 안 됨", "codex login (배포판 터미널에서 직접)")


def claude_login_row(run: Run, which: Which) -> Row:
    """계정 식별 값(메일·조직)은 읽지만 출력하지 않는다. 로그인 여부와 방식만 남긴다."""
    path = which("claude")
    out = run((path, "auth", "status")) if path else None
    try:
        status = json.loads(out[1]) if out else {}
    except ValueError:
        status = {}
    # 상태 명령이 실패했으면 출력이 로그인을 말해도 믿지 않는다(R04).
    if not out or out[0] != 0 or not isinstance(status, dict) or status.get("loggedIn") is not True:
        return Row("Claude 로그인", "missing", "로그인 안 됨(또는 상태 조회 실패)", "claude auth login (배포판 터미널에서 직접)")
    method, provider = status.get("authMethod"), status.get("apiProvider")
    if method == "claude.ai" and provider in (None, "firstParty"):
        return Row("Claude 로그인", "ok", "claude.ai 구독 로그인")
    return Row("Claude 로그인", "missing", f"구독이 아닌 방식({method}, {provider}) — 이 저장소는 구독만 쓴다",
               "claude auth logout 뒤 claude auth login")


# ---- 출력 --------------------------------------------------------------------------------------
def collect(*, windows: bool | None = None, run: Run = run_command, which: Which = shutil.which,
            env: Mapping[str, str] | None = None, home: Path | None = None) -> list[Row]:
    windows = os.name == "nt" if windows is None else windows
    env = os.environ if env is None else env
    rows = common_rows(run, which, windows=windows)
    if windows:
        rows += windows_rows(run, which, env)
    else:
        rows += linux_rows(run, which, env, home or Path.home(), observed=observed_versions(), host=observed_host())
    return rows


def render(rows: Sequence[Row], where: str) -> tuple[str, int]:
    lines = [f"decision-model_lab 준비 확인 ({where}) — 설치·변경·모델 호출 없음"]
    for row in rows:
        mark = "warn" if row.status == "missing" and not row.required else row.status   # 선택 항목은 막지 않는다
        lines.append(f"  {mark:<8} {row.name}: {row.detail}" + (f"\n           → {row.fix}" if row.fix and row.status != "ok" else ""))
    missing = [row.name for row in rows if row.required and row.status == "missing"]
    lines.append("결과: 필수 항목 모두 준비됨(설치·구독 로그인까지 — strict 실행 허가는 이 기기의 관측과 준비 조회가 따로 정한다)"
                 if not missing else f"결과: 필수 항목 {len(missing)}개 준비 안 됨 — " + ", ".join(missing))
    return "\n".join(lines), (1 if missing else 0)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--observed-versions", action="store_true",
                    help="관측 기록의 설치판 버전만 'adapter version' 줄로 출력한다(setup-wsl.sh가 쓴다)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.observed_versions:
        versions = observed_versions()
        bad = [a for a in REQUIRED_ADAPTERS if not re.fullmatch(VERSION_TEXT, versions.get(a) or "")]
        if bad:   # 빈 출력이나 일부만 내면 설치 스크립트가 최신판으로 오해할 수 있다(R02)
            print(f"관측 기록에 쓸 수 있는 판이 없다: {', '.join(bad)} ({OBSERVED})", file=sys.stderr)
            return 1
        for adapter_id in REQUIRED_ADAPTERS:
            print(adapter_id, versions[adapter_id])
        return 0
    windows = os.name == "nt"
    text, code = render(collect(windows=windows), "Windows" if windows else "Linux·WSL")
    print(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
