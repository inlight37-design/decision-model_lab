"""화면 갱신 순서와 시작 영수증(카드 #110, 리뷰 통합 S3). 제품의 실제 JS 함수를 Node로 돌린다. 모델·네트워크 없음.

구조 검토의 재현 `surface_probe.cjs`(AH-05)는 세 결함이 있을 때 통과하던 도구다. 여기서는 같은 세 경우를 올바른
기대값으로 본다: 늦게 온 옛 조회가 최신 화면을 덮지 않고, 한도 조회가 실패해도 실행 상태는 갱신되며, 실행을 만든
뒤 조회가 실패해도 새 실행을 잃지 않는다. 지연 Promise 대역으로 응답 순서를 정한다.
"""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "Node is required for the actual JavaScript checks")
class RefreshOrderTests(unittest.TestCase):
    def run_node(self, body):
        html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
        board = (ROOT / "app/static/role-board.js").read_text(encoding="utf-8")
        refresh = html[html.index("async function refresh("):html.index("async function loadOptions()")]
        manual = html[html.index("async function refreshQuota()"):html.index('$("quotaRefresh").onclick')]
        confirm = board[board.index("async function confirmRun()"):board.index("function closeNewRun()")]
        script = r'''
const vm = require("node:vm"), assert = require("node:assert/strict");
const SOURCE = ''' + json.dumps(refresh + "\n" + manual + "\n" + confirm) + r''';
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; });
  return {promise, resolve, reject}; };
const settle = () => new Promise(r => setTimeout(r, 0));   // 한도 응답은 따로 적용된다 — 다음 차례까지 기다린다
function page(api, extra = {}) {
  const nodes = {}, seen = {headers: 0, quotas: [], toasts: [], navigated: null, closed: false};
  const context = {selected: null, state: {version: "old", runs: []}, connection: "", settledSeen: null, quotaSignature: null, seen, nodes,
    refreshSent: 0, stateShown: 0, quotaShown: 0, refreshBusy: 0,   // 제품에서는 index.html 위쪽의 let
    api, render() {}, renderHeader() { seen.headers++; }, renderQuota(q) { seen.quotas.push(q); }, autoQuota() {},
    $: id => nodes[id] ||= {textContent: "", disabled: false, replaceChildren(...kids) { this.kids = kids; }},
    h: (tag, attrs, ...kids) => ({tag, kids}), toast(text) { seen.toasts.push(text); },
    closeNewRun() { seen.closed = true; }, renderPicked() {}, navigateTask(task, run) { seen.navigated = [task, run]; },
    ...extra};
  vm.createContext(context);
  vm.runInContext(SOURCE, context);
  return context;
}
const text = node => node && typeof node === "object" ? (node.kids || []).map(text).join(" ") : String(node);
// 끝나지 않는 await(돌아오지 않는 조회)는 Node를 종료 코드 0으로 끝낸다 — 끝까지 오지 못했으면 실패로 센다.
let finished = false;
process.on("exit", () => { if (!finished) { console.error("did not reach the end (an await never settled)"); process.exitCode = 1; } });
(async () => {
''' + body + r'''
finished = true;
})().catch(e => { console.error(e); process.exitCode = 1; });
'''
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True,
                                encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_an_older_response_that_arrives_late_does_not_overwrite_the_newer_screen(self):
        self.run_node(r'''
for (const order of [["new", "old"], ["old", "new"]]) {
  let calls = 0;
  const pending = [deferred(), deferred(), deferred(), deferred()];
  const ctx = page(() => pending[calls++].promise);
  const first = ctx.refresh(), second = ctx.refresh();          // 먼저 보낸 조회(0·1), 나중 조회(2·3)
  const answer = {old: [pending[0], pending[1]], new: [pending[2], pending[3]]};
  for (const which of order) {
    answer[which][0].resolve({version: which, runs: []}); answer[which][1].resolve({which});
    await (which === "old" ? first : second);
  }
  await settle();
  assert.equal(ctx.state.version, "new", "order " + order);
  assert.deepEqual(ctx.seen.quotas.at(-1), {which: "new"});
}
''')

    def test_a_slow_quota_holds_neither_state_polling_nor_navigation(self):
        # Codex 교차검토: 한도 조회가 끝나지 않으면 진행 중 표시가 남아 1초 조회가 멈추고 시작 뒤 이동도 기다렸다.
        self.run_node(r'''
let calls = 0;
const never = new Promise(() => {});
const run = {run_id: "new-run", task_id: "t-new", participants: []};
const ctx = page(url => { calls++; return url === "/api/account-quota" ? never
  : url === "/api/runs" ? Promise.resolve({run_id: "new-run"}) : Promise.resolve({version: calls, runs: [run]}); },
  {previewRequest: {question: "q"}});
assert.equal(await ctx.refresh(true), true);                    // 상태는 한도를 기다리지 않고 적용된다
const before = calls;
assert.equal(await ctx.refresh(true), true);                    // 다음 타이머도 건너뛰지 않는다
assert.equal(calls, before + 2);
await ctx.confirmRun();                                         // 시작 뒤 이동도 한도를 기다리지 않는다
assert.deepEqual(ctx.seen.navigated, ["t-new", "new-run"]);
''')

    def test_poll_and_quota_button_responses_apply_in_send_order(self):
        # Codex 교차검토: 조회 버튼의 새 값 뒤에 먼저 보낸 1초 조회의 한도 응답이 오면 새 값을 덮었다.
        self.run_node(r'''
for (const order of [["poll", "button"], ["button", "poll"]]) {
  const quota = {}, stateReply = Promise.resolve({version: "s", runs: []});
  const ctx = page(url => url.startsWith("/api/overview") ? stateReply
    : (quota[url === "/api/account-quota" ? "poll" : "button"] = deferred()).promise);
  const poll = ctx.refresh(), button = ctx.refreshQuota();        // 1초 조회가 먼저, 조회 버튼이 나중
  for (const which of order) { quota[which].resolve({which}); await settle(); }
  await poll; await button;
  assert.deepEqual(ctx.seen.quotas.at(-1), {which: "button"}, "order " + order);
}
// 조회 버튼이 실패하면 한도 칸에 적고 버튼을 되살린다
const failed = page(url => url === "/api/account-quota/refresh" ? Promise.reject(new Error("down"))
                                                                 : Promise.resolve({version: "s", runs: []}));
await failed.refreshQuota();
assert.ok(text(failed.nodes.accountQuota.kids[0]).includes("계정 한도를 조회하지 못했습니다"));
assert.equal(failed.nodes.quotaRefresh.disabled, false);
assert.equal(failed.nodes.quotaRefresh.textContent, "조회");
''')

    def test_a_quota_failure_does_not_block_the_run_state(self):
        self.run_node(r'''
const ctx = page(url => url.startsWith("/api/overview") ? Promise.resolve({version: "new", runs: []})
                                              : Promise.reject(new Error("quota endpoint unavailable")));
assert.equal(await ctx.refresh(), true);
assert.equal(ctx.state.version, "new");
assert.equal(ctx.connection, "");                               // 연결 오류로 보지 않는다
await settle();
assert.ok(text(ctx.nodes.accountQuota.kids[0]).includes("계정 한도를 조회하지 못했습니다"));
await ctx.refresh(); await settle();
assert.equal(ctx.quotaSignature, "failed");                     // 같은 안내를 매초 다시 그리지 않는다
''')

    def test_navigation_does_not_accept_detail_for_the_previous_selection(self):
        self.run_node(r'''
const pending = [], urls = [];
const ctx = page(url => { urls.push(url); const d = deferred(); pending.push(d); return d.promise; }, {selected: "old"});
const first = ctx.refresh();
ctx.selected = "new";
pending[0].resolve({version: "old-detail", runs: []}); pending[1].resolve({});
assert.equal(await first, false);
assert.equal(ctx.state.version, "old");
const second = ctx.refresh();
pending[2].resolve({version: "new-detail", runs: [], settled_real: 4}); pending[3].resolve({});
assert.equal(await second, true);
assert.equal(ctx.settledSeen, 4);
assert.equal(urls[0], "/api/overview?run=old");
assert.equal(urls[2], "/api/overview?run=new");
''')

    def test_the_timer_skips_while_busy_but_an_action_refresh_is_never_dropped(self):
        self.run_node(r'''
let calls = 0;
const pending = [];
const ctx = page(() => { const d = deferred(); pending.push(d); calls++; return d.promise; });
const timer = ctx.refresh(true);                                // 1초 타이머의 조회가 진행 중이다
assert.equal(await ctx.refresh(true), false);                   // 다음 타이머는 건너뛴다
assert.equal(calls, 2);
const action = ctx.refresh();                                   // 버튼 동작 뒤의 갱신 요구는 새로 보낸다
assert.equal(calls, 4);
pending[2].resolve({version: "after-action", runs: []}); pending[3].resolve({}); await action;
pending[0].resolve({version: "before-action", runs: []}); pending[1].resolve({}); await timer;
assert.equal(ctx.state.version, "after-action");
ctx.refresh(true);
assert.equal(calls, 6);                                         // 끝난 뒤에는 타이머가 다시 돈다
''')

    def test_a_started_run_is_kept_when_the_following_refresh_fails(self):
        self.run_node(r'''
const failing = url => url === "/api/runs" ? Promise.resolve({run_id: "new-run"})
  : url.startsWith("/api/overview") ? Promise.reject(new Error("temporary state failure")) : Promise.resolve({});
for (const [task, expected] of [[undefined, null], ["t-old", "t-old"]]) {
  const ctx = page(failing, {previewRequest: {question: "q", ...(task ? {task_id: task} : {})}, picked: ["x"]});
  await ctx.confirmRun();
  assert.equal(ctx.seen.closed, true);
  assert.deepEqual(ctx.seen.navigated, [expected, "new-run"]);   // 응답의 run_id로 그 실행을 고른다
  assert.equal(ctx.nodes.formErr.textContent, "");                // 닫힌 창의 오류 칸에 쓰지 않는다
  assert.ok(ctx.seen.toasts.at(-1).includes("상태를 확인하는 중"));
  assert.equal(ctx.connection, "temporary state failure");
}
// 조회가 새 실행을 가져오면 그 작업으로 간다
const run = {run_id: "new-run", task_id: "t-new", participants: []};
const ok = page(url => url === "/api/runs" ? Promise.resolve({run_id: "new-run"})
  : url.startsWith("/api/overview") ? Promise.resolve({runs: [run]}) : Promise.resolve({}), {previewRequest: {question: "q"}});
await ok.confirmRun();
assert.deepEqual(ok.seen.navigated, ["t-new", "new-run"]);
assert.ok(ok.seen.toasts.at(-1).includes("모두 끝나면"));
// 시작 자체가 거절되면 창에 남아 이유를 보인다
const refused = page(() => Promise.reject(new Error("확인한 입력에서 바뀌었습니다")), {previewRequest: {question: "q"}});
await refused.confirmRun();
assert.equal(refused.seen.closed, false);
assert.equal(refused.nodes.formErr.textContent, "확인한 입력에서 바뀌었습니다");
assert.equal(refused.nodes.confirmStart.disabled, false);
''')


if __name__ == "__main__":
    unittest.main()
