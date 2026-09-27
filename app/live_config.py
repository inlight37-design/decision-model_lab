"""작은 명시적 live 설정. 자동 provider/model/funding 대체나 원격 설정은 없다.

역할판에서 고를 수 있는 모델은 provider마다 적은 허용 목록(`choices`)뿐이다(카드 #119, 역할판 B). 각 항목은 과금
경로와 그 근거를 함께 적는다. 고를 수 있는 것은 구독 포함 한도로 확인한 모델(`included`)뿐이고, 추가 크레딧으로
청구될 수 있거나(`credits`) 확인하지 않은(`unconfirmed`) 모델은 이유와 함께 막힌 채로 보인다(검토 근거 O14).
모델을 불러 과금 경로를 알아내지 않고, 모델 목록 조회를 허용 근거로 삼지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
import re

from core.adapters import MODEL

INCLUDED, CREDITS, UNCONFIRMED = "included", "credits", "unconfirmed"
FUNDING = (INCLUDED, CREDITS, UNCONFIRMED)
# 공식 문서상 계정·좌석에 따라 구독 포함 한도가 아니라 usage credits로 청구되고, 비대화형(-p)에서는 청구 확인창도
# 띄우지 않는 모델(https://code.claude.com/docs/en/model-config#fable-and-usage-credits, 역할판 검토 EVIDENCE O14).
# 설정에 무엇이라 적든 추가 크레딧 경로로 본다 — 구독 전용 정책(인계 2절 6·13)에서는 고를 수 없다.
CREDIT_BILLED = {"claude-code": (re.compile(r"(?i)fable"),
                                 "공식 문서: 계정에 따라 구독 포함 한도가 아니라 추가 크레딧(usage credits)으로 청구된다")}


@dataclass(frozen=True)
class ModelChoice:
    """역할판에서 보여 줄 모델 하나. funding이 included일 때만 고를 수 있다. basis는 그렇게 적은 근거다."""
    model: str
    funding: str
    basis: str

    def __post_init__(self) -> None:
        if (not isinstance(self.model, str) or not MODEL.fullmatch(self.model) or self.funding not in FUNDING
                or not isinstance(self.basis, str) or not self.basis.strip()):
            raise ValueError("a model choice needs a full model name, funding (included|credits|unconfirmed) and a basis")

    @property
    def usable(self) -> bool:
        return self.funding == INCLUDED

    def public(self) -> dict:
        return {"model": self.model, "funding": self.funding, "basis": self.basis, "usable": self.usable}


def credit_billed(adapter_id: str, model: str) -> str | None:
    """문서로 추가 크레딧 경로가 알려진 모델이면 그 근거, 아니면 None."""
    billed = CREDIT_BILLED.get(adapter_id)
    return billed[1] if billed and billed[0].search(model) else None


def classified(adapter_id: str, choice: ModelChoice) -> ModelChoice:
    """문서로 추가 크레딧 경로가 알려진 모델은 설정과 상관없이 credits로 둔다."""
    basis = credit_billed(adapter_id, choice.model)
    if basis and choice.funding != CREDITS:
        return replace(choice, funding=CREDITS, basis=basis)
    return choice


def refusal(adapter_id: str, model: str, choices: tuple[ModelChoice, ...] | None) -> str | None:
    """실행 직전의 모델 허가. 지금의 허용 목록에서 고를 수 없는 모델이면 이유, 아니면 None.

    원장에 저장된 명세(다시 연 원장의 대기 시도·저장된 합성자)도 여기서 다시 본다 — 저장할 때의 목록이 아니라
    지금의 목록이 기준이다. choices가 None이면 목록 없이 만든 실행기(준비 조회·시험)라 문서상 추가 크레딧 모델만 막는다.
    """
    basis = credit_billed(adapter_id, model)
    if basis:
        return f"{model} is refused under the subscription-only policy: {basis}"
    if choices is None:
        return None
    choice = next((c for c in choices if c.model == model), None)
    if choice is None:
        return f"{model} is not in the current model allowlist for {adapter_id}"
    return None if choice.usable else f"{model} is not selectable now ({choice.funding}): {choice.basis}"


@dataclass(frozen=True)
class Provider:
    adapter_id: str
    model: str   # 기본 모델. 허용 목록에 구독 포함으로 있어야 한다
    inventory: Path
    call_budget: int
    input_dir: Path | None = None
    # None이면 목록을 주지 않은 예전 설정 — 기본 모델 하나만 고를 수 있다. 목록을 주면 기본 모델도 그 안에 있어야 한다.
    choices: tuple[ModelChoice, ...] | None = None

    def __post_init__(self) -> None:
        if (self.adapter_id not in ("claude-code", "codex") or not isinstance(self.model, str)
                or not self.model.strip() or not isinstance(self.inventory, Path)
                or type(self.call_budget) is not int or not 1 <= self.call_budget <= 10
                or (self.input_dir is not None and not isinstance(self.input_dir, Path))):
            raise ValueError("provider needs supported adapter, full model, inventory path and call_budget 1..10")
        if self.choices is None:
            # 허용 목록 없이 쓴 예전 설정: 기본 모델 하나만 고를 수 있다(지금까지의 동작). 문서상 추가 크레딧 모델은 막는다.
            choices = (classified(self.adapter_id, ModelChoice(self.model, INCLUDED, "설정·시작 인자로 정한 기본 모델")),)
        elif not isinstance(self.choices, tuple) or not all(isinstance(c, ModelChoice) for c in self.choices):
            raise ValueError("model choices must be a tuple of ModelChoice")
        else:
            choices = tuple(classified(self.adapter_id, c) for c in self.choices)
        if len({c.model for c in choices}) != len(choices):
            raise ValueError("model choices must not repeat a model")
        default = self.choice(self.model, choices)
        if default is None:
            # 목록을 주었으면 기본 모델도 근거와 함께 그 안에 있어야 한다 — 목록 밖 모델을 포함으로 끼워 넣지 않는다
            raise ValueError(f"the default model {self.model} is not in the provider's model list")
        if not default.usable:
            raise ValueError(f"the default model {self.model} cannot run under the subscription-only policy: {default.basis}")
        object.__setattr__(self, "choices", choices)

    def choice(self, model: str, choices: tuple[ModelChoice, ...] | None = None) -> ModelChoice | None:
        return next((c for c in (self.choices if choices is None else choices) if c.model == model), None)


def validate(providers: tuple[Provider, ...]) -> tuple[Provider, ...]:
    if (not 1 <= len(providers) <= 2 or not all(isinstance(p, Provider) for p in providers)
            or len({p.adapter_id for p in providers}) != len(providers)):
        raise ValueError("configure one or two distinct providers explicitly")
    if sum(p.call_budget for p in providers) > 10:
        raise ValueError("total live call budget must not exceed 10")
    return providers


def load(path: Path) -> tuple[Provider, ...]:
    """상대 경로는 설정 파일 기준. 오타·미지의 필드·기본값 없는 모델은 거절한다."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {"providers"} or not isinstance(raw["providers"], list):
        raise ValueError("live config must contain only a providers list")
    providers = []
    for row in raw["providers"]:
        required = {"adapter_id", "model", "inventory", "call_budget"}
        if not isinstance(row, dict) or not required <= set(row) or set(row) - required - {"input_dir", "models"}:
            raise ValueError("invalid provider fields")
        row = dict(row)
        if "models" in row:   # 없으면 예전 설정(기본 모델 하나), 있으면 빈 목록이라도 그 목록이 기준이다
            models = row.pop("models")
            if not isinstance(models, list) or any(not isinstance(m, dict) or set(m) != {"model", "funding", "basis"}
                                                   for m in models):
                raise ValueError("models must be a list of {model, funding, basis}")
            row["choices"] = tuple(ModelChoice(**m) for m in models)
        for key in ("inventory", "input_dir"):
            value = row.get(key)
            if key == "input_dir" and value is None:
                continue
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{key} must be a non-empty local path")
            local = Path(value).expanduser()
            row[key] = (local if local.is_absolute() else path.resolve().parent / local).resolve()
        providers.append(Provider(**row))
    return validate(tuple(providers))
