"""A1의 공개된 초안을 합성 없이 내보낸다. 모델 호출·합의 판정·상태 전이는 없다.

입력은 controller.view()의 사본만 받는다. 공개 권한은 controller가 정하며, 이 함수는 그 권한을 만들지 않는다.
초안과 입력 원문이 들어가므로 내려받은 보고서는 민감한 사용자 자료다. 저장소에 자동으로 올리지 않는다.
이 원문 전용 보고에는 모의 합성 결과를 포함하지 않는다. 결정 보고서는 이 원문과 모의 결과를 함께 묶는다.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any
from app import revisions

# 3: 참여자마다 시도에 저장한 실행 종류(execution)를 싣고, 출처의 "지금 붙은 실행기"는 뺐다(G6).
# 4: 입력에 실행을 만들 때 고정한 공통 자료 목록(이름·sha256·크기)을 싣는다. 자료 내용은 원장에만 둔다.
# 5: 공개 뒤 교차검토(cross_review, 카드 #152)를 싣는다 — 검토 질문, 검토자마다의 상태와 지적(대상·인용·원문 일치·
#    종류·설명), 사람이 고른 처분과 시각, 검토하지 않은 관계, 독립 아님. 검토자 지시문 전문은 싣지 않고 해시만 싣는다.
SCHEMA = "a1-draft-report/5"
# 공개 투영에 나중에 필드가 늘어도 원장·토큰·자유 메타데이터를 통째로 내보내지 않는다.
PARTICIPANT_FIELDS = ("pid", "label", "provider", "transport", "independence", "state", "status", "dropped",
                      "contamination", "execution")
OBSERVATION_FIELDS = ("state", "exit_code", "containment", "tree_confirmed_empty", "input_delivery", "duration_ms",
                      "status", "ok", "requested_model", "reported_models", "model_match", "usage", "source",
                      "marker_echo", "user_confirmed", "independence")
QUORUM_FIELDS = ("policy", "min", "confirmed", "unverified", "counted", "met", "label")
REVIEW_FIELDS = ("seq", "state", "status", "execution", "reviewer", "labels", "input_sha256", "reason")
FINDING_FIELDS = ("target", "target_pid", "quote", "source_check", "kind", "detail", "disposition", "disposition_at")


# 결정 보고의 판. 2: synthesis는 모의(a1-mock-synthesis/1) 또는 실제(a1-model-synthesis/1)이고 그 schema로 가른다.
# 3: 실패한 실제 합성을 failed_model_synthesis로 따로 실었다. 4: 실행마다 실제 합성을 여러 번 할 수 있어
# model_syntheses에 모든 시도를 순서대로 싣는다(시도 ID·상태·결과, 실패면 이유와 검사 실패한 원문 raw).
# 5: 실행에 묶인 모델 호출의 토큰 합계(usage, 카드 #141)를 싣는다. provider별로 나눠 더하고 캐시로 읽은 몫을 따로
# 보이며, 값이 없는 호출은 "관측 안 됨"으로 센다. 정가 추정은 청구액이 아니다(app/usage.py).
DECISION_SCHEMA = "a1-decision-report/5"


class ReportError(ValueError):
    """아직 보고할 수 없거나 공개 자료가 불완전하다. 봉인 자료를 대신 읽지 않는다."""


def build_report(view: dict[str, Any], run_id: str) -> dict[str, Any]:
    """controller의 공개 투영에서 선택한 실행만 내보낸다. 질문/초안을 요약하거나 고쳐 쓰지 않는다."""
    run = next((r for r in view["runs"] if r["run_id"] == run_id), None)
    if run is None:
        raise ReportError("no such run")
    if run["phase"] != "revealed" or any(p["state"] not in ("accepted", "rejected") for p in run["participants"]):
        raise ReportError("report requires controller-revealed, settled drafts")
    data = run["prompt"].encode("utf-8")
    if hashlib.sha256(data).hexdigest() != run["input_sha256"] or len(data) != run["input_bytes"]:
        raise ReportError("fixed input does not match its recorded digest or size")
    participants = []
    for part in run["participants"]:
        item = {key: deepcopy(part[key]) for key in PARTICIPANT_FIELDS}
        if part["state"] == "accepted":
            text = part.get("draft")
            if not isinstance(text, str) or not text.strip():
                raise ReportError("an accepted participant has no public draft")
            item["draft"] = text
            item["draft_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if item["draft_sha256"] != part.get("draft_sha256"):
                raise ReportError("public draft does not match its sealed digest")
        observation = part.get("result") or {}
        item["observation"] = {key: deepcopy(observation[key]) for key in OBSERVATION_FIELDS if key in observation}
        participants.append(item)
    budget = run["budget"]
    return {
        "schema": SCHEMA,
        "disposition": "report_without_synthesis",
        "source": {"run_id": run_id, "created_at": run["created_at"], "phase": run["phase"]},
        "input": {"question": run["question"], "prompt": run["prompt"], "sha256": run["input_sha256"],
                  "bytes": run["input_bytes"],
                  "sources": [{key: item[key] for key in ("name", "sha256", "bytes")} for item in run.get("sources", [])]},
        "quorum": {key: deepcopy(run["quorum"][key]) for key in QUORUM_FIELDS},
        "reduction_approved": run["reduction_approved"],
        "synthesis": {"status": "not_included", "additional_model_calls": 0},
        "verification": {"status": "not_performed", "agreement_is_verification": False},
        "accounting": {"scope": "this_run_cli_attempts_only", "account_remaining": "unknown",
                       "client_estimates_are_invoices": False,
                       "attempts": {key: deepcopy(budget[key]) for key in ("used", "cap", "breakdown", "manual")}},
        "participants": participants,
        "cross_review": _cross_review(run.get("cross_review")),
        "limitations": ["This draft-only export omits synthesis and recommendations; factual verification was not performed.",
                        "Cross-review findings were written after seeing other answers; they are not independent and "
                        "quote matches do not verify facts.",
                        "Checksums detect content changes; they do not prove truth, authorship or independence.",
                        "Manual-app context, independence and account-wide remaining usage are not observed.",
                        "Mock/synthetic execution is not evidence of real model quality or entitlement."],
    }


def _cross_review(round_: dict[str, Any] | None) -> dict[str, Any] | None:
    """화면 투영의 교차검토를 그대로 옮긴다. 새로 판정하지 않는다. 판독 실패·종료 미확인·시작 안 함은 state·status로
    남고 findings는 None이다 — "지적 없음"(통과한 빈 목록)과 섞이지 않는다."""
    if not round_:
        return None
    reviews = []
    for review in round_["reviews"]:
        item = {key: deepcopy(review.get(key)) for key in REVIEW_FIELDS}
        item["targets"] = {label: {"pid": t["pid"], "sha256": t["sha256"], "fresh": t["fresh"]}
                           for label, t in review["targets"].items()}
        reply = review.get("reply")
        item["findings"] = None if reply is None else [{key: deepcopy(f.get(key)) for key in FINDING_FIELDS}
                                                       for f in reply["findings"]]
        item["checks"] = deepcopy(reply["checks"]) if reply else None
        reviews.append(item)
    return {"question": round_["question"], "independence": round_["independence"],
            "factual_check": "not_performed", "coverage": deepcopy(round_["coverage"]), "reviews": reviews}


def decision_report(run: dict[str, Any], draft_report: dict[str, Any]) -> dict[str, Any] | None:
    """결정 보고. 합성이 하나도 없으면 None이다. 서버(`/decision-report`)와 헤드리스 실행(`app.run`)이 같이 쓴다.

    synthesis는 가장 최근에 끝난 합성(모의 또는 실제)이고, model_syntheses는 실제 합성 시도 전부다.
    결과는 사실 검증이 아니며 원문(draft_report)을 함께 싣는다.
    """
    synthesis = run.get("synthesis")
    attempts = run.get("model_syntheses") or []
    if synthesis is None and not attempts:
        return None
    return {"schema": DECISION_SCHEMA, "draft_report": draft_report, "synthesis": synthesis,
            "model_syntheses": attempts, "usage": run.get("usage")}


def revision_report(view, run_id):
    """Separate post-review history; legacy draft/synthesis inputs stay immutable."""
    original = build_report(view, run_id)
    run = next(r for r in view['runs'] if r['run_id'] == run_id)
    drafts = {p['pid']: p for p in original['participants'] if p['state'] == 'accepted'}
    prior, variants = {}, []
    for v in run.get('answer_revisions', []):
        source = v['snapshot']
        initial = drafts.get(v['pid'], {})
        base = prior.get(v['parent_id']) if v['parent_id'] else {'answer': initial.get('draft'), 'sha256': initial.get('draft_sha256')}
        if (revisions.digest(revisions.encoded(source)) != v['snapshot_sha256'] or
                revisions.digest(v['prompt']) != v['input_sha256'] or not base or
                source['original'] != {'text': initial.get('draft'), 'sha256': initial.get('draft_sha256')} or
                source['base'] != {'revision_id': v['parent_id'], 'text': base['answer'], 'sha256': base['sha256']}):
            raise ReportError('revision input or parent digest mismatch')
        if v['reply']:
            if revisions.digest(v['reply']['answer']) != v['reply']['sha256']:
                raise ReportError('revision answer digest mismatch')
            prior[v['revision_id']] = v['reply']
        for check in v['rechecks']:
            if (not v['reply'] or check['answer_sha256'] != v['reply']['sha256'] or
                    revisions.digest(check['prompt']) != check['input_sha256']):
                raise ReportError('recheck input digest mismatch')
        # Explicit new schema; no future projection fields leak into this export.
        variants.append({k: deepcopy(v[k]) for k in ('revision_id', 'pid', 'parent_id', 'created_at', 'state', 'status',
            'snapshot', 'snapshot_sha256', 'input_sha256', 'author', 'execution', 'reply', 'reason', 'raw', 'rechecks')})
    return {'schema': 'decision-revision-history/1', 'draft_report': original, 'revisions': variants,
            'human_judgment': {'reviewed': run['reviewed'], 'memo': run.get('review_memo')},
            'factual_check': 'not_performed', 'independence': 'post_reveal_not_independent',
            'synthesis_scope': 'original_drafts_only'}
