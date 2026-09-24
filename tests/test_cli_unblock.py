"""No provider/model calls: durable caps and the UI's actual JavaScript rendering."""
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from app import controller as c
from app.store import Store, StoreError
import test_app_controller as support
from test_live_cli import UnverifiedSynthetic


class BudgetTests(support.Base):
    def run_live(self, ctl, pid="a", adapter="claude-code"):
        return ctl.create_run("q", [replace(support.cli(pid), adapter_id=adapter)], min_independent=1,
                              quorum_policy=c.INCLUDE_UNVERIFIED)

    def test_first_cap_is_fixed_before_any_call_and_recovers_when_omitted(self):
        ctl = self.controller(UnverifiedSynthetic(), max_real_calls=1)
        with self.assertRaises(StoreError):
            self.controller(UnverifiedSynthetic(), max_real_calls=2)
        path = self.store.path
        self.store.close()
        self.store = Store(path)
        self.addCleanup(self.store.close)
        restored = self.controller(UnverifiedSynthetic())
        self.assertEqual(restored.call_budget(), {"used": 0, "cap": 1})
        self.run_live(restored)
        self.assertTrue(restored.wait_idle())
        second = self.run_live(restored, "b")
        view = self.run_view(restored, second)
        self.assertEqual(view["budget"]["used"], 0)
        self.assertEqual(view["budget"]["not_started"], 1)
        self.assertEqual(view["budget"]["reserved"], 0)
        self.assertEqual(restored.call_budget(), {"used": 1, "cap": 1})

    def test_legacy_cap_is_inferred_not_replaced(self):
        ctl = self.controller(UnverifiedSynthetic(), max_real_calls=1)
        self.run_live(ctl)
        self.assertTrue(ctl.wait_idle())
        with self.store.tx() as tx:
            tx.execute("DROP TABLE live_budget")
            tx.execute("PRAGMA user_version = 5")
        path = self.store.path
        self.store.close()
        self.store = Store(path)
        self.addCleanup(self.store.close)
        with self.assertRaises(StoreError):
            self.controller(UnverifiedSynthetic(), max_real_calls=2)
        self.assertEqual(self.controller(UnverifiedSynthetic()).call_budget(), {"used": 1, "cap": 1})

    def test_inconsistent_legacy_caps_fail_closed_without_rewriting_events(self):
        with self.store.tx() as tx:
            tx.event("legacy", "live_call_reserved", cap=1)
            tx.event("legacy", "live_call_reserved", cap=2)
        before = [tuple(r) for r in self.store.rows("SELECT * FROM events")]
        with self.assertRaises(StoreError):
            self.controller(UnverifiedSynthetic(), max_real_calls=2)
        self.assertEqual(before, [tuple(r) for r in self.store.rows("SELECT * FROM events")])

    def test_provider_limits_cannot_borrow_or_change_on_restart(self):
        ex = UnverifiedSynthetic()
        # Synthetic executor accepts both adapter names; no CLI process is launched.
        ex.adapter_ids = ("claude-code", "codex")
        caps = {"claude-code": 1, "codex": 1}
        ctl = self.controller(ex, max_real_calls=2, provider_call_caps=caps)
        self.run_live(ctl)
        self.assertTrue(ctl.wait_idle())
        refused = self.run_live(ctl, "b")
        self.run_live(ctl, "c", "codex")
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(ex.started, ["a", "c"])
        self.assertEqual(self.run_view(ctl, refused)["budget"]["used"], 0)
        self.assertEqual(ctl.call_budget("codex"), {"used": 1, "cap": 1})
        for changed in (None, {"claude-code": 2}, {"claude-code": 1, "codex": 2}):
            with self.assertRaises(StoreError):
                self.controller(ex, max_real_calls=2, provider_call_caps=changed)

    def test_prestart_failure_keeps_reservation_but_not_execution_count(self):
        class Refused(UnverifiedSynthetic):
            def run(self, plan, timeout, cancel=None):
                return c._not_started(support.cli("a"), "revoked after planning")
        ctl = self.controller(Refused(), max_real_calls=1)
        rid = self.run_live(ctl)
        self.assertTrue(ctl.wait_idle())
        budget = self.run_view(ctl, rid)["budget"]
        self.assertEqual((budget["used"], budget["not_started"], budget["reserved"]), (0, 1, 1))
        self.assertEqual(ctl.call_budget(), {"used": 1, "cap": 1})


@unittest.skipUnless(shutil.which("node"), "Node is required for the actual JavaScript rendering checks")
class RenderTests(unittest.TestCase):
    def test_independence_and_prestart_budget_use_recorded_evidence(self):
        html = (Path(__file__).resolve().parents[1] / "app/static/index.html").read_text(encoding="utf-8")
        functions = html[html.index("function budget(run)"):html.index("function claimComparison(")]
        script = r'''
const assert = require("node:assert/strict");
const STATE_LABEL = {}, EXECUTION_LABEL = {}, BEHAVIOR_LABEL = {};
function h(tag, attrs, ...children) {
  return {tag, attrs, children, append(...items) {this.children.push(...items);}};
}
function text(node) {
  if (node == null) return "";
  if (Array.isArray(node)) return node.map(text).join(" ");
  return typeof node === "object" ? text(node.children) : String(node);
}
'''+functions+r'''
const p = {pid:"a", label:"A", provider:"test", transport:"cli", execution:"real",
  state:"accepted", contamination:[], draft:"PRIVATE DRAFT", result:{state:"exited", usage:{}}};
for (const independence of ["unverified", undefined, null, "confirmed"]) {
  const rendered = text(participantRow({phase:"revealed"}, {...p, independence}));
  assert.equal(rendered.includes("독립성 확인(controller"), independence === "confirmed");
  assert.equal(rendered.includes("문맥 미확인"), independence !== "confirmed");
}
assert.ok(!text(participantRow({phase:"drafting"}, p)).includes("PRIVATE DRAFT"));
const manual = text(participantRow({phase:"revealed"}, {...p, transport:"manual", result:{source:"manual"}}));
assert.ok(manual.includes("독립성 미확인"));
const card = text(budget({budget:{used:0, cap:1, not_started:1, reserved:0,
  breakdown:{succeeded:0, failed:0, unknown:0}, manual:0}}));
assert.ok(card.includes("0 / 1"));
assert.ok(card.includes("시작 전 종료 1"));
assert.ok(card.includes("구독 차감량이 아님"));
'''
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()