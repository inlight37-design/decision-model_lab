# 토큰 낭비 측정, 비용 비교, 첫 구현 순서

2026-09-22 제안. [조사 근거](README.md), [Codex 연결 설계](codex-bridge.md). 이 문서의 숫자 예시는 실측이 아니며 사용자 예산으로 설정되지 않았다.

## 1. 왜 JSON으로 주고받아도 낭비가 생기나

JSON은 필드와 형식을 검증하기 좋은 통신 형식이다. 모델에 동일한 정보를 넣는다면 그 정보를 처리하는 비용은 여전히 생긴다. 키 반복, JSON 안에 넣은 긴 자연어, 출력 설명의 중복 때문에 더 길어질 수도 있다. gzip은 전송 바이트를 줄이지만 압축 해제 뒤 모델이 읽는 토큰을 자동으로 줄이지 않는다.

| 낭비 후보 | trace에서 확인할 증거 | 먼저 적용할 변경 |
|---|---|---|
| 전체 대화의 worker 복제 | task마다 비슷한 큰 입력 prefix | 작업 카드와 관련 근거만 전달 |
| worker가 parent의 조사를 반복 | 같은 경로·검색·문서 읽기가 반복 | 이미 확인한 사실과 원문 참조 인계 |
| 큰 로그와 도구 정의 | 대형 tool result, 사용하지 않은 schema | 서버 측 필터, 필요할 때 도구 정의 로드 |
| 상시 planner/judge | 진행 때마다 비싼 모델 호출 | 시작/실패/범위 변화 같은 사건으로 제한 |
| 빈번한 모델 전환 | 캐시 적중 하락, state 오류, 재설명 | task 동안 provider/model 유지 |
| 과도한 결과 설명 | parent가 전체 trajectory를 다시 읽음 | patch·실패 구간·요약만 반환 |
| 작은 모델의 반복 실패 | 재시도·재조회가 누적 | 한정된 수리 후 상향/중지 |
| 요약이 지나치게 짧음 | 같은 원문을 계속 다시 읽음 | 작업에 필요한 근거를 초기 packet에 추가 |
| 중복 호출/이중 retry | 같은 작업이 여러 번 실행 | idempotency와 재시도 소유자 하나 |
| 너무 많은 병렬 작업 | 충돌·통합 실패·폐기된 patch | 의존 관계와 쓰기 범위를 먼저 분리 |

사용자가 경험한 낭비가 어느 항목 때문인지는 현재 실행 trace가 없어 특정하지 않는다. 조사 근거가 있는 일반 패턴과 실제 진단을 구분한다.

합성 계산 예시: 작업 4개에 각 20,000 토큰의 전체 문맥을 전달하면 최초 전달만 80,000 토큰이다. 작업별 3,000 토큰 packet이면 12,000이다. **여기서의 85% 감소는 최초 문맥 전달만의 산술 결과**다. 작업 중 도구 읽기, parent, 출력·추론, 실패·수리, 캐시를 포함한 실제 절감률이 아니다. 새로운 세션으로 같은 문맥을 읽혀도 캐시 조건에 따라 청구가 달라진다.

## 2. raw 토큰, 청구 비용, 성공을 함께 본다

주 지표는 다음 세 가지다.

1. **작업 수용률:** 사전에 정한 수용 기준을 통과한 작업 / 배정한 전체 작업.
2. **수용 결과당 총비용:** 실패·중지·재시도를 포함한 전체 비용 / 수용된 작업 수.
3. **완료 시간 분포:** end-to-end 중앙값·p95와 timeout 비율.

수용 0개면 결과당 비용은 0이 아니라 계산 불가/무한대로 표시한다. 성공한 실행의 비용만 평균 내면 실패가 잦은 정책이 유리해 보인다. 품질 저하를 숨기기 위해 비용 지표의 분모를 바꾸지 않는다.

비용은 parent, worker, router, reviewer, summary/compaction, 재시도, 도구, 로컬 compute를 모두 포함한다. shadow 판단도 측정 기간에 실제 돈/전력을 썼다면 실험 지출이다. 배포 가정 비용과는 별도 열에 둔다.

API 비용은 provider가 정의한 **서로 겹치지 않는 청구 항목**을 사용한다.

