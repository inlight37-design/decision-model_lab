"""core.eligibility와 runtime-inventory/2 기록 검사(인계 N4). CLI·모델은 부르지 않는다."""
import copy
from datetime import date
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from app import cli_executor
from app.cli_executor import CliExecutor, installed_version
from core import adapters, eligibility
from tools import runtime_inventory

ROOT = Path(__file__).resolve().parents[1]
WSL_V2 = ROOT / "docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.v2.json"
TODAY = date(2026, 9, 23)


def observed(**extra):
    return {"status": "observed", "observed_at": "2026-09-23", "evidence": "synthetic", **extra}


SPEC = adapters.SPEC_REVISION["claude-code"]


def record(**overrides):
    row = {"adapter_id": "claude-code",
           "installed": observed(version="2.1.280"),
           "auth_observed": observed(auth_mode="subscription_oauth", funding_mode="subscription"),
           "transport_observed": observed(spec_revision=SPEC), "context_conformance": observed(spec_revision=SPEC),
           "permission_conformance": observed(spec_revision=SPEC)}
    row.update(overrides)
    return {"schema": eligibility.SCHEMA, "host": {"label": "test-host"}, "adapters": [row]}


def verdict(manifest, **kwargs):
    kwargs.setdefault("enabled", True)
    kwargs.setdefault("today", TODAY)
    kwargs.setdefault("current_version", "2.1.280")
    return eligibility.eligibility(manifest, "claude-code", **kwargs)


class EligibilityTests(unittest.TestCase):
    def test_all_five_fresh_observations_on_the_same_version_and_a_subscription_allow_a_run(self):
        self.assertEqual(verdict(record()), eligibility.Verdict(True, ()))

    def test_each_missing_condition_is_named(self):
        for field in eligibility.FIELDS[2:]:
            for status in ("unknown", "failed"):
                with self.subTest(field=field, status=status):
                    v = verdict(record(**{field: {"status": status}}))
                    self.assertFalse(v.eligible)
                    self.assertIn(f"{field} is {status}", v.reasons)
        cases = (({"current_version": "2.1.281"}, "differs from the recorded 2.1.280"),
                 ({"current_version": None}, "installed version unknown"),
                 ({"today": date(2026, 11, 1)}, "days ago"),
                 ({"enabled": False}, "turned off"))
        for kwargs, words in cases:
            with self.subTest(kwargs=kwargs):
                v = verdict(record(), **kwargs)
                self.assertFalse(v.eligible)
                self.assertTrue(any(words in r for r in v.reasons), v.reasons)

    def test_api_billing_needs_an_explicit_opt_in(self):
        api = record(auth_observed=observed(auth_mode="api_key", funding_mode="api_billing"))
        self.assertFalse(verdict(api).eligible)
        self.assertTrue(verdict(api, allow_api=True).eligible)

    def test_other_records_and_adapters_are_refused(self):
        self.assertFalse(verdict({"schema": "runtime-inventory/1"}).eligible)
        self.assertIn("claude-code is not in the record",
                      verdict({"schema": eligibility.SCHEMA, "adapters": []}).reasons)

    def test_malformed_or_impossible_records_are_refused_at_run_time(self):
        """2026-09-24 리뷰 R02의 반례. 기록 검사기를 거치지 않는 실행 직전 경로에서도 거절한다."""
        def every(mutate):
            broken = record()
            for field in eligibility.FIELDS:
                mutate(broken["adapters"][0][field])
            return broken
        missing_evidence = record()
        missing_evidence["adapters"][0]["context_conformance"].pop("evidence")
        no_version = record()
        no_version["adapters"][0]["installed"].pop("version")
        twice = record()
        twice["adapters"].append(copy.deepcopy(twice["adapters"][0]))
        cases = ((every(lambda e: e.update(observed_at="2099-01-01")), {}, "observed in the future"),
                 (every(lambda e: e.update(observed_at="2026-02-30")), {}, "observed_at as"),
                 (missing_evidence, {}, "context_conformance: observed needs a non-empty evidence"),
                 (no_version, {"current_version": None}, "installed: observed needs the version"),
                 (twice, {}, "appears more than once"),
                 (record(context_conformance="observed"), {}, "context_conformance is missing"))
        for manifest, kwargs, words in cases:
            with self.subTest(words=words):
                v = verdict(manifest, **kwargs)
                self.assertFalse(v.eligible)
                self.assertTrue(any(words in r for r in v.reasons), v.reasons)

    def test_observations_are_bound_to_the_participant_spec_they_were_made_with(self):
        """2026-09-24 리뷰 R04. argv가 바뀌면(명세 판이 오르면) 옛 관측으로 허가하지 않는다. 설치·로그인 칸은 묶지 않는다."""
        v = verdict(record(), spec_revision="discussant-99")
        self.assertFalse(v.eligible)
        self.assertEqual(len(v.reasons), len(eligibility.SPEC_BOUND))
        self.assertTrue(all("the current spec is discussant-99" in r for r in v.reasons), v.reasons)
        unbound = record(permission_conformance=observed())
        self.assertTrue(any("permission_conformance was observed with participant spec unknown" in reason
                            for reason in verdict(unbound).reasons))

    def test_runtime_and_inventory_share_every_structural_refusal(self):
        for field in eligibility.FIELDS:
            for entry in (None, "observed", {"status": "invented"}, {"status": "observed"},
                          observed(evidence=" "), observed(observed_at="2026-02-30")):
                with self.subTest(field=field, entry=entry):
                    broken = record(**{field: entry})
                    problems = eligibility.row_problems(broken["adapters"][0])
                    self.assertTrue(problems)
                    runtime = verdict(broken)
                    inventory = runtime_inventory.validate_manifest_v2(broken)
                    self.assertFalse(runtime.eligible)
                    for problem in problems:
                        self.assertIn(problem, runtime.reasons)
                        self.assertIn("claude-code." + problem, inventory)


