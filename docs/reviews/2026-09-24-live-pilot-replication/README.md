# PR #34·#35 검토·병합과 두 번째 실제 CLI 응답 — 2026-09-24

claude 세션이 사용자 PC에서 직접 실행하고 검토했다. 사용자는 codex 세션의 첫 실측 보고를 전달하며 “너도 해보고 검토한 다음에 정리해서 문서화하고 다음 작업 뭐해야 할지 정리해”라고 요청했다. 이 요청을 **이 세션의 별도 실측 1회**(Codex 1회·Claude 0회·180초)에 대한 승인으로 썼다. 앞선 codex 실측의 원장·서버·예산은 건드리지 않았다.

## 작성·접근 범위

- Claude 데스크톱 앱(Code 탭)의 Windows 세션. 같은 PC의 WSL2 `Ubuntu-24.04`에서 실행했다. 기존 기록의 `aux-pc`/`aux-pc-wsl`로 취급한다 — codex 세션의 원장 `~/.local/state/dml-live-pilot`과 그 서버 프로세스(포트 8765)가 이 WSL에 그대로 있었다.
- CLI를 직접 봤다: Linux-native Codex `0.156.1`, Python `3.12.3`, bubblewrap `0.9.0`. `codex login status`는 ChatGPT 로그인을 보고했다. 인증 파일 내용·계정 식별자는 읽거나 기록하지 않았다.
- 실행 코드는 PR #35 head `2a712e341cfe7b662a562631be71aa0d4031dbc0`을 저장소 밖 임시 worktree로 꺼내 WSL에서 돌렸다. 새 원장 `~/.local/state/dml-live-pilot-claude-20260924`(시작 전 없음), 새 빈 입력 폴더, 포트 8766을 썼다.
- codex 세션의 원장은 SQLite 읽기 전용(`mode=ro`)으로만 열어 보고서와 대조했다. 그 서버는 끄지 않았다.
- GitHub은 `gh`로 PR·Actions run·job 로그·branch 보호를 읽었다.

## 1. 검토 대상과 CI

