# 01. 조사 결과와 근거 지도

> 조사 기준일: **2026-09-21**. 상태: 아키텍처 구상을 위한 공개 자료 조사. 실제 서비스 부하 시험이나 모델 성능 재현 결과가 아니다.
>
> 기존 `../research-notes-2026-09-21.md`는 당시의 출처 중심 기록으로 보존한다. 이 문서는 후속 확인과 변경 사항을 기록한다.

## 1. 결론의 강도를 구분하는 방법

- **공식 사양/코드 확인**: 문서 또는 공개 구현에서 인터페이스·기능을 확인했다. 설치 성공이나 실운영 신뢰성까지 검증했다는 뜻은 아니다.
- **제작자 자체 보고**: 해당 프로젝트가 제시한 성능·비용·벤치마크다. 별도 재현으로 취급하지 않는다.
- **연구 결과**: 논문에 제시된 특정 실험의 결과다. 이 저장소의 코딩 프로젝트로 일반화하지 않는다.
- **사용자 경험**: 커뮤니티 작성자가 보고한 경험이다. 통제된 비교나 대표 표본이 아니다.
- **설계 제안**: 위 자료를 바탕으로 이 저장소에 제안하는 구조다. 이미 검증된 시스템과 구별한다.

현재 확보한 근거는 **구성 요소와 연결 경로가 존재한다**는 판단을 지지한다. 그러나 “Jev + 여러 에이전트 + JSON이면 동일 품질로 비용이 몇 % 줄어든다”는 종단간 검증은 확보하지 못했다. 이것이 다음 단계 평가의 대상이다.

## 2. 먼저 바로잡을 표현

### 2.1 Jev는 ‘결정을 대신해 주는 AI’인가?

일상적인 표현으로는 맞지만, 설계 문서에서는 **제한된 선택지에 대한 확률적 판단 모델(typed decision model)** 이 더 정확하다. 상태와 질문을 주면 `choice`, `score`, `noul` 결과를 반환한다. 일반 생성 모델처럼 긴 설계안·코드·설명문을 작성하는 역할과 다르다. 공식 문서도 질문을 작고 명확한 단위로 만들도록 권장한다. [S01–S03]

따라서 “이 프로젝트를 어떻게 설계할까?”보다 “이 작업은 이미 정해진 네 가지 작업군 중 어디에 속하는가?”에 먼저 적용한다. 후자는 분류 결과를 실제 처리 비용·오류율과 대조하기도 쉽다. **이 적용 범위는 본 저장소의 설계 제안**이다.

### 2.2 출력 토큰이 없으면 모든 비용이 사라지는가?

아니다. 입력 처리와 호출·네트워크·검증 비용은 남는다. TypeSafe 공개 가격은 조사일 기준 입력 100만 토큰당 **US$0.042**, 출력 무료로 안내되지만, 전체 시스템 비용은 다른 생성 모델과 도구 사용까지 합산해야 한다. 공식 가격의 적용 조건과 변경 여부를 실행 시점에 다시 확인한다. [S01]

### 2.3 JSON으로 통신하면 자동으로 토큰을 아끼는가?

아니다. 다음 세 가지를 분리해야 한다.

1. **전송 형식**: 프로세스 간 JSON/JSONL 통신. 파싱·스키마 검증·재시작에 유용하다.
2. **모델에 보여 주는 내용**: 필요한 필드·코드·오류만 전달하는 문맥 투영. 실제 입력량을 좌우한다.
3. **모델이 생성하는 형식**: 자유 서술 대신 제한된 결과를 받는 출력 계약. 재시도와 불필요한 설명을 줄일 가능성이 있지만 형식만으로 추론 비용을 보장하지 않는다.

예컨대 Antigravity의 `--output-format json`과 `--json-schema`, Codex의 `--json`과 `--output-schema`는 서로 다른 기능이다. 이벤트 포장 형식을 바꾼다고 내부 에이전트의 모든 메시지가 짧아지는 것은 아니다. [S11, S13]

