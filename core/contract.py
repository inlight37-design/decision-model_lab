"""실행 계약(인계 순서 5, 구조 검사 G4·G6). 한 시도의 최종 계획을 한 번 만들고, 기록과 실행에 같은 객체를 쓴다.

- 계획(Plan)은 최종 argv(관측 변형 포함)·입력·격리 경계·요청 모델·stderr 표식·실행 종류를 고정한다. 실행기는
  계획을 다시 만들지 않는다. controller는 계획의 기록을 시도 ID와 함께 저장한 뒤에만 그 계획을 실행한다.
- 판(revision)은 실행 틀의 지문이다. 실행 파일 경로·모델 이름·HOME·자료 경로·질문처럼 시도마다 달라지는 값은
  역할로 바꾸고, 출력 형식·도구·권한 profile·세션 보존·연결 역할과 ro/rw처럼 실행 의미가 다른 것은 남긴다.
  같은 틀이면 같은 판이다. 기록(runtime-inventory/2)의 전송·문맥·권한 관측은 판에 묶이고(core.eligibility),
  판이 다르면 다시 관측한다. 관측 도구의 변형(stream-json, 세션 보존)도 판을 바꾼다 — 변형으로 본 관측이
  참여자 계획의 근거가 되지 않는다.
- 옛 이름 판(discussant-1/2)은 자동으로 새 판이 되지 않는다. 최종 argv와 연결을 대조해 같은 계획임을 확인한
  것만 LEGACY에 적는다.
- 실행 종류(mock/real/synthetic)는 계획에 있고 controller가 시도 행에 저장한다. 화면·보고는 저장한 값을 읽는다.
  지금 controller에 붙은 실행기로 과거 시도의 출처를 짐작하지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable

from core import adapters, isolation

MOCK, REAL, SYNTHETIC = "mock", "real", "synthetic"
KINDS = (MOCK, REAL, SYNTHETIC)

# 옛 이름 판 → 같은 계획으로 확인한 판. 기록의 spec_revision이 옛 이름이면 여기에 적은 판에서만 인정한다.
# - codex discussant-2: K46 확인(2026-09-24, argv_changes 없음)이 돈 계획 — 참여자 argv 그대로, 공통 자료 하나를
#   읽기 전용으로 연결. 자료 없는 계획은 연결이 하나 적을 뿐이지만 같은 계획이 아니므로 적지 않았다.
# - claude-code discussant-1은 포괄적 이름이며 예전 진단과 참여자 구분이 없었다. stream-json을 참여자에
#   채택한 뒤에도 자동 대응시키지 않는다. 정확한 새 해시로 다시 관측한 기록만 사용한다.
LEGACY: dict[str, tuple[str, ...]] = {"discussant-2": ("codex@8a0128d4c791",)}


@dataclass(frozen=True)
class Plan:
    """한 시도의 최종 실행 계획. box가 None이면 격리 없이(Windows 모의) work_dir에서 돈다."""
    kind: str
    spec: adapters.ExecutionSpec
    work_dir: str
    box: isolation.Sandbox | None
    model: str
    stderr_marks: tuple[str, ...] = ()
    revision: str = ""
    template: dict[str, Any] | None = None
    changes: tuple[str, ...] = ()   # 관측 도구의 변형이 참여자 argv에서 바꾼 것
    context_unverified: bool = False  # 실행 허가 정책. argv 판과 별도로 보존하며 독립 정족수에 세지 않는다.

    def record(self) -> dict[str, Any]:
        """journal·관측 요약에 남길 사본. 질문 본문은 넣지 않는다(ExecutionSpec.record())."""
        return {**self.spec.record(), "kind": self.kind, "revision": self.revision, "model": self.model,
                "template": self.template, "changes": list(self.changes),
                "context_unverified": self.context_unverified}


def template(spec: adapters.ExecutionSpec, box: isolation.Sandbox | None, *, home: str,
             inputs: Iterable[str] = (), stderr_marks: Iterable[str] = ()) -> dict[str, Any]:
    """판을 정하는 실행 틀. 시도마다 달라지는 값은 역할 이름으로 바꾼다."""
    home, inputs = home.rstrip("/"), set(inputs)
    argv = []
    for i, token in enumerate(spec.argv):
        previous = spec.argv[i - 1] if i else None
        if i == 0:
            token = "<exe>"
        elif previous == "--model":
            token = "<model>"
        elif previous == "--add-dir":
            token = "<input>"
        elif spec.input_via == adapters.ARGV and hashlib.sha256(token.encode("utf-8")).hexdigest() == spec.input_sha256:
            token = "<prompt>"
        elif home:
            token = token.replace(home + "/", "<home>/")
        argv.append(token)

    def config(path: str) -> str:
        return "rw:~/" + path[len(home) + 1:] if home and path.startswith(home + "/") else "rw:<outside-home>"

    # 역할이 같아도 연결이 늘면 다른 계획이다. set으로 합치면 K46의 자료 하나 관측이 여러 폴더까지 허가한다.
    mounts = ["none"] if box is None else sorted(
        [f"ro:{'input' if p in inputs else 'cli'}" for p in box.read_only]
        + [config(p) for p in box.read_write] + ["rw:work", "tmpfs:home"])
    return {"adapter": spec.adapter_id, "argv": argv, "input_via": spec.input_via,
            "stderr_marks": sorted(stderr_marks), "mounts": mounts}


def revision(tmpl: dict[str, Any]) -> str:
    text = json.dumps(tmpl, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"{tmpl['adapter']}@{hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]}"


def covers(recorded: Any, current: str | None) -> bool:
    """기록의 판이 지금 계획의 판을 뒷받침하는가. 같은 판이거나, 검토해 대응시킨 옛 이름 판일 때만."""
    return (isinstance(recorded, str) and bool(recorded) and bool(current)
            and (recorded == current or current in LEGACY.get(recorded, ())))
