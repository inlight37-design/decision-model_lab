"""Readiness is a read-only query, including when all synthetic evidence permits execution."""
from contextlib import redirect_stdout
from datetime import date
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from app import readiness, server
from core import eligibility


class ReadinessTests(unittest.TestCase):
    def test_checks_current_revision_without_starting_any_process(self):
        revision = "claude-code@test"
        row = {"adapter_id": "claude-code"}
        for field in eligibility.FIELDS:
            row[field] = {"status": "observed", "observed_at": date.today().isoformat(),
                          "evidence": "synthetic test evidence", "spec_revision": revision}
        row["installed"]["version"] = "9.9.9"
        row["auth_observed"].update(auth_mode="subscription_oauth", funding_mode="subscription")
        record = {"schema": eligibility.SCHEMA, "adapters": [row]}
        plan = SimpleNamespace(revision=revision, spec=SimpleNamespace(argv=("fake",)), box=object())
        with tempfile.TemporaryDirectory() as root:
            manifest, data = Path(root, "manifest.json"), Path(root, "unused-journal")
            manifest.write_text(json.dumps(record), encoding="utf-8")
            with mock.patch.object(readiness.sys, "platform", "linux"), \
                 mock.patch.object(readiness.CliExecutor, "plan", return_value=plan), \
                 mock.patch.object(readiness, "installed_version", return_value="9.9.9"), \
                 mock.patch.object(readiness.isolation, "_trusted_bwrap"), \
                 mock.patch.object(readiness.isolation, "plan"), \
                 mock.patch.object(readiness.isolation, "run", side_effect=AssertionError("no process")):
                result = readiness.check("claude-code", "full-test-model", manifest, data)
                self.assertTrue(result["eligible"], result)
                self.assertEqual(result["revision"], revision)
                self.assertEqual(result["model_calls"], 0)
                row["context_conformance"]["status"] = "failed"
                manifest.write_text(json.dumps(record), encoding="utf-8")
                refused = readiness.check("claude-code", "full-test-model", manifest, data)
                self.assertFalse(refused["eligible"])
                self.assertIn("context_conformance is failed", refused["reasons"])
            self.assertFalse(data.exists())

    def test_missing_isolation_binary_or_unwritable_scratch_is_a_json_refusal(self):
        with mock.patch.object(readiness.sys, "platform", "linux"), \
             mock.patch.object(readiness.eligibility, "load", return_value={}), \
             mock.patch.object(readiness.isolation, "run", side_effect=AssertionError("no process")):
            for failure in (readiness.isolation.IsolationError("untrusted bwrap"), OSError("scratch denied")):
                with self.subTest(failure=type(failure).__name__), \
                     mock.patch.object(readiness.isolation, "_trusted_bwrap", side_effect=failure):
                    result = readiness.check("codex", "full-test-model", Path("record"), Path("data"))
                    self.assertFalse(result["eligible"])
                    json.dumps(result)

    def test_readiness_cli_exits_without_creating_server_or_ledger(self):
        with mock.patch("sys.argv", ["server", "--check-cli", "codex", "--inventory", "absent.json",
                                     "--model", "full-test-model"]), \
             mock.patch.object(readiness, "check", return_value={"eligible": False, "model_calls": 0}), \
             mock.patch.object(server, "serve", side_effect=AssertionError("must not serve")), \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(server.main(), server.EXIT_NOT_ELIGIBLE)
            self.assertEqual(json.loads(output.getvalue())["model_calls"], 0)

    def test_refusal_permission_and_usage_errors_have_distinct_exit_codes(self):
        """스크립트가 종료 코드만으로 거절과 인자 오류를 가른다(병합 검증 N3). 실제 모드의 시작 전 거절도 같은 코드다."""
        check_cli = ["server", "--check-cli", "codex", "--inventory", "absent.json", "--model", "full-test-model"]
        live_cli = ["server", "--live-cli", "codex", "--inventory", "absent.json", "--model", "full-test-model",
                    "--call-budget", "1", "--data-dir", "separate-ledger"]
        for argv, eligible, expected in ((check_cli, True, 0), (check_cli, False, 3), (live_cli, False, 3)):
            with self.subTest(mode=argv[1], eligible=eligible), mock.patch("sys.argv", argv), \
                 mock.patch.object(readiness, "check", return_value={"eligible": eligible, "model_calls": 0}), \
                 mock.patch.object(server, "serve", side_effect=AssertionError("must not serve")), \
                 redirect_stdout(io.StringIO()):
                self.assertEqual(server.main(), expected)
        with mock.patch("sys.argv", ["server", "--check-cli", "codex", "--inventory", "absent.json"]), \
             mock.patch.object(readiness, "check", side_effect=AssertionError("must not check")), \
             mock.patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit) as usage:
            server.main()
        self.assertEqual(usage.exception.code, 2)
        self.assertNotEqual(usage.exception.code, server.EXIT_NOT_ELIGIBLE)

    def test_real_options_cannot_silently_start_mock_server(self):
        with mock.patch("sys.argv", ["server", "--inventory", "record.json", "--model", "test"]), \
             mock.patch.object(server, "serve", side_effect=AssertionError("must not serve")), \
             mock.patch("sys.stderr", io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                server.main()
            self.assertEqual(exc.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