## 3. Jev 및 로컬 대안: 무엇을 비교해야 하는가

| 후보 | 공개 자료에서 확인한 성격 | 이 프로젝트에서의 위치 | 유의점 |
|---|---|---|---|
| Jev | hosted typed-decision API; 상태 공유, 여러 질문 | API 기준선 및 선택적 판단 어댑터 | 내부 학습·아키텍처의 완전 재현 가능성을 가정하지 않음 |
| Kev | 현재 README는 **Qwen3.5 기반 0.8B / 4B / 9B** 계열, 공개 가중치·평가 자료, TypeSafe 호환 API | 로컬 대안 우선 조사 후보 | 이전 기록의 0.5B 설명은 과거 스냅샷. 최신 모델과 혼용 금지 |
| Laya | 작은 encoder 계열의 typed-decision 구현, 영어·다국어 모델 | 메모리·한국어 적합성 실험 후보 | 다국어 표기가 이 작업의 한국어 코딩 라우팅 품질을 보장하지 않음 |
| NanoJev | 소형 모델, 결정 head, 공개 학습·평가 구현 | 단일 forward-pass 접근 비교 | 게임/내비게이션 결과를 코드 프로젝트 통제 능력으로 해석하지 않음 |
| Bespoke Nimble | 공개 모델과 학습 recipe를 이용한 typed-decision 구현 | 공개 평가·학습 방법 참고, 필요 시 품질 비교 | 좁은 synthetic 평가와 서로 다른 장비의 latency를 일반 순위로 쓰지 않음 |
| SemIf | 기존 open model의 후보 점수를 읽는 semantic-if 접근 | 별도 학습 없는 기준선 실험 | 과거 이름 OpenJev; 아래 DiffusionGemma 프로젝트와 별개 |
| razorback16/openjev | DiffusionGemma를 Jev 형태의 인터페이스로 활용 | 후순위 연구 후보 | 인터페이스 유사성과 동일 학습법·동일 성능은 별개 |

출처: [S04–S09, S30–S31]. 모델 선택은 README의 ‘Jev보다 빠르다’ 문구가 아니라 **동일 입력, 동일 장비 또는 명시된 API 조건, 동일 수용 기준**으로 결정한다.

### Kev의 변경 사항

이번 조사에서 GitHub 커넥터로 실제 읽은 `jaredpalmer/kev/README.md`의 blob SHA는 `adc14469a25b09ae39360b6c827ed5b4b94a814e`다. 현재 내용은 0.8B/4B/9B Qwen3.5 계열을 설명한다. 따라서 기존 연구 노트의 0.5B 수치와 최신 모델 표를 이어 붙여 하나의 실험처럼 제시하면 안 된다. 고정 모델 revision과 평가 suite revision을 함께 저장해야 한다. [S04]

또한 해당 프로젝트가 인용한 ‘Jev의 아키텍처 해석’은 공식 내부 설계 공개와 동등한 근거로 취급하지 않는다.

### ‘확신’ 관련 중요한 구분

TypeSafe의 `confidence`는 반환 확률 분포로부터 계산되는 통계량이며 `max(probabilities)`라고 단정할 수 없다. `noul`에는 같은 confidence 필드가 없다. 이 값이 0.9라고 해서 사용자 작업에서 90%의 정답률이 보장되는 것도 아니다. 원래 확률 분포와 공급자 confidence를 모두 보존하고, 별도의 보정·보류 정책을 평가해야 한다. [S03]

## 4. 실제 구현에서 가져올 수 있는 패턴

### 4.1 LangChain의 Jev 하네스 통합

2026-09-17 공개 글은 Jev 분류기를 모델 라우팅 등에 연결하는 예제를 제공한다. 이는 ‘생성 모델 옆에 작은 판단 계층을 둘 수 있다’는 직접적인 구현 근거다. 그러나 사용자 저장소에서의 품질 유지·비용 절감까지 입증한 사례는 아니다. [S10]

