# 01. 실제 성과와 공개 설계에서 배울 것

> 2026-09-21 확인 / v0.2 사례 연구. **원문·사양·일부 코드 조사이며, 아래 외부 성과를 이 저장소에서 재현한 것은 아니다.**
>
> 이번 질문은 ‘관련 프로젝트가 많은가’가 아니라 ‘무엇이 실제로 효과가 있었고, 어떤 부분을 가져올 수 있는가’다. 기존 v0.1의 원칙을 반복하기보다 채택 순서를 바꿀 근거를 정리한다.

## 1. 결론: 쓸 만한 선례가 있지만 하나의 완제품으로 존재하지는 않는다

현재 근거가 비교적 구체적인 부분은 **모델 라우팅, 읽기 문맥 축소, 작업별 격리 실행, 검증 가능한 작업 환경**이다. 이들을 모두 결합해 사용자의 장기 프로젝트에서 품질을 유지하며 비용을 줄였다는 재현 결과는 별개다.

| 사례 | 확인한 성과/산출물 | 가져올 부분 | 가져오면 안 되는 해석 |
|---|---|---|---|
| Cursor Router | 실제 트래픽 기반 운영 평가, 비용·만족도 보고 | 작업 특징, 모델별 관측 성과, 캐시 손실을 포함한 선택 | 사용자 만족도를 코드 정답률로 바꾸거나 비공개 router를 복제 가능하다고 가정 |
| NVIDIA Switchyard | 공개 라우팅 라이브러리·설정·벤치마크 | 선택과 호출 분리, 세션 유지, 규칙/분류/상향 정책 비교 | demo proxy를 운영용으로 곧바로 채택 |
| LangChain의 Switchyard 평가 | 저가 단독/고가 단독/라우팅 비교와 반복 실행 | 저가 단독 기준선, judge 비용, 품질 손실, 비용 분산 | ‘74% 절감’만 떼어 동일 품질이라고 홍보 |
| SWE-Pruner | 500개 SWE-bench Verified 실험, 모델·코드·평가 자료 | 목적을 지정한 도구 출력 선별 | 모든 문맥을 무조건 압축하거나 40% 절감을 고정 기대 |
| OpenAI Symphony | 구체적인 서비스 사양과 Elixir 참고 구현 | 작업 조회·격리·세션·재시도·재조정 | 범용 분산 플랫폼/완전한 보안·비용 제어가 이미 구현됐다고 가정 |
| OpenAI harness engineering | 내부 제품 개발·사용 경험 보고 | 짧은 문서 지도, 실행 가능한 앱 관측, 구조 검사 | 그 환경의 개발 속도를 사용자 프로젝트 예상치로 사용 |
| mini-swe-agent | 실제 코딩 평가에 쓰이는 작은 공개 하네스 | 모델/환경/실행 분리, 추적 가능한 기준선 | ‘약 100줄’이 전체 시스템 규모라는 해석 |
| StrongDM Attractor | 그래프·handler·checkpoint·human gate의 상세 명세 | 고정된 실행 절차와 검증 조건 | 명세 저장소를 설치 가능한 완제품으로 소개 |
| Cursor 장기 실행 / Anthropic C compiler | 큰 코드 산출물과 실패 양상 공개 | 분해, 독립 oracle, 통합 병목 분석 | 많은 코드·많은 에이전트가 저비용·완성품을 뜻함 |
| JevGrep | 실제 CLI/MCP 코드 검색 구현 | Jev를 문맥 선택에 쓰는 작은 실험 지점 | 범용 코딩 성능/절감 벤치마크가 검증됐다는 주장 |

근거 ID는 아래 E01–E16에 연결한다. ‘채택’은 설계 선택이며 현재 설치 완료를 뜻하지 않는다.

## 2. 가장 직접적인 선례: 라우팅은 이미 성과가 있다

### 2.1 Cursor Router — 운영 데이터에서 배운 선택

2026-08-06 기술 설명에서 Cursor는 작업 난도 신호와 **domain/task/modifier** 분류를 결합하고, 실제 사용자 후속 행동과 비용으로 평가한다고 설명한다. 당시 Auto Intelligence는 비교 대상 대비 비용 68% 감소, Auto Balance는 41% 감소를 자체 보고했다. 지표는 사용자 만족도이며 테스트 기반 정답률이 아니다. 전환에 따른 cache miss도 비용에 포함한다. [E01]

