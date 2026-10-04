# 데이터·상태·API·원장 이행 계약 초안

모든 새 이름은 **제안**이다. 현재 schema 14나 v0.2 wire 계약을 바로 변경하지 않는다. 기존 DB의 모든 event를 replay하면 모든 상태가 복원된다는 전제도 두지 않는다.

## 개체와 정본

| 개체 | 핵심 식별/필드 | 정본 소유 / 불변성 |
|---|---|---|
| Work | work_id, title, goal, requirements, external_card_ref, revision | M01. 앱 작업 내용과 GitHub 개발 카드의 상태는 다른 도메인; 원격은 ref+동기화 관측 |
| WorkflowPlan | plan_id/version, strategy, steps, dependencies, stop_rules | M01. 실행에 사용한 판 불변, 수정은 새 판 |
| Step | step_id, kind, inputs/outputs, acceptance_refs, owner | M01. prepare/review/model/code/delivery 등 typed kind |
| Run | run_id, work_id, plan/step refs, execution_mode, reveal policy | M03/M05. `isolated/general` 의미 보존 |
| InputManifest | manifest_id/hash, question, role/scope, source refs, memory/skill refs, policy/capability version | M02. 실행 후 불변, preview와 freeze 구별 |
| Invocation | invocation_id, run/step/role, attempt ordinal, plan hash, provider/model, reservation, lifecycle | M03. 논리 command와 실제 시도 분리, 모든 모델 부가 호출 포함 |
| ExecutionObservation | invocation_id, input_delivery, native outcome, tree_confirmed_empty, usage, raw refs, observed_at/host | M04 생산/M03 저장. 미상·지원 안 함·오류 구별 |
| ArtifactRevision | artifact_id/revision, content hash, kind, origin invocation, visibility, parent/supersedes | M05. 원문 불변, 변환본·화면·요약 별도 종류 |
| Finding / Check / Disposition | target artifact+hash+locator, check kind, evidence, verdict, author | M05. 모델 지적·검사 관측·사용자 처분 별개 |
| MemorySource / Preference | source ref/type/scope, eligibility, pin/exclude/version | M05 원본, M02 선택 정책. index/점수는 파생물 |
| Outbox / Inbox | event_id, target, dedupe, status, attempt, read/ack | M08. 원본 결과와 전달 상태 분리 |
| Capability / ConfigSnapshot | host, runtime/version, observed/unobserved, effective values, hash, last-good | M09. 비밀값 미포함, invocation에서 참조 |

관계는 `Work → Plan/Steps → Run → Invocation → ArtifactRevision → Finding/Check/Disposition`이며 다음 manifest가 특정 artifact revision을 참조한다. 관계 누락을 자동으로 “최신 것”에 붙이지 않는다. 파일 삭제·보관 정책도 참조가 남은 원본을 보호해야 한다.

## 상태를 한 success로 합치지 않는다

제안 조회는 다음 축을 따로 갖는다. 실제 enum 확정은 R2 계약 카드에서 한다.

| 축 | 예시 | 다음 동작의 의미 |
|---|---|---|
| 준비 | dependencies_satisfied / unresolved / blocked | 일이 성립하는가 |
| 소유 | unclaimed / owned / conflict | 누가 변경할 수 있는가 |
| 배정 | queued / admitted / budget_blocked / unsettled_blocked | 지금 호출해도 되는가 |
| 프로세스 관측 | not_started / running / exited / unknown | OS 수명은 무엇을 확인했는가 |
| 결과 수용 | pending / accepted / rejected | 입력·native outcome·tree 등 계약을 만족했는가 |
| 공개 | sealed / public / collected | 어떤 역할·화면에 보여도 되는가 |
| 검토 | not_reviewed / open_findings / disposition_recorded | 지적과 처리 기록이 있는가 |
| 검사 | not_performed / passed / failed / inconclusive | 어떤 범위의 독립 검사가 수행됐는가 |
| 전달 | pending / sent / acked / dead | 결과 알림이 도착했는가 |

`accepted`도 사실 검증 완료가 아니다. `acknowledge_unknown`은 사용자가 보고한 종료 확인 사건이지 CLI 성공·정족수 등급을 소급 획득하는 기능이 아니다. stale result는 원문/진단 참조를 남길 수 있어도 현재 attempt를 덮지 않는다.

## 명령과 조회

**명령 envelope 제안:** `command_id`, `kind`, `target_id`, `expected_revision`, `input_hash`, `actor`, `payload_version`, `payload`. 같은 command_id+동일 payload는 기존 receipt를 반환한다. 동일 ID+다른 payload는 충돌이다. 모든 실행 종류가 envelope를 무조건 필요로 하는 것은 아니며 우선 실행 생성/취소/수정 명령부터 적용한다.

