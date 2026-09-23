"""tools/w2/codex_sandbox.py·codex_profile.py 검사. 실제 Codex는 부르지 않는다 — 넘기는 권한 profile 인자의 모양과
네트워크 없는 exec 진단의 격리 인자만 본다."""
import os
import sys
import tomllib
import unittest
from unittest import mock

from tools.w2 import codex_profile, codex_sandbox, observe


class DenyProfileTests(unittest.TestCase):
    def test_the_profile_is_valid_toml_that_denies_only_the_target_on_top_of_read_only(self):
        args = codex_sandbox.deny_profile("/home/u", ".codex/auth.json")
        self.assertEqual((args[0], args[2:]), ("-c", ["-P", "dml-deny"]))
        key, value = args[1].split("=", 1)
        self.assertEqual(key, "permissions.dml-deny")
        self.assertEqual(tomllib.loads(f"profile = {value}")["profile"],
                         {"extends": ":read-only", "filesystem": {"/home/u/.codex/auth.json": "deny"}})

    def test_the_auth_probe_prints_exit_codes_not_the_file(self):
        self.assertIn("test -r", codex_sandbox.AUTH)
        self.assertNotIn("cat ", codex_sandbox.AUTH)
        self.assertEqual(codex_sandbox._value(["auth_readable_rc=1", "net=PermissionError"], "net"), "PermissionError")


class ProfileDiagnosticTests(unittest.TestCase):
    def test_the_exec_check_runs_like_isolation_run_without_the_shared_network(self):
        """네트워크 namespace를 새로 만들어(loopback만) exec가 모델에 닿지 못하게 한다. 나머지 격리 인자는 그대로다."""
        planned = [sys.executable, "--unshare-all", "--share-net", "--die-with-parent", "--", "/x"]
        seen = {}

        def execute(args, **kwargs):
            seen.update(args=args, **kwargs)
            return "result"

        with mock.patch.object(codex_profile.isolation, "plan", return_value=(list(planned), {"HOME": "/h"})), \
                mock.patch.object(codex_profile.isolation, "_trusted_bwrap") as trusted, \
                mock.patch.object(codex_profile.runner, "_execute", side_effect=execute):
            box = mock.Mock(work_dir=os.path.dirname(os.path.abspath(__file__)))
            self.assertEqual(codex_profile.offline(["/x"], box, "Q", timeout=5), "result")
        self.assertEqual(list(seen["args"]), [a for a in planned if a != "--share-net"])
        self.assertTrue(seen["pid_namespace"])
        trusted.assert_called_once()

    def test_the_login_file_check_prints_exit_codes_only(self):
        self.assertIn('cat "$HOME/.codex/auth.json" >/dev/null 2>&1; echo auth_open_rc=$?', observe.AUTH_CHECK)
        self.assertEqual(observe.AUTH_CHECK.count("auth.json"), 2)                  # test -e와 cat뿐이다


if __name__ == "__main__":
    unittest.main()
