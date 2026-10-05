"""Summary/detail equivalence, all search categories, and bounded public reads."""
import copy
import json
from unittest.mock import patch

from app import controller as c
from app.queries import catalog
import test_app_controller as support
import test_revisions as revisions
from tools.benchmark_queries import seed


def expected_tasks(view):
    tasks = copy.deepcopy(view['tasks'])
    for task in tasks:
        task['role_config'].pop('memory', None)
        for run in task['runs']:
            run['role_config'].pop('memory', None)
    return tasks


class QueryProjections(support.Base):
    def assert_summary(self, ctl, rid):
        full = ctl.view()
        before = self.store._db.total_changes
        overview = ctl.queries.overview(rid)
        self.assertEqual(overview['tasks'], expected_tasks(full))
        self.assertEqual(overview['runs'], [r for r in full['runs'] if r['run_id'] == rid])
        for key in ('live_call_budget', 'provider_call_budgets', 'slots', 'unsettled', 'paused', 'refinements', 'splits'):
            self.assertEqual(overview[key], full[key], key)
        self.assertEqual(self.store._db.total_changes, before)
        self.assertEqual(ctl.queries.overview()['runs'], [])

    def test_summary_stays_equivalent_through_review_revision_and_recheck(self):
        ctl = self.controller(revisions.RevisionExecutor())
        rid = revisions.Revisions.reviewed(self, ctl)
        self.assert_summary(ctl, rid)
        first = revisions.Revisions.revise(self, ctl, rid)
        ctl.revisions.recheck(first, 'codex')
        self.assertTrue(ctl.wait_idle(support.SLOW_RUNNER_TIMEOUT))
        self.assert_summary(ctl, rid)
        ctl.mark_reviewed(rid, ctl.view(rid)['runs'][0]['result_revision'], '판단 보류')
        self.assert_summary(ctl, rid)
        snapshot = ctl.view()
        for query in ('수정', '답', '반례', '판단', rid, 'notes.txt'):
            for kind in (None, 'question', 'answer', 'review', 'decision', 'synthesis', 'source'):
                with self.subTest(query=query, kind=kind):
                    self.assertEqual(ctl.search(query, kind=kind, limit=1),
                                     catalog.search(snapshot, query, kind=kind, limit=1))

    def test_summary_preserves_sealing_paused_unknown_and_synthesis_usage(self):
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        rid = ctl.create_run('공개 질문', [support.manual('a'), support.manual('b')],
                             min_independent=1, quorum_policy=c.INCLUDE_UNVERIFIED)
        sha = ctl.view(rid)['runs'][0]['input_sha256']
        ctl.submit_manual(rid, 'a', 'SECRET-ANSWER', sha)
        self.assert_summary(ctl, rid)
        self.assertNotIn('SECRET-ANSWER', json.dumps(ctl.queries.overview(rid)))
        ctl.submit_manual(rid, 'b', '두 번째 답', sha)
        for state in ('unknown', 'failed', 'completed'):
            with self.store.tx() as tx:
                tx.event(rid, 'synthesis_started', attempt=state)
                tx.event(rid, 'synthesis_completed' if state == 'completed' else 'synthesis_failed', attempt=state,
                         result={'status': state, 'synthesizer': {'adapter_id': 'codex', 'started': True,
                                 'tree_confirmed_empty': state != 'unknown', 'usage': {'input_tokens': 32}}})
            self.assert_summary(ctl, rid)
        queued = ctl.create_run('대기 질문', [support.cli('c')], min_independent=1)
        ctl.paused = True
        self.assert_summary(ctl, queued)

    def test_overview_does_not_read_answers_or_source_contents_and_task_filter_is_early(self):
        seed(self.store, 100)
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        sql = []
        self.store._db.set_trace_callback(sql.append)
        try:
            overview = ctl.queries.overview()
        finally:
            self.store._db.set_trace_callback(None)
        self.assertEqual(overview['tasks'], expected_tasks(ctl.view()))
        self.assertFalse(any('FROM drafts' in s or 'FROM sources' in s or 'FROM assignments' in s for s in sql))
        self.assertNotIn('needle', json.dumps(overview))
        original = ctl.queries.view
        with patch.object(ctl.queries, 'view', wraps=original) as spy:
            self.assertEqual(ctl.search('needle', task_id='t-000000')['total'], 10)
            self.assertEqual(spy.call_count, 10)
        with patch.object(ctl.queries, 'view', side_effect=AssertionError('no detail needed')):
            self.assertEqual(ctl.search('질문', kind='question')['total'], 100)
            self.assertEqual(ctl.search('source.txt', kind='source')['total'], 100)
            with self.assertRaises(c.ControllerError):
                ctl.search('')

