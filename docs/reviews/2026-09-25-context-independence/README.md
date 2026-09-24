# 참여자 문맥 독립성(E2) — 2026-09-25

작성: claude 세션(Claude 데스크톱 앱). 사용자 PC `aux-pc`(hostname `DESKTOP-L6EA2UJ`)의 Windows와 WSL `aux-pc-wsl`(Ubuntu-24.04, bubblewrap 0.9.0)에서 직접 실행했고, WSL의 Codex 0.156.1·Claude Code 2.1.280을 직접 봤다. 브랜치 `claude/context-independence-20260925`, 기준 main `73444cf`(PR #48). [NEXT-SESSION](../../../NEXT-SESSION.md) 4절 E의 두 번째 단계다. **모델 호출은 6회**(Claude 2·Codex 4)이고, 모두 새 상태 폴더 `~/.local/state/dml-observe-e2-20260925`의 승인 두 창(Claude 2·Codex 1, 그다음 Codex 3) 안에서 불렀다. 승인은 NEXT-SESSION 2절 22(상시 승인)다. 로그인 파일의 내용은 읽지 않았고, 모든 호출 전후로 두 로그인 파일의 크기·수정 시각이 그대로였다.

## 결론

1. **두 참여자 계획을 바꿨다.** Claude는 `--restricted` 위에 `--safe-mode`를 더했다. Codex는 모델의 명령에게 로그인 파일 하나가 아니라 `~/.codex` 전체를 막고, 그러려고 실행 버전 폴더를 격리 안 `/opt/dml-codex`에 읽기 전용으로 보여 그 경로로 실행하며, `-c project_doc_max_bytes=0`으로 작업 폴더의 AGENTS.md를 싣지 않는다. `~/.codex`에 비어 있지 않은 AGENTS.md·AGENTS.override.md가 있으면 실행기가 계획·실행 전에 거절한다.
2. **행동 표식으로 양성·음성 대조를 했다.** 작업 폴더의 지시문 파일(Claude는 CLAUDE.md, Codex는 AGENTS.md)에 "모든 답을 이 표식 줄로 끝내라"를 적고, 질문은 표식을 묻지 않았다. 지시문이 실리는 변형(양성 대조)에서는 두 CLI 모두 표식을 답 끝에 붙였고, 참여자 계획 그대로에서는 붙이지 않았다. 모델이 그 파일을 직접 연 기록은 없었다. 모델의 자기 보고를 쓰지 않았다(K31).
3. **Codex 모델의 명령은 이제 `~/.codex`를 읽지 못한다.** 모델 없는 진단에서 옛 profile은 로그인 파일만 막아 상태·로그·메모리 DB, 로그 폴더, 플러그인·연결 앱 캐시를 모두 읽을 수 있었다 — 지난 실행의 흔적이 남을 수 있는 곳이다(내용은 읽지 않았다). 새 계획에서는 목록 읽기와 로그인 파일 열기가 모두 EACCES로 거절됐다.
4. **새 [관측 manifest](manifest.v2.json)로 두 provider가 strict에서 허가된다.** 앱의 준비 조회(`--check-config`, 모델 호출 0, 원장 생성 없음)가 입력 폴더 하나의 두 계획을 `--allow-context-unverified` 없이 허가했다. 옛 manifest로는 새 계획이 거절된다. 독립 정족수에 셀 수 있게 됐지만 이 PC·이 판·이 설치판·관측 뒤 30일에 한정된다. 앱으로 strict 실행을 실제로 해 본 것은 아니다.
5. **부수 발견: 문맥 옵션 없는 Claude는 사용자 계정의 플러그인·스킬을 동기화한다.** 양성 대조 호출(`--restricted`·`--safe-mode` 없음) 중 Claude Code가 계정의 플러그인 3개(cowork-plugin-management, design, engineering)와 스킬(docx 등)을 `~/.claude/plugins/synced/…`·`~/.claude/skills/synced/…`에 받았다(파일 254개). 바로 뒤의 참여자 계획은 이를 싣지 않았다(init의 skills 0). `--safe-mode`가 필요한 이유를 하나 더 보여 준다.

## 모델 없이 본 것

### Codex가 모델 입력에 싣는 지시문 — `codex debug prompt-input`

0.156.1의 `codex debug prompt-input`은 모델에 보이는 입력 목록을 JSON으로 렌더링한다(help: "Render the model-visible prompt input list as JSON"). 앞 codex 세션이 이미 찾았고, 최종 요청 전체가 아니라는 한계(도구 schema 없음, exec 전용 옵션 없음)를 적었다([GITHUB-C3](../2026-09-24-cli-readiness/GITHUB-C3.md)). 이번에는 참여자와 같은 격리·실행 위치·`-c` 값으로 돌리는 [`tools/w2/codex_prompt_input.py`](../../../tools/w2/codex_prompt_input.py)를 두었다. 결과: [model-free.json](model-free.json)의 `codex_prompt_input`.

| 합성 HOME(로그인 파일 없음) | 전역 `~/.codex/AGENTS.md` 표식 | 작업 폴더 `AGENTS.md` 표식 |
|---|---|---|
| 기본값 | 실림 | 실림 |
| `-c project_doc_max_bytes=0` | **실림** | 빠짐 |
| 빈 전역 파일 | 빠짐(빈 파일은 건너뜀) | 실림 |

- 그래서 작업 폴더 쪽은 계획이 `project_doc_max_bytes=0`으로 막고, 전역 파일은 실행기가 있으면 거절한다. 전역 파일은 공식 [AGENTS.md 안내](https://learn.chatgpt.com/docs/agent-configuration/agents-md)대로 override가 먼저이고 비어 있지 않은 첫 파일만 쓴다.
- 참여자 계획의 값으로 실제 HOME과 빈 합성 HOME을 렌더링하면 둘 다 지시문 묶음(`<INSTRUCTIONS>`)이 없고, 차이는 메시지 ID, 합성 HOME에만 있던 Codex 내장 협업 안내 두 문장(왜 달라지는지는 확인하지 않았다), Codex 자신의 보조 실행 파일 폴더(`~/.codex/tmp/arg0/…`) 읽기 허용 한 줄뿐이었다. 개인 지시문·메모리·플러그인 내용은 없었다(글은 저장소로 옮기지 않았다).

### Codex 명령이 `~/.codex`에서 읽을 수 있는 것 — `codex sandbox`

참여자와 같은 격리에서 `codex sandbox`로 셸 명령을 돌려 `test -r`의 종료 코드만 봤다(내용은 읽지 않음).

| 권한 profile | 결과 |
|---|---|
| 옛 참여자 profile(`~/.codex/auth.json`만 금지) | 로그인 파일만 막힘. `state_5`·`logs_2`·`memories_1`·`goals_1`·`queue_1` DB, `log`, `plugins`, `skills`, `cache`, `tmp`, `installation_id`, `models_cache.json` 모두 읽힘 |
| `~/.codex` 금지 + 실행 버전 폴더 "read"로 다시 엶 | 셸이 돌지 못함: `bwrap: execvp …/bin/codex: Permission denied` — Codex의 내부 샌드박스가 자기 실행 파일을 다시 실행한다 |
| `~/.codex` 금지 + 쓰기로 다시 엶 | `packages`를 연 변형은 돌았지만 모델의 명령에게 쓰기가 열리고, 그 뒤 사용자의 `~/.codex/packages` 수정 시각이 바뀌었다(남은 파일은 없음). 실행 버전 폴더만 연 변형은 Codex가 그 안에 `.git` 연결 지점을 만들려다 실패했다(`bwrap: Can't mkdir …/.git: Read-only file system`) — 둘 다 버렸다 |
| `~/.codex` 금지, 실행 파일은 격리 안 `/opt/dml-codex`에서 | 돌았다. `~/.codex`의 어떤 항목도 읽지 못함, 로그인 파일 열기 EACCES, 작업 폴더 쓰기 EROFS, 입력 읽기 됨, `/opt/dml-codex` 쓰기 거절, 사용자의 `~/.codex` 수정 시각 그대로 — **채택** |

`tools/w2/codex_profile.py --real-home`(네트워크 없음)도 새 profile에서 도우미의 로그인 파일 열기와 `~/.codex` 목록 읽기가 EACCES, profile 없는 대조군에서는 둘 다 열림을 보였다. 같은 도구로 새 참여자 argv를 네트워크 없이 돌리면 설정을 받아들여 대화를 시작했고(`thread.started`·`turn.started`), 없는 profile 이름은 연결 전에 거절됐다([model-free.json](model-free.json)의 `codex_profile_real_home`).

### Claude — 공식 CLI reference(2026-09-25 읽음)

[CLI reference](https://code.claude.com/docs/en/cli-reference)의 `--restricted`는 명령·코드 실행 도구를 빼고 파일 도구를 작업 폴더에 가두며 managed 설정과 `--settings`만 읽는다고 적는다. CLAUDE.md·메모리는 말하지 않는다. `--safe-mode`는 CLAUDE.md·skills·plugins·hooks·MCP·custom agents·output styles·자동 메모리 등을 싣지 않고 인증·모델·내장 도구·권한은 그대로라고 적는다. [memory 문서](https://code.claude.com/docs/en/memory)는 2.1.277부터 AGENTS.md를 읽는 내장 `agents-md` 플러그인을 설명한다(K45의 정체다). `--add-dir` 폴더의 CLAUDE.md는 기본으로 싣지 않는다.

## 바꾼 것

- [`core/isolation.py`](../../../core/isolation.py): `Sandbox.read_only_at` — 호스트 폴더를 격리 안에서 다른 경로로 읽기 전용으로 보인다. 그 경로는 bubblewrap 자신의 빈 루트에 생겨야 하고(호스트 연결 안이면 연결 지점이 호스트에 생기므로 거절), 그 안의 실행 파일은 옮긴 경로로 실행한다. `participant_mounts`가 Codex 실행 버전 폴더를 `CODEX_RELEASE_AT`(`/opt/dml-codex`)에 둔다. 계정 조회 등 다른 실행은 그대로 `cli_mounts`를 쓴다.
- [`core/adapters.py`](../../../core/adapters.py): Codex 권한 profile이 `~/.codex` 전체를 금지, `CODEX_NO_PROJECT_DOCS`(`project_doc_max_bytes=0`), `codex_global_instructions`. Claude는 `CLAUDE_CONTEXT["restricted_safe_mode"]`가 기본이다.
- [`app/cli_executor.py`](../../../app/cli_executor.py): `participant_mounts`로 계획하고, 전역 지시문 파일이 있으면 계획·실행 전에 거절한다(관측 도구도).
- [`core/contract.py`](../../../core/contract.py): 옮겨 보인 연결을 판의 틀(`ro:cli@/opt/dml-codex`)에 넣었다.
- [`tools/w2/observe.py`](../../../tools/w2/observe.py): K46 도우미가 `~/.codex` 목록 읽기도 해 본다(`home=`). 새 probe `c3-claude`·`c3-claude-pos`·`c3-codex`·`c3-codex-pos`. `b1`이 곧 옛 `b1-combo`의 조합이 되어 `b1-combo`는 거절한다.
- [`tools/w2/codex_prompt_input.py`](../../../tools/w2/codex_prompt_input.py): 위의 모델 없는 입력 렌더링.
- 시험: 옛 계획 셋을 지금 계획에서 되돌려 만들어 기록의 판 문자열(`codex@8a0128d4c791`·`codex@5a77e0b7dc7f`·`claude-code@126be128bed7`)과 정확히 같은지 확인한다. 새 격리 규칙은 규칙을 끄면 실패하는 것을 확인했다(변이).

판: Claude `claude-code@a35129c5a1dc`(입력 폴더 하나), Codex `codex@bba3751a36f3`(입력 폴더 하나). 자료 없는 계획은 다른 판이라 이 기록이 뒷받침하지 않는다(앞 기록과 같다).

## 모델 호출

모두 `claude-sonnet-5`·`gpt-6-luna`, timeout 300초. 요약은 [observations.json](observations.json)(관측 도구가 가린 요약만, 답·stdout·stderr 원문 없음)이다. 여섯 번 모두 `pid_namespace`·`tree_confirmed_empty: true`·`input_delivery: complete`·수용 관문 ok·경계 위반 없음·`as_expected: true`였다.

| n | probe | 판 | 결과 |
|---|---|---|---|
| 1 | `c3-claude-pos` | `claude-code@5436b63b80ab`(참여자 계획에서 `--restricted`·`--safe-mode`를 뺌, 도구 없음) | **표식을 답 끝에 붙임**. 도구 사용 0 |
| 2 | `c3-claude` | `claude-code@a35129c5a1dc`(참여자 계획 그대로) | **표식 없음**, CLAUDE.md를 Read로 열지 않음. 허용 자료 인용, 금지 파일 Read를 CLI가 거절(permission_denials 1), init tools Read·MCP 0·skills 0·plugins 2·agents 4 |
| 3 | `k46-codex` | `codex@867a4db616d1`(E2 첫 계획, `project_doc_max_bytes=0` 전) | write EROFS, input ok, auth EACCES, home EACCES |
| 4 | `c3-codex-pos` | `codex@867a4db616d1`(최종 계획에서 `project_doc_max_bytes=0`만 뺌 — 3번과 같은 판) | **표식을 답 끝에 붙임**. 명령 0 |
| 5 | `c3-codex` | `codex@bba3751a36f3`(참여자 계획 그대로) | **표식 없음**. 명령 0 |
| 6 | `k46-codex` | `codex@bba3751a36f3` | write EROFS, input ok, auth EACCES, home EACCES. 입력 25,081(캐시 22,016) — 연결 앱 끄기 기록의 25,009와 비슷 |

- 1·2번은 첫 코드 체크포인트(`eae9a56`)의 도구로 불렀다. 그래서 요약의 판정 칸 이름이 `claude_md_read_by_tool`이다. 그 뒤 두 CLI에 같은 이름을 쓰려고 `instruction_file_opened`로 바꿨다(4·5번).
- 3번 뒤에 Codex 계획이 작업 폴더 AGENTS.md를 빈 폴더라는 조건에만 기대고 있음을 보고 `project_doc_max_bytes=0`을 계획에 더했다. 계획이 바뀌었으므로 승인 창을 새로 기록하고(Codex 3) 양성·음성 대조와 K46을 다시 불렀다. 3번의 판은 최종 계획을 뒷받침하지 않는다.
- Codex는 여전히 답한 모델을 보고하지 않는다(K32).

## C3 판정과 한계

[manifest](manifest.v2.json)는 두 provider의 `context_conformance`를 observed로 적었다. 정의는 "참여자 문맥에 사용자 지시문·메모리·다른 참여자 정보가 실리지 않는가"다.

| 통로 | Claude(`a35129c5a1dc`) | Codex(`bba3751a36f3`) |
|---|---|---|
| 작업 폴더 지시문 | 행동 대조로 안 실림 | 행동 대조로 안 실림, 모델 없는 렌더링으로도 빠짐 |
| 사용자(전역) 지시문 | 이 PC에 없음. 같은 CLAUDE.md 적재가 막힘을 봤고, 문서상 safe mode는 모든 CLAUDE.md를 싣지 않음 | 이 PC에 없음. 있으면 실행기가 거절. 있으면 실린다는 것을 합성 HOME에서 봄 |
| 메모리 | 문서상 safe mode가 자동 메모리를 끔. 시도마다 새 작업 폴더라 그 폴더의 메모리가 없음. 심어서 보지는 않음 | 기능 기본 꺼짐, 사용자 설정 무시. 실제 HOME 렌더링에 없음. 값으로 고정하지는 않음 |
| 계정 플러그인·스킬·연결 앱 | 계정 동기화 뒤에도 skills 0·MCP 0 | 연결 앱 꺼짐(0·0), 스킬은 내장 6개([E 첫 단계](../2026-09-24-codex-apps-off/README.md)) |
| 지난 실행·다른 참여자 초안 | Read가 작업·입력 폴더 밖을 거절(관측), 셸 없음, 다른 CLI 폴더 미연결 | 모델의 명령이 `~/.codex`를 읽지 못함(관측), 다른 CLI 폴더 미연결 |

한계: 최종 요청 전체는 두 CLI 모두 볼 수 없다(Claude init은 불러온 지시문 목록을 보이지 않고, prompt-input은 도구 schema와 exec 전용 옵션을 반영하지 않는다). 대조는 provider별 한 번씩, 한 설치판·한 PC다. 모델이 지시를 따른다는 것은 양성 대조가 보였을 뿐 모든 모델·질문에 대한 보장이 아니다. 네트워크는 공유한다(K08). 설치판·판·날짜가 바뀌면 다시 관측한다(실행기가 강제한다). 이것은 독립성의 **문맥 조건**이 관측됐다는 뜻이지, 두 모델의 판단이 서로 독립이라거나 답이 맞다는 뜻이 아니다.

## 사용자 폴더에 생긴 변화

- `~/.claude/plugins/synced/…`·`~/.claude/skills/synced/…`: 1번 호출에서 Claude Code가 계정의 플러그인·스킬을 받았다(파일 254개). 폴더 이름에 계정 식별자가 들어 있어 이 기록에는 적지 않았다. CLI가 스스로 받은 캐시이고 참여자 계획은 싣지 않으므로 지우지 않았다. 사용자가 원하면 지워도 되며, 문맥 옵션 없이 Claude Code를 쓰면 다시 받는다.
- `~/.codex/packages`: "write" 변형 진단에서 폴더 수정 시각이 바뀌었다. 남은 파일은 없었다.
- `~/.codex`의 상태·로그·메모리·목표·대기열 DB와 모델 목록·플러그인 캐시는 Codex CLI 자신이 매 호출에 고쳤다(이름만 봤다). 모델의 명령은 그곳을 읽지 못한다.
- 로그인 파일(`~/.codex/auth.json`, `~/.claude/.credentials.json`)은 모든 진단·호출 전후에 크기·수정 시각이 같았다.
- 띄운 서버는 없다. 모든 프로세스는 자손 종료가 확인됐다.

## 다시 해 보는 법

저장소 루트에서, WSL 로그인 셸로.

```bash
python3 tools/w2/codex_prompt_input.py --real-home
python3 tools/w2/codex_profile.py --real-home
export DML_OBSERVE_STATE=~/.local/state/<새-상태-폴더>
python3 tools/w2/observe.py approve --claude 2 --codex 3 --timeout 300 --note "<누가·언제·어떤 승인>"
python3 tools/w2/observe.py call c3-claude-pos <Claude 전체 모델 이름>
python3 tools/w2/observe.py call c3-claude <Claude 전체 모델 이름>
python3 tools/w2/observe.py call c3-codex-pos <Codex 전체 모델 이름>
python3 tools/w2/observe.py call c3-codex <Codex 전체 모델 이름>
python3 tools/w2/observe.py call k46-codex <Codex 전체 모델 이름>
python3 -m app.server --check-config <live.json> --data-dir <새-원장>
```

소진한 상태 폴더를 다시 승인해 상한을 늘리지 않는다.

## 남은 것

- 앱에서 strict 정책(`independent_only`)으로 두 참여자를 부르는 실제 실행 — 독립 정족수 충족 표시까지.
- 실제 CLI 중도 취소(V04-03의 마지막 조건).
- 공통 자료 속 지시문: 자료 이름 규칙은 `AGENTS.md`·`CLAUDE.md`라는 이름을 허용한다. Codex는 자료 폴더를 작업 폴더로 쓰지 않고, Claude는 `--add-dir`의 CLAUDE.md를 기본으로 싣지 않지만, 자료 안의 지시문(프롬프트 주입)은 시험하지 않았다.
- Codex 메모리 기능을 값으로 고정하기(`features.memories=false`), Windows Codex 경로(쓰지 않음, 2절 15)는 바꾸지 않았다.
- 사용자 전역 CLAUDE.md·자동 메모리를 합성 설정 폴더에 심어 보는 대조(로그인 파일 복사가 필요해 하지 않았다).
