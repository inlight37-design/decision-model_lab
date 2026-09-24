"""서버 연결 전 현재 참여자 계획의 허가를 조회한다. CLI·모델·원장을 실행하거나 열지 않는다."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import tempfile

from app.cli_executor import CliExecutor, installed_version, REFUSED_BEFORE_START
from app.controller import CLI, ParticipantSpec
from core import eligibility, isolation


def check(adapter_id: str, model: str, inventory: Path, data_dir: Path) -> dict:
    """현재 서버용 계획(자료 없음)을 만든 뒤 설치 버전·관측 기록을 대조한다. 실행 함수는 호출하지 않는다.

    허가된 경우에도 실행 승인이나 예산을 만들지 않는다. 이 결과는 조회 시점의 스냅샷이며,
    실제 실행기는 plan/run에서 다시 검사한다. 프로세스를 만들지 않으므로 인증 갱신도 하지 않는다.
    """
    result = {"mode": "readiness_only", "model_calls": 0, "adapter_id": adapter_id,
              "requested_model": model, "eligible": False, "revision": None,
              "installed_version": None, "isolation_execution": "not_tested", "reasons": []}
    if adapter_id not in CliExecutor.adapter_ids or not model.strip():
        result["reasons"] = ["supported adapter and full model name are required"]
        return result
    if sys.platform != "linux":
        result["reasons"] = ["real participants require Linux/WSL; use the WSL-native installation"]
        return result
    try:
        record = eligibility.load(inventory)
    except (OSError, ValueError):
        result["reasons"] = ["cannot read a runtime-inventory/2 record"]
        return result
    # 관측 조회만: 허가 거절 전에도 정확한 판과 모든 거절 이유를 표시한다.
    # unchecked 실행기를 서버 Controller에 넘기지 않으며 이 모듈에는 run() 경로가 없다.
    executor = CliExecutor(never=(str(data_dir.resolve()),), unchecked=True)
    spec = ParticipantSpec(adapter_id, adapter_id, adapter_id, CLI, adapter_id, model)
    try:
        isolation._trusted_bwrap()  # 바이너리 존재·소유/쓰기 권한만 검사; namespace 생성은 실행 때 확인
        with tempfile.TemporaryDirectory(prefix="dml-readiness-") as work:
            plan = executor.plan(spec, "readiness check; never sent to a model", work)
            isolation.plan(plan.spec.argv, plan.box)  # 경로/격리 설정 검사만; 프로세스 생성 없음
            result["revision"] = plan.revision
            result["installed_version"] = installed_version(adapter_id, plan.spec.argv[0])
        verdict = eligibility.eligibility(record, adapter_id, enabled=True, today=date.today(),
                                          current_version=result["installed_version"],
                                          spec_revision=result["revision"])
    except (*REFUSED_BEFORE_START, OSError) as exc:
        # 로컬 경로·환경 값을 출력하지 않는다. 상세 진단은 별도 관측 도구의 가림 정책을 쓴다.
        result["reasons"] = [f"cannot prepare the isolated participant plan ({type(exc).__name__})"]
        return result
    result.update(eligible=verdict.eligible, reasons=list(verdict.reasons))
    return result
