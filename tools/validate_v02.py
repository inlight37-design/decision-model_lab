#!/usr/bin/env python3
"""v0.2 합성 설계 검사. 네트워크, 모델, 명령 실행, 승인 인증은 수행하지 않는다."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def strict_load(path: Path) -> Any:
    def constant(value: str) -> None:
        raise ValueError(f"Non-standard JSON constant: {value}")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=constant,
                      object_pairs_hook=pairs)


def fingerprint(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def shape_errors(value: Any, kind: str) -> list[str]:
    from jsonschema import Draft202012Validator

    try:
        json.dumps(value, allow_nan=False)
    except (ValueError, TypeError) as error:
        return [f"Non-finite or non-JSON value: {error}"]
    schema = strict_load(ROOT / "contracts/v0.2/pilot.schema.json")
    fragment = {"$ref": f"#/$defs/{kind}", "$defs": schema["$defs"]}
    Draft202012Validator.check_schema(fragment)
    return [f"{error.json_path}: {error.message}"
            for error in Draft202012Validator(fragment).iter_errors(value)]


def validate_plan(plan: dict[str, Any]) -> list[str]:
    errors = shape_errors(plan, "plan")
    if errors:
        return errors
    context, routing, measurement = plan["context"], plan["routing"], plan["measurement"]
    if (context["mode"] == "relevance_remote" or routing["advisory"] == "jev_shadow") and not context["remote_approved"]:
        errors.append("Remote source evaluation needs host-authorized disclosure.")
    if routing["primary"] == "switchyard" and routing["model_selection_owner"] != "gateway":
        errors.append("The pilot's Switchyard route must be the sole gateway selector.")
    if routing["primary"] != "switchyard" and routing["model_selection_owner"] != "host":
        errors.append("Fixed/rule selection is host-owned in this pilot.")
    if measurement["usd_cap"] is not None and measurement["cap_enforcement"] != "preadmission_verified":
        errors.append("Observed spend alone must not be advertised as a hard USD cap.")
    return errors


def validate_proof(plan: dict[str, Any], expected: dict[str, str],
                   proof: dict[str, Any]) -> list[str]:
    """expected는 실제 구현에서 trusted host가 제공해야 한다. fixture는 인증 수단이 아니다."""
    errors = validate_plan(plan) + shape_errors(proof, "proof")
    if errors:
        return errors
    for key in ("base_commit", "candidate_sha256", "acceptance_sha256", "verifier_id"):
        if proof[key] != expected[key]:
            errors.append(f"Host binding mismatch: {key}")
    if proof["policy_sha256"] != fingerprint(plan):
        errors.append("Stale or different policy fingerprint.")
    if proof["status"] != "passed" or not proof["baseline_passed"]:
        errors.append("Only a fully passed verification of a healthy baseline can be handed off.")
    for check in plan["verification"]["required_checks"]:
        if proof["checks"].get(check) != "passed":
            errors.append(f"Missing or unsuccessful required check: {check}")
    if any(status != "passed" for status in proof["checks"].values()):
        errors.append("The bundle contains failed or skipped checks.")
    usage = proof["usage"]
    if usage["status"] == "unknown" and usage["total_usd"] is not None:
        errors.append("Unknown usage cannot be silently replaced with a numeric cost.")
    if usage["status"] == "measured" and usage["total_usd"] is None:
        errors.append("Measured usage needs a numeric cost.")
    return errors


def main() -> int:
    plan = strict_load(ROOT / "examples/v0.2/pilot.json")
    bundle = strict_load(ROOT / "examples/v0.2/proof-fixture.json")
    errors = validate_proof(plan, bundle["expected"], bundle["proof"])
    if errors:
        print("\n".join(errors))
        return 1
    print("PASS: synthetic pilot and proof bindings are internally consistent.")
    print("Not executed: models, commands, real tests, authentication, sandboxing, recovery.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
