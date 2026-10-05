"""Validate, freeze and materialize inputs. No process launch or HTTP dependency."""
from __future__ import annotations
from dataclasses import asdict, replace
import hashlib
import json
import os
import re
import time
import uuid
from typing import Any
from app import memory
from app import source_document
from app.roles import freeze as freeze_roles
from app.state import CLI, MANUAL, RUNNING, ACCEPTED, UNKNOWN, INDEPENDENT_ONLY, QUORUM_POLICIES, ISOLATED, GENERAL, NO_QUORUM, confirmed
from core import contract, membership as m
from app.domain import ParticipantSpec, ControllerError, storable, packet

PROMPT = ("다음 질문에, 다른 참여자의 답을 보지 않은 상태로 독립적으로 답하라. "
          "결론, 근거, 그리고 결론을 뒤집을 조건을 쓴다.\n\n질문:\n{question}\n")


PROMPT_SOURCES = ("\n참고 자료 {count}개가 읽기 전용 폴더 {folder}에 있다. 자료에서 가져온 내용은 파일 이름을 밝히고, "
                  "자료에 없는 판단은 자료 밖의 판단이라고 표시한다.\n{listing}\n")


GENERAL_PROMPT = ("사람이 일을 나눠 너에게 한 부분을 맡겼다. 전체 목표는 참고만 하고 맡은 일만 한다. 파일을 고치지 않고 "
                  "읽기만 한다. 결과, 근거, 확인하지 못한 점을 쓴다.\n\n전체 목표:\n{question}\n\n맡은 일:\n{task}\n")


MAX_TASK_CHARS = 4000


SOURCE_KIND_ORIGINAL, SOURCE_RANGE_WHOLE = "original", "whole"


SOURCE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")


