# 통합 검토: 빠진 연결·충돌·정리·검증

2026-10-04 후속 요청: 오늘 분석한 것을 유기적으로 연결해 현재 제품을 크게 개편할 준비를 하고, 문서 지도를 정리하며 우선순위·효용을 매긴다. 명확히 도움이 되는 정리는 바로 수행한다. 이 기록은 새 upstream 전수 감사가 아니라 **기존 조사와 현재 코드 사이의 설계 검토**다.

## 종합하며 발견한 누락과 해결 위치

| 빠지기 쉬운 것 | 그대로 확장하면 생길 문제 | 준비한 설계 |
|---|---|---|
| 기능마다 다른 작업/실행/세션 단위 | 검색/검토/알림이 서로 다른 ‘같은 작업’을 참조 | Work→Run→Invocation→ArtifactRevision 관계 |
| 역할별 저장 형태와 공통 호출 회계 | 압축·검토·자동화 호출을 누락하거나 중복 계산 | R2 legacy invocation view→필요 시 영속 이행 |
| per-run event seq와 전역 revision 차이 | 재접속 cursor가 다른 run 변경을 놓침 | aggregate cursor 또는 별도 ledger revision |
| 공개 query의 단일 경계 | 새 검색·알림에서 봉인 metadata 노출 | M07 public projection 공통화, index도 같은 입력 |
| 검토 처분 이후의 실제 개선 | 지적 목록만 쌓이고 새 답의 검증 상태 불명 | P06 revision lineage·수정·새 check |
| 자료 변환의 provenance | PDF 추출 성공을 원본 전체 이해로 오인 | 원본/변환본/locator/누락/추출기 판 구별 |
| 설정 reload와 이미 시작한 실행 | 새 설정이 과거 입력 의미를 바꿔 재현 불가 | config snapshot과 last-good, 실행 고정 |
| 외부 실행과 DB 거래의 틈 | timeout/후처리 실패를 미시작으로 보고 이중 호출 | command receipt·reservation·observation·unknown |
| schema downgrade의 회계 유실 | 과거 backup 복원으로 이미 쓴 호출 사라짐 | 새 실제 쓰기 뒤 forward fix/호환 조회 |
| code-only와 model 단계 | 조회/알림에 불필요한 모델, 숨은 비용 | typed step + 공통 invocation budget |
| 범용 workflow와 현재 두 실행 모드 | 일반/격리의 공개 의미를 하나의 done으로 합침 | workflow strategy와 execution_mode 별도 |
| 원격/지속 수명의 기기 경계 | 창 상태·연결 상태로 실제 worker 생존 판단 | instance/host/ledger/runtime 독립 관측 |

위 항목은 설계 누락 가능성이지 현재 제품에서 모두 발생한 버그 목록이 아니다. 특히 현재 `_finish_unstored`, `_recover`, `_Seat`, `wiring`, S3/S6에 이미 들어간 보호·공통화를 기반으로 한다.

## 이전 자료 간 판단을 연결한 방식

| 겉보기 충돌 | 통합 판단 |
|---|---|
| 9월 구조 검토의 “뼈대는 건강, 재작성 불필요” vs 이번 큰 개편 | 당시 기능의 결함 증거가 새로 생긴 것은 아니다. 확대할 기능·연결 요구에 맞춰 내부 책임 재구성안을 준비한다. 기존 검토를 삭제/오답 처리하지 않음 |
| AnchorMind 과거 수동 기억 우선 vs 현재 자동 기억 | 현재 사용자 결정이 기준. 일반/상위 자동, 격리 제외를 목표 구조에도 유지 |
| tmux detach vs launcher 자동 종료 | client/execution 분리 원리는 채택 후보지만 기본 수명 변경은 별도 R5 mode |
| Beads/Gas Town 분산 운영 vs 단일 SQLite owner | claim/capacity/reconcile를 참고하되 분산 DB/daemon 전체가 선행은 아님 |
| Cline checkpoint vs 우리 불변 원장 | 파일 preimage와 결과 판 fork를 구별. 과거 호출·지출 이력을 되감지 않음 |
| Hermes의 tool/plugin/자동 loop vs 읽기 전용 독립 역할 | 일반/코딩/수집 capability에서 선택, 격리 계획을 조용히 확대하지 않음 |
| Lite-Harness 공통 SDK vs 우리 native 계약 | envelope만 참고, 기본 success/zero usage를 우리 성공 의미로 복사하지 않음 |
| 합의/비교/quote match vs 사실 확인 | M05에서 finding/disposition/check를 나누고 report가 더 강한 결론을 만들지 않음 |
| 기능별 작은 도입 권고 vs 최종 개편 준비 | 작은 기능만 추가하는 안 A와 내부를 재구성하는 안 B를 비교. B 권고지만 작은 수직 조각으로 이행 |

