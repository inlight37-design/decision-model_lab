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
import socket
import sys
import threading
from urllib.parse import urlsplit

if __package__ in (None, ""):  # `python app/server.py`로 실행해도 저장소 루트에서 app·core를 찾는다
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.controller import CLI, MANUAL, Controller, ControllerError, MockExecutor, ParticipantSpec
from app.report import ReportError, build_report
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


class RequestError(ValueError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def _text(body: dict, key: str, default: str = "") -> str:
    value = body.get(key, default)
    if not isinstance(value, str):
        raise ControllerError(f"{key} must be a string")
    return value


def make_handler(controller: Controller, token: str, port: int):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        server_version = "ledger-mock"
        timeout = 5.0  # 유휴 제한. 별도로 _Server가 연결 수와 네트워크 I/O 기한을 제한한다.

        def handle(self):
            try:
                super().handle()
            except (ConnectionError, TimeoutError):
                pass  # 연결 만료/클라이언트 종료는 애플리케이션 오류가 아니다.

        def log_message(self, fmt, *args):  # 요청 줄에 토큰이 없으므로 그대로 두되, 조용히
            pass

        def _send(self, code: int, body: bytes, kind: str = "application/json; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
            self.send_header("Connection", "close")
            self.close_connection = True  # 거절한 본문을 다음 요청으로 해석하지 않는다.
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, data) -> None:
            self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"))

        def _guard(self) -> bool:
            if len(self.headers.get_all("Host", [])) != 1 or self.headers.get("Host") not in allowed_hosts:
                self._json(403, {"error": "unexpected Host header"})
                return False
            origins = self.headers.get_all("Origin", [])
            if origins and origins != [f"http://{self.headers['Host']}"]:
                self._json(403, {"error": "unexpected Origin header"})
                return False
            if urlsplit(self.path).path.startswith("/api/"):
                given = self.headers.get("Authorization", "")
                if (len(self.headers.get_all("Authorization", [])) != 1
                        or not hmac.compare_digest(given.encode(), f"Bearer {token}".encode())):
                    self._json(401, {"error": "missing or wrong token"})
                    return False
            return True

        def _read_json(self) -> dict:
            lengths = self.headers.get_all("Content-Length", [])
            if self.headers.get_all("Transfer-Encoding", []) or len(lengths) > 1:
                raise RequestError(400, "ambiguous or unsupported body framing")
            if not lengths:
                raise RequestError(411, "Content-Length required")
            value = lengths[0]
            if not value.isascii() or not value.isdecimal():
                raise RequestError(400, "invalid Content-Length")
            if len(value) > 10 or int(value) > MAX_BODY:
                raise RequestError(413, "body too large")
            types = self.headers.get_all("Content-Type", [])
            if len(types) != 1 or self.headers.get_content_type() != "application/json":
                raise RequestError(415, "application/json required")
            size = int(value)
            try:
                raw = self.rfile.read(size)
            except TimeoutError:
                raise RequestError(408, "request body timed out") from None
            if len(raw) != size:
                raise RequestError(400, "incomplete request body")
            body = json.loads(raw.decode("utf-8"))
            if not isinstance(body, dict):
                raise RequestError(400, "JSON body must be an object")
            return body

        def do_GET(self):
            if not self._guard():
                return
            path = urlsplit(self.path).path
            parts = path.strip("/").split("/")
            if path == "/":
                self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/state":
                self._json(200, controller.view())
            elif path == "/api/options":
                self._json(200, {"participants": [dict(vars(p)) for p in PARTICIPANTS.values()],
                                 "behaviors": list(BEHAVIORS)})
            elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "report":
                try:
                    self._json(200, build_report(controller.view(parts[2]), parts[2]))
                except ReportError as exc:
                    self._json(409, {"error": str(exc)})
            elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "decision-report":
                try:
                    view = controller.view(parts[2])
                    report = build_report(view, parts[2])
                    synthesis = view["runs"][0].get("synthesis")
                    if synthesis is None:
                        raise ReportError("mock synthesis has not been requested")
                    self._json(200, {"schema": "a1-decision-report/1", "draft_report": report,
                                     "synthesis": synthesis})
                except ReportError as exc:
                    self._json(409, {"error": str(exc)})
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._guard():
                return
            try:
                body = self._read_json()
                parts = urlsplit(self.path).path.strip("/").split("/")
                if parts == ["api", "runs"]:
                    chosen = []
                    items = body.get("participants", [])
                    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                        raise ControllerError("participants must be an array of objects")
                    for item in items:
                        spec = PARTICIPANTS[item["pid"]]
                        behavior = item.get("behavior", "ok")
                        if behavior not in BEHAVIORS:
                            raise ControllerError(f"unknown behavior {behavior!r}")
                        chosen.append(ParticipantSpec(**{**vars(spec), "behavior": behavior}))
                    minimum = body.get("min_independent", 2)
                    if type(minimum) is not int:
                        raise ControllerError("min_independent must be an integer")
                    run_id = controller.create_run(_text(body, "question"), chosen,
                                                   min_independent=minimum,
                                                   quorum_policy=_text(body, "quorum_policy", "independent_only"))
                    self._json(200, {"run_id": run_id})
                elif len(parts) == 5 and parts[:2] == ["api", "runs"] and parts[3] == "manual":
                    controller.submit_manual(parts[2], parts[4], _text(body, "text"),
                                             _text(body, "input_sha256"),
                                             user_confirmed=body.get("user_confirmed") is True)
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
                elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "cancel":
                    controller.cancel_run(parts[2])
                    self._json(200, {"ok": True})  # 요청을 저장했다는 뜻. 자손 종료 성공 응답이 아니다.
                elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "synthesize":
                    controller.synthesize(parts[2])
                    self._json(200, {"ok": True})
                elif parts == ["api", "resume"]:
                    controller.resume()
                    self._json(200, {"ok": True})
                else:
                    self._json(404, {"error": "not found"})
            except RequestError as exc:
                self._json(exc.status, {"error": str(exc)})
            except (ControllerError, KeyError, ValueError, TypeError, RecursionError) as exc:
                self._json(400, {"error": str(exc) or type(exc).__name__})

    return Handler


class _Server(ThreadingHTTPServer):
    # Windows의 SO_REUSEADDR은 이미 듣고 있는 포트에도 bind를 허락해서 같은 포트에 서버가 둘 떴다(A1 리뷰 반영
    # 중 관측). Windows에서는 끈다. POSIX에서는 TIME_WAIT 포트를 다시 쓰게 할 뿐이므로 둔다.
    allow_reuse_address = os.name != "nt"
    max_connections = 16
    connection_deadline = 15.0  # 바이트를 조금씩 보내도 연장되지 않는 네트워크 I/O 기한

    def __init__(self, *args, **kwargs):
        self._connections = threading.BoundedSemaphore(self.max_connections)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        # 인증 전에도 같은 상한을 적용한다. 응답을 쓰다가 막히지 않도록 포화 시 연결만 닫는다.
        if not self._connections.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._connections.release()
            raise

    def process_request_thread(self, request, client_address):
        def expire():
            try:
                request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass  # 이미 닫힌 소켓. 파일 기술자를 다시 열거나 다른 연결을 건드리지 않는다.
        timer = threading.Timer(self.connection_deadline, expire)
        timer.daemon = True
        try:
            timer.start()
            super().process_request_thread(request, client_address)
        finally:
            timer.cancel()
            self.shutdown_request(request)  # timer/handler를 시작하지 못한 경우에도 닫는다.
            self._connections.release()


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
