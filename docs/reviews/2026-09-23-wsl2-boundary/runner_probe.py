"""Harmless Python subprocess probes; no provider CLI or model calls.
Tests the bundled, hash-verified source snapshot, not an installed app.
"""
import sys, os, json, time, signal, tempfile, pathlib, threading, hashlib, traceback, ctypes
BASE = pathlib.Path(__file__).resolve().parent
if sys.platform != 'linux':
    raise SystemExit('This runner probe requires Linux; Windows and macOS were not tested.')
(BASE / 'results').mkdir(exist_ok=True)
sys.path.insert(0, str(BASE / 'snapshot'))
from core import runner
b=pathlib.Path(runner.__file__).read_bytes()
sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
assert sha == '321ffa0359b78fa4216a74603bf3a9a0f40a43db'
if ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) != 0:
    raise SystemExit('Linux child subreaper setup failed; refusing to run the child-process probe.')
results={'platform':sys.platform,'python':sys.version.split()[0], 'runner_git_blob':sha,'model_calls':0,'cases':[]}
with tempfile.TemporaryDirectory(prefix='dml-review-') as tmp:
    r=runner.run([sys.executable,'-c',"print('ok')"],cwd=tmp,env=dict(os.environ),timeout=1)
    results['cases'].append({'name':'normal_exit_control','state':r.state,'tree_confirmed_empty':r.tree_confirmed_empty})
    code="import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid,flush=True)"
    r=runner.run([sys.executable,'-c',code],cwd=tmp,env=dict(os.environ),timeout=1)
    pid=int(r.stdout.strip())
    try:
        os.kill(pid,0)
        live=pathlib.Path(f'/proc/{pid}/stat').read_text().split()[2] != 'Z'
        results['cases'].append({'name':'detached_child_closed_pipes','state':r.state,'tree_confirmed_empty':r.tree_confirmed_empty,'child_still_live':live,'duration_ms':r.duration_ms})
    finally:
        os.kill(pid,signal.SIGKILL)
        os.waitpid(pid,0)
    pidfile=pathlib.Path(tmp)/'child.pid'
    code=f"import subprocess,sys,pathlib; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True); pathlib.Path({str(pidfile)!r}).write_text(str(p.pid))"
    box={}
    def run_probe():
        box['result']=runner.run([sys.executable,'-c',code],cwd=tmp,env=dict(os.environ),timeout=2)
    t=threading.Thread(target=run_probe,daemon=True); start=time.monotonic();t.start()
    try:
        t.join(8)
        still=t.is_alive()
        stack=traceback.format_stack(sys._current_frames()[t.ident]) if still else []
        results['cases'].append({'name':'detached_child_inherited_pipes','timeout_s':2,'still_blocked_after_s':round(time.monotonic()-start,2),'runner_thread_still_alive':still,'blocked_stack':stack})
    finally:
        if pidfile.exists():
            pid=int(pidfile.read_text())
            try: os.kill(pid,signal.SIGKILL)
            except ProcessLookupError: pass
            try: os.waitpid(pid,0)
            except ChildProcessError: pass
        t.join(3)
        results['cases'][-1]['returned_after_external_child_cleanup']=not t.is_alive()
        if 'result' in box: results['cases'][-1]['final_state']=box['result'].state
(BASE / 'results' / 'runner-probe-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False,indent=2))
