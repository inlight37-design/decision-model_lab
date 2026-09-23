# 리뷰 요청 — WSL2 리뷰 반영, A1 모의 앱, 한계 목록과 다음 계획 (2026-09-23)

다른 AI 세션에게 검토를 받기 위한 요청서다. 요청한 쪽은 claude 세션(Claude Opus 5.5)이고, 작업은 사용자 보조 PC(`aux-pc`)의 로컬 checkout과 그 안의 WSL2 배포판(`aux-pc-wsl`)에서 했다. 리뷰어는 **GitHub만 볼 수 있다고 가정한다.**

이번 요청의 중심은 두 가지다.
- 새 [`NEXT-SESSION.md`](../../../NEXT-SESSION.md)의 **한계·못 고친 문제 표(4절, K 번호)**와 **다음 계획(4절 1–4단계)**이 정직하고 충분한가.
- 그 표가 기대는 코드(WSL2 리뷰 반영, A1)가 표에 적힌 대로 동작하는가.

## 사용자가 리뷰어에게 붙여 넣을 요청문

> 저장소 https://github.com/inlight37-design/decision-model_lab 의 `main` 브랜치에서 `docs/reviews/2026-09-23-a1-handoff-request/README.md`를 읽고 그대로 따라 검토해 줘. 결과는 그 문서의 "결과를 남기는 방법"대로 남겨 줘. GitHub에 쓸 수 없으면 결과 전문을 답으로 줘.

## 검토 범위

