# 결정 기록·비용 측정·구현 순서

v0.3 설계 제안이며 구현 완료 사양이 아니다.

## 1. 설계 결정 기록 (ADR)

각 결정은 **현재 권고**다. 사용자 확정 조건은 세 구독 사용·구독 CLI 우선·API 선택·확장 가능한 전체 틀이며, 나머지 기본값은 이 프로젝트의 설계 판단이다. 근거 ID는 [sources.json](sources.json)에서 원문·locator·버전으로 추적한다.

| ID | 채택하는 결정 | 근거/이유 | 대안과 재검토 조건 |
|---|---|---|---|
| D01 | Native CLI adapter를 구독의 우선 실행 경로로 사용. API/extra credits는 별도 opt-in profile | E01–E10. 실제 인증·과금이 제품마다 다름 | 통합 API gateway 우선은 현재 요구와 불일치. 공식 구독 재사용·기능 동등성이 확인되면 SDK/wrapper로 교체 가능 |
| D02 | task 또는 명확한 phase 단위로 배정. 시작은 deterministic rule + 작업군별 profile | E12/E13/E18/E19/E30. routing 비용과 전환 문맥을 최소화 | 매 turn judge·학습 router는 저가 단독 대비 순이익과 calibration이 확인될 때 |
| D03 | 공통 실행 계약을 정의하되 native event·기능 차이를 보존 | E02/E03/E06/E08/E22/E23. wrapper만으로 resume/권한/usage 동등성이 생기지 않음 | Lite-Harness 등 기존 wrapper가 conformance를 충족하면 직접 adapter 코드를 줄일 수 있음 |
| D04 | 한 작업 한 worker를 기본값으로 하고 분해 가능한 역할만 추가 | E11/E14/E15/E17/E18/E20/E21. 조정 비용과 오류 전파의 조건부 효과 | 독립 task 병렬화가 순차 실행보다 deadline/수용률/전체비용을 개선하면 확장 |
| D05 | 기계 manifest와 모델 packet 분리. 원문 참조·필요 부분 조회·명시 session affinity | E02/E06/E08/E16/E26/E27/E28/E29. 반복 입력과 누계 중복을 줄이고 원문 재검증 가능하게 함 | 요약/선별이 사실 누락·repair를 늘리면 해당 selector 중단; 캐시 이득도 실측 |
| D06 | candidate digest에 묶인 독립 검증과 bounded repair; 작업 상태 소유자는 하나 | E08/E11/E14/E23. 프로세스 종료/자기보고와 작업 성공은 다름 | 항상 LLM reviewer를 추가하지 않음. 위험과 기계검사 공백이 있을 때만 추가 |
| D07 | cash·quota·token·latency·재작업을 별도 기록. unknown은 0이 아님 | E01/E04/E05/E06/E07/E09/E12/E19/E21/E28. 구독 비용과 API 등가 추정은 다름 | 단일 달러 score는 내부 모델일 뿐. 충분한 관측이 생기면 task별 quota 예측 도입 |
| D08 | 단일 native 기준선·저비용 단독·규칙 routing·context 변경을 분리한 paired 평가 | E12/E13/E15/E16/E18/E19/E20/E21/E25/E30/E31. task 혼합/분산/비용 분모가 결과를 바꿈 | 큰 benchmark 숫자만으로 채택하지 않음. hold-out에서 품질·경제성·운영 조건 충족 시 승격 |
| D09 | Jev류는 교체 가능한 DecisionPlugin/ContextSelector. 먼저 shadow | E13/E16/E24/E25/E26. 분류 성능과 최종 작업 효용은 별도 | 규칙 대비 유의미한 이득·local 가용성·실패 복귀 확인 후 일부 저위험 task에 적용 |

## 2. 배정 정책을 구현 가능한 순서로 풀기

1. **사용 가능성 필터:** task 권한·modality·workspace·headless·구독 entitlement·funding mode를 만족하지 않는 후보는 제외한다.
2. **가용성 필터:** account/공유 quota pool의 cooldown·잔여 allowance·concurrency·deadline을 반영한다. 잔량 API가 없으면 관측한 rate-limit과 재개 시각, 마지막 확인 시각을 사용한다. 임의의 잔량을 추정해 사실처럼 표시하지 않는다.
3. **품질 조건:** 같은 작업군에서 수용 조건을 충족한 profile 우선. 데이터가 없는 새 모델은 탐색용 소량 평가로 시작하며 최약 모델이라는 이유만으로 투입하지 않는다.
4. **비용/시간 순서:** 추가 지출이 없는 허용 후보들 중 quota 기회비용·대기·재작업 예측을 비교한다. reset 전 가용 한도를 활용할 수 있지만 한도 우회용 계정 순환과는 구분한다.
5. **한 번 선택 후 유지:** 정상 진행 중에는 같은 session을 유지. 실제 실패나 capability mismatch가 드러날 때 phase 경계에서 재배정한다.
6. **실패 원인별 처리:** rate limit은 queue/cooldown, auth는 blocked, invalid output은 제한된 형식 복구, test failure는 기술적 수리. 모든 오류를 고가 모델 재시도로 바꾸지 않는다.

