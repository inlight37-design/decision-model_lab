"""실행 허가(eligible_for_run)를 실행 직전에 계산한다(PR #4 R02·R05, 인계 4절 N4). 표준 라이브러리만 쓴다.

기록(manifest `runtime-inventory/2`)은 한 기기의 CLI마다 관측을 다섯 칸으로 나눈다.
  installed               설치와 버전
  auth_observed           격리 안에서 본 로그인 방식과 과금 경로
  transport_observed      비대화형 구조화 출력이 격리 안에서 끝까지 도는가(tier 2 P1)
  context_conformance     참여자 문맥에 사용자 지시문·메모리·다른 참여자 정보가 실리지 않는가(B1·B2)
  permission_conformance  금지한 읽기·쓰기가 실제로 거절되는가(B1·B2)
각 칸은 status(unknown | observed | failed)와, 관측했으면 observed_at·evidence를 갖는다. failed는 "관측했더니 조건을
못 맞췄다"는 뜻이고 unknown과 다르다. 허가는 기록에 저장하지 않는다 — 실행할 때마다 기록·정책·날짜·지금 설치된
버전으로 다시 계산한다. 기록에 `configured: true`가 있다고 허가하지 않는다.

허가 조건: 다섯 칸이 모두 observed이고 max_age_days 안에 관측했다. 지금 설치된 버전이 기록한 버전과 같다. 로그인이
구독이다(API 과금은 명시적 opt-in만, 2절 6). 그 CLI를 켜 두었다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "runtime-inventory/2"
FIELDS = ("installed", "auth_observed", "transport_observed", "context_conformance", "permission_conformance")
STATUSES = ("unknown", "observed", "failed")
SUBSCRIPTION_AUTH = ("subscription_oauth", "chatgpt_login", "google_account_login")


@dataclass(frozen=True)
class Verdict:
    eligible: bool
    reasons: tuple[str, ...]   # 허가하지 않은 이유. 허가했으면 비어 있다


def load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def eligibility(manifest: Mapping[str, Any], adapter_id: str, *, enabled: bool, today: date,
                current_version: str | None, max_age_days: int = 30, allow_api: bool = False) -> Verdict:
    """이 기록으로 지금 이 CLI를 참여자로 불러도 되는가. 이유를 모두 모아 돌려준다."""
    if not isinstance(manifest, Mapping) or manifest.get("schema") != SCHEMA:
        return Verdict(False, (f"the record is not {SCHEMA}",))
    rows = manifest.get("adapters")
    row = next((a for a in rows if isinstance(a, Mapping) and a.get("adapter_id") == adapter_id), None) \
        if isinstance(rows, list) else None
    if row is None:
        return Verdict(False, (f"{adapter_id} is not in the record",))
    reasons: list[str] = []
    if not enabled:
        reasons.append(f"{adapter_id} is turned off")
    for field in FIELDS:
        entry = row.get(field)
        status = entry.get("status") if isinstance(entry, Mapping) else None
        if status != "observed":
            reasons.append(f"{field} is {status or 'missing'}")
            continue
        try:
            age = (today - date.fromisoformat(str(entry.get("observed_at", ""))[:10])).days
        except ValueError:
            reasons.append(f"{field} has no valid observed_at")
            continue
        if age > max_age_days:
            reasons.append(f"{field} was observed {age} days ago (limit {max_age_days})")
    installed = row.get("installed") if isinstance(row.get("installed"), Mapping) else {}
    recorded = installed.get("version")
    if installed.get("status") == "observed" and recorded != current_version:
        reasons.append(f"installed version {current_version or 'unknown'} differs from the recorded {recorded}"
                       " — observe again")
    auth = row.get("auth_observed") if isinstance(row.get("auth_observed"), Mapping) else {}
    if auth.get("status") == "observed" and not allow_api and (
            auth.get("auth_mode") not in SUBSCRIPTION_AUTH or auth.get("funding_mode") != "subscription"):
        reasons.append("the login is not a subscription; API billing needs an explicit opt-in")
    return Verdict(not reasons, tuple(reasons))
