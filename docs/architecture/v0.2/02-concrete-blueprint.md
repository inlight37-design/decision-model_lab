# 02. v0.2 구체 설계 — 기존 실행기 위의 얇은 정책·검증 계층

> **현재 권고 v0.2 / 2026-09-21.** 아래는 설계다. 이 저장소에 Symphony·Switchyard·mini-swe-agent가 설치되거나 연결된 것은 아니다.
>
> v0.1의 책임 경계는 유지한다. 다만 ‘자체 제어부와 영속 DB를 먼저 구현한다’는 초기 순서를 바꾼다. 근거는 [사례 연구](01-case-studies.md), 시험 순서는 [평가·백로그](03-experiments-and-backlog.md).

## 1. 무엇을 바꾸었는가

| v0.1의 방향 | v0.2의 구체 결정 | 근거 |
|---|---|---|
| 여러 구성 요소의 가능성을 열어 둠 | 실용 실행과 경제성 실험을 두 경로로 분리 | Symphony E09–10, mini E11 |
| 코드 제어부·SQLite부터 구축 | 기존 scheduler 적합성 시험 우선; 단일 실험은 task manifest와 run journal로 출발 | E09의 DB 비필수 복구 |
| Jev task routing이 중심 실험 | Jev는 shadow 분류 또는 read-only 코드 후보 점수화; 실행 중 상시 judge는 기본 제외 | E03, E08 |
| 프론티어 대비 개선 평가 | 저가 단독·기존 router 대비 추가 이익도 필수 | E02–04 |
| 일반적인 ContextBuilder | 원문을 보존한 도구 응답 선별 + expand 경로부터 | E05–06 |
| 다수 worker와 verifier의 일반 구조 | `bounded_patch` 하나, 실행 worker 1, 수리 최대 1, 자동 merge 없음 | E12, E15–16 |
| 모든 프로젝트 상태를 새 원장에 보관 | task 상태 소유자 하나, 실행/비용/증거 기록은 별도 자료 | E09–10 |
| 통합을 위한 검토 계층 | 독립 검증은 필수, 상시 AI 통합 관리자와 agent 회의는 제외 | E15 |

이 선택은 Jev나 다중 에이전트를 포기하는 것이 아니다. 먼저 효과를 분리해 측정하고, 더 작은 시스템으로 동일한 성과를 낼 수 있는지 검증하는 순서다.

## 2. 두 경로와 공유 경계

```text
                    승인된 TaskEnvelope
                 목표 / 범위 / 기준 snapshot
                           │
              ┌────────────┴─────────────┐
              │                          │
       실용 실행 경로                 경제성 실험 경로
   기존 coding CLI / app-server      mini-swe-agent 계열 고정 하네스
   scheduler: Symphony 적합성 시험   runner: 단일 task manifest
   모델 내부는 native 기능 유지      모델·read 출력·router만 변경
              │                          │
              └────────────┬─────────────┘
                           │
             공통 RunManifest / Candidate / Usage
                           │
                 독립 VerificationBundle
                           │
              REVIEW_READY + 사람에게 인계
```

**경로 A: 실용 실행.** 실제 사용하는 하네스의 기능을 유지한다. 모델/추론/도구 loop 전체를 새로 만들지 않는다. 먼저 한 개 native adapter의 실행·중지·결과 수집과 workspace 경계를 검증한다. Symphony는 서비스 설계와 재사용 후보이고, 곧바로 fork·전체 도입 확정은 아니다.

**경로 B: 경제성 실험.** 같은 하네스·환경·수용 기준에서 고가/저가/규칙/router/context 방법만 바꾼다. 작은 공개 하네스는 실험에 적합한 코드 경계를 제공한다. 여기서의 API 비용 결과를 구독형 앱의 quota 절감으로 자동 환산하지 않는다.

두 경로의 결과를 같은 보고서 형식으로 수집하되, 서로 다른 하네스의 결과는 ‘모델만의 차이’가 아니라 전체 구성 차이로 표시한다. 처음부터 두 경로를 동시에 완성하지 않는다. **오프라인 계약 → 실험 경로의 한 task → native adapter 적합성 시험** 순서를 기본 제안으로 둔다.

## 3. 우리가 직접 소유할 범위

