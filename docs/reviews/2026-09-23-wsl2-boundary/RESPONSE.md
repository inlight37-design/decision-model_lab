# WSL2와 실행 경계 검토 — 반영 기록

작성: claude (Claude Opus 5.5), 2026-09-23. **보조 PC(`aux-pc`)의 로컬 checkout**에서 작업했다. 이 PC에는 WSL이 설치돼 있지 않아서 리뷰의 Linux 재현(`runner_probe.py`)은 돌리지 못했다. 대신 aux-pc(Windows, Python 3.12)에서 아래를 확인했다. 모델과 CLI는 부르지 않았고, 자식 프로세스는 python sleep만 썼으며 모두 정리했다.

- 스냅숏 두 파일의 blob SHA가 `d0678f4`의 `core/runner.py`·`core/membership.py`와 같다(`git hash-object`).
- 순수 함수 재현(R03, R04)을 현재 코드에서 다시 실행했다.
- R02의 원인 메커니즘을 파이프 하나로 따로 재현했다.
- R01·R02와 같은 시나리오를 Windows 경로(job object)에서 실행했다.

리뷰 원문과 재현 묶음은 받은 그대로 두었다. 판정이 갈릴 만한 두 가지(WSL2 채택, 격리 백엔드)는 사용자에게 물었다. 사용자는 WSL2 방향을 확정했고, 백엔드 선택은 이 세션에 맡겼다.

## 발견별 판정

