"""Publication regressions use synthetic strings only; no native CLI or auth probes."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from tools import redaction, runtime_inventory
from tools.w2 import auth_mounts, observe


class RedactionTests(unittest.TestCase):
    def test_exporters_remove_emails_other_user_paths_and_known_secrets(self):
        samples = ("person@example.test", "/home/other-person/private", r"C:\Users\Jane Doe\secret",
                   "sk-proj-" + "X" * 24, "github_pat_" + "A" * 40,
                   "Bearer synthetic-short-secret", "password=small-secret",
                   "Cookie: private_session=small-secret; user=someone")
        with mock.patch.object(auth_mounts, "HOME", "/home/u"):
            exporters = (runtime_inventory.make_redactor("/home/u"), auth_mounts.hide,
                         lambda s: observe._scrub(s, "/home/u"))
            for sample in samples:
                for export in exporters:
                    with self.subTest(sample=sample, export=export):
                        self.assertNotEqual(sample, export(sample))
                        self.assertNotIn("small-secret", export(sample))
                        self.assertEqual(export(export(sample)), export(sample))

    def test_home_replacement_does_not_expose_a_different_users_suffix(self):
        self.assertEqual(redaction.scrub("/home/user/file /home/u/file", "/home/u"),
                         "/home/<user>/file ~/file")

    def test_recursive_keys_credentials_and_digest_exceptions(self):
        data = {"person@example.test": [{"/home/other/file": "person@example.test"}],
                "input_sha256": "a" * 64, "password": "short", "refresh_token": "short",
                "nested": {"input_sha256": "person@example.test"}}
        out = observe._scrub_all(data, "/home/u")
        self.assertEqual(out["input_sha256"], "a" * 64)
        self.assertEqual(out["password"], "<redacted>")
        self.assertEqual(out["refresh_token"], "<redacted>")
        self.assertEqual(out["nested"]["input_sha256"], "<email>")
        self.assertEqual(out["<email>"], [{"/home/<user>/file": "<email>"}])

    def test_auth_mode_preserves_its_conservative_opaque_string_policy(self):
        # These long lower-case words are safe in help/paths, ambiguous in an auth error.
        value = "z" * 30
        self.assertEqual(redaction.scrub(value), value)
        self.assertEqual(auth_mounts.hide(value), "<redacted>")
        flag = "--disk-cache-directory-path"
        self.assertEqual(runtime_inventory.make_redactor("")(flag), flag)


class InitPublicationTests(unittest.TestCase):
    INIT = {"type": "system", "subtype": "init", "model": "m", "apiKeySource": "none",
            "tools": ["Read", "mcp__private_customer_service"], "plugins": [{"name": "private_plugin"}, None],
            "mcp_servers": [{"name": "claude.ai private_service", "status": "connected"},
                            {"name": "private_service", "status": "private_status"}, "private_broken"],
            "agents": [], "skills": "private_invalid_list", "cwd": "/home/private-user/work",
            "private_field": "anything", "permissionMode": {"private_permission": []}}

    def test_both_exporters_use_counts_and_preserve_absent_vs_empty(self):
        path = Path(__file__).resolve().parents[1] / "tools/v04-01/summarize_claude_init.py"
        spec = importlib.util.spec_from_file_location("init_publication_test", path)
        standalone = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(standalone)
        old = standalone.summarize(self.INIT, {"result": "person@example.test"}, "a" * 64, "b" * 40)
        run = SimpleNamespace(state="exited", exit_code=0, duration_ms=1, containment="pid_namespace",
                              tree_confirmed_empty=True, input_delivery="complete", stderr_counts={}, stderr="", stdout="")
        outcome = SimpleNamespace(text="OK", status="ok", ok=True, reported_models=("m",), model_match=True,
                                  usage={}, permission_denials=[], tool_events=[], detail=None)
        with tempfile.TemporaryDirectory() as tmp:
            current = observe.summarize("b1", run, outcome, record={"argv": []}, argv=[], changes=[],
                                        work=Path(tmp), home="/home/u", init=self.INIT)
        counts = current["init"]["init_counts"]
        self.assertEqual(counts, old["init_counts"])
        self.assertEqual(counts["tools"], 2)
        self.assertEqual(counts["agents"], 0)
        self.assertIsNone(counts["skills"])
        self.assertIsNone(counts["slash_commands"])
        self.assertEqual(counts["mcp_servers_by_status"], {"connected": 1, "unknown": 2})
        self.assertEqual(counts["plugins_by_origin"], {"other": 1, "unknown": 1})
        self.assertEqual(current["init"]["missing_fields"], ["skills", "slash_commands"])
        self.assertEqual(current["init"]["unknown_field_count"], 1)
        self.assertIsNone(current["init"]["permissionMode"])
        for summary in (current, old):
            self.assertNotIn("private_", json.dumps(summary))
            self.assertNotIn("private-user", json.dumps(summary))
            self.assertNotIn("person@example.test", json.dumps(summary))
        self.assertEqual(old["raw_sha256"], "a" * 64)
        self.assertRegex(old["publication_policy_git_blob_sha1"], r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
