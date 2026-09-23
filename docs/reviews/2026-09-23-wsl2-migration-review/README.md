# WSL2 전환 재검토와 실행 코어 간결성 검토

작성: ChatGPT · GPT-6 Astra Pro · 2026-09-23  
검토 기준: `main`의 **`a662e59b0541ea747c50be4b388af9a61dd02b84`**. 아래 코드 줄 번호는 모두 이 SHA 기준이다.  
요청: [검토 요청서](../2026-09-23-wsl2-migration-request/README.md). 브랜치: `chatgpt/review-wsl2-20260923`.

접근 범위는 **GitHub와 별도의 웹 Linux 컨테이너**다. 사용자 PC, `aux-pc-wsl`, 설치된 Claude·Codex에는 접근하지 않았다. 실제 모델 호출, 로그인 변경, 사용자 설정 변경, 운영 코드 수정은 하지 않았다. 기존 코드·시험을 먼저 평가한 뒤 작성자의 RESPONSE와 core README를 대조했다. 초기 인계 탐색에서 상태 설명도 일부 읽었으므로 완전한 맹검 리뷰라고 주장하지 않는다.

## 요약

1. **WSL2 + bubblewrap 방향과 작은 표준 라이브러리 코어는 유지할 만하다. 전면 재설계나 두 번째 격리 백엔드 도입을 권하지 않는다.** 환경·격리·프로세스·CLI 해석·명단을 나눈 경계가 적절하다. 다만 코드가 짧다는 것과 실패를 정확히 처리한다는 것은 다르다. 입력 전송 실패를 버리는 코드, 이름과 플래그만으로 격리를 인정하는 코드가 핵심 결함이다.
2. **실제 모델 pilot 전에 입력 전달과 비밀정보 경로부터 고쳐야 한다.** 합성 CLI가 1,680,000바이트 중 1바이트만 읽고 stdin을 닫았는데도 답이 `ok`로 해석됐다. 별도로 허용 환경변수의 OAuth 토큰 값이 bubblewrap argv에 들어가는 경로를 확인했다. 전자는 직접 재현했고 후자는 가짜 값으로 명령 조립만 재현했다. 실제 Claude 입력 손실이나 실제 토큰 유출을 관측한 것은 아니다.
3. **W2의 긍정적 증거는 인정하되 보장 범위를 좁혀야 한다.** 이번에는 현재 기준 SHA의 CI 원문 로그를 읽었다. 실제 bubblewrap 격리 시험은 skip이 아니라 실행되어 성공했다. 그러나 이것은 임의의 호출 인자, 모든 설정 조합, WSL의 실제 모델 호출까지 증명하지 않는다. 일반 POSIX 실행과 검증된 bubblewrap 실행을 구별해야 한다.

판정: **모의 controller 개발은 진행 가능. 현재 코드를 그대로 연결한 실제 협업 pilot은 보류.** 아래 수정과 실행 허가 관문을 먼저 넣고, 승인된 소수의 CLI 관측을 한 번씩 진행한다.

## 검증 범위와 증거

### 직접 읽은 것

`AGENTS.md`, `docs/COLLABORATION.md`, 요청서, 이전 경계 REVIEW/RESPONSE, 현재 `core/*.py`와 `tests/test_core_*.py`, workflow, WSL 설치·W2 관측 기록, 설치 버전의 Claude/Codex help, `tools/w2/cli_boundary.py`, `core/README.md`, `NEXT-SESSION.md`, v0.4 아키텍처의 실행 원칙과 D11·D13·D18을 대조했다. 전체 저장소의 모든 과거 실험 도구와 UI를 한 줄씩 감사한 것은 아니다.

### 직접 재현한 것

[reproduce.py](reproduce.py)와 [results.json](results.json)을 함께 둔다. Linux 6.18.44 / Python 3.13.5의 웹 컨테이너에서 실행했다. 이 환경에는 실제 bwrap이 없었다. GitHub에서 읽어 옮긴 네 코어 파일의 **Git blob SHA가 원본과 정확히 같은지 검사한 뒤** 실행했다. 저장소 전체를 clone하여 전체 시험을 로컬에서 돌린 것은 아니다.

재현 스크립트는 네 원본 파일의 해시가 다르면 중단한다. 임시 파일, 가짜 CLI, 이 스크립트가 만든 자손만 사용한다. 자손 정리는 스크립트가 직접 생성한 PID에 한정하며, 관측 후 모두 종료·회수했다. 네트워크·모델·실제 bwrap은 호출하지 않는다. 스크립트 종료 코드 0은 **관측 절차 완료**이지 결함이 수정됐다는 뜻이 아니다.

