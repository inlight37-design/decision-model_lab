"""Pinned-core synthetic review probes. No model, network, WSL or real bwrap calls.

Usage: python reproduce.py --repo /path/to/pinned/checkout --output results.json
Only temporary files and this process's synthetic children are created. Linux only.
The report records observed bugs, not an expected-to-pass regression test suite.
"""
from __future__ import annotations

import argparse
import ctypes
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import sys
import tempfile
import threading
import time
from unittest import mock

BASE = "a662e59b0541ea747c50be4b388af9a61dd02b84"
BLOBS = {
    "core/runner.py": "7e80d0698f797c5c82eeeeac19e3a39b45c58a56",
    "core/adapters.py": "c4ea0474e2d388b542099b35ff59d65773e7704c",
    "core/env.py": "9a6dab78bfe1b98b7ed5c8d2c50614b65399cf14",
    "core/isolation.py": "a2e5a6c6351205400bb07d952f29eb18580e0f91",
}


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def alive(pid: int) -> bool:
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
        return state != "Z"
    except FileNotFoundError:
        return False


def end_owned_child(pid: int) -> None:
    # Only PIDs written by our own temporary probe are passed here. No process scanning/killing.
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        os.waitpid(pid, 0)
    except ChildProcessError:
        pass


def result_summary(r) -> dict:
    return {"state": r.state, "exit_code": r.exit_code,
            "containment": r.containment, "tree_confirmed_empty": r.tree_confirmed_empty,
            "unit_confirmed_empty": r.unit_confirmed_empty, "notes": r.notes}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    if sys.platform != "linux":
        ap.error("These synthetic process probes require Linux")
    actual = {name: blob_sha(args.repo / name) for name in BLOBS}
    if actual != BLOBS:
        ap.error("Core blob hashes differ from the reviewed snapshot; use the pinned commit")
    # Adopt and reap our own detached grandchildren. This affects this probe process only.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), "Could not enable child reaping")
    sys.path.insert(0, str(args.repo.resolve()))
    from core import adapters, env, isolation, runner
    report = {"review_base": BASE, "source_blob_shas": actual,
              "environment": {"python": platform.python_version(), "system": platform.system(),
                              "kernel": platform.release(), "real_bwrap_available": bool(shutil.which("bwrap")),
                              "user_pc_access": False, "model_calls": False,
                              "real_bwrap_executed": False}, "probes": {}}
    cases = report["probes"]
    with tempfile.TemporaryDirectory(prefix="dml-review-") as td:
        root = Path(td)
        home, work, inputs = (root / name for name in ("home", "work", "input"))
        for p in (home, work, inputs):
            p.mkdir()

        dummy = "SYNTHETIC_NOT_A_CREDENTIAL"
        box = isolation.Sandbox(str(work), str(home), env={"CLAUDE_CODE_OAUTH_TOKEN": dummy})
        argv = isolation.wrap(["/usr/bin/true"], box)
        # Inspect construction only: no real sandbox is launched.
        cases["oauth_in_argv"] = {"dummy_value_in_argv": dummy in argv,
                                  "setenv_option_present": "CLAUDE_CODE_OAUTH_TOKEN" in argv}
        overlaps = []
        for label, box in (
            ("work_equals_home", isolation.Sandbox(str(home), str(home))),
            ("work_equals_read_only", isolation.Sandbox(str(inputs), str(home), read_only=(str(inputs),))),
        ):
            a = isolation.wrap(["/usr/bin/true"], box)
            overlaps.append({"case": label, "accepted": True,
                             "work_bind_is_after_ro_or_tmpfs": a.index("--chdir") > a.index("--tmpfs"),
                             "last_work_operation": a[a.index("--chdir")-3:a.index("--chdir")]})
        # Remove machine-local temp path details from saved evidence.
        cases["overlap_plan"] = json.loads(json.dumps(overlaps).replace(str(root), "<TEMP>"))

        binary = root / "parent-only-cli"
        binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        binary.chmod(0o755)
        with mock.patch.dict(os.environ, {"PATH": str(root)}):
            resolved = env.resolve("parent-only-cli", {"PATH": ""})
        cases["empty_path_fallback"] = {"child_path": "", "parent_only_executable_found": resolved == str(binary)}

        # Large input, one byte consumed, early closed pipe, superficially valid output.
        prompt = "한글-입력\n" * 120_000
        child = (
            "import os,fcntl,json; cap=fcntl.fcntl(0,fcntl.F_GETPIPE_SZ); "
            "b=os.read(0,1); os.close(0); "
            "print(json.dumps({'type':'result','is_error':False,"
            "'result':json.dumps({'read_bytes':len(b),'pipe_capacity':cap}),"
            "'modelUsage':{'synthetic':{}},'permission_denials':[]}))"
        )
        r = runner.run([sys.executable, "-c", child], cwd=work, env=dict(os.environ),
                       timeout=5, stdin_text=prompt)
        out = adapters.interpret("claude-code", r, requested_model="synthetic")
        cases["stdin_early_close"] = {**result_summary(r), "intended_bytes": len(prompt.encode()),
                                      "child_report": json.loads(out.text), "outcome_ok": out.ok,
                                      "outcome_status": out.status}

        # A file merely named bwrap is enough for the public pid_namespace flag.
        pidfile, fake = root / "detached.pid", root / "bwrap"
        fake.write_text(
            f"#!{sys.executable}\nimport subprocess,sys,pathlib\n"
            "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],"
            "start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
            f"pathlib.Path({str(pidfile)!r}).write_text(str(p.pid))\n", encoding="utf-8")
        fake.chmod(0o755)
        pid = None
        try:
            r = runner.run([str(fake), "--unshare-pid", "--die-with-parent", "--"],
                           cwd=work, env=dict(os.environ), timeout=5, pid_namespace=True)
            pid = int(pidfile.read_text())
            cases["pid_namespace_provenance"] = {**result_summary(r), "detached_child_alive": alive(pid),
                                                   "real_bwrap_used": False}
        finally:
            if pid is None and pidfile.exists():
                pid = int(pidfile.read_text())
            if pid is not None:
                end_owned_child(pid)
        cases["pid_namespace_provenance"]["child_cleaned_up"] = not alive(pid)

        def recorded(body: str):
            return runner.RunResult(("synthetic",), runner.EXITED, 0, body, "", False, False, 1, 0, True)
        deep = '{"type":"result","is_error":false,"result":"x","extra":' + '[' * 10000 + '0' + ']' * 10000 + '}'
        try:
            out = adapters.interpret("claude-code", recorded(deep), requested_model="synthetic")
            cases["deep_json"] = {"exception": None, "status": out.status, "bytes": len(deep)}
        except RecursionError as exc:
            cases["deep_json"] = {"exception": type(exc).__name__, "bytes": len(deep)}
        wrong = json.dumps({"type":"result", "is_error":False, "result":"x", "modelUsage":[], "permission_denials":{}})
        out = adapters.interpret("claude-code", recorded(wrong), requested_model="synthetic")
        cases["falsy_wrong_shapes"] = {"outcome_ok": out.ok, "status": out.status}
        spec = adapters.build_spec("codex", exe=sys.executable, prompt="SYNTHETIC_PRIVATE_PROMPT", model="synthetic")
        cases["spec_log_projection"] = {"prompt_in_repr": spec.stdin_text in repr(spec),
                                        "prompt_in_asdict": dataclasses.asdict(spec)["stdin_text"] == spec.stdin_text}

        # R02 returns now, but abandoned readers/fds accumulate until an external pipe holder exits.
        thread_before = threading.active_count()
        fd_before = len(os.listdir("/proc/self/fd"))
        children = []
        runs = []
        try:
            for index in range(2):
                pfile = root / f"pipe-{index}.pid"
                code = (
                    "import subprocess,sys,pathlib; "
                    "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],"
                    "start_new_session=True,stdin=subprocess.DEVNULL); "
                    f"pathlib.Path({str(pfile)!r}).write_text(str(p.pid))"
                )
                r = runner.run([sys.executable, "-c", code], cwd=work, env=dict(os.environ), timeout=2)
                children.append(int(pfile.read_text()))
                runs.append(result_summary(r))
            cases["retained_output_readers"] = {"runs": runs,
                "extra_live_threads_before_external_cleanup": threading.active_count() - thread_before,
                "extra_open_fds_before_external_cleanup": len(os.listdir("/proc/self/fd")) - fd_before}
        finally:
            for pid in children:
                end_owned_child(pid)
        deadline = time.monotonic() + 2
        while threading.active_count() > thread_before and time.monotonic() < deadline:
            time.sleep(0.01)
        cases["retained_output_readers"]["extra_live_threads_after_cleanup"] = threading.active_count() - thread_before
        cases["retained_output_readers"]["extra_open_fds_after_cleanup"] = len(os.listdir("/proc/self/fd")) - fd_before
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
