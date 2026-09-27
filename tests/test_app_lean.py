"""회귀: 화면에는 필요한 실행/사건 이름만 읽는다. 모델 호출 없음."""
import ast
import json
import sys
import tempfile
from pathlib import Path
import unittest

from app import controller as c
from app.store import Store


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Store(Path(tmp.name) / 'journal.db')
        self.addCleanup(self.store.close)
        self.ctl = c.Controller(self.store, c.MockExecutor(), max_parallel=0)

    def create(self, question):
        return self.ctl.create_run(question, [c.ParticipantSpec('app', 'App', 'test', c.MANUAL)],
                                   min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)

    def test_event_tail_is_bounded_at_the_database_without_reading_payloads(self):
        rid = self.create('q')
        with self.store.tx() as tx:
            for i in range(100):
                tx.event(rid, f'event_{i}', detail='x' * 2048)
        sql = []
        self.store._db.set_trace_callback(sql.append)
        self.addCleanup(self.store._db.set_trace_callback, None)
        view = self.ctl.view()
        self.assertEqual(view['runs'][0]['events'], [f'event_{i}' for i in range(88, 100)])
        queries = [q.upper() for q in sql if q.upper().startswith('SELECT') and 'FROM EVENTS' in q.upper()]
        tail = [q for q in queries if q.startswith('SELECT KIND ')]
        self.assertEqual(len(tail), 1)
        self.assertIn('LIMIT 12', tail[0])
        # 판단 완료는 결과 판과 비교한다(AH-01). 한 번의 집계로 seq·kind만 읽고 내용(payload)은 읽지 않는다.
        review = [q for q in queries if "KIND = 'HUMAN_REVIEWED'" in q]
        self.assertEqual(len(review), 1)
        self.assertTrue(review[0].startswith("SELECT COALESCE(MAX("))
        self.assertNotIn("PAYLOAD", review[0])
        lifecycle = [q for q in queries if q not in tail and q not in review]
        for query in lifecycle:
            self.assertIn("WHERE KIND IN ('SYNTHESIS_STARTED', 'SYNTHESIS_FAILED', 'SYNTHESIS_COMPLETED', "
                          "'SYNTHESIS_UNKNOWN_ACKNOWLEDGED')", query)
        # 종료 미확인의 자리를 재시작 뒤에도 세려면 별도로 합성 사건만 읽어야 한다.
        self.assertTrue(lifecycle)
        self.assertNotIn('x' * 20, json.dumps(view))

    def test_the_synthesis_lifecycle_is_read_once_per_view(self):
        # 카드 #121(S6): 실행 수와 상관없이 한 번의 조회가 합성 이력을 한 번만 읽고, 실행별·전역 투영이 나눠 쓴다
        rids = [self.create(f'q{i}') for i in range(3)]
        with self.store.tx() as tx:
            for rid in rids:
                tx.event(rid, 'synthesis_started', attempt=f'a-{rid}')
        for target in (None, rids[0]):
            sql = []
            self.store._db.set_trace_callback(sql.append)
            try:
                self.ctl.view(target)
            finally:
                self.store._db.set_trace_callback(None)
            lifecycle = [q for q in sql if q.startswith('SELECT run_id, kind, payload FROM events')]
            with self.subTest(target=target):
                self.assertEqual(len(lifecycle), 1)

    def test_the_shared_lifecycle_gives_the_same_answers_as_reading_it_per_run(self):
        # 공개된 실행에서 요청 하나의 이력을 잘라 쓴 결과가 실행마다 새로 읽은 결과와 같다(Codex 교차검토, PR #148)
        runs = []
        for question in ('a', 'b'):
            rid = self.create(question)
            digest = next(r for r in self.ctl.view()['runs'] if r['run_id'] == rid)['input_sha256']
            self.ctl.submit_manual(rid, 'app', f'answer {question}', digest)
            runs.append(rid)
        first, second = runs
        with self.store.tx() as tx:
            # 받지 않은 참여자의 답이 원장에 남아 있어도 내보내지 않는다(공개 뒤 원장에 직접 넣은 대조군)
            tx.execute("INSERT INTO participants (run_id, pid, spec, state, status) VALUES (?, 'gone', ?, 'rejected', "
                       "'withdrawn')", first, json.dumps({'pid': 'gone', 'label': 'Gone', 'provider': 'test2',
                                                          'transport': c.MANUAL}))
            tx.execute("INSERT INTO drafts VALUES (?, 'gone', 'SHOULD-NOT-SHOW', 'x', 'manual', 0)", first)
            tx.event(first, 'synthesis_started', attempt='a1')
            tx.event(first, 'synthesis_completed', attempt='a1', result={'status': 'completed'})
            tx.event(first, 'synthesis_started', attempt='a2')
            tx.event(first, 'synthesis_failed', attempt='a2', result={'reason': 'format', 'message': 'm'})
            tx.event(second, 'synthesis_started', attempt='b1')
        self.ctl._synthesis[second] = (None, None, 'b1')   # 도는 중인 합성(작업자)
        self.addCleanup(self.ctl._synthesis.pop, second, None)
        view = self.ctl.view()
        for rid in runs:
            run = next(r for r in view['runs'] if r['run_id'] == rid)
            with self.subTest(run=rid):
                self.assertEqual(run['model_synthesis'], self.ctl._model_synthesis_state(rid))
                self.assertEqual([m['attempt'] for m in run['model_syntheses']], list(
                    attempt for (_, attempt) in self.ctl._synthesis_attempts(rid)))
                for gone in (p for p in run['participants'] if p['pid'] == 'gone'):
                    self.assertNotIn('draft', gone)
        self.assertEqual(next(r for r in view['runs'] if r['run_id'] == second)['model_synthesis'], {'status': 'running'})
        self.assertEqual((view['slots']['used'], view['unsettled']['count']), (self.ctl._slots_used(), self.ctl.unsettled()))
        self.assertNotIn('SHOULD-NOT-SHOW', json.dumps(view, ensure_ascii=False))

    def test_one_run_projection_does_not_materialize_other_runs(self):
        first, second = self.create('first'), self.create('second')
        sql = []
        self.store._db.set_trace_callback(sql.append)
        self.addCleanup(self.store._db.set_trace_callback, None)
        view = self.ctl.view(first)
        self.assertEqual([r['run_id'] for r in view['runs']], [first])
        self.assertFalse(any(second in q for q in sql))
        self.assertEqual(self.ctl.view('absent')['runs'], [])
        self.assertEqual(len(self.ctl.view()['runs']), 2)


class DependencyBoundaryTests(unittest.TestCase):
    def test_runtime_stays_stdlib_only_and_core_does_not_import_app(self):
        root = Path(__file__).resolve().parents[1]
        for path in [*root.glob("app/*.py"), *root.glob("core/*.py")]:
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    top = name.split(".")[0]
                    with self.subTest(file=path.name, dependency=name):
                        self.assertIn(top, sys.stdlib_module_names | {"core", "app"})
                        if path.parent.name == "core":
                            self.assertNotEqual(top, "app")


if __name__ == '__main__':
    unittest.main()
