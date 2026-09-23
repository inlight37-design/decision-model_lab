# 다음 세션 인계 — decision-model_lab

최종 갱신 **2026-09-24** · 작성 세션: claude (Claude Opus 5.5, 보조 PC의 로컬 checkout과 그 WSL) · 브랜치 `claude/k01-handoff-20260924`

이 파일 하나에서 시작한다. 절 구성은 고정이고 CI가 확인한다. 규칙은 [AGENTS.md](AGENTS.md)와 [협업 규칙](docs/COLLABORATION.md)에 있다. 1단계(실제 호출 전 확인)를 마치고 통째로 다시 쓴 판에 **2단계(승인된 모델 호출)의 결과를 더한 판**이다. 1단계 각 항목(N0–N6)의 경위와 긴 병합 이력은 [1단계 직후 판](docs/handoff/2026-09-23-before-stage2.md)과 Git 로그에 있다. 여기에는 지금 상태, 한계와 못 고친 문제(4절의 K 표), 다음 일만 둔다.

## 0. 먼저 확인할 것

1. `git fetch --all --prune` 후 GitHub의 열린 PR과 원격 브랜치를 본다. **아래 3절에 없는 PR이 있으면 이 문서가 낡은 것이다.** 실제 상태를 기준으로 한다. 이 PC의 GitHub CLI는 `C:\ai\tools\gh\bin\gh.exe`다(PATH에 없다, 6절). 로그인은 사용자가 한다 — `gh auth status`가 로그인 안 됨이면 열린 PR과 CI 결과를 익명 GitHub API로 본다(6절).
2. 지금 어느 기기인지 확인한다. 이 저장소를 편집해 온 기기는 **보조 PC `aux-pc`(Windows)**와 그 안의 **WSL2 배포판 `Ubuntu-24.04`(이름표 `aux-pc-wsl`)**다. 운용 PC는 관측한 세션이 없다.
3. 이 세션이 무엇에 접근할 수 있는지(사용자 PC / 웹 컨테이너 / GitHub만) 정하고 PR에 적는다.
4. **GitHub만 보는 세션**(ChatGPT 웹 등)이라면 main이 아직 이 파일의 최신판이 아닐 수 있다. 3절의 브랜치에서 이 파일을 다시 읽는다.
5. **모델을 부르는 일은 사용자 승인 뒤에만 한다.** 사용량이 막히면 멈추고 알린다(사용자 요청 — Codex 사용량이 적게 남아 있었다). 2단계 승인(Claude 3·Codex 2)은 모두 썼다 — 더 부르려면 새로 승인받는다.
6. **사용자에게 받을 것(3절):** Codex 문맥 판정(`failed`)을 푸는 방법, K46 방어를 adapter에 넣고 Codex 1회로 확인할지, PR #8(tmux 조사, 병합됨)의 TM 항목을 작업으로 받을지. 답을 받기 전에는 진행하지 않는다.

## 1. 지금 상태

