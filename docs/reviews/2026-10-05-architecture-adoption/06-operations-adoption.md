# 06. 운영·작업 도구에서 이식할 범위

검토일: **2026-10-05**. 우리 코드 기준은 **`48ab4bd6f0e297587707aecb83ebc0cd9968892f`**다. GitHub와 클라우드 checkout에서 선택 코드를 읽었다. 사용자 PC·로그인된 CLI·외부 제품의 실행·모델 품질·구독 차감량은 이번 분담 검토에서 관측하지 않았다. 아래의 구현 크기와 기대 효용은 **분석·제안**이며 실측 일정이나 성능 수치가 아니다.

## 판단

**외부 운영 엔진을 더 붙이는 것보다, 이미 이식한 의미를 현재 서비스 경계에서 완성하는 편이 적합하다.** 작업 계획·선행 조건·막힘 설명·입력 고정·공통 호출 회계·판 비교가 이미 있다. 10월 4일의 OP 제안에 `미구현`이라고 적혀 있다는 이유로 이 기능들을 다시 만들면 같은 상태를 두 곳에서 관리하게 된다. 현재 기능과 날짜가 붙은 당시 제안을 먼저 구별해야 한다. [C01] · [C02] · [C03]

핵심 선택은 다음과 같다.

- **유지:** Backlog식 공통 준비 판정, Beads식 조건부 쓰기, Gas Town식 실행/후처리 실패 구분, tmux식 화면/실행 분리라는 원리를 기존 SQLite·서비스 경계에 유지한다.
- **좁혀 도입:** 저장된 검색 조건, 결과·수정 판의 읽기 비교, 요청 응답을 잃었을 때 기존 실행으로 돌아가기, 완료 기준에서 해당 결과 근거로 이동하는 기능을 우선 검토한다. 새 모델 호출이나 상시 서버가 필수인 기능은 아니다.
- **조건부:** 지속 실행, 실행 중 사용자 메시지, 파일 checkpoint, 원격 작업 claim, 설정 hot reload는 실제 사용 요구와 수명·권한 계약이 생긴 뒤 범위를 정한다.
- **보류:** Dolt·Gas Town·LangGraph·Lite-Harness를 두 번째 실행/상태 엔진으로 넣는 변경, PTY 화면을 결과 정본으로 쓰는 연결, 유료 API 라우터의 자동 연결, 여러 쓰기 작업자의 자동 병합은 현재 단계에 필요하지 않다.

앱의 **일반 팀원도 현재 native adapter 수준에서는 읽기 전용 논의자**다. 일반/격리라는 협업 모드 차이가 파일 쓰기 권한 차이라는 뜻은 아니다. worktree·코드 복원·refinery 이식은 화면 편의만 추가하는 일이 아니라 새로운 쓰기 역할을 여는 일이다. `core/adapters.py`가 이 경계를 명시한다. [C04]

## 1. 이번에 직접 다시 읽은 원문

이 절은 이번 검토의 직접 읽기 범위다. 앞선 조사에서 읽었다는 기록을 이번 직접 확인으로 합산하지 않는다. 공개 코드의 고정 SHA를 다시 조회했으며 최신 branch 전체를 감사하지 않았다. `전체`는 **해당 파일 전체**를 뜻한다.

| 프로젝트 | 고정 판·원문 | 이번에 읽은 범위 | 확인한 의미·한계 |
|---|---|---|---|
| tmux | `e476c1230b958df0cb12977517d24b3dc931375b`, [구독 변경][S01], [구독 timer][S01b] | control.c 850–884, 1042–1138 | 값이 같은 구독 알림 생략, 구독 종류별 조회. 서버·PTY·재접속 실행은 이번에 재현하지 않음 |
| Beads | `2f1e8be3ca1fe990727858ccd8e4a78461b39c7c`, [claim.go][S02], [issue_operations_tx.go][S03] | claim 1–210; transaction 파일 전체 1–103 | 소유자/상태/row version CAS, 동일 actor 재claim, SQL commit과 후속 이력 commit의 분리. Dolt 경쟁·장애 주입 미실행 |
| Backlog.md | `69e7b15362337d6712783d9a685f6e4bb693fa9d`, [readiness.ts][S04] | 파일 전체 | unique/missing/ambiguous 의존성의 공통 읽기 판정. import한 identity 함수 내부와 전체 UI는 이번에 재감사하지 않음 |
| Gas Town | `649b832b7672bc7a2dbef26f5983aba6198b819b`, [dispatch.go][S05] | 파일 전체 1–178 | plan, validate, execute, 후처리의 분리. Execute 뒤 OnSuccess 실패의 별도 오류. worker·refinery 통합 미실행 |
| Cline | `39ff2359f7e08231281539696e48a166ce49270c`, [checkpoint-restore.ts][S06] | 1–175 | 현재 worktree의 사전 사본·private ref·commit/rollback. SDK의 이 파일만 읽었고 VS Code 제품 전체 복구 의미를 검증하지 않음 |
| Lite-Harness | `dd99cfdfc68dbb6b3f7f986d54efd42572373a6c`, [session.mjs][S07], [protocol.mjs][S08], [Codex transformation][S09] | session 전체 1–107; protocol 1–180; transformation 전체 1–48 | 빈 결과 경로의 기본 result, 공통 success/비용 기본값, 선택한 텍스트 이벤트만 변환하는 범위. provider SDK·실제 실행 미확인 |
| Symphony | `be10a1b79df723d6d7612b5651c8522704dafb2e`, [workflow_store.ex][S10], [orchestrator.ex][S11] | store 1–180; orchestrator 803–865 | last-good 설정 유지와 candidate/claimed/running/blocked/slot 조건 분리. Linear·App Server·자동 재시도 실행 미확인 |
| LangGraph | [공식 Persistence 문서][S12], 2026-10-05 조회, rolling 문서로 commit SHA 미제공 | Persistence, Checkpointer vs. store, MemorySaver 재시작 한계, checkpoint 증가·하위 graph 범위 절 | thread checkpoint와 cross-thread store의 구별. 코드·영속 backend·외부 부작용 재실행을 이번에 시험하지 않음 |

