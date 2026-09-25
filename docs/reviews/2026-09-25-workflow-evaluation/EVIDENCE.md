# 출처 대조 — 여러 AI 작업 방식

확인일: 2026-09-25. 아래 R 번호는 이 검토 안에서만 쓰는 출처 식별자이며 v0.4 근거 원장의 F 번호가 아니다. 링크의 공식 본문·원본 저장소를 직접 읽었다. 제품을 설치하거나 사용자 PC에서 기능을 실행한 결과는 아니다. 원문의 모든 제품·숫자를 재검증했다고 주장하지 않는다.

## 원문에서 유지·보완할 것

원문: [여러 AI 작업 방식·도구 조사](../../research/multi-ai-workflow-2026-09-25/README.md). 첨부 사본을 기준으로 읽었으며, 날짜가 붙은 원문은 고치지 않는다.

| 원문 위치 | 판정 | 이번 검토 |
|---|---|---|
| §1·§7: 공유 공간, 짧은 규칙, 개발 기억과 독립 참여자의 분리 | 유지 | 읽은 파일도 문맥을 사용한다. 파일은 지속성과 선택적 읽기를 제공하는 것이지 무제한 문맥이 아니다(R01). |
| §3: 자동 요약과 새 세션 인계 구분 | 유지·범위 명확화 | Codex의 임계값 설정은 요약을 시작한다(R02). 새 대화·기존 대화 재개·기록 복제는 별도 API이며, 이것들을 자동 연결하는 복구 정책은 제품이 정해야 한다(R04). |
| §3·§5: Projects가 넘친 작업을 새 세션에서 이어가기도 함 | 조건부 확인 | R05의 오류 표는 새 세션에서 계속한다는 메시지가 있으면 자동 진행, 그렇지 않으면 조정 대화에 새 스레드를 요청하라고 한다. 항상 자동 인계되는 보장은 아니다. |
| §3·§6·§8: Projects에 원격 연결한 로컬 PC 작업을 포함 | 현재 문서와 불일치 | R05는 스레드가 클라우드 세션이고 로컬 세션은 Projects에 편입할 수 없다고 명시한다. 로컬 도구가 필요하면 로컬 세션/agent view를 안내한다. 우리 WSL 작업에 바로 연결할 수 있다고 전제하지 않는다. 영어 URL 열기가 실패해 같은 공식 문서의 번체 중국어판을 확인했으며 번역판 시차 가능성은 남긴다. |
| §3: Codex 보조 에이전트 개수 설정 | 대체로 확인 | 현재 이름은 `agents.max_concurrent_threads_per_session`, 기본값 미지정 시 Codex가 정한다. `agents.max_threads`는 현재 문서에도 남은 legacy alias다(R03). 특정 기본 동시 개수를 고정하지 않는다. |
| §5: Amp가 Handoff를 없애고 자동 요약으로 전환 | 확인 | 2026-05-06 공식 글이 90% 자동 요약과 Handoff 제거를 설명한다(R06). 같은 글은 문맥이 남아도 handoff가 유용할 수 있음을 인정한다. 따라서 우리에게 인계/복구 기능이 필요 없다는 일반 증명은 아니다. |
| §8: 작업 하나 = 세션 하나 = PR 하나 | 운영 구호로만 유효 | 작업은 작게 나누되 세션이 바뀌어도 같은 작업·브랜치·PR을 유지할 수 있어야 한다. 작업 ID와 시도/세션 ID를 분리하는 것은 이번 설계 제안이다. |
| §8: 카드 파일과 수퍼바이저를 두는 비용은 작음 | 수동 시범에 한정 | 자동 실행에는 담당권, 중복/늦은 결과 방지, 취소, 실행 상한, 복구 검사가 추가로 필요하다. 한 작성자가 관리하는 파일 시범과 여러 작성자의 자동 큐는 다르다(R08, 저장소 코드). |
| §4: Beads는 git에 저장하는 작업판 | 구현 설명 보완 | 현재 README는 Dolt 기반, embedded 단일 작성자와 server 다중 작성자 모드, 별도 Dolt 동기화를 설명한다. JSONL은 교환/뷰어용 export이며 원본 저장소나 백업이 아니다(R10). 단순 Markdown 설치처럼 평가하면 비용을 낮게 잡는다. |
| §2·§7: 문서·코드 규모와 시작 읽기 분량 | 이번 세션 미측정 | 원문이 명시한 과거 main `9ca0054`의 전달된 관측이다. 현재 main의 측정값으로 바꾸어 적지 않는다. |

## 직접 읽은 외부 출처

### R01 — Claude Code의 세션과 문맥

