# 시스템 구조와 실행 계약

[v0.3 안내](README.md) · [어댑터](02-adapters.md) · [결정/평가](04-decisions-and-evaluation.md). 아래 구조·필드·정책은 **우리 설계 제안**이다. 실제 runner나 schema를 구현했다는 뜻이 아니다.

## 1. 최적화 목표

일차 목표는 **허용 품질·기한 안에서 수용된 작업 수를 늘리고, 추가 청구·구독 한도 소모·재작업을 줄이는 것**이다. 최소 token 자체가 목적이면 필요한 근거까지 지워 실패를 늘릴 수 있다. 구독 요금은 고정비이고 API·추가 credits는 변동비이므로 따로 본다. 결과가 같아도 기다릴 수 있는 작업과 즉시 끝내야 하는 작업의 최적 배정은 다르다.

한 작업의 측정 벡터는 `(검증 통과, 추가 지출, 공급자별 quota 사용, 전체 token, 시간, 사람 수정 시간)`이다. quota 단위가 서로 다르면 합쳐서 가짜 달러 가격을 만들지 않는다. 내부 우선순위 점수가 필요할 때만 명시적인 가중치를 사용하고, 실제 청구액과 분리해 보관한다. 근거: E01/E04/E09/E19, 결정 D07.

## 2. 서로 분리할 네 가지 개념

| 개념 | 책임과 기록 예 |
|---|---|
| 모델 profile | task 종류별 품질, effort, context 한도, 지원 modality, tokenizer, 모델 revision |
| 하네스 adapter | 도구·파일 편집·session resume·취소·이벤트·권한 지원, CLI/runtime version |
| 구독/과금 profile | 계정의 비밀이 아닌 alias, auth 경로, entitlement, 공유 quota pool, credits fallback, 마지막 확인 시각 |
| 작업 role | 탐색·계획·구현·검증 등 이번 작업의 책임, 필요한 capability, 입력·출력·완료 조건 |

`provider=harness=model=subscription`으로 한 필드에 넣으면 새 모델 추가나 같은 quota 공유를 처리하기 어렵다. Jev는 작은 분류 capability를 가진 후보이지 전체 실행 권한의 소유자가 아니다. 계정 token은 native 도구가 보관하며 registry에 복사하지 않는다.

Registry의 최소 필드 제안: `adapter_id`, `runtime_version`, `model_profile_id`, `auth_mode`, `funding_mode`, `quota_pool_id`, `capabilities`, `policy_checked_on`, `source_ids`, `health`, `observability`. 관측하지 못한 한도는 `null + unknown`, 구독 경로는 `configured`와 `documented_supported`를 구분한다. 현재 세 도구는 후자만 조사했고 전자는 미설정이다.

## 3. 구성 요소와 단일 책임

| 구성 요소 | 맡는 일 | 맡지 않는 일 |
|---|---|---|
| 입구: MCP/CLI/UI | 사용자의 작업을 task card로 접수하고 상태·산출물을 조회 | 자체 다중 manager 계획 반복 |
| Task controller | 상태 전이, task/attempt ID, 재시도 한도, 작업 lease, 종료 | 모델의 자기 보고를 검증 결과로 승인 |
| Policy + scheduler | entitlement·권한·가용 한도로 후보를 걸러 queue 배정 | quota를 우회하거나 조용히 API 과금으로 변경 |
| Router | 허용 후보 중 작업 종류·실패 기록·지연에 맞는 profile 선택 | 권한 확대·budget 변경·merge 승인 |
| Context builder | 원문 위치·hash·필요 부분·완료 조건을 worker에게 전달 | 모든 agent의 대화를 공용 prompt에 누적 |
| Native adapter | CLI/SDK 실행, 이벤트 정규화, 명시 session 재개·취소 | provider 간 내부 reasoning/history 형식 변환 |
| Artifact/evidence store | patch, 원문, 검증 로그, usage, source provenance 보관 | raw 로그 전체를 자동으로 모델/Git에 전송 |
| Verifier | candidate digest에 연결된 명령·검사·수용 조건 평가 | 성공 기준을 worker가 사후 약화하도록 허용 |

**논리적 분리이지 microservice 여덟 개를 만들자는 제안이 아니다.** 첫 구현은 Python 로컬 프로세스와 파일 기반 산출물로 충분하다. 초기는 한 active task와 한 writer로 journal을 운용한다. 중단 복구·복수 task lease를 실제 도입할 때 embedded SQLite 등 원자적 metadata 저장소를 검토한다. 분산 queue나 별도 DB server는 필요하지 않다. E23의 DB 없는 복구 접근도 후보로 남긴다.

현재 native 하네스 안의 도구 loop와 외부의 task loop를 구분한다. 외부 controller는 tool call마다 계획을 다시 세우지 않는다. native 내부 팀 기능을 사용하는 경우 그것을 하나의 실행 전략으로 등록하고 내부 호출까지 계측한다. 외부 controller와 내부 Teamwork가 동시에 무제한 재위임하지 않게 전체 fan-out/시간 예산의 소유자를 하나로 둔다.

