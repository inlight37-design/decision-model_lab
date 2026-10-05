"""Paging must not narrow completion, leak sealed data or reuse stale state."""
import json
from http.client import HTTPConnection
import sqlite3
from unittest.mock import patch

from app import controller as c
from app.queries.pages import encode
from tools.benchmark_queries import seed
import test_app_controller as support
import test_app_integrity as http
from test_workflow import plan


class Pages(support.Base):
    def test_tied_cursors_insertion_and_deep_link_outside_page(self):
        seed(self.store, 300)
        with self.store.tx() as tx:
            tx.execute('UPDATE tasks SET created_at = 1')
            tx.execute('UPDATE runs SET created_at = 1')
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        pages = ctl.queries.pages
        first = pages.browse(limit=7)
        self.assertEqual(len(first['tasks']), 7)
        self.assertTrue(all(not t['runs'] and t['run_count'] == 10 for t in first['tasks']))
        seen = [t['task_id'] for t in first['tasks']]
        ctl.tasks.save(plan('newest'))
        cursor = first['pages']['tasks']['next']
        while cursor:
            value = pages.browse(tasks_after=cursor, limit=7)
            seen.extend(t['task_id'] for t in value['tasks']); cursor = value['pages']['tasks']['next']
        self.assertEqual(seen, [f't-{i:06}' for i in reversed(range(30))])
        detail = pages.browse(run='r-000000', limit=3)
        self.assertEqual(detail['focus_task']['task_id'], 't-000000')
        self.assertNotIn('t-000000', [t['task_id'] for t in detail['tasks']])
        self.assertEqual(detail['runs'][0], ctl.queries.view('r-000000', _global=False)['runs'][0])
        self.assertEqual(detail['focus_run']['run_id'], 'r-000000')
        seen = [r['run_id'] for r in detail['focus_task']['runs']]
        cursor = detail['pages']['runs']['next']
        while cursor:
            value = pages.browse(task='t-000000', runs_after=cursor, limit=3)
            seen.extend(r['run_id'] for r in value['focus_task']['runs']); cursor = value['pages']['runs']['next']
        self.assertEqual(seen, [f'r-{i:06}' for i in reversed(range(10))])

    def test_whole_history_status_inbox_and_prerequisites_survive_paging(self):
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        a = ctl.tasks.save(plan('선행')); b = ctl.tasks.save(plan('후속', [a['task_id']]))
        rid = ctl.create_run('봉인 질문', [support.manual('a'), support.manual('b')], min_independent=1,
                             quorum_policy=c.INCLUDE_UNVERIFIED, task_id=a['task_id'])
        ctl.submit_manual(rid, 'a', 'SEALED-NOT-FOR-PAGES', ctl.view(rid)['runs'][0]['input_sha256'])
        for i in range(6): ctl.tasks.save(plan('later' + str(i)))
        value = ctl.queries.pages.browse(task=b['task_id'], limit=1)
        self.assertNotIn('SEALED-NOT-FOR-PAGES', json.dumps(value))
        self.assertFalse(value['focus_task']['readiness']['dependencies_met'])
        self.assertEqual(value['focus_task']['status'], 'blocked')
        self.assertNotIn('evidence', value['focus_task']['readiness']['dependencies'][0])
        found, cursor = value['inbox'], value['pages']['inbox']['next']
        while cursor:
            p = ctl.queries.pages.browse(inbox_after=cursor, limit=1)
            found += p['inbox']; cursor = p['pages']['inbox']['next']
        self.assertEqual({x['id'] for x in found}, {x['id'] for x in ctl.queries.overview()['inbox']})
        self.assertEqual(len(found), len({x['id'] for x in found}))
        with self.assertRaisesRegex(c.ControllerError, '선행 작업'):
            ctl.create_run('q', [support.manual('a')], min_independent=1,
                           quorum_policy=c.INCLUDE_UNVERIFIED, task_id=b['task_id'])

    def test_cache_invalidation_writes_rollback_external_connection_and_runtime(self):
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        a = ctl.tasks.save(plan('original')); pages = ctl.queries.pages
        with patch.object(ctl.queries, 'overview', wraps=ctl.queries.overview) as read:
            value = pages.browse(); value['tasks'][0]['title'] = 'caller mutation'
            self.assertEqual(pages.browse()['tasks'][0]['title'], 'original')
            self.assertEqual(read.call_count, 1)
            ctl.paused = not ctl.paused
            self.assertEqual(pages.browse()['paused'], ctl.paused)
            self.assertEqual(read.call_count, 2)
            with patch('app.queries.pages.runner.lingering', return_value=2):
                self.assertGreaterEqual(pages.browse()['unsettled']['count'], 2)
            self.assertEqual(pages.browse()['unsettled']['count'], 0)
        with self.assertRaises(RuntimeError):
            with self.store.tx() as tx:
                tx.execute('UPDATE tasks SET title = ? WHERE task_id = ?', 'rolled back', a['task_id'])
                self.assertEqual(pages.browse()['tasks'][0]['title'], 'rolled back')
                raise RuntimeError('rollback')
        self.assertEqual(pages.browse()['tasks'][0]['title'], 'original')
        with sqlite3.connect(self.tmp / 'store' / 'journal.db') as db:
            db.execute('UPDATE tasks SET title = ?', ('external',))
        self.assertEqual(pages.browse()['tasks'][0]['title'], 'external')
        ctl.tasks.save(plan('saved', revision=1), task_id=a['task_id'])
        self.assertEqual(pages.browse()['tasks'][0]['title'], 'saved')

    def test_choices_and_cursor_validation_are_scoped_and_bounded(self):
        seed(self.store, 60); ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        pages = ctl.queries.pages
        a = pages.choices(limit=2); b = pages.choices(limit=2, after=a['next'])
        self.assertEqual(len({t['task_id'] for t in a['items'] + b['items']}), 4)
        self.assertEqual(pages.choices(query='000000')['items'][0]['task_id'], 't-000000')
        for args in ({'limit': True}, {'limit': 0}, {'limit': 101}, {'tasks_after': '???'},
                     {'tasks_after': encode('inbox', [1, 'a'])}, {'runs_after': encode('runs:a', [1, 'a'])},
                     {'task': 'no-such-task'}, {'task': 't-000001', 'run': 'r-000000'}):
            with self.subTest(args=args), self.assertRaises(c.ControllerError): pages.browse(**args)
        with self.assertRaises(c.ControllerError): pages.choices(query='other', after=a['next'])


class PagesHttp(http.HttpServerCase):
    def test_http_validation_and_static_asset(self):
        def get(path):
            conn = HTTPConnection('127.0.0.1', self.port, timeout=2)
            try:
                conn.request('GET', path, headers={'Authorization': 'Bearer ' + self.token})
                response = conn.getresponse(); response.read()
                return response.status
            finally:
                conn.close()
        for path in ('/api/browse', '/api/task-choices', '/paging.js'):
            self.assertEqual(get(path), 200)
        for path in ('/api/browse?limit=101', '/api/browse?limit=1&limit=2', '/api/browse?task=',
                     '/api/browse?unknown=value', '/api/task-choices?after=bad'):
            self.assertEqual(get(path), 400)
