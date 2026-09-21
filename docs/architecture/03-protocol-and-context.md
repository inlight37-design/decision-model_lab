# 03. JSON 계약, 문맥 구성, 에이전트 간 통신

> 2026-09-21 / 제안 계약 v0.1. 특정 공급자의 API를 복제한 문서가 아니다. 공급자별 형식은 adapter가 이 내부 계약으로 변환한다.

## 1. 가장 중요한 원칙: 저장할 데이터와 모델에 넣을 데이터를 분리

프로젝트 원장은 감사·복구를 위해 충분한 필드를 가져야 한다. 모델은 현재 판단이나 구현에 필요한 일부만 보아야 한다.

```text
전체 원장/원본 로그/저장소
    -> 코드로 선택·검사·중복 제거
    -> 현재 작업용 context manifest
    -> 모델별 최소 입력
    -> 구조화된 답변 또는 patch
    -> 코드 검증·원장 갱신
```

전송 JSON을 minify하는 것보다 ‘필요 없는 10MB 로그를 모델에 보내지 않는 것’이 먼저다. 이 문장에 쓰인 10MB는 규모 예시이며 실측 절감량이 아니다. 도구 응답을 모델 밖에서 처리하는 패턴은 [조사 지도 S21](01-evidence-and-landscape.md)을 참고한다.

## 2. 세 종류의 경계를 명확하게 둔다

| 경계 | 형식 제안 | 포함할 것 | 포함하지 않을 것 |
|---|---|---|---|
| 제어부 ↔ worker adapter | 버전 있는 JSON / JSONL | task ID, 실행 설정, 상태, usage, artifact ID | 실행 권한을 바꾸는 임의 자연어 |
| 모델 입력 | 작업에 맞는 JSON/짧은 텍스트/코드 조각 | 목표, 제약, 최소 근거, 필요한 도구 설명 | 전체 원장·모든 동료 대화·전체 로그 |
| artifact 저장 | 원본 파일 + metadata/hash | patch, 검증 로그, 명세, 문맥 조각 | 공개 Git에 넣으면 안 되는 키·민감 trace |

전송 계층에서 gzip이나 binary 형식을 쓸 수 있어도 모델이 원문으로 받는 토큰 수가 자동으로 줄지는 않는다. 압축 데이터를 base64로 프롬프트에 넣는 것을 토큰 절약 전략으로 사용하지 않는다.

## 3. 공통 계약의 범위

### 3.1 TaskSpec — 제어부가 발급하는 작업

의미상 필요한 필드는 다음과 같다.

```json
{
  "schema_version": "0.1",
  "kind": "task",
  "project_id": "demo-project",
  "task_id": "T-017",
  "state_version": 1,
  "base_commit": "1111111111111111111111111111111111111111",
  "goal": "기존 공개 인터페이스를 유지하면서 입력 검증을 추가한다.",
  "depends_on": ["T-010"],
  "write_paths": ["src/parser.py", "tests/test_parser.py"],
  "acceptance_ids": ["ACC-017-v1"],
  "context_ids": ["CTX-017-v1"],
  "risk": "low",
  "budget": {
    "input_token_limit": 16000,
    "output_token_limit": 3000,
    "max_attempts": 2
  }
}
```

이 예시는 실제 저장소/commit/사용자 예산이 아닌 **합성 fixture**다. 반복 숫자 commit은 형식만 보여 준다. 실행 시에는 실제 존재하는 commit을 resolver가 검증해야 한다.

`risk`는 제어부의 정책 분류다. 모델이 낮은 위험을 추천했다고 사용자의 권한 설정을 바꾸지 않는다. 예산은 프로젝트 수준 예약과 함께 확인해야 하며, 위 숫자는 권장 최적값이 아니다.

### 3.2 DecisionAdvice — 판단 모델의 추천

```json
{
  "schema_version": "0.1",
  "kind": "decision",
  "task_id": "T-017",
  "state_version": 1,
  "model_ref": "mock/decision-v0",
  "status": "ok",
  "advice": "cheap_worker",
  "probabilities": {
    "cheap_worker": 0.82,
    "frontier": 0.13,
    "needs_context": 0.05
  },
  "provider_confidence": 0.71,
  "context_id": "CTX-017-v1"
}
```

이 역시 합성 예시다. TypeSafe의 실제 raw response가 위 모양이라는 뜻이 아니다. adapter는 공급자 원문을 별도로 보존하고 공통 필드로 정규화한다. `model_ref`에는 실사용 시 실제 provider/model/revision 정보를 넣는다.

`provider_confidence`와 최대 확률을 동일한 값으로 강제하지 않는다. TypeSafe 공식 설명상 confidence는 분포에서 계산한 통계량이다. 보정된 성공 확률이 필요하면 별도의 평가 과정을 거친다. [조사 지도 S03]

