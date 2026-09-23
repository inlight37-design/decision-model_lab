# decision-model_lab 정밀 검토 — WSL2와 실행 경계

검토일: 2026-09-23 (Asia/Seoul)
검토 기준: `main@d0678f4785f642753b02c039b1fa6bf5622bf0ed`

## 결론

WSL2를 공식 실행 환경으로 삼고 Linux-native CLI/런타임으로 통일하는 방향을 권고한다. 그러나 WSL2 설치 자체를 초안 격리·프로세스 종료·정족수·출력 신뢰성의 해결책으로 취급해서는 안 된다. 권고안은 **Windows UI + WSL2의 Python controller + 실행별 격리 백엔드 하나**다. 기존 runner/adapters/membership의 책임 분리는 유지하되, 각 계층이 보장하는 사실을 명확하게 하고 controller에서 실행 및 결과 수용 조건을 통합한다.

이는 구현·설치 완료 보고가 아니라 검토 제안이다. 사용자 PC 변경, GitHub 쓰기, 외부 모델 호출은 하지 않았다.

## 검토 범위와 증거 수준

GitHub connector로 인계 문서, AGENTS, core의 세 모듈, 관련 테스트, v0.4 설계, aux-pc conformance, UI 경계 실험, 디자인 안내와 대비 테스트, CI 설정/결과를 읽었다. 모든 저장소 파일을 전수 검토하거나 전체 테스트를 이 환경에서 실행한 것은 아니다.

기준 커밋의 GitHub check-runs에서 Python 3.12와 3.13 작업 모두 `completed/success`를 확인했다. CI 설정은 Ubuntu 기반 오프라인 검사다. 이것은 Windows Job object 경로나 실제 CLI/계정/격리 안전성의 검증이 아니다.

이 검토에서 직접 실행한 것은 Linux/Python 3.13.5의 작은 Python 프로세스와 순수 함수 재현이다. aux-pc, 사용자 WSL2, Claude/Codex/agy의 실제 실행은 관측하지 않았다. aux-pc 관련 사실은 저장소의 기존 관측 기록을 읽은 것이다.

### 원본 일치 검증

번들 `snapshot/core/`에는 검토 대상 두 파일만 들어 있다. 전체 저장소가 아니다. 파일 바이트로 Git blob SHA를 재계산해 connector가 준 값과 일치함을 확인한 뒤 재현에 사용했다.

| 파일 | Git blob SHA |
|---|---|
| core/runner.py | `321ffa0359b78fa4216a74603bf3a9a0f40a43db` |
| core/membership.py | `18f41b565a071bd8764132f7684bdbb2ffa224d9` |

## 1. 직접 재현한 발견

### R01 — 종료 확인이 실제 보장보다 강하다 (실제 모델 연결 전 수정)

위치: `core/runner.py`, `_Tree.active()`, `run()`.

POSIX 경로는 `os.killpg(root_pid, 0)`으로 원래 프로세스 그룹의 존재를 확인한다. 자식이 새 세션/그룹으로 이동하고 표준 입출력을 닫으면 원래 그룹은 없어져도 자식은 살아 있을 수 있다.

재현: Python 부모가 `start_new_session=True`로 잠자는 자식을 만든다. 자식의 stdin/stdout/stderr는 DEVNULL이다. 부모가 종료한 뒤 runner는 `state=exited`, `tree_confirmed_empty=true`를 반환했지만 별도의 `/proc` 확인에서 자식이 살아 있었다. 재현기는 그 자식을 종료하고 회수했다.

단순히 문서에 "추적 한계"라고 쓰는 것으로 부족하다. 결과 필드가 실제로 전체 트리 종료를 확정하는 값으로 반환되기 때문이다. 이것을 controller가 신뢰하면 자원 해제나 재시도 판단이 잘못될 수 있다.

