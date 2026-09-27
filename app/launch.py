"""바탕 화면 아이콘으로 여는 앱의 WSL 쪽 입구. 실제 두 참여자(Codex·Claude)를 붙인 화면 서버를 띄우고 끈다.

사용자는 터미널을 보지 않는다(인계 2절 22). Windows의 [start.ps1](start.ps1)이 이 모듈을 부른다:

  python3 -m app.launch serve [--mock]   # 준비 조회 → 원장 고르기 → 서버. 끝날 때까지 앞에서 돈다
  python3 -m app.launch url [--wait 90]  # 서버가 뜰 때까지 기다렸다가 열 주소를 JSON 한 줄로
  python3 -m app.launch stop [--wait 20] # 끄기 요청. 돌던 참여자·합성이 끝나면 서버가 스스로 멈춘다
  python3 -m app.launch cancel-stop      # 끄기 요청 취소(창을 다시 연 경우)
  python3 -m app.launch status

서버·준비 조회·원장·호출 상한·봉인 규칙은 app.server 그대로다. 이 모듈이 정하는 것은 셋뿐이다.

- **관측 기록**: 저장소의 `docs/reviews/*/manifest.v2.json` 가운데 이 기기에 등록된 가장 새 기록(`updated_at`).
  재관측해 등록하면 다음에 열 때 저절로 그 기록을 쓴다. 준비 조회가 거절하면 서버를 띄우지 않고 이유를 남긴다.
- **모델**: 기본은 `MODELS`. 실험(L1·긴 자료)과 같은 이름이다. 바꾸려면 `--codex-model`·`--claude-model`.
  역할판에서 고를 수 있는 모델은 `MODEL_CHOICES`이고, 항목마다 과금 경로와 근거를 적는다(app.live_config).
  기본 모델도 그 목록에 고를 수 있는 항목으로 있어야 한다 — 목록 밖 모델을 인자로 주면 시작하지 않는다.
- **원장**: `<상태 폴더>/live/<시각>`. 가장 새 원장에 provider마다 호출이 남아 있으면 이어 쓰고(앞 실행이 보인다),
  하나라도 다 썼으면 새 원장을 만든다. 원장 하나의 상한은 `CAPS`(Codex 5·Claude 5, 앱의 최대 10)이고 첫 호출에
  고정된다. 앞 원장은 지우지 않는다 — 상한을 늘리는 것이 아니라 새 상한으로 새 기록을 여는 것이다.

끄기는 창을 닫으면 start.ps1이 요청한다. 돌던 호출을 끊지 않으려고 서버는 controller가 쉬고 있을 때만
(`wait_idle(0)`) 요청 받기를 멈추고 `server.serve_until_stopped`의 정상 종료 순서로 닫는다.
토큰은 원장의 `control-token`(0600)에만 있고 이 모듈의 상태 파일·로그에는 쓰지 않는다.

**소유(카드 #120, AH-07)**: serve는 상태 폴더의 `launcher.lock`을 배타 잠금으로 잡은 쪽만 서버를 띄우고, 끝날 때까지
쥔다. 동시에 연 두 번째 serve는 상태 파일·로그·끄기 요청을 건드리지 않고 `lost-<nonce>` 표시만 남긴 채 물러난다.
그 nonce로 기다리던 url은 그 표시를 보고 살아 있는 서버의 주소를 "합류"로 돌려준다. stop --nonce는 그 nonce의 서버에만
끄기를 요청하고, 끄기 요청 파일에는 대상 pid를 적어 다른 서버가 받지 않게 한다.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "dml-launcher/1"
MODELS = {"codex": "gpt-6-luna", "claude-code": "claude-sonnet-5"}
# 역할판의 모델 목록(카드 #119). 고를 수 있는 것은 구독 포함 한도로 쓴 근거가 있는 것뿐이다. 나머지는 이유와 함께
# 막힌 채로 보인다 — 쓰려면 근거를 확인해 funding을 바꾸는 PR을 낸다. 모델을 불러 과금 경로를 알아내지 않는다.
# (model, funding, basis). funding: included | credits | unconfirmed(app.live_config).
MODEL_CHOICES = {
    "codex": (("gpt-6-luna", "included", "구독 로그인으로 관측·실험에 쓴 모델(재관측 2026-09-25·26, 서빙 모델은 미보고 K32)"),
              ("gpt-6-astra", "unconfirmed", "이 기기의 참여자로 관측하지 않았고 구독 포함 여부를 확인하지 않았다")),
    "claude-code": (("claude-sonnet-5", "included", "구독 로그인으로 관측·실험에 쓴 모델(재관측 2026-09-25·26, 요청=보고)"),
                    ("claude-opus-5-5", "unconfirmed", "이 기기의 참여자로 관측하지 않았고 구독 포함 여부를 확인하지 않았다"),
                    ("claude-fable-5-1", "credits", "공식 문서: 계정에 따라 추가 크레딧(usage credits)으로 청구된다")),
}
CAPS = {"codex": 5, "claude-code": 5}
PORTS = range(8765, 8775)
TIMEOUT = 180.0


def state_dir() -> Path:
    override = os.environ.get("DML_LAUNCHER_DIR")
    if override:
        return Path(override)
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "decision-model-lab" / "app"


def _paths() -> dict[str, Path]:
    root = state_dir()
    return {"root": root, "state": root / "launcher.json", "stop": root / "stop-request", "lock": root / "launcher.lock",
            "log": root / "server.log", "live": root / "live", "mock": root / "mock", "inputs": root / "inputs"}


def _write_state(data: dict) -> None:
    path = _paths()["state"]
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump({"schema": SCHEMA, **data}, handle, ensure_ascii=False, indent=1)
        temp = Path(handle.name)
    temp.chmod(0o600)
    os.replace(temp, path)


_OWNER: int | None = None   # 이 프로세스가 쥔 launcher.lock의 fd. 프로세스가 끝나면 풀린다


def _acquire_owner() -> bool:
    """launcher.lock을 배타·비차단으로 잡는다. 다른 serve가 쥐고 있으면 False — 상태를 쓰지 않고 물러난다."""
    global _OWNER
    if _OWNER is not None:
        return True
    import fcntl   # Linux 전용(main이 다른 플랫폼을 거절한다). 모듈 머리에서 들이면 Windows에서 시험을 못 읽는다
    fd = os.open(_paths()["lock"], os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return False
    _OWNER = fd
    return True


def _lost(nonce: str) -> Path | None:
    """동시 시작에서 물러난 serve의 표시 파일. nonce가 비었거나 이름에 못 쓰는 글자가 있으면 None."""
    return _paths()["root"] / f"lost-{nonce}" if nonce and nonce.isascii() and nonce.isalnum() else None


def read_state() -> dict:
    try:
        data = json.loads(_paths()["state"].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) and data.get("schema") == SCHEMA else {}


def _alive(pid) -> bool:
    """그 pid가 살아 있고 이 모듈의 serve인가. 재부팅 뒤 같은 번호의 다른 프로세스를 우리 서버로 보지 않는다."""
    if type(pid) is not int or pid <= 0:
        return False
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    except OSError:
        return False
    return b"app.launch" in cmdline and b"serve" in cmdline


def _listening(port) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except (OSError, TypeError):
        return False


def pick_manifest(root: Path = ROOT) -> Path | None:
    """이 기기에 등록된 관측 기록 가운데 가장 새 것. 등록은 사람이 관측한 기기에서 한다(app.registration)."""
    from app import registration
    found = []
    for path in (root / "docs" / "reviews").glob("*/manifest.v2.json"):
        try:
            updated = json.loads(path.read_text(encoding="utf-8")).get("updated_at") or ""
        except (OSError, ValueError, AttributeError):
            continue
        if registration.problem(path) is None:
            found.append((str(updated), path.parent.name, path))
    return max(found)[2] if found else None


def _has_room(journal: Path, caps: dict[str, int]) -> bool:
    """원장에 provider마다 호출이 하나 이상 남았고 고정된 상한이 지금 CAPS와 같은가. 읽기만 한다."""
    try:
        db = sqlite3.connect(f"file:{journal}?mode=ro", uri=True)
    except sqlite3.Error:
        return False
    try:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        saved = db.execute("SELECT cap, provider_caps FROM live_budget").fetchone() if "live_budget" in tables else None
        if saved is None:
            return "events" in tables and not db.execute(
                "SELECT 1 FROM events WHERE kind = 'live_call_reserved' LIMIT 1").fetchone()
        if saved[0] != sum(caps.values()) or json.loads(saved[1]) != caps:
            return False
        used: dict[str, int] = {}
        for (payload,) in db.execute("SELECT payload FROM events WHERE kind = 'live_call_reserved'"):
            adapter = json.loads(payload).get("adapter_id")
            used[adapter] = used.get(adapter, 0) + 1
        return sum(used.values()) < saved[0] and all(used.get(a, 0) < cap for a, cap in caps.items())
    except (sqlite3.Error, ValueError, TypeError, AttributeError):
        return False
    finally:
        db.close()


def pick_ledger(live_root: Path, caps: dict[str, int] = CAPS) -> Path:
    """호출이 남은 가장 새 원장, 없으면 새 원장 폴더(아직 만들지 않음)."""
    ledgers = sorted(p for p in live_root.glob("*") if (p / "journal.db").is_file()) if live_root.is_dir() else []
    if ledgers and _has_room(ledgers[-1] / "journal.db", caps):
        return ledgers[-1]
    name = time.strftime("%Y%m%d-%H%M%S")
    while (live_root / name).exists():
        time.sleep(1)
        name = time.strftime("%Y%m%d-%H%M%S")
    return live_root / name


def _empty_dir(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if any(path.iterdir()):
        raise ValueError(f"the participant input folder must stay empty: {path}")
    return path


def _watch(server, controller, stop_file: Path, interval: float = 1.0) -> None:
    """끄기 요청이 있고 controller가 쉬고 있으면 serve_forever를 멈춘다 — serve_until_stopped가 정상 순서로 닫는다.

    신호(SIGINT)를 쓰지 않는다: 스크립트가 뒤에서 띄운 프로세스는 SIGINT를 무시한 채 시작될 수 있다(2026-09-25 관측).
    server.shutdown()은 serve_forever와 다른 스레드에서 불러야 한다 — 이 감시 스레드가 그렇다.
    """
    while True:
        time.sleep(interval)
        try:
            target = stop_file.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if target not in ("", str(os.getpid())):   # 다른 서버를 향한 요청 — 받지 않는다(카드 #120)
            continue
        if controller.wait_idle(0):
            stop_file.unlink(missing_ok=True)
            server.shutdown()
            return


def _interrupt(_number, _frame):
    raise KeyboardInterrupt


def free_ports(avoid: str = "") -> list[int]:
    """PORTS에서 Windows 쪽 프로그램이 이미 듣고 있는 포트를 뺀다. WSL 안의 bind는 그 포트가 비어 있다고 보지만,
    Windows의 127.0.0.1:<포트>는 그 프로그램에 닿는다 — 앱 창이 다른 프로그램을 연다(2026-09-27, 8765에서 관측).
    start.ps1이 Windows에서 본 포트를 쉼표로 넘긴다. 숫자가 아닌 값은 거절한다."""
    skipped = set()
    for item in filter(None, (part.strip() for part in avoid.split(","))):
        if not item.isdecimal():
            raise ValueError(f"--avoid-ports takes port numbers, got {item!r}")
        skipped.add(int(item))
    return [port for port in PORTS if port not in skipped]


def serve(args) -> int:
    from app.live_config import ModelChoice, Provider
    from app.server import EXIT_NOT_ELIGIBLE, serve as start_server, serve_until_stopped
    paths = _paths()
    paths["root"].mkdir(mode=0o700, parents=True, exist_ok=True)
    # 소유 잠금을 가장 먼저 잡는다. 진 쪽은 상태 파일·로그·끄기 요청을 건드리지 않는다 — 살아 있는 서버의 기록을
    # 덮지 않는다(카드 #120, AH-07). 그 nonce로 기다리는 url이 합류하도록 표시만 남긴다.
    old = read_state()
    if not _acquire_owner() or (old.get("status") in ("starting", "running") and _alive(old.get("pid"))):
        lost = _lost(args.nonce)
        if lost is not None:
            lost.write_text(json.dumps({"schema": SCHEMA, "status": "already_running", "at": int(time.time())}),
                            encoding="utf-8")
        print(json.dumps({"ok": False, "reason": "already running"}))
        return 1
    paths["stop"].unlink(missing_ok=True)
    # 서버의 요청 기록·오류는 파일로 — 숨긴 창에서 돌므로 읽는 사람이 없는 파이프를 채우지 않는다.
    log = os.open(paths["log"], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.dup2(log, 1)
    os.dup2(log, 2)
    sys.stdout = os.fdopen(1, "w", encoding="utf-8", errors="replace", buffering=1, closefd=False)
    sys.stderr = os.fdopen(2, "w", encoding="utf-8", errors="replace", buffering=1, closefd=False)
    base = {"pid": os.getpid(), "mode": "mock" if args.mock else "live", "started_at": int(time.time()),
            "nonce": args.nonce}
    _write_state({**base, "status": "starting"})
    providers = None
    if args.mock:
        ledger = paths["mock"]
    else:
        manifest = pick_manifest()
        if manifest is None:
            _write_state({**base, "status": "refused", "reasons": [
                "이 기기에 등록된 관측 기록이 없다 — docs/SETUP.md 4절로 관측하고 등록한다"]})
            return EXIT_NOT_ELIGIBLE
        try:
            providers = tuple(Provider(adapter, model, manifest, CAPS[adapter], _empty_dir(paths["inputs"] / f"{adapter}-empty"),
                                       choices=tuple(ModelChoice(*item) for item in MODEL_CHOICES[adapter]))
                              for adapter, model in (("codex", args.codex_model), ("claude-code", args.claude_model)))
        except ValueError as exc:
            _write_state({**base, "status": "failed", "reasons": [str(exc)]})
            return 1
        ledger = pick_ledger(paths["live"])
        from app.readiness import check
        results = [check(p.adapter_id, p.model, p.inventory, ledger, input_dir=p.input_dir) for p in providers]
        base.update(manifest=str(manifest.relative_to(ROOT)), models={p.adapter_id: p.model for p in providers})
        if not all(r["eligible"] for r in results):
            _write_state({**base, "status": "refused",
                          "reasons": [f"{r['adapter_id']}: {reason}" for r in results for reason in r["reasons"]]})
            print(json.dumps({"mode": "readiness_only", "providers": results}, ensure_ascii=False, indent=1), flush=True)
            return EXIT_NOT_ELIGIBLE
    last = None
    try:
        ports = free_ports(args.avoid_ports)
    except ValueError as exc:
        _write_state({**base, "status": "failed", "reasons": [str(exc)]})
        return 1
    if not ports:
        _write_state({**base, "status": "failed", "reasons": [f"every port in {PORTS.start}..{PORTS.stop - 1} is used on the Windows side"]})
        return 1
    for port in ports:
        try:
            server, _token, controller = start_server(ledger, port, timeout=TIMEOUT, live_providers=providers)
            break
        except OSError as exc:        # 포트를 다른 프로그램이 쓰고 있다 — 다음 포트
            last = exc
    else:
        _write_state({**base, "status": "failed", "reasons": [f"no free port in {PORTS.start}..{PORTS.stop - 1} ({last})"]})
        return 1
    # LedgerBusy·StoreError는 OSError가 아니다. 위 반복을 빠져나오지 않고 여기까지 오지 않는다 — main이 받는다.
    port = server.server_address[1]
    print(f"{base['mode']} 서버 — 원장 {ledger}, 포트 {port}", flush=True)
    _write_state({**base, "status": "running", "port": port, "ledger": str(ledger), "paused": controller.paused})
    threading.Thread(target=_watch, args=(server, controller, paths["stop"]), daemon=True).start()
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):   # Ctrl+C·WSL이 닫힐 때도 같은 정상 종료 순서로
        signal.signal(number, _interrupt)
    code = serve_until_stopped(server, controller)
    _write_state({**base, "status": "stopped", "port": port, "ledger": str(ledger), "exit_code": code})
    return code


def url(args) -> int:
    """서버가 포트를 열 때까지 기다린 뒤 토큰이 든 주소를 표준 출력으로만 준다(파일에 쓰지 않는다)."""
    deadline = time.monotonic() + args.wait
    while True:
        state, joined = read_state(), False
        lost = _lost(args.nonce)
        if args.nonce and state.get("nonce") != args.nonce:
            if lost is not None and lost.exists():
                joined = True                # 이번 serve는 동시 시작에서 물러났다 — 살아 있는 서버에 합류한다
            else:
                state = {}                   # 아직 이번 serve의 상태가 아니다(앞 실행의 stopped 등)
        status, alive = state.get("status"), _alive(state.get("pid"))
        if status == "running" and alive and _listening(state.get("port")):
            try:
                token = (Path(state["ledger"]) / "control-token").read_text(encoding="utf-8").strip()
            except (OSError, KeyError, TypeError):
                token = ""
            if token:
                if joined:
                    lost.unlink(missing_ok=True)
                print(json.dumps({"ok": True, "url": f"http://127.0.0.1:{state['port']}/#token={token}",
                                  "mode": state.get("mode"), "paused": state.get("paused", False),
                                  "joined": joined}, ensure_ascii=False))
                return 0
        if status in ("refused", "failed", "stopped") or (status in ("starting", "running") and not alive):
            print(json.dumps({"ok": False, "status": status, "mode": state.get("mode"),
                              "reasons": state.get("reasons", [])}, ensure_ascii=False))
            return 3 if status == "refused" else 1
        if time.monotonic() >= deadline:
            print(json.dumps({"ok": False, "status": status or "not_started",
                              "reasons": ["the server did not open its port in time; see server.log"]}, ensure_ascii=False))
            return 1
        time.sleep(0.5)


def stop(args) -> int:
    state, paths = read_state(), _paths()
    if not _alive(state.get("pid")):
        print(json.dumps({"stopped": True, "was_running": False}))
        return 0
    if args.nonce and state.get("nonce") != args.nonce:   # 다른 창이 띄운 서버다 — 끄지 않는다(카드 #120)
        print(json.dumps({"stopped": False, "was_running": True, "not_owner": True}))
        return 0
    # 대상 pid를 적는다. 요청이 남아 있는 사이 다른 serve가 떠도 그 서버는 이 요청을 받지 않는다(_watch)
    paths["stop"].write_text(str(state["pid"]), encoding="utf-8")
    paths["stop"].chmod(0o600)
    deadline = time.monotonic() + args.wait
    while time.monotonic() < deadline:
        if not _alive(state["pid"]):
            final = read_state()
            print(json.dumps({"stopped": True, "was_running": True, "exit_code": final.get("exit_code"),
                              "port_closed": not _listening(state.get("port"))}))
            return 0 if final.get("exit_code") == 0 else 1
        time.sleep(0.5)
    # 돌던 호출이 있다. 요청은 남겨 두고, 끝나면 서버가 스스로 멈춘다.
    print(json.dumps({"stopped": False, "was_running": True, "waiting_for_work": True}))
    return 0


def status(_args) -> int:
    state = read_state()
    alive = _alive(state.get("pid"))
    print(json.dumps({"running": alive and state.get("status") == "running",
                      "status": state.get("status"), "mode": state.get("mode"), "port": state.get("port"),
                      "manifest": state.get("manifest"), "models": state.get("models"),
                      "stop_requested": _paths()["stop"].exists(), "reasons": state.get("reasons", [])},
                     ensure_ascii=False))
    return 0


def cancel_stop(_args) -> int:
    _paths()["stop"].unlink(missing_ok=True)
    print(json.dumps({"stop_requested": False}))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("serve", help="서버를 띄운다(끝날 때까지 반환하지 않음)")
    s.add_argument("--mock", action="store_true", help="모델을 부르지 않는 모의 모드")
    s.add_argument("--codex-model", default=MODELS["codex"])
    s.add_argument("--claude-model", default=MODELS["claude-code"])
    s.add_argument("--nonce", default="", help="url --nonce가 이번 serve의 상태만 보게 하는 표식")
    s.add_argument("--avoid-ports", default="", help="Windows 쪽에서 이미 쓰는 포트(쉼표 구분). start.ps1이 넘긴다")
    u = sub.add_parser("url", help="열 주소를 JSON으로")
    u.add_argument("--wait", type=float, default=90.0)
    u.add_argument("--nonce", default="")
    t = sub.add_parser("stop", help="끄기 요청")
    t.add_argument("--wait", type=float, default=20.0)
    t.add_argument("--nonce", default="", help="이 nonce로 띄운 서버에만 끄기를 요청한다")
    sub.add_parser("status")
    sub.add_parser("cancel-stop")
    args = ap.parse_args(argv)
    if sys.platform != "linux":
        print(json.dumps({"ok": False, "reasons": ["app.launch runs inside WSL/Linux; on Windows use app/start.ps1"]}))
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    handler = {"serve": serve, "url": url, "stop": stop, "status": status, "cancel-stop": cancel_stop}[args.command]
    if args.command != "serve":
        return handler(args)
    from app.store import LedgerBusy, StoreError
    try:
        return handler(args)
    except (LedgerBusy, StoreError, ValueError) as exc:
        if _OWNER is not None:   # 소유자일 때만 실패를 적는다 — 진 쪽은 살아 있는 서버의 기록을 덮지 않는다
            _write_state({"pid": os.getpid(), "mode": "mock" if args.mock else "live", "status": "failed",
                          "nonce": args.nonce, "reasons": [f"{type(exc).__name__}: {exc}"]})
        return 1


if __name__ == "__main__":
    sys.exit(main())
