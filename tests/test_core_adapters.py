"""core.adapters 검사. 파서는 aux-pc V04-01에서 실제로 받은 출력(tier2/*.txt)을 그대로 쓴다.
CLI·모델은 부르지 않는다."""
import os
from pathlib import Path
import sys
import unittest

from core import adapters
from core.adapters import AdapterError, build_argv, child_env, interpret
from core.runner import EXITED, TIMED_OUT, UNKNOWN, RunResult
from tools.runtime_inventory import ENV_VARS

TIER2 = Path(__file__).resolve().parents[1] / "docs/experiments/v04-01-inventory/hosts/aux-pc/tier2"
EXE = sys.executable  # 절대 경로이기만 하면 된다. 실행하지 않는다
ABS_DIR = str(Path(__file__).resolve().parent)


def recorded(name, *, state=EXITED):
    """기록된 probe 파일에서 머리말(#)을 떼고 exit code를 읽는다."""
    lines = (TIER2 / f"{name}.txt").read_text(encoding="utf-8").splitlines()
    code = next(int(line.split(":", 1)[1]) for line in lines if line.startswith("# exit:"))
    body = "\n".join(line for line in lines if not line.startswith("#")).strip() + "\n"
    return RunResult(("x",), state, code, body, "", False, False, 1, 0, True)


def fake(stdout, *, code=0, state=EXITED, truncated=False):
    return RunResult(("x",), state, code, stdout, "", truncated, False, 1, 0, True)


class EnvironmentTests(unittest.TestCase):
    def test_billing_variables_are_dropped_by_name_only(self):
        env, dropped = child_env({"Anthropic_Api_Key": "FAKE", "OPENAI_API_KEY": "FAKE", "CODEX_HOME": "d",
                                  "CLAUDE_CONFIG_DIR": "c", "PATH": "p"})
        self.assertEqual(dropped, ["Anthropic_Api_Key", "OPENAI_API_KEY"])  # 대소문자를 가리지 않는다
        self.assertNotIn("FAKE", env.values())
        self.assertEqual((env["CODEX_HOME"], env["CLAUDE_CONFIG_DIR"]), ("d", "c"))  # 로그인 위치는 남긴다
        self.assertEqual(env["NO_COLOR"], "1")

    def test_billing_list_follows_the_inventory(self):
        names = {name for name, _, _ in ENV_VARS}
        self.assertTrue(adapters.BILLING_VARS <= names)
        self.assertEqual(adapters.BILLING_VARS | adapters.KEEP_VARS, names)
        self.assertIn("ANTHROPIC_API_KEY", adapters.BILLING_VARS)

    def test_registry_values_replace_tool_shell_values(self):
        env, _ = child_env({"CLAUDECODE": "1", "PATH": "old"}, machine={"Path": "sys"}, user={"Path": "usr"})
        self.assertNotIn("CLAUDECODE", env)  # 데스크톱 앱 셸의 중첩 표시는 넘기지 않는다
        self.assertEqual(env["PATH"], "sys;usr")


