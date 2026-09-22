# Jev 없이 시작하는 다중 모델 협업 — 조사와 설계 보강

> 초기 조사 이력이다. 현재 실행 우선순위는 [v0.4](../architecture/v0.4/README.md), 구독·과금 연결은 [v0.3 adapter](../architecture/v0.3/02-adapters.md)를 따른다. 아래 저가 API 경로는 선택 사항이며 공식 구독 CLI가 우선이다.

작성·원문 확인: **2026-09-22**. 기준 저장소: `main@244e8a1b3fef3a43263e9bff416c67f2cfc0b59f`.

이 문서는 [v0.2](../architecture/v0.2/README.md)를 보강하는 **문서 제안**이다. 실제 모델 호출, 로컬 모델 설치, 하네스 연동, 비용 절감 실험은 수행하지 않았다. 기존 계약 버전은 바꾸지 않는다.

| 읽을 문서 | 답하는 질문 |
|---|---|
| 이 문서 | 어떤 팀워크 방식에 근거가 있으며, 최근 무엇이 달라졌나? |
| [Codex 연결 설계](codex-bridge.md) | 기존 하네스를 유지하면서 여러 모델을 어떻게 연결하나? |
| [토큰·비용 평가와 구현 순서](measurement-and-rollout.md) | 낭비 원인을 어떻게 측정하고 어떤 순서로 구현하나? |

## 1. 지금의 권고

**Jev 없이도 충분히 시작할 수 있다.** 먼저 Codex를 사용자 접점과 주 실행기로 유지하고, 작은 작업을 맡길 수 있는 로컬 bridge를 MCP 도구로 연결한다. bridge 안에서는 코드가 작업 배정·예산·검증을 관리하고, 저가 API 모델이나 별도 native coding harness를 선택한다. Jev류 로컬 모델은 나중에 이 선택기를 교체할 수 있는 부품으로 둔다.

비용 절감의 핵심은 JSON이라는 표기법이 아니라 **전체 대화를 전달하지 않기, 원본 대신 필요한 구간만 읽기, 관리자 호출을 줄이기, 실패한 작업에만 추가 비용 쓰기**다. 다중 모델과 다중 에이전트도 다르다. 하나의 작업 흐름이 단계별로 다른 모델을 사용하는 것만으로 다중 모델 시스템이 된다. 처음부터 여러 에이전트가 동시에 대화할 필요는 없다.

제안하는 초기 원칙은 다음과 같다.

1. 범위가 명확하면 모델 한 개로 실행한다. 고성능 planner는 모호한 요구나 작업 분해에 필요할 때 호출한다.
2. 비용을 쓰는 단위는 `bounded_patch` 같은 완결된 작업이다. 매 도구 호출마다 모델을 바꾸지 않는다.
3. 워커는 작업 카드와 필요한 원문만 받는다. 결과는 patch·검증 근거의 참조와 짧은 요약으로 돌려준다.
4. 테스트·범위 검사·예산·재시도는 코드가 처리한다. 별도 LLM reviewer는 의미 판단이 필요한 경우에만 추가한다.
5. 시작은 동시 워커 1개, 필요하면 독립 작업 2개다. 작업 간 의존성과 파일 충돌이 적을 때만 병렬성을 늘린다.

이는 아래 자료를 종합한 **이 프로젝트의 설계 판단**이며, 모든 작업에서 최적이라는 연구 결과는 아니다.

## 2. 최근 자료에서 실제로 확인한 것

근거를 네 종류로 나눈다. **A: 공식 인터페이스·공개 구현**, **B: 논문/조건이 제시된 실험**, **C: 제작자의 제품·운영 성과 보고**, **D: 커뮤니티 탐색 신호**. A는 기능의 존재를 확인하는 근거이지 비용 절감의 증거가 아니다. B도 우리 프로젝트에서 재현했다는 뜻은 아니다.

### 2.1 9월 Jev 라우터: 96%의 분모는 전체 작업비가 아니다

