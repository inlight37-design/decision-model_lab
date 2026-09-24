"""N3: 격리 안에서 로그인 상태가 되려면 어떤 인증·설정 파일이 보여야 하는지 본다(K09). 모델을 부르지 않는다.

각 CLI마다 연결하는 인증·설정 경로의 조합을 바꿔 가며 격리 안에서 `--version`과 로그인 상태 명령만 실행한다.
좁힌 조합은 모두 **읽기 전용**으로 연결한다 — 사용자 파일을 바꾸지 않는다. 기준 조합(지금의 cli_mounts: 설정
폴더 전체를 쓰기로)만 쓰기다. 계정 이메일·조직 ID·요금제는 버리고 로그인 여부와 방식만 남긴다(cli_boundary와
같은 규칙). 토큰 갱신에 필요한 쓰기는 모델을 불러야 드러나므로 여기서는 보지 않는다(2단계).

  python3 tools/w2/auth_mounts.py      # WSL 로그인 셸(bash -l)에서, 저장소 루트에서
결과: docs/experiments/w2-isolation/
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core import env as core_env, isolation  # noqa: E402
from tools.w2.cli_boundary import STATUS, status_summary  # noqa: E402
from tools.redaction import scrub, scrub_all  # noqa: E402

HOME = os.path.expanduser("~")
SANDBOX_ENV = {"LANG": "C.UTF-8", "NO_COLOR": "1"}
# (이름, 연결할 경로). None은 지금의 cli_mounts(설정 폴더를 쓰기로)를 그대로 쓴다. 나머지는 모두 읽기 전용이다.
CASES = {
    "claude-code": (
        ("current: rw ~/.claude, ~/.claude.json", None),
        ("ro ~/.claude, ~/.claude.json", ("~/.claude", "~/.claude.json")),
        ("ro ~/.claude/.credentials.json, ~/.claude.json", ("~/.claude/.credentials.json", "~/.claude.json")),
        ("ro ~/.claude/.credentials.json", ("~/.claude/.credentials.json",)),
        ("ro ~/.claude.json", ("~/.claude.json",)),
        ("nothing", ()),
    ),
    "codex": (
        ("current: rw ~/.codex", None),
        ("ro ~/.codex", ("~/.codex",)),
        ("ro ~/.codex/auth.json", ("~/.codex/auth.json",)),
        ("ro ~/.codex/auth.json, ~/.codex/config.toml", ("~/.codex/auth.json", "~/.codex/config.toml")),
        ("nothing", ()),
    ),
}
# stderr에서 쓰기 실패·인증 문제로 볼 줄. 요약에는 줄 앞부분만, HOME은 ~로 옮긴다.
HINT = re.compile(r"(?i)read-only|EROFS|permission|denied|not logged|login|auth|credential|token|error")


def tilde(path: str) -> str:
    return scrub(path, HOME)


def hide(text: str) -> str:
    """출력 글에서 HOME은 ~로, 이메일 모양과 긴 토큰 모양 문자열은 지운다. 오류 줄에 값이 섞여 나와도 옮기지 않는다."""
    return scrub(text, HOME, opaque_tokens=True)


def case_mounts(adapter_id: str, exe: str, paths) -> tuple[tuple[str, ...], tuple[str, ...]]:
    ro_cli, rw_cli = isolation.cli_mounts(adapter_id, exe, HOME)
    if paths is None:
        return ro_cli, rw_cli
    extra = tuple(os.path.expanduser(p) for p in paths if os.path.lexists(os.path.expanduser(p)))
    return ro_cli + extra, ()


def observe_case(adapter_id: str, exe: str, label: str, paths) -> dict:
    ro, rw = case_mounts(adapter_id, exe, paths)
    work = tempfile.mkdtemp(prefix="dml-n3-")
    try:
        box = isolation.Sandbox(work_dir=work, home=HOME, read_only=ro, read_write=rw, env=SANDBOX_ENV)
        version = isolation.run([exe, "--version"], box, timeout=60)
        status = isolation.run([exe, *STATUS[adapter_id]], box, timeout=60)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    missing = [p for p in (paths or ()) if not os.path.lexists(os.path.expanduser(p))]
    return {
        "case": label, "read_only": [tilde(p) for p in ro], "read_write": [tilde(p) for p in rw], "missing": missing,
        "version_exit": version.exit_code, "version_state": version.state,
        "status_state": status.state, "status_exit": status.exit_code,
        "tree_confirmed_empty": status.tree_confirmed_empty,
        "status": {k: hide(v) if isinstance(v, str) else v for k, v in status_summary(adapter_id, status).items()},
        "stderr_hints": [hide(line)[:160] for line in status.stderr.splitlines() if HINT.search(line)][:6],
    }


def main() -> int:
    if sys.platform != "linux":
        print("Linux·WSL에서만 돈다", file=sys.stderr)
        return 2
    child, _ = core_env.child_env(os.environ)
    report = {"bwrap": shutil.which("bwrap"), "cli": {}}
    for adapter_id, command in (("claude-code", "claude"), ("codex", "codex")):
        try:
            exe = core_env.resolve(command, child)
        except core_env.EnvError as exc:
            report["cli"][adapter_id] = {"refused": str(exc)}
            continue
        report["cli"][adapter_id] = [observe_case(adapter_id, exe, label, paths) for label, paths in CASES[adapter_id]]
    print(json.dumps(scrub_all(report, HOME), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
