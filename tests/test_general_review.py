"""GR-1: 일반 팀원 교차검토. 합성 실행기만 — 실제 모델·CLI를 부르지 않는다.

설계(docs/architecture/general-team-review) §6 GR-1과 §7 확인표를 고정한다: 모음 뒤에만, 입력 확인(미리보기)은 호출·
예약 없이 하고 확인 값이 맞을 때만 시작, 확인 뒤 답·맡긴 일·결과 판이 바뀌면 거절, 한 라운드, 맡은 일·자료 이름/hash만
전달(자료 본문·자동 기억 없음), 실패한 팀원은 채우지 않고 결과 없음으로 표시, 일반 실행은 검토 뒤에도 collected(공개·
정족수·합성 관문 없음), 진행·대기·종료 미확인이 내 차례·판단 완료·선행 준비에 반영, 격리 검토는 그대로.
"""
import hashlib
import http.client
import json
import sqlite3
import threading
from unittest import mock

from app import controller as c, cross_review as cross, server, usage
from app.domain import ParticipantSpec
from app.store import SCHEMA_VERSION, Store, StoreError, events
import test_app_controller as support
from test_cross_review import Reviewer

ROSTER = server.PARTICIPANTS
SOURCES = [("a.md", "자료 A 원문 · 표식 SRC-A"), ("b.md", "자료 B 원문 · 표식 SRC-B")]
WORK = {"claude": {"task": "A를 읽고 장단점을 정리", "sources": ["a.md"]},
        "codex": {"task": "B를 읽고 위험을 정리", "sources": ["b.md"]}}


def board(*general):
    return {"supervisor": [], "orchestrator": [], "isolated": [], "general": list(general), "input_mode": "original"}


