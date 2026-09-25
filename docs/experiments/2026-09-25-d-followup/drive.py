"""Drive the real app once over its HTTP API and always stop the server (2026-09-25, aux-pc-wsl).

D follow-up (card #60). Copy of docs/experiments/2026-09-25-source-injection/drive.py with three changes:
  - a `single` mode: one provider answers alone under independent_only with min_independent 1;
  - the question is read by key from questions.json next to this file (no shell quoting of multi-line text);
  - the summary adds the run's input digest, the CLI-reported usage, the Claude rate-limit status (whether any
    window is at 80% or more, not the numbers) and the synthesizer's outcome;
  - the printed copy leaves out time and token counts, which hint at draft length: the session grades blind
    before it reads the full summary file (drive-summary.json in the ledger).
The cancel mode is dropped. The summary still never holds a draft, the synthesis text, the token or the HOME path.

Uses subscription model calls. Every run needs a new ledger folder that does not exist yet; the live config's
call budgets are fixed in that ledger on first use.

  python3 drive.py strict --ledger <new folder> --config <live.json> --question-key T1 --synthesizer codex
  python3 drive.py single --ledger <new folder> --config <live.json> --question-key T4 --participant codex
  python3 drive.py strict --ledger <new folder> --config <live.json> --question-key grade --sources-dir <pack>
"""
import argparse, http.client, json, os, re, signal, socket, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
HOME = os.path.expanduser("~")