class ArgvTests(unittest.TestCase):
    def test_claude_discussant_is_restricted_and_toolless(self):
        argv = build_argv("claude-code", exe=EXE, prompt="Q", model="claude-opus-5-5")
        self.assertEqual(argv[:3], [EXE, "-p", "Q"])
        for flag in ("--restricted", "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "dontAsk")
        self.assertEqual(argv[-2:], ["--tools", ""])
        self.assertEqual(argv[argv.index("--model") + 1], "claude-opus-5-5")

    def test_claude_read_only_files_and_safe_mode(self):
        argv = build_argv("claude-code", exe=EXE, prompt="Q", model="m", read_dirs=[ABS_DIR],
                          claude_context="safe_mode")
        self.assertIn("--safe-mode", argv)
        self.assertNotIn("--restricted", argv)
        self.assertEqual(argv[argv.index("--add-dir") + 1], ABS_DIR)
        self.assertEqual(argv[-2:], ["--tools", "Read"])

    def test_codex_discussant_is_read_only(self):
        argv = build_argv("codex", exe=EXE, prompt="Q", model="gpt-x")
        self.assertEqual(argv[1:3], ["exec", "--json"])
        self.assertEqual(argv[argv.index("--sandbox") + 1], "read-only")
        self.assertIn("--ignore-user-config", argv)
        self.assertEqual(argv[-1], "Q")

    def test_agy_is_off_until_the_user_turns_it_on(self):
        with self.assertRaises(AdapterError):
            build_argv("antigravity", exe=EXE, prompt="Q", model="gemini-x")
        argv = build_argv("antigravity", exe=EXE, prompt="Q", model="gemini-x", enabled=True, effort="high")
        self.assertEqual(argv[argv.index("--output-format") + 1], "json")  # agy는 틀린 값을 무시하므로 고정
        self.assertIn("--sandbox", argv)
        with self.assertRaises(AdapterError):
            build_argv("antigravity", exe=EXE, prompt="Q", model="gemini-x", enabled=True, effort="max")

    def test_model_must_be_explicit(self):
        for model in ("", " ", "a b", None, "x" * 81):
            with self.subTest(model=model), self.assertRaises(AdapterError):
                build_argv("codex", exe=EXE, prompt="Q", model=model)

    def test_requests_refused_before_building(self):
        cases = (dict(adapter_id="nope"), dict(prompt=""), dict(exe="claude"), dict(role="writer"),
                 dict(read_dirs=["relative"]), dict(claude_context="bare"), dict(prompt="x" * 40_000))
        for case in cases:
            call = dict(adapter_id="claude-code", exe=EXE, prompt="Q", model="m")
            call.update(case)
            with self.subTest(case=case), self.assertRaises(AdapterError):
                build_argv(call.pop("adapter_id"), **call)

    def test_forbidden_arguments_never_appear_outside_user_text(self):
        for adapter_id in adapters.ADAPTERS:
            argv = build_argv(adapter_id, exe=EXE, prompt="--yolo --bare", model="m", enabled=True)
            prompt_index = argv.index("--yolo --bare")
            others = [a for i, a in enumerate(argv) if i != prompt_index]
            with self.subTest(adapter=adapter_id):
                self.assertFalse(set(others) & adapters.FORBIDDEN[adapter_id])
        with self.assertRaises(AdapterError):
            adapters._check("codex", [EXE, "exec", "--dangerously-bypass-approvals-and-sandbox", "Q"], user_text=(3,))
        with self.assertRaises(AdapterError):
            adapters._check("claude-code", [EXE, "-p", "Q", "--fallback-model", "haiku"], user_text=(2,))


class InterpretRecordedTests(unittest.TestCase):
    """aux-pc에서 받은 실제 출력으로 판정 규칙을 고정한다."""

    def test_claude_success_reports_model(self):
        out = interpret("claude-code", recorded("P1-claude"), requested_model="claude-opus-5-5")
        self.assertTrue(out.ok)
        self.assertEqual((out.text, out.reported_models, out.model_match), ("OK", ("claude-opus-5-5",), True))
        self.assertEqual(out.usage["output_tokens"], 4)
        self.assertEqual(out.permission_denials, 0)

    def test_claude_model_mismatch_is_flagged(self):
        out = interpret("claude-code", recorded("P1-claude"), requested_model="claude-sonnet-x")
        self.assertIs(out.model_match, False)

    def test_claude_error_with_success_subtype_is_an_error(self):
        """P2: subtype은 success인데 is_error가 true."""
        out = interpret("claude-code", recorded("P2-claude"), requested_model="claude-opus-5-5")
        self.assertFalse(out.ok)
        self.assertEqual(out.status, "cli_error")

    def test_codex_success_has_no_model_report(self):
        out = interpret("codex", recorded("P1-codex"), requested_model="gpt-x")
        self.assertTrue(out.ok)
        self.assertEqual(out.text, "OK")
        self.assertEqual(out.usage["input_tokens"], 15268)
        self.assertEqual((out.reported_models, out.model_match), ((), None))

    def test_agy_success_and_silent_text_fallback(self):
        self.assertTrue(interpret("antigravity", recorded("P1-agy"), requested_model="g").ok)
        out = interpret("antigravity", recorded("P3-agy"), requested_model="g")
        self.assertFalse(out.ok)
        self.assertEqual(out.status, "format_error")  # JSON을 요청했는데 text가 왔다

    def test_process_state_wins_over_a_good_looking_answer(self):
        for state in (TIMED_OUT, UNKNOWN):
            with self.subTest(state=state):
                out = interpret("claude-code", recorded("P1-claude", state=state), requested_model="m")
                self.assertFalse(out.ok)
                self.assertEqual(out.status, f"process_{state}")

    def test_truncated_output_is_not_parsed(self):
        out = interpret("codex", fake('{"type":"turn.completed"}', truncated=True), requested_model="m")
        self.assertEqual(out.status, "format_error")

    def test_codex_failure_and_missing_completion(self):
        failed = '{"type":"turn.started"}\n{"type":"turn.failed","error":{"message":"usage limit reached"}}\n'
        out = interpret("codex", fake(failed, code=1), requested_model="m")
        self.assertEqual((out.ok, out.status, out.detail), (False, "cli_error", "usage limit reached"))
        partial = '{"type":"item.completed","item":{"type":"agent_message","text":"half"}}\n'
        out = interpret("codex", fake(partial), requested_model="m")
        self.assertEqual((out.ok, out.status), (False, "format_error"))


if __name__ == "__main__":
    unittest.main()
