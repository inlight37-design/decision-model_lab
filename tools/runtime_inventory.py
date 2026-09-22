#!/usr/bin/env python3
"""V04-01 tier 1: 설치된 CLI의 버전과 help를 비밀 값 없이 기록한다. 표준 라이브러리만 쓴다.

실행하는 것: 아래 ADAPTERS에 적힌 `--version`과 `--help`뿐이다.
하지 않는 것: 로그인, 모델 호출, 설정 변경, 한도 조회, 설정·인증 파일 열기, 환경변수
값 읽기. 환경변수와 설정 파일은 **있는지 여부만** 기록한다.

이 도구가 기능에 붙이는 상태는 `in_help`, `not_in_help`, `unknown` 세 가지뿐이다. help에
플래그가 있다는 것은 이 계정·이 버전에서 그 플래그가 실제로 적용된다는 뜻이 아니다.
그것은 절차서 tier 2의 관측(`observed`)이 정한다. 그래서 tier 1 manifest의
`configured`는 언제나 false다. 절차: docs/experiments/v04-01-inventory/README.md

실행:
    python tools/runtime_inventory.py --host-label main-pc --dry-run   # 실행할 명령만 출력
    python tools/runtime_inventory.py --host-label main-pc             # 기록
    python tools/runtime_inventory.py --validate <manifest.json>       # 기존 기록 검사
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Iterator, Mapping

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "runtime-inventory/1"
DEFAULT_OUT = ROOT / "docs/experiments/v04-01-inventory/hosts"

# unknown: 확인 못 함 · documented: 공식 문서에만 있음 · in_help/not_in_help: 이 버전 help에
# 플래그가 있음/없음 · observed: 실제 실행으로 확인(tier 2) · unsupported: 실행으로 거절 확인
STATUSES = ("unknown", "documented", "in_help", "not_in_help", "observed", "unsupported")
TIER1_STATUSES = ("unknown", "in_help", "not_in_help")


@dataclass(frozen=True)
class Feature:
    name: str
    probe: int          # 몇 번째 help 출력에서 찾는가
    pattern: str        # 그 출력에서 찾을 정규식
    sources: tuple[str, ...] = ()   # 근거 원장 ID. 원장에 없는 문서는 절차서에 적는다


@dataclass(frozen=True)
class Adapter:
    adapter_id: str
    command: str
    help_args: tuple[tuple[str, ...], ...]
    features: tuple[Feature, ...]
    note: str
    version_args: tuple[str, ...] = ("--version",)


ACP = r"(?i)\bacp\b|agent client protocol"

# 새 플래그를 추가할 때는 공식 문서에서 이름을 확인하고 근거 ID를 붙인다.
ADAPTERS: tuple[Adapter, ...] = (
    Adapter("claude-code", "claude", (("--help",),), (
        Feature("print_mode", 0, r"--print\b", ("E06",)),
        Feature("output_format", 0, r"--output-format\b", ("E06",)),
        Feature("json_schema", 0, r"--json-schema\b", ("E06",)),
        Feature("resume", 0, r"--resume\b", ("E06",)),
        Feature("bare_mode", 0, r"--bare\b", ("F25",)),
        Feature("permission_mode", 0, r"--permission-mode\b", ("E06",)),
        Feature("permission_prompts", 0, r"--permission-prompts\b", ("E06",)),
        Feature("allowed_tools", 0, r"--allowedTools\b|--allowed-tools\b", ("E06",)),
        Feature("acp", 0, ACP),
    ), "Claude Code. ANTHROPIC_API_KEY가 있으면 -p 실행은 묻지 않고 그 키를 쓴다(API 과금)."),
    Adapter("codex", "codex", (("--help",), ("exec", "--help")), (
        Feature("exec_mode", 0, r"(?m)^\s*exec\b", ("E02",)),
        Feature("login_command", 0, r"(?m)^\s*login\b", ("E01",)),
        Feature("app_server", 0, r"\bapp-server\b"),
        Feature("json_events", 1, r"--json\b", ("E02",)),
        Feature("output_schema", 1, r"--output-schema\b", ("E02",)),
        Feature("resume", 1, r"(?m)^\s*resume\b", ("E02",)),
        Feature("sandbox", 1, r"--sandbox\b", ("E02",)),
        Feature("ephemeral", 1, r"--ephemeral\b", ("E02",)),
        Feature("ignore_user_config", 1, r"--ignore-user-config\b", ("E02",)),
        Feature("skip_git_repo_check", 1, r"--skip-git-repo-check\b", ("E02",)),
        Feature("acp", 0, ACP),
    ), "Codex CLI. exec는 기본 read-only sandbox. Git 저장소 밖에서는 --skip-git-repo-check 필요."),
    Adapter("antigravity", "agy", (("--help",),), (
        Feature("print_mode", 0, r"--print\b|--prompt\b", ("E08",)),
        Feature("output_format", 0, r"--output-format\b", ("E08",)),
        Feature("json_schema", 0, r"--json-schema\b", ("E08",)),
        Feature("resume", 0, r"--conversation\b|--continue\b", ("E08",)),
        Feature("sandbox", 0, r"--sandbox\b", ("E08",)),
        Feature("skip_permissions", 0, r"--dangerously-skip-permissions\b", ("E08",)),
        Feature("effort", 0, r"--effort\b", ("E08",)),
        Feature("acp", 0, ACP),
    ), "Antigravity CLI. headless 권한 거절은 exit 0 + stderr 경고(soft deny). --version은 문서에 없음."),
    Adapter("gemini-cli", "gemini", (("--help",),), (
        Feature("acp", 0, r"--experimental-acp\b|(?i:\bacp\b)"),
    ), "agy와 다른 제품이다. 둘을 같은 quota pool로 가정하지 않기 위해 설치 여부만 구분한다."),
)

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

# 열지 않는다. 있는지만 본다. 위 *_HOME/CONFIG_DIR 변수가 있으면 실제 위치는 다를 수 있다.
CONFIG_PATHS: tuple[tuple[str, str], ...] = (
    ("claude-code", "~/.claude/.credentials.json"),
    ("claude-code", "~/.claude/settings.json"),
    ("codex", "~/.codex/auth.json"),
    ("codex", "~/.codex/config.toml"),
    ("antigravity", "~/.gemini/antigravity-cli/settings.json"),
)

NOT_CHECKED = (
    "로그인 상태와 인증 방식", "사용 가능한 모델과 effort", "구조화 출력·resume·cancel의 실제 동작",
    "권한 제한이 실행 전에 적용되는지", "사용량·한도 조회", "과금 경로", "OS 격리",
)

# 앞에 영숫자가 오면 비밀이 아니다. 경계가 없으면 '--disk-cache-directory' 안의
# 'sk-cache-directory'까지 가려서 help 원문과 플래그 탐지가 틀어진다.
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    r"sk-(?:ant-|proj-)?[A-Za-z0-9_-]{16,}"
    r"|AIza[0-9A-Za-z_-]{30,}"
    r"|gh[pousr]_[A-Za-z0-9]{30,}"
    r"|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    r"|(?i:bearer)\s+[A-Za-z0-9._-]{20,})"
)
USER_PATH = re.compile(r"(?i)([A-Z]:[\\/]+Users[\\/]+)(?!<user>)[^\\/\s\"']+|(/(?:home|Users)/)(?!<user>)[^/\s\"']+")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
LABEL = re.compile(r"[a-z0-9][a-z0-9-]{1,39}")

Runner = Callable[[list[str], float], dict[str, Any]]


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def make_redactor(home: str) -> Callable[[str], str]:
    """홈 경로 → ~, 다른 사용자 경로의 이름 → <user>, 비밀처럼 보이는 문자열 → <redacted>."""
    homes = sorted({home, home.replace("\\", "/")} - {""}, key=len, reverse=True)

    def redact(text: str) -> str:
        for value in homes:
            text = re.sub(re.escape(value), "~", text, flags=re.IGNORECASE)
        text = USER_PATH.sub(lambda m: (m.group(1) or m.group(2)) + "<user>", text)
        return SECRET.sub("<redacted>", text)
    return redact


def decode(data: bytes | str | None) -> str:
    if data is None:
        return ""
    text = data if isinstance(data, str) else data.decode("utf-8", errors="replace")
    return ANSI.sub("", text).replace("\r\n", "\n")


def run_probe(argv: list[str], timeout: float) -> dict[str, Any]:
    """stdin을 닫고 한 번 실행한다. 대화형 입력을 기다리는 명령은 timeout으로 끝난다."""
    env = dict(os.environ, NO_COLOR="1")
    started = time.monotonic()
    try:
        proc = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                              timeout=timeout, env=env, check=False)
        result = {"exit_code": proc.returncode, "timed_out": False,
                  "stdout": decode(proc.stdout), "stderr": decode(proc.stderr)}
    except subprocess.TimeoutExpired as exc:
        result = {"exit_code": None, "timed_out": True,
                  "stdout": decode(exc.stdout), "stderr": decode(exc.stderr)}
    except OSError as exc:
        result = {"exit_code": None, "timed_out": False, "stdout": "", "stderr": "",
                  "error": type(exc).__name__}
    result["duration_ms"] = int((time.monotonic() - started) * 1000)
    return result


def planned_commands(adapters: tuple[Adapter, ...] = ADAPTERS) -> list[list[str]]:
    return [[a.command, *args] for a in adapters for args in (a.version_args, *a.help_args)]


def collect(label: str, *, adapters: tuple[Adapter, ...] = ADAPTERS,
            which: Callable[[str], str | None] = shutil.which, run: Runner | None = None,
            environ: Mapping[str, str] | None = None, home: str | None = None,
            exists: Callable[[str], bool] = os.path.exists, timeout: float = 20.0,
            now: datetime | None = None) -> tuple[dict[str, Any], dict[str, str]]:
    """manifest와 저장할 help 원문({상대 경로: 텍스트})을 돌려준다. 파일은 쓰지 않는다."""
    run = run or run_probe
    environ = os.environ if environ is None else environ
    home = str(Path.home()) if home is None else home
    redact = make_redactor(home)
    outputs: dict[str, str] = {}
    rows = []
    for adapter in adapters:
        resolved = which(adapter.command)
        row: dict[str, Any] = {
            "adapter_id": adapter.adapter_id, "command": adapter.command, "note": adapter.note,
            "installed": resolved is not None,
            "resolved_path": redact(resolved) if resolved else None,
            "runtime_version": None, "probes": [], "capabilities": {},
            # v0.3 01-system.md의 registry 필드. tier 1은 아래를 알 수 없다.
            "auth_mode": "unknown", "funding_mode": "unknown", "model_profile_id": None,
            "quota_pool_id": None, "policy_checked_on": None, "health": "unknown",
            "observability": "unknown", "configured": False,
        }
        texts: list[str | None] = []
        if resolved:
            for index, args in enumerate((adapter.version_args, *adapter.help_args)):
                result = run([resolved, *args], timeout)
                text = redact(result["stdout"])
                if result["stderr"]:
                    text += "\n--- stderr ---\n" + redact(result["stderr"])
                name = f"help/{adapter.adapter_id}-{index}.txt"
                outputs[name] = text
                row["probes"].append({
                    "argv": [adapter.command, *args], "exit_code": result["exit_code"],
                    "timed_out": result["timed_out"], "error": result.get("error"),
                    "duration_ms": result["duration_ms"], "output_file": name,
                    "output_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                })
                usable = result["exit_code"] == 0 and not result["timed_out"]
                if index == 0:
                    first = next((line.strip() for line in text.splitlines() if line.strip()), None)
                    row["runtime_version"] = first if usable else None
                else:
                    texts.append(text if usable else None)
        for feature in adapter.features:
            text = texts[feature.probe] if feature.probe < len(texts) else None
            if text is None:
                status, evidence = "unknown", None
            elif re.search(feature.pattern, text):
                status, evidence = "in_help", " ".join([adapter.command, *adapter.help_args[feature.probe]])
            else:
                status, evidence = "not_in_help", " ".join([adapter.command, *adapter.help_args[feature.probe]])
            row["capabilities"][feature.name] = {
                "status": status, "evidence": evidence, "source_ids": list(feature.sources)}
        rows.append(row)

    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    manifest = {
        "schema": SCHEMA,
        "tier": 1,
        "collected_at": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "host": {"label": label, "os": platform.system(), "os_release": platform.release(),
                 "os_version": platform.version(), "machine": platform.machine(),
                 "python": platform.python_version()},
        "tool": {"path": "tools/runtime_inventory.py",
                 "git_blob_sha1": git_blob_sha1(Path(__file__).read_bytes())},
        "scope": {"executed": "only the --version/--help commands listed in probes",
                  "not_checked": list(NOT_CHECKED)},
        "env_presence": {name: {"present": name in environ, "adapter": adapter_id, "why": why}
                         for name, adapter_id, why in ENV_VARS},
        "config_presence": {path: {"present": bool(exists(os.path.expanduser(path.replace("~", home, 1)))),
                                   "adapter": adapter_id, "opened": False}
                            for adapter_id, path in CONFIG_PATHS},
        "adapters": rows,
    }
    return manifest, outputs


def strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def validate_manifest(manifest: Any) -> list[str]:
    """기록이 규칙을 지키는지 본다. 기록된 내용이 사실인지는 판정하지 않는다."""
    errors: list[str] = []
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        return [f"schema must be {SCHEMA}"]
    tier = manifest.get("tier")
    if tier not in (1, 2):
        errors.append("tier must be 1 or 2")
    adapters = manifest.get("adapters")
    if not isinstance(adapters, list) or not adapters:
        return errors + ["adapters must be a non-empty list"]
    seen = set()
    for row in adapters:
        if not isinstance(row, dict):
            errors.append("adapter row must be an object")
            continue
        aid = row.get("adapter_id")
        if aid in seen:
            errors.append(f"duplicate adapter {aid}")
        seen.add(aid)
        caps = row.get("capabilities")
        if not isinstance(caps, dict):
            errors.append(f"{aid}: capabilities must be an object")
            continue
        observed = 0
        for name, cap in caps.items():
            status = cap.get("status") if isinstance(cap, dict) else None
            if status not in STATUSES:
                errors.append(f"{aid}.{name}: unknown status {status!r}")
                continue
            if tier == 1 and status not in TIER1_STATUSES:
                errors.append(f"{aid}.{name}: tier 1 cannot record {status!r}")
            if status == "observed":
                observed += 1
                if not (cap.get("evidence") and cap.get("observed_at")):
                    errors.append(f"{aid}.{name}: observed needs evidence and observed_at")
        configured = row.get("configured")
        if type(configured) is not bool:
            errors.append(f"{aid}: configured must be a boolean")
        elif configured and (tier != 2 or observed == 0 or "unknown" in
                             (row.get("auth_mode"), row.get("funding_mode"))):
            errors.append(f"{aid}: configured=true needs tier 2, a known auth and funding mode "
                          "and at least one observed capability")
    for name, entry in (manifest.get("env_presence") or {}).items():
        if not isinstance(entry, dict) or type(entry.get("present")) is not bool:
            errors.append(f"env_presence.{name}: record presence as a boolean only")
    for text in strings(manifest):
        if SECRET.search(text):
            errors.append("manifest contains a secret-like string")
            break
    for text in strings(manifest):
        if USER_PATH.search(text):
            errors.append("manifest contains an unredacted user path")
            break
    return errors


def write(out_dir: Path, manifest: dict[str, Any], outputs: dict[str, str], force: bool) -> Path:
    target = out_dir / "manifest.json"
    if target.exists() and not force:
        raise FileExistsError(f"{target} already exists; pass --force to replace it")
    for relative, text in outputs.items():
        path = out_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    out_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8", newline="\n")
    return target


def summary(manifest: dict[str, Any]) -> list[str]:
    lines = []
    for row in manifest["adapters"]:
        state = row["runtime_version"] or ("설치됨, 버전 미확인" if row["installed"] else "설치 안 됨")
        lines.append(f"{row['adapter_id']:<12} {state}")
        for name, cap in row["capabilities"].items():
            lines.append(f"    {name:<22} {cap['status']}")
    present = [name for name, entry in manifest["env_presence"].items() if entry["present"]]
    if present:
        lines.append("경고: 과금·인증 경로를 바꿀 수 있는 환경변수가 있다(값은 읽지 않음): " + ", ".join(present))
    lines.append("tier 1은 help 문자열만 봤다. 실제 동작은 절차서 tier 2에서 관측한다.")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host-label", help="기기 이름표. 영소문자·숫자·하이픈. 실제 hostname을 쓰지 않는다")
    parser.add_argument("--out", type=Path, help="기본값: docs/experiments/v04-01-inventory/hosts/<label>")
    parser.add_argument("--timeout", type=float, default=20.0, help="명령 하나의 제한 시간(초)")
    parser.add_argument("--dry-run", action="store_true", help="실행할 명령만 출력하고 아무것도 실행하지 않는다")
    parser.add_argument("--force", action="store_true", help="기존 manifest를 덮어쓴다")
    parser.add_argument("--validate", type=Path, metavar="MANIFEST", help="기존 manifest만 검사한다")
    args = parser.parse_args(argv)

    if args.validate:
        try:
            errors = validate_manifest(json.loads(args.validate.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            errors = [f"cannot read manifest: {exc}"]
        for error in errors:
            print(f"INVALID: {error}")
        if errors:
            return 1
        print("PASS: manifest rules only; recorded facts are not verified.")
        return 0

    if not args.host_label or not LABEL.fullmatch(args.host_label):
        parser.error("--host-label is required: 2-40 chars of a-z, 0-9 and '-'")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    if args.dry_run:
        # Windows는 파일 이름의 대소문자를 가리지 않는다. 데스크톱 앱 폴더가 PATH에 있으면
        # 'claude'가 GUI 실행 파일로 풀릴 수 있으므로 실행 전에 실제 경로를 보여 준다.
        redact = make_redactor(str(Path.home()))
        print("실행할 명령 (PATH에 있는 것만 실행된다):")
        for adapter in ADAPTERS:
            resolved = shutil.which(adapter.command)
            print(f"  [{adapter.command}] " + (redact(resolved) if resolved else "PATH에 없음 — 실행하지 않음"))
            for args in (adapter.version_args, *adapter.help_args):
                print("    " + " ".join([adapter.command, *args]))
        print("경로가 해당 CLI가 아니면(예: 데스크톱 앱 실행 파일) 실행하지 말고 PATH를 확인한다.")
        print("환경변수는 이름의 존재만, 설정 파일은 경로의 존재만 확인한다. 값과 내용은 읽지 않는다.")
        return 0

    manifest, outputs = collect(args.host_label, timeout=args.timeout)
    errors = validate_manifest(manifest)
    if errors:
        for error in errors:
            print(f"INVALID: {error}", file=sys.stderr)
        print("기록하지 않았다. 출력에 가려지지 않은 값이 있다.", file=sys.stderr)
        return 1
    out_dir = args.out or DEFAULT_OUT / args.host_label
    try:
        target = write(out_dir, manifest, outputs, args.force)
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print("\n".join(summary(manifest)))
    print(f"\n기록: {target}")
    print("커밋 전에 help/ 아래 파일을 한 번 훑어 개인 정보가 없는지 확인한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
