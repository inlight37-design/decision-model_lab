# 기반 재구성의 최종 대조·구현·검증

2026-10-04 · codex · 클라우드 컨테이너·GitHub · [카드 #160](https://github.com/inlight37-design/decision-model_lab/issues/160), [PR #161](https://github.com/inlight37-design/decision-model_lab/pull/161). 시작점은 `1f51987b18ead6e544498078b13bce1f614a413d`이며 PR #159의 조사/통합 준비서 위에서 작업했다. 사용자 PC·실제 native CLI·모델은 새로 관측하지 않았다.

## 개편 직전 판단

외부 후보 H/O/D/OP의 원문, 배치 지도, 현재 기능, 실제 controller 메서드의 호출·데이터 의존을 대조했다. 빠진 전역 cursor·명령 receipt·검토 판 lineage는 앞 준비서에서 발견한 설계 요구로 유지한다. 구현 전에 해결된 것처럼 가정하지 않았다.

| 판단 | 실제 조치 |
|---|---|
| 입력·실행·회계·계획·검토·조회가 controller에 집중 | 서로를 명시적으로 받는 독립 서비스와 조립 facade로 재구성 |
| `_Seat`, 수용·공개·원장 거래는 이미 검증할 기반이 있음 | 의미를 재작성하지 않고 새 실행/원장 경계에서 재사용 |
| 새 검색이 봉인 판단을 복제하면 위험 | 공개 projection만 읽는 검색 모듈. 본문뿐 아니라 건수·발췌도 같은 입력 |
| 공통 invocation을 위해 즉시 새 DB가 필요한가 | 기존 역할별 행/사건을 읽는 adapter와 공통 예약부터 구현; schema 유지 |
| 기억의 선택 이유와 실제 입력을 연결해야 함 | 새 pack에 근거를 hash로 고정, 옛 이유는 미기록으로 표시 |
| 구조만 바꾸면 사용자 효용이 안 보임 | 공개 검색·원래 실행 이동·호출 기록·기억 출처 버튼까지 연결 |
| 도구·문서가 또 쌓일 수 있음 | 상시 생성기를 추가하지 않고 현재 FEATURES/문서 지도를 갱신. 날짜 자료는 보존 |

원본 기능별 작동·쓰임·조건·부담은 조사 기록, 목표 배치는 개편 준비서, **실제 구현은 [app/ARCHITECTURE](../../../app/ARCHITECTURE.md), 기능 가치와 다음 순서는 [FEATURES](../../FEATURES.md)**로 나눴다. 모든 후보 구현이나 원격 서비스 전환으로 확대하지 않았다.

## 구조와 기능 적용

- Controller → Work/Planning/Review/Synthesis service, InputBuilder, ExecutionCoordinator, InvocationLedger, RunRepository, PublicQueries. 하위 서비스가 controller/HTTP를 import하지 않는다.
- 실제 모델 thread와 executor.run은 coordinator, 모든 실제 예약 사건 쓰기는 InvocationLedger가 맡는다. 기존 역할별 수용·직렬화·회복 의미를 보존한다.
- 읽기 API search/activity/memory, 공개 snapshot 기반 종류·작업·문구 검색, 기록 탐색 대화상자, 원래 실행 이동을 추가했다.
- 전송/token·redirect 제한·취소/응답 소유권은 api.js, 탐색은 catalog.js로 분리했다. 기존 역할판·디자인 부품은 유지했다.
- 기억 선택 이유도 전달문 바이트 상한 안에 저장한다. 새 metadata의 입력 비용 증가·경계에서 선택 항목 수 변화 가능성은 있으며, 모델 품질 이득은 미측정이다.

## 검증과 발견한 문제

**기존 의미 비교.** 기준 commit의 controller를 별도 모듈로 읽어 같은 현재 helper와 합성 실행기에서 새 controller와 비교했다. UUID·기록 시간을 고정한 수동 대기/일부 봉인/공개/사람 판단/취소/합성 실행 사례의 public snapshot과 사건 이력이 같았다. 이는 해당 경로 비교이며 전체 과거 환경이나 PC 동작의 재현은 아니다. 새 기억 metadata는 의도한 추가이며 과거 pack 호환은 별도 회귀로 확인했다.

**경계 검사.** 새 시험은 봉인 검색의 건수·발췌, 일반 실행의 부분 공개, 작업/종류/한도, 읽기의 무변경, 고정 기억·옛 이유 미기록·해시 변조, 역할별 invocation/unknown 보존·manual 제외, HTTP 인증·잘못된 요청, 서비스 의존 방향, 전송 credential 범위·늦은 응답 무시를 확인한다. 원래 테스트의 fault injection은 옮긴 실제 소유 지점으로 바꿨으며 단언을 완화하지 않았다.

**실제 브라우저.** 임시 모의 원장·loopback 서버와 Chromium/Playwright로 홈 검색→원래 실행, 공개 답의 HTML 문자열을 문자로 표시, 호출 기록, 좁은 화면의 무결과 안내를 확인했다. 콘솔 pageerror는 없었다. 첫 화면 검사에서 새 dialog의 기본 브라우저 테두리와 glass 배경 가독성을 발견해 기존 dialog 부품·토큰·blur를 적용한 뒤 다시 확인했다. 임시 서버와 browser는 종료했다.

**회귀.** 전체 unittest·JS 문법·compile·문서 링크·UTF-8·원장/디자인 계약·인계/도구 사용처 검사를 수행했다. 이 cloud에서 변경 전에도 재현한 `test_children_left_behind_are_counted_and_ended`의 `unknown != exited` 실패는 별도이며 runner 규칙을 바꾸지 않았다. 정확한 최종 head·CI 결과는 PR에 둔다.

반복 검증 중 발견한 새 오류는 옮긴 모듈의 호환 import 누락과 테스트의 이전 fault-injection 경로였다. 실제 소유 위치로 수정했고 관련/전체 검사로 재확인했다. 이것을 제품 기능 결함이나 CLI 성공으로 혼동하지 않는다.

## 남는 범위

실제 PC의 CLI·격리·취소 재관측, 큰 원장 검색 지연·사용자 탐색 시간, 새 기억 입력의 품질·비용 효과는 미측정이다. command idempotency table, 전역 revision, 새 invocation 영속 schema, DAG workflow, 자동 수정/재검토, 템플릿, extractor, outbox·지속/원격 worker는 이번 구현에 포함하지 않았다. 새 서비스 경계에 붙일 후속 우선순위와 완료 조건은 FEATURES와 준비서에 연결했다.

원장 migration이 없어 코드 복귀로 같은 DB를 읽을 수 있다. 실제 호출 뒤 과거 DB backup으로 돌아가 사용량·새 결과를 지우는 방식은 사용하지 않는다. main 병합과 사용자 PC 배포는 아직 이 기록의 관측 범위가 아니다.
