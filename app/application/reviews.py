"""Collation, bounded cross-review and human dispositions over immutable source answers."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
import os
import re
import time
import uuid
from app import collate as collating, cross_review as cross, revisions as revising
from app.synthesis import label_order
from app.state import CLI, QUEUED, RUNNING, ACCEPTED, UNKNOWN
from core import contract
from app.domain import ParticipantSpec, ControllerError, _CapReached, storable, _storable_meta, MAX_MEMO_CHARS
from app.execution.seats import COLLATE_SEAT, REVIEW_SEAT


def _digest(text) -> str | None:
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if isinstance(text, str) else None


def _intact(row) -> bool:
    """검토 행에 고정한 입력 전문과 대상 답 본문(일반 검토면 확인한 snapshot까지)이 기록한 hash와 아직 맞는가."""
    targets = json.loads(row["targets"])
    if _digest(row["prompt"]) != row["input_sha256"] or any(
            _digest(item.get("text")) != item.get("sha256") for item in targets.values()):
        return False
    if row["snapshot"] is None:
        return row["snapshot_sha256"] is None
    snapshot = json.loads(row["snapshot"])
    return (_digest(row["snapshot"]) == row["snapshot_sha256"] and snapshot["input_sha256"] == row["input_sha256"]
            and {label: item["answer_sha256"] for label, item in snapshot["targets"].items()}
            == {label: item["sha256"] for label, item in targets.items()})


class ReviewService:
    def __init__(self, runtime, execution, inputs, invocations, repository):
        self.runtime = runtime
        self.store = runtime.store
        self.execution = execution
        self.inputs = inputs
        self.invocations = invocations
        self.repository = repository

    def preview_collation(self, run_id: str, choices=None) -> dict:
        """고른 판 취합(GR-3)의 입력 확인. 모델을 부르지 않고 원장·예산을 예약하지 않는다. 새 collation_id로 팀원별
        판(원래 결과 또는 수정 판)/hash·미해결 지적·누락과 오케스트레이터에 보낼 입력 전문을 만들고, 그 전부를 묶은 확인
        값(confirmation)을 준다. 시작은 같은 choices·collation_id·확인 값으로 한다."""
        with self.runtime.lock:
            return self._collation(run_id, choices, self._collation_key())[0]


    @staticmethod
    def _collation_key() -> str:
        return f"c{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"


    def collate(self, run_id: str, choices=None, *, collation_id=None, confirmation=None) -> str:
        """모두 끝난 일반 실행의 팀원 결과를 역할판의 오케스트레이터 모델이 원문 인용으로 취합한다 — 호출 1회.

        오케스트레이터는 전체 목표와 팀원마다 맡긴 일·고른 판의 결과 원문(이름표 T1·T2, 결과가 없으면 "결과 없음")과 그
        판에 남은 지적을 받는다. 자료 원문은 주지 않는다. 인용은 이 호출이 받은 그 판의 원문과 글자 그대로 대조하고, 사실
        검증은 하지 않는다. 실행 하나에 collate.MAX_PER_RUN번까지, 다른 상위 모델 호출과 같은 관문(한 번에 하나·예약·
        상한·종료 미확인·재시작)을 지난다. 판단 완료는 사람이 한다.

        확인 값이 있으면 preview_collation이 준 collation_id·choices로 입력을 다시 만들어 같을 때만 시작한다(GR-3). 확인
        값이 없으면 모든 팀원의 원래 결과를 모으는 예전 호출이다 — 받아들인 수정 판이 있는 실행에서는 판을 몰래 고르지
        않도록 거절한다."""
        with self.runtime.lock:
            if confirmation is None:
                if choices is not None or collation_id is not None:
                    raise ControllerError("판을 고른 결과 모으기는 입력 확인 값과 함께 시작합니다.")
                if self.store.row("SELECT 1 FROM answer_revisions WHERE run_id = ? AND state = ?", run_id, ACCEPTED):
                    raise ControllerError("수정 판이 있는 실행은 입력 확인에서 팀원마다 쓸 판을 고른 뒤 모읍니다.")
                manifest, prepared = self._collation(run_id, None, self._collation_key())
            else:
                manifest, prepared = self._collation(run_id, choices, collation_id)
                if not isinstance(confirmation, str) or manifest["confirmation"] != confirmation:
                    raise ControllerError("확인한 뒤 모을 입력이 바뀌었습니다. 호출하지 않았습니다. 입력 확인을 다시 받으세요.")
                if self.store.row("SELECT 1 FROM collations WHERE collation_id = ?", manifest["collation_id"]):
                    raise ControllerError("이미 시작한 결과 모으기입니다. 같은 확인으로 다시 부르지 않습니다.")
            self.invocations._upper_call_gate("결과 모으기는")
            key, text, orchestrator = manifest["collation_id"], manifest["prompt"], prepared["orchestrator"]
            selection = json.dumps({k: v for k, v in manifest.items() if k != "prompt"}, sort_keys=True, ensure_ascii=False)

            def insert(tx, attempt, kind):
                tx.execute("INSERT INTO collations (collation_id, run_id, created_at, orchestrator, labels, drafts, prompt, "
                           "input_sha256, attempt, kind, state, selection, selection_sha256) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", key, run_id,
                           time.time(), json.dumps(orchestrator, ensure_ascii=False), json.dumps(prepared["labels"]),
                           json.dumps(prepared["drafts"], ensure_ascii=False), text, manifest["input_sha256"],
                           attempt, kind, RUNNING, selection, _digest(selection))

            self.execution._start_seat(COLLATE_SEAT, run_id, {"collation_id": key}, ParticipantSpec(**orchestrator), text,
                             os.path.join(self.runtime.work_root, run_id, f"collation-{key[-12:]}"), insert)
            return key


    def _collation(self, run_id: str, choices, key) -> tuple[dict, dict]:
        """lock 안에서 부른다. 지금 원장으로 결과 모으기 입력을 다시 만든다 — (화면에 보일 확인 명세, 저장할 이름표·원문).
        같은 key·choices·원장이면 같은 결과다. choices는 {팀원 pid: "original" 또는 그 팀원의 받아들인 수정 판 ID}이고 빠진
        팀원은 원래 결과다. 원래 답(CR-01)·수정 판·재검토의 hash와 맡긴 일의 고정 입력을 확인하고, 다르면 거절한다."""
        if self.runtime.closing:
            raise ControllerError("controller is shutting down")
        if not isinstance(key, str) or not re.fullmatch(r"c\d{4}-\d{6}-[0-9a-f]{32}", key):
            raise ControllerError("결과 모으기 ID가 올바르지 않습니다. 입력 확인을 다시 받으세요.")
        choices = {} if choices is None else choices
        if not isinstance(choices, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in choices.items()):
            raise ControllerError('쓸 판은 {팀원: "original" 또는 수정 판 ID}로 고릅니다.')
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
        spec = ParticipantSpec(**orchestrator)
        self.invocations._cli_card(spec, "오케스트레이터")
        answers = self.repository._answers(run_id)   # 본문 hash 확인(CR-01)
        if set(choices) - {item["pid"] for item in answers if item["state"] == ACCEPTED}:
            raise ControllerError("결과를 낸 팀원의 판만 고릅니다.")
        members, entries, missing, labels, drafts = [], [], [], {}, {}
        for index, answer in enumerate(answers, 1):
            label, member = f"T{index}", ParticipantSpec(**answer["spec"])
            work = self.inputs._checked_assignment(run_id, member.pid)
            labels[label] = member.pid
            entry = {"label": label, "pid": member.pid, "name": member.label, "task": work["task"],
                     "assignment_sha256": work["input_sha256"]}
            if answer["state"] != ACCEPTED:
                drafts[label] = None
                entries.append({**entry, "version": None, "sha256": None, "bytes": None, "rechecked": None, "open": []})
                missing.append({"pid": member.pid, "task": work["task"], "reason": "결과 없음"})
                members.append({"label": label, "name": member.label, "task": work["task"], "text": None})
                continue
            pick = choices.get(member.pid, collating.ORIGINAL)
            if pick == collating.ORIGINAL:
                text, sha, rechecked = answer["text"], answer["sha256"], None
                found = self._review_open(run_id, member.pid, sha)
                version = "원래 결과"
            else:
                text, sha, rechecked, found = self._revision_open(run_id, member.pid, pick, answer["sha256"])
                version = f"수정 판 {pick} · " + ("다른 팀원이 재검토함" if rechecked else "재검토 없음")
            drafts[label] = text
            entries.append({**entry, "version": pick, "sha256": sha, "bytes": len(text.encode("utf-8")),
                            "rechecked": rechecked, "open": found})
            members.append({"label": label, "name": member.label, "task": work["task"], "text": text, "version": version,
                            "open": [f"[{item['from']} · {item['status']}] {item['detail']}" for item in found]})
        footer = self.inputs._run_memory(run)
        text = collating.prompt(run["question"], members, hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]) + footer
        data = text.encode("utf-8")
        manifest = {"contract": collating.SELECTION_CONTRACT, "mode": "general", "run_id": run_id, "collation_id": key,
                    "result_revision": self.repository._review_state(run_id)[0], "goal": run["question"],
                    "orchestrator": {"adapter_id": spec.adapter_id, "label": spec.label, "model": spec.model},
                    "members": entries, "missing": missing, "memory": _digest(footer) if footer else None,
                    "prompt": text, "input_sha256": hashlib.sha256(data).hexdigest(), "input_bytes": len(data),
                    "calls": 1, "factual_check": "not_performed", "source_bodies": "not_sent"}
        manifest["confirmation"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False)
                                                  .encode("utf-8")).hexdigest()
        return manifest, {"orchestrator": orchestrator, "labels": labels, "drafts": drafts}


    def _review_open(self, run_id: str, pid: str, sha: str) -> list[dict]:
        """원래 결과에 남은 교차검토 지적. 사람이 아니라고(rejected) 한 지적은 뺀다. 처분이 없으면 보류(unresolved)다."""
        found = []
        for review in self.store.rows("SELECT * FROM reviews WHERE run_id = ? AND state = ? ORDER BY seq", run_id, ACCEPTED):
            targets = json.loads(review["targets"])
            chosen = {r["finding"]: r["disposition"] for r in self.store.rows(
                "SELECT finding, disposition FROM review_dispositions WHERE review_id = ?", review["review_id"])}
            for index, finding in enumerate(json.loads(review["result"])["reply"]["findings"]):
                target = targets[finding["target"]]
                status = chosen.get(index, "unresolved")
                if target["pid"] == pid and target["sha256"] == sha and status != "rejected":
                    found.append({"from": "review", "id": f"{review['review_id']}:{index}", "status": status,
                                  "detail": finding["detail"]})
        return found


    def _revision_open(self, run_id: str, pid: str, revision_id: str, original_sha: str):
        """고른 수정 판의 (본문, sha256, 재검토 여부, 남은 지적). 판·근거·재검토의 hash가 기록과 다르면 거절한다."""
        row = self.store.row("SELECT * FROM answer_revisions WHERE revision_id = ? AND run_id = ?", revision_id, run_id)
        reply = (json.loads(row["result"] or "{}").get("reply") if row is not None else None) or {}
        snapshot = json.loads(row["snapshot"]) if row is not None else {}
        if (row is None or row["pid"] != pid or row["state"] != ACCEPTED or not isinstance(reply.get("answer"), str)
                or _digest(reply["answer"]) != reply.get("sha256") or revising.digest(revising.encoded(snapshot)) != row["snapshot_sha256"]
                or snapshot.get("mode") != "general" or snapshot["original"]["sha256"] != original_sha):
            raise ControllerError("그 팀원의 받아들인 수정 판이 아니거나 기록된 hash와 맞지 않습니다.")
        found = [{"from": "revision", "id": item["finding"], "status": item["status"], "detail": item["detail"]}
                 for item in reply["responses"] if item["status"] != "addressed"]
        rechecked = False
        for check in self.store.rows("SELECT * FROM revision_checks WHERE revision_id = ? AND state = ? "
                                     "ORDER BY created_at, check_id", revision_id, ACCEPTED):
            if check["answer_sha256"] != reply["sha256"] or _digest(check["answer"]) != reply["sha256"]:
                raise ControllerError("재검토가 다른 판을 가리킵니다.")
            checked = json.loads(check["result"])["reply"]
            rechecked = True
            found += [{"from": "recheck", "id": item["finding"], "status": item["status"], "detail": item["detail"]}
                      for item in checked["assessments"] if item["status"] != "addressed"]
            found += [{"from": "recheck", "id": f"{check['check_id']}:{index}", "status": item["kind"],
                       "detail": item["detail"]} for index, item in enumerate(checked["findings"])]
        return reply["answer"], reply["sha256"], rechecked, found


    def acknowledge_collation_unknown(self, collation_id: str) -> None:
        """사람이 그 결과 모으기 호출의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않는다."""
        row = self.store.row("SELECT run_id FROM collations WHERE collation_id = ?", collation_id)
        if row is None:
            raise ControllerError("결과 모으기를 찾을 수 없습니다.")
        self.execution._acknowledge_seat(COLLATE_SEAT, row["run_id"], {"collation_id": collation_id})


    def preview_cross_review(self, run_id: str, question: str | None = None) -> dict:
        """일반 실행의 교차검토 입력 확인(GR-1). 모델을 부르지 않고 원장·예산을 예약하지 않는다. 새 round_id로 검토자마다
        보낼 입력 전문을 만들고, 그 전부를 묶은 확인 값(confirmation)을 준다. 시작은 같은 round_id·확인 값으로 한다."""
        question = self._question(question)
        with self.runtime.lock:
            manifest, _ = self._general_round(run_id, question, "g" + uuid.uuid4().hex)
            return manifest


    def _question(self, question):
        question = question.strip() if isinstance(question, str) else ""
        question = question or cross.DEFAULT_QUESTION
        if len(question) > cross.MAX_QUESTION or not storable(question):
            raise ControllerError(f"검토 질문은 {cross.MAX_QUESTION}자까지의 올바른 글이어야 합니다.")
        return question


    def _general_round(self, run_id: str, question: str, round_id: str) -> tuple[dict, list[dict]]:
        """lock 안에서 부른다. 지금 원장으로 일반 검토 라운드를 다시 만든다 — (화면에 보일 확인 명세, 검토자별 행).
        같은 round_id와 같은 원장이면 같은 결과다. 답 본문 hash(CR-01)와 맡긴 일의 고정 입력을 확인하고, 다르면
        거절한다. 수집 전·취소·받은 답 둘 미만·CLI 검토자 없음도 거절한다. 실패한 팀원을 채우지 않는다."""
        if self.runtime.closing:
            raise ControllerError("controller is shutting down")
        if not isinstance(round_id, str) or len(round_id) != 33 or round_id[0] != "g" or any(
                ch not in "0123456789abcdef" for ch in round_id[1:]):
            raise ControllerError("검토 라운드 ID가 올바르지 않습니다. 입력 확인을 다시 받으세요.")
        run = self.repository._run(run_id)
        current_gate = self.repository._gate(run_id)
        if not current_gate.general or not current_gate.collected or run["cancel_requested"]:
            raise ControllerError("일반 팀원 교차검토는 모두 끝난(모음으로 닫힌) 일반 실행에만 부릅니다.")
        if self.store.row("SELECT 1 FROM reviews WHERE run_id = ?", run_id):
            raise ControllerError("교차검토는 실행 하나에 한 라운드입니다.")
        members, answers = {}, {}
        for item in self.repository._answers(run_id):   # 본문 hash 확인(CR-01)
            spec = ParticipantSpec(**item["spec"])
            work = self.inputs._checked_assignment(run_id, spec.pid)   # 맡긴 일·입력·묶음 해시 확인
            listed = [{key: source[key] for key in ("name", "sha256", "bytes")} for source in json.loads(work["sources"])]
            members[spec.pid] = {"pid": spec.pid, "label": spec.label, "state": item["state"], "task": work["task"],
                                 "assignment_sha256": work["input_sha256"], "sources": listed,
                                 "answer_sha256": item["sha256"],
                                 "answer_bytes": len(item["text"].encode("utf-8")) if item["text"] is not None else None}
            if item["state"] == ACCEPTED:
                answers[spec.pid] = (spec, item["text"])
        reviewers = [pid for pid, (spec, _) in answers.items()
                     if spec.transport == CLI and spec.adapter_id in self.runtime.executor.adapter_ids]
        if len(answers) < 2 or not reviewers:
            raise ControllerError("교차검토에는 받은 결과가 둘 이상이고, 그중 설정된 CLI 팀원이 하나 이상 있어야 합니다.")
        missing = [{"pid": pid, "task": m["task"], "reason": "결과 없음"} for pid, m in members.items()
                   if pid not in answers]
        rows, previews = [], []
        for pid in reviewers:
            spec, own = answers[pid]
            others = [other for other in answers if other != pid]
            labels = {f"D{index}": other for index, other in
                      enumerate(label_order(f"{run_id}\0review\0{pid}", others), 1)}
            nonce = hashlib.sha256(f"{round_id}\0{pid}".encode("utf-8")).hexdigest()[:12]
            text = cross.general_prompt(
                question, run["question"], {"task": members[pid]["task"], "text": own, "sources": members[pid]["sources"]},
                [(label, {"task": members[other]["task"], "text": answers[other][1], "sources": members[other]["sources"]})
                 for label, other in labels.items()],
                [{"task": m["task"], "reason": m["reason"]} for m in missing], nonce)
            data = text.encode("utf-8")
            rows.append({"pid": pid, "spec": spec, "labels": labels, "prompt": text,
                         "input_sha256": hashlib.sha256(data).hexdigest(),
                         "targets": {label: {"pid": other, "sha256": members[other]["answer_sha256"],
                                             "text": answers[other][1]} for label, other in labels.items()}})
            previews.append({"pid": pid, "label": spec.label, "labels": labels, "prompt": text,
                             "input_sha256": rows[-1]["input_sha256"], "input_bytes": len(data)})
        revision = self.repository._review_state(run_id)[0]
        manifest = {"contract": cross.GENERAL_CONTRACT, "mode": "general", "run_id": run_id, "round_id": round_id,
                    "result_revision": revision, "goal": run["question"], "question": question,
                    "input_sha256": run["input_sha256"], "members": list(members.values()), "missing": missing,
                    "reviewers": previews, "calls": len(reviewers),
                    "input_bytes": sum(item["input_bytes"] for item in previews),
                    "independence": cross.GENERAL_INDEPENDENCE, "factual_check": "not_performed",
                    "source_bodies": "not_sent", "memory_pack": "not_added"}
        manifest["confirmation"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False)
                                                  .encode("utf-8")).hexdigest()
        for row in rows:
            snapshot = {"contract": cross.GENERAL_CONTRACT, "mode": "general", "round_id": round_id,
                        "confirmation": manifest["confirmation"], "result_revision": revision,
                        "goal": run["question"], "question": question, "reviewer": row["pid"], "labels": row["labels"],
                        "own": {key: members[row["pid"]][key] for key in ("pid", "task", "answer_sha256", "sources")},
                        "targets": {label: {key: members[other][key] for key in ("pid", "task", "answer_sha256", "sources")}
                                    for label, other in row["labels"].items()},
                        "missing": missing, "input_sha256": row["input_sha256"]}
            row["snapshot"] = json.dumps(snapshot, sort_keys=True, ensure_ascii=False)
        return manifest, rows


    def _create_general_round(self, run_id: str, question: str, round_id, confirmation) -> list[str]:
        """확인한 일반 검토 라운드를 저장하고 첫 검토자를 시작한다. 확인 뒤 답·맡긴 일·결과 판·질문이 바뀌었으면 원장을
        쓰지 않고 거절한다. 한 라운드 제한은 같은 lock·거래 안에서 다시 본다 — 새 round_id로 우회하지 못한다."""
        if not isinstance(confirmation, str) or not confirmation:
            raise ControllerError("일반 팀원 교차검토는 입력 확인(round_id·confirmation)을 받은 뒤에 시작합니다.")
        with self.runtime.lock:
            manifest, rows = self._general_round(run_id, question, round_id)
            if manifest["confirmation"] != confirmation:
                raise ControllerError("확인한 뒤 검토 입력이 바뀌었습니다. 호출하지 않았습니다. 입력 확인을 다시 받으세요.")
            self.invocations._upper_call_gate("교차검토는")
            first = rows[0]["spec"]
            if (self.runtime.executor.kind == contract.REAL and self.runtime.max_real_calls is not None
                    and self.invocations._budget_exhausted(first.adapter_id)):
                raise ControllerError("real CLI call budget exhausted; no call was started")
            keys, now = [], time.time()
            with self.store.tx() as tx:
                if self.store.row("SELECT 1 FROM reviews WHERE run_id = ?", run_id):
                    raise ControllerError("교차검토는 실행 하나에 한 라운드입니다.")
                for seq, row in enumerate(rows, 1):
                    key = f"v{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"
                    tx.execute("INSERT INTO reviews (review_id, run_id, seq, created_at, question, reviewer, labels, "
                               "targets, prompt, input_sha256, state, snapshot, snapshot_sha256) "
                               "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               key, run_id, seq, now, question, json.dumps(asdict(row["spec"]), ensure_ascii=False),
                               json.dumps(row["labels"]), json.dumps(row["targets"], ensure_ascii=False), row["prompt"],
                               row["input_sha256"], QUEUED, row["snapshot"],
                               hashlib.sha256(row["snapshot"].encode("utf-8")).hexdigest())
                    keys.append(key)
                tx.event(run_id, "review_round_created", reviewers=[row["pid"] for row in rows], calls=len(rows),
                         default_question=question == cross.DEFAULT_QUESTION, mode="general",
                         round_id=round_id, confirmation=confirmation)
            self._advance_reviews(start=True)
            return keys


    def cross_review(self, run_id: str, question: str | None = None, *, round_id=None, confirmation=None) -> list[str]:
        """공개된 격리 실행에서 교차검토 한 라운드를 연다 — 받은 답을 낸 CLI 팀원 한 명 = 호출 1회.

        검토자는 답을 낸 그 카드·모델이다(같은 관측된 계획, 읽기 전용). 자기 답(따로 표시)과 다른 팀원의 답(이름표,
        검토자마다 섞은 순서)과 검토 질문을 받는다. 원본 앱 팀원의 답은 대상으로만 들어간다. 입력은 여기서 모두 고정하고,
        검토자는 다른 상위 모델 호출처럼 한 번에 하나씩 차례로 부른다(pump). 앞 검토자가 받지 못하면(실패·종료
        미확인·상한·시작 못 함) 남은 검토자는 시작하지 않는다. 실행 하나에 한 라운드. 공개 뒤 다른 답을 본 검토라
        독립 정족수에 세지 않는다. 검토는 새 실행을 시작하지 않고, 지적의 처분은 사람이 한다."""
        question = self._question(question)
        with self.runtime.lock:
            if self.runtime.closing:
                raise ControllerError("controller is shutting down")
            run = self.repository._run(run_id)
            current_gate = self.repository._gate(run_id)
            if current_gate.general:   # 일반 실행은 입력 확인을 거친다(GR-1)
                return self._create_general_round(run_id, question, round_id, confirmation)
            if not current_gate.revealed:
                raise ControllerError("교차검토는 공개된 격리 실행에만 부릅니다. 봉인 중에는 부르지 않습니다.")
            if self.store.row("SELECT 1 FROM reviews WHERE run_id = ?", run_id):
                raise ControllerError("교차검토는 실행 하나에 한 라운드입니다.")
            self.invocations._upper_call_gate("교차검토는")
            # pid → (명세, 답 원문, sha256). 받은 답만, 참여자 순서대로. 자기 답을 포함해 본문 hash를 확인한다(CR-01)
            answers = {item["pid"]: (ParticipantSpec(**item["spec"]), item["text"], item["sha256"])
                       for item in self.repository._answers(run_id) if item["state"] == ACCEPTED}
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
            if not _intact(row):   # 라운드에 고정한 입력이 저장 뒤 바뀌었다(CR-01): 이 검토자부터 시작하지 않는다
                self._close_reviews(run_id, "not_started: fixed review input does not match its digest")
                return

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
