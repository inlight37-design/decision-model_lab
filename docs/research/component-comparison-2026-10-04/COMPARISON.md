# 같은 기능끼리 비교하고 우리 위치 표시하기

`—`는 **이번에 읽은 대응 경로에서 확인하지 않음**이다. 제품에 기능이 없다는 뜻이 아니다. “우리”는 이번 기준 `6cfb78c5a91dc26a46d95229c89f6e2bbfb6830c`의 앱·운영이며, “후보”는 미구현 제안이다. 코드 출처는 [근거 문서](EVIDENCE.md)의 AM/HM/PK/WT 그룹, 제안 ID는 [적용 설계](ADOPTION.md)다.

## 기억·검색·문맥

| 기능 | AnchorMind | Hermes | codex-peek | WorkTrail | 우리 현재 → 적용 후보 |
|---|---|---|---|---|---|
| 기억 단위 | fact/decision/procedure 등 파편 | MEMORY/USER와 세션 원문 | MAP 문서·기준 결정 | case/thread의 evidence·state | 같은 task의 공개 실행 묶음 → 실행/결정/절차를 구별(D03/D07) |
| 범위 | key/그룹/workspace/global/session | profile·세션 | repo 지도·결정 | owner/case/thread/repo | task_id 범위 → 프로젝트 확장은 명시 계약(D06) |
| 찾는 방식 | 다채널 후보→융합→예산 | 세션 FTS5 발견→펼치기 | 경로/식별자 lexical | evidence FTS5 | 질문 단어·한국어 2-gram+최신순 → 원문검색(D02) |
| 검색 후보 경계 | 단계별 limit·범위 predicate | 발견/읽기 크기 경계 | seed 개수·범위 | 케이스·소유자·보관 조건 | 최신 적격 24개 → 후보 누락 평가(D05) |
| 정확한 식별자 | 어휘·정확 일치 증거 | FTS 질의 | path/backtick/identifier seed | evidence 본문 | 별도 exact 채널 없음 → 경로/에러코드 우선 후보(D05) |
| 의미 검색 | embedding·재순위 옵션 | 이번 검색 도구는 FTS | 확인 경로는 lexical | 확인 경로는 FTS | 없음 → 평가 후 optional(D10) |
| 한국어 | 로컬 형태소와 fallback | 해당 코드 미검토 | Unicode/NFC 처리 | SQLite FTS | 2-gram → 한국어·조사/동의표현 대조(D05) |
| 검색 이유 | 채널·점수 증거 보존 | 원문 위치·snippet | seed·결정 근거·freshness | evidence 출처/snippet | 원본 ID/hash는 있으나 선택 설명 부족 → 이유 서랍(D01) |
| 중복/정렬 | RRF ID 병합·결정적 hydration tail | lineage 중복 정리 | 결정적 점수/tie-break | 원문 evidence 단위 | query 점수·created_at·run_id → 채널별 근거 유지(D05) |
| 관련 없음 | threshold 등 다단 조건 | 질의 결과 없음 | seed/검색 결과 없음 | FTS 결과 없음 | 0점 후보도 최신 기록으로 채울 수 있음 → 빈 결과 정책 비교(D05) |
| 크기 예산 | 순위 후 공유 budget, MMR 후보 | read 길이 제한 | attachment와 조회 구별 | 검색 결과/원문 구별 | 최대 3실행·발췌/전체 UTF-8 상한 → 설명/실제 입력 일치(D01) |
| 입력 고정 | context 선택 집합 | 세션 시작 frozen snapshot | 기준 자료 snapshot·원문 결속 | 상태 projection 별도 | manifest/pack hash 이미 있음 → 새 기능도 이 계약 재사용 |
| 검색의 상태 변화 | access/cache/seen 갱신 | 이번 계약만으로 전체 부작용 판정 불가 | 조회 log와 첨부 원장 구별 | 기록과 검색 분리 | prepare 시 pack 고정 → preview/attached 분리 유지(D01) |
| 캐시 최신성 | 현재 hash/review/valid_to 확인 | frozen 기간 계약 | baseline decision/fingerprint·stale | evidence 원문 참조 | 저장 답변 hash 확인 → 새 인덱스에 extractor/source hash(D02) |

## 기록 품질·수명·결정

