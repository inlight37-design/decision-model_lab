# 외부 기능과 코드 참고 지도

그동안 조사한 외부 프로젝트에서 **무엇을 읽었고, 우리 어디에 반영했는지** 찾는 입구다. 조사 문서의 추천은 구현 완료가 아니다. 아래의 패턴 적용은 우리 계약에 맞춰 작성한 코드이며, 원본 코드를 복사한 경우는 별도로 표시한다. 원문 URL·고정 commit·읽은 범위·제한은 각 조사 기록의 근거 문서가 기준이다.

**“나중에 이런 기능도 써볼까”를 찾을 때는 [외부 기능 후보 목록](research/feature-catalog-2026-10-04/README.md)**을 연다. Hermes의 화면·검색·스킬·자동화·연동·자료 편의와 다른 프로젝트의 기능을 폭넓게 모았다. 사용자 불편으로 찾는 표, 적용 접점, 추가 호출·운영 조건, 작은 시험, 고정 출처가 있다. 아래 표는 현재 반영 위치이고, 후보 목록은 미구현 선택지까지 포함한다.

## 외부 프로젝트에서 우리 구현으로

| 출처 | 참고한 기능 | 현재 적용 상태와 위치 | 상세 조사와 원본 코드 위치 |
|---|---|---|---|
| AnchorMind | 범위가 있는 기억 검색, 출처 메타데이터, 크기를 제한한 AnswerPack, 사건 이력 | **원리 적용·독자 구현.** [app/memory.py](../app/memory.py)가 같은 작업의 공개 이력을 자동 선택하고 고정. [controller](../app/controller.py)의 기존 원장·입력 경계를 재사용. 외부 패키지 의존성·코드 복사 없음 | [기능·파이프라인·코드 검토](reviews/2026-10-04-anchormind/README.md), [순수 함수 probe](reviews/2026-10-04-anchormind/probes.mjs). 검토의 링크는 upstream commit에 고정 |
| Hermes Agent | native CLI 수명, 오류·사용량, 문맥 snapshot, 기억·스킬 범위 | **실행기 패턴 일부 적용.** [core/runner.py](../core/runner.py)의 HP-01 계약, [환경](../core/env.py)·[격리](../core/isolation.py)·[controller](../app/controller.py). HP-04 이후 자동 스킬·MCP·App Server 전송 전체를 구현한 것은 아님 | [요약](research/hermes-2026-09-23/README.md), [분석](research/hermes-2026-09-23/ANALYSIS.md), [원본 파일·근거](research/hermes-2026-09-23/EVIDENCE.md), [후속 후보](research/hermes-2026-09-23/ADOPTION_PLAN.md) |
| tmux | 실행과 화면 연결 상태 분리, 공통 명령 경로, 조회 억제 | **설계 참고.** 별도 tmux 서버·PTY parser는 없음. 필요한 조회 순서·중복 억제는 [화면](../app/static/index.html)의 S3, 원장 조회 재사용은 [controller](../app/controller.py)의 S6로 처리 | [요약](research/tmux-2026-09-23/README.md), [적용 제안](research/tmux-2026-09-23/ADOPTION_PLAN.md), [원본 위치](research/tmux-2026-09-23/EVIDENCE.md). TM 계획을 통째로 구현했다는 뜻은 아님 |
| codex-peek | 입력과 결과의 결속, 검토 지적의 처분, 훅·프로세스 수명 문제 | **필요한 의미만 적용.** [cross_review](../app/cross_review.py)·[report](../app/report.py)의 원문 결속·처분, [controller](../app/controller.py)의 입력 고정, [launch](../app/launch.py)의 수명 관리. Peek 엔진·전역 Stop 훅·별도 증명 원장은 설치하지 않음 | [Codex 코드 검토](reviews/2026-09-26-codex-peek/README.md), [Claude 검토](reviews/2026-09-26-codex-peek-claude/README.md), [상충 판단 통합](reviews/2026-09-26-review-consolidation/README.md) |
| WorkTrail | 작업 카드, 인계 체크포인트, 원격 공유 | **운영 방식 일부 채택.** [협업 규칙](COLLABORATION.md)의 GitHub 카드·체크포인트와 [카드 양식](../.github/ISSUE_TEMPLATE/card.md). WorkTrail 서버·클라이언트는 도입하지 않음 | [평가](reviews/2026-09-25-worktrail/README.md), [근거](reviews/2026-09-25-worktrail/EVIDENCE.md), [카드 시범](experiments/2026-09-25-card-pilot/README.md) |
| ai_unslop의 island-ui | 색·글자·간격·테마·화면 움직임 | **코드 그대로 복사.** [app/static/island-ui](../app/static/island-ui/README.md). 원본 버전과 변경 절차는 이 폴더의 README가 관리 | [원본 저장소](https://github.com/inlight37-design/ai_unslop), `skills/island-ui/`. 변경은 원본에서 한 뒤 다시 복사 |
| 여러 AI 작업 도구 | 역할판, 사용자 개입, 작업 상태, 문맥 인계 | **선별 설계 참고.** 실제 기능은 [기능 안내](FEATURES.md), 미구현 후보는 조사 기록에서 구별 | [요구·후보·비용](research/multi-ai-workflow-2026-09-25/README.md), [역할판 요청](reviews/2026-09-26-role-board-request/README.md), [구현 순서 판단](reviews/2026-09-26-review-consolidation/README.md) |
| Jev·Lite-Harness·Fusion 등 | 선택적 판단 모델, native CLI 연결, 토큰·비용 평가 | **조사·설계 후보.** Jev가 필수 지휘자이거나 이들 프레임워크가 runtime 의존성인 것은 아님 | [추가 조사](research-2026-09-22/README.md), [초기 Jev 조사](research-notes-2026-09-21.md), [Codex 연결 비교](research-2026-09-22/codex-bridge.md) |

AnchorMind 조사 당시의 수동 기억 우선 제안은 **2026-10-04 사용자 결정으로 일반 팀원·상위 역할의 자동 기억**으로 좁혀 적용했다. 격리 팀원은 제외한다. 당시 검토 기록은 그대로 보존하며, 현재 동작은 [기능 안내](FEATURES.md)의 자동 기억 절이 관리한다. 임베딩·RRF·그래프 DB·자동 회고·충돌 자동 해소·신뢰 점수는 이번 적용에 포함하지 않았다. `probes.mjs`는 upstream 이해를 위한 조사 도구이며 앱 runtime이 아니다.

## 논문과 아키텍처 근거 찾기

| 찾는 내용 | 기준 위치 |
|---|---|
| 상급 모델 독립 추론·교차검토·합성, 연구 결과와 반례 | [v0.4 사례](architecture/v0.4/01-cases-and-findings.md), [v0.4 출처 원장](architecture/v0.4/sources.json) |
| native 하네스·권한·회계·구독 전용 기반 | [v0.3 시스템](architecture/v0.3/01-system.md), [v0.3 출처 원장](architecture/v0.3/sources.json) |
| 결정 번호와 출처를 연결하기 | [v0.4 아키텍처](architecture/v0.4/02-frontier-architecture.md), [v0.3 결정](architecture/v0.3/04-decisions-and-evaluation.md) |
| 계약·fixture·오프라인 검증 경계 | [계약](../contracts/README.md), [v0.4 검증 범위](architecture/v0.4/VALIDATION.md) |
| 날짜별 외부 리뷰·정정·검증 기록 | [리뷰 목록](reviews/README.md). 원본을 고치지 않고 목록에 단서를 붙임 |
| 실제 실행 실험과 관측 환경 | [실험 폴더](experiments/), 현재 적용 가능한 기기·계획은 [인계](../NEXT-SESSION.md) |

출처 원장은 학술·설계 근거이고, 이 지도는 코드와 조사 자료의 길잡이다. 조사에서 읽은 모든 파일을 새 원장 항목으로 중복 등록하지 않는다. 모델 품질·검색 품질을 새로 주장하려면 해당 기능의 대조 실험이 별도로 필요하다.
