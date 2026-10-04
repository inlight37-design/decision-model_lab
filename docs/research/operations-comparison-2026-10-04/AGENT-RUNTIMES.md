# Cline·Lite-Harness·Symphony: 복구·문맥·실행 어댑터

근거는 [고정 소스와 읽은 범위](source-map.json), [직접 실행한 작은 시험](probe-results.json)이다. Cline SDK/VS Code 확장은 서로 다른 코드 표면이며, 제품 문서의 설명을 선택한 SDK 구현 전체의 보증으로 옮기지 않는다. Symphony는 engineering preview reference이고 Lite-Harness는 README에서 preview라고 명시한다.

## 1. Cline — 되돌리기와 긴 작업의 문맥

### checkpoint는 파일·대화·외부 효과를 나눠야 한다

`sdk/packages/core/src/hooks/checkpoint-hooks.ts`의 선택 범위에는 세션별 별도 `GIT_INDEX_FILE`, 작업 폴더+session 식별, snapshot metadata, 오래된 index 정리 기반이 있다. 사용자 index와 에이전트 snapshot 작업을 섞지 않는 발상이다. 이 부분만 읽고 “모든 tool마다 snapshot”이라고 주장하지 않는다. `docs/core-workflows/checkpoints.mdx`는 제품 checkpoint와 shadow Git, 파일/대화 복구 선택을 설명하지만 trigger와 저장 방식은 사용하는 제품 표면에 따라 다시 확인해야 한다.

`session/checkpoint-restore.ts`의 transaction 시작 경로는 복구 전 상태를 stash에 캡처하고 private ref로 보존한 뒤 사용자 stash 목록에서는 제거한다. commit은 rollback용 private ref를 정리하고, rollback은 이전 HEAD/작업 트리와 index를 되살리려 한다. rollback 자체 실패도 합쳐 보고하는 경로가 있다. 성공 뒤 ref 청소 실패를 사용자 작업 실패로 바꾸지 않는 점은 Gas Town의 후처리 경계와 비교할 수 있다.

이 조각은 실제로 `reset --hard`, `clean`, stash apply를 사용할 수 있는 **파일 변경 기능**이다. 이번에는 실행하지 않았다. tracked/untracked, ignored file, submodule, 사용자 동시 변경, 외부 DB/API 쓰기까지 한 버튼으로 복구된다고 말할 근거는 없다. 대화 DB와 파일 복원의 전체 transaction도 이번 선택 범위 밖이다.

**우리 후보:** 먼저 “이번 실행의 입력·답변·검토 판 비교”와 실행 fork를 만든다(OP06). 파일 수정형 역할을 도입할 때만 worktree checkpoint를 붙이고 복구 전 preview와 preimage를 보존한다. 원장 과거를 덮어쓰거나 이미 사용된 호출 budget을 복구 전으로 되감지 않는다.

### 압축은 정상 관리와 overflow 복구가 다르다

`compaction-shared.ts`에는 기본 입력 상한, usable/trigger/target 비율, 최근 문맥 보존량, tool result 길이 제한, 모델 metadata의 max input clamp가 있다. 이 값은 선택 commit의 휴리스틱이며 우리 모델에 대한 최적값이 아니다. 문자를 잘랐다는 사실만으로 token 한도를 증명할 수 없다.

`compaction.ts`는 메시지뿐 아니라 system prompt와 tools가 만드는 overhead도 추정한다. `overflowRecovery`에서는 정상 agentic summary와 다른 recovery mode를 선택한다. 선택한 분기에서 custom compactor에 먼저 기회를 주되, 실패·거절·충분히 작아지지 않은 결과라면 deterministic basic 경로를 쓰도록 설계돼 있다. 이미 context overflow가 난 상태에서 요약용 모델 호출도 같은 이유로 실패할 수 있기 때문이다. 이번에 그 분기의 모든 helper 또는 모델 동작을 실행 검증한 것은 아니다.

**우리 후보:** 현재 기억 pack의 hash·UTF-8 바이트 상한을 유지하면서 실제 입력 구성과 삭제 후보를 보여준다(OP08). API 토큰 추정과 native CLI 내부 문맥을 동일시하지 않는다. CLI 소유 대화를 마음대로 잘라 전송할 수 있는지도 먼저 adapter별로 확인해야 한다. 압축 전 원문, 보존 조건, 삭제 사유를 남기고 격리 초안에는 다른 역할의 중간 메시지를 넣지 않는다.

### 규칙 적용 이유와 stale context

