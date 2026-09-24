# PR #31·#32 병합 검증 — 2026-09-24

작성: claude 세션. **웹 컨테이너**(Claude Code on the web, Linux)와 GitHub 연결 도구만 썼다. 사용자 PC(`aux-pc`·`aux-pc-wsl`), 설치된 Claude·Codex CLI, 로그인, 브라우저에는 접근하지 않았다. 모델 호출·승인 갱신·manifest 변경은 없다. 사용자가 이 세션에서 "GPT와 검토했는데 너도 보고 검증한 다음 진행하라"고 했고, 병합은 인계 2절 8의 허락 범위다.

기준 main: `56bf5afcce385b8bec33f118421428af99944534`. 구현 판단은 [codex 기록](../2026-09-24-cli-readiness/README.md), 독립 재검토는 [ChatGPT 기록](../2026-09-24-pr31-safety-review/README.md)에 있다. 이 기록은 그 둘을 다시 확인한 결과와 병합만 다룬다.

## 대상

| PR | 브랜치 | 검증한 head | CI(정확한 head) | 병합 |
|---|---|---|---|---|
| [#31](https://github.com/inlight37-design/decision-model_lab/pull/31) | `codex/cli-readiness-20260924` | `781412063bb7817062edd14609c5a167e3dcc003` | push [35972635875](https://github.com/inlight37-design/decision-model_lab/actions/runs/35972635875)·pull_request [35972639437](https://github.com/inlight37-design/decision-model_lab/actions/runs/35972639437), `checks (3.12)`·`checks (3.13)` 성공 | `b9f14c8af19328acaf58f8e6dd95dab26cf0f021` |
| [#32](https://github.com/inlight37-design/decision-model_lab/pull/32) | `chatgpt/pr31-safety-review-20260924` | `991423fe772476b85e9a7324c24edf3b9ff7a775` | push [35975431481](https://github.com/inlight37-design/decision-model_lab/actions/runs/35975431481)·pull_request [35975436738](https://github.com/inlight37-design/decision-model_lab/actions/runs/35975436738), 둘 다 성공 | `daf44d64f935efad186887ad08bb49a26dd9bf5e` |

#32의 push run 3.13 job 로그 전체를 읽었다. checkout은 `991423fe772476b85e9a7324c24edf3b9ff7a775`이고, `DML_REQUIRE_BWRAP=1` 전체 시험은 414 tests, skip은 Windows 레지스트리 하나였다. ChatGPT 세션은 이 로그를 읽지 못했다고 적었는데, 그 빈칸을 채운다. #31 head는 check run API의 성공만 봤고 로그는 읽지 않았다(codex 기록이 checkout SHA를 적었다).

## 병합 방식

- 병합 커밋, 저장소 관례의 제목(`Merge PR #N <브랜치>: …`). 두 번 모두 `expectedHeadSha`로 검증한 head를 고정했다.
- #32는 #31의 head 위에서 시작했다. #31 병합 뒤 `git merge-tree`로 충돌 없음을 확인했다. 그때 #32의 차이는 자기 파일 넷(`NEXT-SESSION.md`, 검토 기록 둘, 회귀 시험)뿐이었다.
- 두 head 브랜치는 병합 직후 GitHub 자동 삭제로 지워졌다(`git fetch --prune`에서 확인). 이 세션이 지울 브랜치는 남지 않았다.
- 병합 커밋 두 개의 push CI도 성공했다: [35977360850](https://github.com/inlight37-design/decision-model_lab/actions/runs/35977360850)(`b9f14c8`), [35977410858](https://github.com/inlight37-design/decision-model_lab/actions/runs/35977410858)(`daf44d6`).

## 확인한 것

### 코드 읽기

- `CliExecutor.run()`은 계획을 다시 만들지 않고 같은 계획의 adapter·실행 파일·판으로 현재 기록을 다시 검사한다. 거절은 `REFUSED_BEFORE_START` 안의 `AdapterError`라 `failed_to_start`가 된다. `interpret`가 `process_failed_to_start`를 주고 `tree_confirmed_empty`가 참이라 controller의 수용 관문은 REJECTED로, 화면은 "실행하지 않음"으로 둔다. 늦은 거절이 시작된 시도나 unknown으로 기록되지 않는다.
- `contract.template()`의 연결 목록: `cli_mounts`가 CLI마다 읽기 전용 하나와 서로 다른 설정 경로만 주므로, 목록으로 바꿔 생기는 중복은 자료 폴더(`ro:input`)뿐이다. 자료 0개·1개의 판은 그대로다.
- stdin 질문 가림: `template()`과 `ExecutionSpec.record()` 모두 argv 전송(agy)에서만 가린다. stdin CLI의 argv에는 질문이 없으므로 옳다.
- `app/readiness.py`와 `--check-cli`: unchecked 실행기로 계획만 만들고 `isolation.plan()`까지만 부른다. 프로세스·원장·모델을 시작하지 않는다. 실행 함수 경로가 없다.
- `claude_preflight.assess()`가 보는 키는 `observe.py`의 `summarize()`와 call이 실제로 쓰는 키와 같다. 성공 요약도 전송 칸만 뒷받침한다.
- C3 probe 두 개는 합성 HOME만 연결하고 `unshare --net`으로 네트워크를 끊는다. 실제 인증 폴더를 연결하지 않는다.

### 판을 직접 계산

테스트의 `participant_revision`(실제 `CliExecutor.plan()`과 같은 틀)으로 계산했다.

| 계획 | main `56bf5af` | #31·#32 |
|---|---|---|
| Claude, 자료 없음 | `claude-code@97d0508b4567` | 같음 |
| Codex, 자료 없음 | `codex@58bee2560d83` | 같음 |
| Codex, 자료 하나(K46) | `codex@8a0128d4c791` | 같음 — `LEGACY["discussant-2"]` 유지 |
| Codex, 자료 둘 | `codex@8a0128d4c791` — **K46 관측이 뒷받침하던 결함** | `codex@a01a1721d57f` |

codex의 [조회 결과](../2026-09-24-cli-readiness/readiness-claude.json)에 적힌 판(`claude-code@97d0508b4567`, `codex@58bee2560d83`)과도 맞는다.

### 로컬 전체 검사

두 head를 `git archive`로 풀어 일반 사용자 계정에서 [CI 워크플로](../../../.github/workflows/checks.yml)의 단계를 그대로 돌렸다. Python 3.12.3·3.13.12, jsonschema 4.26.0(고정 판).

| head | 3.12 | 3.13 |
|---|---|---|
| #31 `7814120` | 모든 단계 성공, 409 tests OK | 같음 |
| #32 `991423f` | 모든 단계 성공, 414 tests OK | 같음 |

skip은 모두 OS·격리 전용이다: bubblewrap 전용 18, "job object 또는 bubblewrap" 1, Windows 레지스트리 1. **이 컨테이너에서는 bubblewrap을 쓰지 못했다.** 설치는 됐지만, 권한 없는 user namespace 제한을 푸는 sysctl과 bwrap 실행 자체를 이 세션의 도구 권한 분류기가 거절했다. 설치한 패키지는 지웠다. 격리 시험은 위 CI(`DML_REQUIRE_BWRAP=1`)가 돌렸다. skip을 통과로 세지 않는다.

### 새 시험이 결함을 잡는가(변이 시험)

#32 트리의 사본에 결함을 하나씩 넣고 관련 시험 모듈을 돌렸다. 변이 없는 기준은 통과했다.

| 변이 | 잡은 시험 |
|---|---|
| M1 `run()`에서 허가 재검사 제거 | #32의 차단 시험 셋 전부(기록 손상, 기록 변경의 모든 사례, 실제 버전 변경·미확인)와 #31의 `test_revoked_inventory_between_plan_and_run_starts_nothing` |
| M2 `run()`이 무조건 거절 | 양성 대조 `test_valid_current_record_runs_the_same_plan_exactly_once` |
| M3 `run()`이 실행 전에 계획을 다시 만듦 | 같은 양성 대조 |
| M4 연결 목록을 다시 set으로 | `test_an_additional_codex_input_mount_changes_the_revision` |
| M5 판 틀이 stdin 질문도 가림 | `test_stdin_matching_an_option_does_not_hide_the_option` |
| M6 기록이 stdin 질문도 가림 | `test_stdin_matching_an_option_does_not_mask_recorded_argv` |
| M7 `assess()`가 `status` 무시 | `test_missing_transport_evidence_cannot_be_promoted_by_self_report` |
| M8 `assess()`가 `boundary_violations` 무시 | 같은 시험, `test_w2_claude_preflight` |
| M9 허가가 30일 만료 무시 | #32 만료 사례, `test_core_eligibility` |
| M10 허가가 버전 변경 무시 | #32 버전 사례 둘, `test_core_eligibility` |

열 개 모두 잡혔다. 변이 스크립트는 저장소 밖에서만 썼다.

### 그 밖

- 인계 2절·5절은 main·#31·#32에서 바이트까지 같다(절별 sha256 비교).
- 새로 커밋된 조회·preflight·C3 JSON에 UUID·이메일·토큰 모양·실제 HOME 경로가 없다. 시험 파일의 `private@example.test`는 합성 값이다.
- main 보호: 브랜치 목록 API에서 `main`의 `protected=true`를 봤다. 세부 설정 API는 이 연결 도구에 없어 읽지 않았다 — 필수 검사 이름과 관리자 적용은 codex·ChatGPT 기록의 관측이다.
- Q4: 병합 전 main의 인계는 "A 권고, B 전환 유지, 선호 미확정"이었다. 사용자에게 전달된 요약의 "A 확정"과 다르다는 ChatGPT의 판단이 맞다. 이 세션도 사용자 결정 절을 바꾸지 않았다.

## 병합을 막지 않는 발견

| # | 발견 | 처리 |
|---|---|---|
| N1 | `NEXT-SESSION.md` 3절 표의 "완료。"에 전각 마침표(U+3002) | 살아 있는 문서라 원본에서 고쳤다(이 PR) |
| N2 | [codex 기록](../2026-09-24-cli-readiness/README.md) 검증 절이 최종 결과를 `VALIDATION.md`에 적는다고 했지만, 실제 최종 결과는 `FINAL-VALIDATION.md`에 있다 | 날짜 기록이라 원문은 두고 [검토 색인](../README.md)에 단서를 달았다 |
| N3 | `python -m app.server --check-cli`는 허가 없음에 종료 코드 2를 쓰는데, argparse 인자 오류도 2다. 종료 코드만으로는 둘을 가를 수 없다(JSON 출력으로는 가려진다) | 낮은 우선순위 후보로 인계 4절에 적었다 |
| N4 | codex·ChatGPT 기록이 인용한 `learn.chatgpt.com` 문서 | 이 컨테이너의 외부 접속 정책이 그 도메인을 막아 열지 못했다. 웹 검색 색인에는 `learn.chatgpt.com/docs/developer-commands.md`가 있고, 설명("model-visible prompt input list as JSON")이 기록과 맞는다. 등급은 "문서, 이 세션 미열람"이다 |

`app/readiness.py`가 비공개 `isolation._trusted_bwrap()`를 부르는 것은 기존 `MockExecutor`의 `_bwrap_trusted()`와 같은 방식이라 결함으로 세지 않았다.

## 확인하지 않은 것

- 사용자 PC의 Windows·WSL 전체 시험, 실제 bubblewrap 격리 실행(로컬), 브라우저. #31의 PC 결과는 codex 기록의 관측이다.
- 실제 CLI·모델, 권한 집행, 문맥 독립성. C3는 failed, Claude는 판 불일치로 허가 없음 — 바뀐 것이 없다.
- main 보호의 세부 설정.

## 다음

실제 서버 연결(순서 6)의 선행 조건은 그대로다: 허가가 나오는 CLI가 없다. ChatGPT 기록의 제안대로, 호출을 늘리기 전에 **같은 설치판·계획·설정에서 문맥이 만들어지는 경로를 관측하고, 합성 표식을 넣은 경우와 뺀 경우를 비교**하는 것이 다음이다. 그 관측은 CLI가 설치된 사용자 PC(`aux-pc-wsl`)에서 해야 한다. 이 웹 컨테이너에는 그 CLI와 쓸 수 있는 격리가 없다.
