"""Plan/dependency admission, stale edits, immutable runs and read-only action inbox."""
import json
import sqlite3
from unittest.mock import patch

from app import controller as c
from app.store import Store, SCHEMA_VERSION
import test_app_controller as support
import test_app_integrity as http
import test_refine_mode as refining
import test_split_proposal as splitting


def plan(title='계획', depends_on=(), revision=0):
    return dict(title=title, goal='근거를 비교한다', done_when='반례와 미해결을 읽고 판단한다',
                depends_on=list(depends_on), revision=revision)


class Workflow(support.Base):
    def task(self, ctl, task_id):
        return next(t for t in ctl.queries.overview()['tasks'] if t['task_id'] == task_id)

    def begin(self, ctl, task_id, **kwargs):
        return ctl.create_run('검토 질문', [support.manual('a')], min_independent=1,
                              quorum_policy=c.INCLUDE_UNVERIFIED, task_id=task_id, **kwargs)

    def complete(self, ctl, run_id):
        run = ctl.view(run_id)['runs'][0]
        ctl.submit_manual(run_id, 'a', '검토할 공개 답', run['input_sha256'])
        ctl.mark_reviewed(run_id, ctl.view(run_id)['runs'][0]['result_revision'], '판단 완료 · 사실 검증은 아님')

    def test_planned_tasks_block_until_prerequisites_have_current_human_judgments(self):
        ex = support.SyntheticExecutor(); ctl = self.controller(ex)
        before = self.store._db.total_changes
        first = ctl.tasks.save(plan('자료 검토'))
        second = ctl.tasks.save(plan('결정', [first['task_id']]))
        self.assertEqual(self.task(ctl, first['task_id'])['status'], 'my_turn')
        self.assertEqual(self.task(ctl, second['task_id'])['status'], 'blocked')
        self.assertTrue(self.store._db.total_changes > before)
        changes = self.store._db.total_changes
        self.assertEqual(ctl.queries.overview()['runs'], [])
        self.assertEqual(self.store._db.total_changes, changes)
        with self.assertRaisesRegex(c.ControllerError, '선행 작업'):
            self.begin(ctl, second['task_id'])
        self.assertEqual(self.store.rows('SELECT * FROM runs'), [])
        rid = self.begin(ctl, first['task_id'])
        self.assertEqual(self.task(ctl, second['task_id'])['status'], 'blocked')
        self.complete(ctl, rid)
        self.assertTrue(self.task(ctl, second['task_id'])['readiness']['dependencies_met'])
        downstream = self.begin(ctl, second['task_id'])
        fixed = ctl.view(downstream)['runs'][0]['role_config']['task_plan']
        self.assertEqual(fixed['revision'], 1)
        self.assertEqual(fixed['dependency_evidence'][0]['evidence'][0]['run_id'], rid)
        self.assertEqual(ex.started, [])

    def test_cycles_missing_ids_invalid_shapes_and_stale_edit_are_atomic(self):
        ctl = self.controller(support.SyntheticExecutor())
        a = ctl.tasks.save(plan('A')); b = ctl.tasks.save(plan('B', [a['task_id']]))
        for payload, target in [(plan('cycle', [b['task_id']], 1), a['task_id']),
                                (plan('self', [a['task_id']], 1), a['task_id']),
                                (plan('missing', ['not-here']), None),
                                (plan('duplicate', [a['task_id'], a['task_id']]), None),
                                (plan('stale', revision=0), a['task_id']),
                                ({**plan(), 'revision': True}, None),
                                ({**plan(), 'goal': ''}, None)]:
            before = self.store._db.total_changes
            with self.subTest(payload=payload), self.assertRaises(c.ControllerError):
                ctl.tasks.save(payload, task_id=target)
            self.assertEqual(self.store._db.total_changes, before)
        self.assertEqual(self.task(ctl, a['task_id'])['title'], 'A')

    def test_plan_change_reopens_completion_but_does_not_rewrite_old_input(self):
        ctl = self.controller(support.SyntheticExecutor())
        a = ctl.tasks.save(plan('A')); b = ctl.tasks.save(plan('B', [a['task_id']]))
        rid = self.begin(ctl, a['task_id'])
        before = ctl.view(rid)['runs'][0]['role_config']
        with self.assertRaisesRegex(c.ControllerError, '진행 중'):
            ctl.tasks.save(plan('변경', revision=1), task_id=a['task_id'])
        self.complete(ctl, rid)
        ctl.tasks.save(plan('새 기준', revision=1), task_id=a['task_id'])
        self.assertEqual(ctl.view(rid)['runs'][0]['role_config'], before)
        self.assertFalse(self.task(ctl, a['task_id'])['readiness']['plan_fresh'])
        self.assertEqual(self.task(ctl, b['task_id'])['status'], 'blocked')
        self.complete(ctl, self.begin(ctl, a['task_id']))
        self.assertTrue(self.task(ctl, b['task_id'])['readiness']['dependencies_met'])

    def test_stale_preview_and_transaction_gap_cannot_admit_changed_plan(self):
        ctl = self.controller(support.SyntheticExecutor())
        a = ctl.tasks.save(plan())
        args = dict(min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED, task_id=a['task_id'])
        preview = ctl.prepare_run('q', [support.manual('a')], **args)
        ctl.tasks.save(plan('변경', revision=1), task_id=a['task_id'])
        with self.assertRaisesRegex(c.ControllerError, '다시 확인'):
            ctl.create_run('q', [support.manual('a')], run_id=preview['run_id'], confirmation=preview['confirmation'], **args)
        original = ctl.inputs.prepare_run
        def changed_between_prepare_and_write(*arguments, **keywords):
            value = original(*arguments, **keywords)
            ctl.tasks.save(plan('거래 직전 변경', revision=2), task_id=a['task_id'])
            return value
        with patch.object(ctl.inputs, 'prepare_run', side_effect=changed_between_prepare_and_write):
            with self.assertRaisesRegex(c.ControllerError, '다시 확인'):
                ctl.create_run('q', [support.manual('a')], **args)
        self.assertFalse(self.store.rows('SELECT * FROM runs'))

    def test_new_prerequisite_run_blocks_next_admission_and_keeps_existing_frozen_evidence(self):
        ctl = self.controller(support.SyntheticExecutor())
        a = ctl.tasks.save(plan('A')); b = ctl.tasks.save(plan('B', [a['task_id']]))
        self.complete(ctl, self.begin(ctl, a['task_id']))
        rid = self.begin(ctl, b['task_id']); fixed = ctl.view(rid)['runs'][0]['role_config']['task_plan']
        self.complete(ctl, rid)
        pending = self.begin(ctl, a['task_id'])
        with self.assertRaises(c.ControllerError): self.begin(ctl, b['task_id'])
        self.assertEqual(ctl.view(rid)['runs'][0]['role_config']['task_plan'], fixed)
        ctl.cancel_run(pending)
        with self.assertRaises(c.ControllerError): self.begin(ctl, b['task_id'])
        # A deliberate new plan can recover from settled cancellation. Old input,
        # cancellation and judgments remain in history; unknown calls cannot use this.
        ctl.tasks.save(plan('A 새 판', revision=1), task_id=a['task_id'])
        self.complete(ctl, self.begin(ctl, a['task_id']))
        self.assertTrue(self.task(ctl, b['task_id'])['readiness']['dependencies_met'])

    def test_unknown_work_and_sealed_text_have_only_public_inbox_actions(self):
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        a = ctl.tasks.save(plan())
        rid = ctl.create_run('봉인 질문', [support.manual('a'), support.manual('b')],
                             min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED, task_id=a['task_id'])
        ctl.submit_manual(rid, 'a', 'SECRET-CONTENT', ctl.view(rid)['runs'][0]['input_sha256'])
        value = ctl.queries.overview()
        self.assertNotIn('SECRET-CONTENT', json.dumps(value))
        self.assertTrue(any(x['run_id'] == rid and x['action'] == '원본 앱 답 붙여넣기' for x in value['inbox']))
        with self.store.tx() as tx:
            tx.execute("UPDATE participants SET state = 'unknown' WHERE run_id = ? AND pid = 'b'", rid)
        self.assertEqual(self.task(ctl, a['task_id'])['status'], 'problem')
        with self.assertRaises(c.ControllerError): ctl.tasks.save(plan(revision=1), task_id=a['task_id'])

    def test_schema16_backup_and_restart_preserve_legacy_history_and_new_plans(self):
        ctl = self.controller(support.SyntheticExecutor())
        rid = self.begin(ctl, None); self.complete(ctl, rid)
        original = ctl.view(rid)['runs'][0]
        ctl.shutdown(); self.store.close()
        path = self.tmp / 'store' / 'journal.db'
        with sqlite3.connect(path) as db:
            db.executescript('DROP TABLE task_plans; PRAGMA user_version = 16;')
        self.store = Store(path); self.addCleanup(self.store.close)
        self.assertTrue(list(path.parent.glob('journal.db.v16-*.bak')))
        self.assertEqual(self.store.row('PRAGMA user_version')[0], SCHEMA_VERSION)
        new = self.controller(support.SyntheticExecutor())
        self.assertEqual(new.view(rid)['runs'][0], original)
        saved = new.tasks.save(plan()); new.shutdown(); self.store.close()
        self.store = Store(path); self.addCleanup(self.store.close)
        resumed = self.controller(support.SyntheticExecutor())
        self.assertEqual(self.task(resumed, saved['task_id'])['plan'], saved)
        self.assertEqual(resumed.executor.started, [])

    def test_planning_calls_cannot_bypass_dependencies_and_unattached_unknown_has_an_action(self):
        ex = refining.Refiner(outcomes={'supervisor': 'unknown'})
        ctl = self.controller(ex)
        a = ctl.tasks.save(plan('A')); b = ctl.tasks.save(plan('B', [a['task_id']]))
        with self.assertRaisesRegex(c.ControllerError, '선행 작업'):
            ctl.refine(refining.ROSTER['claude'], '계획 질문', task_id=b['task_id'])
        with self.assertRaisesRegex(c.ControllerError, '선행 작업'):
            ctl.propose_split('분담 질문', refining.ROSTER['claude'], [refining.ROSTER['codex']], task_id=b['task_id'])
        self.assertEqual(ex.started, [])
        self.complete(ctl, self.begin(ctl, a['task_id']))
        self.assertTrue(self.task(ctl, b['task_id'])['readiness']['dependencies_met'])
        key = ctl.refine(refining.ROSTER['claude'], '계획 질문', task_id=a['task_id'])
        self.assertTrue(ctl.wait_idle())
        entries = ctl.queries.overview()['inbox']
        self.assertTrue(any(e.get('refine_id') == key and e['kind'] == 'refine_unknown' for e in entries))
        self.assertTrue(any(e['code'] == 'unsettled' for e in ctl.queries.overview()['admission']['reasons']))
        self.assertEqual(self.task(ctl, a['task_id'])['status'], 'problem')
        with self.assertRaisesRegex(c.ControllerError, '선행 작업'):
            self.begin(ctl, b['task_id'])
        with self.assertRaises(c.ControllerError):
            ctl.tasks.save(plan(revision=1), task_id=a['task_id'])
        ctl.acknowledge_refine_unknown(key, 1)
        self.assertFalse(any(e.get('refine_id') == key for e in ctl.queries.overview()['inbox']))
        self.assertTrue(self.task(ctl, b['task_id'])['readiness']['dependencies_met'])
        self.assertEqual(len(ex.started), 1)
        ctl.tasks.save(plan(revision=1), task_id=a['task_id'])

    def test_unattached_running_and_unknown_split_reopens_prerequisite_until_confirmed(self):
        ex = splitting.Splitter(outcomes={'supervisor': 'unknown'}, hold=['supervisor'])
        ctl = self.controller(ex)
        a = ctl.tasks.save(plan('A')); b = ctl.tasks.save(plan('B', [a['task_id']]))
        self.complete(ctl, self.begin(ctl, a['task_id']))
        try:
            key = ctl.propose_split('분담 질문', refining.ROSTER['claude'], [refining.ROSTER['codex']], task_id=a['task_id'])
            self.assertTrue(support.wait_for(lambda: bool(ex.started)))
            self.assertEqual(self.task(ctl, a['task_id'])['status'], 'working')
            with self.assertRaisesRegex(c.ControllerError, '선행 작업'):
                self.begin(ctl, b['task_id'])
            with self.assertRaises(c.ControllerError):
                ctl.tasks.save(plan(revision=1), task_id=a['task_id'])
        finally:
            ex.release('supervisor')
        self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.task(ctl, a['task_id'])['status'], 'problem')
        self.assertFalse(self.task(ctl, b['task_id'])['readiness']['dependencies_met'])
        self.assertTrue(any(e.get('split_id') == key for e in ctl.queries.overview()['inbox']))
        ctl.acknowledge_split_unknown(key)
        self.assertTrue(self.task(ctl, b['task_id'])['readiness']['dependencies_met'])
        self.assertEqual(len(ex.started), 1)


class WorkflowHttp(http.HttpServerCase):
    def test_plan_posts_use_existing_auth_and_reject_stale_revision(self):
        payload = plan()
        self.assertEqual(self.request(payload, headers={'Authorization': 'Bearer wrong'}, path='/api/tasks')[0], 401)
        status, body, _ = self.request(payload, path='/api/tasks')
        self.assertEqual(status, 200)
        task = json.loads(body)
        target = '/api/tasks/' + task['task_id'] + '/plan'
        self.assertEqual(self.request(payload, path=target)[0], 400)
        self.assertEqual(self.request(plan('변경', revision=1), path=target)[0], 200)
