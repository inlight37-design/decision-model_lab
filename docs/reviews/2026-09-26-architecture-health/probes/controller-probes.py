"""Read-only product review probes. Synthetic executor only: no subprocess/CLI/network.

Usage: python controller-probes.py PATH_TO_REPO OUTPUT_DIRECTORY
Temporary SQLite ledgers live beside the output and are cleaned up after the run.
"""
from __future__ import annotations
import hashlib
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile
import threading

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("repo", type=Path)
parser.add_argument("output_dir", type=Path)
args = parser.parse_args()
REPO = args.repo.resolve()
OUTPUT = args.output_dir.resolve() / "controller-probe-results.json"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO))
from app import controller as c
from app.store import Store, events
from core import adapters, contract, runner

BASE = OUTPUT.parent
TEMPS = []
THREAD_ERRORS = []
THREAD_ERROR_SEEN = threading.Event()


def record_thread_error(args):
    THREAD_ERRORS.append({"type": args.exc_type.__name__, "message": str(args.exc_value)})
    THREAD_ERROR_SEEN.set()


threading.excepthook = record_thread_error


def source_revision():
    """Read Git metadata without spawning Git or any other process."""
    gitdir = REPO / ".git"
    if gitdir.is_file():
        pointer = gitdir.read_text(encoding="utf-8").strip()
        if not pointer.startswith("gitdir: "):
            raise RuntimeError("unsupported .git pointer")
        gitdir = (REPO / pointer[8:]).resolve()
    head = (gitdir / "HEAD").read_text(encoding="ascii").strip()
    if not head.startswith("ref: "):
        sha = head
    else:
        ref = head[5:]
        common = gitdir
        if (gitdir / "commondir").is_file():
            common = (gitdir / (gitdir / "commondir").read_text(encoding="utf-8").strip()).resolve()
        candidate = next((p / ref for p in (gitdir, common) if (p / ref).is_file()), None)
        if candidate:
            sha = candidate.read_text(encoding="ascii").strip()
        else:
            packed = (common / "packed-refs").read_text(encoding="ascii").splitlines()
            sha = next((line.split(" ", 1)[0] for line in packed if line.endswith(" " + ref)), "")
    if not re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", sha):
        raise RuntimeError("could not resolve repository HEAD")
    return sha


class OfflineExecutor:
    name = "architecture-review-no-process"
    kind = contract.SYNTHETIC
    adapter_ids = ("claude-code", "codex")

    def __init__(self, bad_metadata=False, bad_answer=False):
        self.bad_metadata = bad_metadata
        self.bad_answer = bad_answer
        self.started = []
        self.results = []
        self.synth_count = 0

    def plan(self, spec, prompt, work_dir, *, inputs=()):
        data = prompt.encode("utf-8")
        execution = adapters.ExecutionSpec(spec.adapter_id, ("NEVER_EXECUTED", spec.pid), prompt,
                                            adapters.STDIN, hashlib.sha256(data).hexdigest(), len(data))
        return contract.Plan(self.kind, execution, work_dir, None, "m", revision="offline-review-probe")

    def run(self, plan, timeout, *, cancel=None):
        pid = plan.spec.argv[1]
        self.started.append(pid)
        if pid != "synthesis":
            text = "fixed independent draft"
        else:
            self.synth_count += 1
            match = re.search(r"<<<(D\d+) 시작>>>\n(.*?)\n<<<\1 끝>>>", plan.spec.stdin_text, re.S)
            text = json.dumps({"claims": [{"statement": "synthesis " + str(self.synth_count),
                               "quotes": [{"draft": match[1], "text": match[2]}]}],
                               "unresolved": [], "disagreements": [],
                               "strongest_counterexample": None,
                               "recommendation": "synthetic recommendation"})
            if self.bad_answer:
                text = "not valid synthesis JSON"
        models = {"m": {}}
        if self.bad_metadata:
            # JSON is ASCII-safe; the product's real parser accepts both keys.
            # A normal requested model remains present, so model_match is True.
            models["\ud800"] = {}
        stdout = json.dumps({"type": "result", "is_error": False, "result": text, "modelUsage": models})
        result = runner.RunResult(("NEVER_EXECUTED",), runner.EXITED, 0, stdout, "", False, False,
                                  1, 0, True, containment=runner.JOB_OBJECT,
                                  input_delivery=runner.INPUT_COMPLETE)
        outcome = adapters.interpret("claude-code", result, requested_model="m")
        self.results.append({"pid": pid, "acceptance": c.acceptance(result, outcome),
                             "tree_confirmed_empty": result.tree_confirmed_empty,
                             "model_match": outcome.model_match})
        return result, outcome


