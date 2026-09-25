# WorkTrail 평가 근거와 검증 범위

확인일 **2026-09-25**. 이 문서의 W·L·A 번호는 검토 내부 참조이며 전역 근거 원장 번호가 아니다. 코드에 구현된 검사, 제작자의 설명, 우리의 제안을 구분한다. 소스를 읽었다는 것은 실행·보안·성능을 검증했다는 뜻이 아니다.

## W — WorkTrail: 고정한 소스

검토 commit: [`3fb48f980133fd2fb458362648c7bb04cfdbea2b`](https://github.com/jasonethicseo/worktrail/commit/3fb48f980133fd2fb458362648c7bb04cfdbea2b). 공개 commit 날짜는 2026-09-22이다. 아래 줄 범위는 실제로 읽은 범위다.

| ID | 원문과 위치 | 직접 확인한 내용 | 한계·주의 |
|---|---|---|---|
| W01 | [README.ko.md](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/README.ko.md), 전체 | 작업 초점·결정/제약·원문 증거·노트/다음을 구분한다. Claude Code 훅, Codex MCP, claude.ai 호스팅 연결을 안내한다. macOS/Linux/WSL이며 네이티브 Windows 설치기는 지원하지 않는다고 적는다 | 제작자 안내. 이 세션에서 설치·연결·UI를 시험하지 않았다. ChatGPT 연결 실증으로 확대하지 않는다 |
| W02 | [core/worktrail.py L1–340](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/worktrail.py#L1-L340) | 기록 코어 Worktrail은 모델 없이 동작하도록 분리돼 있다. 원문 evidence와 호스트 note를 나누며 요청 키·내용 지문으로 중복 기록을 처리한다. 결정·제약·스레드·checkpoint 메서드를 제공한다 | Casebook 조사 기능과 구분한다. 같은 요청 키에 다른 내용이 오면 새 키로 기록하는 경로가 있다. 우리 실행/내보내기의 충돌 거절 계약으로 그대로 가져오지 않는다. 전체 파일 감사는 아님 |
| W03 | [core/state.py L1–190](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/state.py#L1-L190) | 결정·제약은 이벤트로 남기고 supersedes로 대체한다. rule_out에는 범위와 근거 ID가 필요하다. 결정은 사실 진술과 구분한다 | authority는 agent/user라는 출처 표기다. 이 경로의 열거값 검사가 사용자 승인 증명을 하지는 않는다. 근거 소유권 검사도 관련성·진실성 검사가 아니다. 동시 결정을 단일 승인으로 확정하는 장치라고 보지 않는다 |
| W04 | [core/hookctx.py L1–175](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/hookctx.py#L1-L175) | 시작 문맥은 현재 스레드·다음 차례·Git anchor를 우선하고 자세한 내용은 resume/trail로 읽게 한다. 문자열 길이 상한은 10,000이다. compact 때 대신 저장해 주지 않으므로 진행 중 기록하라고 명시한다 | 문자 상한이지 토큰 상한·절약률 실측이 아니다. 개발 문맥을 독립 초안 참여자에게 주입해도 안전하다는 근거가 아니다 |
| W05 | [adapters/mcp_server.py L1–155](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/adapters/mcp_server.py#L1-L155) | stdio/HTTP 설명, 짧은 목록·현재 상태 투영, find→trail→inspect 탐색, 원문과 해석 구분. 원격 파일 읽기 도구는 거절한다고 설명한다 | 원격 인증 전체 경로를 감사하지 않았다. 주석의 지원 설명은 실제 ChatGPT 커넥터 접속 확인이 아니다. 검색 적중·인용 일치는 사실 검증이 아니다 |
| W06 | [core/threads.py L1–140](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/threads.py#L1-L140) | 저장소 정체성과 branch/HEAD를 분리한다. 작업 디렉터리별 스레드 바인딩과 가상 chat 공간이 있다. 원격 서버에는 클라이언트가 Git 상태를 전달한다 | 바인딩은 작업 포인터이지 파일 잠금이 아니다. 전달된 Git 상태는 서버가 원격 push를 증명한 값이 아니다. PC·가상 세션의 이름 충돌도 별도 검토 대상 |
| W07 | [core/db.py L1–170](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/db.py#L1-L170), [pyproject.toml](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/pyproject.toml) | SQLite 저장과 append-only API 의도, 요청 키 고유성, Python·FastAPI·Uvicorn·선택적 MCP 의존성을 확인했다 | append-only 애플리케이션 API를 변조 불가능한 저장소로 표현하지 않는다. 테스트 실행·복구·성능·운영 취약점 검증은 하지 않았다. 패키지 버전이나 공개 활동량만으로 성숙도를 단정하지 않는다 |
| W08 | [LICENSE](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/LICENSE), 전체 | FSL-1.1-ALv2. 내부 이용·비상업 교육/연구를 명시적으로 허용한다. 소프트웨어를 이용한 경쟁 상용 제공에는 제한이 있고 복사/수정/파생물 재배포에는 조건이 따른다. 각 판 공개 2년 뒤 Apache-2.0 추가 허가 | 지금 Apache-2.0이라고 하거나 상업적 사용이 전부 금지됐다고 하지 않는다. 우리 제품에 코드 편입·상업 배포할 경우의 최종 법률 판단은 하지 않았다 |

## L — 우리 저장소: 기존 기능과 실제 공백

기준 commit: [`2bcdd20dd95209e96ff5a2c540540584754bd57a`](https://github.com/inlight37-design/decision-model_lab/commit/2bcdd20dd95209e96ff5a2c540540584754bd57a). 아래 링크는 이 평가가 작성된 브랜치에서도 읽을 수 있는 저장소 경로다. 미래에 파일이 바뀌면 위 commit에서 확인한다.

| ID | 원문 | 이 평가에 쓰는 사실 | 한계 |
|---|---|---|---|
| L01 | [AGENTS.md](../../../AGENTS.md), [협업 규칙](../../COLLABORATION.md), [NEXT-SESSION.md](../../../NEXT-SESSION.md) | GitHub 공유 지점, 자체 앱, 단일 writer, 한 사실 한 곳, 현재 안내와 날짜 기록 분리, 작은 문맥과 원격 체크포인트 | 이번 세션의 시작 기준이다. 미래 main 상태를 대신하지 않는다 |
| L02 | [카드 양식](../../../.github/ISSUE_TEMPLATE/card.md), [카드 시범](../../experiments/2026-09-25-card-pilot/README.md) | 목표·범위·완료 조건·입력·모델 상한·체크포인트가 이미 있다. 다른 세션의 이어받기 성공과 실행 설정/셸 주의 누락도 기록돼 있다 | 시범 결과는 이전 세션의 기록이다. 우리가 사용자 PC에서 재현한 결과가 아니다. 같은 계정의 댓글 선점은 협력 규칙이며 원자적 작업 배정으로 보지 않는다 |
| L03 | [이전 작업 방식 평가](../2026-09-25-workflow-evaluation/README.md) §1–3 | 판단 AI/실행 관리자 분리, 개발 기억/독립 초안 분리, 작은 카드부터 시작, 양방향 상태 복제 지양을 이미 제안했다 | 이번 문서는 그 구조를 새로 발명했다고 주장하지 않는다. WorkTrail 소스가 제공하는 구체적인 기록·탐색 설계를 보충한다 |
| L04 | [app 안내](../../../app/README.md), [app/store.py](../../../app/store.py) L1–125 | controller의 예약·수용·봉인/공개, 고정된 상한, 참여자에게 숨긴 SQLite 원장, 단일 controller 잠금. report는 공개 결과 투영의 책임을 가진다 | 실제 앱 실행은 안 했다. 미래 exporter의 완성된 API나 안전성으로 확대하지 않는다 |

## A — 보충 비교: 서로 다른 공백을 메우는 도구

다음은 **2026-09-25에 읽은 공식 저장소 설명의 스크리닝**이다. WorkTrail처럼 핵심 소스를 범위별로 감사한 대상은 아니며 설치하지 않았다. 링크는 변할 수 있는 기본 브랜치다. 실제 시험을 시작할 때 그때의 commit·설정·라이선스를 다시 고정한다. 구체적인 도입 판단은 본문의 제안이다.

| ID | 1차 출처와 읽은 부분 | 확인 내용 | 한계 |
|---|---|---|---|
| A01 | [Entire CLI](https://github.com/entireio/cli), README의 Sessions·Checkpoints·Checkpoint Storage·Strategy·Security & Privacy | AI 세션과 코드 commit의 연결, 별도 checkpoint 저장. 현재 README는 checkpoint별 `refs/entire/checkpoints/<shard>/<id>`를 설명한다. 활성 코드 브랜치를 대신 커밋하는 기능과 구분한다 | 오래된 설명의 단일 checkpoint 브랜치를 현재 구조로 복사하지 않는다. 전체 대화 수집·원격 전송은 공개 저장소의 위험이다. 실제 회복·redaction 성능 미검증 |
| A02 | [Beads](https://github.com/gastownhall/beads), README의 Quick Start·Storage/Collaboration | 의존 작업과 ready 조회, claim, Dolt 기반 저장을 설명한다. JSONL을 기본 원장으로 생각하면 도입 비용을 잘못 평가한다 | 이전 평가 L03에도 있다. 이번에는 새 도입을 권하는 대신 필요할 때 가져올 패턴으로 재분류한다. 다중 PC 경합 성능 미검증 |
| A03 | [MCP Agent Mail](https://github.com/dicklesworthstone/mcp_agent_mail), README와 [SKILL.md](https://github.com/dicklesworthstone/mcp_agent_mail/blob/main/SKILL.md)의 file reservations | 작업자 식별·메시지·스레드와 advisory file leases를 제공한다. 파일 예약은 충돌을 피하기 위한 조정 장치다 | 파일 시스템 강제 격리와 다르다. optional guard가 있더라도 우리의 단일 writer·종료 확인을 대신하지 않는다. 다중 호스트의 프로젝트 정체성과 TTL/복구를 시험하지 않았다 |

## 접근하지 못했거나 검증하지 않은 것

- 사용자 제공 [DCInside 소개 글](https://gall.dcinside.com/mgallery/board/view/?id=ai_utilize&no=87654&exception_mode=recommend&page=1): web 접근이 DisabledError, 모바일 경로도 본문을 얻지 못했다. 글의 내용·작성자 주장·댓글 반응은 근거에 포함하지 않았다.
- WorkTrail [호스팅 신청 페이지](https://casebook-api.syncflo.cloud/join)는 본문 데이터 안내를 추출하지 못했다. 보관 기간·운영자 접근 범위·삭제·국외 전송·백업 정책을 확인했다고 하지 않는다. 가입하거나 데이터를 보내지 않았다.
- 웹 컨테이너의 GitHub DNS 해석 실패로 clone하지 못했다. GitHub 커넥터를 통한 소스 읽기/쓰기와 웹 검색은 성공했다. 로컬 전체 시험, WorkTrail 설치·부하·동시 쓰기·장애 복구·보안 시험은 실행하지 않았다.
- 사용자 PC/WSL의 CLI·로그인·권한·사용량은 확인하지 않았다. 실제 모델/구독 CLI 호출은 하지 않았다. 별도 MCP·훅·서비스를 설치하거나 설정하지 않았다.
- PR의 CI는 이 저장소 변경에 대한 검사다. 최종 PR에서 상태를 확인하며, 통과하더라도 WorkTrail 실행 품질·생산성 개선·데이터 안전성의 증거로 쓰지 않는다.

## 이 근거가 허용하는 결론

소스에서 확인한 기록/탐색 방식은 우리 개발 인계에 응용할 만하다. 기존 카드·원장과 겹치므로 통째 도입의 순이익은 아직 입증되지 않았다. 제품 평가, 독립성 경계 분석, 최소 적용안까지는 제시할 수 있지만 성능 향상률·보안 인증·실사용 성공을 선언할 수는 없다.
