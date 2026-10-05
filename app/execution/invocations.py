"""One accounting and occupancy view over legacy participants, role calls and synthesis."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import json
from app.state import CLI, RUNNING, UNKNOWN, synthesis_attempts
from core import runner
from app.domain import ParticipantSpec, ControllerError, _CapReached
from app.execution.seats import SEATS


@dataclass(frozen=True)
class Invocation:
    """Read adapter, not a new execution table or success interpretation."""
    invocation_id: str
    aggregate_id: str
    run_id: str | None
    purpose: str
    attempt: str
    state: str
    execution: str | None
    adapter_id: str | None
    origin: dict

    def public(self):
        # No prompt, output, timing, usage, digest or free-text diagnostics.
        return asdict(self)


class InvocationLedger:
    def __init__(self, runtime):
        self.runtime = runtime
        self.store = runtime.store

    def reserve(self, tx, aggregate_id, *, pid, attempt, adapter_id, purpose=None):
        """Reserve a real call in the caller's state/start transaction; never refund.

        The caller has checked the final plan kind and holds the runtime lock.
        This is the only writer of live_call_reserved across all model roles.
        """
        if self.runtime.max_real_calls is None:
            return
        if self._budget_exhausted(adapter_id):
            raise _CapReached("real CLI call budget exhausted; no call was started")
        tx.event(aggregate_id, "live_call_reserved", pid=pid, attempt=attempt,
                 adapter_id=adapter_id, cap=self.runtime.max_real_calls,
                 **({"purpose": purpose} if purpose else {}))

    def records(self, run_id: str):
        """Normalize persisted attempts for one run without replay or mutation.

        Queued reviews, manual answers and mock synthesis have no invocation ID
        and are not invented as model calls. Acknowledged unknowns retain their
        original attempt and reservation in the source ledger.
        """
        with self.runtime.lock:
            found = []

            def add(table, keys, aggregate, purpose, row, adapter, execution=None):
                if not row['attempt']:
                    return
                origin = {"table": table, "keys": keys}
                identity = json.dumps([table, keys, row['attempt']], sort_keys=True, separators=(',', ':'))
                found.append(Invocation(identity, aggregate, run_id, purpose, row['attempt'], row['state'],
                                        row['kind'] if execution is None else execution, adapter, origin))

            for row in self.store.rows("SELECT pid, spec, attempt, state, kind FROM participants "
                                       "WHERE run_id = ? AND attempt IS NOT NULL ORDER BY rowid", run_id):
                spec = json.loads(row['spec'])
                if spec['transport'] == CLI:
                    add('participants', {'run_id': run_id, 'pid': row['pid']}, run_id, 'draft', row,
                        spec.get('adapter_id'))
            for seat in SEATS:
                card = seat.card_column
                if seat.purpose == 'refine':
                    query = ('SELECT t.refine_id, t.turn, t.attempt, t.kind, t.state, f.supervisor '
                             'FROM refine_turns t JOIN refinements f USING (refine_id) '
                             'WHERE f.run_id = ? ORDER BY t.turn')
                else:
                    column = 'used_by' if seat.purpose == 'split' else 'run_id'
                    columns = ', '.join(dict.fromkeys((*seat.keys, seat.event_column, card, 'attempt', 'kind', 'state')))
                    query = f'SELECT {columns} FROM {seat.table} WHERE {column} = ? ORDER BY created_at'
                for row in self.store.rows(query, run_id):
                    spec = json.loads(row[card])
                    add(seat.table, {key: row[key] for key in seat.keys}, row[seat.event_column],
                        seat.purpose, row, spec.get('adapter_id'))
            starts = {json.loads(row['payload']).get('attempt'): json.loads(row['payload'])
                      for row in self.store.rows("SELECT payload FROM events WHERE run_id = ? "
                                                 "AND kind = 'synthesis_started' ORDER BY seq", run_id)}
            for (_, attempt), item in self._synthesis_attempts(run_id).items():
                start = starts.get(attempt, {})
                add('events', {'run_id': run_id, 'attempt': attempt}, run_id, 'synthesis',
                    {'attempt': attempt, 'state': item['status'], 'kind': start.get('execution')},
                    start.get('adapter_id'))
            return tuple(found)

    def _synthesis_attempts(self, run_id: str | None = None, *, summary=False) -> dict:
        """한 사건 투영을 호출 제한·자리·종료 확인·화면이 같이 사용한다. controller.lock 안에서 읽는다."""
        payload = ("json_object('attempt', json_extract(payload, '$.attempt'), 'result', "
                   "json_object('status', json_extract(payload, '$.result.status'), "
                   "'synthesizer', json_extract(payload, '$.result.synthesizer'))) AS payload") if summary else 'payload'
        rows = self.store.rows(f"SELECT run_id, kind, {payload} FROM events WHERE kind IN "
                               "('synthesis_started', 'synthesis_failed', 'synthesis_completed', "
                               "'synthesis_unknown_acknowledged')" + (" AND run_id = ?" if run_id else "") +
                               " ORDER BY run_id, seq", *((run_id,) if run_id else ()))
        return synthesis_attempts(rows, ((rid, worker[2]) for rid, worker in self.runtime.syntheses.items()))


    def _seat_count(self, *states: str) -> int:
        """상위 모델 호출(SEATS의 모든 표)에서 주어진 상태인 행의 수."""
        marks = ", ".join("?" for _ in states)
        return sum(self.store.row(f"SELECT COUNT(*) AS n FROM {seat.table} WHERE state IN ({marks})", *states)["n"]
                   for seat in SEATS)


    def _slots_used(self, attempts: dict | None = None) -> int:
        """attempts: 같은 요청에서 이미 만든 전역 합성 이력(view가 한 번 만들어 넘긴다, S6). 없으면 새로 읽는다."""
        attempts = self._synthesis_attempts() if attempts is None else attempts
        return sum(item["status"] in (RUNNING, UNKNOWN) for item in attempts.values()) + self.store.row(
            "SELECT COUNT(*) AS n FROM participants WHERE state IN (?, ?)", RUNNING, UNKNOWN)["n"] + self._seat_count(
            RUNNING, UNKNOWN)


    def _budget_exhausted(self, adapter_id: str) -> bool:
        """전체·provider 상한. 거래 안에서 읽고 같은 거래에서 예약한다 — 병렬 요청이 마지막 한 칸을 함께 쓰지 못한다."""
        budget, provider = self.call_budget(), self.call_budget(adapter_id)
        return budget["used"] >= budget["cap"] or bool(self.runtime.provider_call_caps and (
            provider["cap"] is None or provider["used"] >= provider["cap"]))


    def _unknown_slots(self, attempts: dict | None = None) -> int:
        """종료를 확인하지 못해 자리를 쥔 시도: 참여자·합성·상위 모델 호출(다듬기·제안·분담·모으기·검토)."""
        attempts = self._synthesis_attempts() if attempts is None else attempts
        return (self.store.row("SELECT COUNT(*) AS n FROM participants WHERE state = ?", UNKNOWN)["n"]
                + sum(item["status"] == UNKNOWN for item in attempts.values())
                + self._seat_count(UNKNOWN))


    def unsettled(self, attempts: dict | None = None) -> int:
        with self.runtime.lock:
            return self._unknown_slots(attempts) + runner.lingering()


    def call_budget(self, adapter_id: str | None = None) -> dict[str, int | None]:
        """실제 CLI를 시작하기 전에 원장에 예약한다. 재시작·실패·취소로 환불하지 않는다(계정 잔여와 다름)."""
        if self.runtime.max_real_calls is None:
            return {"used": 0, "cap": None}
        reservations = self.store.rows("SELECT payload FROM events WHERE kind = 'live_call_reserved'")
        used = len(reservations) if adapter_id is None else sum(
            json.loads(row["payload"]).get("adapter_id") == adapter_id for row in reservations)
        return {"used": used, "cap": self.runtime.max_real_calls if adapter_id is None
                else self.runtime.provider_call_caps.get(adapter_id)}


    def _supervisor_busy(self) -> bool:
        """상위 모델 호출은 다듬기·제안·분담·모으기를 통틀어 한 번에 하나다. 버튼을 두 번 누르거나 창 두 개에서 불러도
        둘째를 시작하지 않는다(Codex 교차검토, PR #131). 종료 미확인도 아직 돌고 있을 수 있으므로 사람이 종료를 확인할
        때까지 다른 실행·다른 창의 상위 모델 호출까지 막는다(Codex 교차검토, PR #139)."""
        return self._seat_count(RUNNING, UNKNOWN) > 0


    def _upper_call_gate(self, what: str) -> None:
        """상위 모델 호출(다듬기·제안·분담·모으기·검토)의 공통 관문. 호출하는 쪽이 self.lock을 쥔다. 한 번에 하나 →
        멈춤·종료 미확인 → 자리 → 진행 중인 실행 순으로 본다. 여기서 거절하면 아무것도 예약하지 않았다. what은 거절
        문구의 주어("다듬기는" 처럼 조사까지)다."""
        if self._supervisor_busy():
            raise ControllerError("다른 상위 모델 호출(다듬기·제안·분담·모으기·검토)이 진행 중이거나 끝났는지 모릅니다. "
                                  "끝나거나 종료를 확인한 뒤에 다시 부르세요.")
        if self.runtime.paused or self.unsettled() >= self.runtime.unsettled_limit:
            raise ControllerError("execution is paused or has unsettled attempts; no call was started")
        if self._slots_used() >= self.runtime.max_parallel:
            raise ControllerError("parallel execution limit reached; no call was started")
        if self.store.row("SELECT 1 FROM runs WHERE phase = 'drafting' AND NOT cancel_requested"):
            raise ControllerError(f"진행 중인 실행을 먼저 정리하세요. {what} 실행이 없을 때만 부릅니다.")


    def _cli_card(self, spec: ParticipantSpec, who: str) -> None:
        """상위 칸(슈퍼바이저·오케스트레이터)의 카드는 이 실행기가 받는 CLI 카드여야 한다."""
        if spec.transport != CLI or spec.adapter_id not in self.runtime.executor.adapter_ids:
            raise ControllerError(f"{who}는 설정된 CLI 카드여야 합니다.")
