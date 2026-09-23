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

    def test_fine_grained_github_token_is_redacted(self):
        """PR #4 R04: github_pat_ 형식이 SECRET 에 없어 그대로 남았다. 합성 문자열이다."""
        token = "github_" + "pat_" + "A" * 82
        self.assertEqual(inv.make_redactor(HOME)(f"token {token}"), "token <redacted>")

    def test_user_names_with_spaces_are_redacted_whole(self):
        """PR #4 R04: 'C:\\Users\\Jane Doe' 가 '<user> Doe' 로 반만 가려졌고 재검사도 놓쳤다."""
        redact = inv.make_redactor(HOME)
        for text, expected in ((r"C:\Users\Jane Doe\notes.txt", r"C:\Users\<user>\notes.txt"),
                               (r'"C:\\Users\\Jane Doe\\x"', r'"C:\\Users\\<user>\\x"'),
                               ("C:/Users/Jane Doe/x", "C:/Users/<user>/x"),
                               (r"'C:\Users\Jane Doe'", r"'C:\Users\<user>'"),
                               ("/home/jane doe/x and", "/home/<user>/x and"),
                               ("path C:\\Users\\bob\nnext", "path C:\\Users\\<user>\nnext"),
                               (r"see C:\Users\bob now", r"see C:\Users\<user>")):
            with self.subTest(text=text):
                self.assertEqual(redact(text), expected)
                self.assertEqual(redact(expected), expected)
                self.assertIsNone(inv.USER_PATH.search(expected))
        for partial in (r"C:\Users\<user> Doe\notes.txt", "/home/<user> doe/x"):
            with self.subTest(partial=partial):
                self.assertIsNotNone(inv.USER_PATH.search(partial))


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

    def configured_tier2(self):
        self.manifest["tier"] = 2
        row = self.manifest["adapters"][0]
        row.update(configured=True, auth_mode="subscription_oauth", funding_mode="subscription")
        self.cap().update(status="observed", observed_at="2026-09-23T00:00:00Z",
                          evidence="probe P2 in RESULTS.md")
        return row

    def test_tier2_configured_needs_observation_and_known_modes(self):
        self.configured_tier2()
        self.assertEqual(validate_manifest(self.manifest), [])
        self.cap().update(evidence="")
        self.assertTrue(validate_manifest(self.manifest))

    def test_malformed_rows_fail_closed(self):
        """PR #4 R01: 누락·null·빈 값이 '알려진 인증·과금'으로 통과했고, 잘못된 타입은
        검사기를 예외로 멈췄다. 모두 오류 줄로 거절돼야 한다."""
        cases = {
            "auth/funding missing": lambda row, m: (row.pop("auth_mode"), row.pop("funding_mode")),
            "auth/funding null": lambda row, m: row.update(auth_mode=None, funding_mode=None),
            "auth/funding empty": lambda row, m: row.update(auth_mode="", funding_mode=""),
            "auth unknown": lambda row, m: row.update(auth_mode="unknown"),
            "funding not in the list": lambda row, m: row.update(funding_mode="free"),
            "configured but not installed": lambda row, m: row.update(installed=False),
            "installed not a boolean": lambda row, m: row.update(installed="yes"),
            "evidence not a string": lambda row, m: self.cap().update(evidence=True),
            "observed_at not a date": lambda row, m: self.cap().update(observed_at=True),
            "observed_at free text": lambda row, m: self.cap().update(observed_at="today"),
            "adapter_id a list": lambda row, m: row.update(adapter_id=[]),
            "adapter_id missing": lambda row, m: row.pop("adapter_id"),
            "tier a boolean": lambda row, m: m.update(tier=True),
            "env_presence a list": lambda row, m: m.update(env_presence=["bad"]),
            "env_presence missing": lambda row, m: m.pop("env_presence"),
            "value field in env_presence": lambda row, m: m["env_presence"]["ANTHROPIC_API_KEY"].update(
                value="FAKE_NON_TOKEN_SECRET"),
            "config file marked opened": lambda row, m: m["config_presence"][
                "~/.claude/settings.json"].update(opened=True),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                self.manifest, _ = claude_manifest()
                mutate(self.configured_tier2(), self.manifest)
                errors = validate_manifest(self.manifest)
                self.assertTrue(errors)
                self.assertTrue(all(isinstance(e, str) for e in errors))

    def test_unconfigured_rows_may_stay_unknown(self):
        self.manifest["tier"] = 2
        self.assertEqual(self.manifest["adapters"][0]["auth_mode"], "unknown")
        self.assertEqual(validate_manifest(self.manifest), [])

    def test_recorded_aux_pc_manifests_still_pass(self):
        folder = Path(__file__).resolve().parents[1] / "docs/experiments/v04-01-inventory/hosts/aux-pc"
        for name in ("manifest.json", "manifest.tier2.json"):
            with self.subTest(manifest=name):
                manifest = json.loads((folder / name).read_text(encoding="utf-8"))
                self.assertEqual(validate_manifest(manifest), [])

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


class FreshEnvironmentTests(unittest.TestCase):
    """AI 도구 셸에서 잰 값이 사용자의 새 터미널 값인 것처럼 기록되지 않게 한다."""
    BASE = {"CLAUDECODE": "1", "ANTHROPIC_BASE_URL": "https://example.invalid", "MCP_X": "1",
            "OPENAI_API_KEY": "user-set", "SYSTEMROOT": r"C:\Windows", "PATH": r"C:\tool-only"}

    def test_removes_only_process_only_ai_variables(self):
        env, removed = inv.fresh_environment(self.BASE, {"Path": r"C:\Windows"},
                                             {"OPENAI_API_KEY": "x", "Path": r"C:\Users\a\bin"})
        self.assertEqual(removed, ["ANTHROPIC_BASE_URL", "CLAUDECODE", "MCP_X"])
        self.assertIn("OPENAI_API_KEY", env)   # 사용자가 직접 설정한 것은 남긴다
        self.assertIn("SYSTEMROOT", env)
        self.assertEqual(env["PATH"], r"C:\Windows;C:\Users\a\bin")

    def test_persistent_values_win_and_new_persistent_variables_appear(self):
        """PR #4 R03: 설정에도 있는 이름이면 셸이 넣은 값이 남았고, 셸이 뜬 뒤 설정에 생긴
        변수는 빠졌다. 새 터미널은 설정 값을 받는다. 모두 합성 값이다."""
        base = {"ANTHROPIC_BASE_URL": "https://injected.invalid", "Path": "old", "HTTPS_PROXY": "p"}
        env, removed = inv.fresh_environment(
            base, {"Path": "system", "GEMINI_API_KEY": "machine"},
            {"anthropic_base_url": "https://expected.invalid", "CODEX_API_KEY": "FAKE",
             "GEMINI_API_KEY": "user", "Path": "user"})
        self.assertEqual(removed, [])
        upper = {k.upper(): v for k, v in env.items()}
        self.assertEqual(upper["ANTHROPIC_BASE_URL"], "https://expected.invalid")
        self.assertEqual(len([k for k in env if k.upper() == "ANTHROPIC_BASE_URL"]), 1)
        self.assertEqual(upper["CODEX_API_KEY"], "FAKE")
        self.assertEqual(upper["GEMINI_API_KEY"], "user")   # 사용자 설정이 시스템 설정을 이긴다
        self.assertEqual(env["PATH"], "system;user")
        self.assertNotIn("Path", env)
        self.assertEqual(env["HTTPS_PROXY"], "p")           # 접두사 밖은 손대지 않는다

    def test_billing_variable_set_after_the_shell_started_is_reported(self):
        """셸이 뜬 뒤 사용자가 API 키를 설정했다면 새 터미널의 CLI는 그 키를 본다."""
        env, _ = inv.fresh_environment({"Path": "old"}, {"Path": "system"},
                                       {"ANTHROPIC_API_KEY": "FAKE", "Codex_Api_Key": "FAKE"})
        manifest, _ = claude_manifest(environ=env, removed_vars=[])
        self.assertTrue(manifest["env_presence"]["ANTHROPIC_API_KEY"]["present"])
        self.assertTrue(manifest["env_presence"]["CODEX_API_KEY"]["present"])  # 이름 대소문자 무시
        self.assertNotIn("FAKE", json.dumps(manifest))

    def test_manifest_records_mode_and_names_only(self):
        env, removed = inv.fresh_environment(self.BASE, {"Path": ""}, {})
        manifest, _ = claude_manifest(environ=env, removed_vars=removed)
        self.assertEqual(manifest["environment"], {"mode": "fresh", "removed": removed})
        self.assertFalse(manifest["env_presence"]["ANTHROPIC_BASE_URL"]["present"])
        self.assertNotIn("example.invalid", json.dumps(manifest))
        self.assertEqual(validate_manifest(manifest), [])
        manifest["environment"]["removed"].append("ANTHROPIC_BASE_URL=https://example.invalid")
        self.assertTrue(validate_manifest(manifest))

    def test_process_mode_is_the_default(self):
        manifest, _ = claude_manifest()
        self.assertEqual(manifest["environment"], {"mode": "process", "removed": []})

    def test_fresh_env_is_windows_only(self):
        with mock.patch.object(inv, "IS_WINDOWS", False), mock.patch("sys.stderr"), \
                self.assertRaises(SystemExit):
            inv.main(["--host-label", "test-pc", "--dry-run", "--fresh-env"])

    @unittest.skipUnless(inv.IS_WINDOWS, "Windows registry only")
    def test_registry_environment_reads_both_scopes(self):
        machine, user = inv.registry_environment()
        self.assertIn("PATH", {name.upper() for name in machine})
        self.assertIsInstance(user, dict)


def load_summarizer():
    import importlib.util
    path = Path(__file__).resolve().parents[1] / "tools/v04-01/summarize_claude_init.py"
    spec = importlib.util.spec_from_file_location("summarize_claude_init", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SummarizeClaudeInitTests(unittest.TestCase):
    """P4 요약기. 합성 stream 만 쓴다. PR #4 R05: 없는 필드가 0 으로 기록됐다."""
    INIT = {"type": "system", "subtype": "init", "model": "m", "apiKeySource": "none",
            "tools": [], "mcp_servers": [], "plugins": [{"name": "a@builtin"}, {"name": "mine@shop"}],
            "agents": ["x"], "cwd": r"C:\Users\carol\work"}
    RESULT = {"type": "result", "subtype": "success", "is_error": False, "result": "OK", "usage": {}}

    def test_missing_list_is_null_not_zero(self):
        s = load_summarizer()
        summary = s.summarize(self.INIT, self.RESULT, "0" * 64, "0" * 40)
        counts = summary["init_counts"]
        self.assertEqual(counts["tools"], 0)            # 있고 비었다
        self.assertIsNone(counts["skills"])             # 필드가 없었다
        self.assertIsNone(counts["slash_commands"])
        self.assertEqual(summary["missing_fields"], ["skills", "slash_commands"])
        self.assertEqual(counts["plugins_by_origin"], {"builtin": 1, "other": 1})
        self.assertIn("cwd", summary["init_fields"])
        self.assertNotIn("carol", json.dumps(summary))  # 필드 이름만, 값은 싣지 않는다
        self.assertNotIn("mine", json.dumps(summary))

    def test_stream_without_init_is_refused(self):
        s = load_summarizer()
        with self.assertRaises(ValueError):
            s.parse(json.dumps(self.RESULT))


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