class RecordTests(unittest.TestCase):
    def test_the_committed_wsl_record_allows_claude_and_refuses_codex_for_its_context(self):
        # 2단계(2026-09-23) 관측 뒤의 기록: Claude는 다섯 칸이 모두 관측됐다. Codex는 작업 폴더의 AGENTS.md를 실어
        # 문맥 준수가 failed다(K38·K44).
        manifest = json.loads(WSL_V2.read_text(encoding="utf-8"))
        self.assertEqual(runtime_inventory.validate_manifest_v2(manifest), [])
        claude = eligibility.eligibility(manifest, "claude-code", enabled=True, today=TODAY, current_version="2.1.280")
        self.assertTrue(claude.eligible, claude.reasons)
        codex = eligibility.eligibility(manifest, "codex", enabled=True, today=TODAY, current_version="0.156.1")
        # 문맥이 failed이고, 2단계의 전송·권한 관측은 옛 argv(discussant-1, --sandbox read-only)로 본 것이다 — K46
        # profile을 넣은 지금의 argv(discussant-2)로는 다시 관측해야 한다(리뷰 R04)
        self.assertEqual(codex.reasons, (
            "transport_observed was observed with participant spec discussant-1; the current spec is discussant-2"
            " — observe again", "context_conformance is failed",
            "permission_conformance was observed with participant spec discussant-1; the current spec is discussant-2"
            " — observe again"))
        later = eligibility.eligibility(manifest, "claude-code", enabled=True, today=date(2026, 10, 24),
                                        current_version="2.1.280")
        self.assertFalse(later.eligible)                                        # 30일이 지나면 다시 관측한다
        other = eligibility.eligibility(manifest, "claude-code", enabled=True, today=TODAY, current_version="2.1.281")
        self.assertFalse(other.eligible)                                        # 버전이 바뀌어도

    def test_the_validator_refuses_stored_eligibility_and_unbacked_observations(self):
        base = record()
        self.assertEqual(runtime_inventory.validate_manifest_v2(base), [])
        for mutate, words in (
                (lambda m: m["adapters"][0].update(eligible_for_run=True), "must not be stored"),
                (lambda m: m["adapters"][0].update(configured=True), "must not be stored"),
                (lambda m: m["adapters"][0]["context_conformance"].pop("evidence"), "needs a non-empty evidence"),
                (lambda m: m["adapters"][0]["installed"].pop("version"), "needs the version"),
                (lambda m: m["adapters"][0]["auth_observed"].update(auth_mode="unknown"), "known auth_mode"),
                (lambda m: m["adapters"][0].pop("permission_conformance"), "permission_conformance: status"),
                (lambda m: m["adapters"][0]["installed"].update(evidence="/home/someone/.local/bin/claude"),
                 "unredacted user path"),
                (lambda m: m["adapters"][0]["transport_observed"].pop("spec_revision"), "needs the spec_revision"),
                (lambda m: m["adapters"][0]["auth_observed"].update(observed_at="2026-13-01"), "observed_at as")):
            with self.subTest(words=words):
                broken = copy.deepcopy(base)
                mutate(broken)
                self.assertTrue(any(words in e for e in runtime_inventory.validate_manifest_v2(broken)))

    def test_the_command_line_validates_either_schema(self):
        with mock.patch("sys.stdout"):
            self.assertEqual(runtime_inventory.main(["--validate", str(WSL_V2)]), 0)
            self.assertEqual(runtime_inventory.main(["--validate", str(WSL_V2.with_name("manifest.json"))]), 0)


