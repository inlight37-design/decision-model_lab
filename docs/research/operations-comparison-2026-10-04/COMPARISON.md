# 기능별 비교표

코드의 실제 흐름은 [tmux](TMUX.md), [작업 시스템](TASK-SYSTEMS.md), [agent runtime](AGENT-RUNTIMES.md), 비공개 제품은 [공식 문서 분석](PRODUCT-WORKFLOWS.md)에 있다. 이 표의 적용 항목은 제안이다. “부분”은 이미 있는 기반을 보강하는 후보라는 뜻이며 외부 기능 전체를 구현했다는 뜻이 아니다.

## 실행과 상태

| 기능 | 비교한 부품 | 차이/선택 기준 | 우리 현재 기반 → 후보 |
|---|---|---|---|
| 화면과 실행 수명 분리 | tmux server/client; Amp remote; Conductor cloud | tmux detach는 서버 생존 중 실행 유지, cloud sleep은 프로세스 중단 가능 | launcher가 호출 종료 대기 후 서버 종료 → OP02 별도 지속 모드 |
| 다시 열 때 정확한 상태 | tmux notification/snapshot; Symphony reconcile | stream만으로 과거 누락·서버 재시작 복구 안 됨 | 원장 조회·recovery 있음 → OP01 snapshot/revision |
| 명령 수신과 작업 완료 | tmux begin/end; Lite-Harness control response | 응답은 receipt일 수 있고 결과 성공 의미와 다름 | controller result/outcome 분리 → OP01 receipt 설명 |
| 느린 화면 처리 | tmux output pause/exit; Backlog store version | 출력 생략/재동기화와 원본 저장 분리 | S3/S6 조회 개선 → OP01 detail 선택/backoff |
| 안정적인 대상 | tmux pane ID; Backlog canonical task ID | 이름/순서 변경과 identity 별개, 충돌은 unresolved | run/attempt/task ID → OP03 선택 대상 고정 |
| 재시도 세대 | Symphony tokenized timer; Beads read-back | 오래된 timer와 이미 성공한 쓰기 재실행 방지 | unknown/unsettled/recover → OP04 attempt reconciliation |
| 사용량과 성공 해석 | Lite-Harness default result; 기존 native adapters | 비용 미상≠0, result 존재≠성공 | core.adapters.interpret 유지 → OP09 계약 표 |
| 부모/자식과 workspace | Devin sessions; Gas Town worker; Symphony host | 별도 VM·worktree·thread는 격리/비용 단위가 다름 | 역할/호출 상한/보고서 → OP12 관계·환경 보기 |

## 작업과 개입

| 기능 | 비교한 부품 | 차이/선택 기준 | 우리 현재 기반 → 후보 |
|---|---|---|---|
| 시작 가능한 작업 | Beads ready; Backlog readiness | 미완료·의존성·미해결 identity 설명 | GitHub 카드 선행 관계 → OP04 ready projection |
| 원자적 맡기 | Beads claim CAS | 선택/label과 원자적 소유권 다름 | 원장 transaction → OP04 claim version |
| 실행 용량 | Gas Town PlanDispatch; Symphony slots | dependencies와 capacity와 budget은 독립 gate | controller `_slots_used`·cap → OP04 plan preview |
| 후처리만 실패 | Gas Town ErrOnSuccessFailed; Beads history commit | report failure가 실행 미시작 뜻하지 않음 | `_finish_unstored` → OP04 재실행 금지 이유 |
| 작업자 재사용 | Gas Town workstate | idle/clean/unpushed/MR를 따로 확인 | 종료/unknown 기반 → OP12 복구 필요 이유 |
| 명세→완료 기준 | Backlog task; Kiro specs | 작은 task와 큰 spec의 문서 부담 달리 | 기존 카드·고정 입력 → OP05 추적 행 |
| 절차 재사용 | Gas Town formula; Symphony WORKFLOW; Hermes skills | 절차 형식·실행 hook·읽을 지침은 서로 다름 | 이전 D07 템플릿 → OP05/OP10 버전 명세 |
| 선행/후행 시각화 | Backlog BFS graph; Gas Town convoy | 연결 그림과 실행 scheduler는 별도 | task 연결 후보 → OP04 읽기 graph |
| 작업 중 지시 보관 | Gas Town nudge; Amp queue | 다음 경계 전달과 즉시 steering 구별 | 고정 초안·취소 → OP07 inbox |
| 질문·완료 알림 | Jules notifications; Hermes delivery; Anchor outbox | 전달 retry와 모델 실행 retry 분리 | 이전 D09 → OP11 통합 상태함 |
| 실패 원인 후 조치 | Copilot artifacts; Conductor checks | status만 말하기보다 다음 행동 링크 | 현재 원장 오류/보고서 → OP11 action card |

