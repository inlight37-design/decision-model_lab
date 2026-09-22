"""오프라인 경계 테스트. 실제 모델·OS 권한·서버 인증을 검사하지 않는다."""
import json
import unittest
from tools.review_boundary import Attempt, Event, BoundaryError, advance, budget_projection, sealed_projection, quota_projection


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.a = Attempt("attempt-1", "worker-1")
    def event(self, seq, kind, code=None):
        return Event("attempt-1", "worker-1", seq, kind, code)
    def test_start(self):
        self.assertEqual(advance(self.a, self.event(1, "started")).state, "running")
    def test_cancel_is_not_exit(self):
        a = advance(self.a, self.event(1, "cancel_requested"))
        self.assertEqual(a.state, "cancel_requested")
        self.assertIsNone(a.exit_code)
    def test_disconnect_is_unknown(self):
        self.assertEqual(advance(self.a, self.event(1, "connection_lost")).state, "unknown")
    def test_cancel_during_disconnect_stays_unknown(self):
        a = advance(self.a, self.event(1, "connection_lost"))
        a = advance(a, self.event(2, "cancel_requested"))
        self.assertEqual(a.state, "unknown")
        self.assertTrue(a.cancellation_requested)
    def test_reconcile_preserves_cancel(self):
        a = advance(self.a, self.event(1, "cancel_requested"))
        a = advance(a, self.event(2, "connection_lost"))
        self.assertEqual(advance(a, self.event(3, "reconciled_running")).state, "cancel_requested")
    def test_exit_zero_is_not_success(self):
        a = advance(self.a, self.event(1, "process_exited", 0))
        self.assertEqual(a.state, "exited")
        self.assertEqual(a.exit_code, 0)
    def test_identical_event_replay(self):
        e = self.event(1, "started")
        a = advance(self.a, e)
        self.assertIs(advance(a, e), a)
    def test_conflicting_replay_rejected(self):
        a = advance(self.a, self.event(1, "started"))
        with self.assertRaises(BoundaryError): advance(a, self.event(1, "connection_lost"))
    def test_gap_rejected(self):
        with self.assertRaises(BoundaryError): advance(self.a, self.event(2, "started"))
    def test_old_epoch_rejected(self):
        with self.assertRaises(BoundaryError): advance(self.a, Event("attempt-1", "old", 1, "started"))
    def test_old_attempt_rejected(self):
        with self.assertRaises(BoundaryError): advance(self.a, Event("other", "worker-1", 1, "started"))
    def test_terminal_immutable(self):
        a = advance(self.a, self.event(1, "process_exited", 1))
        with self.assertRaises(BoundaryError): advance(a, self.event(2, "started"))
    def test_no_implicit_retry(self):
        a = advance(self.a, self.event(1, "connection_lost"))
        with self.assertRaises(BoundaryError): advance(a, self.event(2, "started"))
    def test_exit_requires_integer(self):
        for code in (None, True, "0"):
            with self.subTest(code=code), self.assertRaises(BoundaryError):
                advance(self.a, self.event(1, "process_exited", code))
    def test_budget_keeps_unknown_and_failed_exit(self):
        unknown = advance(self.a, self.event(1, "connection_lost"))
        failed = advance(Attempt("attempt-2", "worker-1"), Event("attempt-2", "worker-1", 1, "process_exited", 1))
        self.assertEqual(budget_projection([unknown, failed], 3)["remaining"], 1)
    def test_budget_duplicate_rejected(self):
        with self.assertRaises(BoundaryError): budget_projection([self.a, self.a], 3)
    def test_budget_overflow_rejected(self):
        with self.assertRaises(BoundaryError): budget_projection([self.a, Attempt("b", "w")], 1)


class BlindTests(unittest.TestCase):
    def setUp(self):
        self.people = [{"id": "A", "submission": "submitted", "draft": "SECRET", "tokens": 4321,
                        "log_ref": "SECRET-PATH", "future_field": {"raw": "SECRET"}},
                       {"id": "B", "submission": "pending", "draft": "OTHER"}]
    def test_allowlist_no_content_or_length(self):
        v = sealed_projection(self.people, audience="operator")
        self.assertEqual(v["participants"], [{"id":"A", "submission":"submitted"}, {"id":"B", "submission":"pending"}])
        self.assertNotIn("SECRET", json.dumps(v))
        self.assertNotIn("4321", json.dumps(v))
    def test_peer_cannot_see_other_status(self):
        v = sealed_projection(self.people, audience="participant", own_id="A")
        self.assertEqual(len(v["participants"]), 1)
        self.assertEqual(v["participants"][0]["id"], "A")
    def test_unknown_audience_rejected(self):
        with self.assertRaises(BoundaryError): sealed_projection(self.people, audience="anonymous")
    def test_missing_identity_rejected(self):
        with self.assertRaises(BoundaryError): sealed_projection(self.people, audience="participant")
    def test_duplicate_rejected(self):
        with self.assertRaises(BoundaryError): sealed_projection([self.people[0]]*2, audience="operator")


class QuotaTests(unittest.TestCase):
    def project(self, payload, **kw):
        return quota_projection(payload, observed_at=100, now=kw.get("now", 110))
    def test_unknown_is_not_zero(self):
        self.assertEqual(self.project(None)["status"], "unknown")
        self.assertEqual(self.project(None)["limits"], [])
    def test_observed_zero_kept(self):
        v = self.project({"rateLimits":{"primary":{"usedPercent":0}}})
        self.assertEqual(v["limits"][0]["used_percent"], 0)
        self.assertEqual(v["limits"][1]["status"], "unknown")
    def test_multiple_buckets_not_summed_with_legacy(self):
        v = self.project({"rateLimits":{"primary":{"usedPercent":99}}, "rateLimitsByLimitId":{
            "codex":{"primary":{"usedPercent":25}}, "spark":{"primary":{"usedPercent":50}}}})
        self.assertEqual([x["used_percent"] for x in v["limits"]], [25,None,50,None])
    def test_empty_map_falls_back(self):
        v = self.project({"rateLimitsByLimitId":{}, "rateLimits":{"primary":{"usedPercent":25}}})
        self.assertEqual(v["limits"][0]["used_percent"], 25)
    def test_old_observation_stale(self):
        self.assertEqual(self.project({"rateLimits":{"primary":{"usedPercent":20}}}, now=250)["status"], "stale")
    def test_reset_elapsed_not_zeroed(self):
        v = self.project({"rateLimits":{"primary":{"usedPercent":80,"resetsAt":105}}})
        self.assertEqual(v["limits"][0]["status"], "stale")
        self.assertEqual(v["limits"][0]["used_percent"], 80)
    def test_invalid_percent_rejected(self):
        for n in (True, float("nan"), float("inf"), -1, 101, "20"):
            with self.subTest(n=n), self.assertRaises(BoundaryError):
                self.project({"rateLimits":{"primary":{"usedPercent":n}}})
    def test_future_observation_rejected(self):
        with self.assertRaises(BoundaryError): quota_projection(None, observed_at=200, now=100)
    def test_no_hardcoded_window(self):
        v = self.project({"rateLimits":{"primary":{"usedPercent":20,"windowDurationMins":300}}})
        self.assertEqual(v["limits"][0]["window_minutes"], 300)


if __name__ == "__main__":
    unittest.main()
