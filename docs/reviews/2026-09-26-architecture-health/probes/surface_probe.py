"""Pure mock / temporary-file surface probes; no server, CLI, model, account, or real app is started."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
from app import launch, server
from app.store import LedgerBusy


def launch_race():
    # Both starts observe the same pre-start snapshot. The real Store protects
    # its ledger, modelled here by a LedgerBusy from the second start_server.
    with tempfile.TemporaryDirectory(prefix='dml-surface-launch-') as tmp:
        initial_reads = threading.Barrier(2)
        first_starting, second_starting = threading.Event(), threading.Event()
        first_running, release_first = threading.Event(), threading.Event()
        actual_read, actual_write = launch.read_state, launch._write_state
        statuses, results, open_fds, thread_errors = [], {}, [], []
        captured_stdout = io.StringIO()
        def wait(event, label):
            assert event.wait(5), f'harness timed out waiting for {label}'
        def initial_read():
            before = actual_read()
            initial_reads.wait(5)
            # Both callers have observed the old state. Let the first finish
            # its initial write before the second proceeds to log/state I/O.
            if threading.current_thread().name == 'second':
                wait(first_starting, 'first starting write')
            return before
        def write(data):
            name = threading.current_thread().name
            if data['status'] == 'starting' and name == 'second':
                wait(first_starting, 'first starting write')
            actual_write(data)
            statuses.append([name, data['status']])
            # Fix the legal product interleaving, without racing the harness's
            # Windows file replacement: first starting -> second starting ->
            # first running -> second failed. Product functions are unchanged.
            if data['status'] == 'starting' and name == 'first':
                first_starting.set()
                wait(second_starting, 'second starting write')
            elif data['status'] == 'starting' and name == 'second':
                second_starting.set()
            if data['status'] == 'running':
                first_running.set()
        def start(*args, **kwargs):
            if threading.current_thread().name == 'first':
                return mock.Mock(server_address=('127.0.0.1',8765)), 'synthetic-token', mock.Mock(paused=False)
            wait(first_running, 'first running write')
            raise LedgerBusy('synthetic duplicate ledger lock')
        def serve_until(*args):
            wait(release_first, 'owner release')
            return 0
        real_open = os.open
        def open_log(*args, **kwargs):
            fd = real_open(*args, **kwargs)
            if Path(args[0]).name == 'server.log': open_fds.append(fd)
            return fd
        def invoke():
            name = threading.current_thread().name
            try:
                results[name] = launch.main(['serve','--mock','--nonce',name])
            except BaseException as exc:
                thread_errors.append({'thread':name, 'type':type(exc).__name__, 'message':str(exc)})
                # Release the other synthetic thread on harness failure, then
                # fail visibly in the parent after both threads have joined.
                first_starting.set(); second_starting.set(); first_running.set(); release_first.set()
        try:
            with mock.patch.dict(os.environ, {'DML_LAUNCHER_DIR':tmp}), \
                 mock.patch.object(launch.sys,'platform','linux'), \
                 mock.patch.object(launch,'read_state',side_effect=initial_read), \
                 mock.patch.object(launch,'_write_state',side_effect=write), \
                 mock.patch.object(launch,'_watch',return_value=None), \
                 mock.patch.object(launch.signal,'signal'), \
                 mock.patch.object(launch.signal,'SIGHUP',1,create=True), \
                 mock.patch.object(launch.os,'dup2'), \
                 mock.patch.object(launch.os,'open',side_effect=open_log), \
                 mock.patch.object(launch.os,'fdopen',return_value=captured_stdout), \
                 mock.patch.object(server,'serve',side_effect=start), \
                 mock.patch.object(server,'serve_until_stopped',side_effect=serve_until), \
                 contextlib.redirect_stdout(captured_stdout), contextlib.redirect_stderr(captured_stdout):
                first=threading.Thread(target=invoke,name='first'); second=threading.Thread(target=invoke,name='second')
                try:
                    first.start(); second.start(); second.join(5)
                    assert not second.is_alive(), 'second harness thread did not return'
                    assert not thread_errors, thread_errors
                    snapshot=actual_read()
                    result={'first_controller_still_owned':first.is_alive(), 'second_exit':results.get('second'),
                            'shared_launcher_status':snapshot.get('status'), 'shared_launcher_nonce':snapshot.get('nonce'),
                            'status_writes_before_release':list(statuses)}
                    assert result['first_controller_still_owned'] and result['second_exit'] == 1, result
                    assert result['shared_launcher_status'] == 'failed' and result['shared_launcher_nonce'] == 'second', result
                    assert statuses == [['first','starting'],['second','starting'],['first','running'],['second','failed']], statuses
                finally:
                    release_first.set(); first_starting.set(); second_starting.set(); first_running.set()
                    first.join(5); second.join(5)
            assert not first.is_alive() and not second.is_alive(), 'harness threads remained alive'
            assert not thread_errors, thread_errors
        finally:
            # These are harmless temporary log handles, but an assertion must
            # not leave them open and mask the original failure on Windows.
            for fd in open_fds:
                os.close(fd)
        return result


def missing_report():
    controller=mock.Mock(); controller.executor.kind='mock'; controller.view.return_value={'runs':[]}
    handler_type=server.make_handler(controller,'synthetic-token',8765,account_quota=mock.Mock())
    outcomes={}
    for kind in ('report','decision-report'):
        fake=mock.Mock(path=f'/api/runs/no-such-run/{kind}')
        fake._guard.return_value=True
        try:
            handler_type.do_GET(fake)
            outcomes[kind]={'http_status':fake._json.call_args.args[0]}
        except Exception as exc:
            outcomes[kind]={'exception':type(exc).__name__, 'message':str(exc)}
    assert outcomes['report']['http_status'] == 409
    assert outcomes['decision-report']['exception'] == 'IndexError'
    return outcomes


print(json.dumps({'launcher_race':launch_race(),'missing_report':missing_report()},ensure_ascii=False,indent=2))