권고: 앱이 관리하는 격리 실행 단위를 먼저 만들고 그 안에서 프로세스를 시작한다. 종료도 해당 단위 전체에 대해 수행한다. Linux의 cgroup v2 또는 이를 사용하는 컨테이너/supervisor를 검토하되, worker가 관리 경계 밖으로 프로세스를 옮길 권한을 갖지 않아야 한다. 그 보장이 없는 백엔드는 `process_group_empty`와 `containment_empty`를 구분하고 후자를 추정하지 않는다. cgroup은 파일 격리의 대체물이 아니다.

### R02 — 파이프 정리가 반환을 막는다 (실제 모델 연결 전 수정)

위치: `core/runner.py`, `run()`의 reader join 이후 `stream.close()` (기준 파일 268행).

재현: 별도 세션으로 나간 자식이 stdout/stderr 파이프를 물려받는다. `timeout=2`인 실행이 8초 뒤에도 반환하지 않았고 호출 스레드는 `stream.close()`에 있었다. 읽는 스레드가 사용하는 buffered stream을 동기적으로 닫는 단계가 막힌 것이다. 재현기가 자식을 외부에서 정리한 뒤에야 `unknown`으로 반환했다.

8초 관측만으로 영원히 정지함을 증명했다고 주장하지 않는다. 이 사례는 직접 부모가 종료한 뒤 정리 단계가 자식의 파이프 해제에 의존하며, 정리에도 별도 유한 시간 계약이 필요함을 보인다. 테스트용 자식은 유한 시간 sleep을 사용했다.

권고: 실행 시간과 정리 시간을 구분하고 둘 다 상한을 둔다. nonblocking/asynchronous I/O 또는 명확한 FD 소유권을 갖는 수집 구조로 바꾸고, timeout인 join 뒤에 무제한 close가 이어지지 않게 한다. 컨테이너 도입만으로 해당 Python I/O 코드를 자동 수정했다고 간주하지 않는다.

### R03 — 대체 참여자 수용과 전체 실행 가능 판정이 섞였다 (높음)

위치: `core/membership.py`, `decide(..., "substitute_requested", ...)`.

| 변화 | 독립 인원으로 세는 수 | 필요한 수 | 반환 action |
|---|---:|---:|---|
| A/B/C 중 A 이탈 | 2 | 3 | blocked |
| 이어서 B 이탈 | 1 | 3 | blocked |
| 사전 승인된 D 합류 | 2 | 3 | proceed |

이는 직접 재현했다. controller가 아직 없으므로 실제 앱이 정족수 미달로 모델을 실행했다고 주장하는 것은 아니다. **이 반환값을 전체 실행 허가로 사용하면 위반한다**는 발견이다.

권고: "이 대체자를 명단에 받아도 되는가"와 "실행/공개 단계로 진행해도 되는가"를 별도 판정으로 만든다. 모든 변경 이후 동일한 정족수 규칙을 평가한다. `advance()` 역시 현재는 앞 단계로의 이동만 막고 초안 완료 여부를 검사하지 않으므로, 초안 공개와 합성 진입은 controller의 단계별 gate가 책임져야 한다. 이를 membership의 모든 분기에 제각각 덧대지 않는다.

## 2. 코드 정적으로 확인한 보강점

아래 항목은 이번 번들에서 실제 CLI 출력으로 재현하지 않았다. 런타임 침해 사례로 표현하지 않는다.

### R04 — 출력 파서는 외부 입력을 끝까지 검증하지 않는다

`core/adapters.py::interpret()`는 Claude의 `modelUsage`를 mapping으로 가정해 `.keys()`를 호출하고, Codex의 `item`과 `error`를 mapping으로 가정해 `.get()`을 호출한다. JSON 문법이 맞아도 중첩 값의 타입이 다른 경우 예외가 발생할 수 있다. 실패를 Outcome으로 돌려주는 경계가 필요하다.

