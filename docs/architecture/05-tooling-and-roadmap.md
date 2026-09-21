# 05. 기존 도구 재사용, 설계 결정, 단계별 도입

> 2026-09-21 / 설계 제안. 이 문서에 나오는 제품·라이브러리는 조사한 후보이며 설치·연결을 완료한 목록이 아니다.

## 1. 전부 새로 만들 필요는 없다

이 시스템의 차별점은 새 채팅 UI, 새 모델 API, 새 범용 에이전트 프레임워크가 아니다. **작업 단위 계약, 비용·권한 정책, 독립 검증, 재시작 가능한 실행 상태**를 기존 도구 사이에 일관되게 두는 것이다.

초기 제안은 다음과 같다.

- 코딩 능력과 기본 tool loop는 기존 하네스 재사용.
- API 호출 공통화·가격 로그는 필요할 때 기존 gateway 재사용.
- 의미 라우팅은 규칙-only 기준선을 먼저 만들고 Jev/로컬 모델을 비교.
- 프로젝트 전체 제어부는 작은 코드로 시작하되, 이미 존재하는 원장/워크플로 기능을 중복 구현하지 않도록 비교.

## 2. 실제 재사용 후보 비교

| 후보 | 확인된 역할 | 유용한 부분 | 초기 판단 |
|---|---|---|---|
| Antigravity CLI/SDK | headless, 구조화 출력, 자체 Teamwork | 기존 실행 능력·전문 팀 위임 | 우선 worker adapter 후보. 내부 scheduler를 수정한다고 가정하지 않음 |
| Codex CLI | 비대화형 실행, JSONL 이벤트, 출력 schema, 세션 재개 | 범위 제한 코딩·검토와 관측 가능한 실행 | 이미 사용자 워크플로와 가까운 첫 adapter 후보 |
| Claude Code CLI/SDK | 비대화형 실행, SDK, 구조화 출력 및 도구 제어 | 다른 하네스와 비교, 필요 시 전문 워커 | 두 번째 이상 adapter 후보. 자동 설정 로딩 확인 |
| LiteLLM | 다중 공급자 gateway, usage/spend, routing/fallback | API 비용 계측·공통 호출·기존 router 비교 | API 경로가 둘 이상일 때 검토. 구독 앱 전체의 대체재는 아님 |
| LangGraph | 그래프 실행과 persistence | 장기 상태 전이·재개 구현의 기반 | 직접 상태기계보다 단순해지는 경우에만 선택 |
| OpenHands Software Agent SDK | Python/TypeScript/REST, 코드 작업용 agent/server/workspace | 자체 loop 또는 원격 실행이 필요할 때 | 기존 CLI로 부족한 제어 지점이 생기면 검토 |
| Gas Town | 이종 coding agents, 지속 작업 추적, merge queue, 조율 | 대규모 협업 운영 구조의 비교 대상 | 즉시 전체 도입보다 축소 구성/기준선 비교 |
| Beads | 의존성 그래프 작업 원장, claim/ready, 지속 상태 | 마크다운 TODO보다 구조적인 작업 추적 | 원장 후보. 선택 시 SQLite와 동일 상태 이중 기록 금지 |
| MCP Agent Mail | agent identity, inbox/thread, 파일 예약 | 이미 독립 실행 중인 CLI들 사이의 협업 | 중앙 제어부 하나인 MVP에는 선택 사항 |
| Jev / Kev / Laya 등 | 제한된 선택·확률 출력 | 값싼 의미 판단의 실험 | shadow mode부터 시작; 필수 구성으로 고정하지 않음 |

Antigravity/Codex/Claude/LangGraph/Jev 계열 근거는 [01의 S01–S14, S29–S31](01-evidence-and-landscape.md). 추가 후보의 원문은 아래 T01–T08.

### 특히 주의할 최신 변경과 제약