사용자가 즉시 완료를 원하고 남은 구독 경로로 불가능하면 `BLOCKED`와 가능한 선택을 보여준다. 이미 설정된 선택 API 예산이 있으면 그 범위에서 진행한다. 자동으로 새 유료 경로를 활성화하지 않는다. API를 쓰는 일과 다른 구독의 native worker에 task를 옮기는 일은 서로 다른 정책이다.

실행 기록이 축적되면 `task_kind × model/harness version × effort × context_strategy`별 성공률·비용·지연을 갱신한다. 정답을 아는 평가 결과로 threshold를 조정하고 hold-out 과제에 고정한다. 모델 자체 confidence는 검증된 성공 확률이 아니다. task 분포나 CLI/model 버전이 바뀌면 기존 추정을 그대로 신뢰하지 않는다.

## 3. 회계: 같은 token을 두 번 더하지 않기

각 usage observation에 다음 정보를 기록한다.

```text
run_id / attempt_id / native_session_id / event_id / observed_at
provider / harness_version / model_revision / funding_profile / quota_pool
scope: turn_delta | session_cumulative | run_total
input / output / reasoning / cache_read / cache_write (지원하지 않으면 null)
reported_cost / cost_kind: actual_charge | provider_estimate | api_equivalent
quota_unit / quota_delta / remaining / reset_at / freshness
includes_children: true | false | unknown
raw_event_ref / measurement: observed | estimated | unknown
```

부모 세션 누계 안에 자식 사용량이 포함되면 따로 또 더하지 않는다. 누계 관측은 **동일 provider/session/counter 정의 안에서** 이전 관측과의 차이로 환산한다. counter가 감소하거나 reset되면 0으로 덮지 말고 새 segment로 나눠 원인을 기록한다. 입력·출력·reasoning이 서로 포함 관계일 수 있으므로 `total = sum(all fields)`를 공통 공식으로 쓰지 않는다. 원본 의미를 adapter에 명시한다.

구독 profile의 `total_cost_usd`가 API 등가 estimate라면 실제 청구에 합산하지 않는다. 월 구독료, 추가 credits/API 실지출, 등가 가격 추정은 세 줄로 보고한다. 구독 요금이 그대로여도 낭비 감소는 더 많은 수용 작업·덜 잦은 limit·짧아진 대기로 나타날 수 있다.

총비용 범위에는 parent 계획·worker·router/judge·tool/context 처리·실패/repair·최종 검증·필요한 사람 수정까지 포함한다. MCP bridge 밖의 parent 사용량처럼 볼 수 없는 부분이 있으면 **부분 계측**이라고 표시하고 전체 절감률을 발표하지 않는다.

hard token cap을 제공하지 않는 CLI에는 외부 추정치만으로 정확한 token 상한을 보장하지 않는다. adapter가 실제 강제할 수 있는 timeout·실행 수·허용 tool·동시성은 hard limit, 진행 중 token estimate는 soft budget으로 구분한다. 중단 직전 이미 발생한 사용량이나 최종 이벤트 유실 가능성도 관측 상태에 반영한다.

## 4. 저비용부터 시작하는 것이 손해가 되는 경계

단순화하여 저비용 시도 비용을 `L`, routing/검증/인계 추가비용을 `O`, 저비용 시도가 수용되는 확률을 `p`, 실패 후 강한 모델 비용을 `F`라 하면 기대비용은 `L + O + (1-p)F`다. 강한 모델 직행 비용이 `F0`이면 이 값이 `F0`보다 작은지 본다.

예를 들어 같은 비용 단위에서 `L=2, O=1, F=10, F0=10`이면 `p>0.3`일 때만 비용상 유리하다. 이는 설명용 숫자이며 실제 달러/구독 quota 측정이 아니다. 실패한 patch를 정리하는 비용이나 큰 handoff가 있으면 `F`가 `F0`보다 커질 수 있다. 두 경로의 최종 품질도 함께 충족해야 한다.

구독 비용에는 이 식을 그대로 달러로 적용하지 않는다. 공급자별 quota 사용 벡터·deadline·quality constraint를 놓고 비교하며, 필요하면 명시한 내부 가중치를 사용한다.

## 5. 실험 설계

첫 작업군은 기존 v0.2의 `bounded_patch`. 이후 읽기 조사·구조화 추출·테스트 수정·다중 파일 변경 등으로 확대한다. **제품 간 실용 비교**와 **동일 하네스의 모델 인과 비교**를 구분한다. Codex와 Claude Code가 다르면 모델뿐 아니라 system prompt·tool·cache·내부 agent가 함께 달라진다.