또한 Codex의 권한 거절을 저장된 stderr의 특정 문자열로 탐지하면서 `stderr_truncated`는 검사하지 않는다. 거절 진단이 보관 상한 뒤에 있으면 놓칠 수 있는 코드 경로다. 보관할 로그의 길이 제한과 판정에 필요한 이벤트의 수집 완료 여부를 분리한다. 스트림 전체에서 필요한 진단 상태를 모으고, 증거가 불완전하면 정상 수용하지 않는다.

`Outcome.ok` 자체는 코드 주석대로 "오류 없이 형식에 맞는 답을 받음"이라는 좁은 의미가 타당하다. 이것을 모델 일치, blind 검증, 입력 동일성 또는 결론 정확성과 혼동하지 않도록 최종 결과 gate를 별도로 둔다.

### R05 — 실행 코어가 조사 도구에 의존한다

`core/adapters.py`가 `tools.runtime_inventory`에서 환경 정책을 가져온다. NEXT-SESSION은 실행 예산/이벤트에 `tools/review_boundary.py`를 연결할 계획이다. 이 두 도구의 성격은 조사·합성 경계 실험이다.

권고: 실행에 사용할 환경·이벤트·예산 규칙을 작은 runtime/domain 모듈로 옮기고, tools가 그 모듈을 사용하도록 의존 방향을 뒤집는다. 과거 실험 포맷을 운영 포맷으로 이름만 바꿔 승격하지 않는다. 마이크로서비스가 필요한 문제는 아니다.

### R06 — 긴 입력 처리의 단위가 argv에 묶였다

`build_argv()`는 질문 본문을 명령줄에 넣으며, Windows용 30,000자 한도를 플랫폼과 무관하게 적용한다. 한도 오류는 파일로 전달하라고 안내하지만, Codex 논의자를 prompt-only로 운영하려는 인계 방향과 맞지 않는다.

권고: `ExecutionSpec(argv, stdin_bytes, cwd, env_profile, isolation_profile)`처럼 실행 옵션과 데이터를 분리한다. Claude programmatic mode의 stdin, Codex `exec -`는 공식 문서에서 확인했다. 설치 버전에서 EOF·큰 한글 입력·선행 대시·입력 전송 실패를 검사해야 하며, stdin도 무제한은 아니다. 프롬프트를 로그용 argv에 보존하지 않고 입력 digest와 바이트 수 등 필요한 메타데이터만 남기는 방향이 낫다.

## 3. WSL2가 해결하는 것과 해결하지 않는 것

WSL2는 Windows 내의 Linux 실행 환경이다. Microsoft 문서상 기본으로 Windows 드라이브를 마운트하고 Windows 실행 파일을 호출할 수 있다. 같은 배포판의 같은 사용자로 모든 작업을 실행하는 것만으로 참여자별 접근 권한이 분리되지는 않는다.

| 항목 | WSL2 이전의 효과 | 추가 조건 |
|---|---|---|
| PowerShell 5.1 경로/문법, Windows 전용 sandbox 선택 문제 | Linux-native CLI 경로로 전환해 해당 의존성을 줄일 수 있음 | Windows exe를 WSL에서 다시 호출하면 목적을 달성하지 못함 |
| MSIX 내부 설치/앱 주입 환경 | 독립 Linux 런타임으로 줄일 수 있음 | 앱 소유 환경/config 정책은 여전히 필요 |
| Claude OS sandbox | Linux/WSL2에서 지원 | 해당 기능은 command-tool sandbox이며 모든 CLI 코드/Read/MCP를 자동으로 감싼다고 해석하지 않음 |
| peer 초안·과거 기록 읽기 | 설치만으로 해결 안 됨 | worker 파일/프로세스/네트워크 경계 필요 |
| 프로세스 종료·정족수·출력 파싱 | 자동 해결 안 됨 | R01–R06 수정 필요 |
| agy 정책 및 구독 한도 의미 | 환경 이전으로 해결되는 문제가 아님 | 기존 사용자 선택/불확실성 유지 |

