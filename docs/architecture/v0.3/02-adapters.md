# 세 구독의 연결 경로와 하네스 선택

2026-09-22 공식 문서·소스 확인. **사용자의 실제 요금제/CLI 설치/로그인을 조사하거나 변경하지 않았다.** 아래는 지원 문서에 근거한 설계이며 계정별 사용 가능 여부는 첫 연결 때 확인한다. 근거 ID는 [sources.json](sources.json)에서 검색한다.

## 1. 구독 우선 연결표

| 현재 도구 | 우선 연결 | 구독/과금 확인 | 관측과 주의할 의미 |
|---|---|---|---|
| ChatGPT → Codex | 저장된 ChatGPT 로그인으로 native `codex exec`; 이후 공식 SDK 검토 | ChatGPT 로그인과 API 키 과금은 별도. preflight에서 실제 auth 경로 확인 | `--json`은 실행 JSONL, `--output-schema`는 최종 응답 제약. 부모 UI 대화가 새 worker에 자동 상속되지는 않음 |
| Claude → Claude Code | 구독 로그인으로 `claude -p`; SDK는 정책/버전 확인 후 선택 | `ANTHROPIC_API_KEY`가 있으면 구독 대신 API 과금이 우선한다. native 로그인 상태와 충돌 여부 확인 | `json`/`stream-json`과 schema 출력. 재개 시 `total_cost_usd`는 이전 대화까지 포함한 client estimate일 수 있음 |
| Antigravity → `agy` | 로그인된 native CLI의 headless `agy -p` | cached account 인증 사용. quota 소진 후 credits 사용은 `useG1Credits` 설정으로 제어 | JSON/NDJSON, schema, usage, 명시 `conversation_id` 재개. 권한 soft-denial에도 exit 0 가능 |

