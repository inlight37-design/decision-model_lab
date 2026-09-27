"""실행·작업 단위 토큰 합계(카드 #141). 모델을 부르지 않고, controller.view()의 공개 투영만 읽는다.

경제성(수용한 결과 하나당 토큰)을 잴 재료다. 합계는 판정이 아니다.

- **provider끼리 더하지 않는다.** 토큰의 뜻과 셈법이 회사마다 다르다. provider마다 CLI가 보고한 필드 그대로 더한다.
- **캐시로 읽은 몫을 따로 보인다**(Claude `cache_read_input_tokens`, Codex `cached_input_tokens`). 같은 입력을 다시
  읽은 몫이 여기 드러난다. 입력 토큰에 포함되는지는 provider마다 다르므로 빼거나 더하지 않고 그대로 둔다.
- **값이 없으면 0이 아니라 "관측 안 됨"이다.** 원본 앱 수동 참여, 사용량을 보고하지 않은 호출이 그렇다. 시작하지 못한
  시도와 아직 도는 호출은 호출로 세지 않는다.
- **`client_estimate_usd`는 청구액이 아니다.** Claude CLI가 정가로 추정한 값이라 따로 두고 이름에 추정임을 적는다.
- 계정 전역 한도(게이지)와는 다른 층이다. 봉인 중인 실행은 여기 오지 않는다 — controller가 공개 뒤(일반 실행은 처음부터)
  에만 이 합계를 싣는다.
"""
from __future__ import annotations

from typing import Any, Iterable

# provider마다 core.adapters.interpret가 남기는 필드(그 목록과 같이 바꾼다). 표시 순서도 이 순서다.
FIELDS = {"claude-code": ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"),
          "codex": ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"),
          "antigravity": ("input_tokens", "output_tokens", "thinking_tokens", "cache_read_tokens")}
CACHE_READ = {"claude-code": "cache_read_input_tokens", "codex": "cached_input_tokens",
              "antigravity": "cache_read_tokens"}
ESTIMATE = "client_estimate_usd"
NOT_STARTED = ("cancelled_before_start", "process_failed_to_start")


def _number(value: Any) -> bool:
    return type(value) in (int, float) and value >= 0


def calls(run: dict[str, Any]) -> list[dict[str, Any]]:
    """이 실행에 묶인 끝난 모델 호출: [{role, provider(adapter_id 또는 None), usage(dict 또는 None)}].

    참여자, 실제 합성, 다듬기 차례, 분담 제안, 다음 단계 제안, 결과 모으기, 교차검토. 작업의 쓴 호출 수와 같은 범위다."""
    found = []
    for part in run.get("participants", []):
        if part.get("transport") != "cli":
            if part.get("state") == "accepted":   # 원본 앱 답: 사용량을 볼 수 없다
                found.append({"role": "manual", "provider": None, "usage": None})
            continue
        if part.get("state") not in ("accepted", "rejected", "unknown") or part.get("status") in NOT_STARTED:
            continue
        found.append({"role": "participant", "provider": part.get("adapter_id"),
                      "usage": (part.get("result") or {}).get("usage")})
    for attempt in run.get("model_syntheses") or []:
        synthesizer = (attempt.get("result") or {}).get("synthesizer") or {}
        if not synthesizer or synthesizer.get("started") is False:
            continue
        found.append({"role": "synthesis", "provider": synthesizer.get("adapter_id"), "usage": synthesizer.get("usage")})
    refinement = run.get("refinement") or {}
    for turn in refinement.get("turns", []):
        found.extend(_seat("refine", turn, (refinement.get("supervisor") or {}).get("adapter_id")))
    split = run.get("split")
    if split:
        found.extend(_seat("split", split, (split.get("orchestrator") or {}).get("adapter_id")))
    for item in run.get("proposals") or []:
        found.extend(_seat("next_step", item, (item.get("supervisor") or {}).get("adapter_id")))
    for item in run.get("collations") or []:
        found.extend(_seat("collate", item, (item.get("orchestrator") or {}).get("adapter_id")))
    for item in (run.get("cross_review") or {}).get("reviews", []):
        found.extend(_seat("cross_review", item, (item.get("reviewer") or {}).get("adapter_id")))
    return found


