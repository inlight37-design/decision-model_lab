"""헤드리스 실행: 화면 없이 질문 하나를 끝까지 돌리고 결과 JSON 하나를 쓴다.

실험마다 서버를 띄우고 HTTP로 조작하는 드라이버를 복사해 고치던 일을 대신한다(2026-09-25 정리). 서버와 같은
준비 조회·실행기·원장·호출 상한·봉인/공개 규칙을 쓴다 — 새 실행 경로가 아니라 같은 controller를 부르는 다른 입구다.

  # 흐름 확인(모델 호출 없음)
  python -m app.run --mock --data-dir /tmp/dml-mock --question "..." --participants claude,codex \\
      --policy include-unverified --synthesize mock --out result.json
  # 실제(구독 사용량 소비) — 준비 조회가 모두 허가해야 시작한다
  python -m app.run --live-config live.json --data-dir <새 원장> --question-file q.txt [--sources-dir 자료] \\
      --participants claude,codex --synthesize claude-code,codex --out result.json

--synthesize는 공개 뒤 차례로 부른다: `mock`은 모델 없는 발췌 대조, provider 이름(claude-code·codex)은 실제
합성 한 번씩(부를 때마다 호출 하나를 같은 원장의 상한에서 예약). 같은 초안에 합성자를 바꿔 붙일 수 있다(L1).

종료 코드: 0 공개까지 끝남(요청한 합성은 모두 시도함 — 성공·실패는 결과 JSON에), 1 공개되지 않음·원장 정책
거절·끝났는지 모르는 작업이 남음, 2 명령줄 인자 오류, 3 준비 조회가 허가하지 않음(원장을 만들지 않았다).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.controller import CLI, INCLUDE_UNVERIFIED, INDEPENDENT_ONLY, ControllerError, ParticipantSpec
from app.live_config import load as load_live_config
from app.report import ReportError, build_report, decision_report
from app.server import BEHAVIORS, EXIT_NOT_ELIGIBLE, live_setup, new_controller
from app.store import LedgerBusy, Store, StoreError

SCHEMA = "a1-headless-run/1"
MOCK_DIR = Path.home() / ".decision-model-lab" / "mock"
POLICIES = {"independent-only": INDEPENDENT_ONLY, "include-unverified": INCLUDE_UNVERIFIED}


def read_sources(folder: Path | None) -> list[tuple[str, str]]:
    """폴더 바로 아래의 파일들을 (이름, UTF-8 글)로 읽는다. 이름·크기·내용 검사는 controller가 한다."""
    if folder is None:
        return []
    return [(path.name, path.read_text(encoding="utf-8")) for path in sorted(folder.iterdir()) if path.is_file()]


def parse(argv) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mock", action="store_true", help="모의 CLI로 흐름만 확인(모델 호출 없음)")
    mode.add_argument("--live-config", type=Path, help="provider별 모델·관측 기록·입력 폴더·호출 상한 JSON")
    ap.add_argument("--data-dir", type=Path, required=True, help="이 실행의 원장 폴더(실제는 새 폴더)")
    question = ap.add_mutually_exclusive_group(required=True)
    question.add_argument("--question")
    question.add_argument("--question-file", type=Path)
    ap.add_argument("--sources-dir", type=Path, help="공통 자료 폴더(바로 아래 파일만)")
    ap.add_argument("--participants", default="claude,codex", help="CLI 참여자(claude, codex), 쉼표로")
    ap.add_argument("--policy", choices=sorted(POLICIES), default="independent-only")
    ap.add_argument("--min-independent", type=int, help="정족수(기본: 참여자 수)")
    ap.add_argument("--approve-reduction", action="store_true", help="참여자가 빠지면 줄어든 구성으로 공개를 승인")
    ap.add_argument("--synthesize", default="", help="공개 뒤 차례로: mock, claude-code, codex (쉼표로)")
    ap.add_argument("--mock-behavior", action="append", default=[], metavar="PID=BEHAVIOR",
                    help=f"모의 전용: 참여자의 동작({', '.join(BEHAVIORS)})")
    ap.add_argument("--timeout", type=float, default=180.0, help="CLI 한 번의 제한 시간(초, 실제는 최대 180)")
    ap.add_argument("--wait", type=float, default=900.0, help="초안·합성 하나를 기다리는 최대 시간(초)")
    ap.add_argument("--allow-context-unverified", action="store_true", help="C3만 미확인 허용; 독립 정족수에 세지 않음")
    ap.add_argument("--out", type=Path, help="결과 JSON 파일(없으면 표준 출력)")
    args = ap.parse_args(argv)
    args.participant_ids = [p for p in args.participants.split(",") if p]
    args.synthesizers = [s for s in args.synthesize.split(",") if s]
    if not args.participant_ids or len(set(args.participant_ids)) != len(args.participant_ids):
        ap.error("--participants needs distinct CLI participants")
    if any(s not in ("mock", "claude-code", "codex") for s in args.synthesizers):
        ap.error("--synthesize takes mock, claude-code or codex")
    if args.mock and any(s != "mock" for s in args.synthesizers):
        ap.error("a model synthesis needs a live connection (--live-config); use --synthesize mock with --mock")
    if args.mock_behavior and not args.mock:
        ap.error("--mock-behavior is for --mock only")
    if not args.mock and args.data_dir == MOCK_DIR:
        ap.error("a live run needs a separate explicit --data-dir, not the mock journal")
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 180 or not math.isfinite(args.wait) or args.wait <= 0:
        ap.error("--timeout must be in (0, 180] and --wait positive")
    args.behaviors = {}
    for item in args.mock_behavior:
        pid, _, behavior = item.partition("=")
        if behavior not in BEHAVIORS:
            ap.error(f"unknown mock behavior {item!r}")
        args.behaviors[pid] = behavior
    return args


def main(argv=None) -> int:
    args = parse(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    question = args.question if args.question is not None else args.question_file.read_text(encoding="utf-8")
    providers = None
    if args.live_config:
        try:
            providers = load_live_config(args.live_config)
        except (OSError, ValueError, TypeError) as exc:
            print(f"invalid live config: {exc}", file=sys.stderr)
            return 2
        from app.readiness import check   # 서버와 같은 준비 조회. 허가되지 않으면 원장을 만들지 않는다
        results = [check(p.adapter_id, p.model, p.inventory, args.data_dir,
                         allow_context_unverified=args.allow_context_unverified, input_dir=p.input_dir)
                   for p in providers]
        if not all(r["eligible"] for r in results):
            print(json.dumps({"mode": "readiness_only", "model_calls": 0, "eligible": False, "providers": results},
                             ensure_ascii=False, indent=2))
            return EXIT_NOT_ELIGIBLE
    executor, roster, live, call_budget = live_setup(args.data_dir, timeout=args.timeout, live_providers=providers,
                                                     allow_context_unverified=args.allow_context_unverified)
    unknown = [pid for pid in args.participant_ids if pid not in roster or roster[pid].transport != CLI]
    if unknown:
        print(f"not a configured CLI participant: {', '.join(unknown)}", file=sys.stderr)
        return 2
    args.data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        store = Store(args.data_dir / "journal.db")
    except LedgerBusy:
        print(f"another controller is using {args.data_dir}", file=sys.stderr)
        return 1
    try:
        ctl = new_controller(store, executor, live, call_budget, timeout=args.timeout, per_provider=providers is not None)
    except StoreError as exc:
        store.close()
        print(f"ledger policy refused the run: {exc}", file=sys.stderr)
        return 1
    try:
        return _run(ctl, args, question, roster, live=providers is not None)
    finally:
        idle = ctl.shutdown()
        if idle:
            store.close()


def _run(ctl, args, question, roster, *, live: bool) -> int:
    chosen = [ParticipantSpec(**{**vars(roster[pid]), "behavior": args.behaviors.get(pid, "ok")})
              for pid in args.participant_ids]
    try:
        run_id = ctl.create_run(question, chosen, min_independent=args.min_independent or len(chosen),
                                quorum_policy=POLICIES[args.policy], sources=read_sources(args.sources_dir))
    except ControllerError as exc:
        print(f"run refused: {exc}", file=sys.stderr)
        return 1
    settled = ctl.wait_idle(timeout=args.wait)
    run = ctl.view(run_id)["runs"][0]
    if run["phase"] != "revealed" and run["gate"].get("can_approve_reduction") and args.approve_reduction:
        ctl.approve_reduction(run_id)
        run = ctl.view(run_id)["runs"][0]
    attempted = []
    if run["phase"] == "revealed":
        for name in args.synthesizers:
            try:
                if name == "mock":
                    ctl.synthesize(run_id)
                else:
                    spec = next((s for s in roster.values() if s.transport == CLI and s.adapter_id == name), None)
                    ctl.synthesize_with_model(run_id, name, spec=spec)
                attempted.append({"synthesizer": name, "started": True})
            except ControllerError as exc:
                attempted.append({"synthesizer": name, "started": False, "refused": str(exc)})
            settled = ctl.wait_idle(timeout=args.wait) and settled
    view = ctl.view(run_id)
    run = view["runs"][0]
    try:
        draft = build_report(view, run_id)
    except ReportError:
        draft = None
    result = {"schema": SCHEMA, "mode": "live" if live else "mock", "run_id": run_id, "phase": run["phase"],
              "note": run["note"], "gate": run["gate"], "settled": settled,
              "participants": [{k: p[k] for k in ("pid", "state", "status", "independence")} for p in run["participants"]],
              "synthesis_requests": attempted,
              "budget": {"total": view["live_call_budget"], "by_provider": view["provider_call_budgets"]},
              "draft_report": draft, "decision_report": decision_report(run, draft) if draft else None}
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"{run['phase']} · {run_id} · {args.out}")
    else:
        sys.stdout.write(text)
    return 0 if run["phase"] == "revealed" and settled and ctl.unsettled() == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
