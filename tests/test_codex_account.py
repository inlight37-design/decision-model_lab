"""Real local subprocesses pretending to be app-server. No account/credentials/network."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools.w2 import codex_account as account

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


class PlanTests(unittest.TestCase):
    def test_default_plan_does_not_start_any_process(self):
        with mock.patch.object(sys, "argv", ["codex_account.py"]), \
                mock.patch.object(account.subprocess, "Popen", side_effect=AssertionError("no process")):
            self.assertEqual(account.main(), 0)


if __name__ == "__main__":
    unittest.main()