| ID | 판정 | 확인한 것 | 반영 |
|---|---|---|---|
| R01 종료 확인이 과함 | **수용. 범위는 POSIX로 조정** | aux-pc의 Windows 경로는 `DETACHED_PROCESS`로 떨어져 나간 손자도 job에서 세고 끝냈다. 손자의 job 탈출(`CREATE_BREAKAWAY_FROM_JOB`)은 오류 5로 거절됐다. 따라서 **지금 aux-pc 실행에는 영향이 없다.** 그러나 WSL2로 옮기면 POSIX 경로가 운영 경로가 되므로 WSL2 이전의 선행 조건이다 | `RunResult`가 추적 단위(`containment`: `job_object`/`process_group`), 추적 단위가 빈 것(`unit_confirmed_empty`), 자손 전체가 끝난 것(`tree_confirmed_empty`)을 따로 말한다. 프로세스 그룹만으로는 자손 전체를 확인할 수 없어 `None`이다. 자원·예산 반환은 `tree_confirmed_empty`가 True일 때만 한다. 인계 문서 D표의 "트리를 확인 못 하면 unknown"은 사실과 달랐다(실제로는 확인했다고 보고했다) — 원본에서 정정했다 |
| R02 정리가 반환을 막음 | **수용** | 다른 스레드가 `read1()` 중인 buffered stream을 `close()`하면 읽기가 끝날 때까지 막힌다. aux-pc에서 파이프 하나로 재현했다(플랫폼 무관). Windows runner는 job이 파이프를 쥔 손자까지 끝내서 이 상황에 가지 않는다. 다만 job 배정에 실패해 `taskkill`로 넘어가는 경로는 노출돼 있었다 | 읽는 스레드가 EOF에서 스스로 스트림을 닫는다. 합류 시한 뒤에도 살아 있으면 닫지 않고 `unknown`으로 돌려준다. 두 스트림이 합류 시한 하나를 나눠 쓰고, `taskkill`에도 시한을 두었다. 상한은 `runner.CLEANUP_LIMIT`로 공개했다 — `run()`은 `timeout + CLEANUP_LIMIT` 안에 돌아온다. 리뷰가 제안한 nonblocking I/O 재구성은 하지 않았다. 막히는 호출을 없애는 것으로 계약이 서고, 격리 백엔드가 파이프 소유자까지 끝내면 이 경로 자체가 드물어진다 |
| R03 정족수 우회 | **수용하고 범위를 넓힘** | aux-pc에서 재현했다(2/3인데 `proceed`). **리뷰 밖의 같은 구멍:** `cancel_unconfirmed`가 셀 수 있는 인원을 최소 아래로 떨어뜨려도 `keep_unknown`만 돌려줬다(1/2). 단계도 `preflight`에서 `synthesis`로 바로 건너뛸 수 있었다 | `quorum_met()`을 공개했다. 공개 전에는 구성이 바뀔 때마다(이탈·종료 불명·대체) 같은 규칙으로 진행 허가를 다시 정한다. 대체자는 명단에 들어가도 인원이 모자라면 `blocked`다. `advance()`는 한 칸씩만 가고, 초안 단계 진입과 공개에는 정족수가 필요하다. 초안이 실제로 다 들어왔는지는 리뷰대로 controller의 단계 관문이 본다. 기존 시험 두 개가 단계를 건너뛰고 있어 순서대로 고쳤다. UNKNOWN 시험은 최소 3/3에서 2/3으로 바꿨다. 3/3에서 UNKNOWN이 하나 생기면 이제 바로 `blocked`이기 때문이고, 시험의 뜻("UNKNOWN은 세지 않는다")은 그대로다 |
| R04 파서 경계 | **수용** | 리뷰가 든 네 모양이 모두 예외를 던졌다. Codex는 stderr가 잘려도 `ok=True`였다 | `interpret()`가 형식 실패 경계가 됐다. 중첩 값의 타입이 다르면 `format_error`로 돌려준다. Codex `error`가 문자열이면 그 문자열을 사유로 쓴다. stderr가 잘렸으면 Codex 답을 받지 않는다. **남은 것:** 거절 흔적을 보관 상한과 무관하게 스트림 전체에서 세는 일. 2단계의 실행 명세 작업에서 한다 |
| R05 core가 tools에 의존 | **수용, 2단계** | `core/adapters.py`가 `tools.runtime_inventory`에서 환경 규칙을 가져온다 | 환경·이벤트·예산 규칙을 core의 작은 모듈로 옮기고 tools가 그것을 쓰게 한다. `review_boundary.py`의 실험 형식을 운영 형식으로 이름만 바꿔 올리지 않는다 |
| R06 긴 입력이 argv에 묶임 | **수용하고 보강, 2단계** | 코드에서 확인했다 | 인계 A4에 합친다. 실행 옵션과 데이터를 나누고 입력은 stdin으로 준다. Linux에 해당하는 보강 두 가지: 인자 하나가 약 128KiB를 넘으면 실행이 실패한다(`MAX_ARG_STRLEN`). 또 같은 사용자의 다른 프로세스가 `/proc/<pid>/cmdline`에서 프롬프트를 볼 수 있다 |
| §3 WSL2가 해결하는 것 | **수용** | Claude 공식 sandbox 문서를 2026-09-23에 확인했다. sandbox는 Bash·PowerShell·Monitor 명령만 감싸고, Read 등 다른 도구는 권한 규칙이 다룬다. WSL2는 지원하고 WSL1은 지원하지 않는다. 무샌드박스 재시도를 막는 키는 `allowUnsandboxedCommands: false`다. **Ubuntu 24.04 이상은 AppArmor가 bubblewrap의 user namespace를 막을 수 있다** | 4단계 확인 항목에 넣는다 |
| Codex 읽기 금지 설정 | **일부만 확인** | 설정 문서에서 권한 프로필 `permissions.<name>.filesystem`의 `"deny"`는 찾았다. `requirements.toml`의 `permissions.filesystem.deny_read`는 인용된 페이지에서 찾지 못했다 — 미확인 | 우리 adapter는 `--ignore-user-config`를 쓰고 `-c`·`--profile`을 금지한다. 이 설정을 쓰려면 금지 목록부터 바꿔야 한다. 격리의 주 수단으로 삼지 않고 추가 방어층으로만 본다(인계 A3의 우선순위를 낮췄다) |
| §4 권고 구조 | **수용. 백엔드만 조정** | — | 아래 "리뷰와 다르게 정한 것" |
| §5, §6 | **수용** | — | 순서는 아래 "작업 순서" |

## 리뷰와 다르게 정한 것

### 격리 백엔드는 bubblewrap을 먼저 시험한다

리뷰는 rootless 컨테이너를 첫 후보로 들었다. 사용자가 판단을 맡겼고(2026-09-23), 이 세션은 bubblewrap(`bwrap`)을 먼저 시험하기로 정했다. 이유는 다음과 같다.

