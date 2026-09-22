# MCP·기존 앱·Ledger UI 종합 검토

기준일 **2026-09-23 (Asia/Seoul)**. 시작 commit `c109840890bd72cbe5135f14c4d90c54c9039f0f`.
작업 브랜치 `review/mcp-ui-runtime-20260923`. 원문과 확인 범위는 [SOURCES](SOURCES.md), 재현과 한계는 [VALIDATION](VALIDATION.md).

## 1. 결론

**현재 방향은 유지하되, 도구 수를 늘리기보다 신뢰 경계를 먼저 구현한다.** 여러 앱의 좋은 부분을 결합한다는 사용자 결정을 유지한다. Python 제어 코어·native 구독 실행·상급 모델의 독립 추론과 교차검토·근거 원장·Ledger 셸은 서로 양립한다. Jev 같은 저비용 라우터는 선택 부품이지 검증자나 승인자가 아니다.

가장 큰 문제는 화면의 미감이 아니라 **기록을 검사했다는 사실이 실제 근거를 검증했다는 뜻으로 확장되는 것**이다. 기존 checker는 의도적으로 합성 기록만 받으며 운영 보안이나 사실 판정을 하지 않는다. 따라서 runtime/근거/표시의 경계를 연결해야 한다. 이것은 기존 v0.4를 폐기할 이유가 아니라 다음 구현 우선순위다.

이번 변경은 작은 오프라인 경계 실험, 대비 감사, 미발행 비교 시안까지다. 실제 adapter·MCP 서버·DB 복구·provider 호출은 구현 또는 검증했다고 주장하지 않는다. v0.2 계약과 기존 발행 디자인은 변경하지 않았다.

## 2. 우선 보완할 발견

| 우선 | 발견과 근거 | 처리 |
|---|---|---|
| P0 | `check_frontier_protocol.validate()`는 입력된 disposition을 검사할 뿐 계산하지 않는다. `log_ref`는 비어 있지 않은 문자열이어도 된다. 원본 코드의 모듈 설명도 합성 검사라고 명시한다 | 디자인 설명의 과장을 여기서 정정. 운영 verifier와 기존 checker를 구분 |
| P0 | URL과 특정 위치를 회수한 것은 그 문장이 주장을 뒷받침한다는 의미 검증이 아니다 | retrieval/관련성/뒷받침/반대 근거를 분리. 조회 성공만으로 supported 승격 금지 |
| P0 | 모델이 `record_check(status=passed)`를 임의로 호출할 수 있으면 자기 보고를 도구 결과로 세탁할 수 있다 | 결과 기록은 trusted runner 내부 권한. 모델에는 검사 요청만 노출하는 안 제시 |
| P0 | UI 숨김, tool readOnlyHint, Git worktree는 각각 OS 접근 통제를 대신하지 않는다 | agent별 실제 권한·읽기 범위 검증. 봉인 API는 allowlist 응답. peer와 operator의 관측 범위 분리 |
| P1 | herdr의 원 프로세스는 기기/서버 재시작을 넘어서 생존하지 않는다. 배치 복원과 native resume는 별개다(R12–R13) | 연결 단절/종료 확인/새 시도를 분리하는 상태 실험 구현 |
| P1 | Codex 한도 조회 경로가 공식 App Server 문서에 있다(R08) | 미확인 → **문서 경로 확인, 사용자 기기 미검증**으로 정정. quota 투영 실험 추가 |
| P1 | 원래 팔레트의 일반 글자 대비 66쌍 중 5쌍이 4.5:1 미만 | 원본 보존, 검사기·결과 파일·시안의 별도 수정 후보 제공 |
| P2 | 결정 우선 첫 화면이 최선이라는 사용자 실험은 아직 없다 | 두 배치를 같은 fixture로 비교하는 시안. Q4/Q8 미확정 유지 |

