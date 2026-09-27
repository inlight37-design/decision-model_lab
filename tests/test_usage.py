"""카드 #141: 실행·작업 단위 토큰 합계. 합성 실행기와 합성 원장만 — 모델을 부르지 않는다.

완료 조건을 고정한다: provider별로 나누고 캐시로 읽은 몫을 따로 보임, 값이 없는 호출은 0이 아니라 "관측 안 됨",
정가 추정은 청구액과 따로, 봉인 중 투영에는 사용량이 없음, 작업 합계는 봉인 중인 실행을 따로 셈, 결정 보고서에 실음.
"""
import json
import unittest

from app import controller as c, server, usage
from app.report import build_report, decision_report
import test_app_controller as support

ROSTER = server.PARTICIPANTS


def board(*isolated, general=()):
    return {"supervisor": [], "orchestrator": [], "isolated": list(isolated), "general": list(general),
            "input_mode": "original"}


class TotalTests(unittest.TestCase):
    def test_providers_are_never_added_together_and_cache_and_estimate_stay_apart(self):
        result = usage.total([
            {"provider": "claude-code", "usage": {"input_tokens": 100, "output_tokens": 20,
                                                  "cache_read_input_tokens": 80, "client_estimate_usd": 0.0125}},
            {"provider": "claude-code", "usage": {"input_tokens": 50, "cache_creation_input_tokens": 7,
                                                  "client_estimate_usd": 0.0025}},
            {"provider": "codex", "usage": {"input_tokens": 300, "cached_input_tokens": 200, "output_tokens": 9,
                                            "reasoning_output_tokens": 4}},
            {"provider": "codex", "usage": {}},                 # 보고 없음
            {"provider": "codex", "usage": None},
            {"provider": "antigravity", "usage": {"client_estimate_usd": 0.5}},   # 정가 추정만 — 토큰 관측이 아니다
            {"provider": None, "usage": None}])                 # 원본 앱
        claude, codex = result["by_provider"]["claude-code"], result["by_provider"]["codex"]
        self.assertEqual(claude["tokens"], {"input_tokens": 150, "output_tokens": 20, "cache_creation_input_tokens": 7,
                                            "cache_read_input_tokens": 80})
        self.assertEqual((claude["cache_read_field"], claude["list_price_estimate_usd"]), ("cache_read_input_tokens", 0.015))
        self.assertEqual(codex["tokens"], {"input_tokens": 300, "cached_input_tokens": 200, "output_tokens": 9,
                                           "reasoning_output_tokens": 4})
        self.assertEqual((codex["calls"], codex["observed"], codex["unobserved"]), (3, 1, 2))
        self.assertIsNone(codex["list_price_estimate_usd"])                     # 추정이 없으면 0이 아니라 없음
        agy = result["by_provider"]["antigravity"]
        self.assertEqual((agy["observed"], agy["unobserved"], agy["tokens"], agy["list_price_estimate_usd"]),
                         (0, 1, {}, 0.5))                                         # 보고 안 된 필드를 0으로 채우지 않는다
        self.assertEqual(result["unobserved"], {"manual": 1, "no_usage_reported": 3})
        self.assertNotIn("tokens", result)                                     # provider를 넘는 합계가 없다
        self.assertTrue(any("청구액이 아니다" in note for note in result["notes"]))

    def test_calls_cover_every_model_call_bound_to_the_run_and_skip_unstarted_or_running_ones(self):
        seen = {"input_tokens": 1}
        run = {"participants": [
                   {"transport": "cli", "adapter_id": "claude-code", "state": "accepted", "status": "ok",
                    "result": {"usage": seen}},
                   {"transport": "cli", "adapter_id": "codex", "state": "rejected", "status": "cli_error",
                    "result": {"usage": {}}},
                   {"transport": "cli", "adapter_id": "codex", "state": "rejected", "status": "process_failed_to_start"},
                   {"transport": "cli", "adapter_id": "codex", "state": "running", "status": None},
                   {"transport": "manual", "state": "accepted"}],
               "model_syntheses": [{"result": {"synthesizer": {"adapter_id": "codex", "started": True, "usage": seen}}},
                                   {"result": {"synthesizer": {"adapter_id": "codex", "started": False}}}],
               "refinement": {"supervisor": {"adapter_id": "claude-code"},
                              "turns": [{"execution": "real", "state": "accepted", "observation": {"usage": seen}}]},
               "split": {"orchestrator": {"adapter_id": "claude-code"}, "execution": "real", "state": "accepted",
                         "observation": {"usage": seen}},
               "proposals": [{"supervisor": {"adapter_id": "claude-code"}, "execution": "real", "state": "running"},
                             {"supervisor": {"adapter_id": "claude-code"}, "execution": "real", "state": "rejected",
                              "status": "process_failed_to_start", "observation": {"state": "failed_to_start"}}],
               "collations": [{"orchestrator": {"adapter_id": "claude-code"}, "execution": "real", "state": "unknown",
                               "observation": None}],
               "cross_review": {"reviews": [
                   {"reviewer": {"adapter_id": "codex"}, "execution": "real", "state": "accepted",
                    "observation": {"usage": seen}},
                   {"reviewer": {"adapter_id": "claude-code"}, "execution": None, "state": "skipped"}]}}
        roles = [call["role"] for call in usage.calls(run)]
        self.assertEqual(roles, ["participant", "participant", "manual", "synthesis", "refine", "split", "collate",
                                 "cross_review"])
        totals = usage.for_run(run)
        self.assertEqual(totals["by_provider"]["codex"]["unobserved"], 1)       # 실패했지만 보고가 없는 시도
        self.assertEqual(totals["by_provider"]["claude-code"]["unobserved"], 1)  # 끝났는지 모르는 모으기

    def test_a_task_total_combines_runs_and_counts_sealed_runs_apart(self):
        one = usage.total([{"provider": "codex", "usage": {"input_tokens": 5}}])
        two = usage.total([{"provider": "codex", "usage": {"input_tokens": 7, "cached_input_tokens": 3}},
                           {"provider": None, "usage": None}])
        merged = usage.combine([one, None, two], sealed=1)
        self.assertEqual(merged["by_provider"]["codex"]["tokens"]["input_tokens"], 12)
        self.assertEqual(merged["by_provider"]["codex"]["tokens"]["cached_input_tokens"], 3)
        self.assertEqual((merged["by_provider"]["codex"]["calls"], merged["unobserved"]["manual"], merged["sealed_runs"]),
                         (2, 1, 1))


