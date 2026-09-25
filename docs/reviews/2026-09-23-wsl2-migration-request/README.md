# 리뷰 요청 — 경계 리뷰 반영, WSL2 이전, bubblewrap 격리 (2026-09-23)

다른 AI 세션에게 이 저장소의 2026-09-23 오후 작업을 검토받기 위한 요청서다. 요청한 쪽: claude 세션(Claude Opus 5.5). 작업은 사용자 보조 PC(`aux-pc`)의 로컬 checkout에서 했고, WSL2 배포판 안의 명령은 `wsl.exe`로 실행했다. 리뷰어는 **GitHub만 볼 수 있다고 가정한다.**

## 사용자가 리뷰어에게 붙여 넣을 요청문

> 저장소 https://github.com/inlight37-design/decision-model_lab 의 `main` 브랜치에서 `docs/reviews/2026-09-23-wsl2-migration-request/README.md`를 읽고 그대로 따라 검토해 줘. 결과는 그 문서의 "결과를 남기는 방법"대로 남겨 줘. GitHub에 쓸 수 없으면 결과 전문을 답으로 줘.

## 검토 범위

- 커밋: `d0678f4785f642753b02c039b1fa6bf5622bf0ed`(앞 경계 리뷰의 기준) → 이 요청서가 병합된 `main`. GitHub compare나 `git log d0678f4..main`으로 본다.
- 앞 리뷰의 원문과 우리의 반영은 [`2026-09-23-wsl2-boundary/`](../2026-09-23-wsl2-boundary/README.md)에 있다. 이번에는 **그 반영이 맞는지, 그리고 그 뒤의 작업**을 본다.
- 사용자 PC의 상태(WSL 배포판, 설치된 CLI, 로그인)는 리뷰어가 볼 수 없다. 저장소에 옮겨 둔 기록으로만 판단하고, **기록과 다르다고 단정하지 않는다.** 의심되면 "확인 필요"로 적는다.
- 이 범위에서 **모델 호출은 한 번도 없다.** CLI는 `--version`, `--help`, 로그인 상태 명령만 실행했다.

## 한 일