class GeneralReviewTests(support.Base):
    def collected(self, ctl, roster=ROSTER, work=WORK, sources=SOURCES, memory=None):
        kwargs = {} if memory is None else {"use_memory": memory}
        rid = ctl.create_run("전체 목표: 도입 여부 판단", [roster[p] for p in work], min_independent=1,
                             role_board=board(*work), roster=roster, sources=sources, assignments=work,
                             task_title="일반 검토 작업", **kwargs)
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(self.run_view(ctl, rid)["gate"]["collected"])
        return rid

    def start(self, ctl, rid, question=None):
        manifest = ctl.preview_cross_review(rid, question)
        return manifest, ctl.cross_review(rid, question, round_id=manifest["round_id"],
                                          confirmation=manifest["confirmation"])

    def round(self, ctl, rid):
        return self.run_view(ctl, rid)["cross_review"]

    def test_the_preview_calls_nothing_and_shows_every_input_that_the_round_then_sends(self):
        ex = Reviewer()
        ctl = self.controller(ex)
        rid = self.collected(ctl)
        started, events_before = list(ex.started), len(list(events(self.store, rid)))
        manifest = ctl.preview_cross_review(rid)
        self.assertEqual(ex.started, started)                                      # 모델을 부르지 않는다
        self.assertEqual(len(list(events(self.store, rid))), events_before)        # 원장도 쓰지 않는다
        self.assertIsNone(self.store.row("SELECT 1 FROM reviews"))
        self.assertEqual((manifest["contract"], manifest["mode"], manifest["calls"]), (cross.GENERAL_CONTRACT, "general", 2))
        self.assertEqual(manifest["result_revision"], self.run_view(ctl, rid)["result_revision"])
        self.assertEqual({m["pid"]: m["task"] for m in manifest["members"]},
                         {pid: item["task"] for pid, item in WORK.items()})
        self.assertEqual([s["name"] for s in manifest["members"][0]["sources"]], ["a.md"])
        again = ctl.preview_cross_review(rid)
        self.assertNotEqual(again["round_id"], manifest["round_id"])               # 미리보기마다 새 라운드 ID
        keys = ctl.cross_review(rid, round_id=manifest["round_id"], confirmation=manifest["confirmation"])
        self.assertTrue(ctl.wait_idle())
        view = self.round(ctl, rid)
        self.assertEqual((view["mode"], view["round_id"], view["confirmation"], view["independence"]),
                         ("general", manifest["round_id"], manifest["confirmation"], "general_team_not_independent"))
        sent = {item["pid"]: item["prompt"] for item in manifest["reviewers"]}
        self.assertEqual(ex.prompts["reviewer"], list(sent.values()))              # 검토자가 받은 입력 전문, 차례대로
        for review, key in zip(view["reviews"], keys):
            self.assertEqual(review["review_id"], key)
            self.assertEqual(review["state"], c.ACCEPTED)
            pid = review["reviewer"]["pid"]
            self.assertEqual(review["prompt"], sent[pid])                          # 확인한 입력 그대로
            self.assertEqual(review["reply"]["checks"]["independence"], "general_team_not_independent")
            self.assertEqual(review["snapshot"]["confirmation"], manifest["confirmation"])
            other = "codex" if pid == "claude" else "claude"
            self.assertEqual(review["reply"]["findings"][0]["target_pid"], other)
            self.assertEqual(review["reply"]["findings"][0]["source_check"], "exact_match")
            self.assertTrue(review["targets"]["D1"]["fresh"])

    def test_reviewers_get_tasks_and_source_names_but_no_source_bodies_or_memory(self):
        ex = Reviewer()
        ctl = self.controller(ex)
        rid = self.collected(ctl)
        manifest, _ = self.start(ctl, rid, "분담 사이 충돌을 찾아라")
        self.assertTrue(ctl.wait_idle())
        for item in manifest["reviewers"]:
            text = item["prompt"]
            self.assertTrue(text.startswith(cross.MARKER))
            nonce = text.split("이번 경계 표식: ", 1)[1].split("\n", 1)[0]
            for piece in ("전체 목표: 도입 여부 판단", "분담 사이 충돌을 찾아라", "A를 읽고 장단점을 정리",
                          "B를 읽고 위험을 정리", "a.md", "b.md", f"<<<D1 시작 {nonce}>>>", f"<<<내 결과 시작 {nonce}>>>"):
                self.assertIn(piece, text)
            for hidden in ("SRC-A", "SRC-B", "anthropic", "openai", "이전 작업의 기억"):
                self.assertNotIn(hidden, text)
        self.assertEqual(manifest["source_bodies"], "not_sent")
        self.assertEqual(manifest["memory_pack"], "not_added")
        self.assertTrue(self.run_view(ctl, rid)["gate"]["collected"])
        self.assertFalse(self.run_view(ctl, rid)["gate"]["revealed"])             # 검토가 공개로 바꾸지 않는다
        self.assertIsNone(self.run_view(ctl, rid)["quorum"])
        for command in (lambda: ctl.synthesize(rid), lambda: ctl.propose_next(rid)):
            with self.assertRaises((c.ControllerError, ValueError)):
                command()

    def test_a_round_needs_its_confirmation_and_refuses_anything_changed_after_preview(self):
        ex = Reviewer()
        ctl = self.controller(ex)
        rid = self.collected(ctl)
        manifest = ctl.preview_cross_review(rid)
        cases = {"no confirmation": dict(round_id=manifest["round_id"]),
                 "wrong confirmation": dict(round_id=manifest["round_id"], confirmation="0" * 64),
                 "other round id": dict(round_id="g" + "0" * 32, confirmation=manifest["confirmation"]),
                 "bad round id": dict(round_id="x", confirmation=manifest["confirmation"])}
        for name, kwargs in cases.items():
            with self.subTest(name), self.assertRaises(c.ControllerError):
                ctl.cross_review(rid, **kwargs)
        with self.subTest("other question"), self.assertRaises(c.ControllerError):
            ctl.cross_review(rid, "다른 질문", round_id=manifest["round_id"], confirmation=manifest["confirmation"])
        # 확인 뒤 결과 판이 바뀐다(결과 모으기 실패도 새 결과다) → 거절
        with self.store.tx() as tx:
            tx.event(rid, "collation_failed", collation_id="x")
        with self.assertRaisesRegex(c.ControllerError, "바뀌었"):
            ctl.cross_review(rid, round_id=manifest["round_id"], confirmation=manifest["confirmation"])
        self.assertIsNone(self.store.row("SELECT 1 FROM reviews"))
        self.assertNotIn(cross.MARKER, "".join(p for ps in ex.prompts.values() for p in ps))   # 검토 호출 없음

    def test_a_changed_answer_or_task_after_preview_is_refused_without_a_call(self):
        cases = {"answer": "UPDATE drafts SET text = 'CORRUPTED', sha256 = ? WHERE pid = 'codex' AND run_id = ?",
                 "task": "UPDATE assignments SET task = '바꾼 일' WHERE pid = 'codex' AND run_id = ? AND ? IS NOT NULL"}
        ex = Reviewer()
        ctl = self.controller(ex)
        for name, sql in cases.items():
            with self.subTest(name):
                rid = self.collected(ctl)
                manifest = ctl.preview_cross_review(rid)
                with self.store.tx() as tx:
                    args = (hashlib.sha256(b"CORRUPTED").hexdigest(), rid) if name == "answer" else (rid, 1)
                    self.assertEqual(tx.execute(sql, *args), 1)
                with self.assertRaises(c.ControllerError):
                    ctl.cross_review(rid, round_id=manifest["round_id"], confirmation=manifest["confirmation"])
                self.assertIsNone(self.store.row("SELECT 1 FROM reviews WHERE run_id = ?", rid))

    def test_one_round_per_run_even_with_a_fresh_preview(self):
        ctl = self.controller(Reviewer())
        rid = self.collected(ctl)
        stale = ctl.preview_cross_review(rid)
        self.start(ctl, rid)
        self.assertTrue(ctl.wait_idle())
        with self.assertRaises(c.ControllerError):
            ctl.preview_cross_review(rid)
        with self.assertRaises(c.ControllerError):
            ctl.cross_review(rid, round_id=stale["round_id"], confirmation=stale["confirmation"])
        self.assertEqual(self.store.row("SELECT COUNT(*) AS n FROM reviews")["n"], 2)

    def test_refused_before_collection_with_one_answer_and_without_confirmation_for_isolated_shape(self):
        ex = Reviewer(hold=("codex",))
        ctl = self.controller(ex)
        rid = ctl.create_run("목표", [ROSTER["claude"], ROSTER["codex"]], min_independent=1,
                             role_board=board("claude", "codex"), roster=ROSTER, sources=SOURCES, assignments=WORK)
        self.assertTrue(support.wait_for(lambda: "claude" in ex.started))
        with self.assertRaises(c.ControllerError):                                # 모두 끝나기 전
            ctl.preview_cross_review(rid)
        ex.release("codex")
        self.assertTrue(ctl.wait_idle())
        with self.assertRaisesRegex(c.ControllerError, "입력 확인"):              # 일반 실행은 확인 없이 시작하지 않는다
            ctl.cross_review(rid)
        failed = Reviewer(outcomes={"codex": "fail"})
        other = self.controller(failed)
        lone = self.collected(other)
        with self.assertRaisesRegex(c.ControllerError, "둘 이상"):               # 받은 결과가 하나뿐
            other.preview_cross_review(lone)

    def test_a_failed_member_is_listed_as_missing_and_never_filled(self):
        roster = {pid: ParticipantSpec(pid, pid.upper(), pid, c.CLI, "claude-code", "m") for pid in ("a", "b", "x")}
        work = {"a": {"task": "일 A", "sources": ["a.md"]}, "b": {"task": "일 B", "sources": ["b.md"]},
                "x": {"task": "일 X", "sources": []}}
        ex = Reviewer(outcomes={"x": "fail"})
        ctl = self.controller(ex)
        rid = self.collected(ctl, roster=roster, work=work)
        manifest, keys = self.start(ctl, rid)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(manifest["missing"], [{"pid": "x", "task": "일 X", "reason": "결과 없음"}])
        self.assertEqual([r["pid"] for r in manifest["reviewers"]], ["a", "b"])  # 실패한 팀원은 검토자가 아니다
        for item in manifest["reviewers"]:
            self.assertIn("결과가 없는 팀원(검토 대상 아님):\n- 맡은 일: 일 X", item["prompt"])
            self.assertNotIn("x의 답", item["prompt"])
        view = self.round(ctl, rid)
        self.assertEqual(len(keys), 2)
        self.assertEqual(view["missing_members"], manifest["missing"])
        self.assertTrue(all(set(r["labels"].values()) <= {"a", "b"} for r in view["reviews"]))

    def test_status_my_turn_and_judgment_follow_the_round(self):
        ctl = self.controller(Reviewer())
        rid = self.collected(ctl)
        revision = self.run_view(ctl, rid)["result_revision"]
        ctl.mark_reviewed(rid, revision, "검토 전 판단")
        self.assertEqual(ctl.view()["tasks"][0]["status"], "done")
        self.start(ctl, rid)
        self.assertTrue(ctl.wait_idle())
        task = ctl.view()["tasks"][0]
        self.assertEqual(task["status"], "my_turn")                               # 새 결과 → 다시 내 차례
        self.assertEqual(task["calls_used"], 4)                                   # 팀원 2 + 검토 2
        run = self.run_view(ctl, rid)
        self.assertGreater(run["result_revision"], revision)
        self.assertFalse(run["reviewed"])
        ctl.mark_reviewed(rid, run["result_revision"])
        self.assertEqual(ctl.view()["tasks"][0]["status"], "done")

    def test_a_running_or_queued_reviewer_blocks_judgment_and_shows_working(self):
        ex = HoldingReviewer()
        ctl = self.controller(ex)
        rid = self.collected(ctl)
        self.start(ctl, rid)
        self.assertTrue(support.wait_for(lambda: self.round(ctl, rid)["reviews"][0]["state"] == c.RUNNING))
        self.assertEqual([r["state"] for r in self.round(ctl, rid)["reviews"]], [c.RUNNING, c.QUEUED])
        view = ctl.view()
        task, run = view["tasks"][0], view["tasks"][0]["runs"][0]
        self.assertEqual((task["status"], run["active"]), ("working", True))
        self.assertEqual(next(s for s in run["steps"] if s["id"] == "review")["state"], "waiting")
        with self.assertRaises(c.ControllerError):
            ctl.mark_reviewed(rid, self.run_view(ctl, rid)["result_revision"])
        ex.gate.set()
        self.assertTrue(ctl.wait_idle())

    def test_an_unknown_reviewer_is_a_problem_until_acknowledged(self):
        ctl = self.controller(Reviewer(reviews=["unknown"]))
        rid = self.collected(ctl)
        _, (first, second) = self.start(ctl, rid)
        self.assertTrue(ctl.wait_idle())
        reviews = self.round(ctl, rid)["reviews"]
        self.assertEqual([(r["state"], r["status"]) for r in reviews],
                         [(c.UNKNOWN, reviews[0]["status"]), ("skipped", "earlier_reviewer_not_accepted")])
        run = ctl.view()["tasks"][0]["runs"][0]
        self.assertEqual((run["status"], run["action"], run["unsettled"]), ("problem", "종료·실패 확인", True))
        with self.assertRaises(c.ControllerError):
            ctl.mark_reviewed(rid, self.run_view(ctl, rid)["result_revision"])
        ctl.acknowledge_review_unknown(first)
        self.assertEqual(ctl.view()["tasks"][0]["status"], "my_turn")

    def test_search_and_usage_carry_the_round(self):
        ctl = self.controller(Reviewer())
        rid = self.collected(ctl)
        self.start(ctl, rid, "비용 가정을 따져라")
        self.assertTrue(ctl.wait_idle())
        found = ctl.search("비용 가정을 따져라")
        self.assertIn("review", [item["kind"] for item in found["items"]])
        self.assertEqual([item["role"] for item in usage.calls(self.run_view(ctl, rid))].count("cross_review"), 2)

    def test_isolated_rounds_keep_their_shape_and_need_no_confirmation(self):
        ctl = self.controller(Reviewer())
        rid = ctl.create_run("원래 질문", [ROSTER["claude"], ROSTER["codex"]], min_independent=2,
                             role_board={"supervisor": [], "orchestrator": [], "isolated": ["claude", "codex"],
                                         "general": [], "input_mode": "original"}, roster=ROSTER)
        self.assertTrue(ctl.wait_idle())
        with self.assertRaises(c.ControllerError):                                # 미리보기는 일반 실행에만
            ctl.preview_cross_review(rid)
        ctl.cross_review(rid)
        self.assertTrue(ctl.wait_idle())
        view = self.round(ctl, rid)
        self.assertEqual((view["mode"], view["independence"]), ("isolated", "post_reveal_not_independent"))
        self.assertTrue(all(r["snapshot"] is None for r in view["reviews"]))
        self.assertEqual(self.store.row("SELECT COUNT(*) AS n FROM reviews WHERE snapshot IS NULL")["n"], 2)


