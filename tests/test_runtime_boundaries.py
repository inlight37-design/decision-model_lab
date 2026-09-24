"""추가 경계 회귀: 선택적 계정 메타데이터와 고정 자료 경로. 실제 모델 호출 없음."""
import hashlib
import json
import unittest
from pathlib import Path

from app import controller as c
from core import adapters
from core.quota import quota_projection
import test_app_controller as support
from test_claude_limits import outcome, stream
from test_core_adapters import fake
from test_sources import Recording, POLICY


class OptionalMetadataTests(unittest.TestCase):
    def test_huge_claude_utilization_is_unknown_without_losing_a_valid_answer(self):
        for used in (10 ** 400, -(10 ** 400)):
            for info in ({"utilization": used},
                         {"unifiedWindows": {"five_hour": {"utilization": used}}}):
                with self.subTest(positive=used > 0, window="unifiedWindows" in info):
                    result = outcome(stream(info))
                    self.assertTrue(result.ok)
                    self.assertIsNone(result.rate_limit)

    def test_huge_codex_percent_is_a_shape_refusal_not_an_overflow(self):
        for used in (10 ** 400, -(10 ** 400)):
            with self.subTest(positive=used > 0), self.assertRaises(ValueError):
                quota_projection({"rateLimits": {"primary": {"usedPercent": used}}},
                                 observed_at=1000, now=1000)

    def test_usage_numbers_the_screen_cannot_parse_are_dropped_without_losing_the_answer(self):
        # json.dumps의 기본값이 NaN·Infinity 글자를 쓰므로 CLI가 그렇게 보낸 줄과 같다. 브라우저 JSON.parse는 이를
        # 받지 않아 화면 응답 전체가 깨진다. 큰 정수는 표준 JSON이라 남긴다.
        bad = {"output_tokens": float("nan"), "cache_read_input_tokens": float("inf"), "cached_input_tokens": -1,
               "cache_creation_input_tokens": True, "reasoning_output_tokens": -float("inf")}
        claude = json.dumps({"type": "result", "is_error": False, "result": "답", "modelUsage": {"m": {}},
                             "total_cost_usd": float("nan"), "usage": {"input_tokens": 10 ** 400, **bad}})
        codex = "\n".join(json.dumps(event) for event in (
            {"type": "item.completed", "item": {"type": "agent_message", "text": "답"}},
            {"type": "turn.completed", "usage": {"input_tokens": 10 ** 400, **bad}}))
        for adapter_id, stdout in (("claude-code", claude), ("codex", codex)):
            with self.subTest(adapter=adapter_id):
                result = adapters.interpret(adapter_id, fake(stdout), requested_model="m")
                self.assertTrue(result.ok)
                self.assertEqual(result.usage, {"input_tokens": 10 ** 400})
                json.dumps(result.usage, allow_nan=False)


class SourceResumeTests(support.Base):
    def pending(self):
        ex = Recording()
        ctl = self.controller(ex)
        ctl.paused = True
        rid = ctl.create_run("q", [support.cli("a")], min_independent=1,
                             sources=[("policy.md", POLICY)])
        return ctl, ex, rid

    def test_resuming_with_a_different_source_root_refuses_before_planning(self):
        ctl, ex, rid = self.pending()
        original = self.run_view(ctl, rid)["prompt"]
        changed = self.controller(ex, work_root=str(self.tmp / "other-work"))
        changed.resume()
        self.assertTrue(changed.wait_idle())
        self.assertEqual(ex.started, [])
        self.assertEqual(ex.inputs, {})
        self.assertEqual(self.part(changed, rid, "a")["status"], "process_failed_to_start")
        self.assertIn("source", self.part(changed, rid, "a")["detail"])
        self.assertEqual(self.run_view(changed, rid)["prompt"], original)
        self.assertFalse(Path(changed._source_root(rid)).exists())

    def test_same_root_resume_keeps_the_original_prompt_and_sources(self):
        ctl, ex, rid = self.pending()
        before = self.run_view(ctl, rid)
        restarted = self.controller(ex)
        restarted.resume()
        self.assertTrue(restarted.wait_idle())
        after = self.run_view(restarted, rid)
        self.assertEqual(ex.started, ["a"])
        self.assertEqual(ex.inputs["a"], (ctl._source_root(rid),))
        self.assertEqual((before["prompt"], before["input_sha256"]),
                         (after["prompt"], after["input_sha256"]))

    def test_changed_ledger_manifest_is_not_silently_rebound_to_the_old_prompt(self):
        # 사용자/복원 도구가 원장 자료를 바꾼 경우에도 고정 질문의 목록을 기준으로 거절한다.
        # 이 시험은 공격자의 원장 접근이나 시도 도중 TOCTOU 차단을 가정하지 않는다.
        ctl, ex, rid = self.pending()
        changed = b"different policy"
        with self.store.tx() as tx:
            tx.execute("UPDATE sources SET content = ?, bytes = ?, sha256 = ? WHERE run_id = ?",
                       changed, len(changed), hashlib.sha256(changed).hexdigest(), rid)
        ctl.resume()
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(ex.started, [])
        self.assertEqual(ex.inputs, {})
        self.assertEqual(self.part(ctl, rid, "a")["status"], "process_failed_to_start")
        self.assertFalse(Path(ctl._source_root(rid)).exists())


if __name__ == "__main__":
    unittest.main()
