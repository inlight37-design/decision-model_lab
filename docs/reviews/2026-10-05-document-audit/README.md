# 문서 전체 점검과 마무리 정리

2026-10-05, codex. 기준 main은 `3a511b6fa32f9b265d3504a05a1a8940400a9841`(통합 인계 병합 뒤)이다. [카드 #182](https://github.com/inlight37-design/decision-model_lab/issues/182)의 작업이며 클라우드 파일·코드·GitHub에 접근했다. 사용자 PC·실제 구독 CLI·로그인은 확인하지 않았고 모델을 부르지 않았다.

## 확인한 범위

- 추적 중인 Markdown 전체의 목록과 상대 링크 연결을 점검했다. README·AGENTS·NEXT-SESSION을 입구로 문서에 도달할 수 있는지 보고, 연결이 빠진 문서는 내용을 읽어 알맞은 지도에 붙였다.
- 현재 안내인 루트 README, NEXT-SESSION, DOCUMENT-MAP, FEATURES, REFERENCE-MAP, SETUP, app/README·ARCHITECTURE, core/README와 설치·관측 안내를 코드의 책임·입력·원장·화면·명령 범위와 대조했다. 전체 소스의 모든 동작을 새로 검증했다는 뜻은 아니다.
- 조사·설계·실험·검토·보관 인계의 입구, 외부 프로젝트에서 현재 코드로 이어지는 연결, 근거 레지스트리와 공개 카드의 남은 작업을 확인했다. 외부 원문을 새로 전수 조사하거나 과거 실측을 반복하지 않았다.

## 발견과 반영

| 발견 | 바꾼 곳과 확인 근거 | 도움이 되는 점 |
|---|---|---|
| 앱 원장 안내는 schema 16, 실제 Store는 17 | [앱 원장 안내](../../../app/README.md#회계와-원장), [Store](../../../app/store.py)의 `SCHEMA_VERSION`·현재 표와 대조. 완료된 schema별 장문 경위는 git/날짜 기록으로 찾도록 정리 | 현재 구조와 옛 이전 이력을 혼동하지 않음 |
| 구현된 수정·재검토의 사용자 안내가 없고 “고친 답은 받지 않는다”는 문장이 남음 | [수정 사용법](../../../app/README.md#검토-지적으로-답-고치기), [RevisionService](../../../app/application/revisions.py), [화면](../../../app/static/revisions.js). 입력 확인·작성자·재검토·호출 상한·JSON 저장과 일반 팀원 미지원 명시 | 기능을 실제로 찾고 올바른 순서로 사용 |
| 다듬기·제안·분담·취합·합성·일반 입력에서 자동 기억 설명이 빠지거나 “받는 것은 …뿐”으로 남음 | [앱 안내](../../../app/README.md), [PlanningService](../../../app/application/planning.py), [ReviewService](../../../app/application/reviews.py), [SynthesisService](../../../app/application/synthesis.py), [InputBuilder](../../../app/context/inputs.py). 상세 범위는 [FEATURES](../../FEATURES.md#자동-기억의-범위)에 연결 | 실제 모델에 전달되는 입력을 오해하지 않음 |
| 일반 자료를 원문 파일만 받는 것처럼 설명하고 결과 판의 사건 범위가 좁게 적힘 | 같은 앱 안내의 일반 팀원 입력·자료 추출 메타데이터·판단 완료 정정. [RunRepository](../../../app/repository.py)의 `_review_state`로 정확한 사건 범위를 연결 | 추출 자료·고정 기억과 새 결과의 재확인 이유 설명 |
| 헤드리스 연결 위치가 옛 server 함수이며 화면 전체 기능을 지원하는 것처럼 읽힐 수 있음 | [헤드리스 안내](../../../app/README.md#헤드리스-실행--화면-없이-한-번에), [app.run](../../../app/run.py), [wiring](../../../app/wiring.py). 격리 CLI 초안·선택적 합성과 화면/API가 필요한 기능을 구별 | 다음 실험에서 없는 CLI 옵션을 찾지 않음 |
| 참고 프로젝트의 적용 위치가 분리 전 controller에 머물고 실행 기반 안내는 은퇴한 conformance를 가리킴 | [참고 지도](../../REFERENCE-MAP.md)의 InputBuilder·repository·coordinator·PublicQueries/pages, [core 안내](../../../core/README.md)의 현재 SETUP/W2 절차 | Hermes·AnchorMind·tmux·Peek 원리를 담당 코드에서 다시 찾음 |
| 설치 성공과 선택 기능 준비를 구별하는 설명 부족 | [SETUP](../../SETUP.md)에 서버 환경의 Poppler와 Linux Node 시험 준비를 연결. [설치기](../../../tools/setup/setup-wsl.sh)·[준비 조회](../../../tools/setup/check_setup.py)·[추출 안내](../../../app/README.md#공통-자료) 대조 | PDF 기능 준비와 기본 설치 성공을 구별 |
| 문서 입구에서 찾을 수 없던 보조 기록과 부품 정의 | 아래 연결 누락 표의 자료를 DOCUMENT-MAP·REFERENCE-MAP·reviews 목록에서 연결 | 오래된 분석과 재현 기준이 잊히지 않도록 보존 |
| 열린 보류 아이디어가 기능 지도에 없음 | [FEATURES의 보류 아이디어](../../FEATURES.md#보류한-아이디어)에 [카드 #127](https://github.com/inlight37-design/decision-model_lab/issues/127)의 곁가지 질문 세션을 연결 | “나중에 생각하자”는 사용자 결정을 유지하면서 후보를 발견 가능하게 함 |
| 현재 안내를 검사하는 기존 범위가 실제 파일 배치를 따라가지 못함 | [문서 무결성 검사](../../../tests/test_research_integrity.py)의 현재 안내 목록과 app/core/tools/design 상대 링크 검사 범위를 확대 | 같은 종류의 누락·깨진 파일 링크가 다시 쌓이는 것을 줄임 |

현재 남은 일의 입구는 루트 README·reviews 목록에서도 현재 인계와 기능 우선순위로 통일했다. 과거 검토 요청서는 당시의 질문과 한계를 추적할 때 읽는다.

## 연결이 빠져 있던 자료

기준판의 추적 Markdown 264개에서 문서 입구로 도달하지 못하던 파일은 아래 7개였다. 파일 삭제나 이동 없이 연결했다. 추가한 이 감사 기록을 포함한 재검사 결과는 검증 절에 적는다.

| 자료 | 붙인 입구 |
|---|---|
| [DecisionCard](../../../design/project/components/DecisionCard/README.md), [DispositionBadge](../../../design/project/components/DispositionBadge/README.md), [EvidenceChip](../../../design/project/components/EvidenceChip/README.md) | [DOCUMENT-MAP](../../DOCUMENT-MAP.md). 브랜드북의 참고 정의와 실제 island-ui를 구별 |
| [Hermes CROSSCHECK](../../research/hermes-2026-09-23/CROSSCHECK.md) | [REFERENCE-MAP](../../REFERENCE-MAP.md)의 Hermes 원문 목록 |
| [A1 시작 체크포인트](../2026-09-24-a1-integrity/START.md), [CLI unblock 시작 체크포인트](../2026-09-24-cli-unblock/START.md) | [검토 목록](../README.md)의 해당 날짜 행. 현재 할 일이 아니라 당시 시작 상태 |
| [9월 25일 검토 마감·재현 기준](../2026-09-25-review/COMPLETION.md) | 같은 검토 목록에서 본문·UPSTREAM-UPDATE와 함께 연결 |

검사는 코드 블록을 제외한 인라인/참조형 상대 Markdown 링크와 디렉터리 README를 따라간 일회성 목록 검사다. 외부 URL 가용성·브라우저별 앵커 동작·모든 형식의 링크를 보증하지 않는다. 다음은 누락으로 세지 않았다.

- 보관 인계의 루트 기준 상대 경로: [보관 원칙](../../handoff/README.md)에 따라 당시 원문을 유지한다.
- 역할판 요청서의 코드 예시 안 주장·저자 표기: 실제 문서 링크가 아니다.
- 옛 V04-01 검토의 `#L67-L78`·`#L71`: 파일은 존재하며 Markdown 제목이 아닌 GitHub 소스 줄 참조다. 날짜 기록의 표현은 보존한다.

## 검증

클라우드에서 인코딩·디자인 토큰·frontier 기록 일관성·runtime inventory dry-run·설계/v0.2 계약·근거 원장 검사와 `compileall`을 실행했고 성공했다. runtime dry-run은 이 클라우드의 준비 조회이며 사용자 PC 관측을 갱신하지 않는다.

- `test_research_integrity.py`와 `test_accumulation.py`: 확대된 링크 검사·현재 안내·인계 모양/크기·도구 사용처 검사 성공. `git diff --check` 성공.
- 문서 연결 재검사: 새 기록 포함 Markdown 265개, 입구에서 도달하지 못하는 파일 0개, 위 예외를 제외한 깨진 상대 파일 링크나 제목 앵커 후보 없음. 이는 연결 검사 결과이며 내용의 완전성을 보증하지 않는다.
- `python -m app.run --mock ... --policy include-unverified --synthesize mock`: 새 임시 원장에서 종료 0, `a1-headless-run/1` JSON 생성, stderr 없음. 임시 파일은 제거했다.
- `python -m unittest discover -s tests -v`: 최종 로컬 실행 825개 중 기존 `test_children_left_behind_are_counted_and_ended` 1개 실패(`unknown != exited`), OS/격리 조건의 skip 8개. 이 컨테이너에서 이미 기록된 자손 회수 문제이며 제품 코드·검사 조건을 완화하지 않았다. 작성 중 기록 파일 생성보다 먼저 돈 링크 검사의 실패는 파일 완성 후 재검사에서 해소했다.

최종 PR head와 병합 뒤 main의 Linux Python 3.12/3.13·Windows Python 3.13 CI 결과는 이 작업 PR의 Checks·본문을 기준으로 한다. 이 기록을 쓴 시점에 아직 실행하지 않은 CI를 통과했다고 표시하지 않는다.

## 남은 일과 한계

다음 구현은 [일반 팀원 검토 설계](../../architecture/general-team-review/README.md)의 **GR-1 교차검토 → GR-2 작성자 수정·다른 작성자 재검토 → GR-3 선택한 판 취합**이다. 이번 변경은 안내와 기존 문서 검사 범위를 정리한 것이며 일반 팀원 검토를 구현하지 않았다. 보류 아이디어 #127은 사용자가 시작하자고 할 때 다시 판단한다.

주 PC 재관측 시점·실제 품질/구독 비용·실제 원장 부하·브라우저 접근성 등 남은 실측은 [현재 인계](../../../NEXT-SESSION.md#4-다음-작업)를 따른다. 과거 관측 원문·사용자 결정·브랜드북 원본은 고치지 않았다. 새 외부 근거의 진실성·URL 생존·라이선스 재심사·보안 전수 감사를 완료했다고 주장하지 않는다.