검토 브랜치의 파일을 받은 뒤 기준 코드를 별도 worktree에 준비하는 예:

```bash
git worktree add --detach /tmp/dml-wsl2-review-base a662e59b0541ea747c50be4b388af9a61dd02b84
python docs/reviews/2026-09-23-wsl2-migration-review/reproduce.py \
  --repo /tmp/dml-wsl2-review-base --output /tmp/dml-wsl2-review-results.json
```

기준 코드가 나중에 수정돼도 결과를 새 코드의 관측으로 오인하지 않도록 해시를 고정했다. 수정 후 회귀 시험은 별도로 만들고, 이 재현 기록은 덮어쓰지 않는 것이 좋다.

### CI에서 확인한 것

[기준 SHA의 실행 로그](https://github.com/inlight37-design/decision-model_lab/actions/runs/35842786253/job/107121610973)를 직접 읽었다. 검토 브랜치를 기준 SHA에서 만들면서 실행된 job이며 아직 리뷰 파일을 추가하기 전 코드다. Ubuntu 24.04.5 / Python 3.13.15 / bubblewrap 0.9.0-1ubuntu0.3에서 다음 시험이 `ok`였다.

```text
test_a_detached_descendant_ends_with_the_namespace ... ok
test_only_what_was_granted_is_visible ... ok
test_timeout_ends_everything_inside ... ok
Ran 212 tests in 9.906s
OK (skipped=1)
```

유일한 skip은 `test_registry_environment_reads_both_scopes`의 `Windows registry only`였다. 따라서 **이 실행에서는 격리 시험이 실제로 돌았다.** Python 3.12 job도 성공 상태를 확인했지만, 위 상세 수치와 시험별 확인은 3.13 원문 로그 기준이다. 이 고정 기록을 이후 리뷰 PR의 최종 CI 상태와 혼동하지 않는다.

## 발견

등급: **관측**은 코드·저장된 기록에서 직접 확인, **재현**은 이번에 직접 실행, **문서**는 직접 읽은 1차 문서, **추론**은 그로부터의 판단이다. 심각도는 실제 실행 코어로 연결했을 때의 영향 기준이며, 아직 사용자 운영 사고가 있었다는 뜻이 아니다.

### WM-01 · 높음 — stdin 전송 실패가 결과에 남지 않는다

**위치:** `core/runner.py:150–160, 286–288`; `core/adapters.py:216–234, 249–253`.  
**근거:** 관측 + 재현 (`stdin_early_close`).

`_write_stdin()`은 `BrokenPipeError`와 `OSError`를 버리고, 쓰기 스레드의 완료·실패를 결과에 연결하지 않는다. 가짜 CLI가 큰 입력의 1바이트만 읽고 fd 0을 닫은 뒤 유효한 Claude 모양의 JSON을 출력하도록 했다. 결과는 `state=exited`, `exit_code=0`, `notes=[]`, `Outcome.ok=True`였다. 의도한 입력은 1,680,000바이트, 관측한 pipe 용량은 65,536바이트여서 전체 입력을 파이프가 미리 받아 두었을 가능성으로 설명할 수 없다.

이 시험의 `tree_confirmed_empty`는 일반 POSIX 경로이므로 `None`이다. 따라서 완성된 controller가 실제 예산을 잘못 반환했다고 주장하지 않는다. 문제는 **입력이 누락됐다는 사실이 runner/adapter 경계에서 사라진다**는 것이다. 진짜 namespace로 자손 종료를 확인해도 이 입력 문제는 별개다.

**제안:** 문자열 검증·인코딩을 프로세스 생성 전에 끝내고, 쓰기 완료/전송 오류/아직 쓰는 중을 추적하는 작은 결과 필드를 둔다. 알려진 전송 실패 뒤에는 출력이 그럴듯해도 결과 수용을 막는다. `exited`라는 프로세스 사실을 지우기보다 입력 전달 상태를 별도로 보존한다. 전체 쓰기 성공도 CLI가 의미상 전부 사용했다는 증거는 아니므로 실제 버전 관측은 여전히 필요하다. 실패했다고 자동 재호출하거나 이미 쓴 호출 예산을 환급하지 않는다.

### WM-02 · 높음 — 허용한 OAuth 값이 bwrap argv에 들어간다

**위치:** `core/isolation.py:33–34, 110–114`; `core/runner.py:335–337`; `core/adapters.py:85–99`.  
**근거:** 관측 + 명령 조립 재현 (`oauth_in_argv`, `spec_log_projection`).

`PASS_ENV`에는 `CLAUDE_CODE_OAUTH_TOKEN`이 있고, 환경 허용 목록의 모든 값은 `--setenv 이름 값`으로 argv에 펼쳐진다. 가짜 토큰 값이 실제 반환 argv에 포함되는 것을 확인했다. runner도 실행 argv를 결과에 보존한다. 이 경로를 사용하면 호스트 명령행·프로세스 진단 및 결과 직렬화에 비밀이 들어갈 수 있다. W2 스크립트는 LANG/NO_COLOR만 넘겼으므로 **현재 W2 실행에서 실제 토큰이 노출됐다고 주장하지 않는다.**

또한 `ExecutionSpec`의 `repr()`와 `dataclasses.asdict()`에는 질문 본문이 들어간다. 이는 즉시 발생한 로그 유출이 아니라, “기록에는 digest와 크기만”이라는 정책을 강제하는 출력 형식이 아직 없다는 확인이다.

**제안:** 최소 변경은 토큰 환경변수의 argv 전달을 지원하지 않고 명시적으로 거절하는 것이다. 현재 구독 로그인에 필요한 인증 파일 경로를 우선 사용한다. 정말 환경 토큰이 필요할 때만 비밀값을 명령행에 싣지 않는 전달 방법을 별도로 검증한다. 로그 마스킹만으로 `/proc` 명령행 노출 문제는 해결되지 않는다. 실행 객체와 기록용 객체를 구분하고, 기록용 함수는 승인된 메타데이터만 반환한다. `repr=False`는 보조책이며 `asdict()`까지 안전하게 만들지는 않는다.

### WM-03 · 중간 — `pid_namespace=True`의 근거가 이름과 플래그 검사뿐이다

**위치:** `core/runner.py:236–243, 249–258`; `core/isolation.py:88–89`.  
**근거:** 관측 + 재현 (`pid_namespace_provenance`).

`_check_pid_namespace()`는 basename이 `bwrap`인지와 몇 플래그의 존재만 본다. 같은 이름의 가짜 Python 실행 파일이 옵션을 무시하고 자손을 새 세션으로 분리하도록 만들었다. 실제 bwrap을 사용하지 않았는데도 `containment=pid_namespace`, `tree_confirmed_empty=True`가 반환됐고 자손은 살아 있었다. 관측 후 해당 자손을 종료·회수했다.

이는 **진짜 bubblewrap 내부에서 탈출했다는 결과가 아니다.** 신뢰한 controller가 잘못된 실행 파일이나 실행 인자를 넘겼을 때, API가 보장을 과하게 부여한다는 호출 경계의 결함이다.

**제안:** 임의 argv에 공개 boolean을 붙이는 대신, 신뢰한 절대 경로의 bwrap과 검증된 정책으로만 실행하는 단일 진입점을 만든다. `isolation.run(...)` 같은 작은 함수로 조립과 실행을 묶으면 충분하다. 내부 구조체만 도입했다고 Python 호출자를 상대로 보안 경계가 생기는 것은 아니다. 호스트의 신뢰한 실행 파일, 설정 소유권, 실제 격리 경로를 확인해야 한다. 일반 runner 결과에는 namespace 보장을 붙이지 않는다.

### WM-04 · 중간 — work/HOME/읽기 전용 입력의 충돌을 허용한다

**위치:** `core/isolation.py:91–109`.  
**근거:** 관측 + 명령 조립 재현; 실제 마운트 결과는 추론 (`overlap_plan`).

`work_dir == home` 또는 `work_dir == read_only 입력`이 거절되지 않는다. HOME tmpfs와 읽기 전용 마운트를 만든 뒤 마지막 `--bind work_dir work_dir`를 추가한다. “HOME 자체를 writable로 연결하지 않는다”는 검사는 `read_write` 목록에만 적용되고 work에는 적용되지 않는다. 결과적으로 의도한 경계와 충돌하는 마운트 계획을 생성한다.

이번 컨테이너에서는 실제 bwrap이 없어 호스트 HOME 노출이나 입력 쓰기를 실행으로 재현하지 않았다. **위험한 계획이 허용된 사실과 최종 마운트의 효과를 구분한다.**

**제안:** 실행 전 canonical 경로와 역할을 검증한다. work, 봉인 저장소, HOME 보호 범위, 변경 불가 입력 사이의 충돌과 symlink 별칭을 거절한다. 단, 모든 부모·자식 마운트 중첩을 일괄 금지하면 안 된다. 현재 Codex의 RW 설정 폴더 안에 실행 버전 디렉터리를 RO로 덮는 구조는 의도된 중첩이다. 이런 허용 예외만 명시하고 실제 bwrap 회귀 시험으로 고정한다. 존재 검사 이후 파일이 교체되는 경쟁까지 문자열 검사만으로 해결됐다고 말하지 않는다.

### WM-05 · 중간 — 자식 PATH가 비면 부모 PATH로 되돌아간다

**위치:** `core/env.py:105–106, 111–119`.  
**근거:** 관측 + 재현 (`empty_path_fallback`) + Python 문서 S3.

`env.get("PATH") or env.get("Path")`는 명시적인 빈 PATH를 `None`으로 바꾼다. `shutil.which(..., path=None)`는 현재 프로세스 PATH를 사용한다. 자식 PATH를 빈 문자열로 주고 부모 PATH에만 합성 실행 파일을 놓았을 때 해당 파일을 찾아냈다. Windows 항목을 모두 제거한 뒤에도 이 조건이 생길 수 있다.

**제안:** “키 없음”과 “빈 문자열”을 구분한다. 빈 PATH는 그대로 유지하고, 누락은 명시적인 안전 기본값 또는 거절로 처리한다. POSIX에서 `PATH`와 `Path`를 같은 설정으로 취급할지도 분명히 한다. 기존 확장자·실제 경로 검사는 유지하되 이것만으로 실행 파일의 형식이나 interop 차단을 증명하지 않는다.

### WM-06 · 중간 — 파서의 형식 오류 경계가 완전하지 않다

**위치:** `core/adapters.py:208–234, 244–252, 261–267`.  
**근거:** 관측 + 재현 (`deep_json`, `falsy_wrong_shapes`).

이전 R04의 예시는 고쳤다. 그러나 20,057바이트의 유효한 JSON에 깊게 중첩된 추가 값을 넣으면 `RecursionError`가 `interpret()` 밖으로 나왔다. 빈 배열 `modelUsage=[]`와 객체 `permission_denials={}`도 `or {}`/`or []` 때문에 정상처럼 받아들여졌다. 크기가 작은 잘못된 출력도 controller 예외가 되거나 “관측 없음”으로 축약될 수 있다.

**제안:** 필수 중첩 필드의 타입을 직접 확인하고 빈 값과 잘못된 타입을 구분한다. JSON 파싱의 예상 가능한 깊이 오류도 `format_error`로 반환한다. 출력 크기 상한과 의미 필드 검사를 유지한다. 전체 함수를 무차별 `except Exception`으로 덮거나 큰 검증 프레임워크를 추가할 필요는 없다.

### WM-07 · 중간 — R02의 반환 제한은 개선됐지만 잔류 자원 제한은 아니다

**위치:** `core/runner.py:125–144, 286–288, 314–327`; 경계 RESPONSE의 R02 행.  
**근거:** 관측 + 재현 (`retained_output_readers`) + Python 문서 S4.

일반 POSIX 경로에서 분리된 자손이 stdout/stderr를 계속 쥐게 하면 새 runner는 실제로 반환한다. 이전의 동기 close 정지 문제를 고친 점은 인정한다. 다만 두 번 실행 후 외부 정리 전까지 읽기 스레드 4개와 fd 4개가 남았다. 합성 자손들을 종료하자 모두 사라졌다. **영구 누수라고 단정할 수는 없지만, EOF가 오지 않는 반복 UNKNOWN 실행은 자원을 누적시킨다.** 진짜 bwrap 경로에서 이 누적을 재현한 것은 아니다.

쓰기 스레드도 별도 완료 추적이 없다(WM-01). 또한 Python 문서상 프로세스 생성 자체는 많은 플랫폼에서 즉시 중단할 수 없으므로, `timeout + CLEANUP_LIMIT`를 모든 운영체제 상황에 대한 엄밀한 벽시계 보장으로 쓰면 안 된다.

**제안:** controller는 UNKNOWN을 완료나 재실행 허가로 취급하지 않고, 잔류 I/O까지 포함한 정리 상태를 추적해야 한다. 미정리 시도의 수를 제한하고 안전하게 멈춘다. 운영 경로를 검증된 bwrap으로 한정한 뒤에도 필요하면 POSIX 비차단 I/O 또는 짧게 사는 시도별 감독 프로세스로 수명 소유권을 명확히 한다. Windows까지 통째로 다시 쓰는 것보다 범위를 좁히는 편이 낫다. 문구는 “프로세스 생성 후 명시적 정리 대기에는 상한이 있다”로 한정한다.

## 질문별 답

### 1. PID namespace 종료 논리 — 부분 동의

커널의 PID namespace init 종료 시 내부 프로세스를 SIGKILL하는 원리는 맞다(S1). 새 세션을 만드는 것만으로 PID namespace를 벗어나지는 않는다. PID `setns`로 상위 namespace에 올라갈 수도 없다. 실제 bwrap의 reaper/감독 경로를 신뢰하고 그 수명이 추적 단위에 묶여 있다는 전제가 필요하다. W2와 현재 CI는 분리 자손·timeout의 실제 증거를 제공한다.

그러나 프로세스 그룹이 비었다는 사실 자체가 일반적인 namespace 증명은 아니다. WM-03 때문에 현재 공개 API 전체에 보장을 확장하는 데는 반대한다. 호스트 데몬이나 TCP/abstract socket 서비스에 요청해 만들어진 작업은 namespace 자손이 아니므로 종료 보장 밖이다. 제어 API 인증은 읽기·쓰기 모두 적용하고, 참여자가 접근 가능한 무인증 호스트 실행 브로커가 없는지 별도 확인해야 한다. 실제 bwrap의 모든 종료 분기와 커널 구현을 형식 검증한 것은 아니다.

### 2. 격리 경계 — 부분 동의

빈 루트에 필요한 것을 연결하고 HOME·tmp를 분리하는 방향은 적절하다. symlink 대상이 미마운트이면 읽을 수 없다는 W2 시험도 의미 있다. 다만 `/etc` 전체 RO는 “쓰기 불가”이지 “민감한 설정 읽기 불가”가 아니며 `/usr` 전체 역시 신뢰 범위에 포함된다. `resolv.conf`는 대상 파일 하나만 연결하는 것이 전체 `/mnt` 연결보다 낫지만 대상 경로·용도를 진단 결과에 남겨야 한다.

WM-02·WM-04를 먼저 고친다. 기존에 인정한 `~/.claude` 전체 노출 외에 `~/.codex` 전체 RW도 같은 방식으로 검토한다. 이전 세션, 지시문, 플러그인·소켓과 수정 가능한 실행 설치 영역이 어디까지 보이는지 역할별로 구분한다. 동일 CLI의 개인 기록과 이번 시도의 독립 자료를 혼동하지 않는다. 인증 갱신 때문에 쓰기가 필요하다는 사실이 전체 설정 폴더 쓰기를 영구 승인하는 근거는 아니다.

중첩 user namespace를 허용한다고 곧바로 호스트 권한이 생기는 것은 아니다. 반대로 불필요한 커널 기능 노출을 줄이는 방어도 아직 없다. Codex 자체 sandbox와 충돌할 수 있으므로 `--disable-userns`를 무작정 추가하지 말고 중첩 실행을 관측한다(S2). 공유 네트워크·CPU/메모리 무제한은 이미 문서화된 제약이며 신규 탈출 발견으로 세지 않는다.

### 3. 정리 상한 — 부분 동의

reader가 EOF에서 닫고 join 대기를 공유한 것은 실질적인 수정이다. 이전 R02의 반환 정지는 현재 재현에서 발생하지 않았다. 다만 WM-07처럼 반환, 자손 종료, I/O 정리 완료는 다른 상태다. UNKNOWN이 계속 생길 때 새 시도를 계속 만드는 앱은 허용하지 않는다. 프로세스 생성과 운영체제의 모든 지연까지 포함한 하드 실시간 보장에는 동의하지 않는다(S4).

### 4. 정족수와 D11·D13·D18 — 동의, 책임 범위 한정

공개 전 구성 변경에 공통 정족수 판정을 적용하고 대체자 수용과 진행 허가를 구분한 수정은 타당하다. 이전 R03, 취소 미확인, 단계 건너뛰기 회귀 시험도 있다. 공개 후 이탈로 이미 공개한 독립 초안을 없던 것으로 만들지 않는 방향 역시 맞다.

단, 명단의 인원 수는 유효한 초안 수가 아니다. D11의 공개 관문은 동일 입력 digest, 완료·수용된 초안, 공개 순서를 controller가 확인해야 한다. D13의 누적 호출·재시도 한도는 정족수와 별도다. D18은 대체·축소의 사전 허가와 표시를 요구한다. 모델 상실을 유료 fallback으로 바꾸지 않는 현재 방향을 유지한다. 이것들을 membership에 모두 넣어 거대 상태 기계로 만들 필요는 없다.

### 5. stdin 실행 명세 — 부분 동의

옵션과 질문 데이터를 분리한 것은 개선이다. 저장된 Codex 0.156.1 `exec --help`는 `-`와 stdin을 설명한다. Claude 공식 문서도 비대화형 stdin 및 입력 상한을 설명한다(S5). 따라서 구현 후보로 옮긴 것 자체가 잘못은 아니다. 하지만 Windows의 argv 관측을 WSL stdin conformance로 승격할 수는 없다.

digest와 크기는 **보내려던 자료의 식별자**다. 전송 성공, 실제 CLI 수신, 로그 비노출의 증거는 아니다(WM-01·WM-02). 실제 모델 호출 전에 큰 한글·EOF·선행 대시·전송 오류를 가짜 CLI로 먼저 시험한다. 그 뒤 설치 버전에서 소수의 실제 관측으로 의미를 확인한다. agy는 여전히 argv라는 예외가 있으므로 모든 실행의 argv가 안전하다고 쓰지 않는다.

### 6. Windows 실행 파일 가드 — 부분 동의

기본 `/mnt/<드라이브>`와 `.exe`, realpath 검사는 흔한 실수를 막는다. 그러나 명시적인 빈 PATH가 부모로 돌아가는 WM-05는 수정해야 한다. 확장자 없는 PE, 다른 위치에 복사한 파일, Linux 래퍼가 다시 interop를 호출하는 경우, 사용자 지정 automount root까지 문자열 분류가 보장하지는 않는다. Microsoft 문서에서 interop 활성화와 Windows PATH 추가는 별도 설정이며 automount root도 바꿀 수 있다(S6).

실제 extensionless PE의 WSL 실행은 이번에 재현하지 않았다. 이를 “확인된 탈출”로 쓰지 않는다. 파일 형식/승인된 설치 위치 확인, bwrap 내부 `/init`·interop socket 부재를 함께 보는 편이 낫다. 사용자의 WSL 전역 interop를 리뷰 도중 바꾸지는 않는다.

### 7. CI와 AppArmor — 현재 실행 증거에는 동의, 일반화에는 부분 동의

현재 SHA에서 격리 시험이 실제로 실행됐다는 근거는 충분하다. 첫 실패를 통한 추정뿐이라는 요청서의 정보는 이번 원문 로그 확인으로 보완됐다. 이는 과거 작성자가 거짓말했다는 정정이 아니라 이후 확보한 추가 증거다.

일회성 CI에서 **해당 user namespace 제한만** 완화해 기준 동작을 검사하는 것은 수용 가능하다. 이를 “AppArmor 전체 해제”라고 부르면 부정확하다. 다만 AppArmor 제한이 켜진 일반 Ubuntu에서 운영 검증을 했다는 뜻도 아니다. 현재 성공한 설정을 사용자의 PC에 무조건 적용하라고 권하지 않는다. 향후 CI에서 bwrap이 불가능해지면 skip으로 녹색이 되지 않도록 전용 required 모드나 skip 수 검증을 넣는 것이 작은 보강이다. 현재 실행을 skip 통과라고 지적하지 않는다.

### 8. 주장과 증거 — 부분 동의

기존 문서는 설치·로그인·모델 호출의 차이를 상당히 정직하게 구분한다. 다음 문구는 범위를 더 좁히는 것이 좋다.

| 현재 표현/위치 | 권장 범위 |
|---|---|
| `core/README.md`, NEXT W2의 `pid_namespace=True`면 자손 전체 종료 확인 | 검증된 bwrap 실행 경로와 정책에 한정. 임의 호출 인자와 외부 브로커의 작업은 제외(WM-03) |
| RESPONSE R02의 `timeout + CLEANUP_LIMIT` 안 반환 | 생성 후 명시적 대기의 상한이며 잔류 스레드/운영체제 지연까지 해결한 보장은 아님(WM-07) |
| `adapters.py`의 잘못된 중첩 타입은 형식 실패 | 현재 회귀 예시는 처리하지만 깊이 오류·일부 빈 오타 타입은 남음(WM-06) |
| 실행 명세의 기록에는 digest와 크기만 | 기록 정책이며 아직 안전한 직렬화 API로 강제되지 않음(WM-02) |
| W2 끝 | 합성 파일·수명·CLI 시작/로그인 상태 시험의 완료. 실제 질의·blind 독립성·중첩 sandbox 전체 완료는 아님 |

`tools/w2/cli_boundary.py`의 `version_state`·`status_state`는 프로세스 상태이고 exit code와 같지 않다. 이 진단을 자동 실행 허가로 사용할 때는 각 probe의 exit code, 형식 검증, 종료 확인도 저장해야 한다. 현재의 수동 관측 표가 틀렸다는 증거는 아니다. 이 PR은 판단이 필요한 원본 문장을 일괄 수정하지 않고 검토 결과로 남긴다.

### 9. 다음 순서 — 부분 동의, 호출 전 작업 순서는 수정 권고

Claude 약 3회·Codex 약 2회는 첫 smoke 관측 예산으로 합리적이나 모든 conformance 항목을 증명하는 수는 아니다. 수를 채우기 위해 실패 뒤 계속 호출하지 않는다. 같은 한 번의 호출에서 stdin, 출력 형식, 종료, 허용 자료를 함께 관측하도록 하고, 실패 시 해당 provider를 멈춰 원인을 먼저 분석한다.

요청서의 “실제 호출 → A1 → 입력 manifest → 인증 폴더 축소” 순서보다 다음이 안전하고 덜 낭비적이다.

1. **모델 없이:** WM-01·02, 실행/마운트/PATH 검증과 파서 경계를 고치고 합성 회귀 시험을 넣는다. 현재 실제 bwrap 회귀 시험은 유지한다.
2. **A1의 첫 세로 기능:** 고정 입력 manifest → 시도 예약 → 가짜 CLI 실행 → 결과 수용 관문 → 초안 봉인/공개 → 카드 표시. 입력 digest와 불완전 실행 차단은 A6/A5 문서 완성 뒤로 미루지 않는다. 전체 manifest 체계를 한꺼번에 구현할 필요는 없다.
3. **실제 호출 전:** 최소 인증 마운트 후보, controller API 권한, 설치/로그인/transport 관측의 유효성을 확정한다. 인증 폴더 축소의 실제 호환성은 승인된 호출에서 확인하되, 개인 세션 전체를 계속 노출한 상태를 blind 검증 완료로 부르지 않는다.
4. **승인된 소수 호출:** B1/B2를 한 번씩 읽고 다음 호출 여부를 결정한다. 중첩 Codex sandbox가 실패하면 우회 플래그나 다른 백엔드로 조용히 바꾸지 않는다.
5. **그 뒤 B3:** 동일 문제의 직접 사용·single·cross_check 비교. 호출 수/토큰/시간과 공급자가 보이는 구독 잔여를 구별하고, 모델 동의 자체를 검증 성공으로 세지 않는다.

A1에서 가장 먼저 필요한 것은 화면 장식이 아니라 **상태를 소유하는 한 controller와 결과 수용 관문**이다. 이미 NEXT에 있는 누적 호출 예산과 동시 실행 자리의 분리, UNKNOWN 미반환, 초안 봉인은 유지한다. pilot 전 추가 시험으로 controller 중단/재시작, 취소 중 입력 전송, 누락·중복·늦게 온 결과, 제어 API의 인증 실패, 마운트 충돌을 포함한다. 메모리·프로세스 수 무제한은 의도적 제한으로 표시하고, 최소 동시 실행 상한 없이 장시간 운용하지 않는다.

## 추가 요청: 구조와 코드가 필요한 만큼만 있는가

**핵심 코어는 대체로 그렇다. 모든 것을 뜯어고칠 상태는 아니다.** 다섯 모듈은 서로 다른 실패 책임을 가진다. `env`를 tools에서 core로 옮겨 의존 방향을 바로잡은 것, membership의 공통 정족수 함수, native CLI를 그대로 사용하는 exec 중심 구조는 유지한다. runner가 인증·모델 의미까지 판단하지 않고 adapter가 파일 격리까지 책임지지 않는 것도 적절하다.

현재 부족한 것은 추상화의 수가 아니라 **몇 개의 경계 계약**이다. `except ...: pass`로 입력 오류를 버리고, `or {}`로 잘못된 타입을 정상 빈 값으로 바꾸고, boolean 하나로 격리 보장을 추가하는 코드는 짧지만 중요한 상태를 잃는다. 각각 좁은 검증 함수와 결과 필드로 고칠 수 있다.

첫 앱에는 한 Python controller, 작은 SQLite journal과 봉인 파일, 검증된 bwrap 진입점, 읽기 전용 adapter, 얇은 화면이면 충분하다. ACP·MCP 관리 프레임워크·분산 작업 큐·두 번째 컨테이너 백엔드·범용 플러그인 로더를 먼저 만들 이유는 이번 검토에서 찾지 못했다. 기존 v0.4 아키텍처도 논리적 모듈을 microservice 목록으로 해석하지 말라고 명시한다.

Windows job object 경로는 동결된 보조 경로로 두고 신규 제품 기능을 양쪽에 계속 복제하지 않는다. 지금 바로 삭제할 필요도 없다. 역사적 리뷰/실험 코드는 재현 자료이므로 운영 코드 중복과 구별한다. 다만 앞으로 controller에서 `tools/review_boundary.py`를 그대로 가져와 두 번째 상태 권위로 삼지는 않는다.

문서는 현재 상태와 과거 관측이 NEXT에 많이 반복돼 읽는 비용이 크다. 이 PR에서는 요구된 고정 절을 유지하고 3절만 갱신한다. 이후에는 과거 측정값을 관측 문서에, 현재 해야 할 일을 인계에 두고 링크로 연결하는 정도의 정리가 적절하다. 또 하나의 대형 설계 문서를 추가하는 대신 이번 발견을 작은 수정 PR과 회귀 시험으로 닫는 것이 좋다.

## 이전 R01–R06 반영의 재판정

| 항목 | 이번 판정 |
|---|---|
| R01 프로세스 그룹을 전체 자손으로 오인 | 일반 POSIX의 `None` 분리는 적절. 실제 bwrap 시험의 성공도 인정. 보장 부여 API는 WM-03 보강 필요 |
| R02 정리 반환 정지 | 기존 시나리오에서 반환하도록 개선. 잔류 I/O와 엄밀한 시간 문구는 WM-07 |
| R03 정족수 | 수정과 확장에 동의. 완료 초안/호출 한도는 controller 책임 |
| R04 파서 예외·stderr 절단 | 기존 회귀 수정은 인정. 새 형식 반례는 WM-06. stderr 절단 시 수용 거절은 보수적으로 유지 가능 |
| R05 core→tools 역의존 | 분리 방향에 동의. 큰 모듈 재편 불필요 |
| R06 질문을 argv로 전송 | stdin 방향은 적절. 전달 상태와 기록 정책의 실제 강제가 WM-01·02로 남음 |

## 확인하지 못한 것

사용자 WSL에서 실제 bwrap을 다시 실행하지 않았고, 실제 Claude/Codex 질의, 토큰 갱신, DNS/TLS를 통한 모델 요청, nested Codex sandbox, Linux 거절 문자열, extensionless PE/interop, 장시간 부하, AppArmor 제한이 켜진 다른 배포판은 직접 확인하지 못했다. 이전 Windows Job Object 시험도 재실행하지 않았다. 코드의 모든 경쟁 상태, 모든 syscall, bwrap C 구현 전체에 대한 완전한 보안 증명은 하지 않았다.

설치 기록과 help는 읽었지만 `aux-pc-wsl/manifest.json`의 전체 필드를 별도로 재검증하지 않았다. 전체 로컬 test suite를 실행한 것이 아니라 정확한 네 코어 파일에 합성 탐침을 실행했고, 전체 suite의 실행은 GitHub Actions 원문 로그로 확인했다. 아직 없는 controller/실제 UI의 기능·성능을 시험했다고 주장하지 않는다.

## 직접 확인한 외부 근거

아래 S 번호는 이 리뷰의 참고 번호이며 저장소 근거 원장의 E/F 번호가 아니다. 열람일은 2026-09-23이다. 설치 버전의 동작은 저장소 help/관측과 구별한다.

- **S1:** [Linux man-pages — pid_namespaces(7)](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html), init 종료·중첩 PID namespace·setns 설명. Q1의 커널 원리만 뒷받침하며 이 프로젝트의 호출 검증을 대신하지 않는다.
- **S2:** [bubblewrap v0.9.0 README](https://github.com/containers/bubblewrap/blob/v0.9.0/README.md), Sandbox security/Limitations. 정책은 호출자가 결정하며 노출한 소켓과 중첩 앱 sandbox를 주의해야 한다.
- **S3:** [Python shutil.which](https://docs.python.org/3/library/shutil.html#shutil.which), path 생략 시 프로세스 PATH 사용. WM-05는 별도로 Python 3.13.5에서 재현했다.
- **S4:** [Python subprocess](https://docs.python.org/3/library/subprocess.html), timeout과 프로세스 생성 중단의 한계. WM-07의 하드 벽시계 보장 범위에 사용했다.
- **S5:** [Claude Code — Run programmatically](https://code.claude.com/docs/en/headless), 비대화형 stdin과 입력 상한. 현재 문서의 설명을 설치 버전의 구독 호출 성공으로 취급하지 않았다.
- **S6:** [Microsoft — Advanced settings configuration in WSL](https://learn.microsoft.com/en-us/windows/wsl/wsl-config), automount root와 interop/appendWindowsPath 설정. 경로 필터와 interop 차단을 구별하는 근거다.
