"""controller의 실행 계약(순서 5): 계획 한 번(G4), 시도에 저장한 실행 종류(G6), 스키마 5 이전. 모델·프로세스 없음."""
import sqlite3

from app import controller as c, store as s
from core import contract
import test_app_controller as support


class CountingExecutor(support.SyntheticExecutor):
    """계획과 실행을 센다. 실행이 받은 계획이 기록한 계획과 같은 객체인지 본다."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.planned, self.ran = [], []

    def plan(self, spec, prompt, work_dir):
        plan = super().plan(spec, prompt, work_dir)
        self.planned.append(plan)
        return plan

    def run(self, plan, timeout, *, cancel=None):
        self.ran.append(plan)
        return super().run(plan, timeout, cancel=cancel)


class RealLookingExecutor(support.SyntheticExecutor):
    """다시 시작한 controller에 다른 종류의 실행기가 붙은 경우."""
    kind = contract.REAL


class RefusingExecutor(support.SyntheticExecutor):
    def plan(self, spec, prompt, work_dir):
        raise ValueError("no plan for this participant")


class PlanOnceTests(support.Base):
    def test_one_plan_is_recorded_and_the_same_plan_runs(self):
        ex = CountingExecutor()
        ctl = self.controller(ex)
        rid = ctl.create_run("question", [support.cli("a"), support.cli("b")], min_independent=2)
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(len(ex.planned), 2)
        self.assertEqual([id(p) for p in ex.ran], [id(p) for p in ex.planned])     # 다시 만들지 않았다
        started = [e for e in s.events(self.store, rid) if e["kind"] == "attempt_started"]
        self.assertEqual(sorted(e["spec"]["argv"][1] for e in started), ["a", "b"])
        self.assertEqual({e["spec"]["revision"] for e in started}, {"synthetic"})
        self.assertEqual({e["execution"] for e in started}, {contract.SYNTHETIC})
        self.assertNotIn("question", repr([e["spec"] for e in started]))          # 질문 본문은 기록하지 않는다

    def test_a_refused_plan_starts_nothing_and_is_not_unknown(self):
        ex = RefusingExecutor()
        ctl = self.controller(ex)
        rid = ctl.create_run("question", [support.cli("a")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        part = self.part(ctl, rid, "a")
        self.assertEqual((part["state"], part["status"]), (c.REJECTED, "process_failed_to_start"))
        self.assertEqual(ex.started, [])
        self.assertEqual((part["execution"], part["contamination"]), (contract.SYNTHETIC, list(c.NOT_RUN)))
        started = next(e for e in s.events(self.store, rid) if e["kind"] == "attempt_started")
        self.assertIn("no plan for this participant", started["spec"]["refused"])


class StoredKindTests(support.Base):
    def test_the_view_reads_the_stored_kind_not_the_current_executor(self):
        ctl = self.controller(support.SyntheticExecutor())
        rid = ctl.create_run("question", [support.cli("a"), support.manual("m")], min_independent=1,
                             quorum_policy=c.INCLUDE_UNVERIFIED)
        self.assertTrue(ctl.wait_idle())
        ctl.cancel_run(rid)
        self.assertEqual(self.part(ctl, rid, "a")["execution"], contract.SYNTHETIC)
        again = self.controller(RealLookingExecutor())                 # 다시 시작하며 실행기가 바뀌었다
        a, m = self.part(again, rid, "a"), self.part(again, rid, "m")
        self.assertEqual((a["execution"], a["contamination"]),
                         (contract.SYNTHETIC, list(c.CONTAMINATION[contract.SYNTHETIC])))
        self.assertIsNone(m["execution"])
        self.assertEqual(m["contamination"], list(c.CONTAMINATION[c.MANUAL]))

    def test_participants_that_never_ran_say_so(self):
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        rid = ctl.create_run("question", [support.cli("a")], min_independent=1)
        self.assertEqual(self.part(ctl, rid, "a")["contamination"], list(c.NOT_RUN))
        ctl.cancel_run(rid)
        self.assertEqual(self.part(ctl, rid, "a")["contamination"], list(c.NOT_RUN))


class KindMigrationTests(support.Base):
    def legacy_journal(self, executor_name):
        ex = support.SyntheticExecutor()
        ex.name = executor_name
        ctl = self.controller(ex)
        rid = ctl.create_run("question", [support.cli("a")], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        self.store._db.execute("ALTER TABLE participants DROP COLUMN kind")
        self.store._db.execute("PRAGMA user_version = 4")
        path = self.store.path
        self.store.close()
        return path, rid

    def reopen(self, path):
        self.store = s.Store(path)
        self.addCleanup(self.store.close)
        return self.controller(RealLookingExecutor())

    def test_old_attempts_get_their_kind_from_the_start_event(self):
        for name, kind, flags in (("job_object", contract.MOCK, c.CONTAMINATION[contract.MOCK]),
                                  ("bubblewrap", contract.MOCK, c.CONTAMINATION[contract.MOCK]),
                                  ("cli", contract.REAL, c.CONTAMINATION[contract.REAL]),
                                  ("synthetic", None, c.UNRECORDED)):
            with self.subTest(executor=name):
                self.setUp()
                path, rid = self.legacy_journal(name)
                ctl = self.reopen(path)
                part = self.part(ctl, rid, "a")
                self.assertEqual((part["execution"], part["contamination"]), (kind, list(flags)))
                db = sqlite3.connect(path)
                self.addCleanup(db.close)
                self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], s.SCHEMA_VERSION)
