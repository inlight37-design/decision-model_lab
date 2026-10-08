"""Trusted public projection. Sealed outputs never become search or UI data."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
from typing import Any
from app import memory, refine as refining, usage as token_usage
from app import source_document
from app import workflow
from app.queries import catalog
from app.queries.pages import BrowserPages
from app.roles import task_projection
from app.state import CLI, MANUAL, QUEUED, RUNNING, AWAITING_USER, ACCEPTED, REJECTED, UNKNOWN, NOT_STARTED, INDEPENDENT_ONLY, gate, confirmed
from core import contract
from app.domain import ParticipantSpec, ControllerError, packet

SEALED_VIEW_KEYS = frozenset({"state", "exit_code", "containment", "tree_confirmed_empty", "input_delivery",
                              "status", "ok", "model_match"})


DIAGNOSTIC_KEYS = frozenset({"detail", "notes"})


CONTAMINATION = {
    MANUAL: ("원본 앱의 메모리·다른 대화·프로젝트 지시문을 통제하지 못함", "사용량·시간 관측 안 됨"),
    contract.MOCK: ("모의 CLI — 모델 호출 없음",),
    contract.SYNTHETIC: ("합성 실행기 — 모델 호출 없음",),
    contract.REAL: ("실제 CLI — 구독 사용량을 씀", "계정 문맥은 실행 허가의 관측 범위까지만 확인"),
}


NOT_RUN = ("실행하지 않음",)


UNRECORDED = ("실행 종류 기록 없음",)


def _flags(transport: str, part) -> tuple[str, ...]:
    """시작하지 않은 시도(대기, 시작 전 취소, 계획·프로세스 거절)는 종류와 상관없이 "실행하지 않음"이다."""
    if transport == MANUAL:
        return CONTAMINATION[MANUAL]
    if part["state"] == QUEUED or part["status"] in NOT_STARTED:
        return NOT_RUN
    return CONTAMINATION.get(part["kind"], UNRECORDED)


def _card(spec: dict) -> dict:
    """상위 칸 카드의 화면 표시 — 원장에 저장한 명세에서 네 칸만."""
    return {key: spec.get(key) for key in ("pid", "label", "adapter_id", "model")}


def _seat_result(row) -> dict:
    """상위 모델 호출 행의 결과 칸: 통과한 답, 실패 이유, 실패한 답의 원문, 관측. 결과가 없으면 모두 None."""
    record = json.loads(row["result"]) if row["result"] else {}
    return {"reply": record.get("reply"), "reason": record.get("reason"), "raw": record.get("raw"),
            "observation": record.get("observation")}


def _quorum_label(quorum: dict[str, Any]) -> str:
    """공개된 실행의 정족수 표시. 원본 앱 답을 센 실행은 "독립 정족수 충족"이라고 쓰지 않는다."""
    if quorum["policy"] == INDEPENDENT_ONLY:
        extra = f" · 미확인 답 {quorum['unverified']}개는 보조 근거" if quorum["unverified"] else ""
        return f"독립 정족수 충족 — 독립성이 확인된 참여자 {quorum['confirmed']}명(최소 {quorum['min']}명){extra}"
    return (f"미확인 참여 포함 정족수 — 답 {quorum['counted']}명 중 독립성 확인 {quorum['confirmed']}명"
            f"(최소 {quorum['min']}명)")


class PublicQueries:
    def __init__(self, runtime, invocations, repository):
        self.runtime = runtime
        self.store = runtime.store
        self.invocations = invocations
        self.repository = repository
        self.pages = BrowserPages(self)

    def search(self, query, *, task_id=None, kind=None, limit=30):
        # Keep the same public projection, but do not materialize the whole ledger.
        # Validation precedes all reads; counts and snippets still see public data only.
        catalog.validate(query, task_id=task_id, kind=kind, limit=limit)
        with self.runtime.lock:
            rows = self.store.rows('SELECT run_id, task_id, question, phase FROM runs' +
                                   (' WHERE task_id = ?' if task_id is not None else '') +
                                   ' ORDER BY created_at DESC', *((task_id,) if task_id is not None else ()))
            def public_runs():
                for row in rows:
                    if kind in ('question', 'source'):
                        # Questions and source metadata are already public before reveal.
                        yield {**dict(row), 'sources': self.repository.sources(row['run_id'])
                               if kind == 'source' else [], 'participants': []}
                    else:
                        yield self.view(row['run_id'], _global=False)['runs'][0]
            return catalog.search({'tasks': self.store.rows('SELECT task_id, title FROM tasks'),
                                   'runs': public_runs()}, query, task_id=task_id, kind=kind, limit=limit)

    def overview(self, run_id=None):
        """List projection plus only the selected detail, from one locked snapshot."""
        with self.runtime.lock:
            result = self.view(_summary=True)
            result['settled_real'] = self.store.row("SELECT COUNT(*) AS n FROM participants "
                                                   "WHERE kind = 'real' AND state IN ('accepted', 'rejected')")['n']
            result['runs'] = self.view(run_id, _global=False)['runs'] if run_id else []
            return result

    def source(self, run_id, name):
        with self.runtime.lock:
            row = self.store.row('SELECT content, sha256 FROM sources WHERE run_id = ? AND name = ?', run_id, name)
            if row is None or source_document.digest(row['content']) != row['sha256']:
                raise ControllerError('자료를 찾을 수 없거나 저장한 해시와 다릅니다.')
            return {**source_document.listing(name, row['content']), 'text': row['content'].decode('utf-8')}

    def activity(self, run_id):
        with self.runtime.lock:
            self.repository._run(run_id)
            return {"run_id": run_id, "invocations": [r.public() for r in self.invocations.records(run_id)]}

    def memory_sources(self, run_id):
        """Return the consumed frozen pack, never rerun selection for an old run."""
        with self.runtime.lock:
            run = self.repository._run(run_id)
            config = json.loads(run['role_config'])
            pack = config.get('memory')
            if not pack:
                return {"run_id": run_id, "pack": None, "entries": [], "policy": "legacy-unrecorded"}
            try:
                memory.footer(pack)
            except ValueError as exc:
                raise ControllerError(str(exc)) from None
            entries = []
            for entry in pack['entries']:
                source = self.store.row("SELECT * FROM runs WHERE run_id = ?", entry['run_id'])
                # Locate the frozen source. Availability is distinct from verifying
                # that today's source still has the same contents as the old pack.
                available = bool(source and not source['cancel_requested'] and
                                 source['phase'] in ('revealed', 'synthesis', 'collected') and
                                 source['task_id'] == pack['task_id'])
                entries.append({**entry, "source_available": available,
                                "source_task_id": source['task_id'] if available else None,
                                "selection_recorded": 'selection' in entry})
            return {"run_id": run_id, "pack": pack, "entries": entries,
                    "policy": "frozen_task_history", "current_sources_reselected": False}

    def view(self, run_id: str | None = None, *, _summary=False, _global=True) -> dict[str, Any]:
        """화면에 넘기는 것. 공개 전에는 제출 여부와 실행 상태의 고정된 필드만 넘긴다(BlindBarrier 계약).

        초안의 내용·길이·digest, 토큰 수, 걸린 시간은 공개 뒤에 넘긴다. CLI가 쓴 오류 설명과 runner 메모는 모든
        참여자가 끝난 뒤에 넘긴다 — 그 전에는 그것을 본 사람이 아직 답하는 참여자(원본 앱에 질문을 옮기는
        사용자 포함)에게 영향을 줄 수 있다(A1 리뷰 A1-01).
        """
        with self.runtime.lock:
            runs = []
            # 합성 이력은 요청 하나에서 한 번만 만들어 실행별·전역 투영이 나눠 쓴다(카드 #121, S6). 같은 lock 안이라
            # 요청 사이의 캐시가 아니다 — 매 요청 새로 읽는다
            every = self.invocations._synthesis_attempts(None if _global else run_id, summary=_summary)
            columns = ("run_id, created_at, question, task_id, mode, phase, min_independent, roster, "
                       "reduction_approved, cancel_requested, quorum_policy, '' AS prompt, '' AS input_sha256, "
                       "0 AS input_bytes, json_remove(role_config, '$.memory', '$.task_plan.goal', "
                       "'$.task_plan.done_when', '$.task_plan.dependency_evidence') AS role_config") if _summary else '*'
            query = f"SELECT {columns} FROM runs" + (" WHERE run_id = ?" if run_id is not None else "")
            for run in self.store.rows(query + " ORDER BY created_at DESC", *(() if run_id is None else (run_id,))):
                part_columns = ("pid, spec, state, status, NULL AS detail, kind, "
                                "json_object('usage', json_extract(result, '$.usage')) AS result") if _summary else '*'
                rows = self.store.rows(f"SELECT {part_columns} FROM participants WHERE run_id = ? ORDER BY rowid", run["run_id"])
                current_gate = gate(run, rows)
                general = current_gate.general
                # 일반 팀원은 봉인하지 않는다(요청서 P6): 답·진단·실행 정보를 끝나는 대로 보인다. 다른 실행의 봉인된
                # 답은 이 실행의 투영에 들어오지 않는다 — 행을 이 실행에서만 읽는다.
                revealed, settled = current_gate.revealed, current_gate.settled or current_gate.revealed or general
                keep = SEALED_VIEW_KEYS | (DIAGNOSTIC_KEYS if settled else frozenset())
                assigned = {row["pid"]: row for row in self.store.rows(
                    "SELECT * FROM assignments WHERE run_id = ?", run["run_id"])} if general and not _summary else {}
                parts, calls = [], {"succeeded": 0, "failed": 0, "unknown": 0}
                # 받은 답은 실행마다 한 번에 읽는다(참여자마다 읽지 않는다, S6). 공개 뒤·일반 실행에만 싣는다
                drafts = {d["pid"]: d for d in self.store.rows(
                    "SELECT pid, source, sha256, text FROM drafts WHERE run_id = ?", run["run_id"])} if (revealed or general) and not _summary else {}
                for p in rows:
                    spec = ParticipantSpec(**json.loads(p["spec"]))
                    result = json.loads(p["result"]) if p["result"] else None
                    if result and not (revealed or general):
                        result = {k: v for k, v in result.items() if k in keep}
                    if (spec.transport == CLI and p["state"] in (ACCEPTED, REJECTED, UNKNOWN)
                            and p["status"] not in NOT_STARTED):
                        calls[{"accepted": "succeeded", "rejected": "failed", "unknown": "unknown"}[p["state"]]] += 1
                    item = {"pid": spec.pid, "label": spec.label, "provider": spec.provider,
                            "transport": spec.transport, "behavior": spec.behavior if spec.transport == CLI else None,
                            "adapter_id": spec.adapter_id if spec.transport == CLI else None,
                            "state": p["state"], "status": p["status"], "detail": p["detail"] if settled else None,
                            "contamination": list(_flags(spec.transport, p)) +
                                (["개인 문맥 미확인 — 독립 정족수에 세지 않음"]
                                 if spec.transport == CLI and spec.context_unverified and not general else []),
                            "execution": p["kind"] if spec.transport == CLI else None,
                            # 일반 팀원의 답은 blind 초안이 아니다 — 독립 라벨을 붙이지 않는다
                            "independence": "not_applicable" if general else
                                ("confirmed" if confirmed(asdict(spec)) else "unverified"),
                            "result": result, "dropped": spec.pid in current_gate.dropped}
                    if general and spec.pid in assigned:
                        work = assigned[spec.pid]
                        item["assignment"] = {"task": work["task"], "prompt": work["prompt"],
                                              "input_sha256": work["input_sha256"], "input_bytes": work["input_bytes"],
                                              "sources": json.loads(work["sources"])}
                    if not _summary and current_gate.accepting and spec.transport == MANUAL and p["state"] == AWAITING_USER:
                        item["packet"] = packet(run["run_id"], spec.pid, run["input_sha256"], run["prompt"])
                    if (revealed or general) and p["state"] == ACCEPTED:
                        draft = drafts.get(spec.pid)
                        item["draft"] = draft["text"] if draft else None
                        item["draft_sha256"] = draft["sha256"] if draft else None
                    parts.append(item)
                cli_total = sum(1 for p in parts if p["transport"] == CLI)
                quorum = None if general else dict(current_gate.quorum)   # 일반 실행은 정족수를 세지 않는다
                if quorum is not None:
                    quorum["label"] = _quorum_label(quorum) if revealed else None
                revision, reviewed, memo = self.repository._review_state(run["run_id"])
                judged = revealed or current_gate.collected   # 사람이 판단할 결과 판이 있는가
                runs.append({"run_id": run["run_id"], "created_at": run["created_at"], "question": run["question"],
                             "task_id": run["task_id"], "role_config": json.loads(run["role_config"]),
                             "mode": run["mode"],
                             "reviewed": judged and reviewed,   # 지금 결과 판을 판단 완료했는가(AH-01)
                             "review_memo": memo if judged and reviewed else None,
                             "prompt": run["prompt"], "input_sha256": run["input_sha256"],
                             "input_bytes": run["input_bytes"], "sources": [] if _summary else self.repository.sources(run["run_id"]),
                             "phase": run["phase"],
                             "min_independent": run["min_independent"], "note": current_gate.note,
                             "quorum": quorum, "gate": current_gate.public(),
                             "reduction_approved": bool(run["reduction_approved"]),
                             "cancel_requested": bool(run["cancel_requested"]),
                             "diagnostics_sealed": not settled,
                             "budget": {"used": sum(calls.values()) + sum(1 for p in parts if p["state"] == RUNNING),
                                        "cap": cli_total, "breakdown": calls,
                                        "not_started": sum(1 for p in parts if p["transport"] == CLI
                                                           and p["status"] in NOT_STARTED),
                                        "reserved": (self.store.row("SELECT COUNT(*) AS n FROM events WHERE run_id = ? "
                                                                    "AND kind = 'live_call_reserved'", run["run_id"])["n"]
                                                     if any(p["execution"] == contract.REAL for p in parts) else 0),
                                        "manual": sum(1 for p in parts if p["transport"] == MANUAL)},
                             "participants": parts,
                             "events": [] if _summary else [e["kind"] for e in reversed(self.store.rows(
                                 "SELECT kind FROM events WHERE run_id = ? ORDER BY seq DESC LIMIT 12", run["run_id"]))]})
                refined = self.store.row("SELECT * FROM refinements WHERE run_id = ?", run["run_id"])
                # 원래 목표(원문)와 실제로 보낸 질문을 나란히 보이려고 싣는다(P9). 다듬기는 실행 전의 일이라 봉인과 무관하다
                runs[-1]["refinement"] = self._refinement_view(refined, summary=_summary) if refined else None
                came = self.store.row("SELECT proposal_id, run_id FROM proposals WHERE used_by = ?", run["run_id"])
                runs[-1]["proposal"] = {"proposal_id": came["proposal_id"], "source_run": came["run_id"]} if came else None
                divided = self.store.row(f"SELECT {self._seat_columns('splits') if _summary else '*'} FROM splits WHERE used_by = ?", run["run_id"])
                runs[-1]["split"] = (self._seat_summary(divided, 'orchestrator') if _summary else self._split_view(divided)) if divided else None
                if judged:
                    runs[-1]["result_revision"] = revision   # 판단 완료 버튼이 이 판을 함께 보낸다. 공개·모음 뒤에만 싣는다
                if general and current_gate.collected:
                    # 결과 모으기는 모두 끝난 일반 실행의 일이다(#137). 그 전에는 부를 수도 없고 목록도 비어 있다
                    runs[-1]["collations"] = [(self._seat_summary(row, 'orchestrator') if _summary else self._collation_view(row)) for row in self.store.rows(
                        f"SELECT {self._seat_columns('collations') if _summary else '*'} FROM collations WHERE run_id = ? ORDER BY created_at", run["run_id"])]
                if (general and current_gate.collected) or revealed:
                    # 교차검토 라운드: 격리 실행은 공개 뒤(#140), 일반 실행은 모음 뒤(GR-1). 없으면 None. 일반 실행은 검토 뒤에도
                    # collected다 — 공개·정족수·합성의 관문은 열지 않는다
                    runs[-1]["cross_review"] = ({'reviews': [self._seat_summary(row, 'reviewer') for row in self.store.rows(
                        f"SELECT {self._seat_columns('reviews')} FROM reviews WHERE run_id = ? ORDER BY seq", run['run_id'])]}
                        if _summary else self._cross_review_view(run["run_id"], drafts))
                    # 수정·재검토도 같은 관문이다(일반은 GR-2). 원래 답·합성·취합의 입력은 바꾸지 않는다
                    runs[-1]['answer_revisions'] = self._revisions_view(run['run_id'], summary=_summary)
                if revealed:
                    # 다음 단계 제안은 공개 뒤의 일이다. 봉인 중에는 부를 수도 없고 목록도 비어 있다
                    runs[-1]["proposals"] = [(self._seat_summary(row, 'supervisor') if _summary else self._proposal_view(row)) for row in self.store.rows(
                        f"SELECT {self._seat_columns('proposals') if _summary else '*'} FROM proposals WHERE run_id = ? ORDER BY created_at", run["run_id"])]
                    artifact = None if _summary else self.store.row("SELECT payload FROM events WHERE run_id = ? "
                                              "AND kind = 'synthesis_completed' ORDER BY seq DESC LIMIT 1", run["run_id"])
                    if artifact:
                        runs[-1]["synthesis"] = json.loads(artifact["payload"])["result"]
                    mine = {key: item for key, item in every.items() if key[0] == run["run_id"]}
                    runs[-1]["model_synthesis"] = self._model_synthesis_state(run["run_id"], mine)
                    runs[-1]["model_syntheses"] = [
                        {"attempt": attempt, "status": item["status"], "result": item["result"] or None}
                        for (_, attempt), item in mine.items()]
                # 실행의 토큰 합계(카드 #141). 봉인 중에는 싣지 않는다 — 참여자가 볼 수 있는 채널로 새지 않게
                # (2026-09-24 검토 8번). 일반 실행은 봉인이 없어 처음부터 싣는다
                runs[-1]["usage"] = token_usage.for_run(runs[-1]) if revealed or general else None
            if not _global:
                return {'runs': runs}
            unsettled = self.invocations.unsettled(every)
            # 대기 시도를 controller가 지금 시작하지 않고, 사람이 무언가 해야 풀리는 이유(N3). pump()가 멈추는 두 조건에
            # 더해, 종료 미확인 시도가 병렬 자리를 모두 쥔 경우도 같다 — 진행 중인 시도가 끝나서 풀리는 자리가 아니다.
            unknown_slots = self.invocations._unknown_slots(every)
            held = "paused" if self.runtime.paused else ("unsettled" if unsettled >= self.runtime.unsettled_limit or (
                unknown_slots and unknown_slots >= self.runtime.max_parallel) else None)
            specifications = workflow.plans(self.store)
            if run_id is not None and specifications:
                # Legacy per-run snapshots still expose honest dependency status,
                # while the detail-only read avoids this global projection entirely.
                wanted = {r['task_id'] for r in runs}
                tasks = [t for t in self.view(_summary=True)['tasks'] if t['task_id'] in wanted]
            else:
                tasks = workflow.project_tasks(task_projection(self.store.rows("SELECT * FROM tasks ORDER BY created_at DESC"),
                                                                runs, held=held, plans=specifications), specifications,
                                               workflow.planning_states(self.store))
            # 실행에 쓰지 않은 다듬기: 최근 것과, 끝나지 않았거나 종료 미확인인 차례가 있는 것(오래돼도 정리할 수 있게)
            open_rows = {row["refine_id"]: row for row in self.store.rows(
                "SELECT * FROM refinements WHERE run_id IS NULL ORDER BY created_at DESC LIMIT 20")}
            open_rows.update({row["refine_id"]: row for row in self.store.rows(
                "SELECT * FROM refinements WHERE run_id IS NULL AND refine_id IN "
                "(SELECT refine_id FROM refine_turns WHERE state IN (?, ?))", RUNNING, UNKNOWN)})
            refinements = sorted((self._refinement_view(row) for row in open_rows.values()),
                                 key=lambda item: item["created_at"], reverse=True)
            # 실행에 쓰지 않은 분담 제안도 같은 규칙: 최근 것과, 끝나지 않았거나 종료 미확인인 것
            open_splits = {row["split_id"]: row for row in self.store.rows(
                "SELECT * FROM splits WHERE used_by IS NULL ORDER BY created_at DESC LIMIT 20")}
            open_splits.update({row["split_id"]: row for row in self.store.rows(
                "SELECT * FROM splits WHERE used_by IS NULL AND state IN (?, ?)", RUNNING, UNKNOWN)})
            splits = sorted((self._split_view(row) for row in open_splits.values()),
                            key=lambda item: item["created_at"], reverse=True)
            result = {"executor": self.runtime.executor.name, "live_call_budget": self.invocations.call_budget(), "tasks": tasks,
                    "refinements": refinements, "splits": splits,
                    "provider_call_budgets": {aid: self.invocations.call_budget(aid) for aid in self.runtime.provider_call_caps},
                    "slots": {"used": self.invocations._slots_used(every), "cap": self.runtime.max_parallel},
                    "unsettled": {"count": unsettled, "limit": self.runtime.unsettled_limit},
                    "paused": self.runtime.paused, "runs": runs}
            result['inbox'] = [*workflow.unattached_inputs(refinements, splits), *workflow.inbox(tasks)]
            result['admission'] = workflow.admission(result)
            return result

    @staticmethod
    def _seat_columns(table):
        # Only status and usage are needed for the overview. Never fetch prompt,
        # answer, raw result or copied targets just to render a task row.
        card = {'splits': 'orchestrator', 'collations': 'orchestrator', 'proposals': 'supervisor',
                'reviews': 'reviewer', 'answer_revisions': 'author', 'revision_checks': 'reviewer'}[table]
        identity = 'revision_id, ' if table == 'answer_revisions' else ''
        return identity + f"state, status, kind, {card}, json_object('observation', json_extract(result, '$.observation')) AS result"

    @staticmethod
    def _seat_summary(row, card):
        return {'state': row['state'], 'status': row['status'], 'execution': row['kind'],
                card: _card(json.loads(row[card])), **_seat_result(row)}


    def claude_account_limit(self) -> dict[str, Any] | None:
        """마지막으로 끝난 실제 Claude 시도가 stream에서 받은 계정 한도(rate_limit_event)와 그 관측 시각.

        모델을 더 부르지 않는다. 봉인 중인 실행의 값은 내보내지 않는다 — 계정 비율의 변화도 아직 답하는 참여자의
        초안 길이를 짐작하게 한다(2026-09-24 리뷰 8번). 모의·합성 실행기의 시도는 계정 값이 아니므로 쓰지 않는다.
        """
        with self.runtime.lock:
            for event in self.store.rows("SELECT run_id, at, payload FROM events WHERE kind IN ('draft_sealed', "
                                         "'result_accepted', 'attempt_rejected', 'synthesis_completed', 'synthesis_failed') "
                                         "ORDER BY at DESC LIMIT 200"):
                payload = json.loads(event["payload"])
                result = payload.get("result") or {}
                if "synthesizer" in result:   # 실제 합성은 공개 뒤에만 돈다 — 봉인 중인 초안이 없다
                    limit = result["synthesizer"].get("rate_limit")
                    if limit and result["synthesizer"].get("execution") == contract.REAL:
                        return {**limit, "observed_at": int(event["at"])}
                    continue
                limit = result.get("rate_limit")
                if not limit:
                    continue
                part = self.store.row("SELECT kind FROM participants WHERE run_id = ? AND pid = ? AND attempt = ?",
                                      event["run_id"], payload.get("pid"), payload.get("attempt"))
                current = self.repository._gate(event["run_id"])
                if part is None or part["kind"] != contract.REAL or not (current.settled or current.revealed):
                    continue
                return {**limit, "observed_at": int(event["at"])}
        return None


    def _revisions_view(self, run_id, *, summary=False):
        if summary:
            return [{**self._seat_summary(row, 'author'), 'rechecks': [self._seat_summary(check, 'reviewer')
                     for check in self.store.rows(f"SELECT {self._seat_columns('revision_checks')} FROM revision_checks "
                                                  'WHERE revision_id = ? ORDER BY created_at, check_id', row['revision_id'])]}
                    for row in self.store.rows(f"SELECT {self._seat_columns('answer_revisions')} FROM answer_revisions "
                                               'WHERE run_id = ? ORDER BY created_at, revision_id', run_id)]
        variants = []
        for row in self.store.rows('SELECT * FROM answer_revisions WHERE run_id = ? ORDER BY created_at, revision_id', run_id):
            checks = [{**{k: r[k] for k in ('check_id', 'created_at', 'state', 'status', 'answer_sha256', 'input_sha256', 'prompt')},
                       'execution': r['kind'], 'reviewer': _card(json.loads(r['reviewer'])), **_seat_result(r)}
                      for r in self.store.rows('SELECT * FROM revision_checks WHERE revision_id = ? ORDER BY created_at, check_id', row['revision_id'])]
            variants.append({**{k: row[k] for k in ('revision_id', 'pid', 'parent_id', 'created_at', 'state', 'status',
                                                    'snapshot_sha256', 'input_sha256', 'prompt')},
                             'execution': row['kind'], 'author': _card(json.loads(row['author'])),
                             'snapshot': json.loads(row['snapshot']), 'rechecks': checks, **_seat_result(row)})
        return variants

    def _proposal_view(self, row) -> dict[str, Any]:
        return {"proposal_id": row["proposal_id"], "run_id": row["run_id"], "created_at": row["created_at"],
                "state": row["state"], "status": row["status"], "execution": row["kind"], "used_by": row["used_by"],
                "supervisor": _card(json.loads(row["supervisor"])),
                "labels": json.loads(row["labels"]), "prompt": row["prompt"], "input_sha256": row["input_sha256"],
                **_seat_result(row)}


    def _collation_view(self, row) -> dict[str, Any]:
        return {"collation_id": row["collation_id"], "run_id": row["run_id"], "created_at": row["created_at"],
                "state": row["state"], "status": row["status"], "execution": row["kind"],
                "orchestrator": _card(json.loads(row["orchestrator"])),
                "labels": json.loads(row["labels"]), "prompt": row["prompt"], "input_sha256": row["input_sha256"],
                # 고른 판 취합(GR-3)이 확인한 팀원별 판/hash·미해결·누락. 옛 행(None)은 모두 원래 결과를 모았다
                "selection": json.loads(row["selection"]) if row["selection"] else None,
                "selection_intact": (None if row["selection"] is None else
                                     hashlib.sha256(row["selection"].encode("utf-8")).hexdigest() == row["selection_sha256"]),
                **_seat_result(row)}


    def _cross_review_view(self, run_id: str, drafts: dict) -> dict[str, Any] | None:
        """drafts: view가 이 실행에서 이미 읽은 받은 답(pid → 행). 대상 답이 지금 답과 같은 판인지(fresh)를 본다."""
        rows = self.store.rows("SELECT * FROM reviews WHERE run_id = ? ORDER BY seq", run_id)
        if not rows:
            return None
        # 지금 답의 본문이 기록한 hash와 맞을 때만 그 hash를 "지금 판"으로 본다(CR-01). 대상 본문도 같은 규칙이다
        current = {pid: draft["sha256"] for pid, draft in drafts.items()
                   if isinstance(draft["text"], str)
                   and hashlib.sha256(draft["text"].encode("utf-8")).hexdigest() == draft["sha256"]}
        reviews, missing, reviewed = [], [], 0
        for row in rows:
            record = json.loads(row["result"]) if row["result"] else {}
            spec, targets = json.loads(row["reviewer"]), json.loads(row["targets"])
            reply = record.get("reply")
            if reply:
                chosen = {item["finding"]: item for item in self.store.rows(
                    "SELECT finding, disposition, at FROM review_dispositions WHERE review_id = ?", row["review_id"])}
                reply = {**reply, "findings": [
                    {**finding, "target_pid": targets[finding["target"]]["pid"],
                     "disposition": chosen[index]["disposition"] if index in chosen else "unresolved",
                     "disposition_at": chosen[index]["at"] if index in chosen else None}
                    for index, finding in enumerate(reply["findings"])]}
            for label, target in targets.items():
                if row["state"] == ACCEPTED:
                    reviewed += 1
                else:
                    missing.append({"reviewer": spec["pid"], "target": target["pid"],
                                    "reason": row["status"] or row["state"]})
            snapshot = json.loads(row["snapshot"]) if row["snapshot"] else None
            reviews.append({"review_id": row["review_id"], "seq": row["seq"], "state": row["state"],
                            "status": row["status"], "execution": row["kind"],
                            "reviewer": _card(spec),
                            "labels": json.loads(row["labels"]),
                            "targets": {label: {"pid": t["pid"], "sha256": t["sha256"],
                                                "fresh": current.get(t["pid"]) == t["sha256"] and isinstance(t.get("text"), str)
                                                and hashlib.sha256(t["text"].encode("utf-8")).hexdigest() == t["sha256"]}
                                        for label, t in targets.items()},
                            "prompt": row["prompt"], "input_sha256": row["input_sha256"], "reply": reply,
                            "reason": record.get("reason"), "raw": record.get("raw"),
                            "observation": record.get("observation"),
                            # 일반 검토(GR-1)는 확인한 입력을 함께 보인다. 대상마다 맡은 일·자료 목록은 snapshot에 있다
                            "snapshot": snapshot, "snapshot_sha256": row["snapshot_sha256"]})
        general = rows[0]["snapshot"] is not None
        first = json.loads(rows[0]["snapshot"]) if general else {}
        return {"question": rows[0]["question"], "created_at": rows[0]["created_at"], "reviews": reviews,
                "coverage": {"pairs": reviewed + len(missing), "reviewed": reviewed, "missing": missing},
                "mode": "general" if general else "isolated",
                "round_id": first.get("round_id"), "confirmation": first.get("confirmation"),
                "missing_members": first.get("missing", []),
                "independence": "general_team_not_independent" if general else "post_reveal_not_independent"}


    def _split_view(self, row) -> dict[str, Any]:
        return {"split_id": row["split_id"], "task_id": row["task_id"], "created_at": row["created_at"],
                "goal": row["goal"], "state": row["state"], "status": row["status"], "execution": row["kind"],
                "orchestrator": _card(json.loads(row["orchestrator"])),
                "members": json.loads(row["members"]), "sources": json.loads(row["sources"]),
                "prompt": row["prompt"], "input_sha256": row["input_sha256"], "used_by": row["used_by"],
                "as_proposed": None if row["as_proposed"] is None else bool(row["as_proposed"]),
                **_seat_result(row)}


    def _refinement_view(self, row, *, summary=False) -> dict[str, Any]:
        """다듬기 한 건의 화면 투영. 원문·차례별 보낸 입력·받은 답(또는 실패 이유와 원문)·사람이 쓴 말을 그대로 보인다."""
        turns = []
        columns = ("turn, '' AS note, state, status, kind, '' AS prompt, '' AS input_sha256, "
                   "json_object('observation', json_extract(result, '$.observation')) AS result") if summary else '*'
        for turn in self.store.rows(f"SELECT {columns} FROM refine_turns WHERE refine_id = ? ORDER BY turn", row["refine_id"]):
            turns.append({"turn": turn["turn"], "note": turn["note"], "state": turn["state"], "status": turn["status"],
                          "execution": turn["kind"], "prompt": turn["prompt"], "input_sha256": turn["input_sha256"],
                          **_seat_result(turn)})
        return {"refine_id": row["refine_id"], "created_at": row["created_at"], "original": row["original"],
                "supervisor": _card(json.loads(row["supervisor"])),
                "run_id": row["run_id"], "approved_turn": row["approved_turn"], "max_turns": refining.MAX_TURNS,
                "turns": turns}


    def _model_synthesis_state(self, run_id: str, attempts: dict | None = None) -> dict[str, Any] | None:
        """같은 사건 투영으로 진행·실패·종료 미확인을 보인다. 과거 미확인 시도도 숨기지 않는다. attempts: 이 실행의
        합성 이력(view가 요청마다 한 번 만든 것에서 잘라 넘긴다). 없으면 새로 읽는다."""
        attempts = self.invocations._synthesis_attempts(run_id) if attempts is None else attempts
        if not attempts:
            return None
        unknown = [attempt for (_, attempt), item in attempts.items() if item["status"] == UNKNOWN]
        if unknown:
            return {"status": UNKNOWN, "attempts": unknown,
                    "message": "합성 자손의 종료를 확인하지 못했습니다. 자리는 유지하며 재호출·환불하지 않습니다."}
        if run_id in self.runtime.syntheses:
            return {"status": RUNNING}
        latest = list(attempts.values())[-1]
        if latest["status"] == "completed":
            return {"status": "completed"}
        if latest["status"] == "acknowledged":
            return {"status": "acknowledged", "message": "사용자가 종료를 확인했습니다. 재호출·환불하지 않습니다."}
        result = latest["result"]
        state = {"status": "failed", "message": result.get("message"), "reason": result.get("reason"),
                 "synthesizer": result.get("synthesizer")}
        if result.get("raw"):   # 형식 검사에 실패한 원문. 옛 사건에는 이 칸이 없다
            state["raw"] = result["raw"]
        return state
