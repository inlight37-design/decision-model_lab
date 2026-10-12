# 외부 도구 검토 — mixdog와 Concord MCP (2026-10-12)

사용자가 인터넷에서 본 두 도구가 이 프로젝트에 도움이 되는지 나중에 판단할 수 있게 정리한 날짜 기록이다. 하나는 "토큰을 63% 아낀다"는 코딩 에이전트 **mixdog**이고, 다른 하나는 "여러 에이전트를 부릴 때 돕는다"는 **Concord MCP**다.

- 작성: claude 세션, 웹 컨테이너. 사용자 PC와 CLI는 보지 않았고 모델 호출은 하지 않았다.
- 두 저장소는 아래 고정 커밋으로 받아 **읽기만** 했다. 설치하거나 실행하지 않았다. 직접 계산한 것은 mixdog 벤치마크 원자료의 토큰 합계뿐이다.
- 검토 기준은 [인계](../../../NEXT-SESSION.md) 2절의 확정 사항과 이미 정해 둔 절약 우선순위([역할판 검토](../../reviews/2026-09-26-role-board-review/README.md) RB-07·RB-08)다.

## 결론 먼저

| 도구 | 한 줄 정체 | 우리 판단 | 이유 |
|---|---|---|---|
| mixdog | 자기 에이전트 루프를 가진 데스크톱 코딩 에이전트(Electron). 공식 CLI를 부르지 않고 모델 서버를 직접 부른다 | **도입하지 않는다.** 숫자를 읽는 법과 아이디어 두 개만 참고 | 구독 로그인 토큰으로 서버를 직접 부르면서 공식 CLI인 척한다. "공식 구독 CLI만"(2절 6·13)과 정면으로 어긋난다. 절약의 대부분은 자기 루프 안에서만 되는 방식이라 우리 구조에는 옮길 수 없다 |
| Concord MCP | 같은 PC의 여러 코딩 에이전트가 작업을 claim하고 서로 메시지를 주고받게 하는 로컬 MCP 서버 | **도입하지 않는다.** 다시 볼 조건만 적어 둔다 | 격리 팀원에 붙이면 봉인(서로 못 봄)이 깨진다. 일반 팀원은 이미 controller가 원장·상한을 걸고 중계한다. 개발 세션끼리의 협업은 GitHub 카드·브랜치로 하고 있고 웹 세션은 이 도구에 닿지 못한다 |

"토큰 63%"는 실제 원자료로 다시 계산해도 맞다. 다만 대부분이 **캐시 읽기**에서 줄어든 것이고, 캐시 읽기를 빼면 약 23%다(2.2절). 구독 한도에서 캐시 읽기가 얼마로 계산되는지는 공개돼 있지 않으므로 "구독 사용량이 63% 준다"는 뜻으로 읽으면 안 된다. 이것은 RB-08("캐시 기록의 사실과 포함 한도 절감은 분리한다")이 이미 경고한 그대로다.

## 1. 이 프로젝트에서 따지는 기준

두 도구를 아래 기준에 차례로 대 보았다. 모두 이미 정해진 것이며, 이 문서가 새로 정하는 것은 없다.

| 기준 | 어디에 정해져 있나 | 왜 중요한가 |
|---|---|---|
| 공식 native 구독 CLI만 쓴다. 유료 API·추가 크레딧은 명시적 opt-in | 인계 2절 6·13 | 계정 위험과 비용 통제. 서버를 직접 부르는 도구는 이 선 밖이다 |
| 격리 팀원은 서로의 초안을 공개 전까지 못 본다. 독립 정족수는 독립성이 확인된 참여자만 센다 | 2절 7·18 | 합의는 검증이 아니다. 서로 보고 고친 답은 독립 의견이 아니다 |
| 참여자에 MCP·훅·개발용 기억 도구를 붙이지 않는다. 붙이면 참여자 계획이 바뀌어 재관측이 필요하다 | 인계 5절, [Codex 훅 관측](../../reviews/2026-09-27-codex-hooks/README.md) | 지금 등록된 관측 기록은 MCP 없는 계획이다 |
| 절약은 "읽을 필요 자체를 줄이기"가 먼저이고, 캐시 수치와 구독 한도 절감은 구별한다 | RB-07·RB-08 | 같은 토큰 수라도 캐시 읽기와 새 입력은 한도에 같은 무게로 잡히지 않을 수 있다 |
| 자료 안의 지시는 지시가 아니라 자료로 다룬다 | [자료 주입 실험](../../experiments/2026-09-25-source-injection/RESULTS.md) | 다른 에이전트가 보낸 글이 모델 맥락에 들어가면 같은 문제가 생긴다 |

