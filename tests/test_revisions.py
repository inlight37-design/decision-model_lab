"""Revision journeys, stale confirmation, immutable answers and common call lifecycle. No models."""
import copy
from dataclasses import replace
import json
import http.client
import sqlite3

from app import controller as c, fake_cli, memory, revisions as fmt
from app.report import revision_report, ReportError
from app.store import Store, SCHEMA_VERSION
from core import adapters, contract, runner
from test_app_controller import Base, claude_stdout, wait_for, SLOW_RUNNER_TIMEOUT
from test_cross_review import Reviewer, ROSTER, board
from test_app_integrity import HttpServerCase
from app.server import make_handler


class RevisionExecutor(Reviewer):
    def __init__(self, results=(), **kw):
        super().__init__(**kw)
        self.results = list(results)
        self.inputs = []

    def plan(self, spec, prompt, work_dir, *, inputs=()):
        self.inputs.append((spec.pid, inputs))
        plan = super().plan(spec, prompt, work_dir, inputs=inputs)
        return replace(plan, kind=self.kind)

    def execute(self, spec, prompt, work_dir, timeout, *, cancel=None):
        if not prompt.startswith((fmt.MARKER, fmt.CHECK_MARKER)):
            return super().execute(spec, prompt, work_dir, timeout, cancel=cancel)
        self.started.append(spec.pid)
        if spec.pid in self.gates:
            self.gates[spec.pid].wait(10)
        outcome = self.results.pop(0) if self.results else 'ok'
        text = 'malformed answer' if outcome == 'badjson' else fake_cli.revision_reply(prompt)
        result = runner.RunResult(('synthetic',), runner.EXITED, 1 if outcome == 'fail' else 0,
            claude_stdout(text, error=outcome == 'fail'), '', False, False, 5, 0, True,
            containment=runner.PROCESS_GROUP if outcome == 'unknown' else runner.JOB_OBJECT,
            input_delivery=runner.INPUT_COMPLETE)
        return result, adapters.interpret('claude-code', result, requested_model='m')


class RealLike(RevisionExecutor):
    kind = contract.REAL


