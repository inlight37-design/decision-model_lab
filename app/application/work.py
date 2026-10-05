"""Create work and fixed runs atomically, then dispatch through the execution coordinator."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
import time
from app.state import CLI, QUEUED, AWAITING_USER, INDEPENDENT_ONLY, GENERAL
from app.domain import ParticipantSpec, ControllerError
from app.context.inputs import _checked_sources


class WorkService:
    def __init__(self, runtime, execution, inputs, invocations):
        self.runtime = runtime
        self.store = runtime.store
        self.execution = execution
        self.inputs = inputs
        self.invocations = invocations

    def create_run(self, question: str, participants: list[ParticipantSpec], *, min_independent: int,
                   quorum_policy: str = INDEPENDENT_ONLY, sources=None, task_id=None, task_title=None,
                   role_board=None, roster=None, run_id=None, confirmation=None, assignments=None,
                   refinement=None, proposal=None, split=None, use_memory=True) -> str:
        checked_sources = _checked_sources(sources)   # 한 번 검사해 확인 명세와 원장 쓰기가 같은 바이트를 쓴다
        prepared = self.inputs.prepare_run(question, participants, min_independent=min_independent,
                                    quorum_policy=quorum_policy, sources=sources, task_id=task_id, task_title=task_title,
                                    role_board=role_board, roster=roster, run_id=run_id, assignments=assignments,
                                    refinement=refinement, proposal=proposal, split=split, checked=checked_sources,
                                    use_memory=use_memory)
        if confirmation is not None and confirmation != prepared["confirmation"]:
            raise ControllerError("확인한 입력에서 바뀌었습니다. 보낼 입력을 다시 확인하세요.")
        run_id, question, prompt = prepared["run_id"], prepared["question"], prepared["prompt"]
        general = prepared["mode"] == GENERAL
        input_sha256, input_bytes = prepared["input_sha256"], prepared["input_bytes"]
        min_independent, quorum_policy = prepared["min_independent"], prepared["quorum_policy"]
        participants = [ParticipantSpec(**p) for p in prepared["role_config"]["general" if general else "isolated"]]
        with self.runtime.lock, self.store.tx() as tx:
            if self.runtime.closing:
                raise ControllerError("controller is shutting down")
            if self.inputs.task_policy(task_id) != prepared['role_config'].get('task_plan'):
                raise ControllerError('작업 계획이나 선행 결과가 바뀌었습니다. 보낼 입력을 다시 확인하세요.')
            if self.store.row("SELECT 1 FROM runs WHERE run_id = ?", run_id):
                raise ControllerError("이미 시작한 실행입니다. 같은 확인으로 다시 부르지 않습니다.")
            if role_board is not None and (self.store.row(
                    "SELECT 1 FROM runs WHERE phase = 'drafting' AND NOT cancel_requested")
                    or self.invocations._slots_used() or self.invocations.unsettled()):
                raise ControllerError("진행 중이거나 종료 미확인인 실행을 먼저 정리하세요. A 단계는 동시 작업을 시작하지 않습니다.")
            if task_id is None:
                task_id = "t-" + run_id
                tx.execute("INSERT INTO tasks VALUES (?, ?, ?)", task_id, prepared["task_title"], time.time())
            for name, content in checked_sources:
                tx.execute("INSERT INTO sources (run_id, name, sha256, bytes, content) VALUES (?, ?, ?, ?, ?)",
                           run_id, name, hashlib.sha256(content).hexdigest(), len(content), content)
            tx.execute("INSERT INTO runs (run_id, created_at, question, prompt, input_sha256, input_bytes, "
                       "min_independent, roster, quorum_policy, task_id, role_config, mode) "
                       "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       run_id, time.time(), question, prompt, input_sha256, input_bytes,
                       min_independent, "{}", quorum_policy, task_id, json.dumps(prepared["role_config"], ensure_ascii=False),
                       prepared["mode"])
            if prepared.get("refinement"):
                # 다듬기는 실행 하나에만 묶인다. 같은 승인으로 두 번 부르면 여기서 거래 전체가 되돌려진다.
                chosen = prepared["refinement"]
                if not tx.execute("UPDATE refinements SET run_id = ?, approved_turn = ? WHERE refine_id = ? "
                                  "AND run_id IS NULL", run_id, chosen["turn"], chosen["refine_id"]):
                    raise ControllerError("이미 다른 실행에 쓴 다듬기입니다. 같은 승인으로 실행을 두 번 만들지 않습니다.")
                tx.event(chosen["refine_id"], "refine_approved", used_by=run_id, turn=chosen["turn"])
            if prepared.get("proposal"):
                # 제안은 실행 하나에만 묶인다. 같은 제안으로 두 번 부르면 거래 전체가 되돌려진다.
                chosen = prepared["proposal"]
                if not tx.execute("UPDATE proposals SET used_by = ? WHERE proposal_id = ? AND used_by IS NULL",
                                  run_id, chosen["proposal_id"]):
                    raise ControllerError("이미 실행에 쓴 제안입니다. 같은 제안으로 실행을 두 번 만들지 않습니다.")
                tx.event(chosen["source_run"], "proposal_used", proposal_id=chosen["proposal_id"], used_by=run_id)
            if prepared.get("split"):
                # 분담 제안도 실행 하나에만 묶인다. 제안대로였는지(as_proposed)를 함께 남긴다.
                chosen = prepared["split"]
                if not tx.execute("UPDATE splits SET used_by = ?, as_proposed = ? WHERE split_id = ? AND used_by IS NULL",
                                  run_id, int(chosen["as_proposed"]), chosen["split_id"]):
                    raise ControllerError("이미 실행에 쓴 분담 제안입니다. 같은 제안으로 실행을 두 번 만들지 않습니다.")
                tx.event(chosen["split_id"], "split_used", used_by=run_id, as_proposed=chosen["as_proposed"])
            for pid, item in (prepared.get("assignments") or {}).items():
                tx.execute("INSERT INTO assignments VALUES (?, ?, ?, ?, ?, ?, ?)", run_id, pid, item["task"],
                           item["prompt"], item["input_sha256"], item["input_bytes"],
                           json.dumps(item["sources"], ensure_ascii=False))
            for p in participants:
                tx.execute("INSERT INTO participants (run_id, pid, spec, state) VALUES (?, ?, ?, ?)", run_id, p.pid,
                           json.dumps(asdict(p), ensure_ascii=False), QUEUED if p.transport == CLI else AWAITING_USER)
            tx.event(run_id, "run_created", input_sha256=input_sha256, input_bytes=input_bytes,
                     participants=[p.pid for p in participants], min_independent=min_independent,
                     quorum_policy=quorum_policy, mode=prepared["mode"],
                     **({"refinement": {"refine_id": prepared["refinement"]["refine_id"],
                                        "turn": prepared["refinement"]["turn"],
                                        "original_sha256": hashlib.sha256(
                                            prepared["refinement"]["original"].encode("utf-8")).hexdigest()}}
                        if prepared.get("refinement") else {}),
                     sources=[{"name": name, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
                              for name, content in checked_sources],
                     **({"assignments": {pid: {"input_sha256": item["input_sha256"],
                                               "sources": [s["name"] for s in item["sources"]]}
                                         for pid, item in prepared["assignments"].items()}} if general else {}))
            tx.event(run_id, "drafting_started")
        self.execution.pump()
        return run_id
