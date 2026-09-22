# V04-01 런타임 인벤토리 — 절차서

**목적:** 실제로 운용할 PC에서 세 CLI(Claude Code, Codex, Antigravity `agy`)의 상태를 비밀 값 없이 기록한다. 이 결과로 V04-03(두 CLI의 읽기 전용 독립 답변) 진행 여부와 Q1(ACP 우선인가 exec 우선인가)을 정한다. 완료 조건 원문은 [03-evaluation-and-roadmap의 V04-01](../../architecture/v0.4/03-evaluation-and-roadmap.md)이다.

**문서만 보고 `configured = true`로 만들지 않는다.** 설치·help에 플래그가 있다는 것도 관측이 아니다.

| 단계 | 내용 | 한도 소모 | 누가 |
|---|---|---|---|
| 0 | 기기·브랜치·터미널 정하기 | 없음 | 사용자 |
| 1 | 설치 | 없음 | **사용자** |
| 2 | 자동 기록 — tier 1 (`--version`, `--help`만) | 없음 | 사용자 또는 AI 세션 |
| 3 | 로그인 | 없음 | **사용자** — AI는 계정 비밀번호를 입력하지 않는다 |
| 4 | 관측 — tier 2 (짧은 호출 몇 번) | 소량 | 사용자가 한 줄씩 |
| 5 | 정책 확인 (문서 읽기) | 없음 | 사용자 또는 AI 세션 |
| 6 | 결과 정리와 판정 | 없음 | AI 세션 + 사용자 확인 |

명령은 **2026-09-23**에 공식 문서에서 확인했다(맨 아래 출처). 설치 명령과 플래그는 바뀔 수 있으니 실행 전에 한 번 더 본다.

---

## 0. 시작 전

- **기기 이름표**를 정한다. 예: `main-pc`. 실제 hostname은 쓰지 않는다. 결과는 `hosts/<이름표>/`에 쌓인다.
- **일반 PowerShell 창**에서 실행한다. AI 도구 안의 터미널은 자기 환경변수를 넣는다 — 보조 PC의 Claude 데스크톱 앱 셸에는 `CLAUDECODE`, `ANTHROPIC_BASE_URL` 등 26개가 있었다. 그 창에서 잰 환경은 사용자의 실제 환경이 아니다. **AI 세션이 대신 실행한다면** tier 1에 `--fresh-env`를 붙인다(Windows) — 그 변수들을 빼고 PATH를 사용자·시스템 설정으로 다시 만든 환경에서 잰다.
- 저장소를 최신으로 받고, 작업 브랜치를 만든다. 브랜치 이름 규칙은 [협업 규칙](../../COLLABORATION.md) 3절.

```powershell
git clone https://github.com/inlight37-design/decision-model_lab
cd decision-model_lab
git config core.hooksPath .githooks
git switch -c human/v04-01-main-pc-20260924
```

이미 clone이 있으면 `git pull`만 한다. Python 3.12 이상이 필요하고 pip 설치는 필요 없다.

## 1. 설치 — 사용자

공식 주소만 쓴다. 설치 스크립트는 인터넷에서 받은 코드를 실행하므로 제3자 안내나 미러를 따르지 않는다. 설치 후에는 **새 PowerShell 창**을 열어 PATH를 반영한다.

| 도구 | Windows PowerShell (권장) | 대안 | 확인 |
|---|---|---|---|
| Claude Code | `irm https://claude.ai/install.ps1 \| iex` | `winget install Anthropic.ClaudeCode` | `claude --version`, `claude doctor` |
| Codex | `powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 \| iex"` | `npm install -g @openai/codex` (Node.js 필요) | `codex --version` |
| Antigravity | `irm https://antigravity.google/cli/install.ps1 \| iex` | — | `agy --help` (`--version`은 문서에 없음) |

알아 둘 것:

