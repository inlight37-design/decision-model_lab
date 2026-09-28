"""다듬기 모드(역할판 D 첫 조각, 카드 #130): 슈퍼바이저 모델에 보낼 지시문과 그 답의 형식 검사. 모델을 부르지 않는다.

슈퍼바이저는 원문과 지금까지의 다듬기 대화만 받는다(자료·다른 실행의 답·기억 없음). 답은 JSON 하나 — refined(다듬은
질문), changes(원문에서 바뀐 점), ask(사람에게 묻는 말, 없으면 null). 답을 흘리지 않았는지는 기계로 판정하지 않는다:
지시문이 금지하고, 사람이 보고 승인한다. 이 파일의 검사는 형식·길이뿐이다. 승인한 refined만 격리 팀원에게 간다 —
대화·원문·차례 기록은 참여자 입력에 넣지 않는다(controller.prepare_run).
"""
from __future__ import annotations

from typing import Any

from app.reply import check_text, failed_reply, json_object

# 지시문의 첫 줄. 모의 CLI(fake_cli.py)가 이 줄로 다듬기 요청을 알아보고 모의 JSON을 돌려준다 — 두 곳을 같이 바꾼다.
MARKER = "[다듬기 요청]"
MAX_TURNS = 3
MAX_ORIGINAL, MAX_NOTE = 8000, 2000
MAX_REFINED, MAX_CHANGES, MAX_CHANGE, MAX_ASK = 4000, 10, 300, 1000
PROMPT = (MARKER + "\n너는 질문을 다듬는 슈퍼바이저다. 사용자가 쓴 원문 질문을, 여러 AI가 서로의 답을 보지 않고 각자 답할 수 "
          "있게 분명한 질문으로 다듬는다.\n규칙:\n"
          "- 질문에 답하지 않는다. 결론·추천·예상 답을 쓰지 않고, 다듬은 질문에도 답을 암시하지 않는다.\n"
          "- 사용자의 목표를 바꾸지 않는다. 모르는 조건은 지어내지 말고 ask로 묻는다.\n"
          "- 파일을 읽거나 고치지 않는다.\n"
          f"- refined는 {MAX_REFINED}자, changes는 {MAX_CHANGES}개·각 {MAX_CHANGE}자, ask는 {MAX_ASK}자까지다. "
          "넘으면 검사기가 이 차례의 답 전체를 거절한다.\n"
          '출력은 JSON 객체 하나만 쓴다: {{"refined": "다듬은 질문", "changes": ["원문에서 바뀐 점"], '
          '"ask": "사용자에게 물을 것 또는 null"}}\n\n원문:\n{original}\n{history}')


class RefineError(ValueError):
    """슈퍼바이저의 답이 형식·길이 검사를 통과하지 못했다. 그 차례는 승인할 수 없다."""


def prompt(original: str, previous: list[tuple[str, dict | None]], note: str) -> str:
    """이번 차례의 지시문. previous는 앞 차례의 (그 차례를 부를 때 사람이 쓴 말, 통과한 답 또는 None)이다. 답을 받지
    못한 차례도 순서를 지키려고 적되 내용은 넣지 않는다. note는 이번 차례를 부르며 사람이 쓴 말이다."""
    lines = []
    for number, (said, reply) in enumerate(previous, 1):
        if said:
            lines.append(f"차례 {number}를 부르며 사용자가 쓴 말: {said}")
        if reply is None:
            lines.append(f"차례 {number}: 답을 받지 못했다")
            continue
        lines.append(f"차례 {number}의 다듬은 질문: {reply['refined']}")
        if reply["changes"]:
            lines.append(f"차례 {number}에 바꾼 점: " + "; ".join(reply["changes"]))
        lines.append(f"차례 {number}에 사용자에게 물은 것: {reply['ask'] or '없음'}")
    if note:
        lines.append(f"이번 차례를 부르며 사용자가 쓴 말: {note}")
    return PROMPT.format(original=original, history=("\n지금까지의 다듬기:\n" + "\n".join(lines) + "\n") if lines else "")


def _text(value: Any, what: str, limit: int) -> str:
    return check_text(value, what, limit, error=RefineError)


def check(text: str) -> dict[str, Any]:
    """답에서 JSON 객체 하나를 찾아 칸 모양과 길이만 본다. 모르는 칸이 있어도 거절한다 — 다듬은 질문 옆에 답이나
    평가를 끼워 넣은 출력을 조용히 버리지 않는다."""
    raw = json_object(text, error=RefineError, who="supervisor", what="refinement")
    if set(raw) - {"refined", "changes", "ask"}:
        raise RefineError("the supervisor reply may only have refined, changes and ask")
    changes = raw.get("changes")
    if changes is None:   # 없거나 null이면 바뀐 점 없음. false·0·""처럼 목록이 아닌 값은 받지 않는다(Codex 교차검토)
        changes = []
    if not isinstance(changes, list) or len(changes) > MAX_CHANGES:
        raise RefineError(f"changes must be a list of at most {MAX_CHANGES} items")
    ask = raw.get("ask")
    return {"refined": _text(raw.get("refined"), "refined", MAX_REFINED),
            "changes": [_text(item, "change", MAX_CHANGE) for item in changes],
            "ask": None if ask is None or (isinstance(ask, str) and not ask.strip()) else _text(ask, "ask", MAX_ASK)}


def rejected_reply(text: str) -> dict[str, Any]:
    """형식 검사에 실패한 답의 원문. 결과가 아니며 승인할 수 없다. 합성의 실패 원문과 같은 모양이다."""
    return failed_reply(text)
