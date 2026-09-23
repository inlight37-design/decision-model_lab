"""A1 review probes, pinned to unchanged source blobs. No models or credentials.

Run against the reviewed checkout, not against fixed source:
  python reproduce.py --repo /path/to/checkout --output /tmp/a1-results.json
Exit 0 means the observation procedure completed, NOT that defects are fixed.
Only temporary journals, synthetic answers, loopback HTTP, and harmless bwrap
probes are used. The GitHub Actions harness is temporary and is removed from
the final review PR; this standalone script remains reproducible.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import threading
from unittest.mock import patch

BASE = "4bbd034b33649f0ae570b37eecc17d3176669420"
BLOBS = {
    "app/controller.py": "9df69c530d3a8307f1221515f08f191c6ae48c26",
    "app/store.py": "325778b1bd623d47b74029a1d2f5342ffc7ea235",
    "app/server.py": "a786685fc8ba1c6e0e2e0ca0d48f6c5855dfc1ff",
    "app/static/index.html": "999863b0bf94aed10190a80340b6219ecb11cd4b",
    "core/runner.py": "b7438b33c2e8dcba139e77aa67a33e63a43cf78e",
    "core/adapters.py": "6d0a4bfd2cc99fc5e66cfdee1203bb5d34b45549",
    "core/isolation.py": "80c76efb1ac7688b9a619467da47dd835bdf2562",
    "core/env.py": "cee3d6da49358ee34251d7f5e301dcc9b50364de",
    "core/membership.py": "a8a3d29683f7c9ca14523f850a0fec75180a85b6",
}
SENTINEL = "A1_SYNTHETIC_PRIVATE_DETAIL"


def check_source(root):
    actual = {}
    for name, expected in BLOBS.items():
        data = (root / name).read_bytes()
        actual[name] = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual[name] != expected:
            raise RuntimeError(f"Source mismatch: {name}: {actual[name]} != {expected}")
    return actual


def probes(root):
    sys.path.insert(0, str(root))
    from app import controller as c, server
    from app.store import Store
    from core import adapters, isolation, runner

    def cli(pid="a", adapter="claude-code"):
        return c.ParticipantSpec(pid, pid.upper(), "synthetic", c.CLI, adapter, "m")

    def manual(pid="b"):
        return c.ParticipantSpec(pid, pid.upper(), "synthetic", c.MANUAL)

    def result_for(adapter="claude-code", text="synthetic answer", error=None,
                   delivery="complete", model="m"):
        if adapter == "claude-code":
            stdout = json.dumps({"type": "result", "is_error": error is not None,
                                 "result": text, "terminal_reason": error,
                                 "modelUsage": {model: {}}, "permission_denials": []})
        else:
            events = [{"type": "item.completed", "item": {"type": "agent_message", "text": text}}]
            events.append({"type": "turn.failed", "error": {"message": error}}
                          if error is not None else {"type": "turn.completed"})
            stdout = "\n".join(json.dumps(e) for e in events)
        r = runner.RunResult(("synthetic-not-a-process",), runner.EXITED, int(error is not None),
                             stdout, "", False, False, 1, 0, True,
                             containment=runner.PID_NAMESPACE, input_delivery=delivery)
        return r, adapters.interpret(adapter, r, requested_model="m")

    class Executor:
        name = "synthetic-protocol-fixture"

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.started = []

        def execute(self, spec, prompt, work_dir, timeout):
            self.started.append(spec.pid)
            return result_for(adapter=spec.adapter_id, **self.kwargs)

    @contextmanager
    def harness(executor=None, parallel=2):
        with tempfile.TemporaryDirectory(prefix="a1-review-") as tmp:
            store = Store(Path(tmp) / "journal.db")
            ctl = c.Controller(store, executor or Executor(), max_parallel=parallel,
                               work_root=str(Path(tmp) / "work"))
            try:
                yield ctl, store, Path(tmp)
            finally:
                if not ctl.wait_idle(10):
                    raise RuntimeError("synthetic worker did not finish")
                store.close()

    def view(ctl, rid):
        return next(r for r in ctl.view()["runs"] if r["run_id"] == rid)

    observations = {}
    leaks = {}
    for adapter in ("claude-code", "codex"):
        with harness(Executor(error=SENTINEL)) as (ctl, _, _tmp):
            rid = ctl.create_run("synthetic question", [cli(adapter=adapter), manual()], min_independent=1)
            assert ctl.wait_idle(10)
            v = view(ctl, rid)
            p = next(p for p in v["participants"] if p["pid"] == "a")
            leaks[adapter] = {"phase": v["phase"], "participant_state": p["state"],
                              "sentinel_in_view": SENTINEL in json.dumps(v),
                              "sentinel_in_participant_detail": SENTINEL in (p["detail"] or ""),
                              "sentinel_in_result_detail": SENTINEL in (p["result"]["detail"] or "")}
    observations["sealed_error_detail"] = leaks

    acceptance = {}
    for label, kwargs in (("no_delivery_evidence", {"delivery": None}),
                          ("empty_answer", {"text": ""}),
                          ("whitespace_answer", {"text": "  \n"}),
                          ("model_mismatch", {"model": "other-model"})):
        with harness(Executor(**kwargs)) as (ctl, _, _tmp):
            rid = ctl.create_run("synthetic question", [cli()], min_independent=1)
            assert ctl.wait_idle(10)
            v = view(ctl, rid)
            p = v["participants"][0]
            acceptance[label] = {"phase": v["phase"], "state": p["state"],
                                 "input_delivery": p["result"]["input_delivery"],
                                 "model_match": p["result"]["model_match"],
                                 "draft_characters": len(p.get("draft", ""))}
    observations["acceptance_edges_synthetic"] = acceptance

    with harness() as (ctl, store, tmp):
        rid = ctl.create_run("synthetic question", [manual("a"), manual("b")], min_independent=2)
        digest = view(ctl, rid)["input_sha256"]
        ctl.submit_manual(rid, "a", "A", digest)
        # Failure injection: the final result transaction committed, but the next
        # transaction that advances the phase never ran before controller death.
        with patch.object(ctl, "_maybe_reveal", return_value=None):
            ctl.submit_manual(rid, "b", "B", digest)
        second_store = Store(tmp / "journal.db")
        try:
            again = c.Controller(second_store, Executor(), work_root=str(tmp / "work2"))
            again.pump()
            v = view(again, rid)
            observations["restart_after_final_draft_commit"] = {
                "phase": v["phase"], "states": [p["state"] for p in v["participants"]], "note": v["note"]}
        finally:
            second_store.close()

    with harness(parallel=0) as (ctl, _store, tmp):
        rid = ctl.create_run("synthetic question", [cli()], min_independent=1)
        second_store = Store(tmp / "journal.db")
        try:
            ex = Executor()
            again = c.Controller(second_store, ex, work_root=str(tmp / "work2"))
            observations["restart_queued_not_pumped"] = {
                "state": view(again, rid)["participants"][0]["state"], "new_attempts": list(ex.started)}
        finally:
            second_store.close()

    with harness() as (ctl, _store, _tmp):
        rid = ctl.create_run("synthetic question", [manual("a"), manual("b")], min_independent=1)
        ctl.approve_reduction(rid)
        digest = view(ctl, rid)["input_sha256"]
        ctl.submit_manual(rid, "a", "A", digest)
        ctl.withdraw_manual(rid, "b")
        v = view(ctl, rid)
        observations["approval_before_membership_loss"] = {
            "phase": v["phase"], "approved": v["reduction_approved"],
            "dropped": [p["pid"] for p in v["participants"] if p["dropped"]]}

    class HeldExecutor(Executor):
        def __init__(self):
            super().__init__()
            self.release = threading.Event()

        def execute(self, *args):
            if not self.release.wait(10):
                raise RuntimeError("test gate expired")
            return super().execute(*args)

    with tempfile.TemporaryDirectory(prefix="a1-startup-review-") as tmp:
        first_server, _token, first = server.serve(Path(tmp), 0)
        port = first_server.server_address[1]
        ex = HeldExecutor()
        first.executor = ex
        first.work_root = str(Path(tmp) / "work")
        rid = first.create_run("synthetic question", [cli()], min_independent=1)
        old_token = (Path(tmp) / "control-token").read_bytes()
        try:
            bind_error = None
            try:
                unexpected, _newtoken, other = server.serve(Path(tmp), port)
            except OSError as exc:
                bind_error = type(exc).__name__
            else:
                unexpected.server_close()
                other.store.close()
            before = view(first, rid)["participants"][0]["state"]
            changed = old_token != (Path(tmp) / "control-token").read_bytes()
            ex.release.set()
            assert first.wait_idle(10)
            v = view(first, rid)
            observations["failed_second_server_start"] = {
                "bind_error": bind_error, "live_state_after_failed_start": before,
                "token_file_changed": changed,
                "state_after_old_executor_returns": v["participants"][0]["state"],
                "phase_after_old_executor_returns": v["phase"]}
        finally:
            ex.release.set()
            first.wait_idle(10)
            first_server.server_close()
            first.store.close()

    with harness() as (ctl, _store, _tmp):
        from http.server import ThreadingHTTPServer
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(ctl, "SYNTHETIC-TOKEN", 0))
        port = httpd.server_address[1]
        httpd.RequestHandlerClass = server.make_handler(ctl, "SYNTHETIC-TOKEN", port)
        worker = threading.Thread(target=httpd.serve_forever, daemon=True)
        worker.start()
        try:
            def get(token):
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
                headers = {"Origin": "https://untrusted.invalid"}
                if token:
                    headers["Authorization"] = "Bearer SYNTHETIC-TOKEN"
                conn.request("GET", "/api/state", headers=headers)
                res = conn.getresponse()
                answer = {"status": res.status, "cors_allow_origin": res.getheader("Access-Control-Allow-Origin")}
                res.read()
                conn.close()
                return answer
            observations["origin_probe_not_a_browser_csrf_exploit"] = {"without_token": get(False), "with_token": get(True)}
        finally:
            httpd.shutdown()
            httpd.server_close()
            worker.join(3)

    try:
        isolation._trusted_bwrap()
    except isolation.IsolationError as exc:
        observations["real_bwrap"] = {"not_run": str(exc)}
        return observations
    with tempfile.TemporaryDirectory(prefix="a1-bwrap-review-") as tmp:
        r = Path(tmp)
        (r / "work").mkdir()
        (r / "input/work").mkdir(parents=True)
        box = isolation.Sandbox(str(r / "work"), str(r / "home"), env={"TZ": "SYNTHETIC"})
        _planned, planned_env = isolation.plan(["/usr/bin/env", "-0"], box)
        env_run = isolation.run(["/usr/bin/env", "-0"], box, timeout=5)
        if env_run.state != runner.EXITED or env_run.exit_code != 0:
            observations["real_bwrap"] = {"unusable": env_run.state, "exit_code": env_run.exit_code}
            return observations
        actual_env = sorted(x.split("=", 1)[0] for x in env_run.stdout.split("\0") if x)
        real = {"version": subprocess.check_output([isolation.BWRAP, "--version"], text=True).strip(),
                "environment": {"planned_keys": sorted(planned_env), "actual_keys": actual_env,
                                "extra_keys": sorted(set(actual_env) - set(planned_env))}}
        ro_box = isolation.Sandbox(str(r / "input/work"), str(r / "home"), read_only=(str(r / "input"),))
        marker = r / "input/work/marker"
        try:
            rr = isolation.run(["/usr/bin/python3", "-c", "from pathlib import Path; Path('marker').write_text('synthetic')"],
                               ro_box, timeout=5)
            real["work_inside_read_only_input"] = {"plan_accepted": True, "exit_code": rr.exit_code,
                                                   "host_marker_written": marker.exists(),
                                                   "tree_confirmed_empty": rr.tree_confirmed_empty}
        except isolation.IsolationError:
            real["work_inside_read_only_input"] = {"plan_accepted": False}
        forbidden = "/etc/hostname"
        never_box = isolation.Sandbox(str(r / "work"), str(r / "home"), never=(forbidden,))
        code = "import os; fd=os.open('/etc/hostname',os.O_RDONLY); os.close(fd); print('readable')"
        try:
            rr = isolation.run(["/usr/bin/python3", "-c", code], never_box, timeout=5)
            real["never_in_automatic_system_mount"] = {"plan_accepted": True, "forbidden_path": forbidden,
                                                       "readable": rr.stdout.strip() == "readable", "exit_code": rr.exit_code}
        except isolation.IsolationError:
            real["never_in_automatic_system_mount"] = {"plan_accepted": False}

        class NoInputExecutor:
            name = "real-bwrap-synthetic-cli-without-stdin"

            def execute(self, spec, prompt, work_dir, timeout):
                payload = json.dumps({"type": "result", "is_error": False, "result": "never received the question",
                                      "modelUsage": {"m": {}}})
                child_box = isolation.Sandbox(work_dir, work_dir + "-home")
                rr = isolation.run(["/usr/bin/python3", "-c", "print(" + repr(payload) + ")"],
                                   child_box, timeout=5)
                return rr, adapters.interpret("claude-code", rr, requested_model="m")
        with harness(NoInputExecutor()) as (ctl, _store, _hroot):
            rid = ctl.create_run("synthetic question never delivered", [cli()], min_independent=1)
            assert ctl.wait_idle(10)
            v = view(ctl, rid)
            p = v["participants"][0]
            real["missing_stdin_accepted"] = {"phase": v["phase"], "state": p["state"],
                                             "input_delivery": p["result"]["input_delivery"],
                                             "tree_confirmed_empty": p["result"]["tree_confirmed_empty"]}
        observations["real_bwrap"] = real
    return observations


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    root = args.repo.resolve()
    hashes = check_source(root)
    result = {"reviewed_commit": BASE, "source_git_blob_shas": hashes,
              "execution": {"python": sys.version.split()[0], "platform": platform.platform(),
                            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
                            "github_sha": os.environ.get("GITHUB_SHA"),
                            "synthetic_containment_is_not_os_evidence": True},
              "observations": probes(root)}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print("A1_REVIEW_RESULTS_BEGIN\n" + text + "\nA1_REVIEW_RESULTS_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