**Gas Town / Beads**: 예전 `steveyegge` URL은 조사 시 `gastownhall` 저장소로 이동한다. 현재 Beads README는 Dolt 기반 저장을 설명하며 JSONL을 원장 자체가 아닌 interchange/export로 구분한다. 오래된 소개 글의 ‘JSONL 파일만 Git에 두면 된다’를 최신 설치 설계로 가져오지 않는다. [T02–T03]

**MCP Agent Mail**: 파일 예약은 기본적으로 협업 의사를 나타내는 advisory lease이며, 예약 결과에 grant와 conflict가 함께 올 수 있다. 선택적 commit guard가 있다고 해도 OS 수준 쓰기 격리나 완전한 분산 lock과 같지 않다. 통합하려면 제어부가 conflict를 검사해야 한다. [T04]

**OpenHands**: 공개 SDK는 대화 실행·도구·workspace를 제공하고, 자동화 scheduling 등의 경계는 별도 저장소로 구분한다. SDK를 붙인다고 프로젝트 전체 운영 제어가 저절로 해결되는 것으로 보지 않는다. [T05]

## 3. LiteLLM의 최신 라우팅 연구가 의미하는 것

### 3.1 단계별 라우팅 — 2026-09-07

제작자는 tool history를 Explore/Implement/Verify로 나누는 실험을 공개했다. 이 실험의 단계 분류는 별도 LLM 없이 규칙으로 계산된다. 즉 **Jev조차 필요 없는 라우팅 부분이 존재한다**는 직접적인 비교 후보다. 다만 실제 난도와 안전성이 tool 이름만으로 결정되는 것은 아니므로 고위험 정책을 대체하지 않는다. [T06]

### 3.2 하네스 문맥 분리 — 2026-09-10

하네스가 덧붙인 환경·skill·reminder가 분류 입력을 압도하는 문제를 다룬다. 선택된 실행 모델의 원본 요청과 classifier용 입력을 구분하는 구조가 제안 아키텍처와 연결된다. 불필요한 문맥을 제거할 때에도 분류에 필요한 제약까지 삭제하면 안 된다. [T07]

### 3.3 capability router 평가 — 2026-09-11

제작자는 25개 SWE-bench Verified 과제에서 router와 고정 Opus 구성 모두 23개를 해결했고, 각각 US$11.15와 US$20.27을 썼다고 보고했다. 실패 시도와 분류 비용을 포함하고 두 구성에 캐시를 켰다고 설명한다. 다만 **각 구성 한 번, 25개 표본, 서로 다른 성공/실패 항목**이라는 한계를 명시한다. 독립 재현이나 사용자 프로젝트의 예상 45% 절감률은 아니다. [T08]

이 결과에서 차용할 것은 숫자보다 **같은 과제·같은 verifier·같은 캐시 조건·실패 비용 포함**이라는 평가 방법이다. 실험용 capability classifier를 안정적인 범용 제품 기능으로 단정하지 않는다.

## 4. 연결 어댑터의 현실적인 범위

다음은 조사일 공식 문서로 확인한 CLI 입출력 예시이며, 그대로 실행해 검증한 명령은 아니다. 인증·버전·권한 설정을 별도 확인해야 한다.

```text
Antigravity: agy -p <task> --output-format stream-json
             최종 결과 구조 제한은 --json-schema 별도 검토

Codex:       codex exec --json <task>
             최종 결과 구조 제한은 --output-schema 별도 검토

Claude Code: claude -p <task> --output-format json
             SDK/CLI의 구조화 출력 계약 별도 검토
```

### 모델 API 어댑터와 agent 어댑터를 구별

`ModelAdapter`는 입력 메시지를 보내고 모델 응답을 받는다. `AgentAdapter`는 파일·명령·도구를 사용하는 하나의 실행을 관리한다. 둘을 같은 추상화로 묶으면 호출 비용과 실행 권한을 제대로 통제하기 어렵다.

공통 `AgentAdapter` 계약의 후보:

