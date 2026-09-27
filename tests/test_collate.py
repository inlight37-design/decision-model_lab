"""카드 #137: 일반 작업의 결과 모으기(역할판 D 넷째 조각). 합성 실행기와 모의 CLI만 — 실제 모델을 부르지 않는다.

완료 조건을 하나씩 고정한다: 모두 끝난 일반 실행에만 부름, 오케스트레이터는 목표·맡긴 일·결과 원문만 받고 자료는 받지
않음, 인용은 받은 원문과 글자 그대로 대조하고 사실 검증은 하지 않음, 실패한 팀원은 결과 없음으로 들어감, 실행당 2번·
한 번에 하나·예약·종료 미확인·재시작, 새 모으기 결과는 다시 내 차례, 작업 호출 수.
"""
from dataclasses import replace
import json
import sqlite3
import unittest

from app import collate, controller as c, server
from app.store import SCHEMA_VERSION, Store, events
from core import adapters, contract, runner
import test_app_controller as support

ROSTER = server.PARTICIPANTS
SOURCES = [("a.md", "자료 A 원문 · 표식 SRC-A"), ("b.md", "자료 B 원문 · 표식 SRC-B")]
WORK = {"claude": {"task": "A를 읽고 장단점을 정리", "sources": ["a.md"]},
        "codex": {"task": "B를 읽고 위험을 정리", "sources": ["b.md"]}}
REPLY = {"claims": [{"statement": "둘 다 답했다", "quotes": [{"member": "T1", "text": "claude의 답"},
                                                           {"member": "T2", "text": "codex의 답"}]},
                    {"statement": "지어낸 주장", "quotes": [{"member": "T2", "text": "codex가 쓰지 않은 문장"}]},
                    {"statement": "인용 없는 주장", "quotes": []}],
         "overlaps": ["겹침"], "gaps": ["빈 곳"], "next": ["다음 할 일"]}


def board(*general, orchestrator=("claude",), isolated=()):
    return {"supervisor": [], "orchestrator": list(orchestrator), "isolated": list(isolated), "general": list(general),
            "input_mode": "original"}


