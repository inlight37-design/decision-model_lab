# Codex 참여자에게 플러그인 끄기 (2026-09-25, 카드 #64)

작성: claude 세션(Claude 데스크톱 앱, `aux-pc` Windows, WSL `Ubuntu-24.04`, Codex 0.156.1). 기준 main `2bcdd20`(PR #75 병합). **모델 호출 없음.** 실제 로그인 폴더를 연결한 모델 없는 조회는 NEXT-SESSION 2절 22의 상시 승인에 따른다(E·E2·[플러그인 기록](../2026-09-25-plugin-surface/README.md)과 같은 방식). 인증 파일은 읽지 않았다.

## 무엇을 바꿨나

Linux Codex 참여자 계획에 `-c features.plugins=false`를 더했다(`core.adapters.CODEX_PLUGINS_OFF`). 참여자 판이 `codex@bba3751a36f3`(E2가 관측한 계획)에서 **`codex@5bed42d05320`** 으로 바뀐다. Claude 계획은 그대로다.

**그래서 Codex는 재관측 전까지 strict로 실행되지 않는다.** E2 기록은 옛 판만 뒷받침하므로 준비 조회가 거절한다. 재관측은 [카드 #82](https://github.com/inlight37-design/decision-model_lab/issues/82)다 — 카드와 외부 검토(질문 5)가 권고한 대로, 참여자 계획을 먼저 바꾸고 최종 계획을 한 번만 관측한다.

## 왜 — 연결 앱 끄기는 플러그인 스킬을 막지 못했다

[플러그인 기록](../2026-09-25-plugin-surface/README.md)은 계정에 설치된 플러그인이 지금 참여자에게 닿지 않음을 봤지만, 그것은 "지금 플러그인이 연결 앱으로만 도구를 준다"는 관측에 기댔다. 스킬을 가진 플러그인이면 어떤지 합성 HOME에서 봤다([`control.sh`](control.sh), 결과 [`control-output.txt`](control-output.txt)). 표식 스킬 하나를 가진 로컬 플러그인을 로컬 마켓플레이스로 설치하고(`codex plugin marketplace add`, `codex plugin add`), `codex debug prompt-input`으로 **모델에 보이는 입력**을 렌더링해 표식을 셌다. 같은 결과가 두 번 나왔다.

| 설정(합성 HOME, 플러그인 설치·켜짐) | 표식 스킬이 모델 입력에 |
|---|---|
| 기본값 | 실림(양성 대조) |
| `features.apps=false` — 지금까지의 참여자 보호 | **실림** |
| `features.remote_plugin=false`(공식 설정 참조에 있는 키: 원격 플러그인 목록) | 실림 |
| `-c 'plugins."dml-probe@dml-local".enabled=false'` | 실림(까닭은 가르지 않았다) |
| **`features.plugins=false`** | **빠짐** |
| 연결 앱 끄기 + 플러그인 끄기 | 빠짐 |
| `config.toml`을 치운 상태(`--ignore-user-config`의 대용) | 빠짐 |

지금 참여자는 `exec --ignore-user-config`로 돌기 때문에 `config.toml`로 켜진 로컬 플러그인은 이미 싣지 않았을 가능성이 크다(마지막 줄). 그러나 그것은 플러그인이 켜진 상태를 어디에 두는지에 기댄 우연이다. 계정에서 설치한 원격 플러그인의 켜짐이 설정 파일 밖으로 옮겨 가도 참여자에게 닿지 않도록, 플러그인을 이름으로 끈다.

**키의 근거.** `features.plugins`는 [공식 설정 참조](https://learn.chatgpt.com/docs/config-file/config-reference)(2026-09-25 확인)에 **없다.** `codex features list`(0.156.1)에는 `plugins stable true`로 나온다. 뜻은 위 대조로만 확인했다. 판과 설치판이 바뀌면 준비 조회가 재관측을 요구하므로, 다음 판에서 키의 뜻이 바뀌면 재관측의 대조가 그것을 다시 본다. 플러그인 형식은 [Build plugins](https://developers.openai.com/plugins/build/plugins)(`plugin.json`, `skills/<이름>/SKILL.md`, 로컬 마켓플레이스 `.agents/plugins/marketplace.json`, 캐시 `~/.codex/plugins/cache/`)에서 읽었다.

## 실제 로그인 폴더에서 — 바뀐 계획

| 조회(참여자와 같은 격리·연결·`-c` 값) | E2 계획 | 바뀐 계획 |
|---|---|---|
| 앱 서버 표면([`surface.json`](surface.json), [조회 스크립트](../2026-09-25-plugin-surface/probe.py)) — 스킬 | Codex 기본 6개 | 같음 |
| MCP 항목 · 호출 가능한 앱 | 0 · 0 | 0 · 0 |
| 설치·켜진 플러그인 | 넷(GitHub·Google Drive와 기본 둘) | **없음** |
| 모델 입력 렌더링([`model-free.json`](model-free.json), [`codex_prompt_input.py`](../../../tools/w2/codex_prompt_input.py) `--real-home`) | [E2 기록](../2026-09-25-context-independence/model-free.json) | 합성·실제 HOME 모두 항목·글자 수·표식·줄 차이가 E2와 같음 |

지금 계정의 플러그인은 원래 모델 입력에 아무것도 싣지 않았으므로 입력은 그대로이고, 플러그인 목록만 비었다. 두 조회 모두 exit 0, 자손 종료 확인.

## 시험

- 참여자 argv에 이 값이 들어가고(`tests/test_core_adapters.py`, 실행 기록 `tests/test_app_cli_executor.py`), 합성 CLI는 이 값이 없는 계획을 받지 않는다.
- 옛 판을 되살리는 시험이 E2 판 `codex@bba3751a36f3`을 정확히 되살리고(`tests/test_core_contract.py`의 `e2_revision`), E2 기록은 그 판과 Claude 지금 판만 허가하며 **지금 Codex 판은 허가하지 않는다**(`tests/test_live_cli.py`).

## 한계

- 렌더링은 `debug prompt-input`이고 참여자의 `exec`가 아니다. `debug prompt-input`에는 `--ignore-user-config`가 없어 설정 파일을 치우는 것으로 대신했다.
- 합성 플러그인은 스킬 하나만 가졌다. 플러그인이 묶는 MCP 서버·훅은 따로 대조하지 않았다 — `features.plugins=false`가 플러그인 전체를 끈다는 것은 스킬과 설치 목록(`plugin/list`)으로만 봤다.
- 원격(계정) 플러그인이 스킬을 가진 경우는 합성으로 만들 수 없어 보지 않았다.
