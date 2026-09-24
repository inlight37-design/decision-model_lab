"""Allowlisted account-limit projection shared by runtime and offline experiments."""
import re
from typing import Any

CLAUDE_STATES = ("allowed", "allowed_warning", "rejected")
WINDOW = re.compile(r"[a-z0-9_]{1,40}")
MODEL_ID = re.compile(r"[A-Za-z0-9._:-]{1,80}")
MAX_WINDOWS = 8
MAX_MODELS = 100


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def quota_projection(payload: dict[str, Any] | None, *, observed_at: int,
                     now: int, max_age_s: int = 120) -> dict[str, Any]:
    """Codex account/rateLimits/read의 result를 허용한 화면 행으로 변환한다.

    endpoint를 호출하지 않는다. 문서 지원과 실제 호스트 관측은 다른 사실이다.
    legacy rateLimits와 신규 rateLimitsByLimitId를 합산하지 않는다.
    """
    for value in (observed_at, now, max_age_s):
        require(type(value) is int and value >= 0, "invalid observation time")
    require(observed_at <= now, "future observation")
    freshness = "stale" if now - observed_at > max_age_s else "fresh"
    result = {"scope": "account_limit", "unit": "percent_used", "observed_at": observed_at,
              "freshness": freshness, "status": "unknown", "limits": []}
    if payload is None:
        return result
    require(isinstance(payload, dict), "quota result object required")
    buckets = payload.get("rateLimitsByLimitId")
    if buckets is None or buckets == {}:
        legacy = payload.get("rateLimits")
        buckets = {"legacy": legacy} if legacy is not None else {}
    require(isinstance(buckets, dict), "invalid quota buckets")
    rows = []
    for limit_id, bucket in buckets.items():
        require(isinstance(limit_id, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", limit_id) is not None,
                "invalid identifier")
        require(isinstance(bucket, dict), "invalid quota bucket")
        for window in ("primary", "secondary"):
            data = bucket.get(window)
            require(data is None or isinstance(data, dict), "invalid quota window")
            data = data or {}
            used = data.get("usedPercent")
            # 범위 비교만 쓴다. NaN·무한대도 여기서 떨어지고, math.isfinite와 달리 큰 정수를 float로 바꾸다
            # OverflowError를 내지 않는다(2026-09-25 감사 R1).
            require(used is None or (type(used) in (int, float) and 0 <= used <= 100), "invalid usedPercent")
            duration, reset = data.get("windowDurationMins"), data.get("resetsAt")
            require(duration is None or (type(duration) is int and duration > 0), "invalid window duration")
            require(reset is None or (type(reset) is int and reset >= 0), "invalid reset time")
            expired = reset is not None and reset <= now
            rows.append({"limit_id": limit_id, "window": window, "used_percent": used,
                         "window_minutes": duration, "resets_at": reset,
                         "status": "unknown" if used is None else ("stale" if freshness == "stale" or expired else "observed")})
    result["limits"] = rows
    observed = [row for row in rows if row["used_percent"] is not None]
    if observed:
        result["status"] = "stale" if any(r["status"] == "stale" for r in observed) else "observed"
    return result


def claude_limit(info: Any) -> dict[str, Any] | None:
    """Claude stream-json `rate_limit_event.rate_limit_info`에서 허용한 칸만 남긴다. 모양이 다르면 None.

    문서(Agent SDK의 SDKRateLimitEvent, 2026-09-24 읽음)는 status·resetsAt·utilization(0–1 비율)을 적는다.
    2026-09-23 관측(2.1.280)에는 rateLimitType과 창별 unifiedWindows도 있었다. 결제·크레딧 칸은 버린다.
    """
    if not isinstance(info, dict):
        return None
    status = info.get("status")
    if status is not None and status not in CLAUDE_STATES:
        return None
    unified = info.get("unifiedWindows")
    if unified is not None and (not isinstance(unified, dict) or len(unified) > MAX_WINDOWS):
        return None
    if unified:
        windows = list(unified.items())
    elif info.get("utilization") is not None or info.get("resetsAt") is not None:
        name = info.get("rateLimitType")
        windows = [("current" if name is None else name,
                    {"utilization": info.get("utilization"), "resetsAt": info.get("resetsAt")})]
    else:
        windows = []
    rows = []
    for name, data in windows:
        if not isinstance(name, str) or WINDOW.fullmatch(name) is None or not isinstance(data, dict):
            return None
        used, reset = data.get("utilization"), data.get("resetsAt")
        if used is not None and not (type(used) in (int, float) and 0 <= used <= 1):   # 위 usedPercent와 같은 이유
            return None
        if reset is not None and (type(reset) is not int or reset < 0):
            return None
        rows.append({"window": name, "utilization": used, "resets_at": reset})
    if status is None and not rows:
        return None
    return {"provider": "claude", "status": status, "windows": rows}


def claude_limit_projection(limit: dict[str, Any] | None, *, now: int, max_age_s: int = 120) -> dict[str, Any]:
    """저장한 마지막 Claude 관측(claude_limit + observed_at)을 화면 행으로 바꾼다.

    비율(0–1)을 사용 %로 보일 뿐 Codex의 usedPercent와 더하거나 섞지 않는다. 시계가 거꾸로 가면 오래된 값으로 본다.
    """
    result = {"scope": "account_limit", "unit": "percent_used", "source": "last_real_claude_attempt",
              "observed_at": None, "freshness": None, "status": "unknown", "limit_state": "unknown", "limits": []}
    if limit is None:
        return result
    observed_at = limit.get("observed_at")
    for value in (observed_at, now, max_age_s):
        require(type(value) is int and value >= 0, "invalid observation time")
    stale = observed_at > now or now - observed_at > max_age_s
    result.update(observed_at=observed_at, freshness="stale" if stale else "fresh",
                  limit_state=limit.get("status") or "unknown")
    for window in limit["windows"]:
        used = None if window["utilization"] is None else round(window["utilization"] * 100, 1)
        expired = window["resets_at"] is not None and window["resets_at"] <= now
        result["limits"].append({"limit_id": "claude", "window": window["window"], "used_percent": used,
                                 "window_minutes": None, "resets_at": window["resets_at"],
                                 "status": "unknown" if used is None else ("stale" if stale or expired else "observed")})
    known = [row for row in result["limits"] if row["used_percent"] is not None]
    if known:
        result["status"] = "stale" if any(row["status"] == "stale" for row in known) else "observed"
    return result


def model_ids(payload: Any) -> dict[str, Any]:
    """Codex app-server `model/list` result에서 모델 이름만 남긴다. 이 계정의 가용 목록이지,
    실제로 답한 모델의 보고가 아니다. 표시 이름·설명 같은 다른 칸은 버린다."""
    require(isinstance(payload, dict) and isinstance(payload.get("data"), list), "invalid model list")
    ids = set()
    for entry in payload["data"]:
        if isinstance(entry, dict):
            ids.update(value for value in (entry.get("id"), entry.get("model"))
                       if isinstance(value, str) and MODEL_ID.fullmatch(value) is not None)
    listed = sorted(ids)
    return {"status": "observed", "ids": listed[:MAX_MODELS],
            "truncated": payload.get("nextCursor") is not None or len(listed) > MAX_MODELS}
