# AnchorMind 코드 검토와 decision-model_lab 적용안

2026-10-04 · codex · 사용자 요청에 따른 조사 · [카드 #156](https://github.com/inlight37-design/decision-model_lab/issues/156)

## 1. 판단과 조사 범위

**가져올 가치는 있다. 우선순위는 실행 엔진이 아니라, 과거 근거를 찾아 사람이 고른 뒤 실행 입력으로 고정하는 기능이다.** AnchorMind 전체를 기반 제품으로 채택하거나 격리 참여자의 MCP에 직접 연결하는 것은 권하지 않는다. 우리에게 이미 있는 원장·봉인·공개·교차검토를 유지하고, 자료 선택과 출처 표시의 설계를 작게 참고하는 편이 맞다.

비교 기준:

- AnchorMind: [커밋 `bf7a9c5`](https://github.com/JinHo-von-Choi/anchormind/tree/bf7a9c57f06586ebf61ec56751a9b7d40b08f202), package.json의 버전 6.0.0. 최신 main을 shallow clone하여 읽었다. 아래 AnchorMind 링크는 모두 이 판에 고정했다.
- 우리 main: `6ceff05e9bb5690c3fd9f5e0f54ebf84b7b92a01`. 열린 PR은 [#153](https://github.com/inlight37-design/decision-model_lab/pull/153), 미병합 원격 브랜치는 그 PR의 브랜치였다. 이 보고서는 그 head `36b51552049f0e3ea16001e3a1a28e7d3b58bd26`의 소스까지 읽었다. **E2 보고서의 교차검토 포함은 이 PR 기준이며 main 완료로 쓰지 않는다.**
- 접근: 사용자 PC `DESKTOP-T0UDE01`의 Windows 파일·Git·GitHub. CLI 설치·인증·실제 모델 가용성은 이번에 확인하지 않았다. 추가 모델 호출, 서버 기동, MCP/훅 설치, 제품 코드 변경은 없다.
- 검토 방식: 기능 목록을 문서로 파악하고 아래 주요 호출 경로를 코드로 추적했다. 선택한 순수 모듈은 실행했다(8절). 저장소 전체 보안 감사나 실서비스 품질 검증은 아니다. 관리자 화면·OAuth·배포 운영은 구조만 확인했으며 모든 경로를 감사하지 않았다.

## 2. 기능별 비교

AnchorMind는 **에이전트의 장기 기억 서버**다. 우리 앱은 **공식 CLI의 실행·입력·예산·독립성·공개를 통제하는 의사결정 controller**다. 역할이 달라 서로 대체 관계가 아니다.

| 기능 | AnchorMind에서 확인한 구현 | 우리에게 유용한 부분 | 판단 |
|---|---|---|---|
| 기억 저장·수정·삭제 | `remember`, `batch_remember`, `amend`, `forget`; 작은 fragment와 이력, 중복 범위, 재시도 키 | 공개된 실행의 사실·결정·실패를 원문 위치와 함께 찾기 | 저장 형식의 아이디어 채택. 원장을 fragment 저장소로 교체하지 않음 |
| 기억 검색 | 구조 검색, 벡터·형태소·어휘 검색, 그래프 이웃, 순위 결합과 재정렬 | 긴 과거 문서에서 필요한 근거만 선택 | 작게 시작할 가치가 큼 |
| 세션 시작 문맥 | `context`가 anchor/core/learning/working 후보를 묶음 | 개발 세션의 재개 보조 | 격리 참여자에게 자동 주입하지 않음 |
| 자료 묶음 | `recall format:"pack"`, 날짜·출처·추론 여부·대체 관계·잘림 표시 | 입력 확인 화면과 공통 자료의 근거 표시 | 가장 먼저 참고 |
| 출처·검토 | `WriteGate`, provenance, 검토 대기·거절 가시성, 낮은 등급 주입 제외 | 기억 후보와 채택한 자료 구분 | 개념 채택, 등급 기본값은 그대로 이식하지 않음 |
| 사건·이력 | case, 사건, 관계, 미해결 항목을 재구성 | 질문→실행→지적→처분→후속 실행의 연결 | 기존 tasks/runs/events를 활용하여 재구현 |
| 모순·대체 탐지 | 형태소 기반 주장 추출, polarity 충돌, NLI/LLM 보조, superseded 관계 | 서로 맞지 않는 과거 결정을 나란히 표시 | 검토 후보 생성까지만 |
| 피드백·적응 | 사용 피드백, 연결 강화·감쇠, 검색 임계값 조정 | 나중에 검색 편의 개선 | 평가셋을 만든 뒤 검토. 신뢰도·정족수에는 사용 금지 |
| 회고·정리 | 자동 reflect, 기억 분할·압축·TTL·GC·승격 | 사용량이 커졌을 때 선택적 요약 | 초기 도입 보류; 원본 근거는 감쇠·삭제 대상이 아님 |
| 모델 통로 | CLI/API/local provider dispatcher, fallback, semaphore·deadline·egress 정책 | 호출 목적과 외부 전송을 분리하는 아이디어 | 실행기는 이식하지 않음 |
| 운영·권한 | PostgreSQL/pgvector, 선택적 Redis, HTTP MCP, API 키·workspace·agent 범위, 관리 콘솔 | 추후 다중 사용자 서비스 때 참고 | 현재 단일 사용자 SQLite 앱에는 대부분 과함 |
| 비동기 후처리 | DB outbox, 임대·재시도·멱등 키·실패 보관 | 추후 검색 인덱스를 별도로 만들 때 | 실제 비동기 수요가 생기면 도입 |
| 검색 평가 | 정답 자료셋, 순위/토큰 예산 지표, 짝지은 비교와 신뢰구간 | 기억 기능의 효과를 평가하는 방법 | 검색 구현보다 먼저 작은 평가셋을 준비 |

기능 입구는 [tool-registry][registry], 기능의 전체 지도는 [architecture][architecture]에서 확인했다. 문서의 기능 설명을 모두 성능 실측으로 받아들이지는 않았다.

## 3. 실제 아키텍처와 파이프라인

```text
HTTP MCP / CLI / 관리 기능
  → 인증·도구 라우팅·범위 판정
  → MemoryManager (facade)
      ├─ Rememberer → WriteGate → FragmentWriter → PostgreSQL
      │                               └─ 후처리: 색인·임베딩·연결·평가 등
      ├─ Recaller → FragmentSearch → 후보 결합 → 점수·예산 선택 → 응답/Pack
      ├─ Reflector → 회고 내용의 fragment/episode 저장
      └─ Linker → 관계·수정·삭제

주변: Redis 선택 경로, LLM dispatcher, 작업자·정리 주기, outbox, 관리 UI
```

### 3.1 저장

[`MemoryRememberer.remember()`][rememberer]는 session 기억, 재시도 키, dry run, 할당량, case 연결을 처리하고 `_buildGatedFragment()`에서 쓰기 관문을 거친다. 영구 저장 경로의 atomic 분기는 키 행 잠금과 quota 재검사를 INSERT 거래 안에서 수행한다. 저장 뒤 색인·연결·충돌 처리 등이 이어진다. 따라서 **atomic이라는 이름이 전체 후처리까지 원자적으로 완료한다는 뜻은 아니다.**

[`WriteGate`][writegate]는 정규화→민감정보→길이→정책→workspace→anchor 판정에 출처와 검토 상태를 더한다. [`FragmentWriter`][writer]는 관문이 승인한 의미 데이터와 내부 메타데이터 변경을 구분한다. 입구마다 개별 검사를 복제하지 않도록 하는 방향은 좋다. 다만 관문의 일부 정책은 warn/enforce 설정에 따라 경고 또는 거절이 된다.

우리 적용에서는 `remember()`의 호출 성공을 ‘근거 검증 완료’로 번역하면 안 된다. **저장됨, 사람이 선택함, 인용 일치, 외부 확인됨은 각각 다른 상태**여야 한다.

### 3.2 검색과 입력 조립

[`FragmentSearch`][search]는 검색 조건에 따라 L1 캐시, L2 구조·키워드, L3 의미 검색과 어휘·그래프 등의 후보를 얻는다. 모든 요청이 모든 계층을 순차 실행하는 구조는 아니다. [`RankFusion.mergeRRF()`][fusion]는 각 계층의 서로 다른 점수 대신 순위를 `weight / (60 + rank)` 형태로 합친다. 순위가 없는 캐시는 같은 기여를 주고, 같은 ID의 후보를 합친다.

[`MemoryRecaller`][recaller]의 기본 `rankBeforeBudget` 경로는 최종 점수를 정한 뒤 [`BudgetSelector.selectForRecall()`][budget]로 예산 안의 집합을 고른다. 후보 상한, 검색 순서 기준해, 점수/길이를 고려한 탐욕 선택, 중복 완화, 토큰 재확인이 있다. **계산한 점수 합이 높다는 것과 실제 답변이 더 정확하다는 것은 다르다.** MMR의 유사도도 두 후보가 관련 필드를 가질 때 키워드 겹침으로 근사한다.

[`SearchScope`][scope]와 SQL 범위 전달은 검색 계층마다 workspace·agent·case 등의 필터가 달라지는 것을 막으려 한다. `SearchScope` 자체가 키 권한 검사를 전부 대체하지는 않는다. 키 범위는 SQL 등의 별도 경로도 맡는다. 또한 지정 workspace와 함께 `workspace=null`의 공통 자료를 허용하는 계약이 있으므로, 우리 격리 경계에 그대로 대응시켜서는 안 된다.

선택된 자료는 [`AnswerPack`][pack]에서 날짜·유효 상태·추론 상태·출처·대체 관계·잘림 표시와 함께 렌더링한다. 본문에 들어 있는 구분자·제어문자를 이스케이프하며, 자료를 명령으로 취급하지 말라는 고정 문구를 분리한다. 이는 구조를 명확히 하는 완화책이며 모델이 악성 지시를 따르지 않는다는 보장은 아니다.

### 3.3 사용 뒤의 변화

검색에는 접근 기록·평가 신호 등의 부작용이 있고, [`SearchParamAdaptor`][adaptor]는 충분한 표본 뒤 결과 개수에 따라 유사도 문턱을 조정한다. [`AutoReflect`][reflect]와 [`MemoryConsolidator`][consolidator]는 회고·정리·모순 탐지·승격 등의 별도 흐름이다. 기억의 내용과 노출 순서가 시간에 따라 바뀔 수 있는 구조다.

이 기능들은 개인 비서의 연속성에는 유용할 수 있다. 반면 독립 비교 실험에는 검색 결과·정렬 설정·선택 시점까지 고정하지 않으면 입력이 달라지는 원인이 된다.

## 4. 코드에서 골라 쓸 부분과 변경점

### A. 출처가 붙은 고정 자료 묶음 — 우선 적용

**참고:** `AnswerPack.js`의 `escapeAndCap`, `buildAnswerPack`; `provenance.js`; `ContextTrust.js`; `ReviewQueue.js`와 `ReviewVisibility.js`.

**현재 연결점:** 우리 [`Controller.prepare_run()`](../../../app/controller.py), `create_run()`, `_snapshot()`은 이미 `sources` 내용·크기·sha256을 고정하고 시도 전에 대조한다. 새로운 MCP 실행 경로 없이 사람이 고른 기억을 텍스트 자료로 렌더링하여 이 경로에 넣을 수 있다.

첫 적용은 **추가 저장소 없이 ‘과거 근거 선택→자료 파일 생성’**으로 충분하다. 자료별 최소 내용은 원본 문서/공개 보고서 위치, 커밋 또는 원문 해시, 관측일, 인용 범위, 원문인지 요약인지, 미해결·대체 관계다. 과거 모델의 답이면 사실 자료와 구분하고 기본 선택에서 제외한다. 필요한 경우 사용자가 선택한 선행 분석 자료라는 조건을 명시한다.

바꿔야 할 점:

- `created_at`은 저장일이다. 관측일·사건 발생일·원문 개정일과 혼동하지 않도록 별도 표기한다.
- 원문을 몰래 줄이지 않는다. 발췌 범위·누락·원본 위치를 보여 주고 원문과 발췌를 함께 추적한다. Pack의 기본 본문 상한을 그대로 복사하지 않는다.
- 자료 선택 뒤 최종 직렬화된 전체 입력을 다시 제한한다. 본문만의 토큰 수로 머리말·메타데이터·이스케이프 비용까지 충족했다고 말하지 않는다.
- 두 격리 참여자는 같은 pack의 동일 바이트를 받는다. 실행 중 검색·갱신·자동 기억 주입은 없다. 원래 앱의 시도 중 자료 변경 한계(K14)가 이 기능만으로 해결되는 것은 아니다.
- 출처 ID와 요약 여부를 보고서에서 별도 필드로 내보내려면 이후 `app/report.py`의 허용 필드와 보고서 판도 갱신해야 한다. 현재는 sources의 이름·크기·해시만 보고한다.

### B. 작은 검색기와 선택 예산 — 다음 적용

**참고:** `RankFusion.js`, `BudgetSelector.js`, `DeterministicRanking.js`, `SearchScope.js`.

**우리 방식:** 먼저 사람이 허용한 문서·공개 보고서를 대상으로 로컬 어휘 검색과 메타데이터 필터를 붙인다. 현재 원장 DB와 별도로 재생성 가능한 색인을 두는 편이 좋다. SQLite FTS 계열도 후보지만 한국어 조사·코드 식별자 검색은 실제 자료로 확인해야 한다. AnchorMind의 로컬 형태소 처리([MorphemeTokenizer][tokenizer])가 이 문제를 명시적으로 다룬 점은 참고할 만하다.

필요한 자료를 놓치는 사례가 확인되면 로컬 임베딩을 추가하고 어휘·의미 후보를 RRF로 합친다. 초기에 PostgreSQL·pgvector·Redis·cross-encoder를 모두 도입할 이유는 없다. API 임베딩은 구독 CLI 사용과 다른 경로이므로 기본안에 넣지 않는다.

검색 점수는 자료를 보여 줄 순서에만 쓴다. 미해결 반례는 인기가 없거나 오래됐다는 이유로 탈락시키지 않는다. 동일 질문·동일 색인 판·동일 설정의 재현성과 후보 제외 이유를 기록한다. 검색 뒤 사용자가 선택한 결과를 A의 고정 입력으로 넘긴다.

### C. 사건 이력과 미해결 항목 — 기존 원장으로 구현

**참고:** [`HistoryReconstructor`][history]와 [`CaseEventStore`][cases]. `reconstruct()`는 시간순 목록, 관계, 미해결 가지, 보조 자료를 분리해서 돌려준다.

우리 [`Store`](../../../app/store.py)의 `tasks`, `runs`, `events`, `reviews`, `review_dispositions`, `proposals.used_by`가 이미 상당한 재료를 갖고 있다. 별도 그래프 DB를 만들기보다 **공개된 원장 투영**에서 질문·실행·교차검토 지적·사람의 처분·후속 실행을 잇는 조회 기능을 먼저 만든다. `app/report.py`의 공개 조건을 우회해서 sealed draft를 읽지 않는다.

특히 ‘새 실행이 이전 문제를 해결했다’는 연결은 사람이 지정하거나 명시적 검증 결과가 있을 때만 둔다. 같은 시간대에 있었거나 모델이 비슷하다고 판단한 관계는 연관 후보로 표시한다. AnchorMind의 함수명 `causal_chains`가 과학적 인과를 증명하는 것은 아니다.

### D. 쓰기 관문·검토 대기 — 기억 저장이 생길 때

처음에는 사용자가 선택한 원문 자료만 다루면 된다. 이후 요약·자동 추출을 저장할 때는 `WriteGate`처럼 입구 하나로 모으고, 모델이 생성한 기억을 후보 상태에 둔다. 승인·거절·대체를 기록하되 원본을 덮어쓰지 않는다.

우리 `Controller.set_review_disposition()`은 이미 지적의 `qualified/rejected/unresolved`를 저장하며 모델의 동의를 사실 `supported`로 승격시키지 않는다. **기억 검토와 실행 교차검토는 재사용 가능한 원칙이 같을 뿐 같은 객체는 아니다.** 같은 테이블에 억지로 합치지 않는다.

[`provenance.js`][provenance]에서 `origin`은 일부 입구에서 클라이언트가 주장하는 값이고, `trust_tier`는 그 주장과 키 권한 상한으로 계산된다. `agent_inferred`도 기본 NORMAL이며, 기존 NULL 등급도 NORMAL로 읽는다. 따라서 이 등급을 우리 ‘사실 확인’이나 ‘독립성 확인’으로 매핑하면 안 된다. 우리 저장 형식에는 주장 출처·검증 방법·검증 시각·검증자/실행 근거를 분리한다.

### E. 검색 평가 — 구현 전부터 작게 시작

**참고:** [`RecallMetrics`][metrics], [`PairedBootstrap`][bootstrap], [`recall-eval-v2` 설명][evalset]. 같은 질의 ID로 기준/후보를 짝짓고, 미짝지음과 작은 표본, 합성 질의를 따로 보고하는 부분이 유용하다.

우리 공개 문서에서 대표 질문을 만들고 정답 근거 위치를 사람이 확인한다. 예: 현재 사용 기기, 만료된 관측, 철회된 제안, 반박된 주장, CLI 옵션의 근거, 한국어 표현 변형, 파일/함수 이름, 답이 저장되지 않은 질문. 튜닝용과 최종 평가용을 나누고, 평가 질문의 답을 자동 회고로 다시 저장하지 않는다.

기준은 검색 없음/수동 선택이며 후보는 어휘 검색, 필요할 때 어휘+의미 검색이다. 평가할 것은 정답 자료 적중·필요 근거의 누락·오래된 자료 오선택·범위 밖 자료 노출·입력 크기·지연이다. 독립 답변의 품질 개선은 그 뒤 별도의 제한된 실제 비교로 측정한다.

코드의 `recall_at_k`는 정답이 하나라도 상위에 있는 질의의 비율이고, 정답 전체 중 찾은 비율은 `recall_fraction_at_k`로 따로 계산한다. 토큰 예산 nDCG도 이 프로젝트의 계산 정의를 갖고 있으므로 일반 지표와 이름만으로 수치를 비교하지 않는다. 공개 평가셋 폴더는 예제만 담고 실제 질의는 비공개 경로를 쓰므로, 최신 실제 품질을 이번 clone만으로 재현했다고 말할 수 없다.

### F. outbox — 인덱스 동기화가 필요해진 뒤

[`Outbox.enqueue()`][outbox]는 같은 DB 거래에 후처리 이벤트를 남기고 [`OutboxWorker`][outboxworker]가 임대·재시도·실패 보관을 맡는다. 장애 뒤 색인 갱신을 복구하는 패턴으로는 적합하다.

우리의 첫 수동 자료 선택에는 불필요하다. 나중에 기억 저장과 인덱스 생성이 분리되면 기존 SQLite 거래에 작업 ID와 상태를 함께 남기고 재실행을 멱등하게 한다. **모델 호출 예약 원장을 일반 재시도 큐로 바꾸지는 않는다.** OutboxWorker의 `Promise.race`와 AbortSignal은 협조적 timeout이며 임의 handler의 실제 종료를 증명하지 않는다. 제공자에 요청이 도달했는지 불확실한 모델 호출을 자동 재시도하면 상한·중복 실행 문제가 생긴다.

## 5. 그대로 가져오면 안 되는 부분

| 코드 근거 | 확인한 동작 | 우리 쪽에서 필요한 처리 |
|---|---|---|
| [ContextBuilder][context] `buildRankedInjection()` | anchor와 보장 슬롯은 예산 검사 없이 먼저 넣고, 본문 길이/4로 비용 추정 | 참고 자료 예산을 hard cap으로 오해하지 않음. 최종 pack 전체 크기 재확인 |
| [FragmentFactory][factory] `countTokens()` | gpt-4용 인코더, 실패 시 글자 수/4 | Claude·현재 Codex의 실제 토큰/청구량이라고 표시하지 않음 |
| [AnswerPack][pack] `buildAnswerPack()` | 항목별 길이 제한·직렬화 토큰 추정은 있지만 전체 tokenBudget 인자가 없음 | 전체 입력 예산은 호출자가 별도로 제한 |
| [provenance][provenance] | 출처 자기신고와 키 상한으로 등급 계산, NULL 기본 NORMAL | 자동 신뢰 승격 금지. 검증 안 됨을 별도 상태로 유지 |
| [설정 표][switches] | workspace 읽기 권한·anchor 권한의 기본이 `warn` | 키/workspace가 있다는 사실만으로 강제 격리를 가정하지 않음 |
| [ClaimConflictDetector][conflicts] `detectPolarityConflicts()` | 오류 때 `conflicts:[]`, `severity:"none"`, `error` 반환 | 검사 실패를 ‘충돌 없음’으로 합치지 않음. unknown/error 유지 |
| [SearchParamAdaptor][adaptor] `recordOutcome()` | 결과 개수 평균으로 유사도 문턱 조정 | 검색 정확도 학습으로 부르지 않음. 고정 평가에서는 학습 정지 |
| [Codex runner][codexrunner] `runCodexCLI()` | `--sandbox read-only`, timeout에 직접 자식 SIGTERM, exit 0 뒤 출력 파일 반환 | 우리 `core.runner`, isolation, adapters, acceptance 유지. 전체 자손 종료·stderr 거절·문맥 확인을 이식 코드가 대체하지 못함 |
| [LLM dispatcher][llm] | 설정된 provider chain에서 다음 공급자로 넘어감 | 우리 provider 탈락 정책 유지. API나 다른 모델로 조용히 대체 금지 |
| [임베딩 설정][config] | 기본 이름 openai, 키/URL이 없으면 비활성; transformers 로컬 선택 가능 | ‘무조건 과금’도 ‘기본 구독 전용’도 아님. 별도 비용·외부 전송 경로로 판단 |
| [Codex hook manifest][hooks] | SessionStart 기억 로드·SessionEnd 처리 연결 | strict 참여자에 설치하지 않음. 개발 보조와 실험 참여자의 기억 경로 분리 |

자동 회고·모순 해소·연결 강화·중요도 감쇠는 **기억을 어떻게 관리할지 정하는 휴리스틱**이다. 모델 가중치가 학습된다는 뜻이나 사실 정확도가 향상됐다는 증거가 아니다. 특히 우리 dated record·출처 원문·미해결 반례는 사용 빈도에 따라 삭제하거나 요약문으로 대체하지 않는다.

## 6. 우리 프로젝트의 최소 적용 흐름

```text
허용한 저장소 문서 / 공개 보고서
  → 원본 위치·해시를 가진 검색 후보 (초기에는 수동 선택)
  → 출처·발췌·미해결 반례를 화면에서 확인
  → 사용자가 선택한 자료를 sources로 고정
  → 기존 prepare_run / create_run / _snapshot
  → 같은 입력으로 봉인된 CLI 초안 → 기존 공개·교차검토·보고
  → 공개 뒤, 필요한 결과만 다음 작업의 기억 후보로 지정
```

기억 경로가 controller의 봉인 저장소나 다른 참여자의 진행 중 답에 접근하는 통로가 되지 않게 한다. 같은 과거 자료를 받았다는 조건과 모델들의 판단이 통계적으로 독립이라는 주장은 구분한다. 기존 정족수 검사가 새로운 자료의 사실성·편향까지 검증해 주지는 않는다.

| 순서 | 구현 단위 제안 | 완료 조건 | 보류할 것 |
|---|---|---|---|
| 1 | 원문 선택→출처 포함 텍스트 자료 만들기. 기존 sources API 사용 | 양쪽 입력 해시 일치, 재시도 시 같은 내용, 원문/발췌 확인, 잘림·범위 밖·봉인 자료 제외 | 새 DB, MCP, 임베딩, 자동 회고 |
| 2 | 공개 자료의 작은 검색 색인과 평가셋 | 수동 기준과 고정 질의 비교, 한국어·코드 이름·대체된 자료·미해결 반례 시험, 결과/설정 재현 | 학습형 랭킹, API embedding, reranker |
| 3 | 실행·지적·처분·후속 실행 이력 조회 | 미검토/보류/거절 구분, 원본으로 이동, 공개 조건 보존 | 추정 인과관계의 자동 확정 |
| 4 | 실제 사용에서 필요성이 확인된 기억 후보 저장·승인 | 후보가 자동으로 공통 자료에 들어가지 않음, 원문·변경 이력 보존 | 자동 승격·삭제·압축 |

이는 구현 제안이며 이번에 채택된 제품 계약이나 일정이 아니다. 먼저 순서 1의 제한된 사용성·입력 보존 실험을 하고 다음 카드를 정하는 것이 좋다. 정식 데이터 스키마와 범용 memory 서비스를 먼저 늘리지 않는다.

## 7. 가져오는 방식과 유지 비용

**권고는 Python으로 필요한 작은 동작만 재구현하는 것**이다. AnswerPack의 자료/지시 분리, 결정적 정렬, 검색 범위 전달, 짝지은 평가 방식은 비교적 작게 참고할 수 있다. PostgreSQL용 writer·graph·worker 전체를 번역하면 Node/PostgreSQL/Redis/모델 설정의 유지 비용을 우리 앱에 함께 들이게 된다.

외부 서버를 나중에 시험한다면 controller 앞의 자료 후보 조회기로만 두고, 장애 시 기억 자료 없이 시작할지 사용자에게 보이는 방식으로 처리한다. 이미 고정한 실행 입력은 서버의 갱신·삭제와 무관하게 재현되어야 한다. 개발 세션 기억을 사용하더라도 저장소의 `AGENTS.md`와 `NEXT-SESSION.md`, GitHub 공유 규칙을 대체하지 않는다.

원본 [LICENSE][license]는 Apache-2.0이다. 이번에는 제품 코드를 복사하지 않았다. 실제 코드 이식 시 해당 파일의 고지·라이선스·변경 표시와 포함 의존성을 따로 확인해야 한다.

## 8. 직접 확인한 것과 한계

Node v24.19.0으로 원본의 다음 순수 단위시험을 실행했다. 별도 dependency 설치·DB·모델은 사용하지 않았다.

```text
node --test --test-reporter=spec tests/unit/answer-pack.test.js tests/unit/paired-bootstrap.test.js tests/unit/recall-metrics.test.js
```

결과: exit 0, tests 103 / pass 103 / fail 0 / skipped 0. 자료 구분자·제어문자 처리, 날짜·잘림 표시, 짝지은 통계 비교, 지표 계산의 해당 fixture 범위를 확인한 것이다. 실제 검색 품질이나 prompt injection 방어 성공을 증명하지 않는다.

앞선 묶음 실행에 함께 넣었던 `search-scope-contract.test.js`, `search-scope-read-range.test.js`는 `dotenv` 미설치로 로딩에 실패했다. 그 실행 전체는 exit 1이며 두 범위 시험을 성공으로 세지 않는다. AnchorMind 전체 시험·DB concurrency·실제 MCP·hook·임베딩·live 모델·부하·보안은 미검증이다.

추가 [순수 함수 확인 스크립트](probes.mjs)는 고정된 upstream commit에서 RRF 결합, 클라이언트 주장 출처의 등급 계산, CLI 외부 전송 분류, Pack 전체 예산의 호출자 책임을 재현한다. 네트워크·DB·모델 호출은 없다. `node probes.mjs <upstream-clone>` 실행은 exit 0이었다. RRF 순서는 a/b/c, 주장 출처 등급은 user_stated 3과 external_content 1, Codex CLI 분류는 external이었다. Pack은 자료 구분자를 보존했고 측정 크기는 2672였다(이 probe의 계수기는 **UTF-8 바이트**, 실제 토큰이 아님).

우리 저장소 검증과 PR의 최종 CI는 이 보고서를 싣는 PR의 Checks/본문에서 확인한다. 이 보고서는 실행 제품의 품질·entitlement·격리 보증을 새로 부여하지 않는다.

[registry]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/tool-registry.js
[architecture]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/docs/architecture.md
[rememberer]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/processors/MemoryRememberer.js#L175
[writegate]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/write/WriteGate.js
[writer]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/write/FragmentWriter.js#L77
[search]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/read/FragmentSearch.js
[fusion]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/read/RankFusion.js#L29
[recaller]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/processors/MemoryRecaller.js#L318
[budget]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/read/BudgetSelector.js
[scope]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/read/SearchScope.js#L104
[pack]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/read/AnswerPack.js
[provenance]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/provenance.js
[context]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/read/ContextBuilder.js#L69
[factory]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/write/FragmentFactory.js#L44
[adaptor]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/signals/SearchParamAdaptor.js#L71
[reflect]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/processors/AutoReflect.js
[consolidator]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/consolidate/MemoryConsolidator.js
[tokenizer]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/embedding/MorphemeTokenizer.js
[history]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/read/HistoryReconstructor.js#L60
[cases]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/CaseEventStore.js
[conflicts]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/symbolic/ClaimConflictDetector.js#L74
[metrics]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/signals/RecallMetrics.js
[bootstrap]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/memory/signals/PairedBootstrap.js
[evalset]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/tests/fixtures/recall-eval-v2/README.md
[outbox]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/outbox/Outbox.js#L178
[outboxworker]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/outbox/OutboxWorker.js#L134
[codexrunner]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/llm/runners/codex.js#L73
[llm]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/llm/index.js#L180
[config]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/lib/config.js#L620
[switches]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/config/switches.js
[hooks]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/integrations/codex/hooks/hooks.json
[license]: https://github.com/JinHo-von-Choi/anchormind/blob/bf7a9c57f06586ebf61ec56751a9b7d40b08f202/LICENSE
