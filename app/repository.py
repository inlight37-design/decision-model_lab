"""Row-backed identities, transitions and revision policy over the existing ledger."""
from __future__ import annotations
import json
from typing import Any
from app.state import QUEUED, RUNNING, AWAITING_USER, ACCEPTED, REJECTED, UNKNOWN, RunGate, gate
from app.domain import ControllerError


class RunRepository:
    def __init__(self, runtime):
        self.runtime = runtime
        self.store = runtime.store

    def _run(self, run_id: str):
        run = self.store.row("SELECT * FROM runs WHERE run_id = ?", run_id)
        if run is None:
            raise ControllerError(f"no run {run_id!r}")
        return run


    def _part(self, run_id: str, pid: str):
        part = self.store.row("SELECT * FROM participants WHERE run_id = ? AND pid = ?", run_id, pid)
        if part is None:
            raise ControllerError(f"no participant {pid!r} in {run_id!r}")
        return part


    def _gate(self, run_id: str) -> RunGate:
        """Read inside a Store transaction for decisions that change state."""
        return gate(self._run(run_id), self.store.rows(
            "SELECT pid, state, spec FROM participants WHERE run_id = ? ORDER BY rowid", run_id))


    @staticmethod
    def _transition(tx, expected, state: str, **changes) -> bool:
        """One participant mutation path: both the old state and attempt must still match.

        NULL is a real expected attempt for manual/queued participants, not a wildcard.
        The caller writes the corresponding event/draft only when this succeeds.
        """
        allowed = {QUEUED: (RUNNING, REJECTED), RUNNING: (ACCEPTED, REJECTED, UNKNOWN),
                   AWAITING_USER: (ACCEPTED, REJECTED), UNKNOWN: (REJECTED,)}
        if state not in allowed.get(expected["state"], ()):
            raise ControllerError(f"invalid participant transition {expected['state']} -> {state}")
        if set(changes) - {"status", "detail", "result", "attempt", "kind"}:
            raise ControllerError("invalid participant transition fields")
        updates = {"state": state, **changes}
        assignments = ", ".join(f"{name} = ?" for name in updates)
        return bool(tx.execute(f"UPDATE participants SET {assignments} "
                               "WHERE run_id = ? AND pid = ? AND state = ? AND attempt IS ?",
                               *updates.values(), expected["run_id"], expected["pid"],
                               expected["state"], expected["attempt"]))


    def _review_state(self, run_id: str) -> tuple[int, bool, str | None]:
        """(결과 판, 그 판을 판단 완료했는가, 그때 남긴 취합 메모). 판은 사람이 보는 결과를 바꾼 마지막 사건의 seq다 —
        공개, 일반 실행의 모음, 합성 완료·실패, 다음 단계 제안·결과 모으기·교차검토의 결과. 판단 완료 사건이 그보다 뒤에 있어야 그 판을 본 것이다. 새 합성이 끝나면
        판이 올라가 다시 내 차례가 된다(AH-01). 판을 싣지 않은 옛 원장의 판단 완료 사건도 같은 순서 규칙으로 읽는다."""
        row = self.store.row(
            "SELECT COALESCE(MAX(CASE WHEN kind IN ('revealed', 'collected', 'synthesis_completed', 'synthesis_failed', "
            "'proposal_completed', 'proposal_failed', 'collation_completed', 'collation_failed', "
            "'review_completed', 'review_failed', 'review_skipped', "
            # 종료 미확인도 새 결과다 — 종료 확인이 판단을 대신하지 않게 판을 올린다(Codex 교차검토, PR #144)
            "'proposal_unknown', 'collation_unknown', 'review_unknown', "
            "'revision_completed', 'revision_failed', 'revision_unknown', 'revision_result_not_stored', "
            "'recheck_completed', 'recheck_failed', 'recheck_unknown', 'recheck_result_not_stored') "
            "THEN seq END), 0) AS revision, "
            "COALESCE(MAX(CASE WHEN kind = 'human_reviewed' THEN seq END), 0) AS reviewed "
            "FROM events WHERE run_id = ?", run_id)
        memo = None
        if row["reviewed"]:
            payload = self.store.row("SELECT payload FROM events WHERE run_id = ? AND seq = ?", run_id, row["reviewed"])
            memo = json.loads(payload["payload"]).get("memo")
        return row["revision"], row["reviewed"] > row["revision"], memo


    def sources(self, run_id: str) -> list[dict[str, Any]]:
        """화면·보고에 보일 목록. 내용은 넘기지 않는다."""
        return [{"name": row["name"], "sha256": row["sha256"], "bytes": row["bytes"]} for row in self.store.rows(
            "SELECT name, sha256, bytes FROM sources WHERE run_id = ? ORDER BY name", run_id)]


    def _check_role_synthesizer(self, run_id, adapter_id=None):
        roles = json.loads(self._run(run_id)["role_config"])
        if roles["source"] != "board":
            return None  # 이전 실행의 수동 합성 선택은 그대로 둔다.
        spec = roles["orchestrator"]
        if spec is None:
            raise ControllerError("오케스트레이터는 나입니다. 원문 대조표를 직접 판단하세요. 합성은 부르지 않습니다.")
        if adapter_id is not None and spec["adapter_id"] != adapter_id:
            raise ControllerError("시작할 때 고정한 오케스트레이터와 다릅니다. 바꾸려면 새 실행을 만드세요.")
        return spec
