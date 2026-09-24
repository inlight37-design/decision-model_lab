# PR #38·#39 검토·병합과 다음 작업 구체화 — 2026-09-24

claude 세션이 사용자 PC에서 검토하고 병합했다. 사용자는 codex 세션의 PR #39 보고를 전달하며 “검토하고 병합하고 정리해서 다음에 뭘하면좋을지 더 구체적으로 확인해서 문서화하자 오류있으면 고치고”라고 요청했다.

## 작성·접근 범위

- Claude 데스크톱 앱(Code 탭)의 Windows 세션. 기기는 기존 기록의 `aux-pc`(같은 hostname), WSL은 `aux-pc-wsl`(Ubuntu-24.04, Python 3.12.3, bubblewrap 0.9.0, jsonschema 있음). Windows Python은 3.12.6이다. Node는 이 PC에 없다 — 화면 함수의 Node 시험은 로컬에서 건너뛰었고 CI에서 돈다.
- GitHub은 `gh`로 PR·Actions run·job 로그를 읽었다. 병합은 `gh pr merge`로 했다.
- **모델 호출 0회.** 실제 CLI 실행, 인증 폴더 연결, 서버 기동이 없다. 공식 문서는 in-app 브라우저로 직접 읽었다.
- WSL에서는 저장소 worktree를 `/mnt/c` 경로로 열어 시험했다. worktree의 `.git` 파일이 Windows 경로를 가리켜 WSL의 git은 이 worktree를 읽지 못한다(`fatal: not a git repository`) — 시험에는 영향이 없다.

## 1. 대상과 CI

