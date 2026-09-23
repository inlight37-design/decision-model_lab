"""core.membership 검사 — PR #4 R09의 전이 표와 사용자 확정 13(조용히 채우지 않음)."""
import unittest

from core import membership as m


def roster(**kwargs):
    base = dict(min_independent=2, alternates=("gemini",))
    base.update(kwargs)
    return m.start(("claude", "codex", "agy"), **base)


class MembershipTests(unittest.TestCase):
    def test_unavailable_before_start_reduces_or_blocks(self):
        d = m.decide(roster(), "unavailable", "agy")
        self.assertEqual(d.action, m.PROCEED_REDUCED)
        self.assertEqual(d.roster.dropped, (("agy", "unavailable"),))
        d2 = m.decide(d.roster, "unavailable", "codex")
        self.assertEqual(d2.action, m.BLOCKED)  # 최소 인원 미달. 유료 API로 넘기지 않는다
        self.assertIn("No paid fallback", d2.note)

    def test_quota_exhausted_while_drafting_keeps_the_record(self):
        r = m.advance(roster(), m.DRAFTING)
        d = m.decide(r, "quota_exhausted", "claude")
        self.assertEqual(d.action, m.PROCEED_REDUCED)
        self.assertEqual(d.roster.dropped, (("claude", "quota exhausted"),))
        self.assertNotIn("claude", d.roster.active)

    def test_after_reveal_a_loss_only_reduces_the_review_round(self):
        r = m.advance(m.advance(roster(), m.DRAFTING), m.REVEALED)
        d = m.decide(r, "quota_exhausted", "claude")
        self.assertEqual(d.action, m.PROCEED_REDUCED)
        self.assertIn("review round is reduced", d.note)

    def test_substitutes_only_pre_approved_and_only_before_reveal(self):
        r = m.decide(roster(), "unavailable", "agy").roster
        self.assertEqual(m.decide(r, "substitute_requested", "grok").action, m.REJECT_SUBSTITUTE)
        d = m.decide(r, "substitute_requested", "gemini")
        self.assertEqual(d.action, m.PROCEED)
        self.assertIn("gemini", d.roster.active)
        self.assertIn("substitution", d.note)  # 대체는 화면에 드러난다
        revealed = m.advance(m.advance(r, m.DRAFTING), m.REVEALED)
        self.assertEqual(m.decide(revealed, "substitute_requested", "gemini").action, m.REJECT_SUBSTITUTE)

    def test_unconfirmed_cancel_stays_unknown_and_does_not_count(self):
        r = m.advance(roster(min_independent=3), m.DRAFTING)
        d = m.decide(r, "cancel_unconfirmed", "codex")
        self.assertEqual(d.action, m.KEEP_UNKNOWN)
        self.assertIn("codex", d.roster.unknown)
        self.assertIn("codex", d.roster.active)  # 뺐다고 취소된 것이 아니다
        self.assertEqual(m.decide(d.roster, "unavailable", "agy").action, m.BLOCKED)

    def test_recovered_provider_waits_for_the_next_run(self):
        r = m.decide(roster(), "unavailable", "agy").roster
        d = m.decide(r, "recovered", "agy")
        self.assertEqual(d.action, m.DEFER)
        self.assertEqual(d.roster, r)

    def test_synthesizer_loss_is_not_a_synthesis(self):
        d = m.decide(m.advance(roster(), m.SYNTHESIS), "synthesizer_unavailable")
        self.assertEqual(d.action, m.REPORT_WITHOUT_SYNTHESIS)
        self.assertIn("not a completed synthesis", d.note)

    def test_invalid_inputs_are_refused(self):
        with self.assertRaises(m.MembershipError):
            m.start(("a", "a"), min_independent=1)
        with self.assertRaises(m.MembershipError):
            m.start(("a",), min_independent=2)
        with self.assertRaises(m.MembershipError):
            m.advance(m.advance(roster(), m.REVEALED), m.DRAFTING)  # 공개를 되돌릴 수 없다
        with self.assertRaises(m.MembershipError):
            m.decide(roster(), "unavailable", "stranger")
        with self.assertRaises(m.MembershipError):
            m.decide(roster(), "exploded", "agy")


if __name__ == "__main__":
    unittest.main()
