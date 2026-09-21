# 03. 실험 구성과 구현 백로그

> v0.2 / 2026-09-21. **실측 결과가 아니라 실행 가능한 평가를 준비하기 위한 계획**이다. 기간·절감률·최종 모델 선택을 약속하지 않는다.

## 1. 무엇이 이득을 냈는지 분리한다

| Arm | 모델 선택 | 문맥 | 확인할 질문 |
|---|---|---|---|
| A0 | 고가 모델 고정 | 원래 read 경로 | 정상 기준선은 어디인가? |
| A1 | 저가 모델 고정 | A0와 같은 read 경로 | router 없이도 충분한가? |
| A2 | 고가 모델 고정 | 코드 기반 범위 축소 | 의미 모델 없이 얼마나 줄어드는가? |
| A3 | 저가 모델 고정 | A2와 같은 축소 | 더 싼 단순 조합이 있는가? |
| A4 | 규칙 router | A2와 같은 축소 | 모델 기반 판단의 필요성이 있는가? |
| A5 | 기존 공개 router | A2와 같은 축소 | Switchyard 등 재사용으로 충분한가? |
| A6 | A4의 실제 배정 + Jev shadow | A2와 동일 | 실제 배정에 영향을 주지 않고 추천이 유효한가? |
| A7 | 검증된 선택 정책 | SWE-Pruner 또는 Jev 검색 한 종류 | 의미 선별의 추가 비용과 품질 변화는? |

한 번에 모두 실행하지 않는다. A0/A1부터 측정하고, A2/A3, 그다음 routing과 의미 선별로 확장한다. A6의 비용에는 shadow 호출도 포함하지만 shadow 모델의 성능을 worker의 해결 성능으로 표시하지 않는다.

native 하네스의 자체 auto-routing과 비교할 수 있으면 별도 제품 구성 기준선으로 둔다. 그 하네스가 실제 모델별 비용을 노출하지 않으면 API 기반 arm과 완전한 금액 대조라고 하지 않는다.

## 2. task마다 고정할 manifest

```text
task_id / task_family / task_text_hash
repo_snapshot / environment_image_digest / dependency_lock
write_scope / required_capabilities / risk / data_disclosure_policy
acceptance_manifest_hash / holdout_verifier_revision
harness_revision / actual_model_revision / policy_revision
input-output-step-time limits / retry rule / cache regime
seed or repetition ID / run order / evaluator identity
```

같은 과제를 동일 verifier로 평가한다. 한 arm에만 더 좋은 요구사항, 더 많은 시도, 이미 고친 workspace, 더 긴 문맥을 주지 않는다. 프로바이더 모델 alias가 바뀌면 새 조건으로 표시하고 기록한다.

실행 순서를 섞어 공급자 혼잡이나 시간대 효과가 한 arm에 몰리지 않게 한다. cold cache와 warm cache를 나누고, 정확 결과 캐시나 정답 patch가 다른 arm으로 넘어가지 않게 한다. 캐시 읽기·쓰기·uncached input·output의 raw usage와 정규화 의미를 보존한다.

## 3. 단일 버그 점수만으로 큰 프로젝트를 주장하지 않는다

평가 단위를 세 층으로 나눈다.

| 층 | 구성 | 성공 기준 |
|---|---|---|
| Smoke | 작은 합성 오류·권한·중단 사례 | 제어 흐름과 측정이 정상인지 |
| Task | 실제 저장소의 국소 수정·설명·테스트·설계 과제 | 고정된 수용 기준과 비용 |
| Milestone | 서로 의존하는 여러 task와 통합 변경 | 마지막 통합 상태의 사용자 시나리오 통과 |

초기 smoke는 경제성 증명이 아니다. 실제 task pilot에는 한국어 지시+영어 코드, 정보 누락, baseline 환경 실패, 국소 수정, 교차 모듈 변경을 포함한다. 수십 개 표본으로 시스템 동작과 주요 실패를 확인할 수 있지만 희귀한 위험 오류율이나 작은 품질 차이까지 확정할 수는 없다.

Milestone 예시는 인터페이스 정의 → 구현 두 묶음 → 통합 회귀 검사다. task별 PASS만 더하지 않고 최종 head에서 전체 시나리오를 다시 실행한다. 동일 파일을 동시에 수정해야 하는 과제는 초기 병렬 표본에서 제외하거나 의도적인 충돌 시험으로 분리한다.

