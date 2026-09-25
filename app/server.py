"""A1 화면 서버. 127.0.0.1에만 열고, 모든 /api 요청에 토큰을 요구한다(읽기 포함).

참여자는 격리 안에서도 localhost 네트워크를 공유한다(core.isolation). 그래서 제어 API는 참여자에게 없는 토큰으로
막는다. 토큰은 URL의 `#` 뒤(fragment)로만 브라우저에 준다 — fragment는 서버로 보내지지 않으므로 페이지를
받아 가는 것만으로는 토큰을 얻지 못한다. 토큰 파일은 controller 데이터 폴더에 둔다(참여자에게 연결하지 않음).
Host 머리글이 우리 주소가 아니면 거절한다(DNS rebinding).

시작 순서(A1 리뷰 A1-03): 원장 잠금 → 포트 → 복구 → 토큰. 같은 데이터 폴더로 서버를 하나 더 띄우면 원장
잠금에서 멈추므로 돌던 서버의 원장과 토큰 파일을 건드리지 않는다. 포트를 먼저 잡는 것에 기대지 않는다 —
다른 포트로 띄우면 막지 못하고, Windows에서는 SO_REUSEADDR 때문에 같은 포트에 서버가 둘 떴다.

  python -m app.server [--port 8765] [--data-dir ~/.decision-model-lab/mock]

종료 코드: 0 정상 종료·준비 조회 허가, 1 원장 사용 중·원장 정책 거절·종료 미확인(처리하지 못한 예외도 1),
2 명령줄 인자 오류(argparse), 3 준비 조회가 허가하지 않음(`--check-*`, 그리고 실제 모드가 시작 전에 거절될 때).
"""
from __future__ import annotations

import argparse
import hmac
import json
import math
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
from app.store import LedgerBusy, Store, StoreError
from app.live_config import Provider, load as load_live_config, validate as validate_providers
from app.account_quota import AccountQuota

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
# 준비 조회가 허가하지 않았다. argparse의 인자 오류가 2라서 같은 값을 쓰면 스크립트가 둘을 가르지 못한다(병합 검증 N3).
EXIT_NOT_ELIGIBLE = 3


