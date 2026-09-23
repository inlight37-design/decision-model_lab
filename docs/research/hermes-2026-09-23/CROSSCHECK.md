# Claude 교차 확인 — 2026-09-23

작성: claude (Claude Opus 5.5). 접근 범위: **보조 PC(`aux-pc`)의 로컬 checkout.** Hermes는 이 조사와 같은 `c0d7294769a38c17ceae51d8f7995e66e1dcae27`을 저장소 밖 임시 폴더에 shallow fetch해 `grep`·`sed`로 읽었다. Hermes를 설치하거나 실행하지 않았고 모델을 부르지 않았다. [요약](README.md) · [상세 분석](ANALYSIS.md) · [근거](EVIDENCE.md)

**방법의 한계:** 이 조사의 요약(README)을 먼저 읽은 뒤 코드를 봤다. 완전한 blind 검토가 아니다.

이 파일은 ChatGPT 조사의 **원문을 고치지 않고** 옆에 붙이는 확인 기록이다. 결론 — Hermes를 기반으로 삼지 않고 실행기 신뢰성·필요할 때 불러오는 절차·범위 있는 기억을 골라 가져온다 — 에 동의한다.

## 1. 조사의 코드 주장 대조

모두 같은 판본에서 일치했다. 위치는 `NousResearch/hermes-agent` 기준 경로다.

| 주장 | 결과 | 위치 |
|---|---|---|
| 자식 agent는 기억·지시문 파일 없이 시작하지만 부모의 `prefill_messages`를 받는다 (H07) | 일치 | `tools/delegate_tool.py:237,241` |
| Codex 권한 기본 매핑에 `workspace-write`가 있다 (H08) | 일치 | `agent/transports/codex_app_server_session.py:33-37` |
| 표식 없는 알림을 호환성 때문에 받아들인다 (H08) | 일치 | 같은 파일 `:88-101` |
| 자식 프로세스 snapshot은 `psutil`이 없으면 빈 목록이다 (H09) | 일치 | `agent/transports/codex_app_server.py:53-60` |
| `codex app-server` 실행 환경이 provider 자격증명을 물려받는다 (H09) | 일치 | 같은 파일 `:105` (`inherit_credentials=True`) |
| 세션 검색은 LLM을 부르지 않고 긴 메시지를 자른다 (H05) | 일치 | `tools/session_search_tool.py` — `call_llm` 없음, `:248` `content_truncated` |
| 같은 이름의 skill은 먼저 찾은 것이 이긴다 (H03) | 일치 | `tools/skills_tool.py:185-216` |
| 알 수 없는 MoA 주기 값은 `user_turn`으로 보정된다 (H12) | 일치 | `hermes_cli/moa_config.py:58-61` |

## 2. 조사에 없던 것 (코드 관측)

| # | 관측 | 위치 | 우리에게 뜻하는 것 |
|---|---|---|---|
| C1 | **기본값으로 다른 CLI의 로그인을 빌려 쓴다.** `auth.adopt_external_logins: True`. Claude Code의 `~/.claude/.credentials.json`(macOS는 Keychain)과 Codex의 `~/.codex/auth.json`을 읽는다. Anthropic 경로는 토큰을 직접 갱신하고 추론 요청에 `claude-code/` user agent를 쓴다 | `hermes_cli/config_defaults.py:1717`, `agent/credential_sources.py:11-13`, `agent/anthropic_credentials.py:5,41-42` | aux-pc에는 두 파일이 모두 있다(tier 2 manifest의 `config_presence`). **이 PC에 Hermes를 기본 설정으로 설치하면 두 로그인을 가져다 쓴다.** 공식 provider 문서상 Claude 경로는 추가 사용량으로만 청구된다. 인증은 native CLI가 소유한다는 [상세 분석 §1](ANALYSIS.md)의 원칙이 옳고, 사용자 개인 설치 시 주의 사항으로 인계한다 |
| C2 | **마감이 지나도 답 텍스트가 있으면 완료로 받아들인다.** `accept_final_text_at_deadline=True` | `agent/transports/codex_app_server_session.py:541,592-597` | [상세 분석 §7](ANALYSIS.md)이 "가장 구체적인 실행기 참고점"으로 꼽은 파일에 있는, **옮기면 안 되는 동작**이다. [적용 계획](ADOPTION_PLAN.md)의 HF-06이 우리 쪽 요구를 이미 적었다. 이 줄이 그 fixture의 실제 반례다 |
| C3 | **보이지 않는 추가 호출과 승인 없는 쓰기가 기본값이다.** 매 턴 뒤 같은 모델로 기억·skill 저장 여부를 검토하는 fork(`background_review.enabled: True`), 기억과 사용자 프로필 켜짐, 기억 쓰기와 skill 변경의 `write_approval: False` | `hermes_cli/config_defaults.py:789,1286-1291,1455` | HP-03(보조 호출까지 같은 예산 장부)과 HP-06(자동 게시 금지)의 직접 근거다. 사용자 원칙 5(상태 표시에 자원 과소비 금지)와도 맞물린다 |
| C4 | **조용한 모델 강등을 권한다.** 기본 탑재 Claude Code skill이 `--fallback-model haiku`를 예시와 팁으로 싣는다 | `skills/autonomous-ai-agents/claude-code/SKILL.md:250,724` | D18의 반례다. adapter의 옵션 사전 검증에서 `--fallback-model`을 허용하지 않는다(HP-01, HF-09) |
| C5 | **Windows에서도 agent 셸은 PowerShell이 아니라 Git Bash다.** Git for Windows가 없으면 실행을 거부하고, WSL·System32의 `bash.exe`는 건너뛴다 | `tools/environments/local.py:456-510` | 하네스 제작사가 모델에게 bash를 주는 쪽을 택한 사례다. 아래 부록의 관측과 같은 방향이다 |

## 3. 판단

- C1–C5는 조사 결론을 바꾸지 않는다. **그대로 가져오면 안 되는 목록**을 코드 위치로 보강한다.
- 사용자에게 줄 실용 권고: Hermes를 개인적으로 써 본다면 `auth.adopt_external_logins`와 매 턴 검토를 끄고, 금액 상한을 건 별도 API 키로, 주 PC가 아닌 곳에서 쓴다. 우리 앱의 의존성으로 넣지 않는다.

## 부록: 같은 PC의 셸 출력 크기 (관측, 2026-09-23)

aux-pc, Windows PowerShell 5.1과 Git Bash에서 같은 일을 시켜 출력 바이트를 셌다. 사용자 질문("PowerShell이 토큰을 낭비하는가")에 대한 측정이다. 토큰 수가 아니라 바이트 수다.

| 상황 | PowerShell 5.1 | Git Bash |
|---|---|---|
| 없는 파일 조회 오류 | 343 B, 6줄 | 62 B |
| 외부 명령(`git`)의 stderr를 `2>&1`로 받음 | 286 B (`NativeCommandError`로 감쌈) | 32 B |
| `tools/` 목록 | 1,867 B (`Get-ChildItem`) | 255 B (`ls`) |

한국어 Windows의 PowerShell 오류 문장은 UTF-8로 받는 쪽에서 깨져 읽을 수 없었다. 우리 앱은 CLI를 셸 없이 직접 실행하므로 이 비용은 AI 작업 세션과 관측 스크립트에만 해당한다.