### 4.2 browser-use/jev-ultrafast

이 공개 구현은 실행 가능한 행동과 대상 후보를 코드가 구성하고, Jev가 제한된 후보에서 선택하도록 한다. 자유 텍스트 입력이 필요한 부분에는 별도 작은 LLM을 사용한다. 행동의 유효성·페이지 상태를 코드로 검사하는 구조가 핵심이다. [S16]

**여기서 취할 설계 원칙**: 모델이 쉘 명령이나 권한을 마음대로 창작하게 하지 말고, 코드가 제공한 유효한 action ID를 선택하게 한다. 브라우저 데모의 속도 수치는 대규모 코드 협업의 절감률로 옮기지 않는다.

### 4.3 droidrun/mobile-jev

Android 자동화 데모에서도 Jev가 수행 완료라고 선택한 사실과 실제 UI 상태를 확인하는 절차가 분리된다. 이는 판단 출력과 독립된 완료 검증을 구분하는 참고 사례다. 공개 데모의 제한된 환경을 범용 자율 실행 검증으로 해석하지 않는다. [S17]

### 4.4 RouteLLM

강한 모델과 약한 모델 사이의 라우팅을 학습·평가하는 공개 연구 및 구현이 있다. 따라서 이 프로젝트가 새로 해결해야 할 부분은 ‘모델 선택이 가능한가’보다 **프로젝트 작업 단위의 정답 정의, 재시도·검증을 포함한 비용, 위험한 잘못된 하향 배정**이다. 기존 선호도/대화 중심 router를 코딩 작업에 그대로 최적이라고 간주하지 않는다. [S18]

## 5. Antigravity: 확인된 기능과 아직 확인되지 않은 연결

공식 Teamwork 문서는 조사일 기준 `/teamwork-preview`를 Antigravity 2.0 및 CLI의 협업 기능으로 설명한다. 조정자·구현자·독립 검증자 역할, 작업 규모에 따른 실행 경로, 구조화된 산출물 인계, 파일 소유권을 다룬다. 다만 이러한 역할을 모두 항상 실행하는 것이 저비용이라는 뜻은 아니다. [S12]

공식 연구 소개는 워크플로 패턴과 실행 기반을 분리하고 후보 생성·반박·종합을 결합하는 접근을 설명한다. 이 저장소는 **작업 성격에 맞는 패턴 선택**을 참고하되, 해당 시스템 내부를 복제했다는 주장을 하지 않는다. [S15]

| 연결 경로 | 문서 확인 | 판단 |
|---|---|---|
| 외부 프로그램 → Antigravity headless CLI | `agy -p`, JSON/stream-json, 구조화 출력 | 어댑터 경계로 현실적인 후보 |
| 외부 프로그램 → Antigravity SDK | 구조화 출력 및 확장 문서 존재 | CLI 검증 뒤 필요할 때 선택 |
| Jev → 외부 작업 분류 → 어느 에이전트에 위임할지 결정 | Jev API와 각 CLI를 조합해 설계 가능 | **본 저장소의 제안**, 아직 종단간 실행 안 함 |
| Jev가 Teamwork 내부 Sentinel/Orchestrator의 매 판단을 대체 | 이번 조사에서 공개된 대체 계약을 확인하지 못함 | 가능한 것으로 전제하지 않음 |
| 모든 구독형 앱의 한도를 공통 토큰 단위로 측정 | 공급자별 크레딧/할당량 체계가 다름 | 토큰·USD·구독 quota를 별도 저장 |

CLI가 존재한다는 것과 특정 계정의 인증·플랜·운영체제에서 무인 실행 및 취소·재개가 제대로 작동한다는 것은 별도 검증 사항이다.