```text
probe() -> version, capabilities, auth_status
start(task, context_manifest, permission_profile) -> run_handle
events(run_handle) -> normalized events
request_cancel(run_handle) -> cancellation_request_status
inspect(run_handle) -> actual provider/process state
collect(run_handle) -> candidate artifacts, usage, limitations
resume(run_handle, checkpoint) -> supported or explicit unsupported
```

JSON stream의 종료 event나 프로세스 exit code만으로 사용자 작업의 성공을 판정하지 않는다. 코드·테스트·문서 수용 기준은 공통 verifier가 다시 확인한다.

### 인증·플랜의 범위

사용자가 보유한 구독 로그인, 유료 API 키, 로컬 모델은 서로 다른 비용·한도 경로다. 특정 앱의 구독권이 같은 회사의 모든 API에 적용된다고 가정하지 않는다. 지원되는 headless/SDK 경로만 사용하고 인증 우회·브라우저 세션 토큰 추출·할당량 우회는 설계에 포함하지 않는다.

하네스가 custom endpoint를 지원하더라도 모든 기능을 gateway나 다른 모델로 그대로 전달할 수 있는 것은 아니다. tool schema, reasoning 항목, provider session, multimodal 입력, encrypted content, cache semantics에 대한 호환 시험이 필요하다.

## 5. 권장 시작 경로 두 가지

### 경로 A — 실용형: 기존 하네스 중심의 얇은 제어부

**기본 제안**이다. 기존 coding CLI 하나 + 작업 원장 + 문맥 구성 + 실제 테스트 결과 수집부터 만든다. 첫 목표는 ‘무인 대규모 개발’이 아니라 ‘중단해도 이어서 하고, 비용과 완료 여부를 확인할 수 있는 단일 작업’이다.

사용자가 이미 쓰는 하네스부터 연결하되, 실제 사용할 계정에서 `probe/start/cancel/collect`를 확인한다. 하나가 안정화되기 전에 세 하네스를 동시에 구현하지 않는다.

그다음 규칙 라우팅과 Jev shadow 판단을 추가한다. API gateway가 실질적으로 필요한 경우 LiteLLM 등의 계측·호출 공통화를 재사용한다. 처음에는 auto-router를 끄거나 유일한 모델 선택자로 지정해 라우터 중첩을 막는다.

### 경로 B — 연구형: 하네스 내부 loop까지 직접 제어

분류기별 A/B, per-turn 모델 전환, 특수 도구 정책 등 CLI 바깥에서 구현하기 어려운 실험이 필요할 때 OpenHands SDK 또는 자체 tool loop를 비교한다. 이 경우 도구 실행·메모리·취소·보안까지 유지보수할 책임이 커진다.

두 경로가 같은 task/result/usage 계약을 사용하도록 해, 경로 A의 실행을 나중에 경로 B로 교체해도 원장과 평가 데이터를 잃지 않게 한다.

## 6. 초기 설계 결정 기록 (ADR)