def opened(name, executor, **kwargs):
    temporary = tempfile.TemporaryDirectory(prefix="controller-probe-" + name + "-", dir=BASE)
    TEMPS.append(temporary)
    root = Path(temporary.name).resolve()
    assert root.parent == BASE, "temporary probe escaped output directory"
    store = Store(root / "journal.db")
    ctl = c.Controller(store, executor, work_root=str(root / "work"), **kwargs)
    return root, store, ctl


def participant():
    return c.ParticipantSpec("draft", "Draft", "probe", c.CLI, "claude-code", "m")


def create_revealed(ctl):
    rid = ctl.create_run("source-first architecture probe", [participant()], min_independent=1)
    assert ctl.wait_idle(5)
    assert ctl.view(rid)["runs"][0]["phase"] == "revealed"
    return rid


def human_review_after_new_synthesis():
    ex = OfflineExecutor()
    root, store, ctl = opened("human-review", ex)
    try:
        rid = create_revealed(ctl)
        ctl.synthesize_with_model(rid, "claude-code")
        assert ctl.wait_idle(5)
        ctl.mark_reviewed(rid)
        before = ctl.view(rid)
        ctl.synthesize_with_model(rid, "claude-code")
        assert ctl.wait_idle(5)
        after = ctl.view(rid)
        ev = list(events(store, rid))
        assert before["tasks"][0]["status"] == "done", "positive control review not recorded"
        assert after["tasks"][0]["status"] == "done", "counterexample no longer reproduces: new result reopens task"
        assert after["runs"][0]["reviewed"] is True
        assert after["runs"][0]["synthesis"]["claims"][0]["statement"] == "synthesis 2"
        assert len([e for e in ev if e["kind"] == "human_reviewed"]) == 1
        return {"before_task_status": before["tasks"][0]["status"],
                "after_task_status": after["tasks"][0]["status"],
                "after_reviewed": after["runs"][0]["reviewed"],
                "new_claim": after["runs"][0]["synthesis"]["claims"][0]["statement"],
                "review_seq": [e["seq"] for e in ev if e["kind"] == "human_reviewed"],
                "completed_seq": [e["seq"] for e in ev if e["kind"] == "synthesis_completed"],
                "temporary_ledger_cleaned": True}
    finally:
        ctl.shutdown(5)
        store.close()


def synthesis_surrogate_metadata():
    ex = OfflineExecutor(bad_metadata=True)
    root, store, ctl = opened("surrogate", ex)
    start_errors = len(THREAD_ERRORS)
    THREAD_ERROR_SEEN.clear()
    try:
        rid = create_revealed(ctl)
        draft = ctl.view(rid)["runs"][0]["participants"][0]
        ctl.synthesize_with_model(rid, "claude-code")
        assert ctl.wait_idle(5)
        assert THREAD_ERROR_SEEN.wait(5), "expected storage encoding error did not occur"
        view = ctl.view(rid)
        ev = list(events(store, rid))
        assert draft["state"] == "accepted" and draft["result"].get("escaped_text") is True
        assert all(r["acceptance"][0] == "accepted" and r["tree_confirmed_empty"] is True
                   and r["model_match"] is True for r in ex.results)
        assert view["runs"][0]["model_synthesis"]["status"] == "unknown", "counterexample no longer reproduces"
        assert view["slots"]["used"] == 1 and ctl.unsettled() == 1
        assert [e["kind"] for e in ev if e["kind"].startswith("synthesis_")] == ["synthesis_started"]
        assert THREAD_ERRORS[start_errors:] and THREAD_ERRORS[start_errors]["type"] == "UnicodeEncodeError"
        return {"draft_state": draft["state"], "draft_metadata_escaped": draft["result"].get("escaped_text"),
                "execution_results": ex.results,
                "synthesis_state": view["runs"][0]["model_synthesis"],
                "slots_used": view["slots"]["used"], "unsettled": ctl.unsettled(),
                "synthesis_events": [e["kind"] for e in ev if e["kind"].startswith("synthesis_")],
                "thread_errors": THREAD_ERRORS[start_errors:], "temporary_ledger_cleaned": True}
    finally:
        ctl.shutdown(5)
        store.close()


