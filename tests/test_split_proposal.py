"""카드 #135: 일반 작업의 분담 제안(역할판 D 셋째 조각). 합성 실행기와 모의 CLI만 — 실제 모델을 부르지 않는다.

완료 조건을 하나씩 고정한다: 제안은 실행을 시작하지 않음, 내가 확인한 분담만 보내고 제안과 고침 여부를 따로 남김,
같은 제안으로 두 번 만들지 않음, 한 번에 하나·예약·상한·종료 미확인·재시작, 작업 호출 수.
"""
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import unittest
from unittest import mock

from app import controller as c, server, split
from app.store import SCHEMA_VERSION, Store, events
from core import adapters, contract, runner
import test_app_controller as support

ROSTER = server.PARTICIPANTS
SOURCES = [("a.md", "자료 A"), ("b.md", "자료 B")]
GOAL = "검색 방식을 정하기 전에 나눠 알아본다"


def board(*general, orchestrator=("claude",)):
    return {"supervisor": [], "orchestrator": list(orchestrator), "isolated": [], "general": list(general),
            "input_mode": "original"}


class Splitter(support.SyntheticExecutor):
    """분담 지시문에는 JSON으로 답하고(M1에 a.md, M2에 b.md), 팀원 질문에는 기존 합성 답을 준다. 입력 폴더를 기록한다.
    outcomes의 "supervisor": ok · fail · unknown · badjson · wrong(목록에 없는 자료)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prompts, self.inputs = {}, {}

    def plan(self, spec, prompt, work_dir, *, inputs=()):
        self.prompts.setdefault(spec.pid, []).append(prompt)
        self.inputs.setdefault(spec.pid, []).append(
            sorted(name for folder in inputs for name in os.listdir(folder)))
        return super().plan(spec, prompt, work_dir)

    def execute(self, spec, prompt, work_dir, timeout, *, cancel=None):
        if not prompt.startswith(split.MARKER):
            return super().execute(spec, prompt, work_dir, timeout, cancel=cancel)
        self.started.append(spec.pid)
        if spec.pid in self.gates:
            self.gates[spec.pid].wait(10)
        kind = self.outcomes.get(spec.pid, "ok")
        reply = {"assignments": [{"member": "M1", "task": "A를 본다", "sources": ["a.md"]},
                                 {"member": "M2", "task": "B를 본다", "sources": ["z.md" if kind == "wrong" else "b.md"]}],
                 "reason": "자료마다 한 명"}
        text = "분담 대신 답을 씀" if kind == "badjson" else json.dumps(reply, ensure_ascii=False)
        result = runner.RunResult(("synthetic",), runner.EXITED, 1 if kind == "fail" else 0,
                                  support.claude_stdout(text, error=kind == "fail"), "", False, False, 5, 0, True,
                                  containment=runner.PROCESS_GROUP if kind == "unknown" else runner.JOB_OBJECT,
                                  input_delivery=runner.INPUT_COMPLETE)
        return result, adapters.interpret("claude-code", result, requested_model="m")


class RealLike(Splitter):
    kind = contract.REAL

    def plan(self, spec, prompt, work_dir, *, inputs=()):
        return replace(super().plan(spec, prompt, work_dir, inputs=inputs), kind=contract.REAL)


class SplitTests(support.Base):
    def ask(self, ctl, **kwargs):
        options = dict(goal=GOAL, orchestrator=ROSTER["claude"], members=[ROSTER["claude"], ROSTER["codex"]],
                       sources=SOURCES)
        options.update(kwargs)
        sid = ctl.propose_split(**options)
        self.assertTrue(ctl.wait_idle())
        return sid

    def split_of(self, ctl, sid):
        return next(item for item in ctl.view()["splits"] if item["split_id"] == sid)

    def start(self, ctl, sid, work=None, **kwargs):
        work = work or {"claude": {"task": "A를 본다", "sources": ["a.md"]}, "codex": {"task": "B를 본다", "sources": ["b.md"]}}
        return ctl.create_run(GOAL, [ROSTER["claude"], ROSTER["codex"]], min_independent=1,
                              role_board=board("claude", "codex"), roster=ROSTER, sources=SOURCES, assignments=work,
                              split={"id": sid}, **kwargs)

    def test_the_orchestrator_sees_the_goal_members_and_every_file_and_starts_nothing(self):
        ex = Splitter()
        ctl = self.controller(ex)
        sid = self.ask(ctl)
        text = ex.prompts["supervisor"][0]
        for piece in (split.MARKER, GOAL, "M1: Claude Code", "M2: Codex", "a.md (", "b.md ("):
            self.assertIn(piece, text)
        self.assertEqual(ex.inputs["supervisor"][0], ["a.md", "b.md"])       # 자료 전부를 읽기 전용으로
        item = self.split_of(ctl, sid)
        self.assertEqual(item["reply"]["assignments"]["codex"], {"task": "B를 본다", "sources": ["b.md"]})
        self.assertEqual(item["members"], {"M1": "claude", "M2": "codex"})
        self.assertEqual(ctl.view()["runs"], [])                              # 제안은 실행을 시작하지 않는다

    def test_a_run_records_whether_it_went_as_proposed_and_uses_the_split_once(self):
        ctl = self.controller(Splitter())
        sid = self.ask(ctl)
        rid = self.start(ctl, sid, task_title="분담 작업")
        self.assertTrue(ctl.wait_idle())
        run = self.run_view(ctl, rid)
        self.assertEqual((run["split"]["split_id"], run["split"]["as_proposed"]), (sid, True))
        self.assertEqual(ctl.view()["tasks"][0]["calls_used"], 3)             # 분담 제안 1 + 팀원 2
        with self.assertRaises(c.ControllerError):   # 같은 제안으로 두 번째 실행을 만들지 않는다
            self.start(ctl, sid, task_title="또")
        other = self.ask(ctl)
        edited = self.start(ctl, other, task_title="고친 분담",
                            work={"claude": {"task": "A와 B를 본다", "sources": ["a.md", "b.md"]},
                                  "codex": {"task": "B를 본다", "sources": ["b.md"]}})
        self.assertTrue(ctl.wait_idle())
        self.assertIs(self.run_view(ctl, edited)["split"]["as_proposed"], False)   # 고쳐도 받되 고쳤다고 남긴다
        self.assertEqual(ctl.view()["splits"], [])

    def test_a_split_must_match_members_files_goal_task_and_orchestrator(self):
        ctl = self.controller(Splitter())
        sid = self.ask(ctl)
        cases = [
            ("other members", dict(members=[ROSTER["claude"]], layout=board("claude"),
                                   work={"claude": {"task": "t", "sources": ["a.md", "b.md"]}})),
            ("other files", dict(sources=[("a.md", "바뀐 자료 A"), ("b.md", "자료 B")])),
            ("other goal", dict(goal="다른 목표")),
            ("other orchestrator", dict(layout=board("claude", "codex", orchestrator=("codex",)))),
            ("no orchestrator", dict(layout=board("claude", "codex", orchestrator=()))),
        ]
        base = {"claude": {"task": "A를 본다", "sources": ["a.md"]}, "codex": {"task": "B를 본다", "sources": ["b.md"]}}
        for name, o in cases:
            with self.subTest(name), self.assertRaises(c.ControllerError):
                ctl.create_run(o.get("goal", GOAL), o.get("members", [ROSTER["claude"], ROSTER["codex"]]),
                               min_independent=1, role_board=o.get("layout", board("claude", "codex")), roster=ROSTER,
                               sources=o.get("sources", SOURCES), assignments=o.get("work", base), split={"id": sid})
        with self.assertRaises(c.ControllerError):   # 격리 실행에는 분담 제안을 주지 않는다
            ctl.create_run(GOAL, [ROSTER["codex"]], min_independent=1,
                           role_board={"supervisor": [], "orchestrator": [], "isolated": ["codex"], "general": [],
                                       "input_mode": "original"}, roster=ROSTER, split={"id": sid})
        self.assertEqual(ctl.view()["runs"], [])
        self.assertIsNone(self.split_of(ctl, sid)["used_by"])

    def test_failed_or_invalid_splits_cannot_start_a_run(self):
        ex = Splitter(outcomes={"supervisor": "wrong"})
        ctl = self.controller(ex)
        wrong = self.ask(ctl)
        ex.outcomes = {"supervisor": "badjson"}
        bad = self.ask(ctl)
        for sid in (wrong, bad):
            item = self.split_of(ctl, sid)
            self.assertEqual((item["state"], item["status"]), (c.REJECTED, "format_error"))
            with self.subTest(sid=sid), self.assertRaises(c.ControllerError):
                self.start(ctl, sid)
        self.assertEqual(self.split_of(ctl, bad)["raw"]["text"], "분담 대신 답을 씀")

    def test_one_call_at_a_time_unconfirmed_ending_and_restart(self):
        ex = Splitter(hold=("supervisor",))
        ctl = self.controller(ex)
        sid = ctl.propose_split(GOAL, ROSTER["claude"], [ROSTER["claude"], ROSTER["codex"]], SOURCES)
        self.assertTrue(support.wait_for(lambda: self.split_of(ctl, sid)["state"] == c.RUNNING))
        with self.assertRaises(c.ControllerError):   # 상위 모델 호출은 한 번에 하나(다듬기·제안 포함)
            ctl.propose_split(GOAL, ROSTER["claude"], [ROSTER["claude"], ROSTER["codex"]], SOURCES)
        with self.assertRaises(c.ControllerError):
            ctl.refine(ROSTER["claude"], "원문")
        ex.outcomes = {"supervisor": "unknown"}
        ex.release("supervisor")
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.split_of(ctl, sid)["state"], c.UNKNOWN)
        self.assertEqual(ctl.unsettled(), 1)
        ctl.acknowledge_split_unknown(sid)
        self.assertEqual(ctl.unsettled(), 0)
        self.assertEqual(ex.started.count("supervisor"), 1)
        # 재시작: 진행 중이던 분담 제안은 종료 미확인이 된다
        ex.outcomes = {}
        again_id = self.ask(ctl)
        self.assertTrue(ctl.shutdown())
        with self.store.tx() as tx:
            tx.execute("UPDATE splits SET state = 'running', result = NULL WHERE split_id = ?", again_id)
        self.store.close()
        reopened = Store(self.tmp / "store" / "journal.db")
        self.addCleanup(reopened.close)
        restarted = c.Controller(reopened, Splitter(), work_root=str(self.tmp / "work"))
        self.addCleanup(restarted.shutdown)
        item = next(x for x in restarted.view()["splits"] if x["split_id"] == again_id)
        self.assertEqual((item["state"], item["status"]), (c.UNKNOWN, "controller_restarted"))

    def test_real_splits_reserve_under_the_same_cap(self):
        ctl = self.controller(RealLike(), max_real_calls=1)
        sid = self.ask(ctl)
        reserved = [e for e in events(self.store, sid) if e["kind"] == "live_call_reserved"]
        self.assertEqual([e["purpose"] for e in reserved], ["split"])
        with self.assertRaises(c.ControllerError):
            ctl.propose_split(GOAL, ROSTER["claude"], [ROSTER["claude"], ROSTER["codex"]], SOURCES)
        self.assertEqual(ctl.call_budget(), {"used": 1, "cap": 1})

    def test_an_unexpected_error_in_the_check_keeps_the_raw_reply(self):
        # 검사가 뜻밖의 예외를 내도 결과 저장 실패로 빠지지 않고, 원문과 이유를 남긴 형식 실패가 된다(Codex 검토, PR #136)
        def broken(text, row):
            raise TypeError("unhashable member")
        with mock.patch.object(c, "SPLIT_SEAT", replace(c.SPLIT_SEAT, check=broken)):
            ctl = self.controller(Splitter())
            sid = self.ask(ctl)
        item = self.split_of(ctl, sid)
        self.assertEqual((item["state"], item["status"]), (c.REJECTED, "format_error"))
        self.assertIn("TypeError", item["reason"])
        self.assertIn("A를 본다", item["raw"]["text"])

    def test_bad_requests_start_nothing(self):
        ctl = self.controller(Splitter())
        for name, kwargs in (("empty goal", dict(goal="  ")),
                             ("original app member", dict(members=[ROSTER["claude"], ROSTER["claude-app"]])),
                             ("same provider twice", dict(members=[ROSTER["claude"], replace(ROSTER["codex"], provider="anthropic")])),
                             ("original app orchestrator", dict(orchestrator=ROSTER["claude-app"])),
                             ("unknown task", dict(task_id="t-none"))):
            options = dict(goal=GOAL, orchestrator=ROSTER["claude"], members=[ROSTER["claude"], ROSTER["codex"]],
                           sources=SOURCES)
            options.update(kwargs)
            with self.subTest(name), self.assertRaises(c.ControllerError):
                ctl.propose_split(**options)
        self.assertEqual(self.store.row("SELECT COUNT(*) AS n FROM splits")["n"], 0)

    def test_a_schema_eleven_ledger_is_backed_up_before_twelve(self):
        ctl = self.controller(Splitter(), max_parallel=0)
        ctl.create_run("이전 실행", [support.cli("a")], min_independent=1)
        self.assertTrue(ctl.shutdown())
        self.store.close()
        path = self.tmp / "store" / "journal.db"
        db = sqlite3.connect(path)
        db.executescript("DROP TABLE splits; PRAGMA user_version = 11;")
        db.close()
        reopened = Store(path)
        self.addCleanup(reopened.close)
        self.assertEqual(len(list(path.parent.glob("journal.db.v11-*.bak"))), 1)
        self.assertEqual(reopened.row("PRAGMA user_version")[0], SCHEMA_VERSION)


class SplitCheckTests(unittest.TestCase):
    LABELS, NAMES = {"M1": "claude", "M2": "codex"}, ["a.md", "b.md"]

    def reply(self, **change):
        body = {"assignments": [{"member": "M1", "task": "A", "sources": ["a.md"]},
                                {"member": "M2", "task": "B", "sources": ["b.md"]}], "reason": "r"}
        body.update(change)
        return json.dumps(body)

    def test_every_member_once_listed_files_only_and_every_file_used(self):
        self.assertEqual(split.check(self.reply(), self.LABELS, self.NAMES)["assignments"]["claude"],
                         {"task": "A", "sources": ["a.md"]})
        bad = [
            self.reply(assignments=[{"member": "M1", "task": "A", "sources": ["a.md", "b.md"]}]),
            self.reply(assignments=[{"member": "M1", "task": "A", "sources": ["a.md"]},
                                    {"member": "M1", "task": "B", "sources": ["b.md"]}]),
            self.reply(assignments=[{"member": "M1", "task": "A", "sources": ["a.md"]},
                                    {"member": "M2", "task": "B", "sources": []}]),
            self.reply(assignments=[{"member": "M1", "task": "A", "sources": ["a.md"]},
                                    {"member": "M3", "task": "B", "sources": ["b.md"]}]),
            self.reply(reason=""), self.reply(answer="몰래 답"), "JSON 아님",
            self.reply(assignments=[{"member": [], "task": "A", "sources": ["a.md"]},   # 글이 아닌 이름표(Codex 검토)
                                    {"member": "M2", "task": "B", "sources": ["b.md"]}]),
            self.reply(assignments=[{"member": {"M": 1}, "task": "A", "sources": ["a.md"]},
                                    {"member": "M2", "task": "B", "sources": ["b.md"]}]),
        ]
        for text in bad:
            with self.subTest(text=text[:40]), self.assertRaises(split.SplitError):
                split.check(text, self.LABELS, self.NAMES)


@unittest.skipUnless(support.real_path_available(), "Windows job object나 신뢰한 bubblewrap이 있는 Linux에서만")
class MockSplitTests(support.Base):
    def test_the_mock_cli_answers_a_split_through_the_real_path(self):
        ctl = self.controller(c.MockExecutor(never=(str((self.tmp / "store").resolve()),)), timeout=30)
        sid = ctl.propose_split(GOAL, ROSTER["claude"], [ROSTER["claude"], ROSTER["codex"]], SOURCES)
        self.assertTrue(ctl.wait_idle(30))
        item = next(x for x in ctl.view()["splits"] if x["split_id"] == sid)
        self.assertEqual(item["state"], c.ACCEPTED, item)
        self.assertEqual(item["reply"]["assignments"]["claude"]["sources"], ["a.md"])