class RequestError(ValueError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def _text(body: dict, key: str, default: str = "") -> str:
    value = body.get(key, default)
    if not isinstance(value, str):
        raise ControllerError(f"{key} must be a string")
    return value


def make_handler(controller: Controller, token: str, port: int, *, participants=None, account_quota=None):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    roster = dict(PARTICIPANTS if participants is None else participants)
    live = controller.executor.kind == "real"
    behaviors = ("ok",) if live else BEHAVIORS
    account_quota = account_quota or AccountQuota(Path("."), enabled=False)

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
            elif path == "/api/account-quota":
                self._json(200, account_quota.view())
            elif path == "/api/options":
                self._json(200, {"participants": [dict(vars(p)) for p in roster.values()],
                                 "behaviors": list(behaviors), "live": live,
                                 "context_unverified": bool(getattr(controller.executor,
                                                                     "allow_context_unverified", False))})
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
                        raise ReportError("synthesis has not been requested")
                    # 2: synthesis는 모의(a1-mock-synthesis/1) 또는 실제(a1-model-synthesis/1)다. 그 schema로 가른다.
                    self._json(200, {"schema": "a1-decision-report/2", "draft_report": report,
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
                if parts == ["api", "account-quota", "refresh"]:
                    self._json(200, account_quota.refresh())
                elif parts == ["api", "runs"]:
                    chosen = []
                    items = body.get("participants", [])
                    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                        raise ControllerError("participants must be an array of objects")
                    for item in items:
                        spec = roster[item["pid"]]
                        behavior = item.get("behavior", "ok")
                        if behavior not in behaviors:
                            raise ControllerError(f"unknown behavior {behavior!r}")
                        chosen.append(ParticipantSpec(**{**vars(spec), "behavior": behavior}))
                    minimum = body.get("min_independent", 2)
                    if type(minimum) is not int:
                        raise ControllerError("min_independent must be an integer")
                    sources = body.get("sources", [])
                    if not isinstance(sources, list) or any(not isinstance(item, dict) or set(item) != {"name", "text"}
                                                            for item in sources):
                        raise ControllerError("sources must be an array of {name, text} objects")
                    run_id = controller.create_run(_text(body, "question"), chosen,
                                                   min_independent=minimum,
                                                   quorum_policy=_text(body, "quorum_policy", "independent_only"),
                                                   sources=[(item["name"], item["text"]) for item in sources])
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
                elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "acknowledge-synthesis":
                    attempt = _text(body, "attempt")
                    if not attempt:
                        raise ControllerError("attempt is required")
                    controller.acknowledge_synthesis_unknown(parts[2], attempt)
                    self._json(200, {"ok": True})
                elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "approve-reduction":
                    controller.approve_reduction(parts[2])
                    self._json(200, {"ok": True})
                elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "cancel":
                    controller.cancel_run(parts[2])
                    self._json(200, {"ok": True})  # 요청을 저장했다는 뜻. 자손 종료 성공 응답이 아니다.
                elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "synthesize":
                    mode = body.get("mode", "mock")
                    if mode == "model":   # 실제 합성: 호출 1회, 실제 CLI 연결에서만
                        if not live:
                            raise ControllerError("model synthesis needs an explicit live CLI connection")
                        controller.synthesize_with_model(parts[2], _text(body, "adapter_id"))
                    elif mode == "mock":
                        controller.synthesize(parts[2])
                    else:
                        raise ControllerError("mode must be mock or model")
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
    # server_close가 HTTP writer까지 회수한 뒤에만 원장을 닫는다. 연결 수·I/O 기한 상한은 그대로 둔다.
    daemon_threads = False
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
            # CPython 3.12/3.13 ThreadingMixIn은 start 전에 스레드를 등록한다. 시작 실패를 남기면
            # server_close의 join이 실패한다. 기존 목록에서 죽은 항목만 회수하고 살아 있는 handler는 보존한다.
            if self.block_on_close:
                self._threads.reap()
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


def serve(data_dir: Path, port: int, *, timeout: float = 20.0, live_cli: str | None = None,
          inventory: Path | None = None, model: str | None = None, call_budget: int | None = None,
          allow_context_unverified: bool = False,
          input_dir: Path | None = None,
          live_providers: tuple[Provider, ...] | None = None) -> tuple[ThreadingHTTPServer, str, Controller]:
    if live_providers is not None and any(value is not None for value in (live_cli, inventory, model, call_budget, input_dir)):
        raise ValueError("do not mix live_providers with single-provider options")
    providers = validate_providers(tuple(live_providers)) if live_providers is not None else ()
    if live_cli is not None:
        providers = (Provider(live_cli, model, inventory, call_budget, input_dir),)
    if providers:
        from app.cli_executor import CliExecutor
        if sys.platform != "linux" or not math.isfinite(timeout) or not 0 < timeout <= 180:
            raise ValueError("live CLI requires Linux, inventory, full model, call budget 1..10 and timeout 0..180s")
        executor = CliExecutor(never=(str(data_dir.resolve()),), inventory=inventory,
                               inventories_by_adapter={p.adapter_id: p.inventory for p in providers},
                               allow_context_unverified=allow_context_unverified,
                               inputs_by_adapter={p.adapter_id: () if p.input_dir is None else (str(p.input_dir),)
                                                  for p in providers})
        roster = {p.pid: p for p in PARTICIPANTS.values() if p.transport == MANUAL}
        for provider in providers:
            pid = "claude" if provider.adapter_id == "claude-code" else "codex"
            roster[pid] = ParticipantSpec(**{**vars(PARTICIPANTS[pid]), "model": provider.model,
                                            "context_unverified": allow_context_unverified})
        call_budget = sum(p.call_budget for p in providers)
    else:
        if (inventory is not None or model is not None or call_budget is not None
                or allow_context_unverified or input_dir is not None):
            raise ValueError("real options require live_cli; refusing a silent mock fallback")
        executor, roster = MockExecutor(never=(str(data_dir.resolve()),)), PARTICIPANTS
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
        controller = Controller(store, executor, timeout=timeout, max_real_calls=call_budget,
                                provider_call_caps=({p.adapter_id: p.call_budget for p in providers}
                                                    if live_providers is not None else None),
                                max_parallel=len(providers) if providers else 2,
                                unsettled_limit=len(providers) if providers else 2)
        token = secrets.token_urlsafe(32)
        _write_token(data_dir / "control-token", token)
    except BaseException:
        server.server_close()
        store.close()
        raise
    codex = next((p for p in providers if p.adapter_id == "codex"), None)
    quota = AccountQuota(data_dir, enabled=codex is not None, codex_model=codex.model if codex else None,
                         claude=(controller.claude_account_limit
                                 if any(p.adapter_id == "claude-code" for p in providers) else None))
    server.RequestHandlerClass = make_handler(controller, token, server.server_address[1],
                                              participants=roster, account_quota=quota)
    return server, token, controller


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--data-dir", type=Path, default=Path.home() / ".decision-model-lab" / "mock")
    ap.add_argument("--timeout", type=float, default=20.0, help="CLI 한 번의 제한 시간(초); 실측은 최대 180초")
    ap.add_argument("--check-cli", choices=("claude-code", "codex"),
                    help="현재 실제 CLI 계획의 허가만 조회하고 종료(허가 0, 거절 3); 서버·모델을 시작하지 않음")
    ap.add_argument("--live-cli", choices=("claude-code", "codex"), help="명시한 실제 CLI 하나를 화면에 연결")
    ap.add_argument("--live-config", type=Path, help="provider별 모델·관측 기록·입력 폴더·호출 상한 JSON")
    ap.add_argument("--check-config", type=Path,
                    help="live-config와 동일한 계획을 모두 조회한 뒤 종료(허가 0, 거절 3); 모델 호출 없음")
    ap.add_argument("--inventory", type=Path, help="이 기기의 runtime-inventory/2 기록")
    ap.add_argument("--model", help="전체 요청 모델 이름; 기본값·대체 모델 없음")
    ap.add_argument("--call-budget", type=int, help="이 원장 전체에서 예약할 실제 CLI 호출 상한(1..10); 재시작은 환불 아님")
    ap.add_argument("--input-dir", type=Path, help="공통 읽기 전용 입력 폴더 하나; 조회와 실제 실행에 같은 계획 사용")
    ap.add_argument("--allow-context-unverified", action="store_true",
                    help="C3만 미확인으로 허용; 독립 정족수에는 절대 세지 않음")
    args = ap.parse_args()
    providers = None
    config_path = args.live_config or args.check_config
    if config_path:
        if (args.live_config and args.check_config) or any(value is not None for value in (
                args.check_cli, args.live_cli, args.inventory, args.model, args.call_budget, args.input_dir)):
            ap.error("do not mix config mode with single-provider options")
        try:
            providers = load_live_config(config_path)
        except (OSError, ValueError, TypeError) as exc:
            ap.error(f"invalid live config: {exc}")
    if args.check_cli and args.live_cli:
        ap.error("choose --check-cli or --live-cli, not both")
    if (args.check_cli or args.live_cli) and (args.inventory is None or not args.model or not args.model.strip()):
        ap.error("--check-cli/--live-cli requires --inventory and --model")
    if not (args.check_cli or args.live_cli or config_path) and (args.inventory is not None or args.model is not None
                                                 or args.allow_context_unverified or args.input_dir is not None):
        ap.error("real options require --check-cli or --live-cli; refusing a silent mock fallback")
    if args.live_cli and (args.call_budget is None or not 1 <= args.call_budget <= 10
                          or not math.isfinite(args.timeout) or not 0 < args.timeout <= 180):
        ap.error("--live-cli requires --call-budget 1..10 and finite --timeout greater than 0, at most 180")
    if args.call_budget is not None and not args.live_cli:
        ap.error("--call-budget requires --live-cli")
    if args.live_config and (not math.isfinite(args.timeout) or not 0 < args.timeout <= 180):
        ap.error("live config requires finite --timeout greater than 0, at most 180")
    if hasattr(sys.stdout, "reconfigure"):  # Windows 콘솔의 cp949에서도 한글·기호가 깨지지 않게
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.check_cli or args.live_cli or config_path:
        from app.readiness import check
        if (args.live_cli or args.live_config) and args.data_dir == Path.home() / ".decision-model-lab" / "mock":
            ap.error("--live-cli requires a separate explicit --data-dir, not the mock journal")
        if providers is not None:
            results = [check(p.adapter_id, p.model, p.inventory, args.data_dir,
                             allow_context_unverified=args.allow_context_unverified, input_dir=p.input_dir)
                       for p in providers]
            result = {"mode": "readiness_only", "model_calls": 0, "eligible": all(r["eligible"] for r in results),
                      "providers": results}
        else:
            result = check(args.check_cli or args.live_cli, args.model, args.inventory, args.data_dir,
                           allow_context_unverified=args.allow_context_unverified, input_dir=args.input_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.check_cli or args.check_config or not result["eligible"]:
            return 0 if result["eligible"] else EXIT_NOT_ELIGIBLE
    try:
        server, token, controller = serve(args.data_dir, args.port, timeout=args.timeout,
                                           live_cli=args.live_cli, inventory=args.inventory, model=args.model,
                                           call_budget=args.call_budget,
                                           allow_context_unverified=args.allow_context_unverified,
                                           input_dir=args.input_dir, live_providers=providers)
    except LedgerBusy:
        print(f"이미 다른 서버가 이 데이터 폴더를 쓰고 있다: {args.data_dir}. 그 서버를 쓰거나 끈 뒤 다시 띄운다.",
              file=sys.stderr, flush=True)
        return 1
    except StoreError as exc:
        print(f"원장 정책 때문에 서버를 시작하지 않았습니다: {exc}", file=sys.stderr, flush=True)
        return 1
    mode = "실제 CLI · 구독 사용량 소비" if args.live_cli or args.live_config else "모의 모드"
    print(f"Ledger {mode} — 실행기 {controller.executor.name}, 데이터 {args.data_dir}", flush=True)
    if controller.paused:
        print("다시 시작하기 전에 시작하지 못한 시도가 있다. 화면에서 '이어서 시작'을 눌러야 시작한다.", flush=True)
    print(f"열기: http://127.0.0.1:{server.server_address[1]}/#token={token}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # 같은 serve_forever 스레드에서 server.shutdown()을 호출하면 교착된다. 새 호출부터 막고 소켓을 닫는다.
        controller.shutdown(timeout=0)
        try:
            server.server_close()
        finally:
            idle = controller.shutdown()
            clean = idle and controller.unsettled() == 0
            if idle:
                controller.store.close()
            if not clean:
                print("종료를 확인하지 못한 작업이 남았습니다. 원장은 보존되며 재호출·예산 환불은 하지 않습니다.",
                      file=sys.stderr, flush=True)
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