class GeneralReviewRestartTests(support.Base):
    collected = GeneralReviewTests.collected
    start = GeneralReviewTests.start

    def reopen(self):
        self.store.close()
        reopened = Store(self.tmp / "store" / "journal.db")
        self.addCleanup(reopened.close)
        ex = Reviewer()
        again = c.Controller(reopened, ex, work_root=str(self.tmp / "work"))
        self.addCleanup(again.shutdown)
        return again, ex

    def test_a_queued_reviewer_after_restart_waits_for_me_and_then_continues(self):
        ctl = self.controller(Reviewer())
        rid = self.collected(ctl)
        _, (first, second) = self.start(ctl, rid)
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(ctl.shutdown())
        with self.store.tx() as tx:
            tx.execute("UPDATE reviews SET state = 'queued', attempt = NULL, kind = NULL, result = NULL, status = NULL "
                       "WHERE review_id = ?", second)
        again, ex = self.reopen()
        self.assertTrue(again.paused)
        run = again.view()["tasks"][0]["runs"][0]
        self.assertEqual((run["status"], run["action"]), ("my_turn", "멈춘 교차검토 이어서 시작"))
        self.assertEqual(ex.started, [])
        again.resume()
        self.assertTrue(again.wait_idle())
        reviews = next(r for r in again.view()["runs"] if r["run_id"] == rid)["cross_review"]["reviews"]
        self.assertEqual([r["state"] for r in reviews], [c.ACCEPTED, c.ACCEPTED])
        self.assertEqual(reviews[1]["reply"]["checks"]["independence"], "general_team_not_independent")

    def test_a_changed_snapshot_is_not_started(self):
        ctl = self.controller(Reviewer())
        rid = self.collected(ctl)
        _, (first, second) = self.start(ctl, rid)
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(ctl.shutdown())
        with self.store.tx() as tx:
            snapshot = json.loads(self.store.row("SELECT snapshot FROM reviews WHERE review_id = ?", second)["snapshot"])
            snapshot["own"]["task"] = "바꾼 일"
            tx.execute("UPDATE reviews SET state = 'queued', attempt = NULL, kind = NULL, result = NULL, status = NULL, "
                       "snapshot = ? WHERE review_id = ?", json.dumps(snapshot, sort_keys=True, ensure_ascii=False), second)
        again, ex = self.reopen()
        again.resume()
        self.assertTrue(again.wait_idle())
        reviews = next(r for r in again.view()["runs"] if r["run_id"] == rid)["cross_review"]["reviews"]
        self.assertEqual(reviews[1]["state"], "skipped")
        self.assertIn("digest", reviews[1]["status"])
        self.assertEqual(ex.started, [])

    def test_a_schema_seventeen_ledger_is_backed_up_and_old_rounds_read_as_isolated(self):
        ctl = self.controller(Reviewer())
        rid = ctl.create_run("원래 질문", [ROSTER["claude"], ROSTER["codex"]], min_independent=2,
                             role_board={"supervisor": [], "orchestrator": [], "isolated": ["claude", "codex"],
                                         "general": [], "input_mode": "original"}, roster=ROSTER)
        self.assertTrue(ctl.wait_idle())
        ctl.cross_review(rid)
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(ctl.shutdown())
        self.store.close()
        path = self.tmp / "store" / "journal.db"
        db = sqlite3.connect(path)
        db.executescript("ALTER TABLE reviews DROP COLUMN snapshot; ALTER TABLE reviews DROP COLUMN snapshot_sha256; "
                         "PRAGMA user_version = 17;")
        db.close()
        reopened = Store(path)
        self.addCleanup(reopened.close)
        self.assertEqual(len(list(path.parent.glob("journal.db.v17-*.bak"))), 1)
        self.assertEqual(reopened.row("PRAGMA user_version")[0], SCHEMA_VERSION)
        again = c.Controller(reopened, Reviewer(), work_root=str(self.tmp / "work"))
        self.addCleanup(again.shutdown)
        view = next(r for r in again.view()["runs"] if r["run_id"] == rid)["cross_review"]
        self.assertEqual((view["mode"], [r["state"] for r in view["reviews"]]), ("isolated", [c.ACCEPTED, c.ACCEPTED]))
        reopened.close()
        with mock.patch("app.store.SCHEMA_VERSION", 17), self.assertRaises(StoreError):   # 옛 코드는 새 원장을 거절한다
            Store(path)


