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
    python tools/runtime_inventory.py --validate <manifest.json>       # 기존 기록 검사(runtime-inventory/1·2)
    AI 도구 안의 터미널에서 실행한다면(Windows) --fresh-env를 붙인다.
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
sys.path.insert(0, str(ROOT))  # `python tools/runtime_inventory.py`로 실행해도 core를 찾는다
from core.env import AI_TOOL_VARS, ENV_VARS, fresh_environment  # noqa: E402,F401 — 이 도구의 이름으로도 쓴다
from core import eligibility  # noqa: E402 — runtime-inventory/2의 칸과 상태
from tools.redaction import SECRET, USER_PATH, make_redactor  # noqa: E402,F401 — shared publication policy
SCHEMA = "runtime-inventory/1"
DEFAULT_OUT = ROOT / "docs/experiments/v04-01-inventory/hosts"

# unknown: 확인 못 함 · documented: 공식 문서에만 있음 · in_help/not_in_help: 이 버전 help에
# 플래그가 있음/없음 · observed: 실제 실행으로 확인(tier 2) · unsupported: 실행으로 거절 확인
STATUSES = ("unknown", "documented", "in_help", "not_in_help", "observed", "unsupported")
TIER1_STATUSES = ("unknown", "in_help", "not_in_help")
# tier 2에서 관측해 적는 값. 'unknown'은 모른다는 뜻이고, 키가 없거나 null·빈 문자열인
# 것과 같지 않다 — 그런 값은 검사기가 거절한다. 새 경로를 관측하면 여기에 먼저 추가한다.
AUTH_MODES = ("subscription_oauth", "chatgpt_login", "google_account_login", "api_key", "cloud_provider")
FUNDING_MODES = ("subscription", "api_billing", "credits")
# presence 기록에 허용하는 키. 값 필드가 끼어들 자리를 두지 않는다.
PRESENCE_KEYS = {"env_presence": {"present", "adapter", "why"},
                 "config_presence": {"present", "adapter", "opened"}}
OBSERVED_AT = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}Z)?")


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

# 과금 경로나 설정 위치를 바꾸는 변수 목록(ENV_VARS)은 실행 코어와 함께 쓰므로 core/env.py에 있다.
# 이 도구는 그 변수가 있는지만 기록한다. 값은 절대 읽지 않는다.

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

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
LABEL = re.compile(r"[a-z0-9][a-z0-9-]{1,39}")
ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_()]*")
IS_WINDOWS = os.name == "nt"

Runner = Callable[[list[str], float], dict[str, Any]]


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def decode(data: bytes | str | None) -> str:
    if data is None:
        return ""
    text = data if isinstance(data, str) else data.decode("utf-8", errors="replace")
    return ANSI.sub("", text).replace("\r\n", "\n")


