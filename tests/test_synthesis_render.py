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

    def test_controls_never_retry_and_acknowledge_the_exact_unknown_attempt(self):
        html = (Path(__file__).resolve().parents[1] / "app/static/index.html").read_text(encoding="utf-8")
        functions = html[html.index("function modelControls("):html.index("function synthesisPanel(")]
        script = r"""
const assert = require("node:assert/strict");
let liveMode = true, confirmed = false;
const calls = [];
const window = {confirm: () => confirmed};
const act = (...args) => calls.push(args);
const downloaded = [];
const downloadReport = (...args) => downloaded.push(args);
const h = (tag, attrs, ...children) => ({tag, attrs, children: children.flat(Infinity)});
const walk = node => node && typeof node === "object" ? [node, ...node.children.flatMap(walk)] : [];
""" + functions + r"""
const run = {run_id: "r1", participants: [{transport: "cli", adapter_id: "claude-code", label: "C"}]};
assert.equal(walk(modelControls(run)).filter(n => n.tag === "button").length, 1);
for (const status of ["failed", "completed", "acknowledged", "running"]) {
  run.model_synthesis = {status, message: "state"};
  assert.equal(walk(modelControls(run)).filter(n => n.tag === "button").length, 0);
}
run.model_synthesis = {status: "unknown", attempts: ["exact-attempt"], message: "unknown"};
liveMode = false; // Saved unresolved attempts still need an explicit acknowledgement.
const buttons = walk(modelControls(run)).filter(n => n.tag === "button");
assert.equal(buttons.length, 1);
buttons[0].attrs.onclick();
assert.equal(calls.length, 0);
confirmed = true;
buttons[0].attrs.onclick();
assert.deepEqual(calls, [["/api/runs/r1/acknowledge-synthesis", {attempt: "exact-attempt"}]]);
// A reply that failed the format check is shown apart from results and can only be saved, never retried.
const raw = {check: "failed_format_check", text: "JSON이 아닌 답", chars: 9, stored_chars: 9, truncated: false, escaped: false};
run.model_synthesis = {status: "failed", message: "m", reason: "r", raw};
const failed = walk(modelControls(run));
const saves = failed.filter(n => n.tag === "button");
assert.equal(saves.length, 1);
assert.ok(failed.some(n => n.tag === "details"));
const shown = JSON.stringify(modelControls(run));
assert.ok(shown.includes("JSON이 아닌 답") && shown.includes("검사 실패한 원문 · 9자"));
saves[0].attrs.onclick();
assert.deepEqual(downloaded, [["r1", true]]);
assert.equal(calls.length, 1);
run.model_synthesis.raw = {...raw, chars: 70000, stored_chars: 65536, truncated: true, escaped: true};
const cut = JSON.stringify(modelControls(run));
assert.ok(cut.includes("전체 70000자 중 앞 65536자 저장") && cut.includes("\\\\u 표기"));
"""
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        panel = html[html.index("function synthesisPanel("):]
        start = panel.index('if (result.mode === "model")')
        self.assertIn("modelControls(run)", panel[start:panel.index("const controls", start)])


if __name__ == "__main__":
    unittest.main()
