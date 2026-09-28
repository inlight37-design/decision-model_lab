"""카드 #111 후속(사용자 허락 2026-09-27): 실제 로그인 HOME에서 참여자와 같은 격리·argv로 Codex를 한 번 부를 때
사용자 훅(~/.codex/hooks.json)이 실제로 실행되는지 본다. 모델 호출 1회(구독).

- 실행 전에 ~/.codex/hooks.json이 없음을 확인하고, 없을 때만 표식 훅 파일을 새로 만든다(있으면 아무것도 하지 않는다).
- 호출이 끝나면(실패해도, SIGTERM·SIGHUP·SIGINT를 받아도) **이 스크립트가 만든 그 파일일 때만** 지우고 지워졌는지
  확인한다. SIGKILL처럼 막을 수 없는 강제 종료 뒤에는 남을 수 있다 — 그때는 사람이 ~/.codex/hooks.json을 지운다.
  로그인 파일은 읽거나 옮기지 않는다.
- 표식 훅은 이 호출의 빈 작업 폴더에 빈 파일을 만들 뿐이다. 출력 원문은 옮기지 않고 몇 가지 사실만 적는다.

  python3 docs/reviews/2026-09-27-codex-hooks-live/probe_live.py   # WSL 로그인 셸, 저장소 루트. 모델 호출 1회
"""
import json, os, shutil, signal, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from app.cli_executor import SANDBOX_ENV  # noqa: E402
from core import adapters, env as core_env, isolation  # noqa: E402

MODEL = "gpt-6-luna"
EVENTS = ("SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop")
HOME = os.path.realpath(os.path.expanduser("~"))
hooks = Path(HOME, ".codex", "hooks.json")
if os.path.lexists(hooks):
    print(json.dumps({"refused": "~/.codex/hooks.json already exists; not touching it"}))
    sys.exit(2)
child, _ = core_env.child_env(os.environ)
exe = os.path.realpath(core_env.resolve("codex", child))
root = Path(tempfile.mkdtemp(prefix="dml-hook-live-"))
work = root / "work"
work.mkdir()
doc = {"hooks": {ev: [{"matcher": "*", "hooks": [{"type": "command", "command": f"touch {work}/hook-{ev}"}]}]
                 for ev in EVENTS}}
spec = adapters.build_spec("codex", exe=exe, prompt="Reply with the single word OK.", model=MODEL, codex_user_home=HOME)
ro, rw, ro_at = isolation.participant_mounts("codex", exe, HOME)
box = isolation.Sandbox(work_dir=str(work), home=HOME, read_only=ro, read_write=rw, env=SANDBOX_ENV, read_only_at=ro_at)
def _stop(number, _frame):   # 보통의 종료 신호도 finally를 지나게 한다
    raise SystemExit(128 + number)


for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
    signal.signal(number, _stop)
result, created = None, None
try:
    fd = os.open(hooks, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)   # 없을 때만 만든다 — 있으면 여기서 실패한다
    created = os.fstat(fd)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(doc, handle)
    result = isolation.run(list(spec.argv), box, timeout=180, stdin_text=spec.stdin_text, max_output_bytes=2_000_000,
                           stderr_marks=adapters.STDERR_MARKS.get("codex", ()))
finally:
    # 이 스크립트가 만든 바로 그 파일일 때만 지운다 — 그 사이 다른 쪽이 만든 파일은 건드리지 않는다
    try:
        now = os.lstat(hooks)
    except FileNotFoundError:
        now = None
    if created is not None and now is not None and (now.st_dev, now.st_ino) == (created.st_dev, created.st_ino):
        hooks.unlink()
outcome = adapters.interpret("codex", result, requested_model=MODEL)
fired = sorted(p.name for p in work.iterdir() if p.name.startswith("hook-"))
text = (result.stdout + "\n" + result.stderr).lower()
report = {"codex_release": os.path.basename(os.path.dirname(os.path.dirname(exe))),
          "participant_flags": [a for a in spec.argv if a.startswith("--")],
          "state": result.state, "exit": result.exit_code, "tree_confirmed_empty": result.tree_confirmed_empty,
          "ok": outcome.ok, "status": outcome.status, "answer_is_ok": (outcome.text or "").strip().rstrip(".").upper() == "OK",
          "hook_marker_files": fired,
          "output_mentions_hook": "hook" in text, "output_mentions_trust": "trust" in text,
          "hooks_file_removed": not os.path.lexists(hooks), "usage_reported": bool(outcome.usage)}
shutil.rmtree(root, ignore_errors=True)
print(json.dumps(report, ensure_ascii=False, indent=1))
