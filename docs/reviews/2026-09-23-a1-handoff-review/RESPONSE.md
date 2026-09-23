# A1·인계 리뷰 — 반영 기록

작성: claude (Claude Opus 5.5), 2026-09-23. **보조 PC(`aux-pc`)의 로컬 checkout**(Windows)에서 작업했고, Linux 확인은 같은 PC의 WSL2 배포판(`aux-pc-wsl`)에서 `wsl.exe`로 했다. 모델 호출은 없다. 리뷰 원문([README.md](README.md)), [코드 우선 판단](CODE-FIRST.md), [재개 기록](RESUME-20260923.md), [재개 검증·WM-07 정정](VERIFICATION-20260923.md)과 재현 자료([`reproduce.py`](reproduce.py), [`observations.json`](observations.json))는 받은 그대로 두었다.

## 어떻게 확인했나

1. **리뷰어의 재현 스크립트를 고치지 않고 두 환경에서 돌렸다.** 대상은 검토 기준 `4bbd034`의 코드다(blob SHA 일치).
   - `aux-pc` Windows, Python 3.12.6: 합성 관측이 [`observations.json`](observations.json)과 모두 같았다. **하나만 달랐다** — `failed_second_server_start.bind_error`가 `null`이다. Windows에서는 두 번째 서버가 같은 포트에 bind까지 성공했다(아래 "새로 찾은 것" 2). 실제 bubblewrap 탐침은 Windows에서 돌지 않는다(`not_run`).
   - `aux-pc-wsl`, Python 3.12.3, bubblewrap 0.9.0: 합성 관측과 실제 bubblewrap 관측이 모두 기록과 같았다. PWD 추가, RO 입력 아래 작업 폴더에 호스트 표식이 쓰임, 자동 `/etc` 연결이 `never`를 무시함, stdin 기록 없는 답 수용, 두 번째 bind는 `OSError`.
2. **발견마다 회귀 시험을 만들고 고쳤다.** 리뷰의 권고대로 반례를 제품 시험으로 옮기고 기대를 뒤집었다.
3. **새 시험이 수정 전 코드에서는 실패하는지 확인했다.** 기준 코드에 새 시험만 넣어 돌렸다. controller 시험(Windows)과 경로 충돌 시험(WSL)이 모두 실패·오류로 끝났다. 예외는 `test_a_cli_that_reports_no_model_is_still_accepted` 하나다. 과잉 거절을 막는 대조 시험이라 수정 전에도 통과하는 것이 맞다.
4. **수정 뒤에는 두 환경에서 통과했다.** Windows, 그리고 WSL 시스템 Python에 `DML_REQUIRE_BWRAP=1`. CI(3.12·3.13)는 PR에서 확인한다.

## 발견별 판정

리뷰의 심각도와 다르게 본 곳은 "의견" 칸에 적었다. 판정과 반영에는 영향이 없다 — 모두 고쳤다.

