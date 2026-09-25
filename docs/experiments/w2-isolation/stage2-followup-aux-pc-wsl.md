# 2단계 후속 — Codex 명령이 닿는 곳과 권한 profile 시험, `aux-pc-wsl`

2026-09-24 · claude 세션(Claude Opus 5.5, aux-pc의 로컬 checkout, `wsl.exe`로 배포판의 로그인 셸에서 실행). **모델 호출 없음.** 도구: [`tools/w2/codex_sandbox.py`](https://github.com/inlight37-design/decision-model_lab/blob/01cedd3c05dc043465d4476aab2b1a8f547574e9/tools/w2/codex_sandbox.py) — 이번에 인증 파일·네트워크 확인과 권한 profile 변형을 더했다. Codex 0.156.1.

## 왜 했나

- 사용자가 2단계의 후속 호출(K01 큰 입력 Claude 1회, K09 인증 연결 좁히기 Claude 1·Codex 1)을 세션의 판단에 맡겼다(2026-09-24).
- 세션은 K09를 좁히기 전에 **참여자의 명령이 자기 CLI의 인증 파일에 닿는지**부터 모델 없이 봤다. 하위 폴더를 덮어 좁혀도 인증 파일은 가릴 수 없다 — CLI가 그 파일로 로그인한다. 그러니 그것이 가장 큰 노출이다.
- **모델 호출은 하지 않았다.** 후속 호출의 승인을 `observe.py approve`에 적으려 했으나, 이 세션의 자동 권한 확인이 "사용자의 명시적 승인이 아니다"라는 취지로 거절했다. 우회하지 않고 사용자의 명시적 승인을 기다린다.

## 어떻게 봤나

참여자와 같은 경계(Codex의 `cli_mounts`와 읽기 전용 공통 자료 폴더) 안에서 `codex sandbox -- /bin/sh -c …`를 돌렸다. `codex sandbox`는 exec에서 모델의 명령을 돌릴 때와 같은 Codex의 Linux 샌드박스로 명령 하나를 돌린다. 셸이 해 본 것은 넷이다.

- 작업 폴더와 `/tmp`에 쓰기
- 공통 자료 읽기
- `~/.codex/auth.json`이 있는지와 읽을 수 있는지. `test -e`·`test -r`의 종료 코드만 찍었다 — 내용은 읽지 않았다.
- `1.1.1.1:443`으로 TCP 연결 열기. 3초 제한, 아무것도 보내지 않는다.

## 결과

| 변형 | exit | 작업 폴더·`/tmp` 쓰기 | 공통 자료 읽기 | `auth.json` 있음 | `auth.json` 읽힘 | TCP 연결 | 자손 종료 |
|---|---|---|---|---|---|---|---|
| 기본 | 0 | 막힘 | 됨 | 예 | **예** | 막힘(`PermissionError`) | 확인 |
| `-c sandbox_mode="read-only"` | 0 | 막힘 | 됨 | 예 | **예** | 막힘 | 확인 |
| 권한 profile: `:read-only` + `~/.codex` 읽기 금지 | 1 | — | — | — | — | — | 확인 |
| 권한 profile: `:read-only` + `~/.codex/auth.json` 읽기 금지 | 0 | 막힘 | 됨 | 예 | **아니오** | 막힘 | 확인 |

- `~/.codex` 전체를 금지하면 셸이 아예 돌지 않았다: `bwrap: execvp ~/.codex/packages/standalone/releases/0.156.1-x86_64-unknown-linux-musl/bin/codex: Permission denied`. Codex의 샌드박스 보조 프로그램이 `~/.codex` 아래에 있는 codex 실행 파일을 다시 실행하기 때문이다.
- 권한 profile은 `-c 'permissions.dml-deny={ extends = ":read-only", filesystem = { "<HOME>/.codex/auth.json" = "deny" } }' -P dml-deny`로 넘겼다. 문법은 [Codex 권한 문서](https://learn.chatgpt.com/docs/permissions)(2026-09-24 확인)를 따랐다.

## 판정

- **지금 구성에서 Codex 참여자의 명령은 Codex의 로그인 파일(`~/.codex/auth.json`)을 읽을 수 있다(K46).**
  - 모델이 그 파일을 읽어 답에 넣으면 ChatGPT 로그인 토큰이 우리 원장과 공개된 화면에 남는다. 공통 자료에 섞인 지시(프롬프트 주입)로 유도될 수도 있다.
  - 명령의 네트워크는 Codex 샌드박스가 막으므로 명령으로 직접 내보내지는 못한다. 모델 자신의 대화는 OpenAI로 간다.
  - 지금은 기록의 Codex 문맥 판정이 `failed`라 실제 실행기가 Codex를 부르지 않는다. 그래서 당장 드러나는 경로는 없다.
- **Claude는 같은 문제가 작다.** 참여자의 Read 도구가 `--restricted`로 작업·입력 폴더에 갇힌다 — 2단계에서 밖의 경로를 거절하는 것을 봤다. 셸 도구도 없다.
- **방어 후보:** 이름 있는 권한 profile로 `~/.codex/auth.json` 하나만 읽기 금지한다.
  - `codex sandbox`에서는 명령이 그 파일을 못 읽었다. 나머지(쓰기 차단, 공통 자료 읽기, 네트워크 차단, 자손 종료)는 그대로였다.
  - CLI 자신은 샌드박스 밖에서 인증 파일을 읽으므로 로그인에는 영향이 없을 것이다 — exec로는 아직 확인하지 않았다.
- **아직 아닌 것:**
  - `codex exec`에 이 profile을 주려면 `--sandbox read-only` 대신 `-c permissions.…`와 `-P`를 넘겨야 한다. 문서는 옛 `sandbox_mode`와 권한 profile을 함께 쓰지 말라고 한다.
  - adapter는 `-c`를 금지 목록에 두고 있어(허용한 Windows 샌드박스 값만 예외) 허용 목록을 넓혀야 한다.
  - 바꾼 뒤 실제 exec 한 번(모델 호출)으로 보아야 한다: 로그인이 되는지, 모델이 돌린 명령이 `auth.json`을 못 읽는지, 쓰기가 막히는지.
  - 권한 profile은 문서상 베타 기능이다. 예전 버전에서 deny 패턴이 읽기를 막지 못한 보고가 있다([openai/codex#22179](https://github.com/openai/codex/issues/22179), 0.130.0). Codex 버전이 바뀌면 이 진단을 다시 돌린다.

## K09 연결 좁히기를 지금 하지 않은 이유

- 하위 폴더를 빈 tmpfs로 덮는 것은 세션 기록 같은 부수 노출을 줄이지만, 가장 큰 노출인 인증 파일은 그대로다(위).
- 2단계 호출에서 토큰 갱신이 한 번도 일어나지 않았다. 좁힌 구성에서 갱신이 저장되는지 볼 수 없다. 틀리면 사용자의 로그인이 풀린다.
- 그래서 순서를 바꾼다: 먼저 인증 파일 읽기 금지(권한 profile)를 adapter에 넣고 한 번 관측한다. 하위 폴더 덮기는 그 뒤에 한다.

## 한계

- `codex sandbox`로 본 것이다. exec에서 모델이 돌리는 명령이 같은 정책을 받는지는 profile을 exec에 넘겨 한 번 관측해야 안다.
- 인증 파일은 종료 코드만 봤다. 내용은 읽지 않았다.
- 네트워크는 TCP 연결 하나(1.1.1.1:443)만 봤다. DNS, 다른 포트, UDP, 로컬 소켓은 보지 않았다.
- 배포판 하나, Codex 0.156.1 하나다.