최종 실행 경로는 `DecisionAdvice`가 아니라 다음 순서로 결정한다.

```text
기본 권한·위험 정책
    -> task/context 버전 일치 확인
    -> 정상 schema·확률 범위·합계 검사
    -> 모델/작업군별 평가된 수용 기준
    -> 사용 가능한 worker와 예산 확인
    -> final route 또는 abstain/pause/escalate
```

모델 confidence 하나만으로 이 과정을 생략하지 않는다. `needs_context`와 `abstain`은 싼 모델을 계속 호출하라는 뜻이 아니라 자료 추가, 적절한 상위 모델, 사용자 승인 등 별도 경로로 이어진다.

### 3.3 WorkerResult — 산출물 후보

```json
{
  "schema_version": "0.1",
  "kind": "worker_result",
  "task_id": "T-017",
  "attempt_id": "A-017-01",
  "status": "candidate_ready",
  "artifact_ids": ["PATCH-017-01"],
  "summary": "허용된 두 파일의 변경 후보를 제출했다.",
  "limitations": ["독립 수용 검증은 아직 수행되지 않았다."],
  "usage": {
    "input_tokens": 1200,
    "cached_input_tokens": 0,
    "output_tokens": 350,
    "usd": null
  }
}
```

`usd: null`은 금액을 모른다는 뜻이며 0달러가 아니다. `candidate_ready`는 코드가 실제로 맞거나 통합되었다는 뜻이 아니다. 워커에는 `ACCEPTED` 상태를 발급할 권한이 없다.

별도 verifier가 candidate hash와 수용 기준 hash를 기준으로 결과를 내고, 통합 큐에서 필요한 재검증까지 끝나야 제어부가 작업을 수용한다.

## 4. 내부 JSON Schema와 모델 출력 Schema는 별개

내부 계약에서는 충분히 엄격한 schema를 사용할 수 있다. 그러나 공급자마다 constrained output에서 지원하는 JSON Schema 부분집합이 다를 수 있다. 내부 schema 전체를 아무 모델에나 그대로 전달하지 않는다.

권장 처리:

1. 내부 canonical schema는 버전 관리한다.
2. adapter가 공급자가 지원하는 최종 출력 schema로 투영한다.
3. 공급자 출력은 다시 내부 canonical validator를 통과한다.
4. 형식이 맞더라도 권한·참조·확률·최신성·증거 관계를 코드로 별도 검증한다.

파싱 실패를 수정하는 재호출도 예산에 포함한다. 반복 재생성을 무한 허용하지 않는다. refusal, timeout, truncated output, unsupported schema를 정상 오류 상태로 다룬다.

형식 예제와 오프라인 검사는 `contracts/`, `examples/`, `tools/`에 둔다. 이 검사는 실제 adapter나 배포 보안을 구현한 것이 아니다.

## 5. artifact ID와 hash의 의미

`PATCH-017-01` 같은 ID를 모델에 보여 준다고 모델이 그 파일 내용을 저절로 아는 것은 아니다. resolver 도구가 있어야 하고, 해당 작업에 읽기 권한이 있어야 한다.

산출물 metadata의 최소 항목:

```text
artifact_id, project_id, kind, producer_attempt_id
content_sha256, bytes, media_type
base_commit, acceptance_version, created_at
trust_level, sensitivity, access_scope, retention_policy
```

모델이 낸 임의 URL을 자동 다운로드하거나 파일 경로로 열지 않는다. ID를 서버 측 저장 위치에 매핑하고 traversal/symlink/프로젝트 경계/크기를 검사한다. hash는 내용 동일성 확인 수단이지 안전성·정확성·권한 증명은 아니다.

검증용 원본 로그는 보존하되 워커 간 전달에는 필요한 오류 구간과 로그 ID만 포함한다. 부정확한 요약이 의심되면 원본 구간을 다시 읽는다.

## 6. 이벤트와 메시지 전달

초기에는 로컬 subprocess의 NDJSON 이벤트와 SQLite 원장으로 충분하다. 예시 이벤트 이름은 자체 계약이다.

```text
task.claimed
attempt.started
attempt.usage_updated
artifact.created
attempt.candidate_submitted
verification.failed
verification.passed
integration.accepted
attempt.cancel_requested
attempt.cancel_confirmed
attempt.outcome_unknown
```

모든 이벤트에는 `event_id`, `task_id`, `attempt_id`, `sequence`, `schema_version`, `emitter`, 시점이 붙는다. 재전송은 가능하므로 중복 event ID를 무시하고 잘못된 순서·이전 lease의 이벤트는 상태를 되돌리지 못하게 한다.

