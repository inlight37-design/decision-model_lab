# design — 셸의 디자인 시스템 `Ledger`

앱 1층(데스크톱 셸)의 토큰과 컴포넌트. 브랜드북은 [`project/README.md`](project/README.md)부터 읽는다.

## 화면이 쓰는 모양은 island-ui다

앱 화면(`app/static/index.html`)은 2026-09-25부터 사용자가 [ai_unslop](https://github.com/inlight37-design/ai_unslop)의 실험(exp-002~010)을 거쳐 고른 **island-ui**(둥근 섬·알약·테마 세 벌·애플식 움직임)를 쓴다. 부품은 [`app/static/island-ui/`](../app/static/island-ui/README.md)에 그대로 옮겼다. 사용자는 이 브랜드북의 첫 모양(괘선·2–3px 모서리)을 "네모네모하고 색이 우중충하다"며 기각했다.

그래서 이 폴더의 **의미 규칙**(아래 1·2 — 미검증이 검증처럼 보이면 안 된다, 전부 보여주지 않는다)은 그대로 화면의 규칙이고, **모양 규칙**(3 괘선)과 `tokens.json`의 값은 화면에 쓰지 않는다. 브랜드북과 아티팩트는 island-ui로 옮기지 않는다([인계](../NEXT-SESSION.md) 2절 25, 2026-09-27) — island-ui의 원본은 ai_unslop에 있고, 옮기면 같은 모양의 사본이 하나 더 생긴다.

## 이 폴더와 아티팩트의 관계

시스템은 claude.ai 아티팩트로 **발행**되고(미리보기가 실제로 렌더링된다), 이 폴더는 그 **소스 미러**다.

| | 역할 |
|---|---|
| `design/project/` | 소스. Git 이력·diff·CI 검사가 여기에 붙는다 |
| [아티팩트](https://claude.ai/artifact/8tq8q5P8Pj7bpUtCF77FZA) | 발행본. 사람이 눈으로 보는 곳 |

경로는 **1:1로 대응한다.** `design/project/tokens.json` → 아티팩트의 `project/tokens.json`.

미러를 둔 이유는 하나다. 잘못된 hex 값 하나가 토큰을 통째로 드롭시키는데(실제로 두 번 발생), 아티팩트만 있으면 그것을 잡아줄 회귀 검사가 없다. 이제 [`tools/validate_design_tokens.py`](../tools/validate_design_tokens.py)가 CI에서 돌아 문법 위반과 디센더가 잘릴 행간을 막는다.

## 고치는 순서

1. `design/project/` 안에서 편집한다
2. `python tools/validate_design_tokens.py` — 드롭될 값과 좁은 행간을 잡는다
3. commit
4. 아티팩트에 발행한다 (Artifact 도구, `url` = 위 링크, `root` = `design`, 파일은 `project/…` 경로 그대로)

아티팩트 쪽에서 먼저 고쳤다면 반대로 읽어 와 이 폴더에 반영하고 커밋한다. **두 쪽이 갈라진 채로 두지 않는다.**

## 왜 이 시스템이 이렇게 생겼는가

세 규칙이 나머지를 결정한다. 자세한 내용과 근거는 브랜드북에 있다.

1. **미검증이 검증처럼 보이면 안 된다** — 투표는 근거가 아니고, `unknown`은 `0`이 아니다
2. **전부 보여주지 않는다** — 근거를 다 펼치는 것과 사람이 더 나은 판단을 하는 것은 다르다 ([F28](../docs/architecture/v0.4/sources.json))
3. **채움이 아니라 괘선** — 알약 배지를 쓰면 네 상태가 같은 크기 색 덩어리가 되어 무게 차이가 사라진다

상태값이 실제로 어디서 오는지(그리고 왜 추가 비용이 거의 없는지)는 브랜드북의 "상태는 어떻게 정해지는가" 절에 있다.