| ID | 판정 | 의견 | 반영 | 회귀 시험(`tests/test_app_controller.py`, 격리는 `test_core_isolation.py`) |
|---|---|---|---|---|
| A1-01 공개 전 오류 설명 | **수용** | 높음 → 중간. 초안 본문은 새지 않았다. 드러난 것은 실패한 시도의 오류 문자열이고, 그것을 보는 사람은 사용자다. 다만 [BlindBarrier 계약](../../../design/project/components/BlindBarrier/README.md)은 `{id, provider, state, contamination[]}`만 넘기라고 하므로 위반은 맞다 | 공개 전 결과는 허용 목록 `SEALED_VIEW_KEYS`만 넘긴다. CLI 오류 원문과 runner 메모는 **모든 참여자가 끝난 뒤**(공개 보류 포함)에 넘긴다 — 그 전에는 그것을 본 사람이 원본 앱에 질문을 옮기며 다른 참여자에게 영향을 줄 수 있다. 토큰·시간·보고 모델·초안은 공개 뒤. 원인을 코드로 알 수 있게 `controller_restarted`·`executor_error`·`empty_answer`·`model_mismatch`를 더했다. 화면은 원문이 가려졌다고 적는다 | `test_cli_error_text_stays_out_of_the_view_until_everyone_is_done`(Claude·Codex) |
| A1-02 입력 증거 없는 답·빈 답 | **수용** | 높음 유지 | 수용 관문이 `input_delivery == complete`를 요구한다. 기록이 없으면(`None`) `input_error`다. 빈 답·공백 답은 `empty_answer`로 받지 않는다 — 수동 경로와 같은 규칙이다. `interpret()`의 `None` 허용은 `--version`처럼 입력 없는 명령 때문에 둔다. 질문을 argv로 보내는 agy는 붙일 때 그 전송의 증거를 따로 정한다(K07) | `test_the_gate_needs_delivery_a_real_answer_and_the_requested_model` |
| A1-03 두 번째 시작·늦은 완료 | **수용, 범위 넓힘** | 가장 먼저 고칠 것. 리뷰보다 넓다 — 아래 "새로 찾은 것" 1·2 | 원장 잠금: `Store`가 `journal.db.lock`을 배타적으로 잡는다(POSIX `flock`, Windows `msvcrt.locking`). 서버 시작 순서는 잠금 → 포트 → 복구 → 토큰. 시작(queued → running)과 결과 반영(running → …)은 기대한 상태와 시도 ID가 맞을 때만 한다. 시도 ID는 `participants.attempt`에 영속한다. 늦은 결과는 `attempt_result_ignored` 사건으로만 남는다 | `test_a_journal_opens_in_one_store_at_a_time`, `test_a_second_server_on_the_same_data_leaves_the_first_alone`, `test_a_result_after_the_user_acknowledged_unknown_is_ignored`, 기존 `test_attempts_running_at_restart_become_unknown_and_are_not_rerun`의 끝 상태 |
| A1-04 마운트 검사 | **수용** | 높음 → 중간. 지금 그런 구성을 만드는 호출자는 없다(모의 실행기는 `/tmp` 아래 작업 폴더와 홈 아래 원장). 수정은 검사 두 줄이다 | 작업 폴더가 읽기 전용 입력 안에 있으면 거절한다. `never`는 자동 시스템 연결(`/usr`, `/etc`, 병합 링크 폴더, `/etc` 밖을 가리키는 네트워크 파일)과도 비교한다. Codex의 쓰기 설정 폴더 안 읽기 전용 실행 버전은 그대로 허용한다 | `test_conflicting_mounts_are_refused`의 세 경우(WSL), `test_a_read_only_release_inside_the_cli_folder_is_intended`는 그대로 통과 |
| A1-05 초안 저장과 공개 사이의 중단 | **수용** | 중간 유지. 두 거래 사이의 짧은 틈이라 드물다 | 공개 판정을 상태를 바꾼 **같은 거래 안에서** 한다. 다시 시작할 때 초안 작성 중인 실행의 공개 관문을 다시 본다(수정 전 원장용). 대기 중인 시도는 다시 시작한 뒤 저절로 시작하지 않고, 사용자가 화면의 "대기 중인 시도 이어서 시작"(`POST /api/resume`)을 눌러야 시작한다. 취소가 없어서(K19) 서버를 끄는 것이 지금 유일한 멈춤 수단이기 때문이다 | `test_a_run_stopped_between_its_last_draft_and_reveal_is_revealed_on_restart`, `test_queued_attempts_wait_for_the_user_after_a_restart` |
| A1-06 축소 승인이 구성에 안 묶임 | **수용** | 중간 → 낮음. 그 시점에는 화면에 버튼이 없어 API를 직접 부를 때만 생긴다 | 승인은 controller가 기다릴 때만 받는다(초안 작성 중·모두 끝남·이탈 있음·아직 승인 안 함). 그 뒤로는 구성이 바뀌지 않으므로 승인은 지금 구성에 대한 것이다. 사건에 요청 구성과 이탈자를 남긴다. 없는 실행에는 사건을 남기지 않는다 | `test_a_reduction_is_approved_only_while_the_controller_waits_for_it` |
| A1-07 모델 불일치 수용 | **수용** | 중간 유지. 주의: aux-pc tier 2에서 Claude가 보고한 모델은 전체 이름(`claude-opus-5-5`)이었다. 별칭으로 요청하면 정상 호출도 불일치로 보일 수 있다 | `model_match`가 `False`면 `model_mismatch`로 받지 않고 구성 축소로 드러낸다(D18). 보고가 없으면(`None`, Codex·agy) 받는다(K32). 공개 뒤 화면에 요청 → 보고 모델과 불일치를 적는다. 요청은 전체 이름으로 한다(N1). 불일치를 보류해 두고 사용자에게 묻는 상태는 B1에서 별칭 대응을 본 뒤 정한다(K43) | 위 수용 관문 시험의 "another model", `test_a_cli_that_reports_no_model_is_still_accepted` |
| A1-08 수동 답 SHA 설명 | **수용, 더 강하게** | 화면이 그 카드의 digest를 자동으로 넣으므로 K21의 "다른 실행에 잘못 넣는 것만 막는다"도 성립하지 않는다. 화면에서는 검사가 사실상 늘 통과한다 | controller 설명, [app/README](../../../app/README.md), K21을 고쳤다. 막는 것은 화면 밖 요청의 digest 불일치, 공개 뒤·중복 제출, 빈 답이다. 실제로 잡는 방법(복사 패킷의 실행 표식과 되말하기)은 N5에 적었다 | — (문구) |
| A1-09 AGENTS 현재 상태 | **수용** | — | 리뷰 PR에서 이미 고쳤다 | — |
| WM-07 정정 | **수용** | — | 정정 내용이 코드와 맞다. `unsettled()`는 시도 수와 스레드 수를 더한 보수적 지표이고, 시작하기 전에만 비교한다 | — |

