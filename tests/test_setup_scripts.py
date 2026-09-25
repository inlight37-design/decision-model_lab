"""설치 스크립트의 실패 경계(2026-09-25 외부 검토 R01–R03). 대역 명령만 쓰며 내려받기·설치·로그인이 없다.

setup-wsl.sh는 Linux(CI)에서, setup.ps1은 Windows(CI)에서 돈다. 두 스크립트 모두 실패를 성공으로 덮지 않는지,
관측 판을 읽지 못하면 최신판으로 넘어가지 않는지, 승인한 설치 파일의 바이트만 실행하는지를 본다.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")


def write(path: Path, text: str, mode: int = 0o755) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8", newline="\n")
    path.chmod(mode)
    return path


def installer(marker: str) -> str:
    """설치 대역: 실행되면 표식을 남기고 관측 판을 말하는 가짜 codex를 ~/.local/bin에 둔다."""
    return textwrap.dedent(f"""\
        #!/bin/sh
        touch "$HOME/ran-{marker}"
        mkdir -p "$HOME/.local/bin"
        printf '#!/bin/sh\\necho "codex-cli 0.156.1"\\n' > "$HOME/.local/bin/codex"
        chmod +x "$HOME/.local/bin/codex"
        """)


@unittest.skipUnless(BASH and sys.platform != "win32" and os.geteuid() != 0,
                     "setup-wsl.sh runs on Linux (CI) as a normal user only")
class SetupWslTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "tools/setup").mkdir(parents=True)
        shutil.copy(ROOT / "tools/setup/setup-wsl.sh", self.root / "tools/setup/setup-wsl.sh")
        self.bin, self.home = self.root / "bin", self.root / "home"
        self.home.mkdir()
        write(self.bin / "dpkg", "#!/bin/sh\nexit 0\n")                        # 모든 apt 패키지가 있다
        write(self.bin / "claude", '#!/bin/sh\necho "2.1.280 (Claude Code)"\n')  # Claude는 이미 관측 판
        write(self.bin / "curl", """\
            #!/bin/sh
            # 내려받기 대역: 호출을 기록하고 $SERVE 파일을 -o 위치로 복사한다.
            echo call >> "$HOME/curl-calls"
            while [ $# -gt 0 ]; do [ "$1" = -o ] && { cp "$SERVE" "$2"; exit 0; }; shift; done
            exit 1
            """)
        self.python(0, "codex 0.156.1\nclaude-code 2.1.280\n")
        self.a = write(self.root / "a.sh", installer("A"))
        self.b = write(self.root / "b.sh", installer("B"))

    def python(self, code: int, output: str):
        write(self.bin / "python3", f"#!/bin/sh\nprintf '%s' '{output}'\nexit {code}\n")

    def run_script(self, *args, serve=None):
        env = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(self.home), "SERVE": str(serve or self.a),
               "LANG": "C.UTF-8"}
        done = subprocess.run([BASH, str(self.root / "tools/setup/setup-wsl.sh"), "--no-final", *args],
                              capture_output=True, text=True, env=env, timeout=60)
        return done.returncode, done.stdout + done.stderr

    def sha(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_unreadable_observed_versions_stop_before_any_download(self):
        for code, output in ((7, ""), (0, "codex 0.156.1\n"), (0, "codex 0.156.1\nclaude-code latest\n")):
            with self.subTest(code=code, output=output):
                self.python(code, output)
                status, text = self.run_script()
                self.assertEqual(status, 4, text)
                self.assertNotIn("latest", text.split("STOP")[0])   # 조용히 최신판으로 넘어가지 않는다
                self.assertFalse((self.home / "curl-calls").exists())

    def test_a_changed_installer_stops_and_approval_runs_exactly_the_kept_bytes(self):
        status, text = self.run_script()                       # 내려받은 A는 검토한 판이 아니다
        self.assertEqual(status, 3, text)
        self.assertFalse((self.home / "ran-A").exists())
        sha_a = self.sha(self.a)
        self.assertIn(f"--accept-installer-sha codex={sha_a}", text)
        self.assertTrue((self.home / ".cache/dml-setup" / f"codex-install-{sha_a}.sh").exists())
        # 승인 뒤 서버가 B를 주더라도, 승인한 A의 바이트가 그대로 실행된다.
        status, text = self.run_script("--accept-installer-sha", f"codex={sha_a}", serve=self.b)
        self.assertEqual(status, 0, text)
        self.assertTrue((self.home / "ran-A").exists())
        self.assertFalse((self.home / "ran-B").exists())

    def test_approving_one_file_never_runs_a_different_download(self):
        sha_a = self.sha(self.a)                               # A를 승인했지만 보관본이 없고 서버는 B를 준다
        status, text = self.run_script("--accept-installer-sha", f"codex={sha_a}", serve=self.b)
        self.assertEqual(status, 3, text)
        self.assertFalse((self.home / "ran-B").exists())
        self.assertIn(f"codex={self.sha(self.b)}", text)

    def test_bad_approval_values_are_refused(self):
        for value in ("codex=abc", "gemini=" + "a" * 64, "codex=" + "A" * 64):
            with self.subTest(value=value):
                status, _ = self.run_script("--accept-installer-sha", value)
                self.assertEqual(status, 2)


POWERSHELL = shutil.which("powershell") if sys.platform == "win32" else None


@unittest.skipUnless(POWERSHELL, "setup.ps1 runs on Windows (CI) only")
class SetupPs1Tests(unittest.TestCase):
    """setup.ps1의 한 단계를 대역 명령으로 불러 실패가 성공으로 덮이지 않는지 본다(R01)."""

    def step(self, body: str, repo: Path | None = None):
        script = ROOT / "tools/setup/setup.ps1"
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = repo or Path(tmp)
            test = Path(tmp) / "step.ps1"
            test.write_text(textwrap.dedent(f"""\
                $env:DML_SETUP_AS_LIBRARY = '1'
                . '{script}' -RepoDir '{repo_dir}'
                {textwrap.dedent(body)}
                Write-Host 'REACHED-END'
                exit 0
                """), encoding="ascii")
            done = subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(test)],
                                  capture_output=True, text=True, timeout=120)
        return done.returncode, done.stdout + done.stderr

    def test_a_required_tool_that_winget_cannot_install_stops_the_setup(self):
        code, out = self.step("""
            function Test-Package($p) { $false }
            function winget { $global:LASTEXITCODE = 1 }
            Install-WindowsTools
            """)
        self.assertEqual(code, 1, out)
        self.assertIn("STOP", out)
        self.assertNotIn("REACHED-END", out)

    def test_installed_but_not_visible_is_not_finished_rather_than_success(self):
        code, out = self.step("""
            function Test-Package($p) { $false }
            function winget { $global:LASTEXITCODE = 0 }
            Install-WindowsTools
            """)
        self.assertEqual(code, 2, out)
        self.assertIn("NOT FINISHED", out)

    def test_an_optional_tool_failure_is_a_warning(self):
        code, out = self.step("""
            function Test-Package($p) { $p.Id -ne 'OpenJS.NodeJS.LTS' }
            function winget { $global:LASTEXITCODE = 1 }
            Install-WindowsTools
            """)
        self.assertEqual(code, 0, out)
        self.assertIn("WARNING: Node.js LTS", out)
        self.assertIn("REACHED-END", out)

    def test_a_failed_test_dependency_install_stops_the_setup(self):
        with tempfile.TemporaryDirectory() as repo:
            (Path(repo) / ".git").mkdir()
            code, out = self.step("""
                function Invoke-Python { $global:LASTEXITCODE = 1 }
                function git { $global:LASTEXITCODE = 0 }
                Initialize-Repository
                """, repo=Path(repo))
        self.assertEqual(code, 1, out)
        self.assertIn("pip could not install", out)

    def test_the_final_check_result_is_one_number_even_when_the_checks_print(self):
        # 함수 출력이 반환값에 섞여 "준비 안 됨"이 종료 코드 0이 된 적이 있다(2026-09-25, 이 PR의 실제 확인 모드 실행).
        # 결과는 $script:FinalCode로 받고, 검사의 출력은 그대로 화면에 간다.
        with tempfile.TemporaryDirectory() as repo:
            (Path(repo) / "tools/setup").mkdir(parents=True)
            (Path(repo) / "tools/setup/check_setup.py").write_text("", encoding="ascii")
            for exit_code in (0, 1):
                with self.subTest(exit_code=exit_code):
                    code, out = self.step(f"""
                        $CheckOnly = $true
                        function Invoke-Python {{ Write-Output 'report line'; $global:LASTEXITCODE = {exit_code} }}
                        Invoke-FinalCheck
                        $result = $script:FinalCode
                        if ($result -isnot [int]) {{ Write-Host "NOT-A-NUMBER"; exit 9 }}
                        Write-Host "RESULT=$result"
                        """, repo=Path(repo))
                    self.assertEqual(code, 0, out)
                    self.assertIn(f"RESULT={exit_code}", out)
                    self.assertIn("report line", out)   # 보고는 화면에 남는다

    def test_malformed_installer_approvals_are_refused_before_ubuntu_runs(self):
        with tempfile.TemporaryDirectory() as repo:
            code, out = self.step("""
                $AcceptInstallerSha = @('codex=abc')
                function wsl.exe { throw 'must not run' }
                Install-LinuxTools
                """, repo=Path(repo))
        self.assertEqual(code, 1, out)
        self.assertIn("-AcceptInstallerSha takes", out)


if __name__ == "__main__":
    unittest.main()
