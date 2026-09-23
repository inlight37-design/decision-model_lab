"""tools/w2/codex_sandbox.py·codex_profile.py 검사. 실제 Codex는 부르지 않는다 — 넘기는 권한 profile 인자의 모양과
네트워크 없는 exec 진단의 격리 인자만 본다."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

from core import runner
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

    def test_the_helper_opens_the_login_file_without_reading_it(self):
        """리뷰 R01: 내용을 읽지 않고 열었다 닫기만 한다. 결과는 errno 이름이다."""
        source = observe.K46_HELPER.format(nonce="n")
        self.assertEqual(source.count("auth.json"), 1)
        self.assertNotIn(".read(", source)
        self.assertIn("os.close(os.open(", source)
        compile(source, "k46_check.py", "exec")

    def test_the_helper_reports_errno_names_when_run(self):
        """helper를 합성 HOME(인증 파일 없음, 쓸 수 없는 작업 폴더가 아님)에서 실제로 돌려 줄 모양을 본다."""
        root = tempfile.mkdtemp(prefix="dml-k46-helper-")
        self.addCleanup(shutil.rmtree, root, True)
        work, inputs = os.path.join(root, "work"), os.path.join(root, "input")
        os.makedirs(work)
        os.makedirs(inputs)
        Path(inputs, "allowed.txt").write_text("x", encoding="utf-8")
        helper = Path(inputs, observe.K46_FILE)
        helper.write_text(observe.K46_HELPER.format(nonce="n0"), encoding="utf-8")
        out = subprocess.run([sys.executable, str(helper)], cwd=work, env={**os.environ, "HOME": root},
                             capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(observe.K46_LINE.match(out).groups(), ("n0", "ok", "ok", "denied:ENOENT"))


class WriteStateTests(unittest.TestCase):
    def test_a_missing_result_is_not_a_refusal(self):
        """리뷰 R09: 셸이 시작하지 못해 결과 줄이 없으면 거절이 아니라 검사 미실행이다."""
        self.assertEqual(codex_sandbox.write_state(None, False), "not_run")
        self.assertEqual(codex_sandbox.write_state("2", False), "denied")
        self.assertEqual(codex_sandbox.write_state("0", False), "allowed")
        self.assertEqual(codex_sandbox.write_state("2", True), "allowed")      # 파일이 남았으면 막히지 않은 것이다


@unittest.skipUnless(sys.platform == "linux", "Linux·WSL 진단이다 — 합성 HOME이 POSIX 경로여야 한다")
class SyntheticHomeTests(unittest.TestCase):
    def test_the_default_diagnostic_never_mounts_the_real_login_folder(self):
        """리뷰 질문 3·9: 기본 진단은 합성 HOME의 가짜 인증 파일만 쓴다. 사용자의 실제 ~/.codex는 연결하지 않는다."""
        boxes = []

        def fake_offline(argv, box, stdin_text, timeout):
            boxes.append((argv, box))
            line = "K46 diagnostic write=denied:EROFS input=ok auth=denied:EACCES end\n"
            return runner.RunResult(tuple(argv), runner.EXITED, 0, line, "", False, False, 1, 0, True,
                                    containment=runner.PID_NAMESPACE)

        with mock.patch.object(codex_profile, "offline", side_effect=fake_offline):
            report = codex_profile.synthetic(sys.executable)
        self.assertEqual(set(report["helper"]), set(codex_profile.profile_variants("/h")))
        real_codex = os.path.join(codex_profile.HOME, ".codex")
        for argv, box in boxes:
            self.assertNotEqual(box.home, codex_profile.HOME)
            self.assertEqual(box.read_write, (os.path.join(box.home, ".codex"),))
            self.assertFalse(any(p == real_codex for p in box.read_only + box.read_write))
            if "-c" in argv:                                                    # profile은 합성 HOME의 파일을 막는다
                self.assertIn(f'"{box.home}/.codex/auth.json" = "deny"', argv[argv.index("-c") + 1])
        self.assertEqual(report["helper"]["no profile (control)"]["result"],
                         {"write": "denied:EROFS", "input": "ok", "auth": "denied:EACCES"})


if __name__ == "__main__":
    unittest.main()
