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
from dataclasses import replace
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
from urllib.parse import urlsplit, parse_qs, unquote

if __package__ in (None, ""):  # `python app/server.py`로 실행해도 저장소 루트에서 app·core를 찾는다
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.controller import CLI, Controller, ControllerError, ParticipantSpec
from app.report import ReportError, build_report, decision_report, revision_report
from app.store import LedgerBusy, Store, StoreError
from app.live_config import Provider, load as load_live_config
from app.account_quota import AccountQuota
from app.ingestion.extract import extract
# 배선은 app.wiring에 있고 헤드리스 실행(app.run)과 나눠 쓴다. 시험은 이 모듈의 이름으로도 부른다.
from app.wiring import (BEHAVIORS, EXIT_NOT_ELIGIBLE, MOCK_MODEL_CHOICES, PARTICIPANTS, live_setup,  # noqa: F401
                        model_choices, new_controller)

STATIC = Path(__file__).with_name("static")
# 화면이 받아 가는 파일은 이 목록뿐이다(경로를 조립하지 않는다). island-ui는 static/island-ui/README.md.
ASSETS = {"/island-ui/themes.css": ("island-ui/themes.css", "text/css; charset=utf-8"),
          "/api.js": ("api.js", "text/javascript; charset=utf-8"),
          "/catalog.js": ("catalog.js", "text/javascript; charset=utf-8"),
          "/templates.js": ("templates.js", "text/javascript; charset=utf-8"),
          "/revisions.js": ("revisions.js", "text/javascript; charset=utf-8"),
          "/extraction.js": ("extraction.js", "text/javascript; charset=utf-8"),
          "/workflow.js": ("workflow.js", "text/javascript; charset=utf-8"),
          "/role-board.js": ("role-board.js", "text/javascript; charset=utf-8"),
          "/role-board.css": ("role-board.css", "text/css; charset=utf-8"),
          "/island-ui/base.css": ("island-ui/base.css", "text/css; charset=utf-8"),
          "/island-ui/motion.js": ("island-ui/motion.js", "text/javascript; charset=utf-8"),
          "/fonts/PretendardVariable.woff2": ("fonts/PretendardVariable.woff2", "font/woff2")}
