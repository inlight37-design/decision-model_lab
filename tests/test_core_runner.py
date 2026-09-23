"""core.runner 검사. 실제 CLI·모델을 쓰지 않는다. 이 테스트를 돌리는 python 자신을 가짜 CLI로 쓴다.

Windows(job object)와 그 밖(프로세스 그룹)은 서로 다른 코드 경로다. CI(Linux)는 뒤쪽만,
Windows 경로는 로컬 Windows에서 돌린 결과로 확인한다.
"""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from core import runner

PY = sys.executable
CWD = tempfile.gettempdir()
ENV = dict(os.environ)


def run(code, **kwargs):
    kwargs.setdefault("timeout", 20)
    return runner.run([PY, "-c", code], cwd=CWD, env=ENV, **kwargs)


def detached_grandchild(pidfile, *, inherit_pipes):
    """손자를 떼어 놓고(POSIX는 새 세션, Windows는 DETACHED_PROCESS) 바로 끝나는 코드. 손자 pid는 pidfile에."""
    detach = ("creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP"
              if runner.IS_WINDOWS else "start_new_session=True")
    pipes = "" if inherit_pipes else ", stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL"
    return ("import pathlib, subprocess, sys; "
            f"p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], {detach}{pipes}); "
            f"pathlib.Path({str(pidfile)!r}).write_text(str(p.pid))")


def alive(pid):
    if runner.IS_WINDOWS:  # os.kill(pid, 0)은 Windows에서 프로세스를 끝내 버린다
        import ctypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = ctypes.c_void_p
        handle = k32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not handle:
            return False
        try:
            return k32.WaitForSingleObject(ctypes.c_void_p(handle), 0) == 0x102  # WAIT_TIMEOUT
        finally:
            k32.CloseHandle(ctypes.c_void_p(handle))
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return True


def gone_within(pid, seconds=1.0):
    """TerminateJobObject는 비동기다. job 회계가 0이 된 직후 프로세스 객체가 신호를 받기까지 짧은
    틈이 있었다(aux-pc 반복 관측, 모두 16ms 이내). 그 틈만큼 기다린다."""
    deadline = time.monotonic() + seconds
    while alive(pid):
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.01)
    return True


class RunnerContractTests(unittest.TestCase):
    def assert_unit_ended(self, result):
        """추적 단위가 빈 것은 두 플랫폼 모두 확인한다. 자손 전체를 말할 수 있는 것은 job object뿐이다."""
        self.assertIs(result.unit_confirmed_empty, True)
        self.assertIs(result.tree_confirmed_empty, True if runner.IS_WINDOWS else None)

    def test_normal_exit_is_confirmed_and_exit_code_kept(self):
        result = run("import sys; print('OK'); sys.exit(3)")
        self.assertEqual(result.state, runner.EXITED)
        self.assertEqual(result.exit_code, 3)          # exit code는 그대로. 성공 판정은 adapter가 한다
        self.assertEqual(result.stdout, "OK\n")
        self.assert_unit_ended(result)
        self.assertEqual(result.leftover_processes, 0)

    def test_stdout_and_stderr_are_separate(self):
        result = run("import sys; sys.stderr.write('denied'); print('answer')")
        self.assertEqual((result.stdout, result.stderr), ("answer\n", "denied"))

    def test_stdin_is_written_then_closed(self):
        self.assertEqual(run("import sys; print(sys.stdin.read().upper())", stdin_text="hi").stdout, "HI\n")

    def test_stdin_is_closed_when_there_is_no_input(self):
        """codex exec처럼 stdin을 기다리는 CLI가 멈추지 않는다."""
        result = run("import sys; print(repr(sys.stdin.read()))", timeout=10)
        self.assertEqual(result.state, runner.EXITED)
        self.assertEqual(result.stdout, "''\n")

    def test_timeout_is_not_success_even_with_text(self):
        """HF-06. Hermes의 codex 경로는 이 경우 텍스트를 완료로 받는다. 우리는 받지 않는다."""
        result = run("import time; print('answer', flush=True); time.sleep(30)", timeout=1.5)
        self.assertEqual(result.state, runner.TIMED_OUT)
        self.assertEqual(result.stdout, "answer\n")
        self.assert_unit_ended(result)

    def test_children_left_behind_are_counted_and_ended(self):
        """HF-07. CLI가 끝난 뒤 남은 자식(예: MCP 서버)을 세고 트리째 끝낸다."""
        code = ("import subprocess, sys; "
                "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); print('done')")
        result = run(code)
        self.assertEqual(result.state, runner.EXITED)
        self.assertGreaterEqual(result.leftover_processes, 1)
        self.assert_unit_ended(result)

    def test_cancel_ends_the_tree(self):
        cancel = threading.Event()
        threading.Timer(0.5, cancel.set).start()
        result = run("import time; time.sleep(30)", cancel=cancel)
        self.assertEqual(result.state, runner.CANCELLED)
        self.assert_unit_ended(result)

    def test_output_is_capped_and_marked(self):
        result = run("print('a' * 100000)", max_output_bytes=1000)
        self.assertTrue(result.stdout_truncated)
        self.assertEqual(len(result.stdout), 1000)
        self.assertEqual(result.state, runner.EXITED)

    def test_missing_executable_fails_to_start(self):
        result = runner.run([os.path.join(CWD, "no-such-cli.exe")], cwd=CWD, env=ENV, timeout=5)
        self.assertEqual(result.state, runner.FAILED_TO_START)
        self.assertIsNone(result.exit_code)

    def test_requests_refused_before_running(self):
        for argv, kwargs in (([], {}), (["python", "-c", "1"], {}), ([os.path.join(CWD, "x.bat")], {}),
                             ([os.path.join(CWD, "x.CMD")], {}), ([PY, "a\x00b"], {}),
                             ([PY, "-c", "1"], {"timeout": 0}),
                             ([PY, "-c", "1"], {"cwd": os.path.join(CWD, "no-such-dir")})):
            with self.subTest(argv=argv, kwargs=kwargs), self.assertRaises(runner.RunnerError):
                call = dict(cwd=CWD, env=ENV, timeout=5)
                call.update(kwargs)
                runner.run(argv, **call)