- **Claude Code 기본 설치는 백그라운드에서 스스로 업데이트된다.** 실험 도중 버전이 바뀔 수 있으므로 매번 버전을 기록한다(tier 1 도구가 한다). 고정하려면 WinGet 설치나 버전 지정 설치를 쓴다: `& ([scriptblock]::Create((irm https://claude.ai/install.ps1))) <버전>`.
- Claude Code는 Git for Windows가 있으면 Bash 도구를, 없으면 PowerShell 도구를 쓴다. 이 저장소의 검사에는 영향이 없다.
- **Codex의 Windows 샌드박스:** 권장 모드(elevated)는 설정할 때 관리자 승인이 필요하고 로컬 사용자·방화벽·정책을 바꾼다. **보안 설정 변경이므로 사용자가 직접 판단한다.** 설정하지 못하면 제한된 토큰과 ACL 기반 모드(unelevated)로 내려간다. 어느 쪽이 적용됐는지 결과에 적는다 — 읽기 전용 보장의 근거가 달라진다.
- **Claude Code 설치 프로그램이 PATH를 등록하지 않을 수 있다.** 보조 PC(2.1.280)에서 설치는 성공했지만 `~\.local\bin is not in your PATH`라고 안내하고 끝났다. 그러면 사용자 PATH에 `%USERPROFILE%\.local\bin`을 추가하고 새 창을 연다. Codex와 Antigravity는 스스로 등록했다.
- 설치 후 서명을 확인한다: `Get-AuthenticodeSignature (Get-Command claude).Source` — Anthropic, PBC / OpenAI OpCo, LLC / Google LLC이고 `Valid`여야 한다.
- **데스크톱 앱에 들어 있는 CLI는 PATH에 없을 수 있다.** 보조 PC에서는 앱들이 남긴 로그인 파일(`~/.codex/auth.json`, `~/.claude/.credentials.json`)은 있는데 CLI는 PATH에 없었다. tier 1 도구는 PATH 기준으로만 찾는다.

## 2. 자동 기록 — tier 1 (한도 소모 없음)

로그인과 무관하므로 설치 직후, 로그인 전에 해도 된다.

```powershell
python tools/runtime_inventory.py --host-label main-pc --dry-run
python tools/runtime_inventory.py --host-label main-pc
python tools/runtime_inventory.py --validate docs/experiments/v04-01-inventory/hosts/main-pc/manifest.json
```

AI 도구 안에서 실행할 때는 앞의 두 줄에 `--fresh-env`를 붙인다.

- 첫 줄은 실행할 명령과 **실제로 실행될 파일 경로**만 보여 주고 아무것도 실행하지 않는다. 실제로 도는 것은 각 CLI의 `--version`과 `--help`뿐이다.
- **경로가 CLI가 아니면 멈춘다.** Windows는 대소문자를 가리지 않아서, 데스크톱 앱 폴더가 PATH에 있으면 `claude`가 GUI 앱 `Claude.exe`로 풀릴 수 있다.
- 결과는 `hosts/main-pc/manifest.json`과 `hosts/main-pc/help/*.txt`다. 홈 경로와 비밀처럼 보이는 문자열은 가려서 쓴다.
- **환경변수 경고가 나오면 멈춘다.** `ANTHROPIC_API_KEY`가 있으면 `claude -p`는 묻지 않고 그 키를 쓴다(API 과금). 값은 기록하지 않는다. 해당 변수를 어떻게 할지는 사용자가 정한다.
- 커밋 전에 `help/` 파일을 한 번 훑어 개인 정보가 없는지 본다. 버전이 바뀌면 `--force`로 다시 기록한다.

## 3. 로그인 — 사용자

API 키 경로를 쓰지 않는다. 구독 로그인만 한다. **데스크톱 앱의 로그인이 이미 있으면 CLI도 로그인된 상태일 수 있다** — 보조 PC에서는 Claude Code와 Codex가 설치 직후부터 구독 로그인 상태였다. 먼저 확인하고, 안 돼 있을 때만 로그인한다.

| 도구 | 로그인 | 확인 | 하지 않을 것 |
|---|---|---|---|
| Claude Code | `claude` 실행 → 브라우저 로그인 | `claude auth status` — JSON의 `authMethod`가 `claude.ai`, `apiProvider`가 `firstParty`인지. 대화형 `/status`도 된다 | API 키 승인 프롬프트가 나오면 **거절** |
| Codex | `codex login` (브라우저). 브라우저가 없으면 `codex login --device-auth` | `codex login status` | `codex login --with-api-key` |
| Antigravity | `agy` 실행 → OS keyring 또는 브라우저 로그인 | 상태 확인 명령이 문서·help(1.2.8)에 없음 — tier 2 P1의 성공으로 간접 확인 | `modelProvider: gemini` + `GEMINI_API_KEY` 모드 |

## 4. 관측 — tier 2 (소량 한도)

**저장소 밖의 빈 폴더**에서 한다. 저장소 안에서 돌리면 `CLAUDE.md`·`AGENTS.md`와 프로젝트 설정이 문맥에 들어간다.

