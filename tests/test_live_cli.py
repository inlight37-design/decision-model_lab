"""Opt-in live vertical slice. Synthetic evidence is never written over PC observations."""
import copy
from dataclasses import replace
from datetime import date
import http.client
import json
from pathlib import Path
import tempfile
import threading
import sys
import unittest
from unittest import mock

from app import cli_executor, controller as c, readiness, server
from app.report import build_report
from app.store import Store, events
from core import adapters, contract, eligibility, runner
import test_app_controller as support
import test_app_cli_executor as cli_support
import test_core_eligibility as evidence
from test_core_contract import (apps_off_revision, e2_revision, k46_revision, participant_plan,
                                restricted_only_revision)
from tools import runtime_inventory


class ContextGateTests(unittest.TestCase):
    def test_only_c3_semantics_are_optional_not_the_record_structure(self):
        for status in ("unknown", "failed", "observed"):
            record = evidence.record(context_conformance={"status": status, "evidence": "test only",
                "observed_at": "2025-01-01", "spec_revision": "old-spec"})
            with self.subTest(status=status):
                self.assertFalse(evidence.verdict(record).eligible)
                self.assertTrue(evidence.verdict(record, allow_context_unverified=True).eligible)
        for field in eligibility.FIELDS:
            broken = evidence.record(**{field: {"status": "nonsense"}})
            self.assertFalse(evidence.verdict(broken, allow_context_unverified=True).eligible)
        for field in set(eligibility.FIELDS) - {"context_conformance"}:
            for value in ({"status": "unknown"}, evidence.observed(spec_revision="wrong"),
                          evidence.observed(observed_at="2020-01-01", spec_revision=evidence.SPEC)):
                self.assertFalse(evidence.verdict(evidence.record(**{field: value}),
                                                 allow_context_unverified=True).eligible, (field, value))
        paid = evidence.record(auth_observed=evidence.observed(auth_mode="api_key", funding_mode="api_billing"))
        self.assertFalse(evidence.verdict(paid, allow_context_unverified=True).eligible)
        for options in ({"enabled": False}, {"current_version": "9.9.9"}, {"spec_revision": "wrong"}):
            self.assertFalse(evidence.verdict(evidence.record(), allow_context_unverified=True, **options).eligible)

    def test_existing_k46_plan_is_reused_without_relabelling_or_expanding_legacy(self):
        record = json.loads(evidence.K46_MANIFEST.read_text(encoding="utf-8"))
        before = copy.deepcopy(record)
        observed_plan = participant_plan("codex", inputs=("/tmp/public-input",))
        self.assertEqual(k46_revision(observed_plan), "codex@8a0128d4c791")
        options = dict(enabled=True, today=date(2026, 9, 24), current_version="0.156.1",
                       spec_revision=k46_revision(observed_plan))
        self.assertFalse(eligibility.eligibility(record, "codex", **options).eligible)
        self.assertTrue(eligibility.eligibility(record, "codex", **options,
                                               allow_context_unverified=True).eligible)
        # 연결 앱 끄기를 더한 지금 계획, 자료 없음·둘 이상은 K46 기록으로 허가되지 않는다
        for spec_revision in (observed_plan[0], participant_plan("codex")[0],
                              participant_plan("codex", inputs=("/tmp/one", "/tmp/two"))[0]):
            options["spec_revision"] = spec_revision
            self.assertFalse(eligibility.eligibility(record, "codex", **options,
                                                    allow_context_unverified=True).eligible)
        self.assertEqual(before, record)
        self.assertEqual(record["adapters"][1]["context_conformance"]["status"], "failed")

    def test_the_apps_off_record_backs_only_the_plans_it_observed(self):
        """E(2026-09-24): 연결 앱을 끈 Codex 계획으로 K46을 다시 관측한 기록. 그 판과 #39가 관측한 Claude 판만
        뒷받침하고 문맥은 그대로라 strict는 거절한다. E2(2026-09-25)의 지금 계획은 이 기록으로 허가되지 않는다."""
        record = json.loads(evidence.APPS_OFF_MANIFEST.read_text(encoding="utf-8"))
        before = copy.deepcopy(record)
        self.assertEqual(runtime_inventory.validate_manifest_v2(record), [])
        codex = participant_plan("codex", inputs=("/tmp/public-input",))
        claude = participant_plan("claude-code", inputs=("/tmp/public-input",))
        plans = {"codex": (apps_off_revision(codex), "0.156.1"),
                 "claude-code": (restricted_only_revision(claude), "2.1.280")}
        self.assertEqual(plans["codex"][0], "codex@5a77e0b7dc7f")
        self.assertEqual(plans["claude-code"][0], "claude-code@126be128bed7")
        for adapter_id, (revision, version) in plans.items():
            with self.subTest(adapter=adapter_id):
                options = dict(enabled=True, today=date(2026, 9, 24), current_version=version, spec_revision=revision)
                self.assertFalse(eligibility.eligibility(record, adapter_id, **options).eligible)
                self.assertTrue(eligibility.eligibility(record, adapter_id, **options,
                                                       allow_context_unverified=True).eligible)
        # 지금(E2) 계획, 연결 앱을 켠 옛 K46 계획, 자료 없음·둘 이상은 이 기록으로 허가되지 않는다
        for adapter_id, version, revision in (
                ("codex", "0.156.1", codex[0]), ("claude-code", "2.1.280", claude[0]),
                ("codex", "0.156.1", k46_revision(codex)), ("codex", "0.156.1", participant_plan("codex")[0]),
                ("codex", "0.156.1", participant_plan("codex", inputs=("/tmp/one", "/tmp/two"))[0])):
            self.assertFalse(eligibility.eligibility(record, adapter_id, enabled=True, today=date(2026, 9, 24),
                                                    current_version=version, spec_revision=revision,
                                                    allow_context_unverified=True).eligible)
        self.assertEqual(before, record)
        self.assertEqual(record["adapters"][1]["context_conformance"]["status"], "failed")


    def test_the_e2_record_backs_exactly_the_one_input_plans_it_observed(self):
        """E2(2026-09-25): 그때 두 계획의 전송·권한·문맥을 관측한 기록. 그 계획들을 strict에서 허가하고, 자료 없음·둘 이상·
        옛 계획·다른 설치판·30일 뒤는 허가하지 않는다. 판 문자열을 고정해 계획이 바뀌면 이 기록도 다시 보게 한다.
        Codex 계획은 그 뒤 플러그인 끄기(카드 #64)로 바뀌었다 — 지금 Codex 계획은 E2로 허가되지 않고 재관측(카드 #82)을
        기다린다. Claude 계획은 그대로다."""
        record = json.loads(evidence.E2_MANIFEST.read_text(encoding="utf-8"))
        before = copy.deepcopy(record)
        self.assertEqual(runtime_inventory.validate_manifest_v2(record), [])
        codex = participant_plan("codex", inputs=("/tmp/public-input",))
        claude = participant_plan("claude-code", inputs=("/tmp/public-input",))
        self.assertEqual((e2_revision(codex), claude[0]), ("codex@bba3751a36f3", "claude-code@a35129c5a1dc"))
        today = date(2026, 9, 25)
        for adapter_id, revision, version in (("codex", e2_revision(codex), "0.156.1"),
                                              ("claude-code", claude[0], "2.1.280")):
            with self.subTest(adapter=adapter_id):
                verdict = eligibility.eligibility(record, adapter_id, enabled=True, today=today,
                                                  current_version=version, spec_revision=revision)
                self.assertTrue(verdict.eligible, verdict.reasons)
                for options in ({"current_version": version + ".1"}, {"today": date(2026, 10, 26)}):
                    self.assertFalse(eligibility.eligibility(record, adapter_id, enabled=True, **{
                        "today": today, "current_version": version, "spec_revision": revision, **options}).eligible)
        for adapter_id, version, revision in (
                ("codex", "0.156.1", codex[0]),   # 지금 계획(플러그인 끄기)은 아직 관측하지 않았다
                ("codex", "0.156.1", participant_plan("codex")[0]),
                ("codex", "0.156.1", participant_plan("codex", inputs=("/tmp/one", "/tmp/two"))[0]),
                ("codex", "0.156.1", apps_off_revision(codex)), ("codex", "0.156.1", k46_revision(codex)),
                ("claude-code", "2.1.280", participant_plan("claude-code")[0]),
                ("claude-code", "2.1.280", restricted_only_revision(claude))):
            self.assertFalse(eligibility.eligibility(record, adapter_id, enabled=True, today=today,
                                                    current_version=version, spec_revision=revision,
                                                    allow_context_unverified=True).eligible, (adapter_id, revision))
        self.assertEqual(before, record)
        self.assertEqual([row["context_conformance"]["status"] for row in record["adapters"][:2]],
                         ["observed", "observed"])


