"""Evaluate fixed synthetic recall cases, without models, network or real ledgers."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import memory
from app.domain import ParticipantSpec
from app.store import Store

CASES = ROOT / 'tests/fixtures/memory_cases.json'


def seed_case(store, case):
    spec = asdict(ParticipantSpec('a', '합성 기록', 'test', 'manual'))
    with store.tx() as tx:
        tx.execute("INSERT INTO tasks VALUES ('task', '평가 작업', 0)")
        at = 0
        for history in case['history']:
            for index in range(history.get('repeat', 1)):
                at += 1
                rid = history['id'] if history.get('repeat', 1) == 1 else f"{history['id']}-{index}"
                question = history['question'] + ' 검토 맥락' * history.get('question_padding', 0)
                tx.execute('INSERT INTO runs (run_id, created_at, question, prompt, input_sha256, input_bytes, '
                           'min_independent, roster, quorum_policy, phase, task_id, role_config) '
                           "VALUES (?, ?, ?, '', '', 0, 1, '{}', 'include_unverified', ?, 'task', '{}')",
                           rid, at, question, history.get('phase', 'revealed'))
                if history.get('cancelled'):
                    tx.execute('UPDATE runs SET cancel_requested = 1 WHERE run_id = ?', rid)
                tx.execute("INSERT INTO participants (run_id, pid, spec, state) VALUES (?, 'a', ?, 'accepted')",
                           rid, json.dumps(spec))
                answer = history.get('answer', '합성 답 · 사실 검증 안 함') * history.get('answer_repeat', 1) + history.get('answer_suffix', '')
                tx.execute("INSERT INTO drafts VALUES (?, 'a', ?, ?, 'manual', ?)", rid, answer,
                           'bad' if history.get('corrupt') else hashlib.sha256(answer.encode()).hexdigest(), at)
                if history.get('memo'):
                    tx.event(rid, 'human_reviewed', memo=history['memo'] + ' 판단 맥락' * history.get('memo_padding', 0))
                if history.get('findings'):
                    findings = [{'target': 'D1', 'kind': 'risk', 'quote': '합성 근거',
                                 'detail': text + (' 세부 관측' * history.get('first_finding_padding', 0) if i == 0 else '')}
                                for i, text in enumerate(history['findings'])]
                    tx.execute('INSERT INTO reviews (review_id, run_id, seq, created_at, question, reviewer, labels, '
                               'targets, prompt, input_sha256, state, result) '
                               "VALUES (?, ?, 0, ?, '평가', ?, '{}', '{}', '', '', 'accepted', ?)",
                               'review-' + rid, rid, at, json.dumps(spec), json.dumps({'reply': {'findings': findings}}))


def evaluate(case):
    with tempfile.TemporaryDirectory(prefix='dml-memory-eval-') as directory:
        store = Store(Path(directory) / 'journal.db')
        try:
            seed_case(store, case)
            started = time.perf_counter()
            pack = memory.select(store, 'task', case['query'])
            elapsed = (time.perf_counter() - started) * 1000
            text = '\n'.join(entry['excerpt'] for entry in pack['entries'])
            chosen = [entry['run_id'] for entry in pack['entries']]
            missing_runs = [rid for rid in case['required_runs'] if rid not in chosen]
            missing_text = [item for item in case.get('required_text', []) if item not in text]
            forbidden = [item for item in case.get('forbidden_text', []) if item in text]
            forbidden += [rid for rid in case.get('forbidden_runs', []) if rid in chosen]
            size = len(memory.footer(pack).encode())
            relevant = set(case.get('relevant_runs', case['required_runs']))
            hits = relevant.intersection(chosen)
            unrelated = [rid for rid in chosen if rid not in relevant] if 'relevant_runs' in case else []
            too_many = len(unrelated) > case.get('max_unrelated', len(unrelated))
            return {'id': case['id'], 'known_limit': case.get('known_limit', False), 'selected': chosen,
                    'missing_runs': missing_runs, 'missing_text': missing_text, 'forbidden': forbidden,
                    'appendix_bytes': size, 'within_cap': size <= memory.MAX_BYTES,
                    'passed': not (missing_runs or missing_text or forbidden or too_many) and size <= memory.MAX_BYTES,
                    'retrieval': {'relevant': len(relevant), 'selected': len(chosen), 'hits': len(hits),
                                  'precision': len(hits) / len(chosen) if chosen else None,
                                  'recall': len(hits) / len(relevant) if relevant else None,
                                  'unrelated': unrelated,
                                  'recent_fallbacks': sum(e.get('selection', {}).get('recent_fallback', False) for e in pack['entries'])}
                                 if 'relevant_runs' in case else None,
                    'elapsed_ms': round(elapsed, 3),
                    'selection_scope': pack.get('selection_scope'),
                    'omissions': {e['run_id']: e.get('omissions') for e in pack['entries']}}
        finally:
            store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail for supported cases; report known limits separately')
    parser.add_argument('--cases', type=Path, default=CASES)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding='utf-8'))['cases']
    results = [evaluate(case) for case in cases]
    print(json.dumps({'schema': 'decision-memory-evaluation/1', 'model_calls': 0,
                      'cases_sha256': hashlib.sha256(args.cases.read_bytes()).hexdigest(), 'results': results}, ensure_ascii=False, indent=2))
    if args.check and any(not r['passed'] for r in results if not r['known_limit']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