## 4. 평가 결과는 다차원으로 남긴다

```text
accepted / review_ready / failed / blocked / unknown
각 task의 baseline 대비 결과
총 공급자 비용 / 추정 비용 / 미확인 비용
router·judge·pruner·worker·verifier 비용의 분리
실제 frontier 호출·입력·출력 / cache miss
재시도 횟수 / 종단간 시간 / 사람의 검토·수정 시간
원본 읽기와 재읽기량 / 검색 coverage / 필요한 위치 recall
regression / 범위 위반 / stale proof / 중복 실행
```

`REVIEW_READY`와 최종 사용자 수용을 분리한다. 처리 불가능하거나 결과가 불명확한 실행을 분모에서 몰래 제외하지 않는다. 일부 API 청구가 미확인이면 총비용도 불완전하다고 표시한다.

### 기본 비교식

`cost_per_accepted = 실패·재시도·보조 모델까지 포함한 총비용 / 수용 작업 수`

저가 모델에서 프론티어로 넘어가며 문맥이 길어지면 상향 비용이 직접 고가 호출보다 커질 수 있다. judge가 없어서 실패를 감지하지 못한 경우에도 별도 품질 오류로 기록한다. 더 싸고 더 많이 틀리는 설정은 비용–품질 tradeoff이지 동일 품질 절감이 아니다.

품질 목표와 허용 손실은 실험 전에 정한다. 결과를 보고 통과선을 낮추지 않는다. 샘플이 적으면 paired 결과를 그대로 제시하고, 동등성이나 일반 우위를 확정하지 않는다.

## 5. Jev·분류기의 구체 평가

Jev가 출력한 `cheap_worker` 확률, 공급자 confidence, 실제 cheap worker의 성공 확률을 다른 값으로 기록한다. 초기에는 모델 임계값을 운영 승인권으로 쓰지 않는다.

### task routing

잘못된 하향 배정, 불필요한 상향, `needs_context`를 놓친 경우, 고확신 오답, 보류율을 구분한다. 같은 내용을 한국어/영어로 바꾸고 후보 순서를 바꿔도 정책이 과도하게 흔들리지 않는지 본다.

### 코드 후보 선별

질문마다 필요한 파일/행의 정답 근거를 독립적으로 지정한다. Recall@k, 전달 토큰, API/GPU 비용, 재검색·expand 횟수를 함께 본다. grep으로 찾을 수 있는 식별자 과제와 실제 의미 검색 과제를 나누어, 불필요하게 모든 검색을 Jev로 대체하지 않는다.

정답 위치가 없거나 일부만 검색했을 때 ‘코드가 존재하지 않는다’는 단정이 나오지 않아야 한다. 원문에 포함된 지시문이 도구 권한이나 모델 선택 정책을 바꾸면 안 된다.

## 6. 새 구성 요소를 추가하는 통과 조건

| 추가 기능 | 먼저 보여야 할 것 | 실패하면 |
|---|---|---|
| read 선별 | 같은 task에서 품질 기준 충족, 원문 복구 가능, 총비용 이득 | 원문 경로로 복귀 |
| routing | 저가/고가 단독·규칙 대비 실질적인 비용–품질 이점 | 고정 모델/규칙 유지 |
| Jev 실제 배정 | shadow holdout 성능과 보류 정책이 정한 기준 충족 | shadow 유지 또는 비활성 |
| 두 worker 병렬 | 독립 범위·통합 통과·시간/비용 목적의 개선 | 단일 worker 유지 |
| 영속 DB/큐 | 실제 동시 예약·복구 문제가 파일/기존 도구로 해결되지 않음 | 새 인프라 추가 안 함 |
| full workflow engine | 고정 절차로 표현하기 어려운 여러 검증된 흐름 | bounded_patch 유지 |

최저 비용만을 위해 품질 기준을 숨기지 않는다. 시간 단축이 목적이라 비용이 늘어나는 선택도 가능하지만, 그것은 별도의 사용자 가치 판단이며 ‘토큰 절감 성공’으로 표기하지 않는다.

## 7. 구현 백로그 — 지금 바로 시작할 수 있는 작은 단위

아래 항목은 GitHub issue를 실제로 생성했다는 뜻이 아니라 구현 ticket 명세다. 다른 프로젝트에 변경을 가하지 않았고 유료 실행도 시작하지 않았다.

### V02-01 — TaskEnvelope와 RunManifest resolver

