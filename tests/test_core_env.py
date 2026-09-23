"""core.env 검사 — 실행 코어가 조사 도구에 기대지 않고(경계 리뷰 R05), WSL에서 Windows CLI를 다시
부르지 않는다(인계 2절 15). CLI·모델은 부르지 않는다."""
from pathlib import Path
import sys
import tempfile
import unittest

from core import env
from tools import runtime_inventory

CORE = Path(__file__).resolve().parents[1] / "core"


class DependencyDirectionTests(unittest.TestCase):
    def test_core_does_not_import_tools(self):
        for path in CORE.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            with self.subTest(module=path.name):
                self.assertNotRegex(text, r"(?m)^\s*(from|import)\s+tools\b")

    def test_the_inventory_records_the_same_variable_list(self):
        self.assertIs(runtime_inventory.ENV_VARS, env.ENV_VARS)
        self.assertIs(runtime_inventory.fresh_environment, env.fresh_environment)


class PathTests(unittest.TestCase):
    def test_an_empty_or_missing_child_path_does_not_fall_back_to_ours(self):
        """WSL2 리뷰 WM-05. shutil.which는 path=None이면 이 프로세스의 PATH를 쓴다."""
        command = Path(sys.executable).stem   # 이 프로세스의 PATH로는 찾을 수 있는 이름
        with self.assertRaises(env.EnvError):
            env.resolve(command, {"PATH": ""})
        with self.assertRaises(env.EnvError):
            env.resolve(command, {"HOME": "/h"})


class WindowsBinaryTests(unittest.TestCase):
    def test_windows_binaries_are_recognised(self):
        for path in ("/mnt/c/Users/u/AppData/codex.exe", "/mnt/d/tools/claude", "/mnt/c", "/usr/local/bin/agy.EXE"):
            with self.subTest(path=path):
                self.assertTrue(env.is_windows_binary(path))
        for path in ("/usr/local/bin/claude", "/home/u/.local/bin/codex", "/mnt/data/x", "/mnt/cc/x"):
            with self.subTest(path=path):
                self.assertFalse(env.is_windows_binary(path))

    @unittest.skipIf(env.IS_WINDOWS, "WSL·Linux의 PATH 규칙")
    def test_child_path_drops_windows_drives(self):
        child, _ = env.child_env({"PATH": "/usr/bin:/mnt/c/Windows/system32:/home/u/.local/bin:/mnt/d"})
        self.assertEqual(child["PATH"], "/usr/bin:/home/u/.local/bin")

    @unittest.skipIf(env.IS_WINDOWS, "WSL·Linux의 PATH 규칙")
    def test_resolve_refuses_a_windows_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("codex.exe", "codex"):
                path = Path(tmp) / name
                path.write_text("#!/bin/sh\n")
                path.chmod(0o755)
            with self.assertRaises(env.EnvError):
                env.resolve("codex.exe", {"PATH": tmp})
            self.assertEqual(env.resolve("codex", {"PATH": tmp}), str(Path(tmp) / "codex"))
            # 이름은 Linux 것처럼 보여도 링크가 Windows 실행 파일을 가리키면 거절한다
            (Path(tmp) / "linked").symlink_to(Path(tmp) / "codex.exe")
            with self.assertRaises(env.EnvError):
                env.resolve("linked", {"PATH": tmp})
            # 확장자 없는 PE도 내용('MZ')으로 거절한다
            pe = Path(tmp) / "plain"
            pe.write_bytes(b"MZ\x90\x00synthetic")
            pe.chmod(0o755)
            with self.assertRaises(env.EnvError):
                env.resolve("plain", {"PATH": tmp})


if __name__ == "__main__":
    unittest.main()
