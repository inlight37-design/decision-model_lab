"""core.isolation 검사 — bubblewrap 경계의 양성·음성 대조와 PID namespace 수명(인계 W2).

합성 파일과 python 탐침만 쓴다. CLI·모델은 부르지 않는다. bubblewrap을 쓸 수 있는 Linux에서만 돈다
(CI는 bubblewrap을 설치하고 user namespace 제한을 푼다). 원장·초안·인증 대신 표식 문자열을 넣은 가짜 파일을 둔다.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from core import isolation, runner

PROBE = r'''
import json, os, socket, subprocess, sys, time
mode, root, home, port = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return {"ok": True, "text": f.read().strip()}
    except OSError as e:
        return {"ok": False, "error": type(e).__name__}
def write(path):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("x")
        return True
    except OSError:
        return False
if mode == "detach":
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", sys.argv[5]], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(p.pid, flush=True)
    sys.exit(0)
if mode == "hang":
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", sys.argv[5]], start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(60)
try:
    socket.create_connection(("127.0.0.1", port), timeout=2).close()
    tcp = True
except OSError:
    tcp = False
pids = [d for d in os.listdir("/proc") if d.isdigit()]
print(json.dumps({
    "input": read(f"{root}/input/question.md"),
    "own_cli": read(f"{home}/.claude/cred"),
    "peer_draft": read(f"{root}/peer/draft.md"),
    "ledger": read(f"{root}/ledger/run.db"),
    "past_synthesis": read(f"{root}/past/synthesis.md"),
    "home_dotfile": read(f"{home}/.bashrc"),
    "other_cli_auth": read(f"{home}/.codex/auth.json"),
    "symlink_to_peer": read(f"{root}/input/peek"),
    "exists": {p: os.path.exists(p) for p in ("/mnt/c", "/run/user", "/run/WSL", "/init")},
    "mnt": {d: sorted(os.listdir(f"/mnt/{d}")) for d in (os.listdir("/mnt") if os.path.isdir("/mnt") else ())},
    "write_input": write(f"{root}/input/new.txt"),
    "write_work": write(f"{root}/work/out.txt"),
    "write_home": write(f"{home}/scratch.txt"),
    "env": sorted(os.environ),
    "pid1": open("/proc/1/cmdline", "rb").read().split(b"\0")[0].decode(),
    "visible_processes": len(pids),
    "tcp_to_host_localhost": tcp,
}))
'''


# 탐침은 시스템 python으로 돌린다. 격리 안에는 /usr만 보이는데, CI의 python은 /opt 아래에 있다.
SYSTEM_PY = "/usr/bin/python3"


def bwrap_usable():
    if sys.platform != "linux" or not (os.path.exists(isolation.BWRAP) and os.path.exists(SYSTEM_PY)):
        return False
    probe = [isolation.BWRAP, "--unshare-all", "--share-net", "--die-with-parent", "--ro-bind", "/usr", "/usr",
             "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
             "--proc", "/proc", "--", "/usr/bin/true"]
    return subprocess.run(probe, capture_output=True, check=False).returncode == 0


def marked_alive(marker):
    """호스트에서 표식이 붙은 프로세스가 아직 있는가."""
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                if marker.encode() in (entry / "cmdline").read_bytes():
                    return True
            except OSError:
                pass
    return False


class RefusalTests(unittest.TestCase):
    """조립 전 거절. 어느 플랫폼에서나 돈다."""

    def test_runner_accepts_pid_namespace_only_for_our_bwrap(self):
        with self.assertRaises(runner.RunnerError):
            runner.run([sys.executable, "-c", "0"], cwd=tempfile.gettempdir(), env=dict(os.environ),
                       timeout=5, pid_namespace=True)

    def test_relative_or_root_paths_are_refused(self):
        for box in (isolation.Sandbox(work_dir="work", home="/h"),
                    isolation.Sandbox(work_dir="/w", home="/h", read_only=("/",)),
                    isolation.Sandbox(work_dir="/w", home="/h", read_write=("/h",))):
            with self.subTest(box=box), self.assertRaises(isolation.IsolationError):
                isolation.wrap(["/usr/bin/python3"], box)


@unittest.skipUnless(bwrap_usable(), "bubblewrap을 쓸 수 있는 Linux에서만")
class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dml-w2-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        r = self.root
        for rel, text in (("input/question.md", "INPUT-4C"), ("peer/draft.md", "PEER-3K"),
                          ("ledger/run.db", "LEDGER-7Q"), ("past/synthesis.md", "PAST-5Z"),
                          ("home/.bashrc", "HOME-9X"), ("home/.claude/cred", "OWN-1A"),
                          ("home/.codex/auth.json", "OTHER-2B"), ("input/probe.py", PROBE)):
            (r / rel).parent.mkdir(parents=True, exist_ok=True)
            (r / rel).write_text(text, encoding="utf-8")
        (r / "input/peek").symlink_to(r / "peer/draft.md")
        (r / "work").mkdir()
        self.home = str(r / "home")
        self.box = isolation.Sandbox(work_dir=str(r / "work"), home=self.home,
                                     read_only=(str(r / "input"),), read_write=(str(r / "home/.claude"),),
                                     env={"LANG": "C.UTF-8", "SECRET_FROM_HOST": "x", "WSL_INTEROP": "x"})
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.server.listen()
        self.addCleanup(self.server.close)

    def run_probe(self, mode, *extra, timeout=30):
        argv = [SYSTEM_PY, str(self.root / "input/probe.py"), mode, str(self.root), self.home,
                str(self.server.getsockname()[1]), *extra]
        return runner.run(isolation.wrap(argv, self.box), cwd=str(self.root / "work"), env=dict(os.environ),
                          timeout=timeout, pid_namespace=True)

    def test_only_what_was_granted_is_visible(self):
        result = self.run_probe("report")
        self.assertEqual(result.state, runner.EXITED, result.stderr)
        seen = json.loads(result.stdout)
        # 양성 대조: 허용한 것은 읽힌다
        self.assertEqual(seen["input"], {"ok": True, "text": "INPUT-4C"})
        self.assertEqual(seen["own_cli"], {"ok": True, "text": "OWN-1A"})
        self.assertTrue(seen["write_work"])
        # 음성 대조: 원장·다른 참여자·지난 기록·HOME·다른 CLI 인증, symlink 우회
        for key in ("peer_draft", "ledger", "past_synthesis", "home_dotfile", "other_cli_auth", "symlink_to_peer"):
            with self.subTest(key=key):
                self.assertFalse(seen[key]["ok"], seen[key])
        self.assertEqual(seen["exists"], dict.fromkeys(seen["exists"], False))
        # WSL은 resolv.conf가 /mnt/wsl을 가리킨다. 그 파일 하나만 보여야 한다
        self.assertIn(seen["mnt"], ({}, {"wsl": ["resolv.conf"]}))
        self.assertFalse(seen["write_input"])
        self.assertTrue(seen["write_home"])                             # 안에서는 쓸 수 있지만
        self.assertFalse((self.root / "home/scratch.txt").exists())     # 호스트에는 남지 않는다(tmpfs)
        self.assertTrue((self.root / "work/out.txt").exists())
        self.assertNotIn("SECRET_FROM_HOST", seen["env"])
        self.assertNotIn("WSL_INTEROP", seen["env"])
        self.assertIn("bwrap", seen["pid1"])                            # 새 PID namespace의 첫 프로세스
        self.assertLess(seen["visible_processes"], 10)
        # 보장하지 않는 것: 네트워크는 공유한다. controller 포트는 토큰으로 막아야 한다
        self.assertTrue(seen["tcp_to_host_localhost"])

    def test_a_detached_descendant_ends_with_the_namespace(self):
        """R01의 Linux 해법. 새 세션으로 떨어져 나간 손자도 namespace와 함께 끝난다."""
        marker = f"dml-w2-{os.getpid()}-{time.monotonic_ns()}"
        result = self.run_probe("detach", marker)
        self.assertEqual(result.state, runner.EXITED, result.stderr)
        self.assertEqual(result.containment, runner.PID_NAMESPACE)
        self.assertIs(result.tree_confirmed_empty, True)
        self.assertFalse(marked_alive(marker))

    def test_timeout_ends_everything_inside(self):
        marker = f"dml-w2-{os.getpid()}-{time.monotonic_ns()}"
        result = self.run_probe("hang", marker, timeout=2)
        self.assertEqual(result.state, runner.TIMED_OUT)
        self.assertIs(result.tree_confirmed_empty, True)
        self.assertFalse(marked_alive(marker))


if __name__ == "__main__":
    unittest.main()
