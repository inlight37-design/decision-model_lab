# Beads·Backlog.md·Gas Town: 일을 고르고 맡고 끝내는 서로 다른 층

고정 commit과 읽은 함수 범위는 [source-map](source-map.json)에 있다. Beads/Gas Town은 소스 분석, Backlog.md의 순수 판정 함수는 [probe](probe-results.json)로 확인했다. 세 도구를 설치해 함께 돌렸거나 분산 장애를 재현한 것은 아니다.

## 1. Beads — 작업 그래프와 소유권

**구조:** 명령/공통 work API → SQL 조건 작성 → issue operations → Dolt 저장과 이력. `internal/workapi/ready.go`가 frontends에 공통 조회 계약을 제공하고, `sqlbuild/ready.go`가 정렬·상태·제외 유형 등의 조건을 조립한다. 요청의 limit이 생략된 경우와 명시적으로 0인 경우가 다르다. UI가 임의 필터로 “ready”를 다시 정의하면 명령 결과와 어긋날 수 있다.

### ready와 claim은 다르다

ready는 의존성/상태를 포함한 작업 후보 조회다. claim은 **그 일을 누가 맡는가**에 대한 경쟁을 처리한다. `issueops/claim.go`는 이전 상태를 읽고 `row_lock`을 이용한 CAS 쓰기를 수행한다. open과 설정된 custom active 상태, 정확한 assignee, pool alias와 actor를 구별한다. 같은 actor가 이미 in-progress인 경우에는 idempotent no-op 경로가 있다. 경쟁 실패는 `ClaimConflictError`와 현재 assignee/status로 표현한다.

이 소스만으로 모든 호출자가 readiness를 강제한다고 단정하지 않는다. “목록에 방금 ready였다”는 사실도 claim의 원자성을 대신하지 못한다. 우리 적용은 `ready_reason`과 `claim_owner/claim_version`을 분리해 화면에 보여주는 방식이다. GitHub label을 조회한 뒤 바꾸는 두 요청을 SQL CAS와 동등하다고 하지 않는다.

### 데이터 commit과 이력 commit

`dolt/issue_operations_tx.go`는 SQL transaction을 먼저 commit하고 그 뒤 Dolt history commit을 처리한다. history commit 실패를 이미 성공한 데이터 쓰기의 실패로 반환하면 호출자가 같은 일을 다시 시도할 수 있기 때문에, 해당 실패를 기록/계측하는 경로가 있다. 이력 commit이 다른 writer의 변경도 포함할 수 있다는 제한도 소스에 있다.

`dolt/issue_claimer.go`의 verified claim 경로는 모호한 쓰기 결과 후 실제 상태를 다시 읽는다. 재시도 정책은 “예외가 났으니 쓰지 않았다”가 아니라 **부작용이 이미 발생했는지 확인**하는 방식으로 설계해야 한다. 우리 `_finish_unstored`와 재시작 복구를 보강할 때 참고하기 좋다. Dolt를 추가할 필요와는 별개다.

### lease와 압축

`issueops/lease.go`에서 본 lease는 heartbeat와 TTL을 갖지만 **노드 로컬 ephemeral 상태**다. 동기화되는 claim과 heartbeat의 분산 합의를 동일시하면 안 된다. row_lock 변경을 Dolt 충돌 감지에 활용하는 것과 lease를 다른 기기까지 배포하는 것은 다르다.

`compact/compactor.go`는 모델 요약 경로를 갖고 API key가 없으면 dry-run으로 전환한다. 요약이 더 짧지 않으면 건너뛰는 판단이 있다. 보드 정리·closed task 보관과 모델 호출로 본문을 축약하는 기능을 분리해 후보로 남긴다. 우리 현재 구독 전용 경로에 이 API 호출을 기본 연결하지 않는다.

| 재사용 후보 | 사용자 가치 | 우리 위치/한계 |
|---|---|---|
| 공통 ready query + 이유 | 지금 시작할 수 있는 작업만 보기 | 카드 조회 projection; GitHub와 별도 원장 간 진실의 주인 결정 필요 |
| claim 충돌 설명 | 이미 다른 세션이 맡은 이유 알기 | OP04; 같은 원장 내 CAS와 원격 카드 동기화 별도 |
| 모호한 쓰기 후 read-back | 재시도로 중복 일을 만들지 않기 | controller의 attempt 식별자와 저장 사건 결속 |
| lease 만료/heartbeat 표시 | 멈춘 작업자 찾기 | 만료만으로 프로세스 종료·안전한 재실행 단정 금지 |
| 완료 작업 축약/보관 | 큰 작업 목록 정리 | 결정적 보관 우선, 모델 요약은 비용·원문 보존 실험 |

## 2. Backlog.md — 명세와 여러 화면에서 같은 판정

