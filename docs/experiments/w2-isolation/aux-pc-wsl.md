# W2 — bubblewrap 경계 시험, `aux-pc-wsl`

2026-09-23 · claude 세션(Claude Opus 5.5, aux-pc의 로컬 checkout, `wsl.exe`로 배포판 안에서 실행). **모델 호출 없음.** 격리 백엔드는 bubblewrap으로 먼저 시험한다는 결정(NEXT-SESSION 2절 16)의 확인이다. 환경은 [`aux-pc-wsl` V04-01 기록](../v04-01-inventory/hosts/aux-pc-wsl/RESULTS.md): WSL 2.7.14, Ubuntu 24.04.5, bubblewrap 0.9.0(사용자가 apt로 설치), AppArmor 꺼짐.

격리 규칙은 [`core/isolation.py`](../../../core/isolation.py)에 있다. 요지:
- 모든 namespace를 나누되 네트워크는 공유한다(`--unshare-all --share-net`). `--die-with-parent`, `--new-session`, `--clearenv`를 쓴다.
- 시스템 폴더(`/usr`, `/etc`)는 읽기 전용이다. HOME과 `/tmp`는 빈 tmpfs다.
- 입력과 CLI 실행 파일은 읽기 전용, 작업 폴더와 그 CLI 자신의 설정·인증 폴더만 쓰기다.

## 1. 합성 파일 시험 — [`tests/test_core_isolation.py`](../../../tests/test_core_isolation.py)

python 탐침을 격리 안에서 실행했다. 원장·초안·인증 대신 표식을 넣은 가짜 파일을 썼다. 배포판 안에서 통과했다. CI(Linux)도 bubblewrap을 설치해 같은 시험을 돌린다.

| 대조 | 결과 |
|---|---|
| 양성: 입력 자료 읽기, 자기 CLI 폴더 읽기, 작업 폴더 쓰기 | 된다 |
| 음성: 다른 참여자 초안, 원장, 지난 합성, HOME의 다른 파일, 다른 CLI 인증 | 안 된다(파일 없음) |
| 음성: 입력 폴더 안 symlink → 다른 참여자 초안 | 안 된다(대상이 격리 안에 없다) |
| 음성: 입력 폴더 쓰기 | 안 된다(읽기 전용) |
| `/mnt/c`, `/run/user`, `/run/WSL`, `/init` | 없다. `/mnt`에는 DNS용 `wsl/resolv.conf` 파일 하나만 보인다(WSL의 `/etc/resolv.conf`가 그것을 가리킨다) |
| HOME 쓰기 | 안에서는 되지만 호스트에 남지 않는다(tmpfs) |
| 환경변수 | 허용 목록 밖(`WSL_INTEROP` 등)은 없다 |
| PID namespace | 안에서 PID 1은 bwrap이고, 보이는 프로세스는 몇 개뿐이다 |
| 새 세션으로 떨어져 나간 손자(R01 시나리오) | **namespace와 함께 끝난다.** runner가 `containment=pid_namespace`, `tree_confirmed_empty=True`를 돌려주고 호스트에 그 프로세스가 남지 않는다 |
| 시간 초과 | 안의 프로세스가 모두 끝난다 |
| **보장하지 않는 것:** 호스트 localhost TCP 포트 | **닿는다**(네트워크 공유). controller 제어 API는 참여자에게 없는 토큰으로 막아야 한다 |

## 2. 설치된 CLI — [`tools/w2/cli_boundary.py`](../../../tools/w2/cli_boundary.py)

각 CLI의 참여자 경계를 만들고 안에서 `--version`과 로그인 상태 명령(모델 호출 아님)을 실행했다. 계정 이메일·조직 ID·요금제는 버리고 로그인 여부와 방식만 남겼다.

| | Claude Code 2.1.280 | Codex 0.156.1 |
|---|---|---|
| 연결: 읽기 전용 | `~/.local/share/claude/versions/2.1.280`(실행 파일) | `~/.codex/packages/standalone/releases/0.156.1-…`(실행 파일과 `codex-resources`) |
| 연결: 쓰기 | `~/.claude`, `~/.claude.json` | `~/.codex` |
| `--version` | 된다, 자손 전체 종료 확인 | 된다, 자손 전체 종료 확인 |
| 로그인 상태 | `loggedIn: true`, `authMethod: claude.ai`, `apiProvider: firstParty` | Logged in using ChatGPT |
| 보이는 것 | 자기 인증·설정 파일 | 자기 인증 파일 |
| 보이지 않는 것 | Codex 인증, `~/.bashrc`, `/mnt/c` | Claude 인증·설정, `~/.bashrc`, `/mnt/c` |

## 아직 모르는 것 — 모델 호출이 필요하다(B1·B2)

- 실제 질문 한 번이 격리 안에서 끝까지 도는지: 토큰 갱신 쓰기, DNS·TLS, stdin 입력(EOF, 큰 한글, 선행 대시).
- Codex의 자체 bubblewrap(`codex-resources/bwrap`)이 우리 bubblewrap 안에서 명령 샌드박스를 만들 수 있는지(중첩 user namespace). 논의자에게 파일을 읽히지 않으면 명령 자체가 드물다.
- Linux Codex가 명령을 거절할 때 stderr에 남는 문자열(`tools_rejected` 판정).
- 연결한 CLI 폴더를 더 좁힐 수 있는지. 지금은 `~/.claude` 전체라서, 사용자가 이 배포판에서 대화형으로 쓴 Claude 세션 기록도 Claude 참여자에게 보인다. 필요한 파일만 남기는 것을 B1에서 본다.

## 갱신(2026-09-23) — WSL2 리뷰 반영 뒤

[WSL2 리뷰](../../reviews/2026-09-23-wsl2-migration-review/README.md)(PR #6)를 반영하면서 격리의 진입점이 `isolation.run()` 하나로 바뀌었다. 이 진입점은 root 소유 `/usr/bin/bwrap`인지 확인하고, 경로 충돌을 거절하며, 환경변수 값을 명령 인자에 싣지 않는다. 위 1의 합성 시험과 2의 CLI 도구를 새 진입점으로 다시 돌렸고 결과는 같았다. 2의 두 CLI 모두 `--version`과 로그인 상태가 exit 0이었다. 위 표의 "runner가 `containment=pid_namespace`를 돌려준다"는 이제 `isolation.run()`으로 실행했을 때의 일이다. 반영 내역은 [반영 기록](../../reviews/2026-09-23-wsl2-migration-review/RESPONSE.md)에 있다.