**검사 대상 내부 소스:** NEXT-SESSION, AGENTS, v0.4 HANDOFF, `tools/check_frontier_protocol.py`, design/project의 브랜드 문서·tokens·DecisionCard/BlindBarrier preview·BudgetMeter 설명, CI와 연구 무결성 테스트. 전 저장소의 모든 코드·논문·외부 앱 구현을 전수 감사한 것은 아니다.

## 3. 필요한 MCP: 개발 도구와 앱 기능을 분리한다

MCP는 도구 연결 경계다. agent 실행 제어, 인가, 예산 집행, 주장의 참/거짓 판정을 자동 제공하는 계층이 아니다. 공식 tools 사양은 structuredContent, outputSchema, isError 등을 구분하고 annotations를 무조건 신뢰하지 말라고 명시한다(R01–R02). 한도·토큰 효과는 클라이언트와 작업에 따라 측정해야 한다. JSON이나 지연 로딩을 썼다는 이유만으로 절감률을 가정하지 않는다.

| 후보 | 채택 위치와 우선순위 | 최소 범위 / 제외할 것 |
|---|---|---|
| **GitHub 공식 MCP** (R03) | 개발자 도우미 P0. 현재 대화에서는 기존 GitHub connector 사용 | 저장소·diff·PR·CI 읽기부터. `--read-only`와 최소 toolsets/tools. 실제 writer만 별도 쓰기 경로. 설치만으로 사용자 승인 대체 금지 |
| **Playwright** (R04) | UI 재현 테스트 P0, MCP 대화형 디버깅 P1 | 회귀 검사는 deterministic script/CLI 우선. MCP는 문제 재현에 선택 사용. 별도 브라우저 프로필, 실제 계정 쿠키 없음. README도 CLI+skills와 MCP의 효율 차이를 설명 |
| **프로젝트 verifier MCP** (R01–R02) | 앱 runtime P0 설계, native 파일럿 뒤에 얇게 노출 | 먼저 신뢰된 Python runner 함수와 증거 영수증을 만든다. MCP 자체가 검증 보증이라고 설명하지 않음 |
| **Context7** (R05) | 개발 시 라이브러리 문서 검색 P1, 필요할 때만 | 라이브러리 ID·버전 고정. 원문/locator를 원장에 남김. 검색 결과가 자동으로 검증된 근거가 되지 않음 |
| **MCP Inspector** (R06) | 개발/호환성 테스트 P0 | tool discovery·입출력·오류 fixture 점검. 최종 사용자 앱에 상시 번들할 이유는 아직 없음. 설치 시 버전/Node 요구 확인 |
| **Chrome DevTools MCP** (R07) | 성능·네트워크 문제의 선택 진단 P2 | Playwright와 기능 중복을 먼저 확인. 브라우저 데이터 노출 및 기본 telemetry/CrUX 동작 검토. 관측 필요 없는 평시에는 끔 |

범용 filesystem·shell·공유 memory 서버를 전체 참여자에게 기본 연결하지 않는다. 같은 저장소를 읽는 것과 다른 참여자의 초안·native 기록·인증정보까지 읽을 수 있는 것은 다르다. 개발자용 GitHub MCP를 제품 사용자 필수 설치물로 만들 이유도 아직 없다.

### verifier의 구체적인 첫 계약안 — 아직 서버가 아니다

| 제안 도구 | 모델이 지정할 수 있는 입력 | runner가 정하는 결과 |
|---|---|---|
| `request_test` | 승인된 `test_id`, `artifact_id`, `request_id` | 등록된 argv·cwd·입력 digest·검사 버전·timeout·관측 결과 |
| `resolve_source` | 승인된 source ID와 locator | 회수한 원문·content digest·시각·회수 성공/실패. 의미상 지지는 별도 |
| `get_check` | 허용된 check ID | 해당 역할이 읽을 수 있는 영수증과 검사 범위 |
| `record_check` | **모델에게 노출하지 않음** | trusted runner 내부의 append-only 동작 |

