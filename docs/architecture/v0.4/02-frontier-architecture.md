# 상급 모델 협업 아키텍처

[개요](README.md) · [근거](01-cases-and-findings.md) · [평가/구현 순서](03-evaluation-and-roadmap.md).

**상태: 설계 제안.** 아래 모듈·상태·상한은 실제 CLI runner가 구현한 기능이 아니다. 기존 [v0.3 시스템](../v0.3/01-system.md), [adapter](../v0.3/02-adapters.md), [v0.2 합성 계약](../../../contracts/v0.2/README.md)을 유지하고, 협업 전략을 확장한다. v0.4는 운영 API나 wire schema의 호환성 보장을 선언하는 버전이 아니다.

## 1. 프로젝트의 두 목적을 동등하게 취급한다

**Economy:** 필요한 품질을 만족하는 작업을 더 적은 추가 지출·구독 한도·시간으로 끝낸다.

**Frontier collaboration:** 같은 문제를 잘 풀 수 있는 서로 다른 상급 모델의 강점을 사용해 중요한 오류·누락을 줄이고 결정 근거를 더 잘 검토한다. 비용이 늘더라도 품질·검증 이득이 있는 작업에서는 사용할 수 있다. 이 모드의 성공을 'token 절감률'만으로 평가하지 않는다.

두 모드는 공통의 권한·회계·artifact·취소/복구 core 위에서 실행한다. 저가 모델이 상급 모델을 반드시 지휘해야 하는 구조가 아니다. **실행 순서·횟수·권한은 일반 코드가 관리하고, 어려운 계획·쟁점 해석·합성에는 적합한 상급 모델을 배정한다.** Jev는 분류 후보일 뿐 품질 기준·권한·예산의 최종 결정자가 아니다. D10/D14, 근거 F01–F03/F08, 기존 D01–D09.

## 2. 네 가지 실행 모드

| mode | 기본 경로 | 사용 목적 | 기본적으로 하지 않는 것 |
|---|---|---|---|
| `single` | 적합한 단일 native worker + 필요한 검사 | 단순 작업, 기준선, 경제성 우선 | 형식 검사를 위해 모델 팀을 생성 |
| `cross_check` | 2–3개 상급 모델 독립 답변 → 근거 대조·합성 | 조사·풀이·설계의 다른 관점 확보 | 초기 답변 전에 서로의 의견 전달 |
| `deliberate` | 독립 답변 → 한 라운드 쟁점 교차검토 → 검사 → 합성 | 모순·숨은 가정·어려운 추론의 검토 | 합의할 때까지 무제한 반복 |
| `build_review` | 단일/협업 설계 → 한 구현자 → 별도 검토자 + 실행 검사 | 복잡한 코드·설계 변경 | 여러 agent가 같은 파일을 동시에 수정 |

`single`의 경제형/상급형은 profile 선택이며 별도의 프로토콜이 필요하지 않다. `cross_check`와 `deliberate`는 구성원이 전부 상급 모델이어도 된다. 강한 모델 단독이 더 나은 작업은 `single`에 남긴다. `deliberate`를 모든 질문의 기본값으로 삼지 않는다.

사용자가 이미 협업을 명시한 작업은 그 모드를 존중하되, 요구 모델을 사용할 수 없으면 `BLOCKED` 또는 명시적인 부분 결과로 보고한다. 상급 한 자리를 몰래 저가 모델로 바꾸거나 3인 협업을 1인 답변으로 성공 처리하지 않는다. 자동 축소는 사전 승인된 정책이 있는 경우만 허용하며 결과에 실제 구성을 표시한다.

## 3. 전체 뼈대: native 하네스는 남기고 제어권은 하나로

```text
현재 사용 입구: Codex / MCP / CLI / 향후 UI
                      |
            Task controller + policy
         (상태, 권한, 예산, 종료의 단일 소유자)
                      |
        Strategy planner / deterministic scheduler
                      |
       Context builder + immutable evidence manifest
                      |
         +------------+-------------+
         |            |             |
   Codex adapter  Claude adapter  Antigravity adapter
   native harness native harness  native agy harness
   상급 profile A 상급 profile B  상급 profile C
         |            |             |
         +-------- 독립 artifact ----+
                      |
          Claim ledger / targeted cross-review
                      |
        Verifier: source checks / tests / experiments
                      |
            Strong synthesis + report gate
                      |
   지원되는 결론 | 반례 | 미합의 | 다음 검증 | 사용량
```