Claude sandbox를 쓸 경우 실패 시 무샌드박스 실행을 허용하지 않는 설정과 실제 적용 여부를 확인해야 한다. 현재 Claude adapter는 Read만 또는 도구 없음으로 조립하므로 "WSL로 옮겨 Bash sandbox를 켰다"가 현재 Read 경로의 보안 검증을 대체하지 않는다.

### Codex 읽기 금지 연구의 진전

2026-09-23 열람한 공식 설정 문서에는 이름 있는 permission profile의 filesystem `read/write/deny`와, 관리자 `requirements.toml`의 `permissions.filesystem.deny_read`가 있다. 두 설정의 계층은 다르다. 최신 문서가 존재한다는 것과 aux-pc의 정확한 버전/Windows backend에서 기대한 범위로 작동한다는 것은 별개다.

현재 adapter는 `--ignore-user-config` 및 `--sandbox read-only`를 사용한다. 따라서 사용자 config에 deny 설정을 추가하거나 다른 permission 체계를 그대로 섞는 방식은 피하고, 적용 우선순위와 실제 유효 설정을 확인해야 한다. native deny는 방어층으로 유용하지만 CLI 부모가 선로딩하는 문맥, 외부 MCP, 전체 앱 저장소 격리를 모두 대신한다고 가정하지 않는다.

## 4. 권고 구조: 기존 뼈대를 유지하는 모듈식 단일 앱

Windows: 브라우저/화면/사용자 직접 작업.
WSL2: Python controller, 실행 원장, 입력 묶음, 봉인 저장소.
실행 경계: 참여자·시도별 제한된 런타임. 그 안에서 공식 Linux CLI가 구독 인증으로 실행.

첫 격리 백엔드 후보로 rootless 컨테이너를 검토할 수 있다. 목적은 컨테이너라는 이름 자체가 아니라 파일시스템·PID·네트워크·수명 경계의 일관성이다. cgroup/systemd와 namespace 기반 백엔드도 가능하지만 여러 백엔드를 동시에 제품화하지 않는다. 실제 native CLI 로그인/갱신과의 호환성을 확인한 뒤 하나로 정한다. Docker Desktop, Kubernetes, 외부 큐가 필수라는 제안이 아니다.

### 파일 경계

worker에는 승인된 공통 입력, 자기 임시 폴더, 명시한 최소 런타임/인증 상태만 준다. controller의 원장, 다른 참여자의 초안, 지난 실행의 합성, 전체 호스트 HOME, `.git` 안의 비공개 기록, Docker socket, Windows 드라이브, controller 제어 API는 기본 노출하지 않는다. 일부가 업무상 필요하면 명시적인 역할 권한으로 추가한다.

같은 자료를 받았는지는 InputManifest의 digest/버전으로 검사한다. 격리 시험은 금지 자료가 안 읽히는 음성 대조뿐 아니라 허용 자료가 제대로 읽히는 양성 대조도 있어야 한다.

### 봉인과 저장

초안을 메모리에만 두는 계획은 현재 초안 노출을 줄이는 임시 방안이지만 장애 복구와 기록 보존에는 불리하다. controller만 접근할 수 있는 봉인된 영속 저장소에 저장하고, 초안 단계 종료 후 허용된 비교 자료만 새 입력으로 만들어 공개한다. 여기서 필요한 것은 대규모 장기기억 시스템이 아니라 실행 복구용 작은 journal/SQLite와 artifact 저장이다. 해시 고정은 접근 통제를 대신하지 않는다.

### 인증과 환경

Linux에서 공식 CLI로 사용자 로그인/동의를 진행하고, Windows HOME/config/자격증명 폴더 전체를 마운트하는 지름길은 피한다. 인증 갱신을 위한 최소 쓰기 요구를 관측해야 하므로 모든 인증 파일을 무조건 읽기 전용으로 만들라고 지시하지 않는다. 자격증명 값은 prompt/로그/연구 문서에 넣지 않는다. API/유료 크레딧 전환은 기존 opt-in 정책을 유지한다.

