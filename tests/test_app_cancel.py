"""K19: 지속 취소와 자원 정리. 합성 실행기만 쓰며 실제 모델은 부르지 않는다."""
import json
import sqlite3
import threading
from unittest.mock import patch

from app import controller as c, store as s
from app.report import build_report, ReportError
import test_app_controller as support
import test_app_integrity as http_support


class CancellationTests(support.Base):
    def held(self, *, kind="ok", max_parallel=1):
        ex = support.SyntheticExecutor({"a": kind}, hold=("a",))
        ctl = self.controller(ex, max_parallel=max_parallel)
        # 실패한 단언 뒤에도 가짜 worker가 닫힌 DB를 쓰지 않게 한다.
        self.addCleanup(ctl.wait_idle)
        self.addCleanup(ex.release, "a")
        rid = ctl.create_run("고정 질문", [support.cli("a"), support.cli("b"), support.manual("m")],
                             min_independent=1)
        self.assertTrue(support.wait_for(lambda: ex.started == ["a"]))
        return ctl, ex, rid

    def test_queued_and_manual_cancel_is_durable_idempotent_and_costs_no_attempt(self):
        ex = support.SyntheticExecutor()
        ctl = self.controller(ex, max_parallel=0)
        rid = ctl.create_run("q", [support.cli("a"), support.manual("m")], min_independent=1)
        ctl.cancel_run(rid)
        ctl.cancel_run(rid)
        view = self.run_view(ctl, rid)
        self.assertTrue(view["cancel_requested"])
        self.assertEqual(view["budget"]["used"], 0)
        self.assertTrue(all(p["status"] == "cancelled_before_start" for p in view["participants"]))
        self.assertEqual([e["kind"] for e in s.events(self.store, rid)].count("run_cancel_requested"), 1)
        path = self.store.path
        self.store.close()
        self.store = s.Store(path)
        self.addCleanup(self.store.close)
        restarted = self.controller(ex)
        restarted.resume()
        self.assertEqual(ex.started, [])
        self.assertFalse(restarted.paused)
        self.assertTrue(self.run_view(restarted, rid)["cancel_requested"])
        with self.assertRaises(c.ControllerError):
            restarted.submit_manual(rid, "m", "late", view["input_sha256"])
        with self.assertRaises(c.ControllerError):
            restarted.approve_reduction(rid)
        with self.assertRaises(ReportError):
            build_report(restarted.view(rid), rid)

    def test_cancel_signals_after_commit_and_discards_late_success_without_refund(self):
        ctl, ex, rid = self.held()
        with ctl.lock:
            signal = next(iter(ctl._workers.values()))[1]
        original = signal.set
        def committed_first():
            self.assertEqual(self.store.row("SELECT cancel_requested FROM runs WHERE run_id = ?", rid)[0], 1)
            self.assertFalse(self.store._db.in_transaction)
            original()
        with patch.object(signal, "set", side_effect=committed_first):
            ctl.cancel_run(rid)
        self.assertTrue(signal.is_set())
        self.assertEqual(ctl.view()["slots"]["used"], 1)  # 신호 != 종료
        self.assertEqual(self.run_view(ctl, rid)["budget"]["used"], 1)
        ex.release("a")  # 합성 실행기는 신호를 무시하고 정상 답을 돌려준다.
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.part(ctl, rid, "a")["status"], "cancelled")
        self.assertEqual(ctl.view()["slots"]["used"], 0)
        self.assertEqual(self.run_view(ctl, rid)["budget"]["used"], 1)
        self.assertEqual(self.store.rows("SELECT * FROM drafts WHERE run_id = ?", rid), [])
        self.assertEqual(ex.started, ["a"])
        self.assertEqual(ctl._workers, {})

    def test_failed_cancel_transaction_does_not_signal_or_partially_cancel(self):
        ctl, ex, rid = self.held()
        signal = next(iter(ctl._workers.values()))[1]
        self.store._db.execute("CREATE TRIGGER fail_cancel BEFORE INSERT ON events "
                               "WHEN NEW.kind = 'run_cancel_requested' BEGIN SELECT RAISE(ABORT, 'test'); END")
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                ctl.cancel_run(rid)
            self.assertFalse(signal.is_set())
            self.assertFalse(self.run_view(ctl, rid)["cancel_requested"])
            self.assertEqual(self.part(ctl, rid, "b")["state"], c.QUEUED)
        finally:
            self.store._db.execute("DROP TRIGGER fail_cancel")
            ctl.cancel_run(rid)

    def test_unconfirmed_tree_keeps_slot_budget_and_seal_after_acknowledgement(self):
        ctl, ex, rid = self.held(kind="unknown")
        ctl.cancel_run(rid)
        ex.release("a")
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.part(ctl, rid, "a")["status"], "cancel_unconfirmed")
        self.assertEqual(ctl.view()["slots"]["used"], 1)
        ctl.acknowledge_unknown(rid, "a")
        self.assertEqual(ctl.view()["slots"]["used"], 0)
        self.assertEqual(self.run_view(ctl, rid)["budget"]["used"], 1)
        self.assertEqual(self.run_view(ctl, rid)["phase"], "drafting")
        self.assertEqual(ex.started, ["a"])

    def test_restart_does_not_accept_an_old_result_or_revive_cancelled_work(self):
        ctl, ex, rid = self.held()
        ctl.cancel_run(rid)
        restarted = self.controller(ex)  # 같은 Store에서 중단 직후의 복구 규칙을 결정적으로 시험한다.
        restarted.resume()
        self.assertEqual(self.part(restarted, rid, "a")["state"], c.UNKNOWN)
        ex.release("a")
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.part(restarted, rid, "a")["state"], c.UNKNOWN)
        self.assertEqual(ex.started, ["a"])
        self.assertEqual(self.store.rows("SELECT * FROM drafts WHERE run_id = ?", rid), [])
        self.assertIn("attempt_result_ignored", [e["kind"] for e in s.events(self.store, rid)])

    def test_already_sealed_draft_stays_private_and_public_run_cannot_be_cancelled(self):
        ctl = self.controller(support.SyntheticExecutor())
        rid = ctl.create_run("q", [support.cli("a"), support.manual("m")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(len(self.store.rows("SELECT * FROM drafts WHERE run_id = ?", rid)), 1)
        ctl.cancel_run(rid)
        self.assertNotIn("a의 답", json.dumps(ctl.view(), ensure_ascii=False))
        with self.assertRaises(ReportError):
            build_report(ctl.view(rid), rid)
        public = ctl.create_run("q", [support.cli("b")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        with self.assertRaises(c.ControllerError):
            ctl.cancel_run(public)
        self.assertEqual(self.run_view(ctl, public)["phase"], "revealed")
        self.assertFalse(self.run_view(ctl, public)["cancel_requested"])

    def test_completed_worker_registry_is_released_across_many_runs(self):
        ctl = self.controller(support.SyntheticExecutor())
        for _ in range(30):
            ctl.create_run("q", [support.cli("a"), support.cli("b")], min_independent=2)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(ctl._workers, {})
        self.assertEqual(ctl.view()["slots"]["used"], 0)
        self.assertTrue(all(r["phase"] == "revealed" for r in ctl.view()["runs"]))

    def test_run_ids_remain_distinct_when_generated_uuids_share_a_short_prefix(self):
        ctl = self.controller(support.SyntheticExecutor())
        generated = [c.uuid.UUID("12340000-0000-4000-8000-000000000001"),
                     c.uuid.UUID("12340000-0000-4000-8000-000000000002")]
        with patch.object(c.time, "strftime", return_value="0101-000000"), \
                patch.object(c.uuid, "uuid4", side_effect=generated):
            first, second = [ctl.create_run(question, [support.manual("a")], min_independent=1,
                                           quorum_policy=c.INCLUDE_UNVERIFIED)
                             for question in ("first question", "second question")]
        self.assertNotEqual(first, second)
        digest = self.run_view(ctl, first)["input_sha256"]
        ctl.submit_manual(first, "a", "first answer", digest)
        self.assertEqual(self.part(ctl, first, "a")["draft"], "first answer")
        self.assertEqual(self.part(ctl, second, "a")["state"], c.AWAITING_USER)
        self.assertEqual(self.run_view(ctl, second)["question"], "second question")

    def test_thread_start_failure_releases_reserved_slot_but_keeps_attempt_record(self):
        ex = support.SyntheticExecutor()
        ctl = self.controller(ex)
        with patch.object(threading.Thread, "start", side_effect=RuntimeError("no thread")):
            rid = ctl.create_run("q", [support.cli("a")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(ex.started, [])
        self.assertEqual(ctl.view()["slots"]["used"], 0)
        self.assertEqual(self.run_view(ctl, rid)["budget"]["used"], 1)
        self.assertEqual(self.part(ctl, rid, "a")["status"], "process_failed_to_start")

    def test_schema_two_migrates_without_changing_existing_run(self):
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        rid = ctl.create_run("preserve", [support.cli("a")], min_independent=1)
        self.store._db.execute("ALTER TABLE runs DROP COLUMN cancel_requested")
        self.store._db.execute("PRAGMA user_version = 2")
        path = self.store.path
        self.store.close()
        self.store = s.Store(path)
        self.addCleanup(self.store.close)
        row = self.store.row("SELECT question, cancel_requested FROM runs WHERE run_id = ?", rid)
        self.assertEqual(tuple(row), ("preserve", 0))
        self.assertEqual(self.store.row("PRAGMA user_version")[0], s.SCHEMA_VERSION)


class CancelHttpTests(http_support.HttpServerCase):
    def test_authenticated_cancellation_route_and_no_side_effect_for_wrong_token(self):
        rid = self.ctl.create_run("q", [support.cli("a")], min_independent=1)
        route = f"/api/runs/{rid}/cancel"
        self.assertEqual(self.request({}, {"Authorization": "Bearer wrong"}, path=route)[0], 401)
        self.assertFalse(self.ctl.view(rid)["runs"][0]["cancel_requested"])
        self.assertEqual(self.request({}, path=route)[0], 200)
        self.assertEqual(self.request({}, path=route)[0], 200)
        self.assertEqual([e["kind"] for e in s.events(self.store, rid)].count("run_cancel_requested"), 1)