**설계에 반영:** ‘작업이 어려워 보이는가’만 묻는 router보다 실제 작업군별 성공·실패·비용 이력이 중요하다. 다만 초기부터 수십만 학습 표본이 있는 척하지 않는다. 작업 카드에 `task_type`, `scope`, `required_capabilities`를 남기고, 독립 검증 결과를 모아 모델별 역량표를 만든다. Cursor의 임계값이나 특정 모델별 우위를 이 프로젝트의 정답으로 복사하지 않는다.

### 2.2 Switchyard — 가져올 수 있는 공개 구현

현재 README는 라이브러리 **Beta**, 호출/runner **Alpha**, standalone server **Demo, not for production**으로 구분한다. 핵심은 ‘어떤 모델을 쓸지’와 ‘누가 인증·재시도·호출을 소유할지’를 분리하는 것이다. [E02]

현재 README의 Terminal-Bench 2.1 결과는 다음과 같다. 모두 제작자 보고이며 **NVIDIA 내부 추론 endpoint, 평균 ISP 토큰 비용 기준**이라는 조건이 있다. 공개 실행용 profile은 OpenRouter 대상으로 바뀌어 있으므로 같은 절대 점수를 보장하지 않는다.

| 구성 | 정확도 | 표의 총비용 |
|---|---:|---:|
| Opus 4.8 단독 | 76.0% | $98.06 |
| Escalation | 75.7% | $85.00 |
| Execution / Stage | 72.7% | $68.19 |
| Task / Capability | 71.2% | $79.32 |
| GLM 5.2 단독 | 52.4% | $16.47 |

**읽는 방법:** 상향 방식은 0.3%p 낮은 정확도에서 13.3% 낮은 비용을 보고한다. 이것은 ‘정확히 동등한 품질’의 입증과는 다르지만, 공개 구조와 재실행 경로가 있는 유의미한 선례다. 저가 단독의 훨씬 낮은 비용도 함께 보아야 한다. [E02]

**설계에 반영:** 라우팅 엔진을 새로 만들기 전에 고정 모델, 규칙 기반 stage, 기존 escalation, Jev shadow의 네 경로를 비교한다. 검증할 버전을 고정하고, routing과 gateway를 겹쳐 켜지 않는다.

### 2.3 같은 Switchyard가 다른 과제에서는 덜 유리했다

LangChain의 2026-08-11 평가는 145개 다중 턴 과제를 대상으로 한다. SWE 코드 수정만으로 구성된 벤치마크가 아니다. [E03]

| 구성 | 정확도 | 실행당 비용 |
|---|---:|---:|
| Opus 4.8 단독 | 86.0% | $11.45 |
| 저가 + 상향 router | 80.0% | $3.00 |
| Nemotron 3.5 Lightning 단독 | 77.7% | $0.72 |

라우팅은 고가 단독보다 74% 저렴하지만 정확도는 6%p 낮았다. 저가 단독보다 2.3%p 높았으나 실행 간 변동 2.7%p보다 작아, 작성자도 저가 단독 대비 품질 우위를 확인하지 못했다고 명시한다. 라우팅 비용 중 judge가 21.2%였고, 낮은 등급을 사용하는 각 턴에서 judge가 호출됐다. [E03]

**설계 변경:** 고가 단독만 기준선으로 삼지 않는다. **저가 단독과 비교해 router의 추가 비용이 정당한가**를 필수 질문으로 넣는다. 모든 턴에서 ‘잘하고 있니?’를 묻는 AI 관리자를 초기 기본값에서 제외한다. 코드로 확인된 실패·범위 변경 같은 사건에서만 추가 판단을 시험한다.

이 결과와 앞선 Terminal-Bench 결과는 충돌하는 진실이 아니라, 모델 조합·작업 분포·정책이 다른 실험이다. 서로의 숫자를 합쳐 하나의 기대 절감률로 만들지 않는다.

### 2.4 LiteLLM — 작지만 비교 방법이 잘 드러난 사례

2026-09-11 공개 실험은 같은 25개 SWE-bench Verified 과제에서 router와 고가 단독 모두 23개 해결, 각각 $11.15/$20.27을 보고했다. 해결한 과제는 완전히 같지 않고 구성별 한 번의 실행이다. 캐시·실패·분류 비용을 포함한 비교 방식은 참고하되, 이 결과만으로 품질 동등성을 확정하지 않는다. [E04]

