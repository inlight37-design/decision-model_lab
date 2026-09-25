"""Source comparison, mock completion/fallback and reveal boundaries without models."""
from copy import deepcopy
import hashlib
import json
from unittest.mock import patch

from app import controller as c
from app.report import build_report
from app.store import events
from app.synthesis import SynthesisError, compare_claims, mock_synthesize
from test_app_controller import Base, SyntheticExecutor, cli, manual
from test_app_integrity import HttpServerCase


class SynthesisTests(Base):
    def revealed(self):
        ctl = self.controller(SyntheticExecutor())
        run = ctl.create_run("어떤 선택을 할까?", [manual("a"), manual("b")], min_independent=2,
                             quorum_policy=c.INCLUDE_UNVERIFIED)
        digest = self.run_view(ctl, run)["input_sha256"]
        ctl.submit_manual(run, "a", "공통 주장\n찬성: 작게 시작\n반례: 비용이 높으면 보류", digest)
        ctl.submit_manual(run, "b", "공통 주장\n반대: 먼저 측정\n확인 불가: 장기 비용", digest)
        return ctl, run

    def test_exact_agreement_does_not_verify_truth_or_discard_dissent(self):
        ctl, run = self.revealed()
        report = build_report(ctl.view(), run)
        result = mock_synthesize(report)
        self.assertEqual(result, mock_synthesize(report))
        common = next(x for x in result["claims"] if x["text"] == "공통 주장")
        self.assertEqual({r["pid"] for r in common["references"]}, {"a", "b"})
        self.assertEqual(common["disposition"], "unresolved")
        self.assertTrue(all(x["factual_check"] == "not_performed" for x in result["claims"]))
        self.assertIn("반례: 비용이 높으면 보류", [x["text"] for x in result["claims"]])
        self.assertIn("반대: 먼저 측정", [x["text"] for x in result["claims"]])
        self.assertEqual(result["card"]["status"], "qualified")
        self.assertTrue(result["card"]["overturnedBy"])
        self.assertFalse(result["comparison"]["agreement_is_verification"])

    def test_forged_source_identity_offsets_or_digest_are_rejected(self):
        ctl, run = self.revealed()
        report = build_report(ctl.view(), run)
        claims = mock_synthesize(report)["claims"]
        for key, value in (("run_id", "other"), ("pid", "other"), ("sha256", "bad"),
                           ("start", -1), ("end", 99999), ("start", False)):
            altered = deepcopy(claims)
            altered[0]["references"][0][key] = value
            with self.subTest(key=key), self.assertRaises(SynthesisError):
                compare_claims(altered, report)
        changed = deepcopy(report)
        changed["participants"][0]["draft"] += " tampered"
        with self.assertRaises(SynthesisError):
            mock_synthesize(changed)

    def test_display_limits_report_omissions_and_keep_complete_sources(self):
        ctl, run = self.revealed()
        report = build_report(ctl.view(), run)
        before = deepcopy(report)
        with patch("app.synthesis.MAX_EXCERPTS", 2):
            result = mock_synthesize(report)
        self.assertGreater(result["comparison"]["omitted_lines"], 0)
        self.assertEqual(report, before)
        self.assertTrue(any("생략" in text for text in result["card"]["unresolved"]))

    def test_repeated_lines_cannot_expand_the_persisted_artifact_or_source_count(self):
        ctl, run = self.revealed()
        report = build_report(ctl.view(), run)
        part = report["participants"][0]
        part["draft"] = "반복 주장\n" * 10000
        part["draft_sha256"] = hashlib.sha256(part["draft"].encode()).hexdigest()
        result = mock_synthesize(report)
        claim = next(x for x in result["claims"] if x["text"] == "반복 주장")
        self.assertEqual(len(claim["references"]), 1)
        self.assertEqual(result["comparison"]["omitted_lines"], 9999)
        self.assertLess(len(json.dumps(result)), 20000)

    def test_no_displayable_claims_is_unavailable_and_preserves_the_full_draft(self):
        ctl = self.controller(SyntheticExecutor())
        run = ctl.create_run("q", [manual("a")], min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)
        text = "긴문장" * 1000
        ctl.submit_manual(run, "a", text, self.run_view(ctl, run)["input_sha256"])
        ctl.synthesize(run)
        view = self.run_view(ctl, run)
        self.assertEqual(view["synthesis"]["status"], "unavailable")
        self.assertEqual(view["participants"][0]["draft"], text)

    def test_failed_synthesis_commit_rolls_back_and_can_be_requested_again(self):
        ctl, run = self.revealed()
        self.store._db.execute("CREATE TRIGGER reject_synthesis BEFORE INSERT ON events "
                               "WHEN NEW.kind = 'synthesis_completed' BEGIN SELECT RAISE(ABORT, 'fail'); END")
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            ctl.synthesize(run)
        self.assertNotIn("synthesis", self.run_view(ctl, run))
        self.store._db.execute("DROP TRIGGER reject_synthesis")
        ctl.synthesize(run)
        self.assertEqual(self.run_view(ctl, run)["synthesis"]["status"], "completed")

    def test_synthesis_is_explicit_durable_idempotent_and_costs_no_calls(self):
        ctl, run = self.revealed()
        before = self.run_view(ctl, run)["budget"]
        with patch.object(ctl.executor, "execute", side_effect=AssertionError("no model calls")):
            ctl.synthesize(run)
            first = self.run_view(ctl, run)["synthesis"]
            ctl.synthesize(run)
        self.assertEqual(self.run_view(ctl, run)["budget"], before)
        self.assertEqual(first["status"], "completed")
        self.assertEqual(sum(e["kind"] == "synthesis_completed" for e in events(self.store, run)), 1)
        restarted = self.controller(SyntheticExecutor())
        self.assertEqual(self.run_view(restarted, run)["synthesis"], first)

    def test_synthesis_failure_keeps_original_report_and_has_no_retry_loop(self):
        ctl, run = self.revealed()
        before = build_report(ctl.view(), run)
        with patch("app.controller.mock_synthesize", side_effect=SynthesisError("bad synthetic reference")):
            ctl.synthesize(run)
        self.assertEqual(self.run_view(ctl, run)["synthesis"]["status"], "unavailable")
        self.assertEqual(build_report(ctl.view(), run), before)
        ctl.synthesize(run)
        self.assertEqual(sum(e["kind"] == "synthesis_completed" for e in events(self.store, run)), 1)

    def test_no_synthesis_or_content_on_sealed_cancelled_unknown_or_unapproved_run(self):
        for scenario in ("sealed", "cancelled", "unknown", "reduced"):
            with self.subTest(scenario=scenario):
                ex = SyntheticExecutor({"b": "unknown" if scenario == "unknown" else "fail"})
                ctl = self.controller(ex)
                parts = [cli("a"), cli("b")] if scenario in ("unknown", "reduced") else [manual("a")]
                run = ctl.create_run("q", parts, min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)
                self.assertTrue(ctl.wait_idle())
                if scenario == "cancelled":
                    ctl.cancel_run(run)
                with self.assertRaises(c.ControllerError):
                    ctl.synthesize(run)
                self.assertNotIn("synthesis", self.run_view(ctl, run))


