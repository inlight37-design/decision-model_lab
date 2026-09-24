"""Bounded, explicit account-metadata probe; never sends thread/start or turn/start.

Default is a no-process plan. --probe uses the existing bubblewrap boundary and runner.
Only a quota allowlist leaves the sandbox; account identity, credentials, stderr and raw
protocol messages are not saved. Native installed-version compatibility still needs a PC
observation. Protocol source: https://developers.openai.com/codex/app-server (2026-09-24).
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.quota import quota_projection

METHODS = ("initialize", "initialized", "account/read", "account/rateLimits/read")
MAX_BYTES = 1024 * 1024


class ProtocolError(ValueError):
    """Fixed messages only; never put provider response text in an exception."""


def helper_argv(exe: str) -> tuple[str, ...]:
    # Isolation deliberately drops PYTHONPATH; CI's interpreter may live outside /usr.
    code = ("import json,sys; sys.path.insert(0,sys.argv[1]); "
            "from app.codex_account import query; print(json.dumps(query(tuple(sys.argv[2:]))))")
    # cli_mounts exposes the resolved binary, not the host's ~/.local/bin symlink.
    # The outer runner resolves only argv[0] (Python), so resolve this child too.
    return ("/usr/bin/python3", "-c", code, str(ROOT), os.path.realpath(exe), "app-server")


def query(argv: tuple[str, ...], *, timeout: float = 10) -> dict:
    """Internal stdio dialogue, called INSIDE isolation by --probe (fake processes in tests)."""
    if not math.isfinite(timeout) or not 0 < timeout <= 20:
        raise ValueError("timeout must be finite, greater than zero and at most 20 seconds")
    deadline, buffer, received = time.monotonic() + timeout, b"", 0
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, bufsize=0, shell=False)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)

            def send(method, params=None, request_id=None):
                if method not in METHODS:
                    raise ProtocolError("method is not allowed")
                message = {"method": method}
                if params is not None:
                    message["params"] = params
                if request_id is not None:
                    message["id"] = request_id
                proc.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
                proc.stdin.flush()

            def receive(request_id):
                nonlocal buffer, received
                while True:
                    if time.monotonic() >= deadline:
                        raise ProtocolError("metadata request timed out")
                    if b"\n" not in buffer:
                        if not selector.select(max(0, deadline - time.monotonic())):
                            raise ProtocolError("metadata request timed out")
                        chunk = os.read(proc.stdout.fileno(), 4096)
                        if not chunk:
                            raise ProtocolError("metadata server closed before reply")
                        received += len(chunk)
                        if received > MAX_BYTES:
                            raise ProtocolError("metadata output exceeded bound")
                        buffer += chunk
                        continue
                    line, buffer = buffer.split(b"\n", 1)
                    try:
                        message = json.loads(line)
                    except (ValueError, UnicodeError):
                        raise ProtocolError("invalid metadata JSON") from None
                    if not isinstance(message, dict):
                        raise ProtocolError("invalid metadata message")
                    if "method" in message:
                        if "id" in message or str(message["method"]).startswith(("thread/", "turn/", "item/")):
                            raise ProtocolError("unexpected server request or agent activity")
                        continue  # discard notifications, including account identity
                    if type(message.get("id")) is not int or message["id"] != request_id:
                        continue
                    if "error" in message or not isinstance(message.get("result"), dict):
                        raise ProtocolError("metadata method unavailable or refused")
                    return message["result"]

            send("initialize", {"clientInfo": {"name": "decision_model_lab_quota", "version": "0.1"}}, 0)
            receive(0)
            send("initialized", {})
            send("account/read", {"refreshToken": False}, 1)
            account = receive(1).get("account")
            if not isinstance(account, dict) or account.get("type") != "chatgpt":
                raise ProtocolError("existing ChatGPT login required; no login or API fallback attempted")
            del account  # do not retain identity, plan or auth information
            send("account/rateLimits/read", request_id=2)
            payload = receive(2)
            now = int(time.time())
            projection = quota_projection(payload, observed_at=now, now=now)
            return {"schema": "codex-account-observation/1", "inference_requests_sent": 0,
                    "quota": projection}
    finally:
        if proc.stdin:
            try:
                proc.stdin.close()
            except OSError:
                pass
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1)
        proc.stdout.close()


def probe(data_dir: Path) -> dict:
    """One bounded metadata read; reusable by the CLI and an explicit UI refresh."""
    if sys.platform != "linux":
        raise ValueError("metadata probe requires Linux isolation")
    from core import env, isolation, runner
    from app.cli_executor import installed_version
    try:
        child_env, _ = env.child_env(os.environ)
        exe = env.resolve("codex", child_env)
        home = os.path.expanduser("~")
        ro, rw = isolation.cli_mounts("codex", exe, home)
        # Helper source is read-only, work is empty. Neither journal nor peer CLI home is mounted.
        with tempfile.TemporaryDirectory(prefix="dml-account-") as tmp:
            box = isolation.Sandbox(work_dir=tmp, home=home, read_only=ro + (str(ROOT / "app"), str(ROOT / "core")),
                                    read_write=rw, env={"LANG": "C.UTF-8", "NO_COLOR": "1"},
                                    never=(str(data_dir.resolve()),))
            result = isolation.run(helper_argv(exe), box,
                                   timeout=13, max_output_bytes=65536)
            if (result.state != runner.EXITED or result.exit_code != 0
                    or not result.tree_confirmed_empty or result.stdout_truncated):
                raise ProtocolError("isolated metadata probe did not finish successfully; raw diagnostics suppressed")
            report = json.loads(result.stdout)
            report["installed_version"] = installed_version("codex", exe)
            report["tree_confirmed_empty"] = True
            return report
    except (OSError, ValueError, RuntimeError):
        return {"status": "unknown", "inference_requests_sent": 0,
                "reason": "metadata probe unavailable, refused, timed out or unsupported; no fallback"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", action="store_true", help="explicitly query existing login inside bubblewrap; no agent turn")
    ap.add_argument("--data-dir", type=Path, help="controller journal directory to exclude from isolation")
    args = ap.parse_args()
    if not args.probe:
        print(json.dumps({"mode": "plan_only", "processes_started": 0, "inference_requests_sent": 0,
                          "methods": METHODS, "timeout_seconds": 10, "raw_protocol_saved": False}, indent=2))
        return 0
    if sys.platform != "linux" or args.data_dir is None:
        ap.error("--probe requires Linux and --data-dir; never query outside the isolation boundary")
    report = probe(args.data_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("tree_confirmed_empty") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
