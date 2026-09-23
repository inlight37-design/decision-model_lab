"""실행 허가(eligible_for_run)를 실행 직전에 계산한다(PR #4 R02·R05, 인계 4절 N4). 표준 라이브러리만 쓴다.

기록(manifest `runtime-inventory/2`)은 한 기기의 CLI마다 관측을 다섯 칸으로 나눈다.
  installed               설치와 버전
  auth_observed           격리 안에서 본 로그인 방식과 과금 경로
  transport_observed      비대화형 구조화 출력이 격리 안에서 끝까지 도는가(tier 2 P1)
  context_conformance     참여자 문맥에 사용자 지시문·메모리·다른 참여자 정보가 실리지 않는가(B1·B2)
  permission_conformance  금지한 읽기·쓰기가 실제로 거절되는가(B1·B2)
각 칸은 status(unknown | observed | failed)와, 관측했으면 observed_at·evidence를 갖는다. failed는 "관측했더니 조건을
못 맞췄다"는 뜻이고 unknown과 다르다. 참여자 argv로 본 세 칸(전송·문맥·권한)은 그때의 실행 명세 판(spec_revision,
core.adapters.SPEC_REVISION)도 갖는다. 허가는 기록에 저장하지 않는다 — 실행할 때마다 기록·정책·날짜·지금 설치된
버전·지금의 명세 판으로 다시 계산한다. 기록에 `configured: true`가 있다고 허가하지 않는다.

허가 조건: 다섯 칸이 모두 근거와 함께 observed이고, 관측일이 오늘 이전이며 max_age_days 안이다. 지금 설치된 버전을 읽을
수 있고 기록한 버전과 같다. 세 칸의 명세 판이 지금과 같다. 로그인이 구독이다(API 과금은 명시적 opt-in만, 2절 6). 그 CLI를
켜 두었다. 기록 검사기(tools/runtime_inventory.py)와 같은 구조 검사(row_problems)를 쓴다 — 2026-09-24 리뷰 R02가 실행
경로의 검사가 기록 검사기보다 약하다는 것(미래 날짜, 근거 없음, 양쪽 버전 없음)을 보였다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re
from typing import Any, Mapping

from core import adapters

SCHEMA = "runtime-inventory/2"
FIELDS = ("installed", "auth_observed", "transport_observed", "context_conformance", "permission_conformance")
STATUSES = ("unknown", "observed", "failed")
SUBSCRIPTION_AUTH = ("subscription_oauth", "chatgpt_login", "google_account_login")
OBSERVED_AT = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}Z)?")
# 참여자 argv로 관측하는 칸. 그 argv의 판에 묶는다
SPEC_BOUND = ("transport_observed", "context_conformance", "permission_conformance")


@dataclass(frozen=True)
class Verdict:
    eligible: bool
    reasons: tuple[str, ...]   # 허가하지 않은 이유. 허가했으면 비어 있다


def load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def observed_on(entry: Mapping[str, Any]) -> date | None:
    """칸의 관측일. 형식이 틀리거나 없는 날짜(2026-02-30 등)면 None."""
    moment = entry.get("observed_at")
    if not (isinstance(moment, str) and OBSERVED_AT.fullmatch(moment)):
        return None
    try:
        return date.fromisoformat(moment[:10])
    except ValueError:
        return None


def _text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def row_problems(row: Mapping[str, Any]) -> list[str]:
    """한 CLI 기록의 구조 문제. 실행 허가와 기록 검사기가 함께 쓴다. 관측이 사실인지는 보지 않는다."""
    problems: list[str] = []
    for field in FIELDS:
        entry = row.get(field)
        if not isinstance(entry, Mapping) or entry.get("status") not in STATUSES:
            problems.append(f"{field}: status must be one of {', '.join(STATUSES)}")
            continue
        if entry["status"] == "unknown":
            continue
        if not _text(entry.get("evidence")) or observed_on(entry) is None:
            problems.append(f"{field}: {entry['status']} needs a non-empty evidence string "
                            "and observed_at as YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ")
        if field in SPEC_BOUND and not _text(entry.get("spec_revision")):
            problems.append(f"{field}: {entry['status']} needs the spec_revision it was observed with")
    installed = row.get("installed")
    if isinstance(installed, Mapping) and installed.get("status") == "observed" and not _text(installed.get("version")):
        problems.append("installed: observed needs the version")
    return problems


def eligibility(manifest: Mapping[str, Any], adapter_id: str, *, enabled: bool, today: date,
                current_version: str | None, max_age_days: int = 30, allow_api: bool = False,
                spec_revision: str | None = None) -> Verdict:
    """이 기록으로 지금 이 CLI를 참여자로 불러도 되는가. 이유를 모두 모아 돌려준다.

    spec_revision: 지금의 실행 명세 판. 주지 않으면 core.adapters.SPEC_REVISION의 값이다.
    """
    if not isinstance(manifest, Mapping) or manifest.get("schema") != SCHEMA:
        return Verdict(False, (f"the record is not {SCHEMA}",))
    rows = manifest.get("adapters")
    matches = [a for a in rows if isinstance(a, Mapping) and a.get("adapter_id") == adapter_id] \
        if isinstance(rows, list) else []
    if not matches:
        return Verdict(False, (f"{adapter_id} is not in the record",))
    if len(matches) > 1:
        return Verdict(False, (f"{adapter_id} appears more than once in the record",))
    row = matches[0]
    current_spec = spec_revision if spec_revision is not None else adapters.SPEC_REVISION.get(adapter_id)
    reasons: list[str] = []
    if not enabled:
        reasons.append(f"{adapter_id} is turned off")
    for field in FIELDS:
        entry = row.get(field)
        status = entry.get("status") if isinstance(entry, Mapping) else None
        if status != "observed":
            reasons.append(f"{field} is {status or 'missing'}")
            continue
        if not _text(entry.get("evidence")):
            reasons.append(f"{field} is observed without evidence")
        when = observed_on(entry)
        if when is None:
            reasons.append(f"{field} has no valid observed_at")
        elif (today - when).days < 0:
            reasons.append(f"{field} was observed in the future ({entry.get('observed_at')})")
        elif (today - when).days > max_age_days:
            reasons.append(f"{field} was observed {(today - when).days} days ago (limit {max_age_days})")
        if field in SPEC_BOUND and (current_spec is None or entry.get("spec_revision") != current_spec):
            reasons.append(f"{field} was observed with participant spec {entry.get('spec_revision') or 'unknown'};"
                           f" the current spec is {current_spec or 'unknown'} — observe again")
    installed = row.get("installed") if isinstance(row.get("installed"), Mapping) else {}
    recorded = installed.get("version")
    if installed.get("status") == "observed":
        if not _text(recorded):
            reasons.append("the record has no installed version")
        elif current_version is None:
            reasons.append(f"installed version unknown; the record says {recorded} — observe again")
        elif recorded != current_version:
            reasons.append(f"installed version {current_version} differs from the recorded {recorded}"
                           " — observe again")
    auth = row.get("auth_observed") if isinstance(row.get("auth_observed"), Mapping) else {}
    if auth.get("status") == "observed" and not allow_api and (
            auth.get("auth_mode") not in SUBSCRIPTION_AUTH or auth.get("funding_mode") != "subscription"):
        reasons.append("the login is not a subscription; API billing needs an explicit opt-in")
    return Verdict(not reasons, tuple(reasons))