**출처 경로의 실제 변경:** `steveyegge/beads`의 contents 조회는 `Moved Permanently`를 반환했다. 그 응답의 repository ID `1074561042`를 GitHub metadata로 재확인하면 정식 경로는 [`gastownhall/beads`](https://github.com/gastownhall/beads)였다. 이 경로에서 **같은 SHA**의 위 두 파일을 읽었다. 옛 연구의 SHA를 버리거나 새 main 내용을 같은 근거로 섞지 않았다. 날짜 기록의 옛 URL은 보존하고 이 문서가 현재 확인 경로를 제공한다.

LangGraph의 `/durable-execution` 요청은 이번 조회에서 `/persistence`로 이동했다. 따라서 예전 페이지에 있었다는 상세 replay 정책을 이번 읽기로 확인했다고 쓰지 않는다. 이 문서에서 직접 확인한 LangGraph 주장은 위 표의 persistence 범위로 한정한다. [S12]

## 2. OP01–OP12를 현재 코드에 다시 맞추기

아래 상태는 이전 계획을 채택했다는 선언이 아니라, **동일한 의미의 기능이 현재 어디까지 존재하는지**에 대한 대조다. 세부 원안은 [10월 4일 OP 설계](../../research/operations-comparison-2026-10-04/ADOPTION.md)에 있다. 당시 문서는 그대로 두고 현재 기능의 집은 [FEATURES](../../FEATURES.md)와 [실행 아키텍처](../../../app/ARCHITECTURE.md)로 유지한다.

| 기존 후보 | 현행 코드에서 확인한 부분 | 추가 이식 판단·상한 |
|---|---|---|
| OP01 재접속·명령 단계 | 요청 세대/abort, 공개 projection·페이지 캐시, run ID 존재 검사 | **좁혀 도입:** 실패한 화면 요청에서 기존 run ID를 다시 조회하는 동선. 전역 event revision·command receipt는 현재 없지만, 그 부재만으로 중복 호출 결함을 선언하지 않음 [C05] · [C06] · [C07] |
| OP02 지속 실행 | launcher owner 잠금·PID/nonce, 종료 요청 뒤 idle까지 기다림 | **조건부:** 상시 소유 모드는 별도 제품 선택. 현 launcher를 tmux daemon으로 교체하지 않음 [C08] |
| OP03 탐색·필터·명령창 | 공개 검색, task 선택 조회, 페이지화·선택 상세 | **좁혀 도입:** 저장된 query와 최근 선택 복원부터. command palette는 같은 서버 명령을 호출하는 얇은 UI일 때만 [C06] · [C09] |
| OP04 준비/담당/용량 | 계획 의존성, CAS, `missing/plan_changed/dependency_cycle/not_completed`, 슬롯·상한·unsettled 이유 | **대부분 이미 있음:** 분산 claim·worker lease까지 도입하지 않음. GitHub 카드와 앱 원장의 소유권은 다른 문제 [C02] · [C03] |
| OP05 명세·완료 기준 | `title/goal/done_when/depends_on/revision`, 계획 판과 선행 결과 증거를 고정 | **이미 있음 + 좁힌 후속:** 완료 기준별 근거 링크가 실제 판단을 돕는지 확인. requirements/design/tasks 파일 세트를 매 작업에 강제하지 않음 [C02] · [C07] |
| OP06 판 비교·fork·복구 | 원본 보존 수정/재검토, 근거 hash, 템플릿에 실행·승인·예산을 옮기지 않는 경계 | **읽기 비교만 확대 가능:** 새 실행 설정 복원과 파일 복구는 분리. 일반 팀원 확장은 GR 설계가 먼저 [C01] · [C10] |
| OP07 실행 중 메시지 | 실행 입력 고정; 현재 메시지 전달 큐 없음 | **조건부:** 다음 실행의 조건 초안으로 저장하는 방식부터. blind 진행 중 주입·native steering·공유 mailbox는 별도 관측 전 보류 [C07] |
| OP08 문맥·압축 | 제한된 공개 기억 pack·선택 이유·입력 고정·오프라인 평가 경로 | **기존 기능 평가 우선:** Cline/Jev식 추가 요약·삭제 모델을 기본 연결하지 않음. 입력 bytes와 native 내부 tokens를 구별 [C01] |
| OP09 capability·결과 해석 | native outcome·전체 tree·입력 전달·모델 일치 검사를 분리 | **핵심 이미 있음:** 새 adapter 도입 때 실제 관측과 event fixture를 보강. 공통 success frame으로 현 수용 의미를 대체하지 않음 [C04] · [C11] |
| OP10 유효 설정·last-good | 템플릿 schema·내용 hash·현 명단/모델 재검사 | **상태 설명 좁혀 도입:** 자동 파일 reload 요구가 없으면 last-good daemon 불필요. stale 설정을 applied로 표시하지 않음 [C10] |
| OP11 수신함·알림 | 상태에서 계산한 내 차례·막힘·준비 행동, 별도 완료/읽음 DB 없음 | **이미 있음:** 외부 전달 요구가 생기기 전에는 outbox·재전송 큐·읽음 상태를 추가하지 않음 [C03] |
| OP12 공개 결과·산출물 비교 | 역할 결과·원본/수정 판·검색·호출 기록 | **좁혀 도입:** 필요한 차이와 근거를 한 화면에서 찾기. 코딩 산출물/PR 연결은 쓰기 역할이 있는 별도 범위 [C01] · [C04] · [C09] |

### 기존 중복 방어를 정확히 평가하기

`WorkService.create_run()`은 같은 `run_id`가 있으면 거절하고, 다듬기·분담·다음 단계 제안도 한 번만 소비하도록 조건부 UPDATE한다. 따라서 “command receipt table이 없으니 같은 확인 버튼을 재전송하면 무조건 새 모델 호출”이라는 평가는 틀리다. [C07]

남은 차이는 **중복 실행 거절**과 **원래 성공 응답의 재조회** 사이의 UX다. 첫 POST가 서버에 적용됐으나 응답을 못 받은 경우, 이미 알고 있는 run ID로 상태를 조회하고 사용자에게 그 실행을 보여줄 수 있다. 이것이 충분하면 새 receipt schema가 필요 없다. 여러 종류의 비동기 명령에서 응답 유실·재시도가 실제로 반복되고 단순 조회로 해결되지 않을 때만 별도 command ID와 결과 조회를 설계한다. 이 절은 장애를 직접 재현한 결함 보고가 아니라 코드의 현 보장과 가능한 후속 설계를 구분한 것이다.

## 3. 직접 읽은 프로젝트별 판단

### 3.1 tmux: 상태 관찰의 원리를 취하고 터미널을 정본으로 만들지 않는다

`control_check_subs_session()`은 새 값을 계산한 뒤 이전 값과 같으면 알림을 보내지 않는다. 구독 timer도 실제 있는 구독 종류를 보고 필요한 묶음을 조회한다. 여기서 가져올 가치는 **사용자가 보고 있는 대상과 바뀐 정보에 관찰 비용을 집중**하는 방식이다. [S01] · [S01b]

현재 앱은 그 방향을 이미 구현했다. `BrowserPages._snapshot()`은 SQLite 읽기 token과 pause·상한·잔류 I/O·합성 worker 상태를 캐시 키에 포함하고, 거래 내부 projection은 캐시하지 않는다. 명령 관문은 별도의 새 조회를 사용한다. `LatestRequest`도 늦은 응답을 버릴 세대를 갖는다. 따라서 먼저 반복 조회와 차가운 조회를 현재 benchmark로 비교해야 하며, SSE·WebSocket·event bus 도입을 성능 개선의 출발점으로 삼을 필요가 없다. [C05] · [C06]

**남길 한계:** 페이지화는 전송·렌더를 제한하지만 차가운 전체 projection 비용을 상수로 만들지 않는다. 캐시가 바뀐 순간마다 반복되는 전체 이력 계산이 실제 원장에서 병목으로 측정되면 해당 query부터 줄인다. tmux 제어 프로토콜·PTY parser·pane 화면 저장은 이 문제를 해결하지 않는다. 지속 실행 또한 launcher 소유권·shutdown·실행 복구 정책의 변경으로 따로 다뤄야 한다. [C01] · [C08]

### 3.2 Beads: 원자적인 소유권 의미는 유용하지만 Dolt는 현재 필수가 아니다

claim 코드는 actor/assignee와 현재 상태를 확인하고 `row_lock`에 대한 CAS를 수행한다. 이미 같은 actor가 진행 중으로 소유한 경우에는 성공하는 no-op 경로가 있다. 이 코드를 “ready 작업 목록에서 선택하면 맡은 것”으로 축약하면 중요한 경쟁 처리 의미를 잃는다. [S02]

앱 안에서는 단일 owner와 같은 SQLite 거래가 이미 상태 쓰기를 조정하며, 계획 수정도 revision CAS를 사용한다. 개발 세션 간의 GitHub 카드 배정은 이와 다르다. 현재 카드 규칙의 먼저 댓글 단 세션 우선은 사람과 세션의 협업 규칙이지 원격 원자적 claim API가 아니다. 두 체계를 합친 두 번째 SQLite 카드 mirror나 Dolt를 곧바로 넣는 것은 정본·동기화·충돌 책임을 새로 만든다. [C02] · [C12]

**더 직접적인 배움은 쓰기 성공과 후속 이력 실패의 구별이다.** `issue_operations_tx.go`는 SQL commit 뒤 이력 commit이 실패해도 이미 적용된 변경을 재시도 신호로 되돌리지 않는 경계를 설명한다. 우리 coordinator에도 결과 저장 실패·재시작·늦은 결과 경로와 자동 재호출 금지가 있다. 이 방어를 유지하고 실제 attempt와 상태를 먼저 확인해야 한다. worker lease가 만료됐다고 자손 종료를 추론해서도 안 된다. [S03] · [C11a] · [C11b]

도입 재검토 조건은 “앱을 여러 사람·여러 기기가 동시에 제어해야 하며, 관측 가능한 claim 충돌이 실제 발생한다”이다. 그 전에는 기존 GitHub 카드 소유권과 앱 실행 소유권을 분리해서 보여주는 것으로 충분한지 평가한다.

### 3.3 Backlog.md: 같은 준비 판정을 여러 화면이 공유하는 것이 핵심이다

`readiness.ts`는 의존성이 없거나 모든 의존성이 유일하게 해석되고 완료됐을 때 준비됐다고 판단한다. unresolved와 unfinished 이유를 나누고, 이미 끝난 작업은 새로 시작할 후보에서 뺀다. 중요한 점은 이 함수가 상태를 바꾸거나 실행하지 않는 공통 조회라는 것이다. [S04]

우리 `workflow.project_tasks()`는 이 원리를 현재 계약에 맞게 이미 더 구체화했다. 계획 판이 바뀌면 과거 결과가 새 완료 증거가 되지 않으며, 선행 결과는 현재 계획의 사람 판단 완료와 unsettled/active 부재를 함께 본다. 누락/순환 참조는 읽기 때도 실패 쪽으로 처리한다. `TaskService.save()`는 쓰기 때 존재·자기참조·순환·진행 중 변경을 거절한다. [C02] · [C03]

**권고:** 별도의 ready 엔진을 추가하지 말고 이 공통 함수를 UI·headless·앞으로의 도구 연결에 계속 사용한다. 완료 조건은 작은 일에서는 지금의 텍스트로 충분하다. 복잡한 일에서만 완료 조건 하나를 고정 결과·검토·관측 근거에 연결하는 얇은 구조를 검토한다. 요구사항 파일 셋, 별도 Markdown tracker, 전체 kanban framework는 현 SQLite 정본을 개선하는 데 필수적이지 않다.

### 3.4 Gas Town: 배정의 단계는 가져오되 작업자 군집은 보류한다

`DispatchCycle`은 계획을 먼저 만들고, 각 항목에 선택적 validate를 거쳐 execute와 OnSuccess를 분리한다. Execute는 끝났지만 OnSuccess가 계속 실패하면 `ErrOnSuccessFailed`로 구별한다. 그러므로 보고서의 `Failed`를 “아무것도 시작하지 않았다”로 읽을 수 없다. [S05]

우리의 입력 미리보기→같은 거래의 실행 생성→coordinator→조건부 저장 흐름은 이 의미와 맞는다. `_finish_unstored`는 결과를 저장하지 못했어도 시작 비용을 되돌리지 않으며, `_recover`는 진행 중이던 시도를 unknown으로 바꿔 자동 재호출하지 않는다. 이는 새 분산 scheduler보다 먼저 보존해야 할 기능이다. [C07] · [C11a] · [C11b]

추가로 취할 부분은 **왜 아직 시작할 수 없는지 설명하는 작은 조회**다. 하지만 현행 `workflow.admission()`에 pause·unsettled·capacity·budget이 이미 있으므로 새로운 capacity 표를 만들기보다 실제 화면에서 이유를 찾기 쉬운지 확인한다. [C03]

formula·convoy·refinery·감시자·mailbox 전체는 현재 범위에서 보류한다. 새 작업자를 생성할 때마다 원장에 실제 호출이 늘고, 조정·보고·검토도 모델 호출이면 구독을 쓴다. 파일 수정 없는 논의 앱에 자동 병합 인프라를 먼저 넣는 것은 사용 가치보다 운영 표면이 앞서 늘어나는 선택이다. 장래 쓰기 역할을 만들더라도 최초 범위는 **하나의 허용된 worktree, 한 writer, 읽기 전용 검토자, 명시된 산출물**로 한정하는 편이 검증 가능하다. [C04]

### 3.5 Cline: checkpoint라는 이름보다 무엇을 되돌리는지 명시한다

읽은 SDK 복원 코드는 tracked 변경뿐 아니라 untracked 파일도 사전 snapshot에 넣고, 임시 private ref를 만들어 성공 또는 rollback까지 유지한다. rollback은 원래 HEAD와 index/working tree 복구를 시도하며 복합 실패를 따로 다룬다. 이 선택 범위만으로 ignored 파일·외부 DB·네트워크 부작용·모든 동시 수정까지 복원된다고 말할 수 없다. [S06]

우리 앱에서 지금 유용한 것은 **입력·원본 답·수정 답의 비교와 새 실행의 출발점 선택**이다. 이미 저장된 수정 판과 템플릿의 경계를 사용한다. 답을 이전 판으로 읽어 보는 일, 설정을 복원해 새 호출을 준비하는 일, Git 파일을 실제로 되돌리는 일을 하나의 “복구” 버튼에 묶지 않는다. 과거 승인·소비 원장을 복사하거나 되돌리는 일도 포함하지 않는다. [C01] · [C10]

파일 복원을 검토할 시점에는 먼저 쓰기 역할의 conformance가 있어야 한다. 그때 임시 repo에서 dirty index·untracked·ignored·다른 세션 수정·중간 복원 실패를 확인하고, 실패 시 preimage가 남는지 확인한다. 지금 Cline SDK 전체와 자동 checkpoint hook을 가져올 이유는 확인되지 않았다.

### 3.6 Lite-Harness: 인터페이스가 같아 보여도 성공 의미는 맞지 않을 수 있다

선택한 `Session.runTurn()`은 provider가 result를 내지 않아도 마지막에 resultFrame을 만든다. `resultFrame()`은 별도 오류가 없으면 success를 기본으로 만들고 비용 기본값도 0이다. Codex 변환 파일은 `agent_message`의 일부 item 이벤트를 다루며 그 밖의 이벤트는 빈 배열로 넘긴다. 이 **세 파일의 조합**은 공통 JSON이라는 이유로 실행 종료·오류·사용량 의미까지 같다고 가정하면 안 된다는 구체적 근거다. 다른 provider 전체가 같은 결함을 가진다고 확장하지 않는다. [S07] · [S08] · [S09]

우리 `acceptance()`는 전체 tree 확인, native outcome, 완전한 입력 전달, 비어 있지 않은 답, 보고된 모델 불일치를 별도로 확인한다. 구조화 응답의 성공 표시 하나로 이 관문을 대체하면 기존 계약이 약해진다. [C11]

**권고:** Lite-Harness는 adapter 비교 자료로 남기고 기본 의존성으로 채택하지 않는다. 새 provider를 연결할 때만 빈 stream, result 없는 EOF, native failure, unknown event, 사용량 누락, 권한 변경 no-op, 자손 잔류를 기존 recorded fixture와 비교한다. `usage unknown`을 0으로 채우지 않고, 제어 요청 접수와 실제 권한 적용도 구별한다. 공통 인터페이스는 작은 내부 port로 충분하며 실제 구독 실행은 지금의 공식 native 경로를 유지한다.

### 3.7 Symphony: 설정과 admission의 분리가 필요할 때만 작은 부품을 취한다

`WorkflowStore`는 새 설정을 load·parse·validate한 뒤 교체하며, 실패하면 마지막 정상 설정을 유지한다. `should_dispatch_issue?`는 candidate 여부, claimed/running/blocked, 전체/상태별/worker 슬롯을 나누어 확인한다. “파일이 바뀜”과 “유효 설정 적용”, “할 일 있음”과 “실행 허가”를 구별하는 구조다. [S10] · [S11]

현 앱도 템플릿과 입력을 검증하며, 실행 admission은 기존 원장 관문이 맡는다. 현재 읽은 경로에는 workflow 파일을 hot reload하는 요구가 없다. 따라서 last-good watcher를 먼저 만들지 않는다. 설정을 복원한 화면에 **저장된 값·현재 선택한 값·이번 실행에 고정된 값·CLI에서 실제 보고된 값**을 구별해 표시하는 작은 개선이 먼저다. [C10] · [C11]

상시 scheduler나 외부 issue tracker를 연결해야 할 때에는 새 설정을 기존 실행에 소급하지 않고, 실패한 reload의 이유와 실제 사용 판을 함께 표시해야 한다. Symphony를 controller 위에 올린 뒤 동일 SQLite 원장의 예약·unknown을 다시 계산하게 하는 구조는 피한다. 현재는 기존 owner·coordinator를 유지하는 편이 책임을 설명하기 쉽다.

### 3.8 LangGraph: 실행 상태와 공유 지식 구별은 유지하되 저장을 이중화하지 않는다

이번 공식 문서가 구별한 것은 thread별 graph checkpoint와 thread 밖의 store다. InMemorySaver는 process가 재시작되면 checkpoint가 사라지고, checkpoint를 무제한 쌓으면 지연·저장 비용이 늘 수 있다고 설명한다. [S12]

우리에게 필요한 의미는 이미 원장/실행 상태와 제한된 공개 기억을 구분하는 데 있다. 프레임워크 checkpoint가 별도로 `done`을 결정하고 SQLite가 호출·정족수·unknown을 결정하게 만들면 충돌을 해석하는 adapter가 추가된다. 프레임워크 이름 자체가 native CLI의 외부 호출을 정확히 한 번 수행하거나 전체 자손을 종료했다는 증거가 되지는 않는다. 이 마지막 문장은 문서의 제품 보증이 아니라 **현재 앱의 상태·부작용 경계에서 도출한 판단**이다. [C01] · [C11]

도입을 다시 볼 조건은 장기간의 분기·중단·재개 요구가 구체화되고, 기존 상태기계 확장보다 선택한 graph runtime과의 연결이 운영·검증 부담을 실제로 줄이는 경우다. 그때도 누가 상태의 정본인지 먼저 하나로 정하고 같은 호출을 두 엔진이 예약하지 않게 해야 한다.

## 4. 나머지 수집 프로젝트의 위치

이 절은 저장소에 실제 존재하는 수집 목록을 누락하지 않기 위한 지도다. **아래 제품은 이번 분담에서 upstream 전체 또는 최신 기능을 직접 재확인하지 않았다.** 근거는 기준 SHA에 있는 기존 조사 기록이며, 현재 서비스 지원·요금·종료 여부를 새로 보증하지 않는다. 채택하려면 해당 항목의 공식 원문과 판본을 다시 확인한다. 상용 제품 비교 순위를 만들지 않는다.

| 수집 대상 | 기존 기록에서의 참고 기능 | 이번 채택 판단 | 다시 볼 구체 조건 |
|---|---|---|---|
| Orca | 작업별 worktree, inline diff, 구조화 연결/터미널 대체의 경계 | **조건부:** 쓰기 역할의 산출물 비교 패턴만. 전체 executor·PTY 대체 경로는 현 native 계약을 대신하지 않음 | 한 writer 코딩 기능이 실제 제품 범위가 된 때. v0.4 F26의 고정 blob과 현판 차이를 재독 |
| Paseo | daemon과 desktop/web/mobile client 분리 | **조건부:** 재접속 대상과 원장 소유자 표시만 | 모바일·원격 제어의 실제 필요, 인가·relay·서버 소유권 요구가 생길 때 |
| herdr | detach, 화면 배치 복원, native resume의 구별 | **좁혀 도입 가능한 설명:** 연결됨·프로세스 살아 있음·이전 세션에서 새 시도함을 구별 | 지속 실행/재부팅 후 복원 기능을 만들 때. resume 문맥을 새 blind 초안으로 인정하지 않음 |
| OpenCode | 서버와 UI 분리, 공통 HTTP/event 계약 | **원리 이미 있음:** HTTP/headless가 같은 controller를 사용. SSE는 측정 후 | 실제 push UI나 외부 client 필요가 기존 polling/API로 해결되지 않을 때 |
| AionUi | 발견/설치/연결 온보딩·통합 화면 | **좁혀 도입:** 발견됨·로그인됨·관측 적격을 구별해 표시 | 준비 실패 UX가 반복될 때. API key 온보딩을 구독 전용 기본 흐름에 넣지 않음 |
| Vibe Kanban | 작업→workspace→diff→PR 연결 | **조건부 패턴 참고:** 개발 산출물의 링크 관계만 | 쓰기 역할 도입 시 유지보수·현재 배포 상태부터 재조회. 옛 sunsetting 기록을 현재 종료 사실로 확대하지 않음 |
| Claude Code Agent Teams | task 의존성·소유자·메시지·완료 hook | **작업 의미만 참고:** 일반 역할의 좁은 분담·완료 조건. native teams 자체는 보류 | 다른 provider와 동일한 통제·회계가 가능한 실제 headless 지원을 기기에서 관측할 때 |
| Conductor·Cursor | 병렬 사본, 변경/계획/검토 한곳 보기 | **조건부:** diff와 PR 동선을 쓰기 역할 이후 검토 | 동시 여러 writer가 꼭 필요한지 한 writer와 비교한 뒤 |
| Kiro | 요구·설계·작업 및 완료 기준 | **일부 이미 있음:** goal/done_when/depends_on. 복잡한 일에만 기준별 근거 | 텍스트 완료 기준만으로 판단 근거가 자주 사라질 때 |
| Devin | 조정자와 작업자의 분리, 개별 세션 개입 | **일반 분담은 이미 있음:** 중단·근거·호출 가시성부터 | 고정 입력으로 끝낼 수 없는 장기 일반 작업이 필요할 때 |
| Copilot·Jules | 한 작업·한 산출물, 비동기 검토 동선 | **개발 운영에 참고:** 카드→실행 근거→PR. 제품 runtime 구매/연결은 별개 | 기존 구독 경계를 바꾸는 명시적 선택이 있을 때 |
| Amp | 짧은 현재 문맥, 필요할 때 과거 thread 조회 | **현재의 짧은 인계·선택 기억 유지:** 자동 세션 rollover를 필수로 만들지 않음 | 실제 native compaction에서 꼭 필요한 정보가 반복 유실될 때 |
| Jev·Fusion | 선택적 분류/문맥 압축, 여러 후보 합성 | **평가 후보:** 단독/독립/검토/합성의 과제별 비교. 필수 조정자 또는 자동 유료 fallback 금지 | 동일 과제에서 실패·지연·전체 호출·차감량까지 개선된 근거가 있을 때 |

목록 근거: [2026-09-23 MCP/UI/runtime 조사 4절](../2026-09-23-mcp-ui-runtime/README.md#4-기존-앱에서-추출할-것과-가져오지-않을-것), [그 출처표](../2026-09-23-mcp-ui-runtime/SOURCES.md), [여러 AI workflow 조사](../../research/multi-ai-workflow-2026-09-25/README.md), [운영 제품 비교](../../research/operations-comparison-2026-10-04/PRODUCT-WORKFLOWS.md), [OTHER-PROJECTS](../../research/feature-catalog-2026-10-04/OTHER-PROJECTS.md), [v0.4 sources의 F26](../../architecture/v0.4/sources.json). Jev/Fusion의 업체 benchmark 수치를 이번 검토의 검증 결과로 다시 세지 않았다.

## 5. 무엇을 먼저 완성할 것인가

기존 [일반 팀원 검토 설계](../../architecture/general-team-review/README.md)의 GR-1→GR-2→GR-3은 현재 기능의 빈 부분을 메우는 순서다. 새로운 scheduler·graph engine·agent 팀 제품을 먼저 설치할 이유는 이 검토에서 확인되지 않았다. 특히 일반 `collected`를 독립 `revealed`로 바꾸어 검토 코드를 재사용해서는 안 된다. [C01]

다음 선택지는 구현을 승인했다는 뜻이 아니라 **서로 독립적으로 평가할 작은 범위**다. 기존 GR 작업과 겹치면 별도 기능을 만들지 말고 해당 서비스/UI 변경에 합친다.

| 작은 범위 | 사용자 가치·구현 접점 | 추가 호출·운영 비용 | 완료 판단 | 확대/중단 조건 |
|---|---|---|---|---|
| 기존 실행 회수 | POST 응답을 못 받아도 run ID로 조회·이동. `api.js`, `work.py`, 기존 run 조회 | 회수 자체 모델 0; 새 테이블 없이 시작 가능 | 응답 유실 후 같은 run으로 돌아오고 추가 attempt가 없음; stale target은 다른 실행으로 적용되지 않음 | 같은 ID 조회로 충분하면 종료. 다른 명령의 반복 문제가 입증될 때만 receipt 확대 |
| 저장된 탐색 조건 | task/kind/query와 최근 선택 ID 복원. `catalog.js`, `BrowserPages` | 모델 0; UI 상태만. 결과/본문 snapshot은 저장하지 않음 | 원장·작업 전환 뒤 stale filter를 설명하고, 봉인 결과를 저장/노출하지 않음 | 전체 검색 엔진을 다시 만들거나 정본 상태를 복제하게 되면 범위를 줄임 |
| 완료 기준의 근거로 이동 | 사용자가 정한 기준에서 공개 결과·검토·관측으로 연결. `TaskService`, report, PublicQueries | 수동 링크 0; AI가 근거를 고르는 추가 기능은 별도 호출 | 계획 revision 변경 시 낡은 증거임을 표시; 모델의 체크표시와 관측을 구별 | 간단한 작업에도 필수 양식/승인 단계가 늘면 중단하고 현재 텍스트 유지 |
| 공개 판 비교 강화 | 원본·수정·재검토·미해결을 같은 대상 ID/hash로 읽음. `revisions.js`, PublicQueries | 표시 0; 기존 데이터 재사용 | 원본 덮어쓰기 없음, 누락/해시 불일치 설명, 일반/격리 노출 경계 유지 | GR-2/3에 같은 UI가 있으면 별도 OP12 구현 금지 |
| 설정·관측 설명 | 저장 모델/현재 모델/실제 보고/미보고를 구별. template·카드·invocation 조회 | 표시 0; 상태 표시용 모델 호출 금지 | 저장 설정이 실제 적용 증거로 오인되지 않음; 허용 목록 변경은 새 입력 확인 | hot reload 사용 요구가 없으면 watcher/last-good 저장소를 만들지 않음 |

이 표의 모델 0은 **표시·저장·조회 자체에 새 추론 호출이 없다는 뜻**이다. 기억이나 자료가 더 많이 실제 prompt에 들어가면 다음 호출의 토큰·차감량·지연은 늘 수 있다. 따라서 UI 기능과 모델 작업 비용을 따로 집계해야 한다.

## 6. 큰 기능을 선택할 때 비용과 멈춤 조건

### 호출 비용은 팀원 수만으로 계산하지 않는다

계획 1회, 팀원 N회, 검토 R회, 수정 V회, 재검토 K회, 합성 S회가 있다면, 시도 상한은 기본적으로 **`1 + N + R + V + K + S`**이며 다듬기와 추가 계획, 실패한 시작/timeout의 소비 기록도 실제 정책에 맞게 포함한다. 이는 호출 수의 설명 모델이며 실제 계정 사용량의 계산식은 아니다. 같은 구독 안에서도 prompt 길이·출력·provider 정책이 달라 고정 달러 비용으로 환산하지 않는다. 현재 `InvocationLedger`의 예약·provider cap·unknown은 새 역할에서도 공통으로 사용해야 한다. [C13]

Jev 같은 별도 판단 모델은 분류비를 줄일 수 있다는 업체 주장을 가져오는 것보다, **분류→실행 실패→수정→검토→합성까지 포함한 전체 작업 비용**으로 판단해야 한다. Fusion류 합성도 정답 개선과 함께 단독 성공/합성 실패의 회귀를 남겨야 한다. 현재 구독 native 경로 밖의 API는 자동 fallback으로 붙이지 않는다.

### 규모별 경계

| 확장 | 실제로 늘어나는 책임 | 먼저 필요한 증거 | 멈추는 조건 |
|---|---|---|---|
| 지속 실행 | server discovery·owner·stale PID/nonce·브라우저 종료·시스템 재시작 | PC의 창 닫기/재접속/서버 crash 관측, 같은 원장 owner 하나 | 자손 종료 미확정, 다른 서버의 원장 소유권을 확정 못 함 |
| 실행 중 메시지 | 어느 입력/시도에 언제 적용됐는지, 철회·중복·늦은 메시지 | 다음 단계 소비 기록부터 모의 확인; 실제 steering은 adapter별 관측 | blind 초안에 외부 답이 새거나 적용 여부를 증명 못 함 |
| 원격 claim·분산 worker | claim source·lease·재시도 세대·복구·네트워크 분할 | 같은 작업 두 claimant, 모호한 쓰기 응답, 오래된 worker 재등장 | lease 만료만으로 재호출하거나 두 정본이 `done`을 결정함 |
| 코드 쓰기·복구 | 파일 권한·worktree 사전 상태·검토·외부 부작용·통합 | read-only 논의자와 별개의 한 writer conformance, 임시 repo 복원 시험 | 사용자 변경/미push 산출물 보존 실패, rollback 범위 불명 |
| 외부 graph/harness | 스키마 이행·두 실행기 오류 대응·관측/회계 adapter·업그레이드 | 직접 서비스 확장보다 책임/검증 부담이 줄어든 대조 | success frame이 기존 acceptance를 우회, 모델 실패/usage unknown 유실 |
| 자동 요약·분류 | 요약 자체 호출, 원문 보존, 반례/조건 유실, 긴 입력 재조회 | 동일 공개 fixture·과제에서 누락·정답·지연·전체 비용 비교 | 중요한 제약/미해결 반례 유실, 실패 후 유료 경로 전환 |

운영 복잡도는 패키지 개수뿐 아니라 **새 상태 정본·항상 켜 둘 프로세스·기기별 관측·장애 뒤 사람이 풀어야 할 종류**로 평가한다. 지금은 기존 서비스 하나에 작은 읽기 기능을 더하는 선택이 대부분의 사용자 효용을 제공한다. 외부 시스템 전체의 장점이 필요해지는 경우에도 현재의 단일 원장 owner, 한 writer, 독립 초안, 공통 상한과 unknown 의미는 먼저 유지할 계약이다.

## 7. 검증 범위와 후속 기록

- 이번 작업은 선택 소스 정적 대조다. 위 upstream을 설치하거나 실제 CLI·Dolt·Bun·Elixir·graph runtime을 실행하지 않았다. 기존 10월 4일 probe 결과는 이전 관측으로 연결할 뿐 이번 재현으로 표기하지 않았다.
- 이 문서에 제안한 조각은 구현 완료가 아니다. 제품 코드·기존 날짜 기록·출처 registry는 이 분담에서 수정하지 않았다.
- 원문 코드를 복사할 때의 파일별 라이선스·전이 의존성 조건은 별도 확인이 필요하다. 이번 결과는 동작 원리의 독자 구현 범위를 제안하며 재라이선스 허가를 판단하지 않는다.
- 현재 문서에 잘못된 상태를 발견하면 그 사실의 집인 FEATURES/실행 아키텍처에서 정정한다. 옛 OP 문서의 `미구현` 표시는 당시 시점의 기록이므로 그 문서를 덮어 현재판처럼 만들지 않는다.

## 코드 근거

아래 C 참조는 모두 동일한 기준 SHA에 고정한다. 줄 범위는 선택 읽기 위치이며 해당 모듈 전체 감사의 선언이 아니다.

- [C01 — 실행 아키텍처 39–135: 서비스 책임, 현재 구현과 일반 검토의 설계 경계][C01]
- [C02 — TaskService 14–92: 계획 validation·CAS·active/unknown·준비 검사][C02]
- [C03 — workflow 24–148: 단계·현재 계획 완료·선행 이유·수신함·admission][C03]
- [C04 — native adapter 1–29: 현재 read-only discussant 범위][C04]
- [C05 — api.js 15–36: 인증 전송과 요청 세대][C05]
- [C06 — BrowserPages 61–142: 공개 cache·cursor·선택 상세][C06]
- [C07 — WorkService 20–103: 입력 확인·동일 run 거절·일회성 승인 소비·동일 거래][C07]
- [C08 — launch 90–128 및 234–350: owner·stop·관측·원장·서버 수명][C08]
- [C09 — PublicQueries 75–139: 공개 검색·호출·기억 조회][C09]
- [C10 — TemplateService 24–124: 설정/승인 경계·hash·현 모델·import 확인][C10]
- [C11 — 수용 관문 75–97][C11], [결과 저장/늦은 결과 130–189][C11a], [unknown 해제·재시작 316–348][C11b]
- [C12 — 협업 규칙 74–90: GitHub 카드 배정·체크포인트][C12]
- [C13 — InvocationLedger 29–176: 공통 예약·자리·상한·unknown][C13]

[C01]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/ARCHITECTURE.md#L39-L135
[C02]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/tasks.py#L14-L92
[C03]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/workflow.py#L24-L148
[C04]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/core/adapters.py#L1-L29
[C05]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/api.js#L15-L36
[C06]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/pages.py#L61-L142
[C07]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/work.py#L20-L103
[C08]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/launch.py#L90-L350
[C09]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L75-L139
[C10]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/templates.py#L24-L124
[C11]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/domain.py#L75-L97
[C11a]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L130-L189
[C11b]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L316-L348
[C12]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/COLLABORATION.md#L74-L90
[C13]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/invocations.py#L29-L176
[S01]: https://github.com/tmux/tmux/blob/e476c1230b958df0cb12977517d24b3dc931375b/control.c#L850-L884
[S01b]: https://github.com/tmux/tmux/blob/e476c1230b958df0cb12977517d24b3dc931375b/control.c#L1042-L1138
[S02]: https://github.com/gastownhall/beads/blob/2f1e8be3ca1fe990727858ccd8e4a78461b39c7c/internal/storage/issueops/claim.go#L1-L210
[S03]: https://github.com/gastownhall/beads/blob/2f1e8be3ca1fe990727858ccd8e4a78461b39c7c/internal/storage/dolt/issue_operations_tx.go#L1-L103
[S04]: https://github.com/MrLesk/Backlog.md/blob/69e7b15362337d6712783d9a685f6e4bb693fa9d/src/utils/readiness.ts
[S05]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/scheduler/capacity/dispatch.go#L1-L178
[S06]: https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/session/checkpoint-restore.ts#L1-L175
[S07]: https://github.com/LiteLLM-Labs/lite-harness/blob/dd99cfdfc68dbb6b3f7f986d54efd42572373a6c/src/sdk/server/session.mjs#L1-L107
[S08]: https://github.com/LiteLLM-Labs/lite-harness/blob/dd99cfdfc68dbb6b3f7f986d54efd42572373a6c/src/sdk/server/protocol.mjs#L1-L180
[S09]: https://github.com/LiteLLM-Labs/lite-harness/blob/dd99cfdfc68dbb6b3f7f986d54efd42572373a6c/src/sdk/server/providers/codex/transformation.mjs#L1-L48
[S10]: https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/workflow_store.ex#L1-L180
[S11]: https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/orchestrator.ex#L803-L865
[S12]: https://docs.langchain.com/oss/python/langgraph/persistence
