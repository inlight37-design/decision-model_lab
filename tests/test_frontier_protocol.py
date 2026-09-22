"""합성 기록 검사. 실제 provider, 사용량, 인용 의미, sandbox를 검증하지 않는다."""
import unittest

from tools.check_frontier_protocol import ProtocolError, demo, validate


class FrontierProtocolTests(unittest.TestCase):
    def assert_invalid(self, mutate):
        record = demo()
        mutate(record)
        with self.assertRaises(ProtocolError):
            validate(record)

    def test_demo_keeps_unanimous_unverified_claim_unresolved(self):
        record = demo()
        validate(record)
        self.assertEqual(record["report"]["unresolved"], ["c2"])

    def test_cross_check_without_reviews(self):
        record = demo()
        record["mode"] = "cross_check"
        record["limits"] = {"max_calls": 4, "max_review_rounds": 0}
        record["calls"] = [c for c in record["calls"] if c["role"] != "review"]
        validate(record)

    def test_duplicate_participant(self):
        self.assert_invalid(lambda r: r["participants"].append(r["participants"][0]))

    def test_duplicate_provider_alias(self):
        self.assert_invalid(lambda r: r["participants"][1].update(provider="OpenAI"))

    def test_missing_draft(self):
        self.assert_invalid(lambda r: r["drafts"].pop())

    def test_silent_quality_downgrade(self):
        self.assert_invalid(lambda r: r["participants"][1].update(quality="economy"))

    def test_peer_contaminated_blind_pass(self):
        self.assert_invalid(lambda r: r["drafts"][0]["peer_inputs"].append("draft-B"))

    def test_changed_input_snapshot(self):
        self.assert_invalid(lambda r: r["drafts"][0].update(input_digest="sha256:" + "1" * 64))

    def test_self_review(self):
        self.assert_invalid(lambda r: r["calls"][3]["peer_draft_ids"].append("draft-A"))

    def test_dangling_peer_reference(self):
        self.assert_invalid(lambda r: r["calls"][3]["peer_draft_ids"].append("absent"))

    def test_early_review(self):
        self.assert_invalid(lambda r: r["calls"].insert(0, r["calls"].pop(3)))

    def test_call_cap(self):
        self.assert_invalid(lambda r: r["limits"].update(max_calls=6))

    def test_failed_attempt_still_counts(self):
        self.assert_invalid(lambda r: r["calls"].insert(0, {"id": "failed-retry", "role": "draft", "round": 0, "participant": "A", "outcome": "failed"}))

    def test_round_cap(self):
        self.assert_invalid(lambda r: r["calls"][3].update(round=2))

    def test_paid_fallback(self):
        self.assert_invalid(lambda r: r["funding"].update(paid_fallback=True))

    def test_unknown_check_reference(self):
        self.assert_invalid(lambda r: r["claims"][0]["check_refs"].append("missing"))

    def test_wrong_check_target(self):
        self.assert_invalid(lambda r: r["checks"][0].update(target="c2"))

    def test_votes_are_not_verification(self):
        self.assert_invalid(lambda r: r["checks"][0].update(kind="vote"))

    def test_skipped_check_is_not_pass(self):
        self.assert_invalid(lambda r: r["checks"][0].update(status="skipped"))

    def test_missing_check_log(self):
        self.assert_invalid(lambda r: r["checks"][0].update(log_ref=""))

    def test_final_loses_dissent(self):
        self.assert_invalid(lambda r: r["report"]["unresolved"].clear())

    def test_false_ready_label(self):
        self.assert_invalid(lambda r: r["report"].update(status="review_ready"))

    def test_boolean_is_not_integer_budget(self):
        self.assert_invalid(lambda r: r["limits"].update(max_calls=True))

    def test_real_record_rejected(self):
        self.assert_invalid(lambda r: r.update(synthetic=False))

    def test_unfinished_call_rejected(self):
        self.assert_invalid(lambda r: r["calls"][3].update(outcome="unknown"))

    def test_denied_review_not_complete(self):
        self.assert_invalid(lambda r: r["calls"][3].update(outcome="denied"))

    def test_funding_boolean_is_strict(self):
        self.assert_invalid(lambda r: r["funding"].update(paid_fallback=0))

    def test_failed_counterevidence_blocks_supported(self):
        def mutate(record):
            record["checks"].append({"id": "e2", "target": "c1", "kind": "test", "status": "failed", "log_ref": "synthetic://e2"})
            record["claims"][0]["check_refs"].append("e2")
        self.assert_invalid(mutate)

    def test_failed_attempt_with_explicit_extra_budget(self):
        record = demo()
        record["limits"]["max_calls"] = 8
        record["calls"].insert(0, {"id": "failed-retry", "role": "draft", "round": 0, "participant": "A", "outcome": "failed"})
        validate(record)

    def test_malformed_records(self):
        for record in (None, [], {}, {"schema": "wrong"}):
            with self.subTest(record=record), self.assertRaises(ProtocolError):
                validate(record)


if __name__ == "__main__":
    unittest.main()
