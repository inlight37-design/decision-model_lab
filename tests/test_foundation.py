"""Service boundary, public search and legacy invocation integration, without models."""
import ast
import http.client
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from urllib.parse import quote

from app import controller as c, memory
from app.server import _Server, make_handler
from app.store import events
import test_app_controller as support
from test_general_team import Recording, ROSTER, board


class PublicQueryTests(support.Base):
    def manual(self, ctl, text='검색 질문', task_id=None):
        return ctl.create_run(text, [support.manual('a'), support.manual('b')], min_independent=1,
                              quorum_policy=c.INCLUDE_UNVERIFIED, task_id=task_id)

    def test_search_counts_snippets_and_filters_never_include_sealed_answers(self):
        ctl = self.controller(support.SyntheticExecutor())
        rid = self.manual(ctl)
        digest = self.run_view(ctl, rid)['input_sha256']
        ctl.submit_manual(rid, 'a', 'SECRET-NEEDLE 반례', digest)
        before = self.store._db.total_changes
        self.assertEqual(ctl.search('SECRET-NEEDLE')['total'], 0)
        self.assertEqual(ctl.search('검색')['items'][0]['run_id'], rid)
        self.assertEqual(ctl.activity(rid)['invocations'], [])
        self.assertEqual(self.store._db.total_changes, before)
        ctl.submit_manual(rid, 'b', '공개한 다른 답', digest)
        found = ctl.search('SECRET-NEEDLE', kind='answer')
        self.assertEqual(found['total'], 1)
        self.assertIn('반례', found['items'][0]['snippet'])
        self.assertEqual(ctl.search('SECRET-NEEDLE', task_id='other')['total'], 0)
        revision = self.run_view(ctl, rid)['result_revision']
        ctl.mark_reviewed(rid, revision, '보류 결정')
        self.assertEqual(ctl.search('보류', kind='decision')['total'], 1)
        self.assertEqual(ctl.search('답', kind='answer', limit=1)['total'], 1)
        for args in [('', {}), ('q', {'limit': True}), ('q', {'limit': 101}), ('q', {'kind': 'raw'}),
                     ('q', {'task_id': 5}), ('x' * 201, {})]:
            with self.subTest(args=args), self.assertRaises(c.ControllerError):
                ctl.search(args[0], **args[1])

    def test_general_answer_search_is_public_while_another_member_is_pending(self):
        ex = Recording(hold=('codex',))
        ctl = self.controller(ex)
        self.addCleanup(ex.release, 'codex')
        rid = ctl.create_run('구조 검색', [ROSTER['claude'], ROSTER['codex']], min_independent=1,
                             role_board=board('claude', 'codex'), roster=ROSTER,
                             assignments={'claude': {'task': '빠른 답', 'sources': []},
                                          'codex': {'task': '느린 답', 'sources': []}})
        self.assertTrue(support.wait_for(lambda: self.part(ctl, rid, 'claude')['state'] == c.ACCEPTED))
        answer = self.part(ctl, rid, 'claude')['draft']
        self.assertEqual(ctl.search(answer[:12], kind='answer')['total'], 1)
        self.assertNotIn('draft', self.part(ctl, rid, 'codex'))
        ex.release('codex')
        self.assertTrue(ctl.wait_idle())

    def test_frozen_memory_explanation_does_not_reselect_or_rewrite_legacy_packs(self):
        ctl = self.controller(support.SyntheticExecutor())
        prior = self.manual(ctl, '문서 검색')
        digest = self.run_view(ctl, prior)['input_sha256']
        for pid in ('a', 'b'):
            ctl.submit_manual(prior, pid, '기억 원문', digest)
        task = self.run_view(ctl, prior)['task_id']
        rid = self.manual(ctl, '문서 검색 개선', task)
        result = ctl.memory_sources(rid)
        self.assertTrue(result['entries'][0]['selection_recorded'])
        self.assertFalse(result['entries'][0]['selection']['recent_fallback'])
        self.assertTrue(result['entries'][0]['source_available'])
        self.assertEqual(result['pack'], self.run_view(ctl, rid)['role_config']['memory'])
        fallback = memory.select(self.store, task, 'unrelated-xyz')['entries'][0]
        self.assertTrue(fallback['selection']['recent_fallback'])
        with patch('app.memory.select', side_effect=AssertionError('must not reselect')):
            self.assertEqual(ctl.memory_sources(rid), result)
        # Pre-rebuild packs remain valid: there is no invented historical score.
        roles = json.loads(self.store.row('SELECT role_config FROM runs WHERE run_id = ?', rid)['role_config'])
        pack = roles['memory']
        for entry in pack['entries']:
            entry.pop('selection', None)
        pack['sha256'] = memory.digest(memory.encoded({k: v for k, v in pack.items() if k != 'sha256'}))
        with self.store.tx() as tx:
            tx.execute('UPDATE runs SET role_config = ? WHERE run_id = ?', json.dumps(roles), rid)
        legacy = ctl.memory_sources(rid)
        self.assertFalse(legacy['entries'][0]['selection_recorded'])
        pack['sha256'] = 'corrupt'
        with self.store.tx() as tx:
            tx.execute('UPDATE runs SET role_config = ? WHERE run_id = ?', json.dumps(roles), rid)
        with self.assertRaises(c.ControllerError):
            ctl.memory_sources(rid)

    def test_invocation_adapter_keeps_unknown_synthesis_and_excludes_non_calls(self):
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        rid = ctl.create_run('q', [support.cli('a'), support.manual('b')], min_independent=1)
        self.assertEqual(ctl.activity(rid)['invocations'], [])
        with self.store.tx() as tx:
            tx.execute("UPDATE participants SET state = 'unknown', attempt = 'a1', kind = 'synthetic' "
                       "WHERE run_id = ? AND pid = 'a'", rid)
            tx.event(rid, 'synthesis_started', attempt='s1', adapter_id='codex', execution='real')
            tx.event(rid, 'synthesis_failed', attempt='s1', result={'synthesizer': {'tree_confirmed_empty': False}})
            tx.event(rid, 'synthesis_completed', result={'status': 'completed'})  # no model attempt
        before = self.store._db.total_changes
        records = ctl.activity(rid)['invocations']
        self.assertEqual({r['purpose'] for r in records}, {'draft', 'synthesis'})
        self.assertTrue(all(r['state'] == 'unknown' for r in records))
        self.assertEqual(len({r['invocation_id'] for r in records}), 2)
        self.assertEqual(records, ctl.activity(rid)['invocations'])
        self.assertEqual(self.store._db.total_changes, before)
        self.assertTrue(all(not {'prompt', 'usage', 'result', 'duration_ms', 'sha256'} & set(r) for r in records))
        ctl.acknowledge_synthesis_unknown(rid, 's1')
        final = ctl.activity(rid)['invocations']
        self.assertEqual(next(r for r in final if r['purpose'] == 'synthesis')['state'], 'acknowledged')
        self.assertEqual(next(r for r in final if r['purpose'] == 'draft')['state'], 'unknown')

    def test_role_invocations_keep_origin_and_do_not_materialize_private_payloads(self):
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        rid = self.manual(ctl)
        spec = json.dumps(vars(support.cli('a')))
        common = {'prompt': 'PRIVATE-PROMPT', 'input_sha256': 'PRIVATE-HASH',
                  'attempt': 'attempt', 'kind': 'synthetic', 'state': 'unknown'}
        rows = [
            ('refinements', {'refine_id': 'f', 'created_at': 1, 'original': 'goal', 'supervisor': spec, 'run_id': rid}),
            ('refine_turns', {**common, 'refine_id': 'f', 'turn': 1, 'note': ''}),
            ('proposals', {**common, 'proposal_id': 'p', 'run_id': rid, 'created_at': 2,
                           'supervisor': spec, 'labels': '{}'}),
            ('splits', {**common, 'split_id': 's', 'created_at': 3, 'goal': 'goal', 'orchestrator': spec,
                        'members': '[]', 'sources': '[]', 'used_by': rid}),
            ('collations', {**common, 'collation_id': 'c', 'run_id': rid, 'created_at': 4,
                            'orchestrator': spec, 'labels': '{}', 'drafts': '{}'}),
            ('reviews', {**common, 'review_id': 'r', 'run_id': rid, 'seq': 1, 'created_at': 5,
                         'question': 'q', 'reviewer': spec, 'labels': '{}', 'targets': '{}'}),
        ]
        with self.store.tx() as tx:
            for table, row in rows:
                tx.execute(f"INSERT INTO {table} ({', '.join(row)}) VALUES ({', '.join('?' for _ in row)})", *row.values())
        sql = []
        self.store._db.set_trace_callback(sql.append)
        result = ctl.activity(rid)['invocations']
        self.store._db.set_trace_callback(None)
        self.assertEqual({r['purpose'] for r in result}, {'refine', 'next_step', 'split', 'collate', 'cross_review'})
        self.assertEqual(len({r['invocation_id'] for r in result}), 5)
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertTrue(all('SELECT * FROM' not in q.upper() for q in sql if 'FROM runs' not in q))


