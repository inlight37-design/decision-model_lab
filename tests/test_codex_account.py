"""Real local subprocesses pretending to be app-server. No account/credentials/network."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from app import codex_account as account
from core import isolation, runner
from test_core_isolation import REQUIRED, bwrap_usable

FAKE = r'''
import json,sys,time
mode, log = sys.argv[1:]
for line in sys.stdin:
    msg = json.loads(line)
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(msg) + "\n")
    method = msg["method"]
    if mode == "hang":
        time.sleep(10)
    if mode == "overflow":
        print("X" * (1024 * 1024 + 10), flush=True)
        continue
    if mode == "request":
        print(json.dumps({"method":"account/chatgptAuthTokens/refresh", "id":100, "params":{"secret":"PRIVATE"}}), flush=True)
        continue
    if method == "initialized":
        continue
    if mode == "activity" and method == "initialize":
        print(json.dumps({"method":"turn/started", "params":{"turn":{"id":"PRIVATE TURN"}}}), flush=True)
    if mode == "notify" and method == "account/read":
        print(json.dumps({"method":"account/updated", "params":{"email":"PRIVATE EMAIL"}}), flush=True)
    if method == "initialize":
        result = {"userAgent":"PRIVATE INIT"}
    elif method == "account/read":
        result = {"account":{"type":"apiKey" if mode == "api" else "chatgpt",
                             "email":"PRIVATE EMAIL", "planType":"PRIVATE PLAN"}}
    elif method == "account/rateLimits/read":
        if mode == "refused":
            print(json.dumps({"id":msg["id"], "error":{"message":"PRIVATE ERROR"}}), flush=True)
            continue
        result = {"rateLimits":{"primary":{"usedPercent":25, "windowDurationMins":300,
                                             "resetsAt":int(time.time())+300}},
                  "accountId":"PRIVATE ID", "credits":{"balance":"PRIVATE BALANCE"}}
    elif method == "model/list":
        if mode == "nomodels":
            print(json.dumps({"id":msg["id"], "error":{"message":"PRIVATE ERROR"}}), flush=True)
            continue
        result = {"data":[{"id":"gpt-test", "model":"gpt-test", "displayName":"PRIVATE_DISPLAY", "hidden":False},
                          {"id":"bad id", "model":"bad id"}], "nextCursor":None}
    else:
        raise AssertionError("forbidden method sent")
    print(json.dumps({"id":msg["id"], "result":result}), flush=True)
'''


@unittest.skipUnless(sys.platform == "linux", "stdio pipe selector and live probe are Linux-only")
class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "sent.jsonl"
        self.children = []
        original = subprocess.Popen

        def spawn(*args, **kwargs):
            child = original(*args, **kwargs)
            self.children.append(child)
            return child
        patcher = mock.patch.object(account.subprocess, "Popen", side_effect=spawn)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        for child in self.children:
            self.assertIsNotNone(child.poll(), "metadata child was not reaped")
            self.assertTrue(child.stdout.closed)
            self.assertTrue(child.stdin.closed)

    def query(self, mode, timeout=2):
        return account.query((sys.executable, "-u", "-c", FAKE, mode, str(self.log)), timeout=timeout)

    def sent(self):
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def test_only_fixed_metadata_methods_and_no_identity_survives(self):
        result = self.query("ok")
        messages = self.sent()
        self.assertEqual([m["method"] for m in messages], list(account.METHODS))
        self.assertFalse(messages[2]["params"]["refreshToken"])
        self.assertEqual(result["inference_requests_sent"], 0)
        self.assertEqual(result["quota"]["limits"][0]["used_percent"], 25)
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertNotIn("credits", json.dumps(result))

    def test_api_login_is_not_reused_and_no_fallback_or_quota_call_occurs(self):
        with self.assertRaises(account.ProtocolError):
            self.query("api")
        self.assertEqual([m["method"] for m in self.sent()], list(account.METHODS[:3]))

    def test_refusals_server_requests_output_limit_and_timeout_clean_up(self):
        for mode in ("refused", "request", "overflow", "hang"):
            with self.subTest(mode=mode), self.assertRaises(account.ProtocolError) as error:
                self.query(mode, timeout=0.25 if mode == "hang" else 2)
            self.assertNotIn("PRIVATE", str(error.exception))
            self.assertTrue(all(child.poll() is not None for child in self.children))

    def test_notifications_are_dropped_but_agent_activity_stops_the_probe(self):
        # 변이 M11(PR #39 병합 검토): 에이전트 활동 알림을 거절하는 조건을 지워도 시험이 통과했다.
        with self.assertRaises(account.ProtocolError) as error:
            self.query("activity")
        self.assertNotIn("PRIVATE", str(error.exception))
        self.assertEqual([m["method"] for m in self.sent()], ["initialize"])
        result = self.query("notify")
        self.assertEqual(result["quota"]["limits"][0]["used_percent"], 25)
        self.assertNotIn("PRIVATE", json.dumps(result))

    def test_model_list_keeps_names_only_and_its_refusal_keeps_the_quota(self):
        result = self.query("ok")
        self.assertEqual(result["models"], {"status": "observed", "ids": ["gpt-test"], "truncated": False})
        self.assertNotIn("PRIVATE", json.dumps(result))
        refused = self.query("nomodels")
        self.assertEqual(refused["models"], {"status": "unavailable"})
        self.assertEqual(refused["quota"]["limits"][0]["used_percent"], 25)
        self.assertNotIn("PRIVATE", json.dumps(refused))


class PlanTests(unittest.TestCase):
    def test_default_plan_does_not_start_any_process(self):
        with mock.patch.object(sys, "argv", ["codex_account.py"]), \
                mock.patch.object(account.subprocess, "Popen", side_effect=AssertionError("no process")):
            self.assertEqual(account.main(), 0)

    def test_helper_does_not_depend_on_host_python_or_filtered_pythonpath(self):
        args = account.helper_argv("/fake/codex")
        self.assertEqual(args[0], "/usr/bin/python3")
        self.assertEqual(args[3:], (str(account.ROOT), os.path.realpath("/fake/codex"), "app-server"))
        self.assertIn("sys.path.insert", args[2])


class IsolatedProtocolTests(unittest.TestCase):
    def test_actual_helper_import_and_metadata_dialogue_inside_bubblewrap(self):
        if not bwrap_usable():
            if REQUIRED:
                self.fail("CI requires usable bubblewrap for the metadata helper")
            self.skipTest("bubblewrap unavailable; native boundary not tested here")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "work"
            work.mkdir()
            script = root / "fake-codex"
            script.write_text("#!/usr/bin/python3\n" + FAKE.replace(
                "mode, log = sys.argv[1:]", 'mode, log = "ok", "/tmp/metadata-sent.jsonl"'), encoding="utf-8")
            script.chmod(0o700)
            link = root / "codex-link"
            link.symlink_to(script)
            box = isolation.Sandbox(work_dir=str(work), home=str(root / "home"),
                                    read_only=(str(account.ROOT / "app"), str(account.ROOT / "core"), str(script)),
                                    never=(str(root / "ledger"),))
            # Only the real binary is mounted; the installation symlink is hidden.
            result = isolation.run(account.helper_argv(str(link)), box, timeout=13, max_output_bytes=65536)
            self.assertEqual(result.state, runner.EXITED)
            self.assertEqual(result.exit_code, 0, result.stderr)
            self.assertTrue(result.tree_confirmed_empty)
            report = json.loads(result.stdout)
            self.assertEqual(report["inference_requests_sent"], 0)
            self.assertEqual(report["quota"]["limits"][0]["used_percent"], 25)
            self.assertEqual(report["models"]["ids"], ["gpt-test"])
            self.assertNotIn("PRIVATE", result.stdout)


if __name__ == "__main__":
    unittest.main()