## 문서 정리의 실제 범위

| 대상 | 조치 | 이유 |
|---|---|---|
| 새 `docs/DOCUMENT-MAP.md` | 목적별 현재 안내/개편 설계/근거/과거 기록 입구 | 읽을 문서와 순서를 한곳에서 찾기 |
| root README·아키텍처 지도·참고 지도 | 문서 지도와 통합 준비서 연결, 반복 설명은 상세 문서에 위임 | 평행한 ‘최신 입구’가 서로 다른 다음 일을 말하지 않게 함 |
| v0.4 README의 현재 연구 단계 표현 | 9월 설계의 시점과 현재 구현 현황 분리 | 지금 앱이 있는데 실제 구현이 없는 것으로 읽히는 혼동 수정 |
| NEXT-SESSION §3/§4/§5 | 최신 요청·개편 입구로 교체, 옛 문서 확대 금지 문구 조정 | 명시적인 이번 사용자 요청과 오래된 제한 충돌 해소 |
| 앱 프로젝트 안내 | 문서 지도/개편 준비 링크와 현재·제안 구별 문구 | 문서 탐색 경로를 바로 개선; 실행 동작 변경 없음 |
| 날짜별 조사/검토·이전 설계 | 보존하고 새 지도에서 지위 표시 | 그 당시 판단·고정 SHA·다른 날짜 기록의 링크 유지 |
| 도구/코드 삭제 | 새 orphan이 확인되지 않아 광범위 삭제 안 함 | `_Seat`, membership 기반·옛 실험 도구를 외형상 중복만 보고 지우지 않음 |

`docs/research-2026-09-22` 같은 옛 경로를 이동하면 고정 기록 링크와 blob 근거를 깨뜨릴 수 있다. 이번 정리는 **중복 입구·낡은 현재형 안내를 고치고 근거를 찾아갈 지도를 만드는 것**으로 한다. 출처를 없애는 정리가 아니다. 새 상시 generator나 의미 없는 검사 규칙을 추가하지 않는다.

## 우선순위의 근거와 아직 열린 결정

[PRIORITIES](PRIORITIES.md)의 순서는 사용자 효용, 재사용되는 기반, 현재 구조와의 거리, 새 기기/외부 서비스 필요를 함께 본 판단이다. 수치 점수를 발명하지 않는다. 실제 사용의 가장 큰 불편이 확인되면 template/자료 준비/검색 같은 P1 조각 순서는 바꿀 수 있다.

열린 기술 결정은 각 구현 카드에서 증거로 좁힌다: invocation 영속 table 도입 시점, artifact 본문을 SQLite와 파일 중 어디에 둘지, query revision 구현, FTS tokenizer/한국어 정책, workflow의 최소 typed steps, 지속 service의 소유권, native App Server 실제 지원. 이 준비 단계에서는 로컬 단일 DB/기존 exec와 읽기 projection을 기준으로 구체적인 기본안을 제시했다. 결정을 사용자에게 전부 떠넘기지는 않는다.

## 검증 기록과 한계

- [capability-map.json](capability-map.json)과 [표](CAPABILITY-MAP.md)의 H01–H62, O01–O34, 로컬 D01–D10, OP01–OP12를 원본 목록과 대조한다. namespace를 구별하며 누락/중복과 module/pipeline/phase 참조를 검사한다.
- [current-code-map.json](current-code-map.json)은 기준 SHA의 파일 hash와 AST 선언 위치를 보존한다. 선언 목록은 함수 본문 전수 감사가 아니다. source 범위를 명시했다.
- 기존 상대 링크·인코딩·living-doc/인계 크기·도구 사용처 검사, UI JavaScript 문법과 관련 회귀, 전체 오프라인 검사를 수행한다. 최신 head CI와 실제 결과는 [PR #159](https://github.com/inlight37-design/decision-model_lab/pull/159)에 기록한다.
- 이전 조사에서 실행한 tmux/순수 함수 probe는 그 [관측 기록](../../research/operations-comparison-2026-10-04/EVIDENCE.md)이다. 이번 설계가 구현됐음을 검증하는 시험으로 다시 세지 않는다.
- 이 cloud의 기존 `test_children_left_behind_are_counted_and_ended` 실패와 CI 결과를 구분한다. 실제 PC·CLI·모델 품질·개편 후 성능·새 migration 동작은 미검증이다.

완료란 개편을 시작할 자료·경계·순서가 갖춰졌다는 뜻이다. 모든 기능을 구현했거나 이견이 원천적으로 없다는 뜻은 아니다. 바로 수행한 탐색/안내 변경과 후속 구조 변경을 PR에서 명확히 나눈다.
