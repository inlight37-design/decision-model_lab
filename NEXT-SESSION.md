# 다음 세션 인계 — decision-model_lab

최종 갱신 **2026-09-23** · 작성 세션: claude (Claude Opus 5.5, 보조 PC의 로컬 checkout) · 브랜치 `claude/n2-observe-tool-20260923`

이 파일 하나에서 시작한다. 절 구성은 고정이고 CI가 확인한다. 규칙은 [AGENTS.md](AGENTS.md)와 [협업 규칙](docs/COLLABORATION.md)에 있다. 이 판은 2026-09-23 작업을 마치며 **통째로 다시 쓴 판**이다. 지난 관측과 결정의 경위는 링크한 기록 문서로 보내고, 여기에는 지금 상태, 한계와 못 고친 문제(4절의 K 표), 다음 일만 둔다. 바로 전 판은 [docs/handoff/](docs/handoff/README.md)에 보관했다.

## 0. 먼저 확인할 것

1. `git fetch --all --prune` 후 GitHub의 열린 PR과 원격 브랜치를 본다. **아래 3절에 없는 PR이 있으면 이 문서가 낡은 것이다.** 실제 상태를 기준으로 한다.
2. 지금 어느 기기인지 확인한다. 이 저장소를 편집해 온 기기는 **보조 PC `aux-pc`(Windows)**와 그 안의 **WSL2 배포판 `Ubuntu-24.04`(이름표 `aux-pc-wsl`)**다. 운용 PC는 관측한 세션이 없다.
3. 이 세션이 무엇에 접근할 수 있는지(사용자 PC / 웹 컨테이너 / GitHub만) 정하고 PR에 적는다.
4. **GitHub만 보는 세션**(ChatGPT 웹 등)이라면 main이 아직 이 파일의 최신판이 아닐 수 있다. 3절의 브랜치에서 이 파일을 다시 읽는다.
5. **모델을 부르는 일은 사용자 승인 뒤에만 한다.** 사용량이 막히면 멈추고 알린다(사용자 요청 — Codex 사용량이 적게 남아 있었다).
6. **A1 검토(PR #7)는 반영했다:** [리뷰](docs/reviews/2026-09-23-a1-handoff-review/README.md)와 [반영 기록](docs/reviews/2026-09-23-a1-handoff-review/RESPONSE.md). 리뷰와 심각도를 다르게 본 곳, 리뷰 밖에서 새로 찾은 것(같은 참여자 이중 실행, Windows의 같은 포트 이중 bind)은 반영 기록에 있다.

## 1. 지금 상태

**실행 코어, bubblewrap 격리, 모의 모드 앱(controller와 화면), 실제 CLI 실행기까지 있다. 실제 실행기는 가짜 CLI로만 시험했고 서버에는 아직 연결하지 않았다. WSL에서는 모델을 아직 한 번도 부르지 않았다. 합성은 없다.** 근거 원장은 E01–E31 / F01–F31, 결정은 D01–D18이다. 검사 수와 결과는 [CI 실행 기록](https://github.com/inlight37-design/decision-model_lab/actions/workflows/checks.yml)이 기준이다.

### 있는 것

| 부품 | 하는 일 | 보장하지 않는 것 |
|---|---|---|
| [`core/runner.py`](core/runner.py) | CLI 한 번을 셸 없이 실행한다. 입력을 다 보냈는지(`input_delivery`), 추적 단위가 비었는지(`unit_confirmed_empty`), 자손 전체가 끝났는지(`tree_confirmed_empty`)를 따로 남긴다. 정리 대기에 상한이 있다 | 격리 없는 POSIX에서 자손 전체의 종료(K03). 벽시계 보장(K05) |
| [`core/adapters.py`](core/adapters.py) | 읽기 전용 논의자의 실행 명세(`build_spec`, 질문은 stdin), 위험 플래그 거절, 출력 판정(`interpret`). 기록은 `ExecutionSpec.record()`만 | 권한 제한이 실제로 지켜지는지 — 관측(B)이 한다 |
| [`core/env.py`](core/env.py) | 자식 환경(과금 변수 제거), 실행 파일 찾기. WSL에서 Windows 실행 파일 거절 | interop 차단의 증명(K16) |
| [`core/isolation.py`](core/isolation.py) | 참여자 한 번을 bubblewrap으로 가둔다. 진입점 `isolation.run()` 하나. 허용한 폴더만, HOME·`/tmp`는 빈 tmpfs, PID namespace, 경로 충돌·비밀 변수 거절, root 소유 bwrap 확인 | 네트워크 격리(K08), 자원 상한(K10) |
| [`core/membership.py`](core/membership.py) | 참여자가 빠지거나 바뀔 때의 결정. 공개 전에는 구성이 바뀔 때마다 정족수를 다시 본다 | 초안이 다 들어왔는지 — controller 관문이 본다 |
| [`app/`](app/README.md) | **A1 controller와 모의 화면.** 입력 고정 → 시도 예약 → 실행 → 결과 수용 관문 → 초안 봉인 → controller가 공개. 참여자는 CLI(지금은 모의 CLI)와 원본 앱(수동). SQLite journal(스키마 버전, 한 번에 한 controller만 연다), 토큰으로 막은 127.0.0.1 화면 서버 | 실제 CLI로 돌린 적 없음(K17), 합성(K18). 수동 답의 입력 일치(K21) |
| [`tools/w2/cli_boundary.py`](tools/w2/cli_boundary.py) | 설치된 Claude·Codex를 격리 안에서 `--version`·로그인 상태만 실행해 본다 | 실제 질의 |
| [`tools/w2/observe.py`](tools/w2/observe.py) | 2단계 관측(tier 2, B1·B2)을 참여자와 같은 격리 경로로 한 번씩 부른다. 승인한 provider별 상한과 멈춤 규칙을 지킨다. **모델 호출** | 승인 없이 부르지 않는다. 아직 한 번도 부르지 않았다 |
| [`tools/v04-03/conformance.py`](tools/v04-03/conformance.py) | Windows에서 논의자 설정을 관측하는 스크립트. 일부 명령은 모델을 부른다 | WSL에서는 쓰지 않는다 — `tools/w2/observe.py`가 맡는다 |
| [`tools/runtime_inventory.py`](tools/runtime_inventory.py) | V04-01 tier 1. 각 CLI의 `--version`/`--help`만 실행해 기록한다 | `observed`·`configured=true`를 쓸 수 없다 |
| [`check_frontier_protocol.py`](tools/check_frontier_protocol.py), [`review_boundary.py`](tools/review_boundary.py), [`audit_design_contrast.py`](tools/audit_design_contrast.py) | 합성 기록의 일관성 **검사**(계산 아님), PR #3의 순수 함수 경계 실험, 디자인 토큰 대비 계산 | controller의 상태 권위가 아니다 |
| [`design/`](design/README.md) | 디자인 시스템 `Ledger`. [발행본 아티팩트](https://claude.ai/artifact/8tq8q5P8Pj7bpUtCF77FZA)와 맞춰 둔다 | 알려진 대비 미달 조합(K24) |

### 기기와 관측

- **`aux-pc`(Windows):** V04-01([결과](docs/experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md))과 V04-03 첫 conformance([기록](docs/experiments/v04-03-conformance/aux-pc.md))가 끝났다.
  - 설치: Claude Code 2.1.280, Codex 0.155.1, agy 1.2.8.
  - 로그인: Claude는 claude.ai 구독(`firstParty`), Codex는 ChatGPT, agy는 Google 계정이다. Claude CLI는 데스크톱 앱과 한도를 공유한다(E04).
  - **Windows에만 해당하는 사실:** Codex의 `--ignore-user-config`가 샌드박스 선택까지 버린다(openai/codex#42172). Codex가 명령을 PowerShell 5.1로 실행한다. 작업 폴더 밖의 다른 참여자 초안도 읽는다. Claude 데스크톱 앱 셸에는 앱이 넣은 변수가 있어 새 터미널 기준 환경으로 실행한다. `%LOCALAPPDATA%` 설치가 앱의 가상 공간에 들어간 적이 있다(agy).
- **`aux-pc-wsl`(WSL2):**
  - 기록: [V04-01 tier 1](docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/RESULTS.md), [W2 경계 시험](docs/experiments/w2-isolation/aux-pc-wsl.md).
  - 환경: WSL 2.7.14, Ubuntu 24.04.5, systemd 켜짐, bubblewrap 0.9.0, AppArmor 꺼짐.
  - 설치: Claude Code 2.1.280과 Codex 0.156.1을 `~/.local/bin`에 설치했다. 로그인도 했다(Claude `claude.ai`·`firstParty`, Codex ChatGPT).
  - PATH에 Windows 쪽 CLI 폴더가 이어 붙어 있다. Codex는 Linux 샌드박스용 bubblewrap을 스스로 들고 온다.
  - **tier 2와 B1·B2는 아직이다**(모델 호출).
- **세 CLI 공통 관측**(aux-pc tier 2):
  - 셋 다 구독으로 비대화형 JSON 호출이 된다. `--bare`는 구독 불가다(F25).
  - Claude `-p`는 기본으로 사용자 플러그인·MCP를 싣는다.
  - 결과에 모델 이름을 주는 것은 Claude뿐이다.
  - agy는 `--output-format`의 없는 값을 조용히 무시한다. agy 기본 모델은 미확인이고, 모델 이름의 Pro/Flash로 품질을 정하지 않는다(사용자 보고).
- **정책:**
  - Gemini CLI 소비자 인증은 2026-06-18에 닫혔다(F30).
  - Antigravity 약관의 제3자 소프트웨어 조항(F31)이 우리 앱의 `agy` 구동에 해당하는지 불명확하다([#711](https://github.com/google-antigravity/antigravity-cli/issues/711)에 Google 답 없음). agy의 유료 크레딧 전환은 꺼져 있고, 데이터 사용도 사용자 요청으로 껐다.

### 기록

| 무엇 | 어디 |
|---|---|
| 검토 기록과 반영(읽는 순서 포함) | [docs/reviews/](docs/reviews/README.md) — 최근: [경계 리뷰](docs/reviews/2026-09-23-wsl2-boundary/RESPONSE.md), [WSL2 리뷰 PR #6](docs/reviews/2026-09-23-wsl2-migration-review/RESPONSE.md) |
| 조사 | [Hermes 패턴 조사](docs/research/hermes-2026-09-23/README.md)와 [교차 확인](docs/research/hermes-2026-09-23/CROSSCHECK.md) |
| 작업 개념도 | [docs/concept/](docs/concept/README.md), [아티팩트](https://claude.ai/artifact/AZJfdnmMBjpEAtqsSHzjp8)(2026-09-22 스냅숏) |
| 지난 인계 | [docs/handoff/](docs/handoff/README.md) |

### 열린 결정

| ID | 질문 | 상태 |
|---|---|---|
| Q3 | 언어/런타임 | Python 코어, TypeScript는 화면 경계만. **지금 화면은 빌드 없는 HTML·JS다** — 이 PC에 node가 없다(K25). TypeScript로 옮길 시점은 미정 |
| Q4 | 첫 화면 | `unresolved`. 결정 우선과 대조표 우선을 같은 내용으로 비교한 뒤 정한다. 합성이 생긴 뒤(4절 3단계) 모의 화면에서 비교한다 |
| Q5 | 원본 앱을 자동으로 움직일지 | **지금은 하지 않는다**(2절 19). 사람이 옮기는 수동 방식만 있다(2절 17). 소비자 앱의 화면을 프로그램으로 조작하면 깨지기 쉽고 약관상 계정 위험이 있다. 자동화가 필요해지면 공식 통로를 관측한 뒤 다시 정한다 |
| Q6 | blind를 확인할 수 없는 수동 참여자를 독립 정족수에 셀지 | **정했다**(2절 18) — 두 수를 나눠 센다. 지금 코드는 아직 **센다**("blind 미확인" 표시만, K22). N5에서 반영한다 |
| C2 | agy 자동 실행을 켤지 | **꺼 둔다**(2절 19). 켤지는 언제든 사용자가 고른다(2절 14). 위험은 기술 실패가 아니라 계정 제재다(F31) |

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

## 3. 진행 중인 작업

**병합 대기 조사: `chatgpt/tmux-patterns-20260923` ([PR #8](https://github.com/inlight37-design/decision-model_lab/pull/8)).** [조사 요약과 시점별 대조](docs/research/tmux-2026-09-23/README.md), [상세 분석](docs/research/tmux-2026-09-23/ANALYSIS.md), [적용·검증 계획](docs/research/tmux-2026-09-23/ADOPTION_PLAN.md), [출처와 한계](docs/research/tmux-2026-09-23/EVIDENCE.md)를 남겼다. ChatGPT가 공식 문서·소스를 조사했고 사용자 PC·WSL·tmux 실행·모델 호출은 하지 않았다. 동시 진행된 N1·N2와 사용자 확정 사항은 보존했다. 권고는 이미 있는 실행기와 관측 도구를 재사용하고, 최신 실행 준비 계획을 유지하면서 재접속·제어·상태 탐색 패턴을 선별 적용하는 것이다. tmux 운영 보조는 선택이며 참여자 실행 엔진 추가는 권하지 않는다. 계획의 시험은 미실행 제안이다. 제품 코드·의존성·디자인 변경은 없다. 최종 CI를 확인한 뒤 사용자 또는 승인된 claude 세션이 병합하고, 이 진행 문구를 정리하되 조사 링크는 기록 절에 남긴다.

마지막 병합: N2 WSL 관측 도구(가짜 CLI로만 시험, 모델 호출 없음, `claude/n2-observe-tool-20260923`). 그 앞: N1 실제 CLI 실행기(가짜 CLI로만 시험, 서버 미연결)와 K02(`claude/n1-cli-executor-20260923`). 그 앞: 사용자가 정한 Q5·Q6·C2와 모델 호출 승인 절차(2절 18·19, `claude/decisions-20260923`). 그 앞: A1 리뷰의 반영(`claude/a1-review-fixes-20260923`) — 봉인 투영의 허용 목록, 결과 수용 관문(입력 전달·빈 답·모델 불일치), 원장 잠금과 조건부 상태 전이, 재시작 재조정과 대기 시도의 명시적 재개, 축소 승인 조건, 경로 충돌 검사, journal 스키마 버전, 문구 정정과 [반영 기록](docs/reviews/2026-09-23-a1-handoff-review/RESPONSE.md). 보조 PC의 Windows와 `aux-pc-wsl`에서 시험했고 모델은 부르지 않았다. 그 앞은 A1 리뷰 자체([PR #7](https://github.com/inlight37-design/decision-model_lab/pull/7))다. 새 작업을 시작하면 여기에 브랜치를 적고, 병합하는 커밋에서 이 줄을 다시 "없음"으로 돌린다. `git fetch`/열린 PR 결과와 다르면 GitHub가 맞다. 2026-09-23의 앞선 병합 이력은 [지난 판](docs/handoff/2026-09-23-before-consolidation.md) 3절과 Git 로그에 있다.

사용자의 판단을 기다리는 것:
- **모델 호출 승인** — 4절 2단계(Claude 3회 안팎, Codex 2회 안팎). 1단계 N1–N4를 마친 뒤에 받는다. 승인할 때 provider별 최대 시작 횟수·실패 포함 상한·timeout·멈추는 조건을 함께 정한다(2절 19).
- 열린 결정 Q3·Q4 — 급하지 않다. Q5·Q6·C2는 정했다(2절 18·19).
- tmux를 운영에 쓸지(WSL에서 controller를 터미널과 떼어 띄워 두기) — 사용자가 살펴보는 중. 참여자 실행이나 초안 작성 중 분할 창 실시간 보기에는 쓰지 않는다는 것이 claude 세션의 판단이다(BlindBarrier, 자손 종료 확인).
- aux-pc 로컬 모의 데이터(`~/.decision-model-lab/mock`)의 첫 실행 하나가 ChatGPT 앱 수동 답을 기다린다 — 시연용이고 저장소와 무관하다. 새 코드로 처음 열 때 journal 스키마가 1로 올라간다.

## 4. 다음 작업

원칙: **또 하나의 큰 설계 문서를 만들지 않는다.** 작은 실행 계약, 회귀 시험, 모의 controller, 한 번씩 읽는 실제 관측 순으로 증거를 쌓는다. 순서는 [WSL2 리뷰](docs/reviews/2026-09-23-wsl2-migration-review/README.md)의 권고(질문 9)를 따른다. exec 우선과 V04-03 순서는 바꾸지 않는다.

| 단계 | 할 일 | 모델 호출 | 선행 |
|---|---|---|---|
| 1 | **실제 호출 전 확인**(아래 N1–N6) | 없음 | 없음 |
| 2 | **승인된 소수 호출:** `aux-pc-wsl` tier 2와 B1·B2를 격리 안에서 한 번씩 읽고 다음을 정한다 | Claude 3회 안팎, Codex 2회 안팎 | 1, 승인 |
| 3 | **A1 이어서:** 합성과 주장 대조, 결정 카드, Q4 비교, 사용량 두 층 표시, 취소 | 없음(모의) | 2의 결과 |
| 4 | **B3 V04-03 pilot과 사용량 비교** | 여러 번 | 3, 승인 |
| — | B4 agy 관측 | 몇 회 | 사용자가 agy를 켤 때 |

### 1단계 — 실제 호출 전 확인 (모델 없음)

**A1 리뷰가 먼저 하라고 한 관문 보강(리뷰의 N0)과 N1·N2는 끝났다** — [반영 기록](docs/reviews/2026-09-23-a1-handoff-review/RESPONSE.md). 아래 N3–N6이 남았다.

- **N1. 실제 CLI 실행기 — 끝남.** [`app/cli_executor.py`](app/cli_executor.py)의 `CliExecutor`: `env.resolve` → `adapters.build_spec` → `isolation.run(cli_mounts(...), never=controller 데이터 폴더)` → `interpret`. Linux·WSL 전용이다(2절 15).
  - 결과 수용은 A1 관문 그대로다. 실행 명세(`ExecutionSpec.record()`)는 시작 사건에 시도 ID와 함께 남는다 — 질문 본문과 원문 argv는 없다.
  - 프로세스를 만들기 전에 거절하면(실행 파일 없음, 모델 이름 없음, 경로 충돌) `failed_to_start`다. agy는 받지 않는다(2절 19, K07).
  - Codex 거절 표식은 보관 상한과 상관없이 stderr 전체에서 센다(K02).
  - 시험: 설치된 모양 그대로 만든 가짜 `claude`·`codex`로 실제 격리 경로를 돈다 — stdin으로 질문 전체 전달, 자기 설정 폴더만 보임, 수용 관문, 늦은 결과 무시([`tests/test_app_cli_executor.py`](tests/test_app_cli_executor.py)). 실제 CLI와 모델은 부르지 않았다.
  - 서버에는 아직 연결하지 않았다. 서버에서 실제 CLI를 고르는 설정(참여자별 전체 모델 이름)은 승인된 호출을 할 때 붙인다.
- **N2. WSL용 관측 도구 — 끝남.** [`tools/w2/observe.py`](tools/w2/observe.py). `CliExecutor.prepare()`로 참여자와 같은 argv·격리 경계를 만들어 probe마다 한 번 부른다. 승인(`approve`: provider별 상한·timeout·메모)이 없거나, 상한을 다 썼거나, 앞 호출이 기대와 달랐으면 부르지 않는다. 실패도 한 번으로 센다. 가짜 CLI로 실제 격리 경로를 도는 시험이 있다([`tests/test_w2_observe.py`](tests/test_w2_observe.py)).
  - aux-pc-wsl에서 `plan`(실행 없음)으로 실제 설치(Claude Code 2.1.280, Codex 0.156.1)의 argv와 연결 경로가 성립하는 것을 확인했다. **로그인 셸(`bash -l`)에서 돌린다** — 비로그인 셸은 PATH에 `~/.local/bin`이 없어 CLI를 못 찾는다.
- **N3. 인증 연결 좁히기 후보(K09).**
  - 확인할 것: `~/.claude`·`~/.claude.json`·`~/.codex` 가운데 무엇이 있어야 로그인 상태 명령이 격리 안에서 되는지를 모델 없이 본다.
  - 토큰 갱신에 필요한 쓰기는 2단계에서 확인한다.
- **N4. manifest `runtime-inventory/2`(옛 A5).**
  - `installed`·`auth_observed`·`transport_observed`·`context_conformance`·`permission_conformance`로 나눈다.
  - 실행 허가(`eligible_for_run`)는 실행 직전에 계산한다(PR #4 R02·R05).
- **N5. 수동 참여 보강(K21·K22).**
  - 복사하는 질문 첫 줄에 짧은 실행 표식(실행 ID와 입력 sha256 앞자리)을 넣고, 원본 앱이 답 첫 줄에 되말하게 한다. 표식이 다른 실행의 것이면 거절한다 — 다른 카드에 붙여 넣는 실수를 실제로 잡는다. 맞아도 검증이 아니라 약한 증거로만 표시한다.
  - 제출할 때 사용자 확인을 따로 저장한다. 사용자 확인만으로 blind 확인(verified)을 주지 않는다.
  - Q6(정함, 2절 18): "답을 낸 참여자 수"와 "독립성이 확인된 참여자 수"를 나눈다. 엄격한 blind 비교는 확인된 쪽으로 정족수를 세고, 원본 앱 결과는 보조 근거로 함께 보인다. 미확인 참여까지 세는 정책도 고를 수 있지만, 그 결과를 "독립 정족수 충족"으로 표시하지 않고 정책을 실행마다 고정한다.
- **N6. 화면 대비(K24).** `unknown` 색을 라벨 글자에 쓰지 않거나, 토큰을 고친다. 토큰을 고치면 `design/`과 아티팩트를 함께 고친다.

### 2단계 — 승인된 소수 호출

한 번 부르고 결과를 읽은 뒤 다음으로 간다. 실패하면 그 provider를 멈추고 원인부터 본다. 실패를 우회 플래그나 다른 백엔드로 조용히 바꾸지 않는다. 승인을 받을 때 provider별 최대 시작 횟수, 실패를 포함한 상한, timeout, 멈추는 조건을 함께 정한다("3회 안팎"은 계획 추정치다, A1 리뷰 질문 7). tier 2와 B1·B2를 같은 호출로 확인할 수 있으면 겹쳐 부르지 않는다.

- **절차(aux-pc-wsl, 로그인 셸, 저장소 루트):** `observe.py plan`으로 실행할 argv를 확인 → 사용자 승인을 `observe.py approve --claude N --codex M --timeout 300 --note "…"`로 적는다 → `observe.py call <probe> <전체 모델 이름>`을 하나씩 부르고 결과를 읽은 뒤 다음으로 간다. 제안하는 probe와 상한: Claude `b1`·`p3-claude`(+ 선택 `b1-combo`) = 3, Codex `b2`·`p3-codex` = 2(사용량이 남으면 `plain-codex`). `p3`는 모델 응답 없이 거절돼야 하는 호출이지만 상한에는 센다. 요약은 `docs/experiments/`에 옮기고 원 출력은 저장소 밖에 둔다.
- **tier 2(`aux-pc-wsl`):** [V04-01 절차서](docs/experiments/v04-01-inventory/README.md)의 구독 호출. Windows 기록을 복사하지 않는다. `b1`(구독 인증·구조화 출력·깨끗한 문맥, P1·P4), `p3-*`(잘못된 값, P3), `plain-codex`(P1·P4)가 겹친다.
- **B1. Claude.** 격리 안에서 다음을 본다.
  - 위치 인자 없는 `-p`가 stdin을 질문으로 읽는지(K29)
  - `CLAUDE.md`를 싣지 않는지: 자기보고 대신 stream-json의 init 이벤트로 본다(K31)
  - `--restricted`와 `--safe-mode`를 함께 준 조합, 토큰 갱신 쓰기, 큰 한글·선행 대시 입력
  - CLI가 보고한 입력 토큰과 입력 크기가 대략 맞는지(K01의 보강 후보)
- **B2. Codex.** bubblewrap 안에서 다음을 본다.
  - 허용 자료는 읽고 다른 참여자 초안은 못 읽는지
  - 자체 bubblewrap의 중첩(K12)
  - 명령 거절 문자열(K30)
  - stdin만 받은 논의자가 도구를 시도하지 않는지와 입력 토큰. Windows 첫 관측은 도구 시도 때문에 27,000–41,000토큰이었다.

### 3단계 이후

- **A1 이어서:**
  - 합성자와 합성 없는 보고(`report_without_synthesis`)
  - [결정 카드](design/project/components/DecisionCard/README.md)
  - 첫 화면 Q4 비교
  - 사용량 두 층 표시(2절 4, K23)
  - 취소(K19)
  - 공통 자료 첨부(옛 A6)
  - 결과 폴더 감시(옛 A2)
- **B3 pilot:** Claude와 Codex가 서로 모르게 읽기 전용 초안을 내고 합성한다.
  - 배경: 사용자는 AionUi를 쓰지 않는다. 각 앱을 직접 쓸 때보다 사용량을 몇 배 빨리 소모했기 때문이다. 우리 앱이 같은 문제를 만들지 않는지가 B3의 목적이다.
  - 같은 질문을 세 방식으로 돌려 비교한다: (a) 각 앱에서 직접, (b) 우리 앱의 `single`, (c) `cross_check`.
  - **구독 한도는 토큰에 비례해 줄지 않는다**(사용자 지적). 그래서 두 층으로 잰다: CLI가 보고한 토큰·호출 수·시간(비교 기준), 그리고 각 회사가 보여 주는 한도 %를 묶음 전후로 읽은 값(실제 효과, 잡음 있음).
  - 같은 시간대에 번갈아 여러 번 돌려 범위로 적는다. Codex의 한도 조회 경로(app-server)는 문서에만 있고 미시험이다.
- **B4 agy(사용자가 켤 때):**
  - 없는 `--model`·`--effort` 값의 처리를 본다.
  - stream-json init의 `model`을 요청값과 대조한다.
  - stdin 입력이 되는지 본다(K07).

### 알려진 한계와 못 고친 문제

해결 전까지 이 표를 기준으로 지킨다. "닫는 곳"이 비어 있으면 지금은 받아들인 한계다.

| ID | 영역 | 한계·문제 | 지금의 대응 | 닫는 곳 |
|---|---|---|---|---|
| K01 | 실행 코어 | "CLI가 입력 일부만 읽고 닫음"은 입력이 파이프 버퍼보다 클 때만 쓰는 쪽에서 드러난다. 파이프에 다 썼다는 것이 CLI가 다 읽었다는 증거도 아니다 | `input_delivery`를 남기고, 완전하지 않으면 `input_error`. A1은 전달 기록이 없는 결과(`None`)도 받지 않는다 | B1에서 보고된 입력 토큰과의 대조를 본다 |
| K02 | 실행 코어 | Codex 명령 거절은 stderr의 문자열로만 안다. Linux Codex의 그 문자열은 아직 모른다(K30) | runner가 보관 상한과 상관없이 stderr 전체에서 표식을 센다(`stderr_counts`, 실제 실행기가 요청). 셀 수 없었는데 stderr가 잘렸으면 답을 받지 않는다 | B2(문자열) |
| K03 | 실행 코어 | 격리 없는 POSIX 실행은 자손 전체의 종료를 확인하지 못한다 | `tree_confirmed_empty=None` → 앱은 `unknown`. Linux 참여자는 `isolation.run()`으로만 | — |
| K04 | 실행 코어 | 돌아온 뒤에도 파이프를 쥔 자손이 있으면 입출력 스레드·fd가 남는다(격리 없는 POSIX) | `runner.lingering()`으로 세고 정리 안 된 시도의 상한에 넣는다 | 격리 경로에서는 namespace가 정리한다 |
| K05 | 실행 코어 | `CLEANUP_LIMIT`는 명시적 대기의 상한이지 벽시계 보장이 아니다 | 문구를 한정했다 | — |
| K06 | 실행 코어 | Windows: job 배정 전에 생긴 자식은 추적하지 못한다. 끝낸 직후 프로세스 객체가 신호를 받기까지 짧은 틈이 있다 | 문서화, 시험이 기다린다 | Windows 경로는 동결(2절 15) |
| K07 | 실행 코어 | agy는 질문을 명령줄로 보낸다(stdin 미확인). 그래서 `RunResult.argv`에 질문이 들어 있다 | 기록은 `ExecutionSpec.record()`로 | B4 |
| K08 | 격리 | 네트워크를 공유한다. 참여자가 localhost 포트와 abstract unix 소켓에 닿고, 네트워크 서비스에 시켜 만든 작업은 종료 보장 밖이다 | 앱의 제어 API는 토큰으로 막았다 | 미정 |
| K09 | 격리 | `~/.claude`·`~/.codex` 전체를 쓰기로 연결한다. 그 배포판에서 대화형으로 쓴 그 CLI의 세션 기록이 참여자에게 보인다 | 기록해 두었다 | N3, 2단계 |
| K10 | 격리 | 메모리·CPU 상한이 없다 | — | 미정 |
| K11 | 격리 | `/etc` 전체와 `/usr`가 읽기 전용으로 보인다. 설정과 민감한 값이 있을 수 있는 호스트 경로다 | 신뢰 범위로 둔다. `never`는 이 자동 연결과도 비교해 겹치면 거절한다(A1 리뷰 A1-04) | — |
| K12 | 격리 | Codex 자체 bubblewrap이 우리 bubblewrap 안에서 도는지 모른다. `--disable-userns`는 쓰지 않았다 | — | B2 |
| K13 | 격리 | `aux-pc-wsl`은 AppArmor가 꺼져 있고, CI는 user namespace 제한을 sysctl로 푼다. 제한이 켜진 일반 Ubuntu에서의 운영은 보지 않았다 | — | 새 기기에서 확인 |
| K14 | 격리 | 경로 검사와 마운트 사이에 파일이 바뀌는 경쟁 | 문서화 | — |
| K15 | 격리 | bwrap 신뢰는 root 소유 `/usr/bin/bwrap` 확인이다. 같은 Python 프로세스 안의 코드가 내부 함수를 부르는 것은 막지 못한다 | 문서화 | — |
| K16 | CLI·환경 | WSL의 Windows 실행 파일 가드는 경로·링크·`MZ` 내용으로 판정하는 경험칙이다. 사용자가 바꾼 automount root는 PATH 필터가 모른다 | 격리가 `/mnt`·`/init`·`/run`을 연결하지 않는 것이 실제 차단이다 | — |
| K17 | 앱 | 실제 CLI 실행기(`app/cli_executor.py`)는 가짜 CLI로만 시험했다. 서버는 아직 모의 실행기만 쓴다 | 실제 격리 경로·수용 관문·늦은 결과 시험(WSL, CI) | 2단계(승인된 호출) |
| K18 | 앱 | 합성, 주장 대조, 결정 카드, Q4 비교가 없다. 초안 공개까지만 있다 | — | 3단계 |
| K19 | 앱 | 취소가 없고, 취소 중 입력 전송 시험도 없다. 서버를 끄는 것이 지금 유일한 멈춤 수단이다 | 다시 시작한 뒤 대기 시도는 사용자가 "이어서 시작"을 눌러야 시작한다. 멈춘 상태는 메모리에만 있다 | 3단계 |
| K20 | 앱 | 원장 잠금은 한 기기 안의 파일 잠금이다. 기기 여러 대가 한 원장을 나눠 쓰는 것은 지원하지 않는다. 사건 순서는 실행별 순번뿐이다 | 한 원장은 한 controller만 연다. 시작과 결과 반영은 기대한 상태·시도 ID가 맞을 때만 하고, 늦은 결과는 사건으로만 남긴다(A1 리뷰 A1-03) | — |
| K21 | 앱 | 수동 답의 입력 sha256 검사는 화면에서는 사실상 늘 통과한다 — 화면이 그 카드의 digest를 자동으로 넣는다. 막는 것은 화면 밖 요청의 불일치, 공개 뒤·중복 제출, 빈 답이다. 다른 실행의 답을 붙여 넣는 것도, 원본 앱에 그 질문을 넣었는지도 확인하지 못한다 | 문서에 적었다(A1 리뷰 A1-08) | N5 |
| K22 | 앱 | blind를 확인할 수 없는 수동 참여자를 독립 정족수에 센다 | "blind 미확인"으로 표시 | Q6, N5 |
| K23 | 앱 | 구독 사용량 두 층 표시(2절 4)가 없다. 예산은 실행별로 CLI 참여자당 한 번이고, 실행 간 누적 예산이 없다 | — | 3단계, B3 |
| K24 | 앱 | 화면이 `unknown` 색을 11px 라벨 글자에 쓴다 — 알려진 대비 미달 조합이다 | — | N6 |
| K25 | 앱 | 화면이 TypeScript가 아니라 빌드 없는 HTML·JS다(node 없음) | — | Q3 |
| K26 | 앱 | 제어 API 토큰은 controller 데이터 폴더의 파일과 서버 출력에 있다. 격리 밖에서 같은 사용자로 도는 프로세스는 읽을 수 있다 — 신뢰 경계는 사용자 계정이다 | 격리 안에는 그 폴더를 연결하지 않는다(`never`). 토큰 파일은 처음부터 0600으로 만들어 통째로 바꾸고, 데이터 폴더는 0700이다(POSIX) | — |
| K27 | 앱 | claude 세션은 A1 화면을 스크린샷으로 확인하지 못했다(브라우저 패널이 가려짐). 페이지 글자와 API로만 확인했다 | — | 사람이 보고 알려 주면 닫힌다 |
| K28 | 앱 | journal 이전은 올리는 방향뿐이다. 되돌리는 절차는 없다 | 스키마 버전(`user_version`)을 두고, 예전 journal은 열 때 한 거래로 올린다. 새 버전 journal은 건드리지 않고 거절한다(A1 리뷰 반영) | — |
| K29 | CLI | `claude -p`가 위치 인자 없이 stdin을 질문으로 읽는 것을 설치 버전에서 관측하지 않았다(문서 근거뿐) | — | B1 |
| K30 | CLI | Linux Codex의 명령 거절 문자열을 모른다. `tools_rejected`는 Windows 문자열을 찾는다 | — | B2 |
| K31 | CLI | Claude가 `CLAUDE.md`를 싣지 않는다는 것은 모델의 자기보고뿐이다 | — | B1 |
| K32 | CLI | Codex·agy는 결과에 모델 이름이 없어서 조용한 강등을 결과로 잡지 못한다 | — | B4(agy init) |
| K33 | 도구 | WSL용 관측 도구([`observe.py`](tools/w2/observe.py))는 가짜 CLI로만 시험했다. 실제 호출은 한 번도 없다. Claude의 init 이벤트 필드는 aux-pc 기록과 V04-01 절차서에 기댄 것이다 | 요약은 필드를 골라 옮기고, 모르는 필드는 이름만 남긴다 | 2단계 |
| K34 | CLI | Windows 전용 사실(Codex #42172, PowerShell 5.1 재시도, 작업 폴더 밖 읽기) | adapter의 `codex_windows_sandbox`. Codex blind 참여는 WSL에서만 | Windows 경로는 동결 |
| K38 | CLI | Codex는 작업 폴더의 `AGENTS.md`를 싣는다 | 참여자 작업 폴더는 controller가 시도마다 만든 빈 폴더다(지시문 파일 없음). 실제 실행기도 그 폴더에서 돈다 | — |
| K39 | CLI | Codex의 read-only 샌드박스는 쓰기만 막고 읽기는 막지 않는다 | 읽기 경계는 bubblewrap 허용 목록이 맡는다. 확인 전까지 Codex 초안의 blind는 "미확인" | B2 |
| K40 | CLI | agy는 `--output-format`의 없는 값을 조용히 무시한다 | adapter가 값을 고정하고, JSON이 아니면 형식 실패 | — |
| K35 | 과정 | 모든 관측은 PC 한 대와 그 안의 WSL 배포판 하나, 2026-09-23 하루치다. 운용 PC 관측이 없다 | — | 필요할 때 같은 절차서로 |
| K36 | 과정 | WSL에서 모델 호출이 0회다. 격리 안에서 실제 질의가 끝까지 도는지 모른다 | 모의 CLI로 같은 경로를 탔다 | 2단계 |
| K37 | 과정 | claude 세션은 CI 원문 로그를 읽지 못한다(익명 요청 403). 리뷰어는 읽을 수 있었다 | CI는 `DML_REQUIRE_BWRAP=1`로 격리 시험의 건너뛰기를 막는다 | — |
| K41 | 앱 | 공개 전에도 참여자 상태가 바뀌는 시각을 반복 조회로 대략 알 수 있다. 정확한 시간·토큰·길이는 넘기지 않는다 | 운영자용 거친 상태로 허용한다. 참여자에게는 제어 API 토큰이 없다(A1 리뷰 질문 4) | — |
| K42 | 앱 | 제어 API의 방어는 Bearer 토큰, Host 검사, 요청 크기 상한뿐이다. Origin 허용 목록, 콘텐츠 타입 강제, 프레임 삽입 정책, 읽기 시간 제한, 브라우저 교차 출처 음성 시험이 없다 | 토큰을 머리글로만 받으므로 교차 출처 요청은 preflight에서 막힌다고 본다 — 브라우저로는 시험하지 않았다(A1 리뷰 질문 5) | 급하지 않음 |
| K43 | 앱 | 보고된 모델이 요청과 다르면 받지 않고 구성 축소로 드러낸다. 받아들일지 사용자에게 묻는 보류 상태는 없다. 별칭으로 요청하면 보고된 전체 이름과 달라 보일 수 있다 | 요청은 전체 이름으로 한다(N1) | B1 |

### 급하지 않은 것

- 대비 미달 5쌍의 토큰 수정(N6과 함께). `design/`과 아티팩트를 함께 고친다.
- `review_boundary.quota_projection`의 가정(`resetsAt` 단위, 한도 ID 형식)을 실제 한도 응답(B3)으로 확인한다.
- Codex 읽기 금지 설정(권한 프로필의 `"deny"`)은 추가 방어층이다. 쓰려면 adapter 금지 목록(`-c`·`--profile`)을 조정해야 한다.
- Hermes 후속 후보(HP-04–HP-10)는 pilot 뒤에 하나씩.
- v0.4 원장의 `recheck` 미기입, 외부 리뷰의 저우선 지적 L1–L4, 개수 lint의 SHA 예외 범위, Actions의 Node 20 경고, GitHub 저장소 설명·토픽.

### 참고

- **다른 AI의 리뷰가 오면:**
  1. 발견마다 원 출력·코드로 확인한다(재현 스크립트가 있으면 먼저 그대로 돌린다).
  2. **맞으면 원본에서 고치고 회귀 시험을 붙인다. 틀리면 근거를 리뷰 폴더의 반영 기록에 답으로 단다.**
  3. 리뷰 원문은 고치지 않는다. 판단이 갈리는 것은 사용자에게 묻는다.
  4. CI 녹색이면 병합하고 [검토 목록](docs/reviews/README.md)을 갱신한다.
  - 선례: [WSL2 리뷰 반영](docs/reviews/2026-09-23-wsl2-migration-review/RESPONSE.md).
- **WSL을 Windows 쪽에서 부를 때:** PowerShell 5.1에서 `wsl.exe`로 넘기는 인자는 따옴표와 `$`가 깨진다. 명령을 스크립트 파일로 넘긴다. Git Bash의 명령줄 한글은 ANSI 코드페이지로 바뀐다 — 요청 본문은 파일이나 stdin으로 보낸다.
- **보조 스크립트와 함정:** [`tools/v04-01/`](tools/v04-01/README.md), [`tools/v04-03/`](tools/v04-03/README.md), [`tools/w2/`](tools/w2/README.md), V04-01 절차서의 "AI 세션이 Claude 데스크톱 앱 안에서 대신 실행할 때" 절.
- **Hermes에서 옮기면 안 되는 동작**(마감 뒤 답 텍스트를 완료로 수용, 다른 CLI 로그인 빌려 쓰기 기본값, 매 턴 추가 호출, `--fallback-model`)은 [교차 확인](docs/research/hermes-2026-09-23/CROSSCHECK.md)에 있다.

## 5. 하지 말 것

- **PowerShell `Get-Content`/`Set-Content`로 문서를 일괄 편집하지 않는다.** 한글이 `?`로 바뀐다.
- **백슬래시가 든 텍스트를 셸 heredoc 안의 파이썬으로 고치지 않는다.** `\n`·`\\`가 실제 제어 문자로 바뀐다(2026-09-23에도 한 번 더 발생). 편집 도구를 쓴다.
- 사용자 지시 없이 main에 push하지 않는다. 다른 세션의 브랜치에 push하지 않는다.
- 살아 있는 문서에 검사 수·원장 건수·commit 수를 적지 않는다(CI가 막는다).
- API 키 설정, 추가 크레딧, 권한 우회 플래그를 쓰지 않는다. 인증 파일과 환경변수 값, 계정 이메일·조직 ID·요금제를 기록하지 않는다.
- 문서만 보고 `configured = true`로 만들지 않는다.
- **승인 없이 모델을 부르지 않는다.** 사용량이 막히면 멈추고 알린다.
- **exit 0이나 "답이 나왔다"를 성공으로 치지 않는다.** `interpret`의 판정, 입력 전달, 종료 확인을 모두 본다(app의 결과 수용 관문).
- **runner의 `unit_confirmed_empty`나 membership의 판정만 보고 자원·예산을 풀거나 단계를 넘기지 않는다.**
- **Linux에서 참여자를 `isolation.run()` 밖에서 실행하지 않는다.** WSL2 안에서 Windows 실행 파일(`*.exe`, `/mnt/c`의 CLI)을 참여자로 부르지 않고, Windows HOME·자격증명 폴더를 WSL에 연결하지 않는다.
- **초안과 원장을 참여자가 읽을 수 있는 곳에 두지 않는다.** controller 데이터 폴더는 `never`에 넣는다.
- **controller의 상태 전이를 조건 없는 UPDATE로 쓰지 않는다.** 기대한 상태와 시도 ID를 조건에 넣고 바뀐 행 수를 본다(A1 리뷰 A1-03).
- **소비자 앱의 화면을 프로그램으로 조작하지 않는다**(Q5가 정해질 때까지).
- **수동 답의 sha256 일치를 "입력 검증"이라고 부르지 않는다**(K21).
- **Claude 데스크톱 앱 안에서 `%LOCALAPPDATA%`에 새로 설치하지 않는다.** 앱 전용 가상 공간에 들어간다.
- **Windows에서 Codex에 `--ignore-user-config`를 줄 때 샌드박스 덮어쓰기를 빼지 않는다.**
- **실측 전에 설계 문서나 원장 항목을 더 늘리지 않는다.**

## 6. 검사

```bash
git config core.hooksPath .githooks
python -m pip install -r requirements-design.txt
python -m unittest discover -s tests -v
python tools/validate_sources.py
python tools/validate_design_tokens.py
python tools/check_encoding.py
python tools/runtime_inventory.py --host-label <기기> --dry-run
```

- `jsonschema`가 없으면 해당 검사는 skip된다. **skip은 통과가 아니다.**
- CI(Linux)는 bubblewrap을 설치하고 `DML_REQUIRE_BWRAP=1`로 격리 시험의 건너뛰기를 막는다.
- Windows 경로(job object)는 CI가 돌리지 않으므로 Windows에서 한 번 돌린다.

WSL(`aux-pc-wsl`)에서 저장소 루트로:

```bash
DML_REQUIRE_BWRAP=1 python3 -m unittest discover -s tests
python3 tools/w2/cli_boundary.py
```

모의 화면은 `python -m app.server --port 8765`로 띄우고, 출력된 `#token=` 주소로 연다. 모델을 부르는 관측은 검사가 아니다 — 승인 뒤에만 실행한다.
