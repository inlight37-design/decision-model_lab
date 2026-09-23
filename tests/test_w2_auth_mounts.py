"""tools/w2/auth_mounts.py 검사(N3). 실제 CLI를 실행하지 않는다 — 연결 조합과 출력 가리기만 본다."""
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from tools.w2 import auth_mounts


class AuthMountCaseTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="dml-n3-test-"))
        self.addCleanup(shutil.rmtree, self.home, True)
        (self.home / ".claude").mkdir()
        (self.home / ".claude/.credentials.json").write_text("{}", encoding="utf-8")
        (self.home / ".claude.json").write_text("{}", encoding="utf-8")
        self.exe = self.home / ".local/share/claude/versions/9.9.9"
        self.exe.parent.mkdir(parents=True)
        self.exe.write_text("", encoding="utf-8")

    def test_only_the_current_case_writes_and_narrowed_cases_are_read_only(self):
        with mock.patch.object(auth_mounts, "HOME", str(self.home)), \
                mock.patch("os.path.expanduser", lambda p: p.replace("~", str(self.home), 1)):
            ro, rw = auth_mounts.case_mounts("claude-code", str(self.exe), None)
            self.assertEqual(sorted(rw), sorted([str(self.home / ".claude"), str(self.home / ".claude.json")]))
            for label, paths in auth_mounts.CASES["claude-code"][1:]:
                with self.subTest(label):
                    ro, rw = auth_mounts.case_mounts("claude-code", str(self.exe), paths)
                    self.assertEqual(rw, ())                                   # 좁힌 조합은 쓰지 않는다
                    self.assertIn(str(self.exe.resolve()), [str(Path(p).resolve()) for p in ro])
                    self.assertEqual(len(ro), 1 + len(paths))

    def test_output_text_hides_home_email_and_token_like_strings(self):
        with mock.patch.object(auth_mounts, "HOME", "/home/someone"):
            line = auth_mounts.hide("Logged in as someone@example.com via /home/someone/.codex "
                                    "token eyJhbGciOiJIUzI1NiJ9abcdefgh")
            path = auth_mounts.tilde("/home/someone/.codex/packages/0.156.1-x86_64-unknown-linux-musl")
        self.assertEqual(line, "Logged in as <email> via ~/.codex token <redacted>")
        self.assertEqual(path, "~/.codex/packages/0.156.1-x86_64-unknown-linux-musl")   # 경로의 긴 이름은 가리지 않는다


if __name__ == "__main__":
    unittest.main()