**2단계(승인된 모델 호출)가 끝났다. 다음은 3단계 — A1 이어서(모의, 모델 호출 없음)다.** 실행 코어, bubblewrap 격리, 모의 모드 앱(controller와 화면), 실제 CLI 실행기, WSL 관측 도구, 실행 허가 계산이 있다. **WSL 격리 안에서 Claude 3회·Codex 2회를 실제로 불렀고 모두 도구의 기대대로였다**([2단계 기록](docs/experiments/w2-isolation/stage2-aux-pc-wsl.md)). 그 결과로 Claude는 실행 허가가 나오고, Codex는 문맥 판정이 `failed`라 허가가 없다. 화면 서버는 아직 모의 실행기만 쓴다. **합성은 없다.** 근거 원장은 E01–E31 / F01–F31, 결정은 D01–D18이다. 검사 수와 결과는 [CI 실행 기록](https://github.com/inlight37-design/decision-model_lab/actions/workflows/checks.yml)이 기준이다.

### 있는 것

| 부품 | 하는 일 | 보장하지 않는 것 |
|---|---|---|
| [`core/runner.py`](core/runner.py) | CLI 한 번을 셸 없이 실행한다. 입력을 다 보냈는지(`input_delivery`), 추적 단위가 비었는지(`unit_confirmed_empty`), 자손 전체가 끝났는지(`tree_confirmed_empty`)를 따로 남긴다. 정리 대기에 상한이 있다. 지정한 표식은 보관 상한과 상관없이 stderr 전체에서 센다(`stderr_counts`) | 격리 없는 POSIX에서 자손 전체의 종료(K03). 벽시계 보장(K05) |
| [`core/adapters.py`](core/adapters.py) | 읽기 전용 논의자의 실행 명세(`build_spec`, 질문은 stdin), 위험 플래그 거절, 출력 판정(`interpret`). 기록은 `ExecutionSpec.record()`만 | 권한 제한이 실제로 지켜지는지 — 관측(B)이 한다 |
| [`core/env.py`](core/env.py) | 자식 환경(과금 변수 제거), 실행 파일 찾기. WSL에서 Windows 실행 파일 거절 | interop 차단의 증명(K16) |
| [`core/isolation.py`](core/isolation.py) | 참여자 한 번을 bubblewrap으로 가둔다. 진입점 `isolation.run()` 하나. 허용한 폴더만, HOME·`/tmp`는 빈 tmpfs, PID namespace, 경로 충돌·비밀 변수 거절, root 소유 bwrap 확인 | 네트워크 격리(K08), 자원 상한(K10) |
| [`core/membership.py`](core/membership.py) | 참여자가 빠지거나 바뀔 때의 결정. 공개 전에는 구성이 바뀔 때마다 정족수를 다시 본다 | 초안이 다 들어왔는지 — controller 관문이 본다 |
| [`core/eligibility.py`](core/eligibility.py) | 실행 허가를 시도마다 계산한다: 기록의 다섯 칸이 모두 관측됐고, 30일 안이고, 설치 버전이 같고, 구독 로그인일 때만 | 기록된 관측이 사실인지 |
| [`app/`](app/README.md) | **A1 controller와 모의 화면.** 입력 고정 → 시도 예약 → 실행 → 결과 수용 관문 → 초안 봉인 → controller가 공개. 참여자는 CLI(지금은 모의 CLI)와 원본 앱(수동). 수동 질문에는 실행 표식을 달아 다른 카드에 붙여 넣은 답을 거절한다. 정족수 정책은 실행마다 고정한다(기본은 CLI만 센다, Q6). SQLite journal(스키마 버전, 한 번에 한 controller만 연다), 토큰으로 막은 127.0.0.1 화면 서버 | 실제 CLI로 돌린 적 없음(K17), 합성(K18). 수동 답의 입력 일치(K21) |
| [`app/cli_executor.py`](app/cli_executor.py) | 실제 CLI 실행기(Linux·WSL): `env.resolve` → `build_spec` → `isolation.run` → `interpret`. 이 기기의 기록(`runtime-inventory/2`)으로 시도마다 실행 허가를 계산하고, 허가가 없으면 프로세스를 만들기 전에 `failed_to_start`로 끝낸다 | 실제 CLI는 관측 도구가 이 실행기의 `prepare()` 경로로 불렀다(2단계). `execute()` 자체와 서버 연결은 아직이다(K17) |
| [`tools/w2/cli_boundary.py`](tools/w2/cli_boundary.py), [`auth_mounts.py`](tools/w2/auth_mounts.py), [`codex_sandbox.py`](tools/w2/codex_sandbox.py) | 설치된 Claude·Codex를 격리 안에서 `--version`·로그인 상태만 실행해 본다. `auth_mounts`는 인증·설정 연결 조합을 바꿔 가며 본다(N3, K09). `codex_sandbox`는 Codex 자체 샌드박스가 우리 경계 안에서 서는지 본다(K12). 모두 모델 호출 없음 | 실제 질의. 토큰 갱신 쓰기 — 모델을 불러야 드러난다 |
| [`tools/w2/observe.py`](tools/w2/observe.py) | **관측 호출은 이 도구로만 한다.** 참여자와 같은 argv·격리 경계로 probe마다 한 번 부르고, 승인한 provider별 상한과 멈춤 규칙을 지킨다. 요약은 파일 이름·stderr 속 UUID와 긴 ID를 가린다. **모델 호출** | 승인 없이 부르지 않는다. 2단계에서 다섯 번 불렀다 |
| [`tools/v04-03/conformance.py`](tools/v04-03/conformance.py) | Windows에서 논의자 설정을 관측하는 스크립트. 일부 명령은 모델을 부른다 | WSL에서는 쓰지 않는다 — `tools/w2/observe.py`가 맡는다 |
| [`tools/runtime_inventory.py`](tools/runtime_inventory.py) | V04-01 tier 1. 각 CLI의 `--version`/`--help`만 실행해 기록한다. `--validate`는 기록의 스키마(`runtime-inventory/2` 포함)를 검사한다 | `observed`·`configured=true`를 쓸 수 없다 |
| [`check_frontier_protocol.py`](tools/check_frontier_protocol.py), [`review_boundary.py`](tools/review_boundary.py), [`audit_design_contrast.py`](tools/audit_design_contrast.py) | 합성 기록의 일관성 **검사**(계산 아님), PR #3의 순수 함수 경계 실험, 디자인 토큰 대비 계산 | controller의 상태 권위가 아니다 |
| [`design/`](design/README.md) | 디자인 시스템 `Ledger`. [발행본 아티팩트](https://claude.ai/artifact/8tq8q5P8Pj7bpUtCF77FZA)와 맞춰 둔다 | 알려진 대비 미달 조합(K24) |

### 기기와 관측

- **`aux-pc`(Windows):** V04-01([결과](docs/experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md))과 V04-03 첫 conformance([기록](docs/experiments/v04-03-conformance/aux-pc.md))가 끝났다.
  - 설치: Claude Code 2.1.280, Codex 0.155.1, agy 1.2.8.
  - 로그인: Claude는 claude.ai 구독(`firstParty`), Codex는 ChatGPT, agy는 Google 계정이다. Claude CLI는 데스크톱 앱과 한도를 공유한다(E04).
  - GitHub CLI: `gh` 2.101.0을 공식 릴리스 zip(체크섬 확인)으로 `C:\ai\tools\gh\`에 풀었다(2026-09-24, 사용자 승인). 관리자 권한·PATH 변경 없이 전체 경로로 부른다. 로그인(`gh auth login`)은 사용자가 한다.
  - **Windows에만 해당하는 사실:** Codex의 `--ignore-user-config`가 샌드박스 선택까지 버린다(openai/codex#42172). Codex가 명령을 PowerShell 5.1로 실행한다. 작업 폴더 밖의 다른 참여자 초안도 읽는다. Claude 데스크톱 앱 셸에는 앱이 넣은 변수가 있어 새 터미널 기준 환경으로 실행한다. `%LOCALAPPDATA%` 설치가 앱의 가상 공간에 들어간 적이 있다(agy).
- **`aux-pc-wsl`(WSL2):**
  - 기록: [V04-01 tier 1](docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/RESULTS.md), [W2 경계 시험](docs/experiments/w2-isolation/aux-pc-wsl.md), [인증 연결 관측(N3)](docs/experiments/w2-isolation/auth-mounts-aux-pc-wsl.md), [2단계 호출(tier 2, B1·B2, K12 진단)](docs/experiments/w2-isolation/stage2-aux-pc-wsl.md), [2단계 후속(K46, 모델 없음)](docs/experiments/w2-isolation/stage2-followup-aux-pc-wsl.md), [K01 큰 입력](docs/experiments/w2-isolation/k01-large-input-aux-pc-wsl.md).
  - 환경: WSL 2.7.14, Ubuntu 24.04.5, systemd 켜짐, bubblewrap 0.9.0, AppArmor 꺼짐. 저장소는 Windows checkout(`C:\ai\decision-model_lab`)을 `/mnt/c/ai/decision-model_lab`로 열어 쓴다.
  - 설치: Claude Code 2.1.280과 Codex 0.156.1을 `~/.local/bin`에 설치했다. 로그인도 했다(Claude `claude.ai`·`firstParty`, Codex ChatGPT).
  - **로그인 셸(`bash -l`)에서 돌린다.** 비로그인 셸(`wsl.exe -- bash`)은 PATH에 `~/.local/bin`이 없어 CLI를 못 찾는다. PATH에 Windows 쪽 CLI 폴더가 이어 붙어 있다. Codex는 Linux 샌드박스용 bubblewrap을 스스로 들고 온다.
  - 격리 안 로그인 상태에는 인증 파일 하나면 된다(Claude `~/.claude/.credentials.json`, Codex `~/.codex/auth.json`) — 읽기 전용으로도 된다. 그래도 연결을 아직 좁히지 않았다(K09).
  - [`runtime-inventory/2` 기록](docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.v2.json): 2단계로 나머지 세 칸(전송·문맥 준수·권한 준수)을 채웠다. **Claude는 다섯 칸이 모두 `observed`라 실행 허가가 나온다**(30일 안, 같은 버전일 때). **Codex는 문맥 준수가 `failed`라 허가가 없다** — 작업 폴더의 `AGENTS.md`를 싣는다(K38·K44).
  - **2단계 결과(2026-09-23, Claude `claude-sonnet-5` 3회, Codex `gpt-6-luna` 2회):**
    - 다섯 번 모두 자손 전체 종료가 확인됐고 입력은 끝까지 전달됐다.
    - Claude `-p`는 stdin만으로 질문을 받는다. 금지 파일 읽기는 `--restricted`가 CLI 층에서 거절했다.
    - Codex는 금지 파일에 명령을 실제로 돌렸고 우리 경계가 막았다(파일 없음). Codex 자체 샌드박스는 우리 bubblewrap 안에서도 서서 쓰기를 막는다(모델 없는 진단).
    - Claude stream-json에는 계정 한도(`rate_limit_event`: 5시간·7일 창의 사용 비율)가 온다. 참여자 argv의 `json` 결과에는 없다.
    - Codex는 `--ignore-user-config`로도 계정의 원격 플러그인과 공급자 스킬을 `~/.codex`에 받는다.
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
| 검토 기록과 반영(읽는 순서 포함) | [docs/reviews/](docs/reviews/README.md) — 최근: [A1 리뷰 반영](docs/reviews/2026-09-23-a1-handoff-review/RESPONSE.md), [경계 리뷰](docs/reviews/2026-09-23-wsl2-boundary/RESPONSE.md), [WSL2 리뷰 PR #6](docs/reviews/2026-09-23-wsl2-migration-review/RESPONSE.md) |
| 실험·관측 기록 | `docs/experiments/` — [V04-01 절차서](docs/experiments/v04-01-inventory/README.md), [V04-03 conformance](docs/experiments/v04-03-conformance/aux-pc.md), [W2 격리](docs/experiments/w2-isolation/aux-pc-wsl.md) |
| 조사 | [Hermes 패턴 조사](docs/research/hermes-2026-09-23/README.md)와 [교차 확인](docs/research/hermes-2026-09-23/CROSSCHECK.md). [tmux 조사](docs/research/tmux-2026-09-23/README.md)(ChatGPT, [PR #8](https://github.com/inlight37-design/decision-model_lab/pull/8)) — tmux를 참여자 실행 엔진으로 쓰지 않고 개념(TM-01–TM-09)만 옮기라는 권고다. claude 세션이 코드 주장을 main `f044865`와 대조했다: 화면이 1초마다 조회하며 늦게 온 응답이 새 상태를 덮을 수 있다(P05) — 맞다. 새로고침·재접속은 조회만 하고 호출을 만들지 않는다(TM-01) — 이미 성립. 관측 도구가 실행기를 재사용한다(TM-02) — `prepare()`만 재사용해 부분적으로 맞다 |
| 작업 개념도 | [docs/concept/](docs/concept/README.md), [아티팩트](https://claude.ai/artifact/AZJfdnmMBjpEAtqsSHzjp8)(2026-09-22 스냅숏) |
| 지난 인계 | [docs/handoff/](docs/handoff/README.md) — 1단계 N0–N6의 경위는 [바로 전 판](docs/handoff/2026-09-23-before-stage2.md) 4절 |

### 열린 결정

| ID | 질문 | 상태 |
|---|---|---|
| Q3 | 언어/런타임 | Python 코어, TypeScript는 화면 경계만. **지금 화면은 빌드 없는 HTML·JS다** — 이 PC에 node가 없다(K25). TypeScript로 옮길 시점은 미정 |
| Q4 | 첫 화면 | `unresolved`. 결정 우선과 대조표 우선을 같은 내용으로 비교한 뒤 정한다. 합성이 생긴 뒤(4절 3단계) 모의 화면에서 비교한다 |
| Q5 | 원본 앱을 자동으로 움직일지 | **지금은 하지 않는다**(2절 19). 사람이 옮기는 수동 방식만 있다(2절 17). 소비자 앱의 화면을 프로그램으로 조작하면 깨지기 쉽고 약관상 계정 위험이 있다. 자동화가 필요해지면 공식 통로를 관측한 뒤 다시 정한다 |
| Q6 | blind를 확인할 수 없는 수동 참여자를 독립 정족수에 셀지 | **정했고 반영했다**(2절 18) — 정책을 실행마다 고정하고 기본은 독립성이 확인된 참여자(CLI)만 센다 |
| C2 | agy 자동 실행을 켤지 | **꺼 둔다**(2절 19). 켤지는 언제든 사용자가 고른다(2절 14). 위험은 기술 실패가 아니라 계정 제재다(F31) |
| C3 | Codex 문맥 판정(`failed`, K38·K44)을 어떻게 풀지 | 미정. (a) 참여자 구성(빈 작업 폴더)에서 문맥을 보이는 관측을 한 번 더 한다, (b) 빈 작업 폴더 완화를 정책으로 받아들인다. 정하기 전에는 Codex를 실제 실행기로 부르지 않는다(3절). 어느 쪽이든 Codex를 실제로 부르기 전에 K46(인증 파일 읽힘)의 방어가 먼저다 |

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

**지금 병합되지 않은 브랜치: 없음.** 마지막 병합: K01 관측과 인계 정리(`claude/k01-handoff-20260924`, gh로 만든 PR) — 큰 stdin 질문의 Claude 호출 1회([기록](docs/experiments/w2-isolation/k01-large-input-aux-pc-wsl.md))와 다음 세션을 위한 이 파일의 정리. 이 줄은 병합 뒤에 맞도록 브랜치에서 미리 "없음"으로 적었다. 그 앞: [PR #9](https://github.com/inlight37-design/decision-model_lab/pull/9) 2단계 후속(`claude/stage2-followup-20260924`) — Codex 명령이 자기 인증 파일을 읽을 수 있다는 모델 없는 진단(K46)과 권한 profile 시험, GitHub CLI 설치 기록. claude 세션이 gh로 연 첫 PR이고, 사용자 지시로 병합했다. 그 앞: [PR #8](https://github.com/inlight37-design/decision-model_lab/pull/8) `chatgpt/tmux-patterns-20260923` — ChatGPT의 tmux 조사(문서만, head `4e3500e`에서 CI 녹색). 사용자 지시로 claude 세션이 병합했다(2026-09-24). PR이 고친 옛 3절은 버리고 main 쪽을 두었으며, 조사 링크와 claude 세션의 대조는 1절 기록 표의 조사 줄로 옮겼다. 그 앞: 2단계(`claude/stage2-observe-20260923`) — 승인된 호출 다섯 번의 결과 기록, `manifest.v2.json`의 세 칸, 관측 도구의 수정(ID 가림, 경계 위반 멈춤), K12 진단 도구, 다른 AI에게 줄 [2단계 리뷰 요청서](docs/reviews/2026-09-23-stage2-request/README.md)(실패·시행착오 S01–S21). 이 세션의 권한 확인이 처음에는 main 병합을 막았고, 사용자 지시 뒤에 병합했다. 새 작업을 시작하면 여기에 브랜치를 적고, 병합하는 커밋에서 이 줄을 다시 "없음"으로 돌린다. `git fetch`/열린 PR 결과와 다르면 GitHub가 맞다. 그 앞의 병합 이력은 [1단계 직후 판](docs/handoff/2026-09-23-before-stage2.md) 3절과 Git 로그에 있다.

사용자의 판단을 기다리는 것:
- **PR #8의 TM 항목을 작업으로 받을지.** 병합은 조사 문서를 main에 둔 것이고 작업을 받은 것은 아니다. claude 세션의 권고는 적용 계획 A(화면 조회의 요청 겹침 막기, 늦게 온 응답 버리기, 연결 끊김과 마지막 확인 시각 표시)만 3단계 화면 작업에 넣는 것이다. tmux를 참여자 실행 엔진으로 쓰지 않는다는 판단은 조사와 claude 세션이 같다 — bubblewrap 안의 참여자가 밖의 tmux server에 일을 맡기면 격리와 자손 종료 확인이 깨진다.
- **Codex 문맥 판정(`failed`)을 푸는 방법** — (a) 참여자 구성(빈 작업 폴더)에서 한 번 더 관측해 문맥에 무엇이 들어가는지 본다(Codex 1회 승인), 또는 (b) 빈 작업 폴더 완화를 정책으로 받아들이고 계정 플러그인(K44)은 한계로 둔다. 정하기 전에는 Codex를 실제 실행기로 부르지 않는다.
- **K46 방어를 넣을지** — Codex 참여자의 명령이 `~/.codex/auth.json`을 읽을 수 있다(모델 없는 진단). 인증 파일만 읽기 금지하는 권한 profile이 `codex sandbox`에서는 통했다. adapter에 넣으려면 허용 목록을 넓히고 Codex exec 1회로 확인해야 한다(승인 필요). K09의 하위 폴더 덮기보다 먼저 한다(4절 2단계 "남은 것").
- 열린 결정 Q3·Q4 — 급하지 않다. Q5·Q6·C2는 정했다(2절 18·19).
- aux-pc 로컬 모의 데이터(`~/.decision-model-lab/mock`)의 첫 실행 하나가 ChatGPT 앱 수동 답을 기다린다 — 시연용이고 저장소와 무관하다. 새 코드로 처음 열면 journal이 스키마 2로 올라가고, 그 실행은 예전처럼 원본 앱 답도 정족수에 센다(`include_unverified`).

## 4. 다음 작업

원칙: **또 하나의 큰 설계 문서를 만들지 않는다.** 작은 실행 계약, 회귀 시험, 모의 controller, 한 번씩 읽는 실제 관측 순으로 증거를 쌓는다. 순서는 [WSL2 리뷰](docs/reviews/2026-09-23-wsl2-migration-review/README.md)의 권고(질문 9)를 따른다. exec 우선과 V04-03 순서는 바꾸지 않는다.

| 단계 | 할 일 | 모델 호출 | 선행 |
|---|---|---|---|
| 1 | 실제 호출 전 확인(N0–N6) — **끝남** | 없음 | 없음 |
| 2 | 승인된 소수 호출: `aux-pc-wsl` tier 2와 B1·B2 — **끝남**(Claude 3회·Codex 2회, 남은 것은 아래) | 승인한 상한만 | 1, 승인 |
| 3 | **A1 이어서(다음 일):** 합성과 주장 대조, 결정 카드, Q4 비교, 사용량 두 층 표시, 취소 | 없음(모의) | 2의 결과 |
| 4 | **B3 V04-03 pilot과 사용량 비교** | 여러 번 | 3, 승인, Codex 문맥 판정(3절) |
| — | B4 agy 관측 | 몇 회 | 사용자가 agy를 켤 때 |

**다음 세션의 첫 일 — 둘 중 무엇을 먼저 할지 사용자에게 확인한다.**

1. **K46 방어(Codex를 실제로 부르기 전에 필요).**
   - 모델 없이 할 것:
     - `core/adapters.py`의 Codex 명세가 Linux에서 `--sandbox read-only` 대신 권한 profile을 넘긴다: `-c permissions.<이름>={ extends = ":read-only", filesystem = { "<HOME>/.codex/auth.json" = "deny" } }`와 `-P <이름>`. HOME은 실행기가 안다.
     - 금지 목록(`-c`)의 예외를 그 값 하나로 좁혀 둔다.
     - `observe.py`의 `p3-codex`는 지금 `--sandbox` 값을 바꾸므로 함께 고친다.
     - 가짜 CLI 시험을 붙인다. 원 출력을 읽을 때 토큰 모양(JWT·긴 base64)도 가리도록 `_scrub`을 넓힌다.
   - 그다음 사용자 승인을 받아 Codex exec 1회로 본다: 로그인이 유지되는지, 모델이 돌린 명령이 `auth.json`을 못 읽는지(내용이 아니라 종료 코드만 찍게 한다), 쓰기가 막히는지.
   - 열린 결정 C3의 (a)(참여자 구성에서 문맥 확인)를 같은 호출에 붙일 수 있는지도 함께 설계한다.
2. **3단계 A1 이어서(모의, 모델 호출 없음)** — 아래 "3단계 이후"의 목록.

### 1단계 — 끝남

A1 리뷰가 먼저 하라고 한 관문 보강(N0, [반영 기록](docs/reviews/2026-09-23-a1-handoff-review/RESPONSE.md))과 N1–N6을 마쳤다. 항목별 경위는 [1단계 직후 판](docs/handoff/2026-09-23-before-stage2.md) 4절에 있고, 남은 한계는 아래 K 표로 옮겼다. N1 실제 실행기는 아직 서버에 연결하지 않았다 — 서버에서 실제 CLI를 고르는 설정(참여자별 전체 모델 이름)은 3단계 이후에 붙인다(K17).

### 2단계 — 끝남

2026-09-23 사용자 승인(Claude 최대 3·Codex 최대 2, 실패 포함, 호출당 300초, 기대와 다르면 그 provider 멈춤, 한도 메시지면 모두 멈춤)으로 `b1`·`b2`·`p3-claude`·`p3-codex`·`b1-combo`를 한 번씩 불렀다. 모델은 Claude `claude-sonnet-5`(세션이 고름), Codex `gpt-6-luna`(사용자가 정함). 다섯 번 모두 도구의 기대대로였고 한도 메시지는 없었다. 결과와 판정은 [2단계 기록](docs/experiments/w2-isolation/stage2-aux-pc-wsl.md)과 [`manifest.v2.json`](docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.v2.json)에 있다. 이 승인은 다 썼다.

**남은 것 — 하려면 새 승인이 필요하다:**

- ~~K01 큰 입력~~ — **했다(2026-09-24, Claude 1회).** 2단계에서 `--pad-kb`를 빠뜨린 것을 메웠다. 약 95 KB의 stdin 질문이 끝까지 전달됐고 보고 토큰이 입력만큼 늘었다([기록](docs/experiments/w2-isolation/k01-large-input-aux-pc-wsl.md)). 처음 "3번은 알아서 해도 돼"로는 이 세션의 권한 확인이 승인 기록을 막았고, 세션이 명시적 승인을 요청한 뒤의 답("병합하고 할거하고 정리해")으로 1회를 적어 불렀다.
- **Codex 문맥 판정(`failed`).** 참여자 구성(빈 작업 폴더)에서 무엇이 문맥에 들어가는지 볼 probe가 아직 없다. `plain-codex`는 빈 폴더지만 문맥 내용을 보이지 않는다. 후보는 `--ephemeral` 없이 한 번 돌려 Codex가 남기는 세션 기록에서 지시문·도구 목록을 읽는 것이다 — probe를 새로 만들고 승인받는다. 또는 사용자가 빈 폴더 완화를 정책으로 받아들인다(3절).
- **K46 인증 파일 읽기 금지(K09보다 먼저).** 2026-09-24 모델 없는 진단([후속 기록](docs/experiments/w2-isolation/stage2-followup-aux-pc-wsl.md)): Codex 참여자의 명령은 `~/.codex/auth.json`을 읽을 수 있고, 명령의 네트워크는 막혀 있다. `:read-only`를 넓혀 `~/.codex/auth.json`만 금지하는 권한 profile은 `codex sandbox`에서 그 파일만 막고 나머지를 그대로 두었다. `~/.codex` 전체를 금지하면 샌드박스가 codex 실행 파일을 다시 실행하지 못해 돌지 않는다. 넣는 방법: adapter가 `--sandbox read-only` 대신 그 profile(`-c permissions.…`, `-P`)을 넘기도록 허용 목록을 넓히고, Codex exec 1회로 로그인·명령의 인증 파일 읽기 차단·쓰기 차단을 본다.
- **K09 연결 좁히기(K46 뒤).** Claude는 `.credentials.json`·`~/.claude.json`·쓸 곳(`backups`·`cache`)만 쓰기로 두고 나머지를 빈 tmpfs로 덮는 구성이 후보다. Codex는 상태 DB·플러그인 캐시를 모든 실행이 공유한다. 하위 폴더 덮기는 인증 파일 노출을 줄이지 못하고, 토큰 갱신이 한 번도 없어 좁힌 구성에서 갱신이 저장되는지 볼 수 없었다 — 그래서 K46 뒤로 미뤘다. 바꾼 구성으로 한 번씩 다시 불러야 기록의 관측과 맞는다.

**다시 부를 때의 절차** — `aux-pc-wsl`의 로그인 셸에서, 저장소 루트(`/mnt/c/ai/decision-model_lab`)에서:

1. `python3 tools/w2/observe.py plan` — 모델 호출 없음. probe마다 실제로 돌릴 argv, 연결 경로, 승인 상태를 본다. "not on the child PATH"면 로그인 셸이 아니다.
2. `python3 tools/w2/observe.py approve --claude <n> --codex <n> --timeout <초> --note "<누가·언제·어디서 승인>"` — **사용자가 새로 정한 값 그대로.** 모델 이름은 전체 이름으로 받는다(K43). 호출 전에 관측할 목록과 명령의 옵션(`--pad-kb` 등)을 맞춰 본다.
3. `python3 tools/w2/observe.py call <probe> <전체 모델 이름>` — 한 번 부르고 출력 JSON(`as_expected`, `boundary_violations`, `argv_run`, init 요약, `config_changes`, stderr 힌트, 토큰)을 읽는다. 도구의 `as_expected`는 답을 받았는지와 경계 위반(금지 표식이 답·출력에 보임, 작업 폴더에 파일이 생김)까지 본다 — 지시문 표식, 도구 시도, 거절 방식은 답과 원 출력에서 직접 본다. 종료 코드 3은 기대와 다르다는 뜻이다 — 그 provider는 멈춘다. 종료 코드 2는 부르지 않았다는 뜻이다(사용량을 쓰지 않았다). `p3-*`는 모델 응답 없이 거절돼야 하는 호출이지만 상한에는 센다.
4. `python3 tools/w2/observe.py status`로 남은 상한을 본다.

- 원 출력은 WSL 안 `~/.local/state/dml-observe/`(저장소 밖, 격리 안에 연결하지 않음)에 남는다. 저장소에는 요약만 옮기고, 계정 이메일·조직 ID·토큰은 옮기지 않는다. **요약도 옮기기 전에 읽는다** — 2단계에서 CLI가 쓴 파일 이름에 조직 UUID가 들어 있었다(지금은 도구가 가린다).
- Windows 쪽 세션이 부를 때는 명령을 스크립트 파일로 만들어 `wsl.exe -d Ubuntu-24.04 -- bash -l <스크립트의 /mnt/c 경로>`로 넘긴다(아래 참고의 인자 깨짐). 스크립트는 저장소의 무시 폴더(`raw-traces/`)나 AppData 밖에 둔다.

### 3단계 이후

- **A1 이어서(다음 일, 모델 호출 없음).** 순서는 사용자에게 확인하고 시작한다.
  - 합성자와 합성 없는 보고(`report_without_synthesis`)
  - [결정 카드](design/project/components/DecisionCard/README.md)
  - 첫 화면 Q4 비교
  - 사용량 두 층 표시(2절 4, K23). Claude는 호출하는 김에 stream-json의 `rate_limit_event`로 계정 한도 비율을 준다(2단계 관측, 추가 호출 없음). 참여자 argv를 `json`에서 stream-json으로 바꿀지 정해야 한다
  - 취소(K19)
  - 공통 자료 첨부(옛 A6)
  - 결과 폴더 감시(옛 A2)
  - 사용자가 PR #8의 TM 항목을 받으면: 화면 조회의 요청 겹침 막기, 오래된 응답 버리기, 연결 끊김과 마지막 확인 시각 표시(적용 계획 A)
- **B3 pilot:** Claude와 Codex가 서로 모르게 읽기 전용 초안을 내고 합성한다. Codex가 실행 허가를 받아야 한다(3절 Codex 문맥 판정).
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
| K01 | 실행 코어 | "CLI가 입력 일부만 읽고 닫음"은 입력이 파이프 버퍼보다 클 때만 쓰는 쪽에서 드러난다. 파이프에 다 썼다는 것이 CLI가 다 읽었다는 증거도 아니다 — 2단계 `p3-*`에서 CLI가 stdin을 읽지 않고 끝났는데 22바이트가 버퍼에 들어가 `complete`였다 | `input_delivery`를 남기고, 완전하지 않으면 `input_error`. A1은 전달 기록이 없는 결과(`None`)도 받지 않는다. **Claude는 약 95 KB의 stdin 질문을 끝까지 읽었다** — 전달 완료와 함께 보고 토큰이 입력만큼 늘었다(2026-09-24, [기록](docs/experiments/w2-isolation/k01-large-input-aux-pc-wsl.md)) | Codex의 큰 입력(필요할 때). 러너가 CLI의 "다 읽음"을 증명하지 못한다는 한계 자체는 남는다 |
| K02 | 실행 코어 | Codex 명령 거절은 stderr의 문자열로만 안다. Linux Codex에서는 그런 문자열을 보지 못했다(K30) | runner가 보관 상한과 상관없이 stderr 전체에서 표식을 센다(`stderr_counts`, 실제 실행기가 요청). 셀 수 없었는데 stderr가 잘렸으면 답을 받지 않는다 | K30과 함께 |
| K03 | 실행 코어 | 격리 없는 POSIX 실행은 자손 전체의 종료를 확인하지 못한다 | `tree_confirmed_empty=None` → 앱은 `unknown`. Linux 참여자는 `isolation.run()`으로만 | — |
| K04 | 실행 코어 | 돌아온 뒤에도 파이프를 쥔 자손이 있으면 입출력 스레드·fd가 남는다(격리 없는 POSIX) | `runner.lingering()`으로 세고 정리 안 된 시도의 상한에 넣는다 | 격리 경로에서는 namespace가 정리한다 |
| K05 | 실행 코어 | `CLEANUP_LIMIT`는 명시적 대기의 상한이지 벽시계 보장이 아니다 | 문구를 한정했다 | — |
| K06 | 실행 코어 | Windows: job 배정 전에 생긴 자식은 추적하지 못한다. 끝낸 직후 프로세스 객체가 신호를 받기까지 짧은 틈이 있다 | 문서화, 시험이 기다린다 | Windows 경로는 동결(2절 15) |
| K07 | 실행 코어 | agy는 질문을 명령줄로 보낸다(stdin 미확인). 그래서 `RunResult.argv`에 질문이 들어 있다 | 기록은 `ExecutionSpec.record()`로 | B4 |
| K08 | 격리 | 네트워크를 공유한다. 참여자가 localhost 포트와 abstract unix 소켓에 닿고, 네트워크 서비스에 시켜 만든 작업은 종료 보장 밖이다 | 앱의 제어 API는 토큰으로 막았다 | 미정 |
| K09 | 격리 | `~/.claude`·`~/.codex` 전체를 쓰기로 연결한다. 그 배포판에서 대화형으로 쓴 그 CLI의 세션 기록과 `settings.json`, 그리고 앞선 참여자 실행이 남긴 상태(Codex의 상태 DB·계정 플러그인 캐시, Claude의 `.claude.json` 백업)가 참여자에게 보인다 | 로그인 상태에는 인증 파일 하나면 됨을 봤다(N3). 2단계에서 CLI가 실제로 쓰는 곳을 봤다 — Claude는 `~/.claude.json`·`backups`·`cache`, Codex는 상태 DB·캐시·플러그인·스킬. 토큰 갱신은 일어나지 않았다 | K46 뒤에 좁힌 구성과 그 구성의 재관측(승인 필요, 4절 2단계 "남은 것") |
| K10 | 격리 | 메모리·CPU 상한이 없다 | — | 미정 |
| K11 | 격리 | `/etc` 전체와 `/usr`가 읽기 전용으로 보인다. 설정과 민감한 값이 있을 수 있는 호스트 경로다 | 신뢰 범위로 둔다. `never`는 이 자동 연결과도 비교해 겹치면 거절한다(A1 리뷰 A1-04) | — |
| K13 | 격리 | `aux-pc-wsl`은 AppArmor가 꺼져 있고, CI는 user namespace 제한을 sysctl로 푼다. 제한이 켜진 일반 Ubuntu에서의 운영은 보지 않았다 | — | 새 기기에서 확인 |
| K14 | 격리 | 경로 검사와 마운트 사이에 파일이 바뀌는 경쟁 | 문서화 | — |
| K15 | 격리 | bwrap 신뢰는 root 소유 `/usr/bin/bwrap` 확인이다. 같은 Python 프로세스 안의 코드가 내부 함수를 부르는 것은 막지 못한다 | 문서화 | — |
| K16 | CLI·환경 | WSL의 Windows 실행 파일 가드는 경로·링크·`MZ` 내용으로 판정하는 경험칙이다. 사용자가 바꾼 automount root는 PATH 필터가 모른다 | 격리가 `/mnt`·`/init`·`/run`을 연결하지 않는 것이 실제 차단이다 | — |
| K17 | 앱 | 서버는 아직 모의 실행기만 쓴다. 실제 CLI는 관측 도구가 실행기의 `prepare()` 경로로 부른 것뿐이고, `execute()`와 controller를 거친 실제 호출은 없다 | 실제 격리 경로·수용 관문·늦은 결과 시험(WSL, CI). 기록(`runtime-inventory/2`)이 허가하지 않으면 시작 전에 거절한다 — 지금 Codex는 거절된다 | 3단계 이후(서버의 실제 CLI 설정), B3 |
| K18 | 앱 | 합성, 주장 대조, 결정 카드, Q4 비교가 없다. 초안 공개까지만 있다 | — | 3단계 |
| K19 | 앱 | 취소가 없고, 취소 중 입력 전송 시험도 없다. 서버를 끄는 것이 지금 유일한 멈춤 수단이다 | 다시 시작한 뒤 대기 시도는 사용자가 "이어서 시작"을 눌러야 시작한다. 멈춘 상태는 메모리에만 있다 | 3단계 |
| K20 | 앱 | 원장 잠금은 한 기기 안의 파일 잠금이다. 기기 여러 대가 한 원장을 나눠 쓰는 것은 지원하지 않는다. 사건 순서는 실행별 순번뿐이다 | 한 원장은 한 controller만 연다. 시작과 결과 반영은 기대한 상태·시도 ID가 맞을 때만 하고, 늦은 결과는 사건으로만 남긴다(A1 리뷰 A1-03) | — |
| K21 | 앱 | 원본 앱에 정말 이 질문을 넣었는지는 확인하지 못한다. 실행 표식은 모델이 되말해야 드러나고, 되말하지 않은 답(`marker_echo: missing`)도 받는다 | 다른 실행·다른 참여자의 표식이 달린 답은 거절한다. 사용자 확인은 따로 기록한다(N5) | — |
| K22 | 앱 | 원본 앱 참여자의 독립성은 확인할 수 없다 | 정족수 정책을 실행마다 고정한다. 기본(`independent_only`)은 세지 않고 보조 근거로 공개하고, `include_unverified`는 세되 "독립 정족수 충족"이라고 쓰지 않는다(Q6, N5) | — |
| K23 | 앱 | 구독 사용량 두 층 표시(2절 4)가 없다. 예산은 실행별로 CLI 참여자당 한 번이고, 실행 간 누적 예산이 없다 | Claude의 계정 한도 비율은 stream-json의 `rate_limit_event`로 온다(2단계). 참여자 argv의 `json` 결과에는 없다 | 3단계, B3 |
| K24 | 디자인 | 토큰 5쌍이 일반 글자 대비(4.5:1)에 못 미친다(`unknown`은 세 면 모두, `ink-200`은 `surface-200` 위) | 화면은 그 조합을 글자에 쓰지 않는다 — 시험이 지킨다(N6) | 급하지 않음(토큰 수정은 아티팩트와 함께) |
| K25 | 앱 | 화면이 TypeScript가 아니라 빌드 없는 HTML·JS다(node 없음) | — | Q3 |
| K26 | 앱 | 제어 API 토큰은 controller 데이터 폴더의 파일과 서버 출력에 있다. 격리 밖에서 같은 사용자로 도는 프로세스는 읽을 수 있다 — 신뢰 경계는 사용자 계정이다 | 격리 안에는 그 폴더를 연결하지 않는다(`never`). 토큰 파일은 처음부터 0600으로 만들어 통째로 바꾸고, 데이터 폴더는 0700이다(POSIX) | — |
| K27 | 앱 | claude 세션은 A1 화면을 눈으로 확인하지 못했다(브라우저 패널이 가려짐). 페이지 글자, API, CSS 대비 계산으로만 확인했다. N5·N6에서 바뀐 화면(정족수 정책 선택, 질문 복사, 사용자 확인, `UNKNOWN` 라벨)도 마찬가지다 | — | 브라우저 패널을 쓸 수 있는 세션이 스크린샷으로 보거나, 사람이 보고 알려 주면 닫힌다 |
| K28 | 앱 | journal 이전은 올리는 방향뿐이다. 되돌리는 절차는 없다 | 스키마 버전(`user_version`)을 두고, 예전 journal은 열 때 한 거래로 올린다. 새 버전 journal은 건드리지 않고 거절한다(A1 리뷰 반영) | — |
| K30 | CLI | Linux Codex가 실행 전 거절 문자열을 내는지 모른다. `tools_rejected`는 Windows 문자열을 찾는다. 2단계 `b2`의 stderr는 비었고, 모델은 쓰기를 시도하지 않았다. 중첩 샌드박스는 쓰기를 명령 안의 `Read-only file system`으로 막는다(모델 없는 진단) | 거절 문자열이 없어도 쓰기는 막힌다. 답의 수용은 `interpret` 판정대로 | 모델이 쓰기를 시도하는 관측이 필요해지면 |
| K31 | CLI | Claude가 `CLAUDE.md`를 싣지 않는다는 것은 모델의 보고뿐이다. 2.1.280의 stream-json init에는 불러온 지시문·메모리 파일 칸이 없어 init으로 확인할 수 없다(2단계) | 참여자 작업 폴더는 비어 있고 이 배포판에 `~/.claude/CLAUDE.md`가 없다. 두 조합 모두 모델 보고는 "없음" | 큰 표식 파일을 두고 보고 토큰의 차이를 보는 관측(승인 필요) |
| K32 | CLI | Codex·agy는 결과에 모델 이름이 없어서 조용한 강등을 결과로 잡지 못한다 | Codex의 모델 목록 캐시에 요청한 이름(`gpt-6-luna`)이 있는 것까지 봤다(2단계) | B4(agy init) |
| K34 | CLI | Windows 전용 사실(Codex #42172, PowerShell 5.1 재시도, 작업 폴더 밖 읽기) | adapter의 `codex_windows_sandbox`. Codex blind 참여는 WSL에서만 | Windows 경로는 동결 |
| K38 | CLI | Codex는 작업 폴더의 `AGENTS.md`를 싣는다 — `--ignore-user-config --ignore-rules`로도 막히지 않는다(WSL 2단계 `b2`에서도 같다). 그래서 기록의 Codex 문맥 판정이 `failed`다 | 참여자 작업 폴더는 controller가 시도마다 만든 빈 폴더다(지시문 파일 없음). 실제 실행기도 그 폴더에서 돈다 | 사용자 판단(3절) |
| K39 | CLI | Codex의 read-only 샌드박스는 쓰기만 막고 읽기는 막지 않는다 — 2단계 `b2`에서 Codex가 다른 참여자 초안에 명령을 실제로 돌렸다 | 읽기 경계는 bubblewrap 허용 목록이 맡는다 — 그 초안은 연결되지 않아 `No such file`이었다(2단계). 격리 밖에서 Codex를 돌리면 이 경계가 없다 | — |
| K40 | CLI | agy는 `--output-format`의 없는 값을 조용히 무시한다 | adapter가 값을 고정하고, JSON이 아니면 형식 실패 | — |
| K35 | 과정 | 모든 관측은 PC 한 대와 그 안의 WSL 배포판 하나, 2026-09-23 하루치다. 운용 PC 관측이 없다 | — | 필요할 때 같은 절차서로 |
| K41 | 앱 | 공개 전에도 참여자 상태가 바뀌는 시각을 반복 조회로 대략 알 수 있다. 정확한 시간·토큰·길이는 넘기지 않는다 | 운영자용 거친 상태로 허용한다. 참여자에게는 제어 API 토큰이 없다(A1 리뷰 질문 4) | — |
| K42 | 앱 | 제어 API의 방어는 Bearer 토큰, Host 검사, 요청 크기 상한뿐이다. Origin 허용 목록, 콘텐츠 타입 강제, 프레임 삽입 정책, 읽기 시간 제한, 브라우저 교차 출처 음성 시험이 없다 | 토큰을 머리글로만 받으므로 교차 출처 요청은 preflight에서 막힌다고 본다 — 브라우저로는 시험하지 않았다(A1 리뷰 질문 5) | 급하지 않음 |
| K43 | 앱 | 보고된 모델이 요청과 다르면 받지 않고 구성 축소로 드러낸다. 받아들일지 사용자에게 묻는 보류 상태는 없다. 별칭으로 요청하면 보고된 전체 이름과 달라 보일 수 있다 | 요청은 전체 이름으로 한다(N1). 2단계에서 `claude-sonnet-5`로 요청해 init과 `modelUsage`가 같은 이름을 보고했다 | — |
| K44 | CLI | Codex는 `--ignore-user-config`로도 계정의 원격 플러그인(사용자가 만든 것 포함)과 공급자 스킬을 `~/.codex`에 받는다. 그것이 참여자 문맥에 들어가는지는 모른다 | 기록의 Codex 문맥 판정을 `failed`로 두어 실제 실행기가 Codex를 부르지 않는다 | Codex 문맥 판정(3절) |
| K45 | CLI | Claude `--safe-mode`를 더하면 init에 내장 플러그인 `agents-md`가 나타난다. 무엇을 하는지 모른다. 그때도 모델은 `AGENTS.md` 표식을 보고하지 않았다 | 참여자 argv는 `--restricted`만 쓴다 | `--safe-mode`를 쓰기로 할 때 |
| K46 | 격리 | Codex 참여자의 명령은 Codex의 로그인 파일 `~/.codex/auth.json`을 읽을 수 있다(2026-09-24, `codex sandbox` 진단 — 종료 코드만 봄). 모델이 그것을 답에 넣으면 ChatGPT 로그인 토큰이 원장과 공개 화면에 남는다. 공통 자료의 지시로 유도될 수 있다. 명령의 네트워크는 Codex 샌드박스가 막는다(`PermissionError`). Claude는 Read가 `--restricted`로 작업·입력 폴더에 갇히고 셸 도구가 없다 | 기록의 Codex 문맥 판정이 `failed`라 실제 실행기가 Codex를 부르지 않는다. `~/.codex/auth.json`만 읽기 금지하는 권한 profile이 `codex sandbox`에서 통했다(`~/.codex` 전체 금지는 샌드박스를 깨뜨린다) | adapter에 profile을 넣고 Codex exec 1회로 확인(승인 필요) — Codex를 실제로 부르기 전 |

2단계에서 닫은 것: K12(Codex 샌드박스가 우리 경계 안에서 선다 — 모델 없는 진단), K29(`-p`는 stdin을 질문으로 읽는다), K33(관측 도구가 실제 호출을 했다), K36(격리 안에서 실제 질의가 끝까지 돈다). 근거는 [2단계 기록](docs/experiments/w2-isolation/stage2-aux-pc-wsl.md)에 있다. 2026-09-24에 닫은 것: K37(사용자가 `gh`에 로그인한 뒤로 claude 세션이 `gh run view <번호> --log`로 CI 원문 로그를 읽는다 — PR #9의 실행에서 확인). 로그인이 풀리면 다시 익명 API로 결과만 본다.

### 급하지 않은 것

- 대비 미달 5쌍의 토큰 수정(K24). 화면은 이미 그 조합을 글자에 쓰지 않는다. 고칠 때는 `design/`과 아티팩트를 함께 고친다.
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
  - 선례: [A1 리뷰 반영](docs/reviews/2026-09-23-a1-handoff-review/RESPONSE.md), [WSL2 리뷰 반영](docs/reviews/2026-09-23-wsl2-migration-review/RESPONSE.md).
- **작업 한 건의 흐름(이 PC의 claude 세션):** main에서 `<agent>/<주제>-<YYYYMMDD>` 브랜치를 만들고 3절에 적는다 → Windows에서 전체 검사, WSL에서 `DML_REQUIRE_BWRAP=1` 전체 검사 → push → `gh pr create`로 PR을 연다(`gh`에 로그인돼 있을 때, 6절) → CI 녹색 확인(`gh pr checks` 또는 익명 API) → 병합 직전 커밋에서 3절을 "없음"으로 돌린다 → 병합(`gh pr merge --merge` 또는 로컬 `git merge --no-ff`) → main push. 병합은 2절 8의 허락 범위에서만 한다 — 2026-09-23에는 이 세션의 자동 권한 확인이 "검토 없는 병합"으로 막았고, 사용자가 지시한 뒤에 병합했다. `gh` 로그인 전에 만든 브랜치는 PR이 없다 — 3절과 브랜치 이름이 기록이다.
- **WSL을 Windows 쪽에서 부를 때:** PowerShell 5.1에서 `wsl.exe`로 넘기는 인자는 따옴표와 `$`가 깨진다. 명령을 스크립트 파일로 넘긴다. Git Bash는 `/mnt/c/...` 인자를 Windows 경로로 바꾼다 — `MSYS_NO_PATHCONV=1`을 붙인다. Git Bash의 명령줄 한글은 ANSI 코드페이지로 바뀐다 — 요청 본문은 파일이나 stdin으로 보낸다.
- **Windows 파이썬으로 저장소 파일을 쓸 때:** `write_text`는 줄 끝을 CRLF로 바꾼다. `write_bytes(text.encode("utf-8"))`나 편집 도구를 쓴다. 콘솔(cp949)로 한글·기호를 출력하면 깨지거나 예외가 난다 — `PYTHONIOENCODING=utf-8`이나 파일로 받는다.
- **다른 판을 따로 풀어 시험할 때:** 긴 경로(데스크톱 앱의 scratch 폴더)에서는 `git worktree`가 실패했다. `git archive <커밋> | tar -x -C <짧은 임시 폴더>`를 쓴다.
- **보조 스크립트와 함정:** [`tools/v04-01/`](tools/v04-01/README.md), [`tools/v04-03/`](tools/v04-03/README.md), [`tools/w2/`](tools/w2/README.md), V04-01 절차서의 "AI 세션이 Claude 데스크톱 앱 안에서 대신 실행할 때" 절.
- **Hermes에서 옮기면 안 되는 동작**(마감 뒤 답 텍스트를 완료로 수용, 다른 CLI 로그인 빌려 쓰기 기본값, 매 턴 추가 호출, `--fallback-model`)은 [교차 확인](docs/research/hermes-2026-09-23/CROSSCHECK.md)에 있다.

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
python tools/runtime_inventory.py --validate docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.v2.json
```

- `jsonschema`가 없으면 해당 검사는 skip된다. **skip은 통과가 아니다.**
- CI(Linux)는 bubblewrap을 설치하고 `DML_REQUIRE_BWRAP=1`로 격리 시험의 건너뛰기를 막는다.
- Windows 경로(job object)는 CI가 돌리지 않으므로 Windows에서 한 번 돌린다.

WSL(`aux-pc-wsl`)의 로그인 셸에서 저장소 루트(`/mnt/c/ai/decision-model_lab`)로 — 모두 모델 호출 없음:

```bash
DML_REQUIRE_BWRAP=1 python3 -m unittest discover -s tests
python3 tools/w2/cli_boundary.py
python3 tools/w2/codex_sandbox.py
python3 tools/w2/observe.py plan
```

Windows 쪽에서는 위 명령을 스크립트 파일에 넣고 `wsl.exe -d Ubuntu-24.04 -- bash -l /mnt/c/<스크립트 경로>`로 부른다. Git Bash에서 부를 때는 앞에 `MSYS_NO_PATHCONV=1`을 붙인다 — 붙이지 않으면 `/mnt/c/...`가 `C:/Program Files/Git/mnt/c/...`로 바뀐다.

PR과 CI — GitHub CLI는 `C:\ai\tools\gh\bin\gh.exe`(Git Bash에서는 `/c/ai/tools/gh/bin/gh.exe`)다. 로그인은 사용자가 자기 터미널에서 한 번 한다(`gh auth login --hostname github.com --git-protocol https --web`). 에이전트는 로그인하지 않는다.

```bash
/c/ai/tools/gh/bin/gh.exe auth status
/c/ai/tools/gh/bin/gh.exe pr create --base main --head <브랜치> --title "<제목>" --body-file <본문 파일>
/c/ai/tools/gh/bin/gh.exe pr checks <번호>
/c/ai/tools/gh/bin/gh.exe run view <실행 번호> --log
```

`gh`에 로그인하지 않았으면 CI 결과는 익명 GitHub API로 본다:

```bash
curl -s https://api.github.com/repos/inlight37-design/decision-model_lab/commits/<커밋 SHA>/check-runs | python -c "import json,sys; [print(r['name'], r['status'], r['conclusion']) for r in json.load(sys.stdin)['check_runs']]"
```

모의 화면은 `python -m app.server --port 8765`로 띄우고, 출력된 `#token=` 주소로 연다. 모델을 부르는 관측은 검사가 아니다 — 승인 뒤에만 실행한다.