def filesystem_head_of_line():
    ex = OfflineExecutor()
    root, store, ctl = opened("workdir", ex)
    try:
        preview = ctl.prepare_run("first", [participant()], min_independent=1)
        blocker = root / "work" / preview["run_id"] / "draft"
        blocker.parent.mkdir(parents=True)
        blocker.write_text("ordinary existing file occupies participant work directory", encoding="utf-8")
        errors = []
        for question, options in (("first", {"run_id": preview["run_id"], "confirmation": preview["confirmation"]}),
                                  ("second", {})):
            try:
                ctl.create_run(question, [participant()], min_independent=1, **options)
            except Exception as exc:
                errors.append({"request": question, "type": type(exc).__name__})
        assert [e["type"] for e in errors] == ["FileExistsError", "FileExistsError"], "counterexample no longer reproduces"
        assert not ex.started
        assert len(store.rows("SELECT * FROM runs")) == 2
        assert [r["state"] for r in store.rows("SELECT state FROM participants")] == ["queued", "queued"]
        return {"errors": errors, "started": ex.started,
                "runs": [dict(r) for r in store.rows("SELECT question, phase FROM runs ORDER BY created_at")],
                "participants": [dict(r) for r in store.rows("SELECT state, status FROM participants")],
                "event_kinds": [r["kind"] for r in store.rows("SELECT kind FROM events ORDER BY run_id,seq")],
                "temporary_ledger_cleaned": True}
    finally:
        ctl.shutdown(5)
        store.close()


def failed_synthesis_reviewed():
    ex = OfflineExecutor(bad_answer=True)
    root, store, ctl = opened("failed-review", ex)
    try:
        rid = create_revealed(ctl)
        ctl.synthesize_with_model(rid, "claude-code")
        assert ctl.wait_idle(5)
        ctl.mark_reviewed(rid)
        view = ctl.view(rid)
        assert view["runs"][0]["reviewed"] is True and view["tasks"][0]["status"] == "problem"
        assert view["runs"][0]["model_synthesis"]["status"] == "failed"
        return {"reviewed": view["runs"][0]["reviewed"], "task_status": view["tasks"][0]["status"],
                "action": view["tasks"][0]["runs"][0]["action"],
                "synthesis_state": view["runs"][0]["model_synthesis"]["status"],
                "temporary_ledger_cleaned": True}
    finally:
        ctl.shutdown(5)
        store.close()


try:
    result = {"scope": "synthetic in-process execution only; no real process/model/CLI/install/network",
              "source_sha": source_revision(), "python": sys.version.split()[0],
              "source_digests": {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest()
                                 for name in ("app/controller.py", "app/store.py", "app/state.py",
                                              "app/roles.py", "app/synthesis.py", "core/adapters.py")},
              "human_review_after_new_synthesis": human_review_after_new_synthesis(),
              "synthesis_surrogate_metadata": synthesis_surrogate_metadata(),
              "filesystem_head_of_line": filesystem_head_of_line(),
              "failed_synthesis_reviewed": failed_synthesis_reviewed()}
finally:
    # Verify each absolute deletion target is a newly created direct child of BASE.
    for temporary in TEMPS:
        target = Path(temporary.name).resolve()
        assert target.parent == BASE and target.name.startswith("controller-probe-"), "unsafe cleanup target"
        temporary.cleanup()
        assert not target.exists(), "probe temporary directory was not cleaned"
OUTPUT.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=True, indent=2))