## 4. 역할은 필요할 때만 만든다

| 역할 | 첫 배정 원칙 | 강한 모델로 올리는 조건 |
|---|---|---|
| 형식 검사·diff 통계·중복 제거 | 일반 코드, parser, `rg` | 규칙으로 결정 불가능한 의미 판단만 분리 |
| 자료 추출·분류 | 검증 가능한 출력의 저비용 후보; 나중에 로컬 모델 | 원문 불일치·한국어/코드 혼합 실패·abstain |
| 탐색 | 필요한 파일·호출 경로·재현 조건을 찾는 단일 worker | 광범위 의존성이나 모순된 관찰 |
| 계획 | task가 모호하거나 큰 경우에만 강한 후보 | 계획 자체의 불확실성이 높은 경우 |
| 구현 | 해당 task군에서 검증된 가장 경제적인 coding profile | 검증 실패, 범위 증가, 원인 불명, 고위험 변경 |
| 검증 | 우선 test/build/lint/정해진 재현; 필요시 별도 리뷰 | 보안·공개 API·복잡한 동시성 등 기계검사의 사각지대 |
| 통합 | 단일 통합자; dependency 순으로 candidate 결합 | 충돌과 설계 불일치가 있는 경우 |

‘작은 모델’도 shell·검색·편집을 여러 번 하면 비쌀 수 있다. native 하네스의 시작 prompt·tool 정의 비용 때문에 한 줄 분류마다 새 CLI를 띄우는 것도 손해일 수 있다. 규칙으로 처리하거나, 같은 문맥과 완료 조건을 공유하는 작은 작업을 묶는 방식과 비교한다. 이미 parent가 계획한 단순 수정은 planner를 생략한다. 역할 분리 이익은 모델의 브랜드가 아니라 task의 분해 가능성과 skill 차이에서 검증한다. E15/E17/E18/E19, D02/D04.

예시: 부모 Codex가 실패 원인을 찾았다면 Claude/Antigravity worker에 **관련 함수·불변식·재현 명령·수정 범위**를 준다. worker는 patch와 증거 참조만 반환한다. 실패 시 다른 모델에 ‘처음부터 전부 분석’시키기보다 실패 로그와 candidate를 넘긴다. 다만 추측이 틀린 것이 원인이면 기존 계획을 정답처럼 고정하지 않고 재진단한다.

## 5. 실행 생명주기

```text
RECEIVED → PREFLIGHT → QUEUED → RUNNING → VERIFYING → REVIEW_READY
                 ↘ BLOCKED          ↘ FAILED         ↘ REPAIR_QUEUED
                         RUNNING → CANCEL_REQUESTED → CANCELLED/UNKNOWN
```

- PREFLIGHT: base snapshot·task 범위·완료 조건·auth/funding 경로·adapter version·기능을 확인한다. 필요한 기능이 없으면 불완전한 실행 대신 명시적으로 차단한다.
- QUEUED: dependency, workspace lease, quota pool 동시성, deadline을 확인한다. 하나의 사용 가능한 구독 안에서도 task 우선순위를 둔다.
- RUNNING: `task_id` 아래 시도마다 별도 `attempt_id`와 명시 `native_session_id`를 기록한다. 한 provider 세션은 하나의 동시 실행만 소유한다.
- VERIFYING: 실제 diff/commit digest, 사용한 명령, exit code, 검증 로그를 연결한다. timeout·skip·권한 거절은 PASS가 아니다.
- REPAIR: 첫 pilot은 수리 최대 1회. 같은 시도 재개와 새 후보 실행을 구분한다. 한도 초과·인증 실패에는 내용을 바꿔 재추론하지 않는다.
- REVIEW_READY: 테스트 범위와 남은 불확실성을 표시한 결과. 외부 상태 변경이나 병합은 사용자 task에 이미 부여된 권한 범위로 결정한다. pilot의 기본 종료점은 검토 가능한 candidate다.

`exit 0`과 task 성공은 다르다. 특히 E08의 headless soft-denial처럼 도구 실행이 거절됐어도 프로세스가 정상 종료할 수 있다. **모델의 success 문자열 → 실제 artifact → 독립 검사**라는 세 층을 분리한다.

취소 요청 후 process 종료를 관측하지 못하면 `UNKNOWN`으로 남기고 workspace lease를 유지한다. CLI wrapper를 종료했다고 그 자식 shell이나 원격 실행까지 중단됐다고 가정하지 않는다. Windows에서는 프로세스 트리 종료·경로 제한·남은 자식 처리를 adapter별 conformance test로 확인한다.

재시작 시 journal의 `RUNNING`을 그대로 재실행하지 않는다. PID/session/workspace/candidate를 대조하여 살아 있는 실행을 재연결하거나 `UNKNOWN`으로 전환한다. 같은 요청의 재전송은 idempotency key로 기존 run을 반환하되, CLI 내부 부작용의 exactly-once까지 보장한다고 주장하지 않는다.

