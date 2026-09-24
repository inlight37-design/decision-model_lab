"""Provider routing and parallel sealed drafts; fake CLIs/threads only, no model requests."""
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from app import controller as c, live_config, readiness, server
from core import adapters
import test_app_controller as support
import test_app_cli_executor as cli_support
from test_live_cli import UnverifiedSynthetic


class ConfigTests(unittest.TestCase):
    def test_relative_paths_explicit_models_and_unknown_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "live.json"
            rows = [{"adapter_id": "codex", "model": "test-model", "inventory": "codex.json",
                     "input_dir": "empty", "call_budget": 1},
                    {"adapter_id": "claude-code", "model": "other-test-model", "inventory": "claude.json",
                     "call_budget": 1}]
            path.write_text(json.dumps({"providers": rows}), encoding="utf-8")
            parsed = live_config.load(path)
            self.assertEqual(parsed[0].input_dir, Path(tmp) / "empty")
            self.assertIsNone(parsed[1].input_dir)
            self.assertEqual(parsed[1].inventory, Path(tmp) / "claude.json")
            for bad in ([], [rows[0], rows[0]], [{**rows[0], "call_budget": True}],
                        [{**rows[0], "model": " "}], [{**rows[0], "funding": "api"}]):
                path.write_text(json.dumps({"providers": bad}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    live_config.load(path)

    def test_all_provider_readiness_checks_precede_server_and_use_own_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "live.json"
            path.write_text(json.dumps({"providers": [
                {"adapter_id": "codex", "model": "m1", "inventory": "c.json", "input_dir": "empty", "call_budget": 1},
                {"adapter_id": "claude-code", "model": "m2", "inventory": "a.json", "call_budget": 1}
            ]}), encoding="utf-8")
            argv = ["app.server", "--live-config", str(path), "--data-dir", str(Path(tmp) / "state")]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(readiness, "check",
                    side_effect=[{"eligible": True}, {"eligible": False}]) as check, \
                    mock.patch.object(server, "serve", side_effect=AssertionError("must not serve")):
                self.assertEqual(server.main(), 2)
                self.assertEqual(check.call_count, 2)
                self.assertEqual(check.call_args_list[0].kwargs["input_dir"], Path(tmp) / "empty")
                self.assertIsNone(check.call_args_list[1].kwargs["input_dir"])

    @unittest.skipUnless(sys.platform == "linux", "live server is Linux-only")
    def test_live_server_wires_two_slots_and_caps_without_launching_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            providers = (live_config.Provider("codex", "m1", Path(tmp) / "c.json", 1, Path(tmp) / "empty"),
                         live_config.Provider("claude-code", "m2", Path(tmp) / "a.json", 1))
            httpd, _, ctl = server.serve(Path(tmp) / "state", 0, live_providers=providers,
                                         allow_context_unverified=True)
            try:
                self.assertEqual(ctl.max_parallel, 2)
                self.assertEqual(ctl.provider_call_caps, {"codex": 1, "claude-code": 1})
                self.assertEqual(ctl.executor.inputs_by_adapter["codex"], (str(Path(tmp) / "empty"),))
                self.assertEqual(ctl.executor.inputs_by_adapter["claude-code"], ())
                self.assertEqual(ctl.call_budget(), {"used": 0, "cap": 2})
            finally:
                httpd.server_close()
                ctl.store.close()


@unittest.skipUnless(sys.platform == "linux", "uses Linux fake-install symlinks")
class PlanTests(cli_support.Base):
    def test_codex_input_does_not_change_claude_revision_and_explicit_override_wins(self):
        for adapter in ("codex", "claude"):
            cli_support.install(self.home, adapter)
        source = self.root / "empty"
        source.mkdir()
        ex = self.executor(inputs_by_adapter={"codex": (str(source),), "claude-code": ()})
        work = str(self.root / "work")
        before = self.executor().plan(cli_support.claude(), "q", work)
        after = ex.plan(cli_support.claude(), "q", work)
        self.assertEqual(before.revision, after.revision)
        self.assertNotIn("--add-dir", after.spec.argv)
        codex = ex.plan(cli_support.codex(), "q", work)
        direct = self.executor().plan(cli_support.codex(), "q", work, inputs=(str(source),))
        self.assertEqual(codex.revision, direct.revision)
        self.assertEqual(ex.plan(cli_support.codex(), "q", work, inputs=()).revision,
                         self.executor().plan(cli_support.codex(), "q", work).revision)

    def test_missing_provider_inventory_never_becomes_unchecked(self):
        cli_support.install(self.home, "claude")
        ex = self.executor(inventories_by_adapter={"codex": self.root / "codex.json"})
        ex.unchecked = False
        with self.assertRaisesRegex(adapters.AdapterError, "no inventory"):
            ex.plan(cli_support.claude(), "q", str(self.root / "work"))


class ParallelTests(support.Base):
    def test_providers_overlap_but_never_see_an_early_peer_draft(self):
        ex = UnverifiedSynthetic(hold=("a", "b"))
        ex.adapter_ids = ("claude-code", "codex")
        ctl = self.controller(ex, max_real_calls=2, provider_call_caps={"claude-code": 1, "codex": 1})
        try:
            rid = ctl.create_run("same question", [support.cli("a"), replace(support.cli("b"), adapter_id="codex")],
                                 min_independent=2, quorum_policy=c.INCLUDE_UNVERIFIED)
            support.wait_for(lambda: len(ex.started) == 2)  # both active, neither released yet
            self.assertEqual(ctl.call_budget()["used"], 2)
            ex.release("a")
            support.wait_for(lambda: self.part(ctl, rid, "a")["state"] == c.ACCEPTED)
            self.assertNotIn("draft", self.part(ctl, rid, "a"))
            self.assertEqual(self.run_view(ctl, rid)["phase"], "drafting")
            ex.release("b")
            self.assertTrue(ctl.wait_idle())
            view = self.run_view(ctl, rid)
            self.assertEqual(view["phase"], "revealed")
            self.assertEqual(view["quorum"]["confirmed"], 0)
            self.assertEqual({p["draft"] for p in view["participants"]}, {"a의 답", "b의 답"})
        finally:
            ex.release("a")
            ex.release("b")
            ctl.wait_idle()


if __name__ == "__main__":
    unittest.main()