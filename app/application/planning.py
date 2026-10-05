"""Refine, next-step and work-split commands; all model calls use the execution coordinator."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
import os
import time
import uuid
from app import memory, next_step, refine as refining, split as splitting
from app.report import build_report
from app.synthesis import _sources as synthesis_sources, label_order
from app.state import CLI, RUNNING, ACCEPTED, UNKNOWN
from app.domain import ParticipantSpec, ControllerError, storable
from app.context.inputs import _checked_sources
from app.execution.seats import REFINE_SEAT, NEXT_SEAT, SPLIT_SEAT


class PlanningService:
    def __init__(self, runtime, execution, inputs, invocations, queries, repository):
        self.runtime = runtime
        self.store = runtime.store
        self.execution = execution
        self.inputs = inputs
        self.invocations = invocations
        self.queries = queries
        self.repository = repository

    def refine(self, supervisor: ParticipantSpec, original: str | None = None, *, refine_id: str | None = None,
               note: str = "", task_id=None, use_memory=True) -> str:
        """슈퍼바이저 차례 한 번 — 호출 1회. refine_id가 없으면 original로 새 다듬기를 연다. 있으면 그 다듬기의 다음 차례다.

        격리 팀원·합성과 같은 계획·격리로 부르고, 같은 원장의 전체·provider 상한에서 예약한다(환불 없음). 차례는
        다듬기 하나에 refine.MAX_TURNS까지다. 실행에 이미 쓴 다듬기, 앞 차례가 진행 중이거나 종료 미확인인 다듬기,
        진행 중·종료 미확인 실행이 있을 때는 부르지 않는다. 원문·대화와 처음 고정한 선택적 작업 기억을 받는다.
        시작 전 거절은 아무것도 예약하지 않는다. 결과는 백그라운드에서 refine_turns에 조건부로 쓴다."""
        if not isinstance(note, str) or len(note.strip()) > refining.MAX_NOTE or not storable(note):
            raise ControllerError(f"슈퍼바이저에게 쓰는 말은 {refining.MAX_NOTE}자까지의 올바른 글이어야 합니다.")
        note = note.strip()
        with self.runtime.lock:
            if self.runtime.closing:
                raise ControllerError("controller is shutting down")
            self.invocations._cli_card(supervisor, "슈퍼바이저")
            if refine_id is None:
                original = original.strip() if isinstance(original, str) else ""
                if not original or len(original) > refining.MAX_ORIGINAL or not storable(original):
                    raise ControllerError(f"다듬을 원문은 1~{refining.MAX_ORIGINAL}자의 올바른 글이어야 합니다.")
                if note:
                    raise ControllerError("첫 차례에는 원문만 보냅니다. 답은 슈퍼바이저가 물은 뒤에 적습니다.")
                previous = []
                remembered = self.inputs._select_memory(task_id, original, use_memory)
            else:
                row = self.store.row("SELECT * FROM refinements WHERE refine_id = ?", refine_id)
                if row is None:
                    raise ControllerError("다듬기를 찾을 수 없습니다.")
                if row["run_id"]:
                    raise ControllerError("이미 실행에 쓴 다듬기입니다. 새로 다듬으세요.")
                fixed = json.loads(row["supervisor"])
                if (fixed["pid"], fixed["adapter_id"], fixed["model"]) != (supervisor.pid, supervisor.adapter_id,
                                                                           supervisor.model):
                    raise ControllerError("다듬기를 시작한 슈퍼바이저·모델과 다릅니다. 바꾸려면 새로 다듬으세요.")
                turns = self.store.rows("SELECT * FROM refine_turns WHERE refine_id = ? ORDER BY turn", refine_id)
                if any(turn["state"] in (RUNNING, UNKNOWN) for turn in turns):
                    raise ControllerError("앞 차례가 끝나지 않았거나 종료를 확인하지 못했습니다. 먼저 정리하세요.")
                if len(turns) >= refining.MAX_TURNS:
                    raise ControllerError(f"다듬기는 {refining.MAX_TURNS}차례까지입니다. 한 차례를 승인하거나 원문으로 돌아가세요.")
                original = row["original"]
                previous = [(turn["note"], json.loads(turn["result"])["reply"] if turn["state"] == ACCEPTED else None)
                            for turn in turns]
                snapshot = self.store.row("SELECT payload FROM events WHERE run_id = ? AND kind = 'memory_selected'",
                                          refine_id)
                remembered = json.loads(snapshot["payload"])["memory"] if snapshot else None
            self.invocations._upper_call_gate("다듬기는")
            key = refine_id or f"q{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"
            turn = len(previous) + 1
            self.inputs.task_policy((remembered or {}).get('task_id'))
            text = refining.prompt(original, previous, note) + memory.footer(remembered)

            def insert(tx, attempt, kind):
                if refine_id is None:
                    tx.event(key, "memory_selected", memory=remembered)
                    tx.execute("INSERT INTO refinements (refine_id, created_at, original, supervisor) VALUES (?, ?, ?, ?)",
                               key, time.time(), original, json.dumps(asdict(supervisor), ensure_ascii=False))
                tx.execute("INSERT INTO refine_turns (refine_id, turn, note, prompt, input_sha256, attempt, kind, state) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", key, turn, note, text,
                           hashlib.sha256(text.encode("utf-8")).hexdigest(), attempt, kind, RUNNING)

            self.execution._start_seat(REFINE_SEAT, key, {"refine_id": key, "turn": turn}, supervisor, text,
                             os.path.join(self.runtime.work_root, "_refine", key, f"turn-{turn}"), insert)
            return key


    def acknowledge_refine_unknown(self, refine_id: str, turn: int) -> None:
        """사람이 그 차례의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않으며 답을 받지 않는다."""
        if type(turn) is not int:
            raise ControllerError("turn must be an integer")
        self.execution._acknowledge_seat(REFINE_SEAT, refine_id, {"refine_id": refine_id, "turn": turn})


    def propose_next(self, run_id: str) -> str:
        """공개된 격리 실행을 보고 슈퍼바이저가 다음 단계("한 번 더"·"여기서 끝")를 제안한다 — 호출 1회.

        슈퍼바이저는 역할판에 고정한 카드·모델이다. 받는 것은 원래 목표(다듬기 원문 또는 질문)·보낸 질문·공개된 답이고,
        답은 합성과 같은 이름표(실행마다 섞은 순서)로 바꾼다. 봉인 중·일반 실행·슈퍼바이저 없는 실행은 부르지 않는다.
        실행 하나에 next_step.MAX_PER_RUN번까지, 슈퍼바이저 호출은 한 번에 하나, 예약·상한·종료 미확인은 다듬기와 같다.
        제안은 새 실행을 시작하지 않는다."""
        with self.runtime.lock:
            if self.runtime.closing:
                raise ControllerError("controller is shutting down")
            run = self.repository._run(run_id)
            roles = json.loads(run["role_config"]) if run["role_config"] else {}
            supervisor = roles.get("supervisor")
            if not supervisor:
                raise ControllerError("슈퍼바이저 칸이 비어 있습니다(나). 다음 단계는 내가 정합니다.")
            current_gate = self.repository._gate(run_id)
            if current_gate.general or not current_gate.revealed:
                raise ControllerError("다음 단계 제안은 공개된 격리 실행에만 부릅니다. 봉인 중에는 부르지 않습니다.")
            if self.store.row("SELECT COUNT(*) AS n FROM proposals WHERE run_id = ?", run_id)["n"] >= next_step.MAX_PER_RUN:
                raise ControllerError(f"다음 단계 제안은 실행 하나에 {next_step.MAX_PER_RUN}번까지입니다.")
            if self.store.row("SELECT 1 FROM proposals WHERE run_id = ? AND state = ?", run_id, UNKNOWN):
                raise ControllerError("끝났는지 모르는 제안이 있습니다. 종료를 먼저 확인하세요.")
            self.invocations._upper_call_gate("제안은")
            spec = ParticipantSpec(**supervisor)
            self.invocations._cli_card(spec, "슈퍼바이저")
            report = build_report(self.queries.view(run_id), run_id)
            sources = synthesis_sources(report)
            labels = {f"D{index}": pid for index, pid in enumerate(label_order(run_id, sources), 1)}
            refined = self.store.row("SELECT original FROM refinements WHERE run_id = ?", run_id)
            text = next_step.prompt(refined["original"] if refined else run["question"], run["question"],
                                    [(label, sources[pid]["draft"]) for label, pid in labels.items()])
            text += self.inputs._run_memory(run)
            key = f"p{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"

            def insert(tx, attempt, kind):
                tx.execute("INSERT INTO proposals (proposal_id, run_id, created_at, supervisor, prompt, input_sha256, "
                           "labels, attempt, kind, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", key, run_id, time.time(),
                           json.dumps(supervisor, ensure_ascii=False), text,
                           hashlib.sha256(text.encode("utf-8")).hexdigest(), json.dumps(labels), attempt, kind, RUNNING)

            self.execution._start_seat(NEXT_SEAT, run_id, {"proposal_id": key}, spec, text,
                             os.path.join(self.runtime.work_root, run_id, f"proposal-{key[-12:]}"), insert)
            return key


    def acknowledge_proposal_unknown(self, proposal_id: str) -> None:
        """사람이 그 제안 호출의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않는다."""
        row = self.store.row("SELECT run_id FROM proposals WHERE proposal_id = ?", proposal_id)
        if row is None:
            raise ControllerError("제안을 찾을 수 없습니다.")
        self.execution._acknowledge_seat(NEXT_SEAT, row["run_id"], {"proposal_id": proposal_id})


    def propose_split(self, goal: str, orchestrator: ParticipantSpec, members: list[ParticipantSpec], sources=None,
                      task_id=None, use_memory=True) -> str:
        """일반 팀원 작업의 오케스트레이터 모델이 팀원마다 맡길 일과 받을 자료를 제안한다 — 호출 1회.

        오케스트레이터는 전체 목표·팀원 목록·붙인 자료 전부(읽기 전용 사본 폴더 하나)를 받는다. 제안은 실행을 시작하지
        않는다 — 화면이 팀원별 칸을 채우고, 사람이 고치거나 그대로 두고 확인해 시작하면 그때 그 실행 하나에 묶인다.
        다듬기·다음 단계 제안과 같은 관문(한 번에 하나·예약·상한·종료 미확인·재시작)을 지난다."""
        goal = goal.strip() if isinstance(goal, str) else ""
        if not goal or len(goal) > refining.MAX_ORIGINAL or not storable(goal):
            raise ControllerError(f"전체 목표는 1~{refining.MAX_ORIGINAL}자의 올바른 글이어야 합니다.")
        checked_sources = _checked_sources(sources)
        if (not members or len({p.pid for p in members}) != len(members) or any(p.transport != CLI for p in members)
                or len({p.provider for p in members}) != len(members)):
            raise ControllerError("팀원은 서로 다른 provider의 CLI 카드여야 합니다.")
        with self.runtime.lock:
            if self.runtime.closing:
                raise ControllerError("controller is shutting down")
            self.invocations._cli_card(orchestrator, "오케스트레이터")
            if task_id is not None and not self.store.row("SELECT 1 FROM tasks WHERE task_id = ?", task_id):
                raise ControllerError("작업을 찾을 수 없습니다.")
            self.inputs.task_policy(task_id)
            self.invocations._upper_call_gate("분담 제안은")
            key = f"s{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"
            labels = {f"M{index}": p.pid for index, p in enumerate(members, 1)}
            rows = [{"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "content": data}
                    for name, data in checked_sources]
            listed = [{key_: row[key_] for key_ in ("name", "bytes", "sha256")} for row in rows]
            folder = None
            if rows:
                try:
                    folder = self.inputs._snapshot(self.inputs._source_root(key), rows)
                except OSError as exc:
                    raise ControllerError(f"could not prepare the source folder: {type(exc).__name__}") from None
            text = splitting.prompt(goal, {label: next(p.label for p in members if p.pid == pid)
                                           for label, pid in labels.items()}, listed, folder)
            remembered = self.inputs._select_memory(task_id, goal, use_memory)
            text += memory.footer(remembered)

            def insert(tx, attempt, kind):
                for row in rows:
                    tx.execute("INSERT INTO sources (run_id, name, sha256, bytes, content) VALUES (?, ?, ?, ?, ?)",
                               key, row["name"], row["sha256"], row["bytes"], row["content"])
                tx.event(key, "memory_selected", memory=remembered)
                tx.execute("INSERT INTO splits (split_id, task_id, created_at, goal, orchestrator, members, sources, "
                           "prompt, input_sha256, attempt, kind, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           key, task_id, time.time(), goal, json.dumps(asdict(orchestrator), ensure_ascii=False),
                           json.dumps(labels), json.dumps(listed), text,
                           hashlib.sha256(text.encode("utf-8")).hexdigest(), attempt, kind, RUNNING)

            self.execution._start_seat(SPLIT_SEAT, key, {"split_id": key}, orchestrator, text,
                             os.path.join(self.runtime.work_root, "_split", key), insert, inputs=(folder,) if folder else ())
            return key


    def acknowledge_split_unknown(self, split_id: str) -> None:
        """사람이 그 분담 제안 호출의 자손 종료를 직접 확인했다. 자리만 풀고 재호출·환불하지 않는다."""
        self.execution._acknowledge_seat(SPLIT_SEAT, split_id, {"split_id": split_id})
