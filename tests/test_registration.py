"""관측 기록의 기기 등록(카드 #71, 2026-09-25 외부 검토 R06). 임시 등록 파일·가짜 machine-id만 쓴다.

다른 PC에 clone하고 CLI를 같은 판으로 설치해도, 그 기기에서 관측·등록하지 않은 기록으로는 실제 실행이 허가되지
않아야 한다. 공개 저장소의 기록은 바꾸지 않는다 — 등록은 사용자 상태 폴더에만 있다.
"""
from datetime import date
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from app import readiness, registration
from app.cli_executor import CliExecutor
from core import adapters, eligibility
from registration_support import isolate


def eligible_record(label="aux-pc-wsl", revision="claude-code@test"):
    row = {"adapter_id": "claude-code"}
    for field in eligibility.FIELDS:
        row[field] = {"status": "observed", "observed_at": date.today().isoformat(),
                      "evidence": "synthetic test evidence", "spec_revision": revision}
    row["installed"]["version"] = "9.9.9"
    row["auth_observed"].update(auth_mode="subscription_oauth", funding_mode="subscription")
    return {"schema": eligibility.SCHEMA, "host": {"label": label}, "adapters": [row]}


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.root = isolate(self)
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps(eligible_record()), encoding="utf-8")

    def test_an_unregistered_record_is_refused_with_the_way_to_register(self):
        reason = registration.problem(self.manifest)
        self.assertIn("not registered on this machine", reason)
        self.assertIn("python -m app.registration register", reason)

    def test_registering_here_allows_exactly_those_bytes_on_this_machine(self):
        registration.register(self.manifest, "aux-pc-wsl")
        self.assertIsNone(registration.problem(self.manifest))
        # 기록을 바꾸면(새 관측) 다시 등록한다.
        self.manifest.write_text(json.dumps(eligible_record(revision="claude-code@other")), encoding="utf-8")
        self.assertIn("not registered", registration.problem(self.manifest))

    def test_another_machine_or_hostname_does_not_inherit_the_registration(self):
        registration.register(self.manifest, "aux-pc-wsl")
        (self.root / "machine-id").write_text("fedcba9876543210fedcba9876543210\n", encoding="ascii")
        self.assertIn("different machine", registration.problem(self.manifest))
        (self.root / "machine-id").write_text("0123456789abcdef0123456789abcdef\n", encoding="ascii")
        with mock.patch.object(registration.socket, "gethostname", return_value="another-pc"):
            self.assertIn("different machine", registration.problem(self.manifest))
        self.assertIsNone(registration.problem(self.manifest))

    def test_a_record_from_another_host_label_is_not_registered(self):
        with self.assertRaisesRegex(ValueError, "host.label"):
            registration.register(self.manifest, "main-pc")
        self.assertFalse((self.root / "registrations.json").exists())

    def test_no_machine_id_or_a_broken_registry_is_a_refusal_not_a_pass(self):
        registration.register(self.manifest, "aux-pc-wsl")
        (self.root / "registrations.json").write_text("not json", encoding="utf-8")
        self.assertIn("cannot check", registration.problem(self.manifest))
        (self.root / "machine-id").unlink()
        self.assertIn("no /etc/machine-id", registration.problem(self.manifest))
        with self.assertRaises(ValueError):
            registration.register(self.manifest, "aux-pc-wsl")

    def test_the_registry_keeps_no_raw_machine_id_and_is_private(self):
        registration.register(self.manifest, "aux-pc-wsl")
        text = (self.root / "registrations.json").read_text(encoding="utf-8")
        self.assertNotIn("0123456789abcdef", text)
        if os.name != "nt":
            self.assertEqual((self.root / "registrations.json").stat().st_mode & 0o777, 0o600)

    def test_the_command_line(self):
        with mock.patch("sys.stdout"):
            self.assertEqual(registration.main(["status", str(self.manifest)]), 1)
            self.assertEqual(registration.main(["register", str(self.manifest), "--host-label", "main-pc"]), 1)
            self.assertEqual(registration.main(["register", str(self.manifest), "--host-label", "aux-pc-wsl"]), 0)
            self.assertEqual(registration.main(["status", str(self.manifest)]), 0)


class GateTests(unittest.TestCase):
    """준비 조회와 실행 직전 재검사가 모두 등록을 본다. 문맥 미확인 허용도 건너뛰지 않는다."""

    def setUp(self):
        self.root = isolate(self)
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps(eligible_record()), encoding="utf-8")

    def readiness(self, **kwargs):
        plan = SimpleNamespace(revision="claude-code@test", spec=SimpleNamespace(argv=("fake",)), box=object())
        with mock.patch.object(readiness.sys, "platform", "linux"), \
             mock.patch.object(readiness.CliExecutor, "plan", return_value=plan), \
             mock.patch.object(readiness, "installed_version", return_value="9.9.9"), \
             mock.patch.object(readiness.isolation, "_trusted_bwrap"), \
             mock.patch.object(readiness.isolation, "plan"), \
             mock.patch.object(readiness.isolation, "run", side_effect=AssertionError("no process")):
            return readiness.check("claude-code", "full-test-model", self.manifest, self.root / "data", **kwargs)

    def test_readiness_refuses_an_unregistered_record_even_when_context_is_allowed_unverified(self):
        for relaxed in (False, True):
            with self.subTest(allow_context_unverified=relaxed):
                result = self.readiness(allow_context_unverified=relaxed)
                self.assertFalse(result["eligible"])
                self.assertTrue(any("not registered" in r for r in result["reasons"]))
        registration.register(self.manifest, "aux-pc-wsl")
        self.assertTrue(self.readiness()["eligible"])

    def test_the_executor_refuses_before_start_when_the_record_is_not_registered_here(self):
        ex = CliExecutor(never=(str(self.root / "ledger"),), inventory=self.manifest)
        verdict = eligibility.Verdict(True, ())
        with mock.patch.object(eligibility, "eligibility", return_value=verdict), \
             mock.patch("app.cli_executor.installed_version", return_value="9.9.9"):
            with self.assertRaisesRegex(adapters.AdapterError, "not registered"):
                ex._check_eligible("claude-code", "fake", "claude-code@test")
            registration.register(self.manifest, "aux-pc-wsl")
            ex._check_eligible("claude-code", "fake", "claude-code@test")   # 이제 통과


if __name__ == "__main__":
    unittest.main()