# 페이지는 이 서버의 것만 불러오고 요청도 이 서버로만 보낸다 — 밖에서 받는 파일이 없어 인터넷 없이도 같게 그린다.
PAGE_CSP = ("default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; font-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
def chosen_models(roster: dict, choices: dict, requested) -> dict:
    """요청의 모델 선택을 허용 목록으로 확인해 이 실행의 명단 사본에 싣는다(카드 #119). 목록 밖이거나 막힌 모델은
    거절한다 — 미리보기·시작 모두 원장을 쓰기 전이다. 다른 모델로 조용히 바꾸지 않는다."""
    if requested is None:
        return roster
    if not isinstance(requested, dict):
        raise ControllerError("models must map participant IDs to model names")
    chosen = dict(roster)
    for pid, model in requested.items():
        spec, allowed = roster.get(pid), choices.get(pid, ())
        if spec is None or spec.transport != CLI or not allowed:
            raise ControllerError(f"{pid!r}에는 고를 모델이 없습니다.")
        choice = next((c for c in allowed if c.model == model), None)
        if choice is None:
            raise ControllerError(f"{model!r}은(는) {spec.label}에 허용한 모델이 아닙니다.")
        if not choice.usable:
            raise ControllerError(f"{model}은(는) 구독 전용 정책에서 고를 수 없습니다 — {choice.basis}")
        chosen[pid] = replace(spec, model=model)
    return chosen


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


def make_handler(controller: Controller, token: str, port: int, *, participants=None, account_quota=None,
                 choices=None):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    roster = dict(PARTICIPANTS if participants is None else participants)
    live = controller.executor.kind == "real"
    behaviors = ("ok",) if live else BEHAVIORS
    # 실제 연결에 허용 목록을 넘기지 않았으면 고를 모델이 없다(명단의 기본 모델만). 모의 목록으로 채우지 않는다.
    choices = dict(choices if choices is not None else ({} if live else MOCK_MODEL_CHOICES))
    account_quota = account_quota or AccountQuota(Path("."), enabled=False)

    def supervisor_spec(body: dict, key: str = "supervisor") -> ParticipantSpec:
        """다듬기·분담 제안을 부를 상위 칸 카드(key: supervisor 또는 orchestrator). 모델은 역할판과 같은 허용 목록으로
        확인한다(막힌 모델은 부르지 않는다)."""
        pid, model = _text(body, key), body.get("model")
        spec = chosen_models(roster, choices, {pid: model} if model is not None else None).get(pid)
        if spec is None or spec.transport != CLI:
            raise ControllerError("상위 칸 카드는 명단의 CLI 카드여야 합니다.")
        behavior = body.get("behavior", "ok")
        if behavior not in behaviors:
            raise ControllerError(f"unknown behavior {behavior!r}")
        return replace(spec, behavior=behavior)

    def split_request(body: dict):
        """분담 제안 요청의 팀원·자료. 팀원은 명단의 카드이고, 자료는 실행 요청과 같은 {name, text} 모양이다."""
        members = body.get("members")
        if not isinstance(members, list) or any(not isinstance(pid, str) or pid not in roster for pid in members):
            raise ControllerError("members must list participant IDs from the roster")
        sources = body.get("sources", [])
        if not isinstance(sources, list) or any(not isinstance(item, dict) or set(item) != {"name", "text"}
                                                for item in sources):
            raise ControllerError("sources must be an array of {name, text} objects")
        return [roster[pid] for pid in members], [(item["name"], item["text"]) for item in sources]

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

        def _send(self, code: int, body: bytes, kind: str = "application/json; charset=utf-8",
                  csp: str = "frame-ancestors 'none'") -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", csp)
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
                self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8", csp=PAGE_CSP)
            elif path in ASSETS:
                name, kind = ASSETS[path]
                self._send(200, (STATIC / name).read_bytes(), kind)
            elif path == "/api/state":
                self._json(200, controller.view())
            elif path == '/api/overview':
                try:
                    params = parse_qs(urlsplit(self.path).query, keep_blank_values=True, max_num_fields=2)
                    if set(params) - {'run'} or any(len(v) != 1 or not v[0] for v in params.values()):
                        raise ControllerError('invalid overview parameters')
                    self._json(200, controller.queries.overview(params.get('run', [None])[0]))
                except ValueError as exc:
                    self._json(400, {'error': str(exc)})
            elif len(parts) == 3 and parts[:2] == ['api', 'runs']:
                result = controller.queries.view(parts[2], _global=False)['runs']
                self._json(200 if result else 404, result[0] if result else {'error': 'run not found'})
            elif len(parts) == 5 and parts[:2] == ['api', 'runs'] and parts[3] == 'sources':
                try:
                    self._json(200, controller.queries.source(parts[2], unquote(parts[4])))
                except (ControllerError, ValueError) as exc:
                    self._json(409, {'error': str(exc)})
            elif parts[:2] == ['api', 'templates'] and (len(parts) in (2, 3) or len(parts) == 4 and parts[3] == 'export'):
                try:
                    if len(parts) == 2:
                        self._json(200, {'templates': controller.templates.list()})
                    elif len(parts) == 4:
                        self._json(200, controller.templates.export(parts[2]))
                    else:
                        item = controller.templates.load(parts[2])
                        current = chosen_models(roster, choices, item['draft'].get('models'))
                        controller.templates.validate(item['draft'], current, item['bindings'])
                        self._json(200, item)
                except (ControllerError, ValueError, TypeError, KeyError) as exc:
                    self._json(409, {'error': str(exc)})
            elif path == "/api/search":
                try:
                    params = parse_qs(urlsplit(self.path).query, keep_blank_values=True, max_num_fields=10)
                    if set(params) - {"q", "task", "kind", "limit"} or any(len(v) != 1 for v in params.values()):
                        raise ControllerError("invalid search parameters")
                    self._json(200, controller.search(params.get("q", [""])[0],
                               task_id=params.get("task", [None])[0], kind=params.get("kind", [None])[0],
                               limit=int(params.get("limit", ["30"])[0])))
                except ValueError as exc:
                    self._json(400, {"error": str(exc)})
            elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] in ("activity", "memory"):
                try:
                    query = controller.activity if parts[3] == "activity" else controller.memory_sources
                    self._json(200, query(parts[2]))
                except ControllerError as exc:
                    self._json(409, {"error": str(exc)})
            elif path == "/api/account-quota":
                self._json(200, account_quota.view())
            elif path == "/api/options":
                self._json(200, {"participants": [dict(vars(p)) for p in roster.values()],
                                 "model_choices": {pid: [c.public() for c in items] for pid, items in choices.items()
                                                   if pid in roster},
                                 "behaviors": list(behaviors), "live": live,
                                 "context_unverified": bool(getattr(controller.executor,
                                                                     "allow_context_unverified", False))})
            elif len(parts) == 4 and parts[:2] == ['api', 'runs'] and parts[3] == 'revision-report':
                try:
                    self._json(200, revision_report(controller.view(parts[2]), parts[2]))
                except (ReportError, KeyError, ValueError, TypeError) as exc:
                    self._json(409, {'error': str(exc)})
            elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "report":
                try:
                    self._json(200, build_report(controller.view(parts[2]), parts[2]))
                except ReportError as exc:
                    self._json(409, {"error": str(exc)})
            elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "decision-report":
                try:
                    view = controller.view(parts[2])
                    report = build_report(view, parts[2])   # 없는 실행은 여기서 거절된다 — /report와 같은 409
                    result = decision_report(view["runs"][0], report)
                    if result is None:
                        raise ReportError("synthesis has not been requested")
                    self._json(200, result)   # 판의 변천은 app.report.DECISION_SCHEMA 주석
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
                elif parts == ['api', 'tasks']:
                    self._json(200, controller.tasks.save(body))
                elif len(parts) == 4 and parts[:2] == ['api', 'tasks'] and parts[3] == 'plan':
                    self._json(200, controller.tasks.save(body, task_id=parts[2]))
                elif parts == ['api', 'sources', 'extract']:
                    self._json(200, extract(body))
                elif parts == ['api', 'templates']:
                    draft = body.get('draft')
                    if not isinstance(draft, dict):
                        raise ControllerError('템플릿 설정이 필요합니다.')
                    current = chosen_models(roster, choices, draft.get('models'))
                    self._json(200, controller.templates.save(body.get('name'), draft, current))
                elif parts == ['api', 'templates', 'import']:
                    item = body.get('item')
                    if not isinstance(item, dict) or not isinstance(item.get('draft'), dict):
                        raise ControllerError('템플릿 파일이 필요합니다.')
                    current = chosen_models(roster, choices, item['draft'].get('models'))
                    self._json(200, controller.templates.import_copy(item, current))
                elif len(parts) == 4 and parts[:2] == ['api', 'templates'] and parts[3] == 'delete':
                    controller.templates.delete(parts[2], _text(body, 'sha256'))
                    self._json(200, {'ok': True})
                elif parts in (["api", "runs"], ["api", "runs", "preview"]):
                    chosen = []
                    items = body.get("participants", [])
                    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                        raise ControllerError("participants must be an array of objects")
                    # 고른 모델은 이 실행의 명단 사본에만 싣는다 — 격리 팀원과 오케스트레이터가 같은 사본을 쓴다
                    run_roster = chosen_models(roster, choices, body.get("models"))
                    for item in items:
                        spec = run_roster[item["pid"]]
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
                    kwargs = dict(min_independent=minimum,
                                  quorum_policy=_text(body, "quorum_policy", "independent_only"),
                                  sources=[(item["name"], item["text"]) for item in sources],
                                  task_id=body.get("task_id"), task_title=body.get("task_title"),
                                  role_board=body.get("role_board"), roster=run_roster, run_id=body.get("run_id"),
                                  assignments=body.get("assignments"),   # 일반 팀원마다 맡길 일·받을 자료
                                  refinement=body.get("refinement"),     # 다듬기 모드에서 승인한 {id, turn}
                                  proposal=body.get("proposal"),         # 다음 단계 제안에서 온 질문의 {id}
                                  split=body.get("split"), use_memory=body.get("use_memory", True))
                    if parts[-1] == "preview":
                        self._json(200, controller.prepare_run(_text(body, "question"), chosen, **kwargs))
                    else:
                        run_id = controller.create_run(_text(body, "question"), chosen,
                                                       confirmation=body.get("confirmation"), **kwargs)
                        self._json(200, {"run_id": run_id})
                elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "reviewed":
                    controller.mark_reviewed(parts[2], body.get("revision"), memo=body.get("memo"))   # 화면이 본 결과 판
                    self._json(200, {"ok": True})
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
                        adapter_id = _text(body, "adapter_id")
                        spec = next((s for s in roster.values() if s.transport == CLI and s.adapter_id == adapter_id), None)
                        controller.synthesize_with_model(parts[2], adapter_id, spec=spec)
                    elif mode == "mock":
                        controller.synthesize(parts[2])
                    else:
                        raise ControllerError("mode must be mock or model")
                    self._json(200, {"ok": True})
                elif parts == ["api", "refinements"]:   # 다듬기 첫 차례: 호출 1회
                    self._json(200, {"refine_id": controller.refine(supervisor_spec(body), _text(body, "original"),
                        task_id=body.get("task_id"), use_memory=body.get("use_memory", True))})
                elif len(parts) == 4 and parts[:2] == ["api", "refinements"] and parts[3] == "turn":
                    controller.refine(supervisor_spec(body), refine_id=parts[2], note=_text(body, "note"))
                    self._json(200, {"refine_id": parts[2]})
                elif len(parts) == 4 and parts[:2] == ["api", "refinements"] and parts[3] == "acknowledge":
                    controller.acknowledge_refine_unknown(parts[2], body.get("turn"))
                    self._json(200, {"ok": True})
                elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "propose":   # 호출 1회
                    self._json(200, {"proposal_id": controller.propose_next(parts[2])})
                elif parts == ["api", "splits"]:   # 분담 제안: 호출 1회
                    members, split_sources = split_request(body)
                    self._json(200, {"split_id": controller.propose_split(
                        _text(body, "goal"), supervisor_spec(body, "orchestrator"), members, split_sources,
                        task_id=body.get("task_id"), use_memory=body.get("use_memory", True))})
                elif len(parts) == 4 and parts[:2] == ["api", "splits"] and parts[3] == "acknowledge":
                    controller.acknowledge_split_unknown(parts[2])
                    self._json(200, {"ok": True})
                elif len(parts) == 4 and parts[:2] == ["api", "proposals"] and parts[3] == "acknowledge":
                    controller.acknowledge_proposal_unknown(parts[2])
                    self._json(200, {"ok": True})
                elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "collate":   # 호출 1회
                    self._json(200, {"collation_id": controller.collate(parts[2])})
                elif len(parts) == 4 and parts[:2] == ["api", "collations"] and parts[3] == "acknowledge":
                    controller.acknowledge_collation_unknown(parts[2])
                    self._json(200, {"ok": True})
                elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "cross-review":   # 검토자 1명 = 호출 1회
                    question = body.get("question")
                    if question is not None and not isinstance(question, str):
                        raise ControllerError("question must be text")
                    self._json(200, {"review_ids": controller.cross_review(parts[2], question)})
                elif len(parts) == 4 and parts[:2] == ["api", "reviews"] and parts[3] == "acknowledge":
                    controller.acknowledge_review_unknown(parts[2])
                    self._json(200, {"ok": True})
                elif len(parts) == 4 and parts[:2] == ["api", "reviews"] and parts[3] == "disposition":
                    controller.set_review_disposition(parts[2], body.get("finding"), body.get("disposition"))
                    self._json(200, {"ok": True})
                elif len(parts) == 5 and parts[:2] == ['api', 'runs'] and parts[3:] == ['revisions', 'preview']:
                    self._json(200, controller.revisions.prepare(parts[2], _text(body, 'pid')))
                elif len(parts) == 4 and parts[:2] == ['api', 'runs'] and parts[3] == 'revisions':
                    self._json(200, {'revision_id': controller.revisions.revise(parts[2], _text(body, 'pid'),
                        _text(body, 'revision_id'), _text(body, 'confirmation'))})
                elif len(parts) == 4 and parts[:2] == ['api', 'revisions'] and parts[3] == 'recheck':
                    self._json(200, {'check_id': controller.revisions.recheck(parts[2], _text(body, 'reviewer_pid'))})
                elif len(parts) == 4 and parts[0] == 'api' and parts[1] in ('revisions', 'rechecks') and parts[3] == 'acknowledge':
                    controller.revisions.acknowledge(parts[2], recheck=parts[1] == 'rechecks')
                    self._json(200, {'ok': True})
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
    executor, roster, providers, call_budget = live_setup(
        data_dir, timeout=timeout, live_cli=live_cli, inventory=inventory, model=model, call_budget=call_budget,
        allow_context_unverified=allow_context_unverified, input_dir=input_dir, live_providers=live_providers)
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
        controller = new_controller(store, executor, providers, call_budget, timeout=timeout,
                                    per_provider=live_providers is not None)
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
                                              participants=roster, account_quota=quota,
                                              choices=model_choices(providers))
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
    return serve_until_stopped(server, controller)


def serve_until_stopped(server: ThreadingHTTPServer, controller: Controller) -> int:
    """Ctrl+C(SIGINT)까지 요청을 받고, 새 호출을 막은 뒤 돌던 작업의 반환을 기다려 닫는다. 서버와 app.launch가 같이 쓴다.

    종료 코드 0은 모든 작업이 반환하고 종료 미확인이 없다는 뜻이다. 아니면 1이고 원장은 그대로 둔다.
    """
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
