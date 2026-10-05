"""Dated audit reproducer using temporary SQLite and synthetic test executors.

No native provider process, account, user journal, or model is accessed. The
revision search case intentionally changes synthetic fixture content with a
matching digest; it tests recall selection, not the full revision acceptance.
Outputs record baseline behavior and are not regression pass criteria.
"""
import sys
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from test_cross_review import CrossReviewTests, Reviewer
from test_collate import CollateTests, Collator
from test_revisions import Revisions, RevisionExecutor, ROSTER, board
from app import memory
from app.report import build_report, ReportError


def review_corruption():
    test = CrossReviewTests()
    test.setUp()
    try:
        ex = Reviewer()
        ctl = test.controller(ex)
        rid = test.revealed(ctl)
        with test.store.tx() as tx:
            tx.execute('UPDATE drafts SET text = ? WHERE run_id = ? AND pid = ?',
                       'CORRUPTED-CONTENT', rid, 'codex')
        keys = ctl.cross_review(rid)
        assert ctl.wait_idle()
        reviews = test.round(ctl, rid)['reviews']
        rejected_report = False
        try:
            build_report(ctl.view(rid), rid)
        except ReportError:
            rejected_report = True
        return {'review_count': len(keys), 'states': [r['state'] for r in reviews],
                'corrupt_text_in_review_prompt': 'CORRUPTED-CONTENT' in reviews[0]['prompt'],
                'target_reported_fresh': reviews[0]['targets']['D1']['fresh'],
                'draft_report_rejected': rejected_report}
    finally:
        test.doCleanups()


def collate_corruption():
    test = CollateTests()
    test.setUp()
    try:
        ex = Collator()
        ctl = test.controller(ex)
        rid = test.collected(ctl)
        with test.store.tx() as tx:
            tx.execute('UPDATE drafts SET text = ? WHERE run_id = ? AND pid = ?',
                       'CORRUPTED-CONTENT', rid, 'codex')
        ctl.collate(rid)
        assert ctl.wait_idle()
        row = test.collations(ctl, rid)[0]
        return {'state': row['state'],
                'corrupt_text_in_collation_prompt': 'CORRUPTED-CONTENT' in ex.prompts['supervisor'][0]}
    finally:
        test.doCleanups()


def memory_revision():
    test = Revisions()
    test.setUp()
    try:
        ctl = test.controller(RevisionExecutor())
        rid = test.reviewed(ctl)
        view = test.run_view(ctl, rid)
        ctl.mark_reviewed(rid, view['result_revision'], 'OLD-JUDGMENT')
        rev = test.revise(ctl, rid)
        view = test.run_view(ctl, rid)
        task = view['task_id']
        pack = memory.select(test.store, task, '수정 연결')
        stale = {'public_view_reviewed': view['reviewed'],
                 'old_memo_in_new_memory': 'OLD-JUDGMENT' in pack['entries'][0]['excerpt'],
                 'memory_entry_fields': sorted(pack['entries'][0])}
        # Synthetic fixture content: make the new fact exist only in a revision,
        # with an internally valid digest, then add later unrelated public runs.
        row = test.store.row('SELECT result FROM answer_revisions WHERE revision_id = ?', rev)
        result = json.loads(row['result'])
        result['reply']['answer'] = 'quartzneedle is the corrected conclusion'
        result['reply']['sha256'] = memory.digest(result['reply']['answer'].encode('utf-8'))
        with test.store.tx() as tx:
            tx.execute('UPDATE answer_revisions SET result = ? WHERE revision_id = ?', json.dumps(result), rev)
        for i in range(4):
            ctl.create_run('unrelated-topic-' + str(i), [ROSTER['claude'], ROSTER['codex']],
                           min_independent=2, task_id=task, use_memory=False,
                           role_board=board('claude', 'codex'), roster=ROSTER)
            assert ctl.wait_idle()
        recalled = memory.select(test.store, task, 'quartzneedle')
        return {'stale_judgment': stale,
                'revision_only_term': {'matched_runs': recalled['selection_scope']['matched_runs'],
                    'corrected_run_selected': any(e['run_id'] == rid for e in recalled['entries']),
                    'selection_was_recent_fallback': all(e['selection']['recent_fallback'] for e in recalled['entries'])}}
    finally:
        test.doCleanups()


if __name__ == '__main__':
    print(json.dumps({'actual_model_calls': 0, 'review_corruption': review_corruption(),
                      'collate_corruption': collate_corruption(),
                      'memory_revision': memory_revision()}, ensure_ascii=False, indent=2))