각 공급자의 이벤트를 그대로 같은 의미로 취급하지 않는다. 예컨대 네이티브 `result`/`turn.completed`는 하네스의 실행 종료이지 사용자 수용 기준 합격이 아닐 수 있다. 원래 event도 별도로 보존해야 adapter 오류를 조사할 수 있다. [조사 지도 S11, S13–S14]

다수 워커가 하나의 JSONL 파일에 경쟁적으로 쓰게 하지 않는다. 원장은 단일 writer/트랜잭션이 관리하고 JSONL은 export 또는 전송에 쓴다.

## 7. 자유 대화 대신 typed handoff

워커 간 기본 메시지는 다음처럼 제한한다.

| 메시지 | 내용 | 처리 |
|---|---|---|
| `artifact_ready` | 산출물 ID와 인터페이스 버전 | 선행 조건 충족 여부를 코드가 확인 |
| `blocked_by` | 필요한 산출물/결정/정보 | 기존 계획과 대조 후 배정/상향 |
| `interface_change_proposal` | 변경 이유·영향·대안·검증 계획 | 기존 명세를 즉시 바꾸지 않고 검토 경로 |
| `review_finding` | 파일/구간/증거/심각도/재현 절차 | 수정 task 또는 기각 근거 기록 |
| `verification_result` | 대상 hash·검사 ID·결과·로그 ID | 권한 있는 verifier만 제출 |

‘진행 잘 되고 있습니다’, ‘한 번 더 생각해 주세요’ 같은 무의미한 왕복은 기계 간 기본 통신에서 제외한다. 사용자에게는 별도 요약 계층이 실제 증분·막힌 지점·남은 예산을 전달한다.

에이전트가 새 하위 작업을 제안할 수는 있어도 직접 무제한 생성·실행할 수 없다. 제어부가 기존 task 중복, 의존성 순환, 범위, 예산, 필요한 승인을 확인한다.

## 8. context manifest 설계

문맥 묶음은 단순한 긴 문자열이 아니라 다음과 같이 추적 가능한 선택 결과다.

```text
context_id + task_version + base_commit
선택한 명세/심볼/파일 구간/실패 증거의 ID와 hash
누락한 항목의 목록 및 필요할 때 가져오는 resolver
권한/민감도 필터 적용 결과
선택 알고리즘 버전 + 실제 또는 추정 토큰 수
```

### 읽는 순서

1. 현재 목표와 금지 사항, 수용 기준.
2. 관련 모듈의 인터페이스와 직접 의존성.
3. 수정 대상의 실제 코드 구간.
4. 재현 가능한 실패 또는 검사 결과.
5. 필요한 경우에만 넓은 call chain·과거 결정·추가 자료.

파일 일부만 넣으면 의미가 달라지는 경우에는 전체 함수/타입/관련 계약을 확장한다. 짧게 만들기 위해 제약, 단위, 부정 표현, 오류 스택의 원인 구간을 버리지 않는다.

### 문맥 예산의 우선순위

필수 명세와 금지 사항을 먼저 고정한다. 남는 예산에 증거를 넣는다. 필수 정보 자체가 한도를 넘으면 임의 잘라내기보다 task를 재분해하거나 큰 문맥을 지원하는 적절한 경로로 상향한다.

토큰 추정치의 tokenizer와 버전을 저장한다. 서로 다른 모델의 같은 문자열 토큰 수가 같다고 가정하지 않는다. 출력·추론·도구 후속 요청에 필요한 여유도 남긴다.

## 9. 절약 순서: 손실 없는 방법부터

### 단계 A — AI가 볼 필요 없는 것을 밖에서 처리

테스트 종료 코드·중복 로그·반복 검색·정렬·집계·파일 hash·정적 dependency 정보는 코드에서 처리한다. 매번 대형 LLM에게 stdout 전체를 읽히지 않는다.

### 단계 B — 중복 전달 제거

동일 작업 context ID, 고정 인터페이스, 이미 확인한 실패는 참조로 연결한다. 다만 새로운 세션이 필요한 내용을 실제 읽지 않았는데 알고 있다고 가정하면 안 된다. 캐시/세션 보유 여부를 adapter가 확인하고 필요한 내용은 다시 공급한다.

### 단계 C — 필요한 도구만 노출

모든 MCP 서버의 모든 tool schema를 모든 worker에게 넣지 않는다. 작업에 필요한 소수 도구와 명시적인 추가 요청 경로를 둔다. 도구 목록 축소가 안전 정책의 유일한 방어가 되지는 않는다.

### 단계 D — 출력 크기 제한

결과는 짧은 요약·파일 변경·증거 참조·미해결 항목으로 받는다. 코드 자체는 patch artifact로 전달한다. 대화 내에 동일 diff를 여러 번 복사하지 않는다.

### 단계 E — 표현 형식 비교

