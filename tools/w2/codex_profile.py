"""K46: 참여자의 Codex 권한 profile(core.adapters.codex_permissions)을 모델 없이 본다.

기본 — 합성 HOME. 사용자의 로그인 상태를 연결하지 않는다(2026-09-24 리뷰 질문 3·9).
  가짜 `~/.codex/auth.json`을 둔 합성 HOME에서 `codex sandbox`로 observe.py `k46-codex`와 같은 helper를 돌린다. profile
  없는 기본값(대조군: 인증 파일이 열려야 한다)과 exec 방식(`default_permissions`)·`-P` 방식의 profile을 비교한다. helper의
  결과는 errno 이름이라 profile이 막을 때 무엇이 나오는지(EACCES·EPERM인지, ENOENT인지) 알 수 있다 — k46-codex의 합격
  조건이 그것에 기댄다. 네트워크 없는 격리에서 돈다.

--real-home — **사용자 허락 뒤에만.** 사용자의 실제 `~/.codex`(로그인 파일 포함)를 연결한다.
  1. 같은 helper를 실제 HOME에서(기본값, `default_permissions`, `-P`).
  2. 참여자의 실제 exec argv를 네트워크 없는 격리에서: 설정을 받아들이는지, 없는 profile을 연결 전에 거절하는지, 사람용
     머리글이 무엇을 보이는지. 모델에 닿을 수 없지만 로컬 상태·캐시·로그는 바뀔 수 있다. 인증 파일은 크기·수정 시각만
     전후로 비교한다 — 내용이 같다는 증명은 아니다(리뷰 R07).

exec가 모델이 돌린 명령에 이 금지를 적용하는지는 여기서 볼 수 없다 — 승인된 호출(observe.py k46-codex)이 본다.

  python3 tools/w2/codex_profile.py [--real-home]   # WSL·Linux에서, 저장소 루트에서, 로그인 셸(bash -l)로
결과: docs/experiments/w2-isolation/k46-profile-aux-pc-wsl.md(실제 HOME, 2026-09-24),
      docs/experiments/w2-isolation/k46-synthetic-aux-pc-wsl.md(합성 HOME)
"""
import argparse, json, os, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.cli_executor import SANDBOX_ENV, CliExecutor  # noqa: E402
from app.controller import CLI, ParticipantSpec  # noqa: E402
from core import adapters, isolation, runner  # noqa: E402
from tools.w2.observe import K46_FILE, K46_HELPER, K46_LINE, _scrub  # noqa: E402

HOME = os.path.realpath(os.path.expanduser("~"))
MODEL = "gpt-6-luna"  # argv에만 쓴다. 네트워크가 없어 모델에 닿지 않는다
FAKE_AUTH = '{"synthetic": "not a credential"}\n'


def _auth_stat(home):
    try:
        info = os.stat(os.path.join(home, adapters.CODEX_AUTH_FILE))
    except OSError:
        return None
    return info.st_size, info.st_mtime_ns


def _folders(root):
    work, inputs = os.path.join(root, "work"), os.path.join(root, "input")
    os.mkdir(work)
    os.mkdir(inputs)
    Path(inputs, "allowed.txt").write_text("AL-3K readable\n", encoding="utf-8")
    Path(inputs, K46_FILE).write_text(K46_HELPER.format(nonce="diagnostic"), encoding="utf-8")
    return work, inputs


def _lines(text, limit, home=HOME):
    return [_scrub(line, home)[:240] for line in text.splitlines() if line.strip()][:limit]


def offline(argv, box, stdin_text, timeout):
    """box 안에서 argv를 네트워크 없이 한 번 돌린다. isolation.run과 같고 `--share-net`만 뺀다."""
    args, env = isolation.plan(argv, box)
    args.remove("--share-net")
    assert "--unshare-all" in args and "--share-net" not in args  # 새 네트워크 namespace: loopback만 있다
    isolation._trusted_bwrap()
    return runner._execute(runner.validate_argv(args), cwd=os.path.realpath(box.work_dir), env=env, timeout=timeout,
                           stdin_text=stdin_text, max_output_bytes=runner.DEFAULT_MAX_OUTPUT, cancel=None,
                           pid_namespace=True)


