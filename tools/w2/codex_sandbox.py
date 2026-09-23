"""K12: Codex 자체 Linux 샌드박스가 우리 bubblewrap 안에서 서는지 본다. 모델을 부르지 않는다.

참여자와 같은 경계(core.isolation, Codex의 cli_mounts와 읽기 전용 공통 자료 폴더)를 만들고 그 안에서
`codex sandbox -- /bin/sh -c ...`를 실행한다. `codex sandbox`는 Codex의 Linux 샌드박스로 명령 하나를 돌리는 하위
명령이다(0.156.1 help). 셸은 작업 폴더에 파일 쓰기, 공통 자료 읽기, /tmp 쓰기를 해 보고 결과를 찍는다.

- 쓰기가 "Read-only file system"으로 막히고 읽기는 되면: 중첩된 Codex 샌드박스가 서서 쓰기를 막는다.
- namespace·bwrap 오류로 셸이 돌지 못하면: 중첩이 안 된다.
- 쓰기가 되면: Codex 샌드박스가 쓰기를 막지 않았다(우리 경계의 작업 폴더는 쓰기 가능이다).

한계: `codex exec`가 모델의 명령을 돌린 것이 아니라 같은 샌드박스를 직접 부른 것이다. exec의 read-only 정책과
같다는 것은 `-c sandbox_mode="read-only"` 변형이 같은 결과를 내는 데까지만 본다.

  python3 tools/w2/codex_sandbox.py           # WSL·Linux에서, 저장소 루트에서, 로그인 셸(bash -l)로
결과: docs/experiments/w2-isolation/stage2-aux-pc-wsl.md
"""
import json, os, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core import env as core_env, isolation  # noqa: E402

HOME = os.path.expanduser("~")
VARIANTS = {"default": [], "read-only via -c": ["-c", 'sandbox_mode="read-only"']}


def main():
    child, _ = core_env.child_env(os.environ)
    exe = core_env.resolve("codex", child)
    ro, rw = isolation.cli_mounts("codex", exe, HOME)
    report = {"codex": os.path.realpath(exe).replace(HOME, "~"), "variants": {}}
    for name, extra in VARIANTS.items():
        root = tempfile.mkdtemp(prefix="dml-w2-k12-")
        work, inputs = os.path.join(root, "work"), os.path.join(root, "input")
        os.mkdir(work)
        os.mkdir(inputs)
        Path(inputs, "allowed.txt").write_text("AL-3K readable\n", encoding="utf-8")
        script = (f"echo x > created.txt; echo write_rc=$?; head -n1 {inputs}/allowed.txt; echo read_rc=$?; "
                  "touch /tmp/t; echo tmp_rc=$?")
        box = isolation.Sandbox(work_dir=work, home=HOME, read_only=ro + (inputs,), read_write=rw,
                                env={"LANG": "C.UTF-8", "NO_COLOR": "1"})
        result = isolation.run([exe, "sandbox", *extra, "--", "/bin/sh", "-c", script], box, timeout=60)
        out = result.stdout.replace(HOME, "~")
        report["variants"][name] = {
            "state": result.state, "exit": result.exit_code, "tree_confirmed_empty": result.tree_confirmed_empty,
            "write_refused": "write_rc=0" not in out and not os.path.exists(os.path.join(work, "created.txt")),
            "read_ok": "AL-3K readable" in out, "stdout": out.splitlines()[:10],
            "stderr": result.stderr.replace(HOME, "~").splitlines()[:10],
        }
        shutil.rmtree(root, ignore_errors=True)
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
