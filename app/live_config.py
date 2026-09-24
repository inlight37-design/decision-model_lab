"""작은 명시적 live 설정. 자동 provider/model/funding 대체나 원격 설정은 없다."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Provider:
    adapter_id: str
    model: str
    inventory: Path
    call_budget: int
    input_dir: Path | None = None

    def __post_init__(self) -> None:
        if (self.adapter_id not in ("claude-code", "codex") or not isinstance(self.model, str)
                or not self.model.strip() or not isinstance(self.inventory, Path)
                or type(self.call_budget) is not int or not 1 <= self.call_budget <= 10
                or (self.input_dir is not None and not isinstance(self.input_dir, Path))):
            raise ValueError("provider needs supported adapter, full model, inventory path and call_budget 1..10")


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
        if not isinstance(row, dict) or not required <= set(row) or set(row) - required - {"input_dir"}:
            raise ValueError("invalid provider fields")
        row = dict(row)
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