| 직접 정의할 것 | 기존 도구에서 재사용/비교할 것 | 초기 범위 밖 |
|---|---|---|
| 작업·증거·권한 계약 | Symphony의 조회·세션·재시도 구조 | 자체 범용 분산 scheduler |
| 고정 작업 절차와 중단 조건 | native CLI 또는 mini agent loop | 새 코딩 IDE·채팅 UI |
| 원문 참조·검증 결과 결합 | Switchyard/LiteLLM router | 모든 공급자의 프로토콜 재구현 |
| 비용·성패 대조 실험 | SWE-Pruner/JevGrep의 선택 패턴 | 처음부터 판단 모델 학습 |
| 허용 범위와 사용자 인계 정책 | upstream의 관측·환경 도구 | 무인 배포·자동 main merge |

Attractor의 DOT DSL을 이번 저장소의 필수 의존성으로 추가하지 않는다. 그래프 개념과 체크포인트/handler 경계만 가져오고 고정 절차부터 만든다.

## 4. 첫 실행 단위: `bounded_patch`

### 입력 계약

| 입력 | 생성/승인 주체 | 이유 |
|---|---|---|
| task ID, 명확한 목표, 하지 않을 일 | 사용자 또는 승인된 계획 | 작업 범위 통제 |
| repository snapshot / base commit | host resolver | 기준 코드 고정 |
| write scope, network/profile | 사용자 정책·host | 모델 답변이 권한을 확대하지 못함 |
| acceptance manifest 및 hash | 신뢰된 verifier 설정 | worker의 자기 채점 방지 |
| model/harness/policy revision | 실행 설정 | 재현과 비용 귀속 |
| attempt/step/time 상한, 측정 방식 | 운영 설정 | 무한 반복·알 수 없는 비용 관리 |

‘유효한 JSON’은 출발 조건일 뿐이다. 실제 commit·경로·권한·도구 지원 여부는 실행기가 확인한다. 이번 오프라인 검사기는 존재하지 않는 파일이나 실행 중 프로세스를 검사하지 않는다.

### 고정된 절차

| 단계 | 담당 | 출력 | 다음 단계 조건 |
|---|---|---|---|
| 0. Admit | 코드 | 승인된 RunManifest | snapshot·정책·필수 capability 확인 |
| 1. Preflight | 코드/격리 검사 | 환경 및 baseline 결과 | 기존 테스트가 정상; 아니면 환경 조사로 분리 |
| 2. Context | 검색·선별 코드, 선택적 의미 모델 | 원문 참조가 있는 context manifest | 누락·민감도·크기 검사 |
| 3. Implement | worker 1 | patch 후보와 제한 사항 | 실행 종료는 성공 판정 아님 |
| 4. Verify | 독립 verifier | hash가 결합된 검증 결과 | 허용 범위·수용 테스트·회귀 검사 모두 통과 |
| 5. Repair | 동일 또는 승인된 상향 worker | 새 patch 후보 | 검증된 실패 근거, 예산, 최대 한 번 |
| 6. Package | 코드 | ProofBundle + 비용/미확인 항목 | 최종 후보를 다시 검증 |
| 7. Handoff | 코드→사용자 | `REVIEW_READY` 또는 `BLOCKED` | 자동 merge·배포하지 않음 |

Repair 다음은 반드시 Verify다. 수정된 후보에 이전 테스트 결과를 붙여 인계하지 않는다. `PARTIAL_SUCCESS`라는 일반 실행기 상태도 수용 테스트의 PASS로 대체하지 못한다.

baseline이 이미 실패한 경우 이 pilot은 먼저 멈춘다. 더 큰 프로젝트에서 기존 실패를 허용해야 한다면 승인된 known-failure manifest를 따로 설계한다. 여러 worker에게 기존 고장 전체를 자율 수리하도록 시키지 않는다.

### 상태와 반복 제한

```text
READY -> PREFLIGHT -> RUNNING -> VERIFYING -> REVIEW_READY
                        ↑          │
                        └─ REPAIR ─┘   (추가 시도 1회까지만)

어느 단계든 -> BLOCKED / CANCELLED / OUTCOME_UNKNOWN
```

총 시도 2는 정책 예시이며 최적값이나 사용자 확정 예산이 아니다. native 하네스가 실제 step/time/cancel 제한을 강제할 수 있는지 검증해야 한다. 지원 여부가 불명확하면 무인 경로를 시작하지 않는다.

## 5. 프로젝트 상태와 실행 기록을 나눈다

**한 task의 권위 있는 상태는 한 곳에만 둔다.** 초기 오프라인/단일 실험에서는 버전 있는 task manifest, 서비스형 운영에서는 선택한 tracker다. tracker·Beads·SQLite·LangGraph가 같은 task를 각각 READY/DONE으로 결정하는 구조를 만들지 않는다.

별도 run journal에는 다음을 남긴다.