논리적 모듈 분리이며 microservice 도입 목록이 아니다. 첫 구현은 한 로컬 Python 프로세스와 파일 artifact로 시작한다. 장기/동시 작업이 필요할 때 원자적인 journal/SQLite를 검토한다. 외부 scheduler와 native 팀 기능이 동시에 하위 agent를 무제한 늘리지 않게 한다. 통제할 수 없는 native 내부 fan-out은 지원 능력과 사용량 한계로 명시한다. 근거 F14, 기존 v0.3 D03/D04.

## 4. 어떤 상급 모델을 사용할 것인가

특정 모델이 영원히 '최상급'이라는 목록을 코드에 고정하지 않는다. profile은 다음 정보를 구별한다.

| 필드 | 의미 |
|---|---|
| `provider`, `model_id`, `model_revision` | 실제 공급자·모델·확인 가능한 revision. 알 수 없으면 unknown |
| `harness`, `runtime_version`, `effort` | native 도구와 버전, 해당 도구가 지원하는 추론 설정 |
| `quality_band`, `task_evidence` | 이 작업군에서 사용할 상급/경제형 구분과 그 선택 근거. 광고 명칭 자체가 검증은 아님 |
| `funding_profile`, `quota_pool` | 로그인 방식·구독 경로·공유 한도. credential 값은 저장하지 않음 |
| `capabilities`, `permission_profile` | 검색·파일·실행·읽기 전용·명시 session·취소 등의 실제 지원 여부 |
| `availability_checked_at` | 계정별 모델 선택 가능성과 설정을 확인한 시점 |

첫 pilot의 목표 구성이 A=OpenAI, B=Anthropic, C=Google이라고 해서 실제 모델 ID나 entitlement를 추정해 채우지 않는다. 같은 backend를 여러 alias로 등록한 것을 여러 회사로 집계하지 않는다. vendor 다양성, 모델/학습 계열 다양성, 풀이 방법 다양성, 검색 출처 다양성은 별개로 기록한다. 서로 다른 브랜드가 통계적으로 독립인 오류를 낸다고 가정하지 않는다. F02/F03/F07/F09/F20, D11/D14.

합성·검증을 값싼 모델에 일괄 맡겨 상급 답변의 핵심 반례를 놓치면 전체 품질이 낮아질 수 있다. 기계적으로 할 수 있는 중복 ID 검사·횟수 집계·자료 해시 계산은 일반 코드로 처리한다. 의미 판단이 어려운 주장 병합·반례 평가·합성은 작업에 적합한 상급 profile을 사용한다. 추가로 호출한 planner나 extractor도 예산에서 빠지지 않는다.

## 5. `deliberate`의 구체 프로토콜

### P0 — 준비와 고정

사용자 질문, 완료 조건, 금지 사항, repository commit/문서 revision, 공통 제공 자료, 접근 가능 provider, 허용 도구, 구독/추가 과금 정책, 모델 수와 정족수, 최대 호출·검토 라운드·deadline을 manifest로 고정한다. 결론을 보고 나서 수용 기준을 느슨하게 바꾸지 않는다.

모든 모델이 받아야 하는 사실·제약은 같은 버전으로 제공한다. 독립 조사를 허용하면 조회된 추가 출처·시각·도구를 모델별로 기록한다. 고정 source pack 비교와 독립 web 조사 비교는 다른 실험 조건이다. 원본 출처를 읽을 수 없는 artifact ID만 전달하지 않는다.

### P1 — 독립 초안

새로운 task session 또는 오염되지 않은 명시 session에 질문·원문·기준만 준다. 부모가 이미 가진 결론, 다른 모델의 답변, 누적 팀 대화는 초기 packet에서 제외한다. 공유 memory·project instruction·검색 결과 캐시 등 완전하게 통제 못 한 영향은 기록한다. '독립적으로 생각하라'는 문장 하나를 넣었다고 독립성이 확보된 것은 아니다.

출력은 `answer`, `claims`, `assumptions`, `evidence_refs`, `counterexamples`, `unknowns`, `checks_proposed`로 받는다. 검토에 필요한 설명·계산·근거를 요구하되 provider의 숨겨진 내부 reasoning trace를 추출하거나 다른 하네스 형식으로 옮기지 않는다. 간결한 검증 가능한 설명과 원문 참조를 사용한다. 초안과 digest를 수정 불가능한 artifact로 남긴다.

### P2 — 주장별 대조

