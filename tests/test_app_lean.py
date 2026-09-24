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
        lifecycle = [q for q in queries if q not in tail]
        for query in lifecycle:
            self.assertIn("WHERE KIND IN ('SYNTHESIS_STARTED', 'SYNTHESIS_FAILED', 'SYNTHESIS_COMPLETED', "
                          "'SYNTHESIS_UNKNOWN_ACKNOWLEDGED')", query)
        # 종료 미확인의 자리를 재시작 뒤에도 세려면 별도로 합성 사건만 읽어야 한다.
        self.assertTrue(lifecycle)
        self.assertNotIn('x' * 20, json.dumps(view))

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
