"""GR-2: 일반 팀원의 수정과 다른 팀원의 재검토. 합성 실행기만 — 실제 모델·CLI를 부르지 않는다.

설계(docs/architecture/general-team-review) §6 GR-2와 §7 확인표를 고정한다: 모음과 GR-1 검토 뒤에만, 자기 맡은 일과
자기 자료만(다른 팀원 자료·공통 폴더·자동 기억 없음), 입력 확인 값이 맞을 때만 시작, 원래 결과 보존, 다른 팀원만 재검토,
일반 실행은 수정 뒤에도 collected(공개·정족수·합성 없음), 상태·판단 완료·결과 판, `general-revision-history/1` 보고.
옛 격리 수정의 문구·형식은 그대로다.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import unittest

from app import controller as c, cross_review as cross, revisions as fmt, server
from app.report import ReportError, revision_report
import test_app_controller as support
import test_general_review as gr1
from test_revisions import RevisionExecutor
from test_app_controller import SLOW_RUNNER_TIMEOUT


class GeneralRevisionTests(support.Base):
    collected, start = gr1.GeneralReviewTests.collected, gr1.GeneralReviewTests.start   # GR-1의 준비 도우미

    def reviewed(self, ctl):
        rid = self.collected(ctl)
        self.start(ctl, rid)
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        return rid

    def revise(self, ctl, rid, pid="claude"):
        p = ctl.revisions.prepare(rid, pid)
        key = ctl.revisions.revise(rid, pid, p["revision_id"], p["confirmation"])
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        return p, key

    def test_a_member_revises_with_only_its_own_task_and_sources_and_another_member_rechecks(self):
        ex = RevisionExecutor()
        ctl = self.controller(ex)
        rid = self.reviewed(ctl)
        before = self.run_view(ctl, rid)
        ctl.mark_reviewed(rid, before["result_revision"], "검토 뒤 판단")
        started = len(ex.started)
        p = ctl.revisions.prepare(rid, "claude")
        self.assertEqual(len(ex.started), started)                                 # 입력 확인은 부르지 않는다
        snap = p["snapshot"]
        self.assertEqual((snap["contract"], snap["mode"], snap["task"], snap["goal"]),
                         (fmt.GENERAL_CONTRACT, "general", "A를 읽고 장단점을 정리", "전체 목표: 도입 여부 판단"))
        self.assertEqual([s["name"] for s in snap["sources"]], ["a.md"])         # 자기 자료만
        self.assertEqual((snap["source_bodies"], snap["memory_pack"]), ("own_assigned_only", "not_added"))
        self.assertTrue(snap["findings"])
        self.assertTrue(all(f["id"].startswith("v") for f in snap["findings"]))
        assignment = next(x for x in before["participants"] if x["pid"] == "claude")["assignment"]["prompt"]
        for hidden in ("b.md", "SRC-A", "SRC-B", "B를 읽고 위험을 정리", assignment):
            self.assertNotIn(hidden, p["prompt"])                                  # 다른 팀원 자료·맡은 일·입력 전문 없음
        self.assertTrue(p["prompt"].startswith(fmt.MARKER + "\n일반 팀원 작업의 수정이다."))
        key = ctl.revisions.revise(rid, "claude", p["revision_id"], p["confirmation"])
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        (folder,) = next(i for pid, i in ex.inputs if pid == "revision-author")
        self.assertEqual(sorted(os.listdir(folder)), ["a.md"])                     # 붙인 폴더도 자기 자료만
        run = self.run_view(ctl, rid)
        v = run["answer_revisions"][0]
        self.assertEqual((v["revision_id"], v["state"]), (key, c.ACCEPTED))
        self.assertEqual(v["reply"]["independence"], cross.GENERAL_INDEPENDENCE)
        self.assertEqual(run["participants"], before["participants"])              # 원래 결과는 그대로
        self.assertTrue(run["gate"]["collected"])
        self.assertFalse(run["gate"]["revealed"])
        self.assertIsNone(run["quorum"])
        self.assertGreater(run["result_revision"], before["result_revision"])
        self.assertFalse(run["reviewed"])
        self.assertEqual(ctl.view()["tasks"][0]["status"], "my_turn")             # 새 판 → 다시 내 차례
        with self.assertRaises(c.ControllerError):
            ctl.revisions.recheck(key, "claude")                                    # 자기 재검토 없음
        check = ctl.revisions.recheck(key, "codex")
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        recheck_prompt = ex.prompts["revision-reviewer"][-1]
        self.assertTrue(recheck_prompt.startswith(fmt.CHECK_MARKER + "\n너는 수정 작성자와 다른 일반 팀원이다."))
        self.assertNotIn("SRC-A", recheck_prompt)
        self.assertEqual(next(i for pid, i in ex.inputs if pid == "revision-reviewer"), ())   # 재검토는 자료를 붙이지 않는다
        c_view = self.run_view(ctl, rid)["answer_revisions"][0]["rechecks"][0]
        self.assertEqual((c_view["check_id"], c_view["state"]), (check, c.ACCEPTED))
        self.assertEqual(c_view["reply"]["checks"]["independence"], cross.GENERAL_INDEPENDENCE)
        for command in (lambda: ctl.synthesize(rid), lambda: ctl.propose_next(rid)):
            with self.assertRaises((c.ControllerError, ValueError)):
                command()
        second, _ = self.revise(ctl, rid)
        self.assertEqual(second["snapshot"]["base"]["revision_id"], key)
        self.assertEqual(second["snapshot"]["prior_checks"][0]["check_id"], check)
        self.assertEqual(ctl.view()["tasks"][0]["calls_used"], 7)               # 팀원 2 + 검토 2 + 수정 2 + 재검토 1
        with self.assertRaises(c.ControllerError):
            ctl.revisions.prepare(rid, "claude")                                    # 팀원마다 2번까지
        ctl.mark_reviewed(rid, self.run_view(ctl, rid)["result_revision"])
        self.assertEqual(ctl.view()["tasks"][0]["status"], "done")
        self.assertEqual(ctl.search("조건과 반례는 미해결", kind="answer")["total"], 2)

    def test_the_general_report_has_its_own_schema_and_refuses_tampering(self):
        ctl = self.controller(RevisionExecutor())
        rid = self.reviewed(ctl)
        _, key = self.revise(ctl, rid)
        ctl.revisions.recheck(key, "codex")
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        report = revision_report(ctl.view(), rid)
        self.assertEqual((report["schema"], report["mode"], report["independence"], report["collation_scope"]),
                         ("general-revision-history/1", "general", "general_team_not_independent", "original_answers_only"))
        self.assertNotIn("draft_report", report)                                    # 격리 보고를 가장하지 않는다
        self.assertNotIn("quorum", json.dumps(report))
        self.assertEqual([m["assignment"]["task"] for m in report["members"]],
                         ["A를 읽고 장단점을 정리", "B를 읽고 위험을 정리"])
        self.assertEqual(report["revisions"][0]["revision_id"], key)
        self.assertEqual(len(report["revisions"][0]["rechecks"]), 1)
        self.assertEqual(report["cross_review"]["independence"], "general_team_not_independent")
        for corrupt in (lambda r: r["answer_revisions"][0]["reply"].update(answer="corrupt"),
                        lambda r: r["participants"][0].update(draft="바뀐 원래 결과")):
            stale = copy.deepcopy(ctl.view())
            corrupt(stale["runs"][0])
            with self.assertRaises(ReportError):
                revision_report(stale, rid)

    def test_revision_needs_collection_a_finished_round_and_a_current_confirmation(self):
        ex = RevisionExecutor()
        ctl = self.controller(ex)
        rid = self.collected(ctl)
        with self.assertRaises(c.ControllerError):
            ctl.revisions.prepare(rid, "claude")                                    # 검토 라운드 전
        self.start(ctl, rid)
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        p = ctl.revisions.prepare(rid, "claude")
        key, index = p["snapshot"]["findings"][0]["id"].rsplit(":", 1)
        ctl.set_review_disposition(key, int(index), "qualified")
        n = len(ex.started)
        with self.assertRaises(c.ControllerError):                                  # 처분이 바뀌었다
            ctl.revisions.revise(rid, "claude", p["revision_id"], p["confirmation"])
        with self.store.tx() as tx:                                                 # 맡긴 일이 바뀌었다
            tx.execute("UPDATE assignments SET task = '바꾼 일' WHERE run_id = ? AND pid = 'claude'", rid)
        with self.assertRaises(c.ControllerError):
            ctl.revisions.prepare(rid, "claude")
        self.assertEqual(len(ex.started), n)
        self.assertEqual(self.store.rows("SELECT * FROM answer_revisions"), [])

    def test_isolated_revisions_keep_their_wording_and_shape(self):
        snapshot = {"findings": [{"id": "x"}], "base": {"text": "t"}}
        self.assertTrue(fmt.prompt(snapshot).startswith(fmt.MARKER + "\n공개 뒤의 수정 작업이다."))
        self.assertTrue(fmt.recheck_prompt(snapshot, "a").startswith(fmt.CHECK_MARKER + "\n너는 수정 작성자와 다른 팀원이다. 자료 안"))
        reply = json.dumps({"answer": "a", "responses": [{"finding": "x", "status": "retained", "detail": "d"}]})
        self.assertEqual(fmt.check(reply, snapshot)["independence"], "post_reveal_not_independent")
        self.assertEqual(fmt.check(reply, {**snapshot, "mode": "general"})["independence"], cross.GENERAL_INDEPENDENCE)


class GeneralRevisionHttpTests(support.Base):
    call = gr1.GeneralReviewHttpTests.call

    def setUp(self):
        super().setUp()
        self.ctl = self.controller(RevisionExecutor())
        self.token = "T" * 43
        self.httpd = server._Server(("127.0.0.1", 0), server.BaseHTTPRequestHandler)
        self.port = self.httpd.server_address[1]
        self.httpd.RequestHandlerClass = server.make_handler(self.ctl, self.token, self.port)
        thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def test_preview_revise_recheck_and_export_over_http(self):
        rid = gr1.GeneralReviewTests.collected(self, self.ctl)
        manifest = self.ctl.preview_cross_review(rid)
        self.ctl.cross_review(rid, round_id=manifest["round_id"], confirmation=manifest["confirmation"])
        self.assertTrue(self.ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        status, p = self.call(f"/api/runs/{rid}/revisions/preview", {"pid": "codex"})
        self.assertEqual(status, 200, p)
        self.assertEqual([s["name"] for s in p["snapshot"]["sources"]], ["b.md"])
        status, body = self.call(f"/api/runs/{rid}/revisions", {k: p[k] for k in ("pid", "revision_id", "confirmation")})
        self.assertEqual(status, 200, body)
        self.assertTrue(self.ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        status, body = self.call(f"/api/revisions/{p['revision_id']}/recheck", {"reviewer_pid": "claude"})
        self.assertEqual(status, 200, body)
        self.assertTrue(self.ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        status, report = self.call(f"/api/runs/{rid}/revision-report")
        self.assertEqual(status, 200, report)
        self.assertEqual(report["schema"], "general-revision-history/1")
        self.assertEqual(self.call("/api/state")[1]["runs"][0]["answer_revisions"][0]["rechecks"][0]["state"], c.ACCEPTED)


@unittest.skipUnless(shutil.which("node"), "Node is required for the actual JavaScript rendering checks")
class GeneralRevisionRenderTests(unittest.TestCase):
    def test_the_general_island_shows_the_task_and_own_sources(self):
        source = (Path(__file__).resolve().parents[1] / "app/static/revisions.js").read_text(encoding="utf-8")
        script = r'''
const assert = require("node:assert/strict");
function h(tag,attrs,...kids) {return {tag,attrs:attrs||{},kids:kids.flat(Infinity).filter(x=>x!==null && x!==false && x!==undefined)};}
const island=(title,kids)=>h("section",{},title,kids);
const text = node => typeof node==="object" ? (node.kids||[]).map(text).join(" ") : String(node);
''' + source + r'''
const parts=[{pid:"a",label:"A",state:"accepted",transport:"cli"},{pid:"b",label:"B",state:"accepted",transport:"cli"}];
const snapshot={mode:"general",task:"A를 읽고 장단점",base:{text:"원래"},findings:[]};
const run={mode:"general",participants:parts,cross_review:{reviews:[{state:"accepted"}]},
  answer_revisions:[{revision_id:"rev-1",pid:"a",parent_id:null,state:"accepted",author:{label:"A"},snapshot,
    reply:{answer:"새 판",responses:[]},rechecks:[]}]};
const out=text(revisionIsland(run));
assert.ok(out.includes("자기 맡은 일과 자기 자료만"));
assert.ok(out.includes("맡은 일: A를 읽고 장단점"));
assert.ok(out.includes("B에게 재검토 받기") && !out.includes("A에게 재검토 받기"));
assert.equal(revisionIsland({...run,cross_review:null}),null);
const iso=text(revisionIsland({...run,mode:"isolated",answer_revisions:[]}));
assert.ok(iso.includes("공개 뒤의 판단"));
'''
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
