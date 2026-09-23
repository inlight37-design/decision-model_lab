# WSL2 전환 재검토 — 반영 기록

작성: claude (Claude Opus 5.5), 2026-09-23. **보조 PC(`aux-pc`)의 로컬 checkout**에서 작업했고, Linux 확인은 같은 PC의 WSL2 배포판(`aux-pc-wsl`)에서 `wsl.exe`로 했다. 모델 호출은 없다. 리뷰 원문([README.md](README.md))과 재현 자료([`reproduce.py`](reproduce.py), [`results.json`](results.json))는 받은 그대로 두었다.

## 어떻게 확인했나

1. **리뷰어의 재현 스크립트를 고치지 않고 그대로 돌렸다.**
   - 대상: 검토 기준 `a662e59`와 같은 코어 파일(blob SHA 일치).
   - 환경: `aux-pc-wsl`, Python 3.12.3.
   - 결과: 모든 탐침이 리뷰의 [`results.json`](results.json)과 같게 나왔다. 입력 1,680,000바이트 중 1바이트만 읽혔는데 `ok`, 가짜 토큰이 argv에 들어감, 이름만 bwrap인 파일이 `pid_namespace`와 `tree_confirmed_empty=True`를 받음, 경로 충돌 계획을 받아들임, 빈 PATH가 부모 PATH로 되돌아감, 깊은 중첩에서 `RecursionError`, 빈 잘못된 타입을 `ok`로 받음, 정리되지 않은 실행 두 번 뒤 스레드와 fd가 4개씩 남음.
2. **발견마다 회귀 시험을 만들고 고쳤다.**
3. **새 시험이 수정 전 코드에서는 실패하는지 확인했다.** 수정 전 코어(`main`의 `4c1f9c3`)에 새 시험만 넣어 WSL에서 돌렸더니 새로 넣거나 바꾼 시험이 모두 실패·오류로 끝났다.
4. **수정 뒤에는 세 환경에서 통과했다.**
   - Windows(Python 3.12.6)
   - WSL의 시스템 Python
   - WSL에서 `/usr` 밖에 복사한 Python(CI 조건)과 `DML_REQUIRE_BWRAP=1`
5. **W2 CLI 도구를 새 진입점으로 다시 돌렸다.** 모델 호출은 없다. Claude Code·Codex 모두 격리 안에서 `--version`과 로그인 상태가 exit 0이었다. 자기 로그인만 보였고 자손 전체의 종료가 확인됐다.

## 발견별 판정

| ID | 판정 | 반영 | 회귀 시험 |
|---|---|---|---|
| WM-01 stdin 전송 실패가 사라짐 | **수용** | 쓰기 스레드가 쓴 바이트와 오류를 남긴다. 결과에 `input_delivery`(`complete`·`failed`·`incomplete`, 입력이 없으면 `None`)와 메모가 붙는다. 프로세스 상태(`state`)는 그대로 둔다. `interpret()`는 전달이 완전하지 않으면 답이 그럴듯해도 `input_error`로 돌려주고, 다시 부르지 않는다 | `test_core_runner`: `test_input_the_cli_stopped_reading_is_recorded`. `test_core_adapters`: `test_an_answer_to_a_partly_delivered_question_is_not_accepted` |
| WM-02 OAuth 값이 bwrap argv에 | **수용** | 아래 "WM-02 반영의 세 가지" 참조 | `test_core_isolation`: `test_credentials_are_refused_not_passed`, `test_environment_values_never_reach_argv`. `test_core_adapters`: `test_the_record_form_never_carries_the_question` |
| WM-03 이름과 플래그만으로 namespace 보장 | **수용** | 공개 `runner.run()`에서 `pid_namespace`를 뺐다. 진입점은 [`isolation.run()`](../../../core/isolation.py) 하나다. 조립(`plan`) 뒤 `/usr/bin/bwrap`이 일반 파일이고 root 소유이며 그룹·다른 사용자가 쓸 수 없는지 확인하고 실행한다. Python에서 내부 함수 호출을 막을 수는 없다. 실질적인 확인은 실행 파일의 출처 검사다 | `test_the_public_runner_cannot_claim_a_namespace`, `test_only_a_root_owned_bubblewrap_is_trusted` |
| WM-04 work·HOME·입력 충돌 허용 | **수용** | 아래 "WM-04 반영의 규칙" 참조 | `test_conflicting_mounts_are_refused`(symlink 별칭 포함), `test_a_read_only_release_inside_the_cli_folder_is_intended` |
| WM-05 빈 PATH가 부모 PATH로 | **수용** | 자식 환경의 PATH를 대소문자 무관하게 찾는다. 없으면 거절하고, 비어 있으면 찾지 못한 것으로 본다 | `test_core_env`: `test_an_empty_or_missing_child_path_does_not_fall_back_to_ours` |
| WM-06 파서 경계 | **수용** | 형식 실패 경계에 `RecursionError`를 넣었다. `or {}`·`or []` 대신, 값이 없거나 `null`이면 기본값을 쓰고 잘못된 타입이면 형식 실패로 구분한다(`modelUsage`, `permission_denials`, Codex `item`) | `test_deep_or_empty_wrong_shapes_are_format_errors`(`null`은 정상으로 남는지도 본다) |
| WM-07 잔류 스레드·fd | **부분 수용** | 아래 "WM-07 반영과 미룬 것" 참조 | R02 회귀 시험(POSIX)이 `lingering()`이 1 이상이었다가, 손자를 끝낸 뒤 0이 되는 것을 본다 |

