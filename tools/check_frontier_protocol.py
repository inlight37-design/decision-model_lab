"""합성 완료 기록의 일관성 검사. 모델 실행/진실 판정/보안 강제가 아니다."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


class ProtocolError(ValueError):
    """실험용 기록이 최소 불변식을 위반했다."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolError(message)


def load_record(text: str) -> Any:
    """Reject ambiguous keys and non-standard JSON numbers at the input boundary."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ProtocolError(f"non-standard JSON number: {value}")

    return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)


def indexed(value: Any, label: str) -> dict[str, dict[str, Any]]:
    require(isinstance(value, list), f"{label}: list required")
    result = {}
    for item in value:
        require(isinstance(item, dict), f"{label}: object required")
        key = item.get("id")
        require(isinstance(key, str) and bool(re.fullmatch(r"[A-Za-z0-9_.-]+", key)), f"{label}: invalid id")
        require(key not in result, f"{label}: duplicate id")
        result[key] = item
    return result


def validate(record: Any) -> None:
    """첫 위반에 ProtocolError. 합성 기록만 지원하며 운영 schema가 아니다."""
    try:
        require(isinstance(record, dict), "root: object required")
        # Also catches exponent overflow (1e999) and nonfinite values in extra fields.
        json.dumps(record, allow_nan=False)
        require(record["schema"] == "frontier-record-experiment/0", "unsupported schema")
        require(record["synthetic"] is True, "synthetic records only")
        mode = record["mode"]
        require(mode in ("cross_check", "deliberate"), "unsupported mode")
        funding = record["funding"]
        require(isinstance(funding, dict) and funding.get("mode") == "subscription_only" and funding.get("paid_fallback") is False, "funding policy violation")
        limits = record["limits"]
        for field in ("max_calls", "max_review_rounds"):
            require(type(limits[field]) is int and limits[field] >= 0, f"invalid {field}")
        require(limits["max_calls"] > 0, "empty call budget")
        require(limits["max_review_rounds"] <= (1 if mode == "deliberate" else 0), "pilot round limit")
        required = record["required_participants"]
        require(type(required) is int and required >= 2, "invalid quorum")
        participants = indexed(record["participants"], "participants")
        require(len(participants) == required, "configured quorum mismatch")
        for p in participants.values():
            require(p["quality"] == "frontier", "frontier profile required")
            require(isinstance(p["provider"], str) and p["provider"].strip() == p["provider"] and bool(p["provider"]), "invalid provider")
        require(len({p["provider"].lower() for p in participants.values()}) == required, "distinct providers required")
        digest = record["input_digest"]
        require(isinstance(digest, str) and bool(re.fullmatch(r"sha256:[0-9a-f]{64}", digest)), "invalid input digest")
        drafts = indexed(record["drafts"], "drafts")
        require(len(drafts) == required, "missing draft quorum")
        authors = []
        for d in drafts.values():
            require(d["participant"] in participants, "unknown draft author")
            authors.append(d["participant"])
            require(d["peer_inputs"] == [], "blind pass contaminated")
            require(d["input_digest"] == digest, "input snapshot mismatch")
        require(set(authors) == set(participants), "duplicate or missing draft author")
        calls = indexed(record["calls"], "calls")
        require(0 < len(calls) <= limits["max_calls"], "call budget exceeded")
        require(list(calls.values())[-1]["role"] == "synthesize", "final synthesis missing")
        require(sum(c["role"] == "synthesize" for c in calls.values()) == 1, "ambiguous synthesis")
        available_drafts = set()
        for c in calls.values():
            require(c["participant"] in participants, "unknown caller")
            require(c["role"] in ("draft", "review", "synthesize", "plan", "verify"), "unknown call role")
            require(c["outcome"] in ("succeeded", "failed", "denied", "timeout", "unknown"), "unknown outcome")
            require(type(c["round"]) is int, "invalid round type")
            if c["role"] == "review":
                require(1 <= c["round"] <= limits["max_review_rounds"], "review round exceeded")
                require(len(available_drafts) == required, "review before blind barrier")
                peers = c["peer_draft_ids"]
                require(isinstance(peers, list) and bool(peers) and len(set(peers)) == len(peers), "invalid peer references")
                for peer in peers:
                    require(peer in available_drafts, "dangling peer reference")
                    require(drafts[peer]["participant"] != c["participant"], "self review")
            else:
                require(c["round"] == 0, "non-review round must be zero")
            if c["role"] == "draft" and c["outcome"] == "succeeded":
                draft_id = c["draft_id"]
                require(draft_id in drafts and draft_id not in available_drafts, "invalid draft call link")
                require(drafts[draft_id]["participant"] == c["participant"], "draft call author mismatch")
                available_drafts.add(draft_id)
            if c["role"] == "synthesize":
                require(c["outcome"] == "succeeded" and len(available_drafts) == required, "incomplete synthesis input")
        require(not any(c["outcome"] == "unknown" for c in calls.values()), "unfinished call in completed record")
        if mode == "deliberate":
            reviewers = {c["participant"] for c in calls.values() if c["role"] == "review" and c["outcome"] == "succeeded"}
            require(reviewers == set(participants), "incomplete review coverage")
        claims = indexed(record["claims"], "claims")
        checks = indexed(record["checks"], "checks")
        require(bool(claims), "empty claim ledger")
        checks_by_claim = {claim_id: set() for claim_id in claims}
        for check in checks.values():
            require(check["target"] in claims, "dangling check target")
            checks_by_claim[check["target"]].add(check["id"])
            require(check["status"] in ("passed", "failed", "inconclusive", "denied", "skipped"), "invalid check status")
            require(check["kind"] in ("test", "source", "calculation", "vote", "self_report"), "invalid check kind")
            require(isinstance(check["log_ref"], str) and bool(check["log_ref"].strip()), "missing check log")
        dispositions = ("supported", "qualified", "rejected", "unresolved")
        for claim in claims.values():
            require(claim["disposition"] in dispositions, "invalid claim disposition")
            refs = claim["check_refs"]
            require(isinstance(refs, list) and len(set(refs)) == len(refs), "invalid check refs")
            for ref in refs:
                require(ref in checks and checks[ref]["target"] == claim["id"], "check binding mismatch")
            require(set(refs) == checks_by_claim[claim["id"]], "claim omits declared checks")
            if claim["disposition"] == "supported":
                require(any(checks[r]["status"] == "passed" and checks[r]["kind"] in ("test", "source", "calculation") for r in refs), "unsupported promotion")
                require(not any(checks[r]["status"] == "failed" for r in refs), "unresolved counterevidence")
        report = record["report"]
        for disposition in dispositions:
            ids = report[disposition]
            require(isinstance(ids, list) and len(set(ids)) == len(ids), "invalid report ids")
            expected = {c["id"] for c in claims.values() if c["disposition"] == disposition}
            require(set(ids) == expected, f"report loses or misclassifies {disposition}")
        require(report["status"] in ("qualified", "review_ready"), "invalid report status")
        if report["unresolved"] or report["qualified"]:
            require(report["status"] == "qualified", "unresolved report mislabeled")
    except ProtocolError:
        raise
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise ProtocolError(f"malformed record: {exc}") from exc


def demo() -> dict[str, Any]:
    """전원 합의도 근거 없으면 unresolved로 남는 합성 예시."""
    participants = [{"id": p, "provider": v, "quality": "frontier"} for p, v in zip("ABC", ("openai", "anthropic", "google"))]
    digest = "sha256:" + "0" * 64
    drafts = [{"id": f"draft-{p}", "participant": p, "peer_inputs": [], "input_digest": digest} for p in "ABC"]
    calls = [{"id": f"call-{p}", "participant": p, "role": "draft", "round": 0, "outcome": "succeeded", "draft_id": f"draft-{p}"} for p in "ABC"]
    calls += [{"id": f"review-{p}", "participant": p, "role": "review", "round": 1, "outcome": "succeeded", "peer_draft_ids": [f"draft-{q}" for q in "ABC" if q != p]} for p in "ABC"]
    calls += [{"id": "synthesis", "participant": "A", "role": "synthesize", "round": 0, "outcome": "succeeded"}]
    return {
        "schema": "frontier-record-experiment/0", "synthetic": True, "mode": "deliberate",
        "funding": {"mode": "subscription_only", "paid_fallback": False},
        "limits": {"max_calls": 7, "max_review_rounds": 1}, "required_participants": 3,
        "participants": participants, "input_digest": digest, "drafts": drafts, "calls": calls,
        "claims": [{"id": "c1", "disposition": "supported", "check_refs": ["e1"]}, {"id": "c2", "disposition": "unresolved", "check_refs": [], "votes": 3}],
        "checks": [{"id": "e1", "target": "c1", "kind": "source", "status": "passed", "log_ref": "synthetic://not-real-evidence/e1"}],
        "report": {"status": "qualified", "supported": ["c1"], "qualified": [], "rejected": [], "unresolved": ["c2"]},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", nargs="?", type=Path, help="합성 JSON; 생략하면 내장 예시")
    args = parser.parse_args()
    try:
        record = load_record(args.record.read_text(encoding="utf-8")) if args.record else demo()
        validate(record)
    except (OSError, ValueError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print("PASS: synthetic record consistency only; no model or evidence executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
