# V04-01 결과 — `<기기 이름표>`

이 파일을 `hosts/<기기 이름표>/RESULTS.md`로 복사해 채운다. 절차는 [README](README.md)다. 계정 이메일·조직 ID·토큰·API 키 값은 어디에도 적지 않는다.

- 수행일: YYYY-MM-DD
- 수행자: (사용자 / AI 세션 이름)
- 저장소 commit: (40자 SHA)
- tier 1 manifest: `manifest.json` (`--validate` 결과: PASS / INVALID)

## 설치와 로그인

| 도구 | 설치 방법 | 버전 (`--version`) | 로그인 방식 (확인 명령과 결과) | 비고 |
|---|---|---|---|---|
| Claude Code | | | `/status`: | 자동 업데이트 여부 |
| Codex | | | `codex login status`: | Windows 샌드박스: elevated / unelevated / 미확인 |
| Antigravity | | | 미문서화 | |

과금 경로를 바꾸는 환경변수 (tier 1 manifest의 `env_presence`에서 `true`인 것): 없음 / (이름만)

## tier 2 관측

"기대"는 문서가 말하는 동작이다. 결과가 다르면 거기서 멈추고 이 표에 적는다.

| 번호 | 도구 | 실행한 명령 (그대로) | exit | 관측한 것 | 출력 파일 | 기대와 같은가 |
|---|---|---|---|---|---|---|
| P1 | Claude Code | | | 세션 ID: · 사용량 필드: | `tier2/P1-claude.txt` | |
| P1 | Codex | | | | `tier2/P1-codex.txt` | |
| P1 | Antigravity | | | | `tier2/P1-agy.txt` | |
| P2 | Claude Code | | | 인증 실패 / 성공(→ 멈춤) | `tier2/P2-claude.txt` | |
| P3 | Claude Code | | | 모델 호출 전 거절 / 응답 나옴 | `tier2/P3-claude.txt` | |
| P3 | Codex | | | | `tier2/P3-codex.txt` | |
| P3 | Antigravity | | | | `tier2/P3-agy.txt` | |
| P4 | Claude Code | | | 로드된 tools·mcp_servers·plugins: · `~/.claude/CLAUDE.md`: 있음/없음 | `tier2/P4-claude.txt` | |
| P4 | Codex | | | 설정 무시 후 로그인 경로: | `tier2/P4-codex.txt` | |
| P4 | Antigravity | — | — | 미확인 | — | — |
| P5 | 세 도구 | `/model`, `agy models` | | 상급 모델 이름: | | |
| P6 | (선택) | | | 종료 확인 / UNKNOWN · 남은 프로세스: | | |
| P7 | Codex | — | — | 문서 경로 있음, 호출 미시험 | — | — |

## 정책 확인

| 항목 | 문서 | 확인일 | 상단 공지·해당 문구 요약 | 결론 |
|---|---|---|---|---|
| Claude 구독으로 Claude Code | E04 | | | |
| `claude -p`·SDK 구독 차감과 보류 공지 | E05·F18 | | | |
| Codex ChatGPT 로그인과 API 과금 | E01 | | | |
| Antigravity 크레딧 자동 사용 | E09 | | | 꺼짐 / 켜짐 / 미확인 |
| Gemini CLI 소비자 인증 종료설 | 원문 URL | | | 확인 / 반박 / 미확인 |
| 요금제별 동시 기기·세션 제한 | | | | 미확인이면 그대로 |
| 구독 경로가 닫혔을 때의 대안 | — | — | — | 사용자 결정: |

## 판정

| 질문 | 결론 | 근거 (위 번호) |
|---|---|---|
| V04-03 진행 가능한가 | 예 / 아니오 / 보류 | |
| Q1: ACP 우선인가 exec 우선인가 | | |
| blind 초안과 구독 인증을 함께 얻는 조합 | 도구별로 | P2, P4 |
| 잘못된 제한을 무시하고 실행하는 경로 | 없음 / 있음(도구) | P3 |

## 열린 문제

-
