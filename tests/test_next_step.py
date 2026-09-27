"""카드 #133: 다음 단계 제안(역할판 D 둘째 조각). 합성 실행기와 모의 CLI만 — 실제 모델을 부르지 않는다.

완료 조건을 하나씩 고정한다: 봉인 중에는 부를 수 없고 공개된 답만 이름표로 들어감, 제안은 실행을 시작하지 않고 내가
확인해 시작한 실행 하나에만 묶임, 실행당 2번·한 번에 하나·예약·종료 미확인·재시작이 다듬기와 같은 관문, 작업 호출 수.
"""
from dataclasses import replace
import json
import sqlite3
import unittest

from app import controller as c, next_step, server
from app.store import SCHEMA_VERSION, Store, events
from core import adapters, contract, runner
import test_app_controller as support

ROSTER = server.PARTICIPANTS


def board(*isolated, supervisor=("claude",), mode="original"):
    return {"supervisor": list(supervisor), "orchestrator": [], "isolated": list(isolated), "general": [],
            "input_mode": mode}


class Proposer(support.SyntheticExecutor):
    """제안 지시문에는 JSON으로 답하고, 참여자 질문에는 기존 합성 답을 준다. 받은 입력 전문을 기록한다.
    outcomes의 "supervisor": ok(again) · stop · fail · unknown · badjson."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prompts = {}

    def plan(self, spec, prompt, work_dir, *, inputs=()):
        self.prompts.setdefault(spec.pid, []).append(prompt)
        return super().plan(spec, prompt, work_dir)

    def execute(self, spec, prompt, work_dir, timeout, *, cancel=None):
        if not prompt.startswith(next_step.MARKER):
            return super().execute(spec, prompt, work_dir, timeout, cancel=cancel)
        self.started.append(spec.pid)
        if spec.pid in self.gates:
            self.gates[spec.pid].wait(10)
        kind = self.outcomes.get(spec.pid, "ok")
        reply = {"next": "stop", "reason": "두 답이 같다", "question": None, "open_points": []} if kind == "stop" else \
            {"next": "again", "reason": "조건이 갈린다", "question": "예산을 넣어 다시 묻기", "open_points": ["비용"]}
        text = "제안 대신 답을 씀" if kind == "badjson" else json.dumps(reply, ensure_ascii=False)
        result = runner.RunResult(("synthetic",), runner.EXITED, 1 if kind == "fail" else 0,
                                  support.claude_stdout(text, error=kind == "fail"), "", False, False, 5, 0, True,
                                  containment=runner.PROCESS_GROUP if kind == "unknown" else runner.JOB_OBJECT,
                                  input_delivery=runner.INPUT_COMPLETE)
        return result, adapters.interpret("claude-code", result, requested_model="m")


class RealLike(Proposer):
    kind = contract.REAL

    def plan(self, spec, prompt, work_dir, *, inputs=()):
        return replace(super().plan(spec, prompt, work_dir, inputs=inputs), kind=contract.REAL)


class NextStepTests(support.Base):
    def revealed(self, ctl, **kwargs):
        rid = ctl.create_run("원래 질문", [ROSTER["claude"], ROSTER["codex"]], min_independent=2,
                             role_board=board("claude", "codex"), roster=ROSTER, task_title="제안 작업", **kwargs)
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(self.run_view(ctl, rid)["gate"]["revealed"])
        return rid

    def proposals(self, ctl, rid):
        return self.run_view(ctl, rid)["proposals"]

    def test_the_supervisor_sees_only_revealed_answers_under_labels_and_starts_nothing(self):
        ex = Proposer(hold=("claude",))
        ctl = self.controller(ex)
        rid = ctl.create_run("원래 질문", [ROSTER["claude"], ROSTER["codex"]], min_independent=2,
                             role_board=board("claude", "codex"), roster=ROSTER)
        with self.assertRaises(c.ControllerError):   # 봉인 중에는 부르지 않는다
            ctl.propose_next(rid)
        ex.release("claude")
        self.assertTrue(ctl.wait_idle())
        pid = ctl.propose_next(rid)
        self.assertTrue(ctl.wait_idle())
        text = ex.prompts["supervisor"][0]
        self.assertTrue(text.startswith(next_step.MARKER))
        for piece in ("원래 질문", "claude의 답", "codex의 답", "<<<D1 시작>>>", "<<<D2 시작>>>"):
            self.assertIn(piece, text)
        for hidden in ("anthropic", "openai", "Claude Code", "Codex"):   # 이름표 뒤의 회사·카드를 알리지 않는다
            self.assertNotIn(hidden, text)
        item = self.proposals(ctl, rid)[0]
        self.assertEqual(item["proposal_id"], pid)
        self.assertEqual(item["reply"]["next"], "again")
        self.assertEqual(sorted(item["labels"].values()), ["claude", "codex"])
        self.assertEqual(len(ctl.view()["runs"]), 1)                           # 제안은 실행을 시작하지 않는다
        self.assertEqual(ctl.view()["tasks"][0]["calls_used"], 3)              # 팀원 2 + 제안 1
        self.assertIn("proposal_completed", [e["kind"] for e in events(self.store, rid)])

    def test_an_approved_proposal_becomes_one_run_in_the_same_task_only(self):
        ctl = self.controller(Proposer())
        rid = self.revealed(ctl)
        pid = ctl.propose_next(rid)
        self.assertTrue(ctl.wait_idle())
        task = self.run_view(ctl, rid)["task_id"]
        common = dict(min_independent=2, role_board=board("claude", "codex"), roster=ROSTER)
        members = [ROSTER["claude"], ROSTER["codex"]]
        for name, question, extra in (("edited question", "내가 고친 질문", dict(task_id=task)),
                                      ("other task", "예산을 넣어 다시 묻기", dict(task_title="다른 작업")),
                                      ("refine mode", "예산을 넣어 다시 묻기",
                                       dict(task_id=task, role_board=board("claude", "codex", mode="refine")))):
            with self.subTest(name), self.assertRaises(c.ControllerError):
                ctl.create_run(question, members, proposal={"id": pid}, **{**common, **extra})
        self.assertEqual(len(ctl.view()["runs"]), 1)
        new = ctl.create_run("예산을 넣어 다시 묻기", members, proposal={"id": pid}, task_id=task, **common)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.run_view(ctl, new)["proposal"], {"proposal_id": pid, "source_run": rid})
        self.assertEqual(self.proposals(ctl, rid)[0]["used_by"], new)
        with self.assertRaises(c.ControllerError):   # 같은 제안으로 두 번째 실행을 만들지 않는다
            ctl.create_run("예산을 넣어 다시 묻기", members, proposal={"id": pid}, task_id=task, **common)
        self.assertEqual(len(ctl.view()["runs"]), 2)

    def test_stop_and_failed_proposals_cannot_start_a_run(self):
        ex = Proposer(outcomes={"supervisor": "stop"})
        ctl = self.controller(ex)
        rid = self.revealed(ctl)
        stop = ctl.propose_next(rid)
        self.assertTrue(ctl.wait_idle())
        ex.outcomes = {"supervisor": "badjson"}
        bad = ctl.propose_next(rid)
        self.assertTrue(ctl.wait_idle())
        items = {item["proposal_id"]: item for item in self.proposals(ctl, rid)}
        self.assertEqual(items[stop]["reply"]["next"], "stop")
        self.assertIsNone(items[stop]["reply"]["question"])
        self.assertEqual((items[bad]["state"], items[bad]["status"]), (c.REJECTED, "format_error"))
        self.assertEqual(items[bad]["raw"]["text"], "제안 대신 답을 씀")
        task = self.run_view(ctl, rid)["task_id"]
        for proposal in (stop, bad):
            with self.subTest(proposal=proposal), self.assertRaises(c.ControllerError):
                ctl.create_run("무엇이든", [ROSTER["codex"]], min_independent=1, role_board=board("codex"),
                               roster=ROSTER, task_id=task, proposal={"id": proposal})
        with self.assertRaises(c.ControllerError):   # 실행 하나에 2번까지
            ctl.propose_next(rid)

    def test_gates_one_call_at_a_time_unconfirmed_ending_and_review(self):
        ex = Proposer(hold=("supervisor",))
        ctl = self.controller(ex)
        rid = self.revealed(ctl)
        pid = ctl.propose_next(rid)
        self.assertTrue(support.wait_for(lambda: self.proposals(ctl, rid)[0]["state"] == c.RUNNING))
        with self.assertRaises(c.ControllerError):   # 한 번에 하나(다듬기 포함)
            ctl.propose_next(rid)
        with self.assertRaises(c.ControllerError):
            ctl.refine(ROSTER["claude"], "다른 원문")
        revision = self.run_view(ctl, rid)["result_revision"]
        with self.assertRaises(c.ControllerError):   # 제안이 도는 동안 판단 완료를 받지 않는다
            ctl.mark_reviewed(rid, revision)
        ex.outcomes = {"supervisor": "unknown"}
        ex.release("supervisor")
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.proposals(ctl, rid)[0]["state"], c.UNKNOWN)
        self.assertEqual(ctl.unsettled(), 1)
        with self.assertRaises(c.ControllerError):
            ctl.propose_next(rid)
        ctl.acknowledge_proposal_unknown(pid)
        self.assertEqual(self.proposals(ctl, rid)[0]["status"], "unknown_acknowledged")
        self.assertEqual(ctl.unsettled(), 0)
        self.assertEqual(ex.started.count("supervisor"), 1)                  # 자동으로 다시 부르지 않았다
        run = self.run_view(ctl, rid)
        ctl.mark_reviewed(rid, run["result_revision"], memo="제안 없이 끝")
        self.assertTrue(self.run_view(ctl, rid)["reviewed"])

    def test_the_task_shows_a_running_or_unconfirmed_proposal_even_after_review(self):
        # 판단 완료한 작업에 제안을 부르면 끝남으로 남지 않는다(Codex 교차검토, PR #134)
        ex = Proposer(hold=("supervisor",))
        ctl = self.controller(ex)
        rid = self.revealed(ctl)
        ctl.mark_reviewed(rid, self.run_view(ctl, rid)["result_revision"])
        self.assertEqual(ctl.view()["tasks"][0]["status"], "done")
        pid = ctl.propose_next(rid)
        self.assertTrue(support.wait_for(lambda: self.proposals(ctl, rid)[0]["state"] == c.RUNNING))
        self.assertEqual(ctl.view()["tasks"][0]["status"], "working")
        ex.outcomes = {"supervisor": "unknown"}
        ex.release("supervisor")
        self.assertTrue(ctl.wait_idle())
        task = ctl.view()["tasks"][0]
        self.assertEqual((task["status"], task["runs"][0]["action"]), ("problem", "종료·실패 확인"))
        ctl.acknowledge_proposal_unknown(pid)
        self.assertNotEqual(ctl.view()["tasks"][0]["status"], "problem")

    def test_a_supervisor_only_card_keeps_the_model_chosen_for_it(self):
        # 슈퍼바이저 칸에만 둔 카드의 모델이 역할판에 고정된다 — 제안도 그 모델로 부른다
        ex = Proposer()
        ctl = self.controller(ex)
        roster = server.chosen_models(ROSTER, server.MOCK_MODEL_CHOICES, {"claude": "mock-claude-large"})
        rid = ctl.create_run("q", [roster["codex"]], min_independent=1, role_board=board("codex"), roster=roster)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.run_view(ctl, rid)["role_config"]["supervisor"]["model"], "mock-claude-large")
        ctl.propose_next(rid)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.proposals(ctl, rid)[0]["supervisor"]["model"], "mock-claude-large")

    def test_a_new_proposal_result_makes_it_my_turn_again(self):
        ctl = self.controller(Proposer())
        rid = self.revealed(ctl)
        ctl.mark_reviewed(rid, self.run_view(ctl, rid)["result_revision"])
        self.assertEqual(ctl.view()["tasks"][0]["status"], "done")
        ctl.propose_next(rid)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(ctl.view()["tasks"][0]["status"], "my_turn")          # 새 결과(제안)가 오면 다시 내 차례

    def test_refused_without_a_supervisor_for_general_runs_and_while_a_run_drafts(self):
        ctl = self.controller(Proposer())
        rid = ctl.create_run("q", [ROSTER["codex"]], min_independent=1, role_board=board("codex", supervisor=()),
                             roster=ROSTER)
        self.assertTrue(ctl.wait_idle())
        with self.assertRaises(c.ControllerError):
            ctl.propose_next(rid)
        general = ctl.create_run("q", [ROSTER["codex"]], min_independent=1,
                                 role_board={"supervisor": [], "orchestrator": [], "isolated": [], "general": ["codex"],
                                             "input_mode": "original"},
                                 roster=ROSTER, assignments={"codex": {"task": "t", "sources": []}})
        self.assertTrue(ctl.wait_idle())
        with self.assertRaises(c.ControllerError):
            ctl.propose_next(general)
        self.assertEqual(self.store.row("SELECT COUNT(*) AS n FROM proposals")["n"], 0)

    def test_real_proposals_reserve_under_the_same_cap(self):
        ctl = self.controller(RealLike(), max_real_calls=3)
        rid = self.revealed(ctl)
        ctl.propose_next(rid)
        self.assertTrue(ctl.wait_idle())
        reserved = [e for e in events(self.store, rid) if e["kind"] == "live_call_reserved"]
        self.assertEqual(sorted(e.get("purpose", "draft") for e in reserved), ["draft", "draft", "next_step"])
        with self.assertRaises(c.ControllerError):   # 상한 소진
            ctl.propose_next(rid)
        self.assertEqual(ctl.call_budget(), {"used": 3, "cap": 3})
        self.assertEqual(ctl.view()["tasks"][0]["calls_used"], 3)

    def test_restart_turns_a_running_proposal_into_unconfirmed_termination(self):
        ctl = self.controller(Proposer())
        rid = self.revealed(ctl)
        ctl.propose_next(rid)
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(ctl.shutdown())
        with self.store.tx() as tx:
            tx.execute("UPDATE proposals SET state = 'running', result = NULL WHERE run_id = ?", rid)
        self.store.close()
        reopened = Store(self.tmp / "store" / "journal.db")
        self.addCleanup(reopened.close)
        ex = Proposer()
        again = c.Controller(reopened, ex, work_root=str(self.tmp / "work"))
        self.addCleanup(again.shutdown)
        item = next(r for r in again.view()["runs"] if r["run_id"] == rid)["proposals"][0]
        self.assertEqual((item["state"], item["status"]), (c.UNKNOWN, "controller_restarted"))
        self.assertEqual(ex.started, [])

    def test_a_schema_ten_ledger_is_backed_up_before_eleven(self):
        ctl = self.controller(Proposer(), max_parallel=0)
        ctl.create_run("이전 실행", [support.cli("a")], min_independent=1)
        self.assertTrue(ctl.shutdown())
        self.store.close()
        path = self.tmp / "store" / "journal.db"
        db = sqlite3.connect(path)
        db.executescript("DROP TABLE proposals; PRAGMA user_version = 10;")
        db.close()
        reopened = Store(path)
        self.addCleanup(reopened.close)
        self.assertEqual(len(list(path.parent.glob("journal.db.v10-*.bak"))), 1)
        self.assertEqual(reopened.row("PRAGMA user_version")[0], SCHEMA_VERSION)


class NextStepCheckTests(unittest.TestCase):
    def test_again_needs_a_question_stop_has_none_and_unknown_fields_fail(self):
        ok = next_step.check('{"next": "again", "reason": " r ", "question": " q ", "open_points": null}')
        self.assertEqual(ok, {"next": "again", "reason": "r", "question": "q", "open_points": []})
        self.assertIsNone(next_step.check('{"next": "stop", "reason": "r", "question": ""}')["question"])
        for bad in ('{"next": "again", "reason": "r"}', '{"next": "stop", "reason": "r", "question": "q"}',
                    '{"next": "cross_check", "reason": "r"}', '{"next": "stop", "reason": ""}',
                    '{"next": "stop", "reason": "r", "answer": "몰래 답"}',
                    '{"next": "stop", "reason": "r", "open_points": false}', "JSON 아님"):
            with self.subTest(bad=bad[:30]), self.assertRaises(next_step.NextStepError):
                next_step.check(bad)


@unittest.skipUnless(support.real_path_available(), "Windows job object나 신뢰한 bubblewrap이 있는 Linux에서만")
class MockNextStepTests(support.Base):
    def test_the_mock_cli_answers_a_proposal_through_the_real_path(self):
        ctl = self.controller(c.MockExecutor(never=(str((self.tmp / "store").resolve()),)), timeout=30)
        rid = ctl.create_run("모의 질문", [ROSTER["claude"], ROSTER["codex"]], min_independent=2,
                             role_board=board("claude", "codex"), roster=ROSTER)
        self.assertTrue(ctl.wait_idle(30))
        ctl.propose_next(rid)
        self.assertTrue(ctl.wait_idle(30))
        item = self.run_view(ctl, rid)["proposals"][0]
        self.assertEqual(item["state"], c.ACCEPTED, item)
        self.assertTrue(item["reply"]["question"].startswith("[모의 제안]"))