class ControllerTests(support.Base):
    def test_a_sealed_run_carries_no_usage_and_a_revealed_one_does(self):
        ex = support.SyntheticExecutor(hold=("codex",))
        ctl = self.controller(ex)
        rid = ctl.create_run("q", [ROSTER["claude"], ROSTER["codex"]], min_independent=2,
                             role_board=board("claude", "codex"), roster=ROSTER, task_title="합계 작업")
        self.assertTrue(support.wait_for(lambda: self.run_view(ctl, rid)["participants"][0]["state"] == c.ACCEPTED))
        view = ctl.view()
        self.assertIsNone(self.run_view(ctl, rid)["usage"])
        self.assertNotIn("input_tokens", json.dumps(view))                    # 봉인 중에는 어디에도 없다
        self.assertEqual(view["tasks"][0]["usage"]["sealed_runs"], 1)
        ex.release("codex")
        self.assertTrue(ctl.wait_idle())
        run = self.run_view(ctl, rid)
        self.assertEqual({p: e["tokens"]["input_tokens"] for p, e in run["usage"]["by_provider"].items()},
                         {"claude-code": 10, "codex": 10})
        task = ctl.view()["tasks"][0]["usage"]
        self.assertEqual((task["sealed_runs"], task["by_provider"]["codex"]["calls"]), (0, 1))

    def test_a_general_run_shows_usage_as_results_arrive(self):
        ex = support.SyntheticExecutor(hold=("codex",))
        ctl = self.controller(ex)
        rid = ctl.create_run("목표", [ROSTER["claude"], ROSTER["codex"]], min_independent=1,
                             role_board=board(general=("claude", "codex")), roster=ROSTER,
                             assignments={"claude": {"task": "a", "sources": []}, "codex": {"task": "b", "sources": []}})
        self.assertTrue(support.wait_for(lambda: (self.run_view(ctl, rid)["usage"] or {}).get("by_provider")))
        self.assertEqual(list(self.run_view(ctl, rid)["usage"]["by_provider"]), ["claude-code"])
        ex.release("codex")
        self.assertTrue(ctl.wait_idle())

    def test_the_decision_report_carries_the_run_total(self):
        ctl = self.controller(support.SyntheticExecutor())
        rid = ctl.create_run("q", [support.cli("a"), support.cli("b")], min_independent=2)
        self.assertTrue(ctl.wait_idle())
        ctl.synthesize(rid)   # 모의 합성: 결정 보고가 생긴다
        run = self.run_view(ctl, rid)
        body = decision_report(run, build_report(ctl.view(rid), rid))
        self.assertEqual(body["schema"], "a1-decision-report/5")
        self.assertEqual(body["usage"], run["usage"])
        self.assertEqual(body["usage"]["by_provider"]["claude-code"]["observed"], 2)