**구조:** Markdown 작업/문서/결정 → 파일 작업/잠금 → ContentStore snapshot → task detail/search/readiness → CLI/TUI/web/MCP 표면. 이번에는 공통 판정과 파일 쓰기 경계를 읽었고 모든 UI 또는 MCP handler는 감사하지 않았다.

### identity를 먼저 해석한다

`task-record-index.ts`가 정규화된 ID에 대해 unique/ambiguous/missing을 만든다. 다른 두 파일이 같은 정규 ID를 주장하면 삽입 순서로 이긴 파일을 고르지 않는다. 같은 filePath가 active/completed 입력에 중복돼 들어오면 같은 기록으로 보고 completed evidence를 유지한다. 완료 폴더에 있다는 증거와 현재 상태 문자열이 terminal이라는 증거를 따로 보존한다.

`terminal-status.ts`는 설정 목록의 마지막 상태를 완료로 취급한다. “Done” 문자열만 하드코딩한 화면은 다른 설정에서 틀릴 수 있다. 이 규칙을 우리에게 그대로 도입하기보다, 완료의 **명시적 의미**를 저장하는 이유로 참고한다. `task-id.ts`의 큰 정수 문자열 정규화도 ID를 JS Number로 바꾸다 충돌시키지 않는 좋은 부품이다.

### 의존성·막힘·순환

`readiness.ts`는 미완료 작업의 모든 직접 dependency가 유일하게 해석되고 완료됐을 때 ready로 판정한다. unresolved dependency와 아직 미완료인 dependency는 설명을 나눠 준다. 완료 작업은 ready도 blocked도 아닌 상태다. 함수는 읽기 projection이고 원문 정렬·상태를 바꾸지 않는다.

`dependency-graph.ts`는 양방향 BFS로 root와 연결된 dependency/dependent를 모으고, missing/ambiguous node는 표시하되 그 뒤를 확정적으로 따라가지 않는다. 같은 node를 반복 확장하지 않는 점과 root cycle 판정은 실행 계획의 루프 방지에 참고할 수 있다. **이번 probe는 상호 의존 순환이며 모든 self-edge·대규모 graph 사례를 보장하지 않는다.**

B01–B06에서 missing blocker, canonical duplicate, completed corpus, 상호 순환, 큰 ID, custom terminal 상태를 실제 upstream 함수로 확인했다. TypeScript는 Node의 transform-types를 사용했고 Bun의 Markdown text import만 문자열로 읽는 loader를 추가했다. 실제 저장소 앱을 띄운 E2E 시험은 아니다.

### snapshot·검색·파일 쓰기

`ContentStore`의 version/epoch와 tasks/docs/decisions 이벤트 인터페이스는 여러 view가 같은 snapshot을 보게 하는 기반이다. 이번 범위는 필드·인터페이스 검토이므로 모든 watcher race가 해결됐다고 주장하지 않는다. `search-service.ts`는 Fuse 기반 lexical/fuzzy 검색을 공통 store와 연결한다. 검색 결과에는 종류가 있고 작업 필터가 별도로 적용된다. 의미 임베딩 검색은 이 경로의 기능이 아니다.

`operations.ts`의 task lock은 같은 작업 수정을 직렬화하고 여러 lock을 정렬해 잡는 경로가 있다. 그러나 본문 저장은 선택 범위에서 `Bun.write` 직접 쓰기를 사용한다. 잠금을 쓴다는 이유로 모든 파일 쓰기가 crash-atomic하거나 여러 파일이 하나의 DB transaction이라고 하면 안 된다. 우리 SQLite 원장을 파일 저장소로 바꾸기보다 **공통 조회 계약·동시 수정 버전·완료 기준 양식**을 취한다.

| 재사용 후보 | 사용자 가치 | 연결 |
|---|---|---|
| 목표·계획·완료 기준 + 구현 메모 | 작업을 다시 열 때 끝내야 할 범위 선명 | OP05, 기존 GitHub 카드 양식 확장 후보 |
| 막힘 이유와 dependency 그림 | “왜 시작 안 하지?”를 바로 설명 | OP04, 완료/누락/중복 구별 |
| task/doc/decision 한 검색창 | 나중에 근거를 다시 찾기 | 이전 D02와 통합; 새 검색엔진 중복 생성 안 함 |
| 여러 표면의 같은 readiness | 앱과 CLI가 다른 상태를 말하지 않음 | controller/store projection 한 곳 |
| ID와 filePath 중복 구별 | 가져오기·다른 branch 자료 혼동 줄임 | 이전 D06의 import conflict preview |

## 3. Gas Town — 배정·작업자·통합의 운영 계층

Gas Town은 Beads 작업 데이터 위에 여러 작업자의 배정, 작업 묶음, 감시, 병합 흐름을 올리는 방향이다. 이름 자체보다 책임을 나눈다: **formula는 절차 형식, convoy는 작업 묶음, capacity는 배정 가능량, polecat은 작업자 수명, refinery는 통합 과정**이다. 이번에는 이 책임들의 선택 경로를 읽었고 전체 배포/daemon을 시험하지 않았다.