검사 요청에는 임의 shell 문자열·임의 경로·임의 URL을 바로 실행하도록 주지 않는다. URL 회수는 인증정보 전달 금지, 사설망/메타데이터 주소와 redirect 재검증, 크기/시간 제한을 설계한다. 코드 테스트 역시 실행 가능한 코드이므로 읽기 전용 프롬프트만으로 안전해지지 않는다.

영수증의 최소 후보는 `run_id`, `attempt_id`, `request_id`, `test_id`, `test_version`, `input_digest`, `output_digest`, `observed_status`, `started_at`, `finished_at`, `issuer`다. **해시는 바이트 결속이지 발행자 인증이 아니다.** 서명 또는 신뢰된 로컬 저장소 인가와 별도로 다룬다. 요청 재전송은 idempotency 키로 중복 실행을 막고, 다른 실행의 영수증 재사용은 거절해야 한다. 이 부분은 후속 ticket이며 이번 순수 함수 테스트가 이를 보증하지 않는다.

## 4. 기존 앱에서 추출할 것과 가져오지 않을 것

| 사례 | 확인한 패턴 | 우리 프로젝트에 가져올 부분 | 가져오지 않을 가정 |
|---|---|---|---|
| **Orca** (R10) | 작업별 worktree·병렬 agent·inline diff review | 구현 단계의 `task → attempt → worktree → diff → review` 연결. 논의 후 한 writer 기본값은 유지 | worktree가 sandbox나 독립 추론을 보증한다는 해석, 앱 전체를 기반으로 선택 |
| **Paseo** (R11) | daemon과 desktop/web/mobile/CLI client 분리 | UI 종료와 실행 종료를 분리. 상태 재조회·재연결 경계, 동일 session의 여러 view | 첫 파일럿부터 원격 중계/모바일 제어/계정 인가까지 모두 구현 |
| **herdr** (R12–R13) | detach 유지·배치 복원·native resume를 별도 취급 | 복구 능력을 capability로 표시. 화면 복원과 원 실행 생존을 분리 | 재부팅 후 자동으로 원 process가 살아 있다는 표시. resume한 과거 문맥을 fresh blind draft로 인정 |
| **OpenCode** (R14) | HTTP/OpenAPI와 SSE, TUI도 같은 서버의 client | Python core에 UI와 도구가 공통으로 쓰는 command/event 경계를 두는 구조 | `serve`가 무조건 기존 프로세스에 붙는다는 가정, localhost라는 이유만으로 무인가 제어 허용 |
| **AionUi** (R15) | 설치 CLI 자동 탐지·통합 화면, 내장 API agent 경로 | 연결 화면을 발견됨/설치됨/로그인됨/권한 확인됨/실행 검증됨으로 나누기 | API key를 넣는 온보딩을 구독 전용 기본값에 섞기. 로컬 저장을 무조건 외부 전송 없음으로 해석 |
| **Vibe Kanban** (R16) | 작업 → 별도 workspace → diff comment → PR 흐름 | 구현·검토 동선을 짧게 하는 참고 | 공식 README에 sunsetting 안내가 있으므로 새 핵심 의존성으로 채택 |
| **LangGraph** (R17) | thread별 checkpoint와 cross-thread store 분리, RAM saver와 영속 saver 구분 | 실행 상태와 공유 지식을 분리하고 복구 요구를 먼저 명시 | InMemorySaver가 재부팅 복구를 제공한다는 가정, 프레임워크를 붙이면 부작용 재실행이 자동 해결된다는 기대 |
| **Claude Code Agent Teams** (R18) | 의존 task·역할·메시지·완료 hook, 명시된 권한 상속/제약 | 작업의 소유자와 완료 조건, 인간 개입 위치를 명료화 | 실험 기능을 모든 CLI의 headless 협업에 일반화. 자동 plan approval을 사람의 검토 승인으로 표시 |

