"""tools/w2/codex_prompt_input.py 검사(E2). 실제 CLI·모델은 부르지 않는다 — 격리 실행을 가짜 결과로 바꾼다."""
import json
import unittest
from unittest import mock

from core import adapters, runner
from tools.w2 import codex_prompt_input as probe


def rendered(*texts):
    items = [{"type": "message", "role": "developer", "content": [{"type": "input_text", "text": "<skills_instructions>x"}]},
             {"type": "message", "role": "user", "content": [{"type": "input_text", "text": t} for t in texts]}]
    return runner.RunResult(("x",), runner.EXITED, 0, json.dumps(items), "", False, False, 1, 0, True,
                            containment=runner.PID_NAMESPACE)


class PromptInputTests(unittest.TestCase):
    def test_the_values_are_the_participant_plans(self):
        values = probe.participant_values("/home/u")
        self.assertEqual(values[1::2], [*adapters.codex_permissions("/home/u"), adapters.CODEX_APPS_OFF,
                                        adapters.CODEX_NO_PROJECT_DOCS])
        self.assertEqual(set(values[::2]), {"-c"})

    def test_the_summary_keeps_shapes_and_flags_but_not_the_text(self):
        secret = "PRIVATE-INSTRUCTION-TEXT"
        with mock.patch.object(probe.isolation, "run", return_value=rendered(f"<INSTRUCTIONS>{secret}</INSTRUCTIONS>")), \
                mock.patch.object(probe.isolation, "participant_mounts", return_value=((), (), ())):
            summary, text = probe.render("/x/bin/codex", "/home/u", "/tmp/w", [])
        self.assertTrue(summary["instructions_block"])
        self.assertEqual([item["role"] for item in summary["items"]], ["developer", "user"])
        self.assertIn("INSTRUCTIONS", summary["items"][1]["tags"])
        self.assertIn(secret, text)                          # 비교에는 쓰지만
        self.assertNotIn(secret, json.dumps(summary))        # 요약에는 옮기지 않는다

    def test_output_that_is_not_json_is_reported_without_its_text(self):
        broken = runner.RunResult(("x",), runner.EXITED, 1, "not json PRIVATE", "boom", False, False, 1, 0, True)
        with mock.patch.object(probe.isolation, "run", return_value=broken), \
                mock.patch.object(probe.isolation, "participant_mounts", return_value=((), (), ())):
            summary, text = probe.render("/x/bin/codex", "/home/u", "/tmp/w", [])
        self.assertIsNone(text)
        self.assertFalse(summary["json"])
        self.assertNotIn("PRIVATE", json.dumps(summary))


if __name__ == "__main__":
    unittest.main()