VS Code 쪽 `rule-conditionals.ts`는 경로 조건에 picomatch를 쓰고 matched condition을 돌려주는 구조다. 빈 배열, candidate 없음, 잘못된 조건 타입이 서로 다르게 처리된다. 선택 범위에서는 unknown 조건 key를 무시하고 잘못된 타입에 fail-open인 경우가 있어, 규칙 형식을 조금 잘못 썼다고 안전 장벽이 생기는 구조는 아니다. 편의 규칙의 적용 범위를 권한 enforcement와 혼동하면 안 된다.

`FileContextTracker.ts`는 agent가 읽은 뒤 외부에서 변경된 파일을 stale로 표시하기 위한 상태/감시 인터페이스를 갖는다. 파일 watcher의 모든 race나 자동 재독해를 검증하지 않았다. 우리에서는 자료 hash 변경, 템플릿 갱신, 검색 인덱스 stale 표시와 연결할 수 있다. **“이 규칙/자료가 왜 들어갔나”와 “읽은 뒤 바뀌었나”**는 D01/D07/OP10의 유용한 UI 조각이다.

## 2. Lite-Harness — 공통 모양과 의미 보존의 차이

**구조:** Python SDK transport/query → NDJSON server protocol → Session → provider runtime → provider event transformer. 공통 protocol에 맞추면 client 코드 재사용은 쉬워지지만, provider가 지원하지 않는 동작까지 지원되는 것은 아니다.

### 상태 소유와 제어 메시지

`session.mjs`는 process-local session ID, turn count, history, hooks/MCP 설정을 소유한다. `initialize`, `interrupt`, permission/model 변경 등 control을 runtime에 전달하고 user turn을 감싼다. `protocol.mjs`는 request ID로 제어 응답을 결속하고 한 active turn 동안 다른 turn을 거절하는 구조다. malformed JSON은 stderr에 남기고 무시한다. durable 원장이나 프로세스 재시작 후 세션 복원이 이 코드에서 자동 제공되지는 않는다.

`providers/codex/index.mjs`는 선택판에서 SDK의 새 thread를 매 runTurn에 만든다. Session이 history를 가지고 있어도 이 provider가 그 history를 이전 thread로 이어 쓰는 것과 같지 않다. `setPermissionMode`가 no-op인 점도 공통 setter의 존재와 실제 capability를 나눠야 하는 이유다. LiteLLM base URL/key를 주입할 수 있는 gateway/API 경로를 현재의 구독 전용 official CLI 인증 경로와 동등하게 취급하지 않는다.

### 직접 확인한 결과 변환 경계

| probe | 입력/관측 | 의미 |
|---|---|---|
| L01 | `resultFrame` 기본 `success`, usage `{}`, cost `0` | 미관측 비용을 무료로 계산할 수 없음 |
| L02 | 모르는 launch flag 무시, text 변환에서 image 내용 빠짐 | 인자를 받았다는 것과 반영했다는 것 다름 |
| L03 | 아무 frame도 내지 않은 가짜 runtime이 빈 success result를 받음 | 종결 frame이 생겨도 유효 답변·실행 성공 증명 아님 |
| L04 | 가짜 runtime의 throw는 error result로 변환 | 예외 경로와 정상 iterator 종료의 의미가 다름 |
| L05 | Codex transformer가 `turn.failed`/usage event를 빈 배열로 변환 | 알려지지 않은/미지원 event 보존 정책 필요 |
| L06 | 누적 text의 suffix delta + completed의 전체 text | 미리보기 delta와 최종 답변 중복 결합 주의 |

실제 Codex SDK나 네트워크를 부르지 않았다. 따라서 L03을 실제 모든 취소 호출이 성공으로 보고된다는 E2E 결과로 부풀리면 안 된다. 다만 runtime의 silent return 경로와 Session fallback의 조합은 어댑터 검토에서 반드시 시험할 경계다.

Python `query.py`는 자신이 만든 transport인지에 따라 close 소유권을 나누며 result까지 읽는다. `transport.py` 선택 범위에는 subprocess EOF/pending response 처리와 terminate→wait→kill이 있다. parent 프로세스를 기다렸다는 사실이 우리 whole-tree 종료 증명을 충족하지는 않는다. `decode.py`는 모르는 message를 SystemMessage 형태로 남기는 반면, 모르는 content block이 그대로 모두 보존되는 것은 아니다.

**재사용할 것:** 공통 envelope, control request correlation, provider metadata/capability 표, stream과 result 분리. **독자 계약이 필요한 것:** 최종 outcome, 입력 전달 확인, 알려지지 않은 usage, native permission 적용 관측, 취소와 프로세스 tree, context origin. [OP09](ADOPTION.md)에 필드별 변환표와 시험을 제안했다.

