"""취소 전 프로세스 생성/추가 입력을 거절한다. 실제 모델·인증 자료 없음."""
import os
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from core import runner as r


class CancellationBoundaryTests(unittest.TestCase):
    def test_preset_cancel_does_not_spawn_or_send_input(self):
        cancel = threading.Event()
        cancel.set()
        with tempfile.TemporaryDirectory() as cwd, patch.object(r.subprocess, "Popen") as spawn:
            result = r.run([sys.executable, "-c", "raise AssertionError('must not run')"],
                           cwd=cwd, env={}, timeout=1, stdin_text="private prompt", cancel=cancel)
        spawn.assert_not_called()
        self.assertEqual(result.state, r.FAILED_TO_START)
        self.assertTrue(result.tree_confirmed_empty)
        self.assertIsNone(result.input_delivery)
        self.assertIn("cancelled", result.error)

    def test_writer_stops_after_current_chunk_and_records_incomplete_delivery(self):
        cancel = threading.Event()
        with tempfile.TemporaryFile() as stream:
            writer = r._Writer(stream, b"x" * (r._CHUNK + 1), cancel)
            def write_once(fd, data):
                cancel.set()
                return len(data)
            with patch.object(r.os, "write", side_effect=write_once) as write:
                writer.run()
            self.assertEqual(write.call_count, 1)
            self.assertEqual(writer.written, r._CHUNK)
            self.assertEqual(writer.error, "cancelled")
            self.assertTrue(stream.closed)

    def test_limits_cannot_silently_disable_timeout_or_use_boolean_byte_count(self):
        with tempfile.TemporaryDirectory() as cwd, patch.object(r.subprocess, "Popen") as spawn:
            for timeout in (True, float("inf"), float("nan"), -1, 0):
                with self.subTest(timeout=timeout), self.assertRaises(r.RunnerError):
                    r.run([sys.executable], cwd=cwd, env={}, timeout=timeout)
            with self.assertRaises(r.RunnerError):
                r.run([sys.executable], cwd=cwd, env={}, timeout=1, max_output_bytes=True)
        spawn.assert_not_called()

    def test_live_child_cancel_reaches_cleanup_without_inventing_whole_tree_confirmation(self):
        # 취소/스레드 신호가 프로세스 시작 뒤 도달하도록 Popen 반환 직후 신호한다.
        cancel = threading.Event()
        original = r.subprocess.Popen
        def spawn_then_cancel(*args, **kwargs):
            proc = original(*args, **kwargs)
            cancel.set()
            return proc
        with tempfile.TemporaryDirectory() as cwd, patch.object(r.subprocess, "Popen", side_effect=spawn_then_cancel):
            result = r.run([sys.executable, "-c", "import time; time.sleep(60)"], cwd=cwd,
                           env=dict(os.environ), timeout=5, stdin_text="x" * 100000, cancel=cancel)
        self.assertIn(result.state, (r.CANCELLED, r.UNKNOWN))
        self.assertNotEqual(result.input_delivery, r.INPUT_COMPLETE)
        if not r.IS_WINDOWS:
            self.assertIsNot(result.tree_confirmed_empty, True)

    def test_cli_executor_forwards_exact_cancellation_token_to_existing_isolation_path(self):
        from types import SimpleNamespace
        from app.cli_executor import CliExecutor
        from core import contract
        cancel = threading.Event()
        ex = CliExecutor(never=(), unchecked=True, base_env={})
        planned = SimpleNamespace(argv=(sys.executable, "--tools", ""), stdin_text="q", adapter_id="claude-code")
        plan = contract.Plan(contract.REAL, planned, "/unused", object(), "m")
        result = r.RunResult((), r.FAILED_TO_START, None, "", "", False, False, 0, None, True)
        with patch("app.cli_executor.isolation.run", return_value=result) as run:
            ex.run(plan, 1, cancel=cancel)
        self.assertIs(run.call_args.kwargs["cancel"], cancel)
