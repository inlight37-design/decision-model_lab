#!/usr/bin/env python3
"""합성 JSON 계약의 오프라인 검사. 모델/하네스/샌드박스를 실행하지 않는다.

실행: python tools/validate_design.py
의존성: jsonschema (검사 환경: 4.26.0)
이 파일은 제어부나 완전한 보안 validator의 구현이 아니다.
"""
from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, ValidationError
except ImportError as exc:
    raise SystemExit("jsonschema가 필요합니다. 검사에 사용한 버전은 4.26.0입니다.") from exc

ROOT = Path(__file__).resolve().parents[1]


def reject_constant(value: str) -> None:
    raise ValueError(f"표준 JSON에 없는 상수: {value}")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"중복 JSON 키: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"),
                      parse_constant=reject_constant, object_pairs_hook=unique_object)


def require_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("NaN/Infinity는 허용하지 않습니다.")
    if isinstance(value, dict):
        for item in value.values():
            require_finite(item)
    elif isinstance(value, list):
        for item in value:
            require_finite(item)


def validate_packet(packet: dict[str, Any], validator: Draft202012Validator) -> None:
    require_finite(packet)
    validator.validate(packet)
    kind = packet["kind"]
    if kind == "task":
        if packet["task_id"] in packet["depends_on"]:
            raise ValueError("자기 자신에 의존할 수 없습니다.")
        for path in packet["write_paths"]:
            # POSIX 상대 경로만 허용. 실제 symlink/ACL/파일 소유권 검사는 별도다.
            invalid = (path.startswith("/") or "\\" in path
                       or re.match(r"^[A-Za-z]:", path)
                       or any(part in ("", ".", "..", ".git") for part in path.split("/"))
                       or any(ord(char) < 32 for char in path))
            if invalid:
                raise ValueError(f"비정상 쓰기 경로: {path!r}")
    elif kind == "decision" and packet["status"] == "ok":
        if not math.isclose(math.fsum(packet["probabilities"].values()), 1.0,
                            rel_tol=0.0, abs_tol=1e-6):
            raise ValueError("확률 합계가 1이 아닙니다.")
        # provider_confidence를 최대 확률 또는 성공 확률로 치환하지 않는다.
    elif kind == "worker_result":
        if packet["status"] == "candidate_ready" and not packet["artifact_ids"]:
            raise ValueError("후보 상태에는 산출물 ID가 필요합니다.")
        usage = packet["usage"]
        total, cached = usage["input_tokens"], usage["cached_input_tokens"]
        if total is not None and cached is not None and cached > total:
            raise ValueError("정규화된 cached input은 total input을 넘을 수 없습니다.")


def main() -> int:
    schema = load_json(ROOT / "contracts/v0.1.schema.json")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    fixtures = load_json(ROOT / "examples/contracts-v0.1.json")
    cases: list[tuple[str, dict[str, Any], bool]] = [
        (f"valid_{packet['kind']}", packet, True) for packet in fixtures
    ]

    def changed(index: int, **changes: Any) -> dict[str, Any]:
        packet = copy.deepcopy(fixtures[index])
        packet.update(changes)
        return packet

    cases += [
        ("unexpected_permission_field", changed(0, grant_permission=True), False),
        ("path_traversal", changed(0, write_paths=["../.env"]), False),
        ("absolute_path", changed(0, write_paths=["/tmp/output"]), False),
        ("windows_drive", changed(0, write_paths=["C:/secrets"]), False),
        ("self_dependency", changed(0, depends_on=["T-017"]), False),
        ("invalid_state_version", changed(0, state_version=0), False),
        ("bad_probability_sum", changed(1, probabilities={"cheap_worker":0.8,"frontier":0.3,"needs_context":0.1}), False),
        ("out_of_range_probability", changed(1, probabilities={"cheap_worker":1.1,"frontier":0.0,"needs_context":0.0}), False),
        ("nan_confidence", changed(1, provider_confidence=float("nan")), False),
        ("unknown_advice", changed(1, advice="execute_shell"), False),
        ("explicit_abstain", changed(1, status="abstain", advice=None, probabilities=None, provider_confidence=None), True),
        ("inconsistent_abstain", changed(1, status="abstain"), False),
        ("worker_self_acceptance", changed(2, status="accepted"), False),
        ("missing_candidate_artifact", changed(2, artifact_ids=[]), False),
        ("cached_exceeds_total", changed(2, usage={"input_tokens":5,"cached_input_tokens":6,"output_tokens":0,"usd":None}), False),
        ("unknown_usage_is_not_zero", changed(2, usage={"input_tokens":None,"cached_input_tokens":None,"output_tokens":None,"usd":None}), True),
        ("infinite_cost", changed(2, usage={"input_tokens":5,"cached_input_tokens":0,"output_tokens":0,"usd":float("inf")}), False),
        ("empty_goal", changed(0, goal=""), False),
        ("confidence_differs_from_max_probability", changed(1, provider_confidence=0.12), True),
        ("read_only_task", changed(0, write_paths=[]), True),
    ]
    failures: list[str] = []
    for name, packet, expected in cases:
        try:
            validate_packet(packet, validator)
            actual = True
        except (ValidationError, ValueError):
            actual = False
        if actual != expected:
            failures.append(name)
        print(f"{'PASS' if actual == expected else 'FAIL'} {name}")

    # parser 자체도 중복 키와 비표준 NaN을 거부해야 한다.
    for name, text in (("duplicate_json_key", '{"a":1,"a":2}'),
                       ("nonstandard_json_nan", '{"a":NaN}')):
        rejected = False
        try:
            json.loads(text, parse_constant=reject_constant, object_pairs_hook=unique_object)
        except ValueError:
            rejected = True
        if not rejected:
            failures.append(name)
        print(f"{'PASS' if rejected else 'FAIL'} {name}")

    total_checks = len(cases) + 2
    print(f"\n{total_checks - len(failures)}/{total_checks} offline checks passed.")
    print("범위: schema와 일부 순수 데이터 불변 조건. 실제 모델/복구/권한/성능 검증 아님.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
