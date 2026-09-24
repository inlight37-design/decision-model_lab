"""The encoding checker must report results even through a Windows ANSI output pipe."""
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import check_encoding


class ConsoleTests(unittest.TestCase):
    def test_cp1252_stdout_reports_both_success_and_failure_in_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            for data, status, message in (("한글\n".encode("utf-8"), 0, "PASS:"),
                                          (b"\xef\xbb\xbftext", 1, "인코딩 문제:")):
                with self.subTest(status=status):
                    path.write_bytes(data)
                    raw = io.BytesIO()
                    stream = io.TextIOWrapper(raw, encoding="cp1252")
                    try:
                        with mock.patch.object(check_encoding.sys, "stdout", stream), \
                                mock.patch.object(check_encoding.sys, "argv", ["check_encoding.py", str(path)]):
                            self.assertEqual(check_encoding.main(), status)
                            stream.flush()
                        self.assertIn(message, raw.getvalue().decode("utf-8"))
                    finally:
                        stream.close()


if __name__ == "__main__":
    unittest.main()