### 상태와 예산

controller 한 곳이 실행 가능 여부와 단계 전이를 결정한다. membership 변경 수용, 실행 허가, 초안 공개 허가, 결과 수용 허가를 구분한다. 이벤트에는 run/attempt/epoch/sequence가 필요하며 중복/지연/역순 전달을 처리한다.

누적 호출·시도 상한과 동시 실행 자리는 별개다. 종료 확인 후 동시 실행 자리를 해제할 수 있어도 이미 사용한 호출 상한을 되돌리지 않는다. UNKNOWN은 종료가 확인되지 않은 상태로 유지하며 자동 재호출하지 않는다. 로컬 프로세스 종료가 원격 서버의 생성 중단이나 구독 회계 마감까지 증명하지는 않는다.

## 5. 다른 부분의 평가

유지할 것: native CLI 우선, agy 기본 꺼짐/수동 대안, 유료 fallback 금지, argv와 프로세스 실행 책임의 분리, exit code와 의미 성공 구분, 회복 provider의 다음 run 편입, blind 초안과 반례 보존, 단일 writer, 모델을 더 부르지 않는 상태 표시.

UI: Ledger의 unknown과 관측치를 구분하는 방향은 적절하다. 그러나 봉인 UI 투영은 파일 접근 통제의 대체물이 아니다. `tests/test_design_contrast.py`는 대비 계산과 보고 범위를 검사하며 팔레트 접근성 통과를 보증하지 않는다고 명시한다. 알려진 대비 미달은 실제 화면 수용 기준에서 고친다. Git 소스에서 preview를 단방향 생성하는 흐름이 수동 양방향 동기화보다 유지보수에 유리하다. 실제 화면 렌더링/사용성 전수 평가는 이번에 하지 않았다.

수동 참여: 질문/답에 run·attempt·입력 digest를 연결하고, 늦게 들어온 이전 실행의 답이나 중복 제출을 구분한다. 수동 답의 모델/토큰/도구 사용을 자동 관측한 것처럼 표시하지 않는다. 첫 버전은 복사·붙여넣기만으로 작게 시작해도 된다.

구독 사용량: 기기에서 관측한 토큰/호출/시간과 계정 전체 한도 표시를 분리한 기존 방향을 유지한다. WSL 이전으로 실제 한도가 절약된다고 미리 약속하지 않는다. 재시도와 숨은 도구 루프를 줄인 뒤 같은 작업의 direct/single/cross_check를 승인 범위에서 비교한다.

문서와 개발: 또 하나의 큰 아키텍처 버전이나 여러 orchestration framework를 도입할 필요는 없다. 작은 실행 계약, 회귀 시험, mock controller, 한 번의 실제 conformance 순으로 증거를 쌓는다.

## 6. 제안하는 작업 순서

1. 이번 재현을 회귀 시험으로 옮기고, 격리·종료·정족수·출력 수용의 실행 계약을 고정한다. 기존 오프라인 검사는 보존한다.
2. runtime/domain의 작은 책임 분리, stdin, 오류 파서, 예산/단계 gate를 구현한다. fake CLI를 쓰는 mock UI는 같은 controller 계약 위에서 병행한다.
3. 사용자 승인 후 독립 WSL2 환경에 Linux-native CLI를 준비하고 새 호스트 이름으로 inventory를 남긴다. Windows의 성공 기록을 복사해 성공 처리하지 않는다.
4. 먼저 모델 없이 파일/프로세스/환경/입력 전송 경계를 검사한다. `/mnt/c`, symlink, `/proc`, host socket, controller endpoint 등 허용 범위를 확인한다.
5. 승인된 최소 모델 호출로 허용 읽기·금지 읽기·쓰기·컨텍스트·모델/과금 경로를 확인한다. 그 뒤 single과 cross_check pilot을 진행한다.

