"""Synthetic SQLite fixtures only. No CLI/provider/server/UI is started."""
from pathlib import Path
import collections
import hashlib
import json
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict

repo = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(repo))
from app.controller import Controller, MockExecutor, ParticipantSpec, MANUAL, INCLUDE_UNVERIFIED
from app.store import Store
from app.roles import freeze

def fixture(store, run_count, synth_count, draft_chars):
    participants = [ParticipantSpec(f'p{i}', f'Manual {i}', f'fixture-{i}', MANUAL) for i in range(2)]
    roles = json.dumps(freeze(None, participants, {p.pid:p for p in participants}))
    prompt = 'Synthetic review question; no private/user data.'
    p_hash = hashlib.sha256(prompt.encode()).hexdigest()
    draft = 'A' * draft_chars
    d_hash = hashlib.sha256(draft.encode()).hexdigest()
    # Bulk population is benchmark setup, not a supported product write API.
    with store.tx() as tx:
        for n in range(run_count):
            rid, tid = f'r-fixture-{n}', f't-fixture-{n}'
            tx.execute('INSERT INTO tasks VALUES (?, ?, ?)', tid, 'Synthetic task', float(n))
            tx.execute('INSERT INTO runs (run_id,created_at,question,prompt,input_sha256,input_bytes,min_independent,roster,quorum_policy,phase,task_id,role_config) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                       rid, float(n), prompt, prompt, p_hash, len(prompt), 1, '{}', INCLUDE_UNVERIFIED, 'revealed', tid, roles)
            for spec in participants:
                tx.execute('INSERT INTO participants (run_id,pid,spec,state,status,result) VALUES (?,?,?,?,?,?)', rid,spec.pid,json.dumps(asdict(spec)),'accepted','manual_submitted','{}')
                tx.execute('INSERT INTO drafts VALUES (?,?,?,?,?,?)',rid,spec.pid,draft,d_hash,'manual',float(n))
            tx.event(rid,'human_reviewed')
            for j in range(synth_count):
                aid = f'synth-{j}'
                tx.event(rid,'synthesis_started',attempt=aid)
                tx.event(rid,'synthesis_completed',attempt=aid,result={
                    'schema':'synthetic-measurement-only','status':'completed','text':'S'*draft_chars,
                    'synthesizer':{'tree_confirmed_empty':True,'execution':'synthetic'}})

def measure(ctl, store, count, synth, chars, one_run):
    target = 'r-fixture-0' if one_run else None
    view = ctl.view(target)
    statements = []
    store._db.set_trace_callback(statements.append)
    ctl.view(target)
    store._db.set_trace_callback(None)
    selects = [s for s in statements if s.startswith('SELECT')]
    timings = []
    serial = []
    for _ in range(7):
        t=time.perf_counter(); v=ctl.view(target); timings.append((time.perf_counter()-t)*1000)
        t=time.perf_counter(); encoded=json.dumps(v,ensure_ascii=False).encode('utf-8'); serial.append((time.perf_counter()-t)*1000)
    lifecycle = [s for s in selects if s.startswith('SELECT run_id, kind, payload FROM events')]
    return {'runs_in_ledger':count,'syntheses_per_run':synth,'draft_chars_each':chars,'requested':'one' if one_run else 'all',
            'returned_runs':len(view['runs']),'select_queries':len(selects),
            'lifecycle_query_calls':len(lifecycle),'global_lifecycle_calls':sum('AND run_id = ' not in s for s in lifecycle),
            'identical_repeated_selects':[{'sql':q,'count':n} for q,n in collections.Counter(selects).items() if n>1][:8],
            'response_bytes':len(encoded),'median_view_ms':round(statistics.median(timings),3),
            'median_json_ms':round(statistics.median(serial),3),
            'timing_samples':len(timings)}

results=[]
for n,syn,chars in [(1,1,8192),(30,1,8192),(100,1,8192),(1,50,8192)]:
    with tempfile.TemporaryDirectory(prefix='dml-review-projection-') as temp:
        store=Store(Path(temp)/'journal.db')
        ctl=Controller(store,MockExecutor(),max_parallel=0,work_root=str(Path(temp)/'work'))
        try:
            fixture(store,n,syn,chars)
            for only in (False,True):
                results.append(measure(ctl,store,n,syn,chars,only))
        finally:
            assert ctl.shutdown()
            store.close()
result={'source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
        'python':sys.version.split()[0],'platform':sys.platform,
        'method':'Synthetic manual accepted drafts plus synthetic terminal synthesis events; no providers, subprocess executor, server or sockets. Seven warm in-process samples; excludes network, DOM and actual model latency.',
        'limits':'Fixtures explore structural growth, not observed user workload. Default live ledger caps and rotation limit typical real-call history. Manual/mock history can still grow; no claim of measured production slowdown.',
        'cases':results}
output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k!='identical_repeated_selects'} for r in results],indent=2))
