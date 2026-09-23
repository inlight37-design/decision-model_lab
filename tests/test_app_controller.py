"""A1 controller 검사 — 결과 수용 관문, 봉인과 공개, 수동 참여자, 다시 시작, 자리와 상한, 화면 서버의 토큰.

대부분은 프로세스를 띄우지 않는 합성 실행기로 본다. 마지막 묶음만 모의 CLI를 실제 실행 경로(Windows job object,
Linux bubblewrap)로 돌린다. 모델은 부르지 않는다.
"""
import http.client
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import threading
import unittest

from app import controller as c, server
from app.store import LedgerBusy, Store, StoreError, events
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
        # A1 리뷰 A1-03: 예전에는 옛 시도의 결과가 여기서 unknown을 accepted로 덮었고, 이 시험은 그 끝을 보지 않았다
        a = self.part(second, run_id, "a")
        self.assertEqual(a["state"], c.UNKNOWN)
        self.assertIsNone(self.store.row("SELECT 1 FROM drafts WHERE run_id = ?", run_id))
        self.assertIn("attempt_result_ignored", [e["kind"] for e in events(self.store, run_id)])


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


# ---- A1 리뷰(PR #7)의 반례 ----------------------------------------------------------------------------
# 리뷰의 reproduce.py가 대상 커밋에서 관측한 것을 제품 시험으로 옮기고 기대를 뒤집었다. 모델은 부르지 않는다.

SENTINEL = "A1_SYNTHETIC_PRIVATE_DETAIL"


def codex(pid):
    return c.ParticipantSpec(pid, pid.upper(), "test", c.CLI, "codex", "m")


class ShapedExecutor:
    """참여자별로 답·오류·입력 전달·보고 모델을 정하는 합성 실행기. 프로세스는 띄우지 않는다."""
    name = "synthetic"

    def __init__(self, **shapes):
        self.shapes, self.started = shapes, []

    def execute(self, spec, prompt, work_dir, timeout):
        self.started.append(spec.pid)
        shape = {"text": f"{spec.pid}의 답", "error": None, "delivery": runner.INPUT_COMPLETE, "model": "m",
                 **self.shapes.get(spec.pid, {})}
        if spec.adapter_id == "codex":
            lines = [{"type": "item.completed", "item": {"type": "agent_message", "text": shape["text"]}},
                     {"type": "turn.failed", "error": {"message": shape["error"]}} if shape["error"]
                     else {"type": "turn.completed"}]
            stdout = "\n".join(json.dumps(x, ensure_ascii=False) for x in lines)
        else:
            stdout = json.dumps({"type": "result", "is_error": shape["error"] is not None, "result": shape["text"],
                                 "terminal_reason": shape["error"], "modelUsage": {shape["model"]: {}}})
        result = runner.RunResult(("synthetic",), runner.EXITED, int(shape["error"] is not None), stdout, "",
                                  False, False, 5, 0, True, containment=runner.JOB_OBJECT,
                                  input_delivery=shape["delivery"])
        return result, adapters.interpret(spec.adapter_id, result, requested_model=spec.model or "")


class ReviewA1SealTests(Base):
    def test_cli_error_text_stays_out_of_the_view_until_everyone_is_done(self):
        """A1-01. 공개 전 화면은 허용 목록의 고정 필드만 받는다. 오류 원문은 모든 참여자가 끝난 뒤에."""
        for make in (cli, codex):
            with self.subTest(adapter=make("a").adapter_id):
                ctl = self.controller(ShapedExecutor(a={"error": SENTINEL}))
                run_id = ctl.create_run("질문", [make("a"), cli("b"), manual("gpt")], min_independent=1)
                self.assertTrue(ctl.wait_idle())
                self.assertNotIn(SENTINEL, json.dumps(self.run_view(ctl, run_id), ensure_ascii=False))
                self.assertTrue(self.run_view(ctl, run_id)["diagnostics_sealed"])
                a, b = self.part(ctl, run_id, "a"), self.part(ctl, run_id, "b")
                self.assertEqual((a["state"], a["status"], a["detail"]), (c.REJECTED, "cli_error", None))
                for p in (a, b):
                    self.assertLessEqual(set(p["result"]), c.SEALED_VIEW_KEYS)
                ctl.withdraw_manual(run_id, "gpt")                   # 이제 누구도 더 답하지 않는다
                self.assertIn(SENTINEL, self.part(ctl, run_id, "a")["detail"])
                self.assertNotIn("usage", self.part(ctl, run_id, "b")["result"])   # 공개 전이다
                self.assertNotIn("draft", self.part(ctl, run_id, "b"))


