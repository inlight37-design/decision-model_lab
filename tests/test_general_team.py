"""카드 #125: 사람이 나누는 일반 팀원 작업(역할판 C 첫 조각). 합성 실행기만 — 모델·CLI 프로세스를 부르지 않는다.

완료 조건을 하나씩 고정한다: 팀원별 입력·자료(이름·해시·크기·종류·범위)의 고정, 원문만 받음, 독립·정족수 라벨 없음,
예약·상한·취소·종료 미확인·재시작 복구가 격리 팀원과 같은 관문을 지남, 사람이 모아 메모와 함께 판단 완료.
"""
from dataclasses import replace
import hashlib
import http.client
import json
import os
from pathlib import Path
import sqlite3
import threading

from app import controller as c, server
from app.report import ReportError, build_report
from app.store import SCHEMA_VERSION, Store, events
from core import contract
import test_app_controller as support

ROSTER = server.PARTICIPANTS
SOURCES = [("a.md", "자료 A 원문 · 표식 SRC-A"), ("b.md", "자료 B 원문 · 표식 SRC-B")]
WORK = {"claude": {"task": "A를 읽고 장단점을 정리", "sources": ["a.md"]},
        "codex": {"task": "B를 읽고 위험을 정리", "sources": ["b.md"]}}
TABLES = ("tasks", "runs", "sources", "events", "participants", "assignments")


def board(*general, isolated=(), orchestrator=()):
    return {"supervisor": [], "orchestrator": list(orchestrator), "isolated": list(isolated),
            "general": list(general), "input_mode": "original"}


