# island-ui — 화면의 모양·움직임 부품

사용자가 [ai_unslop](https://github.com/inlight37-design/ai_unslop) 저장소에서 실험을 거쳐 고른 화면 스타일(둥근 섬, 알약, 테마 세 벌, 애플식 움직임)의 부품이다. 그 저장소의 `skills/island-ui/`에서 **고치지 않고 그대로** 옮겼다(커밋 `4d90cb2` — 펼친 양식이 포커스 테두리를 자르던 것을 그쪽에서 고친 판).

| 파일 | 무엇 |
|---|---|
| `themes.css` | 색 토큰. `<html data-theme="light·glass·dusk">`로 바꾼다 |
| `base.css` | 글자 7단계·간격 8단계·모서리 토큰 |
| `motion.js` | 누름, 접기, 선택 표시, 버튼 → 패널, 따라오는 옆 단 |

[화면](../index.html)은 이 토큰과 함수만 쓴다. 서버는 이 세 파일만 `/island-ui/…`로 내보낸다(`app/server.py`의 `ASSETS`).

## 고칠 때

여기서 고치지 않는다. ai_unslop의 `skills/island-ui/`를 고치고 그쪽 검사(`python -m unslop_lab check`)를 통과한 뒤 세 파일을 다시 복사하고, 위 커밋을 바꾼다. 여기만 고치면 두 저장소의 스타일이 갈라진다. 글자 대비는 `tests/test_app_contrast.py`가 테마 세 벌에서 잰다.
