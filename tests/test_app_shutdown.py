"""종료는 새 호출을 막되, 미확인 자손을 성공으로 바꾸거나 예산을 환불하지 않는다."""
from __future__ import annotations

from dataclasses import replace
import io
import json
import threading
import unittest
from unittest.mock import Mock, call, patch

from app import controller as c, server
from app.report import build_report
from app.store import Store, events
from core import adapters
import test_app_controller as support


class ShutdownTests(support.Base):
    def test_stop_signals_worker_without_starting_queued_work_and_restart_is_explicit(self):
        ex = support.SyntheticExecutor(hold=("a",))
        ctl = self.controller(ex, max_parallel=1)
        self.addCleanup(ctl.wait_idle)
        self.addCleanup(ex.release, "a")
        rid = ctl.create_run("q", [support.cli("a"), support.cli("b")], min_independent=1)
        self.assertTrue(support.wait_for(lambda: ex.started == ["a"]))
        signal = next(iter(ctl._workers.values()))[1]
        self.assertFalse(ctl.shutdown(timeout=0))
        self.assertTrue(signal.is_set())
        with self.assertRaises(c.ControllerError):
            ctl.resume()
        with self.assertRaises(c.ControllerError):
            ctl.create_run("new", [support.cli("c")], min_independent=1)
        with self.assertRaises(c.ControllerError):
            ctl.synthesize_with_model(rid, "claude-code")
        ex.release("a")
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(ctl.shutdown(timeout=0))
        self.assertEqual(ex.started, ["a"])
        self.assertEqual(self.part(ctl, rid, "b")["state"], c.QUEUED)
        self.assertEqual(len(self.store.rows("SELECT * FROM runs")), 1)
        path = self.store.path
        self.store.close()
        self.store = Store(path)
        self.addCleanup(self.store.close)
        restarted = self.controller(ex, max_parallel=1)
        self.assertTrue(restarted.paused)
        self.assertEqual(ex.started, ["a"])
        restarted.resume()
        self.assertTrue(restarted.wait_idle())
        self.assertEqual(ex.started, ["a", "b"])

    def test_shutdown_waits_outside_the_controller_lock(self):
        class Cooperative(support.SyntheticExecutor):
            def __init__(self):
                super().__init__()
                self.entered = threading.Event()

            def execute(self, spec, prompt, work_dir, timeout, *, cancel=None):
                self.entered.set()
                if not cancel.wait(3):
                    raise RuntimeError("test cancellation signal was not delivered")
                return super().execute(spec, prompt, work_dir, timeout, cancel=cancel)

        ex = Cooperative()
        ctl = self.controller(ex, max_parallel=1)
        self.addCleanup(ctl.wait_idle)
        ctl.create_run("q", [support.cli("a"), support.cli("b")], min_independent=1)
        self.assertTrue(ex.entered.wait(2))
        self.assertTrue(ctl.shutdown(timeout=2))
        self.assertEqual(ex.started, ["a"])
        self.assertEqual(ctl.view()["slots"]["used"], 0)

    def test_invalid_shutdown_timeout_does_not_stop_the_controller(self):
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        for timeout in (-1, float("nan"), float("inf")):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                ctl.shutdown(timeout=timeout)
        self.assertFalse(ctl.paused)
        ctl.create_run("q", [support.cli("a")], min_independent=1)
        self.assertEqual(len(self.store.rows("SELECT * FROM runs")), 1)

    def test_finished_worker_is_not_proof_that_the_process_tree_ended(self):
        ex = support.SyntheticExecutor({"a": "unknown"})
        ctl = self.controller(ex, max_parallel=1)
        rid = ctl.create_run("q", [support.cli("a")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(ctl.shutdown(timeout=0))
        self.assertEqual(self.part(ctl, rid, "a")["state"], c.UNKNOWN)
        self.assertEqual(ctl.view()["slots"]["used"], 1)
        self.assertEqual(ctl.unsettled(), 1)
        self.assertEqual(self.run_view(ctl, rid)["budget"]["used"], 1)

    def test_synthesis_receives_shutdown_signal_and_keeps_public_drafts(self):
        ex = support.SyntheticExecutor(hold=("synthesis",))
        ctl = self.controller(ex)
        self.addCleanup(ctl.wait_idle)
        self.addCleanup(ex.release, "synthesis")
        rid = ctl.create_run("q", [support.cli("a")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        original = build_report(ctl.view(rid), rid)
        ctl.synthesize_with_model(rid, "claude-code")
        self.assertTrue(support.wait_for(lambda: "synthesis" in ex.started))
        signal = ctl._synthesis[rid][1]
        self.assertFalse(ctl.shutdown(timeout=0))
        self.assertTrue(signal.is_set())
        ex.release("synthesis")
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(ctl.shutdown(timeout=0))
        self.assertEqual(ctl.view()["slots"]["used"], 0)
        self.assertEqual(build_report(ctl.view(rid), rid), original)
        self.assertEqual(ex.started, ["a", "synthesis"])

    def test_bad_unicode_synthesis_is_terminal_failed_not_a_stranded_unknown(self):
        class Malformed(support.SyntheticExecutor):
            def execute(self, spec, prompt, work_dir, timeout, *, cancel=None):
                result, outcome = super().execute(spec, prompt, work_dir, timeout, cancel=cancel)
                if spec.pid == "synthesis":
                    raw = json.dumps({"claims": [{"statement": "\ud800", "quotes": []}]})
                    result = replace(result, stdout=support.claude_stdout(raw))
                    outcome = adapters.interpret("claude-code", result, requested_model="m")
                return result, outcome

        ex = Malformed()
        ctl = self.controller(ex)
        self.addCleanup(ctl.wait_idle)
        rid = ctl.create_run("q", [support.cli("a")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        original = build_report(ctl.view(rid), rid)
        ctl.synthesize_with_model(rid, "claude-code")
        self.assertTrue(ctl.wait_idle())
        view = ctl.view(rid)
        self.assertEqual(view["slots"]["used"], 0)
        self.assertEqual(view["unsettled"]["count"], 0)
        self.assertEqual(view["runs"][0]["model_synthesis"]["status"], "failed")
        self.assertEqual(build_report(view, rid), original)
        kinds = [e["kind"] for e in events(self.store, rid)]
        self.assertEqual(kinds.count("synthesis_started"), 1)
        self.assertEqual(kinds.count("synthesis_failed"), 1)
        with self.assertRaises(c.ControllerError):
            ctl.synthesize_with_model(rid, "claude-code")
        self.assertEqual(ex.started, ["a", "synthesis"])


class ServerShutdownTests(unittest.TestCase):
    def run_main(self, *, idle=True, unsettled=0, failure=KeyboardInterrupt):
        resource = Mock()
        resource.server.server_address = ("127.0.0.1", 0)
        resource.server.serve_forever.side_effect = failure
        resource.controller.shutdown.return_value = idle
        resource.controller.unsettled.return_value = unsettled
        resource.controller.executor.name = "synthetic"
        resource.controller.paused = False
        with patch.object(server, "serve", return_value=(resource.server, "test-token", resource.controller)), \
                patch("sys.argv", ["ledger", "--data-dir", "test-only-unused-directory"]), \
                patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()):
            if failure is RuntimeError:
                with self.assertRaises(RuntimeError):
                    server.main()
                status = None
            else:
                status = server.main()
        return status, resource

    def test_interrupt_drains_handlers_and_workers_before_closing_ledger(self):
        status, resource = self.run_main()
        self.assertEqual(status, 0)
        relevant = [entry for entry in resource.mock_calls if entry in (
            call.controller.shutdown(timeout=0), call.server.server_close(),
            call.controller.shutdown(), call.controller.store.close())]
        self.assertEqual(relevant, [call.controller.shutdown(timeout=0), call.server.server_close(),
                                    call.controller.shutdown(), call.controller.store.close()])
        self.assertFalse(server._Server.daemon_threads)

    def test_undrained_worker_keeps_store_open_and_returns_failure(self):
        status, resource = self.run_main(idle=False)
        self.assertEqual(status, 1)
        resource.server.server_close.assert_called_once()
        resource.controller.store.close.assert_not_called()

    def test_unknown_process_is_not_reported_as_a_clean_exit(self):
        status, resource = self.run_main(unsettled=1)
        self.assertEqual(status, 1)
        resource.controller.store.close.assert_called_once()

    def test_unexpected_server_error_still_cleans_up(self):
        _, resource = self.run_main(failure=RuntimeError)
        resource.server.server_close.assert_called_once()
        resource.controller.store.close.assert_called_once()
