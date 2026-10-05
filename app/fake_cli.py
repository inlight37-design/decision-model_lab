"""모의 모드의 가짜 CLI. 모델을 부르지 않고 aux-pc에서 받은 Claude·Codex 출력 형식을 흉내 낸다.

  python fake_cli.py <claude|codex> <행동> [모델]  (질문은 stdin. 모델을 주면 Claude 흉내가 그 이름을 보고한다)

행동: ok(곧 답함) · slow(오래 걸림) · fail(CLI 오류) · partial_input(1바이트만 읽고 stdin을 닫음, WM-01 —
질문이 파이프 버퍼보다 클 때만 쓰는 쪽에서 드러난다) ·
hang(끝나지 않음 → 시간 초과). 답에는 "모의 출력"이라고 적는다 — 실제 모델의 답으로 읽히면 안 된다.
"""
import hashlib
import json
import os
import sys
import time

DELAY = {"ok": 1.2, "slow": 6.0, "fail": 0.8, "partial_input": 0.8, "hang": 3600.0}


REFINE_MARKER = "[다듬기 요청]"   # app/refine.py의 MARKER와 같은 줄. 이 가짜는 격리 안에서 app 패키지 없이 돈다
NEXT_MARKER = "[다음 단계 제안 요청]"   # app/next_step.py의 MARKER와 같은 줄
SPLIT_MARKER = "[분담 제안 요청]"   # app/split.py의 MARKER와 같은 줄
COLLATE_MARKER = "[결과 모으기 요청]"   # app/collate.py의 MARKER와 같은 줄
REVIEW_MARKER = "[교차검토 요청]"   # app/cross_review.py의 MARKER와 같은 줄
REVISION_MARKER = '[수정 답 요청]'
RECHECK_MARKER = '[수정 답 재검토 요청]'


def revision_reply(question):
    recheck = question.startswith(RECHECK_MARKER)
    label = '재검토 근거' if recheck else '수정 근거'
    nonce = question.split('이번 경계 표식: ', 1)[1].split('\n', 1)[0]
    data = json.loads(question.split(f'<<<{label} 시작 {nonce}>>>\n', 1)[1].split(f'\n<<<{label} 끝 {nonce}>>>', 1)[0])
    snapshot = data['source'] if recheck else data
    responses = [{'finding': f['id'], 'status': 'uncertain' if recheck else 'unresolved',
                  'detail': '모의: 반례를 유지함. 실제 개선·검증 아님'} for f in snapshot['findings']]
    reply = {'assessments': responses, 'findings': []} if recheck else {
        'answer': '[모의 수정 · 모델 호출 없음]\n' + snapshot['base']['text'] + '\n조건과 반례는 미해결입니다.',
        'responses': responses}
    return json.dumps(reply, ensure_ascii=False)


def review_reply(question: str) -> str:
    """교차검토 지시문에 모의 JSON으로 답한다. 다른 팀원의 답마다 첫 줄을 글자 그대로 인용해 지적 하나를 낸다. 자기
    답("내 답")은 겨누지 않는다. 이번 경계 표식이 붙은 경계 줄만 믿는다."""
    nonce = question.split("이번 경계 표식: ", 1)[-1].split("\n", 1)[0].strip()
    findings = []
    for line in question.splitlines():
        if not (line.startswith("<<<D") and line.endswith(f" 시작 {nonce}>>>")):
            continue
        label = line[3:].split(" ", 1)[0]
        body = question.split(line + "\n", 1)[-1].split(f"\n<<<{label} 끝 {nonce}>>>", 1)[0]
        first = next((row for row in body.splitlines() if row.strip()), "")
        if first:
            findings.append({"target": label, "quote": first, "kind": "missing_condition",
                             "detail": "모의: 이 문장에 어떤 조건에서 맞는지가 빠져 있다(실제 검토 아님)"})
    return json.dumps({"findings": findings}, ensure_ascii=False)


def collate_reply(question: str) -> str:
    """결과 모으기 지시문에 모의 JSON으로 답한다. 팀원마다 결과의 첫 줄을 글자 그대로 인용하고, 인용 없는 주장 하나를
    덧붙인다 — 화면의 원문 일치·원문에 없음 표시를 확인하려는 것이다. 이번 경계 표식이 붙은 경계 줄만 믿는다."""
    nonce = question.split("이번 경계 표식: ", 1)[-1].split("\n", 1)[0].strip()
    claims = []
    for line in question.splitlines():
        if not (line.startswith("<<<") and line.endswith(f" 시작 {nonce}>>>")):
            continue
        label = line[3:].split(" ", 1)[0]
        body = question.split(line + "\n", 1)[-1].split(f"\n<<<{label} 끝 {nonce}>>>", 1)[0]
        body = body.split("결과:\n", 1)[-1]
        first = next((row for row in body.splitlines() if row.strip()), "")
        if first and not first.startswith("(결과 없음"):
            claims.append({"statement": f"[모의 취합] {label}의 결과 첫 줄", "quotes": [{"member": label, "text": first}]})
    claims.append({"statement": "[모의 취합] 원문에 없는 추가 주장(표시 확인용)", "quotes": []})
    return json.dumps({"claims": claims, "overlaps": ["모의: 겹침·어긋남은 사람이 판단한다(실제 취합 아님)"],
                       "gaps": ["모의: 아무도 비용을 다루지 않았다"], "next": ["모의: 각 결과를 원문으로 읽고 판단"]},
                      ensure_ascii=False)