## 리뷰 밖에서 새로 찾은 것

1. **같은 참여자를 두 번 부를 수 있었다.** `pump()`가 상태를 running으로 바꿀 때 아직 queued인지 보지 않았다. 같은 journal을 연 controller 둘이 거의 동시에 pump하면 둘 다 시작한다. 끼어드는 순서를 고정한 합성 재현에서 시작 사건 2회, 실행 2회였고 화면 예산은 `1 / 1`이었다. 실제 모델이었다면 구독 사용량이 두 배로 빠지는데 화면에는 드러나지 않는다. 조건부 전이와 원장 잠금으로 닫았다(`test_one_participant_starts_once_even_with_two_controllers`).
2. **Windows에서는 두 번째 서버가 실패하지도 않았다.** `ThreadingHTTPServer`가 켜는 SO_REUSEADDR 때문에 이미 듣고 있는 포트에 두 번째 서버가 bind됐다(리뷰 스크립트 결과와 별도 확인). "포트를 먼저 잡으면 된다"는 방어는 Windows에서 성립하지 않는다. Windows에서는 이 옵션을 껐고, 이중 시작은 원장 잠금이 막는다(`test_two_servers_cannot_share_a_port`).
3. **기존 재시작 시험이 결함 상황을 만들고도 끝 상태를 보지 않았다.** 두 번째 controller로 unknown을 만든 뒤 옛 시도를 풀어 주고 끝났다. 그대로 따라가 끝을 보면 `unknown → accepted`, phase `drafting`, 메모 "독립 참여자 0명"(초안이 있는데 0명이라는 모순)이었다. CI가 녹색인데도 A1-03이 안 잡힌 이유다. 끝 상태를 확인하게 했다.
4. **공개 보류 메모가 판정할 때마다 사건을 새로 남겼다.** 다시 시작할 때 공개 관문을 다시 보게 되면서 같은 메모가 쌓일 수 있어, 메모가 바뀔 때만 남기게 했다.

## 리뷰 문구에 대한 의견

