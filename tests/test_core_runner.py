"""core.runner 검사. 실제 CLI·모델을 쓰지 않는다. 이 테스트를 돌리는 python 자신을 가짜 CLI로 쓴다.

Windows(job object)와 그 밖(프로세스 그룹)은 서로 다른 코드 경로다. CI(Linux)는 뒤쪽만,
Windows 경로는 로컬 Windows에서 돌린 결과로 확인한다.
"""
import os
import sys
import tempfile
import threading
import unittest

from core import runner

PY = sys.executable
CWD = tempfile.gettempdir()
ENV = dict(os.environ)


def run(code, **kwargs):
    kwargs.setdefault("timeout", 20)
    return runner.run([PY, "-c", code], cwd=CWD, env=ENV, **kwargs)


class RunnerContractTests(unittest.TestCase):
    def test_normal_exit_is_confirmed_and_exit_code_kept(self):
        result = run("import sys; print('OK'); sys.exit(3)")
        self.assertEqual(result.state, runner.EXITED)
        self.assertEqual(result.exit_code, 3)          # exit code는 그대로. 성공 판정은 adapter가 한다
        self.assertEqual(result.stdout, "OK\n")
        self.assertIs(result.tree_confirmed_empty, True)
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
        self.assertIs(result.tree_confirmed_empty, True)

    def test_children_left_behind_are_counted_and_ended(self):
        """HF-07. CLI가 끝난 뒤 남은 자식(예: MCP 서버)을 세고 트리째 끝낸다."""
        code = ("import subprocess, sys; "
                "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); print('done')")
        result = run(code)
        self.assertEqual(result.state, runner.EXITED)
        self.assertGreaterEqual(result.leftover_processes, 1)
        self.assertIs(result.tree_confirmed_empty, True)

    def test_cancel_ends_the_tree(self):
        cancel = threading.Event()
        threading.Timer(0.5, cancel.set).start()
        result = run("import time; time.sleep(30)", cancel=cancel)
        self.assertEqual(result.state, runner.CANCELLED)
        self.assertIs(result.tree_confirmed_empty, True)

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


if __name__ == "__main__":
    unittest.main()