class UnverifiedSynthetic(support.SyntheticExecutor):
    """Pretends to be live only to exercise classification and reservations; no process/model."""
    kind = contract.REAL
    allow_context_unverified = True

    def plan(self, *args, **kwargs):
        return replace(super().plan(*args, **kwargs), kind=contract.REAL, context_unverified=True)


class PersistedPolicyTests(support.Base):
    def test_unverified_never_fills_strict_quorum_and_survives_restart_and_report(self):
        ex = UnverifiedSynthetic()
        ctl = self.controller(ex, max_real_calls=1)
        with self.assertRaises(c.ControllerError):
            ctl.create_run("q", [support.cli("a")], min_independent=1)
        self.assertEqual(ex.started, [])
        rid = ctl.create_run("q", [support.cli("a")], min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)
        self.assertTrue(ctl.wait_idle())
        for current in (ctl, self.controller(support.SyntheticExecutor(), max_real_calls=1)):
            view = self.run_view(current, rid)
            self.assertEqual(view["phase"], "revealed")
            self.assertEqual((view["quorum"]["confirmed"], view["quorum"]["unverified"]), (0, 1))
            self.assertEqual(view["participants"][0]["independence"], "unverified")
            self.assertNotIn("독립 정족수 충족", view["quorum"]["label"])
            report = build_report(current.view(rid), rid)
            self.assertEqual(report["participants"][0]["independence"], "unverified")
            self.assertEqual(current.call_budget(), {"used": 1, "cap": 1})
        started = next(e for e in events(self.store, rid) if e["kind"] == "attempt_started")
        self.assertTrue(started["spec"]["context_unverified"])

    def test_a_queued_strict_row_cannot_run_under_relaxed_policy_after_restart(self):
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        rid = ctl.create_run("q", [support.cli("a")], min_independent=1)
        ex = UnverifiedSynthetic()
        again = self.controller(ex, max_real_calls=1)
        again.resume()
        self.assertTrue(again.wait_idle())
        self.assertEqual(ex.started, [])
        self.assertEqual(self.part(again, rid, "a")["state"], c.REJECTED)
        self.assertEqual(again.call_budget()["used"], 0)

    def test_one_reservation_caps_parallel_new_runs_and_restart_without_refund(self):
        ex = UnverifiedSynthetic(outcomes={"a": "fail"})
        ctl = self.controller(ex, max_real_calls=1)
        for pid in ("a", "b"):
            ctl.create_run("q", [support.cli(pid)], min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(ex.started, ["a"])
        self.assertEqual(ctl.call_budget(), {"used": 1, "cap": 1})
        other = UnverifiedSynthetic()
        again = self.controller(other, max_real_calls=1)
        again.create_run("q", [support.cli("c")], min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)
        self.assertTrue(again.wait_idle())
        self.assertEqual(other.started, [])
        self.assertEqual(again.call_budget()["used"], 1)


@unittest.skipUnless(sys.platform == "linux", "installs a Linux fake CLI through a symlink; no bubblewrap needed")
class ExecutorPolicyTests(cli_support.Base):
    def test_policy_and_permission_revocation_still_refuse_before_process_start(self):
        cli_support.install(self.home, "codex")
        path = self.root / "inventory.json"
        spec = cli_support.codex()
        unchecked = self.executor()
        plan = unchecked.plan(spec, "q", str(self.root / "work"))
        row = {"adapter_id": "codex"}
        for field in eligibility.FIELDS:
            row[field] = {"status": "observed", "observed_at": date.today().isoformat(),
                          "evidence": "synthetic only", "spec_revision": plan.revision}
        row["installed"]["version"] = "9.9.9"
        row["auth_observed"].update(auth_mode="chatgpt_login", funding_mode="subscription")
        row["context_conformance"]["status"] = "failed"
        def save():
            path.write_text(json.dumps({"schema": eligibility.SCHEMA, "adapters": [row]}), encoding="utf-8")
        save()
        ex = self.executor(inventory=path, allow_context_unverified=True)
        relaxed = ex.plan(spec, "q", str(self.root / "work"))
        self.assertTrue(relaxed.context_unverified)
        with mock.patch.object(cli_executor.isolation, "run", side_effect=AssertionError("must not start")):
            result, _ = ex.run(plan, 1)  # old policy cannot be reinterpreted
            self.assertEqual(result.state, runner.FAILED_TO_START)
            row["permission_conformance"]["status"] = "failed"
            save()
            result, _ = ex.run(relaxed, 1)
            self.assertEqual(result.state, runner.FAILED_TO_START)

    def test_configured_input_is_the_exact_explicit_input_plan(self):
        cli_support.install(self.home, "codex")
        source = self.root / "public"
        source.mkdir()
        explicit = self.executor().plan(cli_support.codex(), "q", str(self.root), inputs=(str(source),))
        configured = self.executor(default_inputs=(str(source),)).plan(cli_support.codex(), "q", str(self.root))
        self.assertEqual(explicit.revision, configured.revision)
        self.assertEqual(explicit.spec, configured.spec)
        self.assertEqual(explicit.box, configured.box)


class ServerLiveTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "linux", "live server is Linux-only; no model/process in this test")
    def test_live_startup_is_explicit_and_options_do_not_offer_mock_fallback_or_mutable_models(self):
        with tempfile.TemporaryDirectory() as root:
            srv, token, ctl = server.serve(Path(root), 0, live_cli="codex", inventory=Path(root)/"missing.json",
                                          model="full-explicit-model", call_budget=1, allow_context_unverified=True)
            self.addCleanup(ctl.store.close)
            self.addCleanup(srv.server_close)
            self.assertIsInstance(ctl.executor, cli_executor.CliExecutor)
            self.assertIsNotNone(ctl.executor.inventory)
            worker = threading.Thread(target=srv.serve_forever, daemon=True)
            worker.start()
            self.addCleanup(srv.shutdown)
            connection = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=2)
            self.addCleanup(connection.close)
            headers = {"Authorization": "Bearer " + token}
            connection.request("GET", "/api/options", headers=headers)
            options = json.loads(connection.getresponse().read())
            self.assertTrue(options["live"])
            self.assertTrue(options["context_unverified"])
            self.assertEqual(options["behaviors"], ["ok"])
            native = [p for p in options["participants"] if p["transport"] == c.CLI]
            self.assertEqual([(p["pid"], p["model"]) for p in native], [("codex", "full-explicit-model")])
            for item in ({"pid": "claude"}, {"pid": "codex", "behavior": "hang"}):
                headers["Content-Type"] = "application/json"
                connection.request("POST", "/api/runs", json.dumps({"question": "q", "participants": [item],
                    "min_independent": 1, "quorum_policy": c.INCLUDE_UNVERIFIED}), headers)
                response = connection.getresponse()
                response.read()
                self.assertEqual(response.status, 400)
            self.assertEqual(ctl.view()["runs"], [])

    def test_budget_and_real_options_cannot_be_implicit(self):
        with tempfile.TemporaryDirectory() as root:
            for options in ({"inventory": Path("i")}, {"allow_context_unverified": True},
                            {"live_cli": "codex", "inventory": Path("i"), "model": "m"},
                            {"live_cli": "codex", "inventory": Path("i"), "model": "m", "call_budget": 0}):
                with self.subTest(options=options), self.assertRaises(ValueError):
                    server.serve(Path(root), 0, **options)