def scrub(value):
    text = json.dumps(value, ensure_ascii=False).replace(HOME, "~")
    return json.loads(re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<uuid>", text))


def limit_status(limit):
    """계정 한도는 공개 기록에 수치를 올리지 않는다. 상태와 80% 이상인 창이 있었는지만 남긴다."""
    if not limit:
        return None
    used = [w.get("utilization") for w in limit.get("windows") or [] if w.get("utilization") is not None]
    return {"status": limit.get("status"), "any_window_at_or_above_80": any(u >= 0.8 for u in used)}


class App:
    def __init__(self, port, token):
        self.port, self.token = port, token

    def call(self, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            data = None if body is None else json.dumps(body).encode()
            headers = {"Host": f"127.0.0.1:{self.port}", "Authorization": f"Bearer {self.token}"}
            if data is not None:
                headers.update({"Content-Type": "application/json", "Content-Length": str(len(data))})
            conn.request(method, path, data, headers)
            response = conn.getresponse()
            return response.status, json.loads(response.read() or b"null")
        finally:
            conn.close()

    def run(self, run_id):
        status, state = self.call("GET", "/api/state")
        assert status == 200, state
        return next(r for r in state["runs"] if r["run_id"] == run_id), state


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("strict", "single"))
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--question-key", required=True, help="key in questions.json next to this file")
    ap.add_argument("--synthesizer", choices=("codex", "claude-code"))
    ap.add_argument("--participant", choices=("codex", "claude"), help="single mode: who answers")
    ap.add_argument("--mock", action="store_true", help="dry run against the mock server; no model call")
    ap.add_argument("--sources-dir", type=Path, help="attach every regular file here as a shared source")
    args = ap.parse_args()
    if args.ledger.exists():
        sys.exit("the ledger folder must be new")
    if (args.mode == "single") != (args.participant is not None) or (args.mode == "single" and args.synthesizer):
        sys.exit("single needs --participant and no --synthesizer; strict takes no --participant")
    question = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))[args.question_key]
    summary = {"mode": args.mode, "mock": args.mock, "question_key": args.question_key,
               "model_calls_expected": 0 if args.mock else (1 if args.mode == "single" else 2 + bool(args.synthesizer))}
    live = [] if args.mock else ["--live-config", str(args.config), "--timeout", "180"]
    if not args.mock:
        check = subprocess.run([sys.executable, "-m", "app.server", "--check-config", str(args.config),
                                "--data-dir", str(args.ledger / "readiness")], cwd=REPO, capture_output=True, text=True)
        summary["readiness"] = {"exit": check.returncode, **{k: v for k, v in json.loads(check.stdout).items()
                                                            if k in ("eligible", "model_calls")}}
        if check.returncode != 0:
            print(json.dumps(scrub(summary), ensure_ascii=False, indent=1))
            sys.exit(2)
    port = free_port()
    args.ledger.mkdir(parents=True, exist_ok=True)
    log = open(args.ledger / "server.log", "w", encoding="utf-8")   # 파이프를 읽지 않아 서버가 막히는 일이 없게
    server = subprocess.Popen([sys.executable, "-u", "-m", "app.server", *live,
                              "--data-dir", str(args.ledger / "data"), "--port", str(port)],
                             cwd=REPO, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        token = None
        deadline = time.monotonic() + 30
        while token is None and time.monotonic() < deadline and server.poll() is None:
            found = re.search(r"#token=(\S+)", (args.ledger / "server.log").read_text(encoding="utf-8"))
            token = found.group(1) if found else None
            time.sleep(0.2)
        if token is None:
            raise RuntimeError("the server did not print its address")
        app = App(port, token)
        if args.mode == "strict":
            participants, minimum = [{"pid": "codex"}, {"pid": "claude"}], 2
        else:
            participants, minimum = [{"pid": args.participant}], 1
        sources = ([{"name": p.name, "text": p.read_text(encoding="utf-8")}
                    for p in sorted(args.sources_dir.iterdir()) if p.is_file()] if args.sources_dir else [])
        status, created = app.call("POST", "/api/runs", {"question": question, "participants": participants,
                                                         "min_independent": minimum,
                                                         "quorum_policy": "independent_only", "sources": sources})
        summary["sources"] = [item["name"] for item in sources]
        assert status == 200, created
        run_id = created["run_id"]
        timeline = []
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            run, state = app.run(run_id)
            states = [p["state"] for p in run["participants"]]
            if run["phase"] == "revealed" or all(s in ("accepted", "rejected", "unknown") for s in states):
                break
            time.sleep(2)
        if args.mode == "strict" and run["phase"] == "revealed" and args.synthesizer:
            status, answer = app.call("POST", f"/api/runs/{run_id}/synthesize",
                                      {"mode": "model", "adapter_id": args.synthesizer})
            timeline.append({"synthesize_http": status, "answer": answer})
            deadline = time.monotonic() + (400 if status == 200 else 0)   # 거절되면 기다릴 것이 없다
            while time.monotonic() < deadline:
                run, state = app.run(run_id)
                current = (run.get("model_synthesis") or {}).get("status")
                if current not in (None, "running"):
                    break
                time.sleep(2)
        run, state = app.run(run_id)
        status, report = app.call("GET", f"/api/runs/{run_id}/report")
        (args.ledger / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        (args.ledger / "view.json").write_text(json.dumps(run, ensure_ascii=False, indent=1), encoding="utf-8")
        keep = ("pid", "state", "status", "independence", "execution", "adapter_id")
        synthesis = run.get("synthesis") or {}
        synthesizer = synthesis.get("synthesizer") or {}
        summary.update(
            input_sha256=run.get("input_sha256"), input_bytes=run.get("input_bytes"),
            run_phase=run["phase"], gate=run.get("gate", {}).get("status"), quorum=run.get("quorum"),
            participants=[{**{k: p.get(k) for k in keep},
                           "result": {**{k: (p.get("result") or {}).get(k) for k in (
                               "state", "exit_code", "containment", "tree_confirmed_empty", "input_delivery",
                               "status", "ok", "model_match", "reported_models", "duration_ms", "usage")},
                               "rate_limit": limit_status((p.get("result") or {}).get("rate_limit"))}}
                          for p in run["participants"]],
            model_synthesis=run.get("model_synthesis"), synthesis_mode=synthesis.get("mode"),
            synthesis_status=synthesis.get("status"), synthesis_checks=synthesis.get("checks"),
            synthesizer={**{k: synthesizer.get(k) for k in (
                "adapter_id", "execution", "started", "state", "status", "revision", "duration_ms",
                "tree_confirmed_empty", "reported_models", "model_match", "usage")},
                "rate_limit": limit_status(synthesizer.get("rate_limit"))} if synthesizer else None,
            live_call_budget=state.get("live_call_budget"), slots=state.get("slots"),
            unsettled=state.get("unsettled"), timeline=timeline, report_http=status)
    finally:
        if server.poll() is None:
            os.killpg(server.pid, signal.SIGINT)
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid, signal.SIGKILL)
                server.wait(timeout=5)
        log.close()
        text = (args.ledger / "server.log").read_text(encoding="utf-8")
        (args.ledger / "server.log").write_text(re.sub(r"#token=\S+", "#token=<hidden>", text), encoding="utf-8")
        summary["server"] = {"exit": server.returncode, "port_still_open": port_open(port)}
    text = json.dumps(scrub(summary), ensure_ascii=False, indent=1)
    (args.ledger / "drive-summary.json").write_text(text + "\n", encoding="utf-8")
    print(json.dumps(blind_copy(scrub(summary)), ensure_ascii=False, indent=1))


def blind_copy(summary):
    """화면에 찍는 사본. 시간·토큰 수는 초안 길이를 짐작하게 하므로 빼고, 멈춤 조건에 필요한 칸은 남긴다."""
    hidden = {"duration_ms", "usage"}
    copy = json.loads(json.dumps(summary))
    for part in copy.get("participants") or []:
        part["result"] = {k: v for k, v in part["result"].items() if k not in hidden}
    if copy.get("synthesizer"):
        copy["synthesizer"] = {k: v for k, v in copy["synthesizer"].items() if k not in hidden}
    return copy


if __name__ == "__main__":
    main()