class Collator(support.SyntheticExecutor):
    """모으기 지시문에는 REPLY로 답하고, 팀원 질문에는 기존 합성 답("<pid>의 답")을 준다. 받은 입력 전문을 기록한다.
    outcomes의 "supervisor": ok · fail · unknown · badjson."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prompts, self.inputs = {}, {}

    def plan(self, spec, prompt, work_dir, *, inputs=()):
        self.prompts.setdefault(spec.pid, []).append(prompt)
        self.inputs.setdefault(spec.pid, []).append(tuple(inputs))
        return super().plan(spec, prompt, work_dir)

    def execute(self, spec, prompt, work_dir, timeout, *, cancel=None):
        if not prompt.startswith(collate.MARKER):
            return super().execute(spec, prompt, work_dir, timeout, cancel=cancel)
        self.started.append(spec.pid)
        if spec.pid in self.gates:
            self.gates[spec.pid].wait(10)
        kind = self.outcomes.get(spec.pid, "ok")
        text = "모으기 대신 답을 씀" if kind == "badjson" else json.dumps(REPLY, ensure_ascii=False)
        result = runner.RunResult(("synthetic",), runner.EXITED, 1 if kind == "fail" else 0,
                                  support.claude_stdout(text, error=kind == "fail"), "", False, False, 5, 0, True,
                                  containment=runner.PROCESS_GROUP if kind == "unknown" else runner.JOB_OBJECT,
                                  input_delivery=runner.INPUT_COMPLETE)
        return result, adapters.interpret("claude-code", result, requested_model="m")


class RealLike(Collator):
    kind = contract.REAL

    def plan(self, spec, prompt, work_dir, *, inputs=()):
        return replace(super().plan(spec, prompt, work_dir, inputs=inputs), kind=contract.REAL)


class CollateTests(support.Base):
    def collected(self, ctl, pids=("claude", "codex"), **kwargs):
        rid = ctl.create_run("전체 목표: 도입 여부 판단", [ROSTER[p] for p in pids], min_independent=1,
                             role_board=board(*pids, **kwargs), roster=ROSTER, sources=SOURCES,
                             assignments={p: WORK[p] for p in pids}, task_title="모으기 작업")
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(self.run_view(ctl, rid)["gate"]["collected"])
        return rid

    def collations(self, ctl, rid):
        return self.run_view(ctl, rid)["collations"]

    def test_the_orchestrator_gets_tasks_and_results_only_and_quotes_are_matched_verbatim(self):
        ex = Collator()
        ctl = self.controller(ex)
        rid = self.collected(ctl)
        key = ctl.collate(rid)
        self.assertTrue(ctl.wait_idle())
        text = ex.prompts["supervisor"][0]
        self.assertTrue(text.startswith(collate.MARKER))
        for piece in ("전체 목표: 도입 여부 판단", "<<<T1 시작 · ", "맡은 일: A를 읽고 장단점을 정리", "claude의 답",
                      "맡은 일: B를 읽고 위험을 정리", "codex의 답", "<<<T2 끝>>>"):
            self.assertIn(piece, text)
        for hidden in ("SRC-A", "SRC-B"):   # 자료 원문은 주지 않는다
            self.assertNotIn(hidden, text)
        self.assertEqual(ex.inputs["supervisor"], [()])   # 자료 폴더도 붙이지 않는다
        item = self.collations(ctl, rid)[0]
        self.assertEqual((item["collation_id"], item["state"]), (key, c.ACCEPTED))
        self.assertEqual(item["labels"], {"T1": "claude", "T2": "codex"})
        claims = item["reply"]["claims"]
        self.assertEqual([q["source_check"] for q in claims[0]["quotes"]], ["exact_match", "exact_match"])
        self.assertEqual([cl["support"] for cl in claims], ["quoted", "unsupported_addition", "unsupported_addition"])
        self.assertEqual(item["reply"]["checks"], {"quotes": 3, "exact_matches": 2, "unsupported_additions": 2,
                                                   "method": "exact_verbatim_quote", "factual_check": "not_performed",
                                                   "agreement_is_verification": False})
        self.assertEqual(len(ctl.view()["runs"]), 1)                           # 모으기는 실행을 시작하지 않는다
        self.assertEqual(ctl.view()["tasks"][0]["calls_used"], 3)              # 팀원 2 + 모으기 1
        self.assertIn("collation_completed", [e["kind"] for e in events(self.store, rid)])

    def test_a_failed_member_goes_in_as_no_result_and_cannot_be_quoted(self):
        ex = Collator(outcomes={"codex": "fail"})
        ctl = self.controller(ex)
        rid = self.collected(ctl)
        ctl.collate(rid)
        self.assertTrue(ctl.wait_idle())
        self.assertIn("(결과 없음", ex.prompts["supervisor"][0])
        self.assertNotIn("codex의 답", ex.prompts["supervisor"][0])
        quotes = self.collations(ctl, rid)[0]["reply"]["claims"][0]["quotes"]
        self.assertEqual([q["source_check"] for q in quotes], ["exact_match", "not_found"])

    def test_refused_before_collection_without_an_orchestrator_and_for_isolated_runs(self):
        ex = Collator(hold=("codex",))
        ctl = self.controller(ex)
        rid = ctl.create_run("목표", [ROSTER["claude"], ROSTER["codex"]], min_independent=1,
                             role_board=board("claude", "codex"), roster=ROSTER, sources=SOURCES, assignments=WORK)
        with self.assertRaises(c.ControllerError):   # 모두 끝나기 전에는 부르지 않는다
            ctl.collate(rid)
        ex.release("codex")
        self.assertTrue(ctl.wait_idle())
        alone = self.collected(ctl, orchestrator=())
        isolated = ctl.create_run("q", [ROSTER["codex"]], min_independent=1, role_board=board(isolated=("codex",)),
                                  roster=ROSTER)
        self.assertTrue(ctl.wait_idle())
        for run in (alone, isolated):
            with self.subTest(run=run), self.assertRaises(c.ControllerError):
                ctl.collate(run)
        self.assertEqual(self.store.row("SELECT COUNT(*) AS n FROM collations")["n"], 0)
        self.assertNotIn("collations", self.run_view(ctl, isolated))

    def test_gates_one_call_at_a_time_unconfirmed_ending_review_and_two_per_run(self):
        ex = Collator(hold=("supervisor",))
        ctl = self.controller(ex)
        rid = self.collected(ctl)
        key = ctl.collate(rid)
        self.assertTrue(support.wait_for(lambda: self.collations(ctl, rid)[0]["state"] == c.RUNNING))
        self.assertEqual(ctl.view()["tasks"][0]["status"], "working")
        with self.assertRaises(c.ControllerError):   # 한 번에 하나(다듬기 포함)
            ctl.collate(rid)
        with self.assertRaises(c.ControllerError):
            ctl.refine(ROSTER["claude"], "다른 원문")
        with self.assertRaises(c.ControllerError):   # 모으기가 도는 동안 판단 완료를 받지 않는다
            ctl.mark_reviewed(rid, self.run_view(ctl, rid)["result_revision"])
        ex.outcomes = {"supervisor": "unknown"}
        ex.release("supervisor")
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.collations(ctl, rid)[0]["state"], c.UNKNOWN)
        task = ctl.view()["tasks"][0]
        self.assertEqual((task["status"], task["runs"][0]["action"]), ("problem", "종료·실패 확인"))
        self.assertEqual(ctl.unsettled(), 1)
        with self.assertRaises(c.ControllerError):
            ctl.collate(rid)
        ctl.acknowledge_collation_unknown(key)
        self.assertEqual(self.collations(ctl, rid)[0]["status"], "unknown_acknowledged")
        self.assertEqual(ctl.unsettled(), 0)
        self.assertEqual(ex.started.count("supervisor"), 1)                  # 자동으로 다시 부르지 않았다
        ex.outcomes = {"supervisor": "badjson"}
        ctl.collate(rid)
        self.assertTrue(ctl.wait_idle())
        bad = self.collations(ctl, rid)[1]
        self.assertEqual((bad["state"], bad["status"]), (c.REJECTED, "format_error"))
        self.assertEqual(bad["raw"]["text"], "모으기 대신 답을 씀")
        with self.assertRaises(c.ControllerError):   # 실행 하나에 2번까지
            ctl.collate(rid)
        ctl.mark_reviewed(rid, self.run_view(ctl, rid)["result_revision"], memo="모으기 없이 판단")
        self.assertTrue(self.run_view(ctl, rid)["reviewed"])

    def test_a_new_collation_result_makes_it_my_turn_again(self):
        ctl = self.controller(Collator())
        rid = self.collected(ctl)
        ctl.mark_reviewed(rid, self.run_view(ctl, rid)["result_revision"])
        self.assertEqual(ctl.view()["tasks"][0]["status"], "done")
        ctl.collate(rid)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(ctl.view()["tasks"][0]["status"], "my_turn")          # 새 결과(모으기)가 오면 다시 내 차례

    def test_the_orchestrator_model_chosen_on_the_board_is_the_one_called(self):
        ctl = self.controller(Collator())
        roster = server.chosen_models(ROSTER, server.MOCK_MODEL_CHOICES, {"claude": "mock-claude-large"})
        rid = ctl.create_run("목표", [roster["codex"]], min_independent=1, role_board=board("codex"), roster=roster,
                             assignments={"codex": {"task": "t", "sources": []}})
        self.assertTrue(ctl.wait_idle())
        ctl.collate(rid)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.collations(ctl, rid)[0]["orchestrator"]["model"], "mock-claude-large")

    def test_real_collations_reserve_under_the_same_cap(self):
        ctl = self.controller(RealLike(), max_real_calls=3)
        rid = self.collected(ctl)
        ctl.collate(rid)
        self.assertTrue(ctl.wait_idle())
        reserved = [e for e in events(self.store, rid) if e["kind"] == "live_call_reserved"]
        self.assertEqual(sorted(e.get("purpose", "draft") for e in reserved), ["collate", "draft", "draft"])
        with self.assertRaises(c.ControllerError):   # 상한 소진
            ctl.collate(rid)
        self.assertEqual(ctl.call_budget(), {"used": 3, "cap": 3})
        self.assertEqual(ctl.view()["tasks"][0]["calls_used"], 3)

    def test_restart_turns_a_running_collation_into_unconfirmed_termination(self):
        ctl = self.controller(Collator())
        rid = self.collected(ctl)
        ctl.collate(rid)
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(ctl.shutdown())
        with self.store.tx() as tx:
            tx.execute("UPDATE collations SET state = 'running', result = NULL WHERE run_id = ?", rid)
        self.store.close()
        reopened = Store(self.tmp / "store" / "journal.db")
        self.addCleanup(reopened.close)
        ex = Collator()
        again = c.Controller(reopened, ex, work_root=str(self.tmp / "work"))
        self.addCleanup(again.shutdown)
        item = next(r for r in again.view()["runs"] if r["run_id"] == rid)["collations"][0]
        self.assertEqual((item["state"], item["status"]), (c.UNKNOWN, "controller_restarted"))
        self.assertEqual(ex.started, [])

    def test_a_schema_twelve_ledger_is_backed_up_before_thirteen(self):
        ctl = self.controller(Collator(), max_parallel=0)
        ctl.create_run("이전 실행", [support.cli("a")], min_independent=1)
        self.assertTrue(ctl.shutdown())
        self.store.close()
        path = self.tmp / "store" / "journal.db"
        db = sqlite3.connect(path)
        db.executescript("DROP TABLE collations; PRAGMA user_version = 12;")
        db.close()
        reopened = Store(path)
        self.addCleanup(reopened.close)
        self.assertEqual(len(list(path.parent.glob("journal.db.v12-*.bak"))), 1)
        self.assertEqual(reopened.row("PRAGMA user_version")[0], SCHEMA_VERSION)


class CollateCheckTests(unittest.TestCase):
    DRAFTS = {"T1": "첫 줄\n  공백 그대로  ", "T2": None}

    def test_quotes_match_only_verbatim_and_unknown_members_or_empty_results_are_not_found(self):
        reply = collate.check(json.dumps({"claims": [
            {"statement": " s ", "quotes": [{"member": "T1", "text": "공백 그대로  "},
                                            {"member": "T1", "text": "공백  그대로"},
                                            {"member": "T2", "text": "첫 줄"},
                                            {"member": "T9", "text": "첫 줄"}]}]}, ensure_ascii=False), self.DRAFTS)
        self.assertEqual([q["source_check"] for q in reply["claims"][0]["quotes"]],
                         ["exact_match", "not_found", "not_found", "not_found"])
        self.assertEqual(reply["claims"][0]["statement"], "s")
        self.assertEqual((reply["overlaps"], reply["gaps"], reply["next"]), ([], [], []))

    def test_shape_errors_fail(self):
        for bad in ('{"claims": []}', '{"claims": [{"statement": "s"}], "verdict": "맞다"}',
                    '{"claims": [{"statement": "s", "quotes": [{"member": "T1"}]}]}',
                    '{"claims": [{"statement": "", "quotes": []}]}',
                    '{"claims": [{"statement": "s", "quotes": [], "confidence": 1}]}',
                    '{"claims": [{"statement": "s"}], "gaps": "빈 곳"}', "JSON 아님"):
            with self.subTest(bad=bad[:30]), self.assertRaises(collate.CollateError):
                collate.check(bad, self.DRAFTS)


@unittest.skipUnless(support.real_path_available(), "Windows job object나 신뢰한 bubblewrap이 있는 Linux에서만")
class MockCollateTests(support.Base):
    def test_the_mock_cli_collates_through_the_real_path(self):
        ctl = self.controller(c.MockExecutor(never=(str((self.tmp / "store").resolve()),)), timeout=30)
        rid = ctl.create_run("모의 목표", [ROSTER["claude"], ROSTER["codex"]], min_independent=1,
                             role_board=board("claude", "codex"), roster=ROSTER,
                             assignments={"claude": {"task": "앞", "sources": []}, "codex": {"task": "뒤", "sources": []}})
        self.assertTrue(ctl.wait_idle(30))
        ctl.collate(rid)
        self.assertTrue(ctl.wait_idle(30))
        item = self.run_view(ctl, rid)["collations"][0]
        self.assertEqual(item["state"], c.ACCEPTED, item)
        self.assertEqual(item["reply"]["checks"]["exact_matches"], 2)
        self.assertEqual(item["reply"]["checks"]["unsupported_additions"], 1)
