# PR #30 실행 계약 재검토 — 2026-09-24

검토 시작 main: `56bf5afcce385b8bec33f118421428af99944534`. 작업 폴더는 `work/repo`, 브랜치는 `codex/cli-readiness-20260924`다. 최신 AGENTS/NEXT-SESSION 및 실행 계약 구현 기록을 읽고, `core/contract.py`, `core/eligibility.py`, `app/cli_executor.py`, controller/store/report와 관련 시험을 검토했다. 실제 모델·인증 파일을 사용하지 않았다.

## 결론

PR #30은 기존 G4의 이중 계획과 G6의 현재 실행기에서 과거 출처를 추측하던 문제를 해결했다. controller는 계획 객체 하나를 기록한 뒤 동일 객체를 worker에 넘기고, 시도 종류를 원장 행에서 읽는다. 다만 실행 직전 허가 확인과 지문 정규화에 재현 가능한 결함이 있어 최소 수정했다. 기존 K46의 단일 자료 계획 지문과 관측 기록은 유지된다.

## 재현하고 수정한 것

### 1. 계획 후 철회된 허가로 실행할 수 있음

- 위치: `app/cli_executor.py`의 `run()`.
- PR #30은 허가 검사를 `plan()`에서만 수행했다. `plan()` 뒤 원장의 permission 관측이 unknown/failed가 돼도 `run(plan)`은 곧바로 `isolation.run()`을 불렀다. controller의 기록/스레드 시작 사이 상태 변경이나, 계획을 먼저 만들어 쓰는 공개 API에서 발생한다.
- 실제 파일로 만든 합성 inventory를 계획 뒤 unknown으로 바꾸는 회귀 시험에서 `isolation.run()` 호출이 발생함을 확인했다. CLI나 모델은 실행하지 않았다.
- 수정: 실행 직전에 같은 계획의 adapter/exe/revision으로 현재 inventory·날짜·설치 버전을 다시 검사한다. argv나 격리 계획을 다시 만들지 않는다. 거절은 기존 `failed_to_start` 경로를 따른다. 공개 API는 바꾸지 않았다.

### 2. Codex 자료 한 폴더와 여러 폴더가 같은 관측 판이 됨

- 위치: `core/contract.py`의 `template()` mount 정규화.
- mount 역할을 set으로 만들면서 `ro:input`의 개수가 지워졌다. `inputs=("/tmp/in",)`과 `inputs=("/tmp/in", "/tmp/other")`가 모두 `codex@8a0128d4c791`이었다. 따라서 단일 자료로 본 K46의 `discussant-2` 대응이 여러 자료 폴더 계획도 뒷받침했다. Claude는 --add-dir 개수 때문에 구별됐지만 Codex는 argv가 같았다.
- 수정: 정렬된 역할 목록으로 개수를 보존했다. 실제 경로값을 역할로 정규화하는 기존 정책은 유지한다. 단일 자료의 기존 지문은 바뀌지 않으며, 추가 폴더 계획에는 K46 대응이 적용되지 않는다.

### 3. stdin 질문이 옵션과 같으면 실행 틀의 옵션이 가려짐

- 위치: `core/contract.py`의 argv 정규화.
- stdin 전송에서도 질문 hash와 같은 argv 토큰을 `<prompt>`로 바꿨다. 정상 `plan(prompt="--ephemeral")`, `prompt="-"`, `prompt="Read"`, `prompt="--restricted"`가 일반 질문과 다른 판을 만들었다. controller의 기본 질문 wrapper 때문에 현재 UI의 직접 영향은 제한되지만 공개 CLI 계획 API의 질문 독립성 계약에 어긋난다.
- 수정: 질문을 argv로 보내는 실행에만 prompt 마스킹을 적용한다. 현재 지원하는 Claude/Codex stdin 경로의 실제 옵션이 지문에 남는다. 정상 기존 지문은 유지된다.
- 같은 원인이 기존 `ExecutionSpec.record()`에도 있어 실제 argv 기록이 질문 표식으로 바뀌었다. 부모의 추가 파일 소유 승인 뒤 `core/adapters.py`에도 동일한 stdin 구분을 적용했다. 대표 정상 입력을 이용한 회귀 시험은 수정 전 실패, 수정 후 성공했다. 기존 argv 전송(agy)의 질문 가림은 유지된다.

