# 다음 세션 인계 — decision-model_lab

최종 갱신 **2026-09-25** · 작성 세션: ChatGPT 웹(격리 컨테이너·GitHub, 사용자 PC 미접근) · 브랜치 `chatgpt/runtime-audit-finish-20260925` · 시작 main `6842406dfaa22f33edc1f44190391b767bd52e13`(PR #45 병합), 미병합 #46 head `5d75bab7cfd53b989585fdcec952e8fd003d6239`를 이어받음. **이 브랜치는 미병합이며 사용량 파서 원격 수정이 남아 있다.**

현재 인계는 이 파일 하나다. 3절은 미병합 후속 작업, 4절은 A–F의 기존 결과와 남은 순서다. PR마다 해당 절만 고친다(부분 갱신은 Git 이력이 보관한다). 크게 다시 쓰기 전 판은 [보관본](docs/handoff/2026-09-24-before-merge-39-next-steps.md)이고 **2절·5절은 그대로다.** 다음 작업의 근거는 [병합 기록](docs/reviews/2026-09-24-merge-39/README.md), 진행 결과는 [A·F 기록](docs/reviews/2026-09-24-account-limits/README.md), [B 기록](docs/reviews/2026-09-24-source-snapshot/README.md), [C 기록](docs/reviews/2026-09-24-model-synthesis/README.md), [D 결과](docs/experiments/2026-09-24-comparison-pilot/RESULTS.md), [E 첫 단계 기록](docs/reviews/2026-09-24-codex-apps-off/README.md), 실제 병렬 실행은 [Windows·계정 한도·병렬 실행 기록](docs/reviews/2026-09-24-windows-live-completion/README.md)에 있다.

## 0. 먼저 확인할 것

1. 열린 PR·현재 main·미병합 브랜치를 먼저 확인한다(`git fetch --all --prune`, `git branch -r --no-merged origin/main`, PR 목록). 실제 GitHub 상태가 이 인계보다 우선이다.
2. [AGENTS.md](AGENTS.md)와 [협업 규칙](docs/COLLABORATION.md)을 읽고 자기 브랜치에서 작업·즉시 push한다. 사용자 또는 권한 받은 Claude가 정확한 head의 CI를 확인한 뒤 병합한다.
3. 이전 판을 쓴 claude 세션은 `aux-pc`의 Windows와 WSL `aux-pc-wsl`에서 시험·변이 시험과 실제 호출(B: Codex 1·Claude 1, C: Claude 1, D: Codex 6·Claude 9, E: Codex 1)을 했다. E에서는 실제 로그인 폴더를 연결한 모델 없는 Codex app-server 조회도 했다. WSL의 Codex 0.156.1·Claude Code 2.1.280이 구독 로그인으로 동작했고, 띄운 서버는 끝냈다. 인증 폴더 내용은 읽지 않았다. 이번 ChatGPT 웹 세션은 그 기록과 코드를 검토하고 오프라인 검사를 했을 뿐, 사용자 PC·로그인·실제 모델을 다시 관측하지 않았다.
4. 실측한 같은 질문을 반복하지 않는다. 필요한 새 실험에는 별도 원장·provider별 상한·멈춤 조건을 기록한다. 기존 소진 원장·권한 관측 원장·병렬 실행 원장을 지우거나 증액하지 않는다.
5. 기존 원장은 새 코드로 열기 전 백업한다(지금 스키마 7 — 공통 자료). 최초 전체·provider별 상한은 원장에 고정되며 재시작으로 늘지 않는다.

## 1. 지금 상태

**main에 PR #38·#39와 다음 작업 A·B·C·D·F, E의 첫 단계(Codex 연결 앱 끄기)가 병합됐다.** provider별 설정(`--live-config`)으로 실제 Codex·Claude를 동시에 부르고, 공통 자료를 같이 주고, 봉인 뒤 함께 공개하고, 원문 대조(모의)나 실행마다 켜는 실제 합성 1회까지 한다. 상한은 원장에 고정되고 시작 전 거절은 실행 수에서 빠진다. Codex 계정 한도는 화면의 명시적 조회로 본다. 시작 직전 허가·격리·봉인·수용·정족수 정책은 그대로다. 별도 오케스트레이터·큐·SDK·유료 API는 없다. 설계 용어로는 `cross_check`(2인 독립 → 대조 → 합성)가 처음으로 끝까지 실제로 돌았다(C). 합성의 인용은 원문과 글자 그대로 대조할 뿐 **사실 검증이 아니다**.

| 항목 | 상태 |
|---|---|
| Windows 검사 | UTF-8 출력 패치와 CP1252 회귀(#39). 병합 검토에서 나머지 검증 도구 넷의 같은 문제를 찾아 고쳤고, Windows CI가 6절의 검증 도구를 단계별로 돈다([N1](docs/reviews/2026-09-24-merge-39/README.md)) |
| 실제 동시 실행 | Codex·Claude 동시 running, 봉인 중 초안 비노출, 두 답 수용·공개, 추가 호출 없는 원문 대조를 확인(#39, 합성 질문 한 건). **공통 자료가 있는 실행**도 확인: 두 답이 같은 자료의 표식·내용을 인용했고 보고서가 자료 목록·해시를 싣는다([B 기록](docs/reviews/2026-09-24-source-snapshot/README.md), 합성 자료 한 파일) |
| 계정 한도 | Codex: `app/codex_account.py`가 격리된 메타데이터 조회를 소유. 화면의 명시적 조회만 프로세스를 띄우고 평소 GET은 캐시만 읽는다. 같은 조회가 `model/list`로 요청 모델이 이 계정의 가용 목록에 있는지도 본다(실제 조회로 확인, 추론 없음). Claude: 마지막으로 끝난 실제 Claude 실행의 stream `rate_limit_event`를 보인다(추가 호출 없음). 봉인 중인 실행·모의 실행의 값은 쓰지 않는다. B의 실제 실행에서 사건·화면·봉인 중 숨김을 확인했다 |
| Claude 권한 | 설치판 2.1.280, `claude-code@126be128bed7`(stream-json/Read/입력 폴더 하나)에서 init의 도구·MCP·dontAsk와 금지된 합성 peer 파일의 Read 거절을 관측. 다른 판의 증거를 복사하지 않음 |
| 실행 관측 기록 | [manifest](docs/reviews/2026-09-24-codex-apps-off/manifest.v2.json). Codex는 연결 앱을 끈 계획 `codex@5a77e0b7dc7f`의 K46 재관측, Claude는 #39의 `claude-code@126be128bed7`. 두 provider 모두 입력 폴더 하나가 필요하다. 판은 경로·내용이 아니라 역할만 보므로 그 폴더에 자료가 있어도 같은 판이다(`core/contract.template`). 날짜·설치판·계획이 바뀌면 준비 조회를 다시 한다. [#39 manifest](docs/reviews/2026-09-24-windows-live-completion/manifest.v2.json)로는 지금 Codex 계획이 거절된다 |
| 독립성·모델 | 양쪽 문맥 미확인, 독립성 확인 정족수 0. 참여자 격리가 `~/.claude`·`~/.codex`를 폴더째 쓰기로 연결하는 것이 구조적 원인이다(4절 E). Codex 참여자에게 열려 있던 계정 연결 앱(GitHub·Google Drive 쓰기 도구 포함)은 E에서 껐다. 로그·shell 스냅샷·상태·메모리 DB 같은 나머지 하위 항목은 아직 모델의 명령이 읽을 수 있다. Claude 보고 모델 일치, Codex 제공 모델 미보고. Codex C3 failed·strict 불허 유지 |
| 원장·서버 | 이전 원장 보존. #39 병렬 원장은 전체 2/2 소진. B·C 원장 `~/.local/state/dml-live-b-20260924`(aux-pc-wsl)은 전체 3/3·Codex 1/1·Claude 2/2로 소진(참여자 2 + 합성 1). D 원장은 [결과](docs/experiments/2026-09-24-comparison-pilot/RESULTS.md)에 적은 대로 소진. E의 K46 상태 폴더 `~/.local/state/dml-observe-e-20260924`는 Codex 1/1 소진. 이전 claude 세션은 자신이 띄운 서버 종료를 확인했다(포트 닫힘·잠금 해제). 이번 웹 세션은 사용자 PC 상태를 재확인하지 않았다 |
| CI·병합 | #39 정확한 head(`948f5a3`)의 push·PR CI와 병합 뒤 main CI가 Linux·Windows 모두 성공. 변이 시험에서 빠진 두 곳(M6·M11)은 시험을 더해 막았다([기록](docs/reviews/2026-09-24-merge-39/README.md)) |

주인 모듈: [core](core/README.md)는 실행·격리·허가·한도 응답 투영, [app](app/README.md)은 controller·원장·계정 조회·화면, [tools/w2](tools/w2/README.md)는 관측이다. 날짜가 붙은 과거 관측은 고치지 않았다.

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
22. **해야 할 일은 모두 승인된 것으로 본다.** 사용자는 바이브코딩으로 만들며 기술 세부를 직접 판단하지 않는다. 권한을 모두 주고 진행하는 것은 계속 해 온 방식이다. 그래서 작업에 필요한 모델 호출·설치·코드 수정과 CI 녹색 병합(8번의 범위 그대로)은 따로 묻지 않고 진행한다. 21번의 권한 위임도 사용자가 이렇게 확인했다. 지키는 것은 그대로다: 구독 CLI만 쓴다(6·13, 유료 API·추가 크레딧 없음). 인증 값을 읽거나 적지 않는다. 호출마다 새 원장·상한·결과를 기록하고, 사용량이 막히면 멈추고 알린다. 비밀번호 입력(`sudo` 등)과 로그인은 사용자가 한다. 사용자는 터미널·WSL을 보지 않으므로 **띄운 서버·프로세스는 세션이 직접 끈다**. 설명은 전문 용어 없이 쉽게 한다. (사용자, 2026-09-24)

## 3. 진행 중인 작업

**실행 경로 후속 감사 진행 중 — 아직 병합하지 않는다.** 시작 시 #46이 열려 있었으므로 이전 “진행 중인 작업 없음”은 현재 상태가 아니다. 실제 상태는 0절대로 GitHub에서 확인한다.

- **이어받은 작업:** [PR #46](https://github.com/inlight37-design/decision-model_lab/pull/46), `chatgpt/runtime-review-20260925` head `5d75bab7cfd53b989585fdcec952e8fd003d6239`. 합성의 실행별 1회·공통 상한·종료 미확인 복구·종료 확인 API/화면과 회귀가 저장돼 있었다. 해당 head의 push·PR CI 성공을 확인했다. 다른 세션 브랜치는 수정하지 않았다.
- **이번 작업:** [PR #47](https://github.com/inlight37-design/decision-model_lab/pull/47), `chatgpt/runtime-audit-finish-20260925`는 그 head 위에 만든 별도 브랜치다. 자료 폴더·목록이 고정 질문과 달라진 복원은 계획·예약 전에 거절하도록 수정했다. 사용량 수치의 극단 정수 오류도 로컬 수정·검증했으나 `core/quota.py`의 GitHub 저장 요청은 도구 보안 판정으로 차단됐다. 원격에는 이를 드러내는 회귀 시험이 있으므로 현재 전체 CI 성공을 주장하지 않는다. [감사·체크포인트](docs/reviews/2026-09-25-runtime-audit-finish/README.md)를 기준으로 이어간다.
- **다음 행동:** 미반영 파서를 검토·반영한 뒤 정확한 새 head의 Linux·Windows 전체 CI를 확인한다. 이 브랜치는 #46 변경을 포함하므로 두 PR을 독립적으로 중복 병합하지 않는다. 사용자 또는 권한 받은 Claude가 통합 PR의 포함 관계와 변경 파일을 확인해 병합한다. 이번 웹 세션은 main에 쓰거나 병합하지 않았다.
- **그다음:** 4절 E의 인증 갱신·동시성 설계와 표식 양성/음성 대조, 실제 취소 관측, D 후속 순서다. 인계의 사용자 결정·금지 사항과 기존 관측·소진 원장은 유지했다.


- **마지막 병합:** [PR #45](https://github.com/inlight37-design/decision-model_lab/pull/45)(`claude/codex-apps-off-20260924`) — 4절 E의 첫 단계(Codex 참여자의 계정 연결 앱 끄기와 K46 재관측, 새 manifest). 모델 호출 1회(Codex). claude 세션이 병합했다(2절 8). [기록](docs/reviews/2026-09-24-codex-apps-off/README.md).
- **그 앞:** [PR #44](https://github.com/inlight37-design/decision-model_lab/pull/44)(`claude/comparison-pilot-20260924`) — 4절 D(작은 비교: 사전 등록과 결과). 모델 호출 15회. claude 세션이 병합했다(2절 8). [결과](docs/experiments/2026-09-24-comparison-pilot/RESULTS.md).
- **그 앞:** [PR #43](https://github.com/inlight37-design/decision-model_lab/pull/43)(`claude/model-synthesis-20260924`) — 4절 C(공개 뒤 실제 합성 1회)와 그 실제 확인. 모델 호출 1회(Claude). claude 세션이 병합했다(2절 8). [기록](docs/reviews/2026-09-24-model-synthesis/README.md).
- **그 앞:** [PR #42](https://github.com/inlight37-design/decision-model_lab/pull/42)(`claude/source-snapshot-20260924`) — 4절 B(공통 자료 스냅샷)와 A·F의 실제 확인. 모델 호출 2회(Codex 1·Claude 1). claude 세션이 병합했다(2절 8). [기록](docs/reviews/2026-09-24-source-snapshot/README.md).
- **그 앞:** [PR #41](https://github.com/inlight37-design/decision-model_lab/pull/41)(`claude/claude-account-limits-20260924`) — 4절 A(Claude 계정 한도 표시)와 F(Codex 가용 모델 확인). 모델 호출 없음, 실제 Codex 메타데이터 조회 1회(추론 없음). claude 세션이 병합했다(2절 8). [기록](docs/reviews/2026-09-24-account-limits/README.md).
- **그 앞:** [PR #40](https://github.com/inlight37-design/decision-model_lab/pull/40)(`claude/merge-39-next-steps-20260924`) — #39 병합 기록, 검증 도구 넷의 Windows 출력 수정과 Windows CI 확장, 변이 시험 빈틈(M6·M11)의 시험 보강, 이 인계의 다음 작업 구체화. 모델 호출 없음. claude 세션이 병합했다(2절 8).
- **그 앞:** [PR #39](https://github.com/inlight37-design/decision-model_lab/pull/39)(`codex/windows-live-completion-20260924`)를 claude 세션이 검토하고 정확한 head로 병합했다(`40b2e67`). 조상인 [PR #38](https://github.com/inlight37-design/decision-model_lab/pull/38)(`chatgpt/cli-unblock-20260924`, 초안)도 함께 들어가 GitHub이 병합됨으로 표시했다. 두 head 브랜치는 자동 삭제됐다. [병합 기록](docs/reviews/2026-09-24-merge-39/README.md).
  - #38(ChatGPT 웹): 스키마 6 상한 고정, 시작 전 거절 회계 분리, provider별 입력·inventory, `--live-config`·`--check-config`, Codex 계정 메타데이터 조회 도구, Node 화면 회귀, Windows CI. Windows 패치는 평문으로만 남겼다.
  - #39(codex): #38의 Windows 패치 적용, 계정 조회를 app·core로 옮기고 화면에 연결, Claude 참여자를 stream-json으로 바꾸고 권한 표면 검사, 실제 Codex·Claude 병렬 응답 관측.
- 그 앞의 병합 이력은 [보관한 인계](docs/handoff/README.md)와 [검토 색인](docs/reviews/README.md)에 있다.

| 사용자 판단 | 권고 / 지금까지 한 일 |
|---|---|
| Q4 첫 화면 | A(결정 우선)를 기본으로 권고, B(원문 대조표 우선)는 전환으로 유지. 화면은 확인했지만 선호는 확정하지 않았다 |
| 실제 합성(4절 C)의 기본값 | 실행마다 켜는 선택(기본 끔)을 권고한다. 호출이 1회 더 들고(2절 5·20), 켜지 않으면 지금처럼 원문 대조표만 낸다. 합성자 모델은 실행마다 사용자가 고른다 |
| 나머지 | Q3 TypeScript 이행은 미정. TM 계획 A는 후보 유지. agy 기본 끔(설치·B4는 사용자가 켜기로 할 때). 원본 앱 자동화는 끔. 편의 후보(공개 결정 전달, 공개 뒤 교차검토, 상급 모델 제안)는 기본 끔 |

미확인 실제 답을 독립 비교로 격상하지 않는다.

## 4. 다음 작업

V04-03(두 provider의 읽기 전용 독립 답변, [완료 조건](docs/architecture/v0.4/03-evaluation-and-roadmap.md))은 #39로 거의 채웠다 — 실제 두 참여자, 입력·초안 digest, 권한 거절, 종료 관측, 사용량 범위. 남은 것은 실제 CLI를 실행 중에 취소하는 관측 하나다(모의 CLI로는 시험했다). 아래 A–F는 그 뒤 진행한 구현·관측의 이력이다. **현재 순서는 3절의 미반영 수정·CI 확인 → E2의 인증 갱신·동시성 설계 → 실제 취소·자료 실험 → D 후속 비교**다. 이미 끝난 A–D를 처음부터 다시 호출하지 않는다. 새 프레임워크·SDK·유료 API는 추가하지 않는다. 실제 호출은 모두 새 원장·provider별 상한·멈춤 조건으로 하고 결과를 기록한다(2절 22). 근거가 된 사실 확인은 [병합 기록 7절](docs/reviews/2026-09-24-merge-39/README.md)에 있다.

| 순서 | 할 일 | 구체 작업 | 완료 조건 | 모델 호출 |
|---|---|---|---|---|
| A | Claude 계정 한도를 화면에(2절 4) — **완료**(B의 실제 실행에서 사건 1번·두 창이 계정 패널에 뜸) | `core/quota.claude_limit`·`core.adapters.claude_rate_limit`이 stream의 마지막 `rate_limit_event`에서 상태와 창별 비율·초기화 시각만 남긴다(결제·식별 칸은 버림). 시도 결과 요약에 넣고, `Controller.claude_account_limit`이 끝난 실제 실행의 값만 계정 패널에 넘긴다. 조회 버튼은 없다(2절 5). [기록](docs/reviews/2026-09-24-account-limits/README.md) | 사건 없음·모양 불일치·범위 밖 값은 미확인이고 답을 보존하는 것이 계약이다. 극단 정수 경계의 미반영 수정은 3절과 후속 감사 R1을 먼저 확인한다. 여러 번 오면 마지막 사건이 기준이며, 그 모양이 다르면 앞 사건으로 대신하지 않는다(계획의 “두 번 오면 미확인”은 다회 실행을 늘 미확인으로 만들어 바꿨다). 봉인 중·모의 값은 안 보인다(실제 실행에서도 봉인 중 숨김 확인). Codex 값과 섞지 않는다 | 0(B 실행에 묻어 감) |
| B | 공통 자료 스냅샷(P0) — **완료** | 실행을 만들 때 텍스트 파일의 내용·sha256을 원장(스키마 7)에 고정하고 목록을 질문 본문에 넣는다. 시도마다 데이터 폴더 밖 사본의 목록·해시를 다시 맞추고, 그 폴더 하나를 모든 CLI 참여자의 읽기 전용 입력으로 준다. 보고서 `a1-draft-report/4`. 수동 참여자에게는 목록·해시만(K21). [기록](docs/reviews/2026-09-24-source-snapshot/README.md) | 판 불변을 시험으로 고정했고 준비 조회가 관측된 두 판 그대로 허가했다. 이름·크기·수정·추가·삭제를 거절한다. 실제 1회에서 두 답이 같은 자료의 표식·내용을 인용했다. 남은 것: 긴 자료·여러 파일·자료 속 지시문(프롬프트 주입), 시도 도중 바꿔치기(K14) | 2(사용) |
| C | 실제 합성 1회(P5, K18) — **완료** | 공개 뒤 사용자가 켠 실행만. 공개 초안을 이름표 D1·D2로 바꿔 그 실행의 CLI provider 하나에 참여자와 같은 계획으로 보낸다. 답은 JSON(주장·인용·갈리는 점·반례·미해결·권고). 인용은 초안에 글자 그대로 있어야 원문 일치이고 `compare_claims`로 다시 대조한다. 일치하는 인용이 없는 주장은 추가 주장으로 표시하되, 이는 일치 인용을 확보하지 못했다는 뜻이지 원문에 없는 사실을 증명한 것은 아니다. 같은 원장의 전체·provider 상한에서 예약한다. [기록](docs/reviews/2026-09-24-model-synthesis/README.md) | 실패·형식 오류·상한 소진이면 원문 보고와 모의 대조표를 그대로 쓴다(Q7). 모든 주장은 미해결 — 사실 검증이 아니다. 실제 1회에서 인용 5개 모두 원문 일치, 추가 주장 0, 반례 보존. D에서 미합의 보존과 부정확한 설명 전이를 함께 봤다. 남은 것은 합성자 교체·충돌 과제·blind 채점으로 일반화 여부를 확인하는 것이다 | 1(사용) |
| D | 작은 비교: 단독 vs 병렬 vs 합성 — **완료(파일럿)** | 과제 셋(계산·코드 결함·제약 있는 설계)과 채점 기준·순서를 호출 전에 커밋했다([사전 등록](docs/experiments/2026-09-24-comparison-pilot/README.md)). 과제마다 Codex 혼자·Claude 혼자·병렬+대조표(Q7)·병렬+합성(`cross_check`) | 결과([RESULTS](docs/experiments/2026-09-24-comparison-pilot/RESULTS.md)): 계산에서 Codex 혼자는 두 번 틀렸고 병렬+합성은 맞혔다(미합의 보존, 합성 손실 0). 다만 합성자가 맞힌 쪽과 같은 Claude라 판단력의 증거는 아니다. 코드는 모두 맞았으나 합성이 한 초안의 부정확한 설명을 받아들였다(인용 대조로는 못 잡음). 설계는 모든 조건이 같은 선택·만점이라 가르지 못했다. 남은 것: 합성자를 Codex로 바꾼 같은 비교, 제약이 충돌하는 설계 과제, blind 채점 | 15(사용) |
| E | 문맥 독립성(C3) — 연결부터 좁힌다 — **첫 단계 완료**(Codex 연결 앱 끄기) | 한 일: 참여자에게 열린 통로를 이름만 조사했다(내용은 읽지 않음). E를 관측한 aux-pc에서는 두 CLI의 사용자 지시문 파일이 없고 Claude는 MCP가 이미 꺼져 있었다. Codex에는 계정 연결 앱(`codex_apps` 도구 198개 — GitHub·Google Drive 쓰기 포함, 호출 가능 앱 9개)이 열려 있어 `-c features.apps=false`로 껐고(0·0), 바뀐 판 `codex@5a77e0b7dc7f`로 K46을 다시 관측해 새 manifest를 만들었다. [기록](docs/reviews/2026-09-24-codex-apps-off/README.md). 남은 계획: 참여자 격리는 `~/.claude`·`~/.claude.json`·`~/.codex`를 폴더째 쓰기로 연결한다(`core/isolation.cli_mounts`). [K09 기록](docs/experiments/w2-isolation/auth-mounts-aux-pc-wsl.md)대로 폴더는 쓰기로 두고(토큰 갱신 때문) 필요 없는 하위 폴더(shell 스냅샷·로그·플러그인 등)를 빈 tmpfs로 덮되, 없는 경로는 덮지 않는다(연결 지점이 사용자 폴더에 생긴다). Codex의 로그·상태·메모리는 폴더가 아니라 버전 붙은 DB 파일(`logs_2`·`state_5`·`memories_1`)이라 덮이지 않는다 — 시도마다 빈 Codex 홈에 로그인 파일만 복사하고 갱신되면 잠금 안에서 되돌려 쓰는 방식을 설계하되, 두 참여자의 동시 갱신 경합과 로그인 손상 위험부터 본다. Claude는 `--safe-mode`(문서상 구독 인증 유지)와 K45(`agents-md@builtin`)부터. `--bare`는 구독 로그인을 쓰지 않으므로 쓰지 않는다 | 모델 없이: 덮은 경로가 격리 안에서 비어 보이고 로그인 상태가 유지되는지. 모델로: 덮개 대신 표식 넣은 합성 파일을 연결한 양성 대조와 빈 덮개의 음성 대조를 같은 계획에서 비교 — 양성에서 표식이 드러나야 음성의 부재가 뜻을 가진다. 연결이 바뀌면 새 판이므로 전송·권한도 다시 관측한다. 사용자의 실제 파일은 고치지 않는다 | 1(사용, K46 재관측). 남은 것 provider별 2–3 |
| F | Codex 가용 모델 확인 — **완료** | app-server의 `model/list`(추론 없음, [문서](https://learn.chatgpt.com/docs/app-server))를 명시적 계정 조회에 붙여 모델 이름만 남기고, 설정한 Codex 모델이 목록에 있는지 계정 패널에 보인다. 준비 조회는 프로세스를 띄우지 않는 조회라 그대로 두었다. 실제 조회에서 `gpt-6-luna`가 가용 목록에 있었다. [기록](docs/reviews/2026-09-24-account-limits/README.md) | "제공 모델"이 아니라 "가용 모델" 확인이다. 실제로 답한 모델 미보고(K32)는 그대로이며 요청 이름으로 보고 칸을 채우지 않는다 | 0 |

새 실행 설정은 [app 안내](app/README.md)와 [직접 관측 기록](docs/reviews/2026-09-24-windows-live-completion/README.md)을 따른다. 계정 상태 조회는 모델을 부르지 않으며 자동 새로 고침으로 프로세스를 계속 실행하지 않는다. 실제 질문 시작은 구독 사용량을 소비한다.

### 남은 범위와 정리 후보

- 실제 CLI를 실행 중에 취소하는 관측(V04-03의 마지막 조건)은 아직이다. 호출 1회가 들며, D의 사전 등록에는 넣지 않았다.
- D의 후속: 합성자를 Codex로 바꾼 같은 비교, 제약이 서로 충돌하는 설계 과제, blind 채점([결과](docs/experiments/2026-09-24-comparison-pilot/RESULTS.md)의 한계). 공통 자료 속 지시문(프롬프트 주입)과 긴 자료·여러 파일은 B 뒤에도 시험하지 않았다.
- Codex의 Windows 경로(`--sandbox read-only`)에는 연결 앱 끄기를 넣지 않았다. Windows에서는 Codex를 blind 참여자로 쓰지 않는다(2절 15). 쓰게 되면 같은 조회로 먼저 확인한다.
- 네트워크 공유(K08), CPU/메모리 상한(K10), TOCTOU(K14), 수동 독립성(K21·K22), 일반 Ubuntu 정책(K13), 별도 PC(K35)는 닫지 않았다. 원본 앱 사용량/품질 비교(2절 17), 접근성 전수·교차 브라우저·원장 규모별 비용·디자인 아티팩트도 남는다.
- 낮은 우선순위: `--check-cli`의 종료 코드 2가 허가 없음과 인자 오류를 가르지 못함([병합 검증 N3](docs/reviews/2026-09-24-merge-31-32/README.md)), Bearer help 과가림, Hermes HP-04–HP-10, 원장 recheck, 외부 리뷰 L1–L4, 저장소 설명·토픽. 목록의 출처는 [이전 인계](docs/handoff/2026-09-24-before-cli-unblock.md) 4절이다.
- #38 기록의 Windows 패치 미적용·계정 응답/화면 미연결·두 provider 응답 미관측은 #39 관측으로 갱신됐다. Claude는 stream-json 계획으로 바뀌었고 그 판을 새로 관측했다 — 옛 json/도구 없음 계획이 관측됐다는 뜻은 아니다. LEGACY 대응을 임의로 넓히지 않는다.

## 5. 하지 말 것

- **PowerShell `Get-Content`/`Set-Content`로 문서를 일괄 편집하지 않는다.** 한글이 `?`로 바뀐다.
- **백슬래시가 든 텍스트를 셸 heredoc 안의 파이썬으로 고치지 않는다.** `\n`·`\\`가 실제 제어 문자로 바뀐다(2026-09-23에도 한 번 더 발생). 편집 도구를 쓴다.
- 사용자 지시 없이 main에 push하지 않는다(CI 녹색인 작업의 병합은 2절 8). 다른 세션의 브랜치에 push하지 않는다.
- 살아 있는 문서에 검사 수·원장 건수·commit 수를 적지 않는다(CI가 막는다).
- API 키 설정, 추가 크레딧, 권한 우회 플래그를 쓰지 않는다. 인증 파일과 환경변수 값, 계정 이메일·조직 ID·요금제를 기록하지 않는다.
- 문서만 보고 `configured = true`로 만들지 않는다. `runtime-inventory/2` 기록의 칸도 관측 없이 `observed`로 바꾸지 않는다.
- **작업에 필요 없는 모델 호출은 하지 않는다.** 필요한 호출은 2절 22로 승인돼 있지만, 호출마다 상한·결과를 기록한다. 사용량이 막히면 멈추고 알린다.
- **`observe.py approve`는 새 호출 계획을 기록할 때만 쓴다.** 다시 쓰면 사용 횟수를 그 뒤부터 센다 — 기존 상한을 늘리는 수단으로 쓰지 않는다. 노트에는 어느 세션이·언제·어떤 승인(2절 22 또는 개별 요청)으로 불렀는지 적는다.
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

저장소 루트에서 실행한다. 의존성은 `requirements-design.txt`, UI 함수 회귀는 Node가 필요하다(CI는 Node 22). 합성/가짜 CLI 검사와 실제 계정·모델 관측을 구분한다.

```bash
python tools/check_encoding.py
python tools/validate_design_tokens.py
python tools/check_frontier_protocol.py
python tools/runtime_inventory.py --host-label <기기> --dry-run
python tools/validate_design.py
python tools/validate_v02.py
python tools/validate_sources.py
python -m unittest discover -s tests -v
python -m compileall -q tools tests core app
```

WSL/Linux 격리 검증은 `DML_REQUIRE_BWRAP=1 python -m unittest discover -s tests -v`다. skip은 통과가 아니며 OS 전용·의존성 부재·격리 불가를 구분한다. CI는 Linux Python 3.12/3.13과 Windows Python 3.13을 실행하고, Windows job도 위 검증 도구를 도구마다 한 단계씩 돈다(PowerShell의 여러 줄 `run`은 마지막 명령의 종료 코드만 본다). 정확한 최신 head의 결과는 PR Checks와 그 job 로그를 확인한다.

Claude 데스크톱 앱이 만든 worktree는 `.git` 파일이 Windows 경로를 가리켜 WSL의 git이 읽지 못한다. WSL에서는 `/mnt/c/...` 경로로 시험만 돌리고 git은 Windows 쪽에서 쓴다. Git Bash에서 `wsl.exe -- bash -lc '…'`로 부르면 작은따옴표 안의 `$변수`도 WSL의 바깥 셸이 먼저 풀어 비므로(2026-09-24 관측) 경로를 직접 적는다.

원장·초안·계정 원시 응답·인증 값은 저장소로 옮기지 않는다. 공개 기록은 허용한 비식별 요약만 남긴다. #39 합성 질문의 답 원문은 codex 세션의 로컬 보고에 있다. 자신이 띄운 서버·참여자의 종료와 포트 닫힘을 확인한다.