## 6. 다중 에이전트가 오히려 비싸질 수 있는 근거

Anthropic은 자체 연구 시스템에서 에이전트 사용량이 일반 채팅보다 커지고 다중 에이전트는 더 커질 수 있음을 보고했다. 그 글의 약 15배 수치는 **일반 채팅과의 비교**이지, 단일 코딩 에이전트 대비 모든 작업에서 15배라는 의미가 아니다. [S19]

MAST 연구는 실패를 시스템 설계, 에이전트 간 조율, 검증·종료 문제 등으로 분류한다. 에이전트 수만 늘리는 것으로 장기 프로젝트의 신뢰성이 해결되지 않는다는 근거다. 버전별 실험 규모가 달라 이 문서에서는 숫자를 섞어 인용하지 않는다. [S20]

따라서 제안 구조는 **단일 에이전트를 기본값**으로 두고, 독립적으로 나눌 수 있는 작업에만 병렬화를 허용한다. ‘상시 회의하는 여러 AI’보다 인터페이스·산출물·검증을 중심으로 인계한다. 이 정책 자체의 성능은 후속 실험 대상이다.

## 7. 커뮤니티 조사: 신호와 한계

| 채널/자료 | 확인 범위 | 설계에 반영할 신호 | 해석의 한계 |
|---|---|---|---|
| Reddit r/google_antigravity, Teamwork token usage 글 [C01] | 본문 접근 및 관련 검색 | 유용성 평가와 과도한 할당량 소모 우려가 함께 존재 | 단일 사용자 경험; 실제 billing·작업 난도 통제 없음 |
| Reddit r/singularity, Jev 논의 [C02] | 검색에서 게시글과 사용자 서술 확인 | 생성 모델의 대체보다 보완으로 사용하는 관점 | 검색에 노출된 서술만으로 실제 운영 효과 검증 불가 |
| X, Antigravity `/goal`·`/teamwork-preview` 관련 게시물 [C03] | 검색 결과로 게시물 식별; 직접 본문 열기 오류 | 후속 조사 경로만 보존 | 본문/영상 확인 실패. 기능이나 성능의 확정 근거로 사용하지 않음 |
| 사용자 제시 haejoe 글 [C04] | 원문 직접 접근 실패; 검색 및 대체 경로 시도 | Google 공식 문서로 관련 주제를 별도 검증 | 원문을 읽거나 원문 주장을 검증했다고 말할 수 없음 |

X나 Reddit에서 ‘모두 이렇게 쓰고 있다’는 결론은 내리지 않는다. 공개 저장소는 구현 패턴의 근거로, 커뮤니티는 평가해야 할 문제를 찾는 보조 자료로 사용한다.

## 8. 토큰·컨텍스트·프로토콜 관련 판단

- **Code execution / local filtering**: 도구의 큰 응답을 코드에서 처리하고 필요한 결과만 모델에 넣는 패턴은 긴 로그를 계속 왕복시키는 문제를 줄이는 직접적인 참고점이다. [S21]
- **Context engineering / long-running harness**: 필요한 문맥의 선택, 진행 기록, 검증 가능한 작은 증분이 긴 작업의 구성 요소다. 기록을 남기는 것과 모든 기록을 매번 프롬프트에 넣는 것은 다르다. [S22–S23]
- **Prompt caching**: 반복 문맥의 안정적인 prefix가 중요하지만, 캐시 정책·쓰기 요금·표시 방식은 모델별로 다르다. 절감 입력량, 청구액, 캐시 적중량을 같은 값으로 취급하지 않는다. [S24]
- **TOON**: 균일한 레코드에 적합한 LLM용 표현 후보다. 제작자도 깊거나 불균일한 데이터에서는 compact JSON, 순수 표에서는 CSV가 유리할 수 있다고 명시한다. 전면 교체하지 않는다. [S25]
- **LLMLingua**: 추가 압축의 연구 후보다. 우선 무손실 선별·참조화·중복 제거부터 하고, 오류 메시지·식별자·숫자·부정 조건의 손상을 별도 평가한다. [S26]
- **MCP / A2A**: 각각 도구 연결과 에이전트 간 상호운용을 위한 계약이다. 토큰 압축기나 이 프로젝트의 스케줄러를 대신하지 않는다. 로컬 MVP가 두 프로토콜 전체를 구현할 필요는 없다. [S27–S28]
- **LangGraph persistence**: 체크포인터와 저장소를 이용한 상태 보존 수단이 있다. 메모리 전용 저장을 내구성 있는 재개와 혼동하지 않는다. 초기 단일 프로세스 제어부에 프레임워크를 쓸지는 복잡도를 비교해 결정한다. [S29]

