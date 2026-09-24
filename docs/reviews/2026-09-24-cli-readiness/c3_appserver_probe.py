"""Synthetic, no-model app-server inventory probe. No actual account state is mounted."""
import collections
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

MCP = r'''import json, sys
from pathlib import Path
for line in sys.stdin:
    msg=json.loads(line)
    method=msg.get("method")
    with Path(__file__).with_name("mcp-methods.jsonl").open("a") as f:
        f.write(json.dumps({"method":method})+"\n")
    if "id" not in msg:
        continue
    if method=="initialize":
        result={"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"c3-synthetic","version":"1"},"instructions":"C3_MCP_INSTRUCTIONS"}
    elif method=="tools/list":
        result={"tools":[{"name":"c3_probe_tool","description":"C3_TOOL_DESCRIPTION","inputSchema":{"type":"object","properties":{}}}]}
    elif method=="resources/list":
        result={"resources":[]}
    elif method=="resources/templates/list":
        result={"resourceTemplates":[]}
    else:
        result={}
    print(json.dumps({"jsonrpc":"2.0","id":msg["id"],"result":result}),flush=True)
'''

CLIENT = r'''import json, os, selectors, subprocess, sys, time
from pathlib import Path
work=Path.cwd()
trace=[]
notifications=[]
responses=[]
buf=b""
err=(work/"app-stderr.txt").open("wb")
p=subprocess.Popen([sys.argv[1],"app-server","--stdio"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err)
sel=selectors.DefaultSelector()
sel.register(p.stdout,selectors.EVENT_READ)
def request(method,params,ident):
    global buf
    trace.append(method)
    p.stdin.write((json.dumps({"method":method,"params":params,"id":ident})+"\n").encode())
    p.stdin.flush()
    until=time.monotonic()+20
    while time.monotonic()<until:
        while b"\n" in buf:
            line,buf=buf.split(b"\n",1)
            if not line.strip():
                continue
            try:
                msg=json.loads(line)
            except ValueError:
                continue
            if msg.get("id")==ident:
                responses.append({"method":method,"response":msg})
                return msg
            notifications.append(msg.get("method","response_other"))
        ready=sel.select(max(0,until-time.monotonic()))
        if not ready:
            break
        data=os.read(p.stdout.fileno(),65536)
        if not data:
            break
        buf+=data
    responses.append({"method":method,"timeout_or_eof":True})
    return None
try:
    init=request("initialize",{"clientInfo":{"name":"dml_c3_synthetic","version":"1"},"capabilities":{"experimentalApi":True}},0)
    if init and "result" in init:
        trace.append("initialized")
        p.stdin.write(b'{"method":"initialized","params":{}}\n')
        p.stdin.flush()
        request("skills/list",{"cwds":[str(work)],"forceReload":True},1)
        request("mcpServerStatus/list",{"detail":"toolsAndAuthOnly","limit":20},2)
        request("app/installed",{"forceRefresh":False},3)
finally:
    p.stdin.close()
    try:
        p.wait(timeout=3)
        ending="eof"
    except subprocess.TimeoutExpired:
        p.terminate()
        try:
            p.wait(timeout=3)
            ending="terminated"
        except subprocess.TimeoutExpired:
            p.kill();p.wait(timeout=3);ending="killed"
    err.close()
    (work/"app-responses.json").write_text(json.dumps({"trace":trace,"responses":responses,"notifications":notifications,"ending":ending,"exit":p.returncode}),encoding="utf-8")
    print(json.dumps({"response_count":len(responses),"ending":ending,"exit":p.returncode}))
'''