서로 다른 모델의 동일 표현과 실제 동일 주장을 구분한다. ID·출처·형식 조립은 코드가 처리하고, 의미상 같은 주장인지 모델이 제안한 병합은 원문 연결을 보존한 채 확인한다. 임베딩 유사도나 Jev 분류만으로 서로 다른 조건의 주장을 합치지 않는다.

주장의 `kind`를 `factual`, `derived`, `value_judgment`로 나눈다. 각 주장에 지지 근거·반박 근거·적용 조건·미확인 사항·원 답변 위치를 연결한다. '모델 두 개가 동의'는 관측값이지 근거 종류 `verified`가 아니다. 중요한 소수 반례는 과반으로 폐기하지 않는다.

### P3 — 한 라운드의 제한된 교차검토

단순 전체 순위표보다 구체적인 질문을 준다. 예: '이 불변식이 취소와 재시작 사이에도 유지되는가? 반례나 검증 방법을 제시하라.' 동료 답변은 익명화하고 평가자별 제시 순서를 섞어 기록한다. 자기 답변을 남의 답변처럼 점수 매기게 하지 않는다. 자기 초안과의 대조가 필요하면 자기 것임을 분명히 구분한다.

기본 3인 구성에서는 각 모델에 다른 두 모델의 **관련 주장/근거**를 전달할 수 있다. 비용 제한 때문에 하나씩 ring review를 한다면 검토되지 않은 관계를 coverage에 남긴다. 입장을 억지로 찬성/반대로 고정하지 않고 유효한 반례와 조건 차이를 찾게 한다. 원문 추가 조회 경로는 유지한다.

수정된 답변은 새 artifact로 저장하고 초기 답변을 덮어쓰지 않는다. 답을 바꿀 때는 바뀐 주장 ID와 새 근거를 남긴다. 표현이 더 단정적이거나 합의율이 높아졌다는 이유만으로 개선으로 판정하지 않는다. F04/F07/F10/F12/F20, D11–D13.

### P4 — 외부 확인

검증 유형은 주장의 종류에 맞춘다. 코드에는 frozen candidate에 대한 test/build/reproducer, 수학에는 조건 점검·반례·독립 계산 또는 가능한 형식 검증, 최신 사실에는 해당 날짜의 원문·버전, 설계 선택에는 가정·trade-off와 작은 실험을 사용한다.

테스트 통과는 테스트 범위에 대한 근거이지 전체 정확성 증명이 아니다. 출처 URL이 존재한다는 것과 해당 주장을 뒷받침한다는 것도 다르다. source checker가 본문·해당 위치를 확인하지 못하면 '인용 확인 완료'로 올리지 않는다. 검사 불가능한 설계 선호는 근거가 붙은 제안으로 남긴다. 치명적 반례가 해결되지 않으면 그 부분을 통과 처리하지 않는다.

### P5 — 합성과 사람에게 인계

상급 합성자는 다음을 구별해 최종 결과를 쓴다: 근거가 지지하는 결론, 조건부 권고, 반박된 주장, 미합의/미검증 사항, 다음으로 가치 있는 검사. 모든 핵심 claim ID의 최종 처리를 ledger에 기록한다. 합성자가 새 사실을 만들면 새 claim으로 등록하여 같은 검사 경로로 보내거나 미검증 표시한다.

report gate는 필요한 섹션/참조와 상태 일관성을 검사한다. gate를 통과한 문서도 곧 객관적 진실은 아니다. 검증하지 못한 중요한 주장은 `qualified` 또는 `unresolved`로 남기며, `REVIEW_READY`는 검토 가능한 결과를 뜻한다. 근거가 없는 만장일치도 `unresolved`일 수 있다. F12/F13/F20/F21, D12.

## 6. 호출·시간 상한과 중단 규칙

| 예시 계획 | 기본 LLM 호출 수 | 해석 |
|---|---:|---|
| 2인 independent + synthesis | 3 | cross_check, 검토 라운드 0 |
| 3인 independent + synthesis | 4 | cross_check, 검토 라운드 0 |
| 2인 independent + 각 1회 review + synthesis | 5 | deliberate, 검토 라운드 1 |
| 3인 independent + 각 1회 review + synthesis | 7 | deliberate, 검토 라운드 1 |

설명용 초기 기본값이지 비용 최적값을 실험으로 찾은 결과가 아니다. planner·의미 병합·추가 verifier·형식 복구를 LLM으로 수행하면 호출 수에 반드시 더한다. 예컨대 별도 planner를 추가한 7-call 계획은 8-call 계획이다. 재시도도 같은 총상한에서 차감한다. native 하네스 한 실행 안의 model/tool turn 수는 이 **외부 invocation 수와 별도**로 관측한다. 7 invocations가 7 model turns나 일정 token이라는 보장은 없다.