**receipt 제안:** `accepted|rejected|blocked`, `operation_id`, `invocation_ids`(알려진 경우), `reasons`, `committed_revision`. 재전송 receipt는 실제 완료를 새로 만들어 내지 않는다. model process 시작은 DB transaction 밖이다. 예약 뒤 crash한 unknown을 자동 재전송으로 우회하지 않는다.

**query envelope 제안:** `ledger_id`, `server_instance_id`, `revision`, `selection_generation`, `observed_at`, `data`. client가 늦은 응답을 버릴 기준과 서버가 같은 내용을 생략할 기준을 구분한다. ledger 전체 revision을 추가하기 전에는 기존 aggregate별 `(id, seq)`만 쓴다. 여러 run의 최대 seq를 전역 cursor로 합치지 않는다.

**가시성:** Query에만 적용하고 storage는 누구나 읽을 수 있게 두는 것이 아니다. 원장 접근은 trusted coordinator 안에 두고 runtime mount에서 배제한다. 검색 index/inbox/report도 동일 public projection에서 만들어야 한다. read model에 봉인 본문을 넣고 화면 CSS로 숨기는 방식은 금지한다.

## 저장과 부작용

1. 상태 변경, command receipt, budget reservation, 관련 event와 필요한 outbox는 같은 SQLite transaction에서 기록한다.
2. 외부 model/Git/network/delivery는 transaction 바깥에서 실행하고 결과를 해당 ID로 되돌린다. DB lock을 잡고 긴 모델 호출을 기다리지 않는다.
3. 결과 저장 실패는 실행 실패와 구별한다. 재실행을 요구하기 전에 시작·종료·artifact 존재를 확인한다.
4. outbox는 필요한 작업에만 둔다. 같은 프로세스의 단순 view 계산까지 모두 event bus로 바꾸지 않는다.
5. current row와 event의 정본 역할을 명시한다. 초기에는 현재 행이 업무 상태의 기준이고 events는 감사/일부 projection 근거다. 새 canonical event log로 완전히 옮기려면 필요한 payload와 replay 검증을 별도로 갖춘다.

## 공통 invocation으로 옮기는 방법

현재 `participants`, `refine_turns`, `proposals`, `splits`, `collations`, `reviews`와 synthesis 사건을 **한 번에 drop/rename하지 않는다.** 첫 단계는 이들을 읽는 `InvocationView` adapter로 의미를 통일한다. 원본 위치를 `legacy_origin {table, primary_keys, event_key}`로 보존한다. 옛 상태에서 알 수 없는 필드를 추정해 채우지 않는다.

영속 invocation table을 도입할 때는 다음을 정한다.

- 기존 attempt ID가 있는 호출은 그 ID와 원본 key를 일대일 연결한다. ID 없는 queued review는 아직 시작하지 않은 step으로 남겨 호출 이력을 만들어 내지 않는다.
- 현재 시작 전 실패의 예약/호출 계수 규칙을 그대로 비교한다. 단순히 accepted/rejected 상태만 보고 소비량을 다시 계산하지 않는다.
- 모든 역할의 사용량 미보고, manual 결과, 취소, ignored late result를 보존한다. 필드 통일을 위해 provider별 token 의미를 합치지 않는다.
- **같은 DB 한 거래의 호환 쓰기만** 제한적으로 허용할 수 있다. 두 DB 또는 두 실행 엔진에 dual-write/dual-execute하지 않는다. 오래된 테이블을 compatibility projection으로 둘지 읽기 전용 legacy로 둘지 카드에서 확정한다.

## version·이행·복구

schema 이전은 배타 잠금/backup/검증/fail-fast를 유지한다. migration은 과거 결과 hash, 입력 hash, 호출 cap, reservation, 원문 인용, 공개 상태를 비교한다. 최신 schema를 옛 앱으로 강제 열지 않는다.

**이행 전 복구:** 사본 DB에서 모의 검증하고 새 engine을 켜기 전이면 기존 DB/코드로 돌아갈 수 있다. **새 실제 호출 후 복구:** 옛 backup 복원만으로 돌아가면 이미 소비한 호출·새 원문이 사라진다. 신규 DB를 보존하고 forward fix 또는 검증된 호환 export/read-only 구버전 조회를 택한다. API/feature flag를 끄는 것과 data downgrade는 별도다.

artifact 복구도 파일/대화/원장/외부 부작용의 범위를 나눠 preview한다. Git worktree rollback이 model token 지출, 외부 전송, 사용자 판단 기록을 되돌리지 않는다.

## 예시 JSON의 지위

이 준비서는 운영 JSON schema를 새로 추가하지 않는다. 필드 이름과 의미를 검토하는 문서이며, 구현 R2에서 실제 schema/fixture·호환 parser를 선택한다. 문서에 적힌 mock enum을 현재 API에 보내면 작동한다고 안내하지 않는다.
