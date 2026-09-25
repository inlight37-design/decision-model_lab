# ChatGPT·Codex 플러그인과 참여자 표면 (2026-09-25)

작성: claude 세션(Claude 데스크톱 앱, `aux-pc` Windows, WSL `Ubuntu-24.04`). 기준 main `a3e4672`(PR #63 병합). **모델 호출 없음.** 실제 로그인 폴더를 연결한 모델 없는 조회는 NEXT-SESSION 2절 22의 상시 승인에 따른다(E·E2와 같은 방식). 인증 파일은 읽지 않았다.

## 왜 봤나

사용자가 [카드 #59](https://github.com/inlight37-design/decision-model_lab/issues/59)를 ChatGPT에 맡기면서 GitHub 플러그인을 붙였다(`+` 버튼 또는 `@GitHub`). 브라우저·컴퓨터 조작 플러그인도 붙일 수 있다고 알려 왔다. ChatGPT는 카드 목록을 읽고 #59에 "읽음: #59, #60, #61" 댓글을 남겼다(GitHub에서 확인). 플러그인은 ChatGPT와 Codex가 같은 목록을 쓴다. 그래서 계정에 설치한 플러그인이 **우리 앱의 Codex 참여자**(눈을 가리고 답하는 쪽)에게 따라 들어가는지 확인했다.

## 공식 문서에서 읽은 것

- [Plugins](https://learn.chatgpt.com/docs/plugins): 플러그인은 스킬·MCP 서버·브라우저 확장·훅을 묶는다. ChatGPT(웹·데스크톱·모바일)와 Codex(데스크톱 앱, CLI의 `/plugins`)가 같은 공개 목록을 쓴다. 설치한 뒤에는 그냥 요청하면 알맞은 도구를 고르고, `@`로 부르면 그 플러그인을 확실히 쓴다. Codex 쪽에서 돌 때는 그 호스트의 샌드박스·승인 정책을 따른다.
- [Computer Use](https://learn.chatgpt.com/docs/computer-use): ChatGPT **데스크톱 앱**의 Work·Codex에서 macOS·Windows의 화면을 보고 조작한다. Windows에서는 활성 데스크톱에서 돈다.
- [Browser](https://learn.chatgpt.com/docs/browser): Codex CLI와 IDE 확장에는 없고 ChatGPT 데스크톱 앱의 내장 브라우저다. 사이트 로그인이 필요한 ChatGPT Work 작업은 클라우드의 별도 컴퓨터에서 도는 브라우저를 쓴다고 적는다.
- [설정 참조](https://learn.chatgpt.com/docs/config-file/config-reference): `features.remote_plugin` — 원격 플러그인 목록, 기본 켜짐. 플러그인별 `plugins.<plugin>.enabled`와 플러그인 MCP 서버별 설정이 있다.

## 조회와 결과

[`probe.py`](probe.py)는 참여자 계획과 같은 격리·연결·`-c` 값으로 `codex app-server`를 띄우고 `skills/list` → `mcpServerStatus/list` → `app/installed` → `plugin/list`만 물었다. 대화·차례는 시작하지 않았다. 대조는 `features.apps=false` 하나만 뺐다(`--control`).

| Codex 0.156.1, aux-pc-wsl | 참여자 계획 | 대조: 연결 앱 끄기만 뺌 |
|---|---|---|
| 스킬 | Codex 기본 6개 | 기본 6개 |
| MCP 항목(서버와 그 도구의 이름) | 0 | 371 |
| 연결 앱: 설치·켜짐·호출 가능 | 9 · 0 · 0 | 9 · 9 · 9 |
| 설치·켜진 플러그인 | 넷(GitHub·Google Drive와 기본 플러그인 둘) | 같음 |
| 종료 | exit 0, 자손 종료 확인 | exit 0, 자손 종료 확인 |

E2의 [모델 입력 렌더링](../../../tools/w2/codex_prompt_input.py)(`--real-home`)도 다시 돌렸다. 항목별 글자 수와 실제·합성 HOME의 줄 차이 종류·개수가 [E2 기록](../2026-09-25-context-independence/model-free.json)과 똑같았다. 지시문 묶음은 없었다.

**판단:** 계정에 플러그인이 설치·켜져 있어도, 지금 참여자 계획에서는 플러그인의 도구·스킬이 참여자에게 닿지 않았다. 다만 이것은 지금 설치된 플러그인이 연결 앱을 통해서만 도구를 준다는 관측에 기댄다. 스킬이나 자체 MCP 서버를 가진 플러그인이 설치되면 달라질 수 있고, 준비 조회는 그것을 모른다. 그래서 참여자에게 플러그인을 명시적으로 끄거나 실행 전에 표면을 검사하는 일을 [카드 #64](https://github.com/inlight37-design/decision-model_lab/issues/64)로 남겼다.

## 협업 규칙에 보탠 것

- ChatGPT 세션은 GitHub 플러그인을 붙이면 이슈를 읽고 댓글을 달 수 있다(#59에서 확인). 붙이는 쪽이 확실하다.
- ChatGPT 데스크톱 앱에서 컴퓨터 조작·브라우저 플러그인을 쓴 세션은 "GitHub만 본다"가 아니다. 접근 범위에 표면과 붙인 플러그인을 적고, 사용자 PC 규칙을 따른다. [AGENTS.md](../../../AGENTS.md)와 [협업 규칙](../../COLLABORATION.md) 1절에 적었다.

## 한계

- 앱 서버의 표면이고 `exec`의 표면을 직접 센 것은 아니다(E 기록과 같은 한계). 같은 실행 파일·`-c` 값·연결이다.
- `plugin/list`는 문서가 개발 중이라고 적은 메서드다. 모양이 바뀌면 조회를 고쳐야 한다.
- 플러그인이 스킬을 안 싣는 이유(플러그인에 스킬이 없는지, 연결 앱 끄기가 막는지)는 가르지 않았다.
- 연결 앱은 ID를 적지 않고 개수만 적었다. 공개 카탈로그의 다른 항목은 옮기지 않았다.
