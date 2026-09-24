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
from test_core_contract import k46_revision, participant_plan, participant_revision
from tools import runtime_inventory

ROOT = Path(__file__).resolve().parents[1]
WSL_V2 = ROOT / "docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.v2.json"
TODAY = date(2026, 9, 23)


def observed(**extra):
    return {"status": "observed", "observed_at": "2026-09-23", "evidence": "synthetic", **extra}


SPEC = participant_revision("claude-code")   # 지금 실행할 계획의 판(core.contract)
K46_MANIFEST = ROOT / "docs/experiments/w2-isolation/2026-09-24-k46-confirmation/manifest.v2.json"


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
    kwargs.setdefault("spec_revision", SPEC)
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
        # 계획 없이 계산하면 판이 맞는 관측이 없다
        self.assertEqual(len(verdict(record(), spec_revision=None).reasons), len(eligibility.SPEC_BOUND))

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
    def test_the_committed_records_back_no_participant_plan_yet(self):
        """순서 5 뒤(core.contract): 관측은 그것을 본 계획의 판에만 묶인다.

        Claude(2단계 b1)는 다섯 칸이 모두 관측됐지만 stream-json·Read 도구·공통 자료로 본 것이라 controller 계획의
        근거가 아니다. Codex는 문맥이 failed이고(K38·K44), 2단계의 전송·권한은 옛 argv(--sandbox read-only)였다.
        K46 기록의 discussant-2는 K46이 돈 계획(공통 자료 하나)만 뒷받침한다.
        """
        def reasons(manifest, adapter_id, version, revision):
            return eligibility.eligibility(manifest, adapter_id, enabled=True, today=date(2026, 9, 24),
                                           current_version=version,
                                           spec_revision=revision).reasons

        def respec(old, new):
            return tuple(f"{field} was observed with participant spec {old}; the current spec is {new} — observe again"
                         for field in ("transport_observed", "permission_conformance"))

        stage2 = json.loads(WSL_V2.read_text(encoding="utf-8"))
        k46 = json.loads(K46_MANIFEST.read_text(encoding="utf-8"))
        for manifest in (stage2, k46):
            self.assertEqual(runtime_inventory.validate_manifest_v2(manifest), [])
        claude = participant_revision("claude-code")
        self.assertEqual(reasons(stage2, "claude-code", "2.1.280", claude), (
            f"transport_observed was observed with participant spec discussant-1; the current spec is {claude}"
            " — observe again",
            f"context_conformance was observed with participant spec discussant-1; the current spec is {claude}"
            " — observe again",
            f"permission_conformance was observed with participant spec discussant-1; the current spec is {claude}"
            " — observe again"))
        with_materials, plain = (participant_revision("codex", inputs=("/tmp/in",)), participant_revision("codex"))
        self.assertEqual(reasons(stage2, "codex", "0.156.1", plain),
                         respec("discussant-1", plain)[:1] + ("context_conformance is failed",)
                         + respec("discussant-1", plain)[1:])
        k46_plan = k46_revision(participant_plan("codex", inputs=("/tmp/in",)))
        self.assertEqual(reasons(k46, "codex", "0.156.1", k46_plan), ("context_conformance is failed",))
        # 연결 앱 끄기를 더한 지금 계획은 K46 기록이 덮지 않는다 — 전송·권한을 다시 관측한다
        self.assertEqual(reasons(k46, "codex", "0.156.1", with_materials),
                         respec("discussant-2", with_materials)[:1] + ("context_conformance is failed",)
                         + respec("discussant-2", with_materials)[1:])
        self.assertEqual(reasons(k46, "codex", "0.156.1", plain),
                         respec("discussant-2", plain)[:1] + ("context_conformance is failed",)
                         + respec("discussant-2", plain)[1:])
        # 판이 맞는 기록이라도 30일이 지나거나 버전이 바뀌면 다시 관측한다
        fresh = record(installed=observed(version="2.1.280"))
        self.assertTrue(verdict(fresh).eligible)
        self.assertFalse(verdict(fresh, today=date(2026, 10, 24)).eligible)
        self.assertFalse(verdict(fresh, current_version="2.1.281").eligible)

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
            ex._check_eligible("claude-code", exe, SPEC)                              # 허가
            self.write(record(context_conformance={"status": "failed", "observed_at": "2026-09-23", "evidence": "x"}))
            with self.assertRaisesRegex(adapters.AdapterError, "context_conformance is failed"):
                ex._check_eligible("claude-code", exe, SPEC)                          # 기록이 바뀌면 바로 반영
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(adapters.AdapterError, "cannot read the inventory"):
                ex._check_eligible("claude-code", exe, SPEC)
            fake_date.today.return_value = date(2027, 1, 1)                    # 오래된 관측은 다시 봐야 한다
            self.write(record())
            with self.assertRaisesRegex(adapters.AdapterError, "days ago"):
                ex._check_eligible("claude-code", exe, SPEC)


if __name__ == "__main__":
    unittest.main()
