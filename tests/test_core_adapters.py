"""core.adapters 검사. 파서는 aux-pc V04-01에서 실제로 받은 출력(tier2/*.txt)을 그대로 쓴다.
CLI·모델은 부르지 않는다."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tomllib
import unittest

from core import adapters, runner
from core.adapters import AdapterError, build_spec, child_env, interpret
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


def build_argv(adapter_id, **kwargs):
    return list(build_spec(adapter_id, **kwargs).argv)


class ArgvTests(unittest.TestCase):
    def test_claude_discussant_is_restricted_and_toolless(self):
        argv = build_argv("claude-code", exe=EXE, prompt="Q", model="claude-opus-5-5")
        self.assertEqual(argv[:3], [EXE, "-p", "--output-format"])  # 질문은 argv에 없다
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
        """HOME을 주지 않으면 옛 read-only 샌드박스다(동결한 Windows 경로). Linux 실행기는 늘 HOME을 준다."""
        argv = build_argv("codex", exe=EXE, prompt="Q", model="gpt-x")
        self.assertEqual(argv[1:3], ["exec", "--json"])
        self.assertEqual(argv[argv.index("--sandbox") + 1], "read-only")
        self.assertIn("--ignore-user-config", argv)
        self.assertEqual(argv[-1], "-")  # 지시문은 stdin에서 읽는다

    def test_codex_windows_sandbox_is_the_only_config_override(self):
        """openai/codex#42172: --ignore-user-config가 Windows 샌드박스 선택까지 버린다."""
        argv = build_argv("codex", exe=EXE, prompt="Q", model="gpt-x", codex_windows_sandbox=True)
        i = argv.index("-c")
        self.assertEqual(argv[i + 1], adapters.CODEX_WINDOWS_SANDBOX)
        self.assertLess(i, argv.index("--model"))
        for bad in ('model="o3"', 'windows.sandbox="unelevated"', 'sandbox_mode="danger-full-access"'):
            with self.subTest(bad=bad), self.assertRaises(AdapterError):
                adapters._check("codex", [EXE, "exec", "-c", bad, "Q"], user_text=(4,))
        for call in (dict(adapter_id="claude-code", codex_windows_sandbox=True),
                     dict(adapter_id="codex", codex_windows_sandbox="yes")):
            with self.subTest(call=call), self.assertRaises(AdapterError):
                build_argv(call.pop("adapter_id"), exe=EXE, prompt="Q", model="m", **call)

    def test_codex_on_linux_denies_its_login_file_instead_of_the_old_sandbox(self):
        """K46. 옛 --sandbox와 섞지 않고(권한 문서), exec에 없는 -P 대신 default_permissions로 고른다(0.156.1)."""
        argv = build_argv("codex", exe=EXE, prompt="Q", model="gpt-x", codex_user_home="/home/u/")
        define, select = adapters.codex_permissions("/home/u")
        self.assertNotIn("--sandbox", argv)
        self.assertNotIn("-P", argv)
        self.assertEqual([argv[i + 1] for i, a in enumerate(argv) if a == "-c"], [define, select])
        self.assertEqual(select, 'default_permissions="dml-discussant"')
        key, value = define.split("=", 1)
        self.assertEqual(key, "permissions.dml-discussant")
        self.assertEqual(tomllib.loads(f"profile = {value}")["profile"],
                         {"extends": ":read-only", "filesystem": {"/home/u/.codex/auth.json": "deny"}})
        self.assertLess(argv.index("-c"), argv.index("--model"))
        self.assertEqual(argv[-1], "-")

    def test_codex_config_exception_is_only_the_values_of_this_run(self):
        define, select = adapters.codex_permissions("/home/u")
        allowed = (define, select)
        adapters._check("codex", [EXE, "exec", "-c", define, "-c", select, "-"], user_text=(), config=allowed)
        for bad in (adapters.codex_permissions("/home/v")[0], define.replace(":read-only", ":workspace"),
                    'default_permissions=":workspace"', adapters.CODEX_WINDOWS_SANDBOX, 'sandbox_mode="read-only"'):
            with self.subTest(bad=bad), self.assertRaises(AdapterError):
                adapters._check("codex", [EXE, "exec", "-c", bad, "-"], user_text=(), config=allowed)
        for flag in ("-P", "--permission-profile"):
            with self.subTest(flag=flag), self.assertRaises(AdapterError):
                adapters._check("codex", [EXE, "exec", flag, "dml-discussant", "-"], user_text=(), config=allowed)

    def test_codex_user_home_must_be_a_plain_posix_path(self):
        for home in ("relative", "", "/", "C:\\Users\\u", '/home/u"x', "/home/u\nx", "/home/u\\x", 3):
            with self.subTest(home=home), self.assertRaises(AdapterError):
                build_argv("codex", exe=EXE, prompt="Q", model="m", codex_user_home=home)
        for call in (dict(adapter_id="claude-code", codex_user_home="/home/u"),
                     dict(adapter_id="codex", codex_user_home="/home/u", codex_windows_sandbox=True)):
            with self.subTest(call=call), self.assertRaises(AdapterError):
                build_argv(call.pop("adapter_id"), exe=EXE, prompt="Q", model="m", **call)

    def test_participant_argv_is_pinned(self):
        """참여자 argv를 고정한다. argv가 바뀌면 core.contract의 판도 바뀌어 기록의 관측으로 허가하지 않는다(리뷰 R04).
        이 시험이 실패하면 argv만 고치지 말고, 바뀐 판에 대해 다시 관측해야 함을 인계에 적는다. 이름은 옛 판이다."""
        pinned = {
            ("claude-code", "discussant-1"): (
                ["-p", "--output-format", "stream-json", "--verbose", "--model", "m", "--permission-mode", "dontAsk",
                 "--no-session-persistence", "--strict-mcp-config", "--disable-slash-commands", "--restricted",
                 "--tools", ""], {}),
            ("codex", "discussant-2"): (
                ["exec", "--json", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config", "--ignore-rules",
                 "-c", *adapters.codex_permissions("/home/u")[:1], "-c", adapters.codex_permissions("/home/u")[1],
                 "--model", "m", "-"], {"codex_user_home": "/home/u"}),
        }
        for (adapter_id, revision), (expected, extra) in pinned.items():
            with self.subTest(adapter=adapter_id):
                self.assertEqual(build_argv(adapter_id, exe=EXE, prompt="Q", model="m", **extra)[1:], expected)

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
                 dict(read_dirs=["relative"]), dict(claude_context="bare"),
                 dict(prompt="x" * (adapters.CLAUDE_MAX_STDIN + 1)),
                 dict(adapter_id="antigravity", enabled=True, prompt="x" * 40_000))  # agy는 아직 argv
        for case in cases:
            call = dict(adapter_id="claude-code", exe=EXE, prompt="Q", model="m")
            call.update(case)
            with self.subTest(case=str(case)[:80]), self.assertRaises(AdapterError):
                build_argv(call.pop("adapter_id"), **call)

    def test_forbidden_arguments_never_appear_outside_user_text(self):
        for adapter_id in adapters.ADAPTERS:
            argv = build_argv(adapter_id, exe=EXE, prompt="--yolo --bare", model="m", enabled=True)
            others = [a for a in argv if a != "--yolo --bare"]
            with self.subTest(adapter=adapter_id):
                self.assertFalse(set(others) & adapters.FORBIDDEN[adapter_id])
        with self.assertRaises(AdapterError):
            adapters._check("codex", [EXE, "exec", "--dangerously-bypass-approvals-and-sandbox", "Q"], user_text=(3,))
        with self.assertRaises(AdapterError):
            adapters._check("claude-code", [EXE, "-p", "Q", "--fallback-model", "haiku"], user_text=(2,))


