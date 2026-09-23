# V04-01 결과 — `aux-pc`

사용자의 **보조 PC**다. 사용자가 2026-09-23 첫 V04-01을 이 기기에서 하기로 정했다. 운용 PC의 결과는 따로 기록한다. 절차는 [README](../../README.md)다. 계정 이메일·조직 ID·토큰·요금제는 기록하지 않았다.

- 수행일: 2026-09-23
- 수행자: claude 세션(Claude Opus 5.5, 이 PC의 로컬 checkout). 설치는 사용자 승인 후 이 세션이 실행
- 측정 환경: Claude 데스크톱 앱 안의 셸. 앱이 넣은 변수 26개를 뺀 새 터미널 근사 환경(`--fresh-env`)에서 실행
- tier 1 manifest: [`manifest.json`](manifest.json) — `--validate` PASS
- tier 2 manifest: [`manifest.tier2.json`](manifest.tier2.json) — 아래 tier 2 표에서 관측한 기능만 `observed`. `configured`는 Claude Code·Codex만 `true`, Antigravity는 판정의 조건 때문에 `false`. `--validate` PASS
- **정정(2026-09-23, [PR #4](https://github.com/inlight37-design/decision-model_lab/pull/4) R02·R05·R07):** 아래 표시한 곳을 고쳤다. 처음 문장은 "처음에 … 라고 적었으나"로 남겼다. 요지: Claude `permission_mode`는 값 검증만 관측돼 manifest 규칙대로 `in_help`다. `configured=true`는 기본 구독 호출을 관측했다는 뜻이지 blind 문맥·권한 conformance 통과가 아니다. "깨끗한 문맥"은 사용자 설치분이 줄었다는 관측이다. agy 기본 모델은 P5로 확인되지 않았다. 검토와 답: [v04-01 리뷰](../../../../reviews/2026-09-23-v04-01-review/README.md), [반영 기록](../../../../reviews/2026-09-23-v04-01-review/RESPONSE.md)

## 설치와 로그인

설치 스크립트는 실행 전에 받아 읽었다. 세 스크립트 모두 공식 manifest의 해시로 바이너리를 검증한 뒤 설치한다. 관리자 권한은 쓰지 않았다.

| 도구 | 설치 방법 | 버전 | 코드 서명 (`Get-AuthenticodeSignature`) | 로그인 방식 | 비고 |
|---|---|---|---|---|---|
| Claude Code | 공식 PowerShell 설치 스크립트 | 2.1.280 | Anthropic, PBC — Valid | `claude auth status`: `loggedIn: true`, `authMethod: claude.ai`, `apiProvider: firstParty` | **설치 프로그램이 PATH를 등록하지 않았다.** 안내 문구에 따라 사용자 PATH에 `%USERPROFILE%\.local\bin`을 추가(사용자 승인 범위). 로그인은 새로 하지 않았다 — 데스크톱 앱과 같은 `~/.claude` 자격증명으로 보인다 |
| Codex | 공식 PowerShell 설치 스크립트 | codex-cli 0.155.1 | OpenAI OpCo, LLC — Valid | `codex login status`: Logged in using ChatGPT | 설치 프로그램이 사용자 PATH를 등록했다. Windows 샌드박스: 미설정(elevated 설정은 관리자 승인 필요 — 사용자 판단). **갱신(2026-09-23 V04-03):** 같은 날 `codex doctor`는 `sandbox backend elevated`, `provisioning complete`를 보고했다. 이 기록 뒤에 설정됐는지, 처음 판단이 틀렸는지는 확인할 수 없다. [V04-03 conformance](../../../v04-03-conformance/aux-pc.md) |
| Antigravity | 공식 PowerShell 설치 스크립트, **`--dir ~\.local\agy\bin`으로 재설치** | 1.2.8 | Google LLC — Valid | **Google 계정 로그인**(사용자가 앱 밖 터미널에서 `agy` 실행 → 브라우저. 시작 화면에 계정과 요금제가 표시됐다 — 기록하지 않음). 상태 확인 명령은 help에 없고, P1 성공으로 비대화형에서도 로그인이 쓰임을 확인 | 첫 설치는 기본 폴더 `%LOCALAPPDATA%\agy\bin`에 했는데, **Claude 데스크톱 앱(MSIX)의 전용 가상 공간으로 들어가** 사용자 터미널에서 "인식되지 않음"이 났다(아래). 가상 사본과 그 PATH 항목을 지우고 AppData 밖에 다시 설치했다. `--dir`로 설치해도 마지막 안내는 기본 경로를 출력한다(표시 문제). `--version`은 문서에 없지만 동작했다 |

### 설치 위치 문제 — Claude 데스크톱 앱의 가상화

이 세션은 Claude 데스크톱 앱(Microsoft Store 방식, `Get-AppxPackage`: Claude 2.2553.13.0) 안에서 실행됐다. 앱 안의 프로세스가 `%LOCALAPPDATA%` 아래에 새로 만든 `agy` 폴더는 `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local\agy\`로 옮겨졌다. 앱 안의 세션에는 원래 경로에 있는 것처럼 보였고(tier 1이 그 사본을 실행했다), 사용자가 앱의 터미널 탭에서 실행하자 파일이 없었다.

- 영향 없었던 것: Claude(`~\.local\bin`, AppData 밖), Codex(`%LOCALAPPDATA%\Programs\OpenAI\Codex\bin`은 `~\.codex\packages\standalone\current\bin`으로 가는 연결 폴더이고, 가상 공간에 생기지 않았다), PATH 레지스트리(앱의 가상 레지스트리 파일은 설치 전 시각 이후 바뀌지 않았다)
- 조치: PATH를 백업(`%TEMP%\v0401-user-path-backup-2.txt`)하고 `%LOCALAPPDATA%\agy\bin` 항목을 지웠다. 가상 사본을 정확한 경로로 지우고, 같은 공식 스크립트로 `~\.local\agy\bin`에 다시 설치했다. 설치 프로그램이 그 폴더를 사용자 PATH에 등록했다
- 사용자 터미널에서의 재확인: 아래 로그인 단계에서 한다

tier 1 기록의 Antigravity 줄은 가상 사본을 실행한 결과다. 두 설치 모두 같은 1.2.8 manifest의 SHA512로 설치 프로그램이 검증했고 크기(197,157,016 바이트)가 같다. 재설치 후 버전과 서명자가 같음을 `tools/v04-01/check-versions.ps1`로 확인했다.

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

2026-09-23, 사용자 승인 후 이 세션이 한 줄씩 실행했다. 저장소 밖의 빈 임시 폴더, 새 터미널 근사 환경, 표준입력은 닫은 상태. 각 호출 뒤 폴더가 비어 있는지 확인했다(모두 비어 있음). 출력 파일은 이메일·UUID·홈 경로를 가렸다. 명령은 각 파일 첫머리에 그대로 있다. Antigravity는 사용자가 로그인한 뒤 같은 날 `tools/v04-01/probe.ps1`로 실행했다.

P3b는 계획에 없던 관측이다. P3-agy가 잘못된 값을 조용히 무시하자, 권한 옵션을 **오타로** 쓰면 제한 없이 실행되는지 세 CLI에 같은 방식으로 확인했다.

| 번호 | 도구 | exit | 관측한 것 | 출력 | 기대와 같은가 |
|---|---|---|---|---|---|
| P1 | Claude Code | 0 | 응답 `OK`. `apiKeySource`는 P4에서 `none`(구독). 모델 `claude-opus-5-5`, `provider: firstParty`. 입력 2 + 캐시 생성 10,873 + 캐시 읽기 13,576 토큰, 출력 4. `total_cost_usd` 0.0898 — `costBasis: list`인 정가 기준 추정치이며 청구액이 아니다 | [P1-claude](tier2/P1-claude.txt) | 예 |
| P1 | Codex | 0 | 응답 `OK`. JSONL `thread.started` → `turn.started` → `item.completed` → `turn.completed`. 사용량은 입력 15,268 · 출력 5 토큰. **모델 이름과 비용 필드가 없다.** 표준입력이 열려 있으면 `Reading additional input from stdin...`을 출력하고 기다린다 | [P1-codex](tier2/P1-codex.txt) | 예 |
| P2 | Claude Code `--bare` | 1 | `Not logged in · Please run /login`, 비용 0, API 시간 0. **`subtype`은 `"success"`인데 `is_error`가 `true`다** | [P2-claude](tier2/P2-claude.txt) | 예 (F25 재현) |
| P3 | Claude Code | 1 | 모델 호출 전 거절: `--permission-mode` 허용값은 `acceptEdits, auto, bypassPermissions, manual, dontAsk, plan` (0.16초) | [P3-claude](tier2/P3-claude.txt) | 예 |
| P3 | Codex | 2 | 모델 호출 전 거절: `--sandbox` 허용값 `read-only, workspace-write, danger-full-access` | [P3-codex](tier2/P3-codex.txt) | 예 |
| P3 | Antigravity `--output-format notaformat` | **0** | **거절하지 않고 모델을 불러 `OK`를 text로 답했다**(10.4초). 경고도 stderr도 없다. help의 허용값은 `text, json, stream-json` | [P3-agy](tier2/P3-agy.txt) | **아니오** — 잘못된 값이 조용히 기본값으로 바뀐다 |
| P3b | Claude Code `--permision-mode plan` (오타) | 1 | 모델 호출 전 거절: `unknown option`, `Did you mean --permission-mode?` | [P3b-claude](tier2/P3b-claude.txt) | 예 |
| P3b | Codex `--sandbx read-only` (오타) | 2 | 모델 호출 전 거절: `unexpected argument '--sandbx'`, 비슷한 인자 `--sandbox` 안내 | [P3b-codex](tier2/P3b-codex.txt) | 예 |
| P3b | Antigravity `--sandbx` (오타) | 2 | 모델 호출 전 거절: `flags provided but not defined: -sandbx` (0.1초) | [P3b-agy](tier2/P3b-agy.txt) | 예 |
| P1 | Antigravity | 0 | 응답 `OK`, JSON 필드 `conversation_id`·`duration_seconds`·`num_turns`·`response`·`status: SUCCESS`·`usage`(입력 11,724 · 출력 23 · 사고 22 · 캐시 읽기 0). **모델 이름과 비용 필드가 없다.** 신뢰하지 않은 빈 폴더에서도 비대화형 실행이 막히지 않았다 | [P1-agy](tier2/P1-agy.txt) | 예 |
| P4 | Claude Code | 0 | 빈 폴더에서도 **사용자 전역 설정이 통째로 실린다**: 도구 35(그중 MCP 도구 8), MCP 서버 18(claude.ai 연결 서비스 4 포함, 연결됨 1·인증 대기 13·실패 4), 플러그인 5, 스킬 44, 에이전트 5, 슬래시 명령 79. 문맥 24,449 토큰(이번엔 전부 캐시 읽기, 추정 비용 0.005). `~/.claude/CLAUDE.md`는 없다. 원본 스트림은 설치 목록이 드러나 PC에만 두고 요약만 올렸다 | [P4-claude](tier2/P4-claude.txt) | 예 — 그리고 blind·권한 문제를 드러냄 |
| P4b | Claude Code `--restricted --strict-mcp-config --disable-slash-commands --tools ""` | 0 | **구독 인증을 유지한 채 사용자 설치분이 빠졌다**(정정: 처음에 "문맥이 깨끗해졌다"고 적었으나, init 목록이 비었다는 관측이지 지시문·메모리·peer 정보가 입력에 없다는 증명은 아니다 — PR #4 R02): `apiKeySource: none`, 도구 0, MCP 서버 0, 스킬 0, 슬래시 명령 0, 메모리 경로 없음(원 stream에서 수행자가 확인. 공개 요약에는 없다). 남은 것은 Claude Code **내장** 플러그인 2개(`@builtin`)와 기본 에이전트 5개. 문맥 1,339 + 531 = 약 1,900 토큰(P4의 약 24,400에서 13분의 1). 첫 시도는 PowerShell 5.1이 빈 문자열 인자를 버려 `--tools` 값 누락으로 실행 전 거절됐고(exit 1, 한도 소모 없음), `'""'`로 넘겨 해결했다 | [P4b-claude](tier2/P4b-claude.txt) | **예 — 설계 입력 1의 해법** |
| P4 | Codex `--ignore-user-config --ignore-rules` | 0 | 사용자 설정을 무시해도 **ChatGPT 로그인으로 돈다.** 입력 13,740 토큰(설정 포함 때 15,268), 캐시 11,776 | [P4-codex](tier2/P4-codex.txt) | 예 |
| P5 | Claude Code·Codex | — | 기본 모델: Claude `claude-opus-5-5`(P1). Codex는 이벤트에 모델 이름이 없다. 전체 목록은 대화형 `/model`이 필요해 미확인 | — | 부분 |
| P5 | Antigravity `agy models` | 0 | 목록 첫 행은 **Gemini 3.8 Flash (High)**. 정정: 처음에 "기본 모델은 Gemini 3.8 Flash (High)"라고 적었으나, 출력은 기본값을 표시하지 않는다 — **기본 모델은 미확인**(PR #4 R07). 이름에 Pro가 붙은 것은 `gemini-3.1-pro-high`/`-low`뿐이다. 정정: 처음에 이를 "Gemini 계열 최상위"라고 적었으나 이름만 보고 판단한 것이다. **사용자 보고(2026-09-23, 전달):** 3.1 Pro는 옛 세대라 3.8 Flash보다 지시를 못 알아듣는다. 그 밖에 `gemini-3.8/3.7/3.6-flash-*`, 그리고 **다른 회사 모델** `claude-opus-4-6-thinking`, `claude-sonnet-4-6`, `gpt-oss-120b-medium` | [P5-agy](tier2/P5-agy.txt) | 예 |
| P6 | — | — | 미실시(선택, V04-03으로) | — | — |
| P7 | Codex | — | `app-server`(experimental) help에 있음, 호출 미시험 | — | — |

### tier 2에서 나온 설계 입력

1. **Claude Code의 기본 `-p`는 blind 초안에 깨끗하지 않지만, 해법이 관측됐다.** 기본 `-p`는 사용자의 플러그인·스킬·MCP 연결(외부 서비스 커넥터 포함)을 모두 싣고(P4), `--bare`는 구독을 쓰지 못한다(P2). **`--restricted --strict-mcp-config --disable-slash-commands --tools ""`는 구독 인증을 유지하면서 사용자 설치분을 모두 뺐다(P4b).** 남은 것은 내장 플러그인 2개와 기본 에이전트 목록이다. 이 조합은 도구가 하나도 없으므로 논의자가 파일을 읽어야 하면 `--tools Read`와 `--add-dir`로 범위를 좁혀 다시 시험한다. `--restricted`는 help에만 있는 이름으로 확인했고 공식 문서 locator는 아직 없다 — adapter 구현 전에 문서와 대조한다.
   **갱신(2026-09-23, PR #4 질문 2, 문서 확인):** 공식 locator는 [CLI reference](https://code.claude.com/docs/en/cli-reference)의 CLI flags 표 `--restricted`다. 평가 harness용으로 안내하고, v2.1.248 이상이며, managed settings와 `--settings`만 읽는다고 적는다. **CLAUDE.md 제외는 말하지 않는다.** 같은 표의 `--safe-mode`는 CLAUDE.md·자동 메모리·플러그인까지 끄고 인증을 유지한다고 적는다 — 다음 관측 후보다. 어느 쪽도 blind 입력 통제를 증명하지 않는다. 합성 marker와 금지 파일 읽기 시도로 확인한다. 이 PC에는 `~/.claude/CLAUDE.md`가 없어서 P4b가 그 경로를 시험하지 못했다.
2. **Codex는 사용자 설정 파일을 빼도 구독 인증으로 돈다**(P4). 인증 파일과 설정 파일이 분리돼 있기 때문으로 보인다. 정정: 처음에 "깨끗한 문맥과 구독 인증을 함께 얻을 수 있다"고 적었으나, help와 [문서](https://learn.chatgpt.com/docs/non-interactive-mode)상 `--ignore-user-config`는 `config.toml`만, `--ignore-rules`는 execpolicy `.rules`만 뺀다. AGENTS.md 같은 지시문 파일은 이 플래그들의 범위가 아니다. 입력 토큰 감소는 두 플래그를 함께 준 결과라 한쪽에 돌리지 않는다(PR #4 R02).
3. **성공 판정은 한 필드로 하지 않는다.** Claude의 실패 결과가 `subtype: "success"`를 달고 나온다(P2). `is_error`와 exit code를 함께 본다.
4. **adapter는 표준입력을 닫아야 한다.** Codex `exec`는 열린 stdin을 추가 입력으로 기다린다(P1).
5. **비용 필드는 제각각이다.** Claude는 정가 기준 추정 비용과 캐시 생성·읽기를 나눠 주고, Codex는 토큰만 준다. 캐시 상태에 따라 같은 호출의 추정 비용이 18배 차이 났다(P1 0.0898 → P4 0.0050). 구독 한도 소모와는 다른 값이다.
6. **옵션 이름은 세 CLI 모두 엄격하지만, 값 검증은 다르다.** 오타 옵션은 셋 다 실행 전에 거절했다(P3b). 그러나 Antigravity는 `--output-format`에 없는 값을 주면 **조용히 기본값(text)으로 바꿔 실행**했다(P3). F26과 같은 계열의 조용한 강등이다. adapter는 CLI에 넘기기 전에 **값을 스스로 허용 목록과 대조**하고, 실행 뒤에는 **요청한 형식으로 나왔는지 확인**해야 한다(JSON을 요청했는데 JSON이 아니면 실패). 다른 값 옵션(`--effort` 등)도 같은지는 미확인이다.
7. **참여자의 회사는 CLI가 아니라 모델로 센다.** Antigravity로 Claude Opus 4.6과 GPT-OSS도 부를 수 있다(P5). `agy`를 Google 참여자로 세고 모델을 Claude로 고르면 Anthropic이 두 번 들어간다. provider 구별 규칙(`check_frontier_protocol`의 `distinct providers`)은 모델 ID에서 회사를 정해야 한다.
8. **상급 모델은 명시해서 고른다.** Antigravity의 기본 모델은 미확인이다(정정: 처음에 "기본값은 Flash다(P5)"라고 적었다). Gemini 상급 자리에 쓰려면 모델을 명시하고(정정: 처음에 `gemini-3.1-pro-high`를 예로 들었으나, 사용자 보고로는 3.8 Flash가 낫다. 이름의 Pro/Flash가 아니라 세대와 실제 비교로 고른다), 실제로 그 모델로 돌았는지는 출력에 모델 필드가 없으므로(P1) 별도로 확인할 방법을 찾아야 한다.
   갱신(PR #4 R07): [headless 문서](https://www.antigravity.google/docs/cli/headless/)는 headless에서 **없는 `--model` 이름이면 조용히 대체하지 않고 비영 종료·`ERROR`**라고 적고, `--model`을 지정하면 stream-json의 init에 `model`이 나온다고 적는다(2026-09-23 문서 확인, 1.2.8 미시험). 명시 지정과 init 대조가 확인 경로다. `--effort`의 없는 값 처리는 문서에 없다.
9. **세 CLI 중 모델 이름을 결과에 주는 것은 Claude뿐이다**(P1). Codex와 Antigravity는 결과만 보고 어느 모델이 답했는지 알 수 없다 — 조용한 모델 강등(D18)을 결과로는 잡을 수 없다는 뜻이다. 단 Antigravity는 위 8의 init 경로가 문서에 있다. init의 모델 이름도 요청이 반영됐다는 표시이지 실제 backend의 증명은 아니다.

캡처 한계: PowerShell 5.1로 출력을 받으면서 ASCII가 아닌 문자 일부가 깨졌다(P2의 `·`). 판정에 쓰인 필드는 ASCII다.

## 정책 확인

2026-09-23 공식 문서를 읽었다. 문서를 읽은 것이며 계정에 적용해 본 것은 아니다.

| 항목 | 문서 | 확인한 문구·내용 | 결론 |
|---|---|---|---|
| Claude 구독으로 Claude Code | [E04](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan) (2026-08-19 갱신) | Pro·Max는 Claude Code를 포함하고 **claude.ai와 한도를 공유**한다. 한도에 닿으면 상위 요금제, 선택적 API 크레딧, 초기화 대기 중에서 고른다. `ANTHROPIC_API_KEY`가 있으면 구독 대신 그 키로 과금된다 | 구독 경로 유효. 데스크톱 앱 사용과 CLI 호출이 **같은 한도**를 쓴다 |
| `claude -p`·SDK 구독 차감과 보류 공지 | [E05·F18](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) (2026-06-16 갱신) | "변경을 보류한다. SDK, `claude -p`, 제3자 앱 사용은 여전히 구독 한도에서 차감된다." 별도 월 크레딧은 없다 | 지금은 유효. 공지가 바뀔 수 있어 adapter 구현 직전에 다시 본다 |
| Codex ChatGPT 로그인과 API 과금 | [E01](https://learn.chatgpt.com/docs/auth) | ChatGPT 로그인은 workspace 권한을 따르고, API 키는 표준 API 요율로 청구된다. 한도 소진 시 동작과 동시 사용은 문서에 없다 | 구독 경로 유효. 한도 소진 동작 미확인 |
| Antigravity 크레딧 자동 사용 | [E09](https://www.antigravity.google/docs/cli/credits/), [설정 문서](https://www.antigravity.google/docs/settings?tab=cli) (날짜 표시 없음) | `useG1Credits`, 메뉴 이름 "Use AI Credits". 설정 문서 원문: "When enabled (`on`), allows the CLI to use your personal AI credits ... if your plan's standard quota is exhausted." | **이 계정은 `off`**(사용자가 `/config`에서 확인). 한도를 다 써도 유료 크레딧으로 넘어가지 않는다 — D18과 맞다. **정정:** 처음에 "기본값이 켜짐으로 읽힌다"고 적었으나, 크레딧 페이지 요약을 잘못 읽은 것이다. 설정 문서는 켤 때의 동작만 설명한다 |
| Gemini CLI 소비자 인증 종료설 | [F30](https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals) (2026-09-02 갱신) | 2026-06-18부터 개인·Google AI Pro·Ultra 계정의 Gemini CLI 요청 중단. Standard·Enterprise는 유지. Antigravity로 이전 안내 | **확인됨.** 구독 경로가 실제로 닫힌 사례. agy에는 직접 적용되지 않는다 |
| Antigravity 약관의 제3자 접근 | [F31](https://antigravity.google/terms) (날짜 표시 없음) | 6조: 제3자 소프트웨어로 서비스에 접근하는 것(예: Antigravity OAuth를 다른 도구에서 쓰기)은 위반. 5조: 상호작용 데이터 사용은 설정에서 바꿀 수 있다 | **우리 앱이 공식 `agy`를 하위 프로세스로 구동하는 것이 해당하는지 불명확.** 사용자 결정 필요 |
| 요금제별 동시 기기·세션 제한 | 위 문서들 | 세 문서 모두 언급하지 않는다 | 미확인 — 가정하지 않는다 |
| 구독 경로가 닫혔을 때의 대안 | — | — | **사용자 결정(2026-09-23): 유료 API로 전환하지 않는다. 경로가 닫히거나 한도를 다 쓰면 그 provider를 구성에서 뺀다.** 원하는 모델을 붙였다 뗐다 하는 구조가 원래 의도다 |
| Antigravity 상호작용 데이터 사용 | [설정 문서](https://www.antigravity.google/docs/settings?tab=cli) | `enableTelemetry`, 메뉴 "Enable Telemetry"(Settings의 Account 구역). 원문: "When toggled on, Antigravity collects interactions for use in evaluating, developing, and improving Antigravity and models". 설정 파일은 기본값과 다른 값만 저장한다 | **끔.** 사용자 요청으로 이 세션이 `~/.gemini/antigravity-cli/settings.json`에 `"enableTelemetry": false`를 추가했다(원본 백업, 다른 항목 유지). agy를 다시 실행해도 값이 유지됐다. 서버 쪽 계정 설정에 반영됐는지는 `/config` 화면에서만 확인할 수 있다 |

첫 실행 관측: agy 1.2.8은 첫 실행 때 **상호작용 데이터 수집 동의가 미리 체크된 화면**을 보여 줬고, 이번 로그인에서는 체크된 채로 완료됐다(위 표에서 끔). 실행 폴더를 신뢰할지도 물었다(저장소 폴더를 신뢰로 선택).

## 판정

| 질문 | 결론 | 근거 |
|---|---|---|
| V04-03 진행 가능한가 | **Claude Code·Codex 두 경로로 진행 가능.** 절차서 기준 세 조건(두 도구 이상 P1 구독 성공, P3 실행 전 거절, 과금 변수 없음)을 충족한다. 두 도구 모두 깨끗한 문맥과 구독 인증을 함께 얻는 조합도 관측됐다(Codex P4, Claude P4b). **Antigravity는 조건부** — P3에서 잘못된 값을 조용히 무시했고(설계 입력 6), 약관상 구동 허용 여부(F31)가 사용자 결정으로 남아 있다. 크레딧 자동 사용은 이 계정에서 꺼져 있다(정책 표). **정정(PR #4 R02):** "진행 가능"은 adapter 배선과 conformance 시험을 시작할 수 있다는 뜻이다. 실제 독립 초안 수집은 문맥·권한 conformance를 통과한 경로에 한한다. "깨끗한 문맥"은 사용자 설치분이 줄었다는 관측이다(설계 입력 1·2) | P1, P3, P3b, P4, 정책 확인 |
| Q1: ACP 우선인가 exec 우선인가 | **exec 우선으로 확정**(사용자가 판단을 claude 세션에 맡김, 2026-09-23). 세 CLI 모두 help에 ACP가 없고, 세 CLI 모두 비대화형 실행(`claude -p`, `codex exec --json`, `agy -p --output-format json`)이 구독 인증으로 관측됐다. ACP는 필요할 때 adapter 계층의 선택지로 남긴다 | tier 1, P1 |

## 열린 문제

- Antigravity의 다른 값 옵션(`--effort`, `--model` 등)도 없는 값을 조용히 무시하는지. 특히 없는 `--model` 값이 기본 Flash로 바뀌는지는 상급 모델 배정에 직결된다. 갱신(PR #4 R07): `--model`은 문서상 오류 종료다 — 1.2.8에서 확인할 것. `--effort`는 문서에 없다.
- Codex와 Antigravity 결과에 모델 이름이 없다. 실제로 요청한 모델이 답했는지 확인할 방법.
- Antigravity 약관 6조가 공식 CLI를 하위 프로세스로 구동하는 경우에 해당하는지(F31). 사용자는 AionUi 같은 도구에서 agy가 잘 동작했다고 한다 — 기술적으로 되는 것과 약관상 허용되는 것은 별개라서 사용자 결정으로 남긴다.
- Claude Code CLI는 데스크톱 앱과 자격증명과 한도를 공유한다(E04). 이 프로젝트의 호출이 사용자의 평소 Claude 사용 한도를 함께 줄인다는 뜻이다.
