"""공통 자료 칸 아래 안내의 실제 JavaScript(카드 #90). 모델 호출 없음.

합계를 보이고, 실제 Claude 참여자가 있을 때만 카드 #61의 두 관측값을 붙인다. 시작을 막지 않으므로 여기서는 글만 본다.
"""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node is required for the actual JavaScript rendering checks")
class SourceNoteRenderTests(unittest.TestCase):
    def test_total_is_shown_and_the_claude_observation_only_for_a_live_claude(self):
        html = (Path(__file__).resolve().parents[1] / "app/static/index.html").read_text(encoding="utf-8")
        functions = html[html.index("function sourceNote("):html.index("function updateSourceNote(")]
        script = r'''
const assert = require("node:assert/strict");
''' + functions + r'''
assert.equal(sourceNote([], true), "");
assert.equal(sourceNote([17, 17], false), "자료 2개 · 합계 34바이트");
const big = sourceNote([260630, 260637, 260620, 260598, 272], true);
assert.ok(big.startsWith("자료 5개 · 합계 1,043 KB · Claude 참여자는"), big);
assert.ok(big.includes("약 490 KB에 104초") && big.includes("180초를 넘겨"), big);
const noClaude = sourceNote([260630, 260637, 260620, 260598, 272], false);
assert.equal(noClaude, "자료 5개 · 합계 1,043 KB");
'''
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=15,
                                encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
