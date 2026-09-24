"""E2: Codex가 모델 입력에 싣는 지시문을 모델 없이 본다(`codex debug prompt-input`, 0.156.1 help: "Render the
model-visible prompt input list as JSON"). 모델에 요청을 보내지 않는다.

1. 합성 HOME(로그인 파일 없음)의 양성 대조: 전역 `~/.codex/AGENTS.md`와 작업 폴더 `AGENTS.md`에 시도마다 새 표식을
   넣고, 기본값·`-c project_doc_max_bytes=0`·빈 전역 파일에서 두 표식이 입력에 실리는지 본다.
2. --real-home — 사용자의 실제 `~/.codex`를 연결한다(NEXT-SESSION 2절 22의 상시 승인 뒤에만). 참여자 계획과 같은 격리·
   같은 `-c` 값(권한 profile, 연결 앱 끄기)·같은 실행 위치(isolation.participant_mounts)로 빈 작업 폴더에서 렌더링하고,
   같은 값의 합성 HOME 결과와 비교한다. 줄 단위 차이의 수와 종류만 적고 렌더링한 글은 옮기지 않는다.

한계(2026-09-24 codex 세션의 C3 조사, docs/reviews/2026-09-24-cli-readiness/GITHUB-C3.md): 이 출력은 최종 요청 전체가
아니다 — 도구 schema가 없고, exec 전용 옵션(`--ignore-user-config`·`--ignore-rules`·`--ephemeral`)을 받지 않는다. 이 PC에는
사용자 config.toml이 없어 첫 옵션의 차이는 없다. 표식 부재는 "이 경로로 실리지 않았다"까지만 뜻한다.

  python3 tools/w2/codex_prompt_input.py [--real-home]   # WSL·Linux에서, 저장소 루트에서, 로그인 셸(bash -l)로
"""
import argparse, difflib, json, os, re, secrets, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.cli_executor import SANDBOX_ENV  # noqa: E402
from core import adapters, env as core_env, isolation  # noqa: E402

HOME = os.path.realpath(os.path.expanduser("~"))
MSG_ID = re.compile(r"^msg_[0-9a-f-]{20,}$")


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def participant_values(home: str) -> list[str]:
    """참여자 exec argv의 `-c` 값 그대로. build_spec에서 뽑으므로 계획이 바뀌면 함께 바뀐다."""
    argv = adapters.build_spec("codex", exe="/opt/dml-codex/bin/codex", prompt="-", model="m",
                               codex_user_home=home).argv
    return [x for i, a in enumerate(argv) if a == "-c" for x in ("-c", argv[i + 1])]


def render(exe: str, home: str, work: str, extra: list[str]) -> tuple[dict, str | None]:
    """참여자와 같은 격리에서 한 번 렌더링한다. (요약, 모든 글을 이은 문자열)."""
    ro, rw, ro_at = isolation.participant_mounts("codex", exe, home)
    box = isolation.Sandbox(work_dir=work, home=home, read_only=ro, read_write=rw, env=SANDBOX_ENV,
                            read_only_at=ro_at)
    result = isolation.run([exe, "debug", "prompt-input", *extra, "Say hi."], box, timeout=90,
                           max_output_bytes=2_000_000)
    out = {"state": result.state, "exit": result.exit_code, "tree_confirmed_empty": result.tree_confirmed_empty}
    try:
        items = json.loads(result.stdout)
    except ValueError:
        return {**out, "json": False, "stderr_lines": len(result.stderr.splitlines())}, None
    shapes = []
    for item in items if isinstance(items, list) else []:
        texts = list(_strings(item.get("content"))) if isinstance(item, dict) else []
        tags = sorted({t for s in texts for t in re.findall(r"<([A-Za-z_][A-Za-z_ ]{2,40})>", s)})
        shapes.append({"role": item.get("role") if isinstance(item, dict) else None,
                       "chars": sum(map(len, texts)), "tags": tags})
    text = "\n".join(_strings(items))
    # AGENTS.md 내용은 <INSTRUCTIONS> 묶음으로 실렸다(합성 HOME 양성 대조, 2026-09-25)
    return {**out, "json": True, "items": shapes, "instructions_block": "<INSTRUCTIONS>" in text}, text


def synthetic_controls(exe: str) -> dict:
    """합성 HOME에서 전역·작업 폴더 AGENTS.md 표식이 실리는지(양성 대조)."""
    marks = {"global": "GLB-" + secrets.token_hex(3).upper(), "project": "PRJ-" + secrets.token_hex(3).upper()}
    root = tempfile.mkdtemp(prefix="dml-prompt-controls-")
    try:
        home, work = os.path.join(root, "home"), os.path.join(root, "work")
        os.makedirs(os.path.join(home, ".codex"))
        os.makedirs(work)
        global_file = os.path.join(home, ".codex", "AGENTS.md")
        Path(global_file).write_text(f"# Global notes\nGlobal marker word: {marks['global']}\n", encoding="utf-8")
        Path(work, "AGENTS.md").write_text(f"# Project notes\nProject marker word: {marks['project']}\n", encoding="utf-8")
        report = {}
        for name, extra in (("default", []), ("project_doc_max_bytes=0", ["-c", "project_doc_max_bytes=0"])):
            summary, text = render(exe, home, work, extra)
            report[name] = {**summary, **{f"{k}_marker": text is not None and v in text for k, v in marks.items()}}
        Path(global_file).write_text("", encoding="utf-8")
        summary, text = render(exe, home, work, [])
        report["empty global file"] = {**summary, **{f"{k}_marker": text is not None and v in text
                                                     for k, v in marks.items()}}
        return report
    finally:
        shutil.rmtree(root, ignore_errors=True)


def real_home_comparison(exe: str) -> dict:
    """참여자 계획의 값으로 실제 HOME과 합성 HOME을 렌더링해 비교한다. 줄 차이는 수와 종류만."""
    root = tempfile.mkdtemp(prefix="dml-prompt-real-")
    try:
        work, synth = os.path.join(root, "work"), os.path.join(root, "home")
        os.makedirs(work)
        os.makedirs(os.path.join(synth, ".codex"))
        s_summary, s_text = render(exe, synth, work, participant_values(synth))
        r_summary, r_text = render(exe, HOME, work, participant_values(HOME))
        report = {"synthetic_home": s_summary, "real_home": r_summary}
        if s_text is not None and r_text is not None:
            a = [line.replace(synth, "<HOME>") for line in s_text.splitlines() if line.strip()]
            b = [line.replace(HOME, "<HOME>") for line in r_text.splitlines() if line.strip()]
            kinds: dict[str, dict[str, int]] = {}
            for line in difflib.unified_diff(a, b, lineterm="", n=0):
                if line[:1] not in "+-" or line[:3] in ("+++", "---"):
                    continue
                body = line[1:].strip()
                kind = ("message id" if MSG_ID.match(body) else "path" if "<HOME>" in body or root in body
                        else "other")
                side = "only_real" if line.startswith("+") else "only_synthetic"
                kinds.setdefault(kind, {"only_real": 0, "only_synthetic": 0})[side] += 1
            report["line_differences"] = kinds
        return report
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--real-home", action="store_true",
                    help="also render with the user's real ~/.codex (standing approval, NEXT-SESSION 2.22)")
    args = ap.parse_args(argv)
    child, _ = core_env.child_env(os.environ)
    exe = os.path.realpath(core_env.resolve("codex", child))
    report = {"codex_release": os.path.basename(os.path.dirname(os.path.dirname(exe))),
              "synthetic_controls": synthetic_controls(exe)}
    if args.real_home:
        report["participant_values"] = real_home_comparison(exe)
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