class GeneralReviewHttpTests(support.Base):
    def setUp(self):
        super().setUp()
        self.ctl = self.controller(Reviewer())
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

    def test_preview_then_start_over_http(self):
        rid = GeneralReviewTests.collected(self, self.ctl)
        path = f"/api/runs/{rid}/cross-review"
        status, manifest = self.call(path + "/preview", {"question": "분담 충돌"})
        self.assertEqual(status, 200, manifest)
        self.assertEqual(self.call(path + "/preview", {"question": 3})[0], 400)
        self.assertEqual(self.call(path, {"question": "분담 충돌"})[0], 400)                # 확인 없이
        status, body = self.call(path, {"question": "분담 충돌", "round_id": manifest["round_id"],
                                        "confirmation": manifest["confirmation"]})
        self.assertEqual(status, 200, body)
        self.assertEqual(len(body["review_ids"]), 2)
        self.assertTrue(self.ctl.wait_idle())
        state = self.call("/api/state")[1]
        self.assertEqual([r["state"] for r in state["runs"][0]["cross_review"]["reviews"]], [c.ACCEPTED, c.ACCEPTED])


class HoldingReviewer(Reviewer):
    """검토 호출만 gate가 열릴 때까지 기다린다. 팀원 초안은 바로 끝난다."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gate = threading.Event()

    def execute(self, spec, prompt, work_dir, timeout, *, cancel=None):
        if prompt.startswith(cross.MARKER):
            self.gate.wait(10)
        return super().execute(spec, prompt, work_dir, timeout, cancel=cancel)