WINDOWS_DEVICES = re.compile(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?")


MAX_SOURCES, MAX_SOURCE_BYTES, MAX_SOURCES_TOTAL = 20, 256 * 1024, 1024 * 1024


def _checked_sources(items) -> list[tuple[str, bytes]]:
    """(이름, 글) 목록을 검사한다. 경로 구분자·숨김 이름·장치 이름·중복(대소문자 무시)·크기 초과·NUL을 거절한다."""
    if items is None:
        return []
    if not isinstance(items, (list, tuple)) or len(items) > MAX_SOURCES:
        raise ControllerError(f"sources must be a list of at most {MAX_SOURCES} files")
    checked, seen, total = [], set(), 0
    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ControllerError("each source needs a name and a text")
        name, text = item
        if (not isinstance(name, str) or SOURCE_NAME.fullmatch(name) is None or WINDOWS_DEVICES.fullmatch(name)
                or name.endswith(".") or name.lower() in seen):
            raise ControllerError("source names use letters, digits, dot, dash or underscore and must be unique")
        if not isinstance(text, str) or "\x00" in text or not storable(text):
            raise ControllerError(f"source {name!r} must be valid Unicode text")
        data = text.encode("utf-8")
        total += len(data)
        if len(data) > MAX_SOURCE_BYTES or total > MAX_SOURCES_TOTAL:
            raise ControllerError(f"sources are limited to {MAX_SOURCE_BYTES} bytes each and {MAX_SOURCES_TOTAL} in total")
        source_document.metadata(data)
        seen.add(name.lower())
        checked.append((name, data))
    return sorted(checked)


def _bundle_digest(members: dict[str, dict[str, Any]]) -> str:
    """일반 실행 전체의 입력 해시: 팀원별 입력 전문의 sha256을 팀원 ID 순으로 묶은 것. 한 팀원의 입력이 바뀌어도 바뀐다."""
    return hashlib.sha256(json.dumps({pid: item["input_sha256"] for pid, item in members.items()},
                                     sort_keys=True).encode("utf-8")).hexdigest()


def _source_footer(folder: str, sources) -> str:
    """생성과 재개가 같은 자료 목록 형식을 쓴다. 경로도 고정 질문의 일부이므로 조용히 바꾸지 않는다."""
    return PROMPT_SOURCES.format(
        count=len(sources), folder=folder,
        listing="\n".join(f"- {item['name']} ({item['bytes']} bytes, sha256 {item['sha256']})" for item in sources))


class InputBuilder:
    def __init__(self, runtime, repository):
        self.runtime = runtime
        self.store = runtime.store
        self.repository = repository

    def prepare_run(self, question: str, participants: list[ParticipantSpec], *, min_independent: int,
                    quorum_policy: str = INDEPENDENT_ONLY, sources=None, task_id=None, task_title=None,
                    role_board=None, roster=None, run_id=None, assignments=None, refinement=None,
                    proposal=None, split=None, checked=None, use_memory=True) -> dict[str, Any]:
        """sources: (이름, 글) 목록. 원장에 내용·해시를 고정하고, CLI 참여자에게는 그 사본 폴더 하나를 읽기
        전용 입력으로 준다(provider별 빈 입력 폴더 대신). 입력 폴더가 하나인 것은 같으므로 계획의 판은 그대로다.
        checked: create_run이 이미 검사한 (이름, 바이트) 목록 — 있으면 sources를 다시 검사하지 않는다.

        역할판의 일반 칸을 채운 실행(카드 #125)은 assignments로 팀원마다 {task, sources: [자료 이름]}을 받는다.
        정족수 인자는 쓰지 않는다. 팀원마다 입력 전문이 다르고, 받은 자료만 든 폴더를 따로 받는다.

        다듬기 모드(카드 #130)는 refinement={id, turn}으로 승인할 차례를 받는다. question은 그 차례의 다듬은 문장과 같아야
        하고, 격리 팀원에게는 그 문장만 간다 — 원문과 다듬기 대화는 확인 명세에만 싣고 참여자 입력에 넣지 않는다.

        다음 단계 제안(카드 #133)에서 온 실행은 proposal={id}를 받는다. 같은 작업·원문 모드·제안한 질문 그대로여야 하고,
        제안은 그 실행 하나에만 묶인다."""
        question = question.strip()
        if not question:
            raise ControllerError("question is empty")
        if not storable(question):
            raise ControllerError("the question contains text that is not valid Unicode")
        checked_sources = _checked_sources(sources) if checked is None else checked
        if len({p.pid for p in participants}) != len(participants) or not participants:
            raise ControllerError("participants must be unique and non-empty")
        for p in participants:
            if p.transport not in (CLI, MANUAL) or (p.transport == CLI and p.adapter_id not in self.runtime.executor.adapter_ids):
                raise ControllerError(f"unsupported participant {p.pid!r}")
        try:
            roles = freeze_roles(role_board, participants, roster or {p.pid: p for p in participants})
        except ValueError as exc:
            raise ControllerError(str(exc)) from None
        general = bool(roles["general"])
        if not general and assignments is not None:
            raise ControllerError("맡길 일은 일반 칸의 팀원에게만 줍니다.")
        if roles["input_mode"] == "refine":
            approved = self._approved_refinement(refinement, roles, question, task_id, use_memory)
        elif refinement is not None:
            raise ControllerError("다듬기 차례는 다듬기 모드에서만 줍니다.")
        else:
            approved = None
        if not general and quorum_policy not in QUORUM_POLICIES:
            raise ControllerError(f"quorum_policy must be one of {', '.join(QUORUM_POLICIES)}")
        # 프런트엔드가 false를 보내도 실행기의 opt-in 등급을 올려 주지 않는다. 더 낮은 등급은 보존한다.
        if getattr(self.runtime.executor, "allow_context_unverified", False):
            participants = [replace(p, context_unverified=True) if p.transport == CLI else p for p in participants]
            roles["general" if general else "isolated"] = [asdict(p) for p in participants]
        if not general:
            confirmable = sum(confirmed(asdict(p)) for p in participants)
            if quorum_policy == INDEPENDENT_ONLY and min_independent > confirmable:
                raise ControllerError(f"only {confirmable} participant(s) can be confirmed independent (CLI); lower "
                                      "min_independent or choose include_unverified to count unverified answers")
            try:
                m.start(tuple(p.pid for p in participants), min_independent=min_independent)
            except m.MembershipError as exc:
                raise ControllerError(str(exc)) from None
        if proposal is not None and general:
            raise ControllerError("제안한 질문은 격리 실행으로 보냅니다.")
        if split is not None and not general:
            raise ControllerError("분담 제안은 일반 팀원 작업에만 씁니다.")
        if run_id is None:
            run_id = f"r{time.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex}"
        elif not isinstance(run_id, str) or not re.fullmatch(r"r[0-9]{4}-[0-9]{6}-[0-9a-f]{32}", run_id):
            raise ControllerError("invalid preview run ID")
        if task_id is not None:
            if not isinstance(task_id, str) or not self.store.row("SELECT 1 FROM tasks WHERE task_id = ?", task_id):
                raise ControllerError("작업을 찾을 수 없습니다.")
            if task_title is not None:
                raise ControllerError("기존 작업의 제목은 실행 생성으로 바꿀 수 없습니다.")
        elif task_title is not None and (not isinstance(task_title, str) or not task_title.strip()
                                         or len(task_title.strip()) > 120 or not storable(task_title)):
            raise ControllerError("작업 제목은 1~120자의 올바른 글이어야 합니다.")
        roles["memory"] = self._select_memory(task_id, question, use_memory)
        suggested = self._approved_proposal(proposal, roles, question, task_id) if proposal is not None else None
        if general:
            return self._general_manifest(run_id, task_id, task_title, question, participants, roles,
                                          checked_sources, assignments, split)
        prompt = PROMPT.format(question=question)
        if checked_sources:
            prompt += _source_footer(self._source_root(run_id), [
                {"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for name, data in checked_sources])
        data = prompt.encode("utf-8")
        manifest = {"run_id": run_id, "task_id": task_id, "task_title": task_title.strip() if task_title else question[:120],
                    "mode": ISOLATED, "question": question, "prompt": prompt, "input_sha256": hashlib.sha256(data).hexdigest(),
                    "input_bytes": len(data), "role_config": roles,
                    "min_independent": min_independent, "quorum_policy": quorum_policy,
                    "sources": [source_document.listing(name, content) for name, content in checked_sources],
                    "calls": {"draft_cli": sum(p.transport == CLI for p in participants),
                              "model_calls": 0 if self.runtime.executor.kind != contract.REAL else None,
                              "live_cap": self.runtime.max_real_calls, "provider_caps": dict(self.runtime.provider_call_caps)},
                    "manual_packets": {p.pid: packet(run_id, p.pid, hashlib.sha256(data).hexdigest(), prompt)
                                       for p in participants if p.transport == MANUAL}}
        if approved is not None:
            manifest["refinement"] = approved   # 원문·승인한 차례. 참여자 입력(prompt)에는 승인한 문장만 있다
        if suggested is not None:
            manifest["proposal"] = suggested    # 이 질문을 제안한 실행과 제안. 내가 확인해 시작해야 묶인다
        manifest["confirmation"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return manifest


    def _general_manifest(self, run_id, task_id, task_title, question, participants, roles, checked_sources,
                          assignments, split=None) -> dict[str, Any]:
        """일반 실행의 확인 명세. 팀원마다 맡긴 일·입력 전문·받은 자료(이름·해시·크기·종류·범위)를 고정한다. 아무
        팀원도 받지 않는 자료는 원장에 두지 않도록 거절한다. 실행의 입력 해시는 팀원별 입력 해시를 묶은 것이다."""
        if not isinstance(assignments, dict) or set(assignments) != {p.pid for p in participants}:
            raise ControllerError("일반 팀원마다 맡길 일과 받을 자료가 필요합니다.")
        contents = dict(checked_sources)
        members, used = {}, set()
        for p in participants:
            item = assignments[p.pid]
            if not isinstance(item, dict) or set(item) != {"task", "sources"}:
                raise ControllerError(f"{p.label}: 맡길 일(task)과 받을 자료(sources)만 적습니다.")
            task = item["task"].strip() if isinstance(item["task"], str) else ""
            if not task or len(task) > MAX_TASK_CHARS or not storable(task):
                raise ControllerError(f"{p.label}: 맡길 일은 1~{MAX_TASK_CHARS}자의 올바른 글이어야 합니다.")
            names = item["sources"]
            if (not isinstance(names, list) or any(not isinstance(n, str) or n not in contents for n in names)
                    or len(set(names)) != len(names)):
                raise ControllerError(f"{p.label}: 받을 자료는 이번에 붙인 자료의 이름을 한 번씩만 적습니다.")
            used.update(names)
            listed = [source_document.listing(n, contents[n], assignment=True) for n in sorted(names)]
            prompt = GENERAL_PROMPT.format(question=question, task=task)
            if listed:
                prompt += _source_footer(self._member_source_root(run_id, p.pid), listed)
            prompt += memory.footer(roles["memory"])
            data = prompt.encode("utf-8")
            members[p.pid] = {"task": task, "prompt": prompt, "input_sha256": hashlib.sha256(data).hexdigest(),
                              "input_bytes": len(data), "sources": listed}
        unused = sorted(set(contents) - used)
        if unused:
            raise ControllerError("아무 팀원도 받지 않는 자료가 있습니다: " + ", ".join(unused))
        manifest = {"run_id": run_id, "task_id": task_id, "task_title": task_title.strip() if task_title else question[:120],
                    "mode": GENERAL, "question": question, "prompt": "",
                    "input_sha256": _bundle_digest(members), "input_bytes": sum(v["input_bytes"] for v in members.values()),
                    "role_config": roles, "min_independent": 0, "quorum_policy": NO_QUORUM,
                    "sources": [source_document.listing(name, content) for name, content in checked_sources],
                    "assignments": members,
                    "calls": {"draft_cli": len(participants),
                              "model_calls": 0 if self.runtime.executor.kind != contract.REAL else None,
                              "live_cap": self.runtime.max_real_calls, "provider_caps": dict(self.runtime.provider_call_caps)},
                    "manual_packets": {}}
        if split is not None:   # 맡길 일·자료를 검사한 뒤에 제안과 견준다(카드 #135)
            manifest["split"] = self._approved_split(split, roles, question, participants, assignments,
                                                     checked_sources, task_id)
        manifest["confirmation"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return manifest


    def _source_root(self, run_id: str) -> str:
        """참여자가 읽기 전용으로 볼 자료 폴더. 참여자의 작업 폴더(work_root/<run>/<pid>)와 겹치지 않는다."""
        return os.path.join(self.runtime.work_root, "_sources", run_id)


    def _source_dir(self, run_id: str) -> str | None:
        """원장의 자료를 폴더로 두고, 시도마다 원장의 목록·크기·sha256과 다시 맞춘다. 다르면 거절한다 — 아무것도
        시작하지 않았다. 폴더는 임시 이름으로 다 쓴 뒤 한 번에 옮긴다. 시도 도중의 바꿔치기(K14)는 막지 못한다."""
        rows = self.store.rows("SELECT name, sha256, bytes, content FROM sources WHERE run_id = ? ORDER BY name", run_id)
        root = self._source_root(run_id)
        run = self.repository._run(run_id)
        expected = PROMPT.format(question=run["question"]) + (_source_footer(root, rows) if rows else "")
        if run["prompt"] != expected:
            raise ControllerError("the fixed source manifest or folder differs from the original prompt; "
                                  "no call was started")
        return self._snapshot(root, rows) if rows else None


    def _member_source_root(self, run_id: str, pid: str) -> str:
        """일반 팀원 한 명이 받는 자료 폴더. 그 팀원이 받은 자료만 든다 — 다른 팀원의 자료 폴더는 연결하지 않는다."""
        return os.path.join(self._source_root(run_id), pid)


    def _assignment(self, run_id: str, pid: str):
        row = self.store.row("SELECT * FROM assignments WHERE run_id = ? AND pid = ?", run_id, pid)
        if row is None:
            raise ControllerError(f"no assignment for {pid!r} in {run_id!r}")
        return row


    def _member_source_dir(self, run_id: str, pid: str) -> str | None:
        """일반 팀원의 입력 전문을 원장의 목표·맡긴 일·자료 목록으로 다시 만들어 저장한 입력과 해시를 맞추고, 그 팀원이
        받은 자료만 폴더로 둔다. 다르면 거절한다 — 아무것도 시작하지 않았다. _source_dir와 같은 규칙이다."""
        run, item = self.repository._run(run_id), self._assignment(run_id, pid)
        listed = json.loads(item["sources"])
        root = self._member_source_root(run_id, pid)
        expected = GENERAL_PROMPT.format(question=run["question"], task=item["task"]) + (
            _source_footer(root, listed) if listed else "")
        expected += self._run_memory(run)
        data = item["prompt"].encode("utf-8")
        if (item["prompt"] != expected or hashlib.sha256(data).hexdigest() != item["input_sha256"]
                or len(data) != item["input_bytes"]):
            raise ControllerError("the fixed assignment differs from its recorded input; no call was started")
        # 행 하나를 스스로 맞게(맡긴 일·입력 전문·해시·크기를 함께) 바꿔도 실행을 만들 때 묶은 입력 해시와는 다르다
        # (Codex 교차검토, PR #129).
        members = {row["pid"]: row for row in self.store.rows(
            "SELECT pid, input_sha256 FROM assignments WHERE run_id = ?", run_id)}
        if _bundle_digest(members) != run["input_sha256"]:
            raise ControllerError("the fixed assignment differs from the input bundled when the run was created; "
                                  "no call was started")
        if not listed:
            return None
        rows = [self.store.row("SELECT name, sha256, bytes, content FROM sources WHERE run_id = ? AND name = ?",
                               run_id, source["name"]) for source in listed]
        if any(row is None or (row["sha256"], row["bytes"]) != (source["sha256"], source["bytes"])
               or source != source_document.listing(row['name'], row['content'], assignment=True)
               for row, source in zip(rows, listed)):
            raise ControllerError("the source snapshot changed after the run was created; no call was started")
        return self._snapshot(root, rows)


    def _attempt_input(self, run_id: str, pid: str) -> tuple[str, str | None]:
        """이 참여자에게 보낼 입력 전문과 읽기 전용 자료 폴더. 격리 실행은 모두 같은 입력, 일반 실행은 팀원마다 다르다."""
        run = self.repository._run(run_id)
        if run["mode"] == GENERAL:
            return self._assignment(run_id, pid)["prompt"], self._member_source_dir(run_id, pid)
        return run["prompt"], self._source_dir(run_id)


    def _snapshot(self, root: str, rows) -> str:
        """원장의 자료 행(이름·sha256·크기·내용)을 root 폴더로 두고 다시 맞춘다."""
        if not os.path.isdir(root):
            staging = f"{root}.{uuid.uuid4().hex}.tmp"
            os.makedirs(staging)
            for row in rows:
                path = os.path.join(staging, row["name"])
                with open(path, "xb") as handle:
                    handle.write(row["content"])
                if os.name == "posix":
                    os.chmod(path, 0o444)
            os.rename(staging, root)   # 원장은 controller 하나만 열고 계획은 self.lock 안에서만 한다 — 경쟁 없음
        if sorted(os.listdir(root)) != [row["name"] for row in rows]:
            raise ControllerError("the source snapshot changed after the run was created; no call was started")
        for row in rows:
            path = os.path.join(root, row["name"])
            if os.path.islink(path) or not os.path.isfile(path):
                raise ControllerError("the source snapshot changed after the run was created; no call was started")
            with open(path, "rb") as handle:
                data = handle.read(MAX_SOURCE_BYTES + 1)
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ControllerError("the source snapshot changed after the run was created; no call was started")
        return root


    def _select_memory(self, task_id, question, enabled):
        if task_id is not None and (not isinstance(task_id, str) or not self.store.row(
                "SELECT 1 FROM tasks WHERE task_id = ?", task_id)):
            raise ControllerError("작업을 찾을 수 없습니다.")
        try:
            with self.runtime.lock:
                return memory.select(self.store, task_id, question, enabled=enabled)
        except ValueError as exc:
            raise ControllerError(str(exc)) from None


    def _run_memory(self, run):
        try:
            return memory.footer(json.loads(run["role_config"] or "{}").get("memory"))
        except ValueError as exc:
            raise ControllerError(str(exc)) from None


    def _approved_proposal(self, proposal, roles, question: str, task_id) -> dict[str, Any]:
        """제안에서 온 새 실행. "한 번 더"인 통과한 제안이고, 실행에 쓰지 않았고, 같은 작업이고, 원문 모드이며, 질문이
        제안한 질문과 글자까지 같아야 한다. 고쳐 쓴 질문은 내 질문이다 — 화면이 제안을 붙이지 않는다."""
        if not isinstance(proposal, dict) or set(proposal) != {"id"} or not isinstance(proposal["id"], str):
            raise ControllerError("제안은 {id}로 줍니다.")
        row = self.store.row("SELECT * FROM proposals WHERE proposal_id = ?", proposal["id"])
        if row is None:
            raise ControllerError("제안을 찾을 수 없습니다.")
        if row["used_by"]:
            raise ControllerError("이미 실행에 쓴 제안입니다. 같은 제안으로 실행을 두 번 만들지 않습니다.")
        reply = (json.loads(row["result"]) if row["result"] else {}).get("reply")
        if row["state"] != ACCEPTED or not reply or reply["next"] != "again":
            raise ControllerError("형식 검사를 통과한 '한 번 더' 제안만 새 실행이 됩니다.")
        if roles["input_mode"] != "original":
            raise ControllerError("제안한 질문은 원문 모드로 보냅니다. 다듬으려면 제안을 붙이지 말고 새로 다듬으세요.")
        if task_id != self.repository._run(row["run_id"])["task_id"]:
            raise ControllerError("제안은 그 제안이 나온 작업의 새 실행에만 씁니다.")
        if question != reply["question"]:
            raise ControllerError("보낼 질문이 제안한 질문과 다릅니다. 고쳐 쓴 질문은 제안 없이 보내세요.")
        return {"proposal_id": row["proposal_id"], "source_run": row["run_id"], "question": reply["question"]}


    def _approved_split(self, split, roles, question, participants, assignments, checked_sources, task_id):
        """분담 제안에서 온 일반 실행. 통과했고 실행에 쓰지 않은 제안이어야 하며, 목표·팀원·자료(이름·해시)·작업·역할판의
        오케스트레이터가 제안 때와 같아야 한다. 사람이 맡길 일이나 자료를 고쳤으면 as_proposed가 거짓이다 — 거절하지 않는다."""
        if not isinstance(split, dict) or set(split) != {"id"} or not isinstance(split["id"], str):
            raise ControllerError("분담 제안은 {id}로 줍니다.")
        row = self.store.row("SELECT * FROM splits WHERE split_id = ?", split["id"])
        if row is None:
            raise ControllerError("분담 제안을 찾을 수 없습니다.")
        if row["used_by"]:
            raise ControllerError("이미 실행에 쓴 분담 제안입니다. 같은 제안으로 실행을 두 번 만들지 않습니다.")
        reply = (json.loads(row["result"]) if row["result"] else {}).get("reply")
        if row["state"] != ACCEPTED or not reply:
            raise ControllerError("검사를 통과한 분담 제안만 씁니다.")
        fixed, board = json.loads(row["orchestrator"]), roles["orchestrator"] or {}
        if (fixed["pid"], fixed["adapter_id"], fixed["model"]) != (board.get("pid"), board.get("adapter_id"),
                                                                     board.get("model")):
            raise ControllerError("분담을 제안한 오케스트레이터·모델과 역할판의 오케스트레이터가 다릅니다.")
        if list(json.loads(row["members"]).values()) != [p.pid for p in participants]:
            raise ControllerError("분담 제안 때와 팀원이 다릅니다. 다시 제안받거나 제안 없이 나누세요.")
        listed = [(s["name"], s["sha256"]) for s in json.loads(row["sources"])]
        if listed != [(name, hashlib.sha256(data).hexdigest()) for name, data in checked_sources]:
            raise ControllerError("분담 제안 때와 자료가 다릅니다. 다시 제안받거나 제안 없이 나누세요.")
        if row["goal"] != question or row["task_id"] != task_id:
            raise ControllerError("분담 제안 때와 전체 목표나 작업이 다릅니다.")
        sent = {pid: {"task": item["task"].strip(), "sources": sorted(item["sources"])}
                for pid, item in assignments.items()}
        return {"split_id": row["split_id"], "as_proposed": sent == reply["assignments"]}


    def _approved_refinement(self, refinement, roles, question: str, task_id=None, use_memory=True) -> dict[str, Any]:
        """다듬기 모드 실행의 승인본을 확인한다. 실행에 쓰지 않은 다듬기의, 형식 검사를 통과한 차례의 문장이어야 하고,
        역할판의 슈퍼바이저와 같은 카드·모델이 만든 것이어야 한다. 보낼 질문은 그 문장과 글자까지 같아야 한다."""
        if not isinstance(refinement, dict) or set(refinement) != {"id", "turn"} or type(refinement["turn"]) is not int:
            raise ControllerError("다듬기 모드에는 승인할 다듬기와 차례({id, turn})가 필요합니다.")
        row = self.store.row("SELECT * FROM refinements WHERE refine_id = ?", refinement["id"])
        if row is None:
            raise ControllerError("다듬기를 찾을 수 없습니다.")
        if row["run_id"]:
            raise ControllerError("이미 다른 실행에 쓴 다듬기입니다. 같은 승인으로 실행을 두 번 만들지 않습니다.")
        snapshot = self.store.row("SELECT payload FROM events WHERE run_id = ? AND kind = 'memory_selected'",
                                  row["refine_id"])
        remembered = json.loads(snapshot["payload"])["memory"] if snapshot else None
        if remembered and remembered["entries"] and (remembered["task_id"] != task_id or not use_memory):
            raise ControllerError("다듬기에 쓴 작업 기억과 설정이 다릅니다. 이 작업에서 새로 다듬으세요.")
        fixed, board = json.loads(row["supervisor"]), roles["supervisor"]
        if (fixed["pid"], fixed["adapter_id"], fixed["model"]) != (board["pid"], board["adapter_id"], board["model"]):
            raise ControllerError("다듬기를 한 슈퍼바이저·모델과 역할판의 슈퍼바이저가 다릅니다.")
        turns = self.store.rows("SELECT * FROM refine_turns WHERE refine_id = ? ORDER BY turn", row["refine_id"])
        if any(turn["state"] in (RUNNING, UNKNOWN) for turn in turns):
            raise ControllerError("끝나지 않았거나 종료를 확인하지 못한 다듬기 차례가 있습니다. 먼저 정리하세요.")
        chosen = next((turn for turn in turns if turn["turn"] == refinement["turn"]), None)
        if chosen is None or chosen["state"] != ACCEPTED:
            raise ControllerError("형식 검사를 통과한 차례만 승인할 수 있습니다.")
        approved = json.loads(chosen["result"])["reply"]["refined"]
        if question != approved:
            raise ControllerError("보낼 질문이 승인한 다듬기 문장과 다릅니다. 승인한 문장을 그대로 보냅니다.")
        return {"refine_id": row["refine_id"], "turn": chosen["turn"], "original": row["original"],
                "approved": approved, "turns": len(turns)}