| ID | 결정 제안 | 이유 | 다시 검토할 조건 |
|---|---|---|---|
| ADR-001 | 제어부는 코드, 모델은 제안/실행 역할 | 운영 규칙을 확률적 답변에 맡기지 않음 | 제어부 정책의 표현력이 실제로 부족할 때 |
| ADR-002 | Jev는 선택적 플러그인 | 저렴한 분류가 항상 필요한 것은 아님 | 자체 데이터에서 규칙-only 대비 실익 확인 |
| ADR-003 | 작업 경계 routing 우선 | 상태·캐시·평가 귀속을 단순화 | per-turn 실험에서 품질/비용 우위와 호환성 확보 |
| ADR-004 | 전송/저장 JSON, 모델 입력은 별도 투영 | 견고한 계약과 짧은 문맥을 동시에 추구 | 실제 tokenizer·품질 비교에서 다른 형식이 우세 |
| ADR-005 | 단일 워커부터, 병렬은 제한적으로 | 조율·중복·병합 비용 통제 | 분해 가능한 작업에서 대조 실험 통과 |
| ADR-006 | 단일 원장 소유자 | Beads/SQLite/LangGraph 상태 불일치 방지 | 분산 실행 요구가 명확해질 때 |
| ADR-007 | 독립 verifier와 merge queue | 자기 선언 PASS·의미적 충돌 방지 | 폐기하지 않는 핵심 불변 조건 |
| ADR-008 | 민감 raw trace는 코드 Git 밖에 | 유출·용량·불필요한 모델 재주입 방지 | 보존 정책 변경과 명시적 공개 승인 |
| ADR-009 | 모델/CLI 버전 고정 | 동적 latest와 숨은 설정의 변화 통제 | 검증된 업그레이드마다 새 실행 manifest |
| ADR-010 | 위험 작업은 승인과 실행 권한을 결합 | 확신 점수는 권한 근거가 아님 | 폐기하지 않는 핵심 불변 조건 |

## 7. 구현 단계와 통과 조건

이 일정은 기간 약속이 아니라 **단계별 진입 조건**이다. 아직 어떤 실사용 단계도 통과했다고 표시하지 않는다.

### P0 — 평가 기준과 샘플 확정

사용자 프로젝트에서 실제 task와 수용 기준을 수집한다. 단일 프론티어 하네스를 기준선으로 돌릴 과제를 정하고, 명세·환경·가격·모델 버전을 기록한다. 라우팅용 라벨과 최종 품질 라벨을 구별한다.

완료 조건: 같은 과제를 다시 실행하여 동일 verifier로 비교할 수 있다. 주관적 과제는 사전 rubric과 검토자를 지정한다. 본 조사에 포함된 문서와 예제만으로 P0 실험이 완료된 것은 아니다.

### P1 — 단일 작업의 내구성 있는 실행

원장, 한 개 adapter, 제한 workspace, 검증기, 비용 기록을 연결한다. API 키가 없다면 mock adapter로 제어 흐름을 시험하되, mock 성공을 실제 하네스 실행으로 표시하지 않는다.

완료 조건: 중간 강제 종료, 잘못된 JSON, unknown usage, 권한 밖 경로 수정, 실패 테스트, 예산 소진을 넣어도 잘못된 ACCEPTED나 무한 재시도가 나오지 않는다. 같은 작업의 중복 claim을 막는다.

### P2 — Jev/로컬 분류기의 shadow 평가

실제 배정은 기준 정책이 한다. 판단 모델은 같은 task에 대해 추천만 기록한다. 잘못된 하향 배정, 정보 부족, 한국어/영어, 옵션 순서 변화, 새 저장소에서 성능을 측정한다.

완료 조건: 검증용 holdout에서 risk–coverage와 총비용 비교를 할 수 있다. 공급자 confidence 0.9를 검증 없이 수용 기준으로 쓰지 않는다.

### P3 — 좁은 범위의 실제 routing

검증된 저위험 작업군에만 classifier 결정을 반영한다. 표본 감사, 즉시 중지, 기준 정책 복귀를 제공한다. 실패가 많은 작업은 처음부터 프론티어에 보낸다.

완료 조건: 사전 정의한 품질 허용 범위와 비용 목표를 동시에 만족한다. 예시 목표는 [04](04-evaluation-and-economics.md)에 있으며 보장값이 아니다.

### P4 — 두 개의 독립 작업 트랙

서로 다른 파일 영역과 고정 인터페이스를 가진 두 작업만 병렬로 실행한다. lease, stale result, 합쳐진 head에서의 회귀 실패, 전체 예산 예약을 시험한다.

완료 조건: 단일 실행과 비교해 병렬화 목적에 맞는 개선이 있다. 시간 단축만 있고 비용 증가가 크면 ‘비용 절감 성공’이라고 부르지 않는다.

### P5 — 확장 여부 결정