class BoundaryReviewRegressionTests(unittest.TestCase):
    """2026-09-23 경계 리뷰 R01·R02(docs/reviews/2026-09-23-wsl2-boundary/)의 재현. 손자는 끝에 반드시 끝낸다."""

    def setUp(self):
        tmp = tempfile.mkdtemp(prefix="dml-runner-")
        self.pidfile = Path(tmp) / "grandchild.pid"
        self.addCleanup(shutil.rmtree, tmp, True)
        self.addCleanup(self.end_grandchild)

    def end_grandchild(self):
        if not self.pidfile.exists():
            return
        pid = int(self.pidfile.read_text())
        if not alive(pid):
            return
        if runner.IS_WINDOWS:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, check=False)
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def test_a_descendant_outside_the_tracked_unit_is_not_reported_gone(self):
        """R01. 손자가 추적 단위를 떠나고 표준 입출력도 닫았다."""
        result = run(detached_grandchild(self.pidfile, inherit_pipes=False))
        pid = int(self.pidfile.read_text())
        self.assertEqual(result.state, runner.EXITED)
        if runner.IS_WINDOWS:
            # job은 자손이 떠날 수 없다. 떨어져 나간 손자도 세고 끝낸다.
            self.assertEqual(result.containment, runner.JOB_OBJECT)
            self.assertIs(result.tree_confirmed_empty, True)
            self.assertGreaterEqual(result.leftover_processes, 1)
            self.assertTrue(gone_within(pid))
        else:
            # 프로세스 그룹은 비었지만 새 세션으로 나간 손자는 살아 있다. 자손 전체가 끝났다고 말하지 않는다.
            self.assertTrue(alive(pid))
            self.assertEqual(result.containment, runner.PROCESS_GROUP)
            self.assertIs(result.unit_confirmed_empty, True)
            self.assertIsNone(result.tree_confirmed_empty)

    def test_a_descendant_holding_the_pipes_does_not_hang_the_return(self):
        """R02. 떨어져 나간 손자가 stdout·stderr를 물려받았다. 정리에도 상한이 있다."""
        box = {}
        code = detached_grandchild(self.pidfile, inherit_pipes=True)
        worker = threading.Thread(target=lambda: box.update(result=run(code, timeout=2)), daemon=True)
        worker.start()
        worker.join(2 + runner.CLEANUP_LIMIT + 5)
        self.assertFalse(worker.is_alive(), "run() did not return within timeout + CLEANUP_LIMIT")
        result = box["result"]
        if runner.IS_WINDOWS:
            self.assertEqual(result.state, runner.EXITED)  # job이 손자까지 끝내서 파이프가 닫힌다
            self.assertIs(result.tree_confirmed_empty, True)
        else:
            self.assertEqual(result.state, runner.UNKNOWN)
            self.assertIn("an output pipe stayed open after termination", result.notes)


if __name__ == "__main__":
    unittest.main()
