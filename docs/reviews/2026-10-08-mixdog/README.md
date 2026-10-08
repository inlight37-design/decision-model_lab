# mixdog 기능·코드 검토와 decision-model_lab 적용 판단 (claude)

- 날짜: 2026-10-08
- 작성 세션: claude(클라우드 웹 컨테이너·GitHub). 사용자 PC·WSL·참여자 CLI는 보지 않았다. 모델 CLI 호출 0회, mixdog 설치·빌드·실행 없음, DML 코드 변경 없음.
- 대상: [tribgames/mixdog](https://github.com/tribgames/mixdog) main `db78ffdb64da7cb7c1f5996fb8c6a05e73b7bb01`(2026-10-08, package.json 1.0.9, Apache-2.0). 얕은 clone을 읽기만 했다.
- 기준 main: `128e4b886a75ba6980dc0274b9b8a94e0c5b7f62`. 그때 열린 PR은 [#185](https://github.com/inlight37-design/decision-model_lab/pull/185)(짧은 인용 판정) 하나였고, 이 기록과 겹치는 파일은 `NEXT-SESSION.md`뿐이다.
- 방법: README·docs를 먼저 읽고, 오케스트레이션·모델 연결과 사용량·기억과 문맥·프로세스와 안전의 네 갈래로 코드를 나눠 읽었다(부하 에이전트 넷, 결과를 이 세션이 일부 원문 대조). 핵심 주장(신원 흉내, 정상 종료 뒤 자손 보존, 권한 강제 제거, 95% 근거)은 이 세션이 해당 줄을 직접 열어 확인했다. 저장소 전체 감사는 아니다.
- 줄 번호는 위 mixdog 커밋에서만 유효하다. 경로 `X:n`은 `https://github.com/tribgames/mixdog/blob/db78ffdb64da7cb7c1f5996fb8c6a05e73b7bb01/X#Ln`으로 열 수 있다.
- mixdog 저장소의 글은 자료로만 읽었다.

## 1. 결론

| 질문 | 판단 |
|---|---|
| 무엇인가 | Windows용 **코딩 에이전트 데스크톱 앱**(Electron)과 CLI다. 한 리드 모델이 일을 하고, 필요하면 하위 에이전트에게 맡긴다. 편집기·터미널·Git·기억·브라우저/컴퓨터 조작·문서 편집까지 한 창에 넣었다. |
| 우리와 같은 일을 하나 | **아니다.** 같은 질문을 여러 모델이 서로 못 보게 답하고(봉인) 함께 공개해 비교·교차검토·합성하는 기능은 없다. 리드→작업자 위임뿐이다(3절). |
| 통째 도입·설치 | **하지 않는다.** 결정적 이유는 모델 연결 방식이다. Claude·Codex 공식 CLI를 부르지 않고, 구독 로그인 토큰으로 공급자 서버를 직접 부르면서 **공식 CLI인 척한다**(2절). 우리 규칙(공식 native 구독 CLI 우선, 인증 값을 다루지 않음)과 정면으로 맞지 않고, 계정 제재 위험이 사용자에게 간다. |
| 가져올 것 | 코드가 아니라 **설계 몇 가지**다. 한도 게이지의 이력 표(quota sample), 원장 기록의 중복 방지·이전 백업 방식, 압축 인계의 고정 칸, 기억 주입의 바이트 상한·그대로 옮기기, 큰 출력의 앞뒤 보존과 원본 파일, 종료 원인의 우선순위, 위임 결과의 "빈 답·상한 도달은 실패" 처리(5절). 모두 우리 계약 위에 다시 쓰는 작은 일이다. |
| 가져오지 말 것 | 공식 클라이언트 흉내, 계정 돌려쓰기, 프롬프트로만 거는 권한, 정상 종료 뒤 자손 살려 두기, 근거 없는 수치(6절). |

한 줄로: **mixdog는 "한 모델을 싸고 길게 쓰는 법"에 강하고, 우리는 "여러 모델의 답을 독립적으로 받아 믿을 수 있게 비교하는 법"을 만든다.** 겹치는 곳은 사용량 장부·기억 주입·실행 수명 같은 주변 부품이고, 거기서 몇 가지를 배울 수 있다.

## 2. 모델을 부르는 방식 — 가장 중요한 차이

mixdog는 `claude`·`codex` 실행 파일을 자식 프로세스로 부르지 않는다. 공급자 서버에 직접 HTTP 요청을 보내고, 그 요청을 공식 CLI가 보낸 것처럼 꾸민다.

| 공급자 | 코드에서 확인한 것 |
|---|---|
| Claude 계정 | 자체 PKCE 로그인에 Claude Code의 것으로 표시된 client id를 쓴다(`src/runtime/agent/orchestrator/providers/anthropic-oauth-credentials.mjs:36-60`). 모든 요청에 `claude-cli/<버전> (external, sdk-cli)` user-agent와 `x-app: cli`(`anthropic-oauth-client-version.mjs:100-104`). 버전은 npm의 최신 Claude Code 판이나, 서버가 "이 버전은 이 모델을 지원하지 않음"이라고 거절하면 그 문구에서 요구 판을 배워 저장하고 다시 보낸다(같은 파일 :111-130). Haiku가 아닌 모델에는 시스템 프롬프트 맨 앞에 "You are Claude Code, Anthropic's official CLI for Claude."를 넣는다. 주석은 Opus/Sonnet OAuth가 이 접두어로 걸러진다고 적었다(`anthropic-oauth.mjs:81-95`). |
| ChatGPT/Codex 계정 | `chatgpt.com/backend-api/codex/responses`에 originator `codex_cli_rs`로 보낸다(`openai-codex-endpoints.mjs:10-21`). user-agent는 `codex_cli_rs/<npm Codex 판>`(`codex-client-meta.mjs`). 요청마다 Codex 설치 ID·턴 정보를 만들어 붙이는데, 그 안에 `sandbox: 'none'`, `sandbox_mode: 'danger-full-access'`를 적는다(`openai-codex-metadata.mjs:140-160`). 실제 Codex 세션이 아닌 합성 원격 측정이다. |
| 사용량 조회 | Codex `chatgpt.com/backend-api/wham/usage`, Claude `api.anthropic.com/api/oauth/usage`를 user-agent `claude-code/2.0.0`으로 직접 부른다(`oauth-usage.mjs`). |
| 위험 표시 | Cursor·Antigravity OAuth는 기본 꺼짐이고 켤 때 "계정 제한 같은 불이익 위험이 크다"를 확인해야 한다(`src/runtime/shared/developer-options.mjs:10-33`, README). **Claude·ChatGPT OAuth에는 그런 경고가 없다** — 같은 흉내 기법을 쓰는데도 그렇다. |
| 여러 계정 | 한 계정이 한도로 거절하면 연결된 다른 구독 계정으로 돌린다(`account-pool.mjs`). |

우리 쪽: 사용자 결정 2절 6·13·22와 AGENTS.md의 "Official native subscription CLIs first", 인증 값을 읽거나 적지 않는다는 규칙에 그대로 걸린다. 공식 CLI가 하는 권한·샌드박스·훅 처리를 건너뛰므로 우리의 strict 참여자 계획·재관측 체계(SETUP 4절)와도 이어 붙일 수 없다. **이 경로는 참고 대상이 아니다.** mixdog가 "Codex와 같은 성능, 토큰 63% 절감"이라고 할 때도 그 Codex 쪽 측정은 공식 CLI, mixdog 쪽은 이 직접 호출 경로다.

mixdog는 사용자의 `~/.claude`·`~/.codex` 로그인 파일을 읽지 않고, 자기 데이터 폴더에 따로 토큰을 둔다(`openai-oauth-tokens.mjs:42-50`). 이 점은 사실대로 적어 둔다.

## 3. 기능과 코드 구조

### 3.1 저장소 지도

| 위치 | 하는 일 |
|---|---|
| `src/cli.mjs`, `src/repl/`, `src/tui/` | 터미널 실행 입구와 화면 |
| `src/headless-exec.mjs`, `src/headless-json-lifecycle.mjs` | `mixdog exec` 한 번 실행. `--json`은 `thread.started`→`turn.*`→`item.*`→`result` JSONL |
| `src/runtime/agent/orchestrator/` | 세션 루프, 도구 실행, 공급자 연결(`providers/`), 압축(`session/compact/`), 캐시 전략, 하위 에이전트 위임 |
| `src/session-runtime/` | 에이전트 도구(spawn/send/cancel 등), 플러그인·기억 주입 |
| `src/agents/<역할>/AGENT.md` | worker·heavy-worker·reviewer·security·maintainer·writer·front-worker 역할 지시문 |
| `src/rules/{lead,agent,shared}/` | 리드·작업자 공통 규칙 |
| `src/workflows/*/WORKFLOW.md` | 워크플로 = 프롬프트 본문뿐(분기·팬아웃 로직 없음) |
| `src/runtime/shared/llm/` | 사용량 원장(SQLite), 한도 이력, 가격, 추정 |
| `src/runtime/memory/` | 기억: 내려받는 PostgreSQL 16 + pgvector, 대화 수집·요약·검색 |
| `native/` (Rust) | `mixdog-spawn`(자식 프로세스 실행·종료), `mixdog-patch`(원자적 파일 편집), `mixdog-graph`(tree-sitter·ast-grep 코드 그래프), `mixdog-computer`, `mixdog-browser-import` |
| `apps/desktop/` | Electron 앱(Monaco 편집기, 터미널, Git/GitHub, 브라우저·컴퓨터 조작 승인) |
| `apps/relay/` | 휴대폰 원격 연결 중계 서버 |
| `benchmarks/terminal-bench-2.1/` | 벤치 결과·재계산 스크립트 |

### 3.2 위임(오케스트레이션)

- 리드가 `agent` 도구로 하위 에이전트를 띄운다(`src/session-runtime/services/agent-tool/tool-def.mjs:19-60`). 하위 에이전트는 **리드의 대화 전체가 아니라 짧은 지시문(brief)만** 받는다(`src/rules/lead/LEAD.md`, `spawn-flow/spawn-plan.mjs:63-86`). 결과는 리드 세션에 알림으로 들어온다.
- 같은 `tag`로 다시 부르면 이어 쓰거나, 끝났으면 같은 이름으로 다시 띄운다(`execute-spawn.mjs:10-53`).
- "Solo→Swarm" 단계는 **프롬프트 문구만 바꾼다**(`runtime-core/orchestration.mjs:3-46`). 실제 상한은 프로세스 전체의 동시 에이전트 8·셸 8(`src/runtime/shared/resource-admission.mjs:11-18`)과 소유자별 공정 대기열(`fair-call-scheduler.mjs`, `owner-fair-gate.mjs`)이다.
- 역할별 모델은 `config.agents[<역할>]`에 provider·model·effort를 적는다(`spawn-preset.mjs:5-60`).
- 빈 답·반복 상한 도달·잘림은 "완료"가 아니라 오류로 올린다(`spawn-run.mjs:93-109`). 진행이 멈추면 역할별 대기 상한(작업자 300초 등) 뒤 끊고, 그때까지 쓴 글은 "부분"으로 표시해 돌려준다(`stall-policy.mjs`, `spawn-run.mjs:170-183`).
- 같은 실패 호출 3회 반복 차단, 도구 없는 "아직 안 끝남" 이어 쓰기 8회 상한(`session/loop/loop-state.mjs:13-17`, `no-tool-turn/continuation.mjs`).
- **토큰·비용 상한은 없다.** Goal에는 시간 예산만 있다(`goal-state.mjs`).
- **검토자(reviewer)도 읽기 전용이 강제되지 않는다.** "Runtime permission enforcement was removed (every tool call is trusted)"(`agent-runtime/agent-dispatch/session-prep.mjs:67`). 역할 권한은 지시문 글일 뿐이다. 다만 리드가 자기 검토를 "독립 검토"라고 부르지 말라는 문구는 좋다(`runtime-core/orchestration.mjs:40-45`).

### 3.3 사용량과 한도

- 원장은 `node:sqlite`, WAL, `synchronous=FULL`(`src/runtime/shared/llm/usage-ledger.mjs`). 숫자만 저장하고 프롬프트·인증은 저장하지 않는다.
- 기록 ID는 공급자 응답 ID, 없으면 내용 해시. 같은 ID는 건너뛴다. 기록과 일별 집계를 한 거래로 쓴다.
- 실패·중단된 시도도 공급자가 알려 준 만큼만 기록하고 "토큰을 지어내지 않는다"(`usage-accounting.mjs:19-110`).
- 스키마 이전 전에 `VACUUM INTO`로 백업하고, 이전 뒤 행 차이·개수·FK로 확인한다(`usage-ledger.mjs:145-192`).
- **한도 이력 표** `quota_samples(provider, account, label, ts, seen_until, used_pct, reset_at)`. 같은 값이 다시 보이면 `seen_until`만 늘리고, 값이 5포인트 넘게 떨어지거나 초기화 시각이 2분 넘게 바뀌면 새 창으로 본다(`usage-ledger-quota.mjs:19-35, 89-133`). 소진 속도 예측과 "내 사용/바깥 사용" 나누기는 코드 스스로 추정이라고 적는다(`quota-value-estimate.mjs`).
- `mixdog exec`는 응답마다 사용량 파일을 원자적으로 다시 써서, 강제 종료돼도 쓴 양이 남는다(`src/headless-exec.mjs:26-57`).

### 3.4 기억과 문맥 줄이기

- **기억 저장소**는 앱이 내려받는 PostgreSQL 16 + pgvector다(`src/runtime/memory/data/runtime-manifest.json`). 대화 전체를 받아 10분마다 모델 한 번으로 압축하고, 검사는 모양만 본다. 요약이 의미상 맞는지·손실 없는지는 보장하지 않는다고 문서가 직접 쓴다(`docs/memory-chunk-quality.md`).
- **자동으로 프롬프트에 들어가는 것은 사용자가 정한 핵심 기억뿐**이고, 생성된 기록은 넣지 않는다(`dbLines: []`, `lib/core-memory-file.mjs:145-148`). 32 KiB 바이트 상한, 사용자 문장을 그대로, 중복 제거, 자른 곳 표시(`src/session-runtime/cwd-plugins/core-memory-context.mjs:8-28`). 프롬프트를 만들 때 DB를 열지 않고 판 번호가 붙은 JSON 스냅숏을 읽는다. 최근 커밋 `cb136dde`부터는 기억 스위치를 꺼도 이 블록은 들어간다(스위치는 도구만 끈다).
- **압축 인계**는 Goal·Constraints·Progress(Done/In Progress/Blocked)·Key Decisions·Next Steps·Critical Context·Relevant Files 일곱 칸이 고정이고, 빈 칸은 "(none)"(`session/compact/summary-schema.mjs:10-18`). "실제 도구 결과가 요약보다 우선"이라는 머리말을 붙인다. 칸이 빠지면 정해진 틀로 고치고, 꼭 필요한 문맥이 예산에 안 들어가면 **조용히 자르지 않고 오류**를 낸다(`session/compact/runner.mjs:528-576`).
- **큰 출력**: 도구별 바이트 상한(일반 50 KB, grep 5 KB 등, 줄 단위로 자르고 이어짐 표시, `src/runtime/shared/tool-output-limit.mjs`). 셸 출력이 넘치면 원본을 파일로 두고 앞·뒤와 생략 바이트 수·경로만 모델에 보인다(`tools/shell-exec-output.mjs:187-213`). 성공한 테스트 출력은 한 줄 요약으로 접는데, 종료 0·시간 초과 없음·error/warning/failed 단어 없음일 때만, 원본을 먼저 저장한 뒤에만 한다(`tools/builtin/shell-lossless-compact.mjs`).

### 3.5 실행 수명과 안전

- `native/mixdog-spawn`(Rust)이 자식을 띄운다. POSIX는 프로세스 그룹, Windows는 Job Object. 시간 초과·취소·오류·강제 종료를 종료 코드보다 먼저 판정한다(`native/mixdog-spawn/src/main.rs:167-213`).
- **루트가 정상 종료하면 자손을 일부러 살려 둔다**(`main.rs:365-369`의 `preserve_descendants`). 뒤에 남은 프로세스를 다시 찾아 끄고 재확인하지만(`tools/lib/shell-descendants.mjs`), POSIX는 같은 프로세스 그룹만 보므로 그룹을 벗어난 자손은 못 본다. 그래도 못 끈 경우 "확인 안 됨"으로 정직하게 보고한다.
- **격리는 없다.** namespace·seccomp·제한 토큰이 없고, 셸은 정규식 거부 목록과 승인 질문으로만 막는다. 헤드리스 `exec`는 승인 없이 모든 도구를 쓴다(`approvalMode: 'implicit'`, `src/headless-exec.mjs`). README도 "오프라인 샌드박스가 아니다"라고 쓴다.
- 자식 메모리·CPU 상한은 없다(동시 개수만 제한, `resource-admission.mjs`의 "memory thresholds are diagnostic only").
- 좋은 부품: 원자적 쓰기(임시 파일 `wx`·fsync·rename·디렉터리 fsync, `src/runtime/shared/atomic-file.mjs:158-237`), 소유자 기록을 하드 링크로 게시하는 잠금(`file-lock.mjs:318-328`), PID와 시작 시각을 함께 보는 생존 확인(`process-lifecycle.mjs:161-258`), 브라우저 조작 승인을 대상·30초 만료·1회용으로 묶는 방식(`apps/desktop/src/main/browser/action-approval.ts:58-123`).
- CI에서 POSIX 자손 종료 시험은 Linux에서 건너뛴다(`scripts/shellhardening/guardians-background.slow.test.mjs:246-251`).

### 3.6 벤치마크 읽는 법

- Codex 비교는 89과제 × 5회, 공식 Harbor 채점, 원자료·재계산 스크립트 공개로 비교적 단단하다(`benchmarks/terminal-bench-2.1/README.md`).
- 한계: Claude Code 비교는 과제당 1회(README 스스로 편차 범위라고 씀). 63%는 캐시 입력을 포함한 총 토큰이고 비용 차이는 39%. 측정한 것은 v1.0.9가 아니라 고정된 이전 소스. 기억·위임은 끈 채로 쟀다. 같은 과제 묶음으로 프롬프트를 다듬은 흔적(`analysis/` 아래 diet 파일들)이 있어 과적합 가능성이 있다(추정). 그리고 2절대로 mixdog 쪽은 공식 CLI가 아니다.
- README의 "터미널 출력의 95%를 걸러 낸다"(`README.md:108`)는 계산한 스크립트나 자료를 찾지 못했다. 근거 없는 수치로 본다.

## 4. 우리가 이미 더 단단한 곳 (바꾸지 않는다)

| 주제 | mixdog | DML |
|---|---|---|
| 모델 연결 | 공식 CLI 흉내로 직접 호출 | 공식 CLI를 strict 계획·관측 기록으로 실행 |
| 독립성 | 없음(위임만) | 봉인·동시 공개·독립 정족수 |
| 종료 확인 | 정상 종료 시 자손 보존, 그룹 단위 확인 | bwrap PID namespace + `--die-with-parent`, `tree_confirmed_empty`가 참일 때만 자원 해제(`core/runner.py`, `core/isolation.py`) |
| 권한 | 프롬프트 글뿐, 헤드리스는 암묵 승인 | 논의자 읽기 전용을 실행기에서 강제 |
| 예산 | 시간만 | 호출마다 새 원장·provider별 상한 |
| 기억 | 스위치를 꺼도 핵심 기억 주입 | 격리 팀원 제외를 코드에서 결정(2절 27), 실행별 끄기 |

## 5. 가져올 만한 것과 붙일 곳

모두 **원리만 가져와 우리 코드로 다시 쓴다.** 모델 호출이 늘지 않는다. 우선순위 순서다.

| # | 아이디어 (mixdog 위치) | 우리 쪽 붙일 곳 | 크기·조건 |
|---|---|---|---|
| M1 | **한도 이력 표.** 값·`seen_until`·초기화 시각, 5포인트 하락이나 초기화 시각 변화로 새 창 판정, 관측 사이 빈 구간은 "미측정"(`usage-ledger-quota.mjs`) | 지금 [`app/account_quota.py`](../../../app/account_quota.py)는 마지막 스냅숏 하나만 든다. Codex 앱 서버 조회값과 Claude `rate_limit_event`(`core/quota.py`)를 같은 표에 쌓으면 게이지에 "언제부터 얼마나 썼나"를 보일 수 있다. 2절 5(상태 표시에 모델을 더 부르지 않음)를 그대로 지킨다 | S–M. 원장 스키마 변경이 필요하면 schema 판을 올리고 이전 백업 규칙을 따른다 |
| M2 | **원장 기록의 중복 방지와 이전 검증.** 공급자 응답/세션 ID를 키로, 없으면 내용 해시. 기록과 집계를 한 거래로. 이전 전 `VACUUM INTO` 백업 + 행 차이 확인(`usage-ledger.mjs`) | [`app/execution/invocations.py`](../../../app/execution/invocations.py)의 예약 쓰기, 스키마 이전 경로. 이미 자동 백업은 있으므로 "이전 뒤 행 차이 확인"만 비교 대상 | S. 먼저 지금 이전 코드에 같은 확인이 있는지 대조 |
| M3 | **"없음은 0이 아님".** 캐시 읽기·캐시 쓰기·추론 토큰을 따로 두고 모르는 값은 null, 공급자별로 입력에 캐시가 포함되는지 표시(`cost.mjs:18-40`, `reasoning-usage.mjs`) | [`app/usage.py`](../../../app/usage.py)의 `FIELDS`·`CACHE_READ`. Codex `input_tokens`는 캐시 포함, Claude는 제외라는 차이를 화면 합계에 명시 | S. 실제 출력 필드는 관측 기록으로 확인한 뒤 |
| M4 | **압축 인계의 고정 칸과 "자르지 말고 실패"**(`session/compact/summary-schema.mjs`, `runner.mjs:528-576`) | 다듬기·다음 단계 제안·결과 모으기의 상위 역할 입력. 그리고 사람용 인계(카드 체크포인트 다섯 줄)와 맞춰 볼 만하다. 격리 팀원의 봉인 입력에는 쓰지 않는다 | S. 프롬프트 감사(2026-09-29)의 출력 계약 규칙을 따른다 |
| M5 | **기억 주입: 바이트 상한·원문 그대로·자른 곳 표시·생성 요약은 넣지 않음**(`core-memory-context.mjs`, `core-memory-file.mjs:145-148`) | [`app/memory.py`](../../../app/memory.py)의 크기 상한·발췌. 이미 크기 상한과 선택 이유가 있으므로 "자른 곳 표시"와 "모델 요약이 아닌 원장 기록만"이 지켜지는지 대조. 반대로 "스위치를 꺼도 주입"은 따라 하지 않는다 | S |
| M6 | **큰 자료·출력의 앞뒤 보존과 원본 파일**: 줄 단위로 자르고, 원본 경로·크기·sha256을 함께 보이고, 원본을 먼저 저장한 뒤에만 줄임(`tool-output-limit.mjs`, `session/tool-result-offload.mjs`) | 자료 미리보기·입력 고정([`app/context/inputs.py`](../../../app/context/inputs.py), [`app/source_document.py`](../../../app/source_document.py)). 격리 팀원 둘에게는 **같은 줄인 판**이 가야 한다 | S–M. 1 MiB 자료에서 Claude가 180초를 넘긴 문제(인계 1절)와 연결해 볼 수 있다 |
| M7 | **종료 원인 우선순위**: 시간 초과 > 취소 > 오류 > 강제 종료 > 종료 코드(`native/mixdog-spawn/src/main.rs:167-213`) | [`core/runner.py`](../../../core/runner.py)·`core.adapters.interpret`. 이미 "exit 0은 성공이 아님"이 있으므로 순서가 명시돼 있는지만 대조 | S, 대조만 |
| M8 | **위임 결과의 실패 승격과 부분 답 표시**: 빈 답·상한 도달·잘림은 오류, 멈춤으로 끊긴 답은 "부분"으로 표시(`spawn-run.mjs`) | GR-1 이후 일반 팀원·오케스트레이터 경로. 부분 답은 정족수·취합에 세지 않는다 | S, GR 카드의 완료 조건 한 줄로 |
| M9 | **자리별 고정 이름표**: 같은 tag로 이어 쓰기·다시 띄우기(`execute-spawn.mjs`) | 역할판 칸 = 고정 이름표. 일반 칸의 이어 쓰기를 넣을 때 참고 | 나중에 |
| M10 | **승인을 대상·만료·1회용으로 묶기**(`action-approval.ts`) | 앞으로 사용자 승인 버튼(실제 모델 호출 확인 등)을 늘릴 때 | 나중에 |

참고(우리 쪽 숙제와 이어지는 것): mixdog에는 자식 메모리·CPU 상한이 없다. 우리 인계 4절의 K10(CPU·메모리 상한)은 mixdog에서 배울 것이 없고, bwrap 실행을 cgroup v2 칸에 넣어 `memory.max`·`pids.max`를 주고 `cgroup.events`의 `populated 0`을 두 번째 종료 증거로 쓰는 쪽을 따로 시험해야 한다(이 세션의 제안이며 WSL2에서 cgroup 위임이 되는지는 미확인).

## 6. 가져오지 말 것

- **공식 클라이언트 흉내 전부**: CLI user-agent·버전 추적·"You are Claude Code" 접두어·Codex 설치/턴 메타데이터·빌린 client id. 공급자 백엔드와 사용량 엔드포인트를 구독 토큰으로 직접 부르는 것도 같다. 규칙 위반이고 계정 위험이 있다.
- **계정 돌려쓰기**와 Codex 초기화 크레딧 자동 사용.
- **프롬프트로만 거는 권한·모드**(검토자 읽기 전용, Solo→Swarm). 우리는 실행기에서 강제한다.
- **정상 종료 뒤 자손 보존**, 프로세스 그룹을 트리 전체로 보는 것, PID만 보는 생존 확인.
- **스위치를 꺼도 들어가는 기억**, 요약을 격리 입력에 넣는 것, 참여자 사이에 캐시나 중복 참조를 공유하는 것.
- **근거 없는 수치**(95%)와 1회 측정 비교를 결론처럼 쓰는 것.
- 통째 설치, PostgreSQL 기억 서버, Electron 작업 공간. 우리 앱의 범위(결정 비교)와 맞지 않고 무겁다.

## 7. 라이선스

- mixdog 본체는 Apache-2.0이다(`LICENSE`). 코드를 옮겨 오면 저작권·라이선스 고지와 변경 표시를 함께 가져와야 하고, Codex CLI 코드 일부를 담고 있어 그 NOTICE도 따라온다(`LICENSES/codex-NOTICE.txt`, `NOTICE.md`).
- 일부 구성 요소는 다른 라이선스다(MIT, BSD, MPL-2.0의 stylua, 선택적 GPL 브라우저 비밀번호 가져오기 부품 등, `NOTICE.md`).
- 위 5절은 **설계만 참고**하고 코드를 복사하지 않는 전제다. 그러면 라이선스 의무는 생기지 않는다. 코드를 옮기게 되면 그 PR에서 고지를 함께 넣는다.
- 2절의 직접 호출 방식이 각 공급자 약관에 맞는지는 판단하지 않았다(검토 범위 밖). 우리에게는 이미 우리 규칙으로 답이 정해져 있다.

## 8. 검증 범위

- 한 것: mixdog 고정 커밋의 README·docs·코드 읽기. 2절의 user-agent·시스템 접두어·Codex 메타데이터, 3.2의 권한 강제 제거 주석, 3.5의 `preserve_descendants`와 동시 실행 기본값, 3.6의 95% 문장은 이 세션이 원문 줄을 직접 열었다. 나머지 줄 번호는 부하 에이전트가 읽고 보고한 것이다.
- 하지 않은 것: mixdog 설치·빌드·시험 실행, 벤치 재계산, 실제 계정 연결, 모델 호출. 공급자가 2절의 요청을 실제로 받아 주는지, 제재가 있는지는 관측하지 않았다. DML 쪽 붙일 곳(5절)은 파일 위치까지만 확인했고 각 항목이 이미 구현돼 있는지의 세부 대조는 그 카드에서 한다.
- 외부 수치(토큰 절감·비용)는 mixdog의 주장이며 이 기록에서 확인한 사실이 아니다.
