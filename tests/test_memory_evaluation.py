"""Fixed retrieval cases, recorded limits and balanced bounded evidence excerpts."""
import json
import unittest
from app import memory
from tools.evaluate_memory import CASES, evaluate, seed_case
import test_app_controller as support


class Evaluation(unittest.TestCase):
    def test_supported_cases_and_explicit_limits(self):
        for case in json.loads(CASES.read_text(encoding='utf-8'))['cases']:
            with self.subTest(case=case['id']):
                result = evaluate(case)
                self.assertTrue(result['within_cap'])
                self.assertFalse(result['forbidden'])
                if not case.get('known_limit'):
                    self.assertTrue(result['passed'], result)
                if case['id'] == 'older-than-window':
                    self.assertEqual(result['selection_scope']['older_runs_not_considered'], 0)
                    self.assertIn('wanted', result['selected'])

    def test_additional_labelled_cases_report_precision_recall_and_known_limits(self):
        path = CASES.with_name('memory_expanded_cases.json')
        for case in json.loads(path.read_text(encoding='utf-8'))['cases']:
            with self.subTest(case=case['id']):
                result = evaluate(case)
                self.assertTrue(result['within_cap'])
                self.assertFalse(result['forbidden'])
                self.assertEqual(result['retrieval']['hits'], len(set(result['selected']) & set(case['relevant_runs'])))
                if not case.get('known_limit'):
                    self.assertTrue(result['passed'], result)

    def test_bounded_excerpts_share_room_across_findings_and_report_every_cut(self):
        sections = {'question': ['긴 질문' * 3000], 'judgment': ['메모' * 2000],
                    'reviews': ['첫 반례' * 2000, '끝나지 않았다 · 반드시 보존'],
                    'revisions': ['수정 대응' * 2000], 'answers': ['답' * 3000]}
        excerpt, omissions = memory._excerpt(sections)
        self.assertLessEqual(len(excerpt.encode()), memory.EXCERPT_BYTES)
        self.assertIn('끝나지 않았다', excerpt)
        self.assertTrue(all(v['included_bytes'] > 0 and v['omitted_bytes'] > 0 for v in omissions.values()))
        self.assertTrue(all(v['source_bytes'] == v['included_bytes'] + v['omitted_bytes'] for v in omissions.values()))


class FrozenEvidence(support.Base):
    def test_query_cap_and_answer_matching_preserve_scope_and_frozen_hash(self):
        case = {'query': 'needle', 'history': [{'id': 'wanted', 'question': '이전 기록', 'answer': 'needle 근거'}],
                'required_runs': ['wanted']}
        seed_case(self.store, case)
        pack = memory.select(self.store, 'task', case['query'])
        self.assertEqual(pack['entries'][0]['selection']['matched_fields'], ['answers'])
        before = memory.footer(pack)
        with self.store.tx() as tx:
            tx.execute("INSERT INTO tasks VALUES ('other', '다른 작업', 2)")
            tx.execute("UPDATE runs SET task_id = 'other' WHERE run_id = 'wanted'")
        self.assertEqual(memory.select(self.store, 'task', case['query'])['entries'], [])
        self.assertEqual(memory.footer(pack), before)
        bounded = memory.select(self.store, 'other', ' '.join('keyword' + str(i) for i in range(100)))
        self.assertEqual(bounded['selection_scope']['query_terms_omitted'], 100 - memory.QUERY_TERMS)
        self.assertLessEqual(len(memory.footer(bounded).encode()), memory.MAX_BYTES)

    def test_selection_and_omissions_are_hash_bound_and_no_legacy_pack_is_rewritten(self):
        case = next(c for c in json.loads(CASES.read_text(encoding='utf-8'))['cases'] if c['id'] == 'finding-only')
        seed_case(self.store, case)
        pack = memory.select(self.store, 'task', case['query'])
        entry = next(e for e in pack['entries'] if e['run_id'] == 'wanted')
        self.assertIn('reviews', entry['selection']['matched_fields'])
        self.assertEqual(entry['review_sources'][0]['id'], 'review-wanted')
        self.assertTrue(memory.footer(pack))
        entry['omissions']['reviews']['omitted_bytes'] += 1
        with self.assertRaises(ValueError): memory.footer(pack)
        # The reader still accepts a v1 pack with no new policy/scope/omission fields.
        legacy = memory.empty(task_id='task')
        body = {k: v for k, v in legacy.items() if k != 'sha256'}
        body['entries'] = [{'run_id': 'old', 'excerpt': '옛 고정 발췌'}]
        frozen = {**body, 'sha256': memory.digest(memory.encoded(body))}
        before = json.dumps(frozen)
        self.assertIn('옛 고정 발췌', memory.footer(frozen))
        self.assertEqual(json.dumps(frozen), before)

    def test_new_source_hash_covers_evidence_even_when_excerpt_is_cut(self):
        case = next(c for c in json.loads(CASES.read_text(encoding='utf-8'))['cases'] if c['id'] == 'long-question-memo')
        seed_case(self.store, case)
        before = memory.select(self.store, 'task', case['query'])['entries'][0]
        with self.store.tx() as tx:
            tx.event('wanted', 'human_reviewed', memo='긴 메모' * 3000 + '맨 끝 변경')
        after = memory.select(self.store, 'task', case['query'])['entries'][0]
        self.assertNotEqual(before['source_sha256'], after['source_sha256'])
        self.assertTrue(after['omissions']['judgment']['omitted_bytes'])
        self.assertIn('COUNTER-AFTER-LONG-MEMO', after['excerpt'])
