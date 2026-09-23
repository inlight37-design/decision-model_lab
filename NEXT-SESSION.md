# 다음 세션 인계 — decision-model_lab

최종 갱신 **2026-09-23** · 작성 세션: claude (Claude Opus 5.5, 보조 PC의 로컬 checkout) · 브랜치 `claude/review-request-20260923`

이 파일 하나에서 시작한다. 절 구성은 고정이고 CI가 확인한다. 규칙은 [AGENTS.md](AGENTS.md)와 [협업 규칙](docs/COLLABORATION.md)에 있다. 이 판은 2026-09-23 하루치 작업을 끝내며 남은 일을 다시 정리한 판에, 같은 날의 [경계 리뷰 반영](docs/reviews/2026-09-23-wsl2-boundary/RESPONSE.md)을 더한 것이다. **실행 기반을 WSL2로 옮기기로 했다**(2절 15·16). 통째로 다시 쓴 마지막 판은 [docs/handoff/](docs/handoff/README.md)에 보관했다.

## 0. 먼저 확인할 것

1. `git fetch --all --prune` 후 GitHub의 열린 PR과 원격 브랜치를 본다. **아래 3절에 없는 PR이 있으면 이 문서가 낡은 것이다.** 실제 상태를 기준으로 한다.
2. 지금 어느 기기인지 확인한다. 이 저장소를 편집해 온 **보조 PC(`aux-pc`)**에는 세 CLI가 Windows에 설치돼 있다(아래 1절 관측). aux-pc에는 2026-09-23부터 **WSL2 배포판 `Ubuntu-24.04`**가 있다(`wsl -l -v`). 그 안의 기록은 이름표 `aux-pc-wsl`이다.
3. 이 세션이 무엇에 접근할 수 있는지(사용자 PC / 웹 컨테이너 / GitHub만) 정하고 PR에 적는다.
4. **GitHub만 보는 세션**(ChatGPT 웹 등)이라면 main이 아직 이 파일의 최신판이 아닐 수 있다. 3절의 브랜치에서 이 파일을 다시 읽는다.
5. **모델을 부르는 일은 사용자 승인 뒤에만 한다.** 사용량이 막히면 멈추고 사용자에게 알린다(사용자 요청, 2026-09-23 — Codex 사용량이 적게 남아 있었다).

## 1. 지금 상태

