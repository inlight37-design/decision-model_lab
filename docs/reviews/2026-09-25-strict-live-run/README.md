# strict 정책의 첫 실제 두 참여자 실행과 실제 CLI 중도 취소 — 2026-09-25

작성: claude 세션(Claude 데스크톱 앱). 사용자 PC `aux-pc`(hostname `DESKTOP-L6EA2UJ`)의 WSL `aux-pc-wsl`에서 앱 서버를 직접 띄워 HTTP API로 몰았다. Codex 0.156.1·Claude Code 2.1.280. 브랜치 `claude/strict-live-run-20260925`, 기준 main `d9af92b`(PR #49, [E2](../2026-09-25-context-independence/README.md) 병합). **모델 호출은 4회**(Codex 3: 참여·합성·취소 대상, Claude 1)이고, 두 새 원장의 고정 상한 안에서 불렀다. 승인은 NEXT-SESSION 2절 22다.

## 결론

1. **처음으로 앱에서 strict 정책(`independent_only`, 최소 2명)으로 두 실제 참여자를 불러 독립 정족수를 채웠다.** Codex·Claude 모두 실제 실행·수용·봉인 뒤 함께 공개됐고, 둘 다 "독립성 확인"으로 세어져 화면에 `독립 정족수 충족 — 독립성이 확인된 참여자 2명(최소 2명)`이 떴다. `--allow-context-unverified`는 쓰지 않았고 두 시도의 계획은 E2 manifest가 뒷받침하는 판(`codex@bba3751a36f3`, `claude-code@a35129c5a1dc`)이었다.
2. **처음으로 Codex가 실제 합성을 했다.** 같은 실행의 공개 초안을 Codex(참여자와 같은 계획)가 합쳤다. 인용 11개가 모두 초안과 글자 그대로 일치했고 원문 밖 추가 주장은 0개였다. 주장 4개 모두 일치 인용이 있고, 갈리는 점 1개·가장 강한 반례·미해결 2개를 보존했다. 사실 검증은 하지 않았다(`factual_check: not_performed`).
3. **실제 CLI를 실행 중에 취소했다(V04-03의 마지막 조건).** Codex 참여자가 `running`인 것을 본 직후 취소를 요청했다. 시도는 `process_cancelled`(SIGTERM, 종료 코드 -15)로 끝났고, PID namespace 안의 자손 전체 종료가 확인됐다. 예약한 호출 1회는 환불되지 않고 원장에 남았으며, 실행 자리와 미종료 수는 0으로 돌아왔다.
4. 두 실행 모두 서버를 끄고 포트가 닫혔으며, `app.server`·`codex`·`claude`·`bwrap` 프로세스가 남지 않은 것을 확인했다.

## 어떻게 했나

- 드라이버 [drive.py](drive.py): 새 원장 폴더가 아직 없어야 시작한다. 먼저 `--check-config`(모델 호출 없음)로 strict 허가를 확인하고, 서버를 새 세션으로 띄워 출력(원장 폴더의 로그 파일)에서 토큰을 읽고, API로 실행을 만들고 기다린 뒤, 끝나면 항상 서버를 끄고 포트가 닫혔는지 본다. 토큰과 HOME 경로는 요약에 남기지 않는다.
- 먼저 모의 서버로 두 흐름을 돌렸다(`--mock`, 모델 호출 없음). 그때 드라이버가 모의 모드의 합성 거절(400) 뒤에도 400초를 기다리는 결함을 찾아 고쳤다.
- 원장(설정의 상한이 첫 사용 때 고정된다): strict `~/.local/state/dml-live-strict-20260925`(전체 3 — Codex 2: 참여+합성, Claude 1), 취소 `~/.local/state/dml-live-cancel-20260925`(Codex 1). 각 provider는 빈 입력 폴더 하나를 받았다(공통 자료 없음).
- 모델: Codex `gpt-6-luna`, Claude `claude-sonnet-5`. 질문은 이 저장소의 주제에서 골랐다 — strict: 두 AI가 서로의 초안을 보지 않고 답하게 하는 시스템에서 그 독립성을 깨는 경로 셋과 확인 방법, 취소: 1부터 200까지의 소수를 설명과 함께 나열(취소할 틈을 두려고 긴 답을 청했다).

## 결과

원장에서 개수·판정만 뽑은 [ledger-summary.json](ledger-summary.json)과 드라이버가 출력한 [drive-output.json](drive-output.json). 초안·합성 원문과 서버 토큰은 원장 폴더에만 있다.

### strict 실행

| 항목 | 값 |
|---|---|
| 사건 순서 | run_created → drafting_started → 예약·시작 ×2 → draft_sealed ×2 → revealed → 예약(synthesis) → synthesis_started → synthesis_completed |
| Codex 참여자 | 수용, `pid_namespace`·자손 종료 확인·입력 전달 완료, 10.1초, 초안 576자, 입력 12,524(캐시 9,984)·출력 347, 제공 모델 미보고(K32) |
| Claude 참여자 | 수용, 같은 종료 확인, 34.0초, 초안 1,264자, 보고 모델 `claude-sonnet-5` 일치, stream에 계정 한도 사건 있음 |
| 정족수 | `independent_only`, confirmed 2·unverified 0, 충족 |
| Codex 합성 | 완료, 22.3초, 판 `codex@bba3751a36f3`(참여자와 같은 계획), 자손 종료 확인, 입력 13,865(캐시 9,984)·출력 1,051 |
| 합성 검사 | 인용 11/11 원문 일치, 추가 주장 0, 주장 4(모두 인용 있음), 갈리는 점 1, 반례 있음, 미해결 2 |
| 상한 | 3/3 사용(참여 2 + 합성 1) |

### 취소 관측

| 항목 | 값 |
|---|---|
| 사건 순서 | run_created → drafting_started → live_call_reserved → attempt_started → run_cancel_requested → attempt_rejected |
| 취소 직전 | 참여자 `running` |
| 끝난 모양 | `process_cancelled`, 종료 코드 -15, `pid_namespace`, `tree_confirmed_empty: true`, 입력 전달 완료, 사용량 보고 없음 |
| 실행 | 단계 drafting·관문 cancelled, 보고서 요청은 409(공개 전) |
| 회계 | 예약 1/1은 그대로(환불 없음), 실행 자리 0·미종료 0 |

## 한계

- 한 번씩 한 질문이다. strict 실행의 두 답과 합성이 좋은 답인지는 평가하지 않았다 — 인용 대조는 의미·사실 검증이 아니다(C·D 기록과 같다).
- 문맥 독립성은 [E2](../2026-09-25-context-independence/README.md)의 범위(이 PC·판·설치판·30일, 최종 요청 전체는 못 봄)를 그대로 가진다. 독립 정족수 충족은 그 기록 위의 판정이지 두 모델의 판단이 독립이라는 증명이 아니다.
- 취소는 시작 직후라 모델 요청이 공급자에 닿았는지는 알 수 없다(사용량 보고 없음). 예약은 보수적으로 1회로 남는다. 모델이 답을 쓰는 도중의 취소는 따로 보지 않았다.
- Codex는 답한 모델을 보고하지 않는다(K32). 네트워크는 공유한다(K08).

## 남은 것

- 합성자를 바꾼 같은 비교, 제약이 충돌하는 설계 과제, blind 채점(D 후속). 이번 Codex 합성은 한 번의 관측이지 비교가 아니다.
- 공통 자료 속 지시문(프롬프트 주입), 긴 자료·여러 파일.
- 원장 규모별 조회 비용 측정.