**설계에 반영:** 같은 성공 개수뿐 아니라 task별 paired 결과를 기록한다. router와 context 축소를 동시에 켜기 전에 각각의 효과부터 분리한다.

## 3. 라우팅보다 먼저 시험할 가치가 있는 문맥 선별

### 3.1 SWE-Pruner — 숫자보다 원문 표의 조건이 중요

논문 **v1 Table 1**의 500개 SWE-bench Verified 결과:

| 기반 에이전트 | 원래 해결 수 → 선별 적용 | 토큰 감소 | 표에 보고한 API 비용 감소 |
|---|---|---:|---:|
| Sonnet 4.5 / mini-swe-agent | 353 → 351 | 23.1% | 26.8% |
| GLM 4.6 / mini-swe-agent | 277 → 274 | 38.3% | 36.4% |

‘성공률이 전혀 떨어지지 않았다’고 쓰지 않는다. README의 40% 문구, 다른 과제의 최대값, 50개 하위 표본에서 수행한 다른 압축법 비교를 이 표와 혼합하지 않는다. 이 저장소에서는 별도 skimmer 운영비까지 포함한 총비용을 다시 측정해야 한다. [E05]

통합 문서는 `context_focus_question`이 있는 도구 응답을 선별하고, 없으면 원본 전체를 돌려주는 방식을 설명한다. 일반 요약문이 아니라 목적에 맞는 원문 코드 구간을 전달하는 패턴이다. [E06]

**설계 변경:** 초기 `ContextBuilder`를 거대한 메모리 시스템 대신 **read-only observation 경계의 선택기**로 축소한다. 원본 hash·경로·행 범위·생략 여부를 보존하고 원문 확장 읽기를 제공한다. 정책·수용 기준·명령의 성공 여부는 이 선택기로 압축하지 않는다.

SWE-Pruner Pro는 별도 연구이며 에이전트의 내부 표현을 이용한다. 원래 service형 선별기처럼 비공개 API에 그대로 붙일 수 있다고 보지 않는다. [E07]

### 3.2 JevGrep — Jev의 역할을 아주 작게 시작하는 사례

JevGrep은 승인된 저장소의 코드 조각을 Jev로 평가하고 원문·경로·행 번호를 돌려주는 CLI/MCP 구현이다. README는 benchmark suite가 없고, 실제 provider와 클라이언트 검증 범위도 제한적임을 명시한다. TypeSafe 직접 경로는 모의 응답으로 검사했지만 실제 계정 시험은 하지 않았다고 적혀 있다. [E08]

Reddit의 Codex/Claude 게시물은 같은 작성자의 교차 게시다. 두 건의 독립 운영 사례로 세지 않았다. 글을 통해 저장소를 찾고 README로 기능·제약을 확인했다.

**설계 변경:** Jev의 첫 후보를 ‘프로젝트 관리자’뿐 아니라 **모르는 동작의 코드 위치 찾기**로 확장한다. 단, 현재 구현은 적격 조각 전부를 평가하고 persistent index가 없으므로 큰 저장소에서 조사·전송 비용을 따로 재야 한다. 우리 제안에서는 `rg/심볼 검색 → 후보 축소 → 필요할 때 의미 점수화 → 원문 확인`을 비교한다. 이 후보 축소는 누락을 만들 수 있으므로 Recall@k와 전체 스캔 경로를 함께 평가한다.

코드를 원격 서비스로 보내는 기능은 사용자 승인 없이 켜지 않는다. ‘작은 판단 모델’도 입력한 코드에 대한 외부 공개 경계를 없애 주지 않는다.

## 4. 운영 구조를 구체화할 선례

### 4.1 Symphony — 가장 가까운 scheduler 참고점

SPEC은 작업 조회, 작업별 workspace, bounded concurrency, 재시도, 상태 재확인, `WORKFLOW.md`를 구체적으로 정의한다. tracker/filesystem을 사용해 재시작할 수 있고 DB는 필수 조건이 아니다. 성공 실행도 `Human Review`에서 종료될 수 있다. README는 trusted 환경용 engineering preview라고 표시한다. [E09]

실제 `agent_runner.ex`를 읽으면 workspace 생성·전후 hook·한 세션의 연속 턴·작업 상태 재조회·정리 단계가 나뉜다. 후속 턴은 기존 문맥이 있으므로 원래 지시를 재설명하지 말라는 짧은 인계를 사용한다. [E10]

