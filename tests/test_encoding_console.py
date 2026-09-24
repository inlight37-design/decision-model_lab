"""Checks must report results even through a Windows ANSI (CP1252) output pipe."""
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import check_encoding, print_code_hashes, validate_design_tokens

try:
    import jsonschema  # noqa: F401
    HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover - 환경에 따라 달라진다
    HAS_JSONSCHEMA = False


class ConsoleTests(unittest.TestCase):
    def run_cp1252(self, module, argv):
        """module.main()을 CP1252 출력에 붙여 돌리고 (반환값, UTF-8로 읽은 출력)을 돌려준다."""
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252")
        try:
            with mock.patch.object(module.sys, "stdout", stream), mock.patch.object(module.sys, "argv", argv):
                status = module.main()
                stream.flush()
            return status, raw.getvalue().decode("utf-8")
        finally:
            stream.close()

    def test_cp1252_stdout_reports_both_success_and_failure_in_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            for data, status, message in (("한글\n".encode("utf-8"), 0, "PASS:"),
                                          (b"\xef\xbb\xbftext", 1, "인코딩 문제:")):
                with self.subTest(status=status):
                    path.write_bytes(data)
                    result, text = self.run_cp1252(check_encoding, ["check_encoding.py", str(path)])
                    self.assertEqual(result, status)
                    self.assertIn(message, text)

    def test_cp1252_stdout_does_not_break_the_stdlib_checks(self):
        # PR #39 병합 검토(2026-09-24 N1): 이 도구들은 한글 결과 줄을 쓰다 UnicodeEncodeError로 끝났다.
        for module, message in ((validate_design_tokens, "범위:"), (print_code_hashes, "로컬 파일의 해시")):
            with self.subTest(tool=module.__name__):
                status, text = self.run_cp1252(module, [module.__name__])
                self.assertEqual(status, 0)
                self.assertIn(message, text)

    @unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema 미설치: python -m pip install -r requirements-design.txt")
    def test_cp1252_stdout_does_not_break_the_schema_checks(self):
        from tools import validate_design, validate_sources
        for module in (validate_design, validate_sources):
            with self.subTest(tool=module.__name__):
                status, text = self.run_cp1252(module, [module.__name__])
                self.assertEqual(status, 0)
                self.assertIn("범위:", text)


if __name__ == "__main__":
    unittest.main()
