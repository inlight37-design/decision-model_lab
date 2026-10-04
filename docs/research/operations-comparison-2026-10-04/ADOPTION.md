# Decision AI 적용 설계 OP01–OP12

모두 **미구현 제안**이다. 새 필드/endpoint/상태명은 계약 초안이며 현재 wire schema를 바꾸지 않는다. 기존 [D01–D10](../component-comparison-2026-10-04/ADOPTION.md)과 중복되는 기억·검색·알림은 같은 기능으로 확장한다. 다음에 선택한 작은 조각만 작업 카드로 옮기면 된다.

검토 기준은 `app/controller.py`의 prepare/create/pump/finish/recover, `app/store.py`의 transaction/events, `app/server.py`, `app/launch.py`, `app/static/index.html`, `app/memory.py`, `app/report.py`, `core/runner.py`, `core/adapters`다. 현재 입력 고정·격리 초안·호출 cap·tree 확인·공개 후 검토 계약을 보존한다.

## 선택표

| ID | 사용자에게 보이는 기능 | 참고 | 크기/추가 모델 호출 | 첫 시험 위치 |
|---|---|---|---|---|
| OP01 | 재접속 상태·변경분·명령 처리 단계 | tmux, Backlog, Symphony | 중간 / 0 | cloud 모의 원장·지연 응답 |
| OP02 | 창을 닫은 뒤에도 다시 찾는 실행 | tmux, Amp, Conductor | 큼 / 관리 자체 0 | cloud 수명 모의→PC launcher |
| OP03 | 작업 찾기·필터·키보드 명령 | tmux, Backlog, Amp/Cursor | 작음~중간 / 0 | cloud UI·모의 작업 |
| OP04 | 준비/담당/용량/복구 이유와 배정 미리보기 | Beads, Backlog, Gas Town, Symphony | 중간~큼 / 판정 0 | cloud 경쟁·장애 fixture |
| OP05 | 명세·완료 기준·진행 단계 연결 | Backlog, Kiro, formula | 작음~중간 / 수동 0 | cloud 데이터/UI |
| OP06 | 실행 판 비교·fork·복구 범위 미리보기 | Cline, Conductor | 중간, 파일 복원 큼 / 비교 0 | cloud temp repo·fixture |
| OP07 | 작업 중 메시지를 다음 단계에 적용 | Gas Town nudge, Amp, Devin | 중간 / 보관 0, 실행 별도 | cloud inbox 먼저 |
| OP08 | 문맥 사용·압축 후보·누락 평가 | Cline, Amp, Jev | 중간~큼 / 방식별 추가 | cloud 오프라인 fixture |
| OP09 | 어댑터 capability·결과 해석 비교 | Lite-Harness, tmux | 중간 / 오프라인 0 | cloud recorded event fixture |
| OP10 | 유효 설정·적용 이유·last-good | Symphony, Cline, Hermes | 중간 / 0 | cloud config validation |
| OP11 | 완료/질문/실패 수신함과 다음 행동 | Jules, Copilot, Anchor outbox | 중간 / 알림 자체 0 | cloud delivery fixture |
| OP12 | 답·검토·작업자·산출물 한곳 비교 | Cursor, Devin, Conductor, Gas Town | 중간 / 표시 0 | cloud 공개된 모의 결과 |

## OP01. 원장에 다시 붙기와 처리 단계 표시

**흐름:** 연결이 끊겨도 실행 ID 유지 → 재접속 표시 → 현재 snapshot 읽기 → 선택 실행 복원 → 새 상태만 갱신. 취소 버튼을 누르면 “요청 접수”와 “종료 확인”을 구별한다.

**계약:** 제안 snapshot envelope는 `ledger_id`, `run_id`, `revision`, `observed_at`, `state`다. 변경 cursor는 `ledger_id + revision`에 결속하고 오래되거나 다른 원장이면 전체 resync한다. mutation에는 `request_id`, `expected_revision`, `target_id`를 넣고 receipt와 operation 결과를 분리한다. 최초 단계는 기존 polling 위에 revision을 얹는 방식이며 SSE/WebSocket이 필수는 아니다.

