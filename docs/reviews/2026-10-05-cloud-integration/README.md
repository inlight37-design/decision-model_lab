# 클라우드 개편 작업 통합·다음 구현 인계 — 2026-10-05

사용자가 요청한 조사·개편·후속 기능을 어디까지 반영했고 무엇부터 이어갈지 정리한 시점 기록이다. 접근 범위는 클라우드 컨테이너·GitHub이며 사용자 PC 접속·실제 모델 호출은 없었다. 예전 PC 관측은 [현재 인계 1절](../../../NEXT-SESSION.md)에 연결된 원래 기록을 유지한다.

## 1. 이번 병합

사용자의 “병합하고 여태한일과 다음에 할일 정리” 지시에 따라 각 최종 head의 CI 성공을 확인한 뒤 merge commit으로 순서대로 통합했다. 보호 규칙 우회·강제 push는 하지 않았다.

| PR | 반영 내용 | 병합 commit | 병합 전 검증 |
|---|---|---|---|
| [#175](https://github.com/inlight37-design/decision-model_lab/pull/175) | 작업·타임라인·내 차례 페이지화 | `7b1ab6319620d96b29837516669ca6f77eb16213` | [CI](https://github.com/inlight37-design/decision-model_lab/actions/runs/37257796150) |
| [#177](https://github.com/inlight37-design/decision-model_lab/pull/177) | 오래된 공개 이력·답 본문 기억 검색과 평가 | `b4a75e7e5bdffa914f20d4473796ad0c198b9832` | [CI](https://github.com/inlight37-design/decision-model_lab/actions/runs/37259280752) |
| [#179](https://github.com/inlight37-design/decision-model_lab/pull/179) | 일반 팀원 교차검토의 구현 전 설계 | `10750f7770116be744dd1a538f84956e17c633f5` | [CI](https://github.com/inlight37-design/decision-model_lab/actions/runs/37260629828) |

통합 main `10750f7770116be744dd1a538f84956e17c633f5`의 파일 트리는 마지막 검증 head `02ff978b40933552edf19cef7c9b9e13beefc846`와 `git diff --exit-code`로 같음을 확인했다. 통합 후 검사는 [main CI](https://github.com/inlight37-design/decision-model_lab/actions/runs/37261111200)에 남는다. schema 17과 기존 소비·사건 기록을 유지한다. 문서 정리 PR의 최종 head·병합 후 CI는 해당 PR의 Checks와 main Actions가 기준이다.

## 2. 지금까지 이어진 작업

이번 표는 10월 4–5일 개편 흐름의 길잡이다. 세부 결론·수치는 각 고정 기록에 있고, 현재 기능의 코드 위치는 [FEATURES](../../FEATURES.md)와 [실행 아키텍처](../../../app/ARCHITECTURE.md)가 관리한다.

| 단계 | 반영한 것과 프로젝트 가치 | 원래 근거 |
|---|---|---|
| 외부 기능 조사 | Hermes 등의 편의·검색·기억·도구 후보를 수집하고 사용처·제약·채택 여부를 구분 | [기능 후보](../../research/feature-catalog-2026-10-04/README.md), [참고 지도](../../REFERENCE-MAP.md) |
| 부품·운영 방식 비교 | AnchorMind 등의 저장/검색/검토와 tmux 등의 실행/연결·복구를 분해해 우리 책임 경계와 대조 | [부품 분석](../../research/component-comparison-2026-10-04/README.md), [운영 분석](../../research/operations-comparison-2026-10-04/README.md) |
| 개편 준비·문서 지도 | 후보→현재 격차→목표 구조→파이프라인→계약→우선순위·이행 단계를 연결 | [개편 준비서](../../architecture/redesign-2026-10-04/README.md), [문서 지도](../../DOCUMENT-MAP.md) |
| 실행 서비스 기반 | 입력·작업·계획·검토·수정·합성·실행·호출·조회를 분리. 공개 검색·호출 기록·기억 선택 이유를 같은 원장에 연결 | [기반 검증](../2026-10-04-foundation/README.md), [PR #161](https://github.com/inlight37-design/decision-model_lab/pull/161) |
| 반복 설정 | 팀/모델·질문·자료·분담·기억 설정 템플릿, 자료 사본과 파일 이동, 복원 후 새 입력 확인 | [템플릿 검증](../2026-10-04-templates/README.md), [PR #163](https://github.com/inlight37-design/decision-model_lab/pull/163) |
| 지적에서 답 수정까지 | 격리 공개 뒤 원래 작성자의 별도 수정 판과 다른 작성자의 재검토. 원본·미해결·상한·복구 보존 | [수정 검증](../2026-10-05-revisions/README.md), [PR #165](https://github.com/inlight37-design/decision-model_lab/pull/165) |
| 자료 준비 | PDF/공개 URL의 선택 범위·누락 미리보기, 원본/변환/선택 hash와 출처를 자료·템플릿·보고에 연결 | [추출 검증](../2026-10-05-source-extraction/README.md), [PR #167](https://github.com/inlight37-design/decision-model_lab/pull/167) |
| 기록 조회 | 목록/상세 분리와 검색 필터 선적용 뒤 페이지화 추가. 전체 상태를 보존하면서 화면 전송·반복 조회 부담 감소 | [조회 측정](../2026-10-05-query-scale/README.md), [페이지화 측정](../2026-10-05-list-pagination/README.md), [#169](https://github.com/inlight37-design/decision-model_lab/pull/169)·[#175](https://github.com/inlight37-design/decision-model_lab/pull/175) |
| 기억 선택 | 판단·지적·반대 근거의 균형 발췌 뒤 오래된 이력·검증된 원래 답 검색으로 확대. 선택 이유·누락과 검색 비용 표시 | [초기 평가](../2026-10-05-memory-evaluation/README.md), [확장 평가](../2026-10-05-recall-expansion/README.md), [#171](https://github.com/inlight37-design/decision-model_lab/pull/171)·[#177](https://github.com/inlight37-design/decision-model_lab/pull/177) |
| 작업 흐름 | 목표·완료 기준·선행 계획, 입력/생성 때 재확인, 현재 단계·내 차례·막힌 이유 표시 | [흐름 검증](../2026-10-05-workflow-inbox/README.md), [PR #173](https://github.com/inlight37-design/decision-model_lab/pull/173) |
| 일반 팀원 검토 준비 | 팀원별 과제/자료, 입력 확인, 공유 실행·상태/보고서, 호출 비용과 구현 순서를 설계 | [설계서](../../architecture/general-team-review/README.md), [PR #179](https://github.com/inlight37-design/decision-model_lab/pull/179). **제품 기능은 미구현** |

외부 기능은 비교·선택해 적용했으며 해당 프로젝트 전체를 이식하거나 모든 후보를 도입했다는 뜻은 아니다. 날짜별 원본 조사·실험은 보존했다.

## 3. 검증한 범위와 남은 제한

- 코드 경계·합성 원장·브라우저 흐름과 Linux/Windows CI를 확인했다. 이전 로컬 전체 suite의 컨테이너 자손 회수 `unknown != exited` 실패는 각 기록에 남겼으며 새 skip이나 무관한 수정으로 숨기지 않았다. 이번 문서 정리로 제품 실행 코드는 바꾸지 않는다.
- 페이지화는 표시/전송과 변경 없는 반복 조회를 줄인다. 첫 조회·원장 변경 후 집계는 선형이고 선택 상세/연결 전 계획 이력은 페이지화하지 않았다. 전체 본문 검색도 선형이다. 실제 PC·실사용 원장 분포의 성능은 별도다.
- 기억 검색은 같은 작업·같은 원장의 공개 이력만 사용한다. 전체 적격 이력을 찾는 만큼 검색 비용이 늘었다. 동의어·관련 근거가 없을 때의 최근 기록 대체·약한 근거 탈락·긴 답의 발췌 밖 표현·수정 답에만 생긴 검색어는 남은 한계다.
- 확장 기억 사례의 개선 수치는 그 사례로 선택기를 조정한 회귀 결과다. 독립 검증 데이터나 일반적인 모델 품질 향상률이 아니다. 실제 비교 실험과 구독 비용·사람 작업 시간은 측정하지 않았다.
- 자료 추출은 OCR·로그인·동적 웹을 지원하지 않는다. 기억·자료 출처 hash와 인용 일치는 사실 검증을 대신하지 않는다.
- 일반 팀원은 결과 취합까지 가능하고, 교차검토·수정·재검토는 아직 격리 공개 뒤만 가능하다. 일반 검토 설계가 병합됐다고 실행 기능이 열린 것은 아니다.
- 사용자 PC의 설치·CLI 판·로그인·관측을 이번 클라우드 작업에서 확인하지 않았다. 기존 주 PC 관측 기한과 잔여 실행/격리 제한은 [인계](../../../NEXT-SESSION.md)의 원래 사실을 유지한다.

## 4. 다음 구현의 순서

아래는 이 기록 시점의 순서다. 바뀐 우선순위는 [현재 기능 안내](../../FEATURES.md#후속-우선순위), 정확한 입력·상태·비용·회귀 계약은 [일반 검토 설계](../../architecture/general-team-review/README.md)를 따른다.

| 순서 | 할 일 | 완료됐다고 볼 조건 |
|---|---|---|
| P1 / GR-1 | 일반 팀원 교차검토 | 과제·답·배정 자료 metadata·검토자·호출 수를 확인한 한 라운드. 검토 입력/생성 확인·순차 호출·공개 조회·화면·검색·사용량·내 차례/선행 상태를 한 경로로 완성 |
| P1 / GR-2 | 일반 작성자 수정·다른 작성자 재검토 | 원래 작성자의 자기 자료만 사용, 지적/처분/앞 판 고정, 상한·복구·원본 비교·일반 수정 보고 연결 |
| P2 / GR-3 | 선택한 판으로 취합 | 팀원별 원래 답/수정 판 ID와 hash를 명시적으로 고르고 미해결·누락을 함께 취합. 원래 초안을 소급 교체하지 않음 |
| 별도 관측 | 실제 PC·과제·원장 평가 | CLI 계획을 바꾸면 재관측. 현 주 PC는 2026-10-27 전 재관측 필요. 실제 기억 누락/검색 부담과 검토의 유효/잘못된 지적·사람 검토 시간·호출 비용 비교 |
| 조건부 | 고급 검색·지속 실행·원격 작업 등 | 먼저 실제 필요·운영 부담·효과 근거. 자동 수정 loop·새 실행 엔진·전역 기억을 선행 작업으로 끼워 넣지 않음 |

GR-1 시작 시 [설계 §2](../../architecture/general-team-review/README.md#2-현재-코드와-바꿀-위치)로 코드 위치를 찾고, §3의 입력 계약과 §7의 실패 확인표를 함께 읽는다. `ReviewService`에서 일반 거절 조건만 없애지 않는다. 팀원마다 맡은 일이 다르며 `collected`를 `revealed`로 바꾸면 격리 합성·정족수까지 잘못 열린다. GR-1은 클라우드의 모의/HTTP/JavaScript 경계 검사로 진행할 수 있고 실제 모델 효과는 별도 평가한다.

## 5. 이어받는 문서 순서

현재 작업은 [NEXT-SESSION](../../../NEXT-SESSION.md) → [문서 지도](../../DOCUMENT-MAP.md) → [기능 우선순위](../../FEATURES.md#후속-우선순위) → [일반 검토 설계](../../architecture/general-team-review/README.md) 순으로 읽는다. 필요한 코드 책임은 [실행 아키텍처](../../../app/ARCHITECTURE.md), 외부 아이디어의 근거는 [참고 지도](../../REFERENCE-MAP.md)에서 내려간다. 이 기록의 완료 이력을 현재 인계에 복사해서 쌓지 않는다.