## 확인한 보호와 범위

- controller가 plan 또는 record 생성에 실패하면 실제 실행을 시작하지 않는다. 시도 예약과 기록은 같은 거래에서 처리하고, worker는 저장된 계획 객체를 사용한다. thread.start 실패도 시작 전 실패로 처리한다.
- schema 5는 기존 `attempt_started`의 실행기 이름과 해당 행의 attempt ID가 맞을 때만 종류를 복원한다. 모르는 실행기는 NULL을 남긴다. 실행기를 바꿔 controller를 다시 열어도 과거 종류는 행에서 읽는다. 공개 보고서 source에서 현재 실행기 이름을 제거한 변경도 맞다.
- 기존 K46 단일 자료 지문 `codex@8a0128d4c791`은 그대로다. Claude의 옛 b1 관측을 controller 계획에 자동 대응하지 않는 것도 유지한다. 새로 실제 실행 허가가 나오는 provider를 만들지 않았다.
- `Plan`의 frozen dataclass는 깊은 불변성이 아니다. `template` 및 `Sandbox.env`는 내부 mutable mapping이고, template 지문은 env·시스템 mount/backend 코드 전체를 포함하지 않는다. 현재 `CliExecutor.plan()`은 고정 환경과 표준 연결을 쓰므로, 임의 내부 객체 변조를 정상 사용자 경로의 우회로 취급해 광범위한 방어 계층을 추가하지 않았다. 환경/격리 옵션을 외부에서 설정 가능하게 만들 때에는 그 값과 정책을 계획·판에 포함해야 한다.
- 외부 파일/심볼릭 링크가 검사와 시작 사이 바뀌는 OS 수준 경쟁은 기존 `isolation.py`가 명시한 한계다. 이번 허가 재검사는 계획을 다시 만들거나 그런 경쟁까지 없애는 기능이 아니다.

## 수정 범위·검증

수정한 저장소 파일은 `core/contract.py`, `core/adapters.py`, `app/cli_executor.py`, `tests/test_core_contract.py`, `tests/test_core_adapters.py`, `tests/test_app_cli_executor.py`다. 서버·화면·관측 도구·원장 이전 코드·보고서 코드·manifest는 수정하지 않았다. 커밋/push도 하지 않았다.

- 새 회귀 시험은 모두 수정 전 실패를 확인하고 수정 후 성공했다.
- 관련 시험(core contract, eligibility, app contract, CLI executor, report, runner cancellation): Windows Python 3.12.6에서 43 tests OK/skipped=4(Linux 실제 격리 실행만), WSL Python 3.12.3 및 `DML_REQUIRE_BWRAP=1`에서 43 tests OK/skipped=0.
- 뒤에 추가한 adapter 기록 수정의 관련 전체 시험은 Windows에서 35 tests OK/skipped=0. 추가 수정까지 포함한 최종 Windows/WSL 전체 시험은 부모가 통합 실행한다.
- WSL은 기존 영속 `work/wsl-audit-venv`의 jsonschema 4.26.0 환경을 사용했다. Windows 작업 폴더의 .git 포인터를 위해 `GIT_DIR`·`GIT_WORK_TREE`를 명시했다.
- 로그: `work/order5-focused-windows.log`, `work/order5-focused-wsl.log`, `work/order5-adapters-windows.log`. 임시 시험 harness의 최초 실행은 repo 경로를 sys.path에 넣지 않아 import 실패했으며, harness 수정 뒤 위 결과를 얻었다. 제품 결함으로 세지 않는다.
- `git diff --check` 성공. 최종 통합 트리의 전체 검사·CI는 부모 작업에서 수행한다.
