"""Offline architecture probes: mock process APIs and synthetic files only."""
from __future__ import annotations
from datetime import date
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest import mock

repo, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
sys.path.insert(0, str(repo))
from core import runner, adapters, contract, isolation, eligibility
from app import registration, cli_executor
from app import controller
from app.store import Store, events

results = []
output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="core-architecture-", dir=output) as td:
    temp = Path(td)
    # No actual child. Simulate resource exhaustion immediately after Popen.
    proc = mock.Mock(pid=424242, stdout=object(), stderr=object(), stdin=None)
    tree = mock.Mock(note=None)
    reader = mock.Mock()
    reader.start.side_effect = RuntimeError("can't start new thread (synthetic)")
    with mock.patch.object(runner.subprocess, "Popen", return_value=proc) as popen, \
         mock.patch.object(runner, "_Tree", return_value=tree), \
         mock.patch.object(runner, "_Reader", return_value=reader):
        try:
            runner._execute((str(temp / "synthetic-cli"),), cwd=temp, env={}, timeout=1,
                            stdin_text=None, max_output_bytes=1024, cancel=None, pid_namespace=False)
        except RuntimeError as exc:
            failed = str(exc)
        else:
            raise AssertionError("expected synthetic thread start failure")
    assert popen.call_count == 1 and tree.kill.call_count == 0 and tree.close.call_count == 0
    results.append({"id":"R1-post-spawn-thread-failure", "exception":failed,
                    "mockPopen":popen.call_count,"treeKill":tree.kill.call_count,
                    "treeClose":tree.close.call_count,"actualProcesses":0})

    # Two reads in one eligibility check can attest different manifest bytes.
    seen = {"status":"observed","observed_at":date.today().isoformat(),"evidence":"synthetic"}
    observed = {**seen,"spec_revision":"claude-code@synthetic"}
    row = {"adapter_id":"claude-code","installed":{**seen,"version":"9.9.9"},
           "auth_observed":{**seen,"auth_mode":"subscription_oauth","funding_mode":"subscription"},
           **{name:dict(observed) for name in eligibility.SPEC_BOUND}}
    eligible = {"schema":eligibility.SCHEMA,"adapters":[row]}
    invalid = copy.deepcopy(eligible);invalid["adapters"][0]["permission_conformance"]={"status":"unknown"}
    a, b = json.dumps(eligible).encode(), json.dumps(invalid).encode()
    manifest, registry = temp / "manifest.json", temp / "registry.json"
    manifest.write_bytes(a)
    registry.write_text(json.dumps({"schema":registration.SCHEMA,"entries":[
        {"manifest_sha256":hashlib.sha256(b).hexdigest(),"fingerprint":"synthetic-machine"}]}),encoding="utf-8")
    executor=cli_executor.CliExecutor(never=(),inventory=manifest,home=str(temp),base_env={"PATH":""})
    original_eligibility=eligibility.eligibility
    def swap_after_verdict(*args, **kwargs):
        result=original_eligibility(*args,**kwargs)
        manifest.write_bytes(b)
        return result
    with mock.patch.object(registration,"fingerprint",return_value="synthetic-machine"), \
         mock.patch.object(registration,"registry_path",return_value=registry):
        initially_registered=registration.problem(manifest) is None
        with mock.patch.object(eligibility,"eligibility",side_effect=swap_after_verdict):
            executor._check_eligible("claude-code",str(temp / "versions" / "9.9.9"),"claude-code@synthetic")
        final_eligible=original_eligibility(eligibility.load(manifest),"claude-code",enabled=True,today=date.today(),
            current_version="9.9.9",spec_revision="claude-code@synthetic").eligible
    assert initially_registered is False and final_eligible is False
    results.append({"id":"R2-split-manifest-snapshot","firstBytesRegistered":False,
                    "secondBytesEligible":False,"combinedCheckAccepted":True,"actualProcesses":0})

    # Frozen dataclasses are shallow; a recorded template and shared env remain mutable.
    spec=adapters.ExecutionSpec("codex",(str(temp / "fake"),"exec","--model","m","-"),
                               "question",adapters.STDIN,hashlib.sha256(b"question").hexdigest(),8)
    mutable_env={"LANG":"C.UTF-8"}
    box=isolation.Sandbox(str(temp / "work"),str(temp / "home"),env=mutable_env)
    tmpl=contract.template(spec,box,home=str(temp / "home"))
    plan=contract.Plan(contract.REAL,spec,str(temp / "work"),box,"m",revision=contract.revision(tmpl),template=tmpl)
    saved=plan.record()
    original_revision=plan.revision
    mutable_env["CODEX_HOME"]="/synthetic/alternate-cli-state"
    revised=contract.revision(contract.template(spec,box,home=str(temp / "home")))
    saved["template"]["argv"].append("synthetic-record-mutation")
    assert revised == original_revision and plan.template["argv"][-1] == "synthetic-record-mutation"
    results.append({"id":"R3-plan-shallow-freeze","environmentMutationKeepsRevision":True,
                    "recordMutationChangesPlanTemplate":True,"actualProcesses":0,
                    "scope":"Public core Plan/Sandbox contract; no current UI exploit demonstrated"})

    # Plan does not validate input existence/mount conflicts. No auth/CLI access: all resolution mocked.
    ex=cli_executor.CliExecutor(never=(),unchecked=True,home=str(temp),base_env={"PATH":""})
    participant=SimpleNamespace(adapter_id="claude-code",model="claude-test")
    missing=str(temp / "does-not-exist")
    with mock.patch.object(cli_executor.core_env,"resolve",return_value=str(temp / "versions" / "9.9.9")), \
         mock.patch.object(isolation,"participant_mounts",return_value=((),(),())), \
         mock.patch.object(isolation,"plan",side_effect=AssertionError("must not be called")) as validate:
        planned=ex.plan(participant,"question",str(temp),inputs=(missing,))
    assert validate.call_count == 0 and missing in planned.box.read_only and not Path(missing).exists()
    results.append({"id":"R4-plan-defers-isolation-validation","planReturnedForMissingInput":True,
                    "isolationPlanCalls":validate.call_count,"actualProcesses":0})
    ex.default_inputs=(missing,)
    store=Store(temp / "ledger" / "journal.db")
    ctl=controller.Controller(store,ex,work_root=str(temp / "attempt-work"),timeout=1,max_real_calls=1)
    try:
        with mock.patch.object(cli_executor.core_env,"resolve",return_value=str(temp / "versions" / "9.9.9")), \
             mock.patch.object(isolation,"participant_mounts",return_value=((),(),())), \
             mock.patch.object(isolation,"run",side_effect=isolation.IsolationError("synthetic missing input")):
            run_id=ctl.create_run("question",[controller.ParticipantSpec("claude","Claude","anthropic",controller.CLI,
                 "claude-code","claude-test")],min_independent=1)
            assert ctl.wait_idle(5)
        reserved=sum(e["kind"]=="live_call_reserved" for e in events(store,run_id))
        part=store.row("SELECT state,status FROM participants WHERE run_id=?",run_id)
        assert reserved==1 and part["status"]=="process_failed_to_start"
        results[-1].update({"controllerLiveReservations":reserved,"finalState":part["state"],"finalStatus":part["status"],
                           "note":"Isolation execution was mocked to refuse before process creation; no refunds proposed."})
    finally:
        ctl.shutdown(5)
        store.close()

report={"reviewedHead":"a232de7d4ae7de097dd014be5a791348b7881ea3","python":sys.version.split()[0],
        "results":results,"limits":"Synthetic/mocked probes only. No model CLI, auth, real home, Linux isolation or process execution."}
(output / "core-probe-results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
