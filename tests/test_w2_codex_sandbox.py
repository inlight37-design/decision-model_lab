"""tools/w2/codex_sandbox.py 검사. 실제 Codex는 부르지 않는다 — 넘기는 권한 profile 인자의 모양만 본다."""
import tomllib
import unittest

from tools.w2 import codex_sandbox


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


if __name__ == "__main__":
    unittest.main()
