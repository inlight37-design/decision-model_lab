"""카드 #99: 모의/합성 실행만. 원장 이전·불변 입력·거절·모든 목록의 봉인을 고정한다."""
import copy
import json
from pathlib import Path
import sqlite3
import threading
from unittest import mock

from app import controller as c, server
from app.store import Store, StoreError
from test_app_controller import Base, SyntheticExecutor, wait_for
from test_app_integrity import HttpServerCase


def board(*isolated, orchestrator=()):
    return {"supervisor": [], "orchestrator": list(orchestrator), "isolated": list(isolated),
            "general": [], "input_mode": "original"}


ROSTER = server.PARTICIPANTS


class RoleBoardTests(Base):
    def create(self, ctl, layout=None, **kwargs):
        layout = layout or board("codex")
        return ctl.create_run("같은 질문", [ROSTER[p] for p in layout["isolated"]], min_independent=1,
                              role_board=layout, roster=ROSTER, **kwargs)

    def test_unsupported_layouts_leave_no_task_run_source_or_event(self):
        ctl = self.controller(SyntheticExecutor(), max_parallel=0)
        layouts = []
        for field, value in (("supervisor", ["claude"]), ("general", ["claude"]),
                             ("orchestrator", ["codex"]), ("orchestrator", ["antigravity-app"]),
                             ("isolated", ["codex", "chatgpt-app"]), ("input_mode", "refine"),
                             ("orchestrator", ["claude", "antigravity-app"])):
            layout = board("codex"); layout[field] = value; layouts.append(layout)
        for layout in layouts:
            with self.subTest(layout=layout), self.assertRaises(c.ControllerError):
                self.create(ctl, layout, sources=[("a.txt", "원문")])
            for table in ("tasks", "runs", "sources", "events", "participants"):
                self.assertEqual(self.store.row(f"SELECT COUNT(*) FROM {table}")[0], 0)

    def test_transaction_rollback_includes_task_and_roles(self):
        ctl = self.controller(SyntheticExecutor(), max_parallel=0)
        with mock.patch("app.store._Tx.event", side_effect=RuntimeError("disk error")):
            with self.assertRaises(RuntimeError):
                self.create(ctl)
        self.assertEqual(ctl.view()["tasks"], [])
        self.assertEqual(ctl.view()["runs"], [])

    def test_preview_is_read_only_exact_and_duplicate_confirmation_cannot_start_twice(self):
        ctl = self.controller(SyntheticExecutor(), max_parallel=0)
        options = dict(min_independent=1, role_board=board("codex", orchestrator=("claude",)), roster=ROSTER,
                       task_title="입력 비교", sources=[("notes.txt", "공통 원문")])
        preview = ctl.prepare_run("  질문 전문\n둘째 줄  ", [ROSTER["codex"]], **options)
        self.assertEqual(ctl.view()["runs"], [])
        options.update(run_id=preview["run_id"], confirmation=preview["confirmation"])
        with self.assertRaises(c.ControllerError):
            ctl.create_run("바꾼 질문", [ROSTER["codex"]], **options)
        self.assertEqual(ctl.view()["tasks"], [])
        rid = ctl.create_run("  질문 전문\n둘째 줄  ", [ROSTER["codex"]], **options)
        saved = self.run_view(ctl, rid)
        for field in ("prompt", "question", "sources", "role_config", "input_sha256", "input_bytes"):
            self.assertEqual(saved[field], preview[field])
        with self.assertRaises(c.ControllerError):
            ctl.create_run("  질문 전문\n둘째 줄  ", [ROSTER["codex"]], **options)
        self.assertEqual(len(ctl.view()["runs"]), 1)

    def test_human_orchestrator_never_synthesizes_and_multiple_runs_survive_restart(self):
        ex = SyntheticExecutor()
        ctl = self.controller(ex)
        layout = board("codex")
        first = self.create(ctl, layout, task_title="작업 하나")
        layout["orchestrator"].append("claude")  # 호출자가 바꾼 목록은 저장된 명세를 바꾸지 않는다.
        self.assertTrue(ctl.wait_idle())
        task = ctl.view()["tasks"][0]
        self.assertEqual(task["status"], "my_turn")
        self.assertIsNone(task["role_config"]["orchestrator"])
        with self.assertRaises(c.ControllerError):
            ctl.synthesize(first)
        with self.assertRaises(c.ControllerError):
            ctl.synthesize_with_model(first, "claude-code", ROSTER["claude"])
        ctl.mark_reviewed(first); ctl.mark_reviewed(first)
        self.assertEqual(ctl.view()["tasks"][0]["status"], "done")
        self.assertEqual(self.store.row("SELECT COUNT(*) FROM events WHERE kind = 'human_reviewed'")[0], 1)
        second = self.create(ctl, task_id=task["task_id"])
        self.assertTrue(ctl.wait_idle())
        ctl.shutdown(); self.store.close()
        reopened = Store(self.tmp / "store" / "journal.db")
        self.addCleanup(reopened.close)
        again = c.Controller(reopened, SyntheticExecutor(), max_parallel=0)
        self.addCleanup(again.shutdown)
        tasks = again.view()["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertEqual([r["run_id"] for r in tasks[0]["runs"]], [first, second])
        self.assertEqual(tasks[0]["title"], "작업 하나")
        self.assertEqual(tasks[0]["calls_used"], 2)
        self.assertIsNone(tasks[0]["role_config"]["orchestrator"])
        self.assertEqual(ex.started, ["codex", "codex"])
        self.assertEqual(reopened.row("SELECT COUNT(*) FROM events WHERE kind LIKE 'synthesis_%'")[0], 0)

    def test_only_configured_orchestrator_and_no_early_human_completion(self):
        ctl = self.controller(SyntheticExecutor(), max_parallel=0)
        rid = self.create(ctl, board("codex", orchestrator=("claude",)))
        with self.assertRaises(c.ControllerError):
            ctl.mark_reviewed(rid)
        with self.assertRaises(c.ControllerError):
            ctl.synthesize_with_model(rid, "codex")
        with self.assertRaises(c.ControllerError):
            self.create(ctl, task_title="동시 작업")
        self.assertEqual(len(ctl.view()["tasks"]), 1)
        ctl.max_parallel = 1; ctl.resume()
        self.assertTrue(ctl.wait_idle())
        ctl.synthesize(rid)
        self.assertIn("synthesis", self.run_view(ctl, rid))
        self.assertEqual(ctl.executor.started, ["codex"])

    def test_home_timeline_and_my_turn_never_project_sealed_answer_metadata(self):
        ctl = self.controller(SyntheticExecutor())
        layout = board("codex", "antigravity-app")
        rid = self.create(ctl, layout)
        self.assertTrue(ctl.wait_idle())
        first = ctl.view()
        self.assertEqual(first["tasks"][0]["status"], "my_turn")
        self.assertEqual(first["tasks"][0]["runs"][0]["action"], "원본 앱 답 붙여넣기")
        before = copy.deepcopy(first["tasks"])
        # 안전하지 않은 저장값을 바꿔도 목록과 내 차례의 공개 투영은 글자 그대로 같아야 한다.
        result = json.loads(self.store.row("SELECT result FROM participants WHERE run_id = ? AND pid = 'codex'", rid)[0])
        result.update(usage={"output_tokens": 87654321}, duration_ms=432109876,
                      reported_models=["SEALED_MODEL_REPORT"], notes=["SEALED_DIAGNOSTIC"])
        with self.store.tx() as tx:
            tx.execute("UPDATE drafts SET text = ?, sha256 = ? WHERE run_id = ? AND pid = 'codex'",
                       "PRIVATE_DRAFT_" * 999, "SECRET_DIGEST", rid)
            tx.execute("UPDATE participants SET result = ? WHERE run_id = ? AND pid = 'codex' AND state = 'accepted'",
                       json.dumps(result), rid)
        projected = ctl.view()
        self.assertEqual(projected["tasks"], before)
        serialized = json.dumps(projected)
        for secret in ("PRIVATE_DRAFT_", "SECRET_DIGEST", "87654321", "432109876", "SEALED_MODEL_REPORT", "SEALED_DIAGNOSTIC"):
            self.assertNotIn(secret, serialized)
        ctl.submit_manual(rid, "antigravity-app", "수동 답", first["runs"][0]["input_sha256"], user_confirmed=True)
        opened = self.run_view(ctl, rid)
        self.assertTrue(opened["gate"]["revealed"])
        self.assertEqual(opened["quorum"]["confirmed"], 1)
        self.assertEqual(opened["quorum"]["unverified"], 1)

    def test_schema_seven_is_backed_up_before_eight_and_old_run_is_visible(self):
        ctl = self.controller(SyntheticExecutor(), max_parallel=0)
        rid = ctl.create_run("이전 실행", [ROSTER["codex"]], min_independent=1)
        ctl.shutdown(); self.store.close()
        path = self.tmp / "store" / "journal.db"
        db = sqlite3.connect(path)
        db.executescript("ALTER TABLE runs DROP COLUMN task_id; ALTER TABLE runs DROP COLUMN role_config; "
                         "DROP TABLE tasks; PRAGMA user_version = 7;")
        db.close()
        reopened = Store(path)
        self.addCleanup(reopened.close)
        backups = list(path.parent.glob("journal.db.v7-*.bak"))
        self.assertEqual(len(backups), 1)
        backup = sqlite3.connect(backups[0]); self.addCleanup(backup.close)
        self.assertEqual(backup.execute("PRAGMA user_version").fetchone()[0], 7)
        self.assertNotIn("task_id", [r[1] for r in backup.execute("PRAGMA table_info(runs)")])
        self.assertEqual(backup.execute("SELECT run_id FROM runs").fetchone()[0], rid)
        self.assertEqual(reopened.row("PRAGMA user_version")[0], 8)
        again = c.Controller(reopened, SyntheticExecutor(), max_parallel=0)
        self.addCleanup(again.shutdown)
        task = again.view()["tasks"][0]
        self.assertEqual(task["title"], "이전 실행")
        self.assertEqual(task["runs"][0]["run_id"], rid)
        self.assertEqual(task["role_config"]["isolated"][0]["pid"], "codex")
        with mock.patch("app.store.SCHEMA_VERSION", 7), self.assertRaises(StoreError):
            reopened._migrate()
        self.assertEqual(reopened.row("PRAGMA user_version")[0], 8)


class RoleBoardHttpTests(HttpServerCase):
    def get_state(self):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        try:
            conn.request("GET", "/api/state", headers={"Authorization": f"Bearer {self.token}"})
            reply = conn.getresponse()
            self.assertEqual(reply.status, 200)
            return json.loads(reply.read())
        finally:
            conn.close()

    def test_manual_mock_flow_reopens_the_same_task_after_server_restart(self):
        # 원본 앱을 실제로 부르지 않고 모의 답을 넣는다. 실제 서버 라우트를 끝까지 거친다.
        body = {"question": "화면 흐름 확인용 질문", "participants": [{"pid": "antigravity-app"}],
                "min_independent": 1, "quorum_policy": "include_unverified",
                "role_board": board("antigravity-app"), "task_title": "모의 작업"}
        status, raw, _ = self.request(body, path="/api/runs/preview")
        self.assertEqual(status, 200)
        preview = json.loads(raw)
        body.update(run_id=preview["run_id"], confirmation=preview["confirmation"])
        self.assertEqual(self.request(body)[0], 200)
        rid = preview["run_id"]
        before = self.get_state()
        self.assertEqual(before["tasks"][0]["status"], "my_turn")
        self.assertEqual(self.request({"text": "이것은 외부 모델을 부르지 않고 작성한 모의 답입니다.",
                                       "input_sha256": preview["input_sha256"], "user_confirmed": True},
                                      path=f"/api/runs/{rid}/manual/antigravity-app")[0], 200)
        opened = self.get_state()
        self.assertTrue(opened["runs"][0]["gate"]["revealed"])
        self.assertEqual(opened["tasks"][0]["runs"][0]["action"], "공개된 답 판단")
        self.assertEqual(self.request({}, path=f"/api/runs/{rid}/reviewed")[0], 200)
        saved = self.get_state()
        self.assertEqual(saved["tasks"][0]["status"], "done")
        self.httpd.shutdown(); self.httpd.server_close(); self.thread.join(2)
        self.assertFalse(self.thread.is_alive())
        self.assertTrue(self.ctl.shutdown()); self.store.close()
        restarted = Store(Path(self.tmp.name) / "journal.db")
        self.addCleanup(restarted.close)
        self.ctl = c.Controller(restarted, c.MockExecutor(), max_parallel=0)
        self.addCleanup(self.ctl.shutdown)
        self.httpd = server._Server(("127.0.0.1", 0), server.BaseHTTPRequestHandler)
        self.port = self.httpd.server_address[1]
        self.httpd.RequestHandlerClass = server.make_handler(self.ctl, self.token, self.port)
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.httpd.server_close); self.addCleanup(self.httpd.shutdown)
        self.assertEqual(self.get_state()["tasks"], saved["tasks"])
        self.assertEqual(self.get_state()["runs"][0]["role_config"], saved["runs"][0]["role_config"])

    def test_preview_then_start_preserves_roles_and_unsupported_posts_create_nothing(self):
        body = {"question": "서버 입력", "participants": [{"pid": "codex"}], "min_independent": 1,
                "role_board": board("codex"), "task_title": "HTTP 작업"}
        bad = copy.deepcopy(body); bad["role_board"]["general"] = ["claude"]
        for endpoint in ("/api/runs/preview", "/api/runs"):
            self.assertEqual(self.request(bad, path=endpoint)[0], 400)
            self.assertEqual(self.ctl.view()["runs"], [])
        status, raw, _ = self.request(body, path="/api/runs/preview")
        self.assertEqual(status, 200)
        self.assertEqual(self.ctl.view()["tasks"], [])
        preview = json.loads(raw)
        body.update(run_id=preview["run_id"], confirmation=preview["confirmation"])
        self.assertEqual(self.request(body)[0], 200)
        self.assertEqual(self.request(body)[0], 400)
        saved = self.ctl.view()["runs"][0]
        self.assertEqual(saved["role_config"], preview["role_config"])
        self.assertEqual(saved["prompt"], preview["prompt"])
        self.assertEqual(self.request({}, path=f"/api/runs/{saved['run_id']}/reviewed")[0], 400)