검토할 중요한 모순이 없으면 P3을 생략할 수 있다. 새 근거 없는 반복, round/call/deadline 초과, 권한·인증 문제, 불충분한 정족수에서는 추가 모델 호출을 막고 상태를 명시한다. 이미 진행 중인 호출의 종료가 확인되지 않으면 `UNKNOWN`이며 소비를 0으로 적지 않는다. 지원하지 않는 CLI token hard cap을 외부 추정치로 보장하지 않는다.

## 7. 데이터 계약의 최소 형태

현재 합성 checker는 `deliberate`의 모든 참여자가 1회 이상 성공 검토를 마친 경로만 지원한다. P3 생략은 manifest 정책에서 허용한 경우의 설계 선택이며, 이를 이 checker에서 `deliberate` 완료로 기록할 수는 없다. 요청 모드와 실제 수행 모드의 차이 및 축소 승인은 후속 runtime 계약에서 명시한다.

아래는 실동작 API가 아니라 구현 시 분리할 객체다. 전체 registry를 모델 prompt에 넣지 않는다.

```text
TaskManifest
  task_id, base_digest, question_ref, acceptance_ref, strategy
  participants[{profile_ref, provider}], required_participants
  policy_ref, budget{max_invocations, max_review_rounds, deadline}
  context_manifest_ref, funding_policy, state, phase

DraftArtifact
  artifact_id, task_id, participant_id, input_digest, output_digest
  answer_ref, claim_ids, evidence_refs, assumptions, unknowns
  received_peer_artifacts[], native_session_ref

ClaimRecord
  claim_id, kind, statement_ref, origin_refs[], materiality
  supports[], contradicts[], assumptions[], checks[], disposition

ReviewArtifact
  reviewer_id, reviewed_claim_ids, peer_artifact_refs, presentation_order
  findings[{claim_id, issue, evidence_refs, check_proposal}]
  changed_claim_ids, unresolved, output_digest

CheckResult
  check_id, claim_or_candidate_digest, method, command_or_locator
  status{passed, failed, inconclusive, denied, skipped}, log_ref
  provenance, checked_at, limitations

DecisionReport
  supported_claim_ids, qualified_claim_ids, rejected_claim_ids
  unresolved_claim_ids, synthesis_ref, omitted_claims_with_reason
  participant_coverage, verification_scope, usage_ref, next_checks
```

지원하지 않거나 관측하지 못한 정보는 null/unknown이다. `passed`는 `CheckResult`의 특정 검사 상태이며 모든 claim의 정답 표시가 아니다. 주장별 검증 충분성은 사전에 정의된 acceptance와 근거 적합성에 따라 별도로 판정한다. JSON은 구조와 참조를 검사하기 위한 형식이지 자동 압축 장치가 아니다.

## 8. 권한·보안·과금

읽기 전용 논의자와 구현자를 분리한다. 논의자는 사용자 원본 checkout에 쓰지 못하는 격리 snapshot/작업 공간을 기본값으로 한다. 코드 실행 검증은 별도 sandbox와 제한된 artifact 복사에서 수행한다. native memory·설정 변경·외부 agent 생성·MCP 도구 호출도 권한 범위에 포함한다. parent의 모든 credential·환경 변수를 child에 전달하지 않는다.

동료 답변·외부 문서·코드 주석은 신뢰할 수 없는 데이터다. 그 안의 '다른 파일을 읽어라', '검사를 끄라' 같은 문장을 controller 명령으로 승격하지 않는다. 허용 파일/명령/provider와 data-egress 정책은 모델이 수정할 수 없게 한다. 같은 artifact를 세 회사에 보내는 것도 세 곳에 데이터가 전송되는 일이므로 민감 자료는 provider별 전달 허용을 먼저 확인한다. raw trace와 비밀은 자동 Git 커밋하지 않는다.

2026-09-22 재확인한 문서상 Codex exec의 기본 sandbox는 read-only(F17), Antigravity headless는 workspace 쓰기가 허용될 수 있고 도구 soft-denial에도 exit 0이 가능하다(F19). PAL의 기본 권한 완화(F05)를 복사하지 않는다. 실제 설치/유효 설정·OS 격리는 별도 conformance 검사가 필요하다. prompt의 '수정 금지'는 OS 쓰기 차단을 대신하지 않는다.