**접점:** `Store`의 events/transaction과 `Controller.view`에서 snapshot을 일관되게 만들고 server가 전달한다. 화면 S3/S6의 오래된 응답 무시·조회 재사용을 보강한다. 이벤트 순번만 있다고 snapshot과 이후 구독 사이가 자동 원자적인 것은 아니다. 구독을 도입할 때 동일 read boundary 또는 replay 가능한 cursor를 정의한다.

**완료 시험:** 다른 원장 전환 중 늦은 응답, 연결 단절 중 종료, 새로고침 연속, cursor 만료, 동일 request 재전송, 느린 화면을 확인한다. 결과 원본은 누락되지 않고 재접속이 모델 호출을 추가하지 않아야 한다. 순번·시간만으로 최신 결과의 의미를 추측하지 않는다.

## OP02. 명시적인 지속 실행 모드

**흐름:** 사용자가 지속 실행을 선택하면 창을 닫아도 서버가 일을 소유하고, 다시 열면 같은 원장/실행을 찾는다. 현재 “호출이 끝난 뒤 서버 종료” 동작과 별도 모드다.

**계약:** `server_instance_id`, `ledger_id`, endpoint, `owner`, `started_at`, 상태 discovery 정보가 필요하다. PID 하나만 저장하면 재사용된 PID를 혼동할 수 있다. 연결 끊김, server down, process unknown, run finished를 따로 표시한다. discovery 정보에는 자격 증명을 넣지 않는다.

**접점/시험:** `app/launch.py`의 창 감시와 서버 소유권, store lock, server shutdown을 먼저 모의화한다. 서버 둘이 같은 원장을 열기, browser crash, server crash 후 stale discovery, 종료 중 재접속을 시험한다. 실제 Windows/WSL 창·프로세스 소유권·native CLI 관측을 마친 뒤 기본값 여부를 정한다. cloud 모의만으로 PC 수명 보장을 쓰지 않는다. tmux 설치는 필수 조건이 아니다.

## OP03. 작업 탐색·저장된 필터·명령 palette

**흐름:** “진행 중 / 내 입력 필요 / 복구 필요 / 완료” 필터 → 작업/실행/팀원 이동 → 현재 대상에서 가능한 명령 검색 → 실행. 답변 비교에서 한 칸 확대, 최근 열었던 실행 복원도 같은 탐색 상태로 다룬다.

**계약:** 읽기 query는 `task_id`, 상태, 기간, text, sort를 갖고 저장된 view는 query와 presentation만 보관한다. 명령 metadata는 `command_id`, 적용 target 종류, label, `enabled`, `disabled_reason`이다. 버튼과 palette가 같은 controller endpoint를 호출하고 서버는 허용 조건을 다시 검사한다. 대상 선택은 표시 순번이 아니라 고정 ID다.

**접점/시험:** 기존 `app/static/index.html`·`Controller.view`에 추가한다. 검색 본문 엔진은 D02와 공유한다. 오래된 filter가 빈 결과를 만들 때 전체 작업이 사라진 것처럼 보이지 않게 하고, target 전환 중 취소를 누르면 새 대상에 잘못 적용되지 않도록 시험한다. keyboard focus/escape/한글 조합 입력을 확인한다. 음성 입력은 후속 선택지로 남긴다.

## OP04. 준비·담당·용량을 나눈 작업판

**흐름:** 작업을 고르면 “선행 작업 미완료”, “자료 ID 불명확”, “다른 세션 담당”, “슬롯 없음”, “호출 상한”, “지난 실행 미확정”을 각각 보여준다. “배정 미리보기”는 실행 없이 후보와 제외 사유를 반환한다.