| 순서 | 무엇 | 병합 커밋 | 근거 |
|---|---|---|---|
| 1 | 경계 리뷰 R01–R04 반영. runner가 추적 단위와 자손 전체를 따로 보고(`unit_confirmed_empty`, `tree_confirmed_empty`, `containment`)하고, 정리 단계에 상한(`CLEANUP_LIMIT`)을 둔다. membership은 공개 전 모든 구성 변경 뒤 정족수를 다시 보고, 단계가 한 칸씩만 간다. 출력 해석은 모양이 다르면 형식 실패, Codex stderr가 잘리면 답을 받지 않는다 | `5790316` | 각 시험 파일의 `BoundaryReviewRegressionTests`(수정 전에 실패함을 먼저 확인), [반영 기록](../2026-09-23-wsl2-boundary/RESPONSE.md) |
| 2 | 실행 명세: 질문을 stdin으로 보내고 기록에는 digest와 크기만(`adapters.build_spec`). 환경 규칙을 [`core/env.py`](../../../core/env.py)로 옮김(R05). WSL에서 Windows PATH 항목을 빼고 Windows 실행 파일을 거절 | `e598de9` | [`tests/test_core_adapters.py`](../../../tests/test_core_adapters.py)의 `ExecutionSpecTests`, [`tests/test_core_env.py`](../../../tests/test_core_env.py) |
| 3 | WSL2 설치(사용자), 공식 스크립트로 Linux Claude Code 2.1.280·Codex 0.156.1 설치, V04-01 tier 1을 새 이름표 `aux-pc-wsl`로 기록, 로그인(사용자) | `6c4a9d2`, 로그인 갱신은 4 | [`aux-pc-wsl/RESULTS.md`](../../experiments/v04-01-inventory/hosts/aux-pc-wsl/RESULTS.md), [`manifest.json`](../../experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.json) |
| 4 | bubblewrap 격리([`core/isolation.py`](../../../core/isolation.py)), runner의 `pid_namespace` 추적 단위, 모델 없는 경계 시험, CI에 bubblewrap 설치 | `03a7d2c` | [`tests/test_core_isolation.py`](../../../tests/test_core_isolation.py), [W2 기록](../../experiments/w2-isolation/aux-pc-wsl.md), [`tools/w2/cli_boundary.py`](https://github.com/inlight37-design/decision-model_lab/blob/01cedd3c05dc043465d4476aab2b1a8f547574e9/tools/w2/cli_boundary.py) |
| 5 | `env.resolve()`가 링크를 따라가 Windows 실행 파일을 거절하도록 수정 | 이 요청서와 같은 병합 | `tests/test_core_env.py` |

사용자가 정한 것: 실행 기반은 WSL2(인계 2절 15), 격리 백엔드는 bubblewrap을 먼저 시험(2절 16, 선택은 claude 세션에 맡김). 앞 리뷰는 rootless 컨테이너를 첫 후보로 들었다. 다르게 정한 이유는 반영 기록의 "리뷰와 다르게 정한 것"에 있다.

## 잘 안 된 것, 틀렸던 것

1. **인계 문서가 사실과 달랐다.** "POSIX에서 트리를 확인 못 하면 `unknown`"이라고 적었지만, 수정 전 runner는 그 경우 트리가 비었다고 보고했다(앞 리뷰 R01). 원본에서 정정 표시와 함께 고쳤다.
2. **W2의 첫 CI가 실패했다.** GitHub 러너의 python이 `/opt/hostedtoolcache` 아래에 있어서, 격리 안에서 실행할 수 없다고 `wrap()`이 거절했다. CI 로그는 저장소 관리자 권한이 있어야 받을 수 있어서(403) 읽지 못했다. 원인을 추정한 뒤 WSL에서 같은 조건(`/usr` 밖에 복사한 venv python)으로 같은 거절을 재현하고 고쳤다. 추정이 맞았다는 근거는 그 재현과 두 번째 CI 녹색뿐이다.
3. **Windows 회귀 시험이 간헐적으로 실패했다.** job을 끝낸 직후, job 회계는 0인데 끝낸 손자의 프로세스 객체가 아직 신호를 받지 않은 짧은 틈이 있었다. 반복하면 30회 중 5회였고 모두 16ms 안에 사라졌다. runner 판정은 유지하고 시험이 그 틈만큼 기다리게 했다. "job 회계가 먼저 0이 된다"는 해석은 관측에서 나온 추론이다.
4. **우리 가드의 첫 판이 틀렸다**(위 5). `resolve()`가 링크를 따라가지 않아서, Linux 이름의 링크가 `/mnt/c/.../codex.exe`를 가리키면 통과했다. 격리 쪽은 실제 경로를 보고 `/mnt/c`를 연결하지 않으므로 격리 실행은 노출되지 않았다. 이 요청서를 준비하다 찾았다.
5. **처음에는 앞 리뷰의 Linux 재현을 돌리지 못했다.** 이 PC에 WSL이 없었다. 그동안 POSIX 경로는 CI에만 기댔고, WSL 설치 뒤 배포판에서 core 시험을 돌렸다.
6. **운영상 자잘한 사고.**
   - PowerShell 5.1에서 `wsl.exe`로 넘기는 인자의 따옴표와 `$`가 깨져 명령이 여러 번 망가졌다. 스크립트 파일로 넘겨 해결했다.
   - Python `write_text`가 Windows에서 줄바꿈을 CRLF로 써서, 인계 문서의 작업 사본이 잠깐 CRLF였다. 커밋은 `.gitattributes`로 LF다.
7. **앞 리뷰의 제안 중 채택하지 않은 것.**
   - R02의 nonblocking I/O 재구성: 대신 막히는 `close()`를 없앴다.
   - rootless 컨테이너 먼저: 대신 bubblewrap을 먼저 시험했다.

## 아직 안 된 것, 모르는 것

- **모델 호출이 없었다.** 격리 안에서 실제 질문 한 번이 끝까지 도는지 모른다(토큰 갱신 쓰기, DNS·TLS, stdin의 EOF·큰 한글·선행 대시). `aux-pc-wsl` tier 2와 B1·B2는 사용자 승인을 기다린다.
- **`claude -p`가 위치 인자 없이 stdin을 질문으로 읽는다는 것**은 공식 문서의 "비대화형 모드는 stdin을 읽는다"와 파이프 예시(파이프와 인자를 함께 쓴 것)에 기댄 것이다. 설치 버전에서 관측하지 않았다. Codex `exec -`는 기록된 help에 있다.
- Codex가 들고 오는 자체 bubblewrap이 우리 bubblewrap 안에서 도는지(중첩 user namespace).
- Linux Codex가 명령을 거절할 때 stderr에 남기는 문자열. `tools_rejected` 판정은 Windows 문자열을 찾는다.
- Codex 거절 흔적을 보관 상한과 무관하게 스트림 전체에서 세기(앞 리뷰 R04의 남은 것). 지금은 stderr가 잘리면 답을 받지 않는다.
- 격리가 `~/.claude` 전체를 쓰기로 연결한다. 그래서 그 배포판에서 사용자가 대화형으로 쓴 Claude 세션 기록이 Claude 참여자에게 보인다.
- 네트워크를 공유하므로 참여자가 localhost 포트와 abstract unix 소켓에 닿는다. controller 제어 API의 토큰은 아직 없다(controller 자체가 없다). 메모리·CPU 상한도 없다.
- agy: WSL에 설치하지 않았다. stdin 입력을 확인하지 않아 질문을 명령줄로 보낸다.
- Windows 네이티브 경로: job 배정 전에 생긴 자식은 추적하지 못한다(문서화한 한계). Codex #42172 우회는 Windows 전용이다.
- CI는 AppArmor의 user namespace 제한을 sysctl로 풀고 격리 시험을 돌린다. `aux-pc-wsl`은 AppArmor가 꺼져 있다. 제한이 켜진 일반 Ubuntu에서의 운영은 보지 않았다.
- **A1(controller와 모의 화면)은 시작 전이다.** 사용자가 보고 싶어 한 화면이 아직 없다.

## 해야 할 것 — 우리 계획, 순서대로

1. (사용자 승인 뒤) `aux-pc-wsl`에서 tier 2와 B1·B2: Claude 3회 안팎, Codex 2회 안팎. 격리 안에서 실제 호출이 끝까지 도는지, 위 "모르는 것"의 앞 네 항목을 본다.
2. A1 controller와 모의 화면. 단계 관문(명단 수용·실행·공개·결과 수용을 따로 판정), 봉인 저장소(작은 SQLite journal과 파일), 예산(누적 상한과 동시 실행 자리를 나누고, 자리는 `tree_confirmed_empty`가 True일 때만 반환), 참여자에게 없는 토큰으로 막은 제어 API, 가짜 CLI.
3. A2 수동 전달, A5 manifest v2, A6 입력 manifest.
4. `~/.claude` 연결을 필요한 파일로 좁히기, 거절 흔적을 스트림 전체에서 세기.
5. B3 pilot과 사용량 비교.

자세한 것은 [`NEXT-SESSION.md`](../../../NEXT-SESSION.md) 4절이다.

## 읽는 순서

결론에 끌려가지 않도록 **코드·시험·관측을 먼저, 우리의 판정을 나중에** 읽는다.

1. [`AGENTS.md`](../../../AGENTS.md), [`docs/COLLABORATION.md`](../../COLLABORATION.md) — 이 저장소에서 여러 AI가 지키는 규칙.
2. [`NEXT-SESSION.md`](../../../NEXT-SESSION.md)의 **2절만**(15·16 포함) — 논쟁하지 않는 전제다.
3. 앞 리뷰 원문 [`REVIEW.md`](../2026-09-23-wsl2-boundary/REVIEW.md). 우리의 반영 기록은 아직 읽지 않는다.
4. 코드와 시험: [`core/`](../../../core/)의 `runner.py`, `membership.py`, `adapters.py`, `env.py`, `isolation.py`, [`tests/`](../../../tests/)의 `test_core_*.py`, [`.github/workflows/checks.yml`](../../../.github/workflows/checks.yml). **여기서 스스로 판단을 적어 둔다.**
5. 관측 기록: [`aux-pc-wsl/RESULTS.md`](../../experiments/v04-01-inventory/hosts/aux-pc-wsl/RESULTS.md)와 [`help/`](../../experiments/v04-01-inventory/hosts/aux-pc-wsl/help/), [W2 기록](../../experiments/w2-isolation/aux-pc-wsl.md), [`tools/w2/cli_boundary.py`](https://github.com/inlight37-design/decision-model_lab/blob/01cedd3c05dc043465d4476aab2b1a8f547574e9/tools/w2/cli_boundary.py).
6. 우리의 판정: [반영 기록](../2026-09-23-wsl2-boundary/RESPONSE.md), [`core/README.md`](../../../core/README.md), `NEXT-SESSION.md`의 나머지. 4·5에서 적은 판단과 비교한다.

## 검토 질문 — 중요한 순서

각 질문에 "동의 / 부분 동의 / 반대"와 근거를 적는다. 근거가 없으면 "판단 보류"라고 쓴다.

1. **PID namespace로 "자손 전체가 끝났다"를 확인하는 논리.** runner는 bwrap의 프로세스 그룹이 비면 namespace도 비었다고 본다. namespace의 첫 프로세스(bwrap의 reaper)가 그 그룹 안에 있고, 안이 빌 때까지 끝나지 않기 때문이라는 논리다.
   - 커널 동작으로 맞는가.
   - 빠져나갈 길이 있는가. 예: 호스트 데몬에 요청해 프로세스를 만들기, 공유 네트워크의 abstract 소켓, setns.
   - `runner._check_pid_namespace`가 우리 bwrap 명령만 받는 검사로 충분한가.
2. **격리 경계의 빈틈.**
   - 지금 규칙: `/etc` 전체 읽기 전용 연결, `/usr`와 병합 링크, `resolv.conf`는 대상 파일만 연결, HOME·`/tmp`는 빈 tmpfs, `--clearenv` 허용 목록, `--new-session`.
   - 참여자가 읽으면 안 되는데 읽히는 것이 있는가.
   - 중첩 user namespace를 허용한 것(`--disable-userns`를 쓰지 않음, Codex 자체 샌드박스 때문)의 위험은 무엇인가.
3. **runner 정리 상한(R02 반영).** 읽는 스레드가 스스로 스트림을 닫고, 시한 뒤에도 살아 있으면 두고 떠나는 구조다. `CLEANUP_LIMIT`가 모든 대기를 덮는가. 두고 떠난 스레드와 fd가 오래 도는 앱에서 쌓이는가.
4. **정족수(R03 반영).**
   - 공개 전에는 모든 구성 변경 뒤 다시 판정한다. 대체자는 명단에 들어가도 진행 허가가 아니다.
   - `advance()`는 한 칸씩 가고, 초안 진입과 공개에는 정족수가 필요하다. 공개 뒤의 이탈은 막지 않는다.
   - 이것이 D11·D13·D18과 맞는가.
5. **stdin 실행 명세(R06·A4).** 관측 전에 입력 경로를 바꾼 것이 위험한가(aux-pc Windows 관측은 명령줄 입력이었다). 문서 근거가 충분한가. 기록에 digest와 크기만 남기는 것으로 충분한가.
6. **WSL의 Windows 실행 파일 가드.** PATH 필터, `.exe`·`/mnt/<드라이브>` 판정, 링크 추적. 다른 우회가 있는가. 예: `binfmt_misc` interop로 확장자 없는 PE를 실행하기.
7. **CI 변경.**
   - 러너에서 AppArmor의 user namespace 제한을 sysctl로 푸는 것이 적절한가.
   - 격리 시험이 CI에서 건너뛰지 않고 실제로 돈다고 볼 근거가 충분한가. 근거는 첫 실행이 그 시험에서 실패했다는 것뿐이고, 로그는 못 읽었다.
8. **말한 것과 증거.** 반영 기록·W2 기록·인계에서 증거보다 강하게 쓴 문장이 있는가. 특히 "R01이 Linux에서 해결됐다"는 표현의 범위.
9. **다음 단계의 위험.**
   - 모델 호출 계획(횟수와 순서)이 적절한가.
   - A1에서 가장 먼저 넣어야 할 것은 무엇인가.
   - pilot 전에 빠진 위험이 있는가.

질문 밖이라도 **틀린 사실, 깨진 링크, 기록과 다른 코드**를 찾으면 적는다.

## 결과를 남기는 방법

- 새 브랜치 `<에이전트>/review-wsl2-<YYYYMMDD>`(예: `chatgpt/review-wsl2-20260924`)를 만든다.
- 리뷰는 `docs/reviews/<YYYY-MM-DD>-wsl2-migration-review/README.md`에 쓰고 PR을 연다. [PR 템플릿](../../../.github/pull_request_template.md)을 채우고, 접근 범위에는 "GitHub만"처럼 실제 범위를 적는다.
- 재현 코드를 돌렸다면 같은 폴더에 스크립트와 결과를 두고, 무엇을 어디서 실행했는지 적는다.
- 리뷰 문서의 형식:

| 절 | 내용 |
|---|---|
| 요약 | 가장 중요한 발견 세 개 이내 |
| 발견 | 번호, 심각도(높음·중간·낮음), 위치(`파일:줄` 또는 URL), 근거 등급(**관측**: 코드·기록에서 직접 확인 / **재현**: 직접 실행 / **문서**: 공식 문서 / **추론**), 내용, 제안 |
| 질문별 답 | 위 1–9에 대한 동의·부분 동의·반대·보류와 근거 |
| 확인하지 못한 것 | 접근할 수 없었거나 읽지 않은 것 |

- **명백한 오류**(오타, 깨진 링크, 기록과 다른 숫자)는 같은 PR에서 원본을 고쳐도 된다. 커밋 메시지에 무엇이 왜 틀렸는지 적는다. **판단이 갈리는 것은 고치지 말고 리뷰에만 적는다.** 사용자와 다음 세션이 판단한다.
- 근거 원장(`sources.json`)에는 1차 출처를 직접 읽은 경우만 항목을 추가한다. 리뷰 안의 참조 번호는 원장 번호가 아니다.
- 살아 있는 문서에 검사 수·원장 건수를 적지 않는다(CI가 막는다). `NEXT-SESSION.md`는 절 구성을 유지한 채 3절에 리뷰 브랜치를 적는다.
- 병합은 하지 않는다. 사용자 또는 claude 세션이 CI를 확인한 뒤 병합한다.

## 이미 알고 있는 한계

리뷰어가 같은 지적을 반복하지 않도록 적어 둔다. 다르게 판단하면 그 근거를 적는다.

- 모든 관측은 **보조 PC 한 대와 그 안의 WSL 배포판 하나, 2026-09-23 하루**의 결과다.
- 모델 호출이 없다. 격리 시험은 python 탐침과, CLI의 `--version`·로그인 상태까지다.
- CI 로그를 읽을 수 없다. CI 쪽 결과는 작업 단위의 성공·실패만 본다.
- 공식 문서는 WebFetch로 읽었다.
  - Claude의 sandbox·headless 문서는 전문을 받아 해당 문장을 찾았다.
  - Codex 설정 문서는 요약만 받았다. 권한 프로필의 `"deny"`는 요약에 있었고, `requirements.toml`의 `deny_read`는 찾지 못했다.
- 계정 이메일·조직 ID·요금제는 기록하지 않는다. 로그인 여부와 방식만 남긴다.
