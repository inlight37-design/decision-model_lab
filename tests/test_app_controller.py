"""A1 controller 검사 — 결과 수용 관문, 봉인과 공개, 수동 참여자, 다시 시작, 자리와 상한, 화면 서버의 토큰.

대부분은 프로세스를 띄우지 않는 합성 실행기로 본다. 마지막 묶음만 모의 CLI를 실제 실행 경로(Windows job object,
Linux bubblewrap)로 돌린다. 모델은 부르지 않는다.
"""
import http.client
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest

from app import controller as c
from app.store import Store, events
from core import adapters, runner


def claude_stdout(text="모의 답", error=False):
    return json.dumps({"type": "result", "is_error": error, "result": text,
                       "modelUsage": {"m": {}}, "usage": {"input_tokens": 10, "output_tokens": 999}})


class SyntheticExecutor:
    """프로세스 없이 결과를 만든다. hold에 든 참여자는 release()까지 기다린다."""
    name = "synthetic"

    def __init__(self, outcomes=None, hold=()):
        self.outcomes, self.hold = outcomes or {}, set(hold)
        self.gates = {pid: threading.Event() for pid in self.hold}
        self.started = []

    def release(self, pid):
        self.gates[pid].set()

    def execute(self, spec, prompt, work_dir, timeout):
        self.started.append(spec.pid)
        if spec.pid in self.gates:
            self.gates[spec.pid].wait(10)
        kind = self.outcomes.get(spec.pid, "ok")
        delivery = runner.INPUT_FAILED if kind == "partial" else runner.INPUT_COMPLETE
        containment = runner.PROCESS_GROUP if kind == "unknown" else runner.JOB_OBJECT
        result = runner.RunResult(("synthetic",), runner.EXITED, 1 if kind == "fail" else 0,
                                  claude_stdout(f"{spec.pid}의 답", error=kind == "fail"), "", False, False, 5, 0, True,
                                  containment=containment, input_delivery=delivery)
        return result, adapters.interpret("claude-code", result, requested_model="m")


def wait_for(check, timeout=10.0):
    deadline = threading.Event()
    for _ in range(int(timeout / 0.02)):
        if check():
            return True
        deadline.wait(0.02)
    return False


def cli(pid):
    return c.ParticipantSpec(pid, pid.upper(), "test", c.CLI, "claude-code", "m")


def manual(pid):
    return c.ParticipantSpec(pid, pid.upper(), "test", c.MANUAL)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dml-app-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.store = Store(self.tmp / "store" / "journal.db")
        self.addCleanup(self.store.close)

    def controller(self, executor, **kwargs):
        kwargs.setdefault("work_root", str(self.tmp / "work"))
        return c.Controller(self.store, executor, **kwargs)

    def run_view(self, ctl, run_id):
        return next(r for r in ctl.view()["runs"] if r["run_id"] == run_id)

    def part(self, ctl, run_id, pid):
        return next(p for p in self.run_view(ctl, run_id)["participants"] if p["pid"] == pid)