입력: 승인된 task와 고정 snapshot. 출력: 실제 경로·commit·정책 hash를 확인한 manifest. 작업 범위, 외부 전송, 지원 capability를 검사한다.

완료 조건: 없는 commit, stale policy, worker가 바꾼 acceptance, 권한 밖 경로를 거부한다. 오프라인 JSON 검사와 실제 filesystem 검사를 분리한다.

### V02-02 — 최소 하네스의 단일 실행 adapter

입력: manifest. 출력: 원본 trajectory, exit status, candidate, raw usage. mini-swe-agent를 실제 고정 revision으로 설치해 적합성을 확인한다. host에 직접 임의 명령을 실행하는 기본 local environment를 무인 실행용으로 채택하지 않는다.

완료 조건: 정상·실패·제한 초과·형식 오류·중지에서 결과와 비용이 누락되지 않는다. 하네스 비용 한도의 사후 검사와 실제 노출 상한을 구분한다. 환경/키가 없으면 mock 결과만 남기고 실제 실행 통과로 표시하지 않는다.

### V02-03 — 독립 verifier와 ProofBundle

입력: patch 후보와 trusted acceptance manifest. 출력: 실제 후보 hash에 연결된 검사·로그·기준 결과.

완료 조건: worker 자기 승인, 삭제/약화한 테스트, 다른 후보의 PASS, stale base, 일부 검사를 생략한 PASS를 거부한다. host가 verifier identity와 산출물 경로를 통제한다.

### V02-04 — A0/A1 paired 보고서

입력: 같은 실제 task들의 두 arm 결과. 출력: task별 성패, 비용, 시간, 검토 시간, unknown 목록.

완료 조건: 실패 비용과 미확인 청구를 숨기지 않고, baseline/환경/캐시가 다른 run을 같은 조건으로 집계하지 않는다. 이것이 첫 유의미한 경제성 결과다.

### V02-05 — 원문 보존형 read 선택기

입력: read 결과와 focus question. 출력: 원본 행·hash·생략 metadata·expand ID. 처음은 규칙 기반 범위 선택으로 구현하고, 이후 SWE-Pruner/Jev 검색을 교체 후보로 시험한다.

완료 조건: full-output fallback, 정확한 원문 복구, 권한 없는 원격 전송 차단, 알려진 정답 위치 recall과 총비용 비교.

### V02-06 — 규칙·기존 router·Jev shadow 비교

입력: 실제 task 특징과 후속 검증 실패. 출력: 선택 추천·이유 코드·비용·policy revision.

완료 조건: 모델 선택자는 하나이며, 매 턴 judge의 비용을 별도 대조할 수 있다. 불명확한 입력을 자동 저가 경로로 보내지 않는다. shadow 결과는 실제 모델을 바꾸지 않는다.

### V02-07 — native adapter / Symphony 적합성 시험

입력: 실제 사용할 계정·하네스·tracker의 명시적 설정. 출력: `start/events/cancel/inspect/collect` 지원 보고서와 한 작업의 REVIEW_READY 결과.

완료 조건: 코드·권한·취소 경계가 확인되고 실제 구독/API 사용량을 가능한 범위로 기록한다. 문서상 기능만 보고 지원 체크를 켜지 않는다. 기존 scheduler의 기능이 충분하면 새 scheduler를 구현하지 않는다.

### V02-08 — 두 task의 milestone 실험

입력: 독립 수정 범위와 고정 인터페이스를 가진 task 두 개. 출력: 통합 head의 회귀 결과와 단일 실행 대비 비용·시간.

완료 조건: stale 결과, 충돌, baseline 실패, 취소, 전체 예산 노출을 검사한다. 이 단계 전에는 ‘대규모 협업이 검증됐다’고 말하지 않는다.

## 8. 이번 작업의 완료 범위

사례별 관측 성과와 한계, 실제 코드/명세의 재사용 경계, v0.1 변경점, 하나의 구체 실행 절차, 실험군, 구현 ticket을 정리한다. 합성 설정·증거·오프라인 검사로 문서 내부의 일부 불변 조건을 확인한다.

실제 task resolver, 하네스 실행, 권한 sandbox, 유료 API, 모델 비교, 영속 복구, 실제 금액 절감은 후속 구현/실험 범위다. 검사 결과는 별도 VALIDATION 문서에 실제 수행한 항목만 기록한다.
