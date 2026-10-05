# 전체 기능 후보의 현재 상태와 도입 범위

검토일 **2026-10-05** · 기준 tree **`48ab4bd6f0e297587707aecb83ebc0cd9968892f`** · 웹 컨테이너 정적 검토.

**결론: 기존 검색·템플릿·입력 고정·격리 수정/재검토·선행 조건·수신함을 활용하고, 일반 팀원 검토를 먼저 완성하는 것이 타당하다.** 외부 제품의 전체 스킬/기억/자동 실행/원격 운영 체계를 먼저 이식할 근거는 아직 없다. 아래는 각 후보를 폐기하거나 일괄 승인하는 목록이 아니라, 현재 구현의 경계와 다음에 가져올 최소 범위를 고정한 판단표다.

원본 후보 **118개**와 이 표 **118개**를 일대일 대조했다(기준 SHA `48ab4bd6f0e297587707aecb83ebc0cd9968892f`). H 62개, O 34개, 로컬 D 10개, OP 12개이며 누락·중복·예상 밖 ID가 없다. 순서·제목·조사 원문 URL도 보존했다. D는 부품 채택 문서의 로컬 번호이며 v0.3/v0.4 ADR 번호와 다르다.

[기계판](08-capability-matrix.json) · [원본 배치 지도](../../architecture/redesign-2026-10-04/CAPABILITY-MAP.md) · [현재 기능](../../FEATURES.md) · [현재 코드 구조](../../../app/ARCHITECTURE.md)

## 판정 기준과 읽은 범위

| 상태 | 의미 |
|---|---|
| 있음 | 후보의 핵심 사용자 기능이 현재 범위에서 코드로 존재; 실사용 품질/운영 안정성 보장 아님 |
| 부분 | 후보의 일부 사용자 기능은 있으나 조합 전체 또는 확장 계약은 미구현 |
| 미구현 | 후보의 주 기능을 실행하는 제품 경로를 이번 확인 범위에서 찾지 못함; 명시된 기존 코드는 후속 접점 |
| 운영 채택 | 개발 카드/PR/문서/공식 로그인 절차로 사용; 앱 내 자동화 구현을 의미하지 않음 |

| 권고 | 의미 |
|---|---|
| 유지 | 이미 구현/운영한 범위를 사용하며 별도 engine을 추가하지 않음 |
| 좁혀도입 | 현재 담당 서비스에 적힌 다음 범위만 선택 구현; 즉시 전량 착수 지시 아님 |
| 조건부 | 실제 반복 불편·자료/기기 요구·선행 기능이 확인된 뒤 최소 실험 |
| 보류 | 현재 핵심 목표의 선행이 아니므로 가까운 구현 대상으로 확대하지 않음 |

기존 안내 문서와 원본 H/O/D/OP 후보를 읽고 아래 코드 근거의 파일·함수·줄 범위를 직접 대조했다. `app/`·`core/`의 파일 목록과 기능 검색으로 접점을 확인했으며, 모든 제품 코드와 upstream의 전체 구현을 실행/감사한 것은 아니다. 미구현 표시는 이 기준 tree와 확인 범위에 대한 판단이다. 코드 접점은 현재 근거와 후속 기능이 들어갈 기존 경계를 함께 가리키며, 접점이 있다는 이유로 그 후보 전체가 구현됐다고 판정하지 않았다.

원 조사에 기록된 upstream 설명은 각 후보 ID의 원문 링크로 보존한다. 이 문서 담당은 upstream 최신판을 새로 검증하지 않았다. 사용자 PC·공식 CLI·계정·실제 원장·브라우저는 관측하지 않았고 제품 회귀 시험도 이 매트릭스 작업에서는 실행하지 않았다. 아래 검증 게이트는 **후속 구현의 합격 조건**이며 이번 검토에서 이미 통과했다는 뜻이 아니다.

## 이 표에서 특히 구분한 것

- **템플릿과 스킬:** H02의 설정 저장/복원은 있다. H19의 필요 시 SKILL 로딩, H21의 절차 학습, H22의 절차 보관/복원, H23의 분야별 라이브러리는 없다. D07/H20의 전체 범위를 완료로 읽으면 안 된다.
- **검토와 수정:** H28/O11/OP06은 격리 공개 뒤의 수정과 재검토까지 있다. 일반 팀원 검토·자기 자료로 수정·선택 판 취합은 GR-1/2/3으로 각각 남아 있다. 기존 hash/입력 확인·호출 상한·실패 복구가 없는 것으로 재지적하지 않았다.
- **기억과 검색:** D01의 이유/입력 미리보기와 O09의 합성 평가셋은 있다. 전역 기억·항목 pin/제외·결정 supersedes·충돌함·다중 검색·동기화는 별도 범위다. 검색 점수는 사실 신뢰도가 아니다.
- **작업 흐름과 수명:** 계획·선행·단계·수신함과 invocation queued→running CAS는 있지만 DAG 자동 실행·다중 기기/worker의 lease·heartbeat 기반 작업 claim·명령 receipt·outbox·지속 실행 모드는 없다. 페이지화와 반복 projection 재사용은 event subscription이 아니다.
- **자료와 파일 변경:** PDF/공개 URL의 선택 추출과 빈 PDF 쪽 경고는 있다. Office/노트북/OCR·브라우저/이미지·코딩 writer·worktree/파일 rollback은 각각 남아 있다. schema 백업을 일반 파일 복구로 확대 해석하지 않았다.