| 기능 | AnchorMind | Hermes | codex-peek | WorkTrail | 우리 현재 → 적용 후보 |
|---|---|---|---|---|---|
| 출처 | origin·client·policy tier | memory/user 대상 구별 | canonical decision과 evidence | user/agent authority·source_ref | 답변/검토/처분 원문·hash → 출처 유형 UI(D01/D03) |
| 승인·보류 | review state와 주입 조건 | write gate 및 staged entry 고정 | 기준 결정과 단순 캐시 구별 | authority 기록; 일괄 승인제 아님 | 실행 승인·검토 처분 → 기억 편집 버전 검사(D04) |
| 수정·교체 | version·supersedes·valid_to | replace/remove·matched entry | baseline 기준 변경 | append-only supersedes | 과거 실행 원문 보존 → 결정 교체 timeline(D04) |
| 핀/핵심 기억 | anchor/core | pin/cron 참조 보호 | authority baseline | declared state | 자동 과거 실행 선택 → 선택 고정/제외 제어(D04) |
| 수명 정리 | TTL·감쇠·병합·압축·GC | 스킬 active/stale/archive | 지도 freshness | case 보관·current projection | 최근 후보 제한, 자동 요약 삭제 없음 → 보관/숨김부터(D04) |
| 충돌 | NLI/모델·symbolic 후보 | 해당 경로 미검토 | 검토 proof·처분은 다른 문제 | ruledout/constraint·교체 이유 | unresolved 반례·검토 처분 이미 있음 → 결정 충돌함(D08) |
| 회고 | 모델을 통한 세션 구조화 | broader 기능 목록 참조 | — | 모델 없이 state/evidence 기록 가능 | 고정 실행 기록 있음 → 기록 projection 먼저(D03), 자동 회고 별도(D10) |
| 피드백 학습 | 관계 가중치·결과 수 기반 threshold | 스킬 사용 시각 기반 분류 | 조회/첨부 사용 기록 | 기록/상태 갱신 | 검색 품질 피드백 없음 → 도움/무관 표시와 평가(D05) |
| 생성 검색 질문 | 별도 모델 생성·원본 앵커 점검 | — | — | — | 없음 → 원본과 분리된 파생 인덱스(D10) |
| 평가 | RecallMetrics·paired bootstrap | 이번 경로 효과 측정 안 함 | 결정성·proof 계약 | 기능 계약/원문 근거 | 경계 tests는 있으나 효과 미측정 → 정답셋 비교(D05) |

## 편의·자동화·운영

| 기능 | AnchorMind | Hermes | codex-peek | WorkTrail | 우리 현재 → 적용 후보 |
|---|---|---|---|---|---|
| 기억 관리 화면 | 필터·상세·이력·그래프·export | 전체 편의 목록 참조 | MAP 읽기/근거 도구 | 작업 상태·evidence | 실행 중심 UI → 검색/기억 서랍(D01/D02/D04) |
| “왜 이 결정?” | case/entity history | 세션 원문을 다시 읽기 | why-query 결정 검색 | decision/constraint/evidence | 보고·검토 원문 조회 → 결정 timeline(D03) |
| 작업 복귀 | context/historical reconstruction | session browse | 기준 자료 확인 | focus/open/next/owner | GitHub 카드/인계 이미 운영 → 앱의 복귀 요약(D03) |
| 재사용 양식 | procedure/skill guide | skills 목록→본문→관련 파일 | — | checkpoint 구조 | 매번 역할·자료 설정 → 팀/작업 양식(D07) |
| 초기 설정 편의 | dry-run diff, 명시 쓰기 | broader onboarding 목록 | 훅/bridge 표면 | CLI 기록 엔진 | 확인 명세·등록 관측 → 저장된 설정/변경 비교(D07) |
| 백그라운드 작업 | outbox·retry·dead·scheduler | 자동화 기능은 이전 목록 | Stop guard 재시도 상한 | pending/finalized | bounded controller/원장 → 알림·인덱싱 큐(D09) |
| 내보내기/가져오기 | versioned JSONL·links·versions | 세션/자료 기능은 이전 목록 | source/baseline 결속 | evidence 참조 | report 있음, 범용 기억 import 없음 → 선택 bundle(D06) |
| 운영 감사 | hash chain·작업 상태 | 해당 경로 미검토 | 입력/proof 결속 | 기록 상태 | 원장/hash/종료 확인 있음 → 다른 감사 DB 중복 도입 보류 |
| 모델·비용 경계 | stage egress·fallback·semaphore | native agent 제공자 체계 | bridge/hook 도구 | record core는 모델 없이 동작 | 구독 CLI·새 원장·호출 상한 → 이 경계를 모든 추가 호출에 적용 |

## 이름은 같아도 바꿔 끼울 수 없는 것

1. **기억:** 사용자 선호, 과거 답변, 확인된 결정, 재사용 절차는 권한과 수명이 다르다. 같은 테이블에 넣더라도 유형과 출처를 잃지 않는다.
2. **신뢰:** AnchorMind tier, WorkTrail authority, Peek baseline, 우리 검토 처분은 모두 다른 의미다. 숫자 하나로 합치지 않는다.
3. **완료:** DB 저장, 인덱싱, 모델 답변, 검토 완료, 프로세스 종료는 다른 사건이다. 사용자 화면에도 필요한 상태를 구별한다.
4. **학습:** 결과 수 조정·조회 횟수·스킬 사용 시각은 관측 신호다. 효과를 주장하려면 동일 질의/작업에 대한 대조가 필요하다.
5. **읽기:** 검색이 접근 횟수나 seen 상태를 바꾸는 구현이 있다. 미리보기·검색·실제 첨부를 모두 하나의 API로 묶기 전에 부작용을 확인한다.

기능을 없애자는 결론이 아니라 **작은 단위로 조합하기 위한 차이**다. 지금은 D01–D07 중 불편한 곳부터 선택할 수 있고, 규모·반복 작업이 늘면 D08–D10의 기능을 더할 근거가 생긴다.
