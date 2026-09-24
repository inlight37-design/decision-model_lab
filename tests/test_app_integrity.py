"""A1 lifecycle and HTTP regressions. Synthetic/offline only; no provider calls."""
import http.client
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import threading
import unittest

from app import controller as c, server as s
from app.store import Store


class StoreTransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / "journal.db")
        self.addCleanup(self.store.close)

    def test_failed_begin_releases_its_lock_for_other_threads(self):
        with self.store.tx():
            with self.assertRaises(sqlite3.OperationalError):
                with self.store.tx():  # SQLite rejects nested BEGIN; the outer transaction remains valid.
                    self.fail("nested transaction unexpectedly started")
        acquired = []
        def reader():
            taken = self.store._lock.acquire(timeout=0.5)
            acquired.append(taken)
            if taken:
                self.store._lock.release()
        worker = threading.Thread(target=reader)
        worker.start()
        worker.join(2)
        self.assertEqual(acquired, [True])

    def test_failed_commit_rolls_back_and_next_transaction_can_start(self):
        self.store._db.execute("PRAGMA foreign_keys = ON")
        self.store._db.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        self.store._db.execute("CREATE TABLE child (id INTEGER REFERENCES parent(id) DEFERRABLE INITIALLY DEFERRED)")
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.tx() as tx:
                tx.execute("INSERT INTO child VALUES (1)")
        self.assertFalse(self.store._db.in_transaction)
        with self.store.tx() as tx:
            tx.execute("INSERT INTO parent VALUES (1)")
        self.assertEqual(self.store.row("SELECT COUNT(*) FROM child")[0], 0)


class HttpServerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / "journal.db")
        self.addCleanup(self.store.close)
        self.ctl = c.Controller(self.store, c.MockExecutor(), max_parallel=0)
        self.token = "T" * 43
        self.httpd = s._Server(("127.0.0.1", 0), s.make_handler(self.ctl, self.token, 0))
        self.port = self.httpd.server_address[1]
        self.httpd.RequestHandlerClass = s.make_handler(self.ctl, self.token, self.port)
        # Short test-only timeout; production defaults need not make this regression slow.
        self.httpd.RequestHandlerClass.timeout = 0.2
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def request(self, value, headers=None, path="/api/runs"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        self.addCleanup(conn.close)
        head = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        head.update(headers or {})
        conn.request("POST", path, json.dumps(value).encode(), head)
        response = conn.getresponse()
        body = response.read()
        return response.status, body, dict(response.getheaders())

    def raw(self, framing, payload=b"{}"):
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        self.addCleanup(sock.close)
        sock.sendall((f"POST /api/resume HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n"
                      f"Authorization: Bearer {self.token}\r\nContent-Type: application/json\r\n"
                      f"{framing}\r\n\r\n").encode() + payload)
        response = http.client.HTTPResponse(sock)
        response.begin()
        response.read()
        return response.status


class HttpBoundaryTests(HttpServerCase):
    def test_nonobject_json_is_a_400_not_a_disconnected_request(self):
        for value in (None, [], "question", 3, True):
            with self.subTest(value=value):
                self.assertEqual(self.request(value)[0], 400)
        self.assertEqual(self.ctl.view()["runs"], [])

    def test_question_and_manual_text_are_not_coerced_from_null_objects_or_numbers(self):
        for value in (None, {}, [], 4, True):
            with self.subTest(value=value):
                status, _, _ = self.request({"question": value, "participants": [{"pid": "claude"}],
                                             "min_independent": 1})
                self.assertEqual(status, 400)
        self.assertEqual(self.ctl.view()["runs"], [])
        spec = c.ParticipantSpec("app", "App", "test", c.MANUAL)
        run = self.ctl.create_run("q", [spec], min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)
        digest = self.ctl.view()["runs"][0]["input_sha256"]
        status, _, _ = self.request({"text": None, "input_sha256": digest}, path=f"/api/runs/{run}/manual/app")
        self.assertEqual(status, 400)
        self.assertEqual(self.store.row("SELECT COUNT(*) FROM drafts")[0], 0)

    def test_quorum_is_an_integer_not_boolean_float_or_numeric_string(self):
        for value in (True, 1.5, "1", None):
            with self.subTest(value=value):
                self.assertEqual(self.request({"question": "q", "participants": [{"pid": "claude"}],
                                               "min_independent": value})[0], 400)

    def test_invalid_or_ambiguous_framing_is_rejected_before_reading_body(self):
        for framing in ("Content-Length: -1", "Content-Length: abc", "Content-Length: +2",
                        "Content-Length: 2\r\nContent-Length: 2", "Transfer-Encoding: chunked",
                        "Content-Length: 2\r\nTransfer-Encoding: chunked"):
            with self.subTest(framing=framing):
                self.assertEqual(self.raw(framing), 400)
        self.assertEqual(self.raw(""), 411)
        self.assertEqual(self.raw(f"Content-Length: {s.MAX_BODY + 1}"), 413)

    def test_incomplete_body_times_out_without_mutation(self):
        self.assertEqual(self.raw("Content-Length: 20", b"{"), 408)
        self.assertEqual(self.ctl.view()["runs"], [])

    def test_origin_content_type_and_embedding_guards(self):
        for origin in ("null", "https://evil.invalid", f"http://127.0.0.1:{self.port + 1}"):
            self.assertEqual(self.request({}, {"Origin": origin}, path="/api/resume")[0], 403)
        self.assertEqual(self.request({}, {"Content-Type": "text/plain"}, path="/api/resume")[0], 415)
        status, _, headers = self.request({}, {"Origin": f"http://127.0.0.1:{self.port}"}, path="/api/resume")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(headers.get("Content-Security-Policy"), "frame-ancestors 'none'")

    def test_valid_korean_request_keeps_its_original_input(self):
        status, _, _ = self.request({"question": "한글 질문", "participants": [{"pid": "claude"}],
                                     "min_independent": 1})
        self.assertEqual(status, 200)
        self.assertEqual(self.ctl.view()["runs"][0]["question"], "한글 질문")
