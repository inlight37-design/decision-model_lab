"""Allowlisted account-limit projection shared by runtime and offline experiments."""
import math
import re
from typing import Any


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
            require(used is None or (type(used) in (int, float) and math.isfinite(used) and 0 <= used <= 100),
                    "invalid usedPercent")
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