- URL: https://code.claude.com/docs/en/how-claude-code-works
- 위치: 세션 저장/재개/분기, context window, context management.
- 확인: 대화·읽은 파일·도구 출력이 문맥을 차지한다. 재개는 이전 세션, 분기는 기록 복사다. 자동 요약 중 세부 지시가 빠질 수 있어 지속 규칙과 필요 시 읽는 자료를 분리한다.
- 한계: 특정 작업에서의 정확도나 요약 손실률은 제공하지 않는다.

### R02 — Codex 설정 참조

- URL: https://learn.chatgpt.com/docs/config-file/config-reference
- 위치: `model_auto_compact_token_limit`, `model_auto_compact_token_limit_scope`, `model_context_window`, `memories.*`.
- 확인: 자동 요약 토큰 임계값을 설정할 수 있다. 임계값은 새 작업자 실행 정책이 아니다.
- 한계: 문서의 현재 설정이 aux-pc에 설치된 판에서 모두 지원된다는 뜻은 아니다. 누적 사용 토큰과 현재 활성 문맥을 혼동하지 않는다.

### R03 — Codex 보조 에이전트

- URL: https://learn.chatgpt.com/docs/agent-configuration/subagents
- 위치: benefits/tradeoffs, permissions, custom agents, configuration.
- 확인: 별도 문맥으로 병렬 조사·검토를 분리하며 사용량이 늘 수 있다. 권한·sandbox 정책을 상속한다. `.codex/agents/` 역할 정의와 동시 실행 설정이 있다.
- 한계: 같은 공급자 내부의 하위 작업이지 Claude와 Codex 사이의 공통 작업 원장이 아니다. 추가 허가를 받을 수 없는 비대화형 실행은 허가 요청에서 실패할 수 있다.

### R04 — Codex App Server

- URL: https://learn.chatgpt.com/docs/app-server
- 위치: lifecycle, start/resume/fork, compact, interrupt, message schema.
- 확인: JSON-RPC로 `thread/start`, `thread/resume`, `thread/fork`, `thread/compact/start`, `turn/start`, `turn/interrupt`를 제공한다. 설치 CLI에서 schema를 생성할 수 있다. `thread/read`는 대화를 재개하지 않고 기록을 읽는다.
- 한계: 새 세션 인계를 만드는 부품이지 우리 예산·Git 백업·자손 종료를 보장하는 완제품은 아니다. `thread/shellCommand`는 sandbox 밖에서 실행하므로 자동 작업 통로로 무분별하게 노출하지 않는다. SDK나 유료 API를 도입해야만 쓰는 통로라고 보지 않는다. 인증·구독 경로와 실제 옵션은 로컬 판에서 별도 관측한다.

### R05 — Claude Code Projects

- URL: https://code.claude.com/docs/zh-TW/claude-projects
- 위치: 개요, project 구조, Overview, 모델/문맥, limitations, troubleshooting.
- 확인: 조정 대화, 작업 스레드, 공유 지시/기억, 검토 대기·사용자 응답 대기 화면. 작업 스레드는 자동 요약하며 넘친 경우 조건부 새 세션 이어가기 안내가 있다. 로컬 세션은 편입 불가라고 명시한다.
- 한계: 공개 베타·계정별 제공 여부를 확인하지 않았다. 본 세션에서는 영어 URL 읽기가 실패했다. 모델·네트워크·권한·추가 크레딧 조건은 우리 구독 전용 운영과 별도로 검토해야 한다.

### R06 — Amp 재구축

- URL: https://ampcode.com/news/neo
- 발표일: 2026-05-06.
- 위치: automatic compaction, discussion of removed handoff, references to other threads.
- 확인: Handoff 기능 제거, 90%에서 자동 요약, 새 스레드에서 다른 스레드 참조는 유지. handoff가 유효한 경우도 있다는 작성자의 단서.
- 한계: 공급자의 설계 선택이며 모든 모델/업무에서 요약만으로 충분하다는 비교 실험이 아니다. 90%를 우리 모든 CLI의 공통값으로 옮기지 않는다.

### R07 — Anthropic 장기 실행 harness 연구

- URL: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- 발표일: 2025-11-26.
- 위치: long-running agent problem, incremental progress, getting up to speed, future work.
- 확인: 요약만으로 부족했던 사례, 작은 작업 단위, 진행 파일·Git 커밋, 새 세션 시작 시 이전 상태와 시험 확인을 제안한다.
- 한계: 공급자 내부의 웹 앱 개발 실험이다. 모든 작업에서 다중 에이전트가 단일 에이전트보다 낫다고 결론내리지 않는다. SDK 예제를 참조하되 우리 앱의 인증/과금 방식 채택으로 연결하지 않는다.

### R08 — OpenAI Symphony 명세 (추가 조사)

