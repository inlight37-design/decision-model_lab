"""Row-backed identities, transitions and revision policy over the existing ledger."""
from __future__ import annotations
import hashlib
import json
from typing import Any
from app.state import QUEUED, RUNNING, AWAITING_USER, ACCEPTED, REJECTED, UNKNOWN, RunGate, gate
from app.domain import ControllerError
from app import source_document

# 사람이 보는 결과를 바꾸는 사건 — 공개, 일반 실행의 모음, 합성 완료·실패, 다음 단계 제안·결과 모으기·교차검토의 결과,
# 수정·재검토의 결과. 종료 미확인도 새 결과다 — 종료 확인이 판단을 대신하지 않게 판을 올린다(Codex 교차검토, PR #144).
RESULT_EVENTS = ('revealed', 'collected', 'synthesis_completed', 'synthesis_failed',
                 'proposal_completed', 'proposal_failed', 'collation_completed', 'collation_failed',
                 'review_completed', 'review_failed', 'review_skipped',
                 'proposal_unknown', 'collation_unknown', 'review_unknown',
                 'revision_completed', 'revision_failed', 'revision_unknown', 'revision_result_not_stored',
                 'recheck_completed', 'recheck_failed', 'recheck_unknown', 'recheck_result_not_stored')
_RESULT_KINDS = ", ".join(f"'{kind}'" for kind in RESULT_EVENTS)


def review_state(store, run_id: str) -> dict[str, Any]:
    """결과 판과 마지막 판단 완료의 관계. 판은 RESULT_EVENTS 중 마지막 사건의 seq다. 판단 완료 사건이 그보다 뒤에 있어야
    현재 판을 본 것이다. 새 합성이 끝나면 판이 올라가 다시 내 차례가 된다(AH-01). 판단이 본 판은 사건에 실린 revision이고,
    판을 싣지 않은 옛 원장의 판단 완료 사건은 같은 순서 규칙으로 그 앞의 마지막 결과 사건에서 읽는다. 지적 처분은 판을
    올리지 않으므로 판단 뒤에 처분이 바뀌었는지를 따로 센다. 화면·판단 완료·기억이 이 한 계산을 함께 쓴다(CR-02)."""
    row = store.row(
        f"SELECT COALESCE(MAX(CASE WHEN kind IN ({_RESULT_KINDS}) THEN seq END), 0) AS revision, "
        "COALESCE(MAX(CASE WHEN kind = 'human_reviewed' THEN seq END), 0) AS reviewed "
        "FROM events WHERE run_id = ?", run_id)
    state = {"result_revision": row["revision"], "judgment": None, "judgment_revision": None,
             "judgment_is_current": row["reviewed"] > row["revision"], "dispositions_changed_after_judgment": False}
    if row["reviewed"]:
        payload = json.loads(store.row("SELECT payload FROM events WHERE run_id = ? AND seq = ?",
                                       run_id, row["reviewed"])["payload"])
        seen = payload.get("revision")
        if type(seen) is not int:
            seen = store.row(f"SELECT COALESCE(MAX(seq), 0) AS seq FROM events WHERE run_id = ? AND seq < ? "
                             f"AND kind IN ({_RESULT_KINDS})", run_id, row["reviewed"])["seq"]
        changed = store.row("SELECT 1 FROM events WHERE run_id = ? AND seq > ? AND kind = 'review_disposition' LIMIT 1",
                            run_id, row["reviewed"])
        state.update(judgment=payload, judgment_revision=seen, dispositions_changed_after_judgment=changed is not None)
    return state


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
        """(결과 판, 그 판을 판단 완료했는가, 그때 남긴 취합 메모). 계산은 `review_state`가 한다."""
        state = review_state(self.store, run_id)
        return state["result_revision"], state["judgment_is_current"], (state["judgment"] or {}).get("memo")


    def _answers(self, run_id: str) -> list[dict[str, Any]]:
        """참여자 순서대로 {pid, spec, state, text, sha256}. 받은 답(accepted)만 본문을 싣고, 그 본문은 저장된 sha256과
        다시 맞춘다 — 본문이 없거나 어긋나면 거절한다(CR-01). 받지 못한 팀원은 text·sha256이 None이다. 교차검토·결과
        모으기가 모델에 넘기기 전에 이 확인을 거친다. 입력 hash를 새로 계산하는 것은 이 확인을 대신하지 않는다."""
        drafts = {row["pid"]: row for row in self.store.rows(
            "SELECT pid, text, sha256 FROM drafts WHERE run_id = ?", run_id)}
        answers = []
        for part in self.store.rows("SELECT pid, spec, state FROM participants WHERE run_id = ? ORDER BY rowid", run_id):
            item = {"pid": part["pid"], "spec": json.loads(part["spec"]), "state": part["state"],
                    "text": None, "sha256": None}
            if part["state"] == ACCEPTED:
                draft = drafts.get(part["pid"])
                if (draft is None or not isinstance(draft["text"], str) or draft["sha256"] !=
                        hashlib.sha256(draft["text"].encode("utf-8")).hexdigest()):
                    raise ControllerError("저장된 답이 기록된 해시와 맞지 않습니다. 호출을 시작하지 않았습니다.")
                item.update(text=draft["text"], sha256=draft["sha256"])
            answers.append(item)
        return answers


    def sources(self, run_id: str) -> list[dict[str, Any]]:
        """화면·보고에 보일 목록. 내용은 넘기지 않는다."""
        prefix = source_document.PREFIX.encode('utf-8')
        rows = self.store.rows('SELECT name, sha256, bytes, CASE WHEN substr(content, 1, ?) = ? '
                               'THEN substr(content, 1, 32100) END AS header FROM sources WHERE run_id = ? ORDER BY name',
                               len(prefix), prefix, run_id)
        result = []
        for row in rows:
            item = {k: row[k] for k in ('name', 'sha256', 'bytes')}
            if row['header'] is not None:
                try:
                    meta = source_document.metadata(row['header'], header_only=True)
                    item.update(kind='extracted', range='selected', provenance=meta)
                except ControllerError:
                    item.update(kind='extracted', provenance_error=True)
            result.append(item)
        return result


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