exe=os.path.realpath(adapters.resolve('codex',dict(os.environ)))
raw_dir=TASK/'c3-appserver-synthetic-raw'
raw_dir.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='dml-c3-appserver-') as root:
    home=Path(root,'home'); cfg=home/'.codex'; work=Path(root,'work')
    cfg.mkdir(parents=True); work.mkdir()
    skill=work/'.agents'/'skills'/'c3-probe';skill.mkdir(parents=True)
    (skill/'SKILL.md').write_text('---\nname: c3-probe\ndescription: C3_SKILL_DESCRIPTION\n---\nC3_SKILL_BODY\n',encoding='utf-8')
    server=work/'c3_stdio.py';server.write_text(MCP,encoding='utf-8')
    client=work/'client.py';client.write_text(CLIENT,encoding='utf-8')
    (cfg/'config.toml').write_text('[mcp_servers.c3_synthetic]\ncommand="/usr/bin/python3"\nargs=['+json.dumps(str(server))+']\n',encoding='utf-8')
    box=isolation.Sandbox(work_dir=str(work),home=str(home),read_only=(str(Path(exe).parent.parent),),
                          read_write=(str(cfg),),env={'LANG':'C.UTF-8','CODEX_HOME':str(cfg)})

    version_result = isolation.run(['/usr/bin/unshare','--user','--map-root-user','--net','--',exe,'--version'], box, timeout=20)
    if version_result.exit_code != 0 or not version_result.tree_confirmed_empty:
        raise RuntimeError('isolated CLI version check did not complete')
    version = version_result.stdout.strip()
    result=isolation.run(['/usr/bin/unshare','--user','--map-root-user','--net','--','/usr/bin/python3',str(client),exe],
                         box,timeout=90,max_output_bytes=50000)
    report={'cli':version,'home':'synthetic only','network':'nested user+network namespace; no egress',
            'real_auth_mounted':False,'model_calls':0,'thread_started':False,'outer_state':result.state,
            'outer_exit':result.exit_code,'tree_confirmed_empty':result.tree_confirmed_empty,
            'supported_schema_methods':['skills/list','mcpServerStatus/list','app/installed'],
            'methods':[]}
    for name in ['app-responses.json','app-stderr.txt','mcp-methods.jsonl']:
        src=work/name
        if src.exists():
            (raw_dir/name).write_bytes(src.read_bytes())
    response_file=work/'app-responses.json'
    if response_file.exists():
        raw=json.loads(response_file.read_text())
        report.update(request_trace=raw['trace'],notification_methods=raw['notifications'],
                      app_server_shutdown=raw['ending'],app_server_exit=raw['exit'])
        for row in raw['responses']:
            m=row['method'];response=row.get('response',{})
            rendered=json.dumps(response,sort_keys=True)
            summary={'method':m,'timeout_or_eof':row.get('timeout_or_eof',False),
                     'success':'result' in response,'response_keys':sorted(response),
                     'response_sha256':hashlib.sha256(rendered.encode()).hexdigest()}
            if 'error' in response:
                summary['error_code']=response['error'].get('code')
                summary['error_message']=response['error'].get('message','').replace(str(root),'<synthetic-root>')
            answer=response.get('result',{})
            if m=='skills/list':
                entries=answer.get('data',[])
                skills=[s for e in entries for s in e.get('skills',[])]
                summary.update(entry_count=len(entries),skill_count=len(skills),
                               error_count=sum(len(e.get('errors',[])) for e in entries),
                               scope_counts=dict(collections.Counter(s.get('scope') for s in skills)),
                               synthetic_skill_present=any(s.get('name')=='c3-probe' for s in skills),
                               description_marker_present='C3_SKILL_DESCRIPTION' in rendered,
                               body_marker_present='C3_SKILL_BODY' in rendered)
            elif m=='mcpServerStatus/list':
                entries=answer.get('data',[])
                summary.update(server_count=len(entries),tools_count=sum(len(e.get('tools',{})) for e in entries),
                               synthetic_tool_present='c3_probe_tool' in rendered,
                               tool_schema_present=any('inputSchema' in t for e in entries for t in e.get('tools',{}).values()),
                               instructions_marker_present='C3_MCP_INSTRUCTIONS' in rendered,
                               tool_errors=sum(bool(e.get('toolsError')) for e in entries),
                               next_cursor_present=bool(answer.get('nextCursor')),
                               runtime_statuses=[e.get('runtimeStatus') for e in entries])
            elif m=='app/installed':
                summary['result_keys']=sorted(answer)
                summary['array_lengths']={k:len(v) for k,v in answer.items() if isinstance(v,list)}
            report['methods'].append(summary)
    methods=work/'mcp-methods.jsonl'
    report['mcp_methods']=[json.loads(line)['method'] for line in methods.read_text().splitlines()] if methods.exists() else []
    report['app_stderr_lines']=len((work/'app-stderr.txt').read_text().splitlines()) if (work/'app-stderr.txt').exists() else None
    (TASK/'c3-appserver-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