리뷰 원문은 고치지 않는다. 읽을 때 다음을 함께 본다.
- A1-02의 실제 bubblewrap 사례(질문 없이 성공 JSON만 출력해도 수용·공개)는 **일부러 stdin을 주지 않는 시험용 실행기**의 결과다. 당시 제품 경로(`MockExecutor`)는 늘 질문을 보냈다. 본문의 "한정" 문단이 정확하고, 의미는 "실제 실행기를 붙이다 실수하면 관문이 못 잡는다"였다. 요약해 옮길 때 이 한정이 빠지기 쉽다.
- A1-04의 "호스트 임시 입력 폴더에 marker 파일이 쓰였다"에서 표식이 쓰인 곳은 작업 폴더 자체다(그 폴더가 입력 아래에 있었다). 결함은 그런 중첩을 막지 않은 것이고, 실제 위험은 그 입력 폴더를 다른 참여자와 함께 쓸 때 생긴다.
- "대부분의 controller 시험은 합성 executor를 쓴다. 거기에 적힌 `PID_NAMESPACE`는 OS 증거가 아니다": 저장소 시험의 합성 실행기는 `JOB_OBJECT`·`PROCESS_GROUP`을 쓴다. `PID_NAMESPACE`는 리뷰의 재현 스크립트 값이다. 요지(합성 containment는 OS 증거가 아니다)는 맞다.

## 질문별 답에 대해

- **질문 1(K 표):** 수용. K11·K19·K20·K21·K26·K28을 고치고 K41–K43을 더했다. K01의 "A1이 `None`을 받는 예외"는 A1-02로 닫혔다.
- **질문 2(WM 반영):** 수용. PWD는 [`core/isolation.py`](../../../core/isolation.py) 설명에 적었다 — 자식 환경은 허용 목록과 똑같지 않다. `_trusted_bwrap`의 설명은 "패키지 서명·해시는 확인하지 않는다"로 좁혔다. 앞 리뷰의 [반영 기록](../2026-09-23-wsl2-migration-review/RESPONSE.md)은 날짜 기록이라 고치지 않는다.
- **질문 3(수용 관문·공개):** 수용. 위 A1-02·03·05·06.
- **질문 4(봉인 투영):** 수용. A1-01. 반복 조회로 상태가 바뀌는 시각을 대략 알 수 있는 것은 운영자용 거친 상태로 허용한다고 K41에 적었다. 참여자에게는 제어 API 토큰이 없다.
- **질문 5(제어 API):** 부분 수용. 토큰 파일을 처음부터 0600으로 만들고 통째로 바꾸며, POSIX에서 데이터 폴더를 0700으로 둔다. Origin 허용 목록, 콘텐츠 타입 강제, 프레임 삽입 정책, 읽기 시간 제한, 브라우저 교차 출처 음성 시험은 미뤘다(K42). 토큰을 `Authorization` 머리글로만 받으므로 교차 출처 요청은 preflight에서 막힌다고 보지만, 브라우저로 시험하지는 않았다.
- **질문 6(수동 참여):** 부분 수용. 문구는 고쳤다(A1-08). "답을 낸 참여자 수"와 "독립성이 확인된 참여자 수"를 나누는 정족수 정책은 **Q6의 사용자 결정**으로 남긴다. 리뷰의 제안(정책을 실행마다 고정하고, 미확인 참여까지 센 결과를 "독립 정족수 충족"으로 표시하지 않음)을 N5의 기본안으로 적었다.
- **질문 7(계획):** 수용. 모델 없는 관문 보강(리뷰의 N0)을 이 반영으로 먼저 했다. K20·K28의 필요한 부분도 여기서 했다. 2단계를 승인할 때 provider별 최대 시작 횟수·실패 포함 상한·timeout·중단 조건을 고정한다고 인계에 적었다.
- **질문 8(인계):** 수용. N1의 완료 조건(명세 기록, 전체 모델 이름, 복구 시험)을 구체화했다.

## 남은 것

- 리뷰 권고 중 미룬 것: 제어 API 추가 방어(K42), 모델 불일치 보류 상태(K43), 수동 참여의 실행 표식·확인 단계와 Q6 정책(N5).
- 원장 잠금은 한 기기 안의 파일 잠금이다. 기기 여러 대가 한 원장을 나눠 쓰는 경우는 범위 밖이다(K20).
- 확인하지 못한 것: CI(PR에서 확인), 실제 모델 호출, 브라우저 화면(K27), 실제 전원 차단.
