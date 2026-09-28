"""상위 모델 자리(다듬기·다음 단계·분담·모으기·교차검토·합성)가 함께 쓰는 조각: 넣을 글의 경계 표식과 이름표 블록,
답에서 JSON 객체 하나 찾기, 칸의 글·목록 검사, 형식 검사에 실패한 답의 원문 보존. 모델을 부르지 않는다.

자리마다 오류 종류가 다르므로(RefineError·CollateError·…) 검사 함수는 던질 오류 종류를 인자로 받는다. 검사는 형식·길이뿐이다
— 인용 대조와 사실 검증은 각 자리가 따로 한다.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
from typing import Any, Iterable

MAX_RAW_CHARS = 65536


def boundary(texts: Iterable[str], nonce: str | None = None) -> str:
    """이번 호출의 경계 표식. 이름표 블록의 시작 줄과 끝 줄에 붙인다.

    넣을 글은 이 호출 전에 끝났으므로 표식을 알 수 없다 — 글 안에 경계 줄을 흉내 내도 다른 이름표의 블록처럼
    보이지 않는다(Codex 교차검토, PR #139). 넣을 글 어디에든 이미 있는 값이면 새로 뽑는다. nonce는 시험용 시작값이다.
    """
    texts = list(texts)
    while nonce is None or any(nonce in text for text in texts):
        nonce = secrets.token_hex(6)
    return nonce


def block(label: str, nonce: str, body: str) -> str:
    """이름표 블록 하나. 모의 CLI(fake_cli.py)가 같은 모양의 시작 줄로 블록을 알아본다 — 두 곳을 같이 바꾼다."""
    return f"<<<{label} 시작 {nonce}>>>\n{body}\n<<<{label} 끝 {nonce}>>>"


def json_object(text: str, *, error: type[ValueError], who: str, what: str) -> dict:
    """답에서 JSON 객체 하나를 찾는다. 통째로, 코드 울타리 안, 첫 { 부터 마지막 } 까지 순서로 본다.

    who는 답한 쪽(synthesizer·supervisor·orchestrator·reviewer), what은 그 답의 이름(synthesis·proposal·…)이다 —
    둘 다 오류 문구에만 쓴다. 중복 키의 마지막 값만 남기면 반례·인용이 조용히 사라지므로 중첩 객체까지 거절한다.
    """
    def unique(pairs: list[tuple[str, Any]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise error(f"duplicate JSON object key in {what}")
            result[key] = value
        return result

    candidates = [text.strip()]
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        candidates.append(fence.group(1))
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        candidates.append(text[start:end + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate, object_pairs_hook=unique)
        except error:
            raise   # 모호한 객체에서 다른 후보를 골라 근거를 조용히 버리지 않는다.
        except (ValueError, RecursionError):
            continue
        if isinstance(value, dict):
            return value
    raise error(f"the {who} did not return one JSON object")


def check_text(value: Any, what: str, limit: int, *, error: type[ValueError], optional: bool = False) -> str | None:
    """칸의 글. 비어 있지 않고 limit자 이하이며 UTF-8로 저장할 수 있어야 한다 — JSON의 고립 surrogate를 원장·HTTP
    출력까지 보내면 결과 저장 자체가 실패한다. 양끝 공백을 지운 값을 돌려준다; 인용 대조는 호출한 쪽이 원래 값으로 한다."""
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise error(f"{what} must be non-empty text of at most {limit} characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise error(f"{what} must be valid UTF-8 text") from None
    return value.strip()


def check_items(value: Any, what: str, limit: int, *, error: type[ValueError]) -> list:
    """목록 칸. 없으면 빈 목록, 있으면 limit개 이하의 list여야 한다."""
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > limit:
        raise error(f"{what} must be a list of at most {limit} items")
    return value


def failed_reply(text: str) -> dict:
    """형식 검사에 실패한 답의 원문(앞 MAX_RAW_CHARS자). 결과가 아니며 인용 대조·사실 검사를 하지 않았다.

    상위 자리의 답은 봉인 대상이 아니라 원문을 남겨도 된다. sha256과 chars는 자르기 전 전체 답의 것이다.
    JSON 문자열의 고립 surrogate는 원장에 쓸 수 없어 \\uXXXX 표기로 바꿔 남기고 escaped로 표시한다.
    """
    data = text.encode("utf-8", "surrogatepass")
    kept = text[:MAX_RAW_CHARS]
    safe = kept.encode("utf-8", "backslashreplace").decode("utf-8")
    return {"check": "failed_format_check", "text": safe, "chars": len(text), "stored_chars": len(kept),
            "truncated": len(kept) < len(text), "escaped": safe != kept, "sha256": hashlib.sha256(data).hexdigest()}
