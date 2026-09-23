"""모의 모드의 가짜 CLI. 모델을 부르지 않고 aux-pc에서 받은 Claude·Codex 출력 형식을 흉내 낸다.

  python fake_cli.py <claude|codex> <행동>  (질문은 stdin)

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


def answer(flavor: str, question: str) -> str:
    digest = hashlib.sha256(question.encode("utf-8")).hexdigest()[:12]
    asked = question.split("질문:", 1)[-1].strip()
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
    model = f"mock-{flavor}"
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
