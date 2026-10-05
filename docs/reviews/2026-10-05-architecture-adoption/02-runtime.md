# 실행 코어·호출 수명·예산 경계 심층 검토

검토 기준은 `48ab4bd6f0e297587707aecb83ebc0cd9968892f`이며, 아래 GitHub 링크는 모두 이 커밋에 고정했다. 2026-10-05 웹 컨테이너에서 소스를 읽고 합성 실행기로 확인했다. 사용자 PC, 실제 로그인, native 모델 응답은 새로 관측하지 않았다. 제품 코드·계정 설정 변경과 실제 모델 호출은 없었다.

## 1. 판단

**현재의 작은 실행 코어를 유지하고, 외부 기능은 이 코어가 이미 갖춘 계획·예약·수용·종료 계약에 연결하는 편이 낫다.** SQLite 원장과 in-process worker를 외부 오케스트레이터로 통째로 바꿀 근거는 이번 검토에서 나오지 않았다. 반대로 자동 후속 작업·더 많은 역할을 붙이기 전에, 원장 경계를 넘어가는 미확인 종료, 직접 통합 시 예산 불변성, 역할별로 다른 완료 기록을 정리할 근거는 확인했다.

현재 방어를 없는 것으로 취급하면 개선 순서가 틀어진다. 이 기준에는 다음이 이미 있다.

