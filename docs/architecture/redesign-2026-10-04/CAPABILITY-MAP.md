# 오늘 분석한 후보의 전체 배치 지도

[우선순위·효용](PRIORITIES.md) · [모듈](TARGET.md) · [파이프라인](PIPELINES.md) · [이행](MIGRATION.md)

2026-10-04 고정 목록의 H/O/D/OP를 모두 연결했다. 한 행은 주 책임 위치이며 관련 모듈의 거래·공개 경계를 생략한다는 뜻은 아니다. D 번호는 이전 부품 분석의 로컬 ID로, 아키텍처 ADR D 번호와 다른 namespace다. **표의 순위는 제안 도입 우선순위이며 구현 완료가 아니다.** 상세 부분 구현/조건/출처는 각 후보 원문을 연다.

기계판 [capability-map.json](capability-map.json)에서 누락·중복·참조를 검사했고 아래 표는 그 배치의 읽기용 판이다. JSON/표는 이 날짜의 설계 기록이며 새 계획을 채택하면 구현 카드에서 달라진 이유를 남긴다. 반복 문서 자동화를 위해 새 상시 도구를 추가하지 않았다.

## H 후보

| 후보·원문 | 작업 묶음 | 주 책임 / 흐름 | 우선순위 / 이행 |
|---|---|---|---|
| [H01 이름·검색·즐겨찾기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L11) | 5. 검색·탐색·필터 | M07 / P08 | P1 / R1 |
| [H02 팀·모델 프리셋](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L12) | 6. 팀·절차·template | M01 / P01 | P1 / R3 |
| [H03 파일·폴더·diff·URL 참조](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L13) | 8. 자료 추출·첨부 | M02 / P02 | P1 / R3 |
| [H04 중단·방향 수정](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L14) | 12. workflow·배정·개입 | M01 / P01 | P2 / R4 |
| [H05 재시도·갈라서 비교·되돌리기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L15) | 10. 검토 후 수정·재검토 | M05 / P06 | P1 / R4 |
| [H06 나를 기다리는 일·완료 알림](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L16) | 11. 수신함·다음 행동 | M08 / P08 | P1 / R5 |
| [H07 결과물 서랍](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L17) | 9. 답·검토·사용량 비교 | M07 / P08 | P1 / R1 |
| [H08 화면 배치·간단 모드](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L18) | 9. 답·검토·사용량 비교 | M07 / P08 | P1 / R1 |
| [H09 빠른 명령·입력 초안](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L19) | 5. 검색·탐색·필터 | M07 / P08 | P1 / R1 |
| [H10 목적별 시작 안내](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L20) | 14. 설정·예약·지속 운영 | M09 / P08 | P1 / R1 |
| [H11 테마·한국어·상태 마스코트](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L21) | 9. 답·검토·사용량 비교 | M07 / P08 | P2 / R1 |
| [H12 짧은 선호·프로젝트 기억](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L27) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [H13 과거 세션 원문 검색](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L28) | 5. 검색·탐색·필터 | M07 / P08 | P1 / R1 |
| [H14 검색 뒤 필요한 부분만 펼치기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L29) | 4. 기억 설명·원문 서랍 | M02 / P02 | P1 / R3 |
| [H15 현재 상태와 긴 이력 분리](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L30) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [H16 기억 지도·사용 흔적](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L31) | 4. 기억 설명·원문 서랍 | M02 / P02 | P1 / R3 |
| [H17 내보내기·가져오기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L32) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [H18 긴 대화 압축·요약 방식 선택](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L33) | 13. 검색·문맥 평가/고급화 | M02 / P02 | P3 / R3 |
| [H19 필요할 때 읽는 스킬 서랍](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L39) | 6. 팀·절차·template | M01 / P01 | P1 / R3 |
| [H20 스킬 묶음·작업 양식](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L40) | 6. 팀·절차·template | M01 / P01 | P1 / R3 |
| [H21 자료·성공 경험에서 절차 만들기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L41) | 6. 팀·절차·template | M01 / P01 | P1 / R3 |
| [H22 스킬 정리·핀·보관함](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L42) | 6. 팀·절차·template | M01 / P01 | P1 / R3 |
| [H23 다른 분야의 절차 라이브러리](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L43) | 6. 팀·절차·template | M01 / P01 | P1 / R3 |
| [H24 목표가 끝날 때까지 제한 반복](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L51) | 12. workflow·배정·개입 | M01 / P01 | P2 / R4 |
| [H25 비동기 분담·구조화 결과](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L52) | 12. workflow·배정·개입 | M01 / P01 | P2 / R4 |
| [H26 의존성이 있는 작업판](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L53) | 12. workflow·배정·개입 | M01 / P01 | P2 / R4 |
| [H27 재사용 가능한 다단계 작업](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L54) | 12. workflow·배정·개입 | M01 / P01 | P2 / R4 |
| [H28 같은 작업에서 검토·수정·재검토](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L55) | 10. 검토 후 수정·재검토 | M05 / P06 | P1 / R4 |
| [H29 남은 예산·체크포인트·질문](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L56) | 3. invocation·회계·복구 | M03 / P04 | P0 / R2 |
| [H30 용량·동시성·재시도 제어](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L57) | 3. invocation·회계·복구 | M03 / P04 | P0 / R2 |
| [H31 작업별 Git 사본·변경 검토](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L58) | 15. 파일 수정·복구 | M04 / P09 | P3 / R6 |
| [H32 여러 관점 프리셋·조언 주기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L59) | 6. 팀·절차·template | M01 / P01 | P1 / R3 |
| [H33 일회·반복 예약](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L65) | 14. 설정·예약·지속 운영 | M08 / P08 | P2 / R5 |
| [H34 모델 없는 예약 작업](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L66) | 14. 설정·예약·지속 운영 | M08 / P08 | P2 / R5 |
| [H35 이벤트로 시작하기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L67) | 14. 설정·예약·지속 운영 | M08 / P08 | P2 / R5 |
| [H36 세션 감시·반복 프롬프트](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L68) | 14. 설정·예약·지속 운영 | M08 / P08 | P2 / R5 |
| [H37 결과 전달·수신함 복구](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L69) | 11. 수신함·다음 행동 | M08 / P08 | P1 / R5 |
| [H38 선택한 MCP·toolset](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L75) | 16. 원격·도구·미디어·연동 | M09 / P03 | P3 / R6 |
| [H39 필요한 도구만 검색·설명 로딩](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L76) | 16. 원격·도구·미디어·연동 | M02 / P02 | P3 / R6 |
| [H40 플러그인·화면 확장 슬롯](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L77) | 16. 원격·도구·미디어·연동 | M09 / P03 | P3 / R6 |
| [H41 native runtime adapter](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L78) | 3. invocation·회계·복구 | M04 / P04 | P3 / R6 |
| [H42 편집기 연결 ACP](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L79) | 16. 원격·도구·미디어·연동 | M07 / P08 | P3 / R6 |
| [H43 다른 UI를 위한 API](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L80) | 16. 원격·도구·미디어·연동 | M07 / P08 | P3 / R6 |
| [H44 원격 실행·여러 기기·메신저](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L81) | 16. 원격·도구·미디어·연동 | M04 / P04 | P3 / R6 |
| [H45 PDF·Office·노트북 추출](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L87) | 8. 자료 추출·첨부 | M02 / P02 | P1 / R3 |
| [H46 스캔 누락 경고·선택 OCR](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L88) | 16. 원격·도구·미디어·연동 | M02 / P02 | P3 / R6 |
| [H47 웹 검색·본문 추출·캐시](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L89) | 8. 자료 추출·첨부 | M02 / P02 | P1 / R3 |
| [H48 브라우저로 자료 선택](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L90) | 16. 원격·도구·미디어·연동 | M02 / P02 | P3 / R6 |
| [H49 이미지 입력·시각 결과](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L91) | 16. 원격·도구·미디어·연동 | M02 / P02 | P3 / R6 |
| [H50 말로 입력·답 읽어주기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L92) | 16. 원격·도구·미디어·연동 | M07 / P01 | P3 / R6 |
| [H51 작업 화면 보기·사람에게 넘기기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L93) | 16. 원격·도구·미디어·연동 | M04 / P09 | P3 / R6 |
| [H52 코드로 자료 가공](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L94) | 16. 원격·도구·미디어·연동 | M04 / P09 | P3 / R6 |
| [H53 편집 직후 진단](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L95) | 15. 파일 수정·복구 | M04 / P09 | P3 / R6 |
| [H54 사용량·시간 분석](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L101) | 9. 답·검토·사용량 비교 | M07 / P08 | P1 / R1 |
| [H55 진단·설정 UI·업데이트 안내](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L102) | 14. 설정·예약·지속 운영 | M09 / P08 | P1 / R3 |
| [H56 스냅숏·복구·보관](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L103) | 15. 파일 수정·복구 | M04 / P09 | P3 / R6 |
| [H57 실행 backend 선택](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L104) | 16. 원격·도구·미디어·연동 | M04 / P04 | P3 / R6 |
| [H58 대체 모델·계정·provider 선택](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L105) | 16. 원격·도구·미디어·연동 | M09 / P03 | P3 / R6 |
| [H59 비밀을 모델 밖에서 취급](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L106) | 16. 원격·도구·미디어·연동 | M09 / P03 | P3 / R6 |
| [H60 음악·홈 자동화·메신저 업무](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L107) | 16. 원격·도구·미디어·연동 | M08 / P08 | P3 / R6 |
| [H61 여러 과제 비교 실행·재개](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L108) | 13. 검색·문맥 평가/고급화 | M09 / P04 | P1 / R3 |
| [H62 서비스 건강·관측 이벤트](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/HERMES.md#L109) | 14. 설정·예약·지속 운영 | M09 / P08 | P1 / R1 |

## O 후보

| 후보·원문 | 작업 묶음 | 주 책임 / 흐름 | 우선순위 / 이행 |
|---|---|---|---|
| [O01 여러 방식으로 기억 찾기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L11) | 13. 검색·문맥 평가/고급화 | M02 / P02 | P3 / R3 |
| [O02 입력 예산 안의 다양한 근거](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L12) | 4. 기억 설명·원문 서랍 | M02 / P02 | P1 / R3 |
| [O03 왜 이 기억인가·다음 조회 안내](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L13) | 4. 기억 설명·원문 서랍 | M02 / P02 | P1 / R3 |
| [O04 프로젝트·사건·세션 범위](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L14) | 7. 결정·복귀·기억 관리 | M05 / P07 | P2 / R3 |
| [O05 남길 기억·검토 대기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L15) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [O06 결정의 교체·사건 이력](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L16) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [O07 모순·보류·미해결 기억](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L17) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [O08 기억 정리·망각·피드백](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L18) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [O09 검색 품질 시험 세트](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L19) | 13. 검색·문맥 평가/고급화 | M02 / P02 | P3 / R3 |
| [O10 기억 내보내기·관리 화면·동기화](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L20) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [O11 지적별 수정·반박·보류와 근거](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L28) | 10. 검토 후 수정·재검토 | M05 / P06 | P1 / R4 |
| [O12 검토 범위·강도·멈춤 조건](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L29) | 10. 검토 후 수정·재검토 | M05 / P06 | P1 / R4 |
| [O13 요청한 모델과 실제 응답 대조](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L30) | 9. 답·검토·사용량 비교 | M07 / P08 | P1 / R1 |
| [O14 검토 중·반영 중·미완 표시](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L31) | 9. 답·검토·사용량 비교 | M07 / P08 | P1 / R1 |
| [O15 세션 연결·긴 검토 회수](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L32) | 3. invocation·회계·복구 | M03 / P04 | P0 / R2 |
| [O16 규칙·지식 지도·출처 재확인](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L33) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [O17 세 줄 작업 요약](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L41) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [O18 관측·해석·결정 분리](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L42) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [O19 실패한 가설·배제 이유 재사용](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L43) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [O20 다음 행동·담당·입력 계약](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L44) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [O21 현재 요약에서 증거로 확대](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L45) | 2. 공개 query·조회 책임 | M07 / P08 | P0 / R1 |
| [O22 화면을 닫아도 작업 찾기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L53) | 14. 설정·예약·지속 운영 | M09 / P08 | P2 / R5 |
| [O23 상태 구독·변경분·출력 억제](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L54) | 2. 공개 query·조회 책임 | M07 / P08 | P0 / R1 |
| [O24 찾기·여러 창·문맥별 조작](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L55) | 9. 답·검토·사용량 비교 | M07 / P08 | P1 / R1 |
| [O25 막히지 않은 일·원자적 가져가기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L63) | 12. workflow·배정·개입 | M01 / P01 | P2 / R4 |
| [O26 명세·계획·완료 기준 양식](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L64) | 6. 팀·절차·template | M01 / P01 | P1 / R3 |
| [O27 대규모 작업의 의존성·병합·감시](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L65) | 12. workflow·배정·개입 | M01 / P01 | P2 / R4 |
| [O28 병렬 사본과 한곳의 diff 검토](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L66) | 15. 파일 수정·복구 | M04 / P09 | P3 / R6 |
| [O29 조정자와 작은 작업자·직접 교정](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L67) | 9. 답·검토·사용량 비교 | M07 / P08 | P1 / R1 |
| [O30 한 작업·한 산출물·비동기 검토](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L68) | 11. 수신함·다음 행동 | M08 / P08 | P1 / R5 |
| [O31 짧은 현재 문맥과 필요할 때 읽는 이력](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L69) | 13. 검색·문맥 평가/고급화 | M02 / P02 | P3 / R3 |
| [O32 계획 모델과 실행 모델을 따로](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L70) | 6. 팀·절차·template | M01 / P01 | P1 / R3 |
| [O33 선택적 라우터·후보 답 합성](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L71) | 13. 검색·문맥 평가/고급화 | M01 / P01 | P3 / R6 |
| [O34 디자인 부품과 반복 UI 양식](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/feature-catalog-2026-10-04/OTHER-PROJECTS.md#L72) | 9. 답·검토·사용량 비교 | M07 / P08 | P1 / R1 |

## D 후보

| 후보·원문 | 작업 묶음 | 주 책임 / 흐름 | 우선순위 / 이행 |
|---|---|---|---|
| [D01 선택 이유와 실제 입력 미리보기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L22) | 4. 기억 설명·원문 서랍 | M02 / P02 | P1 / R3 |
| [D02 원문 검색과 최신성](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L32) | 5. 검색·탐색·필터 | M07 / P08 | P1 / R1 |
| [D03 작업 복귀 요약과 결정 이력](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L42) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [D04 기억 관리: 핀·제외·수정·되돌리기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L52) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [D05 검색 평가와 단계적 개선](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L62) | 13. 검색·문맥 평가/고급화 | M02 / P02 | P1 / R3 |
| [D06 명시적 공유와 이동 가능한 기억 묶음](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L72) | 7. 결정·복귀·기억 관리 | M05 / P07 | P2 / R3 |
| [D07 팀·작업 양식과 스킬 서랍](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L82) | 6. 팀·절차·template | M01 / P01 | P1 / R3 |
| [D08 결정 충돌함](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L92) | 7. 결정·복귀·기억 관리 | M05 / P07 | P1 / R3 |
| [D09 필요한 백그라운드 작업만 관리하기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L102) | 11. 수신함·다음 행동 | M08 / P08 | P1 / R5 |
| [D10 규모가 커질 때 선택하는 확장](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/component-comparison-2026-10-04/ADOPTION.md#L112) | 13. 검색·문맥 평가/고급화 | M02 / P02 | P3 / R3 |

## OP 후보

| 후보·원문 | 작업 묶음 | 주 책임 / 흐름 | 우선순위 / 이행 |
|---|---|---|---|
| [OP01 원장에 다시 붙기와 처리 단계 표시](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L24) | 2. 공개 query·조회 책임 | M07 / P08 | P0 / R1 |
| [OP02 명시적인 지속 실행 모드](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L34) | 14. 설정·예약·지속 운영 | M09 / P08 | P2 / R5 |
| [OP03 작업 탐색·저장된 필터·명령 palette](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L42) | 5. 검색·탐색·필터 | M07 / P08 | P1 / R1 |
| [OP04 준비·담당·용량을 나눈 작업판](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L50) | 3. invocation·회계·복구 | M03 / P04 | P0 / R2 |
| [OP05 명세와 완료 증거가 연결된 작업 양식](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L60) | 6. 팀·절차·template | M01 / P01 | P1 / R3 |
| [OP06 판 비교·실행 fork·복구 미리보기](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L68) | 10. 검토 후 수정·재검토 | M05 / P06 | P1 / R4 |
| [OP07 다음 단계 메시지와 전달 상태](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L76) | 12. workflow·배정·개입 | M01 / P01 | P2 / R4 |
| [OP08 문맥 예산과 압축 실험](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L84) | 13. 검색·문맥 평가/고급화 | M02 / P02 | P3 / R3 |
| [OP09 어댑터의 공통 계약과 capability 표](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L92) | 3. invocation·회계·복구 | M03 / P04 | P0 / R2 |
| [OP10 실제 적용 설정과 마지막 정상판](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L100) | 14. 설정·예약·지속 운영 | M09 / P03 | P1 / R3 |
| [OP11 다음 행동이 있는 수신함](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L108) | 11. 수신함·다음 행동 | M08 / P08 | P1 / R5 |
| [OP12 공개 결과·작업자·산출물 비교 화면](https://github.com/inlight37-design/decision-model_lab/blob/892c5ebe8c53ebba23c9f8e452c67306f35f0c8a/docs/research/operations-comparison-2026-10-04/ADOPTION.md#L116) | 9. 답·검토·사용량 비교 | M07 / P08 | P1 / R1 |

## 목록 밖에서 발견한 필수 연결

원본 후보가 직접 말하지 않은 전역 revision, 공개 query 단일 경계, legacy invocation adapter, schema 이행 후 회계 보존, 검토 판 lineage는 [통합 검토](REVIEW.md)에 따로 기록했다. 인기 있는 외부 기능을 배치하는 것만으로 이 프로젝트의 개편 설계가 완성되지는 않는다.
