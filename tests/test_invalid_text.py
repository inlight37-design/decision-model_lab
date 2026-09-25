"""고립 surrogate가 든 글이 실행을 멈추게 하지 않는다(카드 #70, 2026-09-25 외부 검토 R05). 합성 실행기만 쓴다.

JSON의 올바른 이스케이프 "\\ud800"은 파이썬 글에서 고립 surrogate가 되고, UTF-8 저장·sha256·HTTP 출력에서 모두
실패한다. 예전에는 참여자가 running으로 남아 자리를 차지하고 실행이 공개되지 않았다.
"""
from dataclasses import replace
import json
from unittest.mock import patch

from app import controller as c
from app.store import events
from core import adapters, runner
import test_app_controller as support
from test_live_cli import UnverifiedSynthetic

LONE = "answer \ud800 end"


class Answers(UnverifiedSynthetic):
    """참여자마다 정해 둔 답과 결과를 돌려주는 실행기."""

    def __init__(self, answers, *, detail=None, notes=(), **kwargs):
        super().__init__(**kwargs)
        self.answers, self.detail, self.notes = answers, detail, notes

    def execute(self, spec, prompt, work_dir, timeout, *, cancel=None):
        self.started.append(spec.pid)
        result = runner.RunResult(("synthetic",), runner.EXITED, 0, support.claude_stdout(self.answers[spec.pid]), "",
                                  False, False, 5, 0, True, containment=runner.JOB_OBJECT,
                                  input_delivery=runner.INPUT_COMPLETE, notes=tuple(self.notes))
        outcome = adapters.interpret("claude-code", result, requested_model="m")
        if self.detail is not None:
            outcome = replace(outcome, detail=self.detail)
        return result, outcome


class InvalidTextTests(support.Base):
    def run_of(self, ex, pids=("a", "b")):
        ctl = self.controller(ex)
        rid = ctl.create_run("q", [support.cli(pid) for pid in pids], min_independent=1,
                             quorum_policy=c.INCLUDE_UNVERIFIED)
        self.assertTrue(ctl.wait_idle())
        return ctl, rid

    def parts(self, ctl, rid):
        return {p["pid"]: p for p in self.run_view(ctl, rid)["participants"]}

    def test_a_lone_surrogate_answer_is_a_format_error_and_the_run_moves_on(self):
        ctl, rid = self.run_of(Answers({"a": LONE, "b": "fine"}))
        parts = self.parts(ctl, rid)
        self.assertEqual((parts["a"]["state"], parts["a"]["status"]), ("rejected", "format_error"))
        self.assertEqual(parts["b"]["state"], "accepted")
        view = ctl.view()
        self.assertEqual((view["slots"]["used"], view["unsettled"]["count"]), (0, 0))
        # 멈추지 않고 정상 경로로 간다: 참여자가 빠졌으니 축소 승인을 기다리고, 승인하면 공개된다.
        self.assertTrue(self.run_view(ctl, rid)["gate"]["can_approve_reduction"])
        ctl.approve_reduction(rid)
        self.assertEqual(self.run_view(ctl, rid)["phase"], "revealed")
        self.assertIsNone(self.store.row("SELECT 1 FROM drafts WHERE run_id = ? AND pid = 'a'", rid))
        json.dumps(view, ensure_ascii=False).encode("utf-8")   # 화면으로 보낼 수 있다

    def test_valid_text_that_looks_similar_is_accepted_unchanged(self):
        for text in ("emoji \U0001F600 ok", "literal \\ud800 is plain text"):
            with self.subTest(text=text):
                ctl, rid = self.run_of(Answers({"a": text}), pids=("a",))
                self.assertEqual(self.parts(ctl, rid)["a"]["draft"], text)

    def test_metadata_with_a_lone_surrogate_is_escaped_and_marked_not_stranded(self):
        ex = Answers({"a": "fine"}, detail="cli said \ud800", notes=("note \udfff",))
        ctl, rid = self.run_of(ex, pids=("a",))
        part = self.parts(ctl, rid)["a"]
        self.assertEqual(part["state"], "accepted")
        self.assertTrue(part["result"]["escaped_text"])
        self.assertIn("\\udfff", json.dumps(part["result"]["notes"]))
        self.assertEqual(ctl.view()["slots"]["used"], 0)

    def test_a_result_that_cannot_be_stored_closes_the_attempt_instead_of_leaving_it_running(self):
        ex = Answers({"a": "fine"})
        ctl = self.controller(ex)
        real = c.Controller._maybe_reveal
        calls = {"n": 0}

        def broken(self, *args, **kwargs):   # 결과를 쓰는 거래 안에서 한 번만 실패시킨다
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("storage failed")
            return real(self, *args, **kwargs)
        with patch.object(c.Controller, "_maybe_reveal", broken):
            rid = ctl.create_run("q", [support.cli("a")], min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)
            self.assertTrue(ctl.wait_idle())
        part = self.parts(ctl, rid)["a"]
        self.assertEqual((part["state"], part["status"]), ("rejected", "result_not_stored"))   # 종료는 확인됐다
        self.assertEqual((ctl.view()["slots"]["used"], ctl.unsettled()), (0, 0))
        kinds = [e["kind"] for e in events(self.store, rid)]
        self.assertIn("attempt_result_not_stored", kinds)
        self.assertNotIn("draft_sealed", kinds)

    def test_questions_sources_and_manual_answers_are_refused_before_anything_is_stored(self):
        ctl = self.controller(Answers({}))
        with self.assertRaisesRegex(c.ControllerError, "not valid Unicode"):
            ctl.create_run("q \ud800", [support.manual("m")], min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)
        with self.assertRaisesRegex(c.ControllerError, "valid Unicode"):
            ctl.create_run("q", [support.manual("m")], min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED,
                           sources=[("a.txt", "bad \ud800")])
        self.assertEqual(ctl.view()["runs"], [])
        rid = ctl.create_run("q", [support.manual("m")], min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)
        digest = self.run_view(ctl, rid)["input_sha256"]
        with self.assertRaisesRegex(c.ControllerError, "not valid Unicode"):
            ctl.submit_manual(rid, "m", LONE, digest)
        self.assertEqual(self.parts(ctl, rid)["m"]["state"], "awaiting_user")
        ctl.submit_manual(rid, "m", "fine", digest)   # 같은 참여자가 올바른 답을 다시 낼 수 있다
        self.assertEqual(self.parts(ctl, rid)["m"]["state"], "accepted")