실제 모델 호출이 여전히 승인되지 않았다면 1–2 및 모델 없는 준비/시험 범위에서 멈춘다. 설치 역시 이번 검토 요청만으로 실행하지 않는다.

## 7. 재현 번들 사용법

원본 관측은 `results/*.json`에 있다. 아래 명령은 **번들에 들어 있는 기준 커밋의 스냅숏**을 검사한다. 사용자 저장소를 고치거나 현재 설치된 CLI를 실행하지 않는다. 수정한 최신 코드를 검증하는 전체 회귀 스위트가 아니다.

```bash
python membership_probe.py
# 아래 프로세스 시험은 Linux에서만 실행한다.
python runner_probe.py
```

runner 시험은 자기 테스트용 Python 자식을 생성하고 종료한다. 약 8초 동안 파이프 정지 상태를 관측하는 단계가 있다. 프로세스 생성/종료가 허용된 테스트 환경에서 실행한다. 모델 호출, 계정 로그인, 패키지 설치, 네트워크 요청은 하지 않는다. 결과 파일은 재실행 시 덮어쓴다.

## 출처

### 저장소 — 기준 커밋으로 고정

- 인계: https://github.com/inlight37-design/decision-model_lab/blob/d0678f4785f642753b02c039b1fa6bf5622bf0ed/NEXT-SESSION.md
- runner: https://github.com/inlight37-design/decision-model_lab/blob/d0678f4785f642753b02c039b1fa6bf5622bf0ed/core/runner.py
- adapters: https://github.com/inlight37-design/decision-model_lab/blob/d0678f4785f642753b02c039b1fa6bf5622bf0ed/core/adapters.py
- membership: https://github.com/inlight37-design/decision-model_lab/blob/d0678f4785f642753b02c039b1fa6bf5622bf0ed/core/membership.py
- aux-pc 관측: https://github.com/inlight37-design/decision-model_lab/blob/d0678f4785f642753b02c039b1fa6bf5622bf0ed/docs/experiments/v04-03-conformance/aux-pc.md
- UI 경계: https://github.com/inlight37-design/decision-model_lab/blob/d0678f4785f642753b02c039b1fa6bf5622bf0ed/tools/review_boundary.py
- CI 설정: https://github.com/inlight37-design/decision-model_lab/blob/d0678f4785f642753b02c039b1fa6bf5622bf0ed/.github/workflows/checks.yml
- 해당 CI 실행: https://github.com/inlight37-design/decision-model_lab/actions/runs/35830212021
- 디자인 대비 검사: https://github.com/inlight37-design/decision-model_lab/blob/d0678f4785f642753b02c039b1fa6bf5622bf0ed/tests/test_design_contrast.py

### 공식 외부 문서 — 2026-09-23 열람, 문서는 이후 바뀔 수 있음

- Microsoft WSL 설정: https://learn.microsoft.com/en-us/windows/wsl/wsl-config
- Microsoft 파일시스템/상호운용: https://learn.microsoft.com/en-us/windows/wsl/filesystems
- Claude sandbox: https://code.claude.com/docs/en/sandboxing
- Claude programmatic/stdin: https://code.claude.com/docs/en/headless
- Codex config: https://learn.chatgpt.com/docs/config-file/config-reference
- Codex stdin: https://learn.chatgpt.com/docs/non-interactive-mode
- Linux cgroup v2: https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html
- systemd cgroup 관리: https://systemd.io/CONTROL_GROUP_INTERFACE/
- Docker rootless: https://docs.docker.com/engine/security/rootless/

기술 문서의 지원 설명은 설치된 버전의 성공 관측이 아니다. rootless/container/cgroup은 후보 구현과 원리를 설명하기 위한 근거이며, 사용자 PC에서 해당 구성이 동작함을 확인한 것이 아니다.