전송/저장 JSON은 유지한다. 모델 입력에 반복되는 균일한 표가 많다면 CSV/TOON을 실험하고, 깊거나 불균일한 데이터에는 compact JSON을 비교한다. TOON 제작자도 모든 구조에서 더 효율적이라고 주장하지 않는다. [조사 지도 S25]

### 단계 F — 손실 압축

LLMLingua나 LLM 요약 등은 후순위다. 압축 전후의 검증 성공률, 중요 정보 보존, 다시 읽는 횟수, 총비용을 측정한다. 코드 식별자·숫자·오류·안전 정책에는 특히 보수적으로 적용한다. [조사 지도 S26]

## 10. 세 가지 캐시를 섞지 않는다

| 캐시 | 무엇을 재사용하는가 | 무효화/주의 |
|---|---|---|
| 정확 결과 캐시 | 동일 입력·명세·모델·도구 상태의 확정 결과 | 상태/권한/시간 의존성이 바뀌면 무효화 |
| 공급자 prompt cache | 반복 prefix의 처리 결과 | 모델별 TTL·가격·쓰기/읽기 정책·키 규칙 |
| semantic cache | 비슷한 요청의 이전 답 | 비슷하지만 의미가 다른 명령을 오답으로 재사용할 위험 |

MVP에는 첫 두 가지를 명시적으로 다루고 semantic cache는 기본 비활성으로 둔다. 코드 수정·배포·권한 결정에는 유사도만으로 이전 결과를 재사용하지 않는다.

prompt cache를 위해 안정적인 명세·도구 정의를 앞에 두고 변하는 timestamp/task delta는 뒤에 둔다. 하지만 공급자별 정책이 다르므로 가격을 상수 하나로 가정하지 않는다. 조사 시 OpenAI 문서도 모델 세대별 캐시 차이를 구분한다. [조사 지도 S24]

**더 짧은 입력이 항상 더 싼 호출은 아니다.** 오래 재사용하는 큰 prefix가 할인되어 처리되는 상황에서는 새로 압축한 짧은 입력보다 청구가 적을 수 있다. 반대로 오래된 큰 prefix가 문맥 품질을 해칠 수 있다. 토큰 수, 청구액, 지연, 품질을 함께 본다.

## 11. 메모리 캡슐과 마일스톤 인계

새 세션의 시작 자료는 다음을 우선한다.

```text
현재 승인된 목표·금지 사항
마지막 수용 commit과 명세 버전
완료된 증분과 실제 검증 근거
열린 task / 차단 원인 / 다음 한 단계
아직 유효한 설계 결정과 적용 범위
다시 시도하지 말아야 할 실패 + 그 조건/반례
필요 시 원문을 찾을 수 있는 artifact 목록
```

전체 과거 대화를 매번 붙이지 않는다. 캡슐을 생성하는 비용도 기록하고, 문서가 과거 상황을 영구 규칙으로 굳히지 않게 한다. 캡슐의 원본 증거가 바뀌면 무효화한다.

`AGENTS.md` 같은 자동 로딩 파일에는 짧은 운영 불변 조건과 문서 지도를 둔다. 이 조사 문서 전체를 매 실행의 시스템 프롬프트로 넣지 않는다. ‘관련 문서는 필요할 때 읽기’와 ‘모든 기록을 항상 읽기’는 다르다.

## 12. MCP와 A2A를 언제 붙일 것인가

MCP는 에이전트가 도구·자료에 접근하는 경계에 유용하다. A2A는 독립 실행 주체에게 작업과 산출물을 주고받는 원격 경계에서 검토한다. 로컬 프로세스 두 개를 연결하기 위해 처음부터 모든 프로토콜 계층을 넣을 필요는 없다. [조사 지도 S27–S28]

내부 계약의 ID·상태·오류·산출물 의미를 먼저 고정하면 나중에 transport를 바꿀 수 있다. **프로토콜을 채택하는 것과 coordinator의 권한·예산·검증 정책을 구현하는 것은 별개의 일**이다.

## 13. 반드시 시험할 계약 오류

잘못된 JSON, 알 수 없는 schema version, 누락된 task ID, 다른 task의 context ID, 만료된 state version, 합계가 맞지 않는 확률, 범위 밖 confidence, `NaN`, 없는 artifact, 다른 프로젝트 자료, `../` 경로, absolute path, symlink 경계 우회, 과도한 payload, 허위 usage, 중복 이벤트, 오래된 lease 결과, 워커의 자기 승인 상태를 시험한다.

JSON Schema가 검사하는 부분과 실제 저장소·프로세스·정책이 있어야 검사할 수 있는 부분을 테스트 보고서에서 나눈다. 몇 개의 fixture가 통과했다고 전체 보안·동시성·복구가 구현되었다고 표시하지 않는다.
