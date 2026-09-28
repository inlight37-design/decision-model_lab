"""분담 제안(역할판 D 셋째 조각, 카드 #135): 일반 팀원 작업의 오케스트레이터 모델이 팀원마다 맡길 일과 받을 자료를
제안한다. 이 파일은 지시문과 답의 검사만 한다 — 모델을 부르지 않는다.

오케스트레이터는 전체 목표, 팀원 목록(이름표 M1·M2와 카드 이름), 붙인 자료 전부(읽기 전용 사본 폴더 하나)를 받는다.
일반 작업은 봉인이 없으므로 카드 이름을 가리지 않는다. 제안은 화면의 팀원별 칸을 채우기만 한다 — 사람이 고치거나
그대로 두고 보낼 입력을 확인해 시작해야 실행이 된다(controller.prepare_run). 검사는 일반 실행의 입력 규칙과 같다:
팀원마다 한 번, 목록에 있는 자료만, 모든 자료가 누군가에게 간다.
"""
from __future__ import annotations

from typing import Any

from app.reply import check_text, json_object

# 지시문의 첫 줄. 모의 CLI(fake_cli.py)가 이 줄로 분담 제안 요청을 알아본다 — 두 곳을 같이 바꾼다.
MARKER = "[분담 제안 요청]"
MAX_TASK, MAX_REASON = 4000, 1500   # 맡길 일의 상한은 일반 실행의 MAX_TASK_CHARS와 같다
PROMPT = (MARKER + "\n너는 일반 팀원 작업의 오케스트레이터다. 전체 목표를 팀원들에게 나눠 맡길 계획을 제안한다. 팀원은 "
          "각자 받은 자료만 읽기 전용으로 보고 한 번씩 답하며, 서로의 답을 보지 않는다.\n규칙:\n"
          "- 팀원마다 맡길 일 하나를 겹치지 않게 구체적으로 쓴다. 답을 미리 쓰지 않는다.\n"
          "- 자료는 아래 목록의 이름만 쓰고, 모든 자료는 적어도 한 팀원이 받는다.\n"
          "- 파일을 고치지 않는다.\n"
          f"- task는 {MAX_TASK}자, reason은 {MAX_REASON}자까지다. 넘으면 검사기가 제안 전체를 거절한다.\n"
          '출력은 JSON 객체 하나만 쓴다: {{"assignments": [{{"member": "M1", "task": "맡길 일", '
          '"sources": ["자료 이름"]}}], "reason": "이렇게 나눈 이유"}}\n\n'
          "전체 목표:\n{goal}\n\n팀원:\n{members}\n\n자료:\n{sources}\n")


class SplitError(ValueError):
    """오케스트레이터의 분담 제안이 검사를 통과하지 못했다. 그 제안으로 칸을 채우지 않는다."""


def prompt(goal: str, members: dict[str, str], sources: list[dict], folder: str | None) -> str:
    """members: 이름표 → 카드 이름(보여 주는 이름). sources: 이름·크기. folder: 자료 사본 폴더(자료가 없으면 None)."""
    listing = "\n".join(f"- {label}: {name}" for label, name in members.items())
    files = (f"읽기 전용 폴더 {folder}에 있다.\n" + "\n".join(f"- {s['name']} ({s['bytes']} bytes)" for s in sources)
             if sources else "없음")
    return PROMPT.format(goal=goal, members=listing, sources=files)


def _text(value: Any, what: str, limit: int) -> str:
    return check_text(value, what, limit, error=SplitError)


def check(text: str, labels: dict[str, str], names: list[str]) -> dict[str, Any]:
    """labels: 이름표 → 참여자 ID. names: 붙인 자료 이름. 돌려주는 assignments는 참여자 ID → {task, sources}다."""
    raw = json_object(text, error=SplitError, who="orchestrator", what="split")
    if set(raw) - {"assignments", "reason"}:
        raise SplitError("the split may only have assignments and reason")
    items = raw.get("assignments")
    if not isinstance(items, list) or len(items) != len(labels):
        raise SplitError("assignments must list every member exactly once")
    result, used = {}, set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"member", "task", "sources"}:
            raise SplitError("each assignment has member, task and sources only")
        member = item["member"]
        # 글이 아닌 이름표(목록·객체)는 dict 조회에서 TypeError가 난다 — 형식 실패로 돌려 원문을 남긴다(Codex 교차검토)
        if not isinstance(member, str) or member not in labels or labels[member] in result:
            raise SplitError("each assignment names a different listed member")
        chosen = item["sources"]
        if (not isinstance(chosen, list) or any(not isinstance(n, str) or n not in names for n in chosen)
                or len(set(chosen)) != len(chosen)):
            raise SplitError("sources must be listed file names, each once")
        used.update(chosen)
        result[labels[member]] = {"task": _text(item["task"], "task", MAX_TASK), "sources": sorted(chosen)}
    if set(names) - used:
        raise SplitError("every attached file must go to at least one member")
    return {"assignments": result, "reason": _text(raw.get("reason"), "reason", MAX_REASON)}
