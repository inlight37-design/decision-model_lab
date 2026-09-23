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
        r = m.advance(roster(), m.DRAFTING)
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
        r = roster()
        for phase in (m.DRAFTING, m.REVEALED, m.SYNTHESIS):
            r = m.advance(r, phase)
        d = m.decide(r, "synthesizer_unavailable")
        self.assertEqual(d.action, m.REPORT_WITHOUT_SYNTHESIS)
        self.assertIn("not a completed synthesis", d.note)

    def test_invalid_inputs_are_refused(self):
        with self.assertRaises(m.MembershipError):
            m.start(("a", "a"), min_independent=1)
        with self.assertRaises(m.MembershipError):
            m.start(("a",), min_independent=2)
        with self.assertRaises(m.MembershipError):
            m.advance(m.advance(m.advance(roster(), m.DRAFTING), m.REVEALED), m.DRAFTING)  # 공개를 되돌릴 수 없다
        with self.assertRaises(m.MembershipError):
            m.decide(roster(), "unavailable", "stranger")
        with self.assertRaises(m.MembershipError):
            m.decide(roster(), "exploded", "agy")


class BoundaryReviewRegressionTests(unittest.TestCase):
    """2026-09-23 경계 리뷰 R03(docs/reviews/2026-09-23-wsl2-boundary/). 명단에 받는 것과 진행 허가는 다르다."""

    def test_a_substitute_joins_but_does_not_lift_a_block_on_its_own(self):
        r = m.start(("A", "B", "C"), min_independent=3, alternates=("D",))
        r = m.decide(r, "unavailable", "A").roster
        r = m.decide(r, "unavailable", "B").roster
        d = m.decide(r, "substitute_requested", "D")
        self.assertIn("D", d.roster.active)       # 대체자는 명단에 들어간다
        self.assertEqual(d.action, m.BLOCKED)     # 그래도 2/3이면 진행 허가가 아니다
        self.assertFalse(m.quorum_met(d.roster))
        self.assertIn("substitution", d.note)

    def test_an_unconfirmed_cancel_that_breaks_quorum_blocks(self):
        r = m.advance(m.start(("A", "B"), min_independent=2), m.DRAFTING)
        d = m.decide(r, "cancel_unconfirmed", "A")
        self.assertEqual(d.action, m.BLOCKED)
        self.assertIn("A", d.roster.unknown)      # UNKNOWN과 예산 점유는 그대로다
        self.assertIn("budget slot", d.note)

    def test_phases_advance_one_step_at_a_time_and_need_quorum_before_reveal(self):
        with self.assertRaises(m.MembershipError):
            m.advance(roster(), m.SYNTHESIS)       # 초안·공개를 건너뛰지 않는다
        blocked = m.decide(m.decide(roster(), "unavailable", "agy").roster, "unavailable", "codex")
        self.assertEqual(blocked.action, m.BLOCKED)
        with self.assertRaises(m.MembershipError):
            m.advance(blocked.roster, m.DRAFTING)  # 막힌 명단으로 초안 단계에 들어가지 않는다
        drafting = m.advance(roster(min_independent=3), m.DRAFTING)
        short = m.decide(drafting, "cancel_unconfirmed", "codex").roster
        with self.assertRaises(m.MembershipError):
            m.advance(short, m.REVEALED)           # 셀 수 있는 초안이 모자라면 공개하지 않는다


if __name__ == "__main__":
    unittest.main()