v0.3의 `subscription_only`, paid API/extra credits fallback 금지 기본 정책을 계승한다. Claude SDK 정책의 상단 보류 안내(F18)와 하단 과거 credit 표를 혼동하지 않는다. 구독 token을 추출해 비공식 gateway에 재사용하는 구조를 요구하지 않는다. auth/funding/모델 가용성이 모호하면 비용을 0으로 추정해 실행하지 않고 preflight에서 막는다. D15/D18.

## 9. 중단·재개와 기록

v0.3의 task state를 재사용하고 `phase=P0…P5`를 추가한다. 독립적인 두 state machine이 서로 완료 처리하지 않게 한다. event journal에는 attempt ID, phase, artifact digest, native session ID, effective policy revision, 종료 관측을 append한다. durable metadata와 실제 sandbox/session의 생존 여부를 분리한다. F14/D16.

재개할 때는 다음을 확인한다: 마지막 완료 phase, pending/unknown 호출, 현재 원본 commit, artifact digest, 예산 사용, 남은 정족수. 입력이 변했으면 새 attempt로 분기하며 예전 검사를 새 산출물의 근거로 쓰지 않는다. 'RUNNING이었으니 다시 호출'하지 않는다. exactly-once 외부 부작용은 idempotency ID 하나만으로 보장되지 않는다.

Git에는 연구 문서·설계 결정·재현 가능한 테스트와 **정제한 HANDOFF**를 커밋한다. 모든 실행 로그를 Git에 쌓는 방식과 구분한다. 최소 handoff는 `completed / evidence / decisions / unresolved / next / validation_scope`다. 다음 agent가 모든 과거 문서를 prompt에 넣지 않고 필요한 원문으로 이동할 수 있게 한다.

## 10. 새 결정 기록 D10–D18

| 결정 | 채택하는 제안 | 이유와 재검토 조건 |
|---|---|---|
| D10 | 경제성 경로와 상급 협업을 정식 모드로 분리 | F01/F02/F03/F06/F08/F16/F21. 품질 이득이 없는 작업군은 single 유지 |
| D11 | blind first pass, 원 초안 보존, peer 익명화/순서 기록/자기 평가 분리 | F02/F04/F05/F07/F09/F12/F20/F25/F27. 독립성 자체도 검사 대상이며 완전 독립을 가정하지 않음. 오염을 줄이는 플래그가 과금 경로를 바꿀 수 있고(F25), worktree 분리는 peer 산출물 읽기를 막지 않음(F27) |
| D12 | claim/evidence 중심 합성, 미합의 허용, 투표≠검증 | F01/F04/F07/F12/F13/F20/F21/F22/F24. acceptance가 없는 사실 수용은 보류 |
| D13 | 기본 0/1 review round, 호출·시간·재시도 전체 상한 | F03/F04/F06/F10/F12/F21/F24. 추가 round는 paired 이득과 예산 확인 후 |
| D14 | 어려운 계획·의미 검토·합성에도 상급 profile 허용, Jev는 선택 부품 | F02/F03/F08/F09/F11. 실제 작업군/가용 모델로 선택; vendor 고정 순위 없음 |
| D15 | 단일 writer, read-only 논의자, 실행 sandbox·data-egress 경계 | F05/F16/F17/F19/F24/F26/F27. 실제 OS/adapter 시험 전 안전성 완료 주장 금지. 필수 제한을 적용할 수 없으면 실행 후 경고가 아니라 프로세스 생성 전에 차단 |
| D16 | 하나의 controller와 durable artifact/journal, 명시 session 재개 | F14/F26, 기존 D03/D06. 분산 infra는 운영 요구가 생길 때만. 실행 부품이 스스로 실행 방식을 바꾸면 controller의 단일 소유가 깨짐 |
| D17 | 동일 예산 단일 모델/ensemble 대조군과 오류 전이·합성 손실 평가 | F07–F12/F15/F16/F20/F21/F22/F23/F24. native end-to-end와 모델 인과 효과를 분리 |
| D18 | 구독·가용 모델·정족수 preflight, silent fallback 금지 | F04/F05/F06/F17/F18/F19/F25/F26. 실제 entitlement/transport conformance 필요. silent fallback은 정책 전환만이 아니라 플래그 하나(F25)나 실행 모드 강등(F26)으로도 일어남 |

D10–D18은 사용자가 확정한 제품 사양이 아니라, 이번 근거를 바탕으로 제안하는 설계 결정이다. 이후 실측이 반박하면 원래 근거와 변경 이유를 남기고 수정한다.