```powershell
$w = Join-Path $env:TEMP "v0401-probe"
New-Item -ItemType Directory -Force $w | Out-Null
Set-Location $w
```

각 명령의 출력은 `hosts/<이름표>/tier2/<번호>-<도구>.txt`로 저장하되, **계정 이메일·조직 ID·토큰은 지우고 저장한다.** 결과는 [`RESULTS-TEMPLATE.md`](RESULTS-TEMPLATE.md)를 `hosts/<이름표>/RESULTS.md`로 복사해 채운다. 예상과 다른 결과가 나오면 거기서 멈추고 기록한다 — 다음 명령으로 넘어가지 않는다.

### P1. 구독 인증으로 구조화 출력이 나오는가

| 도구 | 명령 |
|---|---|
| Claude Code | `claude -p "Reply with exactly: OK" --output-format json --permission-mode dontAsk` |
| Codex | `codex exec --json --skip-git-repo-check --ephemeral "Reply with exactly: OK"` |
| Antigravity | `agy -p "Reply with exactly: OK" --output-format json` |

기록: exit code, 세션 ID 필드, 사용량 필드 이름(`total_cost_usd`·`usage`·`input_tokens` 등)과 값의 유무, 응답. Codex `exec`는 기본이 read-only 샌드박스다. Claude의 `total_cost_usd`는 클라이언트 추정치다(F29).

### P2. `--bare`는 구독을 쓰지 않는가 (F25)

```powershell
claude --bare -p "Reply with exactly: OK" --output-format json
```

문서상 `--bare`는 구독 로그인을 읽지 않는다. 2절 자동 기록에서 `ANTHROPIC_API_KEY`가 없었다면 **인증 실패가 정상 관측**이다. 성공했다면 즉시 멈추고 어떤 자격증명으로 돌았는지 확인한다 — API 과금일 수 있다.

### P3. 잘못된 제한 인자가 모델 호출 전에 거절되는가 (F26)

| 도구 | 명령 |
|---|---|
| Claude Code | `claude -p "Reply with exactly: OK" --permission-mode notamode` |
| Codex | `codex exec --skip-git-repo-check --sandbox notamode "Reply with exactly: OK"` |
| Antigravity | `agy -p "Reply with exactly: OK" --output-format notaformat` |

기대: 모델 응답 없이 오류, exit code ≠ 0. **응답이 나왔다면 잘못된 제한을 무시하고 실행하는 경로가 있다는 뜻이다.** 이 프로젝트에서 가장 중요한 관측 중 하나다.

### P4. 깨끗한 문맥과 구독 인증을 함께 얻을 수 있는가 (D11·F25)

| 도구 | 명령 | 기록 |
|---|---|---|
| Claude Code | `claude -p "Reply with exactly: OK" --output-format stream-json --verbose` | 첫 `system/init` 이벤트의 `tools`·`mcp_servers`·`plugins` 이름. `~/.claude/CLAUDE.md` 존재 여부 |
| Codex | `codex exec --json --skip-git-repo-check --ephemeral --ignore-user-config --ignore-rules "Reply with exactly: OK"` | 사용자 설정을 무시해도 ChatGPT 로그인으로 도는가 |
| Antigravity | 해당 플래그를 문서에서 찾지 못함 | "미확인"으로 기록 |

둘 중 하나를 조용히 포기하지 않는다. 동시에 안 되면 그 도구의 blind 초안 한계를 적는다.

### P5. 쓸 수 있는 상급 모델

Claude Code와 Codex는 대화형 `/model` 목록, Antigravity는 `agy models`. **모델 이름만** 적는다. 목록 조회만으로는 한도를 쓰지 않는다.

### P6. 취소 (선택 — V04-03으로 미뤄도 된다)

긴 답을 요구하는 프롬프트를 `-p`/`exec`로 시작하고 몇 초 뒤 `Ctrl+C`. 이어서 남은 프로세스를 본다.

```powershell
Get-Process claude, codex, agy, node -ErrorAction SilentlyContinue | Select-Object Name, Id, StartTime
```

종료가 확인되지 않으면 `UNKNOWN`으로 기록한다. 종료됐다고 가정하지 않는다.

### P7. Codex 한도 조회 경로

tier 1 도구가 `codex --help`에서 `app-server`의 존재를 기록한다. 실제 `account/rateLimits/read` 호출은 JSON-RPC 클라이언트가 필요하므로 V04-03의 adapter 작업으로 넘긴다. 여기서는 "문서 경로 있음, 호출 미시험"으로 적는다.

