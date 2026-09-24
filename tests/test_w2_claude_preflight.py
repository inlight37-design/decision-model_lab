"""Claude preflight does not call a model or mistake diagnostic evidence for participant conformance."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from app.cli_executor import CliExecutor
from app.controller import CLI, ParticipantSpec
from core import runner
from tools.w2 import claude_preflight as probe, observe


def result(stdout, *, exit_code=0, tree=True):
    return runner.RunResult((), runner.EXITED, exit_code, stdout, "", False, False, 1, 0, tree,
                            containment=runner.PID_NAMESPACE)


class ClaudePreflightTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.home = Path(self.root.name, "home").as_posix()
        self.work = Path(self.root.name, "work").as_posix()
        self.exe = self.home + "/.local/share/claude/versions/2.1.280"
        self.executor = CliExecutor(never=(), unchecked=True, home=self.home)
        resolver = mock.patch("app.cli_executor.core_env.resolve", return_value=self.exe)
        mounts = mock.patch("app.cli_executor.isolation.cli_mounts",
                            return_value=((self.exe,), (self.home + "/.claude", self.home + "/.claude.json")))
        resolver.start()
        mounts.start()
        self.addCleanup(resolver.stop)
        self.addCleanup(mounts.stop)
        self.exact, self.diagnostic = probe.plans(self.executor, self.work, "claude-sonnet-5")

    def test_exact_plan_is_the_unmodified_plain_claude_controller_contract(self):
        spec = ParticipantSpec("id", "id", "claude", CLI, "claude-code", "claude-sonnet-5")
        with mock.patch.object(probe.isolation, "run", side_effect=AssertionError("must not execute")):
            plain = self.executor.plan(spec, observe.PLAIN, self.work,
                                       variant=lambda argv: observe._argv_for("plain-claude", argv))
            report = probe.describe(self.exact, self.diagnostic, self.home)
        self.assertEqual(self.exact.spec.argv, plain.spec.argv)
        self.assertEqual(self.exact.revision, plain.revision)
        argv = self.exact.spec.argv
        self.assertEqual(argv[argv.index("--output-format") + 1], "stream-json")
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.assertNotIn("--add-dir", argv)
        self.assertEqual(self.exact.box.read_only, (self.exe,))
        self.assertEqual(self.exact.changes, ())
        self.assertNotEqual(self.exact.revision, self.diagnostic.revision)
        self.assertFalse(report["diagnostic_covers_participant"])
        self.assertEqual(report["model_calls"], 0)
        self.assertFalse(report["approval_changed"])
        self.assertNotIn(observe.PLAIN, json.dumps(report))

    def test_help_keeps_wrapped_descriptions_and_distinguishes_missing_flags(self):
        sections = probe.help_sections("Usage\n  --tools <list>  Use an empty string\n"
                                       "    to disable tools.\n  -p, --print  Print output\n")
        self.assertIn("to disable tools.", sections["--tools"])
        self.assertNotIn("--print", sections["--tools"])
        self.assertIsNone(sections["--restricted"])

    def test_preflight_runs_only_synthetic_help_and_version_by_default(self):
        help_text = "\n".join("  " + flag + "  help" for flag in probe.HELP_FLAGS)
        with mock.patch.object(probe.sys, "platform", "linux"), \
             mock.patch.object(probe.isolation, "run", side_effect=[result("2.1.280 (Claude Code)\n"),
                                                                    result(help_text)]) as launch:
            report = probe.preflight(self.exact)
        self.assertEqual([c.args[0][1:] for c in launch.call_args_list], [["--version"], ["--help"]])
        for call in launch.call_args_list:
            box = call.args[1]
            self.assertNotEqual(box.home, self.home)
            self.assertEqual(box.read_write, ())
            self.assertEqual(box.read_only, (os.path.realpath(self.exe),))
        self.assertTrue(report["ready_for_review"])
        self.assertEqual(report["auth"]["status"], "not_checked")

    def test_real_auth_is_separate_and_drops_account_fields(self):
        help_text = "\n".join("  " + flag + "  help" for flag in probe.HELP_FLAGS)
        auth = json.dumps({"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty",
                           "email": "private@example.test", "orgId": "private-organization"})
        with mock.patch.object(probe.sys, "platform", "linux"), \
             mock.patch.object(probe.isolation, "run", side_effect=[result("2.1.280 (Claude Code)\n"),
                                                                    result(help_text), result(auth)]) as launch:
            report = probe.preflight(self.exact, real_auth=True)
        self.assertEqual(launch.call_args.args[0][1:], ["auth", "status"])
        self.assertIs(launch.call_args.args[1], self.exact.box)
        self.assertEqual(report["auth"]["status"], "subscription_observed")
        self.assertNotIn("private", json.dumps(report))

    def test_incomplete_help_or_unconfirmed_tree_stops_auth_diagnostic(self):
        for help_run in (result(""), result("  --tools help", tree=False)):
            with self.subTest(help=help_run), mock.patch.object(probe.sys, "platform", "linux"), \
                 mock.patch.object(probe.isolation, "run", side_effect=[result("2.1.280 (Claude Code)\n"),
                                                                        help_run]) as launch:
                report = probe.preflight(self.exact, real_auth=True)
                self.assertFalse(report["ready_for_review"])
                self.assertEqual(report["auth"]["status"], "not_run_preflight_failed")
                self.assertEqual(launch.call_count, 2)

    def accepted_summary(self):
        return {"probe": "plain-claude", "spec": self.exact.record(), "argv_changes": [],
                "gate": "ok", "as_expected": True, "runner_state": "exited", "exit": 0,
                "input_delivery": "complete", "tree_confirmed_empty": True,
                "status": "ok", "boundary_violations": [], "permission_denials": 0,
                "created_txt_exists_after_run": False,
                "answer": "No instructions loaded and no tool available.",
                "init": {"tools": [], "skills": [], "mcp_servers": []}}

    def test_json_result_and_model_self_report_only_support_transport(self):
        out = probe.assess(self.accepted_summary(), self.exact.revision)
        self.assertEqual(out["transport_observed"], "observed")
        self.assertEqual(out["inventory_fields_supported"], ["transport_observed"])
        self.assertTrue(out["permission_conformance"].startswith("insufficient:"))
        self.assertTrue(out["context_conformance"].startswith("insufficient:"))
        self.assertFalse(out["eligible_to_run_established"])

    def test_revision_drift_failed_gate_and_missing_evidence_never_pass(self):
        for change in ({"spec": self.diagnostic.record()}, {"input_delivery": "partial"},
                       {"spec": {**self.exact.record(), "kind": "mock"}},
                       {"tree_confirmed_empty": False}, {"gate": "model_mismatch"},
                       {"boundary_violations": ["file_written"]}, {"argv_changes": ["stream-json"]},
                       {"probe": "b1"}, {"as_expected": False}):
            with self.subTest(change=change):
                out = probe.assess({**self.accepted_summary(), **change}, self.exact.revision)
                self.assertEqual(out["inventory_fields_supported"], [])
        for missing in ({}, None, [], {"summary": "bad"}):
            self.assertEqual(probe.assess(missing, self.exact.revision)["transport_observed"], "insufficient")


if __name__ == "__main__":
    unittest.main()
