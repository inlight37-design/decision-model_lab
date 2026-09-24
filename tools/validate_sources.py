#!/usr/bin/env python3
"""근거 원장의 구조 검사. 원문 접근·인용 적합성·주장의 진실을 검증하지 않는다.

실행: python tools/validate_sources.py
의존성: jsonschema (검사 환경: 4.26.0)

이 도구가 확인하는 것은 원장이 자기 계약을 지키는지뿐이다. URL 이 살아 있는지,
locator 가 가리키는 문단이 실제로 그 주장을 담는지, limits 가 정확한지는
사람이 원문을 읽어야 알 수 있다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# (원장 경로, 스키마 $defs 이름)
REGISTRIES = (
    ("docs/architecture/v0.3/sources.json", "registry_v03"),
    ("docs/architecture/v0.4/sources.json", "registry_v04"),
)


def strict_load(path: Path) -> Any:
    """중복 키와 비표준 JSON 상수를 입력 경계에서 거절한다."""
    def constant(value: str) -> None:
        raise ValueError(f"Non-standard JSON constant: {value}")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"),
                      parse_constant=constant, object_pairs_hook=pairs)


def errors_for(registry: Any, definition: str, schema: dict[str, Any]) -> list[str]:
    from jsonschema import Draft202012Validator

    fragment = {"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]}
    Draft202012Validator.check_schema(fragment)
    return [f"{error.json_path}: {error.message}"
            for error in Draft202012Validator(fragment).iter_errors(registry)]


def main() -> int:
    # Windows의 리디렉션된 출력은 CP1252일 수도 있다. 한글 결과 줄이 검사를 실패시키지 않게 UTF-8로 고정한다.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        from jsonschema import Draft202012Validator  # noqa: F401
    except ImportError:
        print("jsonschema가 필요합니다. 검사에 사용한 버전은 4.26.0입니다.")
        print("  python -m pip install -r requirements-design.txt")
        return 2

    schema = strict_load(ROOT / "contracts/sources.schema.json")
    failures = 0
    for relative, definition in REGISTRIES:
        registry = strict_load(ROOT / relative)
        found = errors_for(registry, definition, schema)
        count = len(registry["sources"])
        if found:
            failures += len(found)
            print(f"FAIL {relative} ({count} sources)")
            for message in found:
                print(f"     {message}")
        else:
            print(f"PASS {relative} ({count} sources)")

    if failures:
        print(f"\n{failures} structural problem(s) in the evidence registries.")
        return 1
    print("\n범위: 원장의 구조와 필수 필드만. 원문 진실성·URL 가용성·인용 적합성은 미검증.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