## 5. 정책 확인 (문서 읽기)

각 문서의 **확인일과 상단 공지 문구**를 적는다. 모르면 "미확인"이다. 추정으로 채우지 않는다.

| 확인할 것 | 문서 |
|---|---|
| Claude 구독으로 Claude Code를 쓰는 조건 | [E04](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan) |
| `claude -p`·Agent SDK의 구독 차감 정책과 보류 공지의 현재 상태 | [E05·F18](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) |
| Codex의 ChatGPT 로그인과 API 키 과금 구분 | [E01](https://learn.chatgpt.com/docs/auth) |
| Antigravity 한도 소진 후 크레딧 자동 사용(`useG1Credits`)이 꺼져 있는가 | [E09](https://www.antigravity.google/docs/cli/credits/) — 설정 변경은 사용자 |
| 'Gemini CLI 소비자 인증이 2026-06-18 종료'라는 서술의 원문 | 원문을 찾으면 그때 원장에 등록한다. `agy`와는 다른 도구다 |
| 요금제별 동시 기기·세션 제한 | 각 요금제 도움말. 찾지 못하면 "미확인" — 가정하지 않는다 |
| 구독 경로가 닫혔을 때의 대안 | 유료 API 전환 / 해당 provider 제외 / 기능 축소 중 **사용자 결정** |

## 6. 결과 정리와 판정

`hosts/<이름표>/RESULTS.md`를 채우고, AI 세션이 그 결과로 tier 2 manifest를 만든다 — 관측한 기능만 `observed`로, 증거 칸에 `RESULTS.md`의 P 번호를 적는다. 검사기가 증거 없는 `observed`와 관측 없는 `configured`를 거절한다.

| 판정 | 조건 |
|---|---|
| **V04-03 진행 가능** | 두 도구 이상에서 P1이 구독 인증으로 성공 **그리고** P3에서 잘못된 제한이 실행 전 거절 **그리고** 과금 경로를 바꾸는 환경변수 없음 |
| **Q1 (ACP 우선 여부)** | ACP를 관측한 도구 수. 없으면 exec 우선으로 전환을 제안하고 ACP는 adapter 계층 후보로 남긴다 |
| **보류** | 위 조건 중 하나라도 "미확인"이면 그 이유와 필요한 다음 확인을 적는다 |

## 7. 하지 말 것

- API 키 설정, `codex login --with-api-key`, Antigravity API 키 모드
- 추가 크레딧·초과 사용 켜기
- `--dangerously-skip-permissions`, `--sandbox danger-full-access`, `--permission-mode bypassPermissions`
- 인증 파일(`.credentials.json`, `auth.json`) 열기·복사·커밋
- 환경변수 전체 출력(`Get-ChildItem Env:`, `set`, `env`)
- 한도 오류를 보려고 반복 호출하기
- 문서만 보고 `configured = true`

## 출처 — 설치·인증 절차 참조용

2026-09-23 확인. 근거 원장(E/F)에 이미 있는 것은 ID를 붙였다. 나머지는 설치 절차 참조이며 원장 항목이 아니다.

| 문서 | 쓴 곳 |
|---|---|
| [Claude Code setup](https://code.claude.com/docs/en/setup) | 설치 명령, 자동 업데이트, `claude doctor` |
| [Claude Code authentication](https://code.claude.com/docs/en/authentication) | 로그인, `/status`, 인증 우선순위(`-p`는 `ANTHROPIC_API_KEY`를 묻지 않고 사용) |
| [Claude Code headless](https://code.claude.com/docs/en/headless) (E06·F25) | `-p`, `--output-format`, `--json-schema`, `--bare`, `--permission-mode`, `system/init` |
| [Codex README](https://github.com/openai/codex/blob/main/README.md) | 설치 명령 |
| [Codex authentication](https://learn.chatgpt.com/docs/auth) (E01) | `codex login`, `--device-auth`, `login status` |
| [Codex non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode) (E02) | `exec`, `--json`, 기본 read-only, `--ephemeral`, `--ignore-user-config` |
| [Codex Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox) | elevated/unelevated, 관리자 승인 |
| [Antigravity install](https://www.antigravity.google/docs/cli/install/) (E07) | 설치 명령, 로그인, API 키 모드 |
| [Antigravity headless](https://www.antigravity.google/docs/cli/headless/) (E08) | `-p`, `--output-format`, soft deny의 exit 0 |