class ExecutionSpecTests(unittest.TestCase):
    """경계 리뷰 R06·인계 A4. 질문 본문은 stdin으로 가고 argv에 남지 않는다. 기록에는 digest와 크기만."""

    def test_question_goes_to_stdin_and_only_its_digest_is_recorded(self):
        question = "--yolo 선행 대시로 시작하는 한글 질문. " * 2000  # 명령줄이었다면 Windows 상한을 넘는다
        data = question.encode("utf-8")
        for adapter_id in ("claude-code", "codex"):
            spec = build_spec(adapter_id, exe=EXE, prompt=question, model="m")
            with self.subTest(adapter=adapter_id):
                self.assertEqual(spec.input_via, adapters.STDIN)
                self.assertEqual(spec.stdin_text, question)
                self.assertFalse(any("선행 대시" in a for a in spec.argv))
                self.assertEqual((spec.input_bytes, spec.input_sha256),
                                 (len(data), hashlib.sha256(data).hexdigest()))

    def test_agy_keeps_the_question_on_the_command_line_until_stdin_is_observed(self):
        spec = build_spec("antigravity", exe=EXE, prompt="Q", model="g", enabled=True)
        self.assertEqual((spec.input_via, spec.stdin_text), (adapters.ARGV, None))
        self.assertEqual(spec.argv[1:3], ("-p", "Q"))

    def test_the_record_form_never_carries_the_question(self):
        """WSL2 리뷰 WM-02. 기록은 record()로만 한다. repr()에도 본문이 없다."""
        secret = "SYNTHETIC_PRIVATE_QUESTION"
        for adapter_id in adapters.ADAPTERS:
            spec = build_spec(adapter_id, exe=EXE, prompt=secret, model="m", enabled=True)
            with self.subTest(adapter=adapter_id):
                self.assertNotIn(secret, repr(spec))
                self.assertNotIn(secret, json.dumps(spec.record()))
                self.assertEqual(spec.record()["input_bytes"], len(secret))

    def test_stdin_matching_an_option_does_not_mask_recorded_argv(self):
        for adapter_id, prompt in (("codex", "--ephemeral"), ("codex", "-"),
                                   ("claude-code", "--restricted")):
            with self.subTest(adapter=adapter_id, prompt=prompt):
                spec = build_spec(adapter_id, exe=EXE, prompt=prompt, model="m")
                self.assertEqual(spec.record()["argv"], list(spec.argv))

    def test_the_runner_delivers_the_question_byte_for_byte(self):
        """가짜 CLI가 stdin을 그대로 돌려준다. 한글과 선행 대시, 줄바꿈이 그대로 가는지 본다."""
        spec = build_spec("codex", exe=EXE, prompt="첫 줄\n-둘째 줄", model="m")
        echo = [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"]
        result = runner.run(echo, cwd=ABS_DIR, env=dict(os.environ), timeout=20, stdin_text=spec.stdin_text)
        self.assertEqual(result.stdout, "첫 줄\n-둘째 줄")


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

    def test_codex_commands_rejected_on_stderr_are_not_success(self):
        """aux-pc 첫 Codex 관측: 명령이 모두 거절됐는데 exit 0에 답도 나왔다. JSONL에는 흔적이 없다."""
        body = recorded("P1-codex").stdout
        stderr = ('ERROR codex_core::tools::router: error=exec_command failed: CreateProcess { message: '
                  '"Rejected(\\"`powershell.exe -Command Get-Content allowed.txt` rejected: blocked by policy\\")" }\n')
        run = RunResult(("x",), EXITED, 0, body, stderr, False, False, 1, 0, True)
        out = interpret("codex", run, requested_model="gpt-x")
        self.assertFalse(out.ok)
        self.assertEqual(out.status, "tools_rejected")
        self.assertEqual(out.text, "OK")  # 답은 남기되 성공으로 치지 않는다

    def test_codex_failure_and_missing_completion(self):
        failed = '{"type":"turn.started"}\n{"type":"turn.failed","error":{"message":"usage limit reached"}}\n'
        out = interpret("codex", fake(failed, code=1), requested_model="m")
        self.assertEqual((out.ok, out.status, out.detail), (False, "cli_error", "usage limit reached"))
        partial = '{"type":"item.completed","item":{"type":"agent_message","text":"half"}}\n'
        out = interpret("codex", fake(partial), requested_model="m")
        self.assertEqual((out.ok, out.status), (False, "format_error"))


class BoundaryReviewRegressionTests(unittest.TestCase):
    """2026-09-23 경계 리뷰 R04(docs/reviews/2026-09-23-wsl2-boundary/). 출력은 외부 입력이다."""

    def test_unexpected_shapes_are_format_errors_not_exceptions(self):
        """문법이 맞는 JSON이어도 중첩 값의 타입이 다르면 예외 대신 형식 실패로 돌려준다."""
        for adapter_id, body in (
                ("claude-code", '{"type":"result","is_error":false,"result":"hi","modelUsage":["m"]}'),
                ("claude-code", '{"type":"result","is_error":false,"result":"hi","permission_denials":3}'),
                ("codex", '{"type":"item.completed","item":"oops"}\n{"type":"turn.completed"}\n')):
            with self.subTest(adapter=adapter_id, body=body):
                out = interpret(adapter_id, fake(body), requested_model="m")
                self.assertEqual((out.ok, out.status), (False, "format_error"))

    def test_codex_error_given_as_text_is_kept(self):
        out = interpret("codex", fake('{"type":"turn.failed","error":"boom"}\n', code=1), requested_model="m")
        self.assertEqual((out.ok, out.status, out.detail), (False, "cli_error", "boom"))

    def test_deep_or_empty_wrong_shapes_are_format_errors(self):
        """WSL2 리뷰 WM-06. 아주 깊은 중첩(RecursionError)과 빈 배열·빈 객체로 온 잘못된 타입."""
        deep = '{"type":"result","is_error":false,"result":"x","extra":' + "[" * 10000 + "0" + "]" * 10000 + "}"
        wrong = '{"type":"result","is_error":false,"result":"x","modelUsage":[],"permission_denials":{}}'
        for body in (deep, wrong):
            with self.subTest(body=body[:60]):
                out = interpret("claude-code", fake(body), requested_model="m")
                self.assertEqual((out.ok, out.status), (False, "format_error"))
        absent = '{"type":"result","is_error":false,"result":"x","modelUsage":null}'
        self.assertTrue(interpret("claude-code", fake(absent), requested_model="m").ok)  # null은 없음이다

    def test_an_answer_to_a_partly_delivered_question_is_not_accepted(self):
        """WSL2 리뷰 WM-01. 입력 전달이 완전하지 않으면 답이 그럴듯해도 받지 않는다."""
        good = recorded("P1-claude")
        for delivery in (runner.INPUT_FAILED, runner.INPUT_INCOMPLETE):
            with self.subTest(delivery=delivery):
                run = RunResult(good.argv, EXITED, 0, good.stdout, "", False, False, 1, 0, True,
                                input_delivery=delivery)
                out = interpret("claude-code", run, requested_model="m")
                self.assertEqual((out.ok, out.status), (False, "input_error"))
        run = RunResult(good.argv, EXITED, 0, good.stdout, "", False, False, 1, 0, True,
                        input_delivery=runner.INPUT_COMPLETE)
        self.assertEqual(interpret("claude-code", run, requested_model="m").status,
                         interpret("claude-code", good, requested_model="m").status)

    def test_codex_answer_is_not_accepted_when_stderr_was_cut(self):
        """명령 거절의 흔적은 stderr에만 있다. 잘린 stderr로는 거절이 없었다고 말할 수 없다."""
        run = RunResult(("x",), EXITED, 0, recorded("P1-codex").stdout, "noise", False, True, 1, 0, True)
        out = interpret("codex", run, requested_model="gpt-x")
        self.assertEqual((out.ok, out.status), (False, "format_error"))
        self.assertEqual(out.text, "OK")  # 답은 남기되 성공으로 치지 않는다

    def test_codex_rejections_counted_over_the_whole_stderr_decide_even_when_it_was_cut(self):
        """K02. runner가 stderr 전체에서 센 값이 있으면 잘린 stderr여도 판정할 수 있다."""
        body = recorded("P1-codex").stdout
        for counts, status in (({adapters.CODEX_REJECTED: 0}, "ok"), ({adapters.CODEX_REJECTED: 2}, "tools_rejected")):
            with self.subTest(counts=counts):
                run = RunResult(("x",), EXITED, 0, body, "noise", False, True, 1, 0, True, stderr_counts=counts)
                self.assertEqual(interpret("codex", run, requested_model="gpt-x").status, status)
        self.assertEqual(adapters.STDERR_MARKS["codex"], (adapters.CODEX_REJECTED,))


if __name__ == "__main__":
    unittest.main()
