"""헤드리스 실행(app.run): 서버와 같은 controller를 화면 없이 끝까지 돌린다. 모의 CLI만 쓰며 모델 호출이 없다."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from app import run as headless
from app.live_config import Provider


class HeadlessRunTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.out = self.tmp / "result.json"

    def call(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = headless.main(list(args))
            except SystemExit as exc:   # argparse
                code = exc.code
        return code, stdout.getvalue() + stderr.getvalue()

    def mock(self, *extra):
        return self.call("--mock", "--data-dir", str(self.tmp / "ledger"), "--question", "무엇을 할까?",
                         "--policy", "include-unverified", "--out", str(self.out), *extra)

    def result(self):
        return json.loads(self.out.read_text(encoding="utf-8"))

    def test_the_whole_flow_runs_to_a_decision_report(self):
        code, _ = self.mock("--participants", "claude,codex", "--synthesize", "mock")
        self.assertEqual(code, 0)
        result = self.result()
        self.assertEqual((result["schema"], result["mode"], result["phase"]), ("a1-headless-run/1", "mock", "revealed"))
        self.assertEqual([p["state"] for p in result["participants"]], ["accepted", "accepted"])
        self.assertEqual(result["draft_report"]["schema"], "a1-draft-report/4")
        self.assertEqual(result["decision_report"]["schema"], "a1-decision-report/4")
        self.assertEqual(result["decision_report"]["synthesis"]["mode"], "mock_extractive")
        self.assertEqual(result["synthesis_requests"], [{"synthesizer": "mock", "started": True}])

    def test_without_a_synthesis_there_is_no_decision_report(self):
        code, _ = self.mock("--participants", "claude")
        self.assertEqual(code, 0)
        self.assertIsNone(self.result()["decision_report"])

    def test_a_dropped_participant_waits_for_an_explicit_reduction_approval(self):
        code, _ = self.mock("--participants", "claude,codex", "--mock-behavior", "codex=fail")
        self.assertEqual(code, 1)   # 공개되지 않았다
        self.assertEqual(self.result()["phase"], "drafting")
        self.assertTrue(self.result()["gate"]["can_approve_reduction"])
        self.out.unlink()
        # 줄어든 구성이 정족수를 채울 때만 승인으로 공개된다(정족수 2에 한 명만 남으면 승인해도 공개되지 않는다).
        code, _ = self.call("--mock", "--data-dir", str(self.tmp / "ledger2"), "--question", "q", "--policy",
                            "include-unverified", "--participants", "claude,codex", "--mock-behavior", "codex=fail",
                            "--min-independent", "1", "--approve-reduction", "--out", str(self.out))
        self.assertEqual(code, 0)
        self.assertEqual(self.result()["phase"], "revealed")

    def test_shared_sources_are_fixed_into_the_run(self):
        sources = self.tmp / "sources"
        sources.mkdir()
        (sources / "notes.txt").write_text("자료 한 줄", encoding="utf-8")
        code, _ = self.mock("--participants", "claude", "--sources-dir", str(sources))
        self.assertEqual(code, 0)
        self.assertEqual([s["name"] for s in self.result()["draft_report"]["input"]["sources"]], ["notes.txt"])

    def test_a_refused_readiness_check_starts_nothing_and_creates_no_ledger(self):
        providers = (Provider("codex", "m", self.tmp / "inv.json", 1, None),)
        with mock.patch.object(headless, "load_live_config", return_value=providers), \
                mock.patch("app.readiness.check", return_value={"adapter_id": "codex", "eligible": False}):
            code, text = self.call("--live-config", str(self.tmp / "live.json"), "--data-dir", str(self.tmp / "live"),
                                   "--question", "q", "--participants", "codex")
        self.assertEqual(code, 3)
        self.assertIn('"eligible": false', text)
        self.assertFalse((self.tmp / "live").exists())

    def test_argument_errors(self):
        cases = (("--synthesize", "codex"),            # 모의에서는 실제 합성을 부를 수 없다
                 ("--synthesize", "gemini"),
                 ("--mock-behavior", "codex=explode"),
                 ("--participants", "claude,claude"))
        for extra in cases:
            with self.subTest(extra=extra):
                code, _ = self.mock(*extra)
                self.assertEqual(code, 2)
        code, _ = self.mock("--participants", "chatgpt-app")   # 수동 참여자는 화면에서만
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
