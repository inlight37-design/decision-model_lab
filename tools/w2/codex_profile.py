"""K46: 참여자의 Codex 권한 profile(core.adapters.codex_permissions)을 모델 없이 본다.

1. sandbox — `codex sandbox`에 그 profile을 exec와 같은 방식(`-c default_permissions=…`, `-P` 없이)으로 준다.
   명령이 인증 파일을 열 수 있는지, 작업 폴더 쓰기가 막히는지, 공통 자료가 읽히는지. 비교로 profile 없는 기본값과
   2026-09-24 진단의 `-P` 방식도 돈다.
2. exec(네트워크 없음) — 참여자의 실제 exec argv(CliExecutor.prepare)를 **새 네트워크 namespace**의 격리에서 돌린다.
   loopback만 있어 모델에 닿을 수 없다 — 사용량을 쓰지 않는다. 설정을 받아들이고 연결 단계까지 가는지, 없는 profile
   이름을 주면 연결 전에 끝나는지(observe.py p3-codex의 근거), 사람용 출력의 머리글이 샌드박스를 무엇으로 보이는지.

exec가 모델이 돌린 명령에 이 금지를 적용하는지는 여기서 볼 수 없다 — 승인된 호출(observe.py k46-codex)이 본다.
인증 파일의 내용은 출력하지 않는다. 명령은 종료 코드만 찍고, 도구는 실행 전후의 크기·수정 시각이 같은지만 본다.

  python3 tools/w2/codex_profile.py        # WSL·Linux에서, 저장소 루트에서, 로그인 셸(bash -l)로
"""
import json, os, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.cli_executor import CliExecutor  # noqa: E402
from app.controller import CLI, ParticipantSpec  # noqa: E402
from core import adapters, isolation, runner  # noqa: E402
from tools.w2.observe import AUTH_CHECK, _scrub  # noqa: E402

HOME = os.path.realpath(os.path.expanduser("~"))
AUTH = os.path.join(HOME, adapters.CODEX_AUTH_FILE)
MODEL = "gpt-6-luna"  # argv에만 쓴다. 네트워크가 없어 모델에 닿지 않는다


def _auth_stat():
    try:
        info = os.stat(AUTH)
    except OSError:
        return None
    return info.st_size, info.st_mtime_ns


def _folders(root):
    work, inputs = os.path.join(root, "work"), os.path.join(root, "input")
    os.mkdir(work)
    os.mkdir(inputs)
    Path(inputs, "allowed.txt").write_text("AL-3K readable\n", encoding="utf-8")
    return work, inputs


def _lines(text, limit):
    return [_scrub(line, HOME)[:240] for line in text.splitlines() if line.strip()][:limit]


def sandbox_variants(exe, ro, rw):
    define, select = adapters.codex_permissions(HOME)
    variants = {"no profile (default)": [],
                "profile via default_permissions (exec's way)": ["-c", define, "-c", select],
                "profile via -P (2026-09-24 diagnostic)": ["-c", define, "-P", adapters.CODEX_PROFILE]}
    out = {}
    for name, extra in variants.items():
        root = tempfile.mkdtemp(prefix="dml-k46-")
        try:
            work, inputs = _folders(root)
            box = isolation.Sandbox(work_dir=work, home=HOME, read_only=ro + (inputs,), read_write=rw,
                                    env={"LANG": "C.UTF-8", "NO_COLOR": "1"})
            shell = AUTH_CHECK.format(allowed=os.path.join(inputs, "allowed.txt"))  # observe.py k46-codex와 같은 명령
            result = isolation.run([exe, "sandbox", *extra, "--", "/bin/sh", "-c", shell], box, timeout=60)
            values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "_rc=" in line)
            out[name] = {"state": result.state, "exit": result.exit_code,
                         "tree_confirmed_empty": result.tree_confirmed_empty,
                         "write_refused": values.get("write_rc") not in (None, "0")
                         and not os.path.exists(os.path.join(work, "created.txt")),
                         **values, "stderr": _lines(result.stderr, 6)}
        finally:
            shutil.rmtree(root, ignore_errors=True)
    return out


def offline(argv, box, stdin_text, timeout):
    """box 안에서 argv를 네트워크 없이 한 번 돌린다. isolation.run과 같고 `--share-net`만 뺀다."""
    args, env = isolation.plan(argv, box)
    args.remove("--share-net")
    assert "--unshare-all" in args and "--share-net" not in args  # 새 네트워크 namespace: loopback만 있다
    isolation._trusted_bwrap()
    return runner._execute(runner.validate_argv(args), cwd=os.path.realpath(box.work_dir), env=env, timeout=timeout,
                           stdin_text=stdin_text, max_output_bytes=runner.DEFAULT_MAX_OUTPUT, cancel=None,
                           pid_namespace=True)


def exec_variants(executor):
    spec = ParticipantSpec("k46", "k46", "codex", CLI, "codex", MODEL)
    select = adapters.codex_permissions(HOME)[1]
    out = {}
    for name in ("participant --json", "participant, human output", "undefined profile --json",
                 "legacy --sandbox read-only, human output"):
        root = tempfile.mkdtemp(prefix="dml-k46-exec-")
        try:
            work, _inputs = _folders(root)
            planned, box = executor.prepare(spec, "Reply with exactly: OK", work)
            argv = list(planned.argv)
            if name.startswith("legacy"):
                argv = list(adapters.build_spec("codex", exe=argv[0], prompt="Reply with exactly: OK", model=MODEL).argv)
            if "human output" in name:
                argv.remove("--json")
            if name.startswith("undefined"):
                argv[argv.index(select)] = 'default_permissions="notamode"'
            before = _auth_stat()
            result = offline(argv, box, planned.stdin_text, timeout=90)
            events = []
            for line in result.stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict):
                    events.append(event.get("type"))
            out[name] = {"argv_tail": [_scrub(a, HOME) for a in argv[2:]], "state": result.state,
                         "exit": result.exit_code, "duration_ms": result.duration_ms,
                         "tree_confirmed_empty": result.tree_confirmed_empty, "jsonl_types": events[:20],
                         "stdout_text": [s for s in _lines(result.stdout, 40) if not s.startswith("{")][:20],
                         "stderr": _lines(result.stderr, 30), "auth_file_unchanged": _auth_stat() == before}
        finally:
            shutil.rmtree(root, ignore_errors=True)
    return out


def main():
    executor = CliExecutor(never=(), unchecked=True, home=HOME)
    exe = adapters.resolve("codex", executor.child_env)
    ro, rw = isolation.cli_mounts("codex", exe, HOME)
    report = {"codex": _scrub(os.path.realpath(exe), HOME), "sandbox": sandbox_variants(exe, ro, rw),
              "exec_offline": exec_variants(executor)}
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