이 표는 **패턴 채택 제안**이다. 외부 저장소 코드를 복사하거나 앱을 설치한 결과가 아니다. 실제 코드를 재사용할 때는 해당 버전·파일별 라이선스, transitive 의존성, 보안 정책, telemetry, 유지보수 상태를 별도 확인한다. 별 수·광고 문구·지원 모델 수를 정확도나 신뢰성의 증거로 사용하지 않는다.

## 5. 제어 코어와 adapter 경계 보강안

아래는 권장 구조다. 기존 ACP 우선 구상을 일방적으로 폐기하지 않는다. 다만 **공통 계약**과 **모든 기능을 동일 wire protocol로 강제**하는 것은 분리할 것을 제안한다(R08–R09, R14).

```text
Ledger UI ── command + event view ── Python controller
                                      ├─ 단계/예산/정족수/권한/시도 ID
                                      ├─ provider adapter
                                      │    ├─ ACP (실제 지원 기능 확인)
                                      │    ├─ native transport / 보조 기능 경로
                                      │    └─ 명시적 exec fallback
                                      ├─ trusted verifier runner (선택 MCP facade)
                                      └─ event journal + evidence store (후속 구현)
```

Codex는 App Server의 `account/rateLimits/read`와 `account/rateLimits/updated`가 문서화되어 있다. `rateLimitsByLimitId`와 legacy `rateLimits`를 이중 합산하지 않으며 primary/secondary 창·관측 시각·reset 시각을 분리한다. **문서 예시의 퍼센트·창 길이는 사용자 실제 값이 아니다.** 실제 로그인과 설치 버전이 해당 기능을 지원하는지는 V04-01에서 검증한다. 새 `quota_projection()`은 이 응답의 일부를 합성 입력으로 다루며 네트워크 호출은 하지 않는다(R08).

최소 공통 capability는 `preflight/start/events/collect/cancel/resume`다. provider 고유 한도/승인 기능은 없어졌다고 처리하지 말고 지원·미지원·미확인을 구분한다. `agy`와 Gemini CLI를 섞지 않는다. resume는 같은 세션 연속성이고 새 독립 초안은 fresh context가 필요하다. 공유 memory·검색 cache·프로젝트 기록의 오염 가능성도 따로 기록한다.

운영으로 갈 때는 `run → attempt → native_session`을 별도로 저장한다. controller 재시작 후 attempt의 상태를 먼저 reconcile하고, 상태가 UNKNOWN인 상태에서 자동 재시도·자동 예산 반환을 하지 않는다. 이번 reducer의 epoch/순번 검사는 이 계약의 작은 부분이며 영속 journal·프로세스 인증·OS kill이 구현됐다는 뜻이 아니다.

## 6. Ledger UI 평가

### 유지할 방향

주장·근거를 채팅 말풍선과 분리한 점, unresolved를 숨기지 않는 점, unknown을 0과 구분한 점, “이 결정을 뒤집을 조건”을 앞에 둔 점이 이 프로젝트의 목적과 잘 맞는다. 선 중심 밀도·작은 반경·모노 식별자도 작업 도구로서 일관적이다. 이는 디자인 판단이지 사용성 우월성의 실험 결과는 아니다.

### 바꿀 부분

1. **상태의 근거를 보이기:** `형식 검사 통과 / 실행 관측 / 의미 검토 / 실제 기기 미검증`을 분리한다. supported 옆에는 어떤 검사·어떤 입력 범위인지 접근할 수 있어야 한다. 합의 수나 exit 0으로 승격하지 않는다.
2. **미확정 첫 화면:** 결정 우선 A와 대조표 우선 B를 동일 내용으로 비교한다. 중요한 반례 찾기, 다음 검사 선택, 과신, 걸린 시간, 잘못된 실행 승인을 측정한다. 적은 사용자 탐색은 문제 발견용이지 통계적 우월성 증명이 아니다. 배치 순서도 교차 배정한다.
3. **운영의 빈 상태:** 미연결, 권한 거절, 정족수 부족, 예산 없음, 취소 대기/UNKNOWN, stale 관측에 각각 필요한 다음 행동을 둔다. 정상 완료 화면만 만들지 않는다.
4. **접근성/가독성:** 원본의 ink-200 최소 12px 규칙과 11/11.5px 사용이 불일치한다. 일반 텍스트 대비도 아래 5쌍을 해결해야 한다. 이 감사가 모든 실제 DOM의 WCAG 불합격을 뜻하지는 않지만 해당 조합을 작은 글자에 쓰면 안 된다(R19).

