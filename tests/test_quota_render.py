"""계정 패널의 실제 JavaScript: Codex 행, 요청 모델의 가용 목록, 마지막 실제 실행의 Claude 한도. 모델 호출 없음."""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node is required for the actual JavaScript rendering checks")
class QuotaRenderTests(unittest.TestCase):
    def test_panel_lines_keep_providers_units_and_staleness_apart(self):
        html = (Path(__file__).resolve().parents[1] / "app/static/index.html").read_text(encoding="utf-8")
        functions = html[html.index("function quotaPeriod("):html.index("function renderQuota(")]
        script = r'''
const assert = require("node:assert/strict");
''' + functions + r'''
const text = lines => lines.map(([, t]) => t).join("\n");
const cls = (lines, needle) => lines.find(([, t]) => t.includes(needle))[0];
const mock = quotaLines({enabled: false, claude: {configured: false, quota: null}});
assert.equal(mock.length, 1);
assert.ok(text(mock).includes("모의 모드에는 계정 사용량이 없습니다"));
const now = Math.floor(Date.now() / 1000);
const data = {enabled: true, refresh_failed: false, requested_model: "gpt-test",
  quota: {observed_at: now, limits: [{limit_id: "codex", window: "primary", used_percent: 25, window_minutes: 300,
                                      resets_at: now + 600, status: "observed"}]},
  models: {status: "observed", ids: ["gpt-test"], truncated: false},
  claude: {configured: true, quota: {observed_at: now - 500, limit_state: "allowed_warning", limits: [
    {limit_id: "claude", window: "five_hour", used_percent: 33.3, window_minutes: null, resets_at: now + 900, status: "stale"},
    {limit_id: "claude", window: "seven_day", used_percent: null, window_minutes: null, resets_at: null, status: "unknown"}]}}};
const lines = quotaLines(data);
const all = text(lines);
assert.ok(all.includes("codex · 5시간: 잔여 75% · 사용 25%"));
assert.ok(all.includes("요청 모델 gpt-test: 이 계정의 가용 목록에 있음"));
assert.ok(all.includes("claude · 5시간 창: 잔여 66.7% · 사용 33.3% (과거 관측값 · 다음 실제 실행 때 갱신)"));
assert.ok(all.includes("claude · 7일 창: 미확인"));
assert.ok(all.includes("한도 경고(allowed_warning)"));
assert.equal(cls(lines, "claude · 5시간 창"), "kv st-unknown");
assert.equal(cls(lines, "codex · 5시간"), "kv");
const missing = text(quotaLines({...data, models: {status: "unavailable"},
                                  claude: {configured: true, quota: {observed_at: null, limits: []}}}));
assert.ok(missing.includes("가용 목록에 미확인"));
assert.ok(missing.includes("Claude 한도 미확인"));
assert.ok(text(quotaLines({...data, models: {status: "observed", ids: ["other"], truncated: true}}))
  .includes("목록 일부만 받아 미확인"));
'''
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