## 9. 출처 목록

아래 URL은 2026-09-21 조사에서 확인한 공개 자료의 탐색 경로다. ‘문서 확인’은 필요한 본문 또는 관련 절을 읽었다는 뜻이며 전체 프로젝트를 실행·감사했다는 뜻이 아니다. 동적 문서는 변경될 수 있다.

### 공식 문서·프로젝트 원문

| ID | 자료 / URL | 근거 성격 및 주의점 |
|---|---|---|
| S01 | TypeSafe, Introducing System One Models & Jev — https://typesafe.ai/blog/introducing-system-one-models-and-jev | 2026-09-15 발표; 가격·성능은 공급자 안내/보고 |
| S02 | TypeSafe introduction — https://docs.typesafe.ai/introduction | typed API, atomic questions 공식 설명 |
| S03 | TypeSafe confidence — https://docs.typesafe.ai/confidence | confidence와 확률 분포 관계; 도메인별 threshold 필요 |
| S04 | Kev — https://github.com/jaredpalmer/kev | 현재 README와 공개 모델 계열; 성능은 제작자 평가 |
| S05 | Laya — https://github.com/NandhaKishorM/laya | 공개 encoder decision 구현; 자체 latency |
| S06 | NanoJev — https://github.com/TianyuCodings/NanoJev | 모델·학습·controller 평가 공개 |
| S07 | Bespoke Nimble — https://github.com/bespokelabsai/nimble | 학습 recipe, synthetic 평가, 조건별 serving 수치 |
| S08 | SemIf — https://github.com/TheoLeeCJ/SemIf | open-model 후보 scoring; 다른 OpenJev와 구별 |
| S09 | OpenJev / DiffusionGemma — https://github.com/razorback16/openjev | Jev 형태 인터페이스의 독립 구현 |
| S10 | LangChain, Building a harness with Jev — https://www.langchain.com/blog/building-a-harness-with-jev | 2026-09-17 통합 예제; 운영 절감 재현 아님 |
| S11 | Antigravity headless — https://antigravity.google/docs/cli/headless/ | 전송 JSON과 schema-constrained 출력 구별 |
| S12 | Antigravity Teamwork — https://antigravity.google/docs/teamwork/ | 역할·경로·구조화 인계·파일 소유권 공식 설명 |
| S13 | Codex non-interactive — https://developers.openai.com/codex/noninteractive/ | 조사 시 ChatGPT Learn 공식 문서로 리다이렉트; CLI 이벤트·schema·권한 |
| S14 | Claude Code programmatic usage — https://code.claude.com/docs/en/headless | headless/SDK, 인증과 자동 로딩 관련 조건 |
| S15 | Google, Teamwork: When AI becomes a research partner — https://antigravity.google/blog/teamwork-when-ai-becomes-a-research-partner | 2026-08-27; 공식 설계 소개 및 자체 사례 |
| S16 | browser-use/jev-ultrafast — https://github.com/browser-use/jev-ultrafast | 제한 후보 선택 + 실행 검증 공개 예제 |
| S17 | droidrun/mobile-jev — https://github.com/droidrun/mobile-jev | 모바일 데모, 독립 상태 확인 사례 |
| S18 | RouteLLM — https://arxiv.org/abs/2406.18665 ; https://github.com/lm-sys/RouteLLM | 강/약 모델 라우팅 연구; 코드 프로젝트 전용 평가 아님 |
| S19 | Anthropic multi-agent research system — https://www.anthropic.com/engineering/multi-agent-research-system | 2025-06-13; 연구 시스템 제작자의 경험·비용 보고 |
| S20 | Why Do Multi-Agent LLM Systems Fail? — https://arxiv.org/abs/2503.13657 | MAST 실패 분류 연구; 개정본 간 표본 규모 혼합 금지 |
| S21 | Anthropic, Code execution with MCP — https://www.anthropic.com/engineering/code-execution-with-mcp | 2025-11-04; 모델 밖 데이터 처리 패턴 |
| S22 | Anthropic, Effective context engineering — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | 2025-09-29; 문맥 선택·압축·상태 기록 |
| S23 | Anthropic, Effective harnesses for long-running agents — https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | 2025-11-26; 장기 작업 하네스 경험 |
| S24 | OpenAI prompt caching — https://developers.openai.com/api/docs/guides/prompt-caching | 공급자·모델별 캐시 정책을 분리해야 함 |
| S25 | TOON — https://github.com/toon-format/toon | 형식·비교·부적합한 데이터 형태까지 제작자가 명시 |
| S26 | LLMLingua — https://github.com/microsoft/LLMLingua | 프롬프트 압축 연구·구현 |
| S27 | MCP architecture — https://modelcontextprotocol.io/specification/2025-11-25/architecture | 이 URL의 버전은 2025-11-25; 최신 버전이라고 단정하지 않음 |
| S28 | A2A specification — https://a2a-protocol.org/latest/specification/ | task/artifact 중심의 원격 에이전트 계약; 동적 latest URL |
| S29 | LangGraph persistence — https://docs.langchain.com/oss/python/langgraph/persistence | checkpointer/store 및 영속 저장 구현 |
| S30 | DiffusionGemma developer guide — https://developers.googleblog.com/diffusiongemma-the-developer-guide/ | 생성 모델 계열 설명; active parameter 수와 총 메모리 구별 |
| S31 | Antigravity SDK structured output — https://antigravity.google/docs/sdk/structured-output/ | SDK 통합 후보; 본 저장소에서 실행 안 함 |