class ExecutorGateTests(unittest.TestCase):
    """실제 실행기는 기록 없이 만들 수 없고, 시도마다 기록을 다시 읽어 허가를 계산한다."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dml-n4-"))
        self.addCleanup(shutil.rmtree, self.root, True)

    def write(self, manifest):
        path = self.root / "manifest.v2.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_the_executor_needs_a_record_unless_it_is_an_observation_tool(self):
        with self.assertRaisesRegex(ValueError, "runtime-inventory/2"):
            CliExecutor(never=(str(self.root),))
        CliExecutor(never=(str(self.root),), unchecked=True)

    def test_the_version_is_read_from_the_installed_layout(self):
        self.assertEqual(installed_version("claude-code", "/x/.local/share/claude/versions/2.1.280"), "2.1.280")
        self.assertEqual(installed_version(
            "codex", "/x/.codex/packages/standalone/releases/0.156.1-x86_64-unknown-linux-musl/bin/codex"), "0.156.1")
        self.assertIsNone(installed_version("claude-code", "/usr/bin/claude"))

    def test_each_attempt_rereads_the_record(self):
        exe = str(self.root / "claude/versions/2.1.280")
        path = self.write(record())
        ex = CliExecutor(never=(str(self.root),), inventory=path)
        with mock.patch.object(cli_executor, "date") as fake_date:            # 시험이 실제 날짜에 기대지 않게
            fake_date.today.return_value = TODAY
            ex._check_eligible("claude-code", exe)                              # 허가
            self.write(record(context_conformance={"status": "failed", "observed_at": "2026-09-23", "evidence": "x"}))
            with self.assertRaisesRegex(adapters.AdapterError, "context_conformance is failed"):
                ex._check_eligible("claude-code", exe)                          # 기록이 바뀌면 바로 반영
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(adapters.AdapterError, "cannot read the inventory"):
                ex._check_eligible("claude-code", exe)
            fake_date.today.return_value = date(2027, 1, 1)                    # 오래된 관측은 다시 봐야 한다
            self.write(record())
            with self.assertRaisesRegex(adapters.AdapterError, "days ago"):
                ex._check_eligible("claude-code", exe)


if __name__ == "__main__":
    unittest.main()
