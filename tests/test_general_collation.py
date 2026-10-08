"""GR-3: 고른 판으로 결과 모으기. 합성 실행기와 모의 CLI 답만 — 실제 모델·CLI를 부르지 않는다.

설계(docs/architecture/general-team-review) §6 GR-3과 §7 확인표를 고정한다: 입력 확인은 호출·예약 없이 하고, 팀원별
판(원래 결과 또는 받아들인 수정 판)/hash·남은 지적·누락을 확인 값에 묶어 같을 때만 시작한다. 확인 뒤 판·처분·결과가
바뀌면 거절하고, 수정 판이 있는데 판을 고르지 않은 예전 호출은 원래 결과를 몰래 쓰지 않도록 거절한다. 인용은 고른 판의
원문과 대조한다. 옛 모음은 소급해 바꾸지 않는다(원래 결과). 일반 실행은 그 뒤에도 collected다.
"""
import http.client
import json
import sqlite3
import threading
from unittest import mock

from app import collate, controller as c, fake_cli, server
from app.report import ReportError, revision_report
from app.store import SCHEMA_VERSION, Store, StoreError
from core import adapters, runner
import test_app_controller as support
import test_general_review as gr1
from test_app_controller import SLOW_RUNNER_TIMEOUT
from test_revisions import RevisionExecutor

ROSTER, WORK, SOURCES = gr1.ROSTER, gr1.WORK, gr1.SOURCES


def board(*general):
    return {**gr1.board(*general), "orchestrator": ["claude"]}


class Team(RevisionExecutor):
    """검토·수정·재검토는 RevisionExecutor대로, 결과 모으기는 모의 CLI처럼(팀원 결과의 첫 줄을 인용) 답한다."""

    def execute(self, spec, prompt, work_dir, timeout, *, cancel=None):
        if not prompt.startswith(collate.MARKER):
            return super().execute(spec, prompt, work_dir, timeout, cancel=cancel)
        self.started.append(spec.pid)
        result = runner.RunResult(("synthetic",), runner.EXITED, 0, support.claude_stdout(fake_cli.collate_reply(prompt)),
                                  "", False, False, 5, 0, True, containment=runner.JOB_OBJECT,
                                  input_delivery=runner.INPUT_COMPLETE)
        return result, adapters.interpret("claude-code", result, requested_model="m")


