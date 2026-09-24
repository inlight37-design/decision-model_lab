import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, required=True,
                    help='Existing or new directory outside the repository for summaries and raw diagnostics')
args = parser.parse_args()
TASK = args.output_dir.expanduser().resolve()
if TASK == REPO or REPO in TASK.parents:
    parser.error('--output-dir must be outside the repository')
TASK.mkdir(parents=True, exist_ok=True)
from core import adapters, isolation

exe = os.path.realpath(adapters.resolve('codex', dict(os.environ)))
release = os.path.dirname(os.path.dirname(exe))
rows = []
raw_dir = TASK / 'c3-synthetic-raw'
raw_dir.mkdir(exist_ok=True)

def walk(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)

with tempfile.TemporaryDirectory(prefix='dml-c3-prompt-') as root:
    home = Path(root, 'home')
    cfg = home / '.codex'
    work = Path(root, 'work')
    cfg.mkdir(parents=True)
    work.mkdir()
    box = isolation.Sandbox(work_dir=str(work), home=str(home), read_only=(release,),
                            read_write=(str(cfg),), env={'LANG':'C.UTF-8','CODEX_HOME':str(cfg)})

    version_result = isolation.run(['/usr/bin/unshare','--user','--map-root-user','--net','--',exe,'--version'], box, timeout=20)
    if version_result.exit_code != 0 or not version_result.tree_confirmed_empty:
        raise RuntimeError('isolated CLI version check did not complete')
    version = version_result.stdout.strip()
    def run(name, tail):
        result = isolation.run(['/usr/bin/unshare', '--user', '--map-root-user', '--net', '--', exe, *tail],
                               box, timeout=25, max_output_bytes=500000)
        (raw_dir / (name+'.json')).write_text(json.dumps({'stdout':result.stdout,'stderr':result.stderr}),encoding='utf-8')
        row = {'name':name,'state':result.state,'exit':result.exit_code,
               'tree_confirmed_empty':result.tree_confirmed_empty,
               'stdout_bytes':len(result.stdout.encode()),'stdout_sha256':hashlib.sha256(result.stdout.encode()).hexdigest(),
               'stderr_lines':len(result.stderr.splitlines())}
        try:
            parsed = json.loads(result.stdout)
        except ValueError:
            row['json']=False
            row['selected_error_lines']=[line.replace(str(home),'<synthetic-home>') for line in result.stderr.splitlines()
                                         if any(s in line.lower() for s in ('error:','unexpected','usage:','failed to'))][:6]
        else:
            row['json']=True
            row['top_type']=type(parsed).__name__
            row['top_keys']=sorted(parsed) if isinstance(parsed,dict) else []
            row['top_length']=len(parsed) if isinstance(parsed,(dict,list)) else None
            row['message_roles']=[v.get('role') for v in walk(parsed) if 'role' in v]
            row['types']=sorted({str(v.get('type')) for v in walk(parsed) if 'type' in v})
            row['has_tools_field']=any('tools' in v for v in walk(parsed))
            row['markers']={s:s in result.stdout for s in ['C3_PROJECT_SENTINEL','C3_HOME_SENTINEL','C3_USER_SENTINEL',
                                                          'C3_SKILL_DESCRIPTION','C3_SKILL_BODY','C3_MCP_INSTRUCTIONS','c3_probe_tool']}
        rows.append(row)
    base=['-c','model="gpt-6-luna"','debug','prompt-input','C3_USER_SENTINEL']
    run('empty-home',base)
    (work/'AGENTS.md').write_text('C3_PROJECT_SENTINEL\n',encoding='utf-8')
    (cfg/'AGENTS.md').write_text('C3_HOME_SENTINEL\n',encoding='utf-8')
    run('agents-markers',base)
    run('ignore-option',['debug','prompt-input','--ignore-user-config','C3_USER_SENTINEL'])
    run('mcp-list',['mcp','list','--json'])
    skill = work / '.agents' / 'skills' / 'c3-probe'
    skill.mkdir(parents=True)
    (skill/'SKILL.md').write_text('---\nname: c3-probe\ndescription: C3_SKILL_DESCRIPTION\n---\nC3_SKILL_BODY\n',encoding='utf-8')
    server = work / 'c3_stdio.py'
    server.write_text('''import json, sys
from pathlib import Path
for line in sys.stdin:
    msg = json.loads(line)
    method = msg.get("method")
    with Path("c3-methods.jsonl").open("a") as f:
        f.write(json.dumps({"method":method})+"\\n")
    if "id" not in msg:
        continue
    if method == "initialize":
        result = {"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"c3-synthetic","version":"1"},"instructions":"C3_MCP_INSTRUCTIONS"}
    elif method == "tools/list":
        result = {"tools":[{"name":"c3_probe_tool","description":"Synthetic diagnostic tool only","inputSchema":{"type":"object","properties":{}}}]}
    else:
        result = {}
    print(json.dumps({"jsonrpc":"2.0","id":msg["id"],"result":result}),flush=True)
''',encoding='utf-8')
    (cfg/'config.toml').write_text('[mcp_servers.c3_synthetic]\ncommand = "/usr/bin/python3"\nargs = ['+json.dumps(str(server))+']\n',encoding='utf-8')
    run('skill-mcp-markers',base)
    methods=work/'c3-methods.jsonl'
    rows[-1]['mcp_server_started']=methods.exists()
    rows[-1]['mcp_methods']=[json.loads(line)['method'] for line in methods.read_text().splitlines()] if methods.exists() else []

report={'cli':version,'home':'synthetic only','network':'nested user+network namespace; no egress',
        'real_auth_mounted':False,'model_calls':0,'cases':rows}
(TASK/'c3-prompt-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))