**WM-02 반영의 세 가지**
- 환경변수 값을 명령 인자에 싣지 않는다. 허용 목록의 변수만 bwrap 프로세스의 환경으로 주고, bwrap은 그것을 그대로 넘긴다. 그래서 `--clearenv`·`--setenv`를 쓰지 않는다.
- 인증 토큰과 과금 변수(`CLAUDE_CODE_OAUTH_TOKEN`, `core.env.BILLING_VARS`)는 조용히 버리지 않고 **거절**한다. 인증은 CLI의 로그인 파일로 한다.
- 실행 명세의 기록용 사본은 `ExecutionSpec.record()`다. 본문 대신 digest와 크기를 두고, agy처럼 argv에 질문이 있으면 그 자리를 digest 표시로 바꾼다. `repr()`도 이것을 쓴다. `dataclasses.asdict()`에는 본문이 들어가므로 기록에 쓰지 않는다고 적었다. **남은 것:** agy 실행의 `RunResult.argv`에는 질문이 들어 있다. controller는 `RunResult.argv`가 아니라 `spec.record()`를 기록해야 한다(인계에 적었다).

**WM-04 반영의 규칙** — 모든 연결 경로를 실제 경로로 풀어 비교하고, 다음이면 거절한다.
- 어떤 연결이 HOME 자체이거나 그 위 폴더다.
- 작업 폴더가 읽기 전용 입력과 같거나, 다른 연결을 품는다.
- 연결이 새 `never` 경로(원장·봉인 저장소)와 겹친다.

읽기·쓰기 폴더 안의 읽기 전용 연결(Codex 실행 버전 폴더)은 의도한 겹침으로 허용한다. 검사와 실행 사이에 파일이 바뀌는 경쟁은 해결하지 않았다고 모듈 문서에 적었다.

**WM-07 반영과 미룬 것**
- `runner.lingering()`이 돌아온 뒤에도 끝나지 않은 입출력 스레드를 센다.
- 문구를 좁혔다. 벽시계 보장이 아니라 "프로세스를 만든 뒤의 명시적 정리 대기에 상한"이다.
- 미정리 시도의 상한은 controller의 몫이다(A1).
- 비차단 I/O로의 재구성은 하지 않았다. 운영 경로인 `isolation.run()`에서는 bwrap이 끝나면 namespace가 비워지고, 파이프를 쥔 프로세스도 남지 않기 때문이다. 일반 POSIX 경로의 잔류는 세서 드러낸다.

