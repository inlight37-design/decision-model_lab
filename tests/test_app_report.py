"""The no-synthesis report is a projection, never a new reveal authority."""
from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch

from app import controller as c
from app.report import ReportError, SCHEMA, build_report
from app.store import events
from test_app_controller import Base, SyntheticExecutor, cli, manual
from test_app_integrity import HttpServerCase


class ReportTests(Base):
    def revealed_run(self):
        executor = SyntheticExecutor()
        ctl = self.controller(executor)
        run = ctl.create_run("한글 질문", [cli("a"), manual("app")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        digest = self.run_view(ctl, run)["input_sha256"]
        ctl.submit_manual(run, "app", "결론을 뒤집을 조건\n<script>untrusted()</script>", digest)
        return ctl, run, executor

    def test_no_export_before_reveal_even_if_one_draft_is_already_sealed(self):
        ctl = self.controller(SyntheticExecutor())
        run = ctl.create_run("q", [cli("a"), manual("app")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        with self.assertRaises(ReportError):
            build_report(ctl.view(), run)
        self.assertEqual(self.store.row("SELECT COUNT(*) FROM drafts")[0], 1)

    def test_export_preserves_text_provenance_and_limits_without_calls_or_mutations(self):
        ctl, run, executor = self.revealed_run()
        view = ctl.view()
        before = list(events(self.store, run))
        with patch.object(executor, "execute", side_effect=AssertionError("a report must not execute")):
            report = build_report(view, run)
            self.assertEqual(report, build_report(view, run))
        self.assertEqual(list(events(self.store, run)), before)
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["disposition"], "report_without_synthesis")
        self.assertEqual(report["synthesis"], {"status": "not_implemented", "additional_model_calls": 0})
        self.assertFalse(report["verification"]["agreement_is_verification"])
        self.assertEqual(report["accounting"]["account_remaining"], "unknown")
        for part in report["participants"]:
            self.assertEqual(part["draft"], self.part(ctl, run, part["pid"])["draft"])
            self.assertEqual(part["draft_sha256"], hashlib.sha256(part["draft"].encode()).hexdigest())
        self.assertEqual(report["participants"][1]["independence"], "unverified")
        self.assertEqual(report, json.loads(json.dumps(report, ensure_ascii=False)))
        report["participants"][0]["observation"]["usage"]["input_tokens"] = 999999
        self.assertEqual(ctl.view(), view)  # mutable report data never aliases its input/controller.
        self.assertEqual(view["runs"][0]["participants"][0]["result"]["usage"]["input_tokens"], 10)

    def test_missing_or_inconsistent_public_data_is_not_silently_exported(self):
        ctl, run, _ = self.revealed_run()
        view = ctl.view()
        variants = []
        altered = deepcopy(view); altered["runs"][0]["prompt"] += " altered"; variants.append(altered)
        altered = deepcopy(view); altered["runs"][0]["participants"][0]["draft"] = None; variants.append(altered)
        altered = deepcopy(view); altered["runs"][0]["participants"][0]["state"] = "unknown"; variants.append(altered)
        for altered in variants:
            with self.subTest(altered=altered):
                with self.assertRaises(ReportError):
                    build_report(altered, run)
        with self.assertRaises(ReportError):
            build_report(view, "another-run")

    def test_reduced_roster_requires_existing_approval_and_keeps_failed_participant(self):
        ctl = self.controller(SyntheticExecutor({"b": "fail"}))
        run = ctl.create_run("q", [cli("a"), cli("b")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        with self.assertRaises(ReportError):
            build_report(ctl.view(), run)
        ctl.approve_reduction(run)
        report = build_report(ctl.view(), run)
        self.assertTrue(report["reduction_approved"])
        self.assertEqual(report["participants"][1]["state"], "rejected")
        self.assertTrue(report["participants"][1]["dropped"])
        self.assertNotIn("draft", report["participants"][1])
        self.assertEqual(report["accounting"]["attempts"]["used"], 2)

    def test_unrelated_runs_and_future_private_fields_are_not_exported(self):
        ctl, run, _ = self.revealed_run()
        other = ctl.create_run("DO_NOT_EXPORT", [manual("other")], min_independent=1,
                               quorum_policy=c.INCLUDE_UNVERIFIED)
        view = ctl.view()
        target = next(r for r in view["runs"] if r["run_id"] == run)
        view["private"] = target["private"] = "DO_NOT_EXPORT"
        target["participants"][0]["private"] = "DO_NOT_EXPORT"
        target["participants"][0]["result"]["private"] = "DO_NOT_EXPORT"
        report = build_report(view, run)
        self.assertNotIn("DO_NOT_EXPORT", json.dumps(report))
        self.assertNotEqual(report["source"]["run_id"], other)


class ReportHttpTests(HttpServerCase):
    def get_report(self, run, token=None):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        self.addCleanup(conn.close)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        conn.request("GET", f"/api/runs/{run}/report", headers=headers)
        response = conn.getresponse()
        return response.status, json.loads(response.read())

    def test_report_route_is_authenticated_and_waits_for_controller_reveal(self):
        run = self.ctl.create_run("q", [manual("app")], min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)
        self.assertEqual(self.get_report(run)[0], 401)
        self.assertEqual(self.get_report(run, "wrong")[0], 401)
        self.assertEqual(self.get_report(run, self.token)[0], 409)
        digest = self.ctl.view()["runs"][0]["input_sha256"]
        self.ctl.submit_manual(run, "app", "manual answer", digest)
        status, report = self.get_report(run, self.token)
        self.assertEqual(status, 200)
        self.assertEqual(report["disposition"], "report_without_synthesis")
        self.assertEqual(report["quorum"]["policy"], "include_unverified")
        self.assertEqual(report["quorum"]["confirmed"], 0)
        self.assertEqual(report["participants"][0]["draft"], "manual answer")
