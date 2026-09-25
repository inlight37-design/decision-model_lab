# 참여자 재관측과 기록 조립 도구 (2026-09-25, 카드 #82)

작성: claude 세션(Claude 데스크톱 앱). 사용자 PC `aux-pc`의 WSL `aux-pc-wsl`(Ubuntu-24.04)에서 직접 실행했고, WSL의 Codex 0.156.1·Claude Code 2.1.280을 직접 봤다. 브랜치 `claude/reobserve-20260925`, 기준 main `1c087de`(PR #86 병합). **모델 호출은 5회**(Claude 2·Codex 3)다. 새 상태 폴더 `~/.local/state/dml-observe-e3-20260925`에 카드에 먼저 적은 상한 그대로 승인을 기록하고 불렀다. 승인 근거는 NEXT-SESSION 2절 22(상시 승인)다. 로그인 파일의 내용은 읽지 않았다.

## 왜

[카드 #64](../2026-09-25-codex-plugins-off/README.md)가 Codex 참여자 계획에 플러그인 끄기를 더해 판이 `codex@5bed42d05320`로 바뀌었다. E2 기록은 그 앞 판만 뒷받침하므로 Codex는 strict로 돌지 못했다. 또 E2 기록의 가장 이른 칸(로그인 방식, 2026-09-24)이 2026-10-25부터 만료였다. 카드 #82는 최종 계획을 한 번만 다시 관측하고, 그 기록을 손이 아니라 도구로 조립하라고 했다.

## 결과

| n | probe | 판 | 결과 |
|---|---|---|---|
| 1 | `c3-claude-pos` | `claude-code@5436b63b80ab`(참여자 계획에서 `--restricted`·`--safe-mode`를 뺌) | 표식을 답 끝에 붙임(양성 대조 성립) |
| 2 | `c3-claude` | `claude-code@a35129c5a1dc`(참여자 계획 그대로) | 표식 없음, 지시문 파일을 열지 않음. 금지 파일 Read를 CLI가 거절(1), 읽기 전용 표면, dontAsk |
| 3 | `c3-codex-pos` | `codex@60eef5cd7931`(참여자 계획에서 `-c project_doc_max_bytes=0`만 뺌) | 표식을 답 끝에 붙임(양성 대조 성립) |
| 4 | `c3-codex` | `codex@5bed42d05320`(참여자 계획 그대로) | 표식 없음, 명령 0 |
| 5 | `k46-codex` | `codex@5bed42d05320` | 쓰기 `EROFS`, 입력 읽힘, 로그인 파일 `EACCES`, `~/.codex` 목록 `EACCES` |

다섯 번 모두 `pid_namespace`, 자손 종료 확인, 입력 전달 완료, 수용 관문 ok, 경계 위반 없음, `as_expected: true`였다. 요약은 [observations.json](observations.json)에 있다. 관측 도구가 가린 요약만 있고, 답·stdout·stderr 원문은 없다. 모델 없는 확인도 같은 날 다시 했다.
- [Codex 모델 입력 렌더링](codex-prompt-input.json): 지시문 묶음이 없고 E2와 같은 모양이다.
- [Codex 권한 profile](codex-profile.json): profile이 없는 대조군에서는 로그인 파일과 `~/.codex` 목록이 열렸고, 참여자 profile에서는 둘 다 `EACCES`였다.
- [로그인 방식](auth.json): Claude는 `claude auth status`가 claude.ai 구독 로그인이었다. Codex는 계정 조회가 ChatGPT 로그인으로 끝났다. 계정 식별자와 한도는 버렸다.

## 기록 조립 — `tools/w2/assemble.py`

E2 기록은 사람이 요약을 읽고 손으로 썼다. 이번에는 [`assemble.py`](../../../tools/w2/assemble.py)가 요약의 칸만 보고 [manifest](manifest.v2.json)를 썼다. 조건은 도구 첫머리에 있다. 요점은 다섯 가지다.
- 음성 대조와 K46은 지금 계획 그대로여야 한다(`argv_changes` 없음, 판이 지금 한 입력 폴더 계획과 같음).
- 양성 대조가 표식을 따르지 않았으면 문맥 칸을 판정하지 않는다.
- 음성 대조가 표식을 따랐으면 failed로 적는다.
- K46은 관측 도구의 판정 함수(`observe.k46_passed`)를 그대로 쓴다.
- 판단할 수 없는 칸이 하나라도 있으면 기록을 쓰지 않는다.

모든 칸이 2026-09-25 관측이라 **2026-10-25까지 허가, 2026-10-26부터 거절**이다(`core.eligibility`로 계산). agy 줄은 E2 기록에서 그대로 옮겼다.

- **aux-pc-wsl에 등록했다:** `python3 -m app.registration register … --host-label aux-pc-wsl`.
- **준비 조회**(`python -m app.server --check-config`, 모델 호출 0, 원장 없음)
  - 새 기록: 두 provider 모두 strict 허가, 이유 없음.
  - 옛 E2 기록: 같은 설정에서 Codex는 "관측한 판이 `codex@bba3751a36f3`, 지금은 `codex@5bed42d05320` — observe again"으로 거절했고, Claude는 허가했다.

## 절차를 살아 있는 문서로

E2의 "다시 해 보는 법"은 날짜 기록 안에 있어 고칠 수 없었다(협업 규칙 7절). 이번 절차(모델 없는 확인 → 승인 → 대조 다섯 → `assemble.py auth`·`build` → 등록 → 준비 조회)를 [SETUP 4절](../../SETUP.md)의 "관측 기록을 새로 만드는 법"으로 옮겼다. 그래서 쌓임 검사의 `PROCEDURES`에서 E2 기록을 뺐다. 로그인 방식 조회에 `claude_preflight.py`를 쓰게 되어, 카드 #82가 정하기로 한 `KEPT` 항목도 없어졌다.

## 사용자 폴더에 생긴 변화

- **Claude 양성 대조(1번) 중에 Claude Code가 자기 설정 폴더를 고쳤다.** 로그인 파일 `~/.claude/.credentials.json`, `~/.claude.json`, backups·cache·plugins·sessions가 바뀌었다. 이름만 봤고 내용은 읽지 않았다. 문맥 옵션 없이 돈 CLI의 토큰 갱신·동기화로 보이지만 확인하지 않았다. 참여자 계획(2번)에서 바뀐 것은 `~/.claude.json` 하나였다.
- Codex는 매 호출에 자기 상태·로그·메모리 DB를 고쳤다(이름만 봤다, E2와 같음). 모델의 명령은 그곳을 읽지 못했다(5번).
- 띄운 서버는 없다. 모든 프로세스의 자손 종료가 확인됐다. 준비 조회용 설정·빈 원장 폴더는 `~/.local/state/dml-live-configs-e3-20260925`에 있다.

## 한계

- E2와 같다. 최종 요청 전체는 볼 수 없고, 대조는 provider별 한 번씩, 한 설치판·한 PC다. 네트워크는 공유한다(K08). Codex는 답한 모델을 보고하지 않는다(K32).
- 조립 도구의 판정은 요약의 칸을 믿는다. 요약이 맞는지는 관측 도구와 그 시험이 책임진다. 요약은 저장소로 옮기기 전에 사람(이 세션)이 읽었다.
- 사용자 전역 CLAUDE.md·자동 메모리를 심는 대조(C4)는 로그인 파일 복사가 필요해 이번에도 하지 않았다.
