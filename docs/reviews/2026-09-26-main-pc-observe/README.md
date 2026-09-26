# 주 PC 관측 기록 — main-pc-wsl (2026-09-26)

사용자의 주 PC `DESKTOP-T0UDE01` 안의 WSL(배포판 `Ubuntu-24.04`, 이름표 `main-pc-wsl`)에서 지금의 두 참여자 계획을 [SETUP 4절](../../SETUP.md)의 절차로 관측한 기록이다. 기록은 [manifest.v2.json](manifest.v2.json) 하나이고, 그 PC에 등록해 실제 모드의 허가에 쓴다.

- **관측:** 2026-09-26, 이 PC의 다른 claude 세션. 행동 대조 다섯 번(Claude 2·Codex 3)이 모두 기대대로였고, `tools/w2/assemble.py`가 두 provider의 다섯 칸을 모두 observed로 조립했다. 판은 Codex 0.156.1·Claude Code 2.1.280, 계획은 `codex@5bed42d05320`·`claude-code@a35129c5a1dc`, 요청한 모델은 `gpt-6-luna`·`claude-sonnet-5`. agy 줄은 [2026-09-25 기록](../2026-09-25-reobserve/manifest.v2.json)에서 그대로 옮겼다.
- **올린 경위:** 만든 세션은 공개 저장소라 사용자에게 묻기로 하고 커밋하지 않았다. 사용자가 권고가 붙은 판단을 AI에 맡긴 뒤([인계](../../../NEXT-SESSION.md) 2절 25) 2026-09-27 claude 세션이 바이트 그대로 올렸다(sha256 `23c71bf0735e976f…`).
- **2026-09-27에 올린 세션이 본 것:** 파일에 계정 신원·사용자 이름·로컬 경로가 없다. 그 PC의 WSL 상태 폴더에 남은 원자료로 `assemble.py build`를 다시 돌린 결과가 이 파일과 같다 — 다른 칸은 `updated_at`(도구가 그날 날짜를 적는다)뿐이다. 그 배포판에서 `python3 -m app.registration status`가 "registered on this machine"이고, 설치된 CLI 판이 기록과 같다. 모델은 부르지 않았다.
- **허가 기간:** 모든 칸이 2026-09-26 관측이라 2026-10-27부터 준비 조회가 거절한다(30일). 그 전에 그 PC에서 다시 관측한다.
- **한계:** 대조마다 호출 한 번, 한 판·한 PC다. 네트워크는 공유한다(K08). 대조 요약·`auth.json`·답 원문은 저장소로 옮기지 않았다 — 그 PC의 WSL 상태 폴더에 있다. 다른 기기에서 이 기록을 등록하지 않는다.
