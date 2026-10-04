# 출처·검토 범위

[목록 입구](README.md)

## 방법과 기준

확인일 2026-10-04. 우리 기준은 main `6cfb78c5a91dc26a46d95229c89f6e2bbfb6830c`. 클라우드에서 공개 저장소를 clone하고 공식 웹 문서를 읽었다. 실제 사용자 PC·설치된 CLI·upstream 제품을 실행하지 않았고, 외부 모델 호출·로그인·플러그인 설치도 하지 않았다. 아래 소스 링크는 clone 당시 HEAD에 고정했다. **main 소스의 기능 설명은 안정 릴리스나 우리 구독에서 사용할 수 있다는 보장이 아니다.**

검토 깊이는 다음과 같다.

- **문서 확인:** 기능 설명·관련 절을 읽음. 파일 전부의 모든 옵션과 기본값을 감사한 것은 아니다.
- **코드 부분 확인:** 명시한 함수·경로를 읽어 문서와 대조. 실행·보안 감사와 다르다.
- **기존 조사 재독:** 이전 세션의 고정 근거를 다시 읽음. 이번 최신 원본 재확인으로 표현하지 않는다.
- **우리 제안:** 각 후보의 작은 적용·비용·시험. 외부 제품의 검증된 효과로 인용하지 않는다.

Hermes는 `user-guide/features/*.md`의 제목·도입·기능군을 훑고, 세션/화면/기억/스킬/작업/예약의 관련 절을 더 읽었다. 개별 문서의 모든 backend와 외부 플러그인을 실행하거나 전수 분석하지 않았다. [대응표](HERMES-COVERAGE.md)는 검토 대상 기능 안내를 누락 없이 추적하기 위한 것이다. 원본 문서 전문·첨부 PDF·개인 기록은 저장소에 복사하지 않았다.

## 고정한 저장소