라이선스는 Python pyproject가 MIT라고 선언하지만 이 고정판의 tracked 파일에서 LICENSE/COPYING을 찾지 못했다. 코드 복사에 필요한 고지/허여 범위는 미확정으로 기록한다. 이번에는 링크·소스 읽기·함수 호출 probe만 했고 upstream 코드를 우리 runtime에 복사하지 않았다.

## 3. Symphony — repository workflow를 실행하는 조정자

**구조:** workflow 파일을 load/validate → tracker 후보 조회 → 기존 running/blocked 상태 reconcile → global/state/worker slot 확인 → issue별 workspace → Codex App Server turn → tracker 재확인 → 후처리/재시도. 선택 source는 Elixir reference이며 SPEC의 모든 요구를 구현 검증한 것은 아니다.

### 매번 새 배정보다 먼저 현재 실행을 맞춘다

`orchestrator.ex`의 dispatch 경로는 실행 중/blocked 상태를 먼저 reconcile한다. tracker 조회가 실패했을 때 이미 도는 worker를 무조건 새로 시작하지 않는다. terminal 상태는 cleanup을 포함한 종료 경로로, 라우팅 불가능/활성 상태 변경은 다른 종료·갱신 경로로 간다. issue가 active인가, 이미 claimed/running/blocked인가, 슬롯이 있는가를 각각 확인한다.

running/claimed/retry 등은 선택 구현의 조정자 메모리 상태다. durable exactly-once queue라고 할 수 없다. 작업별 workspace와 tracker 상태가 있다고 해서 서버 crash 직전 시작 여부까지 자동 확정되는 것은 아니다. 우리에는 SQLite 원장과 `_recover`가 있으므로 이 기반 위에서 재시작 시 재조회와 새 실행 생성의 순서를 정한다.

### 재시도는 ID와 세대가 있어야 한다

retry scheduling은 이전 timer를 취소하고 새 token/reference와 monotonic due time, attempt, workspace/host 등 metadata를 붙인다. 늦게 도착한 이전 timer를 현재 재시도로 처리하지 않는 패턴이다. continuation과 failure retry의 지연 정책도 구별한다. 이를 우리 재시도 후보에 적용할 때 모델 호출 cap을 초기화하거나 `unknown`을 무조건 ready로 바꾸면 안 된다.

### workflow reload와 workspace 경계

`workflow_store.ex`는 경로/mtime/size/content hash를 확인하고 새 파일을 load/validate한 다음 상태를 교체한다. reload 오류는 이전 정상 상태를 유지하며 오류를 돌려준다. 첫 시작에 유효 설정이 없는 경우와 운영 중 잘못 저장된 파일의 경우가 다르다. 사용자가 편집하다 잠깐 불완전한 파일을 저장해도 기존 실행 설정을 잃지 않는 좋은 편의다.

`workspace.ex`는 issue별 경로를 만들고 검증한 뒤 새 폴더일 때 after-create hook을 수행한다. runner는 before-run, App Server session/turn, tracker refresh, after-run/finally cleanup을 구분한다. `path_safety.ex`의 경로·symlink 정규화는 디렉터리 탈출 방어의 부품이지 OS 격리 자체가 아니다. hook 명령은 별도의 부작용 표면이다.

**우리 후보:** 버전/hash가 있는 workflow/template와 마지막 정상 설정 유지(OP10), 기존 실행 reconcile과 재시도 세대(OP04), 작업자별 host/workspace 표시(OP12). 새 설정을 이미 고정된 실행 입력에 소급 적용하지 않는다. Linear나 Symphony 서버를 설치할 필요 없이 적용할 수 있는 부품이다.

## 세 프로젝트에서 골라 쓸 순서

| 먼저 만들 수 있는 조각 | 나중에 실측/통합이 필요한 조각 |
|---|---|
| capability 표와 raw/normalized 결과 대조 | provider SDK 또는 native CLI의 실제 auth/permission/context |
| snapshot 비교와 새 실행 fork 미리보기 | Git 작업 트리 복원·동시 변경·외부 부작용 |
| 입력 크기/보존 부분/압축 후보 설명 | 실제 context 한도, 요약 품질, 추가 호출 총비용 |
| workflow 검사·version·last-good 표시 | hook 실행과 worker 재시작 운영 |

이 구분은 기능을 빼기 위한 것이 아니라, 클라우드에서 지금 끝낼 수 있는 부분과 PC·모델 관측으로 확정할 부분을 분리하기 위한 것이다.