## 리뷰 밖에서 새로 찾은 것

- **입력 인코딩이 CLI를 띄운 뒤에 일어났다.** 인코딩할 수 없는 문자(짝 없는 surrogate)가 들어오면, CLI가 이미 떠 있는 상태에서 `UnicodeEncodeError`가 밖으로 나갔다. 이제는 띄우기 전에 `RunnerError`로 거절한다(`test_input_that_cannot_be_encoded_is_refused_before_starting`). 리뷰의 제안 "문자열 검증·인코딩을 프로세스 생성 전에"와 같은 방향이다.
- **확장자 없는 Windows 실행 파일.** 리뷰는 질문 6에서 가능성으로 들었고 재현하지는 않았다. `resolve()`가 파일 내용의 PE 서명(`MZ`)도 보게 했다(`test_resolve_refuses_a_windows_executable`). 이것은 흔한 실수를 막는 가드다. interop 차단의 보장은 격리 쪽(`/mnt`·`/init`·`/run`을 연결하지 않음, W2 시험)이 한다.

## 질문별 답에 대해

- **질문 7(CI):** 리뷰어가 CI 원문 로그로 격리 시험이 실제로 돌았음을 확인해 준 것을 받아들인다. 우리는 로그를 받을 수 없었다(익명 요청 403). 제안대로 CI의 전체 시험 단계에 `DML_REQUIRE_BWRAP=1`을 넣었다. 이제 bubblewrap을 못 쓰면 건너뛰지 않고 실패한다(`test_bubblewrap_is_usable_when_required`).
- **질문 8(문구):** 리뷰의 표대로 좁혔다.
  - `core/README.md`: namespace 보장은 `isolation.run()`과 그 정책에 한정한다. 입력 전달, 기록 형식, 정리 상한의 문구도 고쳤다.
  - 인계: W2는 "모델 없는 경계 시험의 완료"다.
  - 앞 경계 리뷰의 [반영 기록](../2026-09-23-wsl2-boundary/RESPONSE.md)은 날짜 기록이라 고치지 않는다. 그 R02 행의 "timeout + CLEANUP_LIMIT 안에 돌아온다"는 이 문서의 WM-07 행이 대체한다.
- **질문 9(순서):** 리뷰의 순서를 따른다. 인계 4절을 다시 짰다.
  1. 모델 없이 경계 수정 — 이 변경
  2. A1의 첫 세로 기능: 고정 입력 manifest → 시도 예약 → 가짜 CLI → 결과 수용 관문 → 초안 봉인·공개 → 카드
  3. 실제 호출 전 확인: 인증 연결 최소화 후보, controller 제어 API 인증
  4. 승인된 소수 호출: 한 번씩 읽고 다음을 정한다
  5. B3
- **질문 2(격리):** `~/.claude`와 함께 `~/.codex` 전체 쓰기 연결도 좁힐 대상으로 인계에 적었다. 중첩 user namespace는 리뷰대로 막지 않고 실제 호출에서 관측한다.
- **질문 4(정족수):** 동의한다. 명단 인원은 유효한 초안 수가 아니다. 동일 입력 digest, 수용된 초안, 공개 순서는 controller 관문이 본다(A1).
- **구조 평가:** 동의한다. 새 프레임워크나 두 번째 백엔드를 넣지 않았고, 고친 것은 모두 기존 모듈 안의 작은 검사와 결과 필드다. Windows job object 경로는 동결된 보조 경로로 둔다.

## 아직 남은 것

- controller 제어 API의 인증(읽기·쓰기 모두), 미정리 시도 상한, 결과 수용 관문(`input_delivery`, `tree_confirmed_empty`, `interpret` ok를 모두 봄) — A1.
- `~/.claude`·`~/.codex` 연결을 필요한 파일로 좁히기, Codex 중첩 샌드박스, Linux 거절 문자열, 실제 질의의 입력·토큰 갱신 — 승인된 호출(B1·B2).
- Codex 거절 흔적을 보관 상한과 무관하게 세기(경계 리뷰 R04의 남은 것).