**연구·설계와 오프라인 검사 저장소에, 첫 실행 코어([`core/`](core/README.md))가 생긴 단계다. 앱(참여자를 돌리는 controller와 화면)은 아직 없다.** 근거 원장은 E01–E31 / F01–F31, 결정은 D01–D18이다. 검사 수와 결과는 [CI 실행 기록](https://github.com/inlight37-design/decision-model_lab/actions/workflows/checks.yml)이 기준이다.

| 도구 | 무엇이고 무엇이 아닌가 |
|---|---|
| [`core/`](core/README.md) | V04-03 실행 코어. `runner`는 CLI 한 번을 셸 없이 실행하고 추적 단위(Windows job object / POSIX 프로세스 그룹)가 비었는지 확인한다(못 하면 `unknown`). 자손 전체가 끝났는지는 `tree_confirmed_empty`가 따로 말하고, 프로세스 그룹에서는 `None`이다. `adapters`는 읽기 전용 논의자 실행 명세 조립(질문은 stdin, agy만 명령줄)·위험 플래그 거절·출력 판정. `env`는 자식 환경과 실행 파일 찾기(WSL에서 Windows 실행 파일 거절). `isolation`은 참여자 한 번을 bubblewrap으로 가둔다(허용 폴더만, PID namespace) — 이것으로 실행하면 Linux에서도 자손 전체의 종료를 확인한다. `membership`은 참여자가 빠지거나 바뀔 때의 결정이고, 공개 전에는 구성이 바뀔 때마다 정족수를 다시 본다. mock 시험과 aux-pc [conformance](docs/experiments/v04-03-conformance/aux-pc.md)에서 실제 CLI를 돌렸다. **controller·화면은 없다** |
| [`tools/v04-03/conformance.py`](tools/v04-03/conformance.py) | 합성 파일로 논의자 설정을 관측하는 스크립트. 일부 명령은 모델을 부른다 |
| [`check_frontier_protocol.py`](tools/check_frontier_protocol.py) | 합성 완료 기록의 일관성 검사. 기록된 disposition이 규칙에 맞는지 **검사할 뿐 계산하지 않는다** |
| [`review_boundary.py`](tools/review_boundary.py) | PR #3의 순수 함수 경계 실험(이벤트 순서, UNKNOWN 예산, 봉인 화면, 한도 표시). 서버·프로세스 제어가 아니다 |
| [`audit_design_contrast.py`](tools/audit_design_contrast.py) | 디자인 토큰 대비 계산. 일반 글자 5쌍이 4.5:1 미만인 것을 기록한다 |
| [`tools/w2/cli_boundary.py`](tools/w2/cli_boundary.py) | 설치된 Claude·Codex를 bubblewrap 참여자 경계 안에서 `--version`·로그인 상태만 실행해 본다. 모델을 부르지 않는다 |
| [`runtime_inventory.py`](tools/runtime_inventory.py) | V04-01 tier 1. 각 CLI의 `--version`/`--help`만 실행해 기록한다. `observed`와 `configured=true`를 쓸 수 없다 |

| 산출물 | 원본 | 발행본 |
|---|---|---|
| 작업 개념도 | [docs/concept/](docs/concept/README.md) | [아티팩트](https://claude.ai/artifact/AZJfdnmMBjpEAtqsSHzjp8) — 2026-09-22 스냅숏. 이후 변경은 원본 README에 적는다 |
| 디자인 시스템 `Ledger` | [design/](design/README.md) | [아티팩트](https://claude.ai/artifact/8tq8q5P8Pj7bpUtCF77FZA) — 2026-09-23 claude 세션이 `design/`과 맞춤 |
| 검토 기록 | [docs/reviews/](docs/reviews/README.md) | — |
| 조사 기록 | [Hermes 패턴 조사](docs/research/hermes-2026-09-23/README.md)와 [교차 확인](docs/research/hermes-2026-09-23/CROSSCHECK.md) | — |
| 지난 인계 | [docs/handoff/](docs/handoff/README.md) | — |

### 관측한 환경 — 보조 PC, 2026-09-23

**V04-01(설치·help·구독 호출·정책)은 끝났다.** 상세는 [aux-pc 결과](docs/experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md)와 [tier 2 manifest](docs/experiments/v04-01-inventory/hosts/aux-pc/manifest.tier2.json). **V04-03의 첫 conformance도 했다** — [기록](docs/experiments/v04-03-conformance/aux-pc.md).

- 설치: Claude Code 2.1.280 `~\.local\bin`, Codex 0.155.1 `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin`(→ `~\.codex`), agy 1.2.8 **`~\.local\agy\bin`**. 셋 다 설치 스크립트가 해시를 검증했고, `check-versions.ps1`이 서명 `Valid`를 보고한다. `gemini`, `node`, `gh`는 없다.
- **agy는 처음에 Claude 데스크톱 앱의 가상 공간에 설치돼 사용자 터미널에서 보이지 않았다.** AppData 밖으로 재설치했다. 원인과 대처는 절차서의 "AI 세션이 Claude 데스크톱 앱 안에서 대신 실행할 때" 절.
- PATH: Claude 설치 프로그램이 등록하지 않아 `%USERPROFILE%\.local\bin`을 추가했고, agy의 옛 항목을 지우고 새 폴더가 등록됐다(백업: `%TEMP%\v0401-user-path-backup.txt`, `...-backup-2.txt`).
- 로그인: Claude Code는 claude.ai 구독(`firstParty`), Codex는 ChatGPT 로그인 — 둘 다 데스크톱 앱의 기존 자격증명. agy는 사용자가 앱 밖 터미널에서 Google 계정으로 로그인했다. Claude CLI는 데스크톱 앱과 한도를 공유한다(E04).
- 과금 경로를 바꾸는 환경변수는 사용자·시스템 설정에 없다. Claude 데스크톱 앱의 셸에는 앱이 넣은 변수 26개(`CLAUDECODE`, `ANTHROPIC_BASE_URL` 등)가 있어서, AI 세션은 레지스트리 기준 환경(`--fresh-env`, `core.adapters.child_env`)으로 실행한다.
- tier 1·2: ACP는 세 CLI 모두 help에 없다. 세 CLI 모두 구독으로 비대화형 JSON 호출이 된다. 오타 옵션은 셋 다 거절한다. **agy는 `--output-format`의 없는 값을 조용히 무시한다.** `--bare`는 구독 불가(F25). Claude `-p`는 기본으로 사용자 플러그인·MCP를 싣는다. 결과에 모델 이름을 주는 것은 Claude뿐이다. `configured=true`는 기본 구독 호출을 관측했다는 뜻이지 conformance 통과가 아니다([PR #4 반영 기록](docs/reviews/2026-09-23-v04-01-review/RESPONSE.md)).
- **agy 기본 모델은 미확인**이고, **모델 이름의 Pro/Flash로 품질을 정하지 않는다** — 사용자 보고: `gemini-3.1-pro`는 옛 세대라 3.8 Flash보다 지시를 못 알아듣는다.
- **V04-03 conformance(합성 파일, 1회씩):** Claude(`claude-sonnet-5`)는 `--restricted`·`--safe-mode` 모두 허용 파일은 읽고 작업 폴더 밖 파일은 CLI가 거절, 쓰기 없음. **Codex(`gpt-6-luna`)는 Windows에서 `--ignore-user-config`를 주면 샌드박스 선택까지 버려져 모든 명령을 거절하고도 exit 0으로 답한다**([openai/codex#42172](https://github.com/openai/codex/issues/42172), 재현). `-c windows.sandbox="elevated"`를 더하면 읽기가 되고 쓰기는 막히지만 **작업 폴더 밖의 다른 참여자 초안도 읽는다.** Codex는 작업 폴더의 `AGENTS.md`를 싣고, Windows에서 명령을 PowerShell 5.1로 실행한다. `codex doctor`는 Windows 샌드박스가 설정돼 있다고 보고한다.
- 정책: Gemini CLI 소비자 인증은 2026-06-18에 닫혔다(F30). Antigravity 약관은 제3자 소프트웨어를 통한 접근을 위반으로 규정한다(F31) — 우리 앱의 `agy` 구동이 해당하는지 불명확, 공식 저장소 [#711](https://github.com/google-antigravity/antigravity-cli/issues/711)에 같은 질문이 있으나 Google의 답이 없다. agy의 `useG1Credits`(한도 소진 후 유료 크레딧)는 이 계정에서 **꺼져 있고**, 상호작용 데이터 사용(`enableTelemetry`)은 사용자 요청으로 **껐다**.
- 운용 PC는 아직 관측한 세션이 없다.
- 위 관측은 모두 Windows 네이티브 CLI의 것이다. Windows에만 해당하는 관측(openai/codex#42172 우회, PowerShell 5.1 재시도, `tools_rejected`의 거절 문자열)은 WSL에서 다시 본다.
- **WSL2 — `aux-pc-wsl`**([기록](docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/RESULTS.md)). 사용자가 2026-09-23 설치했다. WSL 2.7.14, Ubuntu 24.04.5, systemd 켜짐, 재부팅 불필요. 공식 설치 스크립트로 Claude Code 2.1.280, Codex 0.156.1을 `~/.local/bin`에 설치했다(tier 1 PASS). 사용자가 **로그인했다**(Claude `claude.ai`·`firstParty`, Codex ChatGPT)고 bubblewrap 0.9.0을 설치했다. tier 2(구독 호출)는 아직이다. AppArmor가 꺼져 있고 user·PID namespace를 권한 없이 만들 수 있다. PATH에 Windows 폴더(Windows 쪽 CLI 설치 폴더 포함)가 이어 붙어 있다 — `core/env.py`가 막는다. Codex는 Linux 샌드박스용 bubblewrap을 스스로 들고 온다. **W2 경계 시험 통과**(모델 없음, [기록](docs/experiments/w2-isolation/aux-pc-wsl.md)): 허용한 것만 보이고, 떨어져 나간 손자도 PID namespace와 함께 끝나며, 두 CLI가 격리 안에서 자기 로그인만 보고 시작한다. localhost 포트에는 닿는다(네트워크 공유).

### 열린 결정

| ID | 질문 | 상태 |
|---|---|---|
| Q1 | 어댑터 전송 | **확정 — exec 우선**(2026-09-23). ACP는 adapter 계층의 선택지로 남긴다 |
| Q2 | 의존 범위 | **확정** — 여러 제품에서 패턴을 추출하고 최신 이론과 결합한다 |
| Q3 | 언어/런타임 | Python 코어, TypeScript는 화면 경계만 |
| Q4 | 첫 화면 | `unresolved`. 결정 우선과 대조표 우선을 같은 내용으로 비교하는 실험(Q8) 뒤에 판정한다 — 4절 A1의 모의 화면에서 비교할 수 있게 만든다 |

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
15. **실행 기반은 WSL2로 간다**(옛 C1의 (b)). Windows는 화면과 사용자 작업, WSL2는 Python controller·실행 원장·봉인 저장소를 맡는다. 참여자는 시도마다 격리된 곳에서 Linux-native CLI를 구독 로그인으로 실행한다. WSL2 설치는 격리·종료·정족수의 해결책이 아니라 기반일 뿐이다. aux-pc의 Windows 네이티브 경로는 두되 더 제품화하지 않고, Codex를 blind 참여자로 쓰는 것은 WSL2에서만 한다. (2026-09-23, [경계 리뷰](docs/reviews/2026-09-23-wsl2-boundary/RESPONSE.md))
16. **격리 백엔드는 bubblewrap을 먼저 시험한다.** 참여자별 파일 허용 목록과 PID namespace로 파일 경계와 수명 경계를 함께 얻는다. 4단계 경계 시험에 실패하면 rootless podman으로 간다. 두 백엔드를 동시에 제품화하지 않는다. (사용자가 판단을 맡김, 2026-09-23)

## 3. 진행 중인 작업

2026-09-23의 작업은 모두 main에 병합됐다 — V04-01 리뷰([PR #4](https://github.com/inlight37-design/decision-model_lab/pull/4))와 반영, Hermes 패턴 조사([PR #5](https://github.com/inlight37-design/decision-model_lab/pull/5))와 교차 확인, V04-03 실행 코어, 첫 conformance와 Codex 샌드박스 원인 확인, 인계 정리(`claude/handoff-cleanup-20260923`). 사용자는 **CI 녹색을 확인한 claude 세션이 main에 직접 병합하는 것**을 허락했다(2026-09-23).

**지금 병합되지 않은 브랜치: `claude/review-request-20260923`** — 검토 요청서와 `env.resolve` 링크 우회 수정. bubblewrap 격리와 W2 경계 시험(`claude/w2-isolation-20260923`), `aux-pc-wsl` 설치와 tier 1 기록(W1, `claude/wsl2-setup-20260923`), 경계 리뷰 보존과 반영(`claude/wsl2-boundary-review-20260923`, 4절 1단계)과 실행 명세·stdin(A4)·core 환경 모듈(A7, `claude/execution-spec-20260923`)은 병합됐다. 새 작업을 시작하면 여기에 브랜치를 적고, 병합하는 커밋에서 이 줄을 다시 "없음"으로 돌린다. `git fetch`/열린 PR 결과와 다르면 GitHub가 맞다.

## 4. 다음 작업

**검토 요청 중(2026-09-23):** [요청서](docs/reviews/2026-09-23-wsl2-migration-request/README.md) — 경계 리뷰 반영부터 W2까지의 한 일, 잘 안 된 것, 아직 모르는 것, 계획. 결과가 오면 아래 "참고"의 리뷰 처리 규칙대로 반영한다.

지금 단계: **V04-03 준비 — 실행 기반을 WSL2로 옮기는 중**(2절 15·16). 실행 코어와 첫 conformance가 있고, 참여자를 돌리는 controller와 화면이 없다. exec 우선과 V04-03 순서는 바꾸지 않는다. 순서는 [경계 리뷰 반영](docs/reviews/2026-09-23-wsl2-boundary/RESPONSE.md)의 작업 순서를 따른다. **또 하나의 큰 설계 문서를 만들지 않는다.** 작은 실행 계약, 회귀 시험, 모의 controller, 한 번의 실제 conformance 순으로 증거를 쌓는다.

| 단계 | 할 일 | 모델 호출 | 선행 |
|---|---|---|---|
| 1 | 경계 리뷰 R01–R04의 회귀 시험과 수정 | 없음 | **끝**(`claude/wsl2-boundary-review-20260923`) |
| 2 | A4 실행 명세와 stdin, A7 core 환경 모듈(**끝**, `claude/execution-spec-20260923`). **A1 controller와 모의 모드 화면**(사용자에게 띄워 보여 준다), A2·A5·A6 | 없음 | 없음 |
| 3 | **W1 WSL2 설치와 Linux CLI 준비**, V04-01을 새 호스트 이름으로 다시 — 설치·tier 1·로그인·bubblewrap 끝, **tier 2가 남았다** | tier 2 몇 회 | 승인 |
| 4 | W2 bubblewrap 경계 시험과 runner의 `pid_namespace` 추적 단위 | 없음 | **끝**(`claude/w2-isolation-20260923`) |
| 5 | B1·B2를 WSL2에서, 그 뒤 **B3 V04-03 pilot과 사용량 비교** | 여러 번 | 2, 4, 승인 |
| — | B4 agy 관측 | 몇 회 | 사용자가 agy를 켤 때 |

### A. 바로 할 일 (모델 호출 없음)

- **A1. controller와 모의 모드 화면.** 사용자 요청(2026-09-23): 앱이 동작하는 단계가 되면 눈앞에 띄워 보여 줄 것. 모의 모드는 WSL2 없이도 만든다.
  - controller: 참여자 구성([`core/membership.py`](core/membership.py)) → 실행 명세 → runner → `interpret` 결과 → 카드. 이미 정해진 규칙을 처음부터 넣는다:
    - **단계 관문을 controller 한 곳에 둔다.** 명단 수용, 실행 허가, 초안 공개 허가, 결과 수용 허가를 따로 판정한다. membership의 판정만으로 진행하지 않고, 초안이 다 들어왔는지는 관문이 본다.
    - 논의자 작업 폴더는 앱이 만든 빈 임시 폴더(지시문 파일 없음). Codex는 작업 폴더의 `AGENTS.md`를 싣는다.
    - **초안과 원장은 controller만 여는 봉인 저장소(작은 SQLite journal과 파일)에 둔다.** 참여자 쪽에는 연결하지 않는다 — WSL2에서는 4단계 격리가 보장한다. Windows 네이티브에서 Codex를 돌리면 사용자 계정이 읽을 수 있는 파일을 다 읽으므로 blind는 "미확인"이다. 초안 단계가 끝난 뒤 허용된 비교 자료만 새 입력으로 만든다.
    - 논의자에게는 자료를 프롬프트(stdin)로 준다. 도구 시도와 입력 토큰이 줄어든다. Windows에서 Codex를 돌리면 `codex_windows_sandbox=True`를 준다.
    - 누적 호출·시도 상한과 동시 실행 자리를 나눈다. 자리는 runner의 `tree_confirmed_empty`가 True일 때만 푼다. 이미 쓴 호출 상한은 돌려주지 않는다. `UNKNOWN`은 자동으로 다시 부르지 않는다. 이벤트에는 run·attempt·epoch·sequence를 달고 중복·지연·역순을 처리한다. 규칙은 A7의 core 모듈에 두고, [`review_boundary.py`](tools/review_boundary.py)의 실험 형식을 이름만 바꿔 올리지 않는다(Hermes 조사 HP-03).
  - 모의 모드: 가짜 CLI(python 스크립트)로 Claude·Codex·agy·수동 카드의 흐름을 보여 준다. 사용량을 쓰지 않는다. 가짜 CLI는 aux-pc에서 받은 실제 출력 형식을 흉내 낸다.
  - 화면: [Ledger 디자인 시스템](design/README.md). 첫 화면 Q4(결정 우선 / 대조표 우선)를 같은 내용으로 바꿔 볼 수 있게 한다. 사용량은 두 층(아래 B3)의 자리를 둔다. 화면과 controller 사이 제어 API는 참여자가 닿지 못하게 한다(localhost TCP면 참여자에게 없는 토큰으로 막는다).
- **A2. 수동 전달.** 참여자 카드가 "사용자 전달 대기"로 서고, 앱이 봉인된 질문을 복사해 준다. 답은 붙여넣기나 앱이 지켜보는 결과 폴더로 받아 같은 카드에 채운다. 질문과 답에 run·attempt·입력 digest를 연결해 늦게 온 이전 실행의 답과 중복 제출을 가린다. MCP는 필요 없다. 수동 참여자의 사용량·시간은 "관측 안 됨"으로 표시한다.
- **A3. Codex 읽기 차단 설정(추가 방어층, 낮음).** 설정 문서에 권한 프로필 `permissions.<name>.filesystem`의 `"deny"`가 있다(2026-09-23 확인). 우리 adapter는 `--ignore-user-config`를 쓰고 `-c`·`--profile`을 금지하므로, 쓰려면 금지 목록 조정이 필요하다. 격리의 주 수단은 4단계 bubblewrap이다.
- **A4. 실행 명세와 stdin — 코드는 끝.** `adapters.build_spec()`이 `ExecutionSpec`을 돌려준다. argv에는 옵션만 있고 질문은 stdin으로 간다(Claude는 `-p`에 위치 인자 없이, Codex는 `exec … -`). 기록에는 입력 digest와 바이트 수만 남긴다. Claude 문서의 stdin 상한 10MB를 조립 전에 막는다. agy는 stdin 입력을 확인하지 못해 명령줄로 보낸다(B4에서 확인). cwd·환경·격리는 controller가 정한다(A1, W2). **남은 것:** 설치 버전에서 EOF·큰 한글 입력·선행 대시·전송 실패를 관측한다(W1 뒤 B1·B2와 함께, 모델 호출). Codex 명령 거절 흔적을 보관 상한과 무관하게 스트림 전체에서 세는 일(경계 리뷰 R04의 남은 것) — 지금은 stderr가 잘리면 답을 받지 않는다.
- **A5. manifest `runtime-inventory/2`.** controller가 adapter 상태를 읽게 될 때 `installed`·`auth_observed`·`transport_observed`·`context_conformance`·`permission_conformance`로 나누고, 실행 허가(`eligible_for_run`)는 실행 직전에 계산한다(PR #4 R02·R05).
- **A6. 입력 manifest.** 참여자마다 같은 공통 자료를 받았는지 digest로 고정한다(Hermes 조사 HP-02).
- **A7. core 환경 모듈 — 끝.** 환경 규칙을 [`core/env.py`](core/env.py)로 옮기고 `tools/runtime_inventory.py`가 그것을 쓴다(경계 리뷰 R05). core가 tools를 가져오지 않는 것을 시험이 막는다. WSL에서는 자식 PATH의 Windows 드라이브 항목(`/mnt/c/…`)을 빼고, 실행 파일이 Windows 쪽으로 풀리면 거절한다 — WSL은 기본으로 Windows PATH를 이어 붙인다.

### W. WSL2로 옮기기

- **W1. 설치와 준비.** Windows 기능을 켜는 설치(`wsl --install`)는 **사용자가 관리자 터미널에서 직접** 한다 — Claude 데스크톱 앱 안에서 대신 설치하면 앱의 가상 공간에 들어갈 수 있다(1절 agy 사례). 첫 실행의 Linux 사용자 만들기와 CLI 로그인도 사용자가 한다. 그 뒤 AI 세션이 배포판 안에 Linux-native Claude Code·Codex, `python3`, `bubblewrap`을 준비하고, V04-01 절차를 새 호스트 이름(예: `aux-pc-wsl`)으로 다시 기록한다. **Windows의 성공 기록을 복사해 성공 처리하지 않는다.** Windows HOME·자격증명 폴더를 연결하는 지름길은 쓰지 않는다. agy의 Linux 판은 미확인이다 — 없으면 Windows 수동 전달로 둔다.
- **W2. bubblewrap 경계 시험 — 끝(모델 없음).** [`core/isolation.py`](core/isolation.py)가 참여자·시도마다 허용한 폴더만 연결하고, 모든 namespace를 나누되 네트워크만 공유하며, `--die-with-parent`로 실행한다. `runner.run(..., pid_namespace=True)`면 추적 단위가 PID namespace가 되어 Linux에서도 `tree_confirmed_empty`가 True다. 양성·음성 대조, symlink 우회, `/mnt`·`/run`·`/init`, 환경변수, 떨어져 나간 손자, 시간 초과를 회귀 시험([`tests/test_core_isolation.py`](tests/test_core_isolation.py))으로 두었고, CI도 bubblewrap을 설치해 돌린다. 설치된 두 CLI는 격리 안에서 자기 로그인만 보고 시작했다. [기록](docs/experiments/w2-isolation/aux-pc-wsl.md). **남은 것(모델 호출, B1·B2):** 실제 질문 한 번이 격리 안에서 끝까지 도는지(토큰 갱신, DNS·TLS, stdin), Codex 자체 bubblewrap의 중첩, Linux Codex의 거절 문자열, `~/.claude` 전체 대신 필요한 파일만 연결하기(지금은 이 배포판의 대화형 Claude 세션 기록도 Claude 참여자에게 보인다). **controller 제어 API는 참여자에게 닿는다**(localhost 공유) — 토큰으로 막는다(A1).

### B. 사용자 승인 뒤 할 관측 (모델 호출)

도구는 [`tools/v04-03/conformance.py`](tools/v04-03/conformance.py). 한 번씩 실행하고 결과를 읽은 뒤 다음으로 간다. B1·B2는 WSL2(W2 통과 뒤)에서 한다.

- **B1. Claude 보강.** 지금까지 "`CLAUDE.md`를 싣지 않는다"는 모델의 자기보고뿐이다. stream-json의 init 이벤트(메모리 경로)로 확인한다. `--restricted`와 `--safe-mode`를 함께 준 조합도 한 번 본다. 그 뒤 기본 조합을 정한다.
- **B2. Codex 격리.** bubblewrap 안의 Codex가 허용 자료는 읽고, 다른 참여자 초안(허용 목록 밖 파일)은 읽지 못하는지 실제 호출로 본다. 자료를 stdin으로만 준 논의자가 도구를 시도하지 않고 답하는지와 입력 토큰도 본다(Windows 첫 관측은 도구 시도 때문에 27,000–41,000토큰). Linux Codex의 명령 거절이 stderr에 어떤 문자열로 남는지 보고 `tools_rejected` 판정을 맞춘다.
- **B3. V04-03 pilot과 사용량 비교.** Claude와 Codex가 서로 모르게 읽기 전용 초안을 내고 합성한다. 사용자는 AionUi가 각 앱을 직접 쓸 때보다 사용량을 몇 배 빨리 소모해 쓰지 않는다. 같은 질문을 (a) 각 앱에서 직접, (b) 우리 앱의 `single`, (c) `cross_check`로 돌려 비교한다. **구독 한도는 토큰에 비례해 줄지 않는다**(사용자 지적). 그래서 두 층으로 잰다. CLI가 보고한 토큰·호출 수·시간(안정적, 비교 기준)과, 각 회사가 보여 주는 한도 %를 묶음 전후로 읽은 값(실제 효과, 잡음 있음)이다. 같은 시간대에 번갈아 여러 번 돌려 범위로 적는다. 한도 %를 어디서 읽는지는 회사마다 확인이 필요하다 — Codex는 app-server의 한도 조회 경로가 문서에 있고 호출은 미시험이다(V04-01 P7).
- **B4. agy(사용자가 켤 때).** 없는 `--model`은 문서상 비영 종료·`ERROR`다 — 1.2.8에서 확인한다. 없는 `--effort` 값의 처리를 P3처럼 본다. `--model`을 주면 stream-json init에 `model`이 나온다는 문서 내용을 요청값과 대조한다. 모델은 세대와 실제 비교로 고른다.

### C. 사용자가 정할 것

- ~~C1. Codex를 blind 참여자로 쓸 때의 격리 방식~~ — **확정(2026-09-23): (b) WSL2와 참여자별 격리**, 2절 15·16. (a) 메모리 보관과 Codex 읽기 금지는 이번 실행의 초안만 가리고 지난 실행의 기록은 못 가리며, 읽기 금지 설정은 버전·플랫폼 의존이라 추가 방어층으로만 둔다.
- **C2. agy 자동 실행을 켤지.** 켜는 것은 사용자가 고른다(2절 14). 약관 해석(F31)은 여전히 불명확하고, 위험은 기술 실패가 아니라 계정 제재다.
- **C3. 첫 화면 Q4.** A1의 모의 화면으로 두 안을 비교한 뒤 정한다.

### D. 알려진 문제와 제약 — 해결 전까지 지킨다

| 문제 | 지금의 대응 |
|---|---|
| Codex: Windows에서 `--ignore-user-config`가 샌드박스 선택까지 버림(openai/codex#42172) | adapter의 `codex_windows_sandbox=True`. Codex를 올릴 때마다 다시 확인한다. Windows 네이티브 한정 |
| Codex: read-only 샌드박스는 쓰기만 막고 읽기는 막지 않음 | 초안은 참여자 쪽에서 읽을 수 없는 봉인 저장소에 둔다. W2·B2로 확인될 때까지 Codex 초안의 blind 조건은 "미확인"으로 표시한다 |
| Codex: 명령 거절이 JSONL에 없고 stderr에만 있음, 그래도 exit 0 | `interpret`가 `tools_rejected`로 판정한다. stderr가 잘렸으면 답을 받지 않는다. 찾는 문자열은 Windows 관측이다 — Linux에서 B2로 다시 맞춘다 |
| Codex: 작업 폴더의 `AGENTS.md`를 실음 | 앱이 만든 빈 작업 폴더 |
| Codex: Windows에서 PowerShell 5.1로 명령을 실행해 첫 명령 실패·재시도가 생김 | 논의자에게는 파일을 읽히지 않아 도구 시도 자체를 줄인다. Windows 네이티브 한정 |
| Codex·agy: 결과에 모델 이름이 없음 | 조용한 강등을 결과로는 못 잡는다. agy는 init 경로 확인(B4) |
| agy: `--output-format`의 없는 값을 무시 | adapter가 값을 고정하고 JSON이 아니면 형식 실패 |
| Claude: `CLAUDE.md` 미로딩은 자기보고 | B1 |
| runner: POSIX 프로세스 그룹은 새 세션으로 나간 자손을 담지 못함 | `tree_confirmed_empty=None`으로 보고하고, 자원·예산은 True일 때만 푼다. Linux에서는 참여자를 `core.isolation`의 bubblewrap으로 실행한다(`pid_namespace=True` → True, W2). **정정(2026-09-23):** 이 칸은 "트리를 확인 못 하면 `unknown`"이라고 적었지만, 수정 전 runner는 그 경우 트리가 비었다고 보고했다([경계 리뷰 R01](docs/reviews/2026-09-23-wsl2-boundary/RESPONSE.md)) |
| runner: Windows job 배정 직전에 생긴 자식은 추적 못 함 | 문서화한 한계. job 배정에 실패하면 `unknown` |

### E. 급하지 않은 것

- 대비 미달 5쌍의 토큰 수정. `design/`과 아티팩트를 함께 고친다.
- `review_boundary.quota_projection`의 가정 확인 — `resetsAt` 단위와 한도 ID 형식. 실제 한도 응답(B3)으로 확인한다.
- 운용 PC의 V04-01(필요할 때 같은 절차서로).
- Hermes 후속 후보(HP-04–HP-10: 스킬 단계 로딩, 범위 있는 기억, MCP allowlist, MoA 역할, 저장소 확장, Codex App Server)는 pilot 뒤에 하나씩.
- v0.4 원장 대부분 항목의 `recheck` 미기입, 외부 리뷰의 저우선 지적 L1–L4, 개수 lint의 SHA 예외 범위(보류, [반영 기록](docs/reviews/2026-09-23-v04-01-review/RESPONSE.md)), Actions의 Node 20 경고, GitHub 저장소 설명·토픽.

### 참고

- **다른 AI의 리뷰가 오면:** 발견마다 원 출력·코드로 확인해 **맞으면 원본에서 고치고(정정 표시), 틀리면 근거를 리뷰 폴더의 반영 기록에 답으로 단다.** 리뷰 원문은 고치지 않는다. 판단이 갈리는 것은 사용자에게 묻는다. CI 녹색이면 병합하고 [검토 목록](docs/reviews/README.md)을 갱신한다. 선례: [V04-01 리뷰 반영](docs/reviews/2026-09-23-v04-01-review/RESPONSE.md), [Hermes 교차 확인](docs/research/hermes-2026-09-23/CROSSCHECK.md).
- **보조 스크립트와 함정:** [`tools/v04-01/`](tools/v04-01/README.md), [`tools/v04-03/`](tools/v04-03/README.md), V04-01 절차서의 "AI 세션이 Claude 데스크톱 앱 안에서 대신 실행할 때" 절.
- **Hermes에서 옮기면 안 되는 동작**(마감 뒤 답 텍스트를 완료로 수용, 다른 CLI 로그인 빌려 쓰기 기본값, 매 턴 추가 호출, `--fallback-model`)은 [교차 확인](docs/research/hermes-2026-09-23/CROSSCHECK.md)에 코드 위치와 함께 있다.

## 5. 하지 말 것

- **PowerShell `Get-Content`/`Set-Content`로 문서를 일괄 편집하지 않는다.** 한글이 `?`로 바뀐다. 실제로 문서 3개를 잃었다가 git에서 복구했다.
- 사용자 지시 없이 main에 push하지 않는다. 다른 세션의 브랜치에 push하지 않는다.
- 살아 있는 문서에 검사 수·원장 건수·commit 수를 적지 않는다(CI가 막는다).
- API 키 설정, 추가 크레딧, 권한 우회 플래그를 쓰지 않는다. 인증 파일과 환경변수 값을 기록하지 않는다.
- 문서만 보고 `configured = true`로 만들지 않는다.
- **승인 없이 모델을 부르지 않는다.** 사용량이 막히면 멈추고 알린다.
- **exit 0이나 "답이 나왔다"를 성공으로 치지 않는다.** `core.adapters.interpret`의 판정을 쓴다. 시간 초과는 답이 보여도 실패다.
- **Codex 논의자가 도는 동안 다른 참여자의 초안을 사용자 계정이 읽을 수 있는 곳에 두지 않는다.**
- **Windows에서 Codex에 `--ignore-user-config`를 줄 때 샌드박스 덮어쓰기를 빼지 않는다.** 빼면 아무것도 못 읽은 답이 exit 0으로 나온다.
- **백슬래시가 든 텍스트(Windows 경로 등)를 셸 heredoc 안의 파이썬으로 고치지 않는다.** heredoc이 `\\`를 `\`로 바꿔 넘겨 제어 문자가 됐다(두 번 발생). 편집 도구를 쓴다.
- **Claude 데스크톱 앱 안에서 `%LOCALAPPDATA%`에 새로 설치하지 않는다.** 앱 전용 가상 공간에 들어가 사용자 터미널에서 보이지 않는다(agy에서 발생).
- **실측 전에 설계 문서나 원장 항목을 더 늘리지 않는다.** 막힌 질문은 실제 CLI 결과로 푼다.
- **WSL2 안에서 Windows 실행 파일(`*.exe`, `/mnt/c`의 CLI)을 참여자로 부르지 않는다.** Linux-native CLI만 쓴다. Windows HOME·자격증명 폴더를 WSL에 연결하지 않는다.
- **runner의 `unit_confirmed_empty`나 membership의 판정만 보고 자원·예산을 풀거나 단계를 넘기지 않는다.** 자원은 `tree_confirmed_empty`가 True일 때, 단계는 controller 관문을 지나서다.

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

`jsonschema`가 없으면 해당 검사는 skip된다. **skip은 통과가 아니다.** 로컬에서 skip이 있었다면 CI 로그로 확인한다. `core/` 시험의 Windows 경로(job object)는 CI(Linux)가 돌리지 않으므로 Windows에서 한 번 돌린다. 모델을 부르는 관측([`tools/v04-03/conformance.py`](tools/v04-03/conformance.py)의 `claude`·`codex`)은 검사가 아니다 — 승인 뒤에만 실행한다.
