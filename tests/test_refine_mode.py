"""카드 #130: 다듬기 모드(역할판 D 첫 조각). 합성 실행기와 모의 CLI만 — 실제 모델을 부르지 않는다.

완료 조건을 하나씩 고정한다: 승인한 문장만 격리 팀원에게 감, 원문·차례별 입출력·승인본의 따로 기록, 같은 다듬기로 실행
두 번 만들지 않음, 차례 상한과 예약·상한·종료 미확인·재시작 복구가 같은 관문을 지남, 원문과 보낸 질문을 나란히 보임.
"""
from dataclasses import replace
import http.client
import json
import sqlite3
import threading
import unittest

from app import controller as c, refine, server
from app.store import SCHEMA_VERSION, Store, events
from core import adapters, contract, runner
import test_app_controller as support

ROSTER = server.PARTICIPANTS
ORIGINAL = "사내 검색을 바꿀까? 비용이 걱정된다"


def board(*isolated, supervisor=("claude",), mode="refine", general=()):
    return {"supervisor": list(supervisor), "orchestrator": [], "isolated": list(isolated), "general": list(general),
            "input_mode": mode}


class Refiner(support.SyntheticExecutor):
    """다듬기 지시문에는 JSON으로 답하고, 참여자 질문에는 기존 합성 답을 준다. 받은 입력 전문을 기록한다.

    outcomes의 "supervisor"로 차례의 결과를 바꾼다: ok · fail · unknown · badjson(형식 실패)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prompts = {}

    def plan(self, spec, prompt, work_dir, *, inputs=()):
        self.prompts.setdefault(spec.pid, []).append(prompt)
        return super().plan(spec, prompt, work_dir)

    def execute(self, spec, prompt, work_dir, timeout, *, cancel=None):
        if not prompt.startswith(refine.MARKER):
            return super().execute(spec, prompt, work_dir, timeout, cancel=cancel)
        self.started.append(spec.pid)
        if spec.pid in self.gates:
            self.gates[spec.pid].wait(10)
        kind = self.outcomes.get(spec.pid, "ok")
        turn = prompt.count("의 다듬은 질문:") + 1
        text = "다듬지 않고 답만 씀" if kind == "badjson" else json.dumps(
            {"refined": f"다듬은 질문 {turn}", "changes": [f"바뀐 점 {turn}"], "ask": f"물음 {turn}"}, ensure_ascii=False)
        result = runner.RunResult(("synthetic",), runner.EXITED, 1 if kind == "fail" else 0,
                                  support.claude_stdout(text, error=kind == "fail"), "", False, False, 5, 0, True,
                                  containment=runner.PROCESS_GROUP if kind == "unknown" else runner.JOB_OBJECT,
                                  input_delivery=runner.INPUT_COMPLETE)
        return result, adapters.interpret("claude-code", result, requested_model="m")


class RealLike(Refiner):
    kind = contract.REAL

    def plan(self, spec, prompt, work_dir, *, inputs=()):
        return replace(super().plan(spec, prompt, work_dir, inputs=inputs), kind=contract.REAL)


class RefineTests(support.Base):
    def turns(self, ctl, refine_id):
        return next(item for item in ctl.view()["refinements"] if item["refine_id"] == refine_id)["turns"]

    def start(self, ctl, rid, turn, question=None, layout=None, **kwargs):
        return ctl.create_run(question if question is not None else f"다듬은 질문 {turn}", [ROSTER["codex"]],
                              min_independent=1, role_board=layout or board("codex"), roster=ROSTER,
                              refinement={"id": rid, "turn": turn}, **kwargs)

    def test_only_the_approved_sentence_reaches_members_and_every_turn_is_recorded(self):
        ex = Refiner()
        ctl = self.controller(ex)
        rid = ctl.refine(ROSTER["claude"], ORIGINAL)
        self.assertTrue(ctl.wait_idle())
        ctl.refine(ROSTER["claude"], refine_id=rid, note="기한은 3개월")
        self.assertTrue(ctl.wait_idle())
        turns = self.turns(ctl, rid)
        self.assertEqual([t["state"] for t in turns], [c.ACCEPTED, c.ACCEPTED])
        self.assertEqual(turns[0]["reply"], {"refined": "다듬은 질문 1", "changes": ["바뀐 점 1"], "ask": "물음 1"})
        self.assertIn(ORIGINAL, turns[1]["prompt"])                        # 슈퍼바이저는 원문과 대화를 받는다
        self.assertIn("기한은 3개월", turns[1]["prompt"])
        self.assertIn("다듬은 질문 1", turns[1]["prompt"])
        run_id = self.start(ctl, rid, 2, task_title="다듬은 작업")
        self.assertTrue(ctl.wait_idle())
        member = ex.prompts["codex"][0]
        self.assertIn("다듬은 질문 2", member)
        for leaked in (ORIGINAL, "기한은 3개월", "다듬은 질문 1", "물음", refine.MARKER):   # 대화·원문은 가지 않는다
            self.assertNotIn(leaked, member)
        run = self.run_view(ctl, run_id)
        self.assertEqual(run["question"], "다듬은 질문 2")
        self.assertEqual(run["refinement"]["original"], ORIGINAL)
        self.assertEqual(run["refinement"]["approved_turn"], 2)
        self.assertEqual(len(run["refinement"]["turns"]), 2)
        self.assertEqual(ctl.view()["refinements"], [])                   # 실행에 쓴 다듬기는 열린 목록에서 빠진다
        self.assertEqual(ctl.view()["tasks"][0]["calls_used"], 3)          # 다듬기 2차례 + 팀원 1명
        kinds = [e["kind"] for e in events(self.store, rid)]
        self.assertEqual(kinds.count("refine_turn_completed"), 2)
        self.assertIn("refine_approved", kinds)
        created = next(e for e in events(self.store, run_id) if e["kind"] == "run_created")
        self.assertEqual(created["refinement"]["turn"], 2)
        with self.assertRaises(c.ControllerError):   # 같은 다듬기로 두 번째 실행을 만들지 않는다
            self.start(ctl, rid, 2)
        with self.assertRaises(c.ControllerError):   # 실행에 쓴 다듬기는 더 다듬지 않는다
            ctl.refine(ROSTER["claude"], refine_id=rid, note="더")
        self.assertEqual(len(ctl.view()["runs"]), 1)
        self.assertEqual(ex.started.count("supervisor"), 2)

    def test_turns_stop_at_the_cap(self):
        ctl = self.controller(Refiner())
        rid = ctl.refine(ROSTER["claude"], ORIGINAL)
        for note in ("하나", "둘"):
            self.assertTrue(ctl.wait_idle())
            ctl.refine(ROSTER["claude"], refine_id=rid, note=note)
        self.assertTrue(ctl.wait_idle())
        with self.assertRaises(c.ControllerError):
            ctl.refine(ROSTER["claude"], refine_id=rid, note="넷째")
        self.assertEqual(len(self.turns(ctl, rid)), refine.MAX_TURNS)

    def test_approval_must_match_the_sentence_the_supervisor_and_a_passing_turn(self):
        ex = Refiner(outcomes={"supervisor": "badjson"})
        ctl = self.controller(ex)
        rid = ctl.refine(ROSTER["claude"], ORIGINAL)
        self.assertTrue(ctl.wait_idle())
        bad = self.turns(ctl, rid)[0]
        self.assertEqual((bad["state"], bad["status"]), (c.REJECTED, "format_error"))
        self.assertEqual(bad["raw"]["text"], "다듬지 않고 답만 씀")          # 형식 실패는 원문을 이유와 함께 남긴다
        ex.outcomes = {}
        ctl.refine(ROSTER["claude"], refine_id=rid, note="JSON으로")
        self.assertTrue(ctl.wait_idle())
        cases = [
            ("failed turn", dict(turn=1, question="다듬지 않고 답만 씀")),
            ("different sentence", dict(turn=2, question="내가 고친 문장")),
            ("other supervisor", dict(turn=2, layout=board("claude", supervisor=("codex",)))),
            ("other model", dict(turn=2, layout=board("codex"), models=True)),
        ]
        for name, options in cases:
            with self.subTest(name), self.assertRaises(c.ControllerError):
                layout = options.get("layout") or board("codex")
                roster = ({**ROSTER, "claude": replace(ROSTER["claude"], model="mock-claude-large")}
                          if options.get("models") else ROSTER)
                ctl.create_run(options.get("question", "다듬은 질문 2"),
                               [ROSTER[p] for p in layout["isolated"]], min_independent=1, role_board=layout,
                               roster=roster, refinement={"id": rid, "turn": options["turn"]})
        with self.assertRaises(c.ControllerError):   # 다듬기 모드인데 승인한 차례가 없다
            ctl.create_run("다듬은 질문 2", [ROSTER["codex"]], min_independent=1, role_board=board("codex"),
                           roster=ROSTER)
        with self.assertRaises(c.ControllerError):   # 원문 모드에는 다듬기 차례를 주지 않는다
            ctl.create_run("다듬은 질문 2", [ROSTER["codex"]], min_independent=1,
                           role_board=board("codex", supervisor=(), mode="original"), roster=ROSTER,
                           refinement={"id": rid, "turn": 2})
        self.assertEqual(ctl.view()["runs"], [])
        self.assertIsNone(self.store.row("SELECT run_id FROM refinements")["run_id"])

    def test_an_open_or_unconfirmed_turn_blocks_the_next_call_until_the_person_settles_it(self):
        ex = Refiner(hold=("supervisor",))
        ctl = self.controller(ex)
        rid = ctl.refine(ROSTER["claude"], ORIGINAL)
        self.assertTrue(support.wait_for(lambda: self.turns(ctl, rid)[0]["state"] == c.RUNNING))
        with self.assertRaises(c.ControllerError):
            ctl.refine(ROSTER["claude"], refine_id=rid, note="서두름")
        with self.assertRaises(c.ControllerError):   # 진행 중인 차례가 있으면 역할판 실행도 시작하지 않는다
            ctl.create_run("q", [ROSTER["codex"]], min_independent=1,
                           role_board=board("codex", supervisor=(), mode="original"), roster=ROSTER)
        ex.outcomes = {"supervisor": "unknown"}
        ex.release("supervisor")
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.turns(ctl, rid)[0]["state"], c.UNKNOWN)
        self.assertEqual(ctl.unsettled(), 1)
        with self.assertRaises(c.ControllerError):
            ctl.refine(ROSTER["claude"], refine_id=rid, note="다시")
        with self.assertRaises(c.ControllerError):
            ctl.acknowledge_refine_unknown(rid, 2)
        ctl.acknowledge_refine_unknown(rid, 1)
        self.assertEqual(self.turns(ctl, rid)[0]["status"], "unknown_acknowledged")
        self.assertEqual(ctl.unsettled(), 0)
        self.assertEqual(ex.started.count("supervisor"), 1)                # 자동으로 다시 부르지 않았다
        ex.outcomes = {}
        ctl.refine(ROSTER["claude"], refine_id=rid, note="다시")
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.turns(ctl, rid)[1]["state"], c.ACCEPTED)

    def test_only_one_refine_turn_runs_at_a_time_even_across_refinements(self):
        # 버튼을 두 번 누르거나 창 두 개에서 불러도 두 번째 호출을 시작하지 않는다(Codex 교차검토, PR #131)
        ex = Refiner(hold=("supervisor",))
        ctl = self.controller(ex)
        rid = ctl.refine(ROSTER["claude"], ORIGINAL)
        self.assertTrue(support.wait_for(lambda: self.turns(ctl, rid)[0]["state"] == c.RUNNING))
        with self.assertRaises(c.ControllerError):
            ctl.refine(ROSTER["claude"], ORIGINAL)
        ex.release("supervisor")
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.store.row("SELECT COUNT(*) AS n FROM refinements")["n"], 1)
        self.assertEqual(ex.started.count("supervisor"), 1)

    def test_real_turns_are_reserved_under_the_same_cap_and_refused_when_it_is_used_up(self):
        ex = RealLike()
        ctl = self.controller(ex, max_real_calls=1)
        rid = ctl.refine(ROSTER["claude"], ORIGINAL)
        self.assertTrue(ctl.wait_idle())
        reserved = [e for e in events(self.store, rid) if e["kind"] == "live_call_reserved"]
        self.assertEqual([(e["purpose"], e["adapter_id"]) for e in reserved], [("refine", "claude-code")])
        with self.assertRaises(c.ControllerError):
            ctl.refine(ROSTER["claude"], refine_id=rid, note="한 번 더")
        self.assertEqual(len(self.turns(ctl, rid)), 1)
        self.assertEqual(ctl.call_budget(), {"used": 1, "cap": 1})

    def test_refining_waits_while_a_run_is_drafting(self):
        ctl = self.controller(Refiner(), max_parallel=0)
        ctl.create_run("q", [ROSTER["codex"]], min_independent=1,
                       role_board=board("codex", supervisor=(), mode="original"), roster=ROSTER)
        ctl.max_parallel = 2
        with self.assertRaises(c.ControllerError):
            ctl.refine(ROSTER["claude"], ORIGINAL)
        self.assertEqual(self.store.row("SELECT COUNT(*) AS n FROM refinements")["n"], 0)

    def test_restart_turns_a_running_turn_into_unconfirmed_termination(self):
        ctl = self.controller(Refiner())
        rid = ctl.refine(ROSTER["claude"], ORIGINAL)
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(ctl.shutdown())
        with self.store.tx() as tx:
            tx.execute("UPDATE refine_turns SET state = 'running', result = NULL WHERE refine_id = ?", rid)
        self.store.close()
        reopened = Store(self.tmp / "store" / "journal.db")
        self.addCleanup(reopened.close)
        ex = Refiner()
        again = c.Controller(reopened, ex, work_root=str(self.tmp / "work"))
        self.addCleanup(again.shutdown)
        turn = next(item for item in again.view()["refinements"] if item["refine_id"] == rid)["turns"][0]
        self.assertEqual((turn["state"], turn["status"]), (c.UNKNOWN, "controller_restarted"))
        self.assertEqual(ex.started, [])

    def test_board_rules_for_the_supervisor_slot(self):
        ctl = self.controller(Refiner(), max_parallel=0)
        cases = [("original app", board("codex", supervisor=("claude-app",))),
                 ("two cards", board("codex", supervisor=("claude", "codex"))),
                 ("refine without supervisor", board("codex", supervisor=())),
                 ("general work", board(general=("codex",)))]
        for name, layout in cases:
            members = layout["general"] or layout["isolated"]
            with self.subTest(name), self.assertRaises(c.ControllerError):
                ctl.create_run("q", [ROSTER[p] for p in members], min_independent=1, role_board=layout, roster=ROSTER,
                               assignments={"codex": {"task": "t", "sources": []}} if layout["general"] else None)
        for bad in (dict(original=""), dict(original="x" * (refine.MAX_ORIGINAL + 1)),
                    dict(original=ORIGINAL, note="첫 차례의 답")):
            with self.subTest(bad=str(bad)[:30]), self.assertRaises(c.ControllerError):
                ctl.refine(ROSTER["claude"], **bad)
        with self.assertRaises(c.ControllerError):
            ctl.refine(ROSTER["claude-app"], ORIGINAL)
        self.assertEqual(self.store.row("SELECT COUNT(*) AS n FROM refinements")["n"], 0)

    def test_a_schema_nine_ledger_is_backed_up_before_ten(self):
        ctl = self.controller(Refiner(), max_parallel=0)
        ctl.create_run("이전 실행", [support.cli("a")], min_independent=1)
        self.assertTrue(ctl.shutdown())
        self.store.close()
        path = self.tmp / "store" / "journal.db"
        db = sqlite3.connect(path)
        db.executescript("DROP TABLE refinements; DROP TABLE refine_turns; PRAGMA user_version = 9;")
        db.close()
        reopened = Store(path)
        self.addCleanup(reopened.close)
        self.assertEqual(len(list(path.parent.glob("journal.db.v9-*.bak"))), 1)
        self.assertEqual(reopened.row("PRAGMA user_version")[0], SCHEMA_VERSION)
        again = c.Controller(reopened, Refiner(), max_parallel=0)
        self.addCleanup(again.shutdown)
        self.assertEqual(again.view()["refinements"], [])


class RefineCheckTests(unittest.TestCase):
    def test_only_the_three_fields_with_bounded_lengths_pass(self):
        ok = refine.check('앞말 ```json\n{"refined": " 질문 ", "changes": [], "ask": ""}\n```')
        self.assertEqual(ok, {"refined": "질문", "changes": [], "ask": None})
        for bad in ("JSON 아님", '{"refined": ""}', '{"refined": "q", "answer": "몰래 답"}',
                    '{"refined": "q", "changes": "하나"}', '{"refined": "q", "changes": false}', '{"refined": "q", "refined": "r"}',
                    json.dumps({"refined": "x" * (refine.MAX_REFINED + 1)}),
                    json.dumps({"refined": "q", "changes": ["c"] * (refine.MAX_CHANGES + 1)})):
            with self.subTest(bad=bad[:30]), self.assertRaises(refine.RefineError):
                refine.check(bad)

    def test_the_prompt_carries_the_original_and_the_conversation_only(self):
        text = refine.prompt("원문", [("", {"refined": "d1", "changes": ["c1"], "ask": "a1"}), ("n2", None)], "n3")
        self.assertTrue(text.startswith(refine.MARKER))
        for piece in ("원문", "d1", "c1", "a1", "n2", "차례 2: 답을 받지 못했다", "n3", "질문에 답하지 않는다"):
            self.assertIn(piece, text)


@unittest.skipUnless(support.real_path_available(), "Windows job object나 신뢰한 bubblewrap이 있는 Linux에서만")
class MockRefineTests(support.Base):
    def test_the_mock_cli_answers_a_refine_turn_through_the_real_path(self):
        ctl = self.controller(c.MockExecutor(never=(str((self.tmp / "store").resolve()),)), timeout=30)
        rid = ctl.refine(ROSTER["claude"], ORIGINAL)
        self.assertTrue(ctl.wait_idle(30))
        turn = ctl.view()["refinements"][0]["turns"][0]
        self.assertEqual(turn["state"], c.ACCEPTED, turn)
        self.assertTrue(turn["reply"]["refined"].startswith("[모의 다듬기 1차례]"))
        self.assertEqual(rid, ctl.view()["refinements"][0]["refine_id"])


class RefineHttpTests(support.Base):
    def setUp(self):
        super().setUp()
        self.ctl = self.controller(Refiner())
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

    def test_refine_approve_preview_and_start_over_http(self):
        self.assertEqual(self.call("/api/refinements", {"original": ORIGINAL, "supervisor": "claude",
                                                        "model": "mock-claude-credits"})[0], 400)   # 막힌 모델
        status, made = self.call("/api/refinements", {"original": ORIGINAL, "supervisor": "claude", "model": "mock-claude"})
        self.assertEqual(status, 200, made)
        self.assertTrue(self.ctl.wait_idle())
        rid = made["refine_id"]
        self.assertEqual(self.call(f"/api/refinements/{rid}/turn", {"supervisor": "claude", "model": "mock-claude",
                                                                    "note": "예산은 없음"})[0], 200)
        self.assertTrue(self.ctl.wait_idle())
        body = {"question": "다듬은 질문 2", "participants": [{"pid": "codex"}], "role_board": board("codex"),
                "models": {"claude": "mock-claude", "codex": "mock-codex"}, "min_independent": 1,
                "task_title": "다듬기", "refinement": {"id": rid, "turn": 2}}
        status, preview = self.call("/api/runs/preview", body)
        self.assertEqual(status, 200, preview)
        self.assertEqual(preview["refinement"]["original"], ORIGINAL)
        self.assertNotIn(ORIGINAL, preview["prompt"])
        body.update(run_id=preview["run_id"], confirmation=preview["confirmation"])
        self.assertEqual(self.call("/api/runs", body)[0], 200)
        self.assertEqual(self.call("/api/runs", {**body, "run_id": None, "confirmation": None})[0], 400)
        state = self.call("/api/state")[1]
        self.assertEqual(len(state["runs"]), 1)
        self.assertEqual(state["runs"][0]["refinement"]["approved_turn"], 2)
        self.assertEqual(self.call(f"/api/refinements/{rid}/acknowledge", {"turn": 1})[0], 400)