**v0.1 수정:** 작업 제어부 전체를 처음부터 구현하는 것을 기본 전제로 삼지 않는다. 운영 경로에서는 Symphony의 사양/참고 구현을 먼저 적합성 시험한다. 프로젝트 상태는 tracker가, 실행 증거·비용 기록은 run journal이 소유하도록 분리한다. 후자가 필요한 경우 SQLite를 쓰되 두 곳이 같은 작업 상태를 경쟁적으로 갱신하지 않는다.

Symphony가 보안·회계 정책을 강제하지 않는 부분은 우리 경계에서 보완해야 한다. workspace는 OS sandbox가 아니며, worker가 수정할 수 있는 `WORKFLOW.md`의 새 내용을 실행 도중 승인 없이 다시 읽지 않는다.

### 4.2 mini-swe-agent — 경제성 실험용 대조 하네스

현재 v2의 `DefaultAgent`는 모델 질의, 환경 실행, 관측 메시지, trajectory 저장을 분리한다. `query()`와 `execute_actions()`는 라우팅/도구 응답 실험을 붙일 구체적 경계다. 실제 코드는 비용이 이미 사용된 후 다음 요청 전에 제한을 검사하므로 `cost_limit`를 정확한 선불 hard cap으로 소개하면 안 된다. [E11]

**설계 변경:** 실용 경로와 연구 경로를 분리한다. 실제 사용 중인 CLI를 무조건 교체하지 않고, 고정된 최소 하네스에서 모델·문맥·router만 바꾸는 대조 실험을 수행한다. 하네스를 바꾸면서 모델만 비교했다고 쓰지 않는다. 저가 모델이 bash 환경을 다룰 수 있는지도 평가 대상이다.

### 4.3 Attractor / StrongDM — 자유 협의보다 명시적인 절차

Attractor 저장소는 실행 완제품이 아니라 자연어 명세 묶음이다. DOT 그래프, node handler, checkpoint, human gate, 분기 조건을 구체적으로 설명한다. 일반 CLI와 API 등 서로 다른 backend를 같은 실행 절차 아래 둘 수 있는 설계다. [E12]

StrongDM의 자체 설명은 worker가 편집하는 테스트와 별도로 행동 scenario를 두는 방향을 강조한다. 외부 서비스의 모의 환경도 소개하지만 모의 환경 성공이 실제 서비스 호환성을 증명하지는 않는다. [E13]

**설계 변경:** MVP에는 범용 DOT 엔진을 만들지 않고, 고정된 `bounded_patch` 절차 하나를 둔다. 사전 검사 → 문맥 → 구현 → 독립 검증 → 최대 한 번의 수리 → 검토 인계 순서다. holdout verifier는 worker 쓰기 범위 밖에 두고, 실패를 숨기는 테스트 변경도 검사한다. 복잡한 그래프가 실제 필요해질 때 Attractor 구현 후보를 비교한다.

## 5. 큰 산출물을 만든 사례에서 가져올 것과 버릴 것

OpenAI는 2026-02-11 내부 제품 개발에서 약 1,500개 PR을 처리한 경험을 공개했다. 짧은 `AGENTS.md`를 문서 지도처럼 쓰고, 앱·로그·화면을 에이전트가 직접 검증할 수 있게 만든 점이 중요하다. 이는 제작자의 경험 보고이며 토큰 절감 대조 실험은 아니다. [E14]

Cursor의 장기 실행 연구는 조정·통합 병목과 동일 문제에 몰리는 현상을 설명한다. 연구용 대규모 코드 산출물을 공개 서비스 품질과 동일시할 수 없다. **우리 설계의 통합기는 상시 AI 관리자 대신 코드 기반 검증 큐**로 둔다. 실험 branch의 진행 상태와 사용자에게 수용되는 branch의 품질 기준도 나눈다. [E15]

Anthropic의 C compiler 실험은 16개 병렬 에이전트와 약 $20,000의 API 비용을 보고했다. 큰 산출물의 가능성은 보여 주지만 저비용 증거는 아니다. 같은 거대 실패에 모든 worker가 몰리는 문제와 참조 compiler를 활용한 분해가 더 유용한 교훈이다. 따라서 초기 동시성은 1, 후속 실험은 독립 task 2개로 제한한다. [E16]

