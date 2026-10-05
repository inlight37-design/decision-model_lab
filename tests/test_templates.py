"""Reusable settings preserve inputs without copying execution authority. No models."""
import copy
from dataclasses import replace
import http.client
import json
import sqlite3

from app import controller as c, server
from app.store import Store, SCHEMA_VERSION
from test_app_controller import Base, SyntheticExecutor
from test_app_integrity import HttpServerCase
from test_cross_review import Reviewer, ROSTER, board


def draft():
    return {'question': '문서 검색 검토', 'task_title': '비교 팀', 'role_board': board('claude', 'codex'),
            'models': {}, 'min_independent': 2, 'quorum_policy': 'independent_only',
            'sources': [{'name': 'notes.txt', 'text': '보존할 반례 🧭'}], 'use_memory': False}


class Templates(Base):
    def test_export_import_is_a_new_template_and_never_restores_old_runs_or_budget(self):
        ctl = self.controller(SyntheticExecutor(), max_parallel=0)
        saved = ctl.templates.save('이동', draft(), ROSTER)
        document = ctl.templates.export(saved['template_id'])
        other = Store(self.tmp / 'other' / 'journal.db')
        try:
            target = c.Controller(other, SyntheticExecutor(), max_parallel=0, max_real_calls=2)
            copied = target.templates.import_copy(document, ROSTER)
            self.assertNotEqual(copied['template_id'], saved['template_id'])
            self.assertEqual(target.templates.load(copied['template_id'])['draft'], draft())
            self.assertEqual(target.view()['runs'], [])
            self.assertEqual(target.call_budget()['cap'], 2)
            changed = copy.deepcopy(document); changed['draft']['sources'][0]['text'] = 'changed'
            with self.assertRaises(c.ControllerError): target.templates.import_copy(changed, ROSTER)
            self.assertTrue(target.shutdown())
        finally: other.close()

    def test_saved_copy_survives_reopen_without_starting_or_copying_authority(self):
        ctl = self.controller(SyntheticExecutor(), max_parallel=0)
        data = draft()
        saved = ctl.templates.save('비교 템플릿', data, ROSTER)
        data['sources'][0]['text'] = 'caller changed'
        item = ctl.templates.load(saved['template_id'])
        self.assertEqual(item['draft']['sources'][0]['text'], '보존할 반례 🧭')
        self.assertEqual(ctl.view()['runs'], [])
        self.assertEqual(ctl.executor.started, [])
        self.assertEqual(set(item['draft']) & {'task_id', 'run_id', 'confirmation', 'refinement', 'live_cap'}, set())
        sql = []; self.store._db.set_trace_callback(sql.append)
        self.assertEqual(ctl.templates.list()[0]['template_id'], saved['template_id'])
        self.store._db.set_trace_callback(None)
        self.assertNotIn('payload', ' '.join(sql).lower())
        self.assertTrue(ctl.shutdown()); self.store.close()
        reopened = Store(self.store.path)
        try:
            new = c.Controller(reopened, SyntheticExecutor(), max_parallel=0)
            self.assertEqual(new.templates.load(saved['template_id']), item)
            self.assertTrue(new.shutdown())
        finally:
            reopened.close()

    def test_approval_fields_invalid_inputs_and_changed_card_bindings_are_rejected(self):
        ctl = self.controller(SyntheticExecutor(), max_parallel=0)
        for key in ('run_id', 'confirmation', 'refinement', 'proposal', 'task_id', 'live_cap'):
            with self.subTest(key=key), self.assertRaises(c.ControllerError):
                ctl.templates.save('bad', {**draft(), key: 'old'}, ROSTER)
        for change in ({'question': '\ud800'}, {'min_independent': True}, {'use_memory': 1},
                       {'sources': [{'name': '../outside', 'text': 'bad'}]}, {'models': {'missing': 'm'}}):
            with self.subTest(change=change), self.assertRaises(c.ControllerError):
                ctl.templates.save('bad', {**draft(), **change}, ROSTER)
        saved = ctl.templates.save('valid', draft(), ROSTER)
        item = ctl.templates.load(saved['template_id'])
        with self.assertRaises(c.ControllerError):
            ctl.templates.validate(item['draft'], {**ROSTER, 'claude': replace(ROSTER['claude'], model='changed')}, item['bindings'])
        self.assertEqual(len(ctl.templates.list()), 1)
        self.assertEqual(ctl.executor.started, [])

    def test_general_assignments_and_refine_mode_restore_as_unapproved_drafts(self):
        ctl = self.controller(SyntheticExecutor(), max_parallel=0)
        data = draft(); data['role_board'] = {**board(), 'general': ['claude']}
        data['assignments'] = {'claude': {'task': '반례 찾기', 'sources': ['notes.txt']}}
        saved = ctl.templates.save('분담', data, ROSTER)
        self.assertEqual(ctl.templates.load(saved['template_id'])['draft'], data)
        data = draft(); data['role_board'].update(supervisor=['claude'], input_mode='refine')
        saved = ctl.templates.save('다듬기', data, ROSTER)
        restored = ctl.templates.load(saved['template_id'])['draft']
        self.assertEqual(restored['role_board']['input_mode'], 'refine')
        with self.assertRaises(c.ControllerError):
            ctl.prepare_run(restored['question'], [ROSTER['claude'], ROSTER['codex']],
                            min_independent=2, role_board=restored['role_board'], roster=ROSTER)

    def test_corrupt_payload_and_stale_delete_do_not_change_runs(self):
        ctl = self.controller(SyntheticExecutor(), max_parallel=0)
        saved = ctl.templates.save('보관', draft(), ROSTER)
        with self.assertRaises(c.ControllerError): ctl.templates.delete(saved['template_id'], 'stale')
        with self.store.tx() as tx:
            tx.execute('UPDATE work_templates SET payload = ? WHERE template_id = ?', '{}', saved['template_id'])
        with self.assertRaises(c.ControllerError): ctl.templates.load(saved['template_id'])
        ctl.templates.delete(saved['template_id'], saved['sha256'])
        self.assertEqual(ctl.templates.list(), [])
        self.assertEqual(ctl.view()['runs'], [])

    def test_v14_migration_backs_up_and_preserves_runs_and_budget(self):
        ctl = self.controller(SyntheticExecutor(), max_parallel=0, max_real_calls=3)
        rid = ctl.create_run('보존', [ROSTER['claude']], min_independent=1)
        self.assertTrue(ctl.shutdown()); self.store.close()
        with sqlite3.connect(self.store.path) as db:
            db.execute('DROP TABLE work_templates'); db.execute('PRAGMA user_version = 14')
        reopened = Store(self.store.path)
        try:
            self.assertEqual(reopened.row('PRAGMA user_version')[0], SCHEMA_VERSION)
            self.assertEqual(reopened.row('SELECT question FROM runs WHERE run_id = ?', rid)['question'], '보존')
            self.assertEqual(reopened.row('SELECT cap FROM live_budget')['cap'], 3)
            self.assertEqual(len(list(self.store.path.parent.glob('*.v14-*.bak'))), 1)
        finally: reopened.close()

    def test_confirm_review_decision_search_and_memory_form_a_single_journey(self):
        ctl = self.controller(Reviewer())
        args = dict(min_independent=2, role_board=board('claude', 'codex'), roster=ROSTER)
        saved = ctl.templates.save('연결 확인', {**draft(), 'question': '연결 점검'}, ROSTER)
        question = ctl.templates.load(saved['template_id'])['draft']['question']
        preview = ctl.prepare_run(question, [ROSTER['claude'], ROSTER['codex']], **args)
        rid = ctl.create_run(question, [ROSTER['claude'], ROSTER['codex']], run_id=preview['run_id'],
                             confirmation=preview['confirmation'], **args)
        self.assertTrue(ctl.wait_idle())
        reviews = ctl.cross_review(rid); self.assertTrue(ctl.wait_idle())
        for key in reviews: ctl.set_review_disposition(key, 0, 'qualified')
        view = self.run_view(ctl, rid)
        ctl.mark_reviewed(rid, view['result_revision'], '연결점검-판단기록')
        self.assertEqual(ctl.search('연결점검-판단기록', kind='decision')['total'], 1)
        following = ctl.create_run('연결 점검 이어서', [ROSTER['claude']], min_independent=1,
            role_board={**board(), 'general': ['claude']}, roster=ROSTER, task_id=view['task_id'],
            assignments={'claude': {'task': '반례 보존', 'sources': []}})
        self.assertTrue(ctl.wait_idle())
        self.assertTrue(ctl.memory_sources(following)['entries'][0]['source_available'])
        self.assertIn('연결점검-판단기록', ctl._assignment(following, 'claude')['prompt'])
        self.assertEqual(len(ctl.activity(rid)['invocations']), 4)


