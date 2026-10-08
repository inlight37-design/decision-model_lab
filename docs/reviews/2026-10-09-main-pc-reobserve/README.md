# 주 PC 재관측 — main-pc-wsl (2026-10-09)

[2026-09-26 기록](../2026-09-26-main-pc-observe/README.md)이 2026-10-27부터 만료되기 전에, 같은 주 PC의 WSL(배포판 `Ubuntu-24.04`, 이름표 `main-pc-wsl`)에서 [SETUP 4절](../../SETUP.md)의 절차대로 다시 관측한 기록이다. 기록은 [manifest.v2.json](manifest.v2.json) 하나이고, 이 PC에 등록했다.

- **관측:** 이 PC의 claude 세션(합본 재평가를 돌린 세션, 2026-10-08 UTC 저녁 = 2026-10-09 KST). 모델 호출은 행동 대조 다섯 번(Claude 2·Codex 3)이고 새 상태 폴더에 그 상한을 먼저 적었다(인계 2절 22의 상시 승인과 사용자의 "나머지 다 일시키면" 요청). 다섯 번 모두 기대대로였고 `tools/w2/assemble.py build`가 두 provider의 다섯 칸을 모두 observed로 조립했다.
- **판·계획·모델:** Codex 0.156.1·Claude Code 2.1.280(옛 기록과 같음), 계획 `codex@5bed42d05320`·`claude-code@a35129c5a1dc`(같음), 요청한 모델 `gpt-6-luna`·`claude-sonnet-5`. agy 줄은 옛 기록에서 그대로 옮겼다. 옛 기록과 다른 칸은 날짜(`observed_at`·`updated_at`)와 출처 줄뿐이다.
- **모델 없이 먼저 본 것:** `codex_prompt_input.py --real-home` — 참여자 값으로 렌더링한 입력에 지시문 블록이 없다(합성 HOME·실제 HOME 모두). `codex_profile.py --real-home` — 권한 profile이 로그인 파일과 `~/.codex` 목록을 EACCES로 막고(profile 없는 대조군은 열림), 없는 profile은 연결 전에 거절한다. 네트워크 없는 격리의 exec는 모델에 닿지 못해 제한 시간으로 끝났다(기대대로). 로그인 파일의 크기·수정 시각은 전후 같았다. `~/.codex/hooks.json`은 없다(S4).
- **등록·준비 조회:** `python3 -m app.registration register … --host-label main-pc-wsl` 뒤 `status`가 "registered on this machine". `python3 -m app.server --check-config`(새 기록, 새 원장)가 두 provider 모두 `eligible: true`, 이유 없음, 모델 호출 0.
- **허가 기간:** 모든 칸이 2026-10-09 관측이라 **2026-11-09부터** 준비 조회가 거절한다(`core.eligibility`로 11월 8일·9일을 계산해 확인). 그 전에 이 PC에서 다시 관측한다.
- **한계:** 대조마다 호출 한 번, 한 판·한 PC다. 네트워크는 공유한다(K08). 대조 요약·`auth.json`·답 원문과 모델 없는 검사의 출력은 저장소로 옮기지 않았다 — 이 PC의 WSL 상태 폴더에 있다. 다른 기기에서 이 기록을 등록하지 않는다. 앱 아이콘은 이 기기에 등록된 가장 새 기록을 고르므로 다시 만들 필요가 없다.
