# 검토 출처와 확인 범위

확인일은 모두 **2026-09-23 (Asia/Seoul)**. R01–R19는 이번 검토 문서 안에서만 쓰는 참조 ID이며 기존 E/F 원장이나 D 결정의 새 승인 항목이 아니다. 공식 사양·제작자 문서·공식 저장소 README를 읽었다. 외부 앱 설치, 코드 전수 감사, 보안 보증, 사용자 구독 호환성 실험은 하지 않았다.

별도 발행일을 확인하지 않은 rolling 문서는 **published: null**이다. 확인일을 발행일로 바꾸지 않는다. 사양 버전이 있는 경우 아래에 적었다. README가 설명하는 기능은 제작자 보고이며, 아래 제안의 우월성을 입증한 비교 실험은 아니다. [검토 본문](README.md)에서 해당 ID와 연결한다.

| ID | 1차 출처 · locator | 확인한 내용 | 한계 / 적용 경계 |
|---|---|---|---|
| R01 | [MCP Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools), 2025-11-25 사양, Tool Result / Annotations / Error Handling / Security Considerations | structuredContent·outputSchema·isError, 신뢰할 수 없는 annotation, 도구 입력과 실행 경계 | 사양을 읽은 것이며 MCP 서버 구현·인가·실제 테스트 통과 증명이 아니다 |
| R02 | [MCP Security Best Practices](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices), Token Passthrough / Confused Deputy / SSRF / Local MCP Server Compromise | 토큰 전달, 권한 혼동, URL 회수, 로컬 실행의 위험을 분리 | 제품 전체의 보안 감사가 아니며 구체적인 OS sandbox 구현은 후속 작업 |
| R03 | [GitHub MCP Server](https://github.com/github/github-mcp-server), README의 Read-only mode / Toolsets / tools 설정 | read-only 모드와 노출 도구 축소 경로 | 설치·로그인·사용자 권한을 확인하지 않았다. 이 대화의 GitHub connector와 사용자 앱의 MCP 구성은 별개 |
| R04 | [Playwright MCP](https://github.com/microsoft/playwright-mcp), README의 CLI + Skills / Security | coding agent의 CLI 대안, 브라우저 도구가 보안 경계가 아니라는 설명 | MCP를 설치·호출하지 않았다. 이번 UI smoke는 별도 Playwright Python 스크립트 |
| R05 | [Context7](https://github.com/upstash/context7), README의 library ID / version / tool usage | 라이브러리 문서를 식별하고 개발 문맥에 공급하는 방식 | 인덱스의 최신성·완전성이나 답변 진실성은 보증하지 않는다. 실제 의존 버전과 원문 대조 필요 |
| R06 | [MCP Inspector](https://github.com/modelcontextprotocol/inspector), README의 UI / CLI / TUI 및 요구 환경 | MCP 개발·호환성 확인용 도구 | 설치하지 않았다. Node 및 패키지 요구는 설치할 시점에 고정해 확인 |
| R07 | [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp), README의 Data collection / performance / security 안내 | 브라우저 진단, 사용 통계와 CrUX 관련 설정 및 데이터 노출 주의 | 실제 네트워크 전송을 측정하지 않았다. telemetry opt-out와 CrUX 제한은 서로 구분해야 한다 |
| R08 | [Codex App Server](https://developers.openai.com/codex/app-server) → [공식 문서 이동 주소](https://learn.chatgpt.com/docs/app-server), account/rateLimits/read / account/rateLimits/updated / rateLimitsByLimitId | 계정 한도 snapshot·갱신 이벤트, primary/secondary 및 여러 limit bucket | 사용자 설치 버전·인증·실제 응답은 미검증. 문서 JSON 예시를 실제 잔여 한도로 취급하지 않는다 |
| R09 | [ACP v1 Overview](https://agentclientprotocol.com/protocol/v1/overview), initialization / capability negotiation / session flow | agent와 client의 세션 통신 계약 | ACP라는 이름만으로 모든 provider의 지원·권한·한도 관측을 보증하지 않는다 |
| R10 | [Orca 공식 저장소](https://github.com/stablyai/orca) 및 [공식 제품 설명](https://www.onorca.dev/), worktrees / parallel agents / inline review | 작업 격리와 diff 중심 검토 패턴 | 제품 설명 수준 확인. 코드 복사·라이선스 전수 감사·sandbox 검증 없음 |
| R11 | [Paseo](https://github.com/getpaseo/paseo), README의 daemon / clients / prerequisites | 실행 daemon과 여러 UI client, 기존 coding CLI 필요 | 원격 연결의 암호화·인가를 직접 시험하지 않았다. 모바일/relay가 첫 파일럿에 필수라는 뜻 아님 |
| R12 | [herdr](https://github.com/herdrdev/herdr), README의 persistence / reattach / restore | detach 시 실행 유지와 재시작 후 복원 구분 | 기능 설명이지 사용자의 Windows 기기에서 재현한 결과가 아니다 |
| R13 | [herdr Session state and restore](https://herdr.dev/docs/session-state/), survival 표와 native agent resume 설명 | client 단절, server 재시작, 기기 재시작의 원 프로세스 생존 범위가 다름 | 배치 복원·resume를 원 프로세스 생존이나 fresh blind context로 해석하면 안 됨 |
| R14 | [OpenCode Server](https://opencode.ai/docs/server/), Architecture / Authentication / OpenAPI / Events | HTTP 서버, OpenAPI, SSE와 UI client 분리 | 서버를 띄우거나 인증 설정을 검증하지 않았다. 구조만 참조하며 Python 코어 교체 제안 아님 |
| R15 | [AionUi](https://github.com/iOfficeAI/AionUi), README의 existing CLI integration / auto detection / built-in agent | CLI 탐지 및 통합 온보딩, 별도 내장 API agent 경로 | 자동 탐지가 로그인·effective permission 확인을 의미하지 않는다. 로컬 DB가 외부 전송 없음의 증명도 아님 |
| R16 | [Vibe Kanban](https://github.com/BloopAI/vibe-kanban), README의 sunsetting 안내와 작업·workspace·리뷰 기능 | 작업부터 diff·PR로 이어지는 동선, 유지보수 방향에 관한 종료 예정 안내 | 실제 서비스 종료 시각이나 GitHub archive 상태는 단정하지 않는다. 기반 의존성보다 패턴 참고로 제한 |
| R17 | [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence), threads / checkpoints / memory store / checkpointer libraries | thread checkpoint와 cross-thread store, 메모리형과 영속 saver 구분 | crash·동시 writer·부작용 재실행을 이 프로젝트에서 검증한 것은 아니다 |
| R18 | [Claude Code Agent Teams](https://code.claude.com/docs/en/agent-teams), experimental setup / limitations / plan approval / permissions | task 의존성·소유자·완료 hook, 메시지, 권한 상속 및 비대화형 경로 제약 | 실험 기능. 다른 회사 CLI나 구독 혼합 협업에 일반화하지 않는다. 자동 plan approval을 인간 승인으로 표시하지 않음 |
| R19 | [WCAG 2.2 Understanding Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), contrast ratio / normal text | 일반 글자 4.5:1 기준과 대비 계산 근거 | 이번 계산은 불투명 sRGB token 쌍만. 실제 CSS·확대·포커스·스크린리더·전체 WCAG 준수 판정은 아님 |

## 저장소 내부 근거

아래는 시작 commit `c109840890bd72cbe5135f14c4d90c54c9039f0f`에서 읽은 대상이다. 모델 답변 요약이 아니라 실제 파일 내용을 확인했다.

- [기존 checker](https://github.com/inlight37-design/decision-model_lab/blob/c109840890bd72cbe5135f14c4d90c54c9039f0f/tools/check_frontier_protocol.py): validate의 synthetic 제한, 입력된 disposition 검사, log_ref 문자열 검사. 원문과 실행 검증은 수행하지 않는다.
- [브랜드 문서](https://github.com/inlight37-design/decision-model_lab/blob/c109840890bd72cbe5135f14c4d90c54c9039f0f/design/project/README.md): 의미 규칙, 단계적 공개, 기존 구현에 대한 설명을 checker와 대조했다.
- [토큰](https://github.com/inlight37-design/decision-model_lab/blob/c109840890bd72cbe5135f14c4d90c54c9039f0f/design/project/tokens.json): Git blob `c7ca934569ed612c120a111c53310402e518f64c`; 대비 계산 값의 근원이다.
- [DecisionCard](https://github.com/inlight37-design/decision-model_lab/blob/c109840890bd72cbe5135f14c4d90c54c9039f0f/design/project/components/DecisionCard/preview.html), [BlindBarrier](https://github.com/inlight37-design/decision-model_lab/blob/c109840890bd72cbe5135f14c4d90c54c9039f0f/design/project/components/BlindBarrier/preview.html), [BudgetMeter](https://github.com/inlight37-design/decision-model_lab/blob/c109840890bd72cbe5135f14c4d90c54c9039f0f/design/project/components/BudgetMeter/README.md): 고정 표본과 실제 runtime UI를 구분했다.
- [기존 NEXT-SESSION](https://github.com/inlight37-design/decision-model_lab/blob/c109840890bd72cbe5135f14c4d90c54c9039f0f/NEXT-SESSION.md), AGENTS, v0.4 HANDOFF, CI 및 test_research_integrity.py를 읽어 유지할 결정과 검사 범위를 확인했다.

## 남는 근거의 공백

실제 CLI 버전·구독 로그인·권한·cancel·fresh context를 확인하지 않았으므로 configured=true로 바꾸지 않는다. 외부 README가 바뀔 수 있으므로 실제 재사용 단계에서는 release/commit과 파일별 LICENSE를 고정해야 한다. 새로운 논문의 정확도 결과를 재현하거나 첫 화면의 사용자 실험을 실행한 것도 아니다. 이번 제안의 효과는 후속 V04-01/V04-03/Q8에서 검증한다.