- **파일 경계.** 참여자와 시도마다 허용한 폴더만 연결(bind)한다. 원장, 다른 참여자의 초안, 지난 실행의 합성, 전체 HOME, `/mnt/c`, 다른 CLI의 인증은 연결하지 않는다.
- **수명 경계.** `--unshare-pid`로 별도 PID 공간을 만든다. 그 공간의 첫 프로세스가 끝나면 커널이 안의 모든 프로세스를 끝내고 회수까지 기다린다. R01이 요구하는 "자손 전체가 끝났다"를 실제로 확인하는 수단이다. 부모가 죽으면 함께 끝나게 `--die-with-parent`도 쓴다.
- **움직이는 부품이 적다.** 데몬, 이미지, 레지스트리가 없다. 설치한 CLI와 로그인 상태를 그대로 연결한다. Claude Code가 Linux·WSL2에서 자기 sandbox로 쓰는 도구와 같다.
- **알고 가는 약점.**
  - 네트워크는 공유한다(모델 API가 필요하다). 그래서 controller 제어 API는 localhost TCP로 열지 않거나, worker에 없는 토큰으로 막는다.
  - 메모리·CPU 상한은 없다. 필요하면 따로 붙인다.
  - bwrap 안에서 Codex의 자체 sandbox가 동작하는지는 4단계에서 확인한다.
- **실패하면 rootless podman으로 간다.** 두 백엔드를 동시에 제품화하지 않는다.

### R01은 두 단계로 닫는다

필드만 정직하게 나누면 Linux의 모든 실행이 "자손 전체 미확인"이 되어 예산 자리를 풀 수 없다. 그래서 순서를 나눈다.

1. 이번 변경은 정직한 계약이다.
2. 4단계에서 bubblewrap의 PID 공간을 추적 단위(`pid_namespace`)로 붙여 True를 만든다.

그 사이에는 Linux에서 운영 실행을 하지 않는다.

### Windows 네이티브 경로

aux-pc의 Windows 경로(job object, Claude conformance 통과)는 그대로 두되 더 제품화하지 않는다. Codex를 blind 참여자로 쓰는 것은 WSL2 백엔드에서만 한다.

### 초안 보관

리뷰대로 "초안은 메모리에"는 임시 방안으로 본다. 초안과 원장은 controller만 여는 봉인 저장소(작은 SQLite journal과 파일)에 둔다. worker에는 연결하지 않고, 그것을 격리 백엔드가 보장한다.

## 작업 순서

| 단계 | 내용 | 모델 호출 | 상태 |
|---|---|---|---|
| 1 | 이 리뷰의 재현을 회귀 시험으로 옮기고 R01–R04를 고친다 | 없음 | 이 변경 |
| 2 | 실행 명세(stdin), core 환경 모듈(R05), controller 단계 관문, 봉인 저장소, 가짜 CLI 위의 모의 화면(인계 A1) | 없음 | 다음 |
| 3 | WSL2 설치(사용자), 배포판·Linux CLI 준비, 로그인(사용자), V04-01을 새 호스트 이름으로 다시 실시 | tier 2 몇 회, 승인 뒤 | 사용자 설치 대기 |
| 4 | bubblewrap 경계 시험. 허용 자료 읽힘(양성), 금지 자료 안 읽힘(음성), PID 공간 종료, `/proc`, controller 포트. runner에 `pid_namespace` 추적 단위 | 없음 | 3 뒤 |
| 5 | WSL2에서 B1·B2를 다시 정의해 관측하고 pilot | 승인 범위 | 2·4 뒤 |

## 리뷰 밖에서 새로 찾은 것

- `cancel_unconfirmed`의 정족수 누락과 단계 건너뛰기(위 R03 행).
- Windows에서 job 회계(`ActiveProcesses`)가 0이 된 직후, 끝낸 프로세스의 객체가 아직 신호를 받지 않은 짧은 틈이 있었다. aux-pc에서 반복하면 30회 중 5회였고, 모두 16ms 안에 사라졌다. runner의 판정은 유지하고, 회귀 시험은 그 틈만큼 기다린다.
- WSL2로 옮기면 aux-pc 관측 중 Windows에만 해당하는 것이 무효가 된다. openai/codex#42172 우회, PowerShell 5.1 재시도, `tools_rejected`가 찾는 거절 문자열이 그렇다. 새 호스트 이름으로 다시 관측한다.