| 실험 | 변경하는 요소 | 답하려는 질문 |
|---|---|---|
| B0 | 현재 사용자가 직접 쓰는 native 기본 경로 | 현재 대비 실제 이득이 있는가 |
| B1 | 각 native 하네스의 강한 profile 단독 | task군의 품질 기준선은 무엇인가 |
| B2 | 각 native 하네스의 경제적인 profile 단독 | routing 없이 이미 충분한가 |
| B3 | B2에 한 번의 조건부 상향/수리 | escalation 비용을 포함해 이득인가 |
| C1 | 모델/하네스 고정, 원문 전체 전달 → 참조/부분 조회 | context 방식 자체가 이득인가 |
| R1 | context 고정, task-level 규칙 routing | 선택 이득이 coordination overhead를 넘는가 |
| J0/J1 | Jev류 shadow 후 제한적 실제 선택 | 기존 규칙보다 나은가, abstain/오배정 비용은 어떤가 |
| P1 | 독립 task에만 bounded 병렬 실행 | 전체 quota·통합 비용 포함 deadline 개선이 있는가 |
| T1 | 선택한 native Teamwork 기능 | 외부 task 분리보다 나은 작업군이 있는가 |

모든 조합을 처음부터 완전 교차 실행하지 않는다. 초기에는 B0/B1/B2로 충분하며 두 번째 CLI와 C1을 순차 추가한다. schema나 summary를 추가해 오히려 token이 증가하는 경우도 실패 결과로 기록한다.

평가 manifest에는 task 목록/분할, repo base, acceptance, profile/version, prompt/context revision, budget, cache warm/cold 상태, 실행 순서, 반복 횟수, artifact/evaluator version을 고정한다. 실행 순서는 섞고 같은 task의 paired 차이를 비교한다. quota 시간대·rate-limit·서비스 장애를 별도 기록한다. 실패한 run을 비용 표에서 빼지 않는다.

첫 20–30개 task는 배선·계측·실패 유형을 확인하는 pilot 규모의 제안이지 통계적으로 충분하다는 주장이 아니다. 대표 작업군을 포함하고 일부를 반복하여 변동을 본다. 이후 요구 품질 차이와 관측 분산으로 평가 규모를 정하고 held-out 결과·paired confidence interval을 보고한다. 성공률뿐 아니라 **기준선만 해결한 과제와 새 경로만 해결한 과제**도 비교한다. 프롬프트와 router를 test set에 맞춰 반복 조정하지 않는다.

## 6. 승격 조건

- **기능:** 실제 candidate·test evidence 연결, 명시 session 재개, 취소/장애 복구, auth/funding 식별이 conformance를 통과한다.
- **품질:** 작업군별로 사전에 정한 최소 수용률과 허용 회귀 폭을 충족한다. 기능 보존이 핵심인 patch는 회귀를 개별 검토하며 미해결 회귀를 비용 평균으로 숨기지 않는다.
- **경제성:** B0뿐 아니라 적절한 B2와도 비교한다. 전체 비용·quota·p95 지연·repair를 포함해 선택한 목표가 개선된다.
- **관측:** 부모 또는 내부 subagent 비용 누락이 남으면 그 범위의 제한된 결론만 낸다. unknown 비율도 결과에 표시한다.
- **운영:** 계정별 policy 변경·quota exhaustion·CLI update 때 명시적으로 멈추거나 fallback할 수 있다. API fallback은 설정한 funding 범위 안에서만 가능하다.

임계값은 아직 사용자 workload 데이터가 없어 확정하지 않았다. pilot 전에 task군별 acceptance와 함께 기록해야 하며 결과를 본 후 유리하게 바꾸지 않는다.

## 7. 첫 구현 백로그와 완료 증거

| 순서 | 구현 단위 | 완료를 입증할 artifact |
|---|---|---|
| I01 | 실제 세 CLI inventory·capability/funding profile. 비밀 값 없이 version·auth mode만 확인 | version/help snapshot, policy/source IDs, configured 여부 |
| I02 | Codex 등 이미 설치/로그인된 **하나**의 adapter, 단일 task/worker | 실제 task manifest, normalized events, raw refs, candidate digest |
| I03 | 실제 verifier + usage ledger + 수리 1회/중단 처리 | 명령/exit/log와 candidate 연결, 누계 중복 방지, timeout/cancel 기록 |
| I04 | 작은 MCP bridge로 현재 Codex 세션과 연결 | run/get/read/cancel 왕복, 짧은 응답, 부모 사용량 관측 한계 표시 |
| I05 | Claude Code·Antigravity를 같은 계약에 차례로 연결 | 동일 task군 B0/B1/B2, auth/funding·resume conformance 결과 |
| I06 | context builder·규칙 router·queue/cooldown | C1/R1 결과, 낭비/실패 분석, 원문 복원·cache invalidation 기록 |
| I07 | 필요한 경우 durable metadata·병렬 ownership | restart reconciliation, 중복 실행/충돌/통합 후 검증 기록 |
| I08 | Jev류 local 가용성 확인과 shadow | 설치 가능한 artifact/license/hardware, 한국어+code 평가, J0 비교 |

기존 v0.2의 task/검증 계약을 실제 adapter에 붙이면서 필요한 확장만 별도 schema 변경으로 제안한다. 이번 v0.3 문서 PR에는 실행 가능한 것처럼 보이는 빈 orchestrator나 가짜 모델 결과를 추가하지 않는다.