class TemplateHTTP(HttpServerCase):
    def get(self, path, auth=True):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        try:
            conn.request('GET', path, headers={'Authorization': 'Bearer ' + self.token} if auth else {})
            response = conn.getresponse()
            return response.status, json.loads(response.read())
        finally: conn.close()

    def test_template_routes_keep_auth_and_recheck_current_models(self):
        self.assertEqual(self.get('/api/templates', False)[0], 401)
        status, raw, _ = self.request({'name': 'saved', 'draft': draft()}, path='/api/templates')
        self.assertEqual(status, 200, raw)
        saved = json.loads(raw); path = '/api/templates/' + saved['template_id']
        self.assertEqual(self.get(path, False)[0], 401)
        self.assertEqual(self.get(path)[0], 200)
        self.assertEqual(len(self.get('/api/templates')[1]['templates']), 1)
        bad = draft(); bad['models'] = {'claude': 'unlisted-model'}
        self.assertEqual(self.request({'name': 'bad', 'draft': bad}, path='/api/templates')[0], 400)
        current = {**ROSTER, 'claude': replace(ROSTER['claude'], model='different-default')}
        self.httpd.RequestHandlerClass = server.make_handler(self.ctl, self.token, self.port, participants=current)
        self.assertEqual(self.get(path)[0], 409)
        self.assertEqual(self.ctl.view()['runs'], [])
        self.assertEqual(self.request({'sha256': saved['sha256']}, path=path + '/delete')[0], 200)
        self.assertEqual(self.get(path)[0], 409)
