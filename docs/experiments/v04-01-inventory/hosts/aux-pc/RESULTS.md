# V04-01 결과 — `aux-pc`

사용자의 **보조 PC**다. 사용자가 2026-09-23 첫 V04-01을 이 기기에서 하기로 정했다. 운용 PC의 결과는 따로 기록한다. 절차는 [README](../../README.md)다. 계정 이메일·조직 ID·토큰·요금제는 기록하지 않았다.

- 수행일: 2026-09-23
- 수행자: claude 세션(Claude Opus 5.5, 이 PC의 로컬 checkout). 설치는 사용자 승인 후 이 세션이 실행
- 측정 환경: Claude 데스크톱 앱 안의 셸. 앱이 넣은 변수 26개를 뺀 새 터미널 근사 환경(`--fresh-env`)에서 실행
- tier 1 manifest: [`manifest.json`](manifest.json) — `--validate` PASS

## 설치와 로그인

설치 스크립트는 실행 전에 받아 읽었다. 세 스크립트 모두 공식 manifest의 해시로 바이너리를 검증한 뒤 설치한다. 관리자 권한은 쓰지 않았다.

| 도구 | 설치 방법 | 버전 | 코드 서명 (`Get-AuthenticodeSignature`) | 로그인 방식 | 비고 |
|---|---|---|---|---|---|
| Claude Code | 공식 PowerShell 설치 스크립트 | 2.1.280 | Anthropic, PBC — Valid | `claude auth status`: `loggedIn: true`, `authMethod: claude.ai`, `apiProvider: firstParty` | **설치 프로그램이 PATH를 등록하지 않았다.** 안내 문구에 따라 사용자 PATH에 `%USERPROFILE%\.local\bin`을 추가(사용자 승인 범위). 로그인은 새로 하지 않았다 — 데스크톱 앱과 같은 `~/.claude` 자격증명으로 보인다 |
| Codex | 공식 PowerShell 설치 스크립트 | codex-cli 0.155.1 | OpenAI OpCo, LLC — Valid | `codex login status`: Logged in using ChatGPT | 설치 프로그램이 사용자 PATH를 등록했다. Windows 샌드박스: 미설정(elevated 설정은 관리자 승인 필요 — 사용자 판단) |
| Antigravity | 공식 PowerShell 설치 스크립트 | 1.2.8 | Google LLC — Valid | **미확인** — 상태 확인 명령이 help에 없고 `~/.gemini/antigravity-cli/settings.json`도 없다 | 설치 프로그램이 사용자 PATH를 등록했다. `--version`은 문서에 없지만 동작했다 |

과금 경로를 바꾸는 환경변수: **없음.** 사용자·시스템 설정 범위에서 절차서의 변수 전부가 없다. `ANTHROPIC_BASE_URL`은 데스크톱 앱 셸에만 있었다.

## tier 1 — help 기준 (한도 소모 없음)

| 도구 | help에 있음 | help에 없음 |
|---|---|---|
| Claude Code | `--print`, `--output-format`(text/json/stream-json), `--json-schema`, `--resume`, `--bare`, `--permission-mode`(`dontAsk` 포함), `--permission-prompts`, `--allowedTools`, `auth status` | ACP |
| Codex | `exec`(`--json`, `--output-schema`, `resume`, `-s/--sandbox` read-only·workspace-write·danger-full-access, `--ephemeral`, `--ignore-user-config`, `--ignore-rules`, `--skip-git-repo-check`), `login status`, `app-server`(experimental), `sandbox` | ACP |
| Antigravity | `-p/--print`, `--output-format`(text/json/stream-json), `--json-schema`, `--continue`, `--conversation`, `--sandbox`, `--dangerously-skip-permissions`, `--effort`, `models` | ACP, 로그인 상태 명령 |

help에 있다는 것은 관측이 아니다. 문서와 다른 점:

- `agy --print-timeout` 기본값: 문서 5분, help `0s`(끝날 때까지 기다림)
- `agy --version`: 문서에 없음, 동작함
- `claude auth status`: 읽은 문서는 대화형 `/status`만 안내했으나 비대화형 명령이 있고 JSON을 출력한다

**ACP는 세 CLI의 help 어디에도 없었다.** Q1(ACP 우선) 판정에 쓰이는 관측이지만, help에 없다는 것이 지원하지 않는다는 증명은 아니다 — 별도 adapter로 붙는 경우가 있다.

## tier 2 관측

아직 하지 않았다. Antigravity 로그인(사용자)과 소량 한도 사용 승인이 먼저다.

| 번호 | 도구 | 실행한 명령 | exit | 관측한 것 | 출력 파일 | 기대와 같은가 |
|---|---|---|---|---|---|---|
| P1–P7 | — | — | — | 미실시 | — | — |

## 정책 확인

아직 하지 않았다.

## 판정

| 질문 | 결론 | 근거 |
|---|---|---|
| V04-03 진행 가능한가 | 보류 — tier 2 전 | |
| Q1: ACP 우선인가 exec 우선인가 | 보류. tier 1에서는 세 CLI 모두 help에 ACP 없음 | tier 1 |

## 열린 문제

- Antigravity 로그인 상태를 비대화형으로 확인하는 방법이 없다. tier 2 P1의 성공 여부로 간접 확인한다.
- Claude Code CLI가 데스크톱 앱과 자격증명을 공유하는 것으로 보인다. 앱과 CLI가 같은 구독 한도를 쓰는지는 미확인이다.
