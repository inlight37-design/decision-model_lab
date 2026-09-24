"""Stdlib-only runtime inventory and synthetic view benchmark; never starts an executor."""
import argparse
import ast
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    root = args.repo.resolve()
    sys.path.insert(0, str(root))
    from app.controller import Controller, MockExecutor, ParticipantSpec, MANUAL, INCLUDE_UNVERIFIED
    from app.store import Store

    files = sorted([*root.glob('app/*.py'), *root.glob('core/*.py')])
    local = {'.'.join(p.relative_to(root).with_suffix('').parts).removesuffix('.__init__') for p in files}
    metrics = {'runtime_python_files': len(files),
               'runtime_python_lines': sum(len(p.read_text(encoding='utf-8').splitlines()) for p in files),
               'runtime_dependencies': {}}
    for path in files:
        dependencies = set()
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Import):
                dependencies.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                dependencies.add(node.module)
                dependencies.update(f'{node.module}.{alias.name}' for alias in node.names)
        name = '.'.join(path.relative_to(root).with_suffix('').parts)
        metrics['runtime_dependencies'][name] = sorted(dependencies & local)
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / 'journal.db')
        try:
            ctl = Controller(store, MockExecutor(), max_parallel=0)
            rid = ctl.create_run('synthetic benchmark question',
                                 [ParticipantSpec('app', 'App', 'test', MANUAL)],
                                 min_independent=1, quorum_policy=INCLUDE_UNVERIFIED)
            with store.tx() as tx:
                for _ in range(3000):
                    tx.event(rid, 'synthetic_trace', detail='x' * 2048)
            times = []
            for _ in range(21):
                before = time.perf_counter()
                view = ctl.view()
                times.append((time.perf_counter() - before) * 1000)
            metrics['view_3000_events'] = {
                'median_ms': statistics.median(times[1:]), 'min_ms': min(times[1:]),
                'samples': 20, 'event_payload_bytes': 2048,
                'returned_events': len(view['runs'][0]['events'])}
        finally:
            store.close()
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