### 커뮤니티 및 접근 제한 기록

| ID | URL | 활용 범위 |
|---|---|---|
| C01 | https://www.reddit.com/r/google_antigravity/comments/1uash5h/token_usage_with_the_new_teamworkpreview_command/ | 실제 사용자 서술; 계량적 절감/낭비 결론에는 사용하지 않음 |
| C02 | https://www.reddit.com/r/singularity/comments/1wiq7vn/jev_from_typesafeai_is_getting_hyped_quite_a_bit/ | 검색에서 확인한 논의; 본문 전체 검증 아님 |
| C03 | https://x.com/vamsibatchuk/status/2091052209563750486 | 검색으로 식별, 본문 직접 접근 오류 |
| C04 | https://haejoe.com/community/posts/nfrp2kreqvyz6bs5kg3vkmqd-antigravity-20-teamwork-preview-구조-정리 | 사용자 제시 자료; 원문 미확보 |

## 10. 아직 모르는 것

이 저장소 작업에서 API 키를 등록하거나 실제 유료 호출, Jev/로컬 모델의 GPU 실행, Antigravity/Codex/Claude의 종단간 자동화, 장애 복구, 실제 대규모 저장소 평가를 수행하지 않았다. 기존 레포와 공개 문서·관련 구현을 읽은 결과를 설계 근거로 남긴 단계다. 특히 **사용자 코드에서의 절감률과 로컬 모델의 한국어 라우팅 품질은 미측정**이다.