| 유지할 설계 | 현재 구현과 의미 |
|---|---|
| 한 원장 소유자·원자적 예약 | `Store._lock`/`Store.__init__`가 같은 원장을 동시에 여는 두 Store를 막는다. `_Tx`는 `BEGIN IMMEDIATE`와 상태·사건의 동시 commit을 제공한다. [`store.py:152–193`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/store.py#L152-L193), [`store.py:387–426`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/store.py#L387-L426) |
| 실제 호출의 공통 예약 | **정상 공식 배선에서** `InvocationLedger.reserve`가 모든 모델 역할의 `live_call_reserved`를 쓰는 단일 위치다. 예약을 기록한 뒤 worker를 시작하고, 취소·실패·재시작으로 환불하지 않는다. 전체·provider별 상한도 함께 본다. 직접 embedding의 경계는 RT-01에서 별도로 확인했다. [`invocations.py:34–46`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/invocations.py#L34-L46), [`coordinator.py:71–99`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L71-L99) |
| 마지막 한 칸의 경쟁·늦은 답 방어 | 참여자 전이는 이전 상태와 시도 ID를 모두 조건으로 삼는다. 오래된 worker가 돌아와도 새 상태의 답을 덮지 않는다. [`repository.py:35–53`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/repository.py#L35-L53), [`coordinator.py:165–189`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L165-L189) |
| 보수적인 결과 수용 | `acceptance`는 전체 자손 종료, adapter 결과, 완전한 stdin 전달, 빈 답, 보고 모델 불일치를 따로 본다. `unit_confirmed_empty`만으로 통과하지 않는다. [`domain.py:75–97`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/domain.py#L75-L97), [`runner.py:103–110`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/core/runner.py#L103-L110) |
| 실행 계획과 관측의 결속 | `CliExecutor.plan`이 만든 계획을 기록하고 그대로 실행한다. `run`에서 기록의 적격성·등록·개인 지시문을 다시 확인한다. 설치 버전·관측 기간·명세 판·구독 로그인도 허가 조건이다. [`cli_executor.py:108–127`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/cli_executor.py#L108-L127), [`cli_executor.py:129–197`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/cli_executor.py#L129-L197), [`eligibility.py:92–146`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/core/eligibility.py#L92-L146) |
| 재시작 시 자동 재호출 금지 | 남은 `running`을 `unknown`으로 바꾸고 대기를 자동 실행하지 않는다. 합성도 시작·완료·종료 확인 사건의 투영으로 미확인 점유를 보존한다. [`coordinator.py:328–348`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L328-L348), [`controller.py:72–77`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/controller.py#L72-L77), [`state.py:128–156`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/state.py#L128-L156) |

`core.membership`는 순수 명단 정책이며, 실제 앱의 공개 여부는 `app.state.gate`가 참여자 행과 수동 답의 독립성 등급으로 정한다. 서로 다른 두 기능을 하나의 상태 엔진으로 무조건 합칠 필요는 없다. 현재 앱이 membership 판정만 믿고 공개한다는 지적도 맞지 않는다. [`membership.py:1–15`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/core/membership.py#L1-L15), [`state.py:1–7`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/state.py#L1-L7), [`coordinator.py:192–216`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L192-L216)

## 2. 개선 우선순위

우선순위는 현재 장애의 심각도와 같지 않다. P1은 자동화·직접 embedding 확장 전의 경계 보완, P2는 현 기능의 일관성·운영 편의, P3는 측정 뒤 판단할 확장 비용이다.

| ID | 우선순위 | 판정 | 개선점 |
|---|---|---|---|
| RT-01 | P1 | 합성 재현 | 공식 입구 밖에서도 실제 호출 예산을 불변으로 지키게 한다. |
| RT-02 | P1 | 코드 확인·호스트 실측 미확인 | 새 원장으로 바뀔 때 이전 미확인 종료를 놓치지 않는다. |
| RT-03 | P2 | 코드 확인 | 상위 역할의 Claude 계정 한도 관측도 보존·표시한다. |
| RT-04 | P2 | 합성 입력 재현 | Codex 출력의 완료 사건 순서를 검사한다. |
| RT-05 | P2 | 구조 개선 | 합성·SEATS의 공통 수명 계약을 맞추되 저장소를 한 번에 바꾸지 않는다. |
| RT-06 | P2 | 기능 확장 제안 | 역할별 호출을 개별 취소하는 동일한 관문을 둔다. |
| RT-07 | P3 | 성능 가설·미측정 | 계획 준비와 이력 조회의 lock 점유를 측정한 뒤 줄인다. |

### RT-01. 실제 호출 예산의 마지막 방어가 호출자의 배선에 의존한다

**확인한 사실.** 정상 서버·헤드리스 입구의 `wiring.live_setup`과 `new_controller`는 제한된 provider 설정을 만들고 cap을 넘긴다. `Store.bind_call_budget`는 기존 원장의 상한 변경을 거절하며, cap을 지정하지 않고 재개하면 저장된 상한을 상속한다. 이 방어는 존재한다. [`wiring.py:51–89`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/wiring.py#L51-L89), [`store.py:317–360`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/store.py#L317-L360)

그러나 `Controller.__init__`는 `max_real_calls=None`을 허용하고, 호환 API의 setter가 저장 원장과 재결합하지 않고 `runtime.max_real_calls`·`provider_call_caps`를 바꾼다. 예약 writer는 runtime cap이 `None`이면 그냥 반환하며, 호출 측도 `plan.kind == REAL and max_real_calls is not None`일 때만 예약한다. [`controller.py:53–58`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/controller.py#L53-L58), [`controller.py:256–270`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/controller.py#L256-L270), [`invocations.py:34–46`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/invocations.py#L34-L46)

**이번 재현.** 네트워크와 프로세스를 쓰지 않는 기존 `SyntheticExecutor`의 계획 종류만 `REAL`로 표시해 두 경계를 시험했다.

- 빈 신규 원장에서 cap 없이 직접 Controller를 만들면 합성 실행은 두 번 수행됐으나 예약 사건은 없고 조회 예산은 `used=0, cap=None`이었다.
- cap을 1로 고정한 뒤 첫 실행을 끝내고 `ctl.max_real_calls = 3`을 쓰면 두 번째 실행이 허용됐다. 저장 cap은 1인 채 runtime cap은 3, 예약은 2가 됐다.

현재 HTTP 요청이 이 setter에 닿는다는 결과가 아니다. 외부 SDK·자동 실행 기능을 Controller에 직접 붙일 때 현재의 안전한 배선을 생략할 수 있다는 **통합 계약의 구멍**이다.

**최소 개선.** 실호출용 예산을 Store에 결합된 불변 값으로 취급한다. 공통 예약 진입점에는 최종 계획 종류를 넘겨 `REAL`인데 cap이 없거나 원장과 다르면 시작 전에 거절하게 한다. 테스트에서 필요한 동적 executor·병렬도 변경과 실제 예산 변경을 구분한다. 일일 예산·토큰 예상량·새 회계 엔진을 동시에 추가할 이유는 없다.

**완료 조건.** 기존 정상 입구가 계속 동작하고, 직접 생성·setter·provider cap dict 변이를 통한 확대가 실행 전에 거절된다. 기존 원장 예약과 고정 cap은 그대로이고, cap 없는 mock/synthetic 테스트는 계속 가능해야 한다.

### RT-02. 종료 미확인의 점유는 현재 원장 안에서만 이어진다

**확인한 사실.** `InvocationLedger._unknown_slots`는 현재 Store의 참여자·SEATS·합성 시도를 센다. `shutdown`의 성공은 worker가 반환했다는 뜻이며 자손 종료 증명이 아니라는 계약도 분명하다. [`invocations.py:130–140`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/invocations.py#L130-L140), [`coordinator.py:519–552`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L519-L552)

launcher의 `_has_room`은 provider별 예약 여유만 검사하며, 최신 원장의 어느 provider라도 cap이 소진되면 `pick_ledger`는 새 폴더를 선택한다. 이전 원장의 `running`/`unknown`이나 미완료 합성은 이 선택 조건에 없다. 서버는 선택한 한 원장만 연다. [`launch.py:190–224`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/launch.py#L190-L224), [`launch.py:315–345`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/launch.py#L315-L345)

**해석.** 소진된 원장에 종료 미확인이 남았다면 다음 원장에서 그 점유가 보이지 않는다. 예전 파일을 삭제하는 동작은 아니며, 원장당 호출 cap 자체를 위반하는 것도 아니다. launcher의 소유 잠금도 있으므로 단순히 서버 두 개가 동시에 뜬다고 주장해서는 안 된다. 이번 세션에서 실제 고아 프로세스가 살아 있었다는 관측은 없다. 문제는 **원장 교체가 종료 미확인에 대한 판단까지 초기화하는 효과**다.

**최소 개선.** 호출 cap의 새 구간과 작업·복구의 수명을 구분한다. 새 원장을 고를 때는 최소한 이전 원장의 미확인 실행 목록을 먼저 조회하고 그 원장을 다시 열거나 복구 화면으로 안내한다. 더 큰 변경에서는 호스트의 실행 소유 정보와 종료 증거를 작은 공통 색인으로 유지할 수 있다. 이 색인은 prompt·초안·인증 자료를 복제할 필요가 없다.

**완료 조건.** 참여자·SEATS·합성 각각에 대해 cap 소진+미확인 종료 조합을 만든 뒤 앱을 다시 열어도 새 호출이 무조건 허용되지 않는다. 사용자가 종료를 확인했을 때만 점유가 풀리고, 이전 예산은 환불하지 않는다. task/memory 연속성까지 포함한 제품 영향은 이 검토의 워크플로우 분석과 함께 판단한다.

### RT-03. 상위 역할이 받은 Claude 계정 한도 정보가 저장 단계에서 빠진다

**확인한 사실.** `Outcome`에는 허용 필드로 정리한 `rate_limit`이 있고, 참여자 `_finish`와 합성 `_synthesis_attempt`는 이를 기록한다. 반면 `_settle_seat`의 공통 observation에는 `usage`까지만 들어가고 `rate_limit`은 없다. [`adapters.py:297–311`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/core/adapters.py#L297-L311), [`coordinator.py:144–152`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L144-L152), [`coordinator.py:375–384`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L375-L384), [`coordinator.py:466–495`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L466-L495)

`PublicQueries.claude_account_limit`도 초안·참여자 실패·합성 사건만 읽는다. 따라서 다듬기·다음 단계 제안·분담·취합·교차검토·수정·재검토에서 최신 한도 사건이 오더라도 이 경로에서는 활용하지 않는다. 이전 초안/합성 값이 남거나 미확인으로 보일 수 있다. [`seats.py:38–82`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/seats.py#L38-L82), [`public.py:328–353`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L328-L353)

**최소 개선.** 역할마다 계정 조회 API를 따로 늘리지 말고 공통 완료 observation에 정규화된 한도 관측을 보존한다. 공개 가능한 REAL 시도의 가장 최근 관측을 같은 규칙으로 선택한다. `core.quota`의 허용 필드·fresh/stale·계정 비율과 원장 cap의 구분은 유지한다.

**완료 조건.** 상위 역할의 합성 fixture가 새 비율을 내면 표시가 갱신되고, 봉인 중인 참여자·mock/synthetic·잘못된 관측은 현재처럼 계정 값이 되지 않는다. 표시를 위해 모델을 추가 호출하지 않는다. 원시 계정 식별자·결제 필드는 저장하지 않는다.

### RT-04. Codex parser는 완료 사건 이후의 답도 같은 완료로 받아들인다

**확인한 사실.** Claude parser는 terminal result가 나온 뒤의 사건을 거절한다. Codex parser는 스트림 전체에서 `completed`를 한 번 True로 바꾸고, 이후 `agent_message`가 나올 때마다 답을 바꾼다. 마지막 답 뒤에 대응하는 완료 사건이 있는지, 완료 뒤 새 turn이 이어졌는지는 검사하지 않는다. [`adapters.py:374–404`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/core/adapters.py#L374-L404), [`adapters.py:459–503`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/core/adapters.py#L459-L503)

**이번 재현.** `agent_message A → turn.completed → agent_message B`를 synthetic `RunResult`로 주면 `Outcome.ok=True`, 반환 답 B, controller acceptance `accepted`가 된다. B 뒤에 완료 사건은 없다. 실제 고정 버전의 native CLI가 정상 실행 중 이런 스트림을 낸다는 관측은 없으므로 현재 사용자 실행에서 발생한 장애로 쓰지 않는다.

**최소 개선.** 관측한 native event 순서에 맞는 작은 상태 검사로 마지막으로 수용하는 답과 그 turn의 terminal을 결속한다. 무조건 JSON Schema로 바꾸거나 정상 extension event를 모두 금지할 필요는 없다. 한 번의 exec가 허용하는 start/answer/terminal 순서와 diagnostic event의 위치를 fixture로 명시하고, 버전 변경 시 해당 fixture와 실제 재관측을 함께 갱신한다.

**완료 조건.** 정상 관측 fixture는 그대로 통과하고, 완료 뒤 후속 미완료 답·중복 terminal·뒤늦은 실패·잘린 stdout·정책 거절 stderr는 의도한 결과로 정해진다. 실패를 텍스트가 있다는 이유로 성공으로 바꾸지 않으며 자동 재시도도 하지 않는다.

### RT-05. 합성의 저장 방식은 유지하되 수명 계약의 차이를 줄인다

**확인한 사실.** 참여자는 조건부 행 전이, 상위 역할은 `SEATS`의 공통 시작/완료, 합성은 별도 event 투영으로 관리된다. 예약·전체 병렬 상한·unknown 점유는 이미 합산된다. 그래서 합성이 회계 바깥에 있다는 지적은 틀리다. 다만 합성은 `SEATS`의 상위 역할 단일 실행 관문과 다른 조건을 쓰고, 형식 실패·결과 저장 실패·재시작 처리가 별도 경로에 있다. [`invocations.py:96–120`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/invocations.py#L96-L120), [`invocations.py:154–173`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/invocations.py#L154-L173), [`synthesis.py:50–102`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/synthesis.py#L50-L102), [`coordinator.py:351–407`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L351-L407)

**개선 이유.** GR 후속·새 역할을 더할 때마다 회계, 종료 미확인, 계정 한도, 관측 필드, 개별 취소의 적용 여부를 여러 실행 경로에서 다시 확인해야 한다. RT-03은 그 차이가 실제 기능 누락으로 이어진 사례다.

**최소 개선.** 먼저 하나의 공통 수명 계약과 역할별 정책표를 두고 기존 저장소를 adapter로 감싼다. `Invocation`은 이미 읽기 adapter이므로 이를 활용하되, 과거 event를 새 테이블로 통째로 이전하지 않는다. 실행 종류·attempt·예약·종료 증거·수용 결과·공개 여부의 공통 의미를 먼저 통일한다. 합성을 상위 역할의 전역 단일 실행 제약에 넣을지는 별도 제품 정책으로 명시한다. 현재의 차이 자체를 예산 안전 결함으로 단정하지 않는다.

**완료 조건.** 모든 역할에 대해 시작 전 거절, 스레드 시작 실패, executor 예외, timeout, late result, 결과 저장 실패, 재시작, 종료 확인을 같은 체크표로 검증할 수 있어야 한다. 기존 event·schema 17 원장·보고 결과는 계속 읽힌다. 두 종류의 의미를 하나의 느슨한 `success` boolean으로 축소해서는 안 된다.

### RT-06. 개별 호출 취소를 역할 전체로 확장한다

**확인한 사실.** `cancel_run`은 drafting run의 참여자에 대해 취소 의도를 먼저 기록하고 worker에 신호를 보낸다. 공개된 run은 거절한다. 합성·SEATS worker도 cancel Event를 가지고 있으나, 이들에 대한 신호는 `shutdown`의 전체 종료에서 함께 보내진다. 공개 뒤의 합성·검토만 선택해서 취소하는 실행 API는 이 기준에 없다. [`coordinator.py:219–242`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L219-L242), [`coordinator.py:351–359`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L351-L359), [`coordinator.py:433–441`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L433-L441), [`coordinator.py:528–535`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L528-L535)

**최소 개선.** 외부 작업 관리자에서 가져올 만한 것은 호출 ID별 취소 UX다. `(저장 출처, 키, attempt)`로 특정 시도를 식별하고, 취소 의도를 원장에 먼저 남기고 신호를 보낸다. 늦은 답은 해당 정책에 따라 보존하되 수용하지 않고, 공개된 원래 초안을 숨기지 않는다. 취소가 terminal인지 unknown인지는 동일한 자손 종료 증거로 판정한다.

**완료 조건.** 같은 취소 요청의 반복, 이미 끝난 시도, 종료 중인 시도, 잘못된 attempt, 서버 재시작을 구분한다. 취소한 검토 때문에 다른 run이나 전체 앱이 종료되지 않고, 예산은 환불하지 않는다. 스트림 전송 중 취소가 provider 쪽 계산까지 중단시킨다는 약속은 하지 않는다.

### RT-07. 전역 lock 안의 준비 비용은 측정 대상이며 큐 도입의 즉시 근거는 아니다

**확인한 사실.** `pump`는 runtime lock 안에서 작업 폴더·자료 검증·계획·관측 허가·격리 계획을 준비하고, 각 대기 시도마다 점유 조회를 한다. 합성 역시 lock 안에서 보고·자료·계획을 준비한다. 예산 조회는 예약 payload를 읽어 세고, 합성 점유는 시작·완료 사건을 투영한다. [`coordinator.py:35–85`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L35-L85), [`invocations.py:96–151`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/invocations.py#L96-L151), [`synthesis.py:50–102`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/synthesis.py#L50-L102)

**한계.** 이번에는 큰 사용자 원장에서 지연을 측정하지 않았다. 현재의 작은 실호출 cap을 고려하면 예약 사건 스캔만으로 심각한 성능 문제라고 할 수 없다. 코드의 전역 lock 역시 경쟁을 막는 실제 장치다.

**최소 개선.** 새 기능의 실제 workload를 정해 `prepare→reservation commit`, 취소 요청의 응답 시간, 완료 저장 지연을 먼저 잰다. 문제가 재현되면 원장 판과 입력 digest를 잡아 준비 작업을 lock 밖에서 수행하고, 마지막 짧은 거래에서 판·정책·자리·cap을 다시 확인하는 방식을 검토한다. 이력을 읽는 비용은 SQL 집계나 폐기 가능한 투영으로 줄이되, 기존 예약이 회계의 원본이라는 점은 바꾸지 않는다.

**완료 조건.** 개선 전후 같은 workload에서 지연이 줄고, 준비 중 취소·정책 변경·마지막 예산 경쟁·자료 변경을 놓치지 않는다. 이 결과 없이 Redis, daemon pool, distributed scheduler, 장기 자동 retry를 먼저 들이지 않는다.

## 3. 외부 기능 이식의 실행 경계

다른 프로젝트의 기능은 아래 범위까지 가져오는 것이 현재 구조와 맞는다. 구체적인 upstream 파일·라이선스 판단은 이 검토의 외부 프로젝트 분석에서 다룬다. 여기서는 현재 코드에 붙을 조건만 정한다.

| 외부 기능 유형 | 가져올 범위 | 유지해야 할 연결 조건 |
|---|---|---|
| 작업 보드·진행 이벤트·호출 추적 | 현재 원장의 invocation/상태를 읽는 UI와 정규화된 완료 관측 | UI의 `done`이나 프로세스 exit를 `acceptance` 대신 쓰지 않는다. |
| 실패 복구·checkpoint | 입력 판·시도 ID·종료 증거·사람의 확인을 보존하는 복구 흐름 | blind 초안을 resume 대화에 자동 재주입하거나 unknown을 자동 retry하지 않는다. |
| 작업별 subprocess·worktree | 향후 구현자 역할의 writer 경계에 한정 | 현재 discussant의 읽기 전용 계획을 몰래 write 가능하게 바꾸지 않는다. writer는 새 계획·관측·권한 계약이 필요하다. |
| 자동 다음 단계·병렬 배정 | 사용자가 승인한 작업을 기존 prepare/reserve 경로로 제출 | RT-01/02를 먼저 처리하고, 새로운 큐가 원장을 재생하면서 모델을 다시 부르지 않게 한다. |
| native CLI schema/stream adapter | 구조화 출력 검사·작은 호환 adapter | 관측한 버전과 명세 판에 묶는다. timeout 텍스트 fallback·유료 fallback은 이식하지 않는다. |
| 외부 memory·skills·hooks | 일반/상위 역할의 명시적 자료 선택·고정 사본 | 격리 참여자의 CLI 전역 설정에 연결하지 않는다. 현재 독립성 관측을 그대로 적용할 수 없는 변경이다. |

이 경계에는 의도적으로 남아 있는 제한도 있다. `isolation.plan`은 `--share-net`을 사용하고 CPU·메모리 상한을 두지 않는다. 자신의 CLI 인증 폴더는 토큰 갱신 때문에 쓰기로 연결하며, 검사 후 파일 변경 경쟁도 별도 제한이다. Codex의 앱·플러그인·프로젝트 문서 끄기와 HOME 읽기 금지, Claude의 restricted/safe-mode는 이미 있으므로 이를 새 제안처럼 반복하지 않는다. [`isolation.py:26–32`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/core/isolation.py#L26-L32), [`isolation.py:191–226`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/core/isolation.py#L191-L226), [`adapters.py:258–286`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/core/adapters.py#L258-L286)

로컬 코드를 실행하는 구현자·원격 도구를 붙이는 확장은 이 제한을 다시 평가할 계기다. 단순한 읽기 UI를 붙이는 작업에 전면 보안 재설계를 요구하는 근거는 아니다.

## 4. 재현 명령과 결과

### RT-01 및 RT-04: 실제 모델·프로세스 없는 합성 재현

저장소 루트에서 실행한다. 기존 테스트 fixture를 재사용하고 임시 원장만 만든다. `REAL` 표시는 controller의 회계 분기를 시험하기 위한 것이며 native CLI를 실행하지 않는다.

```python
import dataclasses, json, pathlib, sys, tempfile
sys.path.insert(0, "tests")
from test_app_controller import SyntheticExecutor, cli
from app.controller import Controller
from app.store import Store
from app.domain import acceptance
from core import contract, adapters, runner

class SyntheticRealTag(SyntheticExecutor):
    kind = contract.REAL
    def plan(self, spec, prompt, work_dir, *, inputs=()):
        return dataclasses.replace(
            super().plan(spec, prompt, work_dir), kind=contract.REAL)

for case, cap in [("uncapped_direct_controller", None),
                  ("runtime_setter_after_pinned_cap", 1)]:
    with tempfile.TemporaryDirectory(prefix="dml-review-synthetic-") as td:
        st = Store(pathlib.Path(td) / "store" / "journal.db")
        ex = SyntheticRealTag()
        ctl = Controller(st, ex, work_root=str(pathlib.Path(td) / "work"),
                         max_real_calls=cap)
        try:
            ctl.create_run("offline synthetic review", [cli("a")], min_independent=1)
            assert ctl.wait_idle(5)
            if cap is not None:
                ctl.max_real_calls = 3
            ctl.create_run("offline synthetic review two", [cli("b")], min_independent=1)
            assert ctl.wait_idle(5)
            saved = st.row("SELECT cap FROM live_budget WHERE singleton = 1")
            print(json.dumps({
                "case": case, "model_calls": 0,
                "synthetic_executions": len(ex.started),
                "runtime_budget": ctl.call_budget(),
                "saved_cap": None if saved is None else saved["cap"],
                "reservation_count": st.row(
                    "SELECT COUNT(*) AS n FROM events WHERE kind='live_call_reserved'"
                )["n"],
            }))
        finally:
            assert ctl.shutdown()
            st.close()

stream = [
    {"type": "item.completed", "item": {
        "type": "agent_message", "text": "completed answer"}},
    {"type": "turn.completed", "usage": {}},
    {"type": "item.completed", "item": {
        "type": "agent_message", "text": "uncompleted trailing answer"}},
]
result = runner.RunResult(
    ("synthetic",), runner.EXITED, 0, "\n".join(map(json.dumps, stream)),
    "", False, False, 0, 0, True, containment=runner.JOB_OBJECT,
    input_delivery=runner.INPUT_COMPLETE)
outcome = adapters.interpret("codex", result, requested_model="m")
print(json.dumps({
    "case": "terminal_then_new_answer", "model_calls": 0,
    "adapter_ok": outcome.ok, "answer": outcome.text,
    "controller_acceptance": acceptance(result, outcome)[0],
}))
```

관측 출력:

```json
{"case": "uncapped_direct_controller", "model_calls": 0, "synthetic_executions": 2, "runtime_budget": {"used": 0, "cap": null}, "saved_cap": null, "reservation_count": 0}
{"case": "runtime_setter_after_pinned_cap", "model_calls": 0, "synthetic_executions": 2, "runtime_budget": {"used": 2, "cap": 3}, "saved_cap": 1, "reservation_count": 2}
{"case": "terminal_then_new_answer", "model_calls": 0, "adapter_ok": true, "answer": "uncompleted trailing answer", "controller_acceptance": "accepted"}
```

### 기존 회귀 확인

검증 명령:

```bash
PYTHONPATH=tests python -m unittest test_app_contract test_synthesis_lifecycle test_claude_limits test_core_adapters test_runner_cancel
```

위 전체 묶음은 **완료하지 못했다.** 테스트 수집 중 `test_synthesis_lifecycle → test_model_synthesis → test_live_cli → test_app_cli_executor`의 import가 `bwrap_usable()`로 들어가 대기했다. 첫 실행은 중단했고, 원인 확인용 재실행은 35초 `faulthandler` 종료로 아래 stack을 확보했다. `test_app_cli_executor.py:33`의 `subprocess.run`에 timeout이 없으며, L216의 decorator에서 시험 실행 전에 호출된다. 이 결과는 시험의 assertion 실패가 아니라 이 컨테이너에서의 수집 지연이다. [`test_app_cli_executor.py:26–33`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/tests/test_app_cli_executor.py#L26-L33), [`test_app_cli_executor.py:216–220`](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/tests/test_app_cli_executor.py#L216-L220)

```text
Timeout (0:00:35)!
selectors.py:415 select
subprocess.py:2115 _communicate
subprocess.py:1209 communicate
subprocess.py:550 run
tests/test_app_cli_executor.py:33 bwrap_usable
tests/test_app_cli_executor.py:216 <module>
tests/test_live_cli.py:19 <module>
tests/test_model_synthesis.py:22 <module>
tests/test_synthesis_lifecycle.py:10 <module>
```

프로세스 격리 probe를 import하지 않는 범위는 별도로 완료했다. 실제 사용한 명령은 장기 대기를 막기 위한 timeout·traceback wrapper를 포함한다.

```bash
PYTHONPATH=tests timeout 40s python -u -c 'import faulthandler, unittest; faulthandler.dump_traceback_later(15, exit=True); unittest.main(module=None, argv=["unittest", "-v", "test_app_contract"])'
PYTHONPATH=tests timeout 50s python -u -c 'import faulthandler, unittest; faulthandler.dump_traceback_later(35, exit=True); unittest.main(module=None, argv=["unittest", "-v", "test_core_adapters", "test_runner_cancel"])'
```

결과: 기준 `48ab4bd6f0e297587707aecb83ebc0cd9968892f`에서 `test_app_contract`는 5개, 0.359초, `OK`; `test_core_adapters`+`test_runner_cancel`은 42개, 0.109초, `OK`. 이 완료 묶음에는 skip이 없었다. `test_synthesis_lifecycle`·`test_claude_limits`는 이번 세션의 통과 목록에 넣지 않는다.

테스트 도구의 작은 후속 개선은 capability probe에 짧은 timeout을 두고 import 단계에서 격리 프로세스를 시작하지 않도록 분리하는 것이다. 그래야 합성 lifecycle 검사도 bubblewrap 가능 여부와 독립해서 수집된다. 제품 코드나 CI의 격리 검사를 끄는 제안이 아니다.

이 검증은 합성 fixture와 모의 프로세스의 계약 확인이며, 실제 provider 과금·계정 한도·사용자 PC의 격리 동작·모델 품질을 증명하지 않는다.

## 5. 읽은 범위와 남은 확인

- 전체 읽음: `core/runner.py`, `core/isolation.py`, `core/adapters.py`, `core/contract.py`, `core/env.py`, `core/eligibility.py`, `core/membership.py`, `core/quota.py`; `app/execution/{runtime,executor,invocations,seats,coordinator}.py`; `app/cli_executor.py`, `app/repository.py`, `app/domain.py`, `app/state.py`, `app/wiring.py`, `app/application/synthesis.py`.
- 주요 구간 읽음: `app/store.py`의 schema·잠금·백업·예산·거래·이벤트 저장, `app/controller.py`의 조립·복구·호환 setter, `app/launch.py`의 원장 선택·소유 잠금·서버 수명, `app/queries/public.py`의 계정 한도·합성 상태 조회. scope 밖의 문맥 자료·HTTP·화면은 다른 분석과 교차 확인한다.
- 대조한 테스트: `test_app_controller`, `test_app_contract`, `test_app_cli_executor`, `test_core_adapters`, `test_core_runner`, `test_claude_limits`, `test_synthesis_lifecycle`, `test_runner_cancel`, `test_runtime_boundaries`의 관련 fixture·실패 경계.
- 미확인: 정상 native CLI에서 RT-04 스트림 발생 여부, 실제 종료 미확인 프로세스의 생존, Windows job 배정의 시작 경쟁, 호스트 네트워크/자원 상한, 실사용 원장의 lock 대기·대용량 이력 비용. 이 항목을 실측 완료나 현 사용자 장애로 표기하지 않는다.
