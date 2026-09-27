"""카드 #111 무모델 관측: Codex가 참여자 옵션에서도 ~/.codex/hooks.json을 읽거나 실행하는지 본다.

합성 HOME(로그인 파일 없음 → 모델 호출 불가)에 표식 훅을 두고, 과금 환경변수 없이(환경을 비움) 세 경우를 돌린다:
A. 훅 파일 없음(대조), B. 표식 훅(명령 훅이 표식 파일을 만든다), C. 깨진 JSON(읽으면 오류 문구가 나올 것).
각 경우에 참여자 argv(build_spec — 격리 없이, 합성 HOME이라 읽을 것이 없다)로 `codex exec`, 그리고 `codex debug
prompt-input`을 돌린다. 표식 파일이 생겼는지와 몇 가지 문구가 있는지만 적는다. 출력 원문은 옮기지 않는다.

  python3 docs/reviews/2026-09-27-codex-hooks/probe.py   # WSL·Linux, 저장소 루트, 로그인 셸(bash -l). 모델 호출 없음
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from core import adapters  # noqa: E402

exe = shutil.which("codex")
root = Path(tempfile.mkdtemp(prefix="dml-hookprobe-"))
marks = root / "marks"
marks.mkdir()
(root / "work").mkdir()
EVENTS = ("SessionStart", "UserPromptSubmit", "PreToolUse", "Stop")


def hooks_doc():
    return {"hooks": {ev: [{"matcher": "*", "hooks": [{"type": "command", "command": f"touch {marks}/{ev}"}]}]
                      for ev in EVENTS}}


def run(case: str, argv: list[str], home: Path) -> dict:
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin:" + os.path.dirname(exe), "LANG": "C.UTF-8"}
    try:
        p = subprocess.run(argv, input="Say hi.", capture_output=True, text=True, env=env, timeout=60,
                           cwd=str(root / "work"))
        text, code = (p.stdout + "\n" + p.stderr).lower(), p.returncode
    except subprocess.TimeoutExpired:
        text, code = "", "timeout"
    fired = sorted(x.name for x in marks.iterdir())
    for x in marks.iterdir():
        x.unlink()
    return {"case": case, "exit": code, "hook_markers_fired": fired,
            "hooks_parse_error": "failed to parse hooks config" in text,
            "login_or_auth_mentioned": any(w in text for w in ("login", "log in", "auth", "401"))}


results = []
for case in ("A-none", "B-marker-hooks", "C-broken-json"):
    home = root / f"home-{case}"
    (home / ".codex").mkdir(parents=True)
    if case == "B-marker-hooks":
        (home / ".codex" / "hooks.json").write_text(json.dumps(hooks_doc()), encoding="utf-8")
    elif case == "C-broken-json":
        (home / ".codex" / "hooks.json").write_text("{ this is not json", encoding="utf-8")
    argv = list(adapters.build_spec("codex", exe=exe, prompt="-", model="gpt-6-luna", codex_user_home=str(home)).argv)
    results.append(run(case + " exec(participant argv)", argv, home))
    results.append(run(case + " debug prompt-input", [exe, "debug", "prompt-input", "Say hi."], home))
print(json.dumps({"codex": subprocess.run([exe, "--version"], capture_output=True, text=True).stdout.strip(),
                  "participant_flags": [a for a in argv if a.startswith("--")], "results": results},
                 ensure_ascii=False, indent=1))
shutil.rmtree(root, ignore_errors=True)