```text
API 비용 = 일반 입력 청구 + 캐시 쓰기 청구 + 캐시 읽기 청구
         + 출력 청구 + 별도 청구 도구/기능 비용

전체 비용 = 모든 실행 주체의 API 비용
          + 로컬 compute + 검증 실행비 + 저장/운영비
```

provider마다 input/output usage에 cache·reasoning이 포함되는 방식이 다를 수 있다. `input_tokens`에 cached input이 이미 들어 있거나 `output_tokens`에 reasoning이 들어 있으면 다시 더하지 않는다. 사용량 정규화 규칙과 가격표 revision을 함께 기록한다. 소스에서 없는 reasoning 항목은 `unknown`으로 두고 추측하지 않는다.

구독 경로는 별도다. 실제 추가 청구, 계정 사용량/한도, API 가격으로 환산한 참고값을 나눈다. 미확인 청구를 $0로 처리하지 않는다. 로컬 전력·장비 감가·유휴 시간도 사용 패턴에 맞게 산정하되 실제 측정과 추정을 구분한다.

## 3. 캐시가 있으면 입력 길이만으로 비용을 판단할 수 없다

OpenAI 공식 문서는 렌더링된 prefix의 일치와 적격 cache breakpoint가 재사용에 영향을 준다고 설명한다. 모델·설정별 규칙이 있으며, 앞쪽 내용 변경이나 compaction은 재사용을 줄일 수 있다. ‘고정 system prompt면 무조건 캐시 hit’라고 단순화하지 않는다. [공식 Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)

적용할 설계 판단:

- 가능한 한 안정적인 지시·도구 정의를 유지하고 작업 데이터는 뒤쪽에 배치한다.
- timestamp·run ID 등 모델이 필요하지 않은 값을 재사용 prefix에 매번 주입하지 않는다.
- 동일 task는 native 세션을 유지하되 관련 없는 새 task까지 한 대화에 계속 붙이지 않는다.
- 캐시를 위해 무의미한 문장을 채우지 않는다. 필요한 문맥의 정보 밀도와 청구액을 함께 본다.
- 캐시와 compression을 동시에 바꾼 비교만으로 compression의 효과를 주장하지 않는다.
- 앱/harness가 제어하는 캐시 설정을 bridge가 바꿀 수 있다고 가정하지 않는다. 실제 노출된 옵션과 usage를 확인한다.

**토큰 수 감소, 청구액 감소, 품질 유지, 지연 감소는 서로 다른 결과**다. 네 지표를 별도로 보고한다.

## 4. 이벤트와 usage 최소 계약

제안 event record의 필드다. 모든 record를 모델에게 보내지는 않는다.

| 필드 | 의미 |
|---|---|
| `run_id`, `task_id`, `attempt`, `parent_run_id` | 중복·부모 자식 관계 추적 |
| `event_id`, `source_request_id` | 재수신 이벤트·동일 API 요청의 이중 집계 방지 |
| `harness`, `harness_version`, `model_revision`, `provider` | 실행 조합 식별 |
| `role` | parent / worker / router / verifier / compressor |
| `usage_source` | provider / harness / tokenizer_estimate / unavailable |
| `usage_semantics` | request delta / turn delta / thread cumulative |
| `input_tokens`, `cache_read_tokens`, `cache_write_tokens`, `output_tokens` | 정규화된 사용량, 모르면 null |
| `reasoning_tokens`, `reasoning_included_in_output` | 지원하는 경우에만 관측·중복 여부 |
| `cost`, `cost_status`, `pricing_revision` | observed/estimated/unknown과 근거 |
| `latency_ms`, `terminal_status` | 지연, 성공/실패/취소/미확인 |
| `artifact_refs`, `candidate_hash`, `verification_ref` | 실행과 실제 검증 결과의 연결 |

MCP bridge에서 parent usage를 못 보면 `parent_cost_status=unknown`이다. worker 부분 절감만 보고하고 전체 절감으로 표현하지 않는다. 누적 usage 이벤트는 최종값 또는 검증된 delta를 사용한다. 같은 provider usage와 gateway usage를 동시에 더하지 않는다. runtime 버전을 바꿀 때 event 의미도 다시 확인한다.

원본 로그는 접근을 제한한 저장소에 보관하고 키·민감 데이터를 제거한 요약만 Git에 넣는다. payload 중복률은 hash로 추적할 수 있지만, 서로 다른 tokenizer의 토큰 수를 단순 비교하지 않는다. 문맥 원인 분석용 추정치는 실제 청구 usage와 구분한다.