| 테마 | 글자 / 배경 | 대비 |
|---|---|---:|
| light | unknown / surface-000 | 3.5973 |
| light | unknown / surface-100 | 3.7995 |
| light | unknown / surface-200 | 3.2554 |
| light | ink-200 / surface-200 | 4.0805 |
| dark | ink-200 / surface-200 | 4.3595 |

[계산 기록](contrast-audit.json)과 `tools/audit_design_contrast.py`를 추가했다. 원본 token의 11개 전경 × 3개 배경 × 2테마를 대상으로 한 66쌍 검사다. alpha 합성·실제 CSS 사용처·accent-soft·비텍스트 컨트롤 대비는 범위 밖이다. 원본 design은 발행본 동기화 규칙 때문에 보존했다. 시안에서만 muted 후보를 조정했다.

### 동작하는 비교 시안

[preview.html](preview.html)은 외부 dependency가 없는 별도 미발행 파일이다. 결정/대조표 순서, light/dark, 조건부 검토/봉인/종료 불명/미연결 상태를 전환한다. 원본 디자인 artifact의 새 버전이나 완성 앱은 아니다. 실모델 데이터가 들어오는 백엔드와 연결하지 않았고, Python 투영과 HTML fixture도 아직 별개다.

48개 조합의 가로 넘침·page error·외부 request smoke와 키보드/DOM 순서 검사를 실행했다. 자동 smoke와 스크린샷 확인은 전체 접근성 인증, 실제 Windows 렌더링, 사용성 실험을 대체하지 않는다.

## 7. 구현 결과와 다음 작업

| 항목 | 지금 완료 | 다음 완료 조건 |
|---|---|---|
| `tools/review_boundary.py` | 상태 순서/epoch, 동일 이벤트 재생, UNKNOWN 예산, 봉인 allowlist, quota 관측 투영 | native 이벤트 fixture, 실제 인가와 프로세스 관측, persistent journal에 연결 |
| 대비 감사 | 공식 수식 구현·6개 테스트·기존 팔레트 위험 5쌍 기록 | source+발행본 동시 수정, 실제 CSS/스크린리더·확대 검토 |
| UI 비교 | 4상태 × 2배치 × 2테마 × 3폭 smoke | controller 데이터 경계 연결, Q8 사용자 탐색 |
| MCP/앱 검토 | 최소 도구 구성과 채택/제외 근거 | 실제 버전 고정, host에서 권한·latency·문맥 비용 측정 |

**다음 순서:** V04-01 실제 운용 PC 인벤토리 → V04-03 두 native read-only 독립 응답 → 고정 test ID의 trusted verifier → UI 연결/복구 테스트 → 세 모델·제한 교차검토. shell framework 선택이나 원격/모바일 확장은 이 경로를 막지 않는 선에서 진행한다. 별도 추출·계획·재검토를 추가하면 총 호출 예산에 포함하고, 고급 합성이 필요하면 상급 모델을 명시적으로 배정한다.

기존 handoff는 루트의 날짜 붙은 파일로 **동일 Git blob 그대로 보존**하고, NEXT-SESSION에는 이번 정정과 다음 실행 순서를 우선 표시한다. 최종 commit·전체 CI 결과는 PR과 VALIDATION을 기준으로 확인한다.
