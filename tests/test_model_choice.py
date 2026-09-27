"""역할판에서 모델 고르기(카드 #119, 역할판 B). 모델·실제 CLI를 부르지 않는다.

- 허용 목록: 모델마다 과금 경로와 근거를 적고, 구독 포함(included)만 고를 수 있다. 공식 문서상 추가 크레딧으로
  청구되는 모델(Fable)은 설정과 상관없이 막는다(검토 근거 O14). 목록 밖·막힌 모델은 원장을 쓰기 전에 거절한다.
- 고른 모델이 확인 manifest·원장·계획 기록·argv·결과의 요청/보고 대조까지 그대로 간다. 조용한 대체 없음.
- AH-08: 허가 판단은 관측 기록을 한 번 읽은 바이트로 적격성과 등록을 함께 본다.
"""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from app import cli_executor, controller as c, launch, readiness, registration, server
from app.live_config import CREDITS, INCLUDED, UNCONFIRMED, ModelChoice, Provider, load
from app.store import events
from core import adapters, eligibility, isolation
import test_app_controller as support
from test_app_integrity import HttpServerCase


class AllowlistTests(unittest.TestCase):
    def provider(self, model, *choices):
        return Provider("claude-code", model, Path("inventory.json"), 1, choices=tuple(choices))

    def test_only_included_models_are_usable_and_fable_is_always_credits(self):
        p = self.provider("claude-sonnet-5", ModelChoice("claude-sonnet-5", INCLUDED, "관측"),
                          ModelChoice("claude-opus-5-5", UNCONFIRMED, "미확인"),
                          ModelChoice("claude-fable-5-1", INCLUDED, "설정이 포함이라고 적어도"))
        self.assertEqual([(ch.model, ch.usable) for ch in p.choices],
                         [("claude-sonnet-5", True), ("claude-opus-5-5", False), ("claude-fable-5-1", False)])
        self.assertEqual(p.choice("claude-fable-5-1").funding, CREDITS)            # 문서가 설정보다 우선한다
        self.assertIn("usage credits", p.choice("claude-fable-5-1").basis)

    def test_an_old_single_model_config_offers_just_that_model(self):
        p = Provider("codex", "gpt-6-luna", Path("inventory.json"), 1)
        self.assertEqual([(ch.model, ch.funding) for ch in p.choices], [("gpt-6-luna", INCLUDED)])

    def test_a_blocked_or_repeated_default_is_refused_at_startup(self):
        for model, choices in (("claude-opus-5-5", (ModelChoice("claude-opus-5-5", UNCONFIRMED, "미확인"),)),
                               ("claude-fable-5-1", ()),
                               ("claude-sonnet-5", (ModelChoice("claude-sonnet-5", INCLUDED, "a"),
                                                    ModelChoice("claude-sonnet-5", INCLUDED, "b")))):
            with self.subTest(model=model), self.assertRaises(ValueError):
                self.provider(model, *choices)
        for bad in (("", INCLUDED, "x"), ("m", "free", "x"), ("m", INCLUDED, " "), ("m m", INCLUDED, "x")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ModelChoice(*bad)

    def test_the_live_config_file_takes_an_explicit_models_list(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "live.json"
            row = {"adapter_id": "codex", "model": "gpt-6-luna", "inventory": "i.json", "call_budget": 1,
                   "models": [{"model": "gpt-6-luna", "funding": "included", "basis": "관측"},
                              {"model": "gpt-6-astra", "funding": "unconfirmed", "basis": "미확인"}]}
            path.write_text(json.dumps({"providers": [row]}), encoding="utf-8")
            (provider,) = load(path)
            self.assertEqual([ch.model for ch in provider.choices if ch.usable], ["gpt-6-luna"])
            for broken in ({"model": "gpt-6-astra"}, {"model": "x", "funding": "included", "basis": "y", "extra": 1}):
                with self.subTest(broken=broken), self.assertRaises((ValueError, TypeError)):
                    path.write_text(json.dumps({"providers": [{**row, "models": [broken]}]}), encoding="utf-8")
                    load(path)

    def test_the_desktop_launcher_list_keeps_the_observed_defaults_usable(self):
        for adapter, model in launch.MODELS.items():
            p = Provider(adapter, model, Path("inventory.json"), 1,
                         choices=tuple(ModelChoice(*item) for item in launch.MODEL_CHOICES[adapter]))
            self.assertTrue(p.choice(model).usable)
            for choice in p.choices:
                self.assertTrue(choice.basis.strip())
                if "fable" in choice.model:
                    self.assertEqual(choice.funding, CREDITS)


class ChosenModelsTests(unittest.TestCase):
    roster = server.PARTICIPANTS
    choices = server.MOCK_MODEL_CHOICES

    def test_a_choice_replaces_only_that_participant_in_a_copy(self):
        chosen = server.chosen_models(self.roster, self.choices, {"codex": "mock-codex-large"})
        self.assertEqual(chosen["codex"].model, "mock-codex-large")
        self.assertEqual(chosen["claude"].model, "mock-claude")
        self.assertEqual(self.roster["codex"].model, "mock-codex")                 # 서버 명단은 그대로다
        self.assertIs(server.chosen_models(self.roster, self.choices, None), self.roster)

    def test_off_list_blocked_manual_and_malformed_choices_are_refused(self):
        for requested in ({"codex": "gpt-anything"}, {"codex": "mock-codex-unconfirmed"},
                          {"claude": "mock-claude-credits"}, {"chatgpt-app": "mock-codex"},
                          {"nobody": "mock-codex"}, ["codex"], "mock-codex"):
            with self.subTest(requested=requested), self.assertRaises(c.ControllerError):
                server.chosen_models(self.roster, self.choices, requested)


def board(*isolated, orchestrator=()):
    return {"supervisor": [], "orchestrator": list(orchestrator), "isolated": list(isolated), "general": [],
            "input_mode": "original"}


class ModelChoiceHttpTests(HttpServerCase):
    def call(self, path, body=None):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        self.addCleanup(conn.close)
        headers = {"Authorization": f"Bearer {self.token}"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        conn.request("POST" if body is not None else "GET", path, json.dumps(body) if body is not None else None, headers)
        reply = conn.getresponse()
        return reply.status, json.loads(reply.read())

    def body(self, models):
        return {"question": "모델 고르기", "participants": [{"pid": "codex"}], "min_independent": 1,
                "role_board": board("codex", orchestrator=("claude",)), "task_title": "B", "models": models}

    def test_options_list_the_choices_and_the_choice_is_fixed_into_the_confirmed_input(self):
        status, options = self.call("/api/options")
        self.assertEqual(status, 200)
        self.assertEqual([(m["model"], m["usable"]) for m in options["model_choices"]["codex"]],
                         [("mock-codex", True), ("mock-codex-large", True), ("mock-codex-unconfirmed", False)])
        self.assertNotIn("chatgpt-app", options["model_choices"])
        status, first = self.call("/api/runs/preview", self.body({"codex": "mock-codex-large", "claude": "mock-claude-large"}))
        self.assertEqual(status, 200)
        self.assertEqual(first["role_config"]["isolated"][0]["model"], "mock-codex-large")
        self.assertEqual(first["role_config"]["orchestrator"]["model"], "mock-claude-large")   # 합성자도 같은 사본
        _, other = self.call("/api/runs/preview", self.body({"codex": "mock-codex"}))
        self.assertNotEqual(first["confirmation"], other["confirmation"])       # 확인한 입력이 모델을 덮는다
        status, _ = self.call("/api/runs", {**self.body({"codex": "mock-codex"}), "run_id": first["run_id"],
                                            "confirmation": first["confirmation"]})
        self.assertEqual(status, 400)                                            # 확인 뒤 모델을 바꾸면 시작하지 않는다
        self.assertEqual(self.ctl.view()["runs"], [])

    def test_blocked_or_unknown_models_create_nothing(self):
        for models in ({"codex": "mock-codex-unconfirmed"}, {"codex": "gpt-anything"}, {"claude": "mock-claude-credits"}):
            for path in ("/api/runs/preview", "/api/runs"):
                with self.subTest(models=models, path=path):
                    status, reply = self.call(path, self.body(models))
                    self.assertEqual(status, 400)
                    self.assertTrue(reply["error"])
        self.assertEqual(self.ctl.view()["runs"], [])
        self.assertEqual(self.ctl.view()["tasks"], [])


class ChosenModelRunTests(support.Base):
    def test_the_chosen_model_is_requested_recorded_and_checked_against_the_report(self):
        # 실제 실행 경로(모의 CLI)로 돈다: 가짜 CLI가 고른 이름을 보고하므로 요청=보고로 받는다.
        ctl = self.controller(c.MockExecutor(never=(str(self.tmp / "store"),)), timeout=30)
        roster = server.chosen_models(server.PARTICIPANTS, server.MOCK_MODEL_CHOICES, {"claude": "mock-claude-large"})
        rid = ctl.create_run("q", [roster["claude"]], min_independent=1)
        self.assertTrue(ctl.wait_idle(support.SLOW_RUNNER_TIMEOUT))
        part = self.part(ctl, rid, "claude")
        if part["state"] == c.UNKNOWN:
            self.skipTest("this platform cannot confirm the mock CLI's process tree (Linux without bubblewrap)")
        self.assertEqual(part["state"], c.ACCEPTED)
        self.assertEqual((part["result"]["requested_model"], part["result"]["reported_models"], part["result"]["model_match"]),
                         ("mock-claude-large", ["mock-claude-large"], True))
        started = next(e for e in events(self.store, rid) if e["kind"] == "attempt_started")
        self.assertEqual(started["spec"]["model"], "mock-claude-large")
        stored = json.loads(self.store.row("SELECT spec FROM participants WHERE run_id = ?", rid)["spec"])
        self.assertEqual(stored["model"], "mock-claude-large")


class PlanArgvTests(unittest.TestCase):
    def test_the_real_plan_requests_exactly_the_chosen_model(self):
        # 모델은 판(revision)의 자리표시(<model>)라서 모델만 바꾸면 재관측이 필요 없다. 대신 argv·계획 기록이 같아야 한다.
        with tempfile.TemporaryDirectory() as root:
            temp = Path(root)
            ex = cli_executor.CliExecutor(never=(), unchecked=True, home=str(temp), base_env={"PATH": ""})
            plans = {}
            with mock.patch.object(cli_executor.core_env, "resolve", return_value=str(temp / "versions" / "9.9.9")), \
                    mock.patch.object(isolation, "participant_mounts", return_value=((), (), ())):
                for model in ("claude-sonnet-5", "claude-other-7"):
                    plans[model] = ex.plan(SimpleNamespace(adapter_id="claude-code", model=model, context_unverified=False),
                                           "question", str(temp))
            for model, plan in plans.items():
                argv = list(plan.spec.argv)
                self.assertEqual(argv[argv.index("--model") + 1], model)
                self.assertEqual((plan.model, plan.record()["model"]), (model, model))
            self.assertEqual(plans["claude-sonnet-5"].revision, plans["claude-other-7"].revision)


class ManifestSnapshotTests(unittest.TestCase):
    """AH-08 재현(구조 검토 core-probe.py R2)을 올바른 기대값으로. 적격성 판단 직후 기록 파일이 다른 판으로 바뀐다."""

    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="dml-ah08-"))
        self.addCleanup(shutil.rmtree, self.temp, True)
        seen = {"status": "observed", "observed_at": date.today().isoformat(), "evidence": "synthetic"}
        observed = {**seen, "spec_revision": "claude-code@synthetic"}
        row = {"adapter_id": "claude-code", "installed": {**seen, "version": "9.9.9"},
               "auth_observed": {**seen, "auth_mode": "subscription_oauth", "funding_mode": "subscription"},
               **{name: dict(observed) for name in eligibility.SPEC_BOUND}}
        eligible = {"schema": eligibility.SCHEMA, "adapters": [row]}
        invalid = copy.deepcopy(eligible)
        invalid["adapters"][0]["permission_conformance"] = {"status": "unknown"}
        self.a, self.b = json.dumps(eligible).encode(), json.dumps(invalid).encode()   # a: 적격·미등록, b: 부적격·등록
        self.manifest, registry = self.temp / "manifest.json", self.temp / "registry.json"
        self.manifest.write_bytes(self.a)
        registry.write_text(json.dumps({"schema": registration.SCHEMA, "entries": [
            {"manifest_sha256": hashlib.sha256(self.b).hexdigest(), "fingerprint": "synthetic-machine"}]}), encoding="utf-8")
        for patch in (mock.patch.object(registration, "fingerprint", return_value="synthetic-machine"),
                      mock.patch.object(registration, "registry_path", return_value=registry)):
            patch.start()
            self.addCleanup(patch.stop)
        original = eligibility.eligibility

        def swap_after_verdict(*args, **kwargs):
            result = original(*args, **kwargs)
            self.manifest.write_bytes(self.b)
            return result
        swap = mock.patch.object(eligibility, "eligibility", side_effect=swap_after_verdict)
        swap.start()
        self.addCleanup(swap.stop)

    def test_the_executor_checks_one_snapshot(self):
        executor = cli_executor.CliExecutor(never=(), inventory=self.manifest, home=str(self.temp), base_env={"PATH": ""})
        with self.assertRaises(adapters.AdapterError) as refused:
            executor._check_eligible("claude-code", str(self.temp / "versions" / "9.9.9"), "claude-code@synthetic")
        self.assertIn("not registered", str(refused.exception))                  # 적격성을 본 그 판(a)은 미등록이다

    @unittest.skipUnless(sys.platform == "linux", "readiness is Linux-only")
    def test_readiness_checks_one_snapshot(self):
        with mock.patch.object(readiness, "installed_version", return_value="9.9.9"), \
                mock.patch.object(readiness.isolation, "_trusted_bwrap"), \
                mock.patch.object(readiness.isolation, "plan"), \
                mock.patch.object(cli_executor.core_env, "resolve", return_value=str(self.temp / "versions" / "9.9.9")), \
                mock.patch.object(isolation, "participant_mounts", return_value=((), (), ())):
            result = readiness.check("claude-code", "claude-sonnet-5", self.manifest, self.temp / "ledger")
        self.assertFalse(result["eligible"])


if __name__ == "__main__":
    unittest.main()
