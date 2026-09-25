# N3 — 격리 안 로그인 상태에 필요한 인증 파일, `aux-pc-wsl`

2026-09-23 · claude 세션(Claude Opus 5.5, aux-pc의 로컬 checkout, `wsl.exe`로 배포판의 로그인 셸에서 실행). **모델 호출 없음.** 인계 4절 N3(K09)의 관측이다. 도구: [`tools/w2/auth_mounts.py`](https://github.com/inlight37-design/decision-model_lab/blob/01cedd3c05dc043465d4476aab2b1a8f547574e9/tools/w2/auth_mounts.py). 환경: WSL 2.7.14, Ubuntu 24.04.5, bubblewrap 0.9.0, Claude Code 2.1.280, Codex 0.156.1.

## 어떻게 봤나

각 CLI마다 인증·설정 경로의 연결 조합을 바꿔 가며 [`core/isolation.py`](../../../core/isolation.py)의 참여자 경계 안에서 `--version`과 로그인 상태 명령(`claude auth status`, `codex login status`)만 실행했다. 기준 조합(지금의 `cli_mounts`: 설정 폴더 전체를 쓰기로)만 쓰기이고, **좁힌 조합은 모두 읽기 전용**이다 — 사용자 파일을 바꾸지 않았다. 계정 이메일·조직 ID·요금제는 버리고 로그인 여부와 방식만 남겼다. 모든 실행이 exit 뒤 자손 전체의 종료를 확인했다(`tree_confirmed_empty`).

## 결과

| CLI | 연결 조합 | 로그인 상태 |
|---|---|---|
| Claude Code | 지금: `~/.claude`·`~/.claude.json` 쓰기 | 로그인됨(`claude.ai`, `firstParty`) |
| | `~/.claude`·`~/.claude.json` 읽기 전용 | 로그인됨 |
| | `~/.claude/.credentials.json`·`~/.claude.json` 읽기 전용 | 로그인됨 |
| | **`~/.claude/.credentials.json`만** 읽기 전용 | **로그인됨** |
| | `~/.claude.json`만 읽기 전용 | 로그인 안 됨(`authMethod: none`, exit 1) |
| | 아무것도 없음 | 로그인 안 됨(exit 1) |
| Codex | 지금: `~/.codex` 쓰기 | 로그인됨(ChatGPT) |
| | `~/.codex` 읽기 전용 | exit 0. 먼저 `WARNING: proceeding, even though we could not create PATH aliases: Read-only file system`을 찍는다 — 시작할 때 `~/.codex`에 무언가를 쓰려 한다 |
| | **`~/.codex/auth.json`만** 읽기 전용 | **로그인됨** |
| | 아무것도 없음 | `Not logged in`(exit 1) |

`~/.codex/config.toml`은 이 배포판에 없다. 두 설정 폴더의 맨 위 항목은 이름만 보았다(내용은 읽지 않음): `~/.claude`에는 `backups`·`cache`·`downloads`·`sessions`·`.credentials.json`·`settings.json`, `~/.codex`에는 `log`·`packages`(CLI 설치)·`tmp`·`auth.json`이 있다. 이 배포판에서는 CLI를 대화형으로 거의 쓰지 않아 대화 기록 폴더가 아직 없다.

## 판정

- **로그인 상태에는 인증 파일 하나면 된다.** Claude는 `~/.claude/.credentials.json`, Codex는 `~/.codex/auth.json`. 읽기 전용으로도 된다. `~/.claude.json`은 인증에 필요하지 않았다.
- **그러나 인증 파일 하나만 연결하는 것으로 바로 좁히지 않는다.** 실제 질의 중 토큰이 갱신되면 CLI가 인증 파일을 다시 쓴다.
  - 읽기 전용이면 갱신을 저장하지 못한다.
  - 파일 하나만 쓰기로 연결하면, CLI가 새 파일을 만들어 이름을 바꾸는 방식으로 쓸 때 연결된 파일 위로 바꿀 수 없다.
  - 어느 경우든 갱신 토큰이 한 번 쓰면 바뀌는 방식이라면 새 토큰을 잃고 **사용자의 로그인이 풀릴 수 있다.**
  - 지금의 폴더 전체 쓰기 연결은 같은 폴더 안의 이름 바꾸기가 되므로 이 위험이 없다.
- **다음 후보:** 설정 폴더는 쓰기로 두되, 대화 기록처럼 참여자에게 필요 없는 하위 폴더는 빈 tmpfs로 덮는다. 인증 파일의 저장 방식은 그대로 둔다. 무엇을 덮을지는 실제 질의에서 CLI가 무엇을 읽고 쓰는지를 본 뒤 정한다.
- 그래서 [`tools/w2/observe.py`](../../../tools/w2/observe.py)가 2단계 호출마다 쓰기로 연결한 설정 폴더의 파일 이름·크기·수정 시각을 호출 전후로 비교해 `config_changes`에 남긴다. 내용은 읽지 않는다. 인증 파일이 바뀌었다면 그 호출에서 토큰이 갱신된 것이다.

## 한계

- 한 배포판에서 하루 한 번 본 결과다. CLI 버전이 바뀌면 다시 본다.
- 로그인 상태 명령은 저장된 토큰을 읽는 데까지다. 토큰이 만료돼 갱신이 필요한 상황은 만들지 않았다.
- `codex login status`의 첫 줄만 남겼다. 읽기 전용 `~/.codex`에서는 첫 줄이 경고라서 로그인 줄을 표에 옮기지 못했다(exit 0).