def profile_variants(home):
    define, select = adapters.codex_permissions(home)
    return {"no profile (control)": [],
            "profile via default_permissions (exec's way)": ["-c", define, "-c", select],
            "profile via -P": ["-c", define, "-P", adapters.CODEX_PROFILE]}


def helper_variants(exe, home, read_write):
    """`codex sandbox -- python3 <helper>`를 변형마다 한 번. read_write는 격리 안에 쓰기로 연결할 설정 폴더다.
    실행 버전 폴더는 참여자처럼 HOME 밖에 보인다(isolation.participant_mounts) — profile이 `~/.codex` 전체를 막는다."""
    out = {}
    release = os.path.dirname(os.path.dirname(os.path.realpath(exe)))
    for name, extra in profile_variants(home).items():
        root = tempfile.mkdtemp(prefix="dml-k46-")
        try:
            work, inputs = _folders(root)
            box = isolation.Sandbox(work_dir=work, home=home, read_only=(inputs,), read_write=read_write,
                                    env=SANDBOX_ENV, read_only_at=((release, isolation.CODEX_RELEASE_AT),))
            before = _auth_stat(home)
            result = offline([exe, "sandbox", *extra, "--", "/usr/bin/python3", os.path.join(inputs, K46_FILE)],
                             box, None, timeout=60)
            lines = [m.groups() for line in result.stdout.splitlines() if (m := K46_LINE.match(line.strip()))]
            out[name] = {"state": result.state, "exit": result.exit_code,
                         "tree_confirmed_empty": result.tree_confirmed_empty,
                         "result": dict(zip(("write", "input", "auth", "home"), lines[0][1:])) if len(lines) == 1 else None,
                         "created_txt_left": os.path.exists(os.path.join(work, "created.txt")),
                         "auth_size_mtime_unchanged": _auth_stat(home) == before,
                         "stderr": _lines(result.stderr, 6, home)}
        finally:
            shutil.rmtree(root, ignore_errors=True)
    return out


def synthetic(exe):
    """합성 HOME: 가짜 인증 파일 하나만 있는 `~/.codex`. 사용자의 실제 `~/.codex`는 연결하지 않는다."""
    root = tempfile.mkdtemp(prefix="dml-k46-home-")
    try:
        home = os.path.realpath(os.path.join(root, "home"))
        os.makedirs(os.path.join(home, ".codex"))
        Path(home, adapters.CODEX_AUTH_FILE).write_text(FAKE_AUTH, encoding="utf-8")
        return {"home": "synthetic", "helper": helper_variants(exe, home, (os.path.join(home, ".codex"),))}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def exec_variants(executor):
    spec = ParticipantSpec("k46", "k46", "codex", CLI, "codex", MODEL)
    select = adapters.codex_permissions(HOME)[1]
    out = {}
    for name in ("participant --json", "participant, human output", "undefined profile --json",
                 "legacy --sandbox read-only, human output"):
        root = tempfile.mkdtemp(prefix="dml-k46-exec-")
        try:
            work, _inputs = _folders(root)
            planned = executor.plan(spec, "Reply with exactly: OK", work)
            box, argv = planned.box, list(planned.spec.argv)
            if name.startswith("legacy"):
                argv = list(adapters.build_spec("codex", exe=argv[0], prompt="Reply with exactly: OK", model=MODEL).argv)
            if "human output" in name:
                argv.remove("--json")
            if name.startswith("undefined"):
                argv[argv.index(select)] = 'default_permissions="notamode"'
            before = _auth_stat(HOME)
            result = offline(argv, box, planned.spec.stdin_text, timeout=90)
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
                         "stderr": _lines(result.stderr, 30), "auth_size_mtime_unchanged": _auth_stat(HOME) == before}
        finally:
            shutil.rmtree(root, ignore_errors=True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--real-home", action="store_true",
                    help="also run against the user's real ~/.codex (only after the user agreed)")
    args = ap.parse_args(argv)
    executor = CliExecutor(never=(), unchecked=True, home=HOME)
    exe = adapters.resolve("codex", executor.child_env)
    report = {"codex": _scrub(os.path.realpath(exe), HOME), "synthetic": synthetic(exe)}
    if args.real_home:
        _ro, rw = isolation.cli_mounts("codex", exe, HOME)
        report["real_home"] = {"helper": helper_variants(exe, HOME, rw), "exec_offline": exec_variants(executor)}
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