def _seat(role: str, item: dict, provider: str | None) -> list[dict]:
    """상위 모델 호출 하나. 시작하지 않았거나 아직 도는 호출은 세지 않는다. 실행 종류는 작업자를 띄우기 전에 적히므로
    그것만으로는 시작했다고 보지 않는다 — 시작하지 못한 상태도 뺀다(Codex 교차검토, PR #151)."""
    if (item.get("execution") is None or item.get("state") in ("running", "queued", "skipped")
            or item.get("status") in NOT_STARTED or (item.get("observation") or {}).get("state") == "failed_to_start"):
        return []
    return [{"role": role, "provider": provider, "usage": (item.get("observation") or {}).get("usage")}]


NOTES = ["provider끼리 토큰을 더하지 않는다", "list_price_estimate_usd는 CLI의 정가 추정이며 청구액이 아니다",
         "계정 전역 한도와는 다른 층이다"]


def _empty(provider: str) -> dict[str, Any]:
    """tokens에는 보고된 필드만 들어간다 — 보고되지 않은 필드를 0으로 채우지 않는다(Codex 교차검토, PR #151)."""
    return {"calls": 0, "observed": 0, "unobserved": 0, "tokens": {}, "cache_read_field": CACHE_READ.get(provider),
            "list_price_estimate_usd": None}


def _add_estimate(entry: dict[str, Any], value) -> None:
    if value is not None:
        entry["list_price_estimate_usd"] = round((entry["list_price_estimate_usd"] or 0) + value, 6)


def total(found: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """호출 목록의 provider별 합계. 서로 다른 provider의 토큰은 더하지 않는다."""
    result = {"by_provider": {}, "unobserved": {"manual": 0, "no_usage_reported": 0}, "notes": list(NOTES)}
    for call in found:
        provider, usage = call["provider"], call["usage"]
        if provider is None:
            result["unobserved"]["manual"] += 1
            continue
        entry = result["by_provider"].setdefault(provider, _empty(provider))
        entry["calls"] += 1
        numbers = {key: value for key, value in (usage or {}).items() if _number(value)}
        _add_estimate(entry, numbers.pop(ESTIMATE, None))   # 정가 추정은 토큰 관측이 아니다
        if not numbers:
            entry["unobserved"] += 1
            result["unobserved"]["no_usage_reported"] += 1
            continue
        entry["observed"] += 1
        for key, value in numbers.items():
            entry["tokens"][key] = entry["tokens"].get(key, 0) + value
    return result


def for_run(run: dict[str, Any]) -> dict[str, Any]:
    return total(calls(run))


def combine(totals: Iterable[dict[str, Any] | None], sealed: int = 0) -> dict[str, Any]:
    """실행 합계들을 작업 하나로 합친다. 봉인 중인 실행은 아직 합계가 없어 sealed_runs로만 센다."""
    result = {"by_provider": {}, "unobserved": {"manual": 0, "no_usage_reported": 0}, "notes": list(NOTES),
              "sealed_runs": sealed}
    for item in totals:
        if item is None:
            continue
        for key in result["unobserved"]:
            result["unobserved"][key] += item["unobserved"][key]
        for provider, entry in item["by_provider"].items():
            into = result["by_provider"].setdefault(provider, _empty(provider))
            for key in ("calls", "observed", "unobserved"):
                into[key] += entry[key]
            for key, value in entry["tokens"].items():
                into["tokens"][key] = into["tokens"].get(key, 0) + value
            _add_estimate(into, entry["list_price_estimate_usd"])
    return result
