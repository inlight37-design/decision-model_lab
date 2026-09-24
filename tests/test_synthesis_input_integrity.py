"""Regression checks for exact quotations and lossless model-output parsing.

These use public, synthetic drafts and never launch a CLI or spend model calls.
"""
from __future__ import annotations

import hashlib
import json
import unittest

from app.report import SCHEMA as DRAFT_SCHEMA
from app.synthesis import SynthesisError, check_model_synthesis


class SynthesisInputIntegrityTests(unittest.TestCase):
    def setUp(self):
        draft = "alpha\n beta \n최종 판단 🚀"
        self.report = {
            "schema": DRAFT_SCHEMA,
            "source": {"phase": "revealed", "run_id": "review-fixture"},
            "input": {"question": "synthetic question"},
            "participants": [{"pid": "one", "state": "accepted", "draft": draft,
                              "draft_sha256": hashlib.sha256(draft.encode("utf-8")).hexdigest()}],
        }
        self.labels = {"D1": "one"}
        self.synthesizer = {"started": True, "tree_confirmed_empty": True}

    def check(self, raw):
        return check_model_synthesis(raw, self.report, self.labels, self.synthesizer)

    def payload(self, quote="alpha", **changes):
        value = {"claims": [{"statement": "synthetic claim", "quotes": [{"draft": "D1", "text": quote}]}],
                 "disagreements": [], "strongest_counterexample": None,
                 "unresolved": [], "recommendation": "synthetic recommendation"}
        value.update(changes)
        return value

    def test_absent_boundary_whitespace_is_not_an_exact_quote(self):
        for text in (" alpha", "alpha ", "\talpha", "alpha\n\n"):
            with self.subTest(text=repr(text)):
                result = self.check(json.dumps(self.payload(text)))
                quote = result["claims"][0]["quotes"][0]
                self.assertEqual(quote["text"], text)
                self.assertEqual(quote["source_check"], "not_found")
                self.assertEqual(result["checks"]["exact_matches"], 0)
                self.assertEqual(result["claims"][0]["support"], "unsupported_addition")

    def test_real_boundary_whitespace_and_offsets_are_preserved(self):
        for text in (" beta ", "alpha\n", "최종 판단 🚀"):
            with self.subTest(text=repr(text)):
                result = self.check(json.dumps(self.payload(text)))
                quote = result["claims"][0]["quotes"][0]
                self.assertEqual(quote["text"], text)
                self.assertEqual(quote["source_check"], "exact_match")
                ref = quote["reference"]
                self.assertEqual(self.report["participants"][0]["draft"][ref["start"]:ref["end"]], text)

    def test_valid_unicode_pairs_are_accepted(self):
        result = self.check(json.dumps(self.payload("최종 판단 🚀"), ensure_ascii=True))
        self.assertEqual(result["checks"]["exact_matches"], 1)
        json.dumps(result, ensure_ascii=False).encode("utf-8")

    def test_unpaired_surrogates_fail_as_synthesis_errors(self):
        for field in ("statement", "quote", "label", "unresolved", "recommendation", "disagreement", "counter"):
            for bad in ("\ud800", "\udfff"):
                with self.subTest(field=field, bad=repr(bad)):
                    value = self.payload()
                    if field == "statement":
                        value["claims"][0]["statement"] = bad
                    elif field == "quote":
                        value["claims"][0]["quotes"][0]["text"] = bad
                    elif field == "label":
                        value["claims"][0]["quotes"][0]["draft"] = bad
                    elif field == "unresolved":
                        value["unresolved"] = [bad]
                    elif field == "recommendation":
                        value["recommendation"] = bad
                    elif field == "disagreement":
                        value["disagreements"] = [{"topic": bad, "quotes": []}]
                    else:
                        value["strongest_counterexample"] = {"statement": bad, "quotes": []}
                    with self.assertRaises(SynthesisError):
                        self.check(json.dumps(value))

    def test_duplicate_keys_do_not_silently_discard_evidence(self):
        examples = (
            '{"claims":[{"statement":"minority","quotes":[]}],'
            '"claims":[{"statement":"majority","quotes":[]}]}',
            '{"claims":[{"statement":"first","statement":"second","quotes":[]}]}',
            '{"claims":[{"statement":"claim","quotes":[{"draft":"D1","draft":"D2","text":"alpha"}]}]}',
        )
        for raw in examples:
            for wrapped in (raw, "```json\n" + raw + "\n```", "Result:\n" + raw):
                with self.subTest(raw=wrapped):
                    with self.assertRaises(SynthesisError):
                        self.check(wrapped)

    def test_regular_wrappers_and_unknown_labels_still_work(self):
        for wrapper in ("{}", "```json\n{}\n```", "Result:\n{}"):
            with self.subTest(wrapper=wrapper):
                result = self.check(wrapper.format(json.dumps(self.payload())))
                self.assertEqual(result["checks"]["exact_matches"], 1)
        value = self.payload()
        value["claims"][0]["quotes"][0]["draft"] = "not-a-source"
        result = self.check(json.dumps(value))
        self.assertEqual(result["claims"][0]["quotes"][0]["source_check"], "not_found")


if __name__ == "__main__":
    unittest.main()