**계약:** `readiness {ready, unresolved, blockers}`, `claim {owner, version, acquired_at}`, `capacity {used, limit, unsettled}`, `admission {allowed, reasons}`를 구분한다. claim write는 expected owner/version을 검사한다. lease를 추가해도 만료만으로 이전 프로세스가 끝났다고 보지 않는다. GitHub card가 업무 상태의 원본인 동안 별도 DB가 원격 상태를 무단 확정하지 않도록 `source_revision`, sync status를 둔다.

배정 사건은 `dispatch_id`, `attempt_id`, `execute_started`, `execution_observation`, `bookkeeping_status`를 분리한다. 시작 후 bookkeeping 실패 시 동일 dispatch를 다시 실행하지 말고 실제 attempt를 reconcile한다. timer 재시도에는 generation/token을 붙인다. 이것은 분산 exactly-once 보장 선언이 아니다.

**접점/시험:** `_slots_used`, `unsettled`, `_budget_exhausted`, `pump`, `_recover`의 판정을 공통 projection으로 노출하고 Store transaction으로 소유권을 처리한다. 두 창 동시 claim, CAS 실패, unknown dependency, cyclic dependency, write 결과 모호, 실행 성공 후 저장 실패, stale retry timer를 fixture로 시험한다. 중복 호출이 없고 실패 원인이 사용자에게 설명돼야 한다. GitHub API 두 요청을 로컬 transaction처럼 취급하지 않는다.

## OP05. 명세와 완료 증거가 연결된 작업 양식

**흐름:** 간단한 일은 목표·완료 조건만, 큰 일은 요구/설계/작업을 펼친다. 각 완료 조건에서 결과·검토·시험으로 이동한다. 진행 단계는 모델이 쓴 체크표시와 실제 관측을 구별한다.

**계약:** `requirement_id`, `constraint_refs`, `acceptance_text`, `step_id`, `depends_on`, `evidence_refs`, `verification_state`, template version. 완료 기준의 관측은 `not_checked/observed/not_met/unknown`처럼 보존하며 “agent says done”이 곧 acceptance 통과는 아니다. 기존 사용자 승인·제약을 다시 묻는 단계는 만들지 않는다.

**접점/시험:** 기존 GitHub 카드 양식과 D07 template을 기본으로 하고 앱에서는 `prepare_run`의 고정 자료와 report에 연결한다. 빈 기준, 삭제된 step, 요구 수정 뒤 stale evidence, dependency cycle, 서로 다른 결과가 같은 기준을 주장하는 경우를 시험한다. 수동 작성·검증 연결은 추가 모델 호출이 없고 자동 계획은 현재 상위 역할 호출 cap을 쓴다.

## OP06. 판 비교·실행 fork·복구 미리보기

**흐름:** 이전 실행과 현재 실행을 고른다 → 입력/답변/검토 차이를 본다 → 원하는 판을 새 실행의 출발점으로 선택한다. 파일 수정 역할이 생긴 경우에만 “파일도 복구” 범위를 별도로 보여준다.

**계약:** `parent_run_id`, `source_snapshot_hash`, `fork_reason`, `selected_sections`, locator/hash 결속. 원본 run은 불변이고 budget 사용 이력도 되돌리지 않는다. 제안 file checkpoint에는 repo/worktree/base HEAD, tracked/untracked 범위, preimage ref, `restore_plan`, `restore_result`를 둔다. 외부 API·DB 쓰기 등 복구되지 않는 범위를 명시한다.

**접점/시험:** `app/report.py`, sources/input snapshot, cross-review finding의 source hash를 재사용한다. 처음에는 읽기 비교와 새 prepare까지만 구현해도 된다. file 복원 시험은 사용자 repo가 아닌 임시 repo에서 dirty index, untracked, ignored, concurrent modification, partial rollback을 다룬다. 복구가 실패하면 살아 있는 preimage를 잃지 않고 실패 범위를 보여줘야 한다. Cline의 private ref 구조를 그대로 복사할 필요는 없다.

