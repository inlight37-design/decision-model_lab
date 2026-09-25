"""실제 합성 결과 화면의 실제 JavaScript: 원문 일치·원문에 없음·추가 주장·반례·미해결 줄. 모델 호출 없음."""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node is required for the actual JavaScript rendering checks")
class ModelSynthesisRenderTests(unittest.TestCase):
    def test_lines_mark_unmatched_quotes_and_unsupported_claims(self):
        html = (Path(__file__).resolve().parents[1] / "app/static/index.html").read_text(encoding="utf-8")
        functions = html[html.index("function modelSynthesisLines("):html.index("function modelSynthesisView(")]
        script = r'''
const assert = require("node:assert/strict");
''' + functions + r'''
const q = (draft, pid, text, ok) => ({draft, pid, text, source_check: ok ? "exact_match" : "not_found"});
const lines = modelSynthesisLines({
  synthesizer: {adapter_id: "claude-code", requested_model: "m", reported_models: ["m"], model_match: true},
  checks: {quotes: 3, exact_matches: 2, unsupported_additions: 1},
  claims: [{id: "S001", statement: "결론이 갈린다", support: "quoted", quotes: [q("D1", "claude", "결론은 A다.", true)]},
           {id: "S002", statement: "D가 낫다", support: "unsupported_addition", quotes: [q("D9", null, "결론은 D다.", false)]}],
  disagreements: [{topic: "결론", quotes: []}],
  strongest_counterexample: {statement: "B", quotes: [q("D1", "claude", "반례는 B다.", true)]},
  unresolved: ["비용 자료 없음"]});
const text = lines.map(([, t]) => t).join("\n");
assert.ok(text.includes("인용 3개 중 원문 일치 2개 · 원문에 없는 추가 주장 1개 · 사실 검증 안 함"));
assert.ok(text.includes("원문 일치 · D1(claude) “결론은 A다.”"));
assert.ok(text.includes("원문에 없음 · D9(?) “결론은 D다.”"));
assert.ok(text.includes("S002 D가 낫다 — 원문에 없는 추가 주장"));
assert.ok(text.includes("가장 강한 반례 · B"));
assert.ok(text.includes("미해결 · 비용 자료 없음"));
assert.equal(lines.find(([, t]) => t.startsWith("S002"))[0], "claim st-unknown");
assert.equal(lines.find(([, t]) => t.includes("D9(?)"))[0], "kv st-unknown");
assert.ok(!text.includes("모델 불일치"));
'''
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_controls_offer_a_new_call_except_while_running_or_unconfirmed(self):
        # 사용자 결정(2026-09-25): 같은 실행에 합성자를 바꿔 여러 번 부를 수 있다. 끝났는지 모르는 시도가 있을 때만 막는다.
        html = (Path(__file__).resolve().parents[1] / "app/static/index.html").read_text(encoding="utf-8")
        parts = html[html.index("// ---- 부품"):html.index("// ---- 계정 한도")]   # 접기·배지(h만 쓴다)
        functions = html[html.index("function modelControls("):html.index("function synthesisPanel(")]
        script = r"""
const assert = require("node:assert/strict");
let liveMode = true, confirmed = false, synthesizers = [], synthChoice = null;
const calls = [];
const window = {confirm: () => confirmed};
const act = (...args) => calls.push(args);
const downloaded = [];
const downloadReport = (...args) => downloaded.push(args);
const h = (tag, attrs, ...children) => ({tag, attrs, children: children.flat(Infinity)});
const walk = node => node && typeof node === "object" ? [node, ...node.children.flatMap(walk)] : [];
const label = node => node.children.filter(c => typeof c === "string").join("");
""" + parts + functions + r"""
// 접기의 머리 버튼은 동작이 아니라 펼치기다
const buttonsOf = run => walk(modelControls(run)).filter(n => n.tag === "button" && !/collapse-toggle/.test(n.attrs.class));
const folded = node => walk(node).some(n => /(^| )collapse( |$)/.test((n.attrs || {}).class || ""));
const run = {run_id: "r1", participants: [{transport: "cli", adapter_id: "claude-code", label: "C"}]};
assert.deepEqual(buttonsOf(run).map(label), ["실제 합성(호출 1회)"]);
for (const status of ["completed", "failed", "acknowledged"]) {
  run.model_synthesis = {status, message: "state"};
  run.model_syntheses = [{attempt: "a1", status, result: null}];
  assert.deepEqual(buttonsOf(run).map(label), ["한 번 더 합성(호출 1회)"], status);
}
run.model_synthesis = {status: "running"};
assert.equal(buttonsOf(run).length, 0);
// Unknown termination blocks new calls; only the exact acknowledgement is offered, live or not.
run.model_synthesis = {status: "unknown", attempts: ["exact-attempt"], message: "unknown"};
for (const live of [false, true]) {
  liveMode = live;
  assert.equal(buttonsOf(run).length, 1);
  assert.ok(label(buttonsOf(run)[0]).startsWith("종료 직접 확인"));
}
const ack = buttonsOf(run)[0];
ack.attrs.onclick();
assert.equal(calls.length, 0);
confirmed = true;
ack.attrs.onclick();
assert.deepEqual(calls, [["/api/runs/r1/acknowledge-synthesis", {attempt: "exact-attempt"}]]);
// A reply that failed the format check is shown apart from results, folded; it can be saved, and a new call is offered.
const raw = {check: "failed_format_check", text: "JSON이 아닌 답", chars: 9, stored_chars: 9, truncated: false, escaped: false};
run.model_synthesis = {status: "failed", message: "m", reason: "r", raw};
run.model_syntheses = [{attempt: "a1", status: "failed", result: {raw}}];
assert.ok(folded(modelControls(run)));
const shown = JSON.stringify(modelControls(run));
assert.ok(shown.includes("JSON이 아닌 답") && shown.includes("검사 실패한 원문 · 9자"));
assert.deepEqual(buttonsOf(run).map(label), ["검사 실패한 원문과 원문 보고 저장(JSON)", "한 번 더 합성(호출 1회)"]);
buttonsOf(run)[0].attrs.onclick();
assert.deepEqual(downloaded, [["r1", true]]);
assert.equal(calls.length, 1);
liveMode = false;   // without a live connection only saving remains
assert.deepEqual(buttonsOf(run).map(label), ["검사 실패한 원문과 원문 보고 저장(JSON)"]);
liveMode = true;
run.model_synthesis.raw = {...raw, chars: 70000, stored_chars: 65536, truncated: true, escaped: true};
const cut = JSON.stringify(modelControls(run));
assert.ok(cut.includes("전체 70000자 중 앞 65536자 저장") && cut.includes("\\\\u 표기"));
// Configured providers are offered even when they are not participants of this run.
synthesizers = [{adapter_id: "claude-code", label: "Claude Code"}, {adapter_id: "codex", label: "Codex"}];
run.model_synthesis = null;
run.model_syntheses = [];
assert.deepEqual(walk(modelControls(run)).filter(n => n.tag === "option").map(n => n.attrs.value), ["claude-code", "codex"]);
// Two or more attempts are listed with the synthesizer and the quote check.
run.model_syntheses = [
  {attempt: "a1", status: "completed", result: {status: "completed", synthesizer: {adapter_id: "claude-code"},
   checks: {exact_matches: 4, quotes: 5}, card: {recommendation: "A"}}},
  {attempt: "a2", status: "failed", result: {status: "unavailable", synthesizer: {adapter_id: "codex"}, reason: "bad json"}}];
const listed = JSON.stringify(modelControls(run));
assert.ok(listed.includes("실제 합성 시도 2번"));
assert.ok(listed.includes("1. claude-code · completed · 인용 4/5 원문 일치 · 권고: A"));
assert.ok(listed.includes("2. codex · failed · bad json"));
"""
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        # 실제 합성 결과를 보일 때도 새 호출·종료 확인 조작이 함께 있다
        panel = html[html.index("function synthesisPanel("):]
        start = panel.index('if (result.mode === "model")')
        self.assertIn("modelControls(run)", panel[start:panel.index("} else {", start)])


if __name__ == "__main__":
    unittest.main()
