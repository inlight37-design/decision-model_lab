"""W2: 설치된 Claude Code·Codex가 core.isolation의 bubblewrap 안에서 도는지 본다. 모델을 부르지 않는다.

각 CLI마다 참여자 경계(자기 설정·인증 폴더와 실행 파일만)를 만들고 안에서 실행한다.
  1. `--version`
  2. 로그인 상태(`claude auth status`, `codex login status`) — 모델 호출이 아니다. 계정 이메일·조직 ID·요금제는
     출력에서 버리고 로그인 여부와 방식만 남긴다
  3. python 탐침: 자기 인증 파일, 다른 CLI의 인증 파일, HOME의 다른 파일, /mnt/c가 **보이는지만** 본다(열지 않는다)

  python3 tools/w2/cli_boundary.py            # WSL·Linux에서, 저장소 루트에서
결과: docs/experiments/w2-isolation/
"""
import json, os, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core import env as core_env, isolation, runner
from tools.redaction import scrub_all

HOME = os.path.expanduser("~")
SEEN = {"claude_credentials": "~/.claude/.credentials.json", "claude_config": "~/.claude.json",
        "codex_auth": "~/.codex/auth.json", "bashrc": "~/.bashrc", "mnt_c": "/mnt/c"}
PROBE = ("import json, os, sys; print(json.dumps({k: os.path.lexists(os.path.expanduser(v)) "
         "for k, v in json.loads(sys.argv[1]).items()}))")
STATUS = {"claude-code": ["auth", "status"], "codex": ["login", "status"]}
KEEP = ("loggedIn", "authMethod", "apiProvider")   # claude auth status에서 남기는 칸


def status_summary(adapter_id, result):
    if adapter_id == "claude-code":
        try:
            data = json.loads(result.stdout)
        except ValueError:
            return {"unparsed": True}
        return {k: data.get(k) for k in KEEP}
    text = (result.stdout + result.stderr).strip().splitlines()
    return {"line": text[0] if text else ""}


def main():
    child, _ = core_env.child_env(os.environ)
    report = {"bwrap": shutil.which("bwrap"), "cli": {}}
    for adapter_id, command in (("claude-code", "claude"), ("codex", "codex")):
        exe = core_env.resolve(command, child)
        ro, rw = isolation.cli_mounts(adapter_id, exe, HOME)
        work = tempfile.mkdtemp(prefix="dml-w2-cli-")
        box = isolation.Sandbox(work_dir=work, home=HOME, read_only=ro, read_write=rw,
                                env={"LANG": "C.UTF-8", "NO_COLOR": "1"})

        def inside(argv, timeout=60):
            return isolation.run(argv, box, timeout=timeout)

        version = inside([exe, "--version"])
        status = inside([exe, *STATUS[adapter_id]])
        seen = inside(["/usr/bin/python3", "-c", PROBE, json.dumps(SEEN)])  # 격리 안에는 /usr만 보인다
        report["cli"][adapter_id] = {
            "version": version.stdout.strip() or version.stderr.strip()[:200],
            "version_state": version.state, "version_exit": version.exit_code,
            "tree_confirmed_empty": version.tree_confirmed_empty,
            "status": status_summary(adapter_id, status), "status_state": status.state,
            "status_exit": status.exit_code,
            "visible": json.loads(seen.stdout) if seen.state == runner.EXITED else seen.stderr[:300],
            "read_only": [p.replace(HOME, "~") for p in ro], "read_write": [p.replace(HOME, "~") for p in rw],
        }
        shutil.rmtree(work, ignore_errors=True)
    print(json.dumps(scrub_all(report, HOME), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