```text
run_id / task_id / attempt_id
base commit / policy hash / context hash
provider run ID / 실제 사용량 또는 unknown
candidate hash / verifier hash / handoff 상태
중지 요청 / 실제 중지 확인 / outcome unknown
```

재시작 시 tracker와 workspace로 작업을 다시 판단할 수 있어도, 유료 호출의 결과·비용이 자동 복원되는 것은 아니다. 미확인 호출은 journal에서 조정한다. 재시도를 하면 외부 동작이 중복될 수 있는 상태는 `OUTCOME_UNKNOWN`으로 멈춘다.

단일 실험 journal은 한 writer가 관리하는 JSONL/원자적 파일로 시작할 수 있다. 동시 배정·예산 예약이 실제로 필요해지면 SQLite 트랜잭션으로 확장한다. DB를 없애자는 결정이 아니라, DB가 해결할 문제가 생기기 전에 일반 플랫폼을 만들지 말자는 결정이다.

## 6. 모델 선택 정책: 권한 → 역량 → 경제성

모델 선택을 단순히 ‘싸다/비싸다’ 한 축으로 다루지 않는다.

1. **권한 및 실행 가능성:** 데이터 외부 전송, 도구/문맥 지원, 계정·비용 관측 조건.
2. **필요 역량:** 국소 수정인지, 여러 모듈 설계인지, 시각 입력이나 특수 도구가 필요한지.
3. **경제성:** 해당 작업군에서 관측된 성공·재시도·비용 이력.

고위험 작업을 비싼 모델에 보냈다는 이유로 승인 완료로 보지 않는다. high/unknown risk는 필요한 승인·명세 보완 경로로 간다.

### 초기 정책

- B0/B1은 각각 고정 고가/저가 모델이다. router가 없다.
- 규칙 router는 task 시작과 독립 검증 실패 등 명시된 사건에서만 평가한다.
- Jev는 처음에는 추천만 기록하는 shadow다. 실행 경로를 바꾸지 않는다.
- 실제 상향을 시험할 때는 한 task에서 최대 한 번, 상향 후 같은 세션 범위에서 유지한다. 이 방식의 이득은 실험 대상이다.
- 외부 task router와 gateway의 router가 동시에 모델을 바꾸지 않게 소유자를 하나로 정한다.
- 새로운 도메인·모호한 입력·판단 실패는 `hold`다. 무조건 가장 싼 모델로 fallback하지 않는다.

Switchyard의 매 턴 judge 방식을 그대로 기본값으로 채택하지 않는다. 문서화된 기존 정책을 대조군으로 측정한 뒤, event-triggered 정책이 같은 품질로 judge 비용을 줄이는지 비교한다.

## 7. 문맥 선택을 구체화한다

### 도구 계약의 제안

```text
search_exact(query, scope) -> source references
search_semantic(question, authorized_scope) -> ranked references + coverage
read(ref, line_range) -> original text + original hash
focus(ref, question) -> selected original lines + omissions + raw_ref
expand(raw_ref, range) -> uncompressed original text
```

위 이름은 이 저장소의 내부 계약 제안이다. 특정 하네스가 그대로 이 함수를 지원한다는 뜻이 아니다.

`search_semantic`은 정확한 식별자를 모를 때만 후보로 둔다. `focus`는 읽기 관측에만 적용한다. 명령의 성공/실패, 보안 정책, 사용자 요구, 독립 검증의 기준을 의미 모델이 삭제하게 하지 않는다.

### 문맥 선별의 수용 조건

- 원본은 변하지 않고, 반환 행의 위치와 hash가 검증 가능하다.
- 부분 검색/부분 응답이면 coverage와 누락 가능성이 표시된다.
- 모델이 더 읽어야 할 때 expand를 사용할 수 있다.
- 문맥 감소뿐 아니라 정답에 필요한 위치를 찾았는지와 다시 읽은 비용을 잰다.
- 전송 권한이 없는 저장소는 원격 Jev 검색을 실행하지 않는다.
- 모델을 호출하는 선별기의 지연·청구·GPU 비용도 총비용에 포함한다.

### 캐시와 도구 목록의 수정

v0.1의 ‘필요한 도구만 노출’은 유지하되, 실행 중 매 턴 tool schema를 바꾸라는 뜻으로 해석하지 않는다. 최초 run에서 도구 집합과 안정 prefix를 고정한다. 동적 추가가 필요하면 하네스가 지원하는 lazy tool 경로와 cache miss를 관측한다. 축약을 위해 cache와 이미 형성된 세션 의미를 깨뜨리지 않는다. Cursor가 전환 비용을 실측에 포함한 점을 참고한다. [E01]

