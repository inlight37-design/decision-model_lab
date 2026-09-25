#!/usr/bin/env python3
"""Offline, bounded characterization of review findings; never installs or calls a model.

Run from the repository root:
  python docs/reviews/2026-09-25-review/probe.py --root .
The setup Python functions are loaded by AST, not by importing their environment probe.
The shell script is copied into a TemporaryDirectory and all installation/auth/network
entry points are replaced with inert fixtures. These are boundary tests, not Windows,
WSL or end-to-end controller tests. A successful probe means the stated observation
was reproduced; it does not mean that the reviewed application is correct.
"""
from __future__ import annotations
import argparse
import ast
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import types
from typing import Callable, Mapping, Sequence

BASE = '2f76a1a6fdd6b4ca8edf5111460f7ae806c8977b'
EXPECTED = {
    'tools/setup/setup-wsl.sh': 'cde5228921fd44b1c16d73c3a18c1b1e9669b666',
    'tools/setup/check_setup.py': '40f14f97bcf3a48a6c6b5afdc6108e570b2fbc39',
}


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def load_boundaries(path: Path):
    names = {'Row', 'decode', 'first_line', 'observed_versions', 'tool_row', 'cli_row',
             'codex_login_row', 'claude_login_row', 'render', 'windows_rows'}
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    assert {n.name for n in nodes} == names
    module = types.ModuleType('setup_review_boundary')
    module.__dict__.update(dataclass=dataclasses.dataclass, json=json, Path=Path,
        Callable=Callable, Mapping=Mapping, Sequence=Sequence, Run=Callable, Which=Callable,
        OBSERVED=Path('/not-used-review-manifest.json'),
        CLAUDE_STORE=('Packages', 'Claude_pzs8sxrjxfjjc', 'LocalCache', 'Local'))
    sys.modules[module.__name__] = module
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), module.__dict__)
    return module


def fixture_program(path: Path, body: str):
    path.write_text('#!/bin/bash\nset -eu\n' + body + '\n', encoding='utf-8')
    path.chmod(0o700)