| PR | head | CI | 비고 |
|---|---|---|---|
| [#38](https://github.com/inlight37-design/decision-model_lab/pull/38) `chatgpt/cli-unblock-20260924`(초안) | `b5014de1b5cfeebbf42667f8f4582c44bdad946a` | 이 head의 run 35996331140·35996337744·35997709906 모두 Linux 두 job 성공, `windows-checks` 실패(본문이 스스로 병합 금지라고 적음) | #39의 조상이다. #39 병합으로 main에 들어갔고 GitHub이 병합됨으로 표시했다 |
| [#39](https://github.com/inlight37-design/decision-model_lab/pull/39) `codex/windows-live-completion-20260924` | `948f5a3758146027af7f47989a2e5950a6faefb1` | push run 36001671469, pull_request run 36001678089 모두 성공 | job `checks (3.12)`·`checks (3.13)`(`DML_REQUIRE_BWRAP: 1`)·`windows-checks`. job 로그의 checkout이 정확히 `948f5a3`이다 |

- push job 로그: Linux 두 job `Ran 453 tests … OK (skipped=1)`, Windows job `Ran 453 tests … OK (skipped=44)`.
- 검토 시작 main `16646b34a508f4fbe4fbbd1e00758eb8223a2d65`가 #39 head의 조상이다. 그래서 병합 커밋의 트리는 검사한 head의 트리와 같다.
- 병합 뒤 main `40b2e67c65c07321bb9117045610dc6b600bf5cc`의 push run 36004205796도 세 job 모두 성공했다.

## 2. 로컬 검사(PR #39 head)

- Windows: `python -m unittest discover -s tests` — `Ran 453 tests … OK (skipped=45)`. 건너뜀은 Linux 전용과 Node 없음. 검증 도구(인코딩·설계 토큰·frontier·v0.1·v0.2·원장·inventory dry-run)는 모두 통과.
- WSL: `DML_REQUIRE_BWRAP=1` 전체 — `Ran 453 tests … OK (skipped=2)`. 건너뜀은 Windows 전용 하나와 Node 없음 하나.

## 3. 코드 검토에서 확인한 것

- **Claude 출력.** 참여자가 `--output-format stream-json --verbose`로 바뀌었다. `core.adapters.claude_stream`은 init 하나와 result 하나를 요구하고, result 뒤의 사건·중복 init·깨진 줄을 거절한다. `interpret`는 init의 도구 목록이 계획의 `--tools`와 **순서까지** 같고, `dontAsk`, MCP 없음, 실제 사용한 도구가 허용 목록 안일 때만 해석을 이어 간다. `--tools`는 Claude 명령에 항상 있으므로 실행 뒤 `argv.index("--tools")`가 실패할 경로는 없다.
- **예산.** 스키마 6 `live_budget`이 첫 전체·provider별 상한을 고정하고, 구형 원장은 예약 사건의 같은 cap으로 복원하며 모순이면 거절한다. `pump`는 같은 거래 안에서 전체·provider 상한을 검사하고 예약한다(Store의 잠금은 `RLock`이라 거래 안 재조회가 막히지 않는다). 시작 전 거절은 실행 수에서 빠지고 예약은 남는다.
- **계정 조회.** `GET /api/account-quota`는 캐시만 읽고, `POST …/refresh`만 격리 안의 메타데이터 프로세스를 띄운다. 동시 갱신은 하나만 돌고 60초 간격이다. 120초 초과·초기화 시각 경과·조회 실패는 과거 관측값으로 보인다. 허용 메서드는 `initialize`·`initialized`·`account/read`(`refreshToken: false`)·`account/rateLimits/read`뿐이고, 계정 객체는 받자마자 버린다. `installed_version`은 프로세스를 띄우지 않고 실행 파일 경로에서 판을 읽는다. 원장 폴더는 격리의 `never`다.
- **설정.** `--live-config`는 알 수 없는 칸·중복 provider·불리언 상한·빈 모델 이름을 거절하고, 두 provider의 준비 조회가 모두 통과해야 서버를 띄운다.
- **기록 파일.** 새 JSON·README에서 이메일·조직 ID·토큰·JWT·개인 홈 경로·UUID 모양을 찾았고 없었다.
- **인용.** 코드의 `developers.openai.com/codex/app-server`는 기록의 `learn.chatgpt.com/docs/app-server`로 308 이동하는 같은 문서다. 그 본문에 `account/read`(`refreshToken: false`), `account/rateLimits/read`, `rateLimitsByLimitId`, `usedPercent`, `windowDurationMins`, `resetsAt`가 있다. WebFetch 요약은 문서를 중간에서 잘라 “없음”이라고 답했다 — 없다는 판단은 전체 본문(브라우저)으로 확인한다.

## 4. 변이 시험

WSL `DML_REQUIRE_BWRAP=1` 전체 시험을 각 변이마다 돌렸다. 매번 원래 바이트로 되돌렸고 마지막 재실행은 `OK (skipped=2)`, 작업 트리는 깨끗했다.

| 변이 | 결과 | 잡은 시험(일부) |
|---|---|---|
| M1 Claude 도구·권한 표면 검사 끔 | 실패 2 | `test_changed_surface_or_unoffered_tool_cannot_be_accepted` 외 |
| M2 result 뒤 사건 허용 | 실패 2 | `test_incomplete_duplicate_and_trailing_streams_are_rejected` |
| M3 provider 상한 무시 | 실패 1 | `test_provider_limits_cannot_borrow_or_change_on_restart` |
| M4 재시작 때 상한 변경 허용 | 실패 3 | `test_first_cap_is_fixed_before_any_call_and_recovers_when_omitted` 외 |
| M5 시작 전 실패를 실행으로 셈 | 실패 4 | `test_prestart_failure_keeps_reservation_but_not_execution_count` 외 |
| M6 조회 실패 뒤에도 옛 값이 최신 | **통과(잡히지 않음)** | 없음 — N2 |
| M7 60초 간격 없앰 | 실패 1 | `test_reads_never_query_and_repeat_refreshes_are_coalesced` |
| M8 GET이 조회를 시작 | 실패 1 | `test_http_requires_auth_and_read_has_no_refresh_side_effect` |
| M9 금지 파일 경로 대조 없앰 | 실패 1 | `test_permission_evidence_requires_the_exact_forbidden_fixture` |
| M10 preflight가 금지 파일 거절을 안 봄 | 실패 1 | `test_permission_requires_active_denial_of_the_exact_fixture_in_the_same_plan` |
| M11 계정 조회가 에이전트 활동 알림을 허용 | **통과(잡히지 않음)** | 없음 — N3 |
| M12 ChatGPT가 아닌 로그인 허용 | 실패 1 | `test_api_login_is_not_reused_and_no_fallback_or_quota_call_occurs` |
| M13 `permission_denials: null`을 증거로 채움 | 실패 1 | `test_permission_evidence_requires_the_exact_forbidden_fixture` |

## 5. 발견과 처리

| # | 발견 | 근거 | 처리 |
|---|---|---|---|
| N1 | **영문 Windows(CP1252 출력)에서 검증 도구 넷이 실패한다.** `validate_design_tokens`·`validate_design`·`validate_sources`·`print_code_hashes`가 한글 결과 줄에서 `UnicodeEncodeError`로 끝난다. #38이 `check_encoding`에서 만난 것과 같은 원인이다. Windows CI는 `check_encoding`만 돌려 못 잡았고, 이 PC(CP949)에서는 통과해서 보이지 않았다 | `PYTHONIOENCODING=cp1252`로 재현 | **이 PR에서 고쳤다.** 네 도구의 `main()`이 출력을 UTF-8로 고정한다(다른 도구와 같은 두 줄). `tests/test_encoding_console.py`가 네 도구를 CP1252 출력으로 돌린다. Windows CI job이 인계 6절의 검증 도구를 단계별로 돈다 — PowerShell의 여러 줄 `run`은 마지막 명령의 종료 코드만 보므로 나눴다. 수정을 되돌리면 새 시험이 실패함을 확인했다 |
| N2 | M6 생존. 기존 시험은 이미 120초가 지난 뒤에만 조회 실패를 봐서, 실패 표시가 빠져도 알 수 없었다 | 변이 | **이 PR에서 시험 추가.** 성공 조회 61초 뒤 실패하면 옛 값이 과거 관측값이 된다. 변이 M6이 이제 실패한다 |
| N3 | M11 생존. 가짜 app-server가 `id` 있는 서버 요청만 보내고 `turn/started` 같은 알림은 보내지 않았다 | 변이 | **이 PR에서 시험 추가.** 초기화 직후 `turn/started` 알림이 오면 조회가 멈추고 `account/read`를 보내지 않는다. 평범한 알림(`account/updated`)은 식별 정보째 버리고 조회를 마친다. M11과 “알림을 오류로 바꾸는” 반대 변이 모두 이제 실패한다(WSL) |
| N4 | 색인과 인계가 #38·#39 기록을 덜 담았다. `docs/reviews/README.md`의 표와 시간순 목록에 두 기록이 없고, 인계 재작성으로 main 이전 판의 사용자 판단 표·정리 후보가 한 줄로 줄었다(보관본에는 있다) | 비교 | 색인 표·목록에 두 기록과 이 기록을 넣었다. 인계 3·4절에 남은 판단과 작업을 구체적으로 되살렸다 |
| N5 | 화면: 계정 조회 요청 자체가 실패하면 버튼 글자가 “조회 중…”으로 남는다. 다음 1초 새로 고침에서 제자리로 온다 | 코드 읽기 | 낮음. 인계 4절 정리 후보에 적었다 |
| N6 | #38 본문의 “Windows까지 녹색이 되기 전 병합하지 마세요” | #39 정확한 head의 `windows-checks` 성공 | 조건 충족. #39로 함께 병합 |

병합 판단: N1–N3은 병합을 막지 않는다(현재 코드는 맞고 시험·다른 코드페이지의 문제다). 그래서 #39를 먼저 정확한 head로 병합하고(`--match-head-commit`), 이 후속 PR에서 고쳤다. 병합 사이에 main의 인계 3절은 #39를 “진행 중”으로 적고 있었고 이 PR이 고친다.

## 6. 병합과 정리

- #39 → main `40b2e67`(merge commit, `gh pr merge --merge --match-head-commit 948f5a3…`). #38은 head가 main에 들어가 GitHub이 병합됨으로 표시했다.
- 두 head 브랜치는 병합 때 저장소 설정으로 자동 삭제됐다. 확인한 뒤 원격에는 main만 남았고 열린 PR은 없었다.
- 이 세션은 서버·참여자를 띄우지 않았다. WSL은 시험을 위해 이 세션이 깨웠다(시작 전 Stopped).

## 7. 다음 작업을 구체화하며 확인한 사실(모두 모델 호출 없음)

| 확인 | 근거 | 다음 작업에 주는 뜻 |
|---|---|---|
| Claude `--bare`는 훅·플러그인·자동 메모리·CLAUDE.md를 건너뛰지만 **구독 로그인을 쓰지 않는다**(API 키 필요) | [headless 문서](https://code.claude.com/docs/en/headless) “Start faster with bare mode”, 2026-09-24 읽음 | 구독만 쓰는 원칙(2절 6·13)으로는 쓸 수 없다. F25와 같은 유형 — 깨끗한 문맥과 구독 인증이 한 옵션에서 갈린다 |
| Claude `--safe-mode`는 CLAUDE.md·skills·plugins·hooks·MCP·custom agents·auto memory를 끄고 인증·모델·내장 도구·권한은 그대로다(`--bare`와 다름). `--restricted`는 명령 실행 도구와 사용자·프로젝트 설정 읽기를 막는다 | [CLI 참조](https://code.claude.com/docs/en/cli-reference), 2026-09-24 읽음 | 참여자 계획은 지금 `--restricted`만 쓴다. 2026-09-23 관측에서는 `--restricted --safe-mode`에서 `agents-md@builtin` 플러그인이 오히려 늘었다([2단계 기록](../../experiments/w2-isolation/stage2-aux-pc-wsl.md), K45) — 문서와 관측이 어긋나는 곳부터 본다 |
| Claude 참여자의 격리는 `~/.claude`·`~/.claude.json`, Codex는 `~/.codex`를 **폴더째 쓰기**로 연결한다 | `core/isolation.cli_mounts` | 사용자 지시문·플러그인·지난 세션이 참여자에게 보일 수 있는 구조다. 2026-09-23 [K09 기록](../../experiments/w2-isolation/auth-mounts-aux-pc-wsl.md)의 다음 후보(폴더는 쓰기로 두고 필요 없는 하위 폴더를 빈 tmpfs로 덮기)가 C3의 구조적 해법 후보다 |
| Claude stream-json에는 `rate_limit_event`(5시간·7일 창의 `utilization` 0–1, `resetsAt`)가 있었다 | 2026-09-23 [2단계 기록](../../experiments/w2-isolation/stage2-aux-pc-wsl.md), 같은 2.1.280 | #39로 참여자가 stream-json이 됐으므로 **추가 호출 없이** Claude 계정 한도를 보일 수 있다. 지금 `claude_stream`은 이 사건을 버린다. #39 실행의 출력에 있었는지는 기록되지 않았다 |
| 판은 경로·내용이 아니라 역할(`<input>`, 연결 개수)로 계산된다 | `core/contract.template` | 입력 폴더 하나에 공통 자료를 넣어도 `claude-code@126be128bed7`·`codex@8a0128d4c791`가 그대로다 — 새 관측 없이 공통 자료를 구현할 수 있다 |
| Codex app-server에 `model/list`(추론 없음)가 있다 | [app-server 문서](https://learn.chatgpt.com/docs/app-server) | 요청 모델이 이 계정에서 보이는지를 준비 조회에 더할 수 있다. 실제로 답한 모델의 보고(K32)는 여전히 없다 |
| 실제 합성의 인용 검사기가 이미 있다 | `app/synthesis.compare_claims` — 원문 글자 위치·run·해시 대조 | 합성 출력의 주장마다 원문 인용을 요구하면, 맞지 않는 주장을 “원문에 없는 추가 주장”으로 표시할 수 있다. 설계 [§6](../../architecture/v0.4/02-frontier-architecture.md) 기준 `cross_check` 2인+합성은 3회 호출이다 |

이 사실로 정한 다음 작업 순서와 완료 조건은 [NEXT-SESSION.md](../../../NEXT-SESSION.md) 4절에 있다.
