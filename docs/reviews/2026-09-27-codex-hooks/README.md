# 2026-09-27 — Codex 사용자 훅(`~/.codex/hooks.json`) 무모델 관측과 참여자 계획의 거절(S4)

작성: claude 세션(Claude Opus 5.5), 사용자 PC `DESKTOP-T0UDE01`의 WSL `Ubuntu-24.04`. [카드 #111](https://github.com/inlight37-design/decision-model_lab/issues/111)([리뷰 통합](../2026-09-26-review-consolidation/README.md) 5절 S4)의 관측 부분이다. **모델 호출 0.** 로그인 파일이 없는 합성 HOME만 썼고, 사용자의 실제 `~/.codex`는 연결하지 않았다. 실제 HOME에서는 세 파일(`hooks.json`, `AGENTS.md`, `AGENTS.override.md`)이 있는지만 봤고 셋 다 없었다(내용은 읽지 않음).

## 무엇을 봤나

[`probe.py`](probe.py)를 WSL에서 돌렸다. 결과 요약은 [`result.json`](result.json)이다.
- Codex 0.156.1의 `codex features list`에서 `hooks`는 stable·켜짐이다.
- 합성 HOME에 세 경우를 두었다: 훅 파일 없음, 표식 훅(명령 훅이 표식 파일을 만듦), 깨진 JSON.
- 각 경우에 **참여자 argv 그대로**(`--ignore-user-config`·`--ignore-rules`·`--ephemeral` 등, `build_spec`) `codex exec`를 돌렸다. `codex debug prompt-input`도 돌렸다.
- 환경은 HOME·PATH·LANG만 두었다(과금 환경변수 없음).

| 경우 | `exec`(참여자 argv) | `debug prompt-input` |
|---|---|---|
| 훅 파일 없음 | 로그인 없음으로 끝남(종료 1), 훅 오류 없음 | 종료 0, 훅 오류 없음 |
| 표식 훅 | 종료 1, **표식 파일 없음** | 종료 0, 표식 파일 없음 |
| 깨진 JSON | 종료 1, **"failed to parse hooks config …/.codex/hooks.json"** | 종료 0, 훅 오류 없음 |

**확인한 것.** Codex 0.156.1은 참여자 옵션(`--ignore-user-config` 포함)으로 `exec`를 돌려도 `~/.codex/hooks.json`을 **읽는다**. 깨진 파일에서 그 파일 경로를 이름으로 든 해석 오류가 났다. 이 옵션이 사용자 훅 파일을 막는다고 볼 근거는 없다.

**확인하지 못한 것.**
- 훅이 참여자 실행 중에 실제로 **실행되는지**는 미확인이다. 표식 훅은 실행되지 않았다. 하지만 로그인이 없어 세션이 모델 호출 전에 끝났을 수 있다.
- 바이너리 문자열에 `trusted_hash`가 있어, 신뢰하지 않은 훅을 건너뛰는 장치가 있을 수도 있다. 실제 로그인 HOME으로 보는 진단은 사용자 허락 뒤에만 한다(카드).
- 적은 훅 모양(`hooks` → 사건 → `matcher`·`hooks`·`type: command`)은 바이너리 문자열에서 짐작한 것이다. 표식 훅 경우에 오류가 없었다고 해서 그 모양을 Codex가 알아봤다는 뜻은 아니다 — 모르는 칸을 오류 없이 무시했을 수도 있다. 이 관측이 보인 것은 깨진 JSON을 읽고 알린다는 것까지다.
- `login_or_auth_mentioned`는 단어가 있는지만 보는 거친 표시다. `prompt-input`에서는 지시문 글에 걸렸을 수 있다.

## 그래서 한 것

같은 PR에서 고쳤다.
- **참여자 계획 거절.** `hooks.json`이 있으면 Codex 참여자 계획을 거절한다(`core.adapters.codex_user_hooks` → `app.cli_executor._check_context`).
  - 없음이면 통과한다. 빈 파일·내용 있는 파일·링크·폴더·확인 불가는 거절한다.
  - 빈 지시문 파일과 달리 빈 훅 파일도 거절한다 — 빈 훅 파일을 Codex가 건너뛰는지는 보지 않았다.
  - 이유에는 파일 이름만 쓰고 내용은 읽지 않는다.
- **검사 시점.** 계획(예약 전)을 만들 때 가장 먼저 보고, 실행 직전에 다시 본다.
  - 준비 조회와 관측 도구(`tools/w2`)도 같은 계획 검사를 지난다. 관측 도구는 `isolation.run`을 직접 불러 실행 직전 재검사는 지나지 않는다.
  - 설정 점검(`tools/setup/check_setup.py`)도 같은 함수·같은 위치(`$HOME/.codex` — 참여자는 `CODEX_HOME`을 받지 않는다)로 보고 경고한다.
- **막지 못하는 것.** 이 검사는 **파일 하나**만 본다. 설정 안의 훅, 프로젝트·플러그인·관리형 훅까지 막았다는 뜻이 아니다.
  - 참여자는 연결 앱·플러그인을 끄고 빈 작업 폴더에서 돈다([플러그인 끄기](../2026-09-25-codex-plugins-off/README.md)). 하지만 다른 훅 층은 따로 대조하지 않았다.
- **재관측.** 참여자 argv는 바뀌지 않았으므로 판(revision)도 그대로다. 다음 재관측(인계 4절 2)에서 이 검사와 훅 표면을 함께 확인한다.