- URL: https://github.com/openai/symphony/blob/main/SPEC.md
- 직접 읽은 blob: `cd24131a1e2358cbfecc4f6efb028fc9fc6edefc`, §1–§3, 문서 상태 Draft v1.
- 확인: 이슈마다 작업 공간, 하나의 권위 있는 scheduler 상태, 제한된 동시성, 재시도/backoff, 현재 이슈 상태 재확인, 저장소 `WORKFLOW.md` 계약. 성공은 Human Review 같은 인계 상태일 수도 있다.
- 한계: 일반 분산 워크플로 엔진이나 강한 sandbox를 보장하는 명세가 아니다. 현재 scheduler 메모리 상태를 그대로 재시작 복원한다고 하지 않는다. 우리 원장의 고정 호출 상한·blind 경계를 대신하지 못한다.

### R09 — OpenAI Symphony 소개 (추가 조사)

- URL: https://openai.com/index/open-source-codex-orchestration-symphony/
- 위치: workflow, app server, what's next.
- 확인: 작업판과 Codex App Server 연결, 완료 증거와 검토 인계. 초기 tmux 세션이 작업을 감시하고 보조 에이전트를 띄운 방식은 충분히 안정적이지 않았다고 설명한다. 참조 구현이지 계속 유지할 독립 제품으로 약속한 것이 아니다.
- 한계: 내부 성과·홍보 수치를 우리 프로젝트의 기대 성능으로 사용하지 않는다. Linear·Elixir 구현을 통째로 도입하자는 제안이 아니다.

### R10 — Beads 현재 저장 구조

- URL: https://github.com/gastownhall/beads
- 이전 주소 https://github.com/steveyegge/beads 는 확인 시 위 저장소로 이동했다.
- 위치: README features, essential commands, storage modes.
- 확인: Dolt 기반, 의존성 준비 작업, 원자적 claim, embedded/server 구분, export와 원본 구분. 초기화가 AGENTS.md와 에이전트 통합 설정을 수정할 수 있다.
- 한계: 로컬 원자적 claim 설명을 연결되지 않은 모든 PC의 전역 중복 방지 증명으로 확대하지 않는다. 설치/마이그레이션/계정 환경은 시험하지 않았다.

### R11 — LangGraph persistence (추가 설계 참고)

- URL: https://docs.langchain.com/oss/python/langgraph/persistence
- 위치: checkpointer vs store, troubleshooting.
- 확인: 한 스레드의 체크포인트와 여러 스레드에 걸친 지속 저장소를 구분한다. RAM 저장기는 재시작 후 남지 않는다.
- 한계: 저장이 외부 명령의 정확히 한 번 실행을 보장한다는 근거는 아니다. 개념만 참고하며 새 프레임워크/DB를 도입하지 않는다.

### R12 — Claude Code agent teams

- URL: https://code.claude.com/docs/en/agent-teams
- 위치: experimental status, compare subagents, interactive sessions, permissions, file conflicts.
- 확인: 리더/팀원의 별도 문맥과 작업 목록·메시지. 실험 기능이고 팀원 생성은 대화형 세션이 필요하다. 여러 팀원이 같은 파일을 수정하면 충돌 위험이 있다.
- 한계: 일반 비대화형 다중 공급자 실행기로 대체하지 않는다. 팀의 상호 메시지를 앱의 blind 초안 단계에 허용하지 않는다.

## 저장소에서 직접 읽은 근거

기준 commit: `6e69346852e4863af9a160523170135bdcec7d03`.

| 파일 | 읽은 범위와 확인 |
|---|---|
| `AGENTS.md`, `docs/COLLABORATION.md`, `NEXT-SESSION.md` | 공유 표면·브랜치/병합·인계·구독·독립성 경계. 로컬 실측은 이전 세션 기록이며 새 실측으로 바꾸지 않는다. |
| `app/README.md` | 현재 입력 고정→예약→실행→봉인/공개→합성 흐름, 모듈 책임. |
| `app/store.py` 1–140행 | SQLite 원장·OS 배타 잠금·사건/현재 상태 거래·고정 호출 상한 테이블. |
| `app/controller.py` 1–155행 | 기대 상태와 시도 ID를 통한 결과 수용, unknown 차단, 지속 취소, 재시작 후 명시적 resume, 봉인 투영, Executor 계약. |
| `core/README.md` | 셸 없는 runner·자손 종료 확인·격리, 읽기 전용 논의자 adapter. 코딩 작업자의 쓰기 권한을 이미 지원한다고 보지 않는다. |

이는 수퍼바이저 설계에 필요한 경계 확인이지 저장소 전체 코드의 재감사나 실행 검증은 아니다. 검토 결과와 시범 제안은 [README](README.md)에 정리한다.
