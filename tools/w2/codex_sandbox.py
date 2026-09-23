"""K12·K09: Codex 자체 Linux 샌드박스가 우리 bubblewrap 안에서 서는지, 그 안의 명령이 무엇에 닿는지 본다.
모델을 부르지 않는다.

참여자와 같은 경계(core.isolation, Codex의 cli_mounts와 읽기 전용 공통 자료 폴더)를 만들고 그 안에서
`codex sandbox -- /bin/sh -c ...`를 실행한다. `codex sandbox`는 Codex의 Linux 샌드박스로 명령 하나를 돌리는 하위
명령이다(0.156.1 help). 모델이 exec에서 돌리는 명령이 닿는 곳을 흉내 낸다. 셸은 다음을 해 보고 결과만 찍는다.

- 작업 폴더에 파일 쓰기, 공통 자료 읽기, /tmp 쓰기(K12). 쓰기가 "Read-only file system"으로 막히고 읽기는 되면
  중첩된 Codex 샌드박스가 서서 쓰기를 막는다. namespace·bwrap 오류로 셸이 돌지 못하면 중첩이 안 된다.
- Codex 자신의 인증 파일 `~/.codex/auth.json`이 있는지·읽을 수 있는지(K09). `test -e`·`test -r`의 종료 코드만
  찍는다 — 내용은 읽지 않는다.
- 밖으로 TCP 연결을 열 수 있는지(1.1.1.1:443, 3초). 연결만 열고 아무것도 보내지 않는다.

변형은 기본값, `-c sandbox_mode="read-only"`, 그리고 K09 방어 후보인 이름 있는 권한 profile 둘(`~/.codex` 전체 또는
`~/.codex/auth.json`만 읽기 금지)이다.

한계: `codex exec`가 모델의 명령을 돌린 것이 아니라 같은 샌드박스를 직접 부른 것이다. exec의 read-only 정책과
같다는 것은 `-c sandbox_mode="read-only"` 변형이 같은 결과를 내는 데까지만 본다. 권한 profile을 exec에 넘긴 관측은
아직 없다.

  python3 tools/w2/codex_sandbox.py           # WSL·Linux에서, 저장소 루트에서, 로그인 셸(bash -l)로
결과: docs/experiments/w2-isolation/stage2-aux-pc-wsl.md(K12), stage2-followup-aux-pc-wsl.md(K09·권한 profile)
"""
import json, os, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core import env as core_env, isolation  # noqa: E402

HOME = os.path.expanduser("~")
VARIANTS = {"default": [], "read-only via -c": ["-c", 'sandbox_mode="read-only"']}
# 인증 파일은 종료 코드만 본다. 네트워크는 연결을 열어 보기만 하고 예외의 이름만 찍는다
AUTH = 'test -e "$HOME/.codex/auth.json"; echo auth_exists_rc=$?; test -r "$HOME/.codex/auth.json"; echo auth_readable_rc=$?'
NET = ("/usr/bin/python3 -c \"import socket\ntry:\n    socket.create_connection(('1.1.1.1', 443), 3)\n"
       "    print('net=connected')\nexcept OSError as e:\n    print('net=' + type(e).__name__)\"")


def _value(lines: list[str], key: str) -> str | None:
    return next((line.split("=", 1)[1] for line in lines if line.startswith(key + "=")), None)


def deny_profile(home: str, target: str) -> list[str]:
    """K09 방어 후보: 읽기 전용 기본 profile에 한 경로의 읽기 금지를 더한 이름 있는 권한 profile(베타 기능,
    https://learn.chatgpt.com/docs/permissions). CLI 자신은 샌드박스 밖에서 인증 파일을 읽으므로 명령만 막힌다.
    `~/.codex` 전체를 막으면 Codex의 샌드박스 보조 프로그램이 그 아래의 codex 실행 파일을 다시 실행하지 못한다
    (2026-09-24 관측) — 그래서 인증 파일 하나를 막는 변형과 함께 둔다."""
    profile = f'{{ extends = ":read-only", filesystem = {{ "{home}/{target}" = "deny" }} }}'
    return ["-c", f"permissions.dml-deny={profile}", "-P", "dml-deny"]


def main():
    child, _ = core_env.child_env(os.environ)
    exe = core_env.resolve("codex", child)
    ro, rw = isolation.cli_mounts("codex", exe, HOME)
    report = {"codex": os.path.realpath(exe).replace(HOME, "~"), "variants": {}}
    variants = {**VARIANTS, "profile: read-only + deny ~/.codex": deny_profile(HOME, ".codex"),
                "profile: read-only + deny ~/.codex/auth.json": deny_profile(HOME, ".codex/auth.json")}
    for name, extra in variants.items():
        root = tempfile.mkdtemp(prefix="dml-w2-k12-")
        work, inputs = os.path.join(root, "work"), os.path.join(root, "input")
        os.mkdir(work)
        os.mkdir(inputs)
        Path(inputs, "allowed.txt").write_text("AL-3K readable\n", encoding="utf-8")
        script = (f"echo x > created.txt; echo write_rc=$?; head -n1 {inputs}/allowed.txt; echo read_rc=$?; "
                  f"touch /tmp/t; echo tmp_rc=$?; {AUTH}; {NET}")
        box = isolation.Sandbox(work_dir=work, home=HOME, read_only=ro + (inputs,), read_write=rw,
                                env={"LANG": "C.UTF-8", "NO_COLOR": "1"})
        result = isolation.run([exe, "sandbox", *extra, "--", "/bin/sh", "-c", script], box, timeout=60)
        out = result.stdout.replace(HOME, "~")
        lines = out.splitlines()
        report["variants"][name] = {
            "state": result.state, "exit": result.exit_code, "tree_confirmed_empty": result.tree_confirmed_empty,
            "write_refused": "write_rc=0" not in out and not os.path.exists(os.path.join(work, "created.txt")),
            "read_ok": "AL-3K readable" in out,
            "auth_file_exists": _value(lines, "auth_exists_rc") == "0",
            "auth_file_readable": _value(lines, "auth_readable_rc") == "0",
            "network": _value(lines, "net"), "stdout": lines[:12],
            "stderr": result.stderr.replace(HOME, "~").splitlines()[:10],
        }
        shutil.rmtree(root, ignore_errors=True)
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
