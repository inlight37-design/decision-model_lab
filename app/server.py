"""A1 화면 서버. 127.0.0.1에만 열고, 모든 /api 요청에 토큰을 요구한다(읽기 포함).

참여자는 격리 안에서도 localhost 네트워크를 공유한다(core.isolation). 그래서 제어 API는 참여자에게 없는 토큰으로
막는다. 토큰은 URL의 `#` 뒤(fragment)로만 브라우저에 준다 — fragment는 서버로 보내지지 않으므로 페이지를
받아 가는 것만으로는 토큰을 얻지 못한다. 토큰 파일은 controller 데이터 폴더에 둔다(참여자에게 연결하지 않음).
Host 머리글이 우리 주소가 아니면 거절한다(DNS rebinding).

시작 순서(A1 리뷰 A1-03): 원장 잠금 → 포트 → 복구 → 토큰. 같은 데이터 폴더로 서버를 하나 더 띄우면 원장
잠금에서 멈추므로 돌던 서버의 원장과 토큰 파일을 건드리지 않는다. 포트를 먼저 잡는 것에 기대지 않는다 —
다른 포트로 띄우면 막지 못하고, Windows에서는 SO_REUSEADDR 때문에 같은 포트에도 서버가 둘 떴다.

  python -m app.server [--port 8765] [--data-dir ~/.decision-model-lab/mock]
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import sys
from urllib.parse import urlsplit

if __package__ in (None, ""):  # `python app/server.py`로 실행해도 저장소 루트에서 app·core를 찾는다
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.controller import CLI, MANUAL, Controller, ControllerError, MockExecutor, ParticipantSpec
from app.store import LedgerBusy, Store

STATIC = Path(__file__).with_name("static")
PARTICIPANTS = {
    "claude": ParticipantSpec("claude", "Claude Code", "anthropic", CLI, "claude-code", "mock-claude"),
    "codex": ParticipantSpec("codex", "Codex", "openai", CLI, "codex", "mock-codex"),
    "chatgpt-app": ParticipantSpec("chatgpt-app", "ChatGPT 앱", "openai", MANUAL),
    "claude-app": ParticipantSpec("claude-app", "Claude 앱", "anthropic", MANUAL),
    "antigravity-app": ParticipantSpec("antigravity-app", "Antigravity", "google", MANUAL),
}
BEHAVIORS = ("ok", "slow", "fail", "partial_input", "hang")
MAX_BODY = 2 * 1024 * 1024


def make_handler(controller: Controller, token: str, port: int):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        server_version = "ledger-mock"

        def log_message(self, fmt, *args):  # 요청 줄에 토큰이 없으므로 그대로 두되, 조용히
            pass

        def _send(self, code: int, body: bytes, kind: str = "application/json; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, data) -> None:
            self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"))

        def _guard(self) -> bool:
            if self.headers.get("Host") not in allowed_hosts:
                self._json(403, {"error": "unexpected Host header"})
                return False
            if urlsplit(self.path).path.startswith("/api/"):
                given = self.headers.get("Authorization", "")
                if not hmac.compare_digest(given.encode(), f"Bearer {token}".encode()):
                    self._json(401, {"error": "missing or wrong token"})
                    return False
            return True

        def do_GET(self):
            if not self._guard():
                return
            path = urlsplit(self.path).path
            if path == "/":
                self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/state":
                self._json(200, controller.view())
            elif path == "/api/options":
                self._json(200, {"participants": [dict(vars(p)) for p in PARTICIPANTS.values()],
                                 "behaviors": list(BEHAVIORS)})
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._guard():
                return
            size = int(self.headers.get("Content-Length") or 0)
            if size > MAX_BODY:
                self._json(413, {"error": "body too large"})
                return
            try:
                body = json.loads(self.rfile.read(size) or b"{}")
                parts = urlsplit(self.path).path.strip("/").split("/")
                if parts == ["api", "runs"]:
                    chosen = []
                    for item in body.get("participants", []):
                        spec = PARTICIPANTS[item["pid"]]
                        behavior = item.get("behavior", "ok")
                        if behavior not in BEHAVIORS:
                            raise ControllerError(f"unknown behavior {behavior!r}")
                        chosen.append(ParticipantSpec(**{**vars(spec), "behavior": behavior}))
                    run_id = controller.create_run(str(body.get("question", "")), chosen,
                                                   min_independent=int(body.get("min_independent", 2)))
                    self._json(200, {"run_id": run_id})
                elif len(parts) == 5 and parts[:2] == ["api", "runs"] and parts[3] == "manual":
                    controller.submit_manual(parts[2], parts[4], str(body.get("text", "")),
                                             str(body.get("input_sha256", "")))
                    self._json(200, {"ok": True})
                elif len(parts) == 5 and parts[:2] == ["api", "runs"] and parts[3] == "withdraw":
                    controller.withdraw_manual(parts[2], parts[4])
                    self._json(200, {"ok": True})
                elif len(parts) == 5 and parts[:2] == ["api", "runs"] and parts[3] == "acknowledge":
                    controller.acknowledge_unknown(parts[2], parts[4])
                    self._json(200, {"ok": True})
                elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "approve-reduction":
                    controller.approve_reduction(parts[2])
                    self._json(200, {"ok": True})
                elif parts == ["api", "resume"]:
                    controller.resume()
                    self._json(200, {"ok": True})
                else:
                    self._json(404, {"error": "not found"})
            except (ControllerError, KeyError, ValueError, TypeError) as exc:
                self._json(400, {"error": str(exc) or type(exc).__name__})

    return Handler


class _Server(ThreadingHTTPServer):
    # Windows의 SO_REUSEADDR은 이미 듣고 있는 포트에도 bind를 허락해서 같은 포트에 서버가 둘 뜬다(A1 리뷰 반영
    # 중 관측). Windows에서는 끈다. POSIX에서는 TIME_WAIT 포트를 다시 쓰게 할 뿐이므로 둔다.
    allow_reuse_address = os.name != "nt"


def _write_token(path: Path, token: str) -> None:
    """처음부터 0600으로 만들고 통째로 바꾼다. 쓰는 중이거나 넓은 권한인 토큰 파일이 보이는 틈을 두지 않는다."""
    staging = path.with_name(path.name + ".new")
    try:
        staging.unlink()
    except FileNotFoundError:
        pass
    fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(token)
    os.replace(staging, path)


def serve(data_dir: Path, port: int, *, timeout: float = 20.0) -> tuple[ThreadingHTTPServer, str, Controller]:
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        data_dir.chmod(0o700)
    store = Store(data_dir / "journal.db")          # 다른 controller가 열고 있으면 LedgerBusy — 아무것도 바꾸지 않았다
    try:
        server = _Server(("127.0.0.1", port), BaseHTTPRequestHandler)
    except OSError:
        store.close()
        raise
    try:
        controller = Controller(store, MockExecutor(never=(str(data_dir.resolve()),)), timeout=timeout)
        token = secrets.token_urlsafe(32)
        _write_token(data_dir / "control-token", token)
    except BaseException:
        server.server_close()
        store.close()
        raise
    server.RequestHandlerClass = make_handler(controller, token, server.server_address[1])
    return server, token, controller


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--data-dir", type=Path, default=Path.home() / ".decision-model-lab" / "mock")
    ap.add_argument("--timeout", type=float, default=20.0, help="모의 CLI 한 번의 제한 시간(초)")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):  # Windows 콘솔의 cp949에서도 한글·기호가 깨지지 않게
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        server, token, controller = serve(args.data_dir, args.port, timeout=args.timeout)
    except LedgerBusy:
        print(f"이미 다른 서버가 이 데이터 폴더를 쓰고 있다: {args.data_dir}. 그 서버를 쓰거나 끈 뒤 다시 띄운다.",
              file=sys.stderr, flush=True)
        return 1
    print(f"Ledger 모의 모드 — 실행기 {controller.executor.name}, 데이터 {args.data_dir}", flush=True)
    if controller.paused:
        print("다시 시작하기 전에 시작하지 못한 시도가 있다. 화면에서 '이어서 시작'을 눌러야 시작한다.", flush=True)
    print(f"열기: http://127.0.0.1:{server.server_address[1]}/#token={token}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
