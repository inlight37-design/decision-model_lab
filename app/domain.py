"""Stable request values and acceptance policy. No controller, storage or HTTP dependency."""
from __future__ import annotations
from dataclasses import dataclass
import re
from app.state import ACCEPTED, REJECTED, UNKNOWN
from core import adapters, runner

def storable(text: str) -> bool:
    """UTF-8로 저장·해시할 수 있는 글인가. JSON의 올바른 이스케이프(예: "\\ud800")로 들어온 고립 surrogate는
    원장 쓰기·sha256·HTTP 출력에서 모두 실패한다(카드 #70). 정상 보충 평면 문자와 글자 그대로의 \\ud800은 된다."""
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _storable_meta(value):
    """진단 메타데이터(오류 설명·메모·보고 모델 등)의 고립 surrogate를 \\uXXXX 표기로 바꾼다. 봉인하는 초안이
    아니라서 표기를 바꿔도 digest 계약과 무관하다(외부 검토 R05). 바꿨는지는 호출한 쪽이 표시한다."""
    if isinstance(value, str):
        return value if storable(value) else value.encode("utf-8", "backslashreplace").decode("utf-8")
    if isinstance(value, dict):
        return {_storable_meta(k): _storable_meta(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_storable_meta(v) for v in value]
    return value


MARKER = "[Ledger {run_id}/{pid} · {sha8}]"


MARKER_LINE = re.compile(r"^\s*\[Ledger ([^\s/]+)/(\S+) · ([0-9a-f]{8})\]\s*$")


PACKET = ("{marker}\n답의 첫 줄에 위 대괄호 줄을 그대로 옮겨 적어 주세요. 어느 실행의 답인지 확인하는 데만 씁니다.\n\n"
          "{prompt}")


@dataclass(frozen=True)
class ParticipantSpec:
    pid: str
    label: str
    provider: str
    transport: str                  # CLI | MANUAL
    adapter_id: str | None = None   # CLI만
    model: str | None = None
    behavior: str = "ok"            # 모의 CLI의 행동(fake_cli.py)
    context_unverified: bool = False  # 전송 방식이 아니라 저장된 정책으로 정족수를 계산한다.


def packet(run_id: str, pid: str, input_sha256: str, prompt: str) -> str:
    """원본 앱에 옮길 질문. 첫 줄의 실행 표식을 답 첫 줄에 되말해 달라고 적는다(N5)."""
    return PACKET.format(marker=MARKER.format(run_id=run_id, pid=pid, sha8=input_sha256[:8]), prompt=prompt)


def _marker_echo(text: str, run_id: str, pid: str, input_sha256: str) -> tuple[str, str]:
    """답 첫 줄의 실행 표식을 본다. (matched | missing | other_run | other_participant, 표식 줄을 뺀 답).

    표식이 맞다는 것도, 없다는 것도 약한 증거일 뿐이다 — 모델이 되말했는지만 알려 준다. 다른 실행이나 다른
    참여자의 표식이면 다른 카드에 붙여 넣은 것이므로 받지 않는다.
    """
    lines = text.splitlines()
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    found = MARKER_LINE.match(lines[first]) if first is not None else None
    if found is None:
        return "missing", text
    if (found.group(1), found.group(3)) != (run_id, input_sha256[:8]):
        return "other_run", text
    if found.group(2) != pid:
        return "other_participant", text
    return "matched", "\n".join(lines[first + 1:]).strip("\n")


def acceptance(result: runner.RunResult | None, outcome: adapters.Outcome | None) -> tuple[str, str, str | None]:
    """결과 수용 관문. (상태, 상태 코드, controller가 덧붙이는 이유)를 돌려준다. 관측 도구(tools/w2/observe.py)도
    답을 받는 probe에 같은 관문을 쓴다(2026-09-24 리뷰 R03).

    interpret()는 stdin 없는 명령(--version 등)도 해석해야 해서 입력 전달 None을 허용한다. A1은 질문을 늘
    stdin으로 보내므로 끝까지 보낸 기록이 없으면 받지 않는다(A1-02). 질문을 명령줄로 보내는 CLI(agy, K07)를
    붙일 때는 None을 성공으로 넘기지 말고 그 전송 방식의 증거를 따로 정한다.
    """
    if result is None:
        return UNKNOWN, "executor_error", None
    if result.tree_confirmed_empty is not True:
        return UNKNOWN, "unknown", None
    if not outcome.ok:
        return REJECTED, outcome.status, None
    if result.input_delivery != runner.INPUT_COMPLETE:
        return REJECTED, "input_error", "no complete stdin delivery was recorded for this attempt"
    if not (outcome.text or "").strip():
        return REJECTED, "empty_answer", "the CLI returned an empty answer"
    if outcome.model_match is False:
        # 조용한 강등(D18)을 받지 않는다. 별칭으로 요청하면 보고된 전체 이름과 달라 보이므로 요청은 전체 이름으로 한다
        return REJECTED, "model_mismatch", (f"requested {outcome.requested_model}, "
                                            f"reported {', '.join(outcome.reported_models)}")
    return ACCEPTED, outcome.status, None


class ControllerError(ValueError):
    """요청을 받지 않았다. 상태는 바뀌지 않았다."""


class _CapReached(ControllerError):
    """실제 호출 상한에 닿아 시작하지 않았다. 교차검토 라운드는 이 이유로 남은 검토자를 닫는다."""


MAX_MEMO_CHARS = 8000
