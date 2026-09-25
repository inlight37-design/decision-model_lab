"""계정 패널의 실제 JavaScript: provider 카드와 창별 게이지, 요청 모델, 지난 값·미확인. 모델 호출 없음."""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node is required for the actual JavaScript rendering checks")
class QuotaRenderTests(unittest.TestCase):
    def test_cards_keep_providers_units_and_staleness_apart(self):
        html = (Path(__file__).resolve().parents[1] / "app/static/index.html").read_text(encoding="utf-8")
        functions = html[html.index("function quotaPeriod("):html.index("const GAUGES")]
        script = r'''
const assert = require("node:assert/strict");
''' + functions + r'''
const now = 1790300000;
const mock = quotaCards({enabled: false, claude: {configured: false, quota: null}}, now);
assert.equal(mock.cards.length, 0);
assert.ok(mock.empty.includes("모의 모드에는 계정 사용량이 없습니다"));

const data = {enabled: true, refresh_failed: false, requested_model: "gpt-test",
  quota: {observed_at: now - 30, limits: [
    {limit_id: "codex", window: "primary", used_percent: 25, window_minutes: 300, resets_at: now + 600, status: "observed"},
    {limit_id: "codex", window: "secondary", used_percent: null, window_minutes: null, resets_at: null, status: "unknown"}]},
  models: {status: "observed", ids: ["gpt-test"], truncated: false},
  claude: {configured: true, quota: {observed_at: now - 3700, limit_state: "allowed_warning", limits: [
    {limit_id: "claude", window: "five_hour", used_percent: 33.3, window_minutes: null, resets_at: now + 900, status: "stale"},
    {limit_id: "claude", window: "seven_day", used_percent: null, window_minutes: null, resets_at: null, status: "unknown"}]}}};
const view = quotaCards(data, now);
const [codex, claude] = view.cards;
// Codex: 받은 창 하나만 게이지. 응답에 비어 있던 두 번째 칸은 한도가 아니라서 빠진다.
assert.equal(codex.name, "Codex");
assert.equal(codex.source, "방금 조회");
assert.deepEqual(codex.gauges, [{label: "5시간", used: 25, state: "observed", reset: "10분 뒤 초기화"}]);
assert.equal(codex.stale, false);
// 요청 모델이 목록에 있으면 알림이 아니라 설명(접힘)으로만 간다
assert.equal(codex.alerts.length, 0);
assert.ok(view.notes.some(t => t.includes("요청 모델(gpt-test)은 이 계정의 가용 목록에 있습니다")));
// Claude: 마지막 실제 실행 때의 값. 지난 값은 지난 값으로, 모르는 창은 0이 아니라 미확인(null)으로.
assert.equal(claude.source, "마지막 실제 실행 때 · 1시간 전");
assert.equal(claude.stale, true);
assert.deepEqual(claude.gauges.map(g => [g.label, g.used, g.state]), [["5시간", 33.3, "stale"], ["7일", null, "unknown"]]);
assert.deepEqual(claude.alerts, [["warn", "그 실행 때 Claude가 한도 경고(allowed_warning)를 알렸어요."]]);
assert.ok(view.notes.some(t => t.includes("사용량만 묻는 통로가 없어서")));
assert.ok(view.notes.some(t => t.includes("두 계정을 더하지 않습니다")));

// 요청 모델이 목록에 없거나 모르면 알린다
const missing = quotaCards({...data, models: {status: "observed", ids: ["other"], truncated: false}}, now).cards[0];
assert.ok(missing.alerts[0][1].endsWith("없어요."));
const partial = quotaCards({...data, models: {status: "observed", ids: ["other"], truncated: true}}, now).cards[0];
assert.ok(partial.alerts[0][1].includes("목록 일부만 받음"));
const unlisted = quotaCards({...data, models: {status: "unavailable"}}, now).cards[0];
assert.ok(unlisted.alerts[0][1].includes("확인하지 못했어요"));
// 조회 실패, 아직 조회 전, Claude 실행 전
const failed = quotaCards({...data, refresh_failed: true}, now).cards[0];
assert.ok(failed.alerts[0][1].includes("지난 값"));
const none = quotaCards({...data, quota: null, claude: {configured: true, quota: {observed_at: null, limits: []}}}, now);
assert.equal(none.cards[0].empty, "Codex 한도 미확인");
assert.deepEqual(none.cards[0].gauges, []);
assert.ok(none.cards[1].empty.startsWith("Claude 한도 미확인"));
// 초기화까지 하루가 넘으면 날짜로 적는다
assert.match(fmtUntil(now + 3 * 86400, now), /^\d+월 \d+일 (오전|오후) \d+시 초기화$/);
assert.equal(fmtAgo(now - 125, now), "2분 전");
'''
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=15,
                                encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
