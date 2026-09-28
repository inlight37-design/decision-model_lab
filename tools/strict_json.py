"""표준 라이브러리만으로 JSON을 엄격하게 읽는다 — 중복 키와 NaN·Infinity 같은 비표준 상수를 입력 경계에서 거절한다.

검사 도구 넷(validate_sources·validate_v02·validate_design·check_frontier_protocol)이 같이 쓴다. 도구마다 자기 오류
종류를 넘긴다(기본은 ValueError). 각 도구는 저장소 루트를 sys.path에 넣고 `from tools.strict_json import …`로
가져온다(tools/w2와 같은 방식) — `python tools/x.py`로 돌리든 시험이 import하든 같은 파일이다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def strict_loads(text: str, *, error: type[Exception] = ValueError) -> Any:
    def constant(value: str) -> None:
        raise error(f"Non-standard JSON constant: {value}")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise error(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(text, parse_constant=constant, object_pairs_hook=pairs)


def strict_load(path: Path, *, error: type[Exception] = ValueError) -> Any:
    return strict_loads(path.read_text(encoding="utf-8"), error=error)