def split_reply(question: str) -> str:
    """분담 제안 지시문에 모의 JSON으로 답한다. 팀원 이름표와 자료 이름을 지시문에서 읽어 자료를 차례로 나눠 준다."""
    members = [line[2:].split(":", 1)[0] for line in question.split("팀원:\n", 1)[-1].split("\n\n", 1)[0].splitlines()
               if line.startswith("- M")]
    files = [line[2:].rsplit(" (", 1)[0] for line in question.split("자료:\n", 1)[-1].splitlines() if line.startswith("- ")]
    return json.dumps({"assignments": [{"member": label, "task": f"[모의 분담] {label}: 목표의 {index}번째 부분을 본다",
                                        "sources": files[index - 1::len(members)]}
                                       for index, label in enumerate(members, 1)],
                       "reason": "모의: 자료를 차례로 나눴다(실제 판단 아님)"}, ensure_ascii=False)


def next_reply(question: str) -> str:
    """다음 단계 제안 지시문에 모의 JSON으로 답한다. 늘 "한 번 더"를 제안한다 — 화면 흐름 확인용이다."""
    asked = question.split("보낸 질문:\n", 1)[-1].split("\n", 1)[0].strip() or "(빈 질문)"
    return json.dumps({"next": "again", "reason": "모의: 두 답의 결론이 갈려 조건을 좁혀 한 번 더 묻는다(실제 판단 아님)",
                       "question": f"[모의 제안] {asked[:200]} — 예산 조건을 넣으면?",
                       "open_points": ["모의: 비용 추정이 서로 다름"]}, ensure_ascii=False)


def refine_reply(question: str) -> str:
    """다듬기 지시문에 모의 JSON으로 답한다. 원문 첫 줄을 되풀이할 뿐 다듬지 않는다 — 화면 흐름 확인용이다."""
    original = question.split("원문:\n", 1)[-1].split("\n", 1)[0].strip() or "(빈 원문)"
    turn = question.count("의 다듬은 질문:") + 1
    return json.dumps({"refined": f"[모의 다듬기 {turn}차례] {original[:200]}",
                       "changes": ["모의: 무엇을 비교할지 한 문장으로 모았다(실제 다듬기 아님)"],
                       "ask": "모의: 결정 기한이나 예산 같은 조건이 있나요?"}, ensure_ascii=False)


def answer(flavor: str, question: str) -> str:
    if question.startswith((REVISION_MARKER, RECHECK_MARKER)):
        return revision_reply(question)
    if question.startswith(REFINE_MARKER):
        return refine_reply(question)
    if question.startswith(NEXT_MARKER):
        return next_reply(question)
    if question.startswith(SPLIT_MARKER):
        return split_reply(question)
    if question.startswith(COLLATE_MARKER):
        return collate_reply(question)
    if question.startswith(REVIEW_MARKER):
        return review_reply(question)
    digest = hashlib.sha256(question.encode("utf-8")).hexdigest()[:12]
    # Recall can itself contain '이전 질문:'. Use the current prompt's section
    # heading, including general-team goals, instead of a substring in history.
    asked = question
    for index, line in enumerate(question.splitlines()):
        if line.startswith(("질문:", "전체 목표:")):
            asked = "\n".join([line.split(":", 1)[1], *question.splitlines()[index + 1:]])
            break
    asked = asked.strip()
    first = asked.splitlines()[0][:80] if asked else "(빈 질문)"
    lean = {"claude": "조건부 찬성 — 되돌릴 비용이 작을 때만", "codex": "보류 — 먼저 작은 실험으로 확인"}[flavor]
    return (f"[모의 출력 · {flavor} 흉내 · 모델 호출 없음]\n"
            f"받은 질문: {first}\n입력 sha256 앞자리: {digest}\n"
            f"입장: {lean}.\n근거: 이 답은 화면 흐름을 보여 주려고 만든 고정 문장이다.")


def main() -> int:
    flavor, behavior = sys.argv[1], sys.argv[2]
    if behavior == "partial_input":
        os.read(0, 1)
        os.close(0)
        question = "(1바이트만 읽음)"
    else:
        question = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    time.sleep(DELAY[behavior])
    model = sys.argv[3] if len(sys.argv) > 3 else f"mock-{flavor}"   # Codex 흉내는 실제처럼 모델을 보고하지 않는다
    if flavor == "claude":
        failed = behavior == "fail"
        print(json.dumps({
            "type": "result", "subtype": "success", "is_error": failed,
            "result": "모의 CLI 오류: 사용량 한도(흉내)" if failed else answer(flavor, question),
            "terminal_reason": "mock_error" if failed else None,
            "modelUsage": {model: {"inputTokens": len(question) // 3, "outputTokens": 120}},
            "usage": {"input_tokens": len(question) // 3, "output_tokens": 120},
            "permission_denials": [],
        }, ensure_ascii=False))
        return 1 if failed else 0
    events = [{"type": "thread.started", "thread_id": "mock"}, {"type": "turn.started"}]
    if behavior == "fail":
        events.append({"type": "turn.failed", "error": {"message": "모의 CLI 오류: 사용량 한도(흉내)"}})
    else:
        events.append({"type": "item.completed", "item": {"type": "agent_message", "text": answer(flavor, question)}})
        events.append({"type": "turn.completed", "usage": {"input_tokens": len(question) // 3, "output_tokens": 140}})
    for event in events:
        print(json.dumps(event, ensure_ascii=False))
    return 1 if behavior == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