| PR | head | CI | 비고 |
|---|---|---|---|
| [#34](https://github.com/inlight37-design/decision-model_lab/pull/34) `chatgpt/cli-breakthrough-20260924` | `437010678941afa768b8f36fa738dc4419626295` | pull_request run 35983962566 성공(3.12·3.13). checkout은 merge ref `34b8e58`(= head + main `0946bb6`) | **push run 없음.** head 커밋을 임시 workflow가 `github-actions[bot]`으로 push했고, GITHUB_TOKEN push는 workflow를 부르지 않는다 |
| [#35](https://github.com/inlight37-design/decision-model_lab/pull/35) `codex/live-pilot-observation-20260924` | `2a712e341cfe7b662a562631be71aa0d4031dbc0` | push run 35986032316, pull_request run 35986043331 모두 성공(3.12·3.13) | push job 로그의 checkout이 정확히 `2a712e3`. #34의 모든 커밋을 포함하므로 #34 코드도 정확한 head로 검사됐다 |

- 네 job 모두 `DML_REQUIRE_BWRAP: 1`, `Ran 424 tests … OK (skipped=1)`.
- main `0946bb6`은 두 head의 조상이다. 병합 결과 트리가 각 head 트리와 같다(#34 `aad220f7…`, #35 `37b9d9ae…`).
- main은 `protected=true`.
- 인계 5절은 main과 바이트 단위로 같다. 2절은 #34가 **21번을 덧붙였고** 1–20번은 그대로다. 21번은 chatgpt 세션이 사용자의 말(“직접 수정해봐도되고 모든 권한을 줄테니까 진행좀 나가보자”)을 옮긴 것이다. 이 세션은 그 대화를 볼 수 없어 인용 자체는 확인하지 못했다. 다만 사용자가 그 뒤 codex 실측을 시키고 이 세션에도 실행을 요청한 것과는 맞는다.
- 로컬: PR #35 head에서 WSL `DML_REQUIRE_BWRAP=1` 전체 오프라인 시험이 OK였고 skip은 Windows 레지스트리 전용 하나였다. `jsonschema==4.26.0`은 codex 세션이 `/tmp`에 만든 임시 venv를 그대로 썼다. WSL에 `python3-venv`와 pip가 없어서다. 그 venv는 바꾸지 않았다.

### 변이 시험

PR #35 head에서 핵심 줄 하나씩 되돌리고 WSL(`DML_REQUIRE_BWRAP=1`) 전체 시험을 돌렸다. 매번 원래 파일로 되돌렸고 끝난 뒤 작업 트리는 깨끗했다.

| 변이 | 결과 | 잡은 시험(일부) |
|---|---|---|
| M1 `state.confirmed()`가 문맥 미확인을 무시(CLI면 확인) | 실패 2 | `test_live_cli` 격리 실행기·재시작 뒤 정족수 |
| M2 시작 전 예산 검사 제거 | 실패 1 | `test_one_reservation_caps_parallel_new_runs_and_restart_without_refund` |
| M3 opt-in 없이도 C3 건너뜀 | 실패 14 | `test_core_eligibility`, `test_app_readiness` |
| M4 실행기의 opt-in을 참여자 등급에 강제하지 않음 | 실패 3 | `test_live_cli` |
| M5 계획 뒤 정책 변경 검사 제거 | 실패 1 | `test_policy_and_permission_revocation_still_refuse_before_process_start` |
| M6 PR #35의 독립성 표시 수정 되돌림 | **통과(잡히지 않음)** | 없음 — 아래 N3 |

## 2. 두 번째 실제 응답

### 무모델 조회

- `--check-cli codex --model gpt-6-luna --inventory <K46 manifest> --input-dir <빈 폴더> --allow-context-unverified`: `eligible=true`, 판 `codex@8a0128d4c791`, 설치판 `0.156.1`, `model_calls=0`.
- 같은 조회에서 opt-in만 빼면 `eligible=false`이고 이유는 `context_conformance is failed` 하나였다. strict 거절 이유는 C3뿐이다.
- 조회는 데이터 폴더를 만들지 않았다.

### 화면과 거절 대조(호출 없음)

- 머리글 `실제 CLI · 구독 사용량 소비 · 문맥 미확인`, 상태줄 `실제 호출 예약 0/1`. 선택된 참여자는 Codex(`실제 CLI · gpt-6-luna`)뿐이고 최소 정족수 1, 정책은 `include_unverified`가 기본으로 잡혔다.
- 정책을 `independent_only`로 바꿔 시작하자 `only 0 participant(s) can be confirmed independent …`로 거절됐다. 실행이 생기지 않았고 예약은 0/1 그대로였다.

### 호출 1회

`include_unverified`로 시작했다. 질문은 “1기압에서 순수한 물이 끓는 온도는 섭씨 몇 도인가요? 도구를 사용하지 말고 짧게 답하세요.”(프롬프트 293바이트)이다. 앞선 `2+3`과 달리 프롬프트가 요구하는 결론·근거·뒤집을 조건 형식이 나오는지도 보려고 골랐다.

| | codex 세션(첫 실측) | 이 세션 |
|---|---|---|
| 코드 | PR #34 head `4370106`(표시 수정 전) | PR #35 head `2a712e3` |
| 질문·프롬프트 | `2+3`, 247바이트 | 물의 끓는점, 293바이트 |
| 답 | `5` | `결론: **100°C**` + 근거 + 뒤집을 조건(압력·순도) |
| 시간 | 5332 ms | 5965 ms |
| 입력 전달·종료 | `complete` · exit 0 · `pid_namespace` · 트리 종료 확인 | 같음 |
| 수용·공개 | `accepted` · 공개 | 같음 |
| 요청/보고 모델 | `gpt-6-luna` / 보고 없음(`model_match=null`) | 같음 |
| 입력·캐시·출력 토큰 | 13676 · 11008 · 5 | 13689 · 11008 · 70 |
| 정족수 | `include_unverified`, 확인 0·미확인 1 | 같음 |
| 상세 행 독립성 표시 | “독립성 확인”(오표시) → #35 수정 뒤 재조회로 확인 | 새 실행에서 “문맥 미확인 · 독립 정족수에 세지 않음” |

- CLI 호출 두 번 모두 250–300바이트 프롬프트에 입력 토큰이 약 13.7K였고, 그중 11008이 캐시였다. CLI가 붙이는 고정 문맥이 호출마다 이만큼 든다는 뜻이다. 이 수치로 그 문맥에 개인 지시문이나 메모리가 들었는지 판단하지 않는다(C3는 그대로 `failed`). B3 사용량 비교에서는 호출당 기본 비용으로 따로 적는다.
- 공개 뒤 **모의 합성**(모델 호출 없음)을 실제 답에 돌렸다. 주장 3개(문자 0–17, 19–50, 52–106)가 모두 원문 위치 일치·사실 미검증·미해결로 나왔다. 결정 카드는 `조건부 · QUALIFIED`, “판단 보류”였다. 합의나 원문 일치를 검증으로 올리지 않는 동작이 실제 답에서도 유지됐다.

### 예산 소진 뒤(호출 없음)

같은 서버에서 두 번째 실행을 시작했다. 시도는 `ControllerError: real CLI call budget exhausted; no call was started`로 시작 전에 거절됐다. 상태는 `process_failed_to_start`였고 공개는 `reveal_held`(축소 승인 필요)에서 멈췄다. 원장의 `live_call_reserved`는 여전히 한 건이었고 `codex exec` 프로세스는 없었다.

### 보고와 정리

- 원문 보고(`a1-draft-report/3`)와 결정 보고(`a1-decision-report/1`)를 인증된 로컬 API로 받아 저장소 밖(`Documents/Claude/2026-09-24-live-pilot/`)에 저장했다. 프롬프트 SHA-256 `ef9317f9522b05724f8a07e595c61618cf43042a9fa247e192d4680e539cb184`와 초안 해시를 파일에서 다시 계산해 일치를 확인했다. 파일 SHA-256은 원문 보고 `183ef7e8198ee433469e5258e38f2c205d86ff7459a440ed7cb93e5fd07aa602`, 결정 보고 `2aa3f6ab83f9734735ca37f5c9100c33305dab78739ea36f7fe82e4c8ef183ae`이다. 해시 일치는 진실성이나 독립성을 입증하지 않는다. 원문이 들어 있어 커밋하지 않는다.
- 내장 브라우저의 저장 버튼은 누르지 않았다. 다운로드 끝단은 앞선 Edge 확인([실행 계약 기록](../2026-09-24-execution-contract/README.md))이 기준이다.
- 이 세션의 서버는 SIGINT로 멈췄다. 원장은 예약 1/1 보존을 위해 지우지 않는다. codex 세션의 서버(포트 8765)는 사용자의 화면일 수 있어 그대로 두었다. 그 원장도 예약 1/1이라 더 부를 수 없다.

## 3. 발견

병합을 막는 것은 없다. N6은 병합 뒤 Windows에서 찾았고 이 기록의 PR에서 고쳤다.

| # | 발견 | 근거 | 제안 |
|---|---|---|---|
| N1 | **호출 상한이 원장에 고정되지 않는다.** `Controller.call_budget()`은 원장의 `live_call_reserved` 건수를 세지만 상한은 지금 기동한 `--call-budget` 값이다. 같은 원장을 더 큰 값(최대 10)으로 다시 켜면 그만큼 더 부를 수 있다 | `app/controller.py`의 `call_budget()`·`pump()`를 읽어 확인했다. 재기동으로 직접 해 보지는 않았다 | 첫 상한을 원장에 기록하고 다른 값으로 기동하면 거절한다. 올리려면 새 승인 기록을 요구한다 |
| N2 | **시작 전 거절도 실행별 “외부 호출 예산 — 소진량”에 1/1로 잡힌다.** 거절된 실행의 카드가 `1 / 1 · 받음 0 · 실패 1`을 보였다. 시작 사건도 `execution: real`을 달고 남는다 | 이 세션의 두 번째 실행 화면과 원장 | 서버 전체의 `실제 호출 예약`(정확함)과 실행별 시도 수를 구분해 보이고, 시작 전 거절은 따로 센다. B3 회계 전에 고친다 |
| N3 | PR #35의 표시 수정을 지키는 저장소 시험이 없다 | 변이 M6 | 참여자 행 문구가 저장된 `independence`를 따르는지 보는 시험을 더한다 |
| N4 | **#34는 소스를 base64 조각과 임시 workflow(`contents: write`)로 옮겼다.** 그 workflow가 `github-actions[bot]`으로 커밋·push했다. 스스로 지웠고 최종 diff에는 남지 않았다. 다만 최종 코드 커밋의 작성자가 bot이고, push CI가 돌지 않았고, 조각이 이력에 남는다 | 커밋 `d6c87cf`–`4370106` | 쓰기 권한 workflow로 코드를 들이는 방식을 협업 규칙에서 막을지 사용자가 정한다. 이번에는 #35의 정확한 head push CI가 같은 코드를 덮어서 병합에 지장이 없다 |
| N5 | 인계 2절 21번은 다른 세션이 옮긴 사용자 인용이다 | 위 1절 | 사용자가 문구를 확인한다 |
| N6 | **#34 뒤로 Windows 오프라인 시험이 오류 2건.** `test_live_cli.ExecutorPolicyTests`가 Linux 가짜 CLI를 심볼릭 링크로 설치하는데 플랫폼 조건이 없었다. Windows는 개발자 모드 없이 링크를 만들 수 없다(WinError 1314). CI는 Linux만 돌아 못 잡았다 | 병합 뒤 main에서 Windows Python 3.12.6로 전체 시험 | **이 PR에서 고쳤다.** 같은 파일의 `ServerLiveTests`처럼 Linux 전용으로 표시했다. Windows는 OK, WSL(`DML_REQUIRE_BWRAP=1`)에서는 두 시험이 그대로 돌고 통과한다 |

## 4. 병합

위 확인 뒤 인계 2절 8에 따라 #34 → #35 순서로 병합했다. 각각 검증한 head를 `--match-head-commit`으로 고정했다.

- #34 → `b920f2cd6131c93bfc1e919d82635e9db96dace1`
- #35 → `0219bc91a36038590eacdedd44023d47bb7063b7`

두 head 브랜치는 자동 삭제됐다. 두 병합 커밋의 push CI(run 35987928197, 35987948836)는 성공했다.

## 5. 남은 범위

확인하지 않은 것: C3 문맥 독립성, 실제 제공 모델(K32), Claude 경로, 복수 실제 CLI 동시 참여, 실제 모델 합성·사실 검증, 공통 자료 전달(입력 폴더가 비어 있음), 네트워크 공유·자원 상한(K08·K10), 사람이 직접 누른 조작. 같은 질문 형식으로 두 번 성공했다는 것은 이 경로가 재현된다는 뜻일 뿐 모델 품질의 근거가 아니다.

이 세션의 실측 상한은 소진됐다. 추가 호출에는 새 승인이 필요하다.

## 6. 다음 작업 권고

단일 Codex 경로는 두 세션에서 재현됐다. 같은 단일 호출을 더 반복해도 새로 배우는 것이 없다. 다음은 **참여자를 늘리는 것**과 **그 전에 회계를 바로잡는 것**이다. 순서와 완료 조건은 [인계 4절](../../../NEXT-SESSION.md)에 옮겼다.

1. **무모델 정리(작은 PR):** N1 상한 고정, N2 실행별 회계 분리, N3 표시 회귀 시험. B3 사용량 비교가 이 회계를 쓰므로 먼저 한다.
2. **Claude 경로(승인 1회):** `tools/w2/claude_preflight.py`로 controller 계획 그대로 전송·권한을 관측한다. 관측되면 Codex와 같은 문맥 미확인 opt-in으로 실행할 수 있다. 문맥(K31)은 그대로 미확인이다. preflight는 입력 폴더 없는 계획을 보는데, 서버의 `--input-dir`는 모든 CLI에 붙어 Claude의 판을 바꾼다(`--add-dir`·Read 도구). 그래서 3 전에 입력 폴더를 provider별로 주게 하는 것을 권고한다.
3. **복수 CLI 서버(코드 뒤 승인 2회):** 서버당 CLI 하나라는 제한을 풀고 provider별 상한을 둔다. 같은 질문에 Codex·Claude가 blind 초안을 내고 공개 뒤 모의 합성·대조까지 가는 첫 실제 교차 실행이다.
4. **C3 대조 실험(승인 필요):** 합성 개인 지시문·메모리 표식을 넣은 양성 대조와 뺀 음성 대조. 표식이 새지 않는다는 근거가 쌓여야 strict 허가를 다시 논할 수 있다.
5. **B3 사용량 비교:** 3 뒤. 이번에 본 호출당 고정 입력 약 13.7K 토큰을 기준선으로 쓴다.