원문: [Codex 인증](https://learn.chatgpt.com/docs/auth) E01, [Codex 실행](https://learn.chatgpt.com/docs/non-interactive-mode) E02, [Claude 구독](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan) E04, [Claude 프로그램 실행](https://code.claude.com/docs/en/headless) E06, [Antigravity 설치/인증](https://www.antigravity.google/docs/cli/install/) E07, [headless](https://www.antigravity.google/docs/cli/headless/) E08, [credits](https://www.antigravity.google/docs/cli/credits/) E09.

Antigravity와 별도 제품인 Gemini CLI를 동일한 바이너리·세션·quota pool로 가정하지 않는다. 여기서는 사용자가 쓰는 Antigravity의 공식 `agy` 경로를 우선한다. 동일 provider라도 구독 접근 가능 모델과 API 접근 가능 모델이 같다는 가정은 두지 않는다.

## 2. 지금 특히 잘못 읽기 쉬운 정책

**Claude:** 공식 Agent SDK 구독 문서 상단은 2026-06-15 변경을 보류했고, 현재 SDK·`claude -p`·third-party app 사용이 기존 구독 한도에서 계속 차감된다고 명시한다. 아래의 별도 월간 credit 표는 이전 시행 계획을 보존한 내용이다. 그 표만 읽어 예산을 만들면 잘못된 설계가 된다. 이 문서는 향후 변경 가능성도 알리므로 adapter 구현·업그레이드 시 상단 업데이트를 다시 읽는다. [공식 정책 업데이트](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan), E05.

**Antigravity:** native CLI의 계정 인증과 Python SDK quickstart의 Gemini API key/Vertex 경로를 구별한다. SDK overview만으로 개인 구독을 재사용할 수 있다고 판단하지 않는다. CLI의 API key 모드도 `GEMINI_API_KEY` 하나만으로 바뀌는 것이 아니라 `modelProvider` 설정이 필요하다고 문서가 설명한다. provider마다 인증 우선순위가 다르므로 공통 `API_KEY` 탐지만으로 과금을 판단하지 않는다. [SDK overview](https://www.antigravity.google/docs/sdk/overview/), E07/E10.

**Codex:** ChatGPT 구독 로그인으로 쓰는 native CLI와 별도 API backend는 서로 다른 funding mode다. 구독 credential을 뽑아 임의의 호환 gateway에 넣는 구조를 필요 조건으로 만들지 않는다. headless 실행 지원은 현재 데스크톱 대화를 아무 프로세스에서나 공유할 수 있다는 뜻이 아니다. E01/E02.

현재 선호를 반영한 기본 정책은 `subscription_only`, `paid_api_fallback=false`, `extra_credit_fallback=false`다. 이는 제안이며 이 세션에서 계정 설정을 변경하지 않았다. 잔량·차감 단위를 모르면 `unknown`으로 기록하고 concurrency를 보수적으로 둔다. 무조건 추가 결제가 발생하지 않는다고 주장하려면 실제 계정의 overage 설정까지 확인해야 한다.

## 3. Codex를 계속 입구로 쓰는 방법

```text
현재 Codex 세션
    → 외부 MCP 서버인 우리 bridge
    → task controller
    → Claude Code / agy / 필요시 별도 Codex worker
    → artifact + 검증 결과
    → 현재 Codex에 짧은 결과 반환
```

부모 Codex가 직접 끝내는 편이 싼 작업은 위임하지 않는다. 별도 worker는 분리된 책임이나 문맥 격리의 이득이 있을 때만 띄운다. bridge API는 앞선 [상세 설계](../../research-2026-09-22/codex-bridge.md)의 `run_task`, `get_run`, `read_artifact`, `cancel_run`을 출발점으로 검토한다. `get_run`의 cursor/변경분 조회로 전체 로그를 매번 다시 받지 않게 한다. status polling마다 LLM을 호출하지 않는다.

공식 `codex mcp-server`는 제거됐다. **우리 서버를 Codex가 MCP client로 호출**하는 방향은 계속 지원된다. App Server는 native 대화·인증·승인 이벤트가 필요한 자체 UI의 별도 선택지이며 MCP drop-in 대체가 아니다. 현재 문서의 experimental 표기를 고려해 첫 slice는 CLI 실행으로 시작한다. [공식 제거 안내](https://learn.chatgpt.com/docs/mcp-server), [외부 MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), E03.

bridge는 부모의 모든 native 도구·token·캐시를 자동 계측하지 못한다. 총비용 비교에는 부모 측 export/계측 또는 end-to-end runner가 별도로 필요하다. 확인되지 않은 부모 사용량을 0으로 집계하지 않는다.

## 4. 공통 adapter의 최소 계약

| 함수/데이터 | 의미 |
|---|---|
| `describe_capabilities()` | install/version, headless, schema, tool scope, resume, cancel, usage granularity 지원 상태 |
| `preflight(profile, task)` | 인증 **방식**·funding·workspace·필수 기능 확인; 비밀 값은 반환하지 않음 |
| `start(task, workspace, policy)` | idempotency 확인 뒤 명시 cwd/인자/env allowlist로 실행; run ID 반환 |
| `events(run, cursor)` | 원본 이벤트 참조와 normalized event. stdout 결과와 stderr 진단 구분 |
| `resume(native_session_id, delta_packet)` | 명시 ID에만 재개. 전역 `--last`/`--continue`를 공유 queue에서 사용하지 않음 |
| `cancel(run)` | 요청 수신과 실제 종료 확인을 구분 |
| `collect(run)` | artifact, session ID, usage scope, observation time, 오류/거절 정보 수집 |

flags는 각 CLI에서 확인한 지원 범위에 맞춰 번역한다. 문자열 shell 조립 대신 argument array를 사용하고 prompt/schema를 별도 stdin/파일로 전달한다. 설정은 child-process 단위로 제한하며 부모 전체 `process.env`를 변경해 다른 provider의 인증을 바꾸지 않는다. 사용자 전역 설정을 덮어쓰는 대신 task profile을 적용하고 effective configuration을 기록한다.

정규화할 이벤트 제안: `started`, `progress`, `artifact`, `usage_observed`, `permission_denied`, `rate_limited`, `completed`, `failed`, `cancel_requested`, `cancelled`, `unknown`. provider raw event를 보존해 새 버전에서 의미가 바뀌었을 때 추적한다. `usage_observed`에는 `scope=turn_delta/session_cumulative/run_total`, `measurement=observed/estimated/unknown`, `includes_children`를 둔다.

## 5. 하네스 선택: 도입과 참고를 구분

| 후보 | 유용한 부분 | 현재 결정 |
|---|---|---|
| Native Codex / Claude Code / Antigravity | 이미 쓰는 도구·파일 실행·인증·context loop | 우선 연결. 세 제품을 동일 내부 API로 강제 변환하지 않음 |
| Symphony | task 상태·workspace·retry·reconciliation·usage 경계 | 명세 참고. 이 프로젝트의 subscription-aware controller와 맞는 부분만 재사용 검토 |
| Lite-Harness | 여러 native 하네스의 공통 호출/stream interface | adapter 설계 참고; 현재 기본 의존성 채택은 보류 |
| Aider architect/editor | 계획과 편집의 분리 방식 | 역할 배정 실험 참고. 구독 CLI 통합의 기본 gateway로 채택하지 않음 |
| mini-swe-agent | 작은 고정 하네스에서 모델/context 변수를 비교 | 기존 v0.2의 별도 경제성 연구 경로 유지; 사용자 native 품질 비교와 분리 |
| LangGraph 등 durable graph | 복잡한 graph·checkpoint 관리 | 재시작/장기 분기 요구가 실제로 생길 때 검토. 첫 worker 실행에 필수 아님 |
| Antigravity Teamwork preview | milestone·격리·독립 검증·팀 내부 역할 | native 팀 하나를 별도 실험군으로 비교. 외부 팀을 그 위에 자동 중첩하지 않음 |

mini-swe-agent/LangGraph의 상세 출처와 기존 비교는 [9월 22일 조사](../../research-2026-09-22/README.md), [v0.2 blueprint](../v0.2/02-concrete-blueprint.md)에 있다. 이름을 나열한 것이 설치 결정은 아니다.

### Lite-Harness 실제 코드에서 확인한 경계

commit `dd99cfdfc68dbb6b3f7f986d54efd42572373a6c`의 [Codex adapter](https://github.com/LiteLLM-Labs/lite-harness/blob/dd99cfdfc68dbb6b3f7f986d54efd42572373a6c/src/sdk/server/providers/codex/index.mjs)를 읽었다. `runTurn`에서 매번 `startThread`를 호출하고 `setPermissionMode()`는 비어 있으며, gateway 경로에서 process 전역 API key 환경을 변경한다. [같은 commit README](https://github.com/LiteLLM-Labs/lite-harness/blob/dd99cfdfc68dbb6b3f7f986d54efd42572373a6c/README.md)는 npm/PyPI 미출시 preview라고 명시한다.

따라서 **공통 호출 format이 있다는 것과 구독 인증·session affinity·권한이 완전히 보존된다는 것은 별개**다. 이는 해당 commit 정적 inspection의 결론이며 실행 결함을 재현했다는 뜻은 아니다. 원리는 참고하되 D03 conformance를 통과하기 전 핵심 의존성으로 넣지 않는다. E22.

### Symphony를 그대로 전부 가져오지 않는 이유

commit `be10a1b79df723d6d7612b5651c8522704dafb2e`의 [SPEC](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/SPEC.md)은 workspace·상태·재시도·usage 소유권을 구체적으로 설명한다. [README](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/README.md)는 trusted-environment engineering preview다. 운영 구조는 적합하지만 참고 구현 전체가 현재 세 구독의 adapter·funding·Windows 경계를 해결해 주지는 않는다. 외부 controller를 두 개 겹치지 않고 하나만 상태를 소유하도록 한다. E23.

## 6. adapter 채택 전에 확인할 항목

1. 설치 버전과 해당 버전 `--help`, 로그인 **방식**, 실제 model availability를 기록한다. 연결하지 않은 상태를 configured로 표시하지 않는다.
2. 최소 read-only 작업에서 stdout/stderr/schema/session ID/usage를 수집한다. 의미 없는 schema 재시도에도 사용량이 든다는 점을 기록한다.
3. 격리 workspace 수정·검증을 실행하고 path escape 및 권한 거절을 확인한다. headless 모드의 실제 기본 권한을 제품별로 검증한다.
4. 명시 세션 재개에서 usage가 delta인지 누계인지, 이전 workspace와 연결되는지 확인한다.
5. timeout·사용자 취소·rate limit·프로세스 중단 후 상태를 대조한다. 테스트는 recorded event fixture와 mock으로 먼저 하고 실제 quota 오류를 일부러 대량 호출하여 만들지 않는다.
6. 새 provider를 추가해도 task/verification contract가 바뀌지 않아야 한다. 지원하지 않는 기능은 `unsupported`로 표시한다.

이 목록은 향후 구현의 완료 조건이다. 이번 문서 작업에서 실행했다고 주장하지 않는다.