## 기억·복구·편의

| 기능 | 비교한 부품 | 차이/선택 기준 | 우리 현재 기반 → 후보 |
|---|---|---|---|
| 원문/화면 구별 | tmux capture-pane; adapter raw output | PTY 화면에서 stderr/원본 byte 복원 안 됨 | raw/outcome/report 분리 → OP09 provenance |
| 파일 checkpoint | Cline snapshot/preimage; Conductor history | 파일·chat·외부 효과 범위를 명시 | 고정 입력 hash → OP06 fork/비교 먼저 |
| 일반 압축 | Cline strategy; Amp compaction | 요약 추가 호출·누락 품질·native ownership | memory pack 크기 제한 → OP08 preview |
| overflow 복구 | Cline deterministic fallback | 이미 실패한 요청을 같은 크기로 다시 보내지 않기 | adapter별 경계 → OP08 제한된 실험 |
| 오래된 tool result 선택 | Jev; Cline truncation | 의미 점수와 길이 절단의 손실 다름 | 기존 D05 평가셋 → OP08 선택기 비교 |
| last-good 설정 | Symphony WorkflowStore | 무효 새 설정 거절과 기존 실행 설정 고정 | prepare manifest → OP10 reload snapshot |
| 규칙 적용 이유 | Cline conditionals; Hermes skill selection | 편의 매칭과 권한 enforcement 구별 | D01/D07 → OP10 effective config |
| 자료 최신성 | Cline FileContextTracker; Peek freshness | watcher와 실제 hash 검증의 역할 다름 | 입력 hash → OP10 stale 표시 |
| 통합 검색 | Backlog Fuse; Hermes/WorkTrail FTS; Anchor rank | fuzzy/FTS/semantic은 서로 다른 검색 | D02 하나로 통합, OP03 저장된 필터 |
| keyboard palette | tmux commands; Amp plugins; Conductor shortcuts | 빠른 조작도 server contract 통과 | 현재 버튼 → OP03 공통 command 목록 |
| 병렬 비교/zoom | tmux layouts; Cursor multi-agent review | 숨겨진 독립 초안은 공개 전 미노출 | 역할판/교차검토 → OP12 comparison |
| 변경 위치 피드백 | Conductor diff comments; 우리 finding disposition | 코멘트 위치·원문 version 결속 | cross_review/report → OP06/OP12 locator |
| 자료 pill·프리셋 | Cursor context UI; Kiro template; Hermes skills | 첨부 reference·선택 본문·실제 prompt 차이 보임 | D07, OP05 입력 preview |
| 음성 입력 | Cursor changelog | 브라우저/인식 서비스 비용·권한 별도 | 선택적 UX 후보, OP03 후순위 |
| 후보 답 합성 | Fusion; 기존 frontier protocol | 품질 증가·timeout 회귀·합성 비용 동시 평가 | 이미 독립/합성 있음 → 비교 실험, 새 의존성 불필요 |

## 채택 방식별로 고르기

| 방식 | 해당 후보 | 운영 부담 |
|---|---|---|
| UI/projection 독자 구현 | 막힘 이유, 검색 필터, 비교, 환경/사용량, 효과 설정 | 기본 추가 모델 호출 없음 |
| 기존 원장 위 계약 확장 | request receipt, version claim, inbox, fork metadata | migration/동시성/복구 시험 필요 |
| 별도 worker 수명 추가 | 지속 서버, notification outbox, scheduling | 소유권·재시작·중복 처리·관측 필요 |
| native adapter 기능 확대 | steering, checkpoint, CLI context 관리 | 해당 버전·기기·권한·자금 경로 실측 필요 |
| 외부 패키지/서비스 도입 | Beads/Dolt, Gas Town, LiteLLM/Jev, SaaS products | 라이선스·배포·추가 호출/서비스 비용 별도 검토 |

tmux/Beads/Gas Town의 한 기능을 참고한다고 각 서버를 의존성으로 추가하는 것은 아니다. 반대로 나중에 규모가 커져 운영 책임을 맡길 필요가 생기면 외부 도입도 비교할 수 있도록 출처와 경계를 남겼다.
