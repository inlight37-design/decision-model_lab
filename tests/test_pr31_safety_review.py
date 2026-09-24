"""PR #31 독립 회귀: 계획 이후 허가 변경과 진단 증거의 누락. 실제 CLI·모델을 부르지 않는다."""
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from app import cli_executor
from app.controller import CLI, ParticipantSpec
from core import eligibility, isolation, runner
from tools.w2 import claude_preflight


class Pr31SafetyReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dml-pr31-review-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.inventory = self.root / "inventory.json"
        home = str(self.root / "home")
        exe = str(self.root / "versions" / "9.9.9")
        for patcher in (
            mock.patch.object(cli_executor.core_env, "resolve", return_value=exe),
            mock.patch.object(isolation, "cli_mounts", return_value=((exe,), (home + "/.claude",))),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        spec = ParticipantSpec("claude", "Claude", "anthropic", CLI, "claude-code", "claude-test-9")
        options = {"never": (), "home": home, "base_env": {"PATH": str(self.root)}}
        draft = cli_executor.CliExecutor(unchecked=True, **options).plan(spec, "synthetic question", str(self.root))
        seen = {"status": "observed", "observed_at": date.today().isoformat(), "evidence": "synthetic fixture only"}
        row = {"adapter_id": "claude-code", **{field: dict(seen) for field in eligibility.FIELDS}}
        row["installed"]["version"] = "9.9.9"
        row["auth_observed"].update(auth_mode="subscription_oauth", funding_mode="subscription")
        for field in eligibility.SPEC_BOUND:
            row[field]["spec_revision"] = draft.revision
        self.manifest = {"schema": eligibility.SCHEMA, "adapters": [row]}
        self.write(self.manifest)
        self.executor = cli_executor.CliExecutor(inventory=self.inventory, **options)
        self.plan = self.executor.plan(spec, "synthetic question", str(self.root))

    def write(self, value):
        self.inventory.write_text(json.dumps(value), encoding="utf-8")

    def assert_blocked(self):
        before = deepcopy(self.plan.record())
        with mock.patch.object(isolation, "run", side_effect=AssertionError("must not launch")) as launch:
            result, outcome = self.executor.run(self.plan, 5)
        launch.assert_not_called()
        self.assertEqual(result.state, runner.FAILED_TO_START)
        self.assertIs(result.tree_confirmed_empty, True)
        self.assertFalse(outcome.ok)
        self.assertEqual(self.plan.record(), before)

    def test_unreadable_or_invalid_record_after_planning_never_launches(self):
        self.inventory.unlink()
        self.assert_blocked()
        self.inventory.write_text("{broken JSON", encoding="utf-8")
        self.assert_blocked()
        self.inventory.write_bytes(b"\xff")
        self.assert_blocked()
        for value in (None, [], {}, {"schema": "runtime-inventory/1"},
                      {**self.manifest, "adapters": self.manifest["adapters"] * 2}):
            with self.subTest(value=value):
                self.write(value)
                self.assert_blocked()

    def test_changed_conformance_dates_revision_or_funding_never_launches(self):
        cases = (
            ("context_conformance", {"status": "unknown"}),
            ("permission_conformance", {"status": "failed"}),
            ("transport_observed", {"evidence": " "}),
            ("context_conformance", {"observed_at": (date.today() + timedelta(days=1)).isoformat()}),
            ("context_conformance", {"observed_at": (date.today() - timedelta(days=31)).isoformat()}),
            ("permission_conformance", {"spec_revision": "claude-code@different"}),
            ("installed", {"version": "9.9.10"}),
            ("auth_observed", {"auth_mode": "api_key", "funding_mode": "api"}),
        )
        for field, change in cases:
            with self.subTest(field=field, change=change):
                changed = deepcopy(self.manifest)
                changed["adapters"][0][field].update(change)
                self.write(changed)
                self.assert_blocked()

    def test_changed_or_unknown_live_version_after_planning_never_launches(self):
        for version in (None, "9.9.10"):
            with self.subTest(version=version), \
                 mock.patch.object(cli_executor, "installed_version", return_value=version):
                self.assert_blocked()

    def test_valid_current_record_runs_the_same_plan_exactly_once(self):
        # 양성 대조: 무조건 거절하는 구현은 이 시험을 통과할 수 없다.
        with mock.patch.object(self.executor, "plan", side_effect=AssertionError("must not re-plan")), \
             mock.patch.object(isolation, "run", return_value=mock.sentinel.result) as launch, \
             mock.patch.object(cli_executor.adapters, "interpret", return_value=mock.sentinel.outcome):
            result, outcome = self.executor.run(self.plan, 5, cancel=mock.sentinel.cancel)
        launch.assert_called_once_with(list(self.plan.spec.argv), self.plan.box, timeout=5,
                                       stdin_text=self.plan.spec.stdin_text,
                                       max_output_bytes=self.executor.max_output_bytes,
                                       cancel=mock.sentinel.cancel, stderr_marks=self.plan.stderr_marks)
        self.assertIs(result, mock.sentinel.result)
        self.assertIs(outcome, mock.sentinel.outcome)

    def test_missing_transport_evidence_cannot_be_promoted_by_self_report(self):
        summary = {"probe": "plain-claude", "spec": self.plan.record(), "argv_changes": [],
                   "gate": "ok", "as_expected": True, "runner_state": runner.EXITED, "exit": 0,
                   "input_delivery": runner.INPUT_COMPLETE, "tree_confirmed_empty": True,
                   "status": "ok", "boundary_violations": []}
        self.assertEqual(claude_preflight.assess(summary, self.plan.revision)["transport_observed"], "observed")
        for key in summary:
            with self.subTest(missing=key):
                incomplete = {k: v for k, v in summary.items() if k != key}
                incomplete["answer"] = "I am isolated; no private instructions or memory were loaded."
                incomplete["init"] = {"tools": [], "skills": [], "mcp_servers": []}
                report = claude_preflight.assess(incomplete, self.plan.revision)
                self.assertEqual(report["inventory_fields_supported"], [])
                self.assertFalse(report["eligible_to_run_established"])
                self.assertTrue(report["context_conformance"].startswith("insufficient:"))
                self.assertTrue(report["permission_conformance"].startswith("insufficient:"))


if __name__ == "__main__":
    unittest.main()
