"""Drive the real app once over its HTTP API and always stop the server (2026-09-25, aux-pc-wsl).

Uses subscription model calls. Every run needs a new ledger folder that does not exist yet; the live config's
call budgets are fixed in that ledger on first use. The token and HOME path never reach the printed summary.

  python3 drive.py strict --ledger <new folder> --config <live.json> --question <text> --synthesizer codex
  python3 drive.py cancel --ledger <new folder> --config <live.json> --question <text>

strict: both configured providers answer under independent_only with min_independent 2, then one model synthesis.
cancel: one provider answers under independent_only with min_independent 1; the run is cancelled as soon as the
        participant is running, and the summary shows how the attempt ended and what the ledger kept.
"""
import argparse, http.client, json, os, re, signal, socket, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOME = os.path.expanduser("~")


def scrub(value):
    text = json.dumps(value, ensure_ascii=False).replace(HOME, "~")
    return json.loads(re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<uuid>", text))


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
    ap.add_argument("mode", choices=("strict", "cancel"))
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--question", required=True)
    ap.add_argument("--synthesizer", choices=("codex", "claude-code"))
    ap.add_argument("--mock", action="store_true", help="dry run against the mock server; no model call")
    args = ap.parse_args()
    if args.ledger.exists():
        sys.exit("the ledger folder must be new")
    summary = {"mode": args.mode, "mock": args.mock,
               "model_calls_expected": 0 if args.mock else (1 if args.mode == "cancel" else 2 + bool(args.synthesizer))}
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
        else:  # 모의 시험에서는 끝나지 않는 가짜 CLI로 취소할 틈을 만든다
            participants, minimum = [{"pid": "codex", **({"behavior": "hang"} if args.mock else {})}], 1
        status, created = app.call("POST", "/api/runs", {"question": args.question, "participants": participants,
                                                         "min_independent": minimum,
                                                         "quorum_policy": "independent_only"})
        assert status == 200, created
        run_id = created["run_id"]
        timeline = []
        if args.mode == "cancel":
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                run, _ = app.run(run_id)
                states = [p["state"] for p in run["participants"]]
                if "running" in states:
                    break
                time.sleep(0.1)
            timeline.append({"before_cancel": states})
            status, answer = app.call("POST", f"/api/runs/{run_id}/cancel", {})
            timeline.append({"cancel_http": status, "answer": answer})
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
        keep = ("pid", "state", "status", "independence", "execution", "adapter_id", "requested_model")
        summary.update(
            run_phase=run["phase"], gate=run.get("gate", {}).get("status"), quorum=run.get("quorum"),
            participants=[{**{k: p.get(k) for k in keep},
                           "result": {k: (p.get("result") or {}).get(k) for k in (
                               "state", "exit_code", "containment", "tree_confirmed_empty", "input_delivery",
                               "status", "ok", "model_match", "reported_models", "duration_ms")}}
                          for p in run["participants"]],
            model_synthesis=run.get("model_synthesis"), synthesis_mode=(run.get("synthesis") or {}).get("mode"),
            synthesis_status=(run.get("synthesis") or {}).get("status"),
            synthesis_checks=(run.get("synthesis") or {}).get("checks"),
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
    print(text)


if __name__ == "__main__":
    main()