def shell_boundaries(root: Path):
    if not shutil.which('bash') or os.name == 'nt':
        return {'executed': False, 'reason': 'POSIX bash unavailable'}
    with tempfile.TemporaryDirectory(prefix='dml-review-') as raw:
        tmp = Path(raw)
        target = tmp / 'repo' / 'tools' / 'setup'
        target.mkdir(parents=True)
        script = target / 'setup-wsl.sh'
        shutil.copyfile(root / 'tools/setup/setup-wsl.sh', script)
        assert blob(script) == EXPECTED['tools/setup/setup-wsl.sh']
        tools = tmp / 'bin'; tools.mkdir()
        home = tmp / 'home'; home.mkdir()
        scratch = tmp / 'tmp'; scratch.mkdir()
        fixture_program(tools / 'dpkg', 'exit 0')
        fixture_program(tools / 'sudo', 'echo "UNEXPECTED sudo" >&2; exit 88')
        fixture_program(tools / 'codex', 'exit 1')
        fixture_program(tools / 'claude', 'exit 1')
        fixture_program(tools / 'python3', '''if [ "${2:-}" = --observed-versions ]; then
  if [ "$REVIEW_MODE" = missing ]; then echo 'fixture observation read failure' >&2; exit 7; fi
  printf 'codex 0.156.1\\nclaude-code 2.1.280\\n'
fi
exit 0''')
        fixture_program(tools / 'curl', '''[ "$1" = -fsSL ] && [ "$3" = -o ] || exit 89
printf '#!/bin/sh\\nprintf "inert-installer-%s\\\\n"\\n' "$REVIEW_VERSION" > "$4"''')
        env = {'PATH': f'{tools}:/usr/bin:/bin', 'HOME': str(home), 'TMPDIR': str(scratch),
               'LANG': 'C.UTF-8', 'REVIEW_MODE': 'missing', 'REVIEW_VERSION': 'A'}
        def call(args):
            p = subprocess.run(['/bin/bash', str(script), *args], env=env, cwd=tmp,
                               text=True, capture_output=True, timeout=10)
            return p.returncode, p.stdout, p.stderr
        code, out, err = call(['--check'])
        assert code == 0 and out.count('wants latest') == 2 and 'read failure' in err
        fallback = {'executed': True, 'mode': 'whole original shell script with inert command fixtures',
                    'observation_reader_exit': 7, 'script_exit': code,
                    'selection': [x for x in out.splitlines() if 'wants latest' in x]}
        env['REVIEW_MODE'] = 'versions'
        stop_code, _, _ = call([])
        files = list(scratch.iterdir())
        assert stop_code == 3 and len(files) == 1
        reviewed = files[0].read_bytes()
        assert b'inert-installer-A' in reviewed
        env['REVIEW_VERSION'] = 'B'
        accepted_code, accepted_out, _ = call(['--accept-installer-change'])
        assert accepted_code == 0 and accepted_out.count('inert-installer-B') == 2
        assert 'inert-installer-A' not in accepted_out
        approval = {'executed': True, 'initial_exit': stop_code,
                    'retained_reviewed_sha256': hashlib.sha256(reviewed).hexdigest(),
                    'reviewed_fixture': 'A', 'executed_fixture': 'B',
                    'accepted_script_exit': accepted_code,
                    'note': 'B only prints a marker; no actual installer or network request was executed'}
        return {'missing_pin_fallback': fallback, 'approval_not_bound_to_reviewed_bytes': approval}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path('.'))
    args = ap.parse_args()
    root = args.root.resolve()
    sources = {name: blob(root / name) for name in EXPECTED}
    if sources != EXPECTED:
        raise SystemExit('Reviewed source changed. Re-review before characterizing another version.')
    cs = load_boundaries(root / 'tools/setup/check_setup.py')
    results = {'reviewed_commit': BASE, 'source_blobs': sources,
               'environment': {'python': platform.python_version(), 'system': platform.system(),
                               'scope': 'ChatGPT isolated web container; not user PC'},
               'extra_model_calls': 0}
    which = lambda name: '/fixture/' + name
    api_status = {'loggedIn': True, 'authMethod': 'api_key', 'apiProvider': 'firstParty'}
    api_rows = [cs.codex_login_row(lambda _: (0, 'Logged in using an API key'), which),
                cs.claude_login_row(lambda _: (0, json.dumps(api_status)), which)]
    text, code = cs.render(api_rows, 'isolated auth rows')
    assert code == 0 and all(row.status == 'warn' for row in api_rows)
    results['api_auth_not_a_required_failure'] = {'exit': code, 'row_statuses': [r.status for r in api_rows],
                                                  'summary': text.splitlines()[-1],
                                                  'scope': 'other required rows omitted; assume they are ok'}
    subscription_status = dict(api_status, authMethod='claude.ai')
    row = cs.claude_login_row(lambda _: (1, json.dumps(subscription_status)), which)
    assert row.status == 'ok'
    results['claude_failed_status_accepted'] = {'command_exit': 1, 'status': row.status}
    row = cs.cli_row(lambda _: (0, 'codex-cli 0.156.10'), which, 'codex', 'codex', 'Codex CLI', '0.156.1')
    assert row.status == 'ok'
    results['version_substring_collision'] = {'recorded': '0.156.1', 'installed': '0.156.10', 'status': row.status}
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / 'missing.json'
        assert cs.observed_versions(path) == {}
        path.write_text('[]', encoding='utf-8')
        try:
            cs.observed_versions(path)
        except AttributeError:
            results['malformed_observation_record'] = {'missing': {}, 'root_array': 'AttributeError'}
        else:
            raise AssertionError('expected characterization changed')
    lone = json.loads('"\\ud800"')
    try:
        lone.encode('utf-8')
    except UnicodeEncodeError:
        results['surrogate_utf8_boundary'] = 'UnicodeEncodeError after valid JSON escape was decoded'
    else:
        raise AssertionError('expected UnicodeEncodeError')
    db = sqlite3.connect(':memory:')
    try:
        db.execute('SELECT ?', (json.dumps({'detail': lone}, ensure_ascii=False),))
    except UnicodeEncodeError:
        results['surrogate_metadata_sqlite_boundary'] = 'UnicodeEncodeError for JSON metadata too; draft text alone is not enough'
    finally:
        db.close()
    paired = json.loads('"\\ud83d\\ude00"')
    assert paired.encode('utf-8') == b'\xf0\x9f\x98\x80'
    assert r'\ud800'.encode('utf-8') == b'\\ud800'
    results['unicode_positive_controls'] = ['valid supplementary character encodes', 'literal six-character escape encodes']
    results['shell'] = shell_boundaries(root)
    results['not_executed'] = ['PowerShell/winget/WSL install', 'real auth/CLI calls',
                               'full repository tests', 'end-to-end controller #70 reproduction']
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
