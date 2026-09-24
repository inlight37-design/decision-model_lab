# 다음 세션 인계 — decision-model_lab

최종 갱신 **2026-09-24** · 작성 세션: chatgpt (GitHub 연결 + 격리된 분석 컨테이너, 사용자 PC·로그인된 CLI 접근 없음) · 브랜치 `chatgpt/lean-cancellation-20260924` · [PR #19](https://github.com/inlight37-design/decision-model_lab/pull/19), PR #18 위의 후속

현재 인계는 이 파일 하나다. 완료 이력이 다음 일을 가리지 않도록 정리했다. **이전 판 전체는 [보관본](docs/handoff/2026-09-24-before-a1-integrity.md)에 바이트 그대로 있다.** 사용자 결정(2절)과 금지 사항(5절)은 유지했고, 기기 관측·승인·명세 판정을 바꾸지 않았다. 직전 수정은 [PR #18 기록](docs/reviews/2026-09-24-a1-integrity/README.md), 간결성 점검·지속 취소·자원 정리는 [PR #19 기록](docs/reviews/2026-09-24-lean-lifecycle/README.md)에 있다. 이 판은 이전 인계의 필요한 부분만 고쳤으며 2절·5절 원문과 승인 경계를 유지했다.

## 0. 먼저 확인할 것

1. `git fetch --all --prune` 뒤 열린 PR과 `git branch -r --no-merged origin/main`을 본다. 3절과 다르면 GitHub가 기준이다. 아직 병합되지 않은 PR의 최신 인계는 그 브랜치에서 읽는다.
2. 접근 범위를 PR에 적는다. 기기는 Windows `aux-pc`, 그 안의 WSL2 `Ubuntu-24.04`(`aux-pc-wsl`)로 구분한다. 운용 PC는 별도 관측이 없다. 웹 컨테이너의 성공을 사용자 PC의 성공으로 옮기지 않는다.
3. [AGENTS.md](AGENTS.md)와 [협업 규칙](docs/COLLABORATION.md)을 읽는다. 작은 작업마다 커밋하고 곧바로 push한다. **ChatGPT는 main을 병합하지 않는다.** 사용자 또는 허락받은 claude 세션이 정확한 head의 CI 녹색을 확인한 뒤 병합한다.
4. **이번 전체 검토·수정 요청은 실제 모델 호출 승인이 아니다.** 이전 2단계와 K01 승인은 사용했다. 새 호출, 실제 인증 폴더를 연결하는 진단, 설치·로그인은 별도 승인 경계를 지킨다. 사용량 한도 메시지면 멈추고 알린다.
5. 다음 선택: A1 모의 후속(4절) 또는 K46 확인 호출의 새 승인(3절). Claude 문맥 상태 변경, C3 정책, TM 후보 채택, Q4 결정은 대신 확정하지 않는다.

## 1. 지금 상태

**A1은 독립 초안 공개 후 `report_without_synthesis` JSON을 저장할 수 있다. 합성자·주장 검증·결정 카드는 아직 없다.** 화면 서버는 모의 실행기만 쓴다. PR #18의 원장·HTTP·보고서 수정에 이어, 이번 PR은 실제 모델 호출 없이 지속 취소(K19), 작업 스레드 수명, 필요한 사건만 읽는 조회와 HTTP 연결/I/O 상한을 구현했다. 기존 runner의 취소 경로를 재사용하며 새 실행 엔진·서비스·런타임 의존성을 추가하지 않았다. 기존 실행 명세·격리·실행 허가·기기 관측 판정은 그대로다.

| 부품 | 책임과 현재 경계 |
|---|---|
| [`core/runner.py`](core/runner.py) | 셸 없이 한 번 실행. 프로세스 생성 전/입력 청크 사이 취소 확인, 잔류 스레드 집계 잠금. 입력 전달·추적 단위·전체 자손 종료를 구분하며 격리 없는 POSIX 전체 종료는 미확인이다 |
| [`core/adapters.py`](core/adapters.py), [`env.py`](core/env.py) | CLI별 읽기 전용 명세와 결과 판정, 자식 환경·실행 파일 검사. 기록은 질문 원문이 없는 `ExecutionSpec.record()`로 한다 |
| [`core/isolation.py`](core/isolation.py) | 참여자 진입점 `isolation.run()` 하나. 파일 허용 목록·빈 HOME/tmp·PID namespace·`never` 충돌 검사. 네트워크 공유와 자원 상한 부재는 남는다 |
| [`core/membership.py`](core/membership.py), [`eligibility.py`](core/eligibility.py) | 구성 변경·정족수와 실행 허가 계산. 허가는 근거·날짜·설치 버전·구독·현재 `spec_revision` 관측을 요구한다. 기록 자체의 진실성은 증명하지 않는다 |
| [`app/controller.py`](app/controller.py), [`store.py`](app/store.py) | 고정 입력 → 예약 → 수용 관문 → 봉인 → 공개의 유일한 상태 권위. 한 원장/한 controller, 시도 ID 조건부 전이, 늦은 결과 배제, 재시작 시 unknown. 거래 실패 복구에 이어 취소 의도를 영속화하고 COMMIT 뒤 신호를 보낸다. 늦은 답은 받지 않고 미확인 종료의 자리·예약 예산은 유지한다. 끝난 작업은 활성 스레드 목록에서 제거한다 |
| [`app/report.py`](app/report.py) | controller가 공개한 해당 실행만 원문·출처·고정 정족수·실패 포함 예산과 함께 JSON으로 투영. 합성·추천·사실 검증·추가 호출·원장 변경 없음 |
| [`app/server.py`](app/server.py), [`화면`](app/static/index.html) | 토큰이 필요한 localhost API와 빌드 없는 HTML/JS. 엄격한 요청 검사와 취소/보고 버튼. 인증 전 포함 동시 연결 상한, 소켓 유휴 및 연결별 I/O 기한. Python 계산 전체의 시간·CPU·메모리 상한은 아님 |
| [`app/cli_executor.py`](app/cli_executor.py) | 실제 Linux CLI 경로는 있지만 서버에 연결하지 않았다. 시도마다 기록으로 허가 계산. 관측 도구는 `prepare()`를 재사용하며 실제 controller의 `execute()` 호출 관측과는 다르다(K17) |
| [`tools/w2/observe.py`](tools/w2/observe.py) | 실제 관측 호출의 단일 경로. 승인·예약 잠금, provider별 예산, 수용 관문, K46 nonce/helper/errno, 큰 입력 가운데·끝 표식, 최종 가림 |
| [`tools/w2/`](tools/w2/README.md) | 모델 없는 CLI·인증 연결·Codex sandbox/profile 진단. 실제 로그인 폴더 연결도 승인 뒤에만. 합성 HOME을 먼저 쓴다 |
| [`tools/runtime_inventory.py`](tools/runtime_inventory.py) | 버전/help 수집과 기록 구조 검사. 수집 성공만으로 `observed`나 `configured=true`를 만들지 않는다 |
| [`design/`](design/README.md), [`아키텍처`](docs/architecture/v0.4/README.md) | Ledger 디자인과 계약·근거 원장. 이번 PR은 디자인 토큰·발행 아티팩트·근거 판정을 변경하지 않았다 |

### 기기 관측 — 이번 세션에서 재관측하지 않음

- Windows `aux-pc`: [V04-01 결과](docs/experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md), [첫 conformance](docs/experiments/v04-03-conformance/aux-pc.md). Windows 전용 Codex 설정·PowerShell·job object 사실을 Linux에 그대로 적용하지 않는다. Windows 실행 경로는 동결이다.
- WSL `aux-pc-wsl`: [tier 1](docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/RESULTS.md), [격리](docs/experiments/w2-isolation/aux-pc-wsl.md), [인증 연결](docs/experiments/w2-isolation/auth-mounts-aux-pc-wsl.md), [2단계](docs/experiments/w2-isolation/stage2-aux-pc-wsl.md), [후속](docs/experiments/w2-isolation/stage2-followup-aux-pc-wsl.md), [K01](docs/experiments/w2-isolation/k01-large-input-aux-pc-wsl.md), [K46 profile](docs/experiments/w2-isolation/k46-profile-aux-pc-wsl.md), [합성 HOME](docs/experiments/w2-isolation/k46-synthetic-aux-pc-wsl.md).
- 현재 [manifest](docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.v2.json)의 Claude 칸은 유지했다. 다만 K31/리뷰 R04가 문맥 관측의 증거 수준을 문제 삼는다. Codex 문맥은 `failed`이고 K46 변경 뒤 명세 판도 다시 맞춰야 하므로 **실제 실행 허가 없음**. 이를 고치지 않고 실제 실행기를 연결하지 않는다.
- 2단계는 Claude `claude-sonnet-5` 3회·Codex `gpt-6-luna` 2회였고 승인한 상한을 다 썼다. K01의 추가 Claude 1회도 끝났다. 이 모델 이름은 당시 관측/요청값이지 현재 공급자 모델 목록에 대한 새 주장이나 호출 승인이 아니다.
- WSL에서는 `bash -l`, 저장소 `/mnt/c/ai/decision-model_lab`를 쓴다. 비로그인 셸은 `~/.local/bin`을 못 찾는다. 설치·버전·로그인·OS 상세와 기기별 함정은 보관본 1절 및 위 관측 원문이 기준이다.

### 기록과 열린 결정

검토는 [목록](docs/reviews/README.md) 시간순으로 읽는다. 최근 이전 리뷰는 [PR #14 원문과 반영](docs/reviews/2026-09-24-review/README.md), 그 뒤 [PR #18 검토·수정](docs/reviews/2026-09-24-a1-integrity/README.md), [PR #19 간결성·수명 관리](docs/reviews/2026-09-24-lean-lifecycle/README.md)다. 예전 요청서가 아직 답을 기다리는 것은 아니다. [Hermes 조사·교차 확인](docs/research/hermes-2026-09-23/CROSSCHECK.md), [tmux 조사](docs/research/tmux-2026-09-23/README.md)는 후보이지 채택된 실행 엔진이 아니다.

| ID | 상태 |
|---|---|
| Q3 | Python 코어, TypeScript는 화면 경계. 현재는 빌드 없는 HTML/JS이며 이행 시점 미정 |
| Q4 | `unresolved`. 같은 내용의 결정 우선/대조표 우선을 비교한 뒤 정한다. 이번 배치 수정은 Q4 선택이 아니다 |
| Q5·Q6·C2 | 결정됨: 원본 앱 화면 자동화 안 함, 고정 정족수 정책으로 미확인 수동 답 구분, agy 자동 실행 기본 끔 |
| C3 | Claude 자기 보고의 증거 수준과 Codex 계정 플러그인·MCP 문맥 문제. 추가 관측 또는 명시적 정책 완화 중 사용자가 결정. 완화를 `observed`로 위장하지 않는다 |

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

## 3. 진행 중인 작업

**[PR #19](https://github.com/inlight37-design/decision-model_lab/pull/19), `chatgpt/lean-cancellation-20260924`: 간결성 검토·지속 취소·자원 수명 정리.** 시작점은 아직 열린 [PR #18](https://github.com/inlight37-design/decision-model_lab/pull/18)의 `2e9a74731770b59f2c57f154abe28a9d84654154`다. PR #19의 base도 그 브랜치여서 이번 변경만 보인다. ChatGPT는 main이나 이전 세션 브랜치를 변경·병합하지 않았다.

- **병합 순서:** PR #18을 먼저 main에 병합한 뒤 PR #19의 base를 main으로 바꾸고 최신 head의 CI와 충돌을 다시 확인한다. PR #19를 이전 세션 브랜치에 병합하지 않는다. 실제 PR 상태가 이 파일보다 우선이다.
- 코드 체크포인트 `32c1e2a4402037d9b065d72eb12d629fe542f584`, 임시 전송 파일 제거 `7390530cfcd8f78b7b5e86c64c712ccddbe63c73`. 최종 CI·검증 범위는 PR과 [검토 기록](docs/reviews/2026-09-24-lean-lifecycle/README.md). 모델 호출·실제 인증 폴더 연결은 없었다.
- 기존 병합 이력·원 관측은 바꾸지 않았다. 완전히 병합된 브랜치만 병합한 쪽이 지운다. 필요하면 [prune-merged-branches](.github/workflows/prune-merged-branches.yml)의 `dry_run`으로 먼저 확인한다. 두 열린 작업 브랜치는 아직 지우지 않는다.

### 사용자 판단·승인을 기다리는 것

- **Claude 문맥 칸:** 리뷰 R04(a)는 자기 보고만으로 `observed`라 하지 말고 `unknown`으로 바꾸라고 권했다. 바꾸면 실제 실행 허가도 사라진다. 이번에는 원 관측을 바꾸지 않았다. K31 추가 관측 또는 별도 정책을 정한다.
- **C3 / Codex 문맥:** 빈 작업 폴더에서 추가로 관측할지, 빈 폴더 완화를 정책으로 받아들일지 결정한다. `--keep-session`은 문맥 탐색 보조이지 독립성 증명이 아니며 기본 끔이다. 정책을 관측 성공으로 쓰지 않는다.
- **K46 승인 카드(아직 승인 아님):** Codex 최대 1회, Claude 0회, 실패·거부·timeout 포함, 300초, 요청 모델 `gpt-6-luna`, `--keep-session` 끔. helper 미실행/다른 명령/인증 파일 없음/열림/토큰 모양/종료 미확인에 멈춘다. 한도 메시지는 모두 멈춤이며 원문을 게시하지 않는다. 세션 기록도 원하면 같은 1회에 `--keep-session`을 붙일지 함께 명시적으로 정한다.
- **TM 후보:** PR #8 병합은 조사 보존이지 기능 채택이 아니다. 적용 계획 A(조회 중복 방지·오래된 응답 버리기·마지막 확인 시각)는 후보로 유지했다. tmux를 참여자 실행 엔진으로 붙이지 않는다.
- **Q3·Q4, agy B4:** 지금 대신 결정하지 않는다. aux-pc의 수동 답 대기 시연 journal은 저장소와 무관하며 이번 세션에서 열지 않았다.

## 4. 다음 작업

원칙: 큰 설계 문서를 더 쌓기보다 **재현 → 작은 실행 계약 → 회귀 시험 → 모의 기능 → 승인된 관측** 순으로 간다. 1단계 N0–N6과 2단계 관측은 끝났고, 3단계 A1의 일부를 이번 PR에서 진행했다. N0–N6 경위는 [1단계 직후 판](docs/handoff/2026-09-23-before-stage2.md)에 있다.

### A1 모의 후속 — 실제 모델 호출 없음

**끝난 부분:** 공개된 초안의 `report_without_synthesis` JSON 저장. 합성자가 없는 현재 A1의 산출물이며, 실제 합성 실패 복구나 결정 카드 완성이라고 부르지 않는다. 정족수 부족/미승인 축소/공개 전에는 저장할 수 없다.

**이번에 끝난 부분(K19):** 원장에 저장되는 취소, API/버튼, 실행기 신호 전달, 시작 전/입력 청크 사이 중단, 늦은 답 배제, 재시작 후 취소 유지. 취소 거래가 실패하면 신호도 보내지 않는다. 예약한 호출 예산을 돌려주지 않고 종료 미확인은 unknown/자리 점유를 유지한다. 원본 앱에서 사용자가 실행한 작업이나 이미 OS에 넘긴 입력을 강제로 되돌린다는 보장은 아니다.

**다음 권고:** 새 엔진이나 범용 프레임워크 대신 모의 합성자·주장 대조·결정 카드의 한 흐름을 기존 controller 위에서 완성한다. 전체 사건 payload 조회와 완료 스레드 누적은 제거했지만 기본 상태 조회는 여전히 모든 실행을 읽는다. 이력이 커질 때 목록 페이지화/선택 실행 상세를 먼저 측정하고, TM 조회 경쟁 개선은 아래 승인 후보로 남긴다.

그 뒤 남은 A1 범위:

- 모의 합성자·주장 대조·[결정 카드](design/project/components/DecisionCard/README.md). 반례·미합의·확인 불가를 유지하고, 합의가 사실 검증인 것처럼 표시하지 않는다. 그다음 Q4 비교를 한다.
- 사용량 두 층(K23): 실행별 CLI 보고값과 계정 전체 한도 관측을 구분한다. Claude `rate_limit_event`는 기존 2단계 stream-json 관측에 있다. 참여자 argv를 바꾸면 명세 판과 관측을 다시 맞춘다. 표시를 위해 모델을 더 부르지 않는다.
- 공통 자료 첨부, 결과 폴더 감시. 새 입력은 manifest에 고정하고 경로 허용 목록과 `never`를 유지한다.
- 사용자가 채택한 뒤 TM 적용 계획 A. 현재 UI의 주기 조회 경쟁·재접속 개선은 이번 수정에 포함하지 않았다.
- 편의 후보(2절 20): 공개된 결정 카드·요약만 새 실행의 고정 입력으로 넘기고 이전 run ID를 기록; 공개 뒤 controller가 중개하는 교차검토 한 라운드; 상급 모델의 다음 행동 제안. 모두 기본 끔/실행별 opt-in/추가 호출 예산 표시. 대화 전체·공개 전 초안 전달, CLI 자체 resume, 무제한 합의 루프, 모델이 승인·예산을 넘는 동작은 하지 않는다.

### K46 실제 확인과 C3 — 새 승인 뒤에만

K46은 K09보다 먼저다. adapter profile과 합성 HOME 진단은 끝났으나 **실제 exec에서 모델 명령이 인증 파일 읽기를 거절당하는지는 아직 모른다.** `codex exec`에는 `-P`가 없고 `-c default_permissions=…`를 쓴다. 옛 `--sandbox read-only`와 함께 주지 않는다.

승인이 생기면 `aux-pc-wsl` 로그인 셸에서 저장소 루트로 이동하여:

1. `python3 tools/w2/observe.py plan` — 실행 argv·연결 경로·승인 상태를 읽는다. 호출 목록/옵션을 카드와 대조한다.
2. `python3 tools/w2/observe.py approve --claude <n> --codex <n> --timeout <초> --note "<누가·언제·어디서 승인>"` — 사용자 승인값 그대로. 상한을 초기화하거나 늘리려는 용도로 다시 쓰지 않는다.
3. `python3 tools/w2/observe.py call k46-codex gpt-6-luna` — 승인된 한 번만. `--keep-session`도 승인에 포함된 때만 붙인다.
4. `python3 tools/w2/observe.py status`로 남은 상한을 확인한다.

기대값은 `gate == "ok"`, `k46.verified`, helper의 `write=denied:EROFS`, `input=ok`, `auth=denied:EACCES` 또는 EPERM, 빈 `boundary_violations`다. `as_expected`·`k46.problems`·원 출력까지 본다. 다르면 그 provider를 멈추고 K46을 닫지 않는다. 종료 코드 3은 기대와 다름, 2는 호출 안 함이다. 답이 있는 probe는 controller와 같은 관문을 통과해야 하며 P3 거부 시도도 예산에 센다.

성공한 관측만 현재 `discussant-2`에 맞는 전송·권한 칸으로 기록한다. 그것만으로 Codex 문맥(C3)이 풀리는 것은 아니다. 원 출력/세션은 저장소 밖 `~/.local/state/dml-observe/`에 두고, 읽어서 가린 요약만 옮긴다. 계정 식별자·인증 토큰·자유 파일 이름은 자동 가림 뒤에도 사람이 다시 본다. K01 큰 입력을 다시 볼 때는 `--pad-kb`의 가운데·끝 표식 둘 다 확인한다. 전송 완료가 마지막 바이트 소비의 증명은 아니다.

K09는 K46 뒤 연결을 좁힌 구성에서 재관측한다. Claude의 최소 인증/설정/캐시 연결 후보와 Codex 상태 DB·플러그인 공유, 토큰 갱신 미관측은 [직전 인계](docs/handoff/2026-09-24-before-a1-integrity.md) 4절에 그대로 있다.

### B3·B4

B3는 A1과 실행 허가/승인 뒤에 한다. 같은 질문을 원본 앱 직접 사용, 우리 앱 `single`, `cross_check`로 비교한다. CLI 토큰·시도·시간과 계정 한도 %의 전후 변화를 별도로 여러 번 번갈아 재고 범위로 적는다. 구독 한도 감소가 토큰에 비례한다고 가정하지 않는다. 목적은 AionUi에서 겪은 과한 사용량 소모를 반복하지 않는 것이다. 편의 후보의 실제 사용도 이 비교 뒤 결정한다. Codex 계정 한도 조회 경로는 아직 문서 수준이다.

B4는 사용자가 agy를 켤 때만: 없는 model/effort 처리, stream-json init의 모델 대조, stdin 입력을 관측한다. 약관의 제3자 구동 쟁점(F31)을 해결된 것으로 쓰지 않는다.

### 알려진 한계와 못 고친 문제

ID는 유지했다. 아래는 현재 조치 요약이며 상세 증거/과거 표현은 [직전 K 표](docs/handoff/2026-09-24-before-a1-integrity.md)와 그 표가 가리킨 관측 원문에 보존했다. **K19는 모의/합성 경계에서 구현·검증했다. K04·K27·K42는 보강했지만 OS/실제 기기 한계를 닫지 않았고, 기존 문맥·권한 관측 판정을 올리지 않았다.**

| ID | 현재 한계와 다음 경계 |
|---|---|
| K01 | 파이프 전송 완료 ≠ CLI 전체 소비. Claude 큰 입력은 전송·응답·토큰 증가 관측. 다음 큰 입력은 가운데/끝 표식 둘 다 확인 |
| K02 | Codex 명령 거부는 stderr 문자열 휴리스틱. 전체 스트림의 표식을 세며, 셀 수 없고 잘렸으면 수용하지 않음. K30과 함께 |
| K03 | 격리 없는 POSIX 전체 자손 종료는 미확인. 참여자는 `isolation.run()`만 |
| K04 | 잔류 집계에 잠금을 추가했고 끝난 controller 스레드는 보관하지 않음. 격리 없는 POSIX 잔류 파이프/fd 가능성은 남으며 `runner.lingering()`을 미정리 상한에 포함 |
| K05 | `CLEANUP_LIMIT`는 명시적 대기의 상한이며 벽시계 보장 아님 |
| K06 | Windows job 배정 전 자식/종료 신호 틈. Windows 경로 동결, 해당 OS 시험 별도 |
| K07 | agy 입력은 argv이며 stdin 미확인. 원시 argv 대신 `ExecutionSpec.record()`로 기록; B4 |
| K08 | 네트워크 공유(localhost·abstract socket 포함), 외부 서비스에 맡긴 작업은 종료 보장 밖. 제어 API 토큰은 별도 경계 |
| K09 | CLI 인증/설정 폴더 전체 writable 연결로 상태·세션·플러그인 공유. 토큰 갱신 미관측. K46 뒤 최소 연결 재관측 |
| K10 | 메모리·CPU 상한 없음 |
| K11 | `/etc`·`/usr` 읽기 노출은 신뢰 범위. `never`는 자동 연결과도 충돌 검사 |
| K13 | aux-pc-wsl AppArmor 꺼짐, CI user namespace 제한 해제. 일반 Ubuntu 기본 정책에서 별도 확인 필요 |
| K14 | 경로 검사와 마운트 사이 TOCTOU 가능 |
| K15 | bwrap 신뢰는 root 소유 `/usr/bin/bwrap` 검사. 같은 Python 프로세스의 악성 코드를 격리하는 장치 아님 |
| K16 | WSL Windows CLI 탐지는 경험칙. 실제 경계는 `/mnt`·`/init`·`/run`을 연결하지 않는 격리 |
| K17 | 실제 executor가 서버에 연결되지 않음. 관측의 `prepare()` 재사용 ≠ controller 전체 실제 호출. B3 전 필요 |
| K18 | **부분 진행:** 공개 뒤 합성 없는 JSON 보고 있음. 합성자·주장 대조·결정 카드·Q4 비교 없음 |
| K19 | **구현:** `runs.cancel_requested` 영속화 후 신호, 신규 시작/수동 제출/공개 차단, 늦은 답 배제, 재시작 유지. 예약 예산·미확인 종료 자리 유지. 시작 전/청크 사이 취소 확인이며 이미 진행 중인 OS 쓰기나 외부 앱 작업의 즉시 중단 보장은 아님 |
| K20 | 한 기기 파일 잠금/한 원장. 다중 기기 공유 미지원, 실행별 사건 순번. 거래 실패 복구 보강은 분산 원장 보장이 아님 |
| K21 | 수동 입력 일치/원본 앱 사용은 증명 불가. 다른 실행 표식은 거절하나 표식 없음도 받음; 사용자 확인은 별도 기록 |
| K22 | 수동 독립성 미확인. 고정 정책 `independent_only`/`include_unverified`와 표시를 구분 |
| K23 | 계정 잔여 두 층 표시·실행 간 누적 예산 없음. 보고서도 `account_remaining: unknown`으로 유지 |
| K24 | 대비 미달 토큰 조합 있음. 화면은 글자에 그 조합을 피함. 토큰 수정 시 발행 아티팩트 동기화 필요 |
| K25 | 화면은 HTML/JS, TypeScript 이행 미정(Q3). 분석 컨테이너의 Node 존재는 사용자 PC 설치 관측이 아님 |
| K26 | 토큰은 데이터 폴더와 서버 출력에 있음. 격리 밖 동일 사용자 프로세스는 신뢰 범위; POSIX 폴더 0700/파일 0600 |
| K27 | **부분 진행:** Chromium 오프라인 DOM/취소·보고서 다운로드·한글·390px 배치 확인. 실제 브라우저 localhost 탐색은 관리 정책으로 차단되어 미검증; 사용자 PC/접근성/교차 브라우저도 미검증 |
| K28 | journal 스키마 3: 취소 칸을 추가하며 기존 실행은 취소 아님으로 이전. 상향 이전만 지원, 더 새로운 버전은 거절. 이전 코드로 되돌리기 전 백업 필요 |
| K30 | Linux Codex의 실행 전 거부 문자열 미확인. 파일 쓰기 차단과 stderr 문자열 판정은 별개 |
| K31 | Claude 지시문 미적재는 모델 자기 보고뿐. init으로 확인 불가. 상태 변경/추가 관측은 사용자 판단 |
| K32 | Codex·agy 결과의 모델 보고 부재로 조용한 강등을 결과만으로 감지 불가 |
| K34 | Windows 전용 Codex #42172·PowerShell·폴더 밖 읽기는 Linux와 구분; Windows 동결 |
| K35 | 기기 관측은 aux-pc와 그 WSL뿐. 운용 PC 관측 없음; 이번 컨테이너/CI는 그 대체물이 아님 |
| K38 | Codex는 ignore 플래그에도 작업 폴더 AGENTS를 적재. 빈 작업 폴더 완화를 관측 성공으로 쓰지 않음; C3 |
| K39 | Codex read-only는 읽기 제한 아님. 다른 초안 읽기는 bubblewrap 허용 목록이 막음 |
| K40 | agy는 잘못된 output-format 값을 무시. adapter가 고정하고 비JSON은 형식 실패 |
| K41 | 공개 전 거친 상태 변경 시각은 반복 조회로 추정 가능. 정밀 시간·토큰·길이는 봉인, 참여자는 제어 토큰 없음 |
| K42 | **부분 진행:** 기존 요청 검사에 인증 전 포함 동시 연결 16개·연결별 I/O 기한 15초를 추가. 소켓 유휴 5초 유지. 느린 전송·스레드 시작 실패의 자원 회수 시험. 계산 전체의 시간/CPU/메모리 상한·실제 브라우저 교차 출처는 미검증 |
| K43 | 보고 모델 불일치는 거부/구성 축소. 사용자 승인 대기 상태는 없음; 전체 모델 이름으로 요청 |
| K44 | Codex 계정 플러그인·공급자 스킬·원격 MCP가 문맥에 들어가는지 미확인. `failed` 유지, 세션 요약은 탐색 보조 |
| K45 | Claude safe-mode의 agents-md 플러그인 의미 미확인. 참여자 argv는 restricted만 유지 |
| K46 | Codex auth.json 읽기 위험. adapter profile·합성 HOME errno 검증은 있으나 모델 exec의 집행 미관측. 새 승인 확인 호출 전 닫지 않음 |

기존에 닫힌 ID도 지우지 않는다: K12·K29·K33·K36은 [2단계 기록](docs/experiments/w2-isolation/stage2-aux-pc-wsl.md), K37은 사용자의 gh 로그인 후 claude가 CI 로그를 읽은 기록이다. 로그인이 풀리면 익명 API로 결과만 본다. 이번 PR의 CI 성공은 실제 CLI 인증/모델 품질 검증이 아니다.

낮은 우선순위 후보는 그대로다: 토큰 대비 수정, `quota_projection`의 실제 응답 대조, Hermes HP-04–HP-10, 원장 `recheck`, 외부 리뷰 L1–L4, 개수 lint SHA 범위, Actions Node 경고, 저장소 설명·토픽. 다른 리뷰가 오면 원문을 고치지 말고 반례 재현/원본 수정/회귀 시험/반영 기록 순으로 처리한다.

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

저장소 루트에서 모델 없이 실행한다. 설치가 필요한 기기에서는 먼저 설치 승인을 확인한다.

```bash
git config core.hooksPath .githooks
python -m pip install -r requirements-design.txt
python tools/check_encoding.py
python tools/validate_design_tokens.py
python tools/check_frontier_protocol.py
python tools/runtime_inventory.py --host-label <기기> --dry-run
python tools/runtime_inventory.py --validate docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.v2.json
python tools/validate_design.py
python tools/validate_v02.py
python tools/validate_sources.py
python -m unittest discover -s tests -v
python -m compileall -q tools tests core app
```

**skip은 통과가 아니다.** `jsonschema` 미설치, bubblewrap 사용 불가, 다른 OS 경로를 구분해 기록한다. CI는 Python 3.12/3.13과 `DML_REQUIRE_BWRAP=1`로 Linux 격리 시험을 요구한다. Windows job object는 별도 Windows 시험이 필요하다. root로 만든 가짜 bwrap 파일은 root 소유여서 root 소유 거부 시험의 전제가 달라진다 — 신뢰 가드를 약하게 만들지 말고 일반 사용자로 전체 시험을 돌린다.

WSL 로그인 셸에서는 `DML_REQUIRE_BWRAP=1 python3 -m unittest discover -s tests -v`로 확인한다. `tools/w2/cli_boundary.py`, `codex_sandbox.py`, `codex_profile.py --real-home`처럼 실제 인증 폴더를 연결하는 진단은 **모델이 없어도 사용자 허락이 필요하다**. 합성 HOME 기본 진단과 `observe.py plan`은 실제 호출과 구분한다.

모의 화면: `python -m app.server --port 8765` 뒤 출력된 `#token=…` 주소로 연다. CLI 모의는 Linux에서 bubblewrap이 필요하다. 모델 없는 수동 전달 시험은 CLI 참여자를 끄고, 최소 1·`include_unverified`로 새 실행을 만든 뒤 합성 문자열을 제출하여 보고서 저장을 확인한다. 이것을 원본 앱의 실제 응답으로 기록하지 않는다. 보고 파일에는 원문이 있으므로 공개 저장소에 올리지 않는다.

기기 작업 참고: Windows에서 WSL 호출은 스크립트를 만들어 `wsl.exe -d Ubuntu-24.04 -- bash -l <스크립트의 /mnt/c 경로>`로 넘긴다. Git Bash에서는 `MSYS_NO_PATHCONV=1`을 붙인다. 파이썬 파일 쓰기는 UTF-8 바이트/LF로 한다. PowerShell 인자·한글·긴 worktree 경로·앱 가상 설치의 상세 함정은 [직전 인계](docs/handoff/2026-09-24-before-a1-integrity.md) 4·6절에 있다.

aux-pc의 gh는 `C:\ai\tools\gh\bin\gh.exe`(Git Bash `/c/ai/tools/gh/bin/gh.exe`). 로그인은 사용자가 한다. 로그인돼 있으면 `gh pr checks <번호>`와 `gh run view <번호> --log`; 웹 세션은 GitHub 연결로 정확한 head와 Actions job 결과를 읽는다. 로그인 안 됨은 에이전트가 인증을 대신할 이유가 아니다. 병합 뒤에는 병합한 쪽이 끝난 브랜치를 정리한다.