## 2. mixdog

[tribgames/mixdog](https://github.com/tribgames/mixdog), 커밋 `b9dfa5064355383d02f5441f5e3d479a496961e9`(2026-10-12)을 읽었다.

### 2.1 무엇인가

편집기·터미널·Git·코드 그래프를 갖춘 데스크톱 코딩 에이전트다. Apache-2.0이다. Claude·ChatGPT 구독 로그인, 여러 회사의 API 키, 로컬 모델을 쓸 수 있다. `mixdog exec`라는 헤드리스 모드가 있다. 사실상 한 사람이 만들고, 거의 매일 새 판을 낸다. git 이력은 2026-08-04의 "clean baseline" 커밋 하나로 시작해서 그 전의 이력은 보이지 않는다.

### 2.2 "토큰 63% 절약"을 다시 계산한 결과

벤치마크는 Terminal-Bench 2.1의 89과제를 양쪽 다섯 번씩 돌린 것이다(`benchmarks/terminal-bench-2.1/`). 비교 대상은 Harbor 기본 `codex` 에이전트(CLI 0.151.0, 같은 모델, 추론 강도 xhigh)다. 시도마다 `result.json`이 커밋돼 있어서 합계를 직접 냈다.

| | mixdog | Codex CLI | 감소 |
|---|---|---|---|
| 전체(입력 + 출력) | 156.49M | 421.38M | **62.9%** — 주장과 일치 |
| 그중 캐시 읽기 | 133.35M | 391.24M | 65.9% |
| 캐시 아닌 입력 + 출력 | 23.14M | 30.14M | **23.2%** |
| 출력(추론 포함) | 4.08M | 4.43M | 7.9% |
| 통과한 시도 | 385 / 445 | 383 / 445 | 같은 수준 |

읽을 때 알아 둘 것:

- **절감의 대부분은 캐시 읽기다.** 매 요청마다 다시 보내는 시스템 프롬프트와 도구 목록이 작다(조사 에이전트가 읽은 분석 파일 기준 첫 요청 중앙값 약 4.7K 대 14.4K 토큰, 원 대화 기록은 커밋되지 않아 다시 확인하지 못했다). 캐시 읽기는 API 요금으로는 싸고, 구독 한도에서 어떻게 계산되는지는 공개돼 있지 않다.
- **기준선 조건이 같지 않았다.** Codex 쪽은 웹 검색이 켜진 채 돌았다. 445 시도 중 67 시도에서 웹 검색을 468번 불렀다(원자료에서 직접 셈). mixdog 쪽은 웹 검색을 껐다. 저장소의 `harness/codex_nosearch.py` 머리말은 "기본 에이전트가 웹 검색으로 벤치마크의 테스트 파일까지 찾아봤다"고 스스로 적고 있다. 그런데 공개한 5회 비교는 그 수정판이 아니라 기본판으로 돌렸다. README는 이 차이를 말하지 않는다.
- 두 쪽을 다른 날 돌렸고(mixdog 08-25·26, Codex 08-31), mixdog의 프롬프트·도구는 같은 벤치마크로 여러 번 맞춰 조정했다(`analysis/`, `quick4-*`, `tb-rounds-analysis*`). 그래서 이 벤치마크에 과하게 맞춰졌을 위험이 있다.
- 공개 수치를 낸 실행에서는 대표 기능인 "자동 추론 강도"가 **꺼져 있었다**(README의 fixed effort).
- Claude Code와의 비교는 한 번씩만 돌렸고, README 스스로 오차 범위 안이라고 적는다.

### 2.3 어떻게 아끼나 — 우리에게 옮길 수 있는지

mixdog는 에이전트 루프를 직접 갖고 모델 서버를 직접 부른다. 그래서 대부분의 장치는 `claude -p`·`codex exec`를 부르는 우리 controller에서 쓸 수 없다.

| 장치 | mixdog 위치 | 우리에게 |
|---|---|---|
| 작은 시스템 프롬프트·도구 목록, 도구를 필요할 때만 불러옴 | `src/rules/**`, `context/deferred-tools.mjs` | **불가.** 공식 CLI의 기본 프롬프트를 바꿀 수 없다. 우리가 줄일 수 있는 것은 과제 안내문뿐이다 |
| 같은 파일 다시 읽기·같은 호출 반복을 짧은 참조로 대체, 큰 도구 출력은 파일로 빼고 미리보기만 | `session/cache/`, `session/tool-batch/pre-dispatch.mjs`, `session/tool-result-offload.mjs` | **불가.** CLI 안쪽의 일이다 |
| Anthropic 캐시 구간 지정, OpenAI `prompt_cache_key` | `agent-runtime/cache-strategy.mjs` | **불가.** CLI가 스스로 관리한다. RB-07의 "안정된 앞부분 순서"만 우리 쪽에서 할 수 있다 |
| 구조화 요약으로 문맥 압축, 쉬었다 이어갈 때 먼저 압축 | `session/compact/`, `tui/session/session-flow.mjs` | **이미 다른 방식으로 한다.** 우리 참여자 호출은 매번 새 세션이고, 이어지는 내용은 controller가 고정한 입력(자동 기억·검토 지적)으로만 준다 |
| 코드 그래프(tree-sitter)로 파일 대신 기호를 찾음 | `native/mixdog-graph` | **지금은 아님.** MCP로 붙이면 참여자 계획이 바뀌어 재관측이 필요하다. RB-07의 "작은 기계적 지도"를 controller가 자료로 만들어 주는 쪽이 먼저다 |
| 단계마다 로컬 분류 모델(153 MB)로 추론 강도를 고름 | `providers/auto-effort.mjs`, `src/runtime/effort-judge/` | **단계마다는 불가, 호출마다는 가능.** 우리는 아직 추론 강도를 연결하지 않았다(RB-01). 연결할 때 사용자가 고르게 하면 되고 분류 모델은 필요 없다 |
| 역할별로 다른 모델(Lead는 강한 모델, 탐색·편집은 싼 모델) | `orchestrator/config-presets.mjs`, `src/agents/*` | **이미 있다.** 역할판에서 칸마다 모델을 고른다. 차이는 mixdog는 Lead 모델이 알아서 나누고, 우리는 사람이 시작과 판단을 한다는 것이다(2절 24·25) |

### 2.4 인증 방식 — 우리 원칙과 충돌

mixdog는 공식 CLI를 실행하지 않는다. 구독 로그인 토큰으로 서버를 직접 부르면서 **자신을 공식 CLI로 표시한다**. 코드에서 직접 확인했다.

- Claude: Claude Code의 OAuth client ID를 쓴다. `user-agent: claude-cli/<판> (external, sdk-cli)`를 보내고(`providers/anthropic-oauth-client-version.mjs:105`), 시스템 프롬프트 앞에 "You are Claude Code, Anthropic's official CLI for Claude."를 붙인다(`providers/anthropic-oauth.mjs:85`). 그 문장이 없으면 서버가 429를 준다는 주석이 있다.
- ChatGPT: Codex의 client ID로 `chatgpt.com/backend-api/codex/responses`에 직접 붙는다. `codex_cli_rs`로 자신을 표시하고, 서버의 판 검사를 통과하려고 최신 Codex npm 판을 조회해 맞춘다(`providers/codex-client-meta.mjs`).
- 계정 제한 위험 경고는 Cursor·Antigravity·MiMo 연결에만 있고, Claude·ChatGPT 연결에는 없다.

이것이 각 회사 약관상 허용되는지는 확인하지 않았다. 그러나 허용 여부와 상관없이 우리 원칙("공식 native 구독 CLI", 2절 6)의 밖이다. 또 공식 CLI가 아니면 우리가 관측·등록하는 참여자 계획(권한·도구·문맥 독립성)이 성립하지 않는다.

### 2.5 그 밖

- **다중 에이전트:** Lead가 영어 지시문을 쓰고, 각 에이전트는 자기 지시문만 보고 한 번 보고한다. 결과를 자동으로 합치는 장치는 없고, 끝에 Reviewer를 한 번 부른다. 에이전트별 작업 폴더 격리는 찾지 못했다. Reviewer가 읽기 전용인 것도 프롬프트 지시일 뿐이다. 봉인·정족수·근거 원장은 없다.
- **밖으로 나가는 연결:** 휴대폰 연결용 중계 서버 `wss://192-255-139-161.sslip.io`에 기본으로 접속한다(`src/runtime/channels/lib/webhook/relay-tunnel.mjs:22`, `MIXDOG_RELAY_URL=off`로 끔). 자동 업데이트, npm 판 조회, 분류 모델 내려받기도 있다. 분석 SDK는 찾지 못했다.
- Windows 설치 파일은 아직 코드 서명이 없다(README).

### 2.6 가져올 것

| 번호 | 무엇 | 어디에 연결 | 조건 |
|---|---|---|---|
| MX-1 | 사용량을 비교할 때 **캐시 읽기·캐시 아닌 입력·출력을 따로** 본다. 합계 하나로 "몇 % 절약"이라고 쓰지 않는다 | RB-08, 비교 실험 기록 | 새 규칙이 아니라 RB-08의 실제 사례다. 우리 원장은 이미 칸을 나눠 기록한다([긴 자료 결과](../../experiments/2026-09-25-long-sources/RESULTS.md)) |
| MX-2 | 추론 강도는 **호출마다** 고르게 연결한다. 단계마다 바꾸는 분류 모델은 들이지 않는다 | RB-01(추론 강도 미연결) | 관측한 값만 넣고 그 계획으로 재관측한다는 RB-01 그대로. mixdog의 46%·26% 출력 절감은 자체 소규모 실험이라 근거로 쓰지 않는다 |

## 3. Concord MCP

### 3.1 어느 Concord인가

이름이 같은 프로젝트가 여럿이다. 지금 "Concord MCP"로 소개되는 것은 **[Get-Concord-AI/concord-mcp](https://github.com/Get-Concord-AI/concord-mcp)**(npm `@concord-ai/concord-mcp`)로 보인다. 2026-07에 시작해 지금도 활발하고, 여러 MCP 목록이 이 이름으로 싣는다. 사용자가 본 것이 이것인지는 확인하지 못했다. 한국어 커뮤니티 글은 찾지 못했다.

- `adeyholar/concord-mcp`는 이 저장소의 포크다(같은 첫 커밋, 며칠 뒤처진 사본).
- **zkwasm의 Concord**(`zkwasm/concord-plugin`, npm `concord-mcp`)는 별개다. 규모가 작고 2026-06 이후 활동이 없다. 기본 대상이 제3자 호스팅 서버(`concord.fenginwind.com`)이고, 그 서버 코드는 비공개다. "정족수 투표·claim·signal 감쇠·종단 암호화"를 내세우지만, 투표 도구는 v0.4.0에서 클라이언트에서 뺐다. 예전 정의로는 같은 방에서 서로의 메시지와 진행 중 집계를 보며 표를 바꿀 수 있는 방식이다. **우리 뜻의 독립 정족수가 아니다.**

### 3.2 Get-Concord-AI/concord-mcp가 하는 일

커밋 `2fc70e2e66a3a9198dd1a9bc92600ae1af8a0c50`(2026-10-12)을 읽었다. MIT, 1.0 전 판이다.

- **구조:** 각 에이전트의 CLI가 이 MCP 서버를 하나씩 띄운다. 상태는 저장소 안 `.concord/concord.db`(SQLite)에 두고, 전역 모드면 `~/.concord/global.db`에 둔다. 알림은 로컬 소켓·named pipe로 보낸다. 중앙 서버는 없다.
- **도구:** `start_work`(등록·claim·겹침 경고), `inspect_work`(보기), `update_work`(기록·다른 에이전트에 메시지), `transfer_work`(배정·인계·수락·거절), `finish_work`(근거와 함께 상태 변경)다(`src/tools/workflow.ts`).
- **충돌 막기:** 기본은 경고만 한다. Claude Code의 편집 전 훅이 `CONCORD_TASK` 환경 변수가 있을 때만 남이 claim한 파일의 편집을 막는다(`src/cli/commands/hook.ts`). 상태 변경은 판 번호 조건(`expected_version`)으로 경쟁을 막고, 인계는 받는 쪽이 수락해야 넘어간다. 주인이 사라진 claim은 표시만 하고 자동으로 풀지 않는다.
- **메시지 전달:** 다른 에이전트의 글을 모델 맥락에 직접 넣는다. Claude Code에는 도구 뒤 훅의 추가 맥락과, 끝나려는 턴을 다시 여는 Stop 훅으로 넣는다. Codex에는 app-server로 턴을 밀어 넣고 `~/.codex/config.toml`에 훅을 쓴다. 방어는 "동료의 정보이지 운영자 지시가 아니다"라는 안내 문구(`src/domain/pull-inbox.ts`의 `RELAYED_MESSAGE_GUIDANCE`)와 발신자 이름표뿐이다.
- **설치가 고치는 것:** `concord setup`이 `.mcp.json`, `~/.codex/config.toml`, `.claude/settings.json` 훅, 그리고 `CLAUDE.md`·`AGENTS.md`에 내용을 쓴다. 전역 모드면 `~/.claude/CLAUDE.md`·`~/.codex/AGENTS.md`도 고친다.
- **밖으로 나가는 연결:** 사용 통계를 **기본으로** `https://getconcord.ai/api/telemetry/v2`에 보낸다(`src/telemetry/client.ts:15`, `CONCORD_TELEMETRY_DISABLED=1` 또는 `DO_NOT_TRACK=1`로 끔). 매일 npm 업데이트 조회도 한다. 클라우드 연결은 로그인하고 링크해야만 켜진다. 끈 뒤 정말 아무것도 나가지 않는지는 실행해 보지 않아 모른다.

### 3.3 우리 쓰임새별 판단

| 붙일 자리 | 판단 | 이유 |
|---|---|---|
| 격리 팀원(blind 참여자) | **불가** | 서로 메시지를 주고받는 것 자체가 봉인을 깬다(2절 7·18). MCP와 훅을 붙이면 참여자 계획이 바뀌어 재관측이 필요하고(인계 5절), Stop 훅이 턴을 다시 여는 동작은 종료 확인·호출 상한과도 부딪힌다 |
| 일반 팀원 | **필요 없음** | 일반 팀원 사이의 검토·수정·재검토는 controller가 원문 hash·처분·호출 상한을 걸고 중계한다([일반 팀원 설계](../../architecture/general-team-review/README.md)). Concord로 직접 말하게 하면 원장과 상한 밖에서 호출과 맥락이 늘어난다. 판 번호 조건부 변경과 수락이 있는 인계는 우리도 이미 한다(인계 5절의 조건부 UPDATE, 수정 판 흐름) |
| 개발 세션끼리(Claude·Codex·ChatGPT가 이 저장소를 함께 고칠 때) | **보류** | 지금은 GitHub 카드·브랜치·PR로 나눈다([협업 규칙](../../COLLABORATION.md) 3절, [WorkTrail 평가](../../reviews/2026-09-25-worktrail/README.md)). ChatGPT 웹 세션은 로컬 MCP에 닿지 못해 GitHub이 유일한 공유 지점이다(2절 11). 세션마다 다른 worktree를 쓰면 저장소 안 DB도 나뉜다(전역 모드는 확인하지 않음). 설치가 `AGENTS.md`·`CLAUDE.md`에 내용을 쓰는 것은 "규칙은 `AGENTS.md` 한 곳에"와 부딪힌다 |

### 3.4 가져올 것

새로 들일 기능은 없다. 판 번호 조건부 변경, 수락이 있는 인계, 근거를 남기는 완료 처리는 이미 우리 controller에 있다. 하나만 확인 거리로 남긴다.

| 번호 | 무엇 | 조건 |
|---|---|---|
| CC-1 | 같은 PC에서 두 세션이 **같은 checkout**을 동시에 고치다 부딪힌 일이 실제로 생기면, 그때 파일 claim(경고만, 사용 통계 끔, 전역 설치 없이 저장소 한정)을 작은 시험으로 본다 | [협업 규칙](../../COLLABORATION.md) 7절의 "실제로 일어난 일이 있는가". 지금까지 그런 기록은 찾지 못했다 |

## 4. 다시 볼 조건

| 도구 | 이런 일이 생기면 다시 본다 |
|---|---|
| mixdog | 공식 CLI를 실행하는 모드가 생기거나, 각 회사가 이런 구독 토큰 사용을 공식으로 허용할 때. 웹 검색 조건을 맞춘 기준선으로 다시 잰 결과가 나올 때 |
| Concord | 위 CC-1의 충돌이 실제로 생길 때. 메시지별 권한·신뢰 구분이 생기고 사용 통계가 기본 꺼짐이 될 때 |

## 5. 읽은 범위와 확인하지 않은 것

| 출처 | 고정 | 읽은 범위 |
|---|---|---|
| [tribgames/mixdog](https://github.com/tribgames/mixdog) | `b9dfa5064355383d02f5441f5e3d479a496961e9` | README, `docs/context-efficiency.md`·`docs/auto-reasoning-effort.md`, 위 표의 소스 파일, `benchmarks/terminal-bench-2.1/`의 README·harness·`raw-runs/*/result.json`(합계 직접 계산) |
| [Get-Concord-AI/concord-mcp](https://github.com/Get-Concord-AI/concord-mcp) | `2fc70e2e66a3a9198dd1a9bc92600ae1af8a0c50` | README, `src/tools`, `src/domain`, `src/cli/commands/hook.ts`, `src/relay`, `src/telemetry`, `src/install`, `plugin/` |
| [adeyholar/concord-mcp](https://github.com/adeyholar/concord-mcp) | `b06f78c23d12cdc39164fd95ded4e2892b327192` | 포크 관계 확인 |
| [zkwasm/concord-plugin](https://github.com/zkwasm/concord-plugin), [zkwasm/concord-server](https://github.com/zkwasm/concord-server) | `a784a81b00c40917e177204d1b1e96e665dd832c`, `9acdc63d83c0053329848986efe64dd7adc92717` | README, 도구 정의, 암호화 코드, 투표 도구를 뺀 커밋 |

두 저장소의 코드 읽기는 조사 에이전트 둘에게 나눠 맡겼다. 결론에 쓰인 핵심 주장(mixdog의 공식 CLI 표시 코드·중계 서버 기본값·토큰 합계·기준선의 웹 검색, Concord의 사용 통계 주소·편집 훅 조건·메시지 안내 문구·투표 기능 부재)은 작성 세션이 같은 커밋에서 다시 확인했다.

**확인하지 않은 것:** 두 도구의 실제 실행 결과, npm에 올라간 배포본이 소스와 같은지, 각 회사 약관상 mixdog 방식의 허용 여부, 구독 한도에서 캐시 읽기의 무게, zkwasm 서버의 실제 동작, mixdog 첫 요청 크기 중앙값(원 대화 기록이 커밋되지 않음).
