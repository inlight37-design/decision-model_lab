"""서버(app.server)와 헤드리스 실행(app.run)이 같은 실행 경로를 쓰게 하는 배선: 참여자 명단, 모의 동작·모델 목록,
provider 설정에서 실행기·명단·전체 상한 만들기, 원장 위에 controller 만들기. 원장과 포트는 여기서 열지 않는다.

두 입구가 서로를 import하지 않도록 여기에 둔다 — 헤드리스 실행이 HTTP 서버 모듈을 끌어오지 않는다.
"""
from __future__ import annotations

import math
from pathlib import Path
import sys

from app.controller import CLI, MANUAL, Controller, MockExecutor, ParticipantSpec
from app.live_config import CREDITS, INCLUDED, UNCONFIRMED, ModelChoice, Provider, validate as validate_providers
from app.store import Store

PARTICIPANTS = {
    "claude": ParticipantSpec("claude", "Claude Code", "anthropic", CLI, "claude-code", "mock-claude"),
    "codex": ParticipantSpec("codex", "Codex", "openai", CLI, "codex", "mock-codex"),
    "chatgpt-app": ParticipantSpec("chatgpt-app", "ChatGPT 앱", "openai", MANUAL),
    "claude-app": ParticipantSpec("claude-app", "Claude 앱", "anthropic", MANUAL),
    "antigravity-app": ParticipantSpec("antigravity-app", "Antigravity", "google", MANUAL),
}
BEHAVIORS = ("ok", "slow", "fail", "partial_input", "hang")
# 모의 모드의 모델 고르기(카드 #119). 모델을 부르지 않고, 가짜 CLI가 고른 이름을 그대로 보고한다. 막힌 두 항목은
# 추가 크레딧·미확인 모델이 화면에서 이유와 함께 막히는 모습을 보이려고 둔다.
MOCK_MODEL_CHOICES = {
    "claude": (ModelChoice("mock-claude", INCLUDED, "모의 — 모델 호출 없음"),
               ModelChoice("mock-claude-large", INCLUDED, "모의 — 모델 호출 없음"),
               ModelChoice("mock-claude-credits", CREDITS, "모의 — 추가 크레딧 경로라서 막히는 모습")),
    "codex": (ModelChoice("mock-codex", INCLUDED, "모의 — 모델 호출 없음"),
              ModelChoice("mock-codex-large", INCLUDED, "모의 — 모델 호출 없음"),
              ModelChoice("mock-codex-unconfirmed", UNCONFIRMED, "모의 — 구독 포함 여부를 확인하지 않아 막히는 모습")),
}
# 준비 조회가 허가하지 않았다. argparse의 인자 오류가 2라서 같은 값을 쓰면 스크립트가 둘을 가르지 못한다(병합 검증 N3).
EXIT_NOT_ELIGIBLE = 3


def pid_of(adapter_id: str) -> str:
    """CLI adapter의 참여자 ID. 명단에서 찾는다 — 모르는 adapter를 다른 참여자로 조용히 바꾸지 않는다."""
    for pid, spec in PARTICIPANTS.items():
        if spec.adapter_id == adapter_id:
            return pid
    raise ValueError(f"no CLI participant runs adapter {adapter_id!r}")


def model_choices(providers) -> dict[str, tuple[ModelChoice, ...]]:
    """화면에서 고를 수 있는 모델. 실제 연결은 provider마다 설정한 허용 목록, 모의는 위의 목록이다."""
    return {pid_of(p.adapter_id): p.choices for p in providers} if providers else MOCK_MODEL_CHOICES


def live_setup(data_dir: Path, *, timeout: float, live_cli: str | None = None, inventory: Path | None = None,
               model: str | None = None, call_budget: int | None = None, allow_context_unverified: bool = False,
               input_dir: Path | None = None, live_providers: tuple[Provider, ...] | None = None):
    """실행기·참여자 명단·provider·전체 상한을 만든다. 원장과 포트는 열지 않는다. 실제 옵션 없이 부르면 모의 실행기다."""
    if live_providers is not None and any(value is not None for value in (live_cli, inventory, model, call_budget, input_dir)):
        raise ValueError("do not mix live_providers with single-provider options")
    providers = validate_providers(tuple(live_providers)) if live_providers is not None else ()
    if live_cli is not None:
        providers = (Provider(live_cli, model, inventory, call_budget, input_dir),)
    if providers:
        from app.cli_executor import CliExecutor
        if sys.platform != "linux" or not math.isfinite(timeout) or not 0 < timeout <= 180:
            raise ValueError("live CLI requires Linux, inventory, full model, call budget 1..10 and timeout 0..180s")
        executor = CliExecutor(never=(str(data_dir.resolve()),), inventory=inventory,
                               inventories_by_adapter={p.adapter_id: p.inventory for p in providers},
                               allow_context_unverified=allow_context_unverified,
                               inputs_by_adapter={p.adapter_id: () if p.input_dir is None else (str(p.input_dir),)
                                                  for p in providers},
                               models_by_adapter={p.adapter_id: p.choices for p in providers})
        roster = {p.pid: p for p in PARTICIPANTS.values() if p.transport == MANUAL}
        for provider in providers:
            pid = pid_of(provider.adapter_id)
            roster[pid] = ParticipantSpec(**{**vars(PARTICIPANTS[pid]), "model": provider.model,
                                            "context_unverified": allow_context_unverified})
        call_budget = sum(p.call_budget for p in providers)
    else:
        if (inventory is not None or model is not None or call_budget is not None
                or allow_context_unverified or input_dir is not None):
            raise ValueError("real options require live_cli; refusing a silent mock fallback")
        executor, roster = MockExecutor(never=(str(data_dir.resolve()),)), PARTICIPANTS
    return executor, roster, providers, call_budget


def new_controller(store: Store, executor, providers, call_budget, *, timeout: float, per_provider: bool) -> Controller:
    """원장 위에 controller를 만든다(재시작 복구 포함). provider별 상한은 설정 파일(--live-config)에서만 온다."""
    return Controller(store, executor, timeout=timeout, max_real_calls=call_budget,
                      provider_call_caps=({p.adapter_id: p.call_budget for p in providers} if per_provider else None),
                      max_parallel=len(providers) if providers else 2,
                      unsettled_limit=len(providers) if providers else 2)