class GateAndRevealTests(Base):
    def test_drafts_stay_sealed_until_everyone_is_done_then_the_controller_reveals(self):
        ex = SyntheticExecutor(hold=("b",))
        ctl = self.controller(ex)
        run_id = ctl.create_run("질문", [cli("a"), cli("b")], min_independent=2)
        wait_for(lambda: self.part(ctl, run_id, "a")["state"] == c.ACCEPTED)
        sealed = self.run_view(ctl, run_id)
        self.assertEqual(sealed["phase"], "drafting")
        a = self.part(ctl, run_id, "a")
        self.assertNotIn("draft", a)                                  # 내용을 넘기지 않는다
        self.assertFalse({"usage", "duration_ms"} & set(a["result"]))  # 길이를 짐작하게 하는 것도
        self.assertNotIn("a의 답", json.dumps(ctl.view(), ensure_ascii=False))
        ex.release("b")
        self.assertTrue(ctl.wait_idle())
        opened = self.run_view(ctl, run_id)
        self.assertEqual(opened["phase"], "revealed")
        self.assertEqual({p["pid"]: p["draft"] for p in opened["participants"]}, {"a": "a의 답", "b": "b의 답"})
        self.assertIn("usage", self.part(ctl, run_id, "a")["result"])

    def test_a_partly_delivered_question_is_not_accepted_and_reduction_needs_approval(self):
        ctl = self.controller(SyntheticExecutor({"b": "partial"}))
        run_id = ctl.create_run("질문", [cli("a"), cli("b")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        b = self.part(ctl, run_id, "b")
        self.assertEqual((b["state"], b["status"]), (c.REJECTED, "input_error"))
        view = self.run_view(ctl, run_id)
        self.assertEqual(view["phase"], "drafting")                   # 남은 사람으로 자동 진행하지 않는다
        self.assertIn("축소 승인", view["note"])
        self.assertEqual(view["budget"]["breakdown"], {"succeeded": 1, "failed": 1, "unknown": 0})
        ctl.approve_reduction(run_id)
        self.assertEqual(self.run_view(ctl, run_id)["phase"], "revealed")

    def test_below_quorum_is_held_even_after_approval(self):
        ctl = self.controller(SyntheticExecutor({"b": "fail"}))
        run_id = ctl.create_run("질문", [cli("a"), cli("b")], min_independent=2)
        self.assertTrue(ctl.wait_idle())
        ctl.approve_reduction(run_id)
        view = self.run_view(ctl, run_id)
        self.assertEqual(view["phase"], "drafting")
        self.assertIn("유료로 채우지 않습니다", view["note"])

    def test_an_unconfirmed_ending_keeps_its_slot_blocks_reveal_and_is_never_retried(self):
        ex = SyntheticExecutor({"a": "unknown"})
        ctl = self.controller(ex, max_parallel=2)
        run_id = ctl.create_run("질문", [cli("a"), cli("b")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.part(ctl, run_id, "a")["state"], c.UNKNOWN)
        self.assertNotIn("draft", self.part(ctl, run_id, "a"))
        self.assertEqual(ctl.view()["slots"]["used"], 1)             # 자리를 풀지 않는다
        self.assertEqual(self.run_view(ctl, run_id)["phase"], "drafting")
        ctl.acknowledge_unknown(run_id, "a")
        self.assertEqual(ctl.view()["slots"]["used"], 0)
        self.assertEqual(ex.started.count("a"), 1)                   # 다시 부르지 않았다
        ctl.approve_reduction(run_id)
        self.assertEqual(self.run_view(ctl, run_id)["phase"], "revealed")

    def test_slots_and_the_unsettled_limit_bound_new_attempts(self):
        ex = SyntheticExecutor(hold=("a", "b", "c"))
        ctl = self.controller(ex, max_parallel=2)
        ctl.create_run("질문", [cli("a"), cli("b"), cli("c")], min_independent=1)
        wait_for(lambda: len(ex.started) == 2)
        threading.Event().wait(0.2)
        self.assertEqual(sorted(ex.started), ["a", "b"])             # 자리 두 개
        for pid in "abc":
            ex.release(pid)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(sorted(ex.started), ["a", "b", "c"])
        blocked = self.controller(SyntheticExecutor({"x": "unknown", "y": "unknown"}), unsettled_limit=2)
        blocked.create_run("질문", [cli("x"), cli("y")], min_independent=1)
        self.assertTrue(blocked.wait_idle())
        later = SyntheticExecutor()
        blocked.executor = later
        blocked.create_run("다음 질문", [cli("z")], min_independent=1)
        self.assertEqual(later.started, [])                          # 정리 안 된 시도가 상한에 닿았다

    def test_requests_below_quorum_are_refused_before_anything_starts(self):
        ex = SyntheticExecutor()
        ctl = self.controller(ex)
        with self.assertRaises(c.ControllerError):
            ctl.create_run("질문", [cli("a")], min_independent=2)
        with self.assertRaises(c.ControllerError):
            ctl.create_run("   ", [cli("a")], min_independent=1)
        self.assertEqual(ex.started, [])


class ManualTests(Base):
    def test_manual_answers_are_checked_against_the_input_and_the_phase(self):
        ctl = self.controller(SyntheticExecutor())
        run_id = ctl.create_run("질문", [cli("a"), manual("gpt")], min_independent=2)
        self.assertTrue(ctl.wait_idle())
        view = self.run_view(ctl, run_id)
        self.assertEqual(self.part(ctl, run_id, "gpt")["state"], c.AWAITING_USER)
        self.assertIn("관측 안 됨", " ".join(self.part(ctl, run_id, "gpt")["contamination"]))
        with self.assertRaisesRegex(c.ControllerError, "different input"):
            ctl.submit_manual(run_id, "gpt", "답", "0" * 64)
        with self.assertRaisesRegex(c.ControllerError, "empty"):
            ctl.submit_manual(run_id, "gpt", "  ", view["input_sha256"])
        ctl.submit_manual(run_id, "gpt", "원본 앱의 답", view["input_sha256"])
        opened = self.run_view(ctl, run_id)
        self.assertEqual(opened["phase"], "revealed")
        self.assertEqual(self.part(ctl, run_id, "gpt")["draft"], "원본 앱의 답")
        with self.assertRaisesRegex(c.ControllerError, "late"):
            ctl.submit_manual(run_id, "gpt", "또 다른 답", view["input_sha256"])
        kinds = [e["kind"] for e in events(self.store, run_id)]
        self.assertEqual(kinds.count("manual_refused"), 3)           # 거절도 기록한다

    def test_withdrawing_a_manual_participant_does_not_fill_the_seat(self):
        ctl = self.controller(SyntheticExecutor())
        run_id = ctl.create_run("질문", [cli("a"), manual("gpt")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        ctl.withdraw_manual(run_id, "gpt")
        self.assertIn("축소 승인", self.run_view(ctl, run_id)["note"])


class RestartTests(Base):
    def test_attempts_running_at_restart_become_unknown_and_are_not_rerun(self):
        ex = SyntheticExecutor(hold=("a",))
        first = self.controller(ex)
        run_id = first.create_run("질문", [cli("a")], min_independent=1)
        self.assertEqual(self.part(first, run_id, "a")["state"], c.RUNNING)
        again = SyntheticExecutor()
        second = self.controller(again)                              # 같은 journal로 다시 시작
        self.assertEqual(self.part(second, run_id, "a")["state"], c.UNKNOWN)
        self.assertEqual(again.started, [])
        ex.release("a")
        first.wait_idle()


class ServerTests(Base):
    def setUp(self):
        super().setUp()
        from http.server import ThreadingHTTPServer
        from app import server as s
        ctl = self.controller(SyntheticExecutor())
        self.token = "T" * 43
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), s.make_handler(ctl, self.token, 0))
        self.port = self.httpd.server_address[1]
        self.httpd.RequestHandlerClass = s.make_handler(ctl, self.token, self.port)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def get(self, path, token=None, host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Host": host or f"127.0.0.1:{self.port}"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        conn.request("GET", path, headers=headers)
        res = conn.getresponse()
        body = res.read()
        conn.close()
        return res.status, body

    def test_every_api_call_needs_the_token_and_our_host(self):
        self.assertEqual(self.get("/api/state")[0], 401)
        self.assertEqual(self.get("/api/state", token="wrong")[0], 401)
        self.assertEqual(self.get("/api/state", token=self.token)[0], 200)
        self.assertEqual(self.get("/api/state", token=self.token, host="evil.example:80")[0], 403)
        status, page = self.get("/")
        self.assertEqual(status, 200)
        self.assertNotIn(self.token.encode(), page)                  # 페이지를 받아 가도 토큰은 없다


def real_path_available():
    if runner.IS_WINDOWS:
        return True
    return sys.platform == "linux" and c._bwrap_trusted()


@unittest.skipUnless(real_path_available(), "Windows job object나 신뢰한 bubblewrap이 있는 Linux에서만")
class MockCliIntegrationTests(Base):
    """모의 CLI를 실제 실행 경로로 돌린다. 모델은 부르지 않는다."""

    def test_mock_clis_run_through_the_real_path(self):
        ex = c.MockExecutor(never=(str((self.tmp / "store").resolve()),))
        ctl = self.controller(ex, timeout=30)
        specs = [c.ParticipantSpec("claude", "Claude Code", "anthropic", c.CLI, "claude-code", "mock-claude"),
                 c.ParticipantSpec("codex", "Codex", "openai", c.CLI, "codex", "mock-codex"),
                 c.ParticipantSpec("short", "Codex", "openai", c.CLI, "codex", "mock-codex", "partial_input")]
        # 입력이 파이프 버퍼보다 커야 "1바이트만 읽고 닫음"이 쓰는 쪽에서 드러난다. 작으면 버퍼가 다 받아 버린다
        run_id = ctl.create_run("한글 질문과 --선행 대시\n" + "자료 " * 100_000, specs, min_independent=2)
        self.assertTrue(ctl.wait_idle(60))
        parts = {p["pid"]: p for p in self.run_view(ctl, run_id)["participants"]}
        self.assertEqual(parts["claude"]["state"], c.ACCEPTED, parts["claude"])
        self.assertEqual(parts["codex"]["state"], c.ACCEPTED, parts["codex"])
        self.assertEqual((parts["short"]["state"], parts["short"]["status"]), (c.REJECTED, "input_error"))
        self.assertTrue(parts["claude"]["result"]["tree_confirmed_empty"])
        ctl.approve_reduction(run_id)
        opened = {p["pid"]: p for p in self.run_view(ctl, run_id)["participants"]}
        self.assertIn("한글 질문과 --선행 대시", opened["claude"]["draft"])   # 질문이 stdin으로 그대로 갔다
        self.assertIn("모의 출력", opened["codex"]["draft"])


if __name__ == "__main__":
    unittest.main()