| 저장소 | 읽은 HEAD | root 라이선스 |
|---|---|---|
| NousResearch/hermes-agent | [`55bea1ddf1754dcacb87f13185df1eb1273c0a6e`](https://github.com/NousResearch/hermes-agent/tree/55bea1ddf1754dcacb87f13185df1eb1273c0a6e) | MIT |
| JinHo-von-Choi/anchormind | [`cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb`](https://github.com/JinHo-von-Choi/anchormind/tree/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb) | Apache-2.0 |
| kimbyungsu/codex-peek | [`1baf5ccd360b50da57911401aeca1388e1b0c05e`](https://github.com/kimbyungsu/codex-peek/tree/1baf5ccd360b50da57911401aeca1388e1b0c05e) | MIT |
| jasonethicseo/worktrail | [`3fb48f980133fd2fb458362648c7bb04cfdbea2b`](https://github.com/jasonethicseo/worktrail/tree/3fb48f980133fd2fb458362648c7bb04cfdbea2b) | FSL-1.1-ALv2 |
| steveyegge/beads | [`2f1e8be3ca1fe990727858ccd8e4a78461b39c7c`](https://github.com/steveyegge/beads/tree/2f1e8be3ca1fe990727858ccd8e4a78461b39c7c) | MIT |
| MrLesk/Backlog.md | [`69e7b15362337d6712783d9a685f6e4bb693fa9d`](https://github.com/MrLesk/Backlog.md/tree/69e7b15362337d6712783d9a685f6e4bb693fa9d) | MIT |
| gastownhall/gastown | [`649b832b7672bc7a2dbef26f5983aba6198b819b`](https://github.com/gastownhall/gastown/tree/649b832b7672bc7a2dbef26f5983aba6198b819b) | MIT |

root LICENSE를 확인했다. 파일·asset·의존성의 라이선스를 모두 대신하지 않는다. 이번 작업은 분석과 우리 적용안 작성이며 소스 이식은 없다. WorkTrail은 경쟁 용도 제한과 판별 전환 조건이 있는 source-available 라이선스이므로, 코드를 가져오거나 서비스로 제공할 때 별도로 검토해야 한다. 별 수·인지도·제작자 성능 수치를 채택 근거로 쓰지 않았다.

## Hermes 근거

### H-UI

[website/docs/user-guide/desktop.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/desktop.md) · [website/docs/user-guide/bot-mode.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/bot-mode.md)

읽은 범위: 세션/프로젝트·모델 선택·즐겨찾기·Artifacts·탭/분할·Simple mode·Subagents·Review/Worktrees·Memory Graph·Quick Entry 및 Bot Mode 도입.

한계: UI 문서 확인. 실제 화면 조작·렌더링·접근성·각 플랫폼 지원을 시험하지 않음.

### H-SESSION

[website/docs/user-guide/sessions.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/sessions.md) · [website/docs/reference/slash-commands.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/reference/slash-commands.md)

읽은 범위: 세션 저장·문맥에 들어가는 내용·source 구분, 이름/재개/검색, retry/undo/snapshot 등 명령 표.

한계: 명령 이름이 Decision Lab에 존재한다는 뜻이 아님. 전체 삭제/복구 동작 미실행.

### H-CONTEXT

[website/docs/user-guide/features/context-files.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/context-files.md) · [website/docs/user-guide/features/context-references.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/context-references.md)

읽은 범위: 발견하는 지침 파일과 범위, @file/줄 범위/folder/diff/git/URL·크기 상한·경로 제한.

한계: 자료 참고와 지침 로딩을 분리해서 적용. 문서의 잘못된 줄 범위 처리까지 그대로 채택하지 않음.

### H-MEMORY

[website/docs/user-guide/features/memory.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/memory.md) · [website/docs/user-guide/profiles.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/profiles.md) · [website/docs/user-guide/features/memory-providers.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/memory-providers.md) · [website/docs/user-guide/features/honcho.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/honcho.md)

읽은 범위: bounded memory·USER·frozen snapshot·쓰기 승인/실제 저장 확인, profile별 분리, 외부 provider/Honcho의 도입 설명.

한계: provider별 구현·사용자 모델링 품질·개인정보 처리 전체 미감사. profile은 적대적 OS 격리 보장이 아님.

### H-SKILL

[website/docs/user-guide/features/skills.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/skills.md)

읽은 범위: progressive disclosure·website install·blank profile·stacking·/learn·external/project directories·scan·bundles·agent-managed skills·catalog.

한계: 스캐너가 안전을 증명하는 것으로 취급하지 않음. 개별 스킬 본문/스크립트 전수 미검토.

### H-CURATOR

[website/docs/user-guide/features/curator.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/curator.md)

읽은 범위: 실행 조건, deterministic stale/archive와 opt-in LLM consolidation, pin·cron 참조·미사용 유예·dry-run.

한계: 자동 정리와 모델 통합을 구분. 실제 실행 비용/효과 미측정.

### H-SKILL-CATALOG

[website/docs/reference/skills-catalog.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/reference/skills-catalog.md) · [website/docs/reference/optional-skills-catalog.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/reference/optional-skills-catalog.md)

읽은 범위: 목록의 분류·기술 방식과 분야 탐색 입구.

한계: 개별 스킬의 가용성·의존성·라이선스·실행은 설치 후보 선택 후 확인할 것.

### H-DELEGATE

[website/docs/user-guide/features/delegation.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/delegation.md)

읽은 범위: 비동기 완료·handle·process 소유권·single/batch·output_schema·제한된 수정 요청, Desktop monitoring 설명과 대조.

한계: 격리된 대화와 OS 격리/독립성은 다름. 전체 lifecycle race 감사 아님.

### H-TEAM

[website/docs/user-guide/features/mixture-of-agents.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/mixture-of-agents.md)

읽은 범위: preset·aggregator/참조 역할·one-shot·실행 주기·비용 안내.

한계: 문서 확인. 모든 payload builder 분기와 실제 provider 과금 미확인.

### H-GOAL

[website/docs/user-guide/features/goals.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/goals.md) · [website/docs/user-guide/features/loops.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/loops.md) · [website/docs/user-guide/features/heartbeat.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/heartbeat.md)

읽은 범위: 도입·사용처·서로 다른 수명·명령/상한·중단 조건.

한계: judge의 판단·자동 재개·반복 사용량은 미실험. 목표 완료 판정을 사실 검증으로 부르지 않음.

### H-KANBAN

[website/docs/user-guide/features/kanban.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/kanban.md) · [website/docs/user-guide/features/kanban-worker-lanes.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/kanban-worker-lanes.md) · [website/docs/user-guide/features/kanban-multi-gateway.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/kanban-multi-gateway.md) · [website/docs/user-guide/features/kanban-tutorial.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/kanban-tutorial.md)

읽은 범위: board/worker 구분·checkpoint·PR 완료 계약·review handoff·소유권·multi-gateway 도입 및 tutorial 사용 흐름.

한계: 협력적 소유권 검사는 OS confinement이 아님. 전체 dispatcher·PR acceptance 코드는 감사하지 않음.

### H-CRON

[website/docs/user-guide/features/cron.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/cron.md)

읽은 범위: 할 수 있는 일·모델 pin·preflight·script-only·외부 event·전달·재귀 예약 제한.

한계: 실제 scheduler·시간대·재시작·인증·가격 미실험.

### H-HOOK

[website/docs/user-guide/features/hooks.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/hooks.md) · [website/docs/developer-guide/observer-hooks.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/developer-guide/observer-hooks.md)

읽은 범위: gateway/plugin/shell/outbound hook 종류와 observer 표면 도입.

한계: 모든 훅이 passive가 아님. 개별 callback과 외부 전송은 실행하지 않음.

### H-DELIVERY

[website/docs/developer-guide/completion-backlog-delivery.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/developer-guide/completion-backlog-delivery.md) · [website/docs/user-guide/features/delegation.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/delegation.md)

읽은 범위: 완료 묶음·소유권·이미 소비한 결과·busy 재대기, queue admission과 실제 전달의 차이.

한계: 문서의 at-least-once 설명을 exactly-once로 확대하지 않음.

### H-ARTIFACT

[website/docs/user-guide/features/deliverable-mode.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/deliverable-mode.md)

읽은 범위: 파일 attachment·지원 형식·응답에서 파일 찾기·Kanban 완료 첨부.

한계: 임의 경로 자동 업로드를 그대로 제안하지 않음. 우리 앱에서는 허용한 산출물 목록으로 연결.

### H-MCP

[website/docs/user-guide/features/mcp.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/mcp.md)

읽은 범위: stdio/HTTP·도구 발견·도구 필터·resources/prompts 개요.

한계: 연결·인증·도구 실행 미수행. 기존 blind 참여자에 자동 연결하지 않음.

### H-TOOLSEARCH

[website/docs/user-guide/features/tool-search.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/tool-search.md)

읽은 범위: tool_search/describe/call·deferred schema·core/외부 도구 구분·묶음 호출·검색 실패 안내.

한계: 절감량과 검색 재현율 미측정. 도구 이름 발견이 호출 권한이 아님.

### H-PLUGIN

[website/docs/user-guide/features/plugins.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/plugins.md) · [website/docs/user-guide/features/plugin-catalog.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/plugin-catalog.md) · [website/docs/user-guide/features/built-in-plugins.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/built-in-plugins.md) · [website/docs/user-guide/features/extending-the-dashboard.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/extending-the-dashboard.md)

읽은 범위: manifest·discovery·catalog review·내장 plugin·theme/UI slot/backend router 개요.

한계: plugin 코드를 실행하지 않음. 권한·제3자 유지비는 개별 검토 필요.

### H-NATIVE

[website/docs/user-guide/features/codex-app-server-runtime.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/codex-app-server-runtime.md)

읽은 범위: opt-in native runtime·도구 소유·workflow·설정/MCP migration·auxiliary 호출 비용 설명.

한계: 현재 계정 권리·공식 지원과 설치 CLI 동작 미관측. 해당 직접 인증 경로를 우리 실행 허가로 취급하지 않음.

### H-API

[website/docs/user-guide/features/acp.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/acp.md) · [website/docs/user-guide/features/api-server.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/api-server.md) · [website/docs/user-guide/features/subscription-proxy.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/subscription-proxy.md)

읽은 범위: ACP host 표면·agent API·Runs/Sessions/Jobs 개요·raw inference proxy와의 구분.

한계: API 호환성·동시성·인증 코드 미감사. raw proxy는 기존 공식 CLI 우선 범위 밖.

### H-REMOTE

[website/docs/user-guide/multi-connection-desktop.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/multi-connection-desktop.md) · [website/docs/user-guide/messaging/index.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/messaging/index.md) · [website/docs/user-guide/profiles.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/profiles.md)

읽은 범위: 다중 gateway·profile·platform 개요 및 연결 UI 도입.

한계: 개별 messaging adapter·외부 계정·원격 실행 검증 없음.

### H-DOC

[website/docs/user-guide/features/document-extraction.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/document-extraction.md)

읽은 범위: 지원 형식·read_file 변환·크기/페이지·scan coverage·누락 경고.

한계: 표·수식·OCR 정확성 및 lazy converter 설치 미시험.

### H-WEB

[website/docs/user-guide/features/web-search.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/web-search.md) · [website/docs/user-guide/features/x-search.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/x-search.md)

읽은 범위: search/extract 분리·backend 표·캐시/긴 페이지 처리 안내·X 전용 read/write 표면 차이.

한계: 무료 구간·가격·계정 권리는 보장하지 않음. 웹 도구의 주장을 원문 사실로 승격하지 않음.

### H-BROWSER

[website/docs/user-guide/features/browser.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/browser.md) · [website/docs/user-guide/features/computer-use.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/computer-use.md) · [website/docs/user-guide/features/bot-screen.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/bot-screen.md)

읽은 범위: backend 종류·snapshot/조작·computer-use 도입·bot screen 및 사람이 제어받는 흐름.

한계: 실제 브라우저·OS·로그인·권한 미시험. 소비자 AI 앱 화면 자동화는 현재 제품 범위 밖.

### H-MEDIA

[website/docs/user-guide/features/vision.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/vision.md) · [website/docs/user-guide/features/image-generation.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/image-generation.md)

읽은 범위: clipboard vision·첨부·모델별 입력 경로와 이미지 생성 backend 도입.

한계: 품질·모델 제공 여부·가격 미측정.

### H-VOICE

[website/docs/user-guide/features/voice-mode.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/voice-mode.md) · [website/docs/user-guide/features/tts.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/tts.md) · [website/docs/user-guide/features/wake-word.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/wake-word.md)

읽은 범위: STT/TTS·dictation·local/remote 선택·wake word 동작.

한계: 한국어 음성·마이크·지연·개별 서비스 비용을 확인하지 않음.

### H-CODE

[website/docs/user-guide/features/code-execution.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/code-execution.md) · [website/docs/user-guide/features/lsp.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/lsp.md)

읽은 범위: programmatic tool RPC·child execution·kernel·resource limit·LSP 도입/진단 표면.

한계: 실행 권한·sandbox·language server 설치/실행 미검증.

### H-OPS

[website/docs/user-guide/features/web-dashboard.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/web-dashboard.md) · [website/docs/user-guide/checkpoints-and-rollback.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/checkpoints-and-rollback.md) · [website/docs/reference/cli-commands.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/reference/cli-commands.md)

읽은 범위: dashboard 페이지와 API 항목·analytics/logs/resource pressure, checkpoint/rollback 도입·명령·shadow store, doctor 등 CLI 표.

한계: 전체 관리 API·복구·보안 감사가 아님. 미리보기와 실제 외부 동작을 분리.

### H-ONBOARD

[website/docs/developer-guide/onboarding-recommendations.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/developer-guide/onboarding-recommendations.md) · [website/docs/getting-started/quickstart.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/getting-started/quickstart.md)

읽은 범위: 추천 목적/관측한 capability/연결 없는 대안의 원칙과 초기 설정 도입.

한계: 모든 onboarding 모델 프롬프트·설치 절차를 실행하지 않음.

### H-IMPORT

[website/docs/user-guide/import-from-other-agents.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/import-from-other-agents.md)

읽은 범위: preview-first·dry-run 및 instructions/allowlist/MCP/skills/memory 이관 목록.

한계: 실제 사용자 파일·인증을 읽거나 복사하지 않음.

### H-STYLE

[website/docs/user-guide/features/personality.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/personality.md) · [website/docs/user-guide/features/skins.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/skins.md) · [website/docs/user-guide/features/language-packs.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/language-packs.md) · [website/docs/user-guide/features/pets.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/pets.md)

읽은 범위: persona/visual style 분리·locale overlay·상태 sprite·기본 opt-in 설명.

한계: asset 라이선스·번역 완성도·화면 접근성 미검증.

### H-TOOLS

[website/docs/user-guide/features/tools.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/tools.md)

읽은 범위: toolsets·terminal backend 분류와 process 관리 개요.

한계: backend별 격리·비용·운영 지원을 우리 앱에 그대로 보장하지 않음.

### H-PROVIDER

[website/docs/user-guide/features/provider-routing.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/provider-routing.md) · [website/docs/user-guide/features/fallback-providers.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/fallback-providers.md) · [website/docs/user-guide/features/credential-pools.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/credential-pools.md) · [website/docs/user-guide/features/tool-gateway.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/tool-gateway.md)

읽은 범위: routing/fallback/pool 차이, cache 비용, 별도 Portal tool gateway.

한계: API 자동 전환·인증 우회는 권고하지 않음. 계정별 사용 권리와 가격은 별도 확인.

### H-SECRET

[website/docs/user-guide/features/credential-vault.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/credential-vault.md) · [website/docs/user-guide/secrets/index.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/secrets/index.md)

읽은 범위: 모델 밖 비밀 처리라는 UX·외부 secret provider 개요.

한계: 암호화·redaction·vault 구현을 감사하지 않았으며 우리 사용자 인증 상태도 미접근.

### H-DOMAIN

[website/docs/user-guide/features/spotify.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/spotify.md) · [website/docs/user-guide/messaging/index.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/messaging/index.md) · [website/docs/reference/optional-skills-catalog.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/reference/optional-skills-catalog.md)

읽은 범위: 음악·메신저·업무별 확장 종류와 필요한 계정 설명.

한계: 개별 플랫폼 기능 전체와 인증·외부 쓰기 미실행.

### H-BATCH

[website/docs/user-guide/features/batch-processing.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/features/batch-processing.md)

읽은 범위: dataset·batch runner·checkpoint/resume·trajectory 개요.

한계: 학습 데이터 생성량·성능·비용 재현 없음.

### H-COMPACT

[website/docs/developer-guide/context-compression-and-caching.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/developer-guide/context-compression-and-caching.md) · [website/docs/developer-guide/micro-compaction.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/developer-guide/micro-compaction.md)

읽은 범위: 압축 엔진/캐시·micro-compaction 동기와 호출/cache tradeoff 도입.

한계: 요약 보존율·지연·cache 절감 실측 없음. 매 턴 압축을 기본으로 권하지 않음.

### H-WORKTREE

[website/docs/user-guide/git-worktrees.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/git-worktrees.md) · [website/docs/user-guide/desktop.md](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/website/docs/user-guide/desktop.md)

읽은 범위: 작업 사본과 Desktop review/worktree UI 설명.

한계: Git 작업 사본을 보안 sandbox로 취급하지 않음.

### H-SEARCH

[tools/session_search_tool.py](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/tools/session_search_tool.py)

읽은 범위: 모듈 설명·1–140줄, _shape_message/_session_link/_title_match_result 주변(230–320줄), discovery/read/scroll 함수와 schema 선언을 검색해 대조. 검색 결과의 원문·잘림·계보와 숨김 source를 확인.

한계: 선택한 분기 정적 검토이며 DB 쿼리·권한·성능 전체 감사나 실행 시험 아님.

### H-CODE-CHECK

[tools/memory_tool.py](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/tools/memory_tool.py) · [tools/skills_tool.py](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/tools/skills_tool.py) · [agent/curator.py](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/agent/curator.py)

읽은 범위: memory pending/apply entry 결속과 skills의 도구 위치를 검색. curator 210–258줄에서 pin·cron 참조 보호와 never-used 유예·archive 분기를 읽음.

한계: 함수 전체·동시성·실제 LLM consolidation을 실행하지 않음.

## 다른 프로젝트 근거

### A-SEARCH

[docs/features.md](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/docs/features.md) · [lib/memory/read/RankFusion.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/RankFusion.js) · [lib/memory/read/BudgetSelector.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/BudgetSelector.js)

읽은 범위: features ledger의 검색·범위·trace 설명, RankFusion 앞부분과 BudgetSelector의 알고리즘 설명·상수·함수 앞부분. 기존 AnchorMind 검토의 검색/예산 절을 함께 읽음.

한계: 현재 원본에서 부분 확인. 전체 DB 실행계획·recall 정확성·모든 ranking 분기 미실험.

### A-SCOPE

[docs/features.md](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/docs/features.md) · [docs/architecture.md](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/docs/architecture.md)

읽은 범위: features ledger의 WorkspaceReadAuthz/SearchScope·scope 관련 행과 architecture 개요.

한계: 문서 확인. 실제 인증·전체 범위 집행 미감사.

### A-WRITE

[docs/features.md](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/docs/features.md) · [lib/tool-registry.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/tool-registry.js)

읽은 범위: 쓰기/중복/anchor 관련 ledger 및 tool registry 기능 표면.

한계: 문서·목록 확인. 모든 write path 실행 검증 없음.

### A-HISTORY

[docs/features.md](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/docs/features.md) · [docs/api-reference.md](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/docs/api-reference.md)

읽은 범위: history/case/link/conflict 도구 설명과 ledger. 기존 10월 4일 검토의 사건 이력·모순 절 재독.

한계: 현재 모든 history/NLI 코드를 재검토한 것은 아님.

### A-LIFECYCLE

[docs/features.md](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/docs/features.md)

읽은 범위: AutoReflect·MemoryConsolidator·feedback·decay·graph 및 실험 플래그 표.

한계: 정책 기본값은 판 변경 때 재확인. “성장”·정확성 개선은 제작자 주장이지 우리 측정이 아님.

### A-EVAL

[docs/benchmark.md](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/docs/benchmark.md) · [tests/fixtures/recall-eval-v2/README.md](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/tests/fixtures/recall-eval-v2/README.md)

읽은 범위: 평가 입구와 기존 조사에 연결된 recall fixture 설명.

한계: 벤치 재실행·품질 수치 전이 없음.

### A-OPS

[docs/features.md](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/docs/features.md) · [docs/admin-console-guide.md](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/docs/admin-console-guide.md)

읽은 범위: export/import·outbox ledger 및 관리 화면 개요.

한계: 관리 권한·운영 DB·backup/restore 전수 미검증.

### P-REVIEW

[README.md](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/README.md) · [docs/VERIFY-GOVERNANCE.md](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/docs/VERIFY-GOVERNANCE.md)

읽은 범위: 기능·검토 모드와 검토 경계 문서 도입/경계·판정 우선순위. 기존 검토의 처분/증명 한계와 함께 읽음.

한계: 이번에는 README/선택 설계의 문서 검토이며 새 엔진·훅·proof 전체 코드 감사/설치/모델 실행 없음. 설계 문서의 모든 항목이 현행 구현이라는 뜻이 아님.

### P-UI

[README.md](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/README.md)

읽은 범위: live strip·무결성 경고·설정/실제 모델·추론과 시각화 기능 절.

한계: 이번에는 README/선택 설계의 문서 검토이며 새 엔진·훅·proof 전체 코드 감사/설치/모델 실행 없음. 설계 문서의 모든 항목이 현행 구현이라는 뜻이 아님.

### P-SESSION

[README.md](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/README.md)

읽은 범위: 세션 고정·ask-start/wait·작업 deadline·CLI/doctor·읽기 전용 원칙.

한계: 이번에는 README/선택 설계의 문서 검토이며 새 엔진·훅·proof 전체 코드 감사/설치/모델 실행 없음. 설계 문서의 모든 항목이 현행 구현이라는 뜻이 아님.

### P-MEMORY

[docs/MEMORY-AUTHORITY-DESIGN.md](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/docs/MEMORY-AUTHORITY-DESIGN.md) · [docs/MAP-RETRIEVAL-DESIGN.md](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/docs/MAP-RETRIEVAL-DESIGN.md) · [docs/ROADMAP.md](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/docs/ROADMAP.md)

읽은 범위: 기존 9월 26일 ANALYSIS/ADOPTION/EVIDENCE에 기록된 MAP·기억 권위·승인/주입 구분을 재독. 현재 문서는 탐색 위치로 연결.

한계: 이번에는 README/선택 설계의 문서 검토이며 새 엔진·훅·proof 전체 코드 감사/설치/모델 실행 없음. 설계 문서의 모든 항목이 현행 구현이라는 뜻이 아님.

### W-RECORD

[README.md](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/README.md) · [casebook/core/worktrail.py](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/worktrail.py) · [LICENSE](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/LICENSE)

읽은 범위: README 전체·코어 1–130줄의 모델 없는 기록 책임·LICENSE, 기존 평가의 현재/근거/다음/배제 구조를 재독.

한계: root 라이선스 조건을 기록. UI·서버·인증 실행과 전체 코어 감사를 하지 않음.

### X-BEADS

[README.md](https://github.com/steveyegge/beads/blob/2f1e8be3ca1fe990727858ccd8e4a78461b39c7c/README.md)

읽은 범위: README의 개요·Dolt·기능·ready/claim·의존성·기억·초기 설치 설명.

한계: 실제 Dolt·동시 claim·hook 실행 없음. 과거의 “git에 파일만 저장하는 도구” 설명으로 현재 운영 비용을 추정하지 않음.

### X-BACKLOG

[README.md](https://github.com/MrLesk/Backlog.md/blob/69e7b15362337d6712783d9a685f6e4bb693fa9d/README.md)

읽은 범위: README의 명세/계획/코드 검토, 기능·milestone/dependency·local UI·검색.

한계: CLI·MCP·실제 board 조작 미시험.

### X-GASTOWN

[README.md](https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/README.md)

읽은 범위: Overview·역할/영속 상태·convoy·molecule·monitoring·refinery·escalation·scheduler 설명.

한계: 규모/성과 수치는 제작자 설명. 실제 다중 agent 실행·비용 미측정.

### T-BASE

[2026-09-23 tmux 근거](../tmux-2026-09-23/EVIDENCE.md) · [분석](../tmux-2026-09-23/ANALYSIS.md) · [적용안](../tmux-2026-09-23/ADOPTION_PLAN.md)

기존 조사 재독. tmux 3.7c 소스 commit `e476c1230b958df0cb12977517d24b3dc931375b`의 control mode·server/client·flow control·socket 경계에 대한 이전 기록을 사용했다. 이번 최신 tmux HEAD·실제 detach/attach·PTY를 새로 확인하지 않았다.

### X-EARLY

[Jev·Lite-Harness·Fusion 등 초기 조사](../../research-2026-09-22/README.md) · [Codex 연결](../../research-2026-09-22/codex-bridge.md) · [비용 평가](../../research-2026-09-22/measurement-and-rollout.md) · [v0.4 근거](../../architecture/v0.4/sources.json)

기존 조사 재독. 2026-09-21/22의 판단 모델·native 연결·ensemble/비용 비교를 후보로 보존했다. 해당 외부 프로젝트 최신판·모델 가용성·벤치를 이번에 새로 확인하지 않았다.

### X-DESIGN

[현재 island-ui 출처·업데이트 절차](../../../app/static/island-ui/README.md) · [현재 참고 지도](../../REFERENCE-MAP.md)

우리 저장소의 이미 복사된 부품 위치와 관리 절차를 확인했다. ai_unslop 최신 upstream을 다시 가져오거나 디자인 파일을 수정하지 않았다.

## 공식 웹 문서

2026-10-04에 아래 페이지를 직접 받아 본문을 읽었다. live 페이지는 변경될 수 있다. [조회 메타데이터](source-manifest.json)는 URL·redirect·응답 본문 hash와 조회 결과를 남긴다. hash는 당시 받은 응답을 식별할 뿐 페이지가 정확하다는 증명이 아니다. 동적 UI와 계정별 기능은 미확인이다.

### X-AMP

[amp 공식 문서](https://ampcode.com/news/neo)

압축 중심 재구축·handoff 제거·다른 thread 참조의 본문. 기능 폐지 이유까지 보존.

### X-CONDUCTOR

[conductor 공식 문서](https://www.conductor.build/docs)

Introduction 본문 전체: 작업별 workspace/branch/terminal/diff, review→PR→merge→archive.

### X-KIRO

[kiro 공식 문서](https://kiro.dev/docs/specs/)

Specs 개요: 요구·설계·작업, feature/bugfix/quick spec·병렬 작업 항목.

### X-CLINE

[cline 공식 문서](https://docs.cline.bot/best-practices/memory-bank)

Memory Bank 개요·파일 구조·현재 초점/진행·세션 재개. 문서 방법론임을 구분.

### X-CURSOR

[cursor 공식 문서](https://cursor.com/changelog/2-0)

2.0 changelog의 병렬 worktree/remote·review·voice·plan/build 모델 분리. 제품 최신 전체 기능 목록은 아님.

### X-DEVIN

[devin 공식 문서](https://cognition.com/blog/devin-can-now-manage-devins)

Managed Devins 소개의 coordinator/worker·세션별 링크·메시지/사용량/중단 기능. 성능 개선 주장 미검증.

### X-COPILOT

[copilot 공식 문서](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent)

Cloud agent 개요의 작업→PR·비동기 세션·외부 연결·계정/AI credits·제한 설명. 실제 계정 사용권 미확인.

### X-JULES

[jules 공식 문서](https://jules.google/docs/)

Getting started 전체: VM·계획 확인·repo/branch·완료/입력 알림.

## 우리 구현 대조

기준 main에서 `docs/FEATURES.md`, `docs/REFERENCE-MAP.md`, `NEXT-SESSION.md`, `app/memory.py`의 선택/고정 방식, `app/controller.py`의 작업·실행·역할·검토·취소 메서드, `app/server.py`의 API 경로, `app/store.py`의 원장, `app/static/role-board.js`의 입력/기억 미리보기·작업 표시를 읽거나 해당 심벌/경로를 검색했다. 역할판·상위 역할·교차검토·원장·보고서의 현재 책임과 후보 접점을 대조했다. 제품 전체 코드를 새로 감사하거나 사용자 PC 상태를 재측정한 것은 아니다.

## 이전 조사에 덧붙일 점

- Hermes HP-01–HP-10의 기존 계획은 당시 범위로 보존한다. 이번 목록은 화면·자료·자동화까지 넓힌 별도 조사이며 HP 항목의 일괄 구현 승인이 아니다.
- Hermes README의 “FTS5 session search with LLM summarization”과 선택한 현행 `session_search_tool.py`의 “No LLM calls”를 구분한다. 이번 H13/H14는 원문 반환 경로를 참고한다. 다른 요약/curator 기능까지 모델 호출이 없다고 확대하지 않는다.
- curator의 deterministic archival과 opt-in LLM consolidation은 비용이 다르다. micro-compaction도 실제 요약 호출과 cache 손실 가능성이 있다.
- WorkTrail은 이전 고정판과 같은 HEAD였다. AnchorMind와 codex-peek는 이전 조사 후 다른 HEAD였으므로, 옛 코드 감사 결과를 새 전체 코드의 검증으로 쓰지 않는다.
- Beads 최신 README는 Dolt 기반을 명시한다. 기존 여러 AI 도구 조사의 간단한 git 저장 설명만으로 도입 비용을 판단하지 않는다.
- 기존 “기억 수동 우선” 제안은 10월 4일 자동 기억 결정 전의 기록이다. 현재 기능은 `docs/FEATURES.md`, 이번 확장 후보는 이 목록을 따른다.

## 남겨 둔 확인

외부 제품 설치·upstream 전체 시험·모델 품질·소비량·구독 허용 경로·사용자 계정·Windows/WSL/브라우저·모바일 UX·복구/공격 시나리오·모든 의존성과 라이선스는 이번 범위 밖이다. 후보 하나를 고르면 그때 해당 판의 원본 코드와 조건을 다시 확인한다. 전 세계 모든 프로젝트를 조사했다거나 기록되지 않은 과거 대화까지 복원했다는 주장은 하지 않는다.
