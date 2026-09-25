# 리뷰 요청 — 지금까지의 작업과 실패·시행착오 (2026-09-24)

다른 AI 세션에게 검토를 받기 위한 요청서다. 요청한 쪽은 claude 세션(Claude Opus 5.5)이다. 작업은 사용자 보조 PC(`aux-pc`)의 로컬 checkout과 그 안의 WSL2 배포판(`aux-pc-wsl`)에서 했다. 리뷰어는 **GitHub만 볼 수 있다고 가정한다.**

- 이 요청서는 [2단계 요청서(17번)](../2026-09-23-stage2-request/README.md)를 **이어받는다.** 17번은 아직 리뷰받지 않았다. 17번의 실패 목록(S01–S21)과 질문 1–8은 그대로 유효하다. 여기서는 그 뒤의 일(PR #8–#12), 새 실패(S22–), 지금까지의 전체 흐름을 더한다.
- 리뷰어가 PC에만 있던 관측을 볼 수 있도록 **관측 요약을 이 폴더로 옮겼다**(아래 "리뷰어가 볼 수 있게 옮긴 것").

이번 요청의 중심은 네 가지다.
- **K46 방어**(Codex 참여자의 명령이 Codex 로그인 파일을 읽는 문제)의 설계와, 모델 없이 한 확인이 결론을 뒷받침하는가.
- 2단계와 그 뒤 기록에 적은 **판정이 증거로 뒷받침되는가.** 모델의 보고나 모델 없는 진단에 기댄 판정이 특히 그렇다.
- **실패·실수·시행착오**가 빠짐없이 정직하게 적혔는가. 되풀이되는 실수 유형을 막는 방법이 있는가.
- **일하는 방식**(승인 해석, claude 세션의 자체 병합)이 사용자의 규칙에 맞는가.

## 사용자가 리뷰어에게 붙여 넣을 요청문

> 저장소 https://github.com/inlight37-design/decision-model_lab 에서 `docs/reviews/2026-09-24-review-request/README.md`를 읽고 그대로 따라 검토해 줘. main에 없으면 브랜치 `claude/review-request-20260924`에 있다. 결과는 그 문서의 "결과를 남기는 방법"대로 남겨 줘. GitHub에 쓸 수 없으면 결과 전문을 답으로 줘.

## 검토 범위

- **기준 커밋:** 검토 대상 코드는 main `a26e504`(PR #12 병합)다. 이 요청서를 더한 커밋은 문서만 바꾼다.
- **아직 리뷰받지 않은 범위:** A1 리뷰 반영(`cd94190`) 뒤부터 `a26e504`까지. `git log --first-parent cd94190..a26e504`로 본다.
  1. 1단계 N1–N6과 사용자 결정 Q5·Q6·C2 — 17번이 다룬다.
  2. 2단계 호출 다섯 번 — 17번이 다룬다.
  3. 2단계 뒤: [PR #8](https://github.com/inlight37-design/decision-model_lab/pull/8)부터 [PR #12](https://github.com/inlight37-design/decision-model_lab/pull/12)까지 — 이 문서가 다룬다.
- **이미 리뷰받은 범위:** 아래 연표의 앞 단계다. 다시 읽을 필요는 없다. 다만 지금 코드나 인계가 그 리뷰의 반영과 어긋나면 적는다.
- **모델 호출:** 지금까지 모두 여섯 번이다.
  - 2단계에서 Claude 3회(`claude-sonnet-5`), Codex 2회(`gpt-6-luna`).
  - K01 관측에서 Claude 1회(`claude-sonnet-5`).
  - 그 밖의 실행은 `--version`, `--help`, 로그인 상태, `codex sandbox`, 그리고 **네트워크를 끊은 `codex exec`**(S28)뿐이다.

### 리뷰어가 볼 수 있게 옮긴 것

| 파일 | 무엇 | 가공 |
|---|---|---|
| [`observe-summaries.json`](observe-summaries.json) | 관측 호출 여섯 번의 요약(`summary`)과 모델 답(`answer`). 원 stdout·stderr는 없다 | 지금의 가림 규칙(HOME, UUID, 긴 16진수, 토큰 모양)과 이메일 모양 가림을 다시 적용했다. 공개 저장소라 `~/.codex/plugins/cache/` 아래 파일 이름은 개수만 남겼다. 1–5번은 요약 형식을 고치기 전 판이다 |
| [`k46-profile-run1.json`](k46-profile-run1.json), [`k46-profile-run2.json`](k46-profile-run2.json) | [`tools/w2/codex_profile.py`](../../../tools/w2/codex_profile.py)의 출력 두 번. 두 번째는 커밋한 판의 도구로 돌렸다 | 도구가 HOME·UUID를 가렸다. 그 밖에는 고치지 않았다 |

리뷰어가 **볼 수 없는 것**: 원 stdout·stderr(WSL의 `~/.local/state/dml-observe/results/`), 사용자 PC의 설정·인증 폴더, 계정 정보. 기록으로만 판단하고, 다르다고 단정하지 말고 "확인 필요"로 적는다.

## 지금까지의 흐름

날짜는 사용자 PC의 시각(UTC+9)이다. "리뷰"는 그 단계를 검토한 기록이다.

| 날짜 | 단계 | 한 일 | 주요 기록 | 리뷰 |
|---|---|---|---|---|
| 09-21 | v0.2 | 연구 노트, 계약과 오프라인 검사 | [contracts/v0.2](../../../contracts/v0.2/README.md) | — |
| 09-22 | v0.4 설계 | frontier 모델 독립 추론·교차검토·근거 합성 설계([PR #1](https://github.com/inlight37-design/decision-model_lab/pull/1)), 근거 재검증([PR #2](https://github.com/inlight37-design/decision-model_lab/pull/2)), 첫 실제 cross_check, CI, 인코딩 가드 | [v0.4](../../architecture/v0.4/README.md), [cross_check](../../experiments/2026-09-22-cross-check/README.md) | [FINAL_REVIEW](../../architecture/v0.4/FINAL_REVIEW.md), [외부 검토](../2026-09-22-external-review.md), [반영](../../architecture/v0.4/REVIEW_FIXES.md) |
| 09-23 새벽 | MCP·UI, V04-01 | 앱 사례·Ledger UI 검토([PR #3](https://github.com/inlight37-design/decision-model_lab/pull/3)), aux-pc에 세 CLI 설치·tier 1·2 관측 | [V04-01 aux-pc](../../experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md) | [PR #3](../2026-09-23-mcp-ui-runtime/README.md), [PR #4](../2026-09-23-v04-01-review/README.md) |
| 09-23 오후 | 조사, V04-03 | Hermes 조사([PR #5](https://github.com/inlight37-design/decision-model_lab/pull/5)), 실행 코어(runner·adapter·membership), 첫 conformance, Windows Codex가 아무것도 읽지 못한 원인 | [conformance](../../experiments/v04-03-conformance/aux-pc.md), [Hermes](../../research/hermes-2026-09-23/README.md) | [경계 리뷰](../2026-09-23-wsl2-boundary/README.md) |
| 09-23 저녁 | WSL2, W2 | WSL2 채택·설치, stdin 실행 명세, bubblewrap 격리와 경계 시험 | [W2](../../experiments/w2-isolation/aux-pc-wsl.md) | [PR #6](../2026-09-23-wsl2-migration-review/README.md) |
| 09-23 밤 | A1 | controller·모의 화면·SQLite journal | [app/](../../../app/README.md) | [PR #7](../2026-09-23-a1-handoff-review/README.md) |
| 09-23 밤 | 1단계 | N1 실제 CLI 실행기, N2 관측 도구, N3 인증 연결 관측, N4 실행 허가 계산, N5 실행 표식·정족수 정책, N6 대비 | [1단계 직후 인계](../../handoff/2026-09-23-before-stage2.md) | **없음**(17번) |
| 09-23 23시 | 2단계 | 승인된 호출 다섯 번, 관측 도구 수정, K12 진단 | [2단계 기록](../../experiments/w2-isolation/stage2-aux-pc-wsl.md) | **없음**(17번) |
| 09-24 0시 | 2단계 뒤 | ChatGPT의 tmux 조사 병합([PR #8](https://github.com/inlight37-design/decision-model_lab/pull/8)), K46 발견([PR #9](https://github.com/inlight37-design/decision-model_lab/pull/9)), K01 호출([PR #10](https://github.com/inlight37-design/decision-model_lab/pull/10)), 편의 기능 후보([PR #11](https://github.com/inlight37-design/decision-model_lab/pull/11)) | [후속 기록](../../experiments/w2-isolation/stage2-followup-aux-pc-wsl.md), [K01 기록](../../experiments/w2-isolation/k01-large-input-aux-pc-wsl.md), [tmux](../../research/tmux-2026-09-23/README.md) | **없음**(이 문서) |
| 09-24 1시 | K46 방어 | adapter의 권한 profile, 네트워크 없는 exec 진단, `k46-codex` probe([PR #12](https://github.com/inlight37-design/decision-model_lab/pull/12)) | [K46 profile 기록](../../experiments/w2-isolation/k46-profile-aux-pc-wsl.md) | **없음**(이 문서) |

## 지금 상태 한눈에

자세한 것은 인계 [`NEXT-SESSION.md`](../../../NEXT-SESSION.md) 1절과 4절의 K 표에 있다.

- **있는 것:**
  - 셸 없는 CLI 실행기(`core/runner.py`)와 bubblewrap 격리(`core/isolation.py`).
  - 읽기 전용 논의자 명세(`core/adapters.py`)와 실행 허가 계산(`core/eligibility.py`).
  - A1 controller와 모의 화면(`app/`).
  - 실제 CLI 실행기(`app/cli_executor.py`) — 가짜 CLI로만 시험했다.
  - 관측 도구(`tools/w2/`).
- **실행 허가:** Claude는 다섯 칸이 모두 관측돼 허가가 나온다. Codex는 문맥 판정이 `failed`라 허가가 없다.
- **없는 것:** 합성, 결정 카드, 취소, 사용량 표시. 화면 서버는 아직 모의 실행기만 쓴다.
- **다음 일:** 사용자가 고른다. K46 확인 호출(Codex 1회, 승인 필요)과 3단계 A1 이어서(모의) 가운데 하나다.

## 2단계 뒤에 한 일 (17번에 없는 것)

| PR | 무엇 | 근거 |
|---|---|---|
| [#8](https://github.com/inlight37-design/decision-model_lab/pull/8) | ChatGPT의 tmux 조사 병합(문서만). 사용자 지시로 claude 세션이 병합했다. 충돌한 인계 3절은 main 쪽을 두었다(S31). claude 세션이 조사의 코드 주장 셋을 대조했다(인계 1절 기록 표) | [조사](../../research/tmux-2026-09-23/README.md) |
| [#9](https://github.com/inlight37-design/decision-model_lab/pull/9) | 모델 없는 진단으로 K46을 찾았다: Codex 샌드박스 안의 명령이 `~/.codex/auth.json`을 읽을 수 있다. 명령의 네트워크는 막혀 있다. `auth.json`만 금지하는 권한 profile은 `codex sandbox`에서 통했다. GitHub CLI를 설치했다 | [후속 기록](../../experiments/w2-isolation/stage2-followup-aux-pc-wsl.md), [`codex_sandbox.py`](https://github.com/inlight37-design/decision-model_lab/blob/01cedd3c05dc043465d4476aab2b1a8f547574e9/tools/w2/codex_sandbox.py) |
| [#10](https://github.com/inlight37-design/decision-model_lab/pull/10) | K01: Claude 1회. 약 95 KB의 stdin 질문이 끝까지 전달됐고 보고 토큰이 입력만큼 늘었다 | [K01 기록](../../experiments/w2-isolation/k01-large-input-aux-pc-wsl.md), `observe-summaries.json`의 6번 |
| [#11](https://github.com/inlight37-design/decision-model_lab/pull/11) | 사용자 방침(인계 2절 20): 편의·오케스트레이션 기능은 기본이 꺼진 후보로 둔다. 새 실행으로 넘기기, 공개 뒤 교차검토 한 라운드, 슈퍼바이저 제안 | 인계 4절 |
| [#12](https://github.com/inlight37-design/decision-model_lab/pull/12) | K46 방어의 모델 없는 부분. Linux Codex 명세가 `--sandbox read-only` 대신 `auth.json`만 읽기 금지한 권한 profile을 `-c default_permissions`로 준다. `-c` 예외는 그 실행의 값만 통과한다. 네트워크 없는 exec 진단 도구, `k46-codex` probe, C3 (a)용 `--keep-session`, 토큰 모양 가림을 더했다 | [K46 profile 기록](../../experiments/w2-isolation/k46-profile-aux-pc-wsl.md), 시험 4개 파일 |

검사(각 PR 본문 기준):
- PR #9와 #12는 Windows와 aux-pc-wsl(`DML_REQUIRE_BWRAP=1`)에서 전체 시험을 돌렸다. #10은 Windows 전체 시험만, #11은 문서 검사(`test_research_integrity`, `check_encoding.py`)만 돌렸다.
- CI(Python 3.12·3.13)는 PR #8–#12 모두 녹색이었다. CI는 bubblewrap을 설치하고 격리 시험의 건너뛰기를 막는다.
- PR #12부터는 Windows에서도 `validate_sources.py`가 돈다(S18).

## 잘 안 된 것 — 실패, 실수, 시행착오

번호(S)는 17번에서 이어 쓴다. 이 요청서들 안에서만 쓰는 번호다.

### 17번의 S01–S21 — 지금 상태

| S | 요지 | 지금 |
|---|---|---|
| S01 | 큰 입력(`--pad-kb`)을 빠뜨림 | **해결** — K01 호출(PR #10) |
| S02 | 요약에 조직 UUID가 찍힘 | 도구가 가린다. PR #12에서 토큰 모양까지 넓혔다. 새 모양은 여전히 못 가린다 |
| S03, S04 | 낡은 하위 명령 호출, 셸의 `cd` | 교훈으로 남김. S03은 S23과 같은 유형이다 |
| S05 | 없는 init 필드에 기댄 K31 계획 | **미해결.** `CLAUDE.md`를 싣지 않았다는 근거는 여전히 모델의 보고다 |
| S06 | 모델의 협조에 기댄 probe | K30은 미해결이다. 새 `k46-codex`도 같은 약점이 있다(S29) |
| S07 | Claude 쪽에서 bubblewrap 경계가 시험되지 않음 | 그대로 |
| S08–S10 | 멈춤 규칙·잘린 목록·`argv_run` | 2단계에서 고침 |
| S11 | 파이프에 다 썼다는 것이 CLI가 다 읽었다는 증거가 아님 | 한계로 유지(K01) |
| S12, S13 | 문맥 판정이 갈릴 수 있음 | 미정(열린 결정 C3). `--keep-session`을 준비했다 |
| S14 | Codex가 계정 플러그인을 받음 | K44. exec가 계정 쪽 MCP에도 연결하려 한다는 관측을 더했다 |
| S15 | `agents-md` 플러그인 | 미해결(K45) |
| S16 | main 병합이 권한 확인에 막힘 | 사용자 지시로 병합했다. PR #9–#12는 claude 세션이 CI 녹색 뒤 병합했다(S32) |
| S17 | PR을 만들지 못함 | **해결** — `gh` 설치, 사용자 로그인 |
| S18 | Windows에 `jsonschema` 없음 | **해결** — PR #12 세션이 `requirements-design.txt`로 설치했다 |
| S19–S21 | 훅 출력 깨짐, 기록을 고정한 시험, 세션이 고른 모델 | 그대로 |

### 2단계 뒤의 새 실패·시행착오

**계획·가정의 실수**

- **S22 승인을 해석해서 적었다(PR #9·#10 세션).**
  - "3번은 알아서 해도 돼"를 모델 호출 승인으로 적으려 했으나, 그 세션의 자동 권한 확인이 거절했다.
  - 세션이 K01(Claude 1)과 K46(Codex 1) 호출의 명시적 승인을 요청했고, 사용자는 "병합하고 할거하고 정리해"라고 답했다.
  - 세션은 이것을 K01에만 적용해 Claude 1회, 300초로 적었다([승인 메모](../../experiments/w2-isolation/k01-large-input-aux-pc-wsl.md)). 상한 값은 세션이 요청한 값이고, 사용자가 숫자를 말하지는 않았다.
  - 인계 2절 19는 승인 때 provider별 상한·timeout·멈춤 조건을 함께 정하라고 한다. 이 해석이 그 규칙에 맞는가(질문 6).
- **S23 확인하지 않은 옵션으로 방어 계획을 적었다(PR #9·#10 세션).**
  - 후속 기록(PR #9)이 "exec에 `-c permissions.…`와 `-P`를 넘긴다"고 적었고, 인계 4절(PR #10)이 그대로 옮겨 적었다. `-P`는 `codex sandbox`에서 쓴 옵션이다. exec의 help를 보지 않았다.
  - 0.156.1의 `codex exec`에는 `-P`가 없다(인자 오류). 다음 세션이 모델 호출 전에 help와 인자 해석으로 잡았고, `default_permissions`로 바꿨다.
  - S03(낡은 하위 명령), S05(없는 필드)와 같은 유형이다: **CLI의 표면을 확인하지 않고 계획에 적었다**(질문 7).

**이번 세션(PR #12)의 실수와 시행착오**

- **S24 시험 예시가 틀렸다.** 토큰 가림 시험의 예시 문자열(`Ab1` 반복)이 모두 16진수 글자라서 긴 16진수 규칙에 먼저 걸렸다. 시험이 실패해서 잡았고 예시를 고쳤다. 코드의 결함은 아니었다.
- **S25 `--keep-session` 첫 판이 너무 많이 옮겼다.**
  - 호출 중에 새로 생긴 세션 기록을 **모두** 상태 폴더로 옮기게 짰다. 같은 때 사용자가 그 배포판에서 Codex를 쓰면 사용자의 기록까지 옮겼을 것이다.
  - 커밋 전 자체 검토에서 찾아, 이번 호출의 `thread.started` ID가 이름에 든 기록만 옮기도록 좁혔다.
  - 실제 Codex의 세션 기록 이름에 thread ID가 들어가는지는 확인하지 않았다(가짜 CLI만). 들어가지 않으면 아무것도 옮기지 않고 `session_record_missing`으로 알린다.
- **S26 진단 도구를 실측 뒤에 고쳤다.** 셸 명령을 관측 도구와 공유하도록 바꿨다. 기록이 커밋한 도구와 맞도록 다시 돌렸다(run2). 결과는 같았다.
- **S27 시험 출력을 거르는 방식이 실패를 가릴 수 있었다.** WSL 시험 출력을 `skip` 줄만 grep해서 봤다. 실패가 있었다면 보이지 않았을 것이다. 다시 돌려 전체 요약(`OK`)을 확인했다.
- **S28 네트워크를 끊은 실제 `codex exec`를 승인 없이 돌렸다.**
  - 사용자의 로그인이 연결된 실제 Codex를 bubblewrap `--share-net`만 뺀 격리(loopback만 있는 새 네트워크 namespace)에서 돌렸다. 모델에 닿을 수 없으므로 모델 호출이 아니라고 판단했다.
  - Codex는 모델 목록 갱신과 계정 쪽 MCP(`chatgpt.com/backend-api/ps/mcp`) 연결을 시도했다. 모두 실패했다.
  - 인증 파일은 실행 전후의 크기·수정 시각이 같았다.
  - 이것을 "모델 없는 진단"으로 봐도 되는가는 판단이 갈릴 수 있다(질문 3).
- **S29 `k46-codex`가 모델의 협조에 기댄다.**
  - 모델에게 인증 파일을 여는 셸 명령을 돌리게 한다. 모델이 거부하면 `auth_check`가 비어 기대와 다른 것으로 끝나고 호출 1회를 쓴다.
  - 금지가 실패하면 모델이 내용을 출력할 수도 있다. 명령은 내용을 `/dev/null`로 버리고, 답·출력에 JWT가 보이면 경계 위반으로 멈춘다. 원 출력은 PC 상태 폴더에 남는다.
  - 판정은 모델이 답에 옮긴 값이 아니라 명령의 실제 출력(`aggregated_output`)에서 읽는다(질문 2).

**모델 없이 확인하지 못한 것**

- **S30 exec에서 profile이 적용됐는지 볼 방법을 찾지 못했다.** 사람용 머리글은 profile을 줘도 옛 방식과 같이 `sandbox: read-only`만 보인다. 그래서 exec 쪽은 "설정을 받아들인다", "없는 profile은 거절한다"까지만 봤다.

**일하는 방식**

- **S31 PR #8 병합에서 ChatGPT가 고친 인계 3절을 버렸다.** 충돌에서 main 쪽을 두었고, 조사 링크와 claude 세션의 대조는 1절로 옮겼다. 버린 내용 가운데 살려야 할 것이 있는지 봐 달라.
- **S32 claude 세션이 자기 작업을 CI 녹색 직후 병합한다.** 사용자 허락(인계 2절 8)의 범위다. PR #9–#12는 독립 리뷰 없이 main에 들어갔고, 리뷰는 이처럼 사후에 받는다. 그 사이 다음 세션이 틀린 계획(S23)을 이어받았다(질문 6).
- **S33 인계 3절의 병합 이력을 줄였다(PR #12).** 최근 병합만 남기고 나머지는 PR 본문과 Git 로그로 보냈다. 인계 1–2절에 없고 PR에만 있던 정보가 사라졌는지 봐 달라.


### 이미 기록된 앞 단계의 실패 (참고)

이 요청의 범위는 아니지만 전체 흐름을 보려면 함께 본다.

| 무엇 | 어디 |
|---|---|
| Windows PowerShell 5.1의 `Get-Content`/`Set-Content`가 문서 세 개의 한글을 `?`로 바꿨다. 커밋 훅과 CI의 인코딩 검사를 더했다 | [AGENTS.md](../../../AGENTS.md), [`check_encoding.py`](../../../tools/check_encoding.py) |
| 첫 실제 cross_check의 입력이 오염됐다 | 커밋 `558cc42`, [REVIEW_FIXES](../../architecture/v0.4/REVIEW_FIXES.md) |
| agy를 Claude 데스크톱 앱의 가상 AppData에 설치해 사용자 터미널에서 보이지 않았다 | [V04-01 aux-pc](../../experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md) |
| Windows Codex가 `--ignore-user-config`로 샌드박스 선택을 잃고 모든 명령을 거절한 채 exit 0으로 답했다(openai/codex#42172) | [conformance](../../experiments/v04-03-conformance/aux-pc.md) |
| 리뷰가 찾은 결함(R·WM·A1 번호)과 반영, 리뷰어 쪽의 틀린 지적 | 각 리뷰 폴더의 `RESPONSE.md`, [검토 목록](../README.md)의 단서 |

## 아직 모르는 것

- exec에서 **모델이 돌린 명령**에 권한 profile의 금지가 적용되는지(K46). `observe.py call k46-codex` 1회가 필요하고, 사용자 승인이 먼저다.
- Codex의 계정 플러그인·스킬·MCP가 참여자 문맥에 들어가는지(K44, C3). 세션 기록의 형식과 그 이름에 thread ID가 들어가는지.
- `~/.codex` 아래 다른 파일(세션 기록, 상태 DB, 캐시)에 민감한 값이 있는지. 지금 profile은 `auth.json` 하나만 막는다.
- 토큰 갱신 때 CLI가 인증 파일을 어떻게 쓰는지(K09). Linux Codex의 거절 문자열(K30). `CLAUDE.md`를 싣지 않는다는 비모델 근거(K31). 실제로 답한 Codex 모델(K32). `agents-md`(K45).
- 다른 기기·버전에서도 같은지(K35). A1 화면을 눈으로 본 적이 없다(K27).

## 읽는 순서

결론에 끌려가지 않도록 **코드·관측을 먼저, 우리의 판정을 나중에** 읽는다.

1. [`AGENTS.md`](../../../AGENTS.md), [`docs/COLLABORATION.md`](../../COLLABORATION.md).
2. [`NEXT-SESSION.md`](../../../NEXT-SESSION.md)의 **2절만**. 논쟁하지 않는 전제다.
3. 코드와 시험:
   - [`core/adapters.py`](../../../core/adapters.py)의 `codex_permissions`·`_check`·`build_spec`, [`tests/test_core_adapters.py`](../../../tests/test_core_adapters.py)
   - [`app/cli_executor.py`](../../../app/cli_executor.py), [`tests/test_app_cli_executor.py`](../../../tests/test_app_cli_executor.py)
   - [`tools/w2/observe.py`](../../../tools/w2/observe.py), [`tests/test_w2_observe.py`](../../../tests/test_w2_observe.py)
   - [`tools/w2/codex_profile.py`](../../../tools/w2/codex_profile.py), [`tools/w2/codex_sandbox.py`](https://github.com/inlight37-design/decision-model_lab/blob/01cedd3c05dc043465d4476aab2b1a8f547574e9/tools/w2/codex_sandbox.py), [`tests/test_w2_codex_sandbox.py`](https://github.com/inlight37-design/decision-model_lab/blob/01cedd3c05dc043465d4476aab2b1a8f547574e9/tests/test_w2_codex_sandbox.py)
   - [`core/isolation.py`](../../../core/isolation.py)의 `cli_mounts`·`plan`, [`core/eligibility.py`](../../../core/eligibility.py)
4. 관측: 이 폴더의 JSON 세 개, 그리고 [2단계 기록](../../experiments/w2-isolation/stage2-aux-pc-wsl.md)·[후속 기록](../../experiments/w2-isolation/stage2-followup-aux-pc-wsl.md)·[K01 기록](../../experiments/w2-isolation/k01-large-input-aux-pc-wsl.md)·[K46 profile 기록](../../experiments/w2-isolation/k46-profile-aux-pc-wsl.md)의 결과 절. **"판정" 절은 아직 읽지 않는다.** 여기서 두 가지를 스스로 적어 둔다:
   - 각 CLI의 세 칸(전송·문맥·권한)을 `observed`·`failed`·`unknown` 가운데 무엇으로 적겠는가.
   - K46에 대해 지금까지 확인된 것과 확인되지 않은 것은 무엇인가.
5. 우리의 판정: 위 기록들의 "판정" 절, [`manifest.v2.json`](../../experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.v2.json), 인계 1·3·4절(K 표). 4에서 적은 판단과 비교한다.
6. [17번 요청서](../2026-09-23-stage2-request/README.md)의 "잘 안 된 것", 이 문서의 "잘 안 된 것".

## 검토 질문 — 중요한 순서

각 질문에 "동의 / 부분 동의 / 반대"와 근거를 적는다. 근거가 없으면 "판단 보류"라고 쓴다.

1. **K46 방어의 설계.**
   - `:read-only`를 넓혀 `~/.codex/auth.json` 하나만 금지하는 profile을 `default_permissions`로 고르는 방식이 맞는가. 옛 `--sandbox`를 뺀 판단은 맞는가.
   - 막아야 할 다른 경로가 있는가(세션 기록, 상태 DB, 다른 토큰 캐시). `~/.codex` 전체를 막으면 샌드박스가 깨지는 문제의 다른 해법이 있는가(예: 인증 파일을 격리 안에서 다른 곳에 두기).
   - `-c` 예외를 실행별 값으로 좁힌 방식과 HOME 검증(따옴표·백슬래시·제어 문자 거절)이 충분한가.
2. **`k46-codex` probe와 판정.** `as_expected`의 조건, 경계 위반 목록(`auth_file_readable`, `credential_shape_seen`), 모델 협조 의존(S29)과 프롬프트의 위험. 더 나은 설계가 있는가. 사용자에게 권할 승인 값(횟수, timeout, 모델, `--keep-session` 여부)은 무엇인가.
3. **네트워크 없는 exec 진단(S28).** 모델 없는 진단으로 받아들일 수 있는가. 그것으로 낸 결론(설정을 받아들인다, 없는 profile은 연결 전에 거절한다)이 타당한가. 사용자 계정·인증 파일에 부작용이 생길 수 있는가.
4. **17번 질문 1–8.** 아직 답이 없다. 특히 질문 1(기록의 판정)과 6(다음 단계 순서).
5. **열린 결정 C3.** (a) 참여자 구성에서 문맥을 보는 것과 (b) 빈 작업 폴더 완화를 정책으로 받는 것 가운데 무엇이 맞는가. `--keep-session`의 설계와 요약 방식, 계정 쪽 MCP 연결 관측(K44)을 어떻게 다뤄야 하는가.
6. **일하는 방식.** 승인 해석(S22)과 claude 세션의 자체 병합(S32)이 사용자의 규칙에 맞는가. 무엇을 바꿔야 하는가. 예: 모델 호출 승인은 숫자를 사용자가 직접 말할 때만 받기, 병합 전에 다른 AI의 짧은 리뷰를 받기.
7. **되풀이되는 실수.** S03·S05·S23은 모두 CLI 표면을 확인하지 않고 계획에 적은 것이다. 도구나 절차로 막을 방법이 있는가. 예: 계획에 적는 CLI 옵션마다 기록된 help의 줄을 인용하게 하기, `plan`이 help와 대조하기.
8. **관측 요약의 공개.** `observe-summaries.json`의 가공(가림, 플러그인 이름 생략)이 충분한가. 남은 민감 정보가 있는가. 반대로 판단에 필요한 정보를 너무 뺐는가.
9. **다음 순서.** K46 확인 호출, 3단계(A1 이어서, 모의), B3 pilot의 선행 조건 가운데 무엇을 먼저 해야 하는가.

질문 밖이라도 **틀린 사실, 깨진 링크, 기록과 다른 코드**를 찾으면 적는다.

## 결과를 남기는 방법

- 새 브랜치 `<에이전트>/review-<YYYYMMDD>`를 만든다(예: `chatgpt/review-20260924`). 이 요청서가 main에 없으면 `claude/review-request-20260924`를 base로 한다.
- 리뷰는 `docs/reviews/<YYYY-MM-DD>-review/README.md`에 쓰고 PR을 연다. [PR 템플릿](../../../.github/pull_request_template.md)을 채우고, 접근 범위에는 실제 범위를 적는다.
- 17번만 따로 리뷰해도 된다. 그때는 17번의 "결과를 남기는 방법"을 따른다.
- 재현 코드를 돌렸다면 같은 폴더에 스크립트와 결과를 둔다. 무엇을 어디서 실행했는지 적는다. 검토 대상 파일의 해시를 고정해 두면 수정 뒤와 헷갈리지 않는다(앞 리뷰의 방식).
- 리뷰 문서의 형식:

| 절 | 내용 |
|---|---|
| 요약 | 가장 중요한 발견 세 개 이내 |
| 발견 | 번호, 심각도(높음·중간·낮음), 위치(`파일:줄` 또는 URL), 근거 등급(**관측** / **재현** / **문서** / **추론**), 내용, 제안 |
| 질문별 답 | 위 1–9에 대한 동의·부분 동의·반대·보류와 근거 |
| 확인하지 못한 것 | 접근할 수 없었거나 읽지 않은 것 |

- **명백한 오류**(오타, 깨진 링크, 기록과 다른 숫자)는 같은 PR에서 원본을 고쳐도 된다. 커밋 메시지에 무엇이 왜 틀렸는지 적는다. **판단이 갈리는 것은 고치지 말고 리뷰에만 적는다.**
- 살아 있는 문서에 검사 수·원장 건수를 적지 않는다(CI가 막는다). `NEXT-SESSION.md`는 절 구성을 유지한 채 3절에 리뷰 브랜치를 적는다.
- 병합은 하지 않는다. 사용자 또는 claude 세션이 CI를 확인한 뒤 병합한다.

## 이미 알고 있는 한계

리뷰어가 같은 지적을 반복하지 않도록 적어 둔다. 전체 목록은 인계 4절의 K 표다. 다르게 판단하면 그 근거를 적는다.

- 모든 관측은 보조 PC 한 대와 그 안의 WSL 배포판 하나, 2026-09-23–24의 것이다(K35).
- 원 출력은 PC에만 있다. 저장소에는 가린 요약만 있다.
- 권한 profile은 Codex 문서상 베타 기능이다. 버전이 바뀌면 진단을 다시 돌린다.
- A1 화면은 스크린샷으로 확인하지 못했다(K27).