원격 에이전트, A2A, 서버형 DB, 추가 하네스, 로컬 모델 상시 서비스, 분류기 학습은 병목과 데이터가 확인된 경우에만 도입한다. Gas Town/Beads 같은 기존 구현을 실제 후보로 평가한 뒤 직접 확장할지 결정한다.

## 8. 로컬 모델·하드웨어 접근

이미 사용자가 언급한 주력 PC와 임시 PC의 조건이 다르므로 프로파일을 분리한다. 초기 제어부는 GPU 없이 실행 가능하게 설계하고, 로컬 판단 서버는 없어도 동작하도록 한다. **이 문서에서 두 PC의 설치·VRAM·속도는 실측하지 않았다.**

작은 모델의 가중치 계산만으로 fit를 단정하지 않는다. 예를 들어 0.8B × 2 bytes는 약 1.6GB의 원시 가중치 계산일 뿐이다. 런타임, activation, 문맥 길이, 배치, attention 구현, 다른 프로그램 사용량이 더해진다. 4-bit 옵션이 각 프로젝트의 decision head와 backend에서 실제 지원되는지도 따로 확인한다.

로컬 실험은 작은 모델 하나, 짧은 문맥, 동시 실행 1개에서 시작한다. CPU 또는 지원 dtype 경로를 확인하고, 메모리 측정 뒤 문맥·배치를 늘린다. DiffusionGemma 같은 큰 기반 모델은 활성 파라미터만 보고 작은 모델처럼 취급하지 않는다. [01의 S30]

API 분류비가 매우 작은 사용량에서는 로컬 모델 설치·GPU 점유·유지보수 비용이 더 클 수 있다. 우선 API/규칙 기준선을 측정하고, 프라이버시·오프라인·실제 호출량이 로컬 도입을 정당화하는지 확인한다.

## 9. 구현 전 남은 질문

첫 시험 저장소, 허용 외부 서비스, 실제 API/구독 인증 경로, 위험 허용 범위, 수용 기준, 작업당 최대 노출 비용은 실행 전에 확정해야 한다. 이번 조사에서는 이 값들을 임의로 사용자 결정처럼 확정하지 않았다.

이 값들이 정해지지 않아도 지금의 아키텍처 문서화는 가능하다. 실제 무인 실행의 출발은 이러한 설정을 명시적으로 가진 P1부터다.

## 10. 추가 원문 출처

| ID | URL | 확인 내용 및 성격 |
|---|---|---|
| T01 | https://docs.litellm.ai/docs/ | gateway·spend·routing 공식 기능 소개 |
| T02 | https://github.com/gastownhall/gastown | 현재 공개 README: 이종 하네스 협업·지속 작업·통합 큐; 성능/규모 주장은 제작자 설명 |
| T03 | https://github.com/gastownhall/beads | 현재 Dolt 기반 원장, dependency/claim, JSONL export 구분 |
| T04 | https://github.com/Dicklesworthstone/mcp_agent_mail | inbox/thread/파일 advisory reservation 및 선택적 guard |
| T05 | https://github.com/OpenHands/software-agent-sdk | agent/server/workspace API, 별도 automation 경계 |
| T06 | https://docs.litellm.ai/blog/subtask-type-routing | 2026-09-07; 규칙 기반 단계 분류와 모델 배정 실험 |
| T07 | https://docs.litellm.ai/blog/auto-router-harness-aware-classification | 2026-09-10; classifier 문맥과 원래 실행 요청 분리 |
| T08 | https://docs.litellm.ai/blog/auto-router-capability-benchmark | 2026-09-11; 25개 과제 자체 평가, 일반화 한계 명시 |

모든 후보는 공급망·릴리스·라이선스·플랜 조건을 설치 시점에 다시 점검한다. 조사한 공개 구현의 설치 스크립트를 이 작업에서 실행하거나 사용자의 로컬 설정을 변경하지 않았다.
