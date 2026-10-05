# 작업 흐름·화면·다음 구현 검토

검토 기준: **`48ab4bd6f0e297587707aecb83ebc0cd9968892f`**. 이 문서는 2026-10-05의 코드 독해와 임시 합성 원장 관측이다. 사용자 PC·WSL·실제 CLI·모델 품질·실제 브라우저는 관측하지 않았다. 제품 코드, 기존 날짜 기록, 실행 원장은 변경하지 않았다. 아래 GitHub 링크는 모두 기준 SHA에 고정했다.

## 1. 결론과 우선순위

**현재 구조는 일반 팀원 검토를 덧붙일 수 있을 만큼 책임이 나뉘어 있다. 새 오케스트레이션 프레임워크를 먼저 넣을 이유는 확인하지 못했다.** 입력 고정, 단일 원장의 명령/조회, 공통 실행, 공개 projection, 사람 판단을 유지하면서 일반 검토의 세로 경로를 완성하는 것이 낫다. 다만 사용자가 작업을 오래 이어 가려면 **원장 교체 때의 작업 맥락 보존**, **진행 중 입력 준비 복귀**, **응답 유실 뒤 이미 수락한 명령 찾기**가 기능 확대와 함께 해결되어야 한다.

| 항목 | 판정 | 우선순위 | 사용자에게 달라질 것 |
|---|---|---|---|
| WF-01 원장 수명과 작업 수명의 결합 | 현재 정책·코드로 확인한 구조적 제한. 데이터 삭제 결함은 아님 | P1 | 호출 예산을 새로 열어도 이전 작업·기억·템플릿을 찾아 이어 감 |
| WF-02 닫거나 새로고침한 입력 준비의 복귀 | 기존 기록은 남지만 accepted 다듬기·분담의 UI 재선택 경로 부재를 확인 | P1 | 이미 사용량을 써 받은 제안을 다시 호출하지 않고 검토·승인 |
| WF-03 페이지 응답의 미연결 준비 전문 | 합성 원장으로 응답 크기 재현. 기존 페이지·캐시를 부정하는 지적 아님 | P2 | 홈 polling이 이전 다듬기 전문을 반복 전송하지 않음 |
| WF-04 수락된 명령의 재식별 | 동시 중복 방어는 있음. 응답 유실 후 재조정 계약은 경로별로 다름 | P1, 새 GR 명령부터 | 네트워크 오류를 보고 같은 모델 작업을 새로 호출하는 혼동 감소 |
| GR-1 일반 검토 | 현 설계에 구현 위치·실패 조건이 잘 정리됨. 아직 미구현 | P1 | 분담 답 사이의 충돌·빠진 조건을 같은 작업에서 검토 |
| GR-2 수정·재검토, GR-3 선택 판 취합 | 단계 도입 권고. 자동 전체 반복은 효과 검증 뒤 | P1/P2 | 어떤 지적을 반영한 어느 답으로 판단했는지 추적 |

검토 범위에서 **봉인 누출, 무조건 상태 변경에 의한 CAS 우회, 이미 있는 페이지화의 부재, 이미 있는 hash 검사의 부재를 확정 결함으로 발견한 것은 아니다.** 이 절의 P1/P2는 사용자 효용과 구현 순서를 나타내며 취약점 등급이 아니다.

## 2. 이미 갖춘 기반 — 유지할 것