## OP07. 다음 단계 메시지와 전달 상태

**흐름:** 실행을 보며 추가 조건을 적는다 → “현재 실행에는 아직 미적용” 상태로 보관 → 다음 합법적인 단계/새 실행에서 적용 → 실제 입력에서 확인. 철회·수정·순서 변경이 가능하다.

**계약:** `message_id`, target run/role, author, `created_at`, priority, expiry, body hash, `pending/consumed/withdrawn/expired`, `consumed_by_attempt`, input hash. 삭제 대신 처분 이력을 둔다. 동일 message 재전달도 소비 기록으로 구별한다. 독립 초안 진행 중 다른 역할 답변을 이 통로로 몰래 주입하지 않는다.

**접점/시험:** Store inbox와 `prepare_run`/다음 단계 manifest부터 시작한다. runtime steering은 native adapter가 관측상 지원하는 경우에만 별도 capability로 연결한다. 중복 전달, 메시지 소비 직후 crash, stale target, 취소된 run, 입력 고정 후 edit, TTL 만료를 시험한다. Gas Town rename claim처럼 claim과 최종 delivery ack의 간극을 반드시 고려한다. 보관·목록 자체는 모델 호출이 없다.

## OP08. 문맥 예산과 압축 실험

**흐름:** 기억·자료·질문·시스템 지침이 얼마나 들어가는지 본다 → 포함/제외 이유와 원문을 연다 → 선택한 압축 정책을 적용한 별도 입력으로 실험한다.

**계약:** `source_hash`, `section_kind`, bytes, tokenizer/model metadata, estimated tokens와 measured usage 구별, `preservation_rules`, `removed_locator`, `replacement`, `policy_version`. 원문은 보존한다. protected evidence, unresolved counterevidence, tool call/result 연결, 최근 사용자 조건을 평가한다. 바이트 상한을 token 보장으로 표시하지 않는다.

**접점/시험:** memory pack/D01/D05 위에서 (a) 결정적 섹션 선택, (b) 길이 제한, (c) summary, (d) Jev 유사 relevance 분류를 각각 비교한다. 우선 오프라인 fixture에서 필수 제약 유실률, 원문 재조회 가능성, 크기, 순서, 격리 범위를 측정한다. 모델 실험은 단독/압축 양쪽의 정답·timeout·지연·요약기 비용까지 합산한다. native CLI 내부 context를 제어 못 하는 경우 입력 pack 범위만 관리한다고 표시한다. 외부 API 도입은 기본값이 아니다.

## OP09. 어댑터의 공통 계약과 capability 표

**흐름:** 연결할 CLI의 stream, usage, permission, cancel, context, file changes 지원 상태를 본다. 원본 event와 해석 결과를 대조할 수 있다.

**계약:** capability에는 `supported/unsupported/unobserved`, 관측 버전/기기, evidence ref가 필요하다. frame에는 raw hash, provider event kind, normalized kind, sequence, `is_terminal`, unknown fields 보존 정책을 둔다. `usage=null`은 미상이며 0으로 채우지 않는다. adapter result와 controller acceptance는 분리한다.

**접점/시험:** 기존 `core/adapters.interpret`, runner, registration과 controller `_finish`를 기준으로 테스트 fixture를 만든다. empty stream, text-only then EOF, `turn.failed`, unknown tool event, usage 누락, permission setter no-op, parent 종료 후 child 잔존, stderr rejection을 다룬다. 공통 JSON이 있어도 `tree_confirmed_empty`, 입력 전달, native outcome이 확인되지 않으면 성공으로 승격하지 않는다. Lite-Harness는 비교 자료이며 새 기본 의존성으로 설치하지 않는다.

## OP10. 실제 적용 설정과 마지막 정상판

