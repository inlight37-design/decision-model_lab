# Codex 참여자의 연결 앱 끄기와 K46 재관측 — 2026-09-24

작성: claude 세션(Claude 데스크톱 앱). 사용자 PC `aux-pc`의 Windows와 WSL `aux-pc-wsl`(Ubuntu-24.04)에서 직접 실행했고, WSL의 Codex 0.156.1·Claude Code 2.1.280을 직접 봤다. 브랜치 `claude/codex-apps-off-20260924`, 기준 main `6875fff`(PR #44 병합). [NEXT-SESSION](../../../NEXT-SESSION.md) 4절 E(문맥 독립성 — 연결부터 좁힌다)의 첫 단계다. **모델 호출은 1회**(Codex, K46 재관측)다.

## 결론

1. **Codex 참여자에게 사용자 계정의 연결 앱이 열려 있었다.** 참여자와 같은 격리·같은 연결(실제 로그인 폴더)로 Codex app-server에 모델 없이 물었더니, MCP 서버 `codex_apps` 하나에 도구 198개가 있었다. GitHub·Google Drive의 쓰기 도구(커밋 만들기, 파일 지우기, 파일 공유 등)가 들어 있었고, 호출 가능한 앱은 9개였다. [공식 설정 문서](https://learn.chatgpt.com/docs/config-file/config-reference)는 연결 앱 트래픽이 샌드박스 명령의 네트워크 제한을 받지 않는다고 적는다. 읽기 전용 논의자(NEXT-SESSION 2절 7)와 초안 독립성 모두의 경계 밖이다. 지금까지의 실제 실행에서 이 도구가 불린 흔적은 없었고, 부를 수 있었는지는 시험하지 않았다.
2. **참여자 계획에 `-c features.apps=false`를 더했다.** 같은 조회에서 MCP 서버 0개, 호출 가능한 앱 0개가 됐다. 계획이 바뀌어 판이 `codex@8a0128d4c791`(K46이 돈 계획)에서 `codex@5a77e0b7dc7f`로 바뀌었고, 옛 기록으로는 실행이 거절된다.
3. **새 판으로 K46을 다시 관측했다.** 쓰기 `EROFS`, 공통 입력 ok, 로그인 파일 `EACCES`, 입력 전달 완료, 자손 종료 확인, 수용 관문 ok. [새 manifest](manifest.v2.json)가 새 판의 전송·권한을 뒷받침한다. 모델 없는 준비 조회에서 새 manifest는 문맥 미확인 opt-in일 때 두 provider를 허가하고, strict는 거절한다.
4. **C3(문맥 독립성)는 닫히지 않았다.** Codex 문맥 기록은 failed, Claude는 unknown 그대로다. 이유와 다음 방법은 아래 "남은 것"에 적었다.

## 참여자에게 열려 있던 것

폴더의 이름 목록만 봤고 파일 내용은 읽지 않았다.

| 통로 | Codex(`~/.codex`를 쓰기로 연결) | Claude(`~/.claude`·`~/.claude.json`을 쓰기로 연결) |
|---|---|---|
| 사용자 지시문 | `~/.codex/AGENTS.md` 없음, 사용자 설정 파일(`config.toml`) 없음 | `~/.claude/CLAUDE.md` 없음 |
| 연결 앱·MCP | `codex_apps` 도구 198개, 호출 가능 앱 9개 → **이번에 끔**(0·0) | init의 MCP 서버 없음(`--strict-mcp-config`, [#39 관측](../2026-09-24-windows-live-completion/README.md)) |
| skills | 내장 6개(`skills/.system`)뿐, 사용자 skill 없음. 끄기 전후 같음 | init에 plugins/agents가 남음(#39 기록) |
| 지난 기록·메모리 | 로그 폴더·로그 DB, shell 스냅샷, 상태·메모리·goals·queue DB | 세션·백업·캐시·다운로드 폴더, 설정 파일 |
| 플러그인 캐시 | 원격 플러그인 설치 정보(큐레이션·사용자 제작) | — |

- 이 PC에서는 두 CLI의 사용자 지시문 파일이 없다. 그래서 "사용자 지시문이 문맥에 실리는가"는 이 PC에서 양성 대조 없이 시험할 수 없다. 실제 파일을 만들어 넣으면 사용자의 실제 폴더를 고치게 되므로 하지 않았다.
- Codex 권한 profile은 로그인 파일 하나만 읽기 금지다. 나머지 `~/.codex` 항목은 profile상 모델의 명령이 읽을 수 있다(하나씩 시험하지는 않았다). Claude는 입력 폴더 밖 Read 거절을 합성 peer 파일로 관측했고(#39), `~/.claude` 아래를 직접 시험하지는 않았다.

## 바꾼 것

- [`core/adapters.py`](../../../core/adapters.py): `CODEX_APPS_OFF = "features.apps=false"`. Linux Codex 참여자 계획이 K46 권한 profile 다음에 `-c features.apps=false`를 준다. Windows 경로(`--sandbox read-only`)는 바꾸지 않았다. Codex를 blind 참여자로 쓰는 것은 WSL2에서만 한다(2절 15).
- 시험: 고정한 argv에 그 값이 들어 있다. 가짜 Codex는 그 값이 없으면 거절한다. K46이 돈 옛 계획의 판은 "지금 계획에서 그 한 쌍만 뺀 것"으로 따로 계산한다(`tests/test_core_contract.k46_revision`). 옛 기록은 지금 계획을 허가하지 않는다. 새 기록은 지금 계획(입력 폴더 하나)만 opt-in으로 허가하며, 판 문자열 `codex@5a77e0b7dc7f`·`claude-code@126be128bed7`을 고정해 계획이 바뀌면 시험이 알린다.
- `contract.LEGACY`는 넓히지 않았다. 옛 이름 판 `discussant-2`는 여전히 K46이 실제로 돈 계획 하나에만 대응한다.

## 관측

### 모델 없는 연결 조회

bubblewrap 안에서 참여자와 같은 연결(실행 파일 읽기 전용, `~/.codex` 쓰기, HOME tmpfs)로 `codex app-server`를 띄우고, `initialize` → `skills/list` → `mcpServerStatus/list` → `app/installed`만 보냈다([app-server 문서](https://learn.chatgpt.com/docs/app-server)). thread/turn은 시작하지 않았다. 추론 요청과 agent 활동 알림은 0이다. 이름은 해시로만 출력했고 여기에는 개수만 적는다.

| | 기본 | `-c features.apps=false` |
|---|---|---|
| skills | 6(모두 내장) | 6(모두 내장) |
| MCP 서버 | 1(`codex_apps`, 도구 198) | 0 |
| 설치된 앱 / 켜짐 / 호출 가능 | 9 / 9 / 9 | 9 / 0 / 0 |
| 종료 | exit 0, 자손 종료 확인 | exit 0, 자손 종료 확인 |

app-server 프로세스의 표면이고, 참여자가 쓰는 `exec`의 표면을 직접 센 것은 아니다. 같은 실행 파일·같은 `-c` 값·같은 연결이다. exec가 더 주는 `--ignore-user-config`는 이 PC에 사용자 설정 파일이 없어 차이를 만들지 않는다.

### K46 재관측(모델 1회)

새 상태 폴더(`~/.local/state/dml-observe-e-20260924`, 시작 전 없음)에 `observe.py approve --codex 1 --timeout 300`을 한 번 기록했다. 노트에는 이 세션·날짜·NEXT-SESSION 2절 22 승인을 적었다. `observe.py call k46-codex gpt-6-luna`를 한 번 불렀고 `status`는 Codex 1/1, Claude 0이다. `--keep-session`은 쓰지 않았다. [요약](k46-summary.json)은 원시 출력을 구조로 읽은 뒤 고정 필드만 새로 구성했다. 원시 stdout/stderr, nonce, 세션 ID, 플러그인·캐시 파일 이름은 넣지 않았다.

| 항목 | 관측값 |
|---|---|
| 판 / argv 변형 | `codex@5a77e0b7dc7f` / `argv_changes=[]`(참여자 계획 그대로) |
| 요청 모델 / 제공 모델 | `gpt-6-luna` / CLI가 보고하지 않음(`reported_models=[]`, K32 유지) |
| runner / exit / 시간 | `exited` / 0 / 7,680 ms |
| 입력 / 종료 | stdin 343 bytes, `input_delivery=complete` / `pid_namespace`, `tree_confirmed_empty=true` |
| helper 검증 | `k46.verified=true`, 완료된 고정 명령 정확히 하나, 답의 `output`이 그 명령의 출력과 같음 |
| helper 결과 | `write=denied:EROFS`, `input=ok`, `auth=denied:EACCES` |
| 위반 / 관문 / 판정 | `boundary_violations=[]` / `gate=ok` / `as_expected=true` |
| 사건 | MCP·앱 도구 항목 없음, stderr 비어 있음, 자격증명 모양 없음 |
| 토큰(CLI 보고) | input 25,009(cached 22,016), output 109 — 연결 앱을 켠 [K46 확인](../../experiments/w2-isolation/2026-09-24-k46-confirmation/README.md)은 28,739(cached 25,088) |

`~/.codex`의 변화: 앞 K46에서는 연결 앱 도구 캐시가 바뀌었지만 이번에는 바뀌지 않았다. 원격 플러그인 설치 정보·메모리 DB·로그·상태 DB는 이번에도 바뀌었다. 입력 토큰이 줄고 도구 캐시가 그대로인 것은 연결 앱이 꺼졌다는 것과 맞지만, 무엇이 모델 문맥에 실렸는지의 증거는 아니다. 공식 설정 문서는 메모리 기능(`features.memories`)이 기본으로 꺼져 있다고 적고, `--ignore-user-config`는 사용자 설정이 그것을 켜지 못하게 한다. 메모리 DB 파일의 변화만으로 메모리 주입을 확정하지 않는다.

### 준비 조회(모델 없음, 원장 만들지 않음)

같은 설정(두 provider, 각자 빈 입력 폴더 하나)을 두 manifest로 `--check-config`했다. 원장 폴더는 생기지 않았다.

| manifest | strict | 문맥 미확인 opt-in |
|---|---|---|
| [#39 기록](../2026-09-24-windows-live-completion/manifest.v2.json) | Codex 거절(전송·권한 재관측 필요, 문맥 failed), Claude 거절(문맥 unknown) | Codex 거절(전송·권한 재관측 필요), Claude 허가 |
| [새 기록](manifest.v2.json) | Codex 거절(문맥 failed), Claude 거절(문맥 unknown) | **둘 다 허가**(`codex@5a77e0b7dc7f`, `claude-code@126be128bed7`) |

## 남은 것

- **나머지 `~/.codex` 항목.** 로그인 파일 외의 로그·shell 스냅샷·상태·메모리 DB·플러그인 캐시는 모델의 명령이 읽을 수 있다. 로그·상태 DB에는 앞선 실행의 흔적이, shell 스냅샷에는 그 셸의 환경이 들어 있을 수 있다(내용은 읽지 않았다). 이름으로 막는 목록(권한 profile의 deny)을 늘리지 않았다. 파일 이름에 버전 번호가 붙어(`logs_2`, `state_5`, `memories_1`) CLI가 바뀌면 조용히 빠진다. bubblewrap으로 하위 항목을 빈 tmpfs로 덮는 것도 하지 않았다. CLI 자신이 그 DB·캐시를 쓰고, DB는 폴더가 아니라 파일이라 tmpfs로 덮이지 않으며, 없는 경로를 덮으면 사용자 폴더에 연결 지점이 생긴다. 로그인 파일만 따로 연결하면 토큰 갱신의 파일 교체가 막힐 수 있다([K09 기록](../../experiments/w2-isolation/auth-mounts-aux-pc-wsl.md)이 폴더째 연결한 이유). 다음 후보는 시도마다 빈 Codex 홈을 만들고 로그인 파일만 복사한 뒤 갱신됐으면 잠금 안에서 되돌려 쓰는 것이다. 동시에 도는 두 참여자의 갱신 경합과 사용자 로그인을 망가뜨릴 위험을 먼저 설계해야 한다.
- **최종 문맥 확인.** 설치판에서 모델에 넘기기 직전의 지시문·도구 목록을 볼 공식 진단을 찾지 못했다. 양성·음성 대조(표식 넣은 합성 파일과 빈 덮개)는 덮개를 만들지 않았으므로 하지 않았다. 이 PC는 사용자 지시문 파일이 없어 그 통로의 양성 대조에는 사용자 폴더를 고쳐야 한다.
- **Claude.** MCP는 이미 꺼져 있고 사용자 지시문 파일도 없다. `--safe-mode`(문서상 구독 인증 유지)로 plugins/agents가 빠지는지와 K45(`agents-md@builtin`)는 다시 보지 않았다. `--bare`는 구독 로그인을 쓰지 않으므로 쓰지 않는다.
- K46은 이 고정 helper의 경로만 확인한다. 네트워크는 공유(K08)이고 제공 모델은 미보고(K32)다. 한 설치판·한 WSL 배포판에서 한 번 본 결과다.