- **커밋:** `a662e59b0541ea747c50be4b388af9a61dd02b84`(앞 WSL2 리뷰의 기준) → 이 요청서가 병합된 `main`. `git log a662e59..main`으로 본다.
- **범위 안의 작업:**
  1. [WSL2 리뷰(PR #6)](../2026-09-23-wsl2-migration-review/README.md)의 WM-01–WM-07 반영. 반영 기록은 [RESPONSE](../2026-09-23-wsl2-migration-review/RESPONSE.md)에 있다.
  2. A1 controller와 모의 화면([`app/`](../../../app/README.md)).
  3. 인계 문서의 전면 재작성. 이전 판은 [보관본](../../handoff/2026-09-23-before-consolidation.md)이다.
- **리뷰어가 볼 수 없는 것:** 사용자 PC의 상태(WSL 배포판, 로그인, 실행 중인 모의 서버). 기록으로만 판단하고 다르다고 단정하지 않는다 — "확인 필요"로 적는다.
- **모델 호출:** 이 범위에서 한 번도 없다. CLI는 `--version`, `--help`, 로그인 상태 명령만 실행했다.

## 한 일 (요약)

| 무엇 | 어디 | 근거 |
|---|---|---|
| WM-01 입력 전달 상태(`input_delivery`)와 `input_error` | `core/runner.py`, `core/adapters.py` | `test_core_runner.py`, `test_core_adapters.py` |
| WM-02 환경변수 값을 argv에 싣지 않음, 비밀 변수 거절, 기록용 `ExecutionSpec.record()` | `core/isolation.py`, `core/adapters.py` | `test_core_isolation.py`, `test_core_adapters.py` |
| WM-03 격리 진입점 `isolation.run()` 하나, root 소유 bwrap 확인 | `core/isolation.py`, `core/runner.py` | `test_core_isolation.py` |
| WM-04 경로 충돌·symlink 별칭·`never` 겹침 거절 | `core/isolation.py` | `test_core_isolation.py` |
| WM-05 빈·없는 PATH가 부모 PATH로 돌아가지 않음, PE(`MZ`) 거절 | `core/env.py` | `test_core_env.py` |
| WM-06 깊은 중첩·빈 잘못된 타입을 형식 실패로 | `core/adapters.py` | `test_core_adapters.py` |
| WM-07 남은 입출력 스레드를 `runner.lingering()`으로 셈 | `core/runner.py` | `test_core_runner.py` |
| A1 controller: 결과 수용 관문, 봉인, controller 공개, 축소 승인, `unknown` 처리, 다시 시작, 자리와 상한 | `app/controller.py`, `app/store.py` | `test_app_controller.py` |
| A1 수동(원본 앱) 참여자 | `app/controller.py`, `app/static/index.html` | `test_app_controller.py` |
| A1 화면 서버: 모든 `/api`에 토큰, Host 검사, 토큰은 URL fragment로만 | `app/server.py` | `test_app_controller.py` |
| 모의 CLI를 실제 실행 경로로(Windows job object, Linux bubblewrap) | `app/fake_cli.py`, `app/controller.py` | `test_app_controller.py`의 통합 시험 |
| 인계 재작성과 한계 표 | [`NEXT-SESSION.md`](../../../NEXT-SESSION.md) | — |

**시험의 근거.** 새로 넣거나 바꾼 WM 회귀 시험은 수정 전 코어에서 모두 실패하고 수정 뒤 통과하는 것을 확인했다. 확인한 환경은 셋이다: Windows, WSL 시스템 Python, WSL에서 `/usr` 밖에 복사한 Python(CI 조건). A1 모의 앱은 사용자 PC의 브라우저 패널에 띄웠다. claude 세션은 화면을 스크린샷으로 보지 못하고 페이지 글자와 API로 확인했다(K27).

## 잘 안 된 것, 틀렸던 것

- **수동 답의 입력 sha256 검사를 과장했다.** 사용자에게 "답이 이 실행의 질문으로 만든 것인지 확인한다"고 설명했다. 실제로는 화면이 그 실행의 sha256을 자동으로 넣어 보내므로, 이 검사는 **다른 실행에 잘못 넣는 것**만 막는다. `app/README.md`와 controller 문서를 고치고 K21로 올렸다.
- **"입력 일부만 읽음" 모의 행동은 짧은 질문에서 드러나지 않는다.** 입력이 파이프 버퍼에 다 들어가면 CLI가 1바이트만 읽어도 쓰는 쪽은 성공한다. 통합 시험을 큰 입력으로 바꾸고 화면 설명에 적었다(K01).
- **셸 heredoc 안의 파이썬으로 백슬래시가 든 문자열을 고쳐 시험 파일을 깨뜨렸다.** 저장소 규칙이 이미 경고하던 사고다. 편집 도구로 바로잡았고, 인계 5절에 재발로 적었다.
- **인계 문서에 낡은 문장이 남았다.** A1 병합 뒤에도 "controller·화면은 없다"가 1절과 4절에 있었다. 1절은 별도 커밋으로, 4절은 이번 재작성으로 고쳤다.
- **미리보기 도구가 이 세션의 처음 작업 폴더에서 설정을 읽어** 서버를 저장소 밖에서 띄워야 했다. `app/server.py`가 스크립트로 실행돼도 저장소를 찾게 했다. Windows 콘솔 cp949 출력 오류도 고쳤다.

## 읽는 순서

결론에 끌려가지 않도록 **코드·시험·관측을 먼저, 우리의 판정을 나중에** 읽는다.

1. [`AGENTS.md`](../../../AGENTS.md), [`docs/COLLABORATION.md`](../../COLLABORATION.md).
2. [`NEXT-SESSION.md`](../../../NEXT-SESSION.md)의 **2절만**. 논쟁하지 않는 전제다(17: 원본 앱 참여).
3. 앞 [WSL2 리뷰](../2026-09-23-wsl2-migration-review/README.md)의 발견 WM-01–WM-07. 우리의 반영 기록은 아직 읽지 않는다.
4. 코드와 시험:
   - `core/`의 [`runner.py`](../../../core/runner.py), [`adapters.py`](../../../core/adapters.py), [`env.py`](../../../core/env.py), [`isolation.py`](../../../core/isolation.py)
   - `app/`의 [`controller.py`](../../../app/controller.py), [`store.py`](../../../app/store.py), [`server.py`](../../../app/server.py), [`static/index.html`](../../../app/static/index.html), [`fake_cli.py`](../../../app/fake_cli.py)
   - [`tests/`](../../../tests/)의 `test_core_*.py`, `test_app_controller.py`
   - **여기서 스스로 판단을 적어 둔다.**
5. 디자인 규칙: [Ledger 브랜드북](../../../design/project/README.md), [BlindBarrier](../../../design/project/components/BlindBarrier/README.md), [BudgetMeter](../../../design/project/components/BudgetMeter/README.md).
6. 우리의 판정:
   - WSL2 리뷰 [반영 기록](../2026-09-23-wsl2-migration-review/RESPONSE.md)
   - [`app/README.md`](../../../app/README.md)
   - [`NEXT-SESSION.md`](../../../NEXT-SESSION.md)의 1절과 4절(K 표, 1–4단계)
   - 4·5에서 적은 판단과 비교한다.

## 검토 질문 — 중요한 순서

각 질문에 "동의 / 부분 동의 / 반대"와 근거를 적는다. 근거가 없으면 "판단 보류"라고 쓴다.

1. **한계 표(K 번호)의 완전성과 정직성.**
   - 빠진 한계, 잘못 분류된 항목, 과장·축소한 문장이 있는가.
   - "닫는 곳"이 비어 있는 항목(받아들인 한계) 가운데, 2단계 실제 호출 전에 막아야 할 것이 있는가.
2. **WM 반영의 정확성.**
   - `input_delivery`의 의미와 한계.
   - `isolation.run()`의 출처 확인. 경로 충돌 규칙과 Codex의 의도한 겹침.
   - `--clearenv` 없이 bwrap 프로세스 환경으로 변수를 넘기는 방식: bwrap이 더하는 변수가 있는가.
   - `_typed`의 null과 잘못된 타입 구분.
   - 반영 기록의 판정과 다른 의견이 있으면 적는다.
3. **A1 결과 수용 관문과 공개 규칙.** 다음이 D11·D13·D18과 Ledger 규칙(BlindBarrier, BudgetMeter)에 맞는가.
   - 받는 조건: `ok`, 입력 전달 complete, 자손 전체 종료가 모두 맞아야 받는다.
   - `unknown`: 자리를 잡은 채 두고, 다시 부르지 않으며, 사용자 확인으로 자리만 푼다.
   - 공개: 빠진 사람이 있으면 축소 승인을 기다리고, 정족수 미달이면 열지 않는다.
   - 다시 시작: 돌던 시도를 `unknown`으로 둔다.
4. **봉인 투영.** 공개 전에 화면으로 넘어가는 것 가운데 답의 길이나 내용을 암시하는 것이 있는가. 볼 것: 상태가 바뀌는 시각, 실패 사유와 메모, 사건 목록, 토큰 수를 뺀 결과 필드.
5. **제어 API 보안.**
   - 토큰 전달: URL fragment, sessionStorage, Host 검사, 읽기 요청에도 토큰 요구.
   - 토큰이 파일과 서버 출력에 있는 것(K26).
   - Origin 검사나 CSRF 방어가 더 필요한가.
   - 격리된 참여자 쪽에서 닿을 수 있는 것은 무엇인가.
6. **수동(원본 앱) 참여 설계.**
   - K21: 입력 일치를 사용자 확인에 기대는 것.
   - K22·Q6: blind를 확인할 수 없는 참여자를 정족수에 세는 것.
   - Q5: 원본 앱 자동화에 대한 claude 세션의 권고 — 화면 조작은 하지 않고 공식 통로를 관측한다.
   - 더 나은 방법이 있는가.
7. **다음 계획의 순서와 범위.**
   - 1단계 N1–N6(실제 CLI 실행기, WSL용 관측 도구, 인증 연결 좁히기, manifest v2, 수동 참여 보강, 대비)와 2단계 호출(Claude 3회 안팎, Codex 2회 안팎).
   - 빠진 준비나 순서 문제가 있는가.
8. **인계 문서가 새 세션이 시작하기에 충분한가.** 빠진 맥락이나 과한 내용이 있는가. 특히 이전 판에서 옮기지 않은 것 가운데 필요한 것이 있는가 — [보관본](../../handoff/2026-09-23-before-consolidation.md)과 비교한다.

질문 밖이라도 **틀린 사실, 깨진 링크, 기록과 다른 코드**를 찾으면 적는다.

## 결과를 남기는 방법

- 새 브랜치 `<에이전트>/review-a1-<YYYYMMDD>`를 만든다(예: `chatgpt/review-a1-20260924`).
- 리뷰는 `docs/reviews/<YYYY-MM-DD>-a1-handoff-review/README.md`에 쓰고 PR을 연다. [PR 템플릿](../../../.github/pull_request_template.md)을 채우고, 접근 범위에는 실제 범위를 적는다.
- 재현 코드를 돌렸다면 같은 폴더에 스크립트와 결과를 두고, 무엇을 어디서 실행했는지 적는다. 코어 파일의 해시를 고정해 두면 수정 뒤와 헷갈리지 않는다(앞 리뷰의 방식).
- 리뷰 문서의 형식:

| 절 | 내용 |
|---|---|
| 요약 | 가장 중요한 발견 세 개 이내 |
| 발견 | 번호, 심각도(높음·중간·낮음), 위치(`파일:줄` 또는 URL), 근거 등급(**관측** / **재현** / **문서** / **추론**), 내용, 제안 |
| 질문별 답 | 위 1–8에 대한 동의·부분 동의·반대·보류와 근거 |
| 확인하지 못한 것 | 접근할 수 없었거나 읽지 않은 것 |

- **명백한 오류**(오타, 깨진 링크, 기록과 다른 숫자)는 같은 PR에서 원본을 고쳐도 된다. 커밋 메시지에 무엇이 왜 틀렸는지 적는다. **판단이 갈리는 것은 고치지 말고 리뷰에만 적는다.**
- 살아 있는 문서에 검사 수·원장 건수를 적지 않는다(CI가 막는다). `NEXT-SESSION.md`는 절 구성을 유지한 채 3절에 리뷰 브랜치를 적는다.
- 병합은 하지 않는다. 사용자 또는 claude 세션이 CI를 확인한 뒤 병합한다.

## 이미 알고 있는 한계

리뷰어가 같은 지적을 반복하지 않도록 적어 둔다. 전체 목록은 인계 4절의 K 표다. 다르게 판단하면 그 근거를 적는다.

- 모든 관측은 보조 PC 한 대와 그 안의 WSL 배포판 하나, 2026-09-23 하루치다(K35).
- WSL에서 모델 호출이 없다(K36). 실제 CLI 실행기도 없다(K17).
- claude 세션은 CI 원문 로그를 읽지 못한다(K37). 앞 리뷰어는 읽을 수 있었다.
- A1 화면은 스크린샷으로 확인하지 못했다(K27).
