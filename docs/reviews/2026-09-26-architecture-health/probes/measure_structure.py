"""Read-only structural inventory. Counts describe shape, not a quality score."""
import ast
import json
from pathlib import Path
import subprocess
import sys

repo = Path(sys.argv[1]).resolve()
dest = Path(sys.argv[2]).resolve()
files = []
edges = []
for folder in ('app', 'core'):
    for p in sorted((repo / folder).glob('*.py')):
        source = p.read_text(encoding='utf-8')
        tree = ast.parse(source)
        funcs = []
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs.append({'name': n.name, 'line': n.lineno, 'lines': n.end_lineno - n.lineno + 1})
            if isinstance(n, ast.ImportFrom) and not n.level and n.module:
                target = n.module
                if target in ('app', 'core'):
                    for a in n.names:
                        if (repo / target / (a.name + '.py')).exists():
                            edges.append([p.relative_to(repo).with_suffix('').as_posix().replace('/', '.'), target + '.' + a.name])
                elif target.startswith(('app.', 'core.')):
                    edges.append([p.relative_to(repo).with_suffix('').as_posix().replace('/', '.'), target])
        files.append({'path': p.relative_to(repo).as_posix(), 'lines': len(source.splitlines()),
                      'functions': len(funcs), 'largest_functions': sorted(funcs, key=lambda x: -x['lines'])[:3]})
result = {'source_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
          'scope': 'app/core top-level Python modules; AST imports include function-local imports. No dynamic reachability proof.',
          'files': sorted(files, key=lambda x: -x['lines']), 'internal_import_edges': sorted(set(map(tuple, edges))),
          'static_ui': [{'path': str(p.relative_to(repo)).replace('\\', '/'), 'lines': len(p.read_text(encoding='utf-8').splitlines())}
                        for p in (repo/'app/static/index.html', repo/'app/static/role-board.js')]}
dest.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'largest_files': result['files'][:8], 'static_ui': result['static_ui']}, ensure_ascii=False, indent=2))