## 5. 저가 먼저 실행하는 것이 언제 이익인가

단순화한 의사결정식이다.

```text
F = 처음부터 고성능 경로를 쓸 때의 검증 포함 비용
L = 저가 경로 1회의 검증 포함 비용
O = router + parent 인계 등 추가 비용
p = 저가 경로가 독립 수용 기준을 통과할 확률

저가 먼저 실행의 기대비용 = L + O + (1-p) × F
고성능 직행보다 저렴한 조건 = p > (L + O) / F
```

가상의 `F=$1`, `L=$0.20`, `O=$0.05`라면 `p>25%`가 비용상 손익분기다. `p=80%`일 때 기대값은 $0.45다. **실측값이 아니며 성공 품질이 같다는 증명도 아니다.** 고성능 fallback 비용이 이전 실패로 달라지거나 시간 제한이 있으면 식을 수정해야 한다. 저가 작업을 잘못 통과시키는 verifier의 오류도 별도로 평가해야 한다.

실제로는 모델의 자기 확신이 아니라 동일 작업군의 독립 검증 데이터로 p를 추정한다. 고가 대비 이익이 있어도 저가 단독보다 거의 나아지지 않는다면 routing의 복잡성을 정당화하기 어렵다.

## 6. 평가군: 한 번에 하나씩 바꾼다

v0.2의 평가군을 다음 순서로 축소 실행한다. 아래 샘플 수는 제안이며 유료 실험을 시작하라는 설정이 아니다.

| 단계 | 비교 | 알아낼 것 |
|---|---|---|
| E0 | 고성능 모델 + 현재 하네스 | 품질·총비용 기준선 |
| E1 | 같은 모델/하네스 + 간결한 task packet·도구 출력 | 문맥 설계 자체의 효과 |
| E2 | 호환 가능한 같은 하네스 + 저가 모델 + E1 문맥 | 저가 단독이 충분한가 |
| E3 | 규칙 배정 + 저가/고가 + E1 문맥 | 코드 정책만으로 얻는 이익 |
| E4 | E3에 로컬 decision model을 shadow로 추가 | 판단이 달라지는 task와 추가 비용 |
| E5 | 검증된 로컬 판단을 실제 배정에 사용 | E3 대비 순이익 |
| E6 | 독립 작업 2개 병렬 또는 어려운 작업 후보 합성 | 시간 단축·성공률 변화와 총비용 증가 |

원래 Codex 하네스에서 저가 모델을 동등하게 지원하지 않으면 E2를 억지로 동일 조건으로 만들지 않는다. 이때는 mini-swe-agent 같은 고정 하네스 안에서 모델 비교를 따로 수행하고, native Codex 대비 결과는 **전체 시스템 비교**로 표시한다. 모델·하네스·prompt·tool 범위를 함께 바꾸고 ‘모델만의 효과’라고 부르지 않는다.

첫 smoke set은 실제 사용할 프로젝트에서 작고 대표적인 작업 10~20개로 잡는다. 버그 수정, 한정된 기능, 회귀 테스트, 코드 위치 탐색, 한국어 요구/영문 코드 혼합을 포함한다. 전체 시스템을 한 번 돌려 볼 목적이다. 그 후 비용에 맞춰 30~50개 수준의 paired pilot을 구성하고 변동이 큰 과제는 반복한다. 이 정도 표본만으로 1~2%p 품질 차이가 없다고 증명하지 않는다.

작업별 같은 기준 snapshot·같은 수용 검사·같은 제한을 사용한다. 실행 순서를 섞고 cache 상태와 환경 오류를 기록한다. 모델 profile과 router threshold는 개발 세트에서 정하고 holdout 결과를 보고 다시 맞추지 않는다. 정책마다 성공한 task가 다를 수 있으므로 평균 점수뿐 아니라 paired 성공/실패 표를 보존한다. 반복이 있으면 task 단위로 묶어 불확실성을 계산한다.

## 7. 실험 전에 필요한 통과 조건

### 연결 smoke test