@unittest.skipUnless(cli_support.bwrap_usable(), "requires usable Linux bubblewrap")
class IsolatedLiveTests(cli_support.Base):
    def test_real_executor_fake_binary_to_sealed_draft_and_unverified_report(self):
        cli_support.install(self.home, "codex")
        source = self.root / "public"
        source.mkdir()
        plan = self.executor(default_inputs=(str(source),)).plan(cli_support.codex(), "q", str(self.root/"work"))
        row = {"adapter_id": "codex"}
        for field in eligibility.FIELDS:
            row[field] = {"status": "observed", "observed_at": date.today().isoformat(),
                          "evidence": "synthetic test, not a real model", "spec_revision": plan.revision}
        row["installed"]["version"] = "9.9.9"
        row["auth_observed"].update(auth_mode="chatgpt_login", funding_mode="subscription")
        row["context_conformance"]["status"] = "failed"
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"schema": eligibility.SCHEMA, "adapters": [row]}), encoding="utf-8")
        ex = self.executor(inventory=manifest, default_inputs=(str(source),), allow_context_unverified=True)
        ctl = self.controller(ex, max_real_calls=1)
        rid = ctl.create_run("nonsecret synthetic question", [cli_support.codex()], min_independent=1,
                             quorum_policy=c.INCLUDE_UNVERIFIED)
        self.assertTrue(ctl.wait_idle(10))
        view = self.run_view(ctl, rid)
        self.assertEqual(view["participants"][0]["state"], c.ACCEPTED, view)
        self.assertEqual((view["quorum"]["confirmed"], view["quorum"]["unverified"]), (0, 1))
        self.assertEqual(view["phase"], "revealed")
        self.assertEqual(ctl.call_budget()["used"], 1)


if __name__ == "__main__":
    unittest.main()
