"""실제 합성의 호출·자리·미종료 계약 회귀. 가짜 실행기만 쓰며 모델은 부르지 않는다."""
from dataclasses import replace
import threading
from unittest.mock import patch

from app import controller as c
from app.store import events
from core import runner
import test_app_controller as support
import test_model_synthesis as synthesis_support

SynthExecutor = synthesis_support.SynthExecutor


class Unconfirmed(SynthExecutor):
    def execute(self, spec, prompt, work_dir, timeout, *, cancel=None):
        result, outcome = super().execute(spec, prompt, work_dir, timeout, cancel=cancel)
        if spec.pid == "synthesis":
            result = replace(result, containment=runner.PROCESS_GROUP)
        return result, outcome


class SynthesisLifecycleTests(support.Base):
    revealed = synthesis_support.ControllerTests.revealed
    finish = synthesis_support.ControllerTests.finish

    def controller(self, executor, **kwargs):
        ctl = super().controller(executor, **kwargs)

        def cleanup():
            for held in executor.gates.values():
                held.set()
            # wait_idle은 controller 잠금 안에서 본다. 잠금 없이 보면 합성 스레드가 자리를 비운 뒤 같은 잠금 안에서
            # pump()하는 사이에 원장이 닫혀 "closed database" 스레드 오류가 났다(Windows CI, 2026-09-25).
            self.assertTrue(ctl.wait_idle())
        self.addCleanup(cleanup)
        return ctl

    def test_the_same_drafts_can_be_synthesized_again_by_another_provider(self):
        # 사용자 결정(2026-09-25, 인계 2절 23): 실행마다 합성 한 번·참여자 provider만이라는 제약을 없앴다.
        # 부를 때마다 새 호출 하나를 같은 상한에서 예약하고, 같은 실행은 같은 이름표 순서를 본다.
        ex = SynthExecutor()
        ctl, rid = self.revealed(ex, cap=8)
        ctl.synthesize_with_model(rid, "claude-code")
        self.finish(ctl, rid)
        ctl.synthesize_with_model(rid, "codex", spec=c.ParticipantSpec("codex", "Codex", "openai", c.CLI, "codex", "m"))   # 이 실행의 참여자가 아닌 설정된 provider
        self.finish(ctl, rid)
        self.assertEqual(ctl.call_budget()["used"], 4)
        self.assertEqual(ex.started.count("synthesis"), 2)
        attempts = self.run_view(ctl, rid)["model_syntheses"]
        self.assertEqual([a["status"] for a in attempts], ["completed", "completed"])
        self.assertEqual([a["result"]["synthesizer"]["adapter_id"] for a in attempts], ["claude-code", "codex"])
        started = [e for e in events(self.store, rid) if e["kind"] == "synthesis_started"]
        self.assertEqual(started[0]["labels"], started[1]["labels"])
        reserved = [e for e in events(self.store, rid) if e.get("purpose") == "synthesis"]
        self.assertEqual([e["adapter_id"] for e in reserved], ["claude-code", "codex"])
        self.assertEqual(self.run_view(ctl, rid)["synthesis"]["synthesizer"]["adapter_id"], "codex")   # 가장 최근

    def test_an_unconfigured_synthesizer_is_refused_before_anything_is_reserved(self):
        ex = SynthExecutor()
        ctl, rid = self.revealed(ex, cap=8)
        for adapter, spec in (("codex", None), ("codex", support.cli("x")), ("gemini", None)):
            with self.subTest(adapter=adapter), self.assertRaisesRegex(c.ControllerError, "configured CLI provider"):
                ctl.synthesize_with_model(rid, adapter, spec=spec)
        self.assertEqual(ctl.call_budget()["used"], 2)
        self.assertNotIn("synthesis", ex.started)

    def test_a_failed_synthesis_can_be_tried_again_and_mock_resets_nothing(self):
        ex = SynthExecutor(answer=lambda: "not JSON")
        ctl, rid = self.revealed(ex, cap=8)
        ctl.synthesize_with_model(rid, "claude-code")
        self.finish(ctl, rid)
        ctl.synthesize(rid)
        restarted = self.controller(ex, max_real_calls=8)
        self.assertEqual(len(self.run_view(restarted, rid)["model_syntheses"]), 1)
        self.assertEqual(restarted.call_budget()["used"], 3)   # 실패한 호출은 환불하지 않는다
        restarted.synthesize_with_model(rid, "claude-code")
        self.finish(restarted, rid)
        self.assertEqual(restarted.call_budget()["used"], 4)   # 다시 부르면 새 호출 하나
        self.assertEqual([a["status"] for a in self.run_view(restarted, rid)["model_syntheses"]], ["failed", "failed"])

    def test_synthesis_obeys_the_global_parallel_cap(self):
        ex = SynthExecutor(hold=("synthesis",))
        ctl, first = self.revealed(ex, cap=10)
        second = ctl.create_run("q2", [support.cli("claude"), support.cli("codex")],
                                min_independent=2, quorum_policy=c.INCLUDE_UNVERIFIED)
        self.assertTrue(ctl.wait_idle())
        ctl.max_parallel = 1
        ctl.synthesize_with_model(first, "claude-code")
        try:
            self.assertTrue(support.wait_for(lambda: "synthesis" in ex.started))
            with self.assertRaises(c.ControllerError):
                ctl.synthesize_with_model(second, "claude-code")
            self.assertEqual(ctl.call_budget()["used"], 5)
        finally:
            ex.release("synthesis")
            self.finish(ctl, first)
            self.finish(ctl, second)

    def test_synthesis_obeys_pause_and_unsettled_gates_before_reservation(self):
        ctl, rid = self.revealed(SynthExecutor(), cap=8)
        ctl.paused = True
        with self.assertRaises(c.ControllerError):
            ctl.synthesize_with_model(rid, "claude-code")
        ctl.paused = False
        with patch.object(ctl, "unsettled", return_value=ctl.unsettled_limit):
            with self.assertRaises(c.ControllerError):
                ctl.synthesize_with_model(rid, "claude-code")
        self.assertEqual(ctl.call_budget()["used"], 2)

    def test_unconfirmed_synthesis_keeps_its_slot_and_blocks_a_new_draft(self):
        ex = Unconfirmed()
        ctl, rid = self.revealed(ex, cap=8)
        ctl.unsettled_limit = 1
        ctl.synthesize_with_model(rid, "claude-code")
        self.finish(ctl, rid)
        self.assertEqual(self.run_view(ctl, rid)["model_synthesis"]["status"], "unknown")
        self.assertEqual((ctl.view()["slots"]["used"], ctl.unsettled()), (1, 1))
        pending = ctl.create_run("q2", [support.cli("claude")], min_independent=1,
                                 quorum_policy=c.INCLUDE_UNVERIFIED)
        self.assertEqual(self.part(ctl, pending, "claude")["state"], c.QUEUED)
        self.assertEqual(ctl.call_budget()["used"], 3)

    def test_a_crashed_synthesis_is_occupied_after_restart_without_refund(self):
        ex = SynthExecutor()
        ctl, rid = self.revealed(ex, cap=8)
        with self.store.tx() as tx:
            tx.event(rid, "live_call_reserved", pid="synthesis", attempt="lost",
                     adapter_id="claude-code", cap=8, purpose="synthesis")
            tx.event(rid, "synthesis_started", attempt="lost", adapter_id="claude-code",
                     execution="real", labels={})
        restarted = self.controller(ex, max_real_calls=8)
        self.assertEqual(restarted.call_budget()["used"], 3)
        self.assertEqual((restarted.view()["slots"]["used"], restarted.unsettled()), (1, 1))
        with self.assertRaises(c.ControllerError):
            restarted.synthesize_with_model(rid, "claude-code")
        self.assertEqual(ex.started.count("synthesis"), 0)

    def test_a_legacy_failure_without_raw_or_label_order_still_reads(self):
        ex = SynthExecutor()
        ctl, rid = self.revealed(ex, cap=8)
        with self.store.tx() as tx:   # 카드 #66 전의 사건 모양: 원문 칸·label_order 없음, 참여자 ID 순 이름표
            tx.event(rid, "synthesis_started", attempt="old", adapter_id="claude-code", execution="real",
                     labels={"D1": "claude", "D2": "codex"})
            tx.event(rid, "synthesis_failed", attempt="old", result={
                "schema": "a1-model-synthesis/1", "status": "unavailable", "mode": "model",
                "additional_model_calls": 1, "source_run_id": rid,
                "synthesizer": {"adapter_id": "claude-code", "started": True, "tree_confirmed_empty": True},
                "disposition": "report_without_synthesis", "reason": "the synthesizer did not return one JSON object",
                "message": "실제 합성을 완료하지 못했습니다."})
        state = self.run_view(ctl, rid)["model_synthesis"]
        self.assertEqual((state["status"], state["reason"]), ("failed", "the synthesizer did not return one JSON object"))
        self.assertNotIn("raw", state)
        self.assertEqual([a["attempt"] for a in self.run_view(ctl, rid)["model_syntheses"]], ["old"])
        ctl.synthesize_with_model(rid, "claude-code")   # 끝난 옛 시도는 새 호출을 막지 않는다
        self.finish(ctl, rid)
        self.assertEqual(ex.started.count("synthesis"), 1)

    def test_wait_idle_includes_synthesis_workers(self):
        ex = SynthExecutor(hold=("synthesis",))
        ctl, rid = self.revealed(ex)
        ctl.synthesize_with_model(rid, "claude-code")
        try:
            self.assertFalse(ctl.wait_idle(timeout=.1))
        finally:
            ex.release("synthesis")
            self.finish(ctl, rid)
        self.assertTrue(ctl.wait_idle())

    def test_acknowledgement_is_attempt_bound_persistent_and_never_refunds(self):
        ex = Unconfirmed()
        ctl, rid = self.revealed(ex, cap=8)
        ctl.synthesize_with_model(rid, "claude-code")
        self.finish(ctl, rid)
        attempt = self.run_view(ctl, rid)["model_synthesis"]["attempts"][0]
        with self.assertRaisesRegex(c.ControllerError, "unconfirmed"):   # 끝났는지 모르는 합성이 새 호출을 막는다
            ctl.synthesize_with_model(rid, "claude-code")
        with self.assertRaises(c.ControllerError):
            ctl.acknowledge_synthesis_unknown(rid, "wrong-attempt")
        self.assertEqual(ctl.unsettled(), 1)
        ctl.acknowledge_synthesis_unknown(rid, attempt)
        self.assertEqual((ctl.view()["slots"]["used"], ctl.unsettled()), (0, 0))
        with self.assertRaises(c.ControllerError):
            ctl.acknowledge_synthesis_unknown(rid, attempt)
        restarted = self.controller(ex, max_real_calls=8)
        self.assertEqual(self.run_view(restarted, rid)["model_synthesis"]["status"], "acknowledged")
        self.assertEqual((restarted.view()["slots"]["used"], restarted.call_budget()["used"]), (0, 3))
        restarted.synthesize_with_model(rid, "claude-code")   # 확인한 뒤에는 새 호출 하나를 예약해 다시 부를 수 있다
        self.finish(restarted, rid)
        self.assertEqual(restarted.call_budget()["used"], 4)

    def test_running_synthesis_cannot_be_acknowledged(self):
        ex = SynthExecutor(hold=("synthesis",))
        ctl, rid = self.revealed(ex)
        ctl.synthesize_with_model(rid, "claude-code")
        attempt = next(e["attempt"] for e in events(self.store, rid)
                       if e["kind"] == "synthesis_started")
        with self.assertRaises(c.ControllerError):
            ctl.acknowledge_synthesis_unknown(rid, attempt)
        self.assertEqual(ctl.view()["slots"]["used"], 1)

    def test_executor_exception_is_unknown_not_a_released_failed_slot(self):
        class Broken(SynthExecutor):
            def execute(self, spec, *args, **kwargs):
                if spec.pid == "synthesis":
                    raise RuntimeError("synthetic executor failed")
                return super().execute(spec, *args, **kwargs)
        ctl, rid = self.revealed(Broken(), cap=8)
        ctl.synthesize_with_model(rid, "claude-code")
        self.finish(ctl, rid)
        self.assertEqual((ctl.view()["slots"]["used"], ctl.unsettled()), (1, 1))
        self.assertEqual(self.run_view(ctl, rid)["model_synthesis"]["status"], "unknown")

    def test_thread_start_failure_releases_slot_not_the_reservation_or_one_attempt(self):
        ex = SynthExecutor()
        ctl, rid = self.revealed(ex, cap=8)
        with patch.object(threading.Thread, "start", side_effect=RuntimeError("thread refused")):
            ctl.synthesize_with_model(rid, "claude-code")
        self.assertEqual((ctl.view()["slots"]["used"], ctl.unsettled()), (0, 0))
        self.assertEqual(ctl.call_budget()["used"], 3)
        self.assertEqual(self.run_view(ctl, rid)["model_synthesis"]["status"], "failed")
        self.assertNotIn("synthesis", ex.started)
        ctl.synthesize_with_model(rid, "claude-code")   # 시작하지 못한 시도는 끝난 시도다 — 다시 부르면 새 예약
        self.finish(ctl, rid)
        self.assertEqual((ctl.call_budget()["used"], ex.started.count("synthesis")), (4, 1))

    def test_legacy_repeated_attempts_cannot_be_hidden_by_a_later_result(self):
        ctl, rid = self.revealed(SynthExecutor(), cap=8)
        other = ctl.create_run("other", [support.cli("claude")], min_independent=1,
                               quorum_policy=c.INCLUDE_UNVERIFIED)
        self.assertTrue(ctl.wait_idle())
        with self.store.tx() as tx:
            for attempt in ("lost1", "lost2", "done"):
                tx.event(rid, "synthesis_started", attempt=attempt)
            tx.event(rid, "synthesis_completed", attempt="done", result={
                "status": "completed", "synthesizer": {"tree_confirmed_empty": True}})
            tx.event(rid, "synthesis_completed", result={"mode": "mock_extractive"})
            tx.event(other, "synthesis_failed", attempt="lost1", result={
                "synthesizer": {"tree_confirmed_empty": True}})
        self.assertEqual((ctl.view()["slots"]["used"], ctl.unsettled()), (2, 2))
        self.assertEqual(self.run_view(ctl, rid)["model_synthesis"]["attempts"], ["lost1", "lost2"])
        ctl.acknowledge_synthesis_unknown(rid, "lost1")
        self.assertEqual(ctl.unsettled(), 1)
        ctl.acknowledge_synthesis_unknown(rid, "lost2")
        self.assertEqual(ctl.unsettled(), 0)
        self.assertEqual([a["attempt"] for a in self.run_view(ctl, rid)["model_syntheses"]], ["lost1", "lost2", "done"])
        ctl.synthesize_with_model(rid, "claude-code")   # 옛 시도는 모두 보존되고, 모두 끝났으니 새 호출이 된다
        self.finish(ctl, rid)
        self.assertEqual(len(self.run_view(ctl, rid)["model_syntheses"]), 4)

    def test_competing_requests_reserve_only_one_attempt(self):
        ex = SynthExecutor(hold=("synthesis",))
        ctl, rid = self.revealed(ex, cap=8)
        barrier = threading.Barrier(3)
        results = []
        def request():
            barrier.wait(timeout=3)
            try:
                ctl.synthesize_with_model(rid, "claude-code")
                results.append("started")
            except c.ControllerError:
                results.append("refused")
        threads = [threading.Thread(target=request) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=3)
        for thread in threads:
            thread.join(3)
            self.assertFalse(thread.is_alive())
        self.assertCountEqual(results, ["started", "refused"])
        self.assertEqual(ctl.call_budget()["used"], 3)

    def test_running_draft_uses_the_same_parallel_limit_as_synthesis(self):
        ex = SynthExecutor()
        ctl, rid = self.revealed(ex, cap=8)
        ex.gates["claude"] = threading.Event()
        ctl.max_parallel = 1
        ctl.create_run("later", [support.cli("claude")], min_independent=1,
                       quorum_policy=c.INCLUDE_UNVERIFIED)
        with self.assertRaises(c.ControllerError):
            ctl.synthesize_with_model(rid, "claude-code")
        self.assertEqual(ctl.call_budget()["used"], 3)