class Revisions(Base):
    def reviewed(self, ctl):
        rid = ctl.create_run('수정 연결', [ROSTER['claude'], ROSTER['codex']], min_independent=2,
            role_board=board('claude', 'codex'), roster=ROSTER, sources=[('notes.txt', '남겨야 할 반례')])
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        ctl.cross_review(rid); self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        return rid

    def revise(self, ctl, rid):
        p = ctl.revisions.prepare(rid, 'claude')
        key = ctl.revisions.revise(rid, 'claude', p['revision_id'], p['confirmation'])
        self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        return key

    def test_two_revisions_recheck_search_memory_export_and_original_quorum(self):
        ex = RevisionExecutor(); ctl = self.controller(ex)
        rid = self.reviewed(ctl); before = self.run_view(ctl, rid)
        ctl.mark_reviewed(rid, before['result_revision'], '기존 판단')
        first = self.revise(ctl, rid)
        after = self.run_view(ctl, rid)
        self.assertFalse(after['reviewed'])
        self.assertEqual(after['quorum'], before['quorum'])
        self.assertEqual(after['participants'], before['participants'])
        self.assertEqual(after['answer_revisions'][0]['snapshot']['findings'][0]['disposition'], 'unresolved')
        self.assertTrue(next(i for pid, i in ex.inputs if pid == 'revision-author'))
        with self.assertRaises(c.ControllerError): ctl.revisions.prepare(rid, 'claude')
        with self.assertRaises(c.ControllerError): ctl.revisions.recheck(first, 'claude')
        check = ctl.revisions.recheck(first, 'codex'); self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        second = self.revise(ctl, rid)
        after = self.run_view(ctl, rid)
        self.assertEqual(after['answer_revisions'][1]['parent_id'], first)
        self.assertEqual(after['answer_revisions'][1]['snapshot']['prior_checks'][0]['check_id'], check)
        self.assertEqual(ctl.view()['tasks'][0]['calls_used'], 7)
        self.assertEqual(sum(x['calls'] for x in after['usage']['by_provider'].values()), 7)
        self.assertEqual([x['purpose'] for x in ctl.activity(rid)['invocations']][-3:],
                         ['answer_revision', 'answer_revision', 'revision_recheck'])
        with self.assertRaises(c.ControllerError): ctl.revisions.prepare(rid, 'claude')
        self.assertEqual(ctl.search('조건과 반례는 미해결', kind='answer')['total'], 2)
        report = revision_report(ctl.view(), rid)
        self.assertEqual(report['schema'], 'decision-revision-history/1')
        self.assertEqual(report['revisions'][1]['revision_id'], second)
        pack = memory.select(self.store, after['task_id'], '수정 연결')
        self.assertEqual([v['id'] for v in pack['entries'][0]['revision_sources']], [first, second])
        self.assertTrue(memory.footer(pack))
        stale = copy.deepcopy(ctl.view()); stale['runs'][0]['answer_revisions'][0]['reply']['answer'] = 'corrupt'
        with self.assertRaises(ReportError): revision_report(stale, rid)

    def test_memory_marks_which_result_a_past_judgment_saw(self):
        # CR-02: a judgment stays in memory but never reads as a judgment of a newer result.
        ctl = self.controller(RealLike(results=['ok', 'unknown']), max_real_calls=7)
        rid = self.reviewed(ctl); task = self.run_view(ctl, rid)['task_id']
        def recall():
            entry = memory.select(self.store, task, '수정 연결')['entries'][0]
            self.assertEqual(entry['source_format'], 'canonical-public-context-v3')
            return entry['result_state'], entry['excerpt']
        state, excerpt = recall()
        self.assertEqual((state['judgment_revision'], state['judgment_is_current']), (None, False))
        self.assertIn('판단 기록 없음', excerpt)
        judged = self.run_view(ctl, rid)['result_revision']
        ctl.mark_reviewed(rid, judged, 'OLD-JUDGMENT')
        state, excerpt = recall()
        self.assertEqual(state, {'result_revision': judged, 'judgment_revision': judged,
                                 'judgment_is_current': True, 'dispositions_changed_after_judgment': False})
        self.assertIn(f'현재 결과 판 {judged}을 판단함): OLD-JUDGMENT', excerpt)
        review = self.store.row("SELECT review_id FROM reviews WHERE run_id = ? AND state = 'accepted' ORDER BY seq", rid)['review_id']
        ctl.set_review_disposition(review, 0, 'rejected')
        state, excerpt = recall()
        self.assertTrue(state['judgment_is_current'] and state['dispositions_changed_after_judgment'])
        self.assertIn('판단 뒤 교차검토 지적의 처분이 바뀌었다', excerpt)
        first = self.revise(ctl, rid)
        view = self.run_view(ctl, rid)
        self.assertFalse(view['reviewed'])
        state, excerpt = recall()
        self.assertEqual((state['result_revision'], state['judgment_revision'], state['judgment_is_current']),
                         (view['result_revision'], judged, False))
        self.assertIn(f'이전 결과 판 {judged}에 대한 사람의 판단', excerpt)
        self.assertIn('OLD-JUDGMENT', excerpt)                   # kept, never deleted
        self.assertNotIn('을 판단함)', excerpt)
        ctl.mark_reviewed(rid, view['result_revision'], 'NEW-JUDGMENT')
        self.assertTrue(recall()[0]['judgment_is_current'])
        check = ctl.revisions.recheck(first, 'codex'); self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        self.assertEqual(self.store.row('SELECT state FROM revision_checks WHERE check_id = ?', check)['state'], c.UNKNOWN)
        ctl.revisions.acknowledge(check, recheck=True)
        state, excerpt = recall()
        self.assertFalse(state['judgment_is_current'])           # an unknown result is a new result too
        self.assertFalse(self.run_view(ctl, rid)['reviewed'])
        self.assertIn('NEW-JUDGMENT', excerpt)
        # An old ledger's judgment carried no revision; the event order still says what it saw.
        seen = state['judgment_revision']
        with self.store.tx() as tx:
            tx.execute("UPDATE events SET payload = json_remove(payload, '$.revision') "
                       "WHERE run_id = ? AND kind = 'human_reviewed'", rid)
        self.assertEqual(recall()[0]['judgment_revision'], seen)

    def test_preview_is_free_and_stale_disposition_rejects_without_starting(self):
        ex = RevisionExecutor(); ctl = self.controller(ex)
        rid = self.reviewed(ctl); n = len(ex.started)
        p = ctl.revisions.prepare(rid, 'claude')
        self.assertEqual(len(ex.started), n)
        key, index = p['snapshot']['findings'][0]['id'].rsplit(':', 1)
        ctl.set_review_disposition(key, int(index), 'qualified')
        with self.assertRaises(c.ControllerError): ctl.revisions.revise(rid, 'claude', p['revision_id'], p['confirmation'])
        self.assertEqual(len(ex.started), n)
        key = self.revise(ctl, rid)
        with self.assertRaises(c.ControllerError): ctl.revisions.revise(rid, 'claude', key, p['confirmation'])
        self.assertEqual(len(ex.started), n + 1)

    def test_failure_and_unknown_never_replace_original_or_refund(self):
        for outcome in ('badjson', 'unknown'):
            with self.subTest(outcome=outcome):
                ctl = self.controller(RealLike(results=[outcome]), max_real_calls=6)
                rid = self.reviewed(ctl); before = self.run_view(ctl, rid)['participants']
                key = self.revise(ctl, rid); v = self.run_view(ctl, rid)['answer_revisions'][0]
                self.assertEqual(v['state'], c.UNKNOWN if outcome == 'unknown' else c.REJECTED)
                self.assertEqual(self.run_view(ctl, rid)['participants'], before)
                self.assertEqual(ctl.call_budget()['used'], 5)
                if outcome == 'unknown':
                    with self.assertRaises(c.ControllerError): ctl.revisions.prepare(rid, 'claude')
                    with self.assertRaises(c.ControllerError): ctl.mark_reviewed(rid, self.run_view(ctl, rid)['result_revision'])
                    ctl.revisions.acknowledge(key)
                    self.assertEqual(ctl.unsettled(), 0)
                    self.assertEqual(ctl.call_budget()['used'], 5)
                else:
                    self.assertEqual(v['raw']['text'], 'malformed answer')
                self.revise(ctl, rid)
                with self.assertRaises(c.ControllerError): ctl.revisions.prepare(rid, 'claude')
                self.assertEqual(ctl.call_budget()['used'], 6)
                self.assertTrue(ctl.shutdown())
                # Each subcase owns a separate persisted budget.
                if outcome == 'badjson':
                    self.store.close(); self.store = Store(self.tmp / 'unknown' / 'journal.db'); self.addCleanup(self.store.close)

    def test_live_cap_refuses_recheck_without_row_or_extra_reservation(self):
        ctl = self.controller(RealLike(), max_real_calls=5)
        rid = self.reviewed(ctl); key = self.revise(ctl, rid)
        with self.assertRaises(c.ControllerError): ctl.revisions.recheck(key, 'codex')
        self.assertEqual(self.store.rows('SELECT * FROM revision_checks'), [])
        self.assertEqual(ctl.call_budget()['used'], 5)

    def test_active_revision_blocks_human_completion_and_restart_never_replays(self):
        ex = RevisionExecutor(hold=['revision-author']); ctl = self.controller(ex)
        rid = self.reviewed(ctl); p = ctl.revisions.prepare(rid, 'claude')
        key = ctl.revisions.revise(rid, 'claude', p['revision_id'], p['confirmation'])
        self.assertTrue(wait_for(lambda: 'revision-author' in ex.started))
        self.assertEqual(ctl.view()['tasks'][0]['status'], 'working')
        with self.assertRaises(c.ControllerError): ctl.mark_reviewed(rid, self.run_view(ctl, rid)['result_revision'])
        ex.release('revision-author'); self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT)); self.assertTrue(ctl.shutdown())
        with self.store.tx() as tx:
            tx.execute("UPDATE answer_revisions SET state = 'running', result = NULL WHERE revision_id = ?", key)
        fresh = RevisionExecutor(); new = self.controller(fresh)
        self.assertEqual(self.run_view(new, rid)['answer_revisions'][0]['state'], c.UNKNOWN)
        self.assertEqual(new.unsettled(), 1); self.assertEqual(fresh.started, [])
        new.revisions.acknowledge(key); self.assertEqual(new.unsettled(), 0)

    def test_sealed_or_no_review_cannot_prepare_or_export(self):
        ctl = self.controller(RevisionExecutor(), max_parallel=0)
        rid = ctl.create_run('봉인', [ROSTER['claude']], min_independent=1)
        with self.assertRaises(c.ControllerError): ctl.revisions.prepare(rid, 'claude')
        with self.assertRaises(ReportError): revision_report(ctl.view(), rid)
        self.assertNotIn('answer_revisions', self.run_view(ctl, rid))

    def test_recheck_limit_failed_recheck_and_response_validation(self):
        ctl = self.controller(RevisionExecutor(results=['ok', 'badjson', 'ok']))
        rid = self.reviewed(ctl); key = self.revise(ctl, rid)
        ctl.revisions.recheck(key, 'codex'); self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        with self.assertRaises(c.ControllerError): ctl.revisions.prepare(rid, 'claude')
        ctl.revisions.recheck(key, 'codex'); self.assertTrue(ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        with self.assertRaises(c.ControllerError): ctl.revisions.recheck(key, 'codex')
        self.assertEqual(len(ctl.revisions.prepare(rid, 'claude')['snapshot']['prior_checks']), 1)
        snapshot = {'findings': [{'id': 'id'}]}
        for responses in ([], [{'finding': 'wrong', 'status': 'addressed', 'detail': 'x'}],
                          [{'finding': 'id', 'status': 'supported', 'detail': 'x'}]):
            with self.assertRaises(ValueError): fmt.check(json.dumps({'answer': 'a', 'responses': responses}), snapshot)
        valid = {'assessments': [{'finding': 'id', 'status': 'uncertain', 'detail': 'd'}],
                 'findings': [{'target': 'D1', 'quote': 'absent', 'kind': 'error', 'detail': 'd'}]}
        self.assertEqual(fmt.check_recheck(json.dumps(valid), snapshot, 'answer')['findings'][0]['source_check'], 'not_found')

    def test_schema15_migration_preserves_template_and_budget_with_backup(self):
        ctl = self.controller(RevisionExecutor(), max_parallel=0, max_real_calls=9)
        from test_templates import draft
        saved = ctl.templates.save('기존 설정', draft(), ROSTER)
        self.assertTrue(ctl.shutdown()); self.store.close()
        with sqlite3.connect(self.store.path) as db:
            db.execute('DROP TABLE answer_revisions'); db.execute('DROP TABLE revision_checks'); db.execute('PRAGMA user_version = 15')
        reopened = Store(self.store.path)
        try:
            self.assertEqual(reopened.row('PRAGMA user_version')[0], SCHEMA_VERSION)
            self.assertEqual(reopened.row('SELECT sha256 FROM work_templates WHERE template_id = ?', saved['template_id'])[0], saved['sha256'])
            self.assertEqual(reopened.row('SELECT cap FROM live_budget')[0], 9)
            self.assertEqual(len(list(self.store.path.parent.glob('*.v15-*.bak'))), 1)
        finally: reopened.close()


class RevisionHTTP(HttpServerCase):
    def test_preview_confirm_recheck_export_are_authenticated_and_complete(self):
        self.assertTrue(self.ctl.shutdown())
        self.ctl = c.Controller(self.store, RevisionExecutor(), work_root=str(self.store.path.parent / 'work'))
        self.addCleanup(self.ctl.shutdown)
        self.httpd.RequestHandlerClass = make_handler(self.ctl, self.token, self.port)
        rid = self.ctl.create_run('HTTP 수정', [ROSTER['claude'], ROSTER['codex']], min_independent=2)
        self.assertTrue(self.ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        self.ctl.cross_review(rid); self.assertTrue(self.ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        preview_path = f'/api/runs/{rid}/revisions/preview'
        self.assertEqual(self.request({'pid': 'claude'}, {'Authorization': 'Bearer invalid'}, preview_path)[0], 401)
        status, raw, _ = self.request({'pid': 'claude'}, path=preview_path)
        self.assertEqual(status, 200, raw); p = json.loads(raw)
        body = {k: p[k] for k in ('pid', 'revision_id', 'confirmation')}
        status, raw, _ = self.request(body, path=f'/api/runs/{rid}/revisions')
        self.assertEqual(status, 200, raw); self.assertTrue(self.ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        status, raw, _ = self.request({'reviewer_pid': 'codex'}, path=f"/api/revisions/{p['revision_id']}/recheck")
        self.assertEqual(status, 200, raw); self.assertTrue(self.ctl.wait_idle(SLOW_RUNNER_TIMEOUT))
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        try:
            conn.request('GET', f'/api/runs/{rid}/revision-report', headers={'Authorization': 'Bearer ' + self.token})
            response = conn.getresponse(); self.assertEqual(response.status, 200)
            self.assertEqual(len(json.loads(response.read())['revisions'][0]['rechecks']), 1)
        finally: conn.close()
