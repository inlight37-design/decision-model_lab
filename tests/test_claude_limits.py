"""Claude 계정 한도: stream의 rate_limit_event 허용 칸, 화면 투영, 봉인·실제 실행 규칙. 모델 호출 없음."""
import json
import unittest

from app import controller as c
from core import adapters, contract, runner
from core.quota import claude_limit, claude_limit_projection
import test_app_controller as support
from test_core_adapters import fake
from test_live_cli import UnverifiedSynthetic

# 2026-09-23 관측(2.1.280)의 모양에 결제·식별 칸을 섞었다. 문서의 SDKRateLimitEvent는 status·resetsAt·utilization만 적는다.
OBSERVED = {"status": "allowed", "resetsAt": 1790000000, "rateLimitType": "five_hour",
            "unifiedWindows": {"five_hour": {"utilization": 0.33, "resetsAt": 1790000000},
                               "seven_day": {"utilization": 0.08, "resetsAt": 1790500000}},
            "overageStatus": "PRIVATE", "isUsingOverage": False, "overageResetsAt": 1,
            "errorCode": "credits_required", "canUserPurchaseCredits": True, "hasChargeableSavedPaymentMethod": True}


def stream(*infos, text="답"):
    events = [{"type": "system", "subtype": "init", "tools": [], "permissionMode": "dontAsk", "mcp_servers": []}]
    events += [{"type": "rate_limit_event", "rate_limit_info": info, "uuid": "PRIVATE", "session_id": "PRIVATE"}
               for info in infos]
    events.append({"type": "result", "is_error": False, "result": text, "modelUsage": {"m": {}},
                   "usage": {"input_tokens": 1, "output_tokens": 2}})
    return "\n".join(json.dumps(e) for e in events)


def outcome(stdout):
    return adapters.interpret("claude-code", fake(stdout), requested_model="m", claude_tools=())


class ExtractTests(unittest.TestCase):
    def test_observed_windows_are_kept_and_billing_or_identity_fields_are_dropped(self):
        result = outcome(stream(OBSERVED))
        self.assertTrue(result.ok)
        self.assertEqual(result.rate_limit, {
            "provider": "claude", "status": "allowed", "events": 1,
            "windows": [{"window": "five_hour", "utilization": 0.33, "resets_at": 1790000000},
                        {"window": "seven_day", "utilization": 0.08, "resets_at": 1790500000}]})
        self.assertNotIn("PRIVATE", json.dumps(result.rate_limit))
        self.assertNotIn("credit", json.dumps(result.rate_limit).lower())

    def test_documented_shape_without_windows_becomes_one_current_window(self):
        info = {"status": "allowed_warning", "utilization": 0.9, "resetsAt": 1790000000}
        self.assertEqual(outcome(stream(info)).rate_limit["windows"],
                         [{"window": "current", "utilization": 0.9, "resets_at": 1790000000}])

    def test_malformed_or_missing_limits_are_unknown_but_never_reject_the_answer(self):
        for bad in ({"status": "maybe"}, {"utilization": 1.5}, {"utilization": -0.1}, {"utilization": "0.3"},
                    {"utilization": True}, {"utilization": float("nan")}, {"resetsAt": -1}, {"resetsAt": 1.5},
                    {"unifiedWindows": []}, {"unifiedWindows": {"Five Hour": {"utilization": 0.1}}},
                    {"unifiedWindows": {"five_hour": 0.1}}, {}, "allowed", None):
            with self.subTest(info=bad):
                result = outcome(stream(bad))
                self.assertTrue(result.ok)
                self.assertIsNone(result.rate_limit)
        self.assertIsNone(outcome(stream()).rate_limit)

    def test_the_last_event_decides_and_an_earlier_one_never_replaces_it(self):
        first, second = {"status": "allowed", "utilization": 0.1}, {"status": "allowed", "utilization": 0.2}
        latest = outcome(stream(first, second)).rate_limit
        self.assertEqual((latest["windows"][0]["utilization"], latest["events"]), (0.2, 2))
        self.assertIsNone(outcome(stream(first, {"utilization": 7})).rate_limit)


class ProjectionTests(unittest.TestCase):
    def test_ratio_is_shown_as_percent_and_ages_to_stale(self):
        limit = {**claude_limit(OBSERVED), "observed_at": 1000}
        fresh = claude_limit_projection(limit, now=1060)
        self.assertEqual([row["used_percent"] for row in fresh["limits"]], [33.0, 8.0])
        self.assertEqual((fresh["freshness"], fresh["status"], fresh["limit_state"]), ("fresh", "observed", "allowed"))
        self.assertEqual(claude_limit_projection(limit, now=1121)["status"], "stale")
        self.assertEqual(claude_limit_projection(limit, now=999)["freshness"], "stale")   # 시계가 거꾸로 갔다
        reset = {**limit, "windows": [{"window": "five_hour", "utilization": 0.5, "resets_at": 1030}]}
        self.assertEqual(claude_limit_projection(reset, now=1060)["limits"][0]["status"], "stale")
        self.assertEqual(claude_limit_projection(None, now=1060)["status"], "unknown")


class LimitExecutor(UnverifiedSynthetic):
    """실제처럼 분류되는 합성 실행기. 프로세스·모델 없이 rate_limit_event가 든 Claude stream을 돌려준다."""

    def execute(self, spec, prompt, work_dir, timeout, *, cancel=None):
        self.started.append(spec.pid)
        if spec.pid in self.gates:
            self.gates[spec.pid].wait(10)
        result = runner.RunResult(("synthetic",), runner.EXITED, 0, stream(OBSERVED, text=f"{spec.pid}의 답"), "",
                                  False, False, 5, 0, True, containment=runner.JOB_OBJECT,
                                  input_delivery=runner.INPUT_COMPLETE)
        return result, adapters.interpret("claude-code", result, requested_model="m")


class SyntheticLimitExecutor(support.SyntheticExecutor):
    execute = LimitExecutor.execute


class ControllerTests(support.Base):
    def test_only_settled_real_attempts_reach_the_account_panel(self):
        ex = LimitExecutor(hold=("a",))
        ctl = self.controller(ex, max_real_calls=2)
        rid = ctl.create_run("q", [support.cli("a"), support.cli("b")], min_independent=1,
                             quorum_policy=c.INCLUDE_UNVERIFIED)
        self.assertTrue(support.wait_for(lambda: self.part(ctl, rid, "b")["state"] == c.ACCEPTED))
        self.assertIsNone(ctl.claude_account_limit())   # a가 아직 초안을 쓴다 — 실행이 봉인 중이다
        self.assertNotIn("rate_limit", self.part(ctl, rid, "b")["result"])
        ex.release("a")
        self.assertTrue(ctl.wait_idle())
        limit = ctl.claude_account_limit()
        self.assertEqual(limit["windows"][0], {"window": "five_hour", "utilization": 0.33, "resets_at": 1790000000})
        self.assertIsInstance(limit["observed_at"], int)
        self.assertEqual(self.part(ctl, rid, "a")["result"]["rate_limit"]["status"], "allowed")

    def test_mock_or_synthetic_attempts_never_become_account_values(self):
        ctl = self.controller(SyntheticLimitExecutor())
        ctl.create_run("q", [support.cli("a")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        self.assertIsNone(ctl.claude_account_limit())
        self.assertEqual(contract.SYNTHETIC, SyntheticLimitExecutor.kind)


if __name__ == "__main__":
    unittest.main()