class GeneralCollationTests(support.Base):
    def team(self, ctl, *, revise=True, recheck=True):
        """모은 일반 실행 → 교차검토 → (claude 수정 → codex 재검토). 실행 ID와 수정 판 ID."""
        rid = ctl.create_run("전체 목표: 도입 여부 판단", [ROSTER[p] for p in WORK], min_independent=1,
                             role_board=board(*WORK), roster=ROSTER, sources=SOURCES, assignments=WORK,
                             task_title="고른 판 취합")
        self.assertTrue(ctl.wait_idle())
        manifest = ctl.preview_cross_review(rid)
        ctl.cross_review(rid, round_id=manifest["round_id"], confirmation=manifest["confirmation"])
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        key = None
        if revise:
            p = ctl.revisions.prepare(rid, "claude")
            key = ctl.revisions.revise(rid, "claude", p["revision_id"], p["confirmation"])
            self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
            if recheck:
                ctl.revisions.recheck(key, "codex")
                self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        return rid, key

    def test_the_chosen_revision_is_what_the_orchestrator_reads_and_quotes(self):
        ex = Team()
        ctl = self.controller(ex)
        rid, key = self.team(ctl)
        run = self.run_view(ctl, rid)
        original = next(p for p in run["participants"] if p["pid"] == "claude")["draft"]
        revised = run["answer_revisions"][0]["reply"]["answer"]
        started, calls = len(ex.started), ctl.view()["tasks"][0]["calls_used"]
        m = ctl.preview_collation(rid, {"claude": key})
        self.assertEqual((len(ex.started), ctl.view()["tasks"][0]["calls_used"]), (started, calls))   # 부르지 않는다
        self.assertIsNone(self.store.row("SELECT 1 FROM collations"))
        self.assertEqual((m["contract"], m["mode"], m["calls"], m["result_revision"]),
                         (collate.SELECTION_CONTRACT, "general", 1, run["result_revision"]))
        mine, other = m["members"]
        self.assertEqual((mine["pid"], mine["version"], mine["rechecked"], mine["task"]),
                         ("claude", key, True, WORK["claude"]["task"]))
        self.assertEqual(mine["sha256"], run["answer_revisions"][0]["reply"]["sha256"])
        self.assertEqual({o["from"] for o in mine["open"]}, {"revision", "recheck"})   # 모의 응답은 반례를 남겨 둔다
        self.assertEqual((other["version"], other["rechecked"]), ("original", None))
        self.assertTrue(other["open"] and all(o["from"] == "review" for o in other["open"]))
        self.assertIn(revised, m["prompt"])
        self.assertNotIn(original + "\n결과:", m["prompt"])
        for hidden in ("SRC-A", "SRC-B"):
            self.assertNotIn(hidden, m["prompt"])                                     # 자료 본문은 보내지 않는다
        cid = ctl.collate(rid, {"claude": key}, collation_id=m["collation_id"], confirmation=m["confirmation"])
        self.assertEqual(cid, m["collation_id"])
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        self.assertIn(m["prompt"], [x for sent in ex.prompts.values() for x in sent])   # 확인한 입력 그대로 보냈다
        run = self.run_view(ctl, rid)
        col = run["collations"][0]
        self.assertEqual(col["state"], c.ACCEPTED)
        self.assertTrue(col["selection_intact"])
        self.assertEqual([x["version"] for x in col["selection"]["members"]], [key, "original"])
        quote = col["reply"]["claims"][0]["quotes"][0]
        self.assertEqual((quote["member"], quote["source_check"]), ("T1", "exact_match"))
        self.assertTrue(revised.startswith(quote["text"]))                            # 고른 판의 원문과 대조했다
        self.assertTrue(run["gate"]["collected"])
        self.assertFalse(run["gate"]["revealed"])
        self.assertEqual(ctl.view()["tasks"][0]["status"], "my_turn")
        with self.assertRaises(c.ControllerError):
            ctl.collate(rid, {"claude": key}, collation_id=m["collation_id"], confirmation=m["confirmation"])
        report = revision_report(ctl.view(), rid)
        self.assertEqual(report["collation_scope"], "selected_versions")
        self.assertEqual([x["version"] for x in report["collations"][0]["members"]], [key, "original"])
        with self.store.tx() as tx:
            tx.execute("UPDATE collations SET selection = replace(selection, ?, ?)", key, "rev-" + "0" * 32)
        with self.assertRaises(ReportError):
            revision_report(ctl.view(), rid)

    def test_a_changed_choice_disposition_or_result_after_the_preview_starts_nothing(self):
        ex = Team()
        ctl = self.controller(ex)
        rid, key = self.team(ctl, recheck=False)
        m = ctl.preview_collation(rid, {"claude": key})
        self.assertFalse(m["members"][0]["rechecked"])
        started = len(ex.started)
        with self.assertRaises(c.ControllerError):                                    # 다른 판을 고르면 확인 값이 다르다
            ctl.collate(rid, {"claude": "original"}, collation_id=m["collation_id"], confirmation=m["confirmation"])
        review = self.run_view(ctl, rid)["cross_review"]["reviews"][0]
        ctl.set_review_disposition(review["review_id"], 0, "rejected")                # 원래 결과에 남은 지적이 바뀐다
        o = ctl.preview_collation(rid)
        ctl.set_review_disposition(review["review_id"], 0, "qualified")
        with self.assertRaises(c.ControllerError):
            ctl.collate(rid, None, collation_id=o["collation_id"], confirmation=o["confirmation"])
        ctl.revisions.recheck(key, "codex")                                           # 새 결과(재검토)
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        started = len(ex.started)
        with self.assertRaises(c.ControllerError):
            ctl.collate(rid, {"claude": key}, collation_id=m["collation_id"], confirmation=m["confirmation"])
        self.assertEqual(len(ex.started), started)
        self.assertIsNone(self.store.row("SELECT 1 FROM collations"))

    def test_choices_must_name_a_members_own_accepted_revision(self):
        ctl = self.controller(Team())
        rid, key = self.team(ctl)
        for choices in ({"codex": key}, {"nobody": "original"}, {"claude": "rev-" + "f" * 32}, {"claude": 3}, ["claude"]):
            with self.assertRaises(c.ControllerError):
                ctl.preview_collation(rid, choices)
        for bad in ("x", "c0000-000000-" + "g" * 32, None):
            with self.assertRaises(c.ControllerError):
                ctl.collate(rid, {"claude": key}, collation_id=bad, confirmation="0" * 64)
        with self.assertRaises(c.ControllerError):   # 수정 판이 있으면 판을 고르지 않은 예전 호출은 원래 결과를 몰래 쓰지 않는다
            ctl.collate(rid)
        self.assertIsNone(self.store.row("SELECT 1 FROM collations"))

    def test_originals_without_revisions_still_collate_and_record_what_they_used(self):
        ctl = self.controller(Team())
        rid, _ = self.team(ctl, revise=False)
        cid = ctl.collate(rid)                                                        # 예전 호출(확인 값 없음)
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        col = self.run_view(ctl, rid)["collations"][0]
        self.assertEqual((col["collation_id"], col["state"]), (cid, c.ACCEPTED))
        self.assertEqual([x["version"] for x in col["selection"]["members"]], ["original", "original"])
        self.assertEqual(revision_report(ctl.view(), rid)["collation_scope"], "original_answers_only")

    def test_a_schema_eighteen_ledger_keeps_old_collations_as_originals(self):
        ctl = self.controller(Team())
        rid, _ = self.team(ctl, revise=False)
        ctl.collate(rid)
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        self.assertTrue(ctl.shutdown())
        self.store.close()
        path = self.tmp / "store" / "journal.db"
        db = sqlite3.connect(path)
        db.executescript("ALTER TABLE collations DROP COLUMN selection; "
                         "ALTER TABLE collations DROP COLUMN selection_sha256; PRAGMA user_version = 18;")
        db.close()
        reopened = Store(path)
        self.addCleanup(reopened.close)
        self.assertEqual(len(list(path.parent.glob("journal.db.v18-*.bak"))), 1)
        self.assertEqual(reopened.row("PRAGMA user_version")[0], SCHEMA_VERSION)
        again = c.Controller(reopened, Team(), work_root=str(self.tmp / "work"))
        self.addCleanup(again.shutdown)
        col = next(r for r in again.view()["runs"] if r["run_id"] == rid)["collations"][0]
        self.assertEqual((col["state"], col["selection"], col["selection_intact"]), (c.ACCEPTED, None, None))
        self.assertEqual(revision_report(again.view(), rid)["collations"][0]["members"], None)
        self.assertTrue(again.shutdown())
        reopened.close()
        with mock.patch("app.store.SCHEMA_VERSION", 18), self.assertRaises(StoreError):   # 옛 코드는 새 원장을 거절한다
            Store(path)


