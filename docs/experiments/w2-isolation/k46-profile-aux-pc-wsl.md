# K46 — 권한 profile을 adapter에 넣기 전의 모델 없는 확인, `aux-pc-wsl`

2026-09-24 · claude 세션(Claude Opus 5.5, aux-pc의 로컬 checkout, `wsl.exe`로 배포판의 로그인 셸에서 실행). **모델 호출 없음.** 도구: [`tools/w2/codex_profile.py`](../../../tools/w2/codex_profile.py). Codex 0.156.1.

## 왜 했나

- 사용자가 다음 세션의 첫 일로 K46 방어를 골랐다(2026-09-24).
- 인계는 adapter가 `-c permissions.…`와 `-P <이름>`을 exec에 넘기라고 했다. 넘기기 전에 exec가 그 인자를 받는지부터 봤다.

## 정정: `codex exec`에는 `-P`가 없다

- `codex exec --help`(0.156.1, [기록](../v04-01-inventory/hosts/aux-pc-wsl/help/codex-2.txt))에 `-P`가 없다.
  - `codex exec -P nosuchprofile --help`는 인자 오류(종료 코드 2)로 끝났다.
  - `-P, --permission-profile`은 `codex sandbox`에만 있다.
- [Codex 권한 문서](https://learn.chatgpt.com/docs/permissions)(2026-09-24 확인)는 설정 키 `default_permissions`로 기본 profile을 고른다고 한다.
- 그래서 [후속 기록](stage2-followup-aux-pc-wsl.md)의 "`-c permissions.…`와 `-P`를 넘겨야 한다"는 exec에는 틀리다. 그 기록은 날짜가 있는 기록이라 고치지 않고, 이 기록과 목록([검토 목록](../../reviews/README.md), [`tools/w2/`](../../../tools/w2/README.md), 인계)에서 바로잡는다.
- adapter는 `-c 'permissions.dml-discussant={ extends = ":read-only", filesystem = { "<HOME>/.codex/auth.json" = "deny" } }'`와 `-c 'default_permissions="dml-discussant"'`를 넘기고, 옛 `--sandbox read-only`는 넘기지 않는다. 문서는 둘을 섞지 말라고 한다.

## 어떻게 봤나

1. **`codex sandbox`** — 참여자 경계 안에서 [`observe.py`](../../../tools/w2/observe.py) `k46-codex`와 같은 셸 명령을 돌렸다.
   - 명령: 작업 폴더 쓰기, 공통 자료 읽기, `~/.codex/auth.json` 열기. 종료 코드만 찍고 내용은 `/dev/null`로 버린다.
   - 변형: profile 없음, exec 방식(`default_permissions`로 고름), 지난 진단의 `-P` 방식.
2. **`codex exec`, 네트워크 없음** — 참여자의 실제 argv(`CliExecutor.prepare`)를 같은 격리 경계에서 돌렸다.
   - bwrap 인자에서 `--share-net`만 빼서 새 네트워크 namespace(loopback만)를 만들었다. 모델에 닿을 수 없으므로 사용량을 쓰지 않는다.
   - 질문은 "Reply with exactly: OK", 제한 90초.
   - 변형: 참여자 argv(`--json`), 같은 argv의 사람용 출력, 없는 profile 이름, 옛 `--sandbox read-only`의 사람용 출력.
- 인증 파일은 실행 전후의 크기·수정 시각만 비교했다. 네 exec 변형 모두 바뀌지 않았다.
- 도구를 두 번 돌렸다. 두 번째는 셸 명령을 `observe.AUTH_CHECK`로 합친 뒤의 판(이 기록과 함께 커밋한 판)이다. 결과는 같았고, 없는 profile을 거절하기까지 걸린 시간만 달랐다.

## 결과

### `codex sandbox`

| 변형 | exit | 작업 폴더 쓰기 | 공통 자료 읽기 | `auth.json` 있음 | `auth.json` 열림 | 자손 종료 |
|---|---|---|---|---|---|---|
| profile 없음(기본) | 0 | 막힘 | 됨 | 예 | **예** | 확인 |
| profile, `default_permissions`로 고름(exec 방식) | 0 | 막힘 | 됨 | 예 | **아니오** | 확인 |
| profile, `-P`로 고름(지난 진단) | 0 | 막힘 | 됨 | 예 | **아니오** | 확인 |

### `codex exec`, 네트워크 없음

| 변형 | 끝 | 본 것 |
|---|---|---|
| 참여자 argv(`--json`) | 90초 제한에 끊음, 자손 종료 확인 | JSONL `thread.started`·`turn.started` 뒤 `error` 넷. 설정 오류 없이 연결 단계까지 갔다 |
| 같은 argv, 사람용 출력 | 같음 | 머리글에 `sandbox: read-only`. 재연결을 5/5까지 시도했다 |
| 없는 profile 이름(`default_permissions="notamode"`) | exit 1, 54 ms·82 ms(두 번) | ``Error: default_permissions refers to undefined profile `notamode` ``. 연결 전에 끝났다 |
| 옛 `--sandbox read-only`, 사람용 출력 | 90초 제한에 끊음 | 머리글에 `sandbox: read-only` — profile을 준 경우와 같다 |

- 연결까지 간 세 변형 모두 stderr에 `failed to refresh available models`와 `https://chatgpt.com/backend-api/ps/mcp`로의 연결 실패(`rmcp`)가 여러 번 있었다. `--ignore-user-config`를 줘도 exec가 계정 쪽 MCP 서버에 붙으려 한다.

## 판정

- `default_permissions`로 고른 profile은 `codex sandbox`에서 `-P`로 고른 것과 같이 인증 파일만 막는다. 쓰기 차단과 공통 자료 읽기는 그대로다.
- exec는 이 설정 조합(옛 `--sandbox` 없이, `--ignore-user-config`와 함께)을 설정 오류 없이 받아들인다.
- 없는 profile을 주면 exec는 연결 전에 끝난다. 조용히 기본값으로 돌아가지 않는다. 그래서 `observe.py`의 `p3-codex`는 이제 이 값을 넘긴다(전에는 `--sandbox notamode`).
- 사람용 머리글은 profile을 구분해 보이지 않는다. 머리글로는 profile이 적용됐는지 확인할 수 없다.
- K44·C3의 재료: exec가 `--ignore-user-config`에도 `chatgpt.com/backend-api/ps/mcp`에 연결하려 한다. 그 MCP의 도구가 참여자 문맥에 들어가는지는 아직 모른다.

## 아직 아닌 것

- exec에서 **모델이 돌린 명령**에 이 금지가 적용되는지는 보지 못했다. `observe.py call k46-codex` 1회로 본다(승인 필요).
- 네트워크가 없을 때와 있을 때 exec가 같은 설정 경로를 탄다고 가정했다.
- 배포판 하나, Codex 0.156.1 하나다. 권한 profile은 문서상 베타다. 버전이 바뀌면 이 도구를 다시 돌린다.
