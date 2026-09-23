# V04-01 결과 — `aux-pc-wsl`

사용자의 **보조 PC**(`aux-pc`) 안의 WSL2 배포판이다. 실행 기반을 WSL2로 옮기기로 한 결정(NEXT-SESSION 2절 15)에 따라 V04-01을 새 이름표로 다시 한다. **Windows 쪽 [`aux-pc`](../aux-pc/RESULTS.md)의 관측을 복사해 성공으로 치지 않는다.** 절차는 [README](../../README.md)다. 계정 이메일·조직 ID·토큰·요금제·Linux 사용자 이름은 기록하지 않는다.

- 수행일: 2026-09-23
- 수행자: claude 세션(Claude Opus 5.5, aux-pc의 로컬 checkout). Windows 쪽 Claude 데스크톱 앱 안의 세션이 `wsl.exe`로 배포판 안의 명령을 실행했다. WSL 설치와 Linux 사용자 만들기는 사용자가 관리자 PowerShell에서 직접 했다
- 측정 환경: WSL 2.7.14.0, 커널 6.18.33.2-microsoft-standard-WSL2, Ubuntu 24.04.5 LTS, systemd 켜짐. 재부팅 없이 바로 동작했다(Virtual Machine Platform이 이미 켜져 있었다)
- tier 1 manifest: [`manifest.json`](manifest.json) — `--validate` PASS. 배포판 안에서 `python3 tools/runtime_inventory.py --host-label aux-pc-wsl`로 기록했다(`/mnt/c`의 checkout)
- tier 2: **아직 없다.** 로그인이 먼저다(아래)

## 설치와 로그인

설치 스크립트는 실행 전에 받아 읽었고, 읽은 파일을 그대로 실행했다(배포판 안에서 해시를 다시 확인). 두 스크립트 모두 공식 배포처의 SHA-256으로 바이너리를 검증한 뒤 홈 폴더에 설치한다. sudo는 쓰지 않았다.

| 도구 | 설치 방법 | 버전 | 설치 위치 | 로그인 | 비고 |
|---|---|---|---|---|---|
| Claude Code | 공식 `https://claude.ai/install.sh` (읽은 파일 SHA-256 `3a68d340…a944`) | 2.1.280 | `~/.local/bin/claude` | **아직** — 사용자가 한다 | 바이너리는 `downloads.claude.ai`의 manifest 체크섬으로 검증된다. 설치 프로그램은 그 셸의 PATH에 `~/.local/bin`이 없다고 안내했다. Ubuntu의 `~/.profile`이 로그인 셸에서 그 폴더를 PATH에 넣는다 |
| Codex | 공식 `https://chatgpt.com/codex/install.sh` (읽은 파일 SHA-256 `150e3cf6…28bf6`), `CODEX_NON_INTERACTIVE=true` | codex-cli 0.156.1 | `~/.local/bin/codex` → `~/.codex/packages/standalone/` | **아직** — 사용자가 한다 | 받는 곳은 `releases.openai.com`(대체: GitHub releases), SHA256SUMS로 검증한다. **`~/.bashrc`에 PATH 줄을 추가한다.** Linux 샌드박스용 bubblewrap을 스스로 들고 온다(`codex-resources/bwrap`, `--version`: "bubblewrap built for Codex"). Windows의 aux-pc는 0.155.1이었다 |
| Antigravity | 설치하지 않았다 | — | — | — | 기본은 꺼짐(2절 14). Linux용 공식 설치 스크립트 주소가 응답하는 것만 확인했다(내용은 읽지 않았다). 켤 때 B4와 함께 한다 |

과금 경로를 바꾸는 환경변수: **없음**(배포판 프로세스 환경, manifest `env_presence`). 인증·설정 파일: 없음 — 로그인 전이다.

## 환경 관측 — 격리 백엔드(W2)에 필요한 것

| 항목 | 관측 | 뜻 |
|---|---|---|
| AppArmor | `/sys/module/apparmor/parameters/enabled` = `N` | Ubuntu 24.04의 bubblewrap user namespace 제한이 이 커널에서는 걸리지 않는다 |
| user·PID namespace | `unshare --user --pid --fork --map-root-user true` 성공, `max_user_namespaces` 0이 아님 | 권한 없이 bubblewrap을 쓸 수 있는 조건이다. 실제 bwrap 시험은 W2 |
| bubblewrap 패키지 | 없음 | 설치에 sudo가 필요하다 — 사용자가 한다 |
| PATH | **Windows 폴더가 이어 붙어 있다**(WSL 기본값). Windows 쪽 Claude·Codex·agy 설치 폴더(`/mnt/c/Users/<user>/.local/bin` 등)도 들어 있다 | 이름만으로 찾으면 Windows CLI를 다시 부를 수 있다. [`core/env.py`](../../../../../core/env.py)가 자식 PATH에서 빼고 Windows 실행 파일을 거절한다. tier 1 도구는 Linux 판(`~/.local/bin`)을 찾았다 |
| Windows 드라이브 | `/mnt/c` 자동 연결(WSL 기본값), interop 켜짐 | 참여자 격리에서 연결하지 않을 목록에 넣는다(W2) |

## tier 1 — help 기준 (한도 소모 없음)

| 도구 | help에 있음 | help에 없음 |
|---|---|---|
| Claude Code | `--print`, `--output-format`, `--json-schema`, `--resume`, `--bare`, `--permission-mode`, `--permission-prompts`, `--allowedTools` | ACP |
| Codex | `exec`(`--json`, `--output-schema`, `resume`, `--sandbox`, `--ephemeral`, `--ignore-user-config`, `--skip-git-repo-check`), `login`, `app-server`, `sandbox` | ACP |

## 다음

1. 사용자: `sudo apt-get install -y bubblewrap`, 그리고 배포판 터미널에서 `claude`(구독 로그인)와 `codex login`(ChatGPT 로그인).
2. 모델 호출 없이 `claude auth status`와 `codex login status`로 로그인 방식을 기록한다.
3. tier 2(구독 호출)는 사용자 승인 뒤 절차서대로 한다.
