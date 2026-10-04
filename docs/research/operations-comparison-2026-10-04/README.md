# tmux와 남은 운영·작업 도구 심층 비교

2026-10-04, 클라우드 컨테이너에서 수행한 후속 조사다. 사용자 요청은 tmux와 나머지 참고 프로젝트를 해체해, 나중에 비슷한 기능을 비교하고 Decision AI에 넣기 좋은 형태로 남기는 것이다. **앱 기능을 구현하거나 외부 에이전트 서비스를 도입한 기록은 아니다.**

앞선 [기능 후보 목록](../feature-catalog-2026-10-04/README.md)의 O22–O33을 구체화한다. [AnchorMind·Hermes·Peek·WorkTrail 부품 분석](../component-comparison-2026-10-04/README.md)은 그대로 연결한다. 여기서는 실행 연결, 작업 대기열, 명세·의존성, 체크포인트, 문맥 관리, 비동기 검토를 다룬다.

## 어디부터 읽을까

| 필요 | 문서 | 얻는 것 |
|---|---|---|
| 전체 기능을 나란히 비교 | [COMPARISON](COMPARISON.md) | 비슷한 이름 아래 다른 책임, 현재 있는 기반, 적용 후보 |
| 화면을 닫거나 끊겼다가 돌아오기 | [TMUX](TMUX.md) | client/server, 명령 큐, control 응답, 구독, 화면과 원본의 차이 |
| 다음 일·담당·막힘을 관리 | [TASK-SYSTEMS](TASK-SYSTEMS.md) | Beads, Backlog.md, Gas Town의 경계와 실패 처리 |
| 체크포인트·압축·CLI 연결·복구 | [AGENT-RUNTIMES](AGENT-RUNTIMES.md) | Cline, Lite-Harness, Symphony의 실제 코드 경로 |
| 편의 기능·제품 화면을 참고 | [PRODUCT-WORKFLOWS](PRODUCT-WORKFLOWS.md) | Conductor, Kiro, Cursor, Devin, Copilot, Jules, Amp, Jev/Fusion |
| 우리 코드에 넣을 조각 선택 | [ADOPTION](ADOPTION.md) | OP01–OP12의 흐름·데이터·코드 위치·시험·비용 |
| 검토 범위와 재현 확인 | [EVIDENCE](EVIDENCE.md) | 고정 commit, 파일별 읽은 범위, 직접 실행한 probe와 미검증 사항 |

## 이번에 확인한 수준

| 대상 | 이번 범위 | 실제 실행 |
|---|---|---|
| tmux 3.7c | 명령/이벤트/화면/대기/수명 핵심 함수 | 격리 socket에서 control mode, detach/reconnect, 화면·종료 상태 시험 |
| Beads | claim CAS, Dolt transaction/history 경계, ready, lease, compaction | 소스 분석만. Dolt 서버·동시 claim 실험 없음 |
| Backlog.md | 공통 identity/ready/graph, 잠금·저장, 검색·snapshot 인터페이스 | 실제 TypeScript 순수 함수 시험; Bun 앱·브라우저 미실행 |
| Gas Town | dispatch 계획/실행/후처리, convoy, 재사용 판정, formula, nudge | 소스 분석만. 작업자·refinery·tmux 통합 미실행 |
| Cline | SDK checkpoint/compaction, VS Code 규칙·파일 변경 감지 | 선택 소스 분석만. SDK와 확장 표면을 구분 |
| Lite-Harness | Session/protocol, Codex 변환기/런타임, Python transport | 순수 함수·가짜 runtime 시험; provider SDK·모델 미호출 |
| Symphony | orchestrator, workflow reload, workspace, runner, App Server 진입 | 선택 소스 분석만. Linear·Codex 연결 미실행 |
| 비공개 제품·Jev/Fusion | 공식 문서의 흐름·제약·업체 보고 | 로그인·실사용·벤치마크 재현 없음 |

전체 tracked 경로를 [inventory](inventory)에 분류했지만, **전체 파일을 읽었다는 뜻은 아니다.** `inventory-only`, 선택 범위, 전체 본문 읽기를 구별했다. 각 코드베이스의 플러그인·모든 화면·모든 테스트를 완전 감사했다고 주장하지 않는다. 기존 연구에 등장한 모든 모델·논문을 이번에 다시 검증한 것도 아니다.

## 가장 유용한 구분

- **준비됨, 맡음, 자리 있음, 호출 가능함**은 다른 상태다. Backlog의 의존성 판정, Beads의 claim, Gas Town의 capacity, 우리 controller의 호출·격리 계약을 하나의 `ready`로 합치지 않는다.
- **연결, 실행, 결과 저장, 검토 완료**도 다르다. tmux `%end`는 비동기 작업 완료 증명이 아니고, dead pane이 남아 있어도 프로세스는 실패할 수 있다.
- **파일 복구, 대화 복구, 외부 부작용 복구**는 범위가 다르다. 체크포인트 버튼에 복구 대상을 보여줄 가치가 크다.
- **성공 모양의 공통 JSON**이 실제 성공을 보장하지 않는다. Lite-Harness의 기본 success/비용 0을 우리 실행 결과로 승격하면 안 된다.
- 편의 기능의 상당수는 모델 호출 없이 가능하다. 막힘 설명, 선택 대상 고정, 비교 보기, 저장된 필터, 변경 이력, 결과 링크부터 독립적으로 고를 수 있다.

우선 추천은 [OP01·OP03·OP05·OP06·OP12](ADOPTION.md)의 읽기/미리보기 부분이다. 클라우드에서 구현·모의 검증할 수 있다. 상시 실행, native CLI 문맥 압축, 실시간 개입, 실제 Git 복원은 별도 기능 카드와 기기 관측이 필요한 큰 조각으로 남긴다. 우선순위는 후보를 폐기한다는 뜻이 아니다.
