"""WF-01: earlier ledgers are found read-only and a task's public results carry over as an explicit source. No models."""
import hashlib
import http.client
import json
from pathlib import Path
import threading

from app import controller as c, ledgers, server as s
from app.store import Store
import test_app_controller as support


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LedgerTests(support.Base):
    def setUp(self):
        super().setUp()
        self.live = self.tmp / "live"
        self.old = self.live / "20261001-090000"
        old_store = Store(self.old / "journal.db")
        ctl = c.Controller(old_store, support.SyntheticExecutor(), work_root=str(self.tmp / "old-work"))
        self.public = ctl.create_run("공개된 질문 KEEP-ME", [support.cli("a"), support.cli("b")], min_independent=2,
                                     task_title="이전 작업")
        self.assertTrue(ctl.wait_idle())
        view = self.run_view(ctl, self.public)
        self.task = view["task_id"]
        ctl.mark_reviewed(self.public, view["result_revision"], "옛 판단 메모")
        self.sealed = ctl.create_run("봉인된 질문 SEALED-TEXT", [support.cli("a"), support.cli("b")], min_independent=2,
                                     task_id=self.task)
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(ctl.shutdown())
        with old_store.tx() as tx:   # a run that never revealed and whose member never confirmed its end
            tx.execute("UPDATE runs SET phase = 'drafting' WHERE run_id = ?", self.sealed)
            tx.execute("UPDATE participants SET state = 'unknown' WHERE run_id = ? AND pid = 'a'", self.sealed)
        old_store.close()
        self.current = self.live / "20261008-090000"
        self.store.close()
        self.store = Store(self.current / "journal.db"); self.addCleanup(self.store.close)
        (self.live / "not-a-ledger").mkdir()
        self.before = digest(self.old / "journal.db")

    def test_previous_ledgers_are_listed_with_their_tasks_and_unsettled_attempts(self):
        found = ledgers.previous(self.live, self.current)
        self.assertEqual([item["name"] for item in found], [self.old.name])   # never the current ledger
        item = found[0]
        self.assertIsNone(item["error"])
        self.assertEqual(item["unsettled"], 1)
        self.assertEqual([(t["task_id"], t["title"], t["runs"]) for t in item["tasks"]], [(self.task, "이전 작업", 2)])
        self.assertEqual(ledgers.previous(None, self.current), [])
        self.assertEqual(digest(self.old / "journal.db"), self.before)

    def test_handoff_carries_public_results_only_and_becomes_a_fixed_source_of_a_new_run(self):
        made = ledgers.handoff(self.live, self.current, self.old.name, self.task)
        text = made["text"]
        self.assertIn("공개된 질문 KEEP-ME", text)
        self.assertIn("옛 판단 메모", text)
        self.assertIn("원본 sha256", text)
        self.assertNotIn("SEALED-TEXT", text)
        self.assertIn("실행 2개 중 공개 완료 1개", text)
        for bad in (("..", self.task), (self.current.name, self.task), ("not-a-ledger", self.task),
                    (self.old.name, "t-missing")):
            with self.assertRaises(ledgers.LedgerError):
                ledgers.handoff(self.live, self.current, *bad)
        ctl = self.controller(support.SyntheticExecutor())
        rid = ctl.create_run("이어서 볼 질문", [support.cli("a"), support.cli("b")], min_independent=2,
                             task_title=made["title"], sources=[(made["name"], text)])
        self.assertTrue(ctl.wait_idle())
        listed = self.run_view(ctl, rid)["sources"]
        self.assertEqual([(i["name"], i["sha256"]) for i in listed],
                         [(made["name"], hashlib.sha256(text.encode()).hexdigest())])
        self.assertEqual(ctl.call_budget()["used"], 0)            # nothing consumed moves across
        self.assertEqual(len(ctl.view()["tasks"]), 1)
        self.assertEqual(digest(self.old / "journal.db"), self.before)

    def test_http_lists_and_hands_off_only_with_a_ledger_root(self):
        ctl = self.controller(c.MockExecutor(), max_parallel=0)
        token = "T" * 43
        for root, expected in ((self.live, [self.old.name]), (None, [])):
            httpd = s._Server(("127.0.0.1", 0), s.make_handler(ctl, token, 0))
            port = httpd.server_address[1]
            httpd.RequestHandlerClass = s.make_handler(ctl, token, port, ledger_root=root)
            thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
            thread.start()
            try:
                def get(path):
                    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                    try:
                        conn.request("GET", path, headers={"Authorization": "Bearer " + token})
                        response = conn.getresponse()
                        return response.status, json.loads(response.read())
                    finally:
                        conn.close()
                status, body = get("/api/ledgers")
                self.assertEqual((status, [item["name"] for item in body["ledgers"]]), (200, expected))
                status, body = get(f"/api/ledgers/{self.old.name}/tasks/{self.task}/handoff")
                self.assertEqual(status, 200 if root else 409)
                if root:
                    self.assertIn("공개된 질문 KEEP-ME", body["text"])
                    self.assertEqual(get(f"/api/ledgers/..%2F{self.old.name}/tasks/{self.task}/handoff")[0], 409)
            finally:
                httpd.shutdown(); httpd.server_close()