1. 작은 작업이 완료되고 최종 산출물이 해당 `run_id`에 연결된다.
2. 검증은 worker의 주장 대신 실제 candidate hash에 수행된다.
3. 같은 idempotency key를 다시 보내도 worker가 중복 생성되지 않는다.
4. deadline/cancel 뒤 프로세스가 남는지 확인한다. 원격 취소는 취소 요청과 실제 완료를 구분한다.
5. 인증 실패·rate limit·tool 오류를 코드 실패와 구분한다.
6. usage 누락은 null/unknown이고, provider와 gateway 수치가 이중 청구로 계산되지 않는다.
7. worker가 수정한 검증 설정, stale patch, 충돌한 범위를 거부한다.

### 문맥·라우터 승격 조건

중요 정보가 packet에서 사라지는 사례를 먼저 확인한다. 실패 로그, acceptance, API 경계, 코드 원문을 재조회할 수 있어야 한다. router는 분류 정확도만 높아서는 부족하다. 검증된 작업 성공률, 품질 회귀 종류, 전체 비용, timeout을 E3보다 낫게 만들었는지 본다. 허용 품질 손실과 예산 기준은 실험 시작 전에 정한다.

### 예산 제한의 정직한 표현

실행 후 집계된 usage로는 이미 쓴 돈을 되돌릴 수 없다. 하네스가 매 요청의 상한을 제어하지 못하면 이를 완전한 hard dollar cap이라 부르지 않는다. 요청 전 예산 예약, provider별 최대 출력, 동시 실행 예약, deadline과 취소를 결합하고 최악의 진행 중 노출액을 기록한다. 제어할 수 없는 경로는 ‘soft budget / bounded overshoot unknown’으로 표시한다.

## 8. 구현 backlog: 첫 vertical slice를 완성하는 순서

| 순서 | 구현 단위 | 완료의 증거 |
|---|---|---|
| 1 | Codex adapter + 하나의 task manifest + journal | 시작/완료/실패/usage source가 한 run에 연결 |
| 2 | artifact 저장·범위 읽기 + task/result packet | 큰 결과를 다시 읽을 수 있고 기본 응답은 작음 |
| 3 | 실제 verifier + snapshot/patch 결합 | 후보 변경 시 이전 PASS 증거 재사용 불가 |
| 4 | 같은 runner를 감싸는 MCP 도구 | 현재 Codex에서 한 작업 위임과 결과 회수가 동작 |
| 5 | 저가 worker adapter + RuleRouter | E0~E3 비용·품질 비교 가능 |
| 6 | 로컬 DecisionProvider shadow | 배정을 바꾸지 않고 추천·추가 비용 기록 |
| 7 | 로컬 판단 승격 또는 폐기 | E3 대비 품질·비용 기준 충족 여부 기록 |
| 8 | 독립 task 두 개 + 충돌·통합 검사 | 시간 이익과 총비용을 함께 보고 |

1~4가 하나의 첫 구현 목표다. 범용 agent framework를 만드는 대신 사용자의 Codex에서 한 작은 작업을 맡기고 검증 결과를 받아 보는 데 집중한다. profile·실제 모델·GPU·예산은 연결 전에 정하며, 이번 문서에서는 `unconfigured` 상태를 유지한다.

## 9. 이번 조사에서 수행한 것과 남은 것

수행: 원격 저장소 v0.2와 기존 계약/문맥 설계 검토, GitHub·X 검색, 공식 문서와 논문/제작자 글 확인, 최신 Codex 연결 방식·로컬 판단 모델 현황 반영, 세 문서 작성.

문서 검사: 변경·추가한 Markdown 5개에서 로컬 파일 링크 39개가 존재함을 확인했고, JSON 코드 블록 2개를 파싱했다. 코드 펜스 짝과 UTF-8 대체문자 여부도 검사했다. 외부 링크 33개를 집계했으며, 앞서 명시한 X 직접 열기 실패를 링크 정상 접근으로 간주하지 않았다. 이 검사는 실행 시스템이나 Mermaid 렌더링 검증이 아니다.

미수행: 외부 프로젝트 설치·코드 실행, API/구독 모델 호출, 로컬 GPU 측정, 실제 agent trace 분석, 비용 절감 재현. 문서 안의 JSON 예시는 형식 설명이며 실행 가능한 bridge를 뜻하지 않는다. 기존 v0.2의 28개 합성 검사는 이전 버전의 검증 기록으로 보존한다.

이 단계의 산출물은 **다음 구현에서 무엇을 연결하고 무엇을 측정할지 구체화한 설계 문서**다. 실제 수용률과 절감률은 첫 vertical slice 이후의 결과로 채운다.