class ReviewA1AcceptanceTests(Base):
    def test_the_gate_needs_delivery_a_real_answer_and_the_requested_model(self):
        """A1-02·A1-07. 입력 전달 기록 없음, 빈 답, 공백 답, 다른 모델은 받지 않고 구성 축소로 드러낸다."""
        for label, shape, status in (("no stdin record", {"delivery": None}, "input_error"),
                                     ("empty", {"text": ""}, "empty_answer"),
                                     ("whitespace", {"text": "  \n"}, "empty_answer"),
                                     ("another model", {"model": "other-model"}, "model_mismatch")):
            with self.subTest(label):
                ctl = self.controller(ShapedExecutor(a=shape))
                run_id = ctl.create_run("질문", [cli("a"), cli("b")], min_independent=1)
                self.assertTrue(ctl.wait_idle())
                a = self.part(ctl, run_id, "a")
                self.assertEqual((a["state"], a["status"]), (c.REJECTED, status))
                self.assertIn("축소 승인", self.run_view(ctl, run_id)["note"])   # 조용히 넘어가지 않는다
                ctl.approve_reduction(run_id)
                opened = self.run_view(ctl, run_id)
                self.assertEqual(opened["phase"], "revealed")
                self.assertEqual([p["pid"] for p in opened["participants"] if "draft" in p], ["b"])

    def test_a_cli_that_reports_no_model_is_still_accepted(self):
        """K32. Codex는 모델 이름을 알리지 않는다 — model_match None은 불일치가 아니다."""
        ctl = self.controller(ShapedExecutor())
        run_id = ctl.create_run("질문", [codex("a")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        opened = self.run_view(ctl, run_id)
        self.assertEqual(opened["phase"], "revealed")
        self.assertIsNone(opened["participants"][0]["result"]["model_match"])


class ReviewA1OwnershipTests(Base):
    def test_a_journal_opens_in_one_store_at_a_time(self):
        """A1-03. 원장 잠금. 닫으면 다시 열 수 있다."""
        path = self.tmp / "other" / "journal.db"
        first = Store(path)
        with self.assertRaises(LedgerBusy):
            Store(path)
        first.close()
        first.close()                                                # 두 번 닫아도 된다
        Store(path).close()

    def test_a_second_server_on_the_same_data_leaves_the_first_alone(self):
        """A1-03. 예전에는 포트 bind 전에 복구·토큰 교체를 해서, 실패한 두 번째 시작이 돌던 시도를 unknown으로
        바꾸고 토큰 파일을 갈았다. 이제 원장 잠금에서 멈추고 아무것도 바꾸지 않는다."""
        data = self.tmp / "data"
        httpd, _token, first = server.serve(data, 0)
        try:
            ex = SyntheticExecutor(hold=("a",))
            first.executor, first.work_root = ex, str(self.tmp / "work")
            run_id = first.create_run("질문", [cli("a")], min_independent=1)
            token_before = (data / "control-token").read_bytes()
            with self.assertRaises(LedgerBusy):
                server.serve(data, 0)
            self.assertEqual((data / "control-token").read_bytes(), token_before)
            self.assertEqual(self.part(first, run_id, "a")["state"], c.RUNNING)
            ex.release("a")
            self.assertTrue(first.wait_idle())
            self.assertEqual(self.run_view(first, run_id)["phase"], "revealed")
        finally:
            ex.release("a")
            first.wait_idle()
            httpd.server_close()
            first.store.close()

    def test_two_servers_cannot_share_a_port(self):
        """Windows의 SO_REUSEADDR은 듣고 있는 포트에도 두 번째 bind를 허락했다(A1 리뷰 반영 중 관측)."""
        httpd = server._Server(("127.0.0.1", 0), BaseHTTPRequestHandler)
        self.addCleanup(httpd.server_close)
        with self.assertRaises(OSError):
            server._Server(("127.0.0.1", httpd.server_address[1]), BaseHTTPRequestHandler).server_close()

    def test_one_participant_starts_once_even_with_two_controllers(self):
        """같은 journal의 controller 둘이 거의 동시에 pump하면 같은 참여자를 두 번 불렀다 — 화면 예산은 1회로
        보였다(A1 리뷰 반영 중 재현). 끼어드는 순서를 고정한다: A가 대기 목록을 읽은 직후 B가 먼저 시작한다."""
        ex_a, ex_b = SyntheticExecutor(), SyntheticExecutor(hold=("a",))
        first = self.controller(ex_a, max_parallel=0)                # 자리 0: 만들기만 한다
        run_id = first.create_run("질문", [cli("a")], min_independent=1)
        second = self.controller(ex_b, max_parallel=2)
        first.max_parallel = 2
        read, fired = self.store.rows, []

        def rows(sql, *args):
            found = read(sql, *args)
            if "WHERE p.state = ?" in sql and not fired:
                fired.append(True)
                second.resume()                                      # B가 먼저 queued → running
            return found

        self.store.rows = rows
        try:
            first.pump()
        finally:
            del self.store.rows
            ex_b.release("a")
        self.assertTrue(first.wait_idle() and second.wait_idle())
        self.assertEqual((ex_a.started, ex_b.started), ([], ["a"]))
        self.assertEqual([e["kind"] for e in events(self.store, run_id)].count("attempt_started"), 1)

    def test_a_result_after_the_user_acknowledged_unknown_is_ignored(self):
        """A1-03의 남은 조합: 사용자가 unknown을 확인한 뒤 옛 시도의 결과가 와도 초안·명단을 바꾸지 않는다."""
        ex = SyntheticExecutor(hold=("a",))
        first = self.controller(ex)
        run_id = first.create_run("질문", [cli("a"), manual("gpt")], min_independent=1)
        second = self.controller(SyntheticExecutor())
        second.acknowledge_unknown(run_id, "a")
        ex.release("a")
        self.assertTrue(first.wait_idle())
        a = self.part(second, run_id, "a")
        self.assertEqual((a["state"], a["status"]), (c.REJECTED, "unknown_acknowledged"))
        self.assertIsNone(self.store.row("SELECT 1 FROM drafts WHERE run_id = ? AND pid = 'a'", run_id))


class ReviewA1RestartTests(Base):
    def test_a_run_stopped_between_its_last_draft_and_reveal_is_revealed_on_restart(self):
        """A1-05. 수정 전 원장은 마지막 초안 저장과 공개가 다른 거래였다. 다시 시작하면 공개 관문을 다시 본다."""
        ctl = self.controller(SyntheticExecutor())
        run_id = ctl.create_run("질문", [manual("a"), manual("b")], min_independent=2)
        digest = self.run_view(ctl, run_id)["input_sha256"]
        ctl.submit_manual(run_id, "a", "A", digest)
        with self.store.tx() as tx:                                  # 공개 없이 마지막 초안만 저장된 상태
            tx.execute("INSERT INTO drafts VALUES (?, 'b', 'B', ?, 'manual', 0)", run_id, "0" * 64)
            tx.execute("UPDATE participants SET state = 'accepted', status = 'manual' WHERE run_id = ? AND pid = 'b'",
                       run_id)
        self.assertEqual(self.run_view(ctl, run_id)["phase"], "drafting")
        again = self.controller(SyntheticExecutor())
        self.assertEqual(self.run_view(again, run_id)["phase"], "revealed")

    def test_queued_attempts_wait_for_the_user_after_a_restart(self):
        """A1-05. 시작하지 못한 시도는 서버가 다시 뜬다고 저절로 시작하지 않는다 — 취소가 없어서 서버를 끄는
        것이 지금의 멈춤 수단이다(K19). 사용자가 이어서 시작하라고 하면 한 번 시작한다."""
        first = self.controller(SyntheticExecutor(), max_parallel=0)
        run_id = first.create_run("질문", [cli("a")], min_independent=1)
        ex = SyntheticExecutor()
        again = self.controller(ex)
        self.assertTrue(again.view()["paused"])
        again.pump()
        again.create_run("다른 질문", [cli("b")], min_independent=1)
        self.assertEqual(ex.started, [])
        again.resume()
        self.assertTrue(again.wait_idle())
        self.assertEqual(sorted(ex.started), ["a", "b"])
        self.assertFalse(again.view()["paused"])
        self.assertEqual(self.part(again, run_id, "a")["state"], c.ACCEPTED)


class ReviewA1ApprovalTests(Base):
    def test_a_reduction_is_approved_only_while_the_controller_waits_for_it(self):
        """A1-06. 이탈 전에 한 승인이 나중 구성에 쓰이지 않는다. 없는 실행에는 사건도 남기지 않는다."""
        ctl = self.controller(SyntheticExecutor())
        run_id = ctl.create_run("질문", [manual("a"), manual("b")], min_independent=1)
        with self.assertRaisesRegex(c.ControllerError, "no reduction"):
            ctl.approve_reduction(run_id)
        with self.assertRaises(c.ControllerError):
            ctl.approve_reduction("r-none")
        self.assertIsNone(self.store.row("SELECT 1 FROM events WHERE run_id = 'r-none'"))
        ctl.submit_manual(run_id, "a", "A", self.run_view(ctl, run_id)["input_sha256"])
        ctl.withdraw_manual(run_id, "b")
        view = self.run_view(ctl, run_id)
        self.assertEqual((view["phase"], view["reduction_approved"]), ("drafting", False))   # 새로 물어야 한다
        ctl.approve_reduction(run_id)
        self.assertEqual(self.run_view(ctl, run_id)["phase"], "revealed")
        with self.assertRaisesRegex(c.ControllerError, "no reduction"):
            ctl.approve_reduction(run_id)


class JournalSchemaTests(unittest.TestCase):
    """K28. 스키마 버전(user_version)과 이전 절차."""

    def setUp(self):
        self.path = Path(tempfile.mkdtemp(prefix="dml-schema-")) / "journal.db"
        self.addCleanup(shutil.rmtree, self.path.parent, True)

    def test_an_unversioned_journal_is_migrated_in_place(self):
        db = sqlite3.connect(self.path)
        db.executescript("CREATE TABLE participants (run_id TEXT NOT NULL, pid TEXT NOT NULL, spec TEXT NOT NULL, "
                         "state TEXT NOT NULL, status TEXT, detail TEXT, result TEXT, PRIMARY KEY (run_id, pid));"
                         "INSERT INTO participants VALUES ('r1', 'a', '{}', 'awaiting_user', NULL, NULL, NULL);")
        db.close()
        store = Store(self.path)
        self.addCleanup(store.close)
        self.assertEqual(store.row("PRAGMA user_version")[0], 1)
        self.assertIn("attempt", [r[1] for r in store.rows("PRAGMA table_info(participants)")])
        self.assertEqual(store.row("SELECT state FROM participants WHERE pid = 'a'")["state"], "awaiting_user")

    def test_a_newer_journal_is_left_untouched(self):
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA user_version = 99")
        db.close()
        with self.assertRaises(StoreError):
            Store(self.path)
        db = sqlite3.connect(self.path)
        self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 99)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0], 0)
        db.close()
        with self.assertRaises(StoreError):                          # 잠금이 풀려서 다시 시도해도 같은 답이다
            Store(self.path)


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