class SynthesisHttpTests(HttpServerCase):
    def decision_report(self, run, token=None):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        self.addCleanup(conn.close)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        conn.request("GET", f"/api/runs/{run}/decision-report", headers=headers)
        response = conn.getresponse()
        return response.status, json.loads(response.read())

    def test_decision_export_requires_auth_reveal_and_synthesis_and_excludes_other_runs(self):
        run = self.ctl.create_run("selected", [manual("app")], min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)
        self.assertEqual(self.decision_report(run)[0], 401)
        self.assertEqual(self.decision_report(run, "wrong")[0], 401)
        self.assertEqual(self.decision_report(run, self.token)[0], 409)
        digest = self.ctl.view(run)["runs"][0]["input_sha256"]
        self.ctl.submit_manual(run, "app", "주장\n반례", digest)
        self.assertEqual(self.decision_report(run, self.token)[0], 409)
        self.ctl.synthesize(run)
        self.ctl.create_run("PRIVATE_OTHER_RUN", [manual("other")], min_independent=1,
                            quorum_policy=c.INCLUDE_UNVERIFIED)
        status, result = self.decision_report(run, self.token)
        self.assertEqual(status, 200)
        self.assertEqual((result["schema"], result["model_syntheses"]), ("a1-decision-report/4", []))
        self.assertEqual(result["synthesis"]["status"], "completed")
        self.assertEqual(result["draft_report"]["synthesis"]["status"], "not_included")
        self.assertNotIn("PRIVATE_OTHER_RUN", json.dumps(result))

    def test_synthesis_uses_authenticated_mutation_endpoint(self):
        run = self.ctl.create_run("q", [manual("app")], min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)
        path = f"/api/runs/{run}/synthesize"
        self.assertEqual(self.request({}, path=path, headers={"Authorization": "Bearer wrong"})[0], 401)
        self.assertEqual(self.request({}, path=path)[0], 400)
        digest = self.ctl.view()["runs"][0]["input_sha256"]
        self.ctl.submit_manual(run, "app", "주장\n반례", digest)
        self.assertEqual(self.request({}, path=path)[0], 200)
        result = self.ctl.view()["runs"][0]["synthesis"]
        self.assertEqual(result["additional_model_calls"], 0)
        self.assertEqual(result["card"]["status"], "qualified")
