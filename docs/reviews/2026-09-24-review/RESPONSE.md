# 2026-09-24 리뷰 — 반영 기록

작성: claude (Claude Opus 5.5), 2026-09-24. **보조 PC(`aux-pc`)의 로컬 checkout**(Windows)에서 작업했고, Linux 확인은 같은 PC의 WSL2 배포판(`aux-pc-wsl`)에서 `wsl.exe`로 했다. **모델 호출은 없다.** 리뷰 원문([README.md](README.md)), [중간 판정](EVIDENCE-ASSESSMENT.md), [진행 기록](PROGRESS.md)과 재현 자료([`reproduce.py`](reproduce.py), [`eligibility-source.py`](eligibility-source.py), [`results.json`](results.json))는 받은 그대로 두었다.

- 리뷰 PR([#14](https://github.com/inlight37-design/decision-model_lab/pull/14))은 CI 녹색이었지만, 이 세션의 자동 권한 확인이 병합을 "리뷰 없는 병합"으로 막았다. 우회하지 않았다. 반영 브랜치(`claude/review-response-20260924`)를 리뷰 브랜치 위에 쌓았다 — 이 브랜치를 병합하면 리뷰도 함께 들어간다.

## 어떻게 확인했나

1. **검토 기준이 지금 코드와 같은지 봤다.** main의 `core/eligibility.py`, `tools/w2/observe.py`, `core/adapters.py`, `app/cli_executor.py`의 Git blob이 리뷰 7절의 값과 같았다. 리뷰의 반례는 main에 그대로 해당했다.
2. **리뷰어가 돌리지 않은 `--repo` 검증까지 돌렸다.** `python reproduce.py --repo .`(Windows, Python 3.12.6)는 종료 코드 0이었고 `repository_ast_verification: true`였다. 발췌한 판정식이 실제 `observe.py`와 AST로 같다. 반례 12개가 모두 재현됐고 대조군 2개도 기대대로였다:
   - k46: 무관한 명령, 인증 파일 없음, 앞의 열기 성공이 덮임, 쓰기 성공 뒤 파일 없음, 자손 종료 미확인
   - P3: 시간 초과, 종료 미확인
   - b1: 모델 불일치
   - 실행 허가: 미래 날짜, 근거 없음, 양쪽 버전 없음
3. **반례를 제품 회귀 시험으로 옮기고 기대를 뒤집었다.** 수정한 코드에서는 `reproduce.py --repo`가 해시 불일치로 멈춘다 — 리뷰 7절이 말한 의도된 동작이다. 반례의 수정 전 동작은 이 폴더의 `results.json`과 위 2의 재실행이 기록이다.
4. **두 환경에서 전체 시험을 통과했다.** Windows(Python 3.12.6. skip은 bubblewrap·Linux 전용 시험이다)와 WSL 시스템 Python 3.12.3에 `DML_REQUIRE_BWRAP=1`(bubblewrap 0.9.0. skip은 Windows 레지스트리 시험 하나다). CI(3.12·3.13)는 PR에서 확인한다.
5. **합성 HOME 진단을 돌렸다(모델 없음, 실제 로그인 파일 연결 없음).** 리뷰 질문 9가 권한 단계다. [기록](../../experiments/w2-isolation/k46-synthetic-aux-pc-wsl.md): profile 없는 대조군에서는 helper가 가짜 인증 파일을 **열었고**, exec 방식·`-P` 방식의 profile에서는 `denied:EACCES`였다. 쓰기는 `denied:EROFS`, 공통 자료는 열렸다. 새 합격 조건이 기대하는 모양과 같다.

## 발견별 판정

| ID | 판정 | 의견 | 반영 | 회귀 시험 |
|---|---|---|---|---|
| R01 K46 합격 조건 | **수용** | 높음 유지. 실제 호출 전에 알아서 다행이다 — 지금 판정으로 1회를 썼다면 결과를 믿을 수 없었다 | 셸 명령을 **고정 helper**로 바꿨다. 관측 도구가 시도마다 nonce를 넣어 읽기 전용 공통 자료 폴더에 둔다. helper는 인증 파일을 열었다 닫기만 하고(내용을 읽지 않는다) errno 이름을 찍는다. 판정(`observe.k46_check`)은 명령 항목이 정확히 `python3 <helper>` 하나이고 끝까지 돌았고 이번 nonce의 결과 줄이 하나일 때만 `verified`다. 인증 파일 열기(`auth=ok`)나 쓰기 성공은 **어느 출력에서든** 지워지지 않는 위반이다. `ENOENT`는 거절로 치지 않는다 — `EACCES`·`EPERM`만 받는다. 인증 파일이 실제로 있는지는 부르기 전에 관측 도구가 격리 밖에서 본다(없으면 부르지 않고 세지도 않는다). 질문에서 문맥 자기 보고를 뺐다(R06) | `JudgementTests`의 세 시험, `CallTests.test_k46_judges_the_helper_output_of_this_attempt`(정상, 열림, 덮어쓰기, 쓰기 성공, ENOENT, helper 흉내, 토큰), `test_k46_is_not_started_without_a_login_file_to_test` |
| R02 실행 허가의 검증 누락 | **수용** | 높음 유지. 기록 검사기도 `2026-13-01` 같은 없는 날짜를 받았다(아래 "새로 찾은 것" 1) | 실행 허가와 기록 검사기가 같은 구조 검사(`eligibility.row_problems`)를 쓴다. 실행 허가는 미래 관측일, 없는 날짜, 근거 없는 `observed`, 기록 버전 없음, 지금 버전을 못 읽음(`None`), 같은 CLI의 중복 행을 모두 거절한다. 나이는 `0 <= age <= max_age_days`다 | `EligibilityTests.test_malformed_or_impossible_records_are_refused_at_run_time`, 검사기 시험의 새 두 경우 |
| R03 관측 도구의 수용 조건 | **수용** | 중간 유지 | controller의 수용 관문을 공개 함수 `app.controller.acceptance()`로 바꾸고(전 이름 `_verdict`), 답을 받는 probe는 모두 그것을 통과해야 기대대로다 — 자손 종료, 입력 전달, 빈 답, 모델 불일치. P3는 스스로 끝남, 자손 종료 확인, 비영 종료, 모델 답·사용량 없음, 그리고 **그 버전에서 확인한 오류 문구**가 stderr에 있어야 한다. 요약에 `gate`를 적는다 | `JudgementTests.test_a_refusal_needs_a_clean_exit_and_the_known_error`, `CallTests.test_answers_must_pass_the_controller_gate` |
| R04 상태와 구성의 결합 | **부분 수용** | 둘로 나눈다. (b)는 받고 (a)는 사용자에게 묻는다(아래 "사용자에게 묻는 것" 1) | (b) **관측을 실행 명세의 판에 묶었다.** `core.adapters.SPEC_REVISION`(argv와 격리 연결)을 두고, 기록의 전송·문맥·권한 칸에 관측할 때의 `spec_revision`을 적는다. 판이 다르면 허가하지 않는다. WSL 기록은 2단계 관측을 `discussant-1`로 적었다. Codex는 K46 profile로 argv가 바뀌어 `discussant-2`이므로, 옛 권한 관측으로는 허가가 나오지 않는다 — 리뷰가 걱정한 재사용이 막혔다. 판마다 argv를 시험이 고정한다. (a) Claude 문맥 `observed → unknown`: 기록을 바꾸지 않았다 | `test_observations_are_bound_to_the_participant_spec_they_were_made_with`, `test_each_spec_revision_pins_its_argv`, 기록 시험의 Codex 이유 |
| R05 예약의 원자성 | **수용** | 중간 유지. 순차로만 불러 실제 초과는 없었다 | 상태 폴더의 `fcntl` 배타 잠금 안에서 승인 검사 → 준비 → 시도 번호 예약을 한 번에 한다(`observe._reserve`). 준비에서 거절되면 예약하지 않는다. `approve`도 같은 잠금을 쓴다. 승인 ID와 `--after-failure`를 사용자 허락에 잇는 것은 하지 않았다 — 질문 6의 승인 카드로 대신한다 | `ReservationTests`(스레드 넷이 상한 1을 두고 겨룸, 준비 거절) |
| R06 세션 요약의 한계 | **수용** | 중간 유지 | 요약이 모든 문자열과 짧아서 뺀 수, 목록에서 자른 수, 읽지 못한 줄 수를 적는다. 우리 질문에서 온 글은 `from_prompt`로 표시한다. k46 질문에서 skill·plugin·MCP를 묻는 자기 보고를 뺐다 — 그 단어가 기록의 표식을 오염시켰다. 도구 설명과 인계에 "탐색 보조이지 C3를 닫는 근거가 아니다", "`--ephemeral`을 빼는 것은 진단 변형이다"를 적었다. 세션 ID·이벤트 역할의 대조는 실제 기록 형식을 본 뒤에 한다 | `test_keep_session_moves_this_calls_record_out_and_keeps_only_its_shape`의 수 |
| R07 가림의 한계 | **수용** | 중간 유지. "JWT가 없으니 안 샜다"고 쓴 적은 없지만, 도구 설명이 그렇게 읽힐 수 있었다 | 요약을 저장하기 전에 모든 문자열(키 포함)을 한 번 더 가린다 — 입력 digest는 남긴다(질문 8). JWT 검사를 stderr까지 넓혔다. 설정 폴더 목록이 상한에 걸리면 `snapshot_limit_reached`를 적는다. 진단의 `auth_file_unchanged`를 `auth_size_mtime_unchanged`로 이름을 바꿨다 — 내용이 같다는 뜻이 아니다. 도구 설명에 "토큰 모양 검출은 추가 정지 신호이고 방어는 인증 경로 차단"이라고 적었다. 고정 필드 허용 목록은 이미 `summarize`가 명시한 칸만 만드는 방식이라 따로 두지 않았다 | `SummaryTests.test_the_final_pass_scrubs_every_string_but_keeps_the_input_digest` |
| R08 K01 완료 표현 | **수용** | 중간 유지 | 인계의 K01 줄과 2단계 목록을 "약 95 KB 전송, 정상 응답, 입력만큼의 토큰 증가 관측"으로 좁혔다. 날짜가 있는 [K01 기록](../../experiments/w2-isolation/k01-large-input-aux-pc-wsl.md)은 고치지 않고 여기와 목록에서 단서를 단다. `--pad-kb`는 이제 채움 글의 가운데와 끝에 시도마다 새로 만든 표식을 두고, 답이 그것을 되말했는지(`pad_markers_seen`)를 적는다. 추가 호출은 요구하지 않는다는 리뷰의 판단에 동의한다 | `test_a_padded_question_hides_fresh_markers_in_the_middle_and_at_the_end`, `CallTests.test_a_padded_question_is_judged_by_its_end_marker` |
| R09 `write_refused` | **부분 수용** | 낮음 유지. `codex_sandbox.py`는 맞다 — 결과 줄이 없어도 참이 됐다. `codex_profile.py`는 이미 `write_rc`가 있어야 참이었다(`values.get("write_rc") not in (None, "0")`) | `codex_sandbox.write_state()`가 `not_run`·`denied`·`allowed`를 나눈다. `codex_profile.py`는 helper의 errno로 바꿨다 | `WriteStateTests` |

## 질문별 답에 대한 대응

- **질문 1(K46 설계):** 동의. `~/.codex`의 다른 파일(세션 기록, 상태 DB, 메모리, 로그, 캐시)을 분류하는 일은 K09·K46에 남긴다. 인증 파일을 옮기지 않는다는 권고에도 동의한다.
- **질문 2(승인 값):** 리뷰가 권한 승인안을 인계에 그대로 옮겼다 — Codex 최대 1회, Claude 0회, 실패·거부·시간 초과 포함, 호출당 300초, `gpt-6-luna`, `--keep-session` 기본 끔. 사용자에게 승인 카드로 묻는다(아래 2).
- **질문 3(네트워크 없는 exec):** 동의. 이름을 "네트워크를 차단한 인증 상태 연결 startup 진단"으로 받는다. `codex_profile.py`의 기본을 합성 HOME으로 바꿨다. 실제 로그인 상태를 연결하는 진단(`--real-home`, `codex_sandbox.py`)은 사용자 허락 뒤에만 돌린다고 도구와 인계에 적었다.
- **질문 5(C3):** 동의. (b)는 정책이지 관측 성공이 아니다. 지금 실행 허가에는 정책으로 받아들이는 길이 없다. (b)를 고르면 `observed`로 바꾸지 않고 별도 정책 칸을 설계해야 한다.
- **질문 6(승인·병합):** 승인 카드(provider, 전체 모델 이름, 최대 시작 횟수, 실패 포함, timeout, 멈춤 조건, 세션 보관)를 다음 승인부터 쓴다. 자체 병합은 사용자가 정할 일이다 — 이번에는 이 세션의 권한 확인이 리뷰 PR 병합을 막았다.
- **질문 7(CLI 표면):** 부분 반영. 옵션을 계획에 적을 때 기록된 help 줄을 인용하는 규칙은 인계 5절에 넣었다. `plan`이 help와 대조하는 도구는 만들지 않았다.
- **질문 8(공개 요약):** 도구의 마지막 가림이 입력 digest를 남긴다. 공개한 JSON의 SHA-256은 다음과 같다(2026-09-24 요청서 폴더):
  - `observe-summaries.json` `45a8e2ca4351bac2cbd9671a95bc30e5c0f2970a646d258200f1d2fb739f78e3`
  - `k46-profile-run1.json` `f16ca36750119ac48cdaec8cedb8e6c6c07e9a9c7a10048c7b8bd31ce5b2e2c8`
  - `k46-profile-run2.json` `fd1f67b224a809ad9ba5721fcd81084e4c776f93f215a5d16fe429c0d0ed300b`
  - 1–5번 요약의 `as_expected`는 당시 판정이다. 새 판정식으로 다시 계산하지 않는다.
- **질문 9(다음 순서):** 동의하고 그대로 했다 — 오프라인 판정식·허가·예약 보강, 합성 HOME 진단. 남은 것은 새 승인으로 K46 1회다.
- **17번 질문 8(계정 한도):** 동의. stream-json 해석 경로와 회귀 fixture를 3단계 사용량 표시 작업에 넣는다.
- **S31 대조:** 리뷰가 PR #8의 버린 인계 내용에서 사용자 결정의 손실을 찾지 못했다 — 받아들인다.

## 리뷰 밖에서 새로 찾은 것

1. **기록 검사기도 없는 날짜를 받았다.** 검사기는 `observed_at`의 모양만 정규식으로 봤다. `2026-13-01`이 통과했다. 이제 날짜로 읽을 수 있어야 한다.
2. **k46 질문의 자기 보고가 세션 요약을 오염시켰을 것이다.** 질문에 skill·plugin·MCP·AGENTS.md를 적어 두었기 때문에, 그 질문이 세션 기록에 들어가면 요약의 표식이 항상 켜진다. 질문에서 뺐다.
3. **진단 도구의 기본이 실제 로그인 상태를 연결하고 있었다.** `codex_profile.py`를 인자 없이 돌리면 사용자 `~/.codex`를 연결했다. 기본을 합성 HOME으로 바꿨다.
4. **profile이 막을 때 errno는 `EACCES`다**(합성 HOME 진단). ENOENT가 아니어서, 파일이 없는 것과 막힌 것이 helper로 구분된다.
5. **옛 이름을 가리키는 문서가 있다.** ChatGPT의 [tmux 분석](../../research/tmux-2026-09-23/ANALYSIS.md)이 `_verdict()`를 가리킨다. 다른 세션의 조사 문서라 고치지 않았다 — 지금 이름은 `acceptance()`다.

## 사용자에게 묻는 것

1. **Claude 문맥 칸(R04 (a)).** 리뷰는 `observed`를 `unknown`으로 바꾸라고 권한다. 근거는 `CLAUDE.md`를 싣지 않았다는 것이 모델의 자기 보고뿐이라는 점이다. claude 세션도 그 근거 평가에 동의한다.
   - 바꾸면 Claude도 실제 실행 허가를 잃는다. 되찾으려면 K31을 모델 보고가 아닌 방법(큰 표식 파일과 보고 토큰 차이 — 모델 1회)으로 닫거나, 정책 칸을 새로 설계해야 한다. 지금 화면 서버는 모의 실행기만 써서 당장 막히는 작업은 없다. B3 전에는 풀어야 한다.
   - 권고: `unknown`으로 바꾸고, K31 확인을 B3 전 승인 목록에 넣는다.
2. **K46 확인 호출의 승인 카드.** Codex 최대 1회(Claude 0), 실패·거부·시간 초과 포함, 호출당 300초, 모델 `gpt-6-luna`, `--keep-session` 끔. 인증 파일이 없거나, helper가 아닌 명령이 돌거나, 종료가 확인되지 않거나, 인증 파일이 열리거나 토큰 모양이 보이면 멈춘다. 사용량 한도 메시지면 모두 멈추고 원문을 게시하지 않는다.
3. **병합.** 리뷰 PR #14와 이 반영 PR은 사용자가 병합하거나, claude 세션에게 병합을 지시해야 한다.