class GeneralCollationHttpTests(support.Base):
    def test_preview_and_start_go_through_the_api(self):
        ctl = self.controller(Team())
        rid, key = GeneralCollationTests.team(self, ctl)
        token = "T" * 43
        httpd = server._Server(("127.0.0.1", 0), server.BaseHTTPRequestHandler)
        port = httpd.server_address[1]
        httpd.RequestHandlerClass = server.make_handler(ctl, token, port)
        threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)

        def post(path, body):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            try:
                conn.request("POST", path, json.dumps(body).encode(),
                             {"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
                reply = conn.getresponse()
                return reply.status, json.loads(reply.read())
            finally:
                conn.close()

        path = f"/api/runs/{rid}/collate"
        status, m = post(path + "/preview", {"choices": {"claude": key}})
        self.assertEqual(status, 200, m)
        self.assertEqual(post(path, {})[0], 400)                                        # 수정 판이 있는데 고르지 않음
        self.assertEqual(post(path, {"choices": {"claude": key}, "collation_id": m["collation_id"],
                                     "confirmation": "0" * 64})[0], 400)
        status, body = post(path, {"choices": {"claude": key}, "collation_id": m["collation_id"],
                                   "confirmation": m["confirmation"]})
        self.assertEqual((status, body), (200, {"collation_id": m["collation_id"]}))
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