H30·OP04·E09 등의 호출 상한·unknown 차단은 **정상 공식 배선과 현재 원장 안의 보호**를 뜻한다. 직접 Controller 통합의 예산 불변성과 원장 교체 시 미확정 종료에는 [RT-01](02-runtime.md#rt-01-실제-호출-예산의-마지막-방어가-호출자의-배선에-의존한다)·[RT-02](02-runtime.md#rt-02-종료-미확인의-점유는-현재-원장-안에서만-이어진다)의 제한을 함께 적용한다.

## 후보별 의사결정

ID를 누르면 원래 조사 행으로 이동한다. 코드 접점의 E 번호는 아래 기준 SHA의 고정 링크이고, G 번호는 이후 검증에 재사용할 기존 경계다. 관련 ID는 중복 구현을 피하기 위한 연결이다.

### H01–H11: 화면·세션

| 후보·원문 | 현재 상태와 경계 | 권고·다음 범위 | 코드 접점 | 검증 게이트 |
|---|---|---|---|---|
| [H01 이름·검색·즐겨찾기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L11) | **부분** — 작업 제목·공개 문구·작업/종류 검색과 페이지 목록은 있으나 즐겨찾기·날짜/모델/상태 필터는 없다. | **좁혀도입** — OP03과 함께 현재 검색에 저장된 필터·고정 항목만 필요 순서로 더한다. 관련: D02, OP03. | [E01](#e01) · [E19](#e19) | [G06](#g06): 비슷한 제목·목록 밖 실행·필터 복귀에서 같은 대상을 찾기. |
| [H02 팀·모델 프리셋](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L12) | **부분** — 팀·모델·질문·자료·기억 설정 템플릿은 있으나 모델별 추론 강도는 연결하지 않았다. | **유지** — 기존 템플릿을 반복 과제에 사용하고 추론 연결은 실제 관측을 거친 별도 변경으로 둔다. 관련: D07, O32. | [E02](#e02) · [E15](#e15) | [G02](#g02): 복원 시 현재 카드/모델 재검사와 승인·예산 비복제. |
| [H03 파일·폴더·diff·URL 참조](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L13) | **부분** — UTF-8 자료 사본과 PDF/URL 쪽·줄 추출은 있으나 폴더 수집·Git diff 참조는 없다. | **좁혀도입** — 기존 추출 앞단에 텍스트 줄 선택을 우선 연결하고 폴더/diff는 코딩 요구가 생길 때 분리한다. 관련: H45, H47, H31. | [E03](#e03) · [E11](#e11) | [G08](#g08): 선택 범위 오류를 전체 자료 첨부로 확장하지 않기. |
| [H04 중단·방향 수정](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L14) | **부분** — drafting 단계의 참여자 취소는 저장 뒤 신호를 보내지만 진행 중 모델에 방향을 전달하는 채널은 없다. | **조건부** — 먼저 취소 뒤 바뀐 지시로 새 실행을 준비하고 실시간 steer는 일반 역할의 필요가 확인될 때 검토한다. 관련: OP07, H24. | [E10](#e10) · [E03](#e03) | [G03](#g03): 취소 신호·종료 확인·새 지시 반영의 구분과 기존 고정 입력 보존. |
| [H05 재시도·갈라서 비교·되돌리기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L15) | **부분** — 같은 작업의 새 실행과 격리 답 수정 전후 비교는 있으나 범용 fork·undo·파일 rollback은 없다. | **좁혀도입** — OP06에 원 실행/판을 가리키는 명시적 새 실행 복제부터 묶는다. 관련: OP06, H56. | [E03](#e03) · [E06](#e06) | [G02](#g02): 원본·소비·판단을 보존하고 이전 입력 승인 재사용 금지. |
| [H06 나를 기다리는 일·완료 알림](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L16) | **부분** — 현재 계획/실행에서 내 차례·문제·선행 대기를 계산하지만 브라우저 완료 알림이나 전달 ACK는 없다. | **유지** — OP11의 로컬 수신함을 사용해 누락 사례를 모은 뒤 알림만 선택적으로 추가한다. 관련: H37, OP11. | [E04](#e04) · [E19](#e19) | [G06](#g06): 새로고침·재연결에서 대상과 다음 행동을 다시 찾기. |
| [H07 결과물 서랍](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L17) | **부분** — 공개 답·수정 이력·보고서와 원 실행 이동은 있으나 생성 파일을 묶는 artifact registry는 없다. | **좁혀도입** — 기존 보고서·첨부 사본을 읽는 결과 목록부터 만들고 파일 생성 엔진은 별개로 둔다. 관련: OP12, O30. | [E01](#e01) · [E06](#e06) · [E20](#e20) | [G01](#g01): 동명 자료·사라진 참조·봉인 실행을 구분. |
| [H08 화면 배치·간단 모드](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L18) | **부분** — 상세 접기와 원문/수정 전후 나란히 보기는 있으나 사용자 배치 저장·범용 탭 편집은 없다. | **유지** — 현재 비교 화면을 실제 과제로 사용하며 불편이 반복되는 배치만 고친다. 관련: O24, OP12. | [E06](#e06) · [E20](#e20) | [G06](#g06): 좁은 화면·키보드·실행 전환에서 내용 혼합 없음. |
| [H09 빠른 명령·입력 초안](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L19) | **미구현** — 검색 대화상자는 있지만 명령 palette·지속 입력 초안 복구 경로는 확인되지 않았다. | **조건부** — OP03의 접근 동작을 재사용하는 읽기/이동 명령만 먼저 추가한다. 관련: OP03. | [E01](#e01) · [E19](#e19) | [G06](#g06): 입력 중 단축키 충돌과 의도치 않은 실행 방지. |
| [H10 목적별 시작 안내](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L20) | **부분** — readiness 조회와 작업 템플릿은 있으나 목적별 시작 안내는 별도 기능이 아니다. | **좁혀도입** — 사용자가 저장한 비교/검토 템플릿에 현재 준비되지 않은 이유를 함께 표시한다. 관련: H55. | [E02](#e02) · [E14](#e14) | [G09](#g09): 지원하지 않는 모델·만료 관측을 사용 가능한 양식으로 제시하지 않기. |
| [H11 테마·한국어·상태 마스코트](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L21) | **부분** — 한국어 화면·테마·감소 모션 처리는 있으나 상태 마스코트/언어팩 시스템은 없다. | **유지** — 용어와 상태 의미를 유지하고 마스코트는 사용자가 원할 때 시각 요소로만 추가한다. 관련: O34. | [E20](#e20) | [G06](#g06): 장식/색/움직임 없이도 성공·실패·미확인을 읽기. |

### H12–H23: 기억·스킬·반복 절차

| 후보·원문 | 현재 상태와 경계 | 권고·다음 범위 | 코드 접점 | 검증 게이트 |
|---|---|---|---|---|
| [H12 짧은 선호·프로젝트 기억](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L27) | **부분** — 자동 기억은 같은 원장·같은 작업의 공개 이력이며 선호·프로젝트 사실 저장소가 아니다. | **조건부** — O04/D04에서 명시적 범위와 사용 중인 판을 정한 뒤 수동 선호 항목부터 검토한다. 관련: O04, D04. | [E07](#e07) · [E08](#e08) | [G05](#g05): 다른 작업으로 새는 기억·오래된 선호·격리 주입 없음. |
| [H13 과거 세션 원문 검색](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L28) | **부분** — 공개 답·검토·판단·자료 메타데이터의 원문 문구 검색은 있으나 FTS·세션 메시지 전체 검색은 없다. | **좁혀도입** — D02의 동의어/한국어 실패 사례를 쌓고 현재 선형 검색이 부족한 범위만 개선한다. 관련: D02, D05, O01. | [E01](#e01) · [E19](#e19) | [G05](#g05): 오래된 핵심 답과 반복 로그를 함께 넣어 누락·응답 비용 확인. |
| [H14 검색 뒤 필요한 부분만 펼치기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L29) | **부분** — 기억 발췌·생략 bytes·원 실행 이동은 있으나 메시지 주변 문맥을 도구로 추가 조회하지는 않는다. | **좁혀도입** — 선택한 발췌에서 해당 지적/답 위치로 이동하는 UI를 우선 붙인다. 관련: D01, O03. | [E08](#e08) · [E01](#e01) | [G01](#g01): 발췌 밖 반례를 원문에서 찾고 봉인 범위는 유지. |
| [H15 현재 상태와 긴 이력 분리](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L30) | **부분** — 공개 목록/상세·단계·타임라인과 고정 기억 창은 분리했으나 현재 결론의 의미 요약은 없다. | **유지** — O17/D03의 현재·다음·막힘 표시를 사용하고 의미 요약은 근거 연결을 갖춘 별도 선택으로 둔다. 관련: D03, O17, O31. | [E04](#e04) · [E07](#e07) · [E19](#e19) | [G07](#g07): 새 계획 뒤 옛 완료를 현재 결론으로 표시하지 않기. |
| [H16 기억 지도·사용 흔적](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L31) | **부분** — 실행별 사용한 기억·선택 이유·출처는 조회하지만 전역 기억 그래프는 없다. | **유지** — 현재 출처 목록을 유지하고 여러 실행에서의 역방향 사용처가 필요할 때만 조회를 더한다. 관련: D01, O03. | [E08](#e08) | [G05](#g05): 기억의 연관과 사실 근거를 구분하고 옛 pack 이유를 추정하지 않기. |
| [H17 내보내기·가져오기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L32) | **부분** — 템플릿 export/import는 있으나 작업 이력·기억·agent 설정 전체 이동은 없다. | **조건부** — D06/O10에서 사용자가 고른 공개 자료 묶음만 설계하고 인증·승인·원장 소비는 이동 대상에서 제외한다. 관련: D06, O10. | [E02](#e02) · [E08](#e08) | [G02](#g02): 다른 원장 ID·중복 import·손상 hash·비밀 값 혼입 대조. |
| [H18 긴 대화 압축·요약 방식 선택](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L33) | **미구현** — 기억은 원문 발췌이며 긴 대화를 모델로 압축하거나 요약 전략을 고르는 기능은 없다. | **보류** — OP08의 원문 발췌 평가로 부족한 긴 일반 대화가 확인될 때 압축 한 방식만 비교한다. 관련: OP08, O31. | [E07](#e07) · [E21](#e21) | [G10](#g10): 반례 손실·요약 추가 호출·캐시 변화를 원문 방식과 비교. |
| [H19 필요할 때 읽는 스킬 서랍](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L39) | **미구현** — 템플릿은 설정을 저장할 뿐 SKILL 검색·버전·필요 시 본문 로딩은 구현하지 않았다. | **좁혀도입** — D07에 선택한 절차 문서 하나의 버전/hash를 입력 자료로 고정하는 최소 서랍부터 검토한다. 관련: D07, H20, H22. | [E02](#e02) · [E03](#e03) | [G02](#g02): 선택하지 않은 절차 미주입·역할/자료 충돌·본문 크기 확인. |
| [H20 스킬 묶음·작업 양식](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L40) | **부분** — 작업 양식 템플릿은 있지만 skill bundle의 의존성·여러 실행 단계 계약은 없다. | **좁혀도입** — H02의 양식과 H19의 선택 절차를 연결하고 다단계 엔진은 H27로 분리한다. 관련: H02, H19, H27. | [E02](#e02) · [E04](#e04) | [G02](#g02): 중복 지시·미지원 도구·빠진 의존 자료를 시작 전에 표시. |
| [H21 자료·성공 경험에서 절차 만들기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L41) | **미구현** — 완료 작업에서 절차를 추출하거나 실패 사례를 함께 학습해 저장하는 명령은 없다. | **보류** — 반복 성공/실패 과제가 모이면 사람이 고르는 절차 초안만 만들고 자동 게시·자동 실행은 분리한다. 관련: H19, H22. | [E02](#e02) · [E07](#e07) | [G10](#g10): 원 실행/조건/실패를 보존하며 다른 과제에서 재사용 효과 확인. |
| [H22 스킬 정리·핀·보관함](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L42) | **미구현** — 템플릿 삭제는 있으나 절차 사용 흔적·핀·보관·복원 기능은 없다. | **조건부** — H19를 도입해 실제 절차가 쌓인 뒤 수동 보관/복원만 추가한다. 관련: H19, O08. | [E02](#e02) | [G02](#g02): 참조 중인 절차와 원문/부속 자료를 함께 보존. |
| [H23 다른 분야의 절차 라이브러리](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L43) | **미구현** — 범용 문서·디자인·업무 절차 라이브러리는 조사 목록에 있고 제품에는 없다. | **보류** — H19로 반복 사용한 소수 절차만 가져오며 분야별 도구/스크립트는 따로 검토한다. 관련: H19, H40. | [E02](#e02) · [E15](#e15) | [G12](#g12): 선택한 절차의 입력·출력·실행 도구·라이선스 확인. |

### H24–H37: 분담·작업 흐름·예약

| 후보·원문 | 현재 상태와 경계 | 권고·다음 범위 | 코드 접점 | 검증 게이트 |
|---|---|---|---|---|
| [H24 목표가 끝날 때까지 제한 반복](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L51) | **부분** — 완료 기준·선행 확인과 제한된 다음 단계 제안은 있으나 목표 달성까지 자동 반복하지 않는다. | **조건부** — GR-1/2 이후 검사 가능한 작은 일반 과제에 명시적 단계/호출 상한을 붙여 비교한다. 관련: H27, O27. | [E04](#e04) · [E12](#e12) · [E09](#e09) | [G03](#g03): 반복 실패·unknown·상한에서 정지하고 판정 호출도 예약. |
| [H25 비동기 분담·구조화 결과](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L52) | **부분** — 일반 분담·비동기 결과 수집은 있으나 child 질문/진행 메시지·범용 handle API는 없다. | **좁혀도입** — 먼저 일반 팀원 검토 GR-1의 과제/자료/대상 계약을 완성한다. 관련: H28, O29. | [E03](#e03) · [E12](#e12) · [E10](#e10) | [G04](#g04): 팀원별 자료 경계·형식 실패 원문·취소 책임 유지. |
| [H26 의존성이 있는 작업판](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L53) | **부분** — 앱의 선행 조건/막힌 이유·invocation queued→running CAS와 개발 GitHub 카드는 있으나 다중 기기/worker의 lease·heartbeat 기반 작업 claim은 없다. | **유지** — OP04의 현재 계획/준비 상태를 유지하고 앱·GitHub 카드의 동기화는 추가하지 않는다. 관련: O25, OP04. | [E04](#e04) · [E10](#e10) · [E23](#e23) | [G07](#g07): 계획 판·선행 변경·순환·missing 상태와 시작 gate 일치. |
| [H27 재사용 가능한 다단계 작업](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L54) | **부분** — 작업 템플릿·의존성·단계 projection은 있으나 재사용 DAG 실행 engine은 없다. | **조건부** — H24에 앞서 두 단계의 입출력·완료 근거·명시 시작을 기존 서비스로 표현한다. 관련: H24, OP05. | [E02](#e02) · [E04](#e04) · [E12](#e12) | [G03](#g03): 재연결/중복 명령에 단계 재호출·소비 삭제 없음. |
| [H28 같은 작업에서 검토·수정·재검토](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L55) | **부분** — 격리 공개 뒤 검토→별도 수정 판→다른 작성자 재검토는 구현됐으나 일반 팀원 검토는 아직 설계다. | **좁혀도입** — 기존 GR-1→GR-2→GR-3 순서로 일반 검토·수정·선택 판 취합까지 각각 완성한다. 관련: O11, O12, OP06. | [E05](#e05) · [E06](#e06) | [G04](#g04): 일반 collected 유지·자기 자료 범위·선택 판/hash·미해결 연결. |
| [H29 남은 예산·체크포인트·질문](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L56) | **부분** — 호출 예산과 상태/질문 대기는 보이지만 모델의 중간 체크포인트를 저장·회수하는 계약은 없다. | **좁혀도입** — 우선 남은 원장 예산·차단 이유를 같은 화면에서 읽고 체크포인트는 긴 일반 작업에만 검토한다. 관련: O15, OP04. | [E09](#e09) · [E04](#e04) | [G03](#g03): 진행 표시·체크포인트 저장 완료·자손 종료를 구분. |
| [H30 용량·동시성·재시도 제어](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L57) | **부분** — 정상 공식 배선의 현재 원장에는 공통 호출 상한·동시 자리·unknown 차단이 있으나 자동 재시도 정책/circuit breaker는 없다. | **유지** — 현재 무환불·unknown 보유를 유지하고 새 재시도는 검증된 시작 전 실패 등 좁은 경우만 검토한다. 관련: OP04, OP09. | [E09](#e09) · [E10](#e10) | [G03](#g03): 마지막 슬롯 경쟁·시작 전 거절·호출 후 실패·미확정 종료 구분. |
| [H31 작업별 Git 사본·변경 검토](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L58) | **운영 채택** — 개발 세션은 브랜치/PR로 작업하지만 앱에는 코드 writer·worktree 생성/병합 executor가 없다. | **조건부** — 코딩 모드가 필요할 때 한 writer의 사본·diff·PR 연결만 별도 실행 계약으로 붙인다. 관련: O28, H53, H56. | [E23](#e23) · [E15](#e15) | [G12](#g12): 사용자 미커밋 변경·충돌·writer 소유권·프로세스 격리를 별도로 확인. |
| [H32 여러 관점 프리셋·조언 주기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L59) | **부분** — 독립 초안·선택적 합성·저장 템플릿은 있으나 자동 조언 주기나 동적 MoA 정책은 없다. | **유지** — 빠른 비교/반례 우선 등 이름 있는 설정을 현재 템플릿으로 표현한다. 관련: O32, O33. | [E02](#e02) · [E13](#e13) · [E15](#e15) | [G10](#g10): 독립 초안과 공개 뒤 조언을 구분해 단독 대비 비용/효과 확인. |
| [H33 일회·반복 예약](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L65) | **미구현** — 사용자 작업을 일회/반복 예약하는 scheduler와 예약 실행 기록은 없다. | **보류** — 지속 실행 OP02의 수요·기기 운영이 정해진 뒤 예약 한 종류만 검토한다. 관련: OP02, H34. | [E17](#e17) · [E04](#e04) | [G03](#g03): 시간대·꺼진 PC·누락 예약·중복 실행·관측 만료·누적 상한 확인. |
| [H34 모델 없는 예약 작업](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L66) | **미구현** — readiness/주기적 상태 조회는 모델 없이 돌지만 사용자가 정한 무모델 작업 예약기는 없다. | **조건부** — 실제 필요한 관측 만료/CI 확인은 기존 운영 도구를 먼저 사용하고 앱 예약기를 필수화하지 않는다. 관련: H33, H62. | [E14](#e14) · [E19](#e19) · [E23](#e23) | [G10](#g10): 반복할 작업·실패 후 행동·운영 소유자를 지정하고 모델 호출 0 유지. |
| [H35 이벤트로 시작하기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L67) | **미구현** — 외부 webhook이 앱 작업을 생성하는 경로는 없다. | **보류** — 외부 자료/PR 변경이 반복 업무가 될 때 실행 대신 검토 대기 항목 수신부터 검토한다. 관련: OP07, O30. | [E22](#e22) · [E04](#e04) | [G12](#g12): 서명·중복 delivery·다른 저장소 오배정·입력 자료 권한 확인. |
| [H36 세션 감시·반복 프롬프트](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L68) | **부분** — 코드 기반 polling·종료 대기 감시는 있으나 모델의 loop/heartbeat 반복 프롬프트는 없다. | **유지** — 현 상태 감시를 유지하고 해석 호출은 실제 변화와 별도 예산이 있을 때만 추가한다. 관련: H24, H34. | [E17](#e17) · [E19](#e19) | [G03](#g03): 변화 없는 감시가 모델 호출·중복 후속 실행을 만들지 않기. |
| [H37 결과 전달·수신함 복구](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L69) | **부분** — 로컬 수신함은 현재 원장의 문제/내 차례를 재계산하지만 전달 ACK·재전달·파일 배달 기록은 없다. | **조건부** — OP11에서 놓친 결과가 확인될 때 로컬 읽음/대기 처리 필요부터 판단한다. 관련: H06, OP11. | [E04](#e04) · [E19](#e19) | [G06](#g06): 다시 열 때 같은 항목·현재 판·다음 행동 회복; 읽음을 해결로 세지 않기. |

### H38–H53: 도구·자료·상호작용

| 후보·원문 | 현재 상태와 경계 | 권고·다음 범위 | 코드 접점 | 검증 게이트 |
|---|---|---|---|---|
| [H38 선택한 MCP·toolset](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L75) | **미구현** — 제품의 작업별 MCP/toolset 선택은 없고 현 논의자 계약은 도구 표면을 제한한다. | **조건부** — 일반 역할의 자료 수집 하나에 필요한 도구만 별도 계약/관측으로 연결한다. 관련: H39, H40. | [E15](#e15) · [E03](#e03) | [G09](#g09): 도구 권한·설정 변화·기억 범위·격리 참여자 계약을 각각 재검증. |
| [H39 필요한 도구만 검색·설명 로딩](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L76) | **미구현** — 앱에 도구 검색→설명→호출 registry가 없다. | **보류** — H38의 연결 도구가 실제로 많아지고 설명 비용이 측정된 뒤 선택 로딩을 검토한다. 관련: H38. | [E15](#e15) · [E03](#e03) | [G10](#g10): 검색 누락·미설치·왕복 지연·전달 토큰의 변화를 함께 비교. |
| [H40 플러그인·화면 확장 슬롯](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L77) | **미구현** — 서비스 분리는 되었지만 외부 플러그인 manifest·화면 slot·권한 SDK는 없다. | **보류** — 확장 한 종류가 필요할 때 기존 ingestion/보고서 경계에 작은 내부 인터페이스부터 둔다. 관련: H23, H38. | [E11](#e11) · [E22](#e22) | [G12](#g12): 버전 불일치·해제·실패가 기존 입력/공개/호출을 깨지 않기. |
| [H41 native runtime adapter](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L78) | **부분** — 공식 CLI 일회 실행 adapter는 있지만 대화 thread/turn을 유지하는 native app-server runtime은 없다. | **조건부** — 일반 역할의 긴 세션·resume가 필요한 경우에만 현재 exec와 비교한다. 관련: O15, OP09. | [E15](#e15) · [E10](#e10) | [G09](#g09): 새 session 수명·입력 전달·중복 재개·취소·사용량을 해당 PC에서 관측. |
| [H42 편집기 연결 ACP](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L79) | **미구현** — 편집기 ACP 연결과 편집기 승인/diff 경로는 없다. | **보류** — 코딩 모드 H31이 실제 요구가 될 때 먼저 공개 결과 읽기 연동만 검토한다. 관련: H31, O28. | [E22](#e22) · [E15](#e15) | [G12](#g12): controller 상태 정본·writer 소유권·protocol 판·취소의 책임 구분. |
| [H43 다른 UI를 위한 API](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L80) | **부분** — 로컬 HTTP API와 Host/Origin/token 경계는 있으나 타 UI용 버전 계약/SDK는 없다. | **조건부** — 실제 두 번째 UI가 필요하면 공개 읽기 계약부터 고정하고 원시 모델 proxy는 만들지 않는다. 관련: OP01, OP09. | [E22](#e22) · [E01](#e01) | [G01](#g01): 직접 ID·동시/중복 요청·봉인·출력 제한·실행 상한 대조. |
| [H44 원격 실행·여러 기기·메신저](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L81) | **미구현** — 다른 기기의 worker/원장·메신저 원격 조작은 연결하지 않았다. | **보류** — 원격 수요가 생기면 읽기 전용 상태/보고서 열람을 먼저 비교한다. 관련: H57, OP02. | [E14](#e14) · [E22](#e22) | [G12](#g12): 기기·원장·관측 등록을 구분하고 다른 PC 기록으로 실행 허가하지 않기. |
| [H45 PDF·Office·노트북 추출](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L87) | **부분** — 쪽/줄 지정 PDF 추출은 있지만 Office·노트북 전용 변환은 없다. | **좁혀도입** — 반복 사용하는 문서 형식 하나만 기존 ingestion 계약으로 추가한다. 관련: H03, H46. | [E11](#e11) | [G08](#g08): 원본/도구/위치/누락·표/수식/한글 추출 오류를 함께 표시. |
| [H46 스캔 누락 경고·선택 OCR](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L88) | **부분** — PDF의 글 없는 쪽 목록과 전부 비면 거절하는 경고는 있으나 OCR 실행은 없다. | **조건부** — 스캔 자료가 반복될 때 사용자가 고른 쪽의 OCR만 추가하고 원 추출과 구분한다. 관련: H45. | [E11](#e11) | [G08](#g08): 빈 쪽과 스캔 누락 구분·수식/표/한글 오독·선택 쪽 비용 확인. |
| [H47 웹 검색·본문 추출·캐시](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L89) | **부분** — 사람이 지정한 공개 URL의 본문/범위/출처 고정은 있으나 웹 검색 backend·공용 캐시는 없다. | **좁혀도입** — 현재 추출의 실패/누락을 먼저 보완하고 검색은 자료 선택 요구가 생긴 범위만 연결한다. 관련: H03, H48. | [E11](#e11) | [G08](#g08): 검색 요약을 원문으로 취급하지 않고 redirect·변경 시각·누락 확인. |
| [H48 브라우저로 자료 선택](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L90) | **미구현** — 앱이 브라우저 요소를 조작하거나 화면에서 자료를 선택하는 기능은 없다. | **보류** — 동적 자료가 URL 추출로 부족한 실제 경우에 사람이 확인한 자료 첨부부터 유지한다. 관련: H47. | [E11](#e11) · [E03](#e03) | [G12](#g12): 세션 권한·캡처 범위·개인 자료를 확인하고 소비자 AI 앱 자동 조작과 분리. |
| [H49 이미지 입력·시각 결과](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L91) | **미구현** — 실행 입력과 답 계약은 텍스트 중심이며 이미지 입력/시각 결과 pipeline은 없다. | **조건부** — 도표·설계 이미지 판단이 실제 과제일 때 한 입력 형식과 모델 계약부터 관측한다. 관련: H45. | [E03](#e03) · [E15](#e15) | [G09](#g09): 이미지 bytes/hash·전달 지원·출력 취급·보고서 원문 보존 확인. |
| [H50 말로 입력·답 읽어주기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L92) | **미구현** — 음성 입력·TTS 출력은 제품 경로에 없다. | **보류** — 접근성 또는 음성 사용 요구가 있을 때 텍스트 입력 전후 변환으로만 검토한다. 관련: H49. | [E03](#e03) · [E22](#e22) | [G12](#g12): 전사 오독 수정·실행 전 입력 확인·재생/전송 범위 확인. |
| [H51 작업 화면 보기·사람에게 넘기기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L93) | **미구현** — 원본 앱 답 수동 참여와 달리 컴퓨터 화면 관찰/조작 handoff 기능은 없다. | **보류** — 화면을 통한 외부 작업이 필요한지 먼저 정하고 사람 인계와 실행 권한을 분리한다. 관련: H48, H52. | [E15](#e15) · [E22](#e22) | [G12](#g12): 현재 대상·진행 작업·권한 인계·중단 후 책임을 확인. |
| [H52 코드로 자료 가공](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L94) | **미구현** — 앱에는 자료 가공용 범용 코드 실행/산출물 계약이 없고 변환은 제한된 ingestion 경로다. | **조건부** — 반복 전처리 한 종류를 무모델 변환기로 붙인 뒤 코드 executor의 필요를 판단한다. 관련: H40, H45. | [E11](#e11) · [E15](#e15) | [G12](#g12): 입력/출력 상한·도구 판·파일 소유권·실패 격리·산출물 hash 확인. |
| [H53 편집 직후 진단](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L95) | **운영 채택** — 개발 시 CI/검토를 쓰지만 앱이 파일을 편집한 직후 진단하는 제품 기능은 없다. | **조건부** — H31의 writer를 추가할 때 변경 범위에 해당하는 기존 검사 결과를 연결한다. 관련: H31, O28. | [E23](#e23) · [E15](#e15) | [G11](#g11): 실제 검사 실행·대상 commit·실패 원문을 연결하며 체크 표시를 품질 보증으로 쓰지 않기. |

### H54–H62: 운영·비용·확장

| 후보·원문 | 현재 상태와 경계 | 권고·다음 범위 | 코드 접점 | 검증 게이트 |
|---|---|---|---|---|
| [H54 사용량·시간 분석](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L101) | **부분** — provider별 호출/토큰·미보고와 역할별 원장은 있으나 기간·실패·기억 영향의 종합 분석 화면은 없다. | **좁혀도입** — 기존 usage projection에 작업/역할/실패 비교만 추가해 중복 수집을 피한다. 관련: OP12, O13. | [E16](#e16) · [E09](#e09) | [G10](#g10): 구독 차감·CLI 토큰·정가 추정·미보고를 분리하고 추가 호출 0 유지. |
| [H55 진단·설정 UI·업데이트 안내](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L102) | **부분** — 기기/모델/관측 readiness와 설정 검증은 있으나 통합 doctor·업데이트/설정 UI는 없다. | **좁혀도입** — 사용 불가 이유와 SETUP의 다음 행동을 하나의 조회 화면으로 연결한다. 관련: OP10, H10, H62. | [E14](#e14) · [E17](#e17) | [G09](#g09): 설치/관측 등록/실행 가능을 구분하고 민감 경로·계정 값 노출 없음. |
| [H56 스냅숏·복구·보관](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L103) | **부분** — schema 변경 전 원장 백업은 있지만 파일/설정 부분 rollback·보관/복구 미리보기는 없다. | **조건부** — 먼저 백업 위치/대상 판과 읽기 전용 복구 검토를 마련하고 소비 원장은 과거 상태로 덮지 않는다. 관련: OP06, H31. | [E18](#e18) · [E09](#e09) | [G03](#g03): 모델 호출 후 복구가 소비 기록을 지우지 않고 실행 중 복구를 차단. |
| [H57 실행 backend 선택](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L104) | **부분** — mock/native와 관측된 Linux/WSL 실행 경계는 있으나 Docker/SSH/서버리스 backend 선택은 없다. | **보류** — 원격 기기 요구가 정해지기 전 현 executor를 유지한다. 관련: H44, OP09. | [E15](#e15) · [E14](#e14) | [G09](#g09): backend별 입력/인증/격리/자손 종료/관측을 각각 갖추기. |
| [H58 대체 모델·계정·provider 선택](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L105) | **부분** — 허용 목록에서 모델을 고를 수 있지만 자동 fallback·계정 pool·자격증명 routing은 없다. | **조건부** — 한도 후 다른 구독 구성으로 새 실행을 준비하는 명시적 안내만 우선 검토한다. 관련: O32, O33. | [E02](#e02) · [E09](#e09) · [E15](#e15) | [G09](#g09): 새 입력 동등성·보고 모델·새 원장 상한·자동 유료 전환 없음. |
| [H59 비밀을 모델 밖에서 취급](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L106) | **운영 채택** — 공식 CLI 로그인과 제한된 참여자 환경을 사용하며 앱의 비밀번호 금고는 만들지 않았다. | **유지** — 로그인 필요 상태와 사용자가 공식 경로로 해결하는 안내를 유지한다. 관련: H55, H58. | [E14](#e14) · [E15](#e15) | [G09](#g09): 모델 입력/공개 보고에 비밀을 넣지 않고 새 credential pool을 만들지 않기. |
| [H60 음악·홈 자동화·메신저 업무](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L107) | **미구현** — 음악·홈 자동화·메일/캘린더 업무 adapter는 제품에 없다. | **보류** — 의사결정의 후속 외부 행동이 반복 과제가 될 때 서비스 하나만 따로 검토한다. 관련: H35, H44. | [E22](#e22) | [G12](#g12): 대상 계정·전송/수정 내용·완료 확인·실패 재처리 책임을 먼저 고정. |
| [H61 여러 과제 비교 실행·재개](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L108) | **부분** — 단일 과제 headless 실행·순차 합성·결과 JSON은 있으나 batch 상태/이어하기 관리자는 없다. | **좁혀도입** — 기존 app.run을 작은 고정 과제 묶음의 비교 절차로 사용하고 재개 표식만 필요에 따라 더한다. 관련: O09, O33. | [E25](#e25) · [E09](#e09) | [G10](#g10): 과제/설정/실패/시간/소비를 같은 기준으로 비교하고 재개 중 중복 호출 없음. |
| [H62 서비스 건강·관측 이벤트](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L109) | **부분** — 원장 events·readiness·상태 polling은 있으나 지연/조회 오류/자원 압박의 통합 관측 화면은 없다. | **좁혀도입** — 기존 사건과 측정 도구로 드러난 장애의 다음 행동만 모델 없이 표시한다. 관련: H34, H55. | [E09](#e09) · [E14](#e14) · [E19](#e19) | [G06](#g06): 본문/인증을 로그에 더 싣지 않고 stale 값·접속 실패·실행 상태를 구분. |

### O01–O16: 기억·검토

| 후보·원문 | 현재 상태와 경계 | 권고·다음 범위 | 코드 접점 | 검증 게이트 |
|---|---|---|---|---|
| [O01 여러 방식으로 기억 찾기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L11) | **부분** — 한국어 부분 일치·완전 표현·희귀 표현 가중치를 쓰지만 FTS/형태소/embedding/RRF 다중 검색은 없다. | **조건부** — D05의 동의어·식별자 누락을 현재 lexical과 비교한 뒤 한 채널씩 도입한다. 관련: D02, D05, D10. | [E07](#e07) · [E21](#e21) | [G05](#g05): 관련 기록 누락·무관 기록·검색 지연을 같은 질의로 비교. |
| [O02 입력 예산 안의 다양한 근거](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L12) | **부분** — 기억의 section별/지적별 예산과 미해결 우선 발췌는 있으나 의미적 중복 제거·다양성 최적화는 없다. | **유지** — 현재 균등 발췌를 유지하며 긴 반례·중복 답의 실제 누락 사례로 다음 변경을 결정한다. 관련: D01, OP08. | [E07](#e07) · [E21](#e21) | [G05](#g05): 12,000 bytes 안에서 원문 반례와 처분의 포함 여부 확인. |
| [O03 왜 이 기억인가·다음 조회 안내](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L13) | **부분** — 선택 표현·일치 위치·생략·recent fallback·원 실행은 보이지만 추천 재질의/범위 확대는 없다. | **좁혀도입** — D01/H14에서 누락이 큰 섹션으로 바로 이동하는 안내를 더한다. 관련: D01, H14. | [E08](#e08) | [G05](#g05): 미검색·약한 일치·상한 탈락·원문 unavailable을 구분. |
| [O04 프로젝트·사건·세션 범위](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L14) | **부분** — 현재 자동 기억은 원장/작업 경계만 지원하고 프로젝트·사건·phase별 공유 정책은 없다. | **조건부** — 명시적 대상 작업의 자료 공유 D06부터 비교하고 전역 자동 범위는 넓히지 않는다. 관련: H12, D06. | [E07](#e07) · [E08](#e08) | [G02](#g02): 검색·직접 ID·가져오기·격리 역할에서 같은 범위 적용. |
| [O05 남길 기억·검토 대기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L15) | **미구현** — 사용자가 결론을 선택해 기억 후보/보류/승인으로 저장하는 별도 write gate는 없다. | **조건부** — D03의 구조화 결정이 필요해지면 수동 저장 미리보기부터 추가한다. 관련: D03, D04. | [E07](#e07) · [E05](#e05) | [G02](#g02): 저장 승인·실제 저장·새 실행 주입을 구분하고 과거 pack 보존. |
| [O06 결정의 교체·사건 이력](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L16) | **부분** — 사람 판단 사건·검토 처분·수정 부모 판은 있지만 결정을 대체하는 supersedes 객체는 없다. | **좁혀도입** — D03에 현재 결정·대체 이유·유효 범위의 명시적 기록만 먼저 도입한다. 관련: D03, D08. | [E05](#e05) · [E06](#e06) · [E24](#e24) | [G07](#g07): 옛 결론 보존·동시 교체·대체 순환·근거 없는 새 결론 확인. |
| [O07 모순·보류·미해결 기억](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L17) | **부분** — 수용한 검토의 unresolved/qualified를 기억에 남기지만 시점이 다른 결정의 모순 탐지/충돌함은 없다. | **조건부** — D03의 결정 참조가 생긴 뒤 D08에서 양쪽 근거를 사람이 비교하는 화면부터 만든다. 관련: D08, O06. | [E07](#e07) · [E05](#e05) | [G05](#g05): 범위/기간 차이를 모순으로 단정하거나 반례를 자동 폐기하지 않기. |
| [O08 기억 정리·망각·피드백](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L18) | **미구현** — 기억의 pin·수동 보관·복원·도움/무관 피드백·회고 통합은 없다. | **조건부** — D04에서 선택 제외와 되돌리기부터 도입하고 자동 망각은 평가 뒤 결정한다. 관련: D04, H22. | [E07](#e07) · [E08](#e08) | [G05](#g05): 오래됨/미사용이 진실성 판단을 대신하지 않고 과거 입력은 불변. |
| [O09 검색 품질 시험 세트](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L19) | **있음** — 고정 합성 검색 질의·정답 출처·금지 원문·관련/무관 기록·bytes/시간 평가가 구현돼 있다. | **유지** — 기존 평가셋에 사용자 과제의 실패를 비식별 사례로 추가하고 별도 평가 engine은 만들지 않는다. 관련: D05, H61. | [E21](#e21) | [G05](#g05): 합성 이득과 실사용 품질을 구분하며 알려진 한계는 제외 은폐하지 않기. |
| [O10 기억 내보내기·관리 화면·동기화](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L20) | **미구현** — 템플릿 파일 이동은 가능하지만 기억 항목 export/import·관리 console·동기화 outbox는 없다. | **조건부** — D06의 선택 공개 기억 묶음부터 만들고 외부 서비스 동기화는 필요가 생긴 뒤 별도 검토한다. 관련: D06, H17. | [E02](#e02) · [E08](#e08) | [G02](#g02): 중복/충돌/부분 실패/스키마와 대상 작업 범위 확인. |
| [O11 지적별 수정·반박·보류와 근거](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L28) | **부분** — 격리 실행에서 지적 처분·별도 수정·지적별 대응·재검토는 있지만 일반 팀원 대상은 없다. | **좁혀도입** — H28과 같은 GR-1/2 작업으로 진행해 기능을 별도로 중복 구현하지 않는다. 관련: H28, OP06. | [E05](#e05) · [E06](#e06) | [G04](#g04): 지적 ID·원문 hash·작성자·부모 판·남은 문제를 연결. |
| [O12 검토 범위·강도·멈춤 조건](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L29) | **부분** — 검토 질문·한 라운드·순차 실행·실패 정지/수정 상한은 있으나 core/integrity 프로필·추론 강도 연결은 없다. | **좁혀도입** — 먼저 GR-1의 검토 범위를 입력 미리보기로 명확히 하고 프로필은 반복 사용 후 템플릿으로 추가한다. 관련: H28, H02. | [E05](#e05) · [E06](#e06) · [E15](#e15) | [G04](#g04): 범위 밖 지적·필수 수정·상한·미실행 검토자를 구분. |
| [O13 요청한 모델과 실제 응답 대조](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L30) | **부분** — Outcome은 요청/보고 모델과 미보고를 구분하며 사용량도 미상을 유지하지만 새 CLI 필드/추론 설정은 미연결이다. | **유지** — 기존 관측값만 표시하고 화면 필드 확장은 PC 관측에 맞춘다. 관련: H54, OP09. | [E16](#e16) · [E15](#e15) | [G09](#g09): 미보고를 일치/불일치로 추측하지 않고 requested/reported 원자료 대조. |
| [O14 검토 중·반영 중·미완 표시](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L31) | **부분** — 실행·검토·수정·재검토의 단계/미확정은 보이지만 일반 검토 왕복은 아직 없다. | **좁혀도입** — GR-1을 공개 조회·단계·검색·사용량까지 한 사용자 흐름으로 완성한다. 관련: H28, OP12. | [E04](#e04) · [E05](#e05) · [E06](#e06) | [G04](#g04): 옛 검토를 새 답 완료로 재사용하지 않고 미실행/미완을 표시. |
| [O15 세션 연결·긴 검토 회수](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L32) | **부분** — 실행/attempt ID와 restart unknown 회수는 있지만 verifier 세션 유지·native resume는 없다. | **조건부** — GR-1의 재연결은 기존 원장으로 해결하고 긴 대화 resume는 H41의 별도 관측으로 검토한다. 관련: H41, OP01. | [E09](#e09) · [E10](#e10) · [E15](#e15) | [G03](#g03): 화면 timeout·실제 종료·새 호출을 구분하고 재시작에 재호출하지 않기. |
| [O16 규칙·지식 지도·출처 재확인](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L33) | **운영 채택** — 개발용 규칙·기능/코드 지도·SHA 고정 출처는 있지만 앱의 규칙 후보/승인/동적 freshness engine은 없다. | **좁혀도입** — 기존 문서 지도와 출처를 사용하고 H19에 필요한 짧은 절차만 명시적으로 선택한다. 관련: H19, D03. | [E24](#e24) · [E02](#e02) | [G11](#g11): 현재 코드와 날짜 설계를 구분하고 읽지 않은 전역 지식을 자동 주입하지 않기. |

### O17–O34: 인계·운영·협업·디자인

| 후보·원문 | 현재 상태와 경계 | 권고·다음 범위 | 코드 접점 | 검증 게이트 |
|---|---|---|---|---|
| [O17 세 줄 작업 요약](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L41) | **부분** — 작업 단계·다음 행동·막힘은 projection으로 보이고 개발 카드 체크포인트도 있지만 의미적 세 줄 요약은 없다. | **유지** — 기존 현재/다음/막힘 표시를 유지하고 원문 근거 이동만 보완한다. 관련: H15, D03. | [E04](#e04) · [E23](#e23) | [G07](#g07): 계획 변경·새 결과·unknown 뒤에도 현재 행동이 원문 상태와 일치. |
| [O18 관측·해석·결정 분리](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L42) | **부분** — CLI 관측·모델 답·사람 판단/처분은 분리하지만 범용 관측/해석/결정 지식 객체는 없다. | **유지** — 새 필드를 만들기 전에 기존 사건/판정 이름으로 현재 근거와 해석을 표시한다. 관련: D03, O06. | [E16](#e16) · [E05](#e05) · [E24](#e24) | [G01](#g01): AI 답/인용 일치를 관측 사실·사람 판단 완료를 사실 검증으로 승격하지 않기. |
| [O19 실패한 가설·배제 이유 재사용](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L43) | **운영 채택** — 실패 가설·배제 이유는 개발 날짜 기록에 보존하지만 앱에 구조화된 ruled_out 기억은 없다. | **좁혀도입** — D03이 필요할 때 배제 조건·다시 볼 계기·근거를 사람 기록으로 추가한다. 관련: D03, O16. | [E24](#e24) · [E07](#e07) | [G11](#g11): OS·버전·과제가 바뀌었는데 예전 배제를 영구 규칙으로 주입하지 않기. |
| [O20 다음 행동·담당·입력 계약](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L44) | **부분** — 개발 카드와 앱의 분담 사본/선행/내 차례에는 담당·입력·다음 행동이 있으나 일반 메시지 인계는 없다. | **유지** — 현재 클릭 가능한 다음 행동을 유지하며 전달/소비 상태는 OP07로 분리한다. 관련: OP07, OP11. | [E03](#e03) · [E04](#e04) · [E23](#e23) | [G07](#g07): 미정 담당·누락 자료·새 계획에서 잘못된 실행을 시작하지 않기. |
| [O21 현재 요약에서 증거로 확대](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L45) | **있음** — 작업/타임라인/수신함은 페이지로 읽고 선택한 실행 상세에서 원문을 펼친다. | **유지** — 기존 공개 조회를 모든 새 화면에서 재사용하고 cold 집계의 선형 비용은 측정으로 관리한다. 관련: OP01, OP12. | [E01](#e01) · [E19](#e19) | [G01](#g01): 목록이 답/자료 전문을 싣지 않고 페이지 밖 선택과 전체 상태를 유지. |
| [O22 화면을 닫아도 작업 찾기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L53) | **부분** — 원장 기록은 남지만 현재 launcher는 닫기 요청 후 호출이 끝나면 서버를 종료한다. | **조건부** — 지속 실행이 필요하면 OP02의 명시적 별도 모드를 설계하고 현재 자동 종료 기본값은 유지한다. 관련: OP02. | [E17](#e17) · [E10](#e10) | [G06](#g06): 같은 원장/실행 재연결과 crash/unknown/완료 구분. |
| [O23 상태 구독·변경분·출력 억제](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L54) | **부분** — 선택 상세 조회·페이지·변경 없는 projection 재사용·늦은 응답 폐기는 있지만 SSE/변경 cursor 구독은 없다. | **유지** — 먼저 polling 비용/사용 불편을 측정하고 필요한 경우에만 revision/변경분을 도입한다. 관련: OP01. | [E19](#e19) | [G06](#g06): 구독으로 확대할 때 초기 snapshot과 변경 replay 사이의 누락 없음. |
| [O24 찾기·여러 창·문맥별 조작](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L55) | **부분** — 작업 이동·검색·원문 비교는 있으나 범용 여러 창/분할 상태 저장은 없다. | **조건부** — H08/OP03에서 기존 선택 실행을 고정하는 비교 편의만 추가한다. 관련: H08, OP03. | [E20](#e20) · [E19](#e19) · [E01](#e01) | [G06](#g06): 다른 실행으로 전환 중 명령이 잘못된 대상에 적용되지 않기. |
| [O25 막히지 않은 일·원자적 가져가기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L63) | **운영 채택** — GitHub 카드의 수동 가져가기 절차와 앱 선행 확인은 있으나 다중 세션 원자적 claim은 없다. | **조건부** — 충돌 사례가 반복될 때만 GitHub 원본 상태와 양립하는 claim 방법을 좁게 검토한다. 관련: H26, OP04. | [E23](#e23) · [E04](#e04) | [G11](#g11): 두 세션 경쟁을 실제로 검증하며 GitHub 두 요청을 로컬 거래처럼 취급하지 않기. |
| [O26 명세·계획·완료 기준 양식](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L64) | **있음** — 개발 카드 양식과 앱 목표·완료 기준·선행 계획 저장은 구현/운영 중이다. | **유지** — 간단한 일은 현재 양식을 사용하고 요구별 자동 검증/증거 객체는 OP05의 별도 범위로 둔다. 관련: OP05, D07. | [E04](#e04) · [E23](#e23) | [G07](#g07): 완료 조건 변경 시 새 계획/실행을 요구하고 과거 근거를 조용히 재사용하지 않기. |
| [O27 대규모 작업의 의존성·병합·감시](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L65) | **부분** — 작은 작업의 의존성/막힘 projection은 있지만 대규모 convoy·병합·자동 감시 engine은 없다. | **보류** — 앱의 두 provider 읽기 전용 실행에 필요한 선행 목록과 개발 협업의 한 writer 원칙을 유지하며, 규모 근거 전에는 엔진을 확대하지 않는다. 관련: H24, H27, O25. | [E04](#e04) · [E09](#e09) · [E23](#e23) | [G10](#g10): 작업 수가 아닌 반복 병목·복구 부담·총 호출 비용으로 확대 판단. |
| [O28 병렬 사본과 한곳의 diff 검토](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L66) | **운영 채택** — 개발 브랜치/PR/diff 검토는 하지만 앱에서 병렬 worktree·수정 실행·PR 생성은 지원하지 않는다. | **조건부** — H31의 코딩 확장에서 사본/변경 검토를 하나의 범위로 묶는다. 관련: H31, H53. | [E23](#e23) · [E15](#e15) | [G12](#g12): 동시 파일 수정·이중 commit·미커밋/ignored 파일 보존·한 writer 확인. |
| [O29 조정자와 작은 작업자·직접 교정](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L67) | **부분** — 일반 팀원 분담과 상위 역할의 제안/취합은 있으나 실행 중 질문/직접 교정 경로는 없다. | **좁혀도입** — GR-1의 일반 결과 검토를 먼저 끝낸 뒤 OP07의 다음 입력 메시지를 검토한다. 관련: H25, H28, OP07. | [E03](#e03) · [E12](#e12) · [E04](#e04) | [G04](#g04): 과제 소유권·취소·자료 범위·호출 회계를 같은 원장으로 확인. |
| [O30 한 작업·한 산출물·비동기 검토](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L68) | **운영 채택** — 개발 카드→브랜치/PR→CI 연결은 운영하지만 앱의 cloud coding agent/PR 산출물 pipeline은 없다. | **좁혀도입** — 현재 카드의 실행/문서/PR 링크를 분명히 하고 앱 산출물 목록은 H07로 연결한다. 관련: H07, OP11. | [E23](#e23) · [E04](#e04) | [G11](#g11): 작업/산출물/검토/CI가 같은 기준 commit을 가리키는지 확인. |
| [O31 짧은 현재 문맥과 필요할 때 읽는 이력](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L69) | **부분** — 현재 상태와 긴 원문을 나누고 제한 기억 발췌를 보내지만 모델 요약/다른 thread 자동 참조는 없다. | **조건부** — H15/D03을 유지하며 장문 일반 세션에서만 OP08 압축 비교를 검토한다. 관련: H18, OP08. | [E07](#e07) · [E19](#e19) | [G05](#g05): 반례/최근 조건 손실·중복 읽기·추가 요약 비용을 비교. |
| [O32 계획 모델과 실행 모델을 따로](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L70) | **부분** — 상위 계획 역할과 일반/격리 팀원은 구분하고 모델 선택을 저장하지만 자동 가격/품질 라우팅은 없다. | **유지** — 실제 검증한 모델 조합을 H02 템플릿으로 사용한다. 관련: H02, H32, O33. | [E02](#e02) · [E12](#e12) · [E15](#e15) | [G10](#g10): 저가 모델의 재시도/검토까지 포함한 전체 비용과 품질 비교. |
| [O33 선택적 라우터·후보 답 합성](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L71) | **부분** — 선택적 공개 후 합성은 있으나 Jev/Lite-Harness형 router·자동 단독/ensemble 선택은 없다. | **조건부** — H61의 과제별 비교로 합성이 유용한 조건을 정한 뒤 단순 선택 정책만 검토한다. 관련: H32, H58, H61. | [E13](#e13) · [E25](#e25) | [G10](#g10): 단독/독립 초안/합성을 같은 과제에서 비용·누락·오답으로 비교. |
| [O34 디자인 부품과 반복 UI 양식](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L72) | **있음** — island-ui의 테마·간격·모션 부품을 실제 화면에서 사용하고 원본 우선 수정 절차가 있다. | **유지** — 검색·검토·수신함의 새 UI도 같은 부품을 사용한다. 관련: H11, OP12. | [E20](#e20) · [E26](#e26) | [G06](#g06): 테마 대비·모션 감소·작은 화면을 확인하고 복사본만 따로 변경하지 않기. |

### D01–D10: 로컬 부품 채택 후보

| 후보·원문 | 현재 상태와 경계 | 권고·다음 범위 | 코드 접점 | 검증 게이트 |
|---|---|---|---|---|
| [D01 선택 이유와 실제 입력 미리보기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L22) | **있음** — 새 pack의 선택 이유·생략·원 실행·실제 보낼 입력과 hash를 미리 볼 수 있다. | **유지** — 현재 서랍을 유지하며 위치 이동/제외 같은 후속은 H14/D04에서 별도로 다룬다. 관련: H14, O03, D04. | [E08](#e08) · [E27](#e27) | [G05](#g05): 옛 이유 추정 없음·미리보기 이후 변경 재확인·일반/격리 입력 차이 유지. |
| [D02 원문 검색과 최신성](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L32) | **부분** — 공개 원문/검토 검색과 원 실행 이동은 있으나 FTS 인덱스·stale 재구축·검색 결과 직접 첨부는 없다. | **좁혀도입** — 현재 lexical 검색의 실제 실패를 D05에 추가하고 오래된/누락 근거 표시부터 개선한다. 관련: H13, O01, OP03. | [E01](#e01) · [E08](#e08) · [E19](#e19) | [G05](#g05): 선택한 snippet이 같은 원문을 가리키고 손상/삭제/다른 task를 구분. |
| [D03 작업 복귀 요약과 결정 이력](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L42) | **부분** — 상태·다음 행동·판단 사건·수정 lineage는 있으나 decision/constraint/ruled_out/supersedes 선언은 없다. | **좁혀도입** — 반복 인계에 필요한 현재 결정·근거·대체 이유의 수동 기록부터 추가한다. 관련: O06, O17, O19. | [E04](#e04) · [E05](#e05) · [E06](#e06) | [G07](#g07): A→B 교체·B 보류·동시 선언·근거 누락·순환을 구분. |
| [D04 기억 관리: 핀·제외·수정·되돌리기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L52) | **미구현** — 기억 사용 전체 켜기/끄기는 있으나 항목별 pin·제외·교체·되돌리기는 없다. | **조건부** — 자동 선택 오류가 반복되면 먼저 항목 제외/되돌리기와 누락 이유만 도입한다. 관련: O08, H12. | [E07](#e07) · [E08](#e08) | [G05](#g05): 동시 변경·pin/제외 충돌·예산 초과·과거 pack 불변 확인. |
| [D05 검색 평가와 단계적 개선](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L62) | **부분** — 합성 평가/확장 fixture와 lexical 개선은 반영됐으나 사용자 피드백 UI·형태소/RRF 비교·실사용 정답셋은 없다. | **유지** — 기존 평가 도구에 실패 사례를 더하고 새 알고리즘은 한 번에 한 변수만 비교한다. 관련: O09, O01, OP08. | [E21](#e21) · [E07](#e07) | [G05](#g05): known_limit을 숨기지 않고 합성셋 향상을 실사용 품질로 확대하지 않기. |
| [D06 명시적 공유와 이동 가능한 기억 묶음](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L72) | **미구현** — 템플릿 이동과 달리 다른 작업에 결정/기억/관계를 선택 공유하는 bundle은 없다. | **조건부** — 여러 작업 간 재사용 수요가 확인되면 target_task 필수의 읽기 미리보기부터 만든다. 관련: O04, O10, H17. | [E02](#e02) · [E08](#e08) | [G02](#g02): new/duplicate/conflict/rejected와 누락 relation·부분 실패를 구분. |
| [D07 팀·작업 양식과 스킬 서랍](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L82) | **부분** — 팀·작업·자료 템플릿 저장/복원은 있지만 skill_refs·source slot·pin·사용 흔적을 갖춘 서랍은 없다. | **좁혀도입** — 기존 템플릿에 H19의 명시 선택 절차 하나를 연결하는 정도로 제한한다. 관련: H02, H19, H20. | [E02](#e02) · [E27](#e27) | [G02](#g02): 오래된 카드/모델·변경된 절차·누락 자료를 재검사하고 과거 실행 유지. |
| [D08 결정 충돌함](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L92) | **미구현** — 교차검토 지적 처분은 있어도 서로 다른 시점의 결정 간 conflict 객체/화면은 없다. | **조건부** — D03의 명시 결정과 근거 참조 뒤 같은 대상의 충돌 후보를 사람이 비교한다. 관련: O06, O07, D03. | [E05](#e05) · [E07](#e07) | [G05](#g05): 시간/범위 차이·표현 차이·실제 충돌·근거 손상을 구분. |
| [D09 필요한 백그라운드 작업만 관리하기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L102) | **부분** — 로컬 수신함/unknown 표시는 있지만 인덱싱·알림 job용 durable queue/outbox는 없다. | **조건부** — OP11의 읽기 수신함을 유지하고 실제 비동기 부수 작업이 생길 때만 작은 큐를 검토한다. 관련: OP11, H37. | [E04](#e04) · [E19](#e19) | [G03](#g03): 기존 CLI 실행을 새 큐에서 이중 관리하지 않고 stale 완료/재시도 중복 방지. |
| [D10 규모가 커질 때 선택하는 확장](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L112) | **미구현** — 임베딩·생성 질문 인덱스·회고·관계 그래프·외부 기억 서버는 제품에 없다. | **보류** — D05로 드러난 구체적인 검색/공유 한계를 풀 때 해당 확장 하나만 비교한다. 관련: O01, D05, D06. | [E07](#e07) · [E21](#e21) | [G10](#g10): 검색 이득·메모리/지연·갱신/복구·추가 모델/서버 비용을 함께 확인. |

### OP01–OP12: 운영 적용 후보

| 후보·원문 | 현재 상태와 경계 | 권고·다음 범위 | 코드 접점 | 검증 게이트 |
|---|---|---|---|---|
| [OP01 원장에 다시 붙기와 처리 단계 표시](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L24) | **부분** — 선택 실행/페이지·늦은 응답 폐기·재조회는 있지만 ledger_id+전역 revision·명령 receipt 계약은 없다. | **좁혀도입** — 현재 원장/실행 식별을 명확히 하고 중복/재접속이 실제 문제인 명령부터 receipt를 검토한다. 관련: O21, O23, O15. | [E19](#e19) · [E22](#e22) · [E10](#e10) | [G06](#g06): 원장 전환·끊긴 응답·중복 요청에서 같은 작업을 조회하고 모델 재호출 없음. |
| [OP02 명시적인 지속 실행 모드](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L34) | **미구현** — 창 닫기 후 호출 종료를 기다려 서버를 내리는 동작과 별개인 지속 실행 모드는 없다. | **조건부** — 오래 걸리는 일반 작업의 재접속 필요가 확인되면 명시적 모드와 discovery/owner 수명을 설계한다. 관련: O22, H33. | [E17](#e17) · [E10](#e10) | [G09](#g09): browser/server crash·stale owner·같은 원장 중복 소유·종료 중 재접속을 PC에서 확인. |
| [OP03 작업 탐색·저장된 필터·명령 palette](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L42) | **부분** — 작업/종류/문구 검색과 페이지 이동은 있으나 저장 필터·상태/기간 필터·명령 palette는 없다. | **좁혀도입** — H01/H09와 같은 UI 작업으로 저장된 조회와 대상에 맞는 읽기/이동 명령부터 추가한다. 관련: H01, H09, O24. | [E01](#e01) · [E19](#e19) | [G06](#g06): 오래된 필터 빈 결과·한글 조합 입력·대상 전환 중 명령 오류 확인. |
| [OP04 준비·담당·용량을 나눈 작업판](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L50) | **부분** — 정상 공식 배선의 현재 원장에는 선행 readiness·슬롯/상한/unknown·배정 사본·invocation 시작 CAS가 있지만 다중 기기/worker의 lease·heartbeat 기반 작업 claim·원격 카드 동기화는 없다. | **유지** — 현재 준비/용량 projection을 유지하고 자동 소유권은 실제 경쟁 사례 뒤에만 도입한다. 관련: H26, H30, O25. | [E04](#e04) · [E09](#e09) · [E10](#e10) | [G03](#g03): 준비/소유/용량을 구분하며 unknown·CAS 실패·저장 실패 후 재호출 없음. |
| [OP05 명세와 완료 증거가 연결된 작업 양식](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L60) | **부분** — 목표·완료 기준·계획 판·선행 결과 근거는 있지만 요구별 evidence_refs/verification_state 연결은 없다. | **좁혀도입** — 반복 중요 과제에 한해 완료 조건에서 공개 결과/검토 근거로 이동하는 연결을 추가한다. 관련: O26, D07. | [E04](#e04) · [E27](#e27) | [G07](#g07): 요구 변경 뒤 옛 증거·모델의 done·사람 판단 완료를 각각 구분. |
| [OP06 판 비교·실행 fork·복구 미리보기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L68) | **부분** — 격리 수정의 부모 판/원문 hash/전후 비교는 있지만 run fork·입력 diff·파일 복구 계획은 없다. | **좁혀도입** — GR-1/2/3 이후 필요한 실행 복제와 읽기 비교를 H05와 묶고 파일 복구는 H31로 분리한다. 관련: H05, H28, H56. | [E06](#e06) · [E03](#e03) | [G04](#g04): 선택 판·원본/새 입력·소비 보존·오래된 검토 판의 재사용 방지. |
| [OP07 다음 단계 메시지와 전달 상태](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L76) | **미구현** — 다음 단계 제안을 새 실행에 묶을 수 있지만 사용자 메시지의 pending/consumed/withdrawn/expiry 계약은 없다. | **조건부** — 일반 팀원 검토 이후 추가 조건을 다음 입력에 넣는 필요가 확인되면 입력 hash에 결속된 대기 메시지부터 만든다. 관련: H04, O20, O29. | [E12](#e12) · [E03](#e03) | [G03](#g03): 소비 직후 crash·중복 전달·입력 고정 후 편집·격리 답 유입 방지. |
| [OP08 문맥 예산과 압축 실험](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L84) | **부분** — 기억 bytes/생략·섹션 발췌·평가셋은 있지만 tokenizer 기반 보장이나 모델 압축 실험 pipeline은 없다. | **유지** — 현 pack 범위의 반례 보존 평가를 유지하고 긴 일반 세션에서만 H18의 별도 압축을 비교한다. 관련: D05, H18, O31. | [E07](#e07) · [E21](#e21) · [E27](#e27) | [G05](#g05): bytes와 measured tokens 구분·CLI 내부 문맥 미통제·원문 재조회 가능성 확인. |
| [OP09 어댑터의 공통 계약과 capability 표](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L92) | **부분** — runtime-inventory/2에는 기기/version/plan revision에 묶인 설치·인증·전송·문맥·권한 관측이 있으나 resume/steer/stream 등 세부 capability 지원표와 범용 frame schema는 없다. | **좁혀도입** — 기존 관측을 재사용해 세부 capability의 지원/미지원/미관측을 연결하는 얇은 표부터 만들고 새 runtime 도입 시 검증한다. 관련: H41, H57, O13. | [E09](#e09) · [E14](#e14) · [E15](#e15) · [E16](#e16) · [E28](#e28) | [G09](#g09): 누락 usage·EOF·native 오류·stderr 거절·잔류 child를 adapter와 acceptance 단계로 구분. |
| [OP10 실제 적용 설정과 마지막 정상판](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L100) | **부분** — 고정 입력/모델·템플릿 검증·schema 백업은 있으나 config provenance/last-good 활성화 관리자는 없다. | **조건부** — readiness와 현재 설정의 불일치 사례가 반복되면 적용판/hash·유효값 출처 조회부터 추가한다. 관련: H55, H56. | [E02](#e02) · [E14](#e14) · [E18](#e18) · [E27](#e27) | [G09](#g09): 검사 성공과 실제 CLI 적용을 구분하고 실행 manifest는 설정 변경 후에도 불변. |
| [OP11 다음 행동이 있는 수신함](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L108) | **부분** — 현재 작업에서 문제·내 차례·선행·미연결 unknown과 다음 행동을 계산하지만 read/delivery/outbox 상태는 없다. | **유지** — 기존 읽기 수신함을 사용하며 누락 사례가 생기면 H37/D09 범위만 좁혀 추가한다. 관련: H06, H37, D09. | [E04](#e04) · [E19](#e19) | [G06](#g06): 읽기/이동이 해결·전달 완료·모델 재시도를 의미하지 않기. |
| [OP12 공개 결과·작업자·산출물 비교 화면](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L116) | **부분** — 공개 답·수정 전후·검토/사용량을 비교하지만 일반 수정 판 취합·코딩 artifact/PR drawer는 없다. | **좁혀도입** — GR-1/2/3의 공개 결과/판을 같은 화면에 연결하고 artifact 확대는 실제 산출물 유형에 맞춘다. 관련: H07, O14, O34. | [E06](#e06) · [E16](#e16) · [E20](#e20) | [G01](#g01): 봉인 비노출·비교 중 새 결과·선택 판 hash·미관측 비용·다른 기기 관측을 구분. |

## 코드 근거

모든 링크는 기준 SHA `48ab4bd6f0e297587707aecb83ebc0cd9968892f`에 고정했다. 아래 범위가 이 문서 담당이 직접 읽은 핵심 코드 범위다. 개발 운영 근거(E23/E24/E26)는 코드 구현과 별도로 표시한다.

### E01

공개 문구 검색·발췌·원래 실행 연결.

- [app/queries/catalog.py:7–78](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/catalog.py#L7-L78) — `validate/search`.
- [app/queries/public.py:75–101](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L75-L101) — `PublicQueries.search/overview`.

### E02

편집 가능한 작업 설정 템플릿·현재 모델 재검사·해시 결속 파일 이동.

- [app/application/templates.py:15–124](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/templates.py#L15-L124) — `FIELDS/TemplateService`.

### E03

입력 준비와 같은 거래의 실행 생성·분담 사본·중복 실행 거절.

- [app/application/work.py:20–103](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/work.py#L20-L103) — `WorkService.create_run`.

### E04

계획 판·선행 조건·준비 상태·단계·로컬 수신함.

- [app/application/tasks.py:14–92](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/tasks.py#L14-L92) — `TaskService.save/require_ready`.
- [app/workflow.py:24–163](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/workflow.py#L24-L163) — `steps/project_tasks/inbox/admission/unattached_inputs`.

### E05

격리 공개 뒤 교차검토·지적 처분·사람 판단.

- [app/application/reviews.py:84–246](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/reviews.py#L84-L246) — `cross_review/_advance_reviews/set_review_disposition/mark_reviewed`.

### E06

격리 답변의 별도 수정 판·근거 고정·재검토·상한.

- [app/application/revisions.py:28–165](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/revisions.py#L28-L165) — `RevisionService._context/prepare/revise/recheck`.
- [app/static/revisions.js:44–71](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/revisions.js#L44-L71) — `revisionIsland`.

### E07

같은 작업 공개 이력의 어휘 선택·발췌·반례·고정 pack.

- [app/memory.py:60–243](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/memory.py#L60-L243) — `select/_context/_findings/_fair_parts/_excerpt`.

### E08

사용한 기억 사본의 이유·누락·출처 조회.

- [app/queries/public.py:115–139](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L115-L139) — `PublicQueries.memory_sources`.
- [app/static/role-board.js:406–438](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L406-L438) — `memoryPreview`.

### E09

정상 공식 배선·현재 원장 안의 실제 호출 예약·예산·동시성·종료 미확정 자리.

- [app/execution/invocations.py:12–179](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/invocations.py#L12-L179) — `Invocation/reserve/_slots_used/call_budget/_upper_call_gate`.

### E10

고정 계획·조건부 시작·취소·재시작 unknown 처리.

- [app/execution/coordinator.py:29–108](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L29-L108) — `pump/resume`.
- [app/execution/coordinator.py:219–242](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L219-L242) — `cancel_run`.
- [app/execution/coordinator.py:328–348](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/coordinator.py#L328-L348) — `_recover`.

### E11

PDF·공개 URL 추출, 빈 쪽 경고, 명시적 범위.

- [app/ingestion/extract.py:76–158](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/ingestion/extract.py#L76-L158) — `from_url/from_pdf/extract`.

### E12

상위 역할의 다음 단계·일반 분담 제안; 자동 실행 없음.

- [app/application/planning.py:99–141](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/planning.py#L99-L141) — `propose_next`.
- [app/application/planning.py:152–207](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/planning.py#L152-L207) — `propose_split`.

### E13

공개 뒤 선택적 합성·동일 예산 예약.

- [app/application/synthesis.py:25–102](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/synthesis.py#L25-L102) — `synthesize/synthesize_with_model`.

### E14

실제 관측 준비 조회와 기기 등록 대조.

- [app/readiness.py:15–62](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/readiness.py#L15-L62) — `check`.

### E15

읽기 전용 공식 CLI 명세·명시 모델·세션 비영속·도구 제한.

- [core/adapters.py:225–286](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/core/adapters.py#L225-L286) — `build_spec`.

### E16

요청/보고 모델 구분·provider별 사용량 합계.

- [core/adapters.py:297–325](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/core/adapters.py#L297-L325) — `Outcome/_model_match`.
- [app/usage.py:33–137](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/usage.py#L33-L137) — `calls/total/combine`.

### E17

원장 재사용 선택과 종료 대기; 별도 지속 실행 기능과 다름.

- [app/launch.py:190–251](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/launch.py#L190-L251) — `_has_room/pick_ledger/_watch`.

### E18

schema 이행 전 자동 백업; 일반 복구 UI와 다름.

- [app/store.py:198–218](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/store.py#L198-L218) — `Store._migrate`.

### E19

페이지화와 변경 없는 공개 projection 재사용; cold 조회는 선형.

- [app/queries/pages.py:61–142](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/pages.py#L61-L142) — `BrowserPages._snapshot/browse/choices`.
- [app/static/index.html:1270–1294](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/index.html#L1270-L1294) — `refresh/timer`.
- [app/static/index.html:1367–1370](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/index.html#L1367-L1370) — `setInterval(refresh)`.

### E20

원래 답 나란히 비교·한국어 테마·감소 모션 기반.

- [app/static/role-board.js:830–835](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L830-L835) — `humanComparison`.
- [app/static/index.html:1–15](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/index.html#L1-L15) — `document language/theme/assets`.
- [app/static/island-ui/motion.js:10–29](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/island-ui/motion.js#L10-L29) — `createSpring`.

### E21

고정 합성 기억 평가·관련 기록 포함률·누락·입력 크기.

- [tools/evaluate_memory.py:53–103](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/tools/evaluate_memory.py#L53-L103) — `evaluate/main`.

### E22

HTTP guard와 기존 controller API 입구.

- [app/server.py:165–220](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/server.py#L165-L220) — `Handler._guard/do_GET`.

### E23

개발 협업 카드·수동 소유권·PR·체크포인트 운영.

- [docs/COLLABORATION.md:74–90](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/COLLABORATION.md#L74-L90) — `작업 카드`.

### E24

개발 문서의 관측/문서/전달 구분·정정·현재와 이력 분리.

- [docs/COLLABORATION.md:45–99](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/COLLABORATION.md#L45-L99) — `출처 등급/정정/문서의 두 종류`.

### E25

동일 controller를 쓰는 단일 과제 headless 실행·순차 합성·결과 JSON.

- [app/run.py:93–188](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/run.py#L93-L188) — `main/_run`.

### E26

island-ui 부품의 출처와 원본 우선 수정 절차.

- [app/static/island-ui/README.md:1–15](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/island-ui/README.md#L1-L15) — `고칠 때`.

### E27

일반/격리 전달문·자료·기억·입력 확인 hash와 실제 미리보기.

- [app/context/inputs.py:164–239](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/context/inputs.py#L164-L239) — `prepare_run/_general_manifest`.
- [app/static/role-board.js:439–494](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/static/role-board.js#L439-L494) — `generalPreview/showInputPreview`.

### E28

기기·설치 버전·plan revision에 결속한 설치/인증/전송/문맥/권한 관측 계약.

- [core/eligibility.py:1–38](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/core/eligibility.py#L1-L38) — `runtime-inventory/2/FIELDS/SPEC_BOUND`.

## 검증 게이트

기존 검사의 이름은 출발점을 가리킨다. 없는 기능의 새 검사는 해당 기능을 실제로 구현할 때 추가해야 하며, 이 표를 위해 상시 도구나 중복 검사 체계를 추가하지 않는다.

### G01

**공개 조회** — 봉인 중 답·토큰·시간·원시 출력이 검색/목록/상세/직접 ID/새 화면에 나오지 않고 기존 공개 결과와 동일하다.

기존 접점: [tests/test_foundation.py](../../../tests/test_foundation.py) · [tests/test_query_projections.py](../../../tests/test_query_projections.py).

### G02

**입력과 이동** — 입력·자료·모델·역할을 재검사하고 확인 hash가 달라지면 새 확인을 요구한다; 과거 승인·실행 권한·소비를 복사하지 않는다.

기존 접점: [tests/test_templates.py](../../../tests/test_templates.py) · [tests/test_sources.py](../../../tests/test_sources.py) · [tests/test_foundation.py](../../../tests/test_foundation.py).

### G03

**호출 수명** — 예약과 시작 상태는 같은 거래, 동시 마지막 자리 중복 없음, 실패/취소/재시작에 소비 환불 없음, unknown 종료 전 자리 재사용 없음.

기존 접점: [tests/test_app_controller.py](../../../tests/test_app_controller.py) · [tests/test_foundation.py](../../../tests/test_foundation.py) · [tests/test_synthesis_lifecycle.py](../../../tests/test_synthesis_lifecycle.py).

### G04

**검토와 판** — 원본·입력·지적·처분·수정 판 hash·부모 판을 연결하고 상한/늦은 결과/재시작을 보존한다; 일반 collected와 격리 revealed를 구분한다.

기존 접점: [tests/test_cross_review.py](../../../tests/test_cross_review.py) · [tests/test_revisions.py](../../../tests/test_revisions.py) · [tests/test_general_team.py](../../../tests/test_general_team.py).

### G05

**기억 품질** — 한글·코드명·동의어·무관 질문·긴 반례의 포함/누락과 실제 전달 bytes를 비교하고 오래된 고정 pack을 재계산하지 않는다.

기존 접점: [tests/test_memory.py](../../../tests/test_memory.py) · [tests/test_memory_evaluation.py](../../../tests/test_memory_evaluation.py) · [tools/evaluate_memory.py](../../../tools/evaluate_memory.py) · [tools/benchmark_queries.py](../../../tools/benchmark_queries.py).

### G06

**화면과 재연결** — 대상 실행/원장 일치, 늦은 응답 폐기, 재연결 후 실제 상태 회복, 키보드·좁은 화면·모션 감소를 확인한다.

기존 접점: [tests/test_api_client.py](../../../tests/test_api_client.py) · [tests/test_role_board_render.py](../../../tests/test_role_board_render.py) · [tests/test_app_launch.py](../../../tests/test_app_launch.py).

### G07

**계획과 선행** — 계획 CAS·순환/누락·과거 판·선행 결과 변경·종료 미확정에서 admission과 표시가 일치하고 조회로 실행하지 않는다.

기존 접점: [tests/test_workflow.py](../../../tests/test_workflow.py).

### G08

**자료 변환** — 원본/변환/선택 hash·범위·누락을 결속하고 변환 실패·공개 주소/redirect·크기/시간 제한을 확인한다.

기존 접점: [tests/test_extraction.py](../../../tests/test_extraction.py) · [tests/test_sources.py](../../../tests/test_sources.py).

### G09

**실제 CLI 계약** — 추가 capability/옵션/기기/세션 생명주기는 해당 PC의 관측·등록·입력·취소·자손 종료와 구독 경로를 다시 확인한다.

기존 접점: [tests/test_core_adapters.py](../../../tests/test_core_adapters.py) · [tests/test_live_config.py](../../../tests/test_live_config.py).

이번 검토에서는 사용자 PC·공식 CLI를 실행하지 않음.

### G10

**도입 효과** — 실제 반복 불편 또는 과제를 먼저 지정하고 현재 방법과 결과 누락·사용자 시간·전체 호출/토큰·복구 부담을 비교한다.

모델 품질과 실제 사용자 효용은 정적 코드·모의 통과로 대체하지 않음

### G11

**개발 운영** — 기존 GitHub 카드·브랜치·PR·CI·체크포인트 기록으로 책임과 완료 근거를 찾는다; 앱 원장과 두 개의 정본을 만들지 않는다.

운영 채택을 앱의 자동화 구현으로 세지 않음

### G12

**외부 확장** — 필요한 작업 하나의 권한·입력·출력·소유권·실패 복구를 먼저 고정하고 별도 엔진/계정/서버 운영 비용을 비교한다.

새 외부 도구·제품 설치를 현재 결정으로 승인하거나 실행하지 않음

## 누락·중복 대조 결과

기준 SHA `48ab4bd6f0e297587707aecb83ebc0cd9968892f`에서 원본 JSON·원본 Markdown 표·이 결과 JSON/Markdown의 후보 ID를 비교했다.

| 항목 | 결과 |
|---|---|
| 원본 JSON / 원본 표 / 결과 | 118 / 118 / 118 |
| 누락 / 예상 밖 ID / 중복 | 없음 / 없음 / 없음 |
| 원본 순서·제목·조사 URL | 모두 보존 |
| 관련 ID 참조·코드 파일/줄·기존 검사 경로 | 모든 참조가 기준 tree의 경로/범위 안에 있음 |

후보 간 중복이 있으므로 위 수치는 제품 완성률·새 작업 수·가치 점수로 해석하지 않는다. 한 ID 안에서도 일부는 유지하고 나머지는 조건부로 남길 수 있다. 이번 문서는 그 판단을 숨기지 않기 위해 현재 상태와 권고를 별도 칸으로 두었다.