LiteLLM의 9월 20일 글은 9월 18일 실행한 **80개 합성 프롬프트 × 3회**의 분류기 비교다. Jev 1.13.0과 Haiku의 중앙 지연은 126.81/688.40ms, 등록 가격으로 계산한 분류비는 $0.007706664/$0.198534였다. 작성자가 붙인 tier label과의 일치율은 95.00%/73.75%다. 독립 검토된 정답이나 최종 코딩 성공률은 측정하지 않았다. 따라서 ‘분류기 비용 약 96% 감소’를 ‘코딩 비용 96% 감소’로 해석하면 안 된다. **B/C**. [원문](https://docs.litellm.ai/blog/jev-auto-router-benchmark)

**적용:** router를 `RuleRouter`, `SmallModelRouter`, `LocalDecisionRouter`로 바꿀 수 있게 만들되, 최종 수용 결과당 비용으로 비교한다. 분류비가 원래 전체 비용의 작은 부분이면 분류기만 크게 개선해도 전체 효과는 작다.

### 2.2 9월 Jev compaction: 연결 예제는 있고 코딩 품질 보장은 없다

LiteLLM의 9월 18일 구현 안내는 오래된 도구 결과를 Jev로 평가하고, 불필요한 결과를 짧은 표시로 바꾼다. tool-call ID와 대화 구조, system/user 메시지, 최근 교환 등은 보호한다. 공개 예제는 날씨 조회 뒤 상점 영업시간을 묻는 상황이다. 이를 장기 코딩 작업에서 품질 손실 없는 절감 실험으로 확대 해석할 수 없다. **A/C**. [원문](https://docs.litellm.ai/blog/typesafe-jev-compaction)

**적용:** 첫 버전은 오래된 대화를 프록시에서 지우기보다, 큰 로그가 최초로 모델에 들어가기 전에 필요한 부분만 반환한다. 의미 기반 삭제는 원문 복구 경로와 독립 대조 실험이 생긴 뒤 적용한다. 요구사항·실패 근거가 ‘최근 질문과 덜 비슷하다’는 이유로 사라지면 안 된다.

### 2.3 Cursor의 7월 협업 실험: 역할과 문맥을 나누는 데 의미가 있다

7월 20일 Cursor는 SQLite 문서로 Rust 구현을 만드는 작업에서 planner/worker를 분리한 새 swarm을 비교했다. 새 하네스는 여러 모델 조합에서 기존 하네스보다 나았고, 최종 보고 비용은 Opus 4.8 + Composer 2.5 조합 $1,339, GPT-5.5 조합 $10,565였다. 이는 큰 특정 과제의 제작자 실험이며 일상적인 버그 수정의 기대 절감률이 아니다. 같은 글에서도 planner의 토큰 비중과 비용 비중이 크게 다르다고 설명한다. **C**. [원문](https://cursor.com/blog/agent-swarm-model-economics)

**적용:** 어려운 결정과 반복 구현을 분리하는 방향은 채택한다. 다만 작은 작업마다 비싼 planner를 의무 호출하지 않는다. planner가 세부 구현 로그까지 계속 읽으면 역할 분리의 이익을 잃는다.

### 2.4 라우팅은 고가 단독뿐 아니라 저가 단독과도 비교해야 한다

LangChain의 8월 11일 Switchyard 평가는 145개 다중 턴 과제에서 고가 단독 86.0%/$11.45, 라우팅 80.0%/$3.00, 저가 단독 77.7%/$0.72를 보고했다. 라우터는 고가 대비 저렴했지만 품질도 낮았고, 저가 대비 개선 2.3%p는 보고된 실행 변동 2.7%p보다 작았다. judge가 라우팅 비용의 21.2%였다. **B/C**. [원문](https://www.langchain.com/blog/switchyard-agent-routing-benchmark)

LiteLLM의 9월 11일 다른 실험에서는 SWE-bench Verified 25개 중 라우터와 Opus 5가 모두 23개를 해결하고 $11.15/$20.27을 사용했다. 소표본·구성별 단일 실행이며 성공한 task가 완전히 같지는 않다. **B/C**. [원문](https://docs.litellm.ai/blog/auto-router-capability-benchmark)

**적용:** 고가/저가/규칙 상향을 같은 과제로 먼저 비교한다. 모든 턴마다 ‘잘하고 있나’를 묻는 judge보다 테스트 실패·반복 오류 등 구체적인 사건에 반응하도록 설계한다.

### 2.5 병렬 후보 합성은 해결률과 총지출을 함께 높일 수 있다

9월 1일 LiteLLM Fusion은 21개 Terminal-Bench 과제에서 단일 모델 9개 해결/$67.13, 여러 모델과 합성 14개 해결/$91.64를 보고했다. 수용 결과당 비용은 낮아졌지만 총지출은 36% 증가했고, 작업 중앙 시간도 5분에서 8분으로 늘었다. 더 적은 agent turn이 더 낮은 총비용을 뜻하지 않는 구체적인 사례다. **B/C**. [원문](https://docs.litellm.ai/blog/fusion-terminal-bench-benchmark)

**적용:** 여러 모델이 같은 문제를 풀고 답을 합치는 방식은 어려운 실패 과제의 후순위 실험이다. 기본 절약 모드로 켜지 않는다.

### 2.6 연구·운영 자료도 무조건적인 에이전트 증설을 지지하지 않는다

Google 계열 연구의 논문 v1은 도구와 토큰 예산을 맞춘 180개 구성에서 협업 효과가 작업 구조에 따라 달라진다고 보고한다. 병렬 분해 가능한 작업과 순차 의존이 강한 작업을 같은 방식으로 다루면 안 된다. **B**. [버전을 고정한 논문](https://arxiv.org/html/2512.08296v1), [2026-01-28 저자 해설](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/)

Anthropic의 2025년 Research 운영 글은 내부 데이터에서 chat 대비 단일 agent 약 4배, multi-agent 약 15배 토큰 사용을 보고했다. **15배는 단일 agent 대비 수치가 아니다.** 독립 방향의 조사에서 얻는 품질·속도 이익과 비용 증가를 함께 본다. **C**. [원문](https://www.anthropic.com/engineering/multi-agent-research-system)

**적용:** 팀원을 늘리는 조건을 ‘역할 이름을 만들 수 있음’이 아니라 ‘입력과 산출물이 분리되고 독립 검증이 가능함’으로 정한다.

### 2.7 토큰 감소의 강한 후보는 모델 밖에서 데이터를 처리하는 것이다

Anthropic의 2025-11-04 Code execution with MCP 글은 도구 정의를 필요할 때 로드하고 중간 데이터를 코드에서 처리하는 예시에서 150,000 → 2,000 토큰을 제시한다. 98.7%는 그 예시의 수치이며 일반 코딩 작업의 절감률이 아니다. **A/C**. [원문](https://www.anthropic.com/engineering/code-execution-with-mcp)

같은 회사의 context engineering 글은 파일 경로·쿼리·링크 같은 참조를 유지하다 필요한 내용을 읽는 접근을 설명한다. 탐색 호출이 늘어날 수 있다는 비용도 함께 언급한다. **C**. [원문](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

**적용:** 테스트 원본 로그, 문서 원문, worker trajectory는 저장소에 남기고, parent에게는 실패 요약·원본 참조만 보낸다. 단, 재조회가 반복되면 요약을 넓혀야 한다. JSON 포장과 무관하게 적용할 수 있다.

## 3. 어떤 기존 도구를 가져올 것인가

| 후보 / 확인 근거 | 적합한 역할 | 이번 판단 |
|---|---|---|
| [Codex 공식 SDK](https://learn.chatgpt.com/docs/codex-sdk) / [비대화형 실행](https://learn.chatgpt.com/docs/non-interactive-mode) | Codex를 작업 실행기로 호출, 결과·usage 수집 | 첫 adapter의 기본 후보 |
| [Lite-Harness](https://github.com/LiteLLM-Labs/lite-harness) | 여러 native 하네스의 호출·스트림 형식 통일 | 직접 유사한 선례. 현재 README는 npm/PyPI 미출시 preview라고 명시. 설치·연동 검증 후 판단 |
| [Lite-Harness 발표](https://docs.litellm.ai/blog/lite-harness-sdk) | 하네스 내부 loop는 유지하고 바깥 호출만 통일 | 초기 실험 프로젝트. 공통 API가 모든 하네스의 기능 동등성을 보장하지 않음 |
| [Switchyard](https://github.com/NVIDIA-NeMo/Switchyard) | 모델 선택과 호출 계층 분리 | 기존 router 대조군. standalone server는 Demo/not for production |
| [Symphony](https://github.com/openai/symphony) | 작업 tracker → 격리 workspace → 실행 관리 | 여러 작업을 계속 운영할 때 검토. trusted 환경용 engineering preview |
| [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) | 작은 고정 하네스에서 경제성 비교 | 연구용 대조군. 실제 Codex 워크플로와 결과를 구분 |
| [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) | durable execution, 상태·분기·재개 | 긴 workflow가 생길 때. 단일 작업 bridge의 필수 의존성은 아님 |
| [Fugu Max / Ultra v2, 9월 11일](https://sakana.ai/fugu-max-release/) | 여러 모델을 하나의 서비스 API 뒤에서 조율 | 최신 상용 선례. 가격/벤치마크는 제작자 보고이며 자체 재현 가능한 로컬 orchestration으로 간주하지 않음 |

Sakana는 [7월 24일 Claude Code 호환 endpoint](https://sakana.ai/fugu-1-1-claude-code-interface/)도 발표했다. 기존 하네스 뒤에 orchestration을 넣는 방식이 실제 제품으로 존재함을 보여준다. 하지만 이것이 Codex의 모든 도구·상태·스트리밍까지 자동 호환된다는 증거는 아니다. Codex 연결은 별도 적합성 시험이 필요하다.

MVP에 위 후보를 모두 설치하지 않는다. **Codex + 작은 bridge + 기존 검증 명령**을 출발점으로 하고, 다중 공급자 인증·사용량 관리가 복잡해질 때 gateway를 추가한다. 상태 저장·스케줄러·gateway·router 각각의 책임을 하나씩만 둔다.

## 4. 로컬 Jev를 생각할 때 구분할 것

TypeSafe의 공식 Jev 소개는 early-access 서비스와 typed probabilistic decision을 설명한다. 이번에 확인한 공식 소개만으로는 **원본 Jev를 내려받아 로컬 실행할 공개 가중치/배포 경로를 확인하지 못했다.** 불가능하다고 단정하지도 않는다. ‘Jev 로컬’은 정확한 제품/모델을 지정해야 한다. 타입이 맞는 출력도 사실 판단은 틀릴 수 있다. [공식 Jev 소개](https://typesafe.ai/blog/introducing-system-one-models-and-jev)

| 로컬 후보 | 현재 원문에서 확인한 범위 | 판단 |
|---|---|---|
| [Kev](https://github.com/jaredpalmer/kev) | 현재 README의 중심은 Qwen3.5 기반 0.8B/4B/9B, local System One 호환 API | 기존 9/21 노트의 0.5B 수치를 최신 제품군 전체에 적용하지 않는다. 후보 선택·보정 재평가 필요 |
| [Laya](https://github.com/NandhaKishorM/laya) | encoder 기반 판단 모델과 다국어 checkpoint, 로컬 Python 진입점 | 한국어 작업 카드+영문 코드 혼합 입력은 자체 평가 필요. API 호환성과 성공률은 별도 |

우선순위는 **규칙 → 저가 모델 → 로컬 decision model의 shadow 평가 → 실제 라우팅**이다. 첫 적용 후보는 작업 유형 분류나 검색 후보 점수화다. 로컬 모델이 권한 부여, 병합 승인, ‘테스트를 안 해도 됨’을 결정하게 만들지 않는다.

GPU 종류·VRAM·동시 사용량이 지정되지 않아 특정 모델 크기나 로컬 처리속도를 추천값으로 확정하지 않았다. 모델 다운로드·로드·배치 구성·유휴 전력도 총비용에 포함한다. 짧은 분류를 드물게 실행한다면 로컬 상시 구동이 꼭 경제적이지는 않다.

## 5. X 조사 결과와 한계

`Jev TypeSafe`, `local Jev`, `agent context tokens`, `subagents`, 작성자 계정 등을 조합해 X 검색을 수행했다. 최신 Jev 관련 검색에서 유효한 직접 결과를 충분히 확보하지 못했다. 다음 게시물은 검색 결과에서 발견했지만 직접 열기는 **403**이었다.

| 탐색 링크 | 발견한 주제 | 근거로 취급한 수준 |
|---|---|---|
| [morluto 게시물](https://x.com/morluto/status/2043664759246258688) | 고성능 advisor와 저가 worker 조합 | 검색 스니펫만. 가격 최적이라는 주장 채택 안 함 |
| [Sydney Runkle 게시물](https://x.com/sydneyrunkle/status/2041572233496117642) | deepagents 비동기 subagent 발표 | 검색 스니펫만. 비용/품질 검증 근거 아님 |
| [Kaxil Naik 게시물](https://x.com/kaxil/status/2037503513350005134) | 문맥·권한 분리를 위한 subagent 사용 경험 | 검색 스니펫만. 독립 벤치마크로 집계하지 않음 |

검색 스니펫의 일부 문장을 본문 전체를 검토한 것처럼 취급하지 않는다. X의 자동 생성 trending 요약, 조회 수, 단순 재인용은 기술 근거로 쓰지 않았다. 실제 권고는 위 공식 문서·논문·제작자 저장소에서 확인한 내용에 근거한다.

## 6. 기존 v0.2에서 바뀌는 부분

| 항목 | 보강 결정 |
|---|---|
| 첫 실용 연결 | Codex 사용자 세션 → MCP bridge → 제한된 worker 작업부터 명시 |
| Codex를 바깥에서 실행 | SDK/`codex exec` 우선; 자체 UI는 App Server 검토 |
| 오래된 MCP 튜토리얼 | `codex mcp-server`는 제거됨. 외부 MCP 서버를 Codex에 연결하는 기능과 구분 |
| JSON | 기계용 전체 envelope와 모델이 읽는 짧은 task packet 분리 |
| 로컬 판단 | 원본 Jev와 공개 Jev류 모델을 분리하고 endpoint를 교체 가능하게 설계 |
| 비용 계측 | 분류기·parent·worker·수리·검증·캐시·실패 지출을 합산 |
| 평가 | 같은 하네스 비교와 실제 운영 조합 비교를 분리; 작은 표본의 동등성 주장 제한 |

Codex 인터페이스 변경의 직접 근거는 [공식 MCP server 제거 안내](https://learn.chatgpt.com/docs/mcp-server)다. 기존 v0.2의 독립 검증, 단일 작업 소유자, 최대 한 번의 수리, Jev shadow 평가 원칙은 유지한다. 다음 문서에서 bridge 계약과 구현 순서를 구체화한다.