| 경계 | 실제 구현·근거 | 검토 판단 |
|---|---|---|
| HTTP 제어권 | `make_handler._guard`: Host·Origin·Bearer 확인. `_read_json`: 명확한 본문 길이·JSON·크기 제한. `_Server`: 연결 수·I/O 기한 제한. [server.py L147–205](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/server.py#L147-L205), [L471–497](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/server.py#L471-L497) | localhost라는 이유만으로 열린 제어 API라고 평가하면 틀림 |
| 입력과 실행 연결 | `InputBuilder`의 manifest hash, `WorkService.create_run`의 재검사·같은 run ID 중복 거절·계획/선행 근거 재검사·승인 사용 CAS. [inputs.py L150–190](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/context/inputs.py#L150-L190), [work.py L24–80](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/work.py#L24-L80) | 미리보기에 실린 입력이 바뀌면 새 확인 필요. 단순 더블 클릭이 곧 중복 실행이라는 주장은 부정확 |
| 계획 편집과 선행 작업 | `TaskService.save`의 revision CAS·순환/존재 검사·active/unknown 편집 차단. `require_ready`는 공개 캐시를 사용하지 않고 현재 상태를 다시 읽음. [tasks.py L14–92](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/tasks.py#L14-L92) | 계획 저장을 작업 완료나 모델 실행 권한으로 사용하지 않음 |
| 템플릿 복원 | 설정 필드 allowlist, 현재 카드/모델 binding 검증, payload hash, hash 조건부 삭제. 실행·승인·소비 복사 금지. [templates.py L24–124](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/templates.py#L24-L124) | 복원은 편집 초안이고 새 입력 확인이 필요하다는 계약이 적절함 |
| 공개 projection | 격리 공개 전 허용 필드만 노출하며 원문·길이·digest·usage 등 제외. 일반 팀원은 모드에 맞춰 도착한 답을 공개. [public.py L141–235](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L141-L235) | 격리와 일반의 서로 다른 공개 의미를 유지해야 함 |
| 목록 페이지·조회 캐시 | cursor의 scope/시각/ID 검증, 같은 시각 tie 처리, 페이지 밖 선택 상세, DB/runtime 변경 무효화, 거래 내부 projection 비캐시. [pages.py L12–123](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/pages.py#L12-L123) | 페이지에 보이는 실행만으로 완료·선행 상태를 계산하지 않음 |
| 늦은 응답 | 공통 `LatestRequest`, preview 세대, 조회 순번·현재 browse URL 비교. [api.js L15–37](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/api.js#L15-L37), [role-board.js L49–53](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L49-L53), [index.html L1270–1302](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/index.html#L1270-L1302) | 이미 세대 방어가 존재. 남은 문제는 수락된 명령의 복귀 경로와 준비 기록의 수명 |
| 사람 판단 | 현재 결과 revision 검증, 검토/수정/합성 running·unknown 차단, 같은 판 중복 사건 억제. [reviews.py L214–246](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/reviews.py#L214-L246) | 버튼이 보인다는 이유로 진행 중 판단이 실제 수락된다고 추정하면 안 됨 |

## 3. 현재 사용자 여정과 다음 접점

| 단계 | 현재 가능한 일 | 실제 코드와 다음 접점 |
|---|---|---|
| 계획 | 제목·목표·완료 기준·선행 작업을 저장하고 새 판으로 편집 | [workflow.js L3–66](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/workflow.js#L3-L66). 이미 계획 UI가 있으므로 새 보드 제품을 겹쳐 넣을 필요가 작음 |
| 입력 준비 | 원문 또는 슈퍼바이저 다듬기, 역할/모델, 자료, 일반 과제 배정, 분담 제안, 템플릿 | [role-board.js L106–208](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L106-L208), [L230–346](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L230-L346). 실행 전 준비의 복귀가 약함(WF-02) |
| 입력 확인→실행 | 자료 사본과 역할별 전달문, 예상 호출 수, 기억·계획 근거를 확인한 뒤 시작 | [index.html L732–769](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/index.html#L732-L769), [role-board.js L440–514](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L440-L514). 생성 성공 이후 조회 실패는 재실행으로 처리하지 않음 |
| 결과 수집 | 격리: 봉인 후 공개/정족수. 일반: 팀원별 과제·자료를 받고 도착대로 공개, 정리 후 collected | [roles.py L12–73](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/roles.py#L12-L73), [public.py L162–218](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L162-L218) |
| 검토·수정 | 격리 공개 뒤 교차검토와 원래 작성자의 수정·다른 작성자 재검토. 일반은 원래 답 취합까지 | [reviews.py L84–141](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/reviews.py#L84-L141), [role-board.js L707–733](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L707-L733), [revisions.js L44–70](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/revisions.js#L44-L70). GR-1/2가 명확한 기능 공백 |
| 취합·판단 | 일반은 과제+원래 답을 취합 모델에 보내고, 사용자는 메모와 판단 완료를 기록. 격리는 공개 답/합성 판단 | [reviews.py L26–73](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/reviews.py#L26-L73), [index.html L1046–1064](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/index.html#L1046-L1064). GR-3 전에는 수정 판을 취합했다고 표시할 수 없음 |
| 다음 일 | 같은 작업에 새 실행, 격리 슈퍼바이저 제안으로 새 입력 준비, 내 차례/선행 의존성 이동 | [role-board.js L608–647](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L608-L647), [L735–752](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L735-L752), [workflow.py L47–148](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/workflow.py#L47-L148). 자동 실행은 현재 사용 방식의 필수 요소가 아님 |

### WF-01. 새 호출 예산을 열 때 사용자 작업까지 바뀌는 경계

**확인한 동작.** 데스크톱 입구는 가장 새 원장에 모든 provider의 잔여가 있어야 재사용한다. 하나라도 소진되면 다음 시작에서 새 원장 폴더를 선택한다. 기본 `CAPS`는 provider별 5이다. 이 정책은 주석에도 명시되어 있고 기존 원장 파일은 지우지 않는다. [launch.py L18–20](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/launch.py#L18-L20), [L58–60](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/launch.py#L58-L60), `_has_room`/`pick_ledger` [L190–224](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/launch.py#L190-L224).

그러나 `serve`는 고른 원장 하나로 서버를 연다. 작업·계획·템플릿·공개 검색·기억은 그 Store 안의 행으로 이루어진다. 그러므로 기본 앱을 닫았다 열었을 때 예산 교체가 발생하면, 이전 작업이 삭제되지는 않아도 화면에서 읽는 작업 집합과 기억 범위는 바뀐다. 특히 한 provider가 먼저 다 찼을 때 다른 provider의 잔여와 관계없이 작업 맥락이 끊기는 점을 사용자가 이해하기 어렵다. [launch.py L303–345](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/launch.py#L303-L345), [public.py L75–139](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L75-L139), [tasks.py L28–70](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/tasks.py#L28-L70).

**추가 복구 경계.** `_has_room`는 cap과 reservation만 읽고 이전 원장의 unknown을 판정하지 않는다. 선택된 원장 밖의 미확정 시도가 새 원장의 gate에 자동으로 들어오는 경로는 이 입구에서 확인되지 않았다. 이를 **총 호출 상한 위반**, **동시에 두 서버가 뜸**, **실제 고아 프로세스 생존**으로 확대 해석하지 않는다. 원장별 cap 갱신은 현재 의도된 정책이고 launcher 소유 잠금도 존재한다. 실제 프로세스가 남았는지는 PC 실측 범위다. [launch.py L190–224](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/launch.py#L190-L224), [L275–288](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/launch.py#L275-L288).

**최소 개선.** 먼저 현재 원장 이름·예산 잔여와 이전 원장 읽기를 사용자 작업 관점에서 연결한다. 다음 단계로 장기 `workspace/task`와 짧은 `budget_epoch`를 분리하는 설계를 선택한다. 이것은 소비 기록을 지우거나 기존 상한을 높이는 변경이 아니다. 새 epoch는 새 명시적 예산이고 기존 호출은 원래 epoch에 남아야 한다. 과거 공개 자료를 사용할 때는 선택한 출처와 고정 사본을 남기며, 봉인 답과 미확정 결과는 기억 후보로 들이지 않는다.

**완료 조건.** 한 provider 소진→정상 종료→재시작 뒤에도 이전 작업을 찾고 새 예산에서 이어갈 수 있으며 이전 소비와 새 소비를 별도로 볼 수 있다. 예산을 바꾸기 전에 호스트에서 아직 정리하지 않은 실행을 찾을 수 있다. 기존 unknown을 새 원장 선택으로 해결된 것처럼 표시하지 않는다. 기존 원장 전체를 새 원장에 복사해서 소비/승인 의미를 바꾸지 않는다.

### WF-02. 받은 다듬기·분담을 화면에서 다시 고를 수 없다

**확인한 동작.** 다듬기의 현재 ID와 승인 차례, 분담의 현재 ID·적용 여부·File 객체는 브라우저 메모리에만 있다. `resetRefine`와 `resetSplit`이 이를 지우고 `openNewRun`은 초기화를 호출한다. 서버는 미연결 준비 기록을 보관하고 최근 결과 및 running/unknown을 내보낸다. 하지만 정상 완료한 기존 다듬기/분담을 홈에서 골라 `refineCurrent`/`splitCurrent`로 되돌리는 경로는 없다. 수신함의 미연결 입력 항목과 홈의 별도 다듬기 항목은 unknown 종료 확인만 제공한다. [role-board.js L108–147](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L108-L147), [L232–252](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L232-L252), [L295–321](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L295-L321), [index.html L1319–1332](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/index.html#L1319-L1332), [public.py L288–309](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L288-L309), [workflow.py L151–163](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/workflow.py#L151-L163).

**영향.** 사용자가 다듬기를 요청하고 새로고침하거나 작성 창을 닫았다 새로 열면, 이미 받은 답은 DB에 있어도 앱에서 그 작업을 이어 승인하기 어렵다. 통신 성공 응답에서 ID를 못 받은 경우에도 유사하다. 현재 코드의 늦은 응답 무시 자체는 맞는 방어다. 새 창에 옛 결과를 덮어쓰는 방식으로 고치면 안 된다.

**최소 개선.** 읽기 전용 `입력 준비 기록` 목록을 두고, 사용자가 고른 기존 ID를 편집 창에 명시적으로 복원한다. 먼저 읽기와 재선택을 완성한 다음 필요하면 작성 중 과제/자료 선택을 저장한다. 복원 시 현재 모델·role binding·작업 계획·자료 hash를 재검사하고 승인 차례는 사용자가 다시 선택하게 한다. 새 실행은 항상 새 manifest 확인을 거친다. 템플릿의 재검증과 승인 비복사 계약을 재사용할 수 있다. [templates.py L24–65](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/templates.py#L24-L65).

분담 복원에는 옛 `File` 객체를 억지로 재사용할 수 없다. 서버에 저장한 자료 사본과 hash로 새 편집용 File을 만들고, 그 배정이 어떤 제안에서 왔는지 별도 포인터를 유지해야 한다. 단순 파일 이름 일치로 복원하면 현재 `splitMatchesNow`가 지키는 내용 동일성보다 약해진다. [role-board.js L240–263](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L240-L263), [planning.py L174–202](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/planning.py#L174-L202).

**완료 조건.** 요청 직후 새로고침, 응답 수락 뒤 창 닫기, 서버 재시작, 현재 명단 변경, 자료 변조를 각각 구분한다. 기존 수락 결과는 추가 모델 호출 없이 찾을 수 있고, unknown은 기존 종료 확인 규칙을 따른다. 한 준비 기록을 두 실행에 쓰려는 시도는 기존 `used_by`/`run_id` CAS에서 거절한다.

### WF-03. 목록 페이지를 작게 해도 미연결 준비 전문은 계속 전송된다

**확인한 동작.** `BrowserPages._snapshot`은 `overview()`를 캐시하며 `browse`가 작업·타임라인·수신함을 페이지로 자른다. 그러나 응답은 `{**snapshot, ...}` 형태여서 snapshot의 `refinements`와 `splits`는 그대로 유지한다. `overview`의 `_summary=True` 경로도 미연결 준비 조회에서는 `_refinement_view(row)`와 `_split_view(row)`를 전문으로 호출한다. [pages.py L71–123](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/pages.py#L71-L123), [public.py L288–311](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L288-L311), [L431–453](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L431-L453).

**이 세션의 합성 재현.** 원문은 `검토`를 3,900번 반복한 7,800자이며, 기존 `test_refine_mode.Refiner` 합성 실행기로 각 준비의 한 차례를 accepted로 만들었다. 모두 `use_memory=False`, 작업에 미연결, 실제 모델 호출은 없다. 기본 앱의 provider별 호출 크기와 비교할 수 있게 작은 경우를 함께 측정했다. 기준 SHA `48ab4bd6f0e297587707aecb83ebc0cd9968892f`에서의 값이다.

| 합성 원장 | `/browse(limit=1)` JSON 바이트 | 그중 refinements | 작업/수신함 | warm 응답 |
|---|---:|---:|---|---:|
| 빈 원장 | 598 | 빈 목록 | 모두 없음 | 별도 측정 안 함 |
| 미연결 다듬기 5건, 각 1차례 | 243,145 | 242,549 | 모두 없음 | 243,145 |
| 미연결 다듬기 20건, 각 1차례 | 970,792 | 970,196 | 모두 없음 | 970,792 |

큰 경우는 기본 단일 live 원장의 한 provider cap을 넘긴 **조회 스트레스 입력**이며 그만큼의 실제 사용자가 이미 있다고 주장하지 않는다. 작은 경우도 모두 임시 합성 결과다. 측정 JSON은 서버와 같은 `json.dumps(..., ensure_ascii=False).encode('utf-8')`의 길이다. HTTP/브라우저 전송 시간·메모리·실제 latency를 측정한 것은 아니다.

warm projection 호출 자체는 작은 경우 약 0.15 ms, 큰 경우 약 0.44 ms로 이 컨테이너에서 빨랐다. 따라서 이 결과로 캐시가 효과 없다고 결론 내리면 안 된다. 문제는 캐시 뒤의 JSON 직렬화·전송·클라이언트 파싱 바이트가 줄지 않는 것이다. 기본 화면은 1초마다 상태를 조회하고, refresh가 아직 진행 중일 때만 해당 타이머 조회를 건너뛴다. account quota 자동 추가 조회의 visibility 방어와 달리 상태 polling 자체에는 hidden 조건이 없다. [index.html L1270–1294](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/index.html#L1270-L1294), [L1362–1370](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/index.html#L1362-L1370).

**최소 개선.** WF-02의 준비 목록은 ID·원문 짧은 제목·state·task·시각·현재 차례만 반환한다. 열어 본 준비 하나의 상세만 별도 조회하거나 선택 ID로 응답에 넣는다. 기존 공개 allowlist를 그대로 사용하고 DB/runtime 변화는 기존 cache key로 무효화한다. 먼저 불필요한 본문 전송을 줄인 뒤 idle/hidden polling 간격을 늘릴지 측정한다. SSE/웹소켓/별도 이벤트 서버는 그 다음에도 이득이 분명할 때 검토한다.

검색 역시 이미 task 필터를 먼저 적용하고 질문/자료 종류는 답 본문을 읽지 않는다. 전체 답 검색은 아직 공개 projection의 선형 순회이며 한도는 반환량의 한도다. 이는 알려진 비용과 일치한다. 초기에 문구/작업 필터를 잘 드러내고, 실제 원장에서 검색이 느린 것이 확인되면 공개 결과의 FTS index를 추가하는 순서가 낫다. 봉인 DB 전체를 곧바로 색인하는 방식은 이 구조의 장점을 잃는다. [public.py L75–92](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L75-L92), [catalog.py L19–78](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/catalog.py#L19-L78).

### WF-04. 동시 중복 방어와 응답 유실 뒤 복귀는 별개다

| 명령 | 현재 방어 | 남은 사용자 복귀 문제 |
|---|---|---|
| 실행 생성 | preview의 고정 run ID·confirmation, 기존 ID 거절 | 서버가 수락했으나 POST 응답이 끊기면 UI는 오류를 보여 줌. 같은 run ID 조회로 이미 만든 실행에 연결할 수 있지만 자동 복귀는 없음 |
| 수정 시작 | preview의 고정 revision ID·confirmation, 버튼 일회성 | 오류 후 버튼은 비활성이고 새 preview를 요구. 먼저 기존 revision ID 존재를 읽어야 재호출 혼동을 줄일 수 있음 |
| 계획 편집 | 예상 revision CAS | 충돌은 재조회로 해결 가능. 자동 재전송하지 않는 현재 방향 유지 |
| 새 계획·템플릿·첫 다듬기·분담 | 새 서버 UUID, 상위 호출 gate·전역/provider cap | 같은 payload가 나중에 재전송되면 새로운 의도로 취급될 수 있음. 동일 요청과 사용자가 명시적으로 한 번 더 누른 일을 구별할 영수증은 없음 |
| 검토 라운드 | 한 실행에 한 라운드, 저장·시작 상태 조건 | 새 GR preview에 round ID가 생기면 존재 확인과 동일 확인 재전송의 응답 계약을 함께 정하는 것이 효율적 |

근거: [work.py L24–47](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/work.py#L24-L47), [role-board.js L495–514](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L495-L514), [revisions.js L16–34](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/revisions.js#L16-L34), [planning.py L28–89](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/planning.py#L28-L89), [L159–203](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/planning.py#L159-L203), [reviews.py L96–141](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/reviews.py#L96-L141).

임시 합성 검사에서 같은 원문으로 첫 다듬기를 순차 요청하면 각 요청에 서로 다른 ID가 생성되었다. 이는 현재 메서드 계약대로이며 **자동 retry가 이미 존재한다거나 실제로 중복 과금됐다는 재현은 아니다.** 통신이 끊긴 뒤 사용자가 동일 명령을 다시 실행할 수 있으므로 복귀 계약을 제안하는 것이다. 현재 `createAPI`는 자동 재전송을 하지 않는다. [api.js L15–25](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/api.js#L15-L25).

**최소 개선.** 이미 고정 ID가 있는 실행·수정·GR 라운드는 그 ID의 조회를 우선한다. 생성 명령이 더 늘어나면 한정된 `command_id + canonical payload hash → resource ID + acceptance state`를 같은 거래에 기록한다. 같은 ID/다른 payload는 충돌, 같은 ID/같은 payload는 원래 자원을 반환한다. 결과 응답 캐시는 공개 projection을 통해 현재 안전한 상태만 반환한다. 명령 영수증은 native provider가 정확히 한 번 실행되었다는 보장과 다르며, unknown에서 새 CLI를 자동으로 부르면 안 된다.

공통 전송 오류에 status/code/resource ID를 보존하면 UI가 입력 오류, 오래된 판, 이미 수락한 명령, 수락 여부 미확인을 구분할 수 있다. 기존 오류 거절을 없애거나 모든 실패를 재전송하는 수단으로 사용하지 않는다. `server.py`의 현재 POST 오류 분기와 `api.js`의 Error 변환이 이 변경의 작은 접점이다. [server.py L463–466](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/server.py#L463-L466).

## 4. GR 설계와 실제 코드의 대조

현재 [일반 팀원 검토 설계](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/architecture/general-team-review/README.md#L18-L34)는 변경 지점을 잘 짚었다. 서비스의 general 거절 조건만 없애서 구현했다고 하면 공개 조회·작업 완료·보고서가 어긋난다. **설계를 다시 대형 문서로 쓰기보다 현재 설계의 완료 조건을 그대로 구현 카드로 옮기는 것이 낫다.**

| 구현 지점 | 기준 코드에서 확인한 차단/현재 의미 | GR에서 지켜야 할 변경 |
|---|---|---|
| `ReviewService.cross_review` | `current_gate.general or not revealed` 거절. 입력은 같은 질문에 대한 자기 답/다른 답 | 일반 collected의 accepted 원래 CLI 작성자만 허용하고 각 과제·자료 메타데이터를 답과 같은 label에 결속 |
| `PublicQueries.view` | 검토·수정·다음 단계·격리 합성이 하나의 `if revealed` 안에 위치 | 검토·수정만 일반 collected 분기로 분리. 일반이 격리 합성/정족수 자격까지 얻지 않게 함 |
| `_general_status` | 참여자 상태·취합만 반영 | 새 review/revision/recheck queued/running/unknown을 판단 완료보다 먼저 표시 |
| `workflow.steps` | 입력으로 받은 review/revision/recheck 상태는 이미 공통 단계에 반영 | 새 객체가 summary와 detail에 모두 도달하도록 연결. 다른 완료 DB 만들지 않음 |
| `mark_reviewed` | 모든 역할의 진행/미확정을 이미 차단하고 결과 revision 확인 | 그대로 재사용하고 일반 라운드/새 판에도 회귀 확인 |
| UI | `crossReviewIsland`와 `revisionIsland`는 일반을 제외 | 일반 전용 문구·입력 확인, 모드에 맞는 상태/보고서 제공 |

근거: [reviews.py L84–141](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/reviews.py#L84-L141), [public.py L243–269](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L243-L269), [roles.py L160–178](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/roles.py#L160-L178), [workflow.py L24–44](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/workflow.py#L24-L44), [reviews.py L223–246](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/reviews.py#L223-L246).

### 구현 단위 GR-1: 미리보기부터 내 차례까지 한 경로

일반 검토의 사용 장면은 서로 다른 일을 한 작성자 사이의 충돌 확인이다. 따라서 전체 목표·검토 질문·자기 과제/답·상대 과제/답/hash·각자의 자료 접근 범위·실패한 팀원의 누락을 미리보기와 저장 입력 모두에 넣어야 한다. 자료 이름/hash가 있다는 이유로 검토자가 그 원문을 읽었다고 표시하지 않는다. 현재 설계의 frozen manifest와 nonce/hash 확인을 재사용하고, 모드별 prompt builder를 순수 함수로 둔다. [설계 L55–78](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/architecture/general-team-review/README.md#L55-L78).

GR-1은 기존 `REVIEW_SEAT`와 순차 배정을 사용한다. 앞 검토자 실패로 뒤 검토자가 skipped 된 것을 지적 없음으로 표시하지 않는다. 작업·내 차례·선행 준비가 새 검토를 보도록 summary와 detail을 같은 PR에서 연결한다. **새 review 엔진, 영속 inbox 상태, 대기열 서버는 필요 없다.** [reviews.py L144–185](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/reviews.py#L144-L185), [설계 L80–88](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/architecture/general-team-review/README.md#L80-L88).

추가할 회귀는 추상 단위 테스트보다 실제 사용자 전이 중심이 낫다. 이미 사람이 판단한 일반 결과에서 검토 시작→페이지 밖으로 이동→queued/running→unknown 또는 새 accepted 결과→옛 revision으로 판단 시도→현재 결과 재조회까지 확인한다. 이는 단계별 체크리스트를 복제하는 목적이 아니라 **작업 완료가 새 진행 상태보다 앞서지 않는 하나의 구체적 위험**을 해결한다.

### 구현 단위 GR-2: 자기 자료와 별도 수정 판

수정 prompt에 옛 `assignment.prompt` 전체를 재활용하면 그 안의 고정 기억 전달문까지 다시 들어갈 수 있다. 목표·자기 과제·원래 답·앞 판·지적과 당시 처분을 명시적으로 구성하고 자료 mount도 그 작성자 배정만 사용한다. 재검토자는 수정 답과 고정 지적을 받고 자료 원문을 추가로 받지 않는다. 원래 답과 수정 답은 계속 별개로 남아야 한다. [설계 L57–66](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/architecture/general-team-review/README.md#L57-L66), [inputs.py L260–308](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/context/inputs.py#L260-L308).

이 단계에서는 일반 수정 이력 내보내기를 완성하되 격리 보고서의 공개 조건을 풀어 대체하지 않는다. 원래 작성자·고른 판·지적/처분·재검토의 연결이 핵심이며, 수정 횟수를 늘리는 것은 효용이 아니다. 현재 설계의 별도 일반 보고 형식 방향이 적절하다. [설계 L108–117](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/architecture/general-team-review/README.md#L108-L117).

### 구현 단위 GR-3: 선택한 판으로 취합

현재 일반 취합은 `drafts`의 원래 답을 읽는다. 수정 후에도 원래 답을 모으는 동작은 현 구현과 일치하지만 사용자가 쉽게 오해할 수 있으므로 GR-2 UI부터 `원래 답으로 모으기`를 명시하는 편이 낫다. GR-3에서는 팀원별 `original/revision ID/hash`를 선택·확인하고 미해결·실패·누락과 함께 고정해 취합한다. 새 결과가 나왔다고 기존 취합 입력을 소급 교체하지 않는다. [reviews.py L51–69](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/reviews.py#L51-L69), [revisions.js L49–50](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/revisions.js#L49-L50), [설계 L85–114](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/architecture/general-team-review/README.md#L85-L114).

설계의 추가 호출 상한 `n + r×v×(1+c) + k`는 호출과 입력량을 구별하고 있다. 채택 판단에는 원래 답만 읽기, 취합만 추가, 검토 추가, 수정/재검토 추가를 같은 과제에서 비교하는 실험이 필요하다. 호출 cap 전체를 소진하도록 자동 반복하는 기능을 먼저 넣지 않는다. [설계 L90–106](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/architecture/general-team-review/README.md#L90-L106).

## 5. 외부 기능을 이식할 범위 — 이 영역의 판단

이 절은 저장소의 기존 기능 후보를 **현재 코드에 어떻게 적용할지** 판단한 것이다. 해당 외부 프로젝트의 최신 구현을 이 세션에서 새로 실행하거나 검증했다는 의미가 아니다. 외부 1차 소스 검증과 전체 후보 비교는 이 검토 묶음의 채택 분석을 따른다.

| 기존 후보 | 가져올 단위 | 여기서 권고하지 않는 확장 | 완료를 판단할 사용자 관측 |
|---|---|---|---|
| H28·O11/O12, OP06의 검토·판 비교 | GR-1/2/3의 입력 확인·고정 판·지적 처분·원본 비교 | 자동 전원 토론, 무한 수정, Git 전체 복원 엔진을 같은 PR에 도입 | 올바른 수정이 늘고 잘못된 지적·판단 시간이 비용 대비 감소 |
| WorkTrail의 작업 복귀 기록 | 목표·제약·미해결·다음 행동을 현재 task/판단 메모/입력 준비 기록에 연결 | 별도 WorkTrail 서버를 앱의 두 번째 작업 정본으로 둠 | 재접속 후 작업과 이미 받은 준비 결과를 찾아 재호출 없이 진행 |
| H26/O25의 의존 작업·가져가기 | 현재 계획/CAS/선행 projection을 쓰고 필요할 때 task claim 계약만 추가 | 단일 사용자 순차 앱에 분산 queue·lease worker를 선행 도입 | 선행 조건이 바뀌어도 이미 고정된 입력은 유지되고 새 실행만 정확히 차단 |
| OP07의 다음 단계 메시지/전달 상태 | 먼저 현재 작업의 다음 행동과 기존 제안 ID 복귀를 구현 | 단순 화면 이동을 위해 outbox·broker·외부 알림 의무화 | 응답 유실 뒤 새 작업을 중복 생성하지 않고 수락된 자원으로 이동 |
| 대규모 목록·검색 패턴 | 준비 목록/선택 상세 분리, 현재 cursor·cache 유지, 필요시 공개 FTS | 원장 전문의 무조건 임베딩·봉인 자료 색인 | 큰 원문이 있어도 홈 응답은 작은 메타데이터로 유지 |

후보 위치: [CAPABILITY-MAP H26–H28](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/architecture/redesign-2026-10-04/CAPABILITY-MAP.md#L38-L40), [O11/O12](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/architecture/redesign-2026-10-04/CAPABILITY-MAP.md#L90-L91), [O25](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/architecture/redesign-2026-10-04/CAPABILITY-MAP.md#L104), [OP06/OP07](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/architecture/redesign-2026-10-04/CAPABILITY-MAP.md#L139-L140), [REFERENCE-MAP WorkTrail](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/REFERENCE-MAP.md#L23-L25).

### 코드 규모보다 변경 결합을 줄인다

`server.py`는 경로 분기, `index.html`/`role-board.js`는 여전히 넓은 화면 조립을 맡는다. 이미 `api/catalog/templates/revisions/extraction/workflow/paging`으로 작은 기능을 나눈 상태다. GR 추가 시 이 패턴으로 `reviews` 화면을 독립시키고 모드별 표시 문구·명령 가능 이유를 공통 projection에서 받는 정도가 적절하다. 지금 곧바로 SPA 프레임워크나 TypeScript 전환을 해야 한다는 근거는 이번 정적 검토에서 얻지 못했다. [server.py L46–60](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/server.py#L46-L60), [role-board.js L671–835](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L671-L835).

다만 단계 상태는 `roles.task_projection`, `workflow.steps`, 화면의 개별 버튼, 서비스 gate에 나뉘어 있다. 서비스가 권한의 정본인 현재 계약은 유지하되 조회용 `available_actions`에 이유·기준 판·예상 호출 수를 싣는 작은 경로를 고려할 수 있다. 이것은 UI가 허용한 명령을 서버가 맹신하자는 뜻이 아니다. 최종 시작 거래에서는 늘 실제 조건을 재검사한다. 일반 검토 추가 시 여러 파일이 제각각 새 state 이름을 알아야 하는 부담을 줄이는 목적이다. [roles.py L76–145](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/roles.py#L76-L145), [workflow.py L24–44](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/workflow.py#L24-L44).

## 6. 실행 입구와 운영에서 남길 작은 작업

`app.run`은 별도 controller가 아니라 동일 준비 조회·원장·gate를 쓰는 headless 입구이며 공개 초안과 선택적 합성에 범위가 명확하다. 현재 일반 배정·교차검토·수정용 CLI 옵션은 없다. 이는 문서와 일치하는 기능 범위이지 오류가 아니다. GR 비교 실험을 반복하게 되면 HTTP 서버를 띄우는 임시 드라이버를 계속 복사하기보다 같은 서비스로 실행하는 제한된 실험 scenario 입구를 추가하는 것이 낫다. 자동 제품 워크플로우와 연구용 동일 조건 실행은 구분한다. [run.py L1–17](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/run.py#L1-L17), [L48–90](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/run.py#L48-L90), [L139–184](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/run.py#L139-L184).

headless 종료 코드 0은 현재 공개까지 완료되고 요청한 합성을 시도했다는 뜻이며 모델 품질 합격을 뜻하지 않는다. 모델별 실패와 시도 여부는 결과 JSON에서 보아야 한다. 실험 입구를 넓힐 때 이 의미를 바꾸기보다 scenario acceptance 결과를 별도 필드로 추가한다. 파일 출력과 실제 원장 저장은 역할이 다르므로 보고 파일만을 복구 정본으로 삼지 않는다. [run.py L13–17](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/run.py#L13-L17), [L153–184](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/run.py#L153-L184).

launcher는 소유자 nonce·PID·잠금을 갖고 창을 닫으면 idle을 기다렸다 정상 종료한다. 상시 daemon으로 바꾸면 편리해질 수 있지만 자동 예산 갱신·unknown·기기 관측 만료·사용자가 실행 상태를 아는 방법까지 같이 설계해야 한다. 현재 규모에서는 WF-01/02의 이어가기부터 완성하는 편이 유용하다. [launch.py L22–29](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/launch.py#L22-L29), [L234–251](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/launch.py#L234-L251).

## 7. 이 세션의 검증과 재현 방법

다음 기존 검사를 이 웹 컨테이너에서 실행해 모두 `OK`, skip 없음으로 확인했다. **저장소 전체 CI나 사용자 PC 실측 통과를 뜻하지 않는다.** 각 검사의 결과는 이 기준 SHA의 관측이며 본문에 새 제품 기능이 구현되었다고 주장하지 않는다.

```bash
python -m unittest discover -s tests -p 'test_workflow.py' -v
python -m unittest discover -s tests -p 'test_pages.py' -v
python -m unittest discover -s tests -p 'test_templates.py' -v
python -m unittest discover -s tests -p 'test_api_client.py' -v
python -m unittest discover -s tests -p 'test_query_projections.py' -v
python -m unittest discover -s tests -p 'test_role_board_render.py' -v
```

확인한 보호 범위는 계획 순환·없는 선행·CAS·preview/생성 틈, 페이지 밖의 전체 상태·선행·inbox, DB 변경·rollback·외부 commit·runtime cache 무효화, 템플릿 hash·현재 모델·미승인 복원, 늦은 요청 소유권, 봉인/공개 summary 일치, 순수 JavaScript 역할판 렌더다. 실제 브라우저 키보드·스크린리더·레이아웃·네트워크 중단을 완전하게 검사한 것은 아니다.

### 합성 원장 probe 재현

저장소 루트에서 임시 디렉터리를 사용한다. [재현 스크립트](repro_workflow_projection.py)는 기존 합성 실행기를 이용하며 실제 CLI·모델을 부르지 않는다. `python docs/reviews/2026-10-05-architecture-adoption/repro_workflow_projection.py --preparations 5`와 `--preparations 20`으로 조회 크기·warm cache·별도 ID 생성·원장 선택을 재확인한다. 아래는 조회 부분만 옮긴 예다. 시간·UUID·work 경로 길이에 따라 소량의 바이트 차이는 가능하다.

```python
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path('tests').resolve()))
from app.controller import Controller
from app.store import Store
from test_refine_mode import Refiner, ROSTER

N = 5
with tempfile.TemporaryDirectory(prefix='dml-workflow-review-') as folder:
    root = Path(folder)
    store = Store(root / 'journal.db')
    ctl = Controller(store, Refiner(), work_root=str(root / 'work'))
    try:
        ids = []
        for _ in range(N):
            ids.append(ctl.refine(ROSTER['claude'], '검토' * 3900,
                                  use_memory=False))
            assert ctl.wait_idle()
        page = ctl.queries.pages.browse(limit=1)
        size = lambda value: len(json.dumps(value, ensure_ascii=False).encode('utf-8'))
        print({'body_bytes': size(page),
               'refinement_bytes': size(page['refinements']),
               'warm_bytes': size(ctl.queries.pages.browse(limit=1)),
               'tasks': page['pages']['tasks']['total'],
               'inbox': page['inbox'],
               'distinct_ids': len(set(ids)) == N})
    finally:
        assert ctl.shutdown()
        store.close()
```

WF-01은 별도 임시 SQLite에서 `live_budget(cap=10, provider_caps={codex:5, claude-code:5})`와 `live_call_reserved(adapter_id=codex)` 사건 5개만 만들고 닫은 뒤 `launch.pick_ledger(root)`를 호출했다. 선택 경로는 기존 원장과 달랐고 기존 `journal.db`는 존재했다. 이는 `_has_room`/`pick_ledger`의 선택 정책에 대한 최소 함수 재현이며 정상 제품 원장 전체의 migration·복구나 실제 프로세스 종료를 시험한 것은 아니다.

## 8. 구현 순서 권고

1. **GR-1은 현재 설계대로 구현한다.** 미리보기·라운드·공개 조회·상태·내 차례·검색·사용량까지 하나의 사용자 경로를 끝낸다. 새 round ID의 응답 유실 복귀 계약을 함께 정한다.
2. **WF-02/03은 한 조각으로 묶는다.** 입력 준비 목록/선택 상세/복귀가 생기면 기존 전문 polling 비용과 잃어버린 준비 UI를 동시에 줄일 수 있다. 기록 복원은 자동 실행 권한을 갖지 않는다.
3. **WF-01은 작업 수명 설계로 명시한다.** 예산을 모두 쓴 뒤 처음부터 작업이 사라져 보이는 경험을 막는다. 호스트의 미정리 호출을 확인하는 경계도 함께 다룬다.
4. **GR-2는 자기 배정 자료와 별도 판·보고서를 완성한다.** 먼저 한 작성자 수정과 다른 작성자 재검토의 실제 유용성을 본다.
5. **GR-3과 일반 headless 비교 입구는 효과 측정에 맞춰 확장한다.** 여러 후보 제품의 비슷한 보드·queue·agent runtime을 한 번에 가져오는 대신, 기존 원장과 공개 projection이 하나의 정본으로 남게 한다.

이 순서는 새로운 상태 저장소나 프레임워크를 늘리는 양보다, 사용자가 한 작업을 끊김 없이 준비하고 판단하는 데 필요한 경로를 우선한다.
