"""Repeatable synthetic-ledger query costs; no model, real ledger or network access.

Run from the repository root: python tools/benchmark_queries.py --runs 100 1000
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.controller import Controller
from app.domain import ParticipantSpec
from app.store import Store


class NoCalls:
    name = 'benchmark-no-calls'
    adapter_ids = ()


def seed(store, count):
    """Public manual answers plus sources, grouped in tasks. Nothing is executed."""
    spec = asdict(ParticipantSpec('manual', '수동 답', 'test', 'manual'))
    roles = json.dumps(dict(source='board', input_mode='original', supervisor=None,
                           orchestrator=None, general=[], isolated=[spec]))
    answer = '합성 원장 공개 답변. 검색 기준 needle. 반례와 미해결은 원문을 확인한다. ' * 160
    data = ('자료 본문 ' * 2000).encode()
    with store.tx() as tx:
        for i in range(count):
            task, rid = f't-{i // 10:06}', f'r-{i:06}'
            tx.execute('INSERT OR IGNORE INTO tasks VALUES (?, ?, ?)', task, '합성 작업 ' + task, i // 10)
            tx.execute('INSERT INTO runs (run_id, created_at, question, prompt, input_sha256, input_bytes, '
                       'min_independent, roster, quorum_policy, phase, task_id, role_config) '
                       "VALUES (?, ?, ?, ?, ?, ?, 1, '{}', 'include_unverified', 'revealed', ?, ?)",
                       rid, i, '질문 ' + rid, '입력 ' * 1000, 'a' * 64, 7000, task, roles)
            tx.execute("INSERT INTO participants (run_id, pid, spec, state) VALUES (?, 'manual', ?, 'accepted')",
                       rid, json.dumps(spec))
            tx.execute("INSERT INTO drafts VALUES (?, 'manual', ?, ?, 'manual', ?)",
                       rid, answer, hashlib.sha256(answer.encode()).hexdigest(), i)
            tx.execute("INSERT INTO sources VALUES (?, 'source.txt', ?, ?, ?)",
                       rid, hashlib.sha256(data).hexdigest(), len(data), data)
            tx.event(rid, 'revealed')


def measure(store, function, repeats):
    elapsed = []
    for _ in range(repeats):
        start = time.perf_counter()
        value = function()
        encoded = json.dumps(value, ensure_ascii=False).encode()
        elapsed.append((time.perf_counter() - start) * 1000)
    statements = []
    store._db.set_trace_callback(statements.append)
    tracemalloc.start()
    try:
        value = function()
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
        store._db.set_trace_callback(None)
    return dict(median_ms=round(statistics.median(elapsed), 2), peak_bytes=peak,
                response_bytes=len(encoded), statements=len(statements))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', nargs='+', type=int, default=[100, 1000])
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1 or any(n < 1 or n > 10000 for n in args.runs):
        parser.error('runs must be 1..10000 and repeats positive')
    results = []
    for count in args.runs:
        with tempfile.TemporaryDirectory(prefix='dml-query-bench-') as directory:
            store = Store(Path(directory) / 'journal.db')
            ctl = None
            try:
                seed(store, count)
                ctl = Controller(store, NoCalls(), max_parallel=0)
                functions = {'full_snapshot': ctl.view,
                             'one_detail': lambda: ctl.view('r-000000'),
                             'search_all': lambda: ctl.search('needle'),
                             'search_task': lambda: ctl.search('needle', task_id='t-000000'),
                             'search_question': lambda: ctl.search('질문', kind='question')}
                if hasattr(ctl.queries, 'overview'):
                    functions['overview'] = ctl.queries.overview
                results.append(dict(runs=count, measurements={
                    name: measure(store, function, args.repeats) for name, function in functions.items()}))
            finally:
                if ctl is not None:
                    ctl.shutdown()
                store.close()
    print(json.dumps({'scope': 'synthetic cloud ledger; no model calls', 'results': results}, indent=2))


if __name__ == '__main__':
    main()
