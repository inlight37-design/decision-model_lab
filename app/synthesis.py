"""Offline extractive synthesis and source comparison; never a truth verifier.

Only controller-revealed draft reports enter here. Identical excerpts are grouped,
not voted on. All claims remain unresolved until a separate factual check exists.
The complete drafts stay in the source report, including omitted/contrary material.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any
from app.report import SCHEMA as DRAFT_SCHEMA

SCHEMA = "a1-mock-synthesis/1"
MAX_EXCERPTS = 80
MAX_EXCERPT_CHARS = 1200


class SynthesisError(ValueError):
    pass


def _sources(report: dict[str, Any]) -> dict[str, dict]:
    if report.get("schema") != DRAFT_SCHEMA or report.get("source", {}).get("phase") != "revealed":
        raise SynthesisError("synthesis requires a revealed draft report")
    sources = {}
    for part in report["participants"]:
        if part["state"] != "accepted":
            continue
        draft = part["draft"]
        if hashlib.sha256(draft.encode("utf-8")).hexdigest() != part["draft_sha256"]:
            raise SynthesisError("draft digest mismatch")
        if part["pid"] in sources:
            raise SynthesisError("duplicate source participant")
        sources[part["pid"]] = part
    if not sources:
        raise SynthesisError("no accepted drafts")
    return sources


def compare_claims(claims: list[dict], report: dict) -> list[dict]:
    """Validate exact character offsets, run identity and stored digest, not meaning."""
    sources = _sources(report)
    checked = []
    seen = set()
    for claim in claims:
        if claim["id"] in seen or not claim["text"].strip() or not claim["references"]:
            raise SynthesisError("claim needs a unique id, text and source references")
        seen.add(claim["id"])
        for ref in claim["references"]:
            part = sources.get(ref["pid"])
            start, end = ref["start"], ref["end"]
            if (part is None or ref["run_id"] != report["source"]["run_id"]
                    or ref["sha256"] != part["draft_sha256"]
                    or type(start) is not int or type(end) is not int
                    or not 0 <= start < end <= len(part["draft"])
                    or part["draft"][start:end] != claim["text"]):
                raise SynthesisError("claim reference does not match its revealed source")
        checked.append({**claim, "source_check": "exact_match", "disposition": "unresolved",
                        "factual_check": "not_performed"})
    return checked


def mock_synthesize(report: dict) -> dict:
    """A deterministic, bounded UI exercise. No model, majority verdict or semantic inference."""
    sources = _sources(report)
    grouped: dict[str, dict] = {}
    omitted = 0
    # Round-robin preserves representation when a long first draft consumes the display limit.
    excerpts = {pid: iter(re.finditer(r"\S[^\n]*", part["draft"])) for pid, part in sources.items()}
    while excerpts:
        for pid in list(excerpts):
            match = next(excerpts[pid], None)
            if match is None:
                del excerpts[pid]
                continue
            text = match.group().rstrip()
            if len(text) > MAX_EXCERPT_CHARS or (text not in grouped and len(grouped) >= MAX_EXCERPTS):
                omitted += 1
                continue
            claim = grouped.setdefault(text, {"id": f"C{len(grouped) + 1:03}", "text": text, "references": []})
            if any(ref["pid"] == pid for ref in claim["references"]):
                omitted += 1  # A repeated line is not an additional independent source.
                continue
            claim["references"].append({"run_id": report["source"]["run_id"], "pid": pid,
                                        "sha256": sources[pid]["draft_sha256"],
                                        "start": match.start(), "end": match.start() + len(text)})
    claims = compare_claims(list(grouped.values()), report)
    if not claims:
        raise SynthesisError("no comparable excerpts within the display limits")
    unresolved = ["발췌문의 사실 여부·서로 다른 입장의 의미 관계는 확인하지 않았습니다.",
                  "반례와 결론을 뒤집을 조건은 참여자 원문을 함께 검토해야 합니다."]
    if omitted:
        unresolved.append(f"표시 한도·같은 참여자의 반복으로 {omitted}개 줄을 대조표에서 생략했습니다. 전체 원문은 보고서에 보존됩니다.")
    return {"schema": SCHEMA, "status": "completed", "mode": "mock_extractive",
            "additional_model_calls": 0, "source_run_id": report["source"]["run_id"],
            "claims": claims, "comparison": {"method": "exact_text_only", "omitted_lines": omitted,
                                               "agreement_is_verification": False},
            "card": {"question": report["input"]["question"], "status": "qualified",
                     "recommendation": "판단 보류 — 원문 대조와 외부 검증이 필요합니다.",
                     "overturnedBy": ["핵심 주장과 반례를 독립된 근거로 확인하고, 미합의가 결정에 미치는 영향을 해소할 때"],
                     "coverage": {"supported": 0, "rejected": 0, "qualified": 0, "unresolved": len(claims)},
                     "unresolved": unresolved,
                     "nextChecks": ["서로 다른 입장과 반례를 원문에서 확인", "핵심 주장에 외부 근거를 연결해 검사"]}}


def unavailable(report: dict) -> dict:
    """Keep the already-public drafts available when mock synthesis fails."""
    return {"schema": SCHEMA, "status": "unavailable", "mode": "mock_extractive",
            "additional_model_calls": 0, "source_run_id": report["source"]["run_id"],
            "disposition": "report_without_synthesis",
            "message": "모의 합성을 완료하지 못했습니다. 공개된 원문 보고서를 사용할 수 있습니다."}
