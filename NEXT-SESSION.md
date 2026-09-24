# 다음 세션 인계 — decision-model_lab

최종 갱신 **2026-09-24** · 작성 세션: chatgpt(구독 CLI 실측 경로 연결) · 브랜치 `chatgpt/cli-breakthrough-20260924` · 시작 main `0946bb614172987777fc154bef04ee8c080189b4`(#33 병합 뒤) · 접근: GitHub·웹 컨테이너. 사용자 PC 연결은 도구 호출에서 연결 오류가 났으며 실제 CLI·모델·PC 브라우저는 이번에 실행하지 않았다. 앞선 `aux-pc`/`aux-pc-wsl` 관측은 그대로 보존한다.

현재 인계는 이 파일 하나다. 직전 판은 [보관본](docs/handoff/2026-09-24-before-post-merge-verification.md)에 바이트 그대로 두었고 **사용자 결정(2절)과 금지 사항(5절)은 그대로 유지했다.** 완료 이력과 상세 K 표는 보관본으로 옮겼다. 최신 근거는 [#31·#32 병합 검증](docs/reviews/2026-09-24-merge-31-32/README.md)과 그 대상인 [실행 계약 재검토·무모델 진단](docs/reviews/2026-09-24-cli-readiness/README.md)·[PR #31 독립 재검토](docs/reviews/2026-09-24-pr31-safety-review/README.md), 과거 검토는 [색인](docs/reviews/README.md)에서 찾는다.

## 0. 먼저 확인할 것

1. `git fetch --all --prune`, 열린 PR, `git branch -r --no-merged origin/main`을 먼저 확인한다. 실제 GitHub가 3절보다 우선한다.
2. [AGENTS.md](AGENTS.md)와 [협업 규칙](docs/COLLABORATION.md)을 읽는다. 자기 브랜치에서 작업하고 커밋은 바로 push한다. 사용자 또는 허락받은 claude 세션이 정확한 head의 CI 녹색을 확인한 뒤 main을 병합한다.
3. 접근한 기기를 구분한다. 앞선 PC 관측은 Windows `aux-pc`와 그 WSL2 `Ubuntu-24.04`(`aux-pc-wsl`)다. 뒤의 chatgpt 재검토와 claude 병합 검증은 GitHub와 웹 컨테이너만 접근했으며 사용자 PC·CLI·브라우저를 재실행하지 않았다. 기존 PC 관측은 보존한다. 별도 운용 PC는 관측하지 않았다.
4. 순서 5(실행 계약)는 끝났다. **6의 단일 CLI 서버 연결 코드를 구현했고, 다음은 그 경로의 실제 모델 응답이다.** [실행 방법](app/README.md#첫-실제-실행-기존-k46-계획을-그대로-사용). K46의 입력 폴더 하나 계획을 그대로 재사용하고 문맥 미확인 opt-in으로 실행한다. C3 `failed`와 strict 정책은 그대로이며 Q4·TM은 확정하지 않았다. K46을 다시 부르거나 자료 없는 다른 판을 만들 필요가 없다.
5. 앞선 #28 작업에서는 사용자가 허용한 미실행 실험 범위에서 K46을 Codex 1회·Claude 0회·180초 상한으로 실행해 Codex 예산을 다 썼다. 기존 2단계·K01 승인도 사용했다. 순서 5 재검토·연결 준비, 독립 재검토, 병합 검증은 모두 모델 호출 없이 진행했다. `approve`를 다시 써서 남은 예산처럼 만들지 않는다. 구독 전용이며 사용량 제한 때 멈춘다.

## 1. 지금 상태

**시작 main에는 순서 1–5가 병합돼 있다.** 공유 가림·실행 허가, 격리 연결 모델, 참여자 행 중심 상태/gate, 공개 뒤 모의 합성·원문 대조·조건부 결정 카드·Q4 두 배치, 그리고 실행 계약([`core/contract.py`](core/contract.py))이 있다. 이번 변경은 `--live-cli`로 실제 실행기를 연결하고, 문맥 미확인 등급을 참여자·계획·정족수·보고에 보존한다. 기본 strict 관문, 설치·구독·전송·권한·판/버전/날짜 검사, 시작 직전 허가 재검사는 유지한다. 실제 CLI 시작 예약은 원장에 남아 재시작·실패로 환불되지 않는다. 모의 모드는 기본이며 자동 대체는 없다. 실제 모델 합성/사실 검증은 여전히 없고 모의 합성의 모든 주장은 미해결이다.

| 확인 | 현재 판단과 근거 |
|---|---|
| 병합·CI | #31→#32는 claude 세션이 정확한 head의 push·pull_request CI와 job 로그의 checkout, 로컬 Python 3.12·3.13 전체 검사(격리 시험은 CI만), 변이 시험, 2·5절 동일성을 확인하고 병합했다([병합 검증](docs/reviews/2026-09-24-merge-31-32/README.md)). 그 앞 #22→#23→#24→#25 순서와 각 head의 push CI checkout/Python 3.12·3.13 성공을 [재확인](docs/reviews/2026-09-24-post-merge-verification/GITHUB.md)했다. #25 head와 전체 트리가 같은 것은 문서 정리 전 `fbb7225eaeec72360731d58db214da7375411375`; 검토 시작 main `eec60e9`는 문서만 다르고 코드는 같았다 |
| Windows·WSL | 전체 오프라인 시험 성공. WSL은 `DML_REQUIRE_BWRAP=1`; OS 전용 skip은 구분했다. Windows 진단 stdout의 CP949 오류를 고치고 회귀 검증했다. [검토 기록](docs/reviews/2026-09-24-post-merge-verification/README.md) |
| 실제 브라우저(K27·K42) | aux-pc의 Codex 내장 Chromium에서 localhost 실행→공개→모의 합성, A/B·좁은 폭, 합성 수동 답, 교차 출처 읽기/프레임 차단을 확인했다. 남았던 끝단은 claude 세션이 설치된 Edge 153(headless, Playwright)으로 확인했다(PR #30의 코드). 취소 확인창을 거절하면 취소되지 않고 수락하면 저장됐다. 원문 보고·결정 보고 버튼은 실제 JSON 파일을 저장했고, 내용·해시가 원장과 맞았다. 사람이 직접 누른 조작, 다른 브라우저, 접근성 전수 검사는 미실시 |
| K46 | [실제 확인 성공](docs/experiments/w2-isolation/2026-09-24-k46-confirmation/README.md): Codex 0.156.1, 고정 helper의 쓰기 EROFS·인증 열기 EACCES, 입력/종료/수용 관문 성공. 요청 모델과 실제 제공 모델 일치는 CLI가 보고하지 않아 미확인 |
| Codex 실행 허가 | 기존 K46 manifest와 `contract.LEGACY`를 그대로 둔다. **입력 폴더 하나의 판 `codex@8a0128d4c791` + 명시적 문맥 미확인 정책**에서는 기존 기록을 대조한 오프라인 허가 계산이 성공한다. 자료 없음/둘 이상은 다른 판이라 여전히 거절한다. 현재 PC의 설치·날짜·경계는 `--check-cli`가 재검사한다. C3는 `failed`, strict 허가는 없음. 캐시 변경·토큰 증가만으로 모델 문맥을 단정하지 않는다 |
| Claude 실행 허가 | **순서 5 뒤로 허가 없음.** 기록의 `discussant-1` 관측(2단계 b1)은 stream-json 출력·Read 도구·공통 자료로 본 것이다. 그래서 controller 계획(json, `--tools ""`, 자료 없음)의 판을 뒷받침하지 않고, 대응도 두지 않았다. controller 계획 그대로 다시 관측해야 한다. 문맥 증거가 자기 보고뿐인 문제(K31)도 남는다 |
| 원장 | 스키마 5로 상향 이전(4: 공개 단계, 5: 시도의 실행 종류). 기존 사용 원장은 열기 전에 백업한다. 이번 UI는 별도 임시 데이터 폴더를 사용했고 사용자 시연 원장은 열지 않았다 |
| GitHub 보호 | **PR #31 PC 세션에서 적용 완료·재조회 확인.** main은 PR 경유, `checks (3.12)`·`checks (3.13)` 필수(GitHub Actions에 묶음), 관리자도 적용, 승인 인원 0. 최신 main 재반영 강제는 끄고 force push·삭제는 허용하지 않음. 사용자 직접 설정 불필요. chatgpt 웹 재검토는 branch API의 보호·필수 검사만 독립 확인했고 세부 protection API는 403이었다([범위](docs/reviews/2026-09-24-pr31-safety-review/README.md)). claude 병합 검증도 `protected=true`만 확인했다 |

주인 모듈: [core/](core/README.md)는 실행·어댑터·환경·격리·허가, [app/](app/README.md)는 controller·journal·상태 투영·화면/보고, [tools/w2/](tools/w2/README.md)는 관측이다. 격리의 네트워크 공유·CPU/메모리 상한 부재, 실제 controller 경로의 모델 실측(K17), 계정 사용량 두 층(K23)은 남았다. 이번 검증은 웹 컨테이너의 일반 사용자 오프라인 시험이며 격리 경로는 PR CI에서 확인한다. 실제 구독 모델 호출은 하지 않았다.

기기 기록: [Windows](docs/experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md), [WSL](docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/RESULTS.md), [과거 manifest](docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.v2.json). hostname은 기존 근거에 따라 `aux-pc`로 취급하며 다른 기기라는 사용자 정정이 오면 고친다. Windows 실행 경로는 동결이고 Linux 참여자는 `isolation.run()`으로만 실행한다.

## 2. 사용자가 확정한 것

논쟁하지 않고 전제로 삼는다.

1. **앱을 직접 만들어 붙여 쓴다.** 셸, 오케스트레이션 코어, 근거 저장소가 이 프로젝트의 것이다.
2. **한 제품을 기반으로 채택하지 않는다.** 여러 앱의 장점을 뽑아 최신 이론과 결합하고, 검증으로 신뢰성을 확보하는 것에 같은 비중을 둔다.
3. **CLI가 전제다.** 비대화형 실행, 구조화 출력, resume/cancel, 권한 분리가 필요하다.
4. **구독 사용량을 화면에 띄운다.** 이 기기에서 관측한 값과 계정 전체 잔여(불완전, 파선)를 나눈다.
5. **상태 표시에 자원을 과하게 쓰지 않는다.** 사용량이나 색을 보여 주려고 모델을 더 부르지 않는다.
6. 공식 native 구독 CLI가 우선이다. API·추가 크레딧은 명시적 opt-in만. `agy`는 Gemini CLI가 아니다.
7. 논의자는 읽기 전용, 구현자는 한 writer. 합의는 검증이 아니다. blind 초안·반례·미합의·호출 예산을 보존한다.
8. **여러 AI가 함께 작업한다.** [협업 규칙](docs/COLLABORATION.md)을 따른다. main 병합은 사용자가 하거나, CI 녹색을 확인한 claude 세션이 한다(사용자 허락). (2026-09-23)
9. **V04-01은 절차서로 진행한다.** 로그인은 사용자가 직접 한다. 설치는 사용자 승인을 받고 AI 세션이 실행해도 된다. (2026-09-23)
10. **첫 V04-01은 보조 PC(`aux-pc`)에서 한다.** 운용 PC는 필요할 때 따로 기록한다. (2026-09-23)
11. **GitHub이 유일한 공유 지점이다.** ChatGPT 웹 세션은 GitHub만 보므로 커밋은 바로 push하고, 끝난 작업은 제때 main에 반영한다. (2026-09-23)
12. **어댑터는 CLI 직접 실행(exec)을 우선한다.** ACP는 필요할 때 붙이는 선택지. (Q1, 사용자가 판단을 맡김, 2026-09-23)
13. **유료 API로 전환하지 않는다. 모델은 붙였다 뗐다 하는 구조다.** 구독 경로가 닫히거나 한도를 다 쓰면 그 provider만 뺀다. 빠진 자리를 다른 모델로 조용히 채우지 않고 구성이 줄었음을 표시한다(D18). (2026-09-23)
14. **agy는 CLI adapter로 넣어 두고, 쓸지는 사용자가 고른다.** 기본은 꺼짐이다. 쓸 수 없거나 쓰지 않을 때는 수동 전달(Antigravity에서 직접 실행)로도 참여시키고, 그 과정도 같은 화면에서 보이게 한다. (2026-09-23)
15. **실행 기반은 WSL2로 간다.** Windows는 화면과 사용자 작업, WSL2는 Python controller·실행 원장·봉인 저장소를 맡는다. 참여자는 시도마다 격리된 곳에서 Linux-native CLI를 구독 로그인으로 실행한다. WSL2 설치는 격리·종료·정족수의 해결책이 아니라 기반일 뿐이다. aux-pc의 Windows 네이티브 경로는 두되 더 제품화하지 않고, Codex를 blind 참여자로 쓰는 것은 WSL2에서만 한다. (2026-09-23, [경계 리뷰](docs/reviews/2026-09-23-wsl2-boundary/RESPONSE.md))
16. **격리 백엔드는 bubblewrap을 먼저 시험한다.** 참여자별 파일 허용 목록과 PID namespace로 파일 경계와 수명 경계를 함께 얻는다. W2 경계 시험에 실패하면 rootless podman으로 간다. 두 백엔드를 동시에 제품화하지 않는다. (사용자가 판단을 맡김, 2026-09-23)
17. **각 AI의 원본 앱에서 돌린 결과도 참여시키고, 내용은 우리 화면에서 모두 본다.** agy 수동 경로(14)를 ChatGPT·Claude 앱 등으로 넓힌 것이다. 원본 앱의 기능(컴퓨터 사용, 메모리, 세션 기능)을 그대로 쓰는 대신 blind·사용량은 "관측 안 됨"으로 표시한다. 자동으로 움직이는 방식은 열린 결정 Q5. (사용자 제안, 2026-09-23)
18. **정족수는 "답을 낸 참여자 수"와 "독립성이 확인된 참여자 수"를 나눠 센다(Q6).** 엄격한 blind 비교는 독립성이 확인된 참여자로 정족수를 계산하고, 원본 앱 답은 보조 근거로 함께 보여 준다. 확인되지 않은 참여까지 세는 정책도 고를 수 있지만, 그 결과를 "독립 정족수 충족"으로 표시하지 않고 고른 정책을 실행마다 고정한다. 사용자 확인만으로 독립성 확인을 주지 않는다. (A1 리뷰의 기본안을 사용자가 받아들임, 2026-09-23)
19. **화면 조작 자동화는 하지 않는다(Q5), agy 자동 실행은 꺼 둔다(C2).** 원본 앱 자동화가 필요해지면 공식 통로(Codex `app-server`, Claude CLI 양방향 `stream-json`)를 관측한 뒤 다시 정한다. 모델 호출 승인은 4절 N1–N4를 마친 뒤에 받고, 그때 provider별 최대 시작 횟수·실패 포함 상한·timeout·멈추는 조건을 함께 정한다. (claude 세션의 권고를 사용자가 받아들임, 2026-09-23)
20. **편의·오케스트레이션 기능은 후보로 넣어 두고, 사용량이나 복잡도가 심하면 쓰지 않는다.** 슈퍼바이저 제안, 새 실행으로 넘기기, 공개 뒤 교차검토 같은 기능이다(4절 3단계의 후보 목록). 켜고 끌 수 있게 만든다. 7(blind 초안·호출 예산)과 5(상태 표시에 자원을 과하게 쓰지 않음)는 그대로 지킨다. (사용자, 2026-09-24)
21. **검증만 반복하지 말고 실제 진행을 위한 수정·실험을 수행할 권한을 위임했다.** “직접 수정해봐도되고 모든 권한을 줄테니까 진행좀 나가보자”라는 사용자 요청(2026-09-24). 이번 작업자의 구현 판단은 C3를 거짓 합격으로 바꾸는 대신 명시적 미확인 실측을 여는 것이다. 기존 구독 전용·격리·예산 제한을 없애는 허가는 아니다. 이번 웹 세션은 PC에 연결하지 못해 새 실제 호출을 하지 않았다.

## 3. 진행 중인 작업

**진행 중:** `chatgpt/cli-breakthrough-20260924` — 단일 실제 CLI 서버 연결, 문맥 미확인 등급 보존, 원장 누적 호출 상한, K46 입력 계획 재사용과 회귀 시험. 현재 정확한 head의 검사 결과는 PR/Actions가 기준이다. 사용자 PC 실측은 하지 않았다. 다른 열린 PR은 작업 시작 시 없었다.

- **시작 시 확인한 최신 병합:** #33, `0946bb614172987777fc154bef04ee8c080189b4`. 아래 #31·#32 설명은 앞선 완료 이력이다.

- **마지막 병합:** [PR #31](https://github.com/inlight37-design/decision-model_lab/pull/31)(`codex/cli-readiness-20260924`) → [PR #32](https://github.com/inlight37-design/decision-model_lab/pull/32)(`chatgpt/pr31-safety-review-20260924`). claude 세션이 검증하고 순서대로 병합했다(`b9f14c8`, `daf44d6`). 모델 호출 없음. [병합 검증](docs/reviews/2026-09-24-merge-31-32/README.md).
  - #31: 계획 뒤 허가를 철회하면 `run()`이 시작 전에 막는다 — 같은 계획을 다시 검사할 뿐 새로 만들지 않는다. Codex 자료 폴더 개수가 판에 남는다: 자료 둘 이상은 K46 판(`codex@8a0128d4c791`)이 아니다. stdin 질문이 옵션 문자열과 같아도 판·기록의 옵션이 가려지지 않는다. 화면 행은 시도에 저장된 실행 종류를 표시한다. `app.server --check-cli`, `tools/w2/claude_preflight.py`, C3 무모델 진단을 더했다. [기록](docs/reviews/2026-09-24-cli-readiness/README.md).
  - #32: 계획 뒤 기록 삭제·손상·만료·판/버전/과금 변경과 전송 증거 누락의 회귀 시험, 정상 허가의 양성 대조. 제품 코드는 바꾸지 않았다. [기록](docs/reviews/2026-09-24-pr31-safety-review/README.md).
  - 두 병합 커밋의 push CI는 성공했고, head 브랜치 둘은 자동 삭제됐다.
- **그 앞:** [PR #30](https://github.com/inlight37-design/decision-model_lab/pull/30)(`claude/execution-contract-20260924`) — 순서 5 실행 계약(G4·G6). 모델 호출 없음. [기록](docs/reviews/2026-09-24-execution-contract/README.md).
  - 실행기 계약은 `plan()` → 기록 → `run(plan)`이다. controller와 관측 도구가 같은 계획을 쓰고, 관측 변형도 계획을 만들 때 넣는다.
  - 판은 [`core/contract.py`](core/contract.py)가 계획에서 계산한다. 손으로 쓰던 `SPEC_REVISION`은 없앴다.
  - 원장 스키마 5가 시도의 실행 종류를 저장한다. 보고서는 `a1-draft-report/3`이다.
  - 결과: Claude는 기록의 관측이 지금 계획의 판이 아니어서 허가가 없다. Codex는 여전히 C3 때문에 허가가 없다(1절).
- **그 앞:** [PR #28](https://github.com/inlight37-design/decision-model_lab/pull/28)(codex) — 병합·CI 재검토, 실제 브라우저 관측, 승인된 K46 확인과 새 manifest, Windows 진단 인코딩 수정, 인계 축소. [기록](docs/reviews/2026-09-24-post-merge-verification/README.md). claude 세션이 정확한 head의 push CI와 Windows·WSL 전체 시험, 보관본 동일성, K46 요약의 식별자 부재를 확인하고 병합했다(`e0d21a6`). #29는 그 뒤 인계 정리다.
- **그 앞:** #26으로 #22–#25를 순서대로 통합하고 #27로 자동 삭제 표현을 정정했다. 과거 병합과 정리의 상세는 [GitHub 대조](docs/reviews/2026-09-24-post-merge-verification/GITHUB.md)와 [직전 인계](docs/handoff/2026-09-24-before-post-merge-verification.md)에 보존했다.

| 사용자 판단 | 권고 / 지금까지 한 일 |
|---|---|
| Q4 첫 화면 | A(결정 우선)를 기본으로 권고. 판단·뒤집을 조건·미해결 항목이 먼저 보인다. B는 원문 검토용 전환으로 유지. 실제 A/B 화면을 확인했지만 선호는 확정하지 않았다. 전달된 요약의 “A 확정”을 사용자 결정으로 옮기지 않는다 |
| 순서 5 판 정책 | **권고안대로 구현했다(PR #30).** 옛 이름 판은 실제로 돈 계획과 정확히 같은 것만 대응시켰다. 그래서 `discussant-2`는 K46 계획(자료 하나)만 뒷받침하고, `discussant-1`은 아무 계획도 뒷받침하지 않는다. 자료 없는 Codex 계획까지 `discussant-2`로 인정하려면 동등성 근거와 함께 `contract.LEGACY`에 더한다. 그 판단은 사용자가 원할 때 한다 |
| Claude 재관측 | [준비 도구·설계 완료](docs/experiments/w2-isolation/2026-09-24-claude-preflight/README.md). 설치·구독 로그인까지 무모델로 확인. 정확한 판의 1회·300초는 전송만 확인하며 문맥·권한을 해결하지 못한다. 별도 stream 진단도 완전한 문맥 증거가 아니다. **지금 여러 번 호출하기보다 증거 경로를 먼저 보완**하는 안을 권고; 새 모델 호출/승인 초기화 없음 |
| C3 문맥 | 기존 [관측·한계](docs/reviews/2026-09-24-cli-readiness/GITHUB-C3.md)와 `failed`는 유지한다. strict 검증과 실제 호출 가능성을 분리했다. `--allow-context-unverified`는 C3 의미상 합격만 실행 조건에서 제외하며, 결과를 독립 정족수에 세지 않는다. 전체 최종 요청을 보기 전에는 호출도 못 한다는 순환 선행 조건으로 다시 만들지 않는다 |
| main 보호 | **완료.** PR #31의 codex 세션이 사용자의 기존 권한 위임 범위에서 설정하고 재조회했다. 이번 웹 재검토의 세부 API 접근 한계와 이미 적용된 설정은 구분한다. 필수 검사·관리자 적용을 유지한다 |
| 나머지 선택 | Q3 TypeScript 이행은 미정. TM 계획 A는 후보 유지. agy 기본 끔; 설치/B4는 사용자가 켜기로 결정할 때. 원본 앱 자동화는 끔 |

## 4. 다음 작업

### 구현 순서

1–5는 완료했다. **6의 코드 연결 뒤 첫 실제 응답 → 복수 CLI 연결 → 7** 순서다. 새 프레임워크·SDK나 유료 API를 추가하지 않았다.

| 순서 | 할 일 | 완료 조건 |
|---|---|---|
| 5 · 완료 #30 | 실행 계약 G4·G6 | 최종 계획 한 번 생성 → 기록 → 같은 계획 실행. 판·stderr 표식·요청 모델·자료 연결을 계획이 소유. 실행 종류는 시도에 저장해 재시작 뒤에도 그대로 표시. 공통 자료 첨부는 설계만 했다(아래) |
| 6 · 코드 연결 | 실제 실행기 서버 실측(K17) | `app/README.md`의 K46 동일 계획으로 조회 후 단일 Codex를 실제 호출. 별도 앱 원장, Codex 시작 상한 1·Claude 0·180초, 실패 포함 차감·사용량 제한/UNKNOWN 때 정지. 엄격 정책과 미확인 정책을 구분해 기록. 출력은 실제 CLI·독립성 미확인이어야 하며 원문 보고를 저장. 이전 observe 승인 원장을 초기화하지 않음. 이번 웹 세션에서는 미실측 |
| 7 | B3 사용량 비교 | 원본 앱 직접 사용 / single / cross_check를 같은 질문으로 번갈아 비교. CLI 토큰·시도·시간과 계정 한도 변화는 따로 기록. 토큰과 구독 차감을 비례로 가정하지 않음 |

관측 변형은 계약에 들어 있다(PR #30). Claude b1의 stream-json, `--keep-session`, P3의 틀린 값은 계획을 만들 때 넣으므로 판이 바뀐다. 참여자 계획의 판을 뒷받침하려면 변형 없는 probe로 본다. 판의 지문에는 질문·nonce·임시 경로·HOME·모델 이름을 넣지 않는다(역할로 바꾼다).

- **Claude 재관측 준비 완료:** `claude_preflight.py`의 plan/preflight/assess는 모델 호출 없이 현재 json 참여자 판과 stream 진단 판을 구분한다. result JSON·init·자기 보고로 문맥/권한 칸을 관측 성공으로 올리지 않는다. stream-json을 참여자 명세로 채택해도 전체 문맥 부재의 증거가 저절로 생기지는 않는다. [설계·실측](docs/experiments/w2-isolation/2026-09-24-claude-preflight/README.md).
- **공통 자료 첨부 설계(구현은 6 뒤 화면 작업과 함께):** 실행을 만들 때 자료 파일을 controller 소유 폴더로 복사하고 파일별 sha256 목록을 실행에 고정한다(`never`와 겹치지 않는 별도 폴더). 모든 CLI 참여자에게 같은 폴더를 읽기 전용 `input` 연결로 준다. Claude는 `--add-dir`와 Read 도구, Codex는 연결만 받는다. 자료 유무가 판에 들어가므로 자료 있는 계획은 그 판으로 따로 관측해야 허가된다. 수동 참여자에게는 자료 목록과 해시만 보이고, 원본 앱에 옮긴 것은 확인하지 못한다(K21).

### 남은 실험과 범위

- **K46는 이번 고정 helper 범위에서 완료**했다. 같은 호출을 반복할 필요는 없다. [요약](docs/experiments/w2-isolation/2026-09-24-k46-confirmation/summary.json)은 전송·권한만 뒷받침한다.
- **C3/K44·K09:** 인증/상태/플러그인 연결을 좁히고 입력 직전 문맥을 확인할 수 있는 경로부터 조사한다. 실패 판정을 정책 완화로 몰래 바꾸지 않는다. 새 옵션·연결 변형은 별도 명세와 상한을 기록한다. 다음 확인은 호출을 늘리는 것이 아니다: 같은 설치판·계획·설정에서 기존 진단이 무엇을 보는지 대조하고, 합성 개인 지시문·메모리 표식을 넣은 양성 대조와 뺀 음성 대조를 비교한다([ChatGPT 제안](docs/reviews/2026-09-24-pr31-safety-review/README.md), [C3 관측·한계](docs/reviews/2026-09-24-cli-readiness/GITHUB-C3.md)). CLI가 설치된 `aux-pc-wsl`에서 한다 — 웹 컨테이너에는 그 CLI와 쓸 수 있는 격리가 없다.
- **Claude 재관측:** controller의 최종 계획 그대로(위 probe 설계). 모델 자기 보고 외의 문맥 증거를 먼저 설계한다(K31). 기존 Claude 칸의 값은 바꾸지 않았다 — 판이 맞지 않아 허가에 쓰이지 않을 뿐이다.
- **브라우저 잔여:** 취소 확인창과 실제 JSON 파일 저장은 Edge(headless, Playwright)로 확인했다([기록](docs/reviews/2026-09-24-execution-contract/README.md)). Playwright는 저장소 의존성이 아니라 임시 가상환경에 설치했고, 브라우저는 설치된 Edge를 썼다. 사람이 직접 누른 조작, 교차 브라우저, 접근성은 남는다.
- **B3·agy B4:** 선행 실행 계약/허가와 채택 결정이 있어야 의미가 있다. 권한 부족 때문에 미루는 것이 아니라 선행 조건 미충족이다. 추가 API·크레딧으로 대체하지 않는다.

### 한계와 정리 후보

상세 K01–K46 표와 닫힌 항목의 근거는 [직전 인계 4절](docs/handoff/2026-09-24-before-post-merge-verification.md)에 보존한다. 그 기록 중 **K46·K27·K42의 후속 상태는 이번 인계/관측이 우선**이다. K17·K18의 실제 모델 합성·K23·K31·K32·K38·K44는 여전히 남는다. 네트워크 공유(K08), 자원 상한(K10), 연결 TOCTOU(K14), 수동 독립성(K21·K22), 일반 Ubuntu 정책(K13), 별도 운용 PC(K35)는 이번 시험으로 닫지 않았다.

- 인계 축소(P-2)는 이번에 했다. 끝난 일회성 진단 은퇴와 동결 Windows 코드 이동은 아직 안 했다. 30일 재관측 도구의 대체 경로를 먼저 보존하고 지운다.
- 관측 probe 표 통합은 다음 관측 도구 변경에 묶는다. 원장 ID 범위 수동 사본 제거(P-3), 의미 있는 UI 목록 페이지화/재접속 측정은 후속이다.
- `python -m app.server --check-cli`는 허가 없음에 종료 코드 2를 쓰는데 argparse 인자 오류도 2다. JSON 출력으로는 가려지지만 종료 코드만 보는 스크립트는 둘을 가르지 못한다([병합 검증 N3](docs/reviews/2026-09-24-merge-31-32/README.md)). 낮은 우선순위.
- Bearer help 과가림은 보수적인 표시 문제다. 최소 길이를 섣불리 늘리면 짧은 실제 토큰을 노출할 수 있으므로 이번에는 가림 규칙을 완화하지 않았다.
- 디자인 토큰 대비·발행 아티팩트, quota_projection 실제 응답 대조, Hermes HP-04–HP-10, 원장 recheck, 외부 리뷰 L1–L4, Actions Node 경고·저장소 설명/토픽은 낮은 우선순위 후보로 남는다.
- 편의 후보는 기본 끔: 공개 결정의 다음 실행 전달, 공개 뒤 교차검토 한 라운드, 상급 모델 제안. 사용량 비교 뒤 채택하고 실행별 opt-in·호출 상한을 표시한다.

## 5. 하지 말 것

- **PowerShell `Get-Content`/`Set-Content`로 문서를 일괄 편집하지 않는다.** 한글이 `?`로 바뀐다.
- **백슬래시가 든 텍스트를 셸 heredoc 안의 파이썬으로 고치지 않는다.** `\n`·`\\`가 실제 제어 문자로 바뀐다(2026-09-23에도 한 번 더 발생). 편집 도구를 쓴다.
- 사용자 지시 없이 main에 push하지 않는다(CI 녹색인 작업의 병합은 2절 8). 다른 세션의 브랜치에 push하지 않는다.
- 살아 있는 문서에 검사 수·원장 건수·commit 수를 적지 않는다(CI가 막는다).
- API 키 설정, 추가 크레딧, 권한 우회 플래그를 쓰지 않는다. 인증 파일과 환경변수 값, 계정 이메일·조직 ID·요금제를 기록하지 않는다.
- 문서만 보고 `configured = true`로 만들지 않는다. `runtime-inventory/2` 기록의 칸도 관측 없이 `observed`로 바꾸지 않는다.
- **승인 없이 모델을 부르지 않는다.** 사용량이 막히면 멈추고 알린다.
- **`observe.py approve`는 사용자가 새로 승인할 때만 쓴다.** 다시 쓰면 사용 횟수를 그 뒤부터 센다 — 상한을 늘리는 수단으로 쓰지 않는다. 노트에는 누가·언제 승인했는지 적는다.
- **관측 요약을 읽지 않고 저장소로 옮기지 않는다.** CLI가 쓴 파일 이름에 조직 UUID가 들어 있었다(2단계). 도구가 모양으로 가리지만, 새 모양의 식별자는 못 가린다.
- **exit 0이나 "답이 나왔다"를 성공으로 치지 않는다.** `interpret`의 판정, 입력 전달, 종료 확인을 모두 본다(app의 결과 수용 관문).
- **runner의 `unit_confirmed_empty`나 membership의 판정만 보고 자원·예산을 풀거나 단계를 넘기지 않는다.**
- **Linux에서 참여자를 `isolation.run()` 밖에서 실행하지 않는다.** WSL2 안에서 Windows 실행 파일(`*.exe`, `/mnt/c`의 CLI)을 참여자로 부르지 않고, Windows HOME·자격증명 폴더를 WSL에 연결하지 않는다.
- **초안과 원장을 참여자가 읽을 수 있는 곳에 두지 않는다.** controller 데이터 폴더는 `never`에 넣는다.
- **controller의 상태 전이를 조건 없는 UPDATE로 쓰지 않는다.** 기대한 상태와 시도 ID를 조건에 넣고 바뀐 행 수를 본다(A1 리뷰 A1-03).
- **소비자 앱의 화면을 프로그램으로 조작하지 않는다**(Q5가 정해질 때까지).
- **수동 답의 sha256 일치나 실행 표식 되말함을 "입력 검증"·"독립성 확인"이라고 부르지 않는다**(K21·K22).
- **Claude 데스크톱 앱 안에서 `%LOCALAPPDATA%`에 새로 설치하지 않는다.** 앱 전용 가상 공간에 들어간다.
- **Windows에서 Codex에 `--ignore-user-config`를 줄 때 샌드박스 덮어쓰기를 빼지 않는다.**
- **사용자의 실제 로그인 상태(`~/.claude`·`~/.codex`)를 연결하는 진단은 모델을 부르지 않아도 사용자 허락 뒤에만 한다**(리뷰 질문 3). 먼저 합성 HOME으로 본다(`codex_profile.py` 기본).
- **계획에 CLI 옵션·하위 명령·출력 필드를 적을 때는 기록된 help 줄이나 관측 출력을 함께 적는다**(리뷰 질문 7, S03·S05·S23). 확인하지 않은 것은 "미확인"이라고 쓴다.
- **Linux Codex에 옛 `--sandbox`와 권한 profile을 함께 주지 않는다. exec에 `-P`를 넘기지 않는다** — exec에 없는 옵션이다. profile은 `default_permissions`로 고른다(K46).
- **실측 전에 설계 문서나 원장 항목을 더 늘리지 않는다.**

## 6. 검사

저장소 루트에서 모델 없이 실행한다. Python 의존성은 `requirements-design.txt`의 고정 판을 쓴다. WSL 시스템 패키지가 더 오래돼도 통과할 수 있으므로 판을 확인하고 필요하면 별도 venv를 쓴다. 전역 환경을 바꿀 필요는 없다.

```bash
git config core.hooksPath .githooks
python -m pip install -r requirements-design.txt
python tools/check_encoding.py
python tools/validate_design_tokens.py
python tools/check_frontier_protocol.py
python tools/runtime_inventory.py --host-label <기기> --dry-run
python tools/runtime_inventory.py --validate docs/experiments/w2-isolation/2026-09-24-k46-confirmation/manifest.v2.json
python tools/validate_design.py
python tools/validate_v02.py
python tools/validate_sources.py
python -m unittest discover -s tests -v
python -m compileall -q tools tests core app
```

WSL은 로그인 셸에서 `DML_REQUIRE_BWRAP=1 python3 -m unittest discover -s tests -v`를 실행한다. Windows 명령은 WSL bash 스크립트 파일로 넘기며 참여자를 Windows exe로 바꾸지 않는다. **skip은 통과가 아니다:** 다른 OS 시험, jsonschema 부재, bubblewrap 불가를 구분한다. root 소유 시험의 전제가 달라지지 않도록 일반 사용자로 실행한다.

모의 화면은 `python -m app.server --port 8765 --data-dir <새-시험-폴더>` 뒤 출력된 fragment 토큰 주소로 연다. 기존 사용 원장을 시험에 재사용하지 않는다. 합성 수동 답은 CLI를 끄고 최소 1·include_unverified로 확인하며 원본 앱의 실제 응답이라고 기록하지 않는다. JSON 보고는 원문을 담으므로 공개 저장소에 올리지 않는다.

실제 인증 폴더를 연결하는 무모델 진단도 승인 범위에 포함돼야 한다. 관측은 `tools/w2/observe.py plan` → 승인 상한 기록 → 승인된 call → status 순서이며 예상 밖 결과면 provider를 멈춘다. raw 출력은 저장소 밖에 보존하고 직접 가린 요약만 옮긴다. 이번 K46의 상한은 소진됐다.

aux-pc의 gh는 `C:/ai/tools/gh/bin/gh.exe`. 로그인돼 있으면 정확한 head의 push CI와 job checkout SHA를 읽는다. pull_request run의 API head_sha만 보고 실제 checkout이 head였다고 단정하지 않는다. 인증이 풀리면 사용자 로그인이 필요하며 우회하지 않는다.
