"""새 컴퓨터 준비 확인(tools/setup/check_setup.py). 가짜 명령 결과만 쓰며 설치·로그인·모델 호출이 없다."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_setup", ROOT / "tools" / "setup" / "check_setup.py")
cs = importlib.util.module_from_spec(spec)
sys.modules["check_setup"] = cs   # dataclass가 자기 모듈을 찾는다
spec.loader.exec_module(cs)

STATUS = {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty",
          "email": "someone@example.com", "orgId": "org-secret"}


def fake(outputs, found=("git", "gh", "node", "codex", "claude", "wsl")):
    """outputs: 명령의 앞 두 낱말 → (종료 코드, 출력)."""
    calls = []

    def run(argv):
        calls.append(tuple(argv))
        key = " ".join(Path(argv[0]).name.split(".")[0:1] + list(argv[1:2]))
        return outputs.get(key)

    def which(name):
        return f"/usr/bin/{name}" if name in found else None
    return run, which, calls


class CheckSetupTests(unittest.TestCase):
    def linux(self, outputs, env=None, found=("git", "codex", "claude")):
        run, which, calls = fake(outputs, found)
        with tempfile.TemporaryDirectory() as home:
            rows = cs.linux_rows(run, which, env or {}, Path(home), observed={"codex": "0.156.1",
                                                                                "claude-code": "2.1.280"},
                                 host="aux-pc-wsl", bwrap=Path(home) / "no-bwrap")
        return {row.name: row for row in rows}, calls

    def test_claude_login_keeps_account_values_out_of_the_report(self):
        rows, _ = self.linux({"claude auth": (0, json.dumps(STATUS)), "codex login": (0, "Logged in using ChatGPT")})
        text, _ = cs.render(list(rows.values()), "test")
        self.assertEqual((rows["Claude 로그인"].status, rows["Codex 로그인"].status), ("ok", "ok"))
        self.assertNotIn("someone@example.com", text)
        self.assertNotIn("org-secret", text)

    def test_logins_that_are_not_subscriptions_or_absent(self):
        api = dict(STATUS, authMethod="api_key")
        rows, _ = self.linux({"claude auth": (0, json.dumps(api)), "codex login": (0, "Logged in using an API key")})
        self.assertEqual((rows["Claude 로그인"].status, rows["Codex 로그인"].status), ("warn", "warn"))
        rows, _ = self.linux({"claude auth": (1, json.dumps({"loggedIn": False})), "codex login": (1, "Not logged in")})
        self.assertEqual((rows["Claude 로그인"].status, rows["Codex 로그인"].status), ("missing", "missing"))
        rows, _ = self.linux({"claude auth": (0, "not json")})
        self.assertEqual(rows["Claude 로그인"].status, "missing")

    def test_cli_versions_are_compared_with_the_observation_record(self):
        rows, _ = self.linux({"codex --version": (0, "codex-cli 0.156.1"), "claude --version": (0, "2.1.281 (Claude Code)")})
        self.assertEqual(rows["Codex CLI"].status, "ok")
        self.assertEqual(rows["Claude Code"].status, "info")   # 다른 판: 준비 조회가 거절한다는 안내
        self.assertIn("2.1.280", rows["Claude Code"].detail)
        rows, _ = self.linux({}, found=("git",))
        self.assertEqual(rows["Codex CLI"].status, "missing")

    def test_a_windows_cli_found_through_wsl_path_is_refused(self):
        run, _, _ = fake({})
        row = cs.cli_row(run, lambda name: "/mnt/c/Users/u/.local/bin/codex.exe", "codex", "codex", "Codex CLI", None)
        self.assertEqual(row.status, "missing")
        self.assertIn("Windows", row.detail)

    def test_bubblewrap_missing_is_required_and_fails_the_exit_code(self):
        rows, _ = self.linux({"claude auth": (0, json.dumps(STATUS)), "codex login": (0, "Logged in using ChatGPT"),
                              "codex --version": (0, "codex-cli 0.156.1"), "claude --version": (0, "2.1.280 (Claude Code)")})
        self.assertEqual((rows["bubblewrap"].status, rows["bubblewrap"].required), ("missing", True))
        text, code = cs.render(list(rows.values()), "test")
        self.assertEqual(code, 1)
        self.assertIn("bubblewrap", text.splitlines()[-1])

    def test_optional_items_warn_without_failing(self):
        rows = [cs.Row("Python", "ok", "3.12"), cs.Row("Node", "missing", "PATH에 없다", "설치", required=False)]
        text, code = cs.render(rows, "test")
        self.assertEqual(code, 0)
        self.assertIn("warn     Node", text)

    def test_billing_variables_are_named_but_never_read(self):
        rows, _ = self.linux({}, env={"ANTHROPIC_API_KEY": "sk-secret-value", "PATH": "/usr/bin"})
        self.assertEqual(rows["과금 환경변수"].status, "warn")
        self.assertIn("ANTHROPIC_API_KEY", rows["과금 환경변수"].detail)
        self.assertNotIn("sk-secret-value", cs.render(list(rows.values()), "test")[0])

    def test_global_agents_file_for_codex_is_reported(self):
        run, which, _ = fake({})
        with tempfile.TemporaryDirectory() as home:
            (Path(home) / ".codex").mkdir()
            (Path(home) / ".codex" / "AGENTS.md").write_text("x", encoding="utf-8")
            rows = {r.name: r for r in cs.linux_rows(run, which, {}, Path(home), observed={}, host=None,
                                                     bwrap=Path(home) / "none")}
        self.assertEqual(rows["Codex 전역 AGENTS.md"].status, "warn")

    def test_wsl_list_is_decoded_from_utf16(self):
        self.assertEqual(cs.decode("Ubuntu-24.04\r\n".encode("utf-16-le")).strip(), "Ubuntu-24.04")
        self.assertEqual(cs.decode("가 ok".encode("utf-8")), "가 ok")
        run, which, _ = fake({"wsl --list": (0, "docker-desktop\nUbuntu-24.04\n")})
        rows = {r.name: r for r in cs.windows_rows(run, which, {})}
        self.assertEqual((rows["WSL"].status, rows["WSL"].detail), ("ok", "Ubuntu-24.04"))
        run, which, _ = fake({"wsl --list": (0, "docker-desktop\n")})
        self.assertEqual({r.name: r for r in cs.windows_rows(run, which, {})}["WSL"].status, "warn")

    def test_setup_scripts_are_ascii_and_parse(self):
        """Windows PowerShell 5.1은 BOM 없는 UTF-8 .ps1을 ANSI로 읽는다 — 한 글자만 섞여도 원터치가 깨진다."""
        ps1, sh = ROOT / "tools/setup/setup.ps1", ROOT / "tools/setup/setup-wsl.sh"
        ps1.read_bytes().decode("ascii")
        self.assertNotIn(b"\r", sh.read_bytes())   # bash는 CRLF 줄을 명령의 일부로 읽는다
        import shutil
        import subprocess
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if powershell:
            check = ("$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile("
                     f"'{ps1}', [ref]$null, [ref]$e); if ($e) {{ $e | % {{ $_.Message }}; exit 1 }}")
            done = subprocess.run([powershell, "-NoProfile", "-Command", check], capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        bash = shutil.which("bash")
        if bash and not bash.lower().startswith(("c:\\windows", "c:/windows")):   # WSL 실행 스텁은 건너뛴다
            done = subprocess.run([bash, "-n", str(sh)], capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stderr)

    def test_observed_versions_come_from_the_current_record(self):
        versions = cs.observed_versions()
        self.assertEqual(set(versions), {"codex", "claude-code"})
        self.assertEqual(cs.observed_host(), "aux-pc-wsl")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(cs.observed_versions(Path(tmp) / "missing.json"), {})


if __name__ == "__main__":
    unittest.main()
