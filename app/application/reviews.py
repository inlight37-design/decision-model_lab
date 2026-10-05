"""Collation, bounded cross-review and human dispositions over immutable source answers."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
import os
import time
import uuid
from app import collate as collating, cross_review as cross
from app.synthesis import label_order
from app.state import CLI, QUEUED, RUNNING, ACCEPTED, UNKNOWN
from core import contract
from app.domain import ParticipantSpec, ControllerError, _CapReached, storable, _storable_meta, MAX_MEMO_CHARS
from app.execution.seats import COLLATE_SEAT, REVIEW_SEAT


class ReviewService:
    def __init__(self, runtime, execution, inputs, invocations, repository):
        self.runtime = runtime
        self.store = runtime.store
        self.execution = execution
        self.inputs = inputs
        self.invocations = invocations
        self.repository = repository

    def collate(self, run_id: str) -> str:
        """모두 끝난 일반 실행의 팀원 결과를 역할판의 오케스트레이터 모델이 원문 인용으로 취합한다 — 호출 1회.

        오케스트레이터는 전체 목표와 팀원마다 맡긴 일·결과 원문(이름표 T1·T2, 결과가 없으면 "결과 없음")을 받는다. 자료
        원문은 주지 않는다. 인용은 이 호출이 받은 원문과 글자 그대로 대조하고, 사실 검증은 하지 않는다. 실행 하나에
        collate.MAX_PER_RUN번까지, 다른 상위 모델 호출과 같은 관문(한 번에 하나·예약·상한·종료 미확인·재시작)을 지난다.
        판단 완료는 사람이 한다."""
        with self.runtime.lock:
            if self.runtime.closing:
                raise ControllerError("controller is shutting down")
            run = self.repository._run(run_id)
            roles = json.loads(run["role_config"]) if run["role_config"] else {}
            orchestrator = roles.get("orchestrator")
            current_gate = self.repository._gate(run_id)
            if not current_gate.general or not current_gate.collected:
                raise ControllerError("결과 모으기는 모두 끝난 일반 팀원 작업에만 부릅니다.")
            if not orchestrator:
                raise ControllerError("오케스트레이터 칸이 비어 있습니다(나). 결과는 내가 모읍니다.")
            if self.store.row("SELECT COUNT(*) AS n FROM collations WHERE run_id = ?", run_id)["n"] >= collating.MAX_PER_RUN:
                raise ControllerError(f"결과 모으기는 실행 하나에 {collating.MAX_PER_RUN}번까지입니다.")
            if self.store.row("SELECT 1 FROM collations WHERE run_id = ? AND state = ?", run_id, UNKNOWN):
                raise ControllerError("끝났는지 모르는 결과 모으기가 있습니다. 종료를 먼저 확인하세요.")
            self.invocations._upper_call_gate("결과 모으기는")
            spec = ParticipantSpec(**orchestrator)
            self.invocations._cli_card(spec, "오케스트레이터")
            members, labels, drafts = [], {}, {}
            for index, part in enumerate(self.store.rows(
                    "SELECT pid, spec, state FROM participants WHERE run_id = ? ORDER BY rowid", run_id), 1):
                label, member = f"T{index}", ParticipantSpec(**json.loads(part["spec"]))
                work = self.inputs._assignment(run_id, member.pid)
                draft = self.store.row("SELECT text FROM drafts WHERE run_id = ? AND pid = ?", run_id, member.pid)
                text = draft["text"] if draft and part["state"] == ACCEPTED else None
                labels[label], drafts[label] = member.pid, text
                members.append({"label": label, "name": member.label, "task": work["task"], "text": text})
            text = collating.prompt(run["question"], members)
            text += self.inputs._run_memory(run)
            key = f"c{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"

            def insert(tx, attempt, kind):
                tx.execute("INSERT INTO collations (collation_id, run_id, created_at, orchestrator, labels, drafts, prompt, "
                           "input_sha256, attempt, kind, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", key, run_id,
                           time.time(), json.dumps(orchestrator, ensure_ascii=False), json.dumps(labels),
                           json.dumps(drafts, ensure_ascii=False), text, hashlib.sha256(text.encode("utf-8")).hexdigest(),
                           attempt, kind, RUNNING)

            self.execution._start_seat(COLLATE_SEAT, run_id, {"collation_id": key}, spec, text,
                             os.path.join(self.runtime.work_root, run_id, f"collation-{key[-12:]}"), insert)
            return key


    def acknowledge_collation_unknown(self, collation_id: str) -> None:
        """사람이 그 결과 모으기 호출의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않는다."""
        row = self.store.row("SELECT run_id FROM collations WHERE collation_id = ?", collation_id)
        if row is None:
            raise ControllerError("결과 모으기를 찾을 수 없습니다.")
        self.execution._acknowledge_seat(COLLATE_SEAT, row["run_id"], {"collation_id": collation_id})


    def cross_review(self, run_id: str, question: str | None = None) -> list[str]:
        """공개된 격리 실행에서 교차검토 한 라운드를 연다 — 받은 답을 낸 CLI 팀원 한 명 = 호출 1회.

        검토자는 답을 낸 그 카드·모델이다(같은 관측된 계획, 읽기 전용). 자기 답(따로 표시)과 다른 팀원의 답(이름표,
        검토자마다 섞은 순서)과 검토 질문을 받는다. 원본 앱 팀원의 답은 대상으로만 들어간다. 입력은 여기서 모두 고정하고,
        검토자는 다른 상위 모델 호출처럼 한 번에 하나씩 차례로 부른다(pump). 앞 검토자가 받지 못하면(실패·종료
        미확인·상한·시작 못 함) 남은 검토자는 시작하지 않는다. 실행 하나에 한 라운드. 공개 뒤 다른 답을 본 검토라
        독립 정족수에 세지 않는다. 검토는 새 실행을 시작하지 않고, 지적의 처분은 사람이 한다."""
        question = question.strip() if isinstance(question, str) else ""
        question = question or cross.DEFAULT_QUESTION
        if len(question) > cross.MAX_QUESTION or not storable(question):
            raise ControllerError(f"검토 질문은 {cross.MAX_QUESTION}자까지의 올바른 글이어야 합니다.")
        with self.runtime.lock:
            if self.runtime.closing:
                raise ControllerError("controller is shutting down")
            run = self.repository._run(run_id)
            current_gate = self.repository._gate(run_id)
            if current_gate.general or not current_gate.revealed:
                raise ControllerError("교차검토는 공개된 격리 실행에만 부릅니다. 봉인 중에는 부르지 않습니다.")
            if self.store.row("SELECT 1 FROM reviews WHERE run_id = ?", run_id):
                raise ControllerError("교차검토는 실행 하나에 한 라운드입니다.")
            self.invocations._upper_call_gate("교차검토는")
            answers = {}   # pid → (명세, 답 원문, sha256). 받은 답만, 참여자 순서대로
            for part in self.store.rows("SELECT pid, spec, state FROM participants WHERE run_id = ? ORDER BY rowid",
                                        run_id):
                draft = self.store.row("SELECT text, sha256 FROM drafts WHERE run_id = ? AND pid = ?", run_id, part["pid"])
                if part["state"] == ACCEPTED and draft:
                    answers[part["pid"]] = (ParticipantSpec(**json.loads(part["spec"])), draft["text"], draft["sha256"])
            reviewers = [pid for pid, (spec, _, _) in answers.items()
                         if spec.transport == CLI and spec.adapter_id in self.runtime.executor.adapter_ids]
            if len(answers) < 2 or not reviewers:
                raise ControllerError("교차검토에는 받은 답이 둘 이상이고, 그중 설정된 CLI 팀원이 하나 이상 있어야 합니다.")
            first = answers[reviewers[0]][0]
            if (self.runtime.executor.kind == contract.REAL and self.runtime.max_real_calls is not None
                    and self.invocations._budget_exhausted(first.adapter_id)):
                raise ControllerError("real CLI call budget exhausted; no call was started")
            keys, now = [], time.time()
            with self.store.tx() as tx:
                for seq, pid in enumerate(reviewers, 1):
                    spec, own, _ = answers[pid]
                    others = [other for other in answers if other != pid]
                    labels = {f"D{index}": other for index, other in
                              enumerate(label_order(f"{run_id}\0review\0{pid}", others), 1)}
                    targets = {label: {"pid": other, "sha256": answers[other][2], "text": answers[other][1]}
                               for label, other in labels.items()}
                    text = cross.prompt(question, run["question"], own,
                                        [(label, item["text"]) for label, item in targets.items()])
                    key = f"v{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"
                    tx.execute("INSERT INTO reviews (review_id, run_id, seq, created_at, question, reviewer, labels, "
                               "targets, prompt, input_sha256, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               key, run_id, seq, now, question, json.dumps(asdict(spec), ensure_ascii=False),
                               json.dumps(labels), json.dumps(targets, ensure_ascii=False), text,
                               hashlib.sha256(text.encode("utf-8")).hexdigest(), QUEUED)
                    keys.append(key)
                tx.event(run_id, "review_round_created", reviewers=reviewers, calls=len(reviewers),
                         default_question=question == cross.DEFAULT_QUESTION)
            self._advance_reviews(start=True)
            return keys


    def _advance_reviews(self, *, start: bool) -> None:
        """교차검토 라운드를 한 걸음 진행한다. pump가 lock 안에서 부른다. 앞 검토자가 받지 못했으면(실패·종료 미확인·
        상한·시작 못 함) 남은 검토자를 시작하지 않고 그 이유로 닫는다 — 닫는 것은 관문과 상관없이 한다. start이면 관문
        (한 번에 하나·자리·진행 중인 실행 없음)이 허락할 때 다음 검토자 하나를 시작한다. 한 번에 하나만 부른다."""
        for item in self.store.rows("SELECT run_id FROM reviews WHERE state = ? GROUP BY run_id "
                                    "ORDER BY MIN(created_at)", QUEUED):
            run_id = item["run_id"]
            rows = self.store.rows("SELECT * FROM reviews WHERE run_id = ? ORDER BY seq", run_id)
            if any(row["state"] == RUNNING for row in rows):
                continue
            done = [row for row in rows if row["state"] != QUEUED]
            if done and done[-1]["state"] != ACCEPTED:
                self._close_reviews(run_id, "earlier_reviewer_not_accepted")
                continue
            if not start or self.invocations._supervisor_busy() or self.invocations._slots_used() >= self.runtime.max_parallel or self.store.row(
                    "SELECT 1 FROM runs WHERE phase = 'drafting' AND NOT cancel_requested"):
                continue
            row = next(row for row in rows if row["state"] == QUEUED)
            spec = ParticipantSpec(**json.loads(row["reviewer"]))

            def insert(tx, attempt, kind, review_id=row["review_id"]):
                if not tx.execute("UPDATE reviews SET state = ?, attempt = ?, kind = ? WHERE review_id = ? AND state = ?",
                                  RUNNING, attempt, kind, review_id, QUEUED):
                    raise ControllerError("this reviewer was already started")

            try:
                self.execution._start_seat(REVIEW_SEAT, run_id, {"review_id": row["review_id"]}, spec, row["prompt"],
                                 os.path.join(self.runtime.work_root, run_id, f"review-{row['review_id'][-12:]}"), insert)
            except _CapReached:
                self._close_reviews(run_id, "cap_reached")
            except ControllerError as exc:   # 계획 거절 등: 이 검토자부터 시작하지 않았다
                self._close_reviews(run_id, _storable_meta(f"not_started: {exc}")[:300])
            return


    def _close_reviews(self, run_id: str, reason: str) -> None:
        """남은(대기 중인) 검토자를 시작하지 않은 채 닫는다. 검토하지 않은 관계로 보이고 호출은 쓰지 않았다."""
        with self.store.tx() as tx:
            closed = tx.execute("UPDATE reviews SET state = 'skipped', status = ? WHERE run_id = ? AND state = ?",
                                reason, run_id, QUEUED)
            if closed:
                tx.event(run_id, "review_skipped", reviewers=closed, reason=reason)


    def acknowledge_review_unknown(self, review_id: str) -> None:
        """사람이 그 검토 호출의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않는다."""
        row = self.store.row("SELECT run_id FROM reviews WHERE review_id = ?", review_id)
        if row is None:
            raise ControllerError("교차검토를 찾을 수 없습니다.")
        self.execution._acknowledge_seat(REVIEW_SEAT, row["run_id"], {"review_id": review_id})


    def set_review_disposition(self, review_id: str, finding: int, disposition: str) -> None:
        """사람이 지적 하나의 처분을 고른다(qualified 받아들임·rejected 아님·unresolved 보류). 결과 판을 올리지 않는다 —
        사람의 판단이지 새 결과가 아니다. 모델이 동의해도 supported로 올리는 길은 없다(외부 검사 없음)."""
        if type(finding) is not int or disposition not in cross.DISPOSITIONS:
            raise ControllerError(f"처분은 {', '.join(cross.DISPOSITIONS)} 중 하나이고 지적 번호는 정수입니다.")
        with self.runtime.lock, self.store.tx() as tx:
            row = self.store.row("SELECT run_id, state, result FROM reviews WHERE review_id = ?", review_id)
            if row is None or row["state"] != ACCEPTED:
                raise ControllerError("받은 교차검토의 지적에만 처분을 고릅니다.")
            findings = json.loads(row["result"])["reply"]["findings"]
            if not 0 <= finding < len(findings):
                raise ControllerError("그런 지적이 없습니다.")
            tx.execute("INSERT INTO review_dispositions (review_id, finding, disposition, at) VALUES (?, ?, ?, ?) "
                       "ON CONFLICT (review_id, finding) DO UPDATE SET disposition = excluded.disposition, "
                       "at = excluded.at", review_id, finding, disposition, time.time())
            tx.event(row["run_id"], "review_disposition", review_id=review_id, finding=finding, disposition=disposition)


    def mark_reviewed(self, run_id: str, revision: int, memo: str | None = None) -> None:
        """사람이 공개된 원문 초안과 그때까지의 합성 결과(실패 포함) — 일반 실행이면 팀원들의 결과 — 를 판단했다. 모델
        호출 없이 내 차례를 끝내며 재시작에도 남는다. revision은 화면이 보여 준 결과 판이다 — 그 사이 새 결과가 나왔으면
        거절한다. 같은 판을 두 번 누르면 사건은 하나다(두 번째 메모는 남기지 않는다). memo는 사람이 쓴 취합 메모이며
        검증이나 합의 판정이 아니다. 합성 실패 기록을 지우거나 품질 통과로 바꾸지 않는다."""
        if type(revision) is not int:
            raise ControllerError("revision must be the integer result revision shown on screen")
        if memo is not None and (not isinstance(memo, str) or len(memo) > MAX_MEMO_CHARS or not storable(memo)):
            raise ControllerError(f"취합 메모는 {MAX_MEMO_CHARS}자까지의 올바른 글이어야 합니다.")
        with self.runtime.lock, self.store.tx() as tx:
            current_gate = self.repository._gate(run_id)
            if current_gate.general and not current_gate.collected:
                raise ControllerError("모든 팀원이 끝난 뒤에만 판단 완료로 표시할 수 있습니다. 종료 미확인은 먼저 확인하세요.")
            if not current_gate.general and not current_gate.revealed:
                raise ControllerError("공개된 답을 확인한 뒤에만 판단 완료로 표시할 수 있습니다.")
            if any(item["status"] in (RUNNING, UNKNOWN) for item in self.invocations._synthesis_attempts(run_id).values()):
                raise ControllerError("합성의 종료를 먼저 확인하세요.")
            if self.store.row("SELECT 1 FROM proposals WHERE run_id = ? AND state IN (?, ?)", run_id, RUNNING, UNKNOWN):
                raise ControllerError("다음 단계 제안이 끝나거나 그 종료를 확인한 뒤에 판단 완료를 누르세요.")
            if self.store.row("SELECT 1 FROM collations WHERE run_id = ? AND state IN (?, ?)", run_id, RUNNING, UNKNOWN):
                raise ControllerError("결과 모으기가 끝나거나 그 종료를 확인한 뒤에 판단 완료를 누르세요.")
            if self.store.row("SELECT 1 FROM reviews WHERE run_id = ? AND state IN (?, ?, ?)",
                              run_id, QUEUED, RUNNING, UNKNOWN):
                raise ControllerError("교차검토 라운드가 끝나거나 그 종료를 확인한 뒤에 판단 완료를 누르세요.")
            current, reviewed, _ = self.repository._review_state(run_id)
            for table in ('answer_revisions', 'revision_checks'):
                if self.store.row(f'SELECT 1 FROM {table} WHERE run_id = ? AND state IN (?, ?)', run_id, RUNNING, UNKNOWN):
                    raise ControllerError('수정·재검토의 종료를 확인한 뒤 판단 완료를 누르세요.')
            if revision != current:
                raise ControllerError("화면에 보인 뒤 새 결과가 나왔습니다. 새 결과를 확인하고 다시 판단 완료를 누르세요.")
            if not reviewed:
                note = (memo or "").strip()
                tx.event(run_id, "human_reviewed", revision=current, **({"memo": note} if note else {}))