**공통 학습:** 모델이 잘 일할 수 있는 저장소·검증 환경을 만드는 일이 중심이다. 큰 supervisor 프롬프트 하나나 ‘완료할 때까지 계속’하는 loop만으로 장기 프로젝트가 운영되는 것은 아니다.

## 6. 근거가 약하거나 확보하지 못한 사례

Stripe Minions 공식 두 글은 제목·날짜·공식 관련 요약까지 확보했지만, 웹 파서에서 상세 본문이 비어 있었다. 공식 요약의 대규모 PR 처리 언급은 운영 사례 탐색 신호로만 남긴다. 2차 글에 나온 blueprint·CI 횟수를 원문 확인 사실처럼 설계 근거에 쓰지 않았다.

기존 haejoe 원문 접근 한계도 해소되지 않았다. X/Reddit은 프로젝트를 발견하는 경로이며, 스타 수·조회 수·동일 작성자의 여러 게시물은 성능 검증을 대신하지 않는다.

## 7. 원문과 확인 범위

| ID | 원문 | 실제 확인 범위 |
|---|---|---|
| E01 | https://cursor.com/blog/how-cursor-router-works | 2026-08-06 기술 본문; live outcome·분류·캐시 비용·자체 보고 |
| E02 | https://github.com/NVIDIA-NeMo/Switchyard | README의 API 경계·stability·Benchmark Provenance; `a302618642735cc6676b88eba45eefb4a29fb7df` blob |
| E03 | https://www.langchain.com/blog/switchyard-agent-routing-benchmark | 2026-08-11; 145개 과제·3개 arm·반복·judge 비용·한계 |
| E04 | https://docs.litellm.ai/blog/auto-router-capability-benchmark | 2026-09-11; 25개 과제 비교 및 한계 |
| E05 | https://arxiv.org/html/2601.16746v1 | 버전 고정 논문 Table 1·Table 3 범위·통합·latency 설명 |
| E06 | https://github.com/Ayanami1314/swe-pruner/blob/public/examples/README.md | optional focus question, 전체 출력 fallback; `3015f026bbe02b68da86c1ddf17401b3b11d058f` blob |
| E07 | https://arxiv.org/html/2607.18213v1 | Pro의 내부 표현 기반 접근; 원래 모델과 구별 |
| E08 | https://github.com/nassim-arifette/jevgrep | 기능·외부 전송·캐시·미검증 사항; `82b93522f9c2792056871e2e277e95bcbaa30430` blob |
| E09 | https://github.com/openai/symphony/blob/main/SPEC.md | §§1–4; `cd24131a1e2358cbfecc4f6efb028fc9fc6edefc` blob. README preview도 확인 |
| E10 | https://github.com/openai/symphony/blob/main/elixir/lib/symphony_elixir/agent_runner.ex | 실행·세션·상태 재조회 코드; `f99a2d97555e46a84ed4c76b03a9b96fb58a424e` blob |
| E11 | https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/agents/default.py | 실제 run/query/execute_actions/save; `ca310e37d7c61888c576f73f5e1790ac769407b1` blob |
| E12 | https://github.com/strongdm/attractor/blob/main/attractor-spec.md | §§1–2.6; `aaaa969f0d5c1144b5c3b30b389e5fb6c588e53a` blob. README spec-only도 확인 |
| E13 | https://factory.strongdm.ai/ | scenario/외부 서비스 모의 환경에 대한 제작자 설명 |
| E14 | https://openai.com/index/harness-engineering/ | 2026-02-11 내부 제품 경험 및 저장소 환경 설계 |
| E15 | https://cursor.com/blog/self-driving-codebases | 2026-02-05 연구, 조율·통합·완성도 한계 |
| E16 | https://www.anthropic.com/engineering/building-c-compiler | 2026-02-05; 16개 agent·비용·참조 구현·한계 |

Git blob SHA는 읽은 **파일 내용** 식별자다. 설치할 commit/release가 아니므로 `pip @<blob SHA>`처럼 사용하지 않는다. 실제 통합 때에는 테스트한 commit·의존성 lock·모델 revision을 별도로 고정한다.

추가 탐색 기록: https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents ; https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2 ; https://www.reddit.com/r/codex/comments/1wlfdu5/i_built_a_jevpowered_mcp_tool_that_gives_codex/ ; https://www.reddit.com/r/ClaudeAI/comments/1wlmww8/a_jevpowered_mcp_tool_that_gives_claude_code/
