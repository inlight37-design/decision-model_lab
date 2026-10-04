"""Research-only tmux 3.7c probes on an isolated socket; no model calls.

python tmux-probes.py /path/to/tmux-3.7c/tmux
"""
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time

binary = str(Path(sys.argv[1]).resolve())
version = subprocess.check_output([binary, '-V'], text=True).strip()
assert version == 'tmux 3.7c', version
rows = []
clients = []
env = {k: os.environ[k] for k in ('PATH', 'HOME', 'LANG', 'LC_ALL', 'TERM') if k in os.environ}
env.setdefault('TERM', 'xterm-256color')

with tempfile.TemporaryDirectory(prefix='dml-tmux-probe-') as directory:
    root = Path(directory)
    socket = root / 'server.sock'
    prefix = [binary, '-S', str(socket), '-f', '/dev/null']

    def run(*args, check=True):
        return subprocess.run(prefix + list(args), env=env, text=True, capture_output=True, timeout=8, check=check)

    def until(fn):
        end = time.monotonic() + 5
        while time.monotonic() < end:
            value = fn()
            if value:
                return value
            time.sleep(.03)
        raise AssertionError('bounded wait expired')

    def control():
        proc = subprocess.Popen(prefix + ['-C', 'attach-session', '-t', 'probe'], env=env,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, bufsize=1)
        clients.append(proc)
        lines = queue.Queue()
        def reader():
            for line in proc.stdout:
                lines.put(line.rstrip('\n'))
        threading.Thread(target=reader, daemon=True).start()
        return proc, lines

    def read_until(lines, predicate):
        seen = []
        end = time.monotonic() + 5
        while time.monotonic() < end:
            try:
                line = lines.get(timeout=.1)
            except queue.Empty:
                continue
            seen.append(line)
            if predicate(line):
                return seen
        raise AssertionError(f'missing control frame: {seen!r}')

    def send(proc, command):
        proc.stdin.write(command + '\n')
        proc.stdin.flush()

    def record(id, note):
        rows.append({'id': id, 'note': note, 'result': 'pass'})

    try:
        run('new-session', '-d', '-s', 'probe', '-x', '100', '-y', '24', 'sleep 30')
        run('set-option', '-w', '-t', 'probe', 'remain-on-exit', 'on')
        identity = run('display-message', '-p', '-t', 'probe', '#{session_id}|#{window_id}|#{pane_id}').stdout.strip()
        pane = identity.split('|')[-1]
        proc, lines = control()
        read_until(lines, lambda x: x.startswith('%end '))
        send(proc, 'display-message -p CONTROL_FIXTURE')
        frames = read_until(lines, lambda x: x == 'CONTROL_FIXTURE')
        frames += read_until(lines, lambda x: x.startswith('%end '))
        begin = next(x for x in frames if x.startswith('%begin '))
        end = next(x for x in reversed(frames) if x.startswith('%end '))
        assert begin.split()[1:] == end.split()[1:]
        record('T01', 'Control command has matching begin/end receipt identifiers')
        send(proc, 'not-a-real-tmux-command')
        read_until(lines, lambda x: x.startswith('%error '))
        record('T02', 'Parse failure emits an error block')

        send(proc, 'wait-for dml-gate')
        read_until(lines, lambda x: x.startswith('%end '))
        send(proc, 'display-message -p AFTER_GATE')
        time.sleep(.08)
        buffered=[]
        while not lines.empty():
            buffered.append(lines.get_nowait())
        assert 'AFTER_GATE' not in buffered
        run('wait-for', '-S', 'dml-gate')
        read_until(lines, lambda x: x == 'AFTER_GATE')
        record('T03', 'wait-for emits end receipt before continuation; signal releases queued command')

        send(proc, 'detach-client')
        proc.wait(timeout=5)
        assert run('has-session', '-t', 'probe').returncode == 0
        other, other_lines = control()
        read_until(other_lines, lambda x: x.startswith('%end '))
        assert run('display-message', '-p', '-t', 'probe', '#{session_id}|#{window_id}|#{pane_id}').stdout.strip() == identity
        run('rename-window', '-t', 'probe', 'renamed')
        assert run('display-message', '-p', '-t', pane, '#{pane_id}').stdout.strip() == pane
        record('T04', 'Detach/reconnect and window rename preserve live-server pane identity')

        fixture = root / 'fixture.py'
        fixture.write_text("import sys\nprint('STDOUT_FIXTURE',flush=True)\nprint('STDERR_FIXTURE',file=sys.stderr,flush=True)\nprint('before\\rafter ',flush=True)\nsys.exit(7)\n", encoding='utf-8')
        run('respawn-pane', '-k', '-t', pane, sys.executable, str(fixture))
        until(lambda: run('display-message', '-p', '-t', pane, '#{pane_dead}').stdout.strip() == '1')
        capture = run('capture-pane', '-p', '-S', '-', '-t', pane).stdout
        assert 'STDOUT_FIXTURE' in capture and 'STDERR_FIXTURE' in capture, repr(capture)
        assert 'before' not in capture and 'after' in capture
        assert run('display-message', '-p', '-t', pane, '#{pane_dead_status}').stdout.strip() == '7'
        record('T05', 'Captured screen mixes stdout/stderr and contains rendered overwrite, not raw stream')
        record('T06', 'remain-on-exit retains dead pane with exit status 7; pane presence is not process success')

        run('wait-for', '-S', 'dml-latched')
        run('wait-for', 'dml-latched')
        record('T07', 'Signal before wait is retained in this live server')
    finally:
        run('kill-server', check=False)
        for proc in clients:
            if proc.poll() is None:
                proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(timeout=5)
        assert run('has-session', check=False).returncode != 0
        record('T08', 'Test server no longer answers has-session; control clients have exited')

print(json.dumps({'observed_at':'2026-10-04', 'version':version,
                  'binary_sha256':hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
                  'limits':'Linux cloud, isolated socket, ASCII screen fixtures; no WSL/Windows, crash recovery, slow-client stress, model CLI or whole-process-tree proof.',
                  'results':rows}, ensure_ascii=False, indent=2))