**흐름:** 설정/템플릿을 수정 → 검사 결과 확인 → 유효판 활성화 → 실행에는 그 버전을 고정. 잘못 저장한 새 판은 오류를 보여주고 마지막 정상판을 계속 사용할 수 있게 한다. 화면은 “어떤 값이 어디서 왔나”를 펼친다.

**계약:** `config_version/hash`, source location, parsed/effective values, matching rule reasons, loaded_at, last_good, validation errors. CLI에서 관측하지 않은 값은 설정 문자열만으로 applied라고 하지 않는다. 이미 실행한 manifest는 설정이 바뀌어도 그대로다.

**접점/시험:** 현재 prepare manifest와 D07 template loader에 연결한다. 부분 파일 write, invalid YAML/JSON, 경로 변경, 같은 mtime 다른 내용, unknown option, 중복 규칙, source hash 변경을 시험한다. last-good이 없으면 준비 불가이며 있으면 어떤 판을 썼는지 명확해야 한다. validation을 통과했다고 외부 hook을 자동 실행하지 않는다.

## OP11. 다음 행동이 있는 수신함

**흐름:** 완료, 사용자 질문, 미확정 종료, 저장 실패, 검토 필요를 한 목록에서 본다. 항목을 열면 관련 run/attempt/원문과 가능한 다음 행동이 나온다. 알림을 읽었다고 실행 실패가 해결되지는 않는다.

**계약:** 기존 D09 outbox를 확장해 `event_id`, action kind, target ID, dedupe key, delivery status, read status, retry count를 둔다. 모델 실행 재시도와 알림 재전송을 다른 큐/명령으로 둔다. 답변 전문을 외부 채널에 보내는 기능은 별도 선택이다.

**접점/시험:** 원장 event→read-only inbox→필요하면 durable outbox 순으로 구현한다. offline UI, 중복 이벤트, 전달은 성공했지만 ack 저장 실패, 오래된 action, 삭제된 target, 읽음/해결 상태 차이를 시험한다. 기본 앱 내부 목록은 서버·모델·외부 메시지 채널 추가가 없다.

## OP12. 공개 결과·작업자·산출물 비교 화면

**흐름:** 작업의 역할판에서 공개된 답/검토를 나란히 보고, 각 칸의 입력·모델·환경·사용량·종료 근거를 펼친다. 코딩 작업이면 branch/diff/checks/PR 링크를 함께 본다. 전체 요약에서 문제가 있는 칸으로 바로 이동한다.

**계약:** `task_id`, `run_id`, `role_id`, parent/child relation, workspace/host label, artifact kind/locator/hash, observed state/time. live 연결 상태와 원장에 저장된 관측을 구분한다. 다른 기기에서 얻은 CLI 관측을 이 기기 준비 완료로 재사용하지 않는다. 미관측 비용은 미상으로 표시한다.

**접점/시험:** 현재 `Controller.view`, 역할판, `app/report.py`, cross-review 원문 결속을 재사용한다. 공개 전 독립 초안 비노출, 비교 중 한 결과 갱신, artifact hash mismatch, 오래된 CI 링크, parent 취소 후 child unknown을 모의 시험한다. 기존 UI 디자인 부품을 사용하고 디자인 원본 수정이 필요하면 기존 원본→복사 절차를 따른다. 구현 초기는 모든 정보를 한꺼번에 펼치지 말고 상태 요약과 상세 drawer로 나눈다.

## 지금 클라우드에서 할 다음 조각

작은 카드 하나를 고른다면 **OP03 탐색·저장된 필터** 또는 **OP12 공개 결과 비교/상태 설명**이 사용자 편의에 바로 닿는다. 원장 신뢰성을 먼저 보강한다면 **OP01 revision/재접속** 또는 **OP04 실패 이유 projection**이다. OP05 명세 양식과 OP06 읽기 비교도 모델/PC 없이 가능하다. 실제 구현 우선순위는 사용자가 겪는 불편에 맞춰 고르며, 이 문서는 나머지 후보를 삭제하지 않고 유지한다.