class QueryHttpTests(support.Base):
    def test_query_endpoints_require_auth_and_report_invalid_input(self):
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        rid = ctl.create_run('한글 검색', [support.manual('a')], min_independent=1,
                             quorum_policy=c.INCLUDE_UNVERIFIED)
        server = _Server(('127.0.0.1', 0), make_handler(ctl, 'token', 0))
        port = server.server_address[1]
        server.RequestHandlerClass = make_handler(ctl, 'token', port)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def get(path, auth=True):
            con = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            try:
                con.request('GET', path, headers={'Authorization': 'Bearer token'} if auth else {})
                response = con.getresponse()
                return response.status, response.read()
            finally:
                con.close()

        for endpoint in ['/api/search?q=' + quote('한글'), f'/api/runs/{rid}/activity', f'/api/runs/{rid}/memory']:
            self.assertEqual(get(endpoint, False)[0], 401)
            self.assertEqual(get(endpoint)[0], 200)
        for endpoint in ['/api/search', '/api/search?q=q&limit=0', '/api/search?q=a&q=b', '/api/search?q=a&other=b']:
            self.assertEqual(get(endpoint)[0], 400)
        self.assertEqual(get('/api/runs/missing/activity')[0], 409)
        self.assertEqual(get('/api.js')[0], 200)
        self.assertEqual(get('/catalog.js')[0], 200)


class LayerTests(unittest.TestCase):
    def test_services_do_not_import_facade_or_transports_and_queries_do_not_launch(self):
        root = Path(__file__).resolve().parents[1] / 'app'
        for folder in ('application', 'context', 'execution', 'queries'):
            for path in (root / folder).glob('*.py'):
                module = ast.parse(path.read_text(encoding='utf-8'))
                for n in ast.walk(module):
                    if isinstance(n, ast.ImportFrom):
                        self.assertNotIn(n.module, ('app.controller', 'app.server', 'app.run'), str(path))
                    if folder in ('application', 'queries', 'context') and isinstance(n, ast.Call):
                        call = ast.unparse(n.func)
                        self.assertNotEqual(call, 'threading.Thread', str(path))
                        self.assertNotIn(call, ('self.runtime.executor.run', 'runner.run', 'isolation.run'), str(path))
