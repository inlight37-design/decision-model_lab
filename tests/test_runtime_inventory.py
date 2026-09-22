"""V04-01 tier 1 도구 검사. 실제 CLI·로그인·모델을 쓰지 않는다. 가짜 실행기와 python 자신만 쓴다."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from tools import runtime_inventory as inv
from tools.runtime_inventory import ADAPTERS, Adapter, Feature, collect, validate_manifest

HOME = r"C:\Users\alice"
NOW = datetime(2026, 9, 23, tzinfo=timezone.utc)
CLAUDE_HELP = "Usage: claude [options]\n  -p, --print\n  --output-format <format>\n  --bare\n  --resume [id]\n"


def fake_run(outputs):
    """argv 뒷부분(명령 이름 제외)으로 결과를 고른다. 호출된 argv 를 모두 기록한다."""
    calls = []

    def run(argv, timeout):
        calls.append(argv)
        result = outputs.get(tuple(argv[1:]), {"exit_code": 0, "stdout": "", "stderr": ""})
        return {"timed_out": False, "duration_ms": 1, **result}
    run.calls = calls
    return run


def only(adapter_id):
    return tuple(a for a in ADAPTERS if a.adapter_id == adapter_id)


def claude_manifest(**overrides):
    kwargs = dict(adapters=only("claude-code"), which=lambda c: HOME + r"\.local\bin\claude.exe",
                  run=fake_run({("--version",): {"exit_code": 0, "stdout": "2.1.300 (Claude Code)\n", "stderr": ""},
                                ("--help",): {"exit_code": 0, "stdout": CLAUDE_HELP, "stderr": ""}}),
                  environ={}, home=HOME, exists=lambda p: False, now=NOW)
    kwargs.update(overrides)
    return collect("test-pc", **kwargs)


class SafetyTests(unittest.TestCase):
    def test_every_probe_is_version_or_help(self):
        """모델을 부르는 인자(-p, exec 프롬프트 등)가 섞이면 한도가 소모된다. 구조로 막는다."""
        for command in inv.planned_commands():
            with self.subTest(command=command):
                self.assertIn(command[-1], ("--help", "--version"))
                self.assertNotIn("-p", command)

    def test_env_values_are_never_recorded(self):
        secret = "sk-ant-THISISNOTAREALKEY000000"
        manifest, outputs = claude_manifest(environ={"ANTHROPIC_API_KEY": secret})
        self.assertTrue(manifest["env_presence"]["ANTHROPIC_API_KEY"]["present"])
        self.assertFalse(manifest["env_presence"]["OPENAI_API_KEY"]["present"])
        self.assertNotIn(secret, json.dumps(manifest) + "".join(outputs.values()))

    def test_config_files_are_checked_for_presence_only(self):
        opened = mock.mock_open()
        with mock.patch("builtins.open", opened):
            manifest, _ = claude_manifest(exists=lambda p: p.endswith(".credentials.json"))
        opened.assert_not_called()
        entry = manifest["config_presence"]["~/.claude/.credentials.json"]
        self.assertEqual(entry, {"present": True, "adapter": "claude-code", "opened": False})

    def test_home_and_other_user_paths_are_redacted(self):
        run = fake_run({("--version",): {"exit_code": 0, "stdout": "2.1.300\n", "stderr": ""},
                        ("--help",): {"exit_code": 0, "stdout": CLAUDE_HELP + "cache: /home/bob/.cache\n"
                                      + r"see C:\Users\carol\notes" + "\n", "stderr": ""}})
        manifest, outputs = claude_manifest(run=run)
        self.assertEqual(manifest["adapters"][0]["resolved_path"], r"~\.local\bin\claude.exe")
        text = outputs["help/claude-code-1.txt"]
        self.assertIn("/home/<user>/.cache", text)
        self.assertIn(r"C:\Users\<user>\notes", text)
        self.assertNotIn("bob", text)
        self.assertNotIn("carol", text)

    def test_secret_like_output_is_redacted_but_flag_names_are_not(self):
        run = fake_run({("--help",): {"exit_code": 0, "stdout": CLAUDE_HELP +
                                      "  --disk-cache-directory-path\n token sk-proj-ABCDEFGHIJKLMNOPQRST\n",
                                      "stderr": ""}})
        _, outputs = claude_manifest(run=run)
        text = outputs["help/claude-code-1.txt"]
        self.assertIn("--disk-cache-directory-path", text)
        self.assertNotIn("sk-proj-ABCDEFGHIJKLMNOPQRST", text)
        self.assertIn("<redacted>", text)


class DetectionTests(unittest.TestCase):
    def test_flags_in_help_are_in_help_not_observed(self):
        manifest, _ = claude_manifest()
        row = manifest["adapters"][0]
        self.assertEqual(row["runtime_version"], "2.1.300 (Claude Code)")
        caps = row["capabilities"]
        self.assertEqual(caps["bare_mode"]["status"], "in_help")
        self.assertEqual(caps["bare_mode"]["source_ids"], ["F25"])
        self.assertEqual(caps["json_schema"]["status"], "not_in_help")
        self.assertFalse(row["configured"])
        self.assertEqual((row["auth_mode"], row["funding_mode"]), ("unknown", "unknown"))

    def test_missing_cli_is_unknown_not_unsupported(self):
        run = fake_run({})
        manifest, outputs = claude_manifest(which=lambda c: None, run=run)
        row = manifest["adapters"][0]
        self.assertFalse(row["installed"])
        self.assertEqual(run.calls, [])
        self.assertEqual(outputs, {})
        self.assertEqual({c["status"] for c in row["capabilities"].values()}, {"unknown"})

    def test_failed_or_timed_out_help_is_unknown(self):
        for result in ({"exit_code": 1, "stdout": CLAUDE_HELP, "stderr": "boom"},
                       {"exit_code": None, "stdout": CLAUDE_HELP, "stderr": "", "timed_out": True}):
            with self.subTest(result=result):
                manifest, _ = claude_manifest(run=fake_run({("--help",): result}))
                caps = manifest["adapters"][0]["capabilities"]
                self.assertEqual({c["status"] for c in caps.values()}, {"unknown"})

    def test_second_help_probe_feeds_its_own_features(self):
        run = fake_run({("--help",): {"exit_code": 0, "stdout": "Commands:\n  exec  run\n  login\n", "stderr": ""},
                        ("exec", "--help"): {"exit_code": 0, "stdout": "  --json\n  --sandbox <mode>\n", "stderr": ""}})
        manifest, _ = collect("test-pc", adapters=only("codex"), which=lambda c: "/usr/bin/codex", run=run,
                              environ={}, home="/home/alice", exists=lambda p: False, now=NOW)
        caps = manifest["adapters"][0]["capabilities"]
        self.assertEqual(caps["exec_mode"]["status"], "in_help")
        self.assertEqual(caps["json_events"]["status"], "in_help")
        self.assertEqual(caps["json_events"]["evidence"], "codex exec --help")
        self.assertEqual(caps["output_schema"]["status"], "not_in_help")

    def test_real_subprocess_with_python_as_the_cli(self):
        """실제 subprocess 경로. 설치된 CLI 대신 이 테스트를 실행 중인 python 을 쓴다."""
        adapter = Adapter("python", "python", (("--help",),),
                          (Feature("version_flag", 0, r"--version\b"),), "test only")
        manifest, outputs = collect("test-pc", adapters=(adapter,), which=lambda c: sys.executable,
                                    environ={}, now=NOW)
        row = manifest["adapters"][0]
        self.assertTrue(row["runtime_version"].startswith("Python 3."))
        self.assertEqual(row["probes"][1]["exit_code"], 0)
        self.assertEqual(row["capabilities"]["version_flag"]["status"], "in_help")
        self.assertEqual(validate_manifest(manifest), [])

    def test_timeout_is_recorded(self):
        result = inv.run_probe([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.5)
        self.assertTrue(result["timed_out"])
        self.assertIsNone(result["exit_code"])


class ManifestRuleTests(unittest.TestCase):
    def setUp(self):
        self.manifest, _ = claude_manifest()

    def cap(self):
        return self.manifest["adapters"][0]["capabilities"]["bare_mode"]

    def test_collected_manifest_is_valid(self):
        self.assertEqual(validate_manifest(self.manifest), [])

    def test_tier1_cannot_claim_observed(self):
        self.cap().update(status="observed", observed_at="2026-09-23T00:00:00Z", evidence="x")
        self.assertTrue(validate_manifest(self.manifest))

    def test_documentation_alone_cannot_configure(self):
        self.manifest["adapters"][0]["configured"] = True
        self.assertTrue(validate_manifest(self.manifest))
        self.manifest["tier"] = 2
        self.assertTrue(validate_manifest(self.manifest))  # 관측도, 인증 방식도 없다

    def test_tier2_configured_needs_observation_and_known_modes(self):
        self.manifest["tier"] = 2
        row = self.manifest["adapters"][0]
        row.update(configured=True, auth_mode="subscription_oauth", funding_mode="subscription_only")
        self.cap().update(status="observed", observed_at="2026-09-23T00:00:00Z",
                          evidence="probe P2 in RESULTS.md")
        self.assertEqual(validate_manifest(self.manifest), [])
        self.cap().update(evidence="")
        self.assertTrue(validate_manifest(self.manifest))

    def test_unknown_status_rejected(self):
        self.cap()["status"] = "works"
        self.assertTrue(validate_manifest(self.manifest))

    def test_env_value_instead_of_presence_rejected(self):
        self.manifest["env_presence"]["ANTHROPIC_API_KEY"]["present"] = "sk-..."
        self.assertTrue(validate_manifest(self.manifest))

    def test_secret_or_user_path_rejected(self):
        for field, value in (("note", "key sk-ant-ABCDEFGHIJKLMNOPQRSTUV"),
                             ("resolved_path", r"C:\Users\alice\bin\claude.exe")):
            with self.subTest(field=field):
                manifest, _ = claude_manifest()
                manifest["adapters"][0][field] = value
                self.assertTrue(validate_manifest(manifest))


class CliTests(unittest.TestCase):
    def test_dry_run_executes_nothing(self):
        with mock.patch.object(inv, "run_probe", side_effect=AssertionError("executed")), \
                mock.patch("sys.stdout"):
            self.assertEqual(inv.main(["--host-label", "test-pc", "--dry-run"]), 0)

    def test_label_format_is_enforced(self):
        for label in (None, "My PC", "DESKTOP-L6EA2UJ", "a"):
            argv = ["--dry-run"] + (["--host-label", label] if label else [])
            with self.subTest(label=label), self.assertRaises(SystemExit), mock.patch("sys.stderr"):
                inv.main(argv)

    def test_refuses_to_overwrite_without_force(self):
        manifest, outputs = claude_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            inv.write(out, manifest, outputs, force=False)
            self.assertTrue((out / "help/claude-code-1.txt").is_file())
            with self.assertRaises(FileExistsError):
                inv.write(out, manifest, outputs, force=False)
            inv.write(out, manifest, outputs, force=True)
            with mock.patch("sys.stdout"):
                self.assertEqual(inv.main(["--validate", str(out / "manifest.json")]), 0)


if __name__ == "__main__":
    unittest.main()