## 8. 검증 증거의 구체 계약

`ProofBundle`은 worker가 작성한 자신감 문장이 아니다.

```text
candidate_sha256 + base_commit + policy_sha256
acceptance_sha256 + trusted verifier identity
실제 실행한 check IDs / 각각의 status
원본 로그 artifact hashes
baseline 결과 / 변경 범위 검사 결과
측정된 비용, 추정 비용, unknown의 구분
미해결 문제와 사람 검토가 필요한 이유
```

host가 기대하는 candidate/policy/acceptance hash와 verifier 결과를 맞춘다. worker가 바꾼 정책이나 이전 후보에서 나온 PASS는 사용할 수 없다. verifier ID 문자열을 썼다는 사실만으로 인증이 되는 것은 아니므로 실제 실행에서는 host가 verifier 프로세스와 산출물 경로를 통제한다.

최종 `REVIEW_READY`에도 사용자 승인이 남아 있다. main에 merge할 때에는 그 시점의 head에서 필요한 검증을 다시 한다. 변경 통합이 필요해지더라도 새 ‘관리자 AI’를 항상 호출하지 않고, 충돌·실패가 실제로 있을 때만 진단한다.

## 9. 실제로 읽은 코드/명세의 재사용 지도

| 소스와 경계 | 확인한 구체 지점 | 도입 판단 |
|---|---|---|
| Symphony `SPEC.md` | loader / config / tracker / orchestrator / workspace / runner | controller 명세를 새로 발명하기 전 적합성 시험 |
| Symphony `agent_runner.ex` | `run_on_worker_host`, `run_codex_turns`, `continue_with_issue?`, `build_turn_prompt` | 같은 세션 유지, 상태 재확인, 정리 구조 참고 |
| mini `agents/default.py` | `query`, `execute_actions`, `serialize`, `save` | router/observation 실험과 trajectory 수집 경계 |
| Switchyard README Path 2 | `run_stream`, `Step.CallModel`, `Step.Done`, host의 최종 호출 | 직접 gateway 전체를 만들지 않는 library 경계 |
| SWE-Pruner integration README | optional `context_focus_question`, 없으면 full output | read-only 선택기와 안전한 fallback |
| JevGrep README | 정확 원문/행, per-question/per-fragment score cache, coverage | 검색 실험·외부 전송 승인·부분 결과 표시 |
| Attractor spec §§1–2.6 | handler, checkpoint, human gate, retry semantics | 고정 절차의 설계 참고; full DSL은 보류 |

이 표는 해당 코드 전체를 실행·보안 감사했다는 뜻이 아니다. 특히 mini의 비용 한도는 사용 후 검사이므로 사전 예약식 hard cap과 다르다. Switchyard README 예제는 배포된 package보다 최신일 수 있다고 원문이 경고한다. 설치 전에 실제 commit과 의존성 lock을 고정해야 한다.

## 10. 첫 실제 실행에서 제외할 것

무인 PR merge, 배포·결제·삭제, 다른 계정에 메시지 보내기, repository가 수정한 hook 자동 신뢰, 외부 코드 다운로드 후 무조건 실행, native 구독 세션 우회, 무제한 병렬 하위 agent, 온라인 자동 학습을 제외한다.

workspace는 격리된 branch를 뜻할 뿐 보안 sandbox는 아니다. host 파일·비밀·Docker socket에 접근하지 않는 별도 실행 환경과 최소 권한은 실제 adapter 검증의 조건이다.

## 11. 실제 파일과 아직 계획인 파일

이번 v0.2에서 실제 추가하는 것은 문서, 합성 pilot 설정, 검증 증거 fixture, 오프라인 설계 검사기다. 이들은 모델·도구를 실행하지 않는다.

향후 구현할 최소 모듈은 아래처럼 역할을 나눌 수 있다. **아래 목록은 아직 존재하는 런타임이 아니다.**

```text
runner        : 한 task 실행 / 취소 / 결과 수집
policy        : 권한·역량·선택 사건 / 예산 표시
context       : 원문 참조 / 선택 / 확장
verifier      : 독립 실행 / hash 결합 / scope 검사
report        : paired 결과 / 모든 호출 비용 / 미확인 항목
```

새 scheduler·DB·proxy를 이 다섯 이름 옆에 자동으로 추가하지 않는다. 기존 도구로 처리할 수 없는 검증된 결함이 있을 때만 구현 범위를 넓힌다.