class Recording(support.SyntheticExecutor):
    """팀원마다 받은 입력 전문과 입력 폴더의 파일 내용을 기록한다."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prompts, self.inputs = {}, {}

    def plan(self, spec, prompt, work_dir, *, inputs=()):
        self.prompts[spec.pid] = prompt
        self.inputs[spec.pid] = {name: Path(folder, name).read_text(encoding="utf-8")
                                 for folder in inputs for name in sorted(os.listdir(folder))}
        return super().plan(spec, prompt, work_dir)


class RealLike(Recording):
    """실제 CLI처럼 예약하는 계획을 낸다. 실행은 합성이다 — 호출 예약 관문만 본다."""
    kind = contract.REAL

    def plan(self, spec, prompt, work_dir, *, inputs=()):
        return replace(super().plan(spec, prompt, work_dir, inputs=inputs), kind=contract.REAL)


class GeneralTeamTests(support.Base):
    def create(self, ctl, pids=("claude", "codex"), work=None, sources=SOURCES, **kwargs):
        return ctl.create_run("전체 목표: 도입 여부 판단", [ROSTER[p] for p in pids], min_independent=1,
                              role_board=board(*pids), roster=ROSTER, sources=sources,
                              assignments=work if work is not None else {p: WORK[p] for p in pids}, **kwargs)

    def count(self, table):
        return self.store.row(f"SELECT COUNT(*) AS n FROM {table}")["n"]

    def test_each_member_gets_its_own_task_and_only_the_sources_it_was_given(self):
        ex = Recording()
        ctl = self.controller(ex)
        rid = self.create(ctl)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(ex.inputs["claude"], {"a.md": SOURCES[0][1]})
        self.assertEqual(ex.inputs["codex"], {"b.md": SOURCES[1][1]})
        self.assertIn("A를 읽고 장단점을 정리", ex.prompts["claude"])
        self.assertNotIn("B를 읽고", ex.prompts["claude"])
        self.assertIn("전체 목표: 도입 여부 판단", ex.prompts["codex"])
        run = self.run_view(ctl, rid)
        self.assertEqual(run["mode"], "general")
        self.assertIsNone(run["quorum"])
        members = {}
        for part in run["participants"]:
            work = part["assignment"]
            members[part["pid"]] = work
            self.assertEqual(part["independence"], "not_applicable")          # blind 초안이 아니다
            self.assertFalse(any("독립" in flag for flag in part["contamination"]))
            self.assertEqual(work["prompt"], ex.prompts[part["pid"]])
            self.assertEqual(work["input_sha256"], hashlib.sha256(work["prompt"].encode()).hexdigest())
        text = SOURCES[0][1].encode()
        self.assertEqual(members["claude"]["sources"], [{"name": "a.md", "bytes": len(text),
                                                         "sha256": hashlib.sha256(text).hexdigest(),
                                                         "kind": "original", "range": "whole"}])
        self.assertEqual(run["input_sha256"], c._bundle_digest(members))

    def test_results_show_as_they_arrive_and_the_person_reviews_after_all_end(self):
        ex = Recording(hold=("codex",))
        ctl = self.controller(ex)
        rid = self.create(ctl, task_title="나눠 보기")
        self.assertTrue(support.wait_for(lambda: self.part(ctl, rid, "claude")["state"] == c.ACCEPTED))
        early = self.run_view(ctl, rid)
        claude = next(p for p in early["participants"] if p["pid"] == "claude")
        self.assertEqual(claude["draft"], "claude의 답")                    # 봉인하지 않는다
        self.assertIn("usage", claude["result"])
        self.assertFalse(early["gate"]["collected"])
        self.assertEqual(ctl.view()["tasks"][0]["status"], "working")
        with self.assertRaises(c.ControllerError):
            ctl.mark_reviewed(rid, 0)
        ex.release("codex")
        self.assertTrue(ctl.wait_idle())
        run = self.run_view(ctl, rid)
        self.assertTrue(run["gate"]["collected"])
        self.assertFalse(run["gate"]["revealed"])
        task = ctl.view()["tasks"][0]
        self.assertEqual((task["status"], task["runs"][0]["action"]), ("my_turn", "결과 모아 판단"))
        kinds = [e["kind"] for e in events(self.store, rid)]
        self.assertEqual(kinds.count("result_accepted"), 2)
        self.assertNotIn("draft_sealed", kinds)
        self.assertNotIn("revealed", kinds)
        ctl.mark_reviewed(rid, run["result_revision"], memo="  A는 쓰고 B의 위험은 따로 본다  ")
        done = self.run_view(ctl, rid)
        self.assertTrue(done["reviewed"])
        self.assertEqual(done["review_memo"], "A는 쓰고 B의 위험은 따로 본다")
        self.assertEqual(ctl.view()["tasks"][0]["status"], "done")
        with self.assertRaises(c.ControllerError):
            ctl.synthesize(rid)
        with self.assertRaises(c.ControllerError):
            ctl.synthesize_with_model(rid, "claude-code", ROSTER["claude"])
        with self.assertRaises(ReportError):
            build_report(ctl.view(rid), rid)
        with self.assertRaises(c.ControllerError):
            ctl.mark_reviewed(rid, run["result_revision"], memo="x" * (c.MAX_MEMO_CHARS + 1))

    def test_a_failed_member_leaves_an_empty_place_without_a_reduction_step(self):
        ctl = self.controller(Recording(outcomes={"codex": "fail"}))
        rid = self.create(ctl)
        self.assertTrue(ctl.wait_idle())
        run = self.run_view(ctl, rid)
        self.assertTrue(run["gate"]["collected"])
        self.assertEqual({p["pid"]: p["state"] for p in run["participants"]},
                         {"claude": c.ACCEPTED, "codex": c.REJECTED})
        self.assertFalse(run["gate"]["can_approve_reduction"])
        self.assertEqual(ctl.view()["tasks"][0]["status"], "my_turn")

    def test_an_unconfirmed_ending_blocks_collection_until_the_person_confirms_it(self):
        ctl = self.controller(Recording(outcomes={"codex": "unknown"}))
        rid = self.create(ctl)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.part(ctl, rid, "codex")["state"], c.UNKNOWN)
        self.assertFalse(self.run_view(ctl, rid)["gate"]["collected"])
        task = ctl.view()["tasks"][0]
        self.assertEqual((task["status"], task["runs"][0]["action"]), ("problem", "종료·실패 확인"))
        with self.assertRaises(c.ControllerError):
            ctl.mark_reviewed(rid, 0)
        ctl.acknowledge_unknown(rid, "codex")
        self.assertTrue(self.run_view(ctl, rid)["gate"]["collected"])
        self.assertEqual(ctl.executor.started.count("codex"), 1)            # 다시 부르지 않는다

    def test_unsupported_layouts_and_assignments_leave_nothing_behind(self):
        ctl = self.controller(Recording(), max_parallel=0)
        one = {"claude": {"task": "A와 B를 본다", "sources": ["a.md", "b.md"]}}
        cases = [
            ("isolated+general", ["claude"], board("claude", isolated=("codex",)), one),
            # CLI 오케스트레이터는 분담 제안(카드 #135)으로 받는다. 원본 앱 카드는 여전히 거절한다
            ("original-app orchestrator", ["claude"], board("claude", orchestrator=("claude-app",)), one),
            ("original app", ["antigravity-app"], board("antigravity-app"),
             {"antigravity-app": {"task": "t", "sources": ["a.md", "b.md"]}}),
            ("no assignment", ["claude"], board("claude"), None),
            ("missing member", ["claude", "codex"], board("claude", "codex"), one),
            ("empty task", ["claude"], board("claude"), {"claude": {"task": "  ", "sources": ["a.md", "b.md"]}}),
            ("long task", ["claude"], board("claude"),
             {"claude": {"task": "x" * (c.MAX_TASK_CHARS + 1), "sources": ["a.md", "b.md"]}}),
            ("unknown source", ["claude"], board("claude"), {"claude": {"task": "t", "sources": ["a.md", "b.md", "z.md"]}}),
            ("repeated source", ["claude"], board("claude"), {"claude": {"task": "t", "sources": ["a.md", "a.md", "b.md"]}}),
            ("unused source", ["claude"], board("claude"), {"claude": {"task": "t", "sources": ["a.md"]}}),
            ("extra field", ["claude"], board("claude"),
             {"claude": {"task": "t", "sources": ["a.md", "b.md"], "summary": "AI 요약"}}),
        ]
        for name, pids, layout, work in cases:
            with self.subTest(name), self.assertRaises(c.ControllerError):
                ctl.create_run("목표", [ROSTER[p] for p in pids], min_independent=1, role_board=layout,
                               roster=ROSTER, sources=SOURCES, assignments=work)
        with self.assertRaises(c.ControllerError):   # 격리 실행에는 맡길 일을 주지 않는다
            ctl.create_run("목표", [ROSTER["codex"]], min_independent=1, role_board=board(isolated=("codex",)),
                           roster=ROSTER, assignments={"codex": {"task": "t", "sources": []}})
        for table in TABLES:
            self.assertEqual(self.count(table), 0, table)

    def test_the_preview_fixes_every_member_input_and_a_changed_assignment_is_refused(self):
        ctl = self.controller(Recording(), max_parallel=0)
        options = dict(min_independent=1, role_board=board("claude", "codex"), roster=ROSTER, sources=SOURCES,
                       task_title="미리 보기")
        members = [ROSTER["claude"], ROSTER["codex"]]
        preview = ctl.prepare_run("목표", members, assignments=WORK, **options)
        self.assertEqual(self.count("runs"), 0)
        self.assertEqual(preview["mode"], "general")
        self.assertEqual(preview["calls"]["draft_cli"], 2)
        self.assertEqual(preview["assignments"]["codex"]["sources"][0]["kind"], "original")
        options.update(run_id=preview["run_id"], confirmation=preview["confirmation"])
        changed = {**WORK, "codex": {"task": "다른 일", "sources": ["b.md"]}}
        with self.assertRaises(c.ControllerError):
            ctl.create_run("목표", members, assignments=changed, **options)
        self.assertEqual(self.count("runs"), 0)
        rid = ctl.create_run("목표", members, assignments=WORK, **options)
        saved = {p["pid"]: p["assignment"] for p in self.run_view(ctl, rid)["participants"]}
        for pid, item in preview["assignments"].items():
            self.assertEqual({k: saved[pid][k] for k in item}, item)

    def test_cancel_stops_members_that_have_not_started(self):
        ex = Recording(hold=("claude",))
        ctl = self.controller(ex, max_parallel=1)
        rid = self.create(ctl)
        self.assertTrue(support.wait_for(lambda: self.part(ctl, rid, "claude")["state"] == c.RUNNING))
        ctl.cancel_run(rid)
        self.assertEqual(self.part(ctl, rid, "codex")["status"], "cancelled_before_start")
        ex.release("claude")
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(ex.started, ["claude"])
        run = self.run_view(ctl, rid)
        self.assertEqual(run["gate"]["status"], "cancelled")
        self.assertFalse(run["gate"]["collected"])
        self.assertEqual(ctl.view()["tasks"][0]["status"], "problem")

    def test_real_calls_are_reserved_once_per_member_under_the_same_cap(self):
        ex = RealLike()
        ctl = self.controller(ex, max_real_calls=1)
        rid = self.create(ctl)
        self.assertTrue(ctl.wait_idle())
        reserved = [e for e in events(self.store, rid) if e["kind"] == "live_call_reserved"]
        self.assertEqual(len(reserved), 1)
        states = {p["pid"]: (p["state"], p["status"]) for p in self.run_view(ctl, rid)["participants"]}
        self.assertEqual(sorted(s for s, _ in states.values()), [c.ACCEPTED, c.REJECTED])
        self.assertIn(("rejected", "process_failed_to_start"), states.values())   # 상한이 차서 시작하지 않음
        self.assertEqual(len(ex.started), 1)
        self.assertEqual(ctl.call_budget(), {"used": 1, "cap": 1})

    def test_restart_marks_a_running_member_unknown_and_waits_to_resume_the_rest(self):
        ctl = self.controller(Recording(), max_parallel=0)
        rid = self.create(ctl)
        self.assertTrue(ctl.shutdown())
        with self.store.tx() as tx:
            tx.execute("UPDATE participants SET state = 'running', attempt = 'lost' WHERE run_id = ? AND pid = 'claude'", rid)
        self.store.close()
        reopened = Store(self.tmp / "store" / "journal.db")
        self.addCleanup(reopened.close)
        ex = Recording()
        again = c.Controller(reopened, ex, work_root=str(self.tmp / "work"))
        self.addCleanup(again.shutdown)
        self.assertTrue(again.paused)
        self.assertEqual(ex.started, [])
        parts = {p["pid"]: p for p in next(r for r in again.view()["runs"] if r["run_id"] == rid)["participants"]}
        self.assertEqual((parts["claude"]["state"], parts["claude"]["status"]), (c.UNKNOWN, "controller_restarted"))
        self.assertEqual(parts["codex"]["state"], c.QUEUED)
        again.acknowledge_unknown(rid, "claude")
        again.resume()
        self.assertTrue(again.wait_idle())
        run = next(r for r in again.view()["runs"] if r["run_id"] == rid)
        self.assertTrue(run["gate"]["collected"])
        self.assertEqual(ex.started, ["codex"])                               # 멈춘 팀원을 다시 부르지 않는다

    def test_a_changed_assignment_or_member_source_starts_nothing(self):
        ex = Recording()
        ctl = self.controller(ex, max_parallel=0)
        rid = self.create(ctl)
        with self.store.tx() as tx:
            tx.execute("UPDATE assignments SET task = '바꾼 일' WHERE run_id = ? AND pid = 'claude'", rid)
        folder = ctl._member_source_dir(rid, "codex")
        if os.name == "posix":
            os.chmod(Path(folder, "b.md"), 0o644)
        Path(folder, "b.md").write_text("바꿔치기", encoding="utf-8")
        ctl.max_parallel = 2
        ctl.pump()
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(ex.started, [])
        for pid in ("claude", "codex"):
            self.assertEqual(self.part(ctl, rid, pid)["status"], "process_failed_to_start")
        refusals = [e["spec"]["refused"] for e in events(self.store, rid) if e["kind"] == "attempt_started"]
        self.assertTrue(any("assignment differs" in r for r in refusals))
        self.assertTrue(any("snapshot changed" in r for r in refusals))

    def test_a_self_consistent_rewrite_of_one_assignment_still_starts_nothing(self):
        # 맡긴 일·입력 전문·해시·크기를 서로 맞게 함께 바꿔도, 실행을 만들 때 묶은 입력 해시와 다르면 거절한다
        ex = Recording()
        ctl = self.controller(ex, max_parallel=0)
        rid = self.create(ctl, pids=("codex",), work={"codex": {"task": "원래 일", "sources": ["a.md", "b.md"]}})
        row = ctl._assignment(rid, "codex")
        prompt = c.GENERAL_PROMPT.format(question="전체 목표: 도입 여부 판단", task="바꾼 일") + \
            row["prompt"][len(c.GENERAL_PROMPT.format(question="전체 목표: 도입 여부 판단", task="원래 일")):]
        data = prompt.encode("utf-8")
        with self.store.tx() as tx:
            tx.execute("UPDATE assignments SET task = ?, prompt = ?, input_sha256 = ?, input_bytes = ? "
                       "WHERE run_id = ? AND pid = 'codex'", "바꾼 일", prompt, hashlib.sha256(data).hexdigest(),
                       len(data), rid)
        ctl.max_parallel = 1
        ctl.pump()
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(ex.started, [])
        self.assertEqual(self.part(ctl, rid, "codex")["status"], "process_failed_to_start")
        refused = next(e for e in events(self.store, rid) if e["kind"] == "attempt_started")
        self.assertIn("input bundled when the run was created", refused["spec"]["refused"])

    def test_a_general_run_does_not_start_while_another_run_is_drafting(self):
        ctl = self.controller(Recording(), max_parallel=0)
        ctl.create_run("격리 질문", [ROSTER["codex"]], min_independent=1, role_board=board(isolated=("codex",)),
                       roster=ROSTER)
        with self.assertRaises(c.ControllerError):
            self.create(ctl)
        self.assertEqual(self.count("assignments"), 0)

    def test_a_schema_eight_ledger_is_backed_up_and_its_runs_stay_isolated(self):
        ctl = self.controller(Recording(), max_parallel=0)
        rid = ctl.create_run("이전 실행", [support.cli("a")], min_independent=1)
        self.assertTrue(ctl.shutdown())
        self.store.close()
        path = self.tmp / "store" / "journal.db"
        db = sqlite3.connect(path)
        db.executescript("ALTER TABLE runs DROP COLUMN mode; DROP TABLE assignments; PRAGMA user_version = 8;")
        db.close()
        reopened = Store(path)
        self.addCleanup(reopened.close)
        self.assertEqual(len(list(path.parent.glob("journal.db.v8-*.bak"))), 1)
        self.assertEqual(reopened.row("PRAGMA user_version")[0], SCHEMA_VERSION)
        again = c.Controller(reopened, Recording(), max_parallel=0)
        self.addCleanup(again.shutdown)
        run = next(r for r in again.view()["runs"] if r["run_id"] == rid)
        self.assertEqual(run["mode"], "isolated")
        self.assertIsNotNone(run["quorum"])


class GeneralTeamHttpTests(support.Base):
    """실제 서버 경로로 미리 보기 → 시작 → 모두 끝남 → 메모와 판단 완료. 실행은 합성이다."""

    def setUp(self):
        super().setUp()
        self.ctl = self.controller(Recording())
        self.token = "T" * 43
        self.httpd = server._Server(("127.0.0.1", 0), server.BaseHTTPRequestHandler)
        self.port = self.httpd.server_address[1]
        self.httpd.RequestHandlerClass = server.make_handler(self.ctl, self.token, self.port)
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def call(self, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("POST" if body is not None else "GET", path,
                         json.dumps(body).encode() if body is not None else None,
                         {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
            reply = conn.getresponse()
            return reply.status, json.loads(reply.read())
        finally:
            conn.close()

    def test_preview_start_collect_and_review_with_a_memo(self):
        body = {"question": "HTTP 목표", "participants": [{"pid": "claude"}, {"pid": "codex"}],
                "role_board": board("claude", "codex"), "task_title": "일반 작업",
                "sources": [{"name": n, "text": t} for n, t in SOURCES], "assignments": WORK}
        status, preview = self.call("/api/runs/preview", body)
        self.assertEqual(status, 200, preview)
        self.assertEqual(sorted(preview["assignments"]), ["claude", "codex"])
        self.assertEqual(self.call("/api/state")[1]["runs"], [])
        body.update(run_id=preview["run_id"], confirmation=preview["confirmation"])
        self.assertEqual(self.call("/api/runs", body)[0], 200)
        self.assertTrue(self.ctl.wait_idle())
        state = self.call("/api/state")[1]
        run = state["runs"][0]
        self.assertTrue(run["gate"]["collected"])
        self.assertEqual(state["tasks"][0]["runs"][0]["action"], "결과 모아 판단")
        path = f"/api/runs/{run['run_id']}/reviewed"
        self.assertEqual(self.call(path, {"revision": run["result_revision"], "memo": 3})[0], 400)
        self.assertEqual(self.call(path, {"revision": run["result_revision"], "memo": "모아 본 결론"})[0], 200)
        state = self.call("/api/state")[1]
        self.assertEqual(state["runs"][0]["review_memo"], "모아 본 결론")
        self.assertEqual(state["tasks"][0]["status"], "done")
