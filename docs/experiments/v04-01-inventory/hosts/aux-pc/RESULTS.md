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

2026-09-23, 사용자 승인 후 이 세션이 한 줄씩 실행했다. 저장소 밖의 빈 임시 폴더, 새 터미널 근사 환경, 표준입력은 닫은 상태. 각 호출 뒤 폴더가 비어 있는지 확인했다(모두 비어 있음). 출력 파일은 이메일·UUID·홈 경로를 가렸다. 명령은 각 파일 첫머리에 그대로 있다. Antigravity는 로그인 후 진행한다.

| 번호 | 도구 | exit | 관측한 것 | 출력 | 기대와 같은가 |
|---|---|---|---|---|---|
| P1 | Claude Code | 0 | 응답 `OK`. `apiKeySource`는 P4에서 `none`(구독). 모델 `claude-opus-5-5`, `provider: firstParty`. 입력 2 + 캐시 생성 10,873 + 캐시 읽기 13,576 토큰, 출력 4. `total_cost_usd` 0.0898 — `costBasis: list`인 정가 기준 추정치이며 청구액이 아니다 | [P1-claude](tier2/P1-claude.txt) | 예 |
| P1 | Codex | 0 | 응답 `OK`. JSONL `thread.started` → `turn.started` → `item.completed` → `turn.completed`. 사용량은 입력 15,268 · 출력 5 토큰. **모델 이름과 비용 필드가 없다.** 표준입력이 열려 있으면 `Reading additional input from stdin...`을 출력하고 기다린다 | [P1-codex](tier2/P1-codex.txt) | 예 |
| P2 | Claude Code `--bare` | 1 | `Not logged in · Please run /login`, 비용 0, API 시간 0. **`subtype`은 `"success"`인데 `is_error`가 `true`다** | [P2-claude](tier2/P2-claude.txt) | 예 (F25 재현) |
| P3 | Claude Code | 1 | 모델 호출 전 거절: `--permission-mode` 허용값은 `acceptEdits, auto, bypassPermissions, manual, dontAsk, plan` (0.16초) | [P3-claude](tier2/P3-claude.txt) | 예 |
| P3 | Codex | 2 | 모델 호출 전 거절: `--sandbox` 허용값 `read-only, workspace-write, danger-full-access` | [P3-codex](tier2/P3-codex.txt) | 예 |
| P4 | Claude Code | 0 | 빈 폴더에서도 **사용자 전역 설정이 통째로 실린다**: 도구 35(그중 MCP 도구 8), MCP 서버 18(claude.ai 연결 서비스 4 포함, 연결됨 1·인증 대기 13·실패 4), 플러그인 5, 스킬 44, 에이전트 5, 슬래시 명령 79. 문맥 24,449 토큰(이번엔 전부 캐시 읽기, 추정 비용 0.005). `~/.claude/CLAUDE.md`는 없다. 원본 스트림은 설치 목록이 드러나 PC에만 두고 요약만 올렸다 | [P4-claude](tier2/P4-claude.txt) | 예 — 그리고 blind·권한 문제를 드러냄 |
| P4 | Codex `--ignore-user-config --ignore-rules` | 0 | 사용자 설정을 무시해도 **ChatGPT 로그인으로 돈다.** 입력 13,740 토큰(설정 포함 때 15,268), 캐시 11,776 | [P4-codex](tier2/P4-codex.txt) | 예 |
| P5 | Claude Code·Codex | — | 기본 모델: Claude `claude-opus-5-5`(P1). Codex는 이벤트에 모델 이름이 없다. 전체 목록은 대화형 `/model`이 필요해 미확인 | — | 부분 |
| P6 | — | — | 미실시(선택, V04-03으로) | — | — |
| P7 | Codex | — | `app-server`(experimental) help에 있음, 호출 미시험 | — | — |

### tier 2에서 나온 설계 입력

1. **Claude Code의 blind 초안은 지금 방식으로는 깨끗하지 않다.** `--bare` 없이 `-p`를 쓰면 사용자의 플러그인·스킬·MCP 연결(외부 서비스 커넥터 포함)이 모두 문맥과 도구에 들어온다. `--bare`는 구독을 쓰지 못한다(P2). 읽기 전용 논의자가 사용자의 외부 서비스 도구를 가질 수 있다는 점은 권한 경계 문제이기도 하다. 후보(미시험): 별도 `CLAUDE_CONFIG_DIR`에서 구독으로 한 번 로그인해 빈 설정을 쓰는 방법, `--strict-mcp-config`와 빈 MCP 설정. V04-03 전에 시험한다.
2. **Codex는 깨끗한 문맥과 구독 인증을 함께 얻을 수 있다**(P4). 인증 파일과 설정 파일이 분리돼 있기 때문으로 보인다.
3. **성공 판정은 한 필드로 하지 않는다.** Claude의 실패 결과가 `subtype: "success"`를 달고 나온다(P2). `is_error`와 exit code를 함께 본다.
4. **adapter는 표준입력을 닫아야 한다.** Codex `exec`는 열린 stdin을 추가 입력으로 기다린다(P1).
5. **비용 필드는 제각각이다.** Claude는 정가 기준 추정 비용과 캐시 생성·읽기를 나눠 주고, Codex는 토큰만 준다. 캐시 상태에 따라 같은 호출의 추정 비용이 18배 차이 났다(P1 0.0898 → P4 0.0050). 구독 한도 소모와는 다른 값이다.
6. 잘못된 제한 인자는 두 CLI 모두 실행 전에 거절했다(P3). 이 버전들에서는 F26 같은 조용한 강등을 관측하지 못했다 — 다른 인자 조합까지 안전하다는 뜻은 아니다.

캡처 한계: PowerShell 5.1로 출력을 받으면서 ASCII가 아닌 문자 일부가 깨졌다(P2의 `·`). 판정에 쓰인 필드는 ASCII다.

## 정책 확인

아직 하지 않았다.

## 판정

| 질문 | 결론 | 근거 |
|---|---|---|
| V04-03 진행 가능한가 | **Claude Code·Codex 두 경로는 조건 충족**(P1 구독 성공, P3 실행 전 거절, 과금 변수 없음). 단 Claude의 blind 문맥 문제(설계 입력 1)를 먼저 풀어야 한다. Antigravity는 로그인 후 판정 | P1, P3, P4 |
| Q1: ACP 우선인가 exec 우선인가 | 보류. 세 CLI 모두 help에 ACP가 없고, 두 CLI는 비대화형 실행(`-p`, `exec --json`)이 관측으로 동작했다 — exec 우선 쪽 근거가 쌓이는 중 | tier 1, P1 |

## 열린 문제

- Antigravity 로그인 상태를 비대화형으로 확인하는 방법이 없다. tier 2 P1의 성공 여부로 간접 확인한다.
- Claude Code CLI가 데스크톱 앱과 자격증명을 공유하는 것으로 보인다. 앱과 CLI가 같은 구독 한도를 쓰는지는 미확인이다.
