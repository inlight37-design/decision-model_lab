"""계획 경로의 빈틈(카드 #122, 구조 검토 R3·R4). 모델·실제 CLI를 부르지 않는다.

- R4: 없는 입력 폴더·겹치는 연결은 **예약 전에** 거절한다. 재현 `R4-plan-defers-isolation-validation`에서는 controller가
  호출 예약을 먼저 쓴 뒤 시작 전 실패로 끝났다(예약 1). 이제 실행기의 check()가 예약 직전에 격리 경로를 본다.
- R3: 계획이 쥔 실행 틀·격리 환경은 사본이다. 재현 `R3-plan-shallow-freeze`에서는 기록 사본이나 넘긴 env를 고치면
  계획이 따라 바뀌었다.
"""
import hashlib
from pathlib import Path
import sys
import unittest
from unittest import mock

from app import cli_executor, controller as c
from app.store import events
from core import adapters, contract, isolation
import test_app_controller as support
import test_model_synthesis as synthesis


class ReserveAfterIsolationCheckTests(support.Base):
    def executor(self, **kwargs):
        home = self.tmp / "home"
        home.mkdir(exist_ok=True)
        ex = cli_executor.CliExecutor(never=(), unchecked=True, home=str(home), base_env={"PATH": ""}, **kwargs)
        for patch in (mock.patch.object(cli_executor.core_env, "resolve", return_value=str(home / "versions" / "9.9.9")),
                      mock.patch.object(isolation, "participant_mounts", return_value=((), (), ())),
                      mock.patch.object(isolation, "run", side_effect=AssertionError("must not start a process"))):
            patch.start()
            self.addCleanup(patch.stop)
        return ex

    def claude(self):
        return c.ParticipantSpec("claude", "Claude Code", "anthropic", c.CLI, "claude-code", "claude-test")

    def reservations(self, rid):
        return [e for e in events(self.store, rid) if e["kind"] == "live_call_reserved"]

    def test_a_refused_isolation_check_reserves_nothing(self):
        # 재현을 그대로 옮기되(격리가 시작 전에 거절) 기대값을 바꿨다: 예약 0
        ex = self.executor()
        ctl = self.controller(ex, max_real_calls=1)
        with mock.patch.object(isolation, "plan", side_effect=isolation.IsolationError("synthetic missing input")):
            rid = ctl.create_run("q", [self.claude()], min_independent=1)
            self.assertTrue(ctl.wait_idle())
        part = self.part(ctl, rid, "claude")
        self.assertEqual((part["state"], part["status"]), (c.REJECTED, "process_failed_to_start"))
        self.assertEqual(self.reservations(rid), [])
        self.assertEqual(ctl.call_budget(), {"used": 0, "cap": 1})         # 상한 한 칸이 그대로다

    @unittest.skipUnless(sys.platform == "linux", "isolation paths are POSIX; the real check runs on Linux/WSL")
    def test_a_missing_input_folder_is_refused_before_reservation(self):
        missing = str(self.tmp / "does-not-exist")
        ctl = self.controller(self.executor(default_inputs=(missing,)), max_real_calls=1)
        rid = ctl.create_run("q", [self.claude()], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.part(ctl, rid, "claude")["status"], "process_failed_to_start")
        self.assertEqual(self.reservations(rid), [])
        refused = next(e for e in events(self.store, rid) if e["kind"] == "attempt_started")
        self.assertIn("does not exist", refused["spec"]["refused"])


class SynthesisCheckTests(support.Base):
    class Refusing(synthesis.SynthExecutor):
        def check(self, plan):
            if plan.spec.argv[1] == "synthesis":
                raise isolation.IsolationError("synthetic overlapping mount")

    def test_a_synthesis_whose_isolation_is_refused_reserves_nothing(self):
        ctl, rid = synthesis.ControllerTests.revealed(self, self.Refusing(), cap=3)
        with self.assertRaises(c.ControllerError):
            ctl.synthesize_with_model(rid, "claude-code")
        self.assertEqual(ctl.call_budget(), {"used": 2, "cap": 3})
        self.assertFalse([e for e in events(self.store, rid) if e["kind"] == "synthesis_started"])


class PlanCopyTests(unittest.TestCase):
    def spec(self):
        return adapters.ExecutionSpec("codex", ("/opt/fake/codex", "exec", "--model", "m", "-"), "question",
                                      adapters.STDIN, hashlib.sha256(b"question").hexdigest(), 8)

    def test_the_record_and_the_given_template_are_copies(self):
        env = {"LANG": "C.UTF-8"}
        box = isolation.Sandbox("/w", "/h", env=env)
        template = contract.template(self.spec(), box, home="/h")
        plan = contract.Plan(contract.REAL, self.spec(), "/w", box, "m", revision=contract.revision(template),
                             template=template)
        saved = plan.record()
        saved["template"]["argv"].append("synthetic-record-mutation")
        template["argv"].append("synthetic-caller-mutation")
        self.assertNotIn("synthetic-record-mutation", plan.template["argv"])
        self.assertNotIn("synthetic-caller-mutation", plan.template["argv"])
        self.assertEqual(contract.revision(plan.template), plan.revision)

    def test_the_sandbox_keeps_its_own_frozen_environment(self):
        env = {"LANG": "C.UTF-8"}
        box = isolation.Sandbox("/w", "/h", env=env)
        env["CODEX_HOME"] = "/synthetic/alternate-cli-state"               # 넘긴 쪽이 나중에 고쳤다
        self.assertEqual(dict(box.env), {"LANG": "C.UTF-8"})
        with self.assertRaises(TypeError):
            box.env["CODEX_HOME"] = "/synthetic"                            # 계획 쪽에서도 바꿀 수 없다


if __name__ == "__main__":
    unittest.main()