### plan → validate → execute → bookkeeping

`scheduler/capacity/pipeline.go`는 pending 후보와 ready ID 집합, capacity, batch limit를 받아 배정 계획/제외 이유를 만든다. message·handoff·merge-request 같은 비작업 항목을 제외하는 정책이 있다. 계획 수립을 실행과 나누면 “지금 실행하면 누가 무엇을 맡나”를 모델 호출 없이 보여줄 수 있다.

`dispatch.go`의 실행은 재검사 뒤 Execute를 호출하고 OnSuccess 후처리를 한다. Execute 성공 뒤 OnSuccess가 실패하면 bounded retry 후 `ErrOnSuccessFailed`로 보고된다. **report.Failed에 있다는 사실이 ‘작업이 시작되지 않았다’를 의미하지 않는다.** 배정 플래그 청소가 실패한 일을 다시 Execute하면 이중 작업자가 생길 수 있다. 우리 OP04는 배정 사실과 후처리 확인을 별도로 남기도록 한다.

### 완료 통지·재사용·안전 중단

`convoy/operations.go`의 완료 연계는 작업 종료 때 묶음의 상태를 확인하고 ready work를 공급하는 event 경로다. “한 작업 닫힘”과 “모든 묶음 산출물이 통합됨”은 다르다. `polecat/workstate.go`는 작업자 상태뿐 아니라 dirty files, stash, unpushed commits, Git 조회 실패, active MR 등을 받아 **Reusable / SafeToNuke / CountsTowardCapacity**를 나누는 pure policy다. idle 하나로 지워도 된다고 하지 않는 점이 핵심이다.

`refinery/safety_stop.go`의 `safety_stop:*`는 operator가 명시적으로 해제하는 durable 표식이다. 참조 작업이 닫혔다고 자동 해제하는 것과 다르다. 우리 실행 실패마다 이런 운영 장치를 추가할 필요는 없지만, 통합 실패를 일반 대기와 구별하는 표시로 보관한다.

### 절차와 작업 중 메시지

`formula/types.go`에는 workflow/convoy/expansion/aspect 구조와 steps/needs/acceptance 같은 항목이 있다. 스키마에 나온 필드를 모두 실행 기능으로 세지 않는다. 특히 `Compose.Aspects`는 reserved future로 표시돼 있다. `pour=false`의 inline step과 materialized checkpoint 차이는 사용자에게 보이는 진행 단계를 모두 별도 작업으로 부풀릴 필요가 없다는 참고다.

`nudge/queue.go`는 터미널에 즉시 키를 집어넣기보다 다음 자연스러운 경계에서 읽을 메시지를 per-session 파일로 쌓는다. 우선순위·TTL·대기열 상한이 있고 drain은 claim rename을 사용한다. 오래된 orphan claim을 다시 queue로 돌리는 코드가 있다. 이 부분의 주석만 읽고 “오래되면 폐기”라고 쓰면 틀린다. enqueue의 direct write와 delivery ack 전체는 별도 검토 대상이다. **정확히 한 번 전달을 보장하는 durable bus로 소개하지 않는다.**

우리의 현재 일반/격리 초안은 고정 입력으로 진행한다. OP07에서는 실행 중 메시지를 먼저 inbox에 보관하고 “다음 단계에 적용”하도록 한다. live CLI가 입력 도중 실제 steering을 지원하는지는 adapter별 관측이 있어야 한다. 메시지를 넣었다고 독립 초안이 자동으로 독립성을 유지하는 것도 아니다.

## 비교 결론을 구현 단위로 옮기기

| 질문 | 주로 참고할 프로젝트 | 다른 프로젝트가 대신 못 하는 것 |
|---|---|---|
| 선행 작업이 끝났는가? | Backlog readiness / Beads ready | claim이나 빈 worker만으로 해결 안 됨 |
| 누가 맡았는가? | Beads CAS | UI의 선택 상태·GitHub label 변경과 다름 |
| 지금 더 실행할 여유가 있는가? | Gas Town capacity | 우리 호출 상한·미확정 슬롯 판정은 별도로 필요 |
| 시작 후 기록만 실패했는가? | Beads verified write / Gas Town post-success failure | 무조건 재시작하면 안 됨 |
| 작업자/폴더를 재사용해도 되는가? | Gas Town workstate | 종료 0·idle만으로 충분하지 않음 |
| 사용자에게 왜 대기인지 어떻게 보여줄까? | Backlog blocker explanation + Gas Town skip reasons | 로그 전체를 읽게 하지 않아도 됨 |

우리 앱에는 이미 호출 cap, unknown/unsettled 슬롯, 취소, 원장 transaction, 고정 입력이 있다. 새 도구를 통째로 가져오기보다 [OP04–OP07](ADOPTION.md)의 데이터·화면 조각을 그 위에 연결할 수 있다.