def registry_environment() -> tuple[dict[str, str], dict[str, str]]:  # pragma: no cover - Windows 전용
    """새 로그온 세션이 받는 시스템·사용자 환경변수. 값은 PATH 재구성에만 쓰고 기록하지 않는다."""
    import winreg

    def read(root: Any, subkey: str) -> dict[str, str]:
        values: dict[str, str] = {}
        with winreg.OpenKey(root, subkey) as key:
            index = 0
            while True:
                try:
                    name, value, kind = winreg.EnumValue(key, index)
                except OSError:
                    return values
                if isinstance(value, str):
                    values[name] = (winreg.ExpandEnvironmentStrings(value)
                                    if kind == winreg.REG_EXPAND_SZ else value)
                index += 1

    return (read(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
            read(winreg.HKEY_CURRENT_USER, "Environment"))


def run_probe(argv: list[str], timeout: float, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """stdin을 닫고 한 번 실행한다. 대화형 입력을 기다리는 명령은 timeout으로 끝난다."""
    env = dict(os.environ if env is None else env, NO_COLOR="1")
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
            now: datetime | None = None, removed_vars: list[str] | None = None,
            ) -> tuple[dict[str, Any], dict[str, str]]:
    """manifest와 저장할 help 원문({상대 경로: 텍스트})을 돌려준다. 파일은 쓰지 않는다.

    removed_vars가 None이면 이 프로세스의 환경을 그대로 쟀다는 뜻이고, 목록이면
    fresh_environment()로 지운 변수 이름이다.
    """
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
    # Windows 변수 이름은 대소문자를 가리지 않는다. fresh_environment()가 돌려주는 dict는
    # 가리므로, 설정에 'Anthropic_Api_Key'로 적혀 있어도 있다고 기록되게 대문자로 비교한다.
    env_names = {name.upper() for name in environ}
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
        "environment": {"mode": "process" if removed_vars is None else "fresh",
                        "removed": list(removed_vars or [])},
        "env_presence": {name: {"present": name.upper() in env_names, "adapter": adapter_id, "why": why}
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
    """기록이 규칙을 지키는지 본다. 기록된 내용이 사실인지는 판정하지 않는다.

    모르는 형태는 통과시키지 않는다. 키가 없거나 타입이 다르면 예외가 아니라 오류 줄이 된다.
    `configured=true`는 '기본 연결을 관측했다'는 뜻일 뿐이다. blind 문맥·권한 제한이 실제로
    지켜지는지(conformance)는 이 검사도, 이 필드도 말하지 않는다.
    """
    errors: list[str] = []
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        return [f"schema must be {SCHEMA}"]
    tier = manifest.get("tier")
    if type(tier) is not int or tier not in (1, 2):
        errors.append("tier must be 1 or 2")
    adapters = manifest.get("adapters")
    if not isinstance(adapters, list) or not adapters:
        return errors + ["adapters must be a non-empty list"]
    seen = set()
    for index, row in enumerate(adapters):
        if not isinstance(row, dict):
            errors.append(f"adapters[{index}]: adapter row must be an object")
            continue
        aid = row.get("adapter_id")
        if not (isinstance(aid, str) and aid.strip()):
            errors.append(f"adapters[{index}]: adapter_id must be a non-empty string")
            aid = f"adapters[{index}]"
        elif aid in seen:
            errors.append(f"duplicate adapter {aid}")
        seen.add(aid)
        if type(row.get("installed")) is not bool:
            errors.append(f"{aid}: installed must be a boolean")
        for field, allowed in (("auth_mode", AUTH_MODES), ("funding_mode", FUNDING_MODES)):
            if row.get(field) not in ("unknown", *allowed):
                errors.append(f"{aid}: {field} must be 'unknown' or one of {', '.join(allowed)}; "
                              f"got {row.get(field)!r}")
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
                evidence, moment = cap.get("evidence"), cap.get("observed_at")
                if not (isinstance(evidence, str) and evidence.strip()
                        and isinstance(moment, str) and OBSERVED_AT.fullmatch(moment)):
                    errors.append(f"{aid}.{name}: observed needs a non-empty evidence string "
                                  "and observed_at as YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ")
        configured = row.get("configured")
        if type(configured) is not bool:
            errors.append(f"{aid}: configured must be a boolean")
        elif configured and (tier != 2 or row.get("installed") is not True or observed == 0
                             or row.get("auth_mode") not in AUTH_MODES
                             or row.get("funding_mode") not in FUNDING_MODES):
            errors.append(f"{aid}: configured=true needs tier 2, installed=true, a known auth and "
                          "funding mode and at least one observed capability")
    for section, keys in PRESENCE_KEYS.items():
        entries = manifest.get(section)
        if not isinstance(entries, dict):
            errors.append(f"{section} must be an object")
            continue
        for name, entry in entries.items():
            if not isinstance(entry, dict) or type(entry.get("present")) is not bool:
                errors.append(f"{section}.{name}: record presence as a boolean only")
            elif set(entry) - keys:
                errors.append(f"{section}.{name}: unexpected fields {sorted(set(entry) - keys)}; "
                              "presence records never carry values")
            elif section == "config_presence" and entry.get("opened") is not False:
                errors.append(f"{section}.{name}: config files are never opened")
    environment = manifest.get("environment")
    if not (isinstance(environment, dict) and environment.get("mode") in ("process", "fresh")
            and isinstance(environment.get("removed"), list)
            and all(isinstance(n, str) and ENV_NAME.fullmatch(n) for n in environment["removed"])):
        errors.append("environment must record mode process|fresh and removed variable names only")
    for text in strings(manifest):
        if SECRET.search(text):
            errors.append("manifest contains a secret-like string")
            break
    for text in strings(manifest):
        if USER_PATH.search(text):
            errors.append("manifest contains an unredacted user path")
            break
    return errors


def validate_manifest_v2(manifest: Any) -> list[str]:
    """`runtime-inventory/2` 기록이 규칙을 지키는지 본다(인계 N4). 기록된 관측이 사실인지는 판정하지 않는다.

    칸 다섯 개(core.eligibility.FIELDS)가 모두 있고, observed·failed에는 근거와 날짜가 있어야 한다. 참여자 argv로 본
    세 칸에는 그때의 실행 명세 판(spec_revision)도 있어야 한다. 실행 허가(`eligible_for_run`)와 `configured`는 저장하지
    않는다 — 실행 직전에 core.eligibility가 계산한다.
    """
    errors: list[str] = []
    if not isinstance(manifest, dict) or manifest.get("schema") != eligibility.SCHEMA:
        return [f"schema must be {eligibility.SCHEMA}"]
    host = manifest.get("host")
    if not (isinstance(host, dict) and isinstance(host.get("label"), str) and LABEL.fullmatch(host["label"])):
        errors.append("host.label must be 2-40 chars of a-z, 0-9 and '-'")
    adapters = manifest.get("adapters")
    if not isinstance(adapters, list) or not adapters:
        return errors + ["adapters must be a non-empty list"]
    seen = set()
    for index, row in enumerate(adapters):
        if not isinstance(row, dict):
            errors.append(f"adapters[{index}]: adapter row must be an object")
            continue
        aid = row.get("adapter_id")
        if not (isinstance(aid, str) and aid.strip()):
            errors.append(f"adapters[{index}]: adapter_id must be a non-empty string")
            aid = f"adapters[{index}]"
        elif aid in seen:
            errors.append(f"duplicate adapter {aid}")
        seen.add(aid)
        stored = sorted({"eligible_for_run", "configured"} & set(row))
        if stored:
            errors.append(f"{aid}: {stored} must not be stored; eligibility is computed right before a run")
        # 실행 허가(core.eligibility)와 같은 구조 검사를 쓴다(2026-09-24 리뷰 R02)
        errors += [f"{aid}.{problem}" for problem in eligibility.row_problems(row)]
        auth = row.get("auth_observed") if isinstance(row.get("auth_observed"), dict) else {}
        if auth.get("status") == "observed" and (auth.get("auth_mode") not in AUTH_MODES
                                                 or auth.get("funding_mode") not in FUNDING_MODES):
            errors.append(f"{aid}.auth_observed: observed needs a known auth_mode and funding_mode")
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
    # Windows에서 출력을 파일/파이프로 보내도 한글·기호를 UTF-8로 보존한다.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host-label", help="기기 이름표. 영소문자·숫자·하이픈. 실제 hostname을 쓰지 않는다")
    parser.add_argument("--out", type=Path, help="기본값: docs/experiments/v04-01-inventory/hosts/<label>")
    parser.add_argument("--timeout", type=float, default=20.0, help="명령 하나의 제한 시간(초)")
    parser.add_argument("--dry-run", action="store_true", help="실행할 명령만 출력하고 아무것도 실행하지 않는다")
    parser.add_argument("--force", action="store_true", help="기존 manifest를 덮어쓴다")
    parser.add_argument("--validate", type=Path, metavar="MANIFEST", help="기존 manifest만 검사한다")
    parser.add_argument("--fresh-env", action="store_true",
                        help="Windows 전용. AI 도구 변수와 PATH를 시스템·사용자 설정 값으로 다시 만든 "
                             "환경에서 잰다. AI 도구 안에서 실행할 때 쓴다")
    args = parser.parse_args(argv)

    if args.validate:
        try:
            loaded = json.loads(args.validate.read_text(encoding="utf-8"))
            check = validate_manifest_v2 if isinstance(loaded, dict) and loaded.get("schema") == eligibility.SCHEMA                 else validate_manifest
            errors = check(loaded)
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
    if args.fresh_env and not IS_WINDOWS:
        parser.error("--fresh-env reads the Windows registry and is Windows-only")

    environ: Mapping[str, str] = os.environ
    removed: list[str] | None = None
    if args.fresh_env:
        environ, removed = fresh_environment(os.environ, *registry_environment())
    which = lambda command: shutil.which(command, path=environ.get("PATH"))  # noqa: E731

    if args.dry_run:
        # Windows는 파일 이름의 대소문자를 가리지 않는다. 데스크톱 앱 폴더가 PATH에 있으면
        # 'claude'가 GUI 실행 파일로 풀릴 수 있으므로 실행 전에 실제 경로를 보여 준다.
        redact = make_redactor(str(Path.home()))
        print("실행할 명령 (PATH에 있는 것만 실행된다):")
        for adapter in ADAPTERS:
            resolved = which(adapter.command)
            print(f"  [{adapter.command}] " + (redact(resolved) if resolved else "PATH에 없음 — 실행하지 않음"))
            for args in (adapter.version_args, *adapter.help_args):
                print("    " + " ".join([adapter.command, *args]))
        print("경로가 해당 CLI가 아니면(예: 데스크톱 앱 실행 파일) 실행하지 말고 PATH를 확인한다.")
        print("환경변수는 이름의 존재만, 설정 파일은 경로의 존재만 확인한다. 값과 내용은 읽지 않는다.")
        if removed is not None:
            print(f"--fresh-env: 이 셸에만 있는 AI 도구 변수 {len(removed)}개를 빼고 잰다.")
        return 0

    manifest, outputs = collect(
        args.host_label, timeout=args.timeout, which=which, environ=environ, removed_vars=removed,
        run=lambda argv, timeout: run_probe(argv, timeout, env=environ))
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