## 6. 작업 카드와 문맥 패킷

**기계용 manifest**에는 auth profile, budget, file scopes, lineage, policy revision, artifact digest를 담는다. **모델용 packet**에는 목표·완료 조건·제약·필요 원문 참조만 담는다. 모델이 알 필요 없는 전체 registry와 usage journal을 prompt에 반복하지 않는다.

아래는 형태를 설명하는 예시이며 실제 파일이 존재하는 실행 입력도, v0.2 schema fixture도 아니다.

```json
{
  "task_id": "example-task-17",
  "role": "implement",
  "objective": "빈 목록에서 요약 함수가 예외를 내지 않도록 수정",
  "scope": ["src/summary.py", "tests/test_summary.py"],
  "constraints": ["공개 함수 시그니처 유지", "새 의존성 추가 없음"],
  "context_refs": [{"artifact_id": "source-snapshot-17", "section": "summary entry point"}],
  "acceptance_ref": "acceptance-17",
  "return": ["patch_ref", "evidence_refs", "unresolved"]
}
```

artifact ID는 실제 resolver가 접근 범위·digest를 검증해 읽을 수 있어야 한다. 단지 URL처럼 보이는 문자열만 보내면 문맥 전달이 아니다. worker의 격리 workspace 안에 필요한 원문을 materialize하거나 scoped read tool을 제공한다. 원본 revision/줄 범위를 저장하고 큰 결과는 section/line 단위로 조회한다.

긴 tool result는 먼저 파일로 보관하고, 코드로 필터한 요약·경로·실패 부분만 모델에 보여준다. 요약에는 `facts / decisions / unresolved / next / source_refs`를 구분한다. 제약·실패 이유·반례를 제거해서 다음 모델이 실패한 행동을 반복하지 않게 한다. 정당한 원문 재조회 경로도 남긴다. **JSON은 구조를 검증하기 위한 형식이지 압축 알고리즘이 아니다.** E27/E29.

이 최적화는 우리가 관리하는 입출력 경계부터 적용한다. wrapper만으로 native 하네스 내부의 모든 read/tool result를 가로채거나 줄일 수는 없다. 내부 pruning은 해당 하네스의 공식 hook/extension 지점이 확인될 때 별도 기능으로 구현한다. 그런 지점이 없으면 초기 packet·외부 tool 반환·인계 크기만 줄이고, 내부 token은 관측 가능한 범위에서 측정한다.

## 7. 세션 전환과 캐시

동일 task를 같은 하네스에서 이어갈 때에는 해당 세션을 재개한다. 다른 provider로 옮길 때는 새 세션에 정리된 task packet·candidate·검증 로그를 넘긴다. 내부 thinking·암호화 reasoning·tool history를 공통 대화로 강제 변환하지 않는다. 새 provider가 원문을 다시 읽는 비용은 `handoff_cost`에 포함한다.

문맥 캐시 key에는 source revision, selector, schema/prompt revision, model/harness profile을 포함한다. 사용자가 바꾼 파일이나 수용 조건이 달라졌으면 관련 결과를 무효화한다. stable prefix와 task별 부분을 나눌 수 있지만 캐시 지원 조건을 실제 backend에서 측정한다. 자주 모델을 바꿔 cache를 잃는 비용과 pruning 후 cache 손실도 기록한다. E28은 API 근거이며 구독의 한도 환급을 의미하지 않는다.

## 8. 병렬화와 변경 소유권

초기는 한 worker. 이후 **서로 독립적인 읽기 조사**, 또는 interface/파일 소유권이 합의된 독립 변경만 병렬화한다. 같은 base에서 분리 worktree를 만들고 한 candidate를 검증한 뒤 dependency 순서로 통합한다. 공유 파일이 겹치면 통합자가 순차 적용한다. 결합 후 검증도 다시 한다.

worker가 다른 worker의 초안을 읽으려면 명시 artifact dependency가 있어야 한다. 모두가 같은 대화·동일 파일을 실시간 수정하는 shared chat 방식은 기본 구조에 넣지 않는다. fan-out은 planner 수가 아닌 **전체 실행 수·토큰/시간·quota 예산**으로 제한한다. 복제 후보 여러 개를 만드는 방식은 어려운 과제의 선택적 실험으로 둔다. E14/E15/E18/E21, D04.

## 9. 확장 지점

`NativeHarnessAdapter`, `ApiWorkerAdapter`, `DecisionPlugin`, `ContextSelector`, `Verifier`, `UsageNormalizer`를 분리한다. 새 구독은 adapter와 entitlement profile을 추가한다. Jev류는 DecisionPlugin 또는 read-only ContextSelector로 붙인다. 출력은 route 후보·선택한 원문 span·abstain이며 권한이나 최종 성공 판정이 아니다. 실패하면 기존 규칙과 원문 조회로 복귀한다.

핵심은 **새 판단 모델을 추가해도 task·artifact·검증·회계의 계약을 바꾸지 않는 것**이다. 학습/실험 도구의 내부 format은 adapter 안에 한정한다.
