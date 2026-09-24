# 다음 세션 인계 — decision-model_lab

최종 갱신 **2026-09-24** · 작성 세션: codex(순서 1–4 구현), 병합 뒤 claude가 3절과 병합 표현을 고침 (둘 다 `aux-pc` — hostname `DESKTOP-L6EA2UJ`, 1절 기기 이름 — Windows와 WSL Ubuntu-24.04, 실제 모델 호출·인증 연결 진단 없음) · 브랜치 `claude/merge-offline-progression-20260924` · 기준 main `34975794dec2a45b9fd8a11f3133d2b202ebb8ee`

현재 인계는 이 파일 하나다. 완료 이력이 다음 일을 가리지 않도록 정리했다. **이전 판 전체는 [보관본](docs/handoff/2026-09-24-before-a1-integrity.md)에 바이트 그대로 있다.** 사용자 결정(2절)과 금지 사항(5절)은 유지했고, 기기 관측·승인·명세 판정을 바꾸지 않았다. 직전 수정은 [PR #18 기록](docs/reviews/2026-09-24-a1-integrity/README.md), 간결성 점검·지속 취소·자원 정리는 [간결성 검토 기록](docs/reviews/2026-09-24-lean-lifecycle/README.md)에 있다. 이 판은 이전 인계의 필요한 부분만 고쳤으며 2절·5절 원문과 승인 경계를 유지했다. 4절의 순서표는 2026-09-24 claude 세션이 두 검사(간결성·[구조](docs/reviews/2026-09-24-structure-audit/README.md))와 새 main의 실행 허가 계산을 보고 정했다.

## 0. 먼저 확인할 것

1. `git fetch --all --prune` 뒤 열린 PR과 `git branch -r --no-merged origin/main`을 본다. 3절과 다르면 GitHub가 기준이다. 아직 병합되지 않은 PR의 최신 인계는 그 브랜치에서 읽는다.
2. 접근 범위를 PR에 적는다. 기기는 Windows `aux-pc`, 그 안의 WSL2 `Ubuntu-24.04`(`aux-pc-wsl`)로 구분한다. 운용 PC는 별도 관측이 없다. 웹 컨테이너의 성공을 사용자 PC의 성공으로 옮기지 않는다.
3. [AGENTS.md](AGENTS.md)와 [협업 규칙](docs/COLLABORATION.md)을 읽는다. 작은 작업마다 커밋하고 곧바로 push한다. **ChatGPT는 main을 병합하지 않는다.** 사용자 또는 허락받은 claude 세션이 정확한 head의 CI 녹색을 확인한 뒤 병합한다.
4. **PR #22–#25의 검토·수정과 그 병합 요청은 실제 모델 호출 승인이 아니다.** 이전 2단계와 K01 승인은 사용했다. 새 호출, 실제 인증 폴더를 연결하는 진단, 설치·로그인은 별도 승인 경계를 지킨다. 사용량 한도 메시지면 멈추고 알린다.
5. 다음 일은 4절의 순서표를 따른다. 1–4는 끝났고 다음은 5다 — 5의 명세 판 설계는 사용자와 먼저 정한다. 사용자 결정이 필요한 것은 3절 표에 있다. Claude 문맥 상태 변경, C3 정책, TM 후보 채택, Q4 결정은 대신 확정하지 않는다.

## 1. 지금 상태

**main에 순서 1–4가 들어왔다**(PR #22–#25, 3절). 공유 가림·실행 허가 검사, 격리 연결 모델, 참여자 행을 원본으로 삼는 gate에 이어 공개 뒤 모의 합성·원문 대조·조건부 결정 카드와 Q4 두 배치 미리보기가 있다. 모의 합성은 같은 문장을 묶고 원문 위치·저장 해시를 대조할 뿐 의미나 사실을 판정하지 않는다. 모든 주장은 미해결이며 실제 모델 합성·품질 검증은 아직 없다. 화면 서버는 모의 실행기만 쓴다. 새 서비스·런타임 의존성·실제 모델 호출은 추가하지 않았다. 기존 기기 관측과 실행 명세 판정은 유지한다.

| 부품 | 책임과 현재 경계 |
|---|---|
| [`core/runner.py`](core/runner.py) | 셸 없이 한 번 실행. 프로세스 생성 전/입력 청크 사이 취소 확인, 잔류 스레드 집계 잠금. 입력 전달·추적 단위·전체 자손 종료를 구분하며 격리 없는 POSIX 전체 종료는 미확인이다 |
| [`core/adapters.py`](core/adapters.py), [`env.py`](core/env.py) | CLI별 읽기 전용 명세와 결과 판정, 자식 환경·실행 파일 검사. 기록은 질문 원문이 없는 `ExecutionSpec.record()`로 한다 |
| [`core/isolation.py`](core/isolation.py) | 참여자 진입점 `isolation.run()` 하나. 파일 허용 목록·빈 HOME/tmp·PID namespace·`never` 충돌 검사. 네트워크 공유와 자원 상한 부재는 남는다 |
| [`core/membership.py`](core/membership.py), [`eligibility.py`](core/eligibility.py) | 구성 변경·정족수와 실행 허가 계산. 허가는 근거·날짜·설치 버전·구독·현재 `spec_revision` 관측을 요구한다. 기록 자체의 진실성은 증명하지 않는다 |
| [`app/controller.py`](app/controller.py), [`store.py`](app/store.py) | 고정 입력 → 예약 → 수용 관문 → 봉인 → 공개의 유일한 상태 권위. 한 원장/한 controller, 시도 ID 조건부 전이, 늦은 결과 배제, 재시작 시 unknown. 거래 실패 복구에 이어 취소 의도를 영속화하고 COMMIT 뒤 신호를 보낸다. 늦은 답은 받지 않고 미확인 종료의 자리·예약 예산은 유지한다. 끝난 작업은 활성 스레드 목록에서 제거한다 |
| [`app/state.py`](app/state.py), [`synthesis.py`](app/synthesis.py) | 참여자 행에서 진행 gate를 파생. 공개 뒤 모의 합성을 한 번 저장하고 원문 위치·저장 해시 대조·조건부 결정 카드로 표시. 실패도 원문 보고를 보존하며 추가 호출 없음 |
| [`app/report.py`](app/report.py) | controller가 공개한 해당 실행만 원문·출처·고정 정족수·실패 포함 예산과 함께 JSON으로 투영. 합성·추천·사실 검증·추가 호출·원장 변경 없음 |
| [`app/server.py`](app/server.py), [`화면`](app/static/index.html) | 토큰이 필요한 localhost API와 빌드 없는 HTML/JS. 엄격한 요청 검사와 취소/보고 버튼. 인증 전 포함 동시 연결 상한, 소켓 유휴 및 연결별 I/O 기한. Python 계산 전체의 시간·CPU·메모리 상한은 아님 |
| [`app/cli_executor.py`](app/cli_executor.py) | 실제 Linux CLI 경로는 있지만 서버에 연결하지 않았다. 시도마다 기록으로 허가 계산. 관측 도구는 `prepare()`를 재사용하며 실제 controller의 `execute()` 호출 관측과는 다르다(K17) |
| [`tools/w2/observe.py`](tools/w2/observe.py) | 실제 관측 호출의 단일 경로. 승인·예약 잠금, provider별 예산, 수용 관문, K46 nonce/helper/errno, 큰 입력 가운데·끝 표식, 최종 가림 |
| [`tools/w2/`](tools/w2/README.md) | 모델 없는 CLI·인증 연결·Codex sandbox/profile 진단. 실제 로그인 폴더 연결도 승인 뒤에만. 합성 HOME을 먼저 쓴다 |
| [`tools/runtime_inventory.py`](tools/runtime_inventory.py) | 버전/help 수집과 기록 구조 검사. 수집 성공만으로 `observed`나 `configured=true`를 만들지 않는다 |
| [`design/`](design/README.md), [`아키텍처`](docs/architecture/v0.4/README.md) | Ledger 디자인과 계약·근거 원장. PR #18·#20–#26은 디자인 토큰·발행 아티팩트·근거 판정을 변경하지 않았다 |

### 기기 관측

- Windows `aux-pc`: [V04-01 결과](docs/experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md), [첫 conformance](docs/experiments/v04-03-conformance/aux-pc.md). Windows 전용 Codex 설정·PowerShell·job object 사실을 Linux에 그대로 적용하지 않는다. Windows 실행 경로는 동결이다.
- WSL `aux-pc-wsl`: [tier 1](docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/RESULTS.md), [격리](docs/experiments/w2-isolation/aux-pc-wsl.md), [인증 연결](docs/experiments/w2-isolation/auth-mounts-aux-pc-wsl.md), [2단계](docs/experiments/w2-isolation/stage2-aux-pc-wsl.md), [후속](docs/experiments/w2-isolation/stage2-followup-aux-pc-wsl.md), [K01](docs/experiments/w2-isolation/k01-large-input-aux-pc-wsl.md), [K46 profile](docs/experiments/w2-isolation/k46-profile-aux-pc-wsl.md), [합성 HOME](docs/experiments/w2-isolation/k46-synthetic-aux-pc-wsl.md).
- 현재 [manifest](docs/experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.v2.json)의 Claude 칸은 유지했다. 다만 K31/리뷰 R04가 문맥 관측의 증거 수준을 문제 삼는다. Codex 문맥은 `failed`이고 K46 변경 뒤 명세 판도 다시 맞춰야 하므로 **실제 실행 허가 없음**. 이를 고치지 않고 실제 실행기를 연결하지 않는다.
- 2단계는 Claude `claude-sonnet-5` 3회·Codex `gpt-6-luna` 2회였고 승인한 상한을 다 썼다. K01의 추가 Claude 1회도 끝났다. 이 모델 이름은 당시 관측/요청값이지 현재 공급자 모델 목록에 대한 새 주장이나 호출 승인이 아니다.
- WSL에서는 `bash -l`, 저장소 `/mnt/c/ai/decision-model_lab`를 쓴다. 비로그인 셸은 `~/.local/bin`을 못 찾는다. 설치·버전·로그인·OS 상세와 기기별 함정은 보관본 1절 및 위 관측 원문이 기준이다.
- **2026-09-24 claude 세션(aux-pc, 모델 호출 없음):** PR #20 head에 이어, PR #22–#25를 병합한 트리(#25 head `e053d0de35f71396d701020e43a032e2c43dc806`와 같은 트리)에서도 Windows 전체 시험과 WSL `DML_REQUIRE_BWRAP=1` 전체 시험이 통과했다. Windows에서 건너뛴 것은 Linux 전용 시험뿐이고, WSL에서는 Windows 레지스트리 시험 하나뿐이다. CLI 설치·로그인·버전은 다시 보지 않았다.
- **기기 이름:** codex 기록의 hostname `DESKTOP-L6EA2UJ`는 `aux-pc`로 본다. 같은 날 claude 세션이 그 hostname에서 OS 판(10.0.26200)·Windows Python 판·`C:\ai\tools\gh`·저장소 경로·WSL 배포판이 [aux-pc 기록](docs/experiments/v04-01-inventory/hosts/aux-pc/manifest.json)과 이 인계 6절과 같음을 봤다. hostname 자체는 aux-pc 기록에 없으므로 사용자가 다르다고 하면 고친다. 기록에는 hostname 대신 `aux-pc`/`aux-pc-wsl`을 쓴다.
- **실행 허가(같은 날 `eligibility()`로 계산, 설치 버전은 기록값으로 가정):**
  - **Claude:** 허가가 나온다. 다만 관측 30일 규칙으로 2026-10-23까지다. 그 근거인 전송·문맥·권한 관측은 모두 2단계 b1(`--add-dir … --tools Read`)에서 나왔다. controller의 실제 실행기는 공통 자료 없이 `--tools ""`로 부른다(구조 검사 G4).
  - **Codex:** 허가가 나오지 않는다. 명세 판이 `discussant-2`로 바뀌어 전송·권한을 다시 관측해야 하고, 문맥은 `failed`다.
  - **agy:** WSL에 설치돼 있지 않다.
- 기존 journal은 지금 main의 코드로 처음 열 때 스키마 4로 올라간다. 기존 `roster.phase`가 없거나 잘못되면 이전 전체를 롤백한다. 사용자 시연용 journal은 PR #22–#26의 세션 모두 열지 않았다. 사용 중인 원장은 새 코드로 열기 전에 백업하며 하향 이전은 없다(K28).

### 기록과 열린 결정

검토는 [목록](docs/reviews/README.md) 시간순으로 읽는다. 최근 이전 리뷰는 [PR #14 원문과 반영](docs/reviews/2026-09-24-review/README.md), 그 뒤 [PR #18 검토·수정](docs/reviews/2026-09-24-a1-integrity/README.md), [간결성·수명 관리](docs/reviews/2026-09-24-lean-lifecycle/README.md)다. 예전 요청서가 아직 답을 기다리는 것은 아니다. [Hermes 조사·교차 확인](docs/research/hermes-2026-09-23/CROSSCHECK.md), [tmux 조사](docs/research/tmux-2026-09-23/README.md)는 후보이지 채택된 실행 엔진이 아니다.

| ID | 상태 |
|---|---|
| Q3 | Python 코어, TypeScript는 화면 경계. 현재는 빌드 없는 HTML/JS이며 이행 시점 미정 |
| Q4 | `unresolved`. 같은 결과의 결정 우선/대조표 우선 미리보기를 구현했다. 사용자 비교·선택과 실제 브라우저 시각 확인은 남았다 |
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

**진행 중:** 없음. 열린 PR이나 `git branch -r --no-merged origin/main`에 무엇이 보이면 GitHub가 기준이다.

- **마지막 병합:** 순서 1–4(codex) — [PR #22](https://github.com/inlight37-design/decision-model_lab/pull/22) 공유 가림·실행 허가 → [#23](https://github.com/inlight37-design/decision-model_lab/pull/23) 격리 연결 모델 → [#24](https://github.com/inlight37-design/decision-model_lab/pull/24) 참여자 상태·gate → [#25](https://github.com/inlight37-design/decision-model_lab/pull/25) 모의 합성·결정 카드·Q4 미리보기. claude 세션이 [PR #26](https://github.com/inlight37-design/decision-model_lab/pull/26)(`claude/merge-offline-progression-20260924`)으로 이 순서대로 병합했다. 모델 호출 없음. 병합 검증과 검토는 [병합 기록](docs/reviews/2026-09-24-merge-22-25/README.md), 구현 판단과 검토 중 고친 결함(실행 ID 충돌, 공개 단계 없는 옛 원장 이전, 초안 해시 검증 누락)은 [codex 검토](docs/reviews/2026-09-24-offline-progression/README.md)에 있다.
  - 네 브랜치는 차례로 쌓였지만 같은 수정("공개 검사·짧은 실행 ID")이 층마다 따로 커밋돼, #22를 병합하면 #23·#24가 이 파일에서 충돌했다(코드는 충돌 없음). 다른 세션의 브랜치에는 push하지 않으므로 통합 브랜치에서 순서대로 병합하고 이 파일은 뒤 브랜치 판을 택했다. 병합 트리는 CI를 통과한 #25 head `e053d0d`와 같고, 네 PR의 head가 모두 main 이력에 들어간다.
  - 구조 검사의 틈 중 G1·G2·G3·G5·G7·G8·G9를 닫았다. 실행 계약의 G4·G6은 순서 5에 남는다.
- **그 앞:** [PR #21](https://github.com/inlight37-design/decision-model_lab/pull/21)(`claude/cleanup-merge-branches-il1srl`, 문서만, 모델 호출 없음) — [구조 전수검사](docs/reviews/2026-09-24-structure-audit/README.md), 간결성 검토와의 [비교](docs/reviews/2026-09-24-structure-audit/COMPARISON.md), 다음 일의 순서(4절). 결론: 뼈대는 구조적이고 살은 리뷰마다 덧댔다. 전면 재작성은 필요 없다. 흩어진 사본을 한 주인으로 모은다.
- **그 앞:** [PR #20](https://github.com/inlight37-design/decision-model_lab/pull/20) ChatGPT의 간결성 검토·지속 취소(K19)·자원 수명 정리. 사용자 지시로 claude 세션이 병합했다(`962b61c`). 병합 전에 CI 녹색에 더해 aux-pc의 Windows(job object 경로)와 WSL(`DML_REQUIRE_BWRAP=1`)에서 전체 시험이 통과했다. 처음 연 PR #19가 자동으로 닫히고 #20으로 다시 열린 경위는 [검토 목록](docs/reviews/README.md)의 22번 단서에 있다.
- **그 앞:** [PR #18](https://github.com/inlight37-design/decision-model_lab/pull/18) ChatGPT의 A1 무결성 수정과 합성 없는 보고. 보관한 인계와 2절·5절 원문이 그대로인지 확인하고 병합했다. 그보다 앞은 [직전 인계](docs/handoff/2026-09-24-before-a1-integrity.md) 3절과 Git 로그에 있다.
- 병합된 PR의 브랜치는 저장소 설정(병합 시 자동 삭제 — 켜져 있음을 2026-09-24 확인)이 지운다. 로컬에서 병합해 push한 브랜치와 통합 PR로 들어간 브랜치(PR #22–#25의 codex 브랜치처럼)는 자동으로 지워지지 않으므로 병합한 쪽이 지운다. 남은 것은 [prune-merged-branches](.github/workflows/prune-merged-branches.yml)를 `dry_run`부터 돌려 지운다.

### 사용자 판단·승인을 기다리는 것

순서 1–4는 main에 들어왔다. 다음은 순서 5의 실행 계약 설계와 아래 결정이다. 실제 모델 호출·정책 완화·설정 변경을 검토·병합 요청의 승인으로 해석하지 않았다.

| 결정 | 권고 | 무엇을 막고 있나 |
|---|---|---|
| **K46 확인 호출 승인.** 카드: Codex 최대 1회(Claude 0), 실패·거부·timeout 포함, 호출당 300초, 요청 모델 `gpt-6-luna`, `--keep-session`은 따로 정한다. 멈춤 조건은 4절 K46 절 | 이제 승인할 수 있다. 이 호출의 요약을 저장소로 옮기므로 먼저 하기로 한 가림 통합(4절 순서 1)이 PR #22로 main에 들어왔다 | Codex의 전송·권한 재관측 |
| **C3 Codex 문맥.** (a) 추가 관측 (b) 빈 작업 폴더 완화를 실행 허가의 정책 칸으로 받아들인다. 정책 칸은 관측과 구분해 화면·보고에 표시한다 | (b). 관측만으로는 계정 플러그인·원격 MCP가 문맥에 "없음"을 보이기 어렵다(K44). (b)는 실행 허가에 칸 하나를 더하는 작은 코드 변경이다. `--keep-session`은 탐색 보조이지 독립성 증명이 아니다 | Codex의 실행 허가 |
| **Claude 실행 허가를 다시 세우는 방법**(리뷰 R04(a)·K31·G4) | 4절 순서 5 뒤에 Claude 1회로 controller argv 그대로 다시 관측한다. 문맥은 모델 자기 보고가 아닌 방법으로 본다. 그때까지 기록은 바꾸지 않는다 — 서버가 모의 실행기만 써서 당장 막히는 일은 없다 | Claude의 실제 실행(순서 6) |
| **Codex 자동 리뷰** | 자동은 끄고, 코드를 바꾸는 PR에서만 세션이 `@codex review`로 부른다. 실제 버그를 두 번 잡았지만, 문서 PR에도 Codex 사용량을 쓸 수 있다. 설정: [Codex 설정](https://chatgpt.com/codex/cloud/settings/general) | 없음 |
| **main 필수 상태 검사**(저장소 주인만) | 켠다(`checks (3.12)`·`checks (3.13)`). "CI 녹색 전 병합 금지"가 문장이 아니라 장치가 된다. 주인 계정으로 한 push는 규칙을 우회할 수 있다 | 없음 |
| **정리 작업:** 끝난 일회성 진단 은퇴, 동결 Windows 경로를 한 모듈로, 인계 축소(구조 검사 P-2) | 셋 다 한다. 은퇴하는 파일은 기록 색인에 `retired at <sha>`를 남기고 지운다 | 4절 정리 작업 |
| **TM 적용 계획 A.** PR #8 병합은 조사 보존이지 채택이 아니다. tmux를 참여자 실행 엔진으로 붙이지 않는다 | 순서 4(PR #25)에는 넣지 않았다. 채택하면 다음 화면 작업 때 함께 한다 | 없음 |
| **Q3(TypeScript)·Q4(첫 화면)** | Q4: 두 첫 화면이 main에 있다. 모의 화면(6절)에서 공개 뒤 "모의 합성" 버튼을 누르고 A(결정 우선)·B(대조표 우선)를 실제 브라우저로 비교해 고른다 — 아직 없는 실제 브라우저 시각 확인(K27)도 이때 된다. Q3은 미룬다 | 없음 |
| **agy(B4)** | 필요할 때만 켠다. WSL에는 설치돼 있지 않다 | B4 |

## 4. 다음 작업

원칙: 큰 설계 문서를 더 쌓기보다 **재현 → 작은 실행 계약 → 회귀 시험 → 모의 기능 → 승인된 관측** 순으로 간다. 1단계 N0–N6과 2단계 관측은 끝났다. 3단계 A1은 공개, 합성 없는 보고, 지속 취소까지 왔다. N0–N6 경위는 [1단계 직후 판](docs/handoff/2026-09-23-before-stage2.md)에 있다.

### 순서 — 2026-09-24 정리

두 검사(간결성·[구조](docs/reviews/2026-09-24-structure-audit/README.md))와 main의 실행 허가 계산으로 정한 순서다. **1–4는 PR #22–#25로 main에 들어왔다. 다음 구현은 5다.** 각 단계는 main 대상 PR로 나누었다. G1–G9는 구조 검사 4절의 틈이다. Q4 배치 선택과 실제 호출 승인은 여전히 사용자 판단이다.

| 순서 | 할 일 | 왜 이 자리인가 |
|---|---|---|
| 1 · 완료 #22 | **작은 통합 묶음**(PR 둘로 나눠도 된다). 제품 쪽: 실행 허가가 `row_problems`로 시작한다(G5). 원장 `CREATE TABLE`의 정책 기본값을 지운다(G7) — 이전(migration)의 기본값은 스키마 2 이전 실행의 동작을 지키므로 둔다. 토큰 변수의 넘김·거절을 격리 여부별 표 하나로 적는다(G8). 도구 쪽: 가림을 한 모듈로 모으고 init 이름 공개 정책을 하나로 한다(G2·G3) | 작고 서로 독립이다. 가림 누락(G2)은 다음 실제 관측(K46) 전에 닫는다 |
| 2 · 완료 #23 | **격리 연결 모델**(G1). bwrap 적용 순서의 `(경로, ro/rw/tmpfs)` 목록 하나를 인자 조립과 검사에 함께 쓴다. 규칙은 셋이다: 덮음 거절, 바깥보다 넓은 안쪽 권한 거절, `never`와 겹침 거절 | 시스템 경로를 쓰기 가능하게 연결하는 부류를 통째로 막는다. 공통 자료 첨부와 실제 실행기 연결로 사용자가 고른 경로가 들어오기 전에 둔다 |
| 3 · 완료 #24 | **참여자 상태의 주인 하나 + 파생 gate**(구조 검사 5절 4, G9). 참여자 행을 유일한 주인으로 두고 전이를 헬퍼 하나로 모은다. `runs.roster` 사본은 참여자 행에서 파생해 손 동기화를 없앤다(`cancel_run`은 지금 명단을 맞추지 않는다). `cancel_requested` 판단 7곳을 gate 하나로 모은다. membership 결정의 `action`은 쓰거나 지운다 | 합성 단계가 전이를 더 만들기 전이다. PR #20의 취소 회귀 시험이 안전망이다 |
| 4 · 완료 #25 | **모의 합성자 → 주장 대조 → [결정 카드](design/project/components/DecisionCard/README.md)**, 그 뒤 Q4의 두 첫 화면 비교(K18). 반례·미합의·확인 불가를 보존하고, 합의를 사실 검증처럼 표시하지 않는다 | A1 완성이다. 3 위에서 전이 하나로 붙인다 |
| 5 | **실행 계약 완결**(G4·G6). `ExecutionSpec`이 명세 판·stderr 표식·모델을 갖고, 판은 argv 틀에서 정한다. 실행기는 계획 → 기록 → 실행(계획) 한 길로 간다. controller에서 모의 실행기 지식을 뺀다. 공통 자료 첨부도 여기서 함께 설계한다 | K17과 다음 Claude 관측 전에 한다. Claude argv는 공통 자료 유무로 두 모양인데, 지금 허가의 근거는 자료가 있는 모양이고 controller는 없는 모양을 쓴다(1절 기기 관측). 판이 갈리면 Claude 기록을 다시 적어야 하므로 판 설계는 사용자와 먼저 정한다 |
| 6 | **실제 실행기를 서버에 연결**(K17) | 5 뒤에 한다. 허가가 나온 CLI만 붙인다 |
| 7 | **B3 파일럿과 사용량 비교**(아래 B3 절) | 6 뒤, 승인 뒤에 한다. 여러 번 부른다 |

### 실제 관측 — 승인 뒤에만

- **K46 확인(Codex 1회):** 순서 1 뒤라면 언제든 된다. Codex argv는 공통 자료와 상관없이 한 모양이라(자료는 격리의 읽기 전용 연결로만 들어간다) 순서 5의 판 설계가 이 관측을 무효로 만들지 않는다. 성공하면 Codex의 전송·권한이 현재 판(`discussant-2`)으로 다시 선다. 그래도 문맥(C3)이 풀리기 전에는 허가가 나오지 않는다. 절차는 아래 K46 절이다.
- **Claude 재관측(1회):** 순서 5 뒤에 한다. controller argv 그대로 전송·문맥·권한을 보고, 문맥은 모델 자기 보고가 아닌 방법으로 본다(K31). 리뷰 R04(a)와 G4를 함께 닫고 30일 기한도 새로 연다.
- **agy(B4):** 사용자가 켤 때만.

### 정리 작업 — 작고 아무 때나

- **끝난 일회성 진단 은퇴**(사용자 확인 뒤, 시험 포함 약 −630줄): `tools/w2/codex_sandbox.py`, `tools/v04-03/conformance.py`, `tools/smoke_review_preview.py`, 쓰이지 않는 `tools/review_boundary.py`, 겹치는 `tools/w2/cli_boundary.py`. 실행 허가의 30일 재관측에 쓸 로그인 상태 탐침 하나는 관측 도구의 모델 없는 probe로 옮긴다.
- **관측 probe를 표 하나로**(약 −80줄): 관측 도구를 다음에 크게 고칠 때(예: Claude 재관측 probe를 더할 때) 함께 한다. 실제 호출 경로라 따로 떼어 하지 않는다.
- **동결 Windows 경로를 한 모듈로**(사용자 확인 뒤, 줄 수는 그대로): runner의 job object 분기, `codex_windows_sandbox`, `fresh_environment`.
- **과정:** 리뷰 반영 기록에 "주인 모듈"과 "부류 제거/국소 수정" 칸을 둔다(구조 검사 P-1). 원장 범위 표기를 지우고 시험이 원장에서 ID를 계산한다(P-3). 인계 축소(P-2)는 사용자 확인 뒤 한 세션에서 한 번에 한다.

### A1 모의 후속 — 실제 모델 호출 없음

**PR #25에서 끝난 부분:** 공개 초안의 원문 JSON 저장, 명시적 모의 합성, 원문 위치·저장 해시 대조, 조건부 결정 카드, Q4 두 배치 미리보기. 원문 보고 판 2의 합성 상태는 `not_included`이며 결정 보고는 모의 결과를 별도로 묶는다. 정족수 부족/미승인 축소/공개 전에는 합성하거나 저장할 수 없다. 실패는 `unavailable`로 기록하고 원문을 보존한다. 실제 모델 합성 실패나 사실 검증을 재현했다는 뜻은 아니다.

**PR #20에서 끝난 부분(K19):** 원장에 저장되는 취소, API/버튼, 실행기 신호 전달, 시작 전/입력 청크 사이 중단, 늦은 답 배제, 재시작 후 취소 유지. 취소 거래가 실패하면 신호도 보내지 않는다. 예약한 호출 예산을 돌려주지 않고 종료 미확인은 unknown/자리 점유를 유지한다. 원본 앱에서 사용자가 실행한 작업이나 이미 OS에 넘긴 입력을 강제로 되돌린다는 보장은 아니다.

**다음:** 위 순서표 5의 실행 명세 판 설계, Q4의 사용자 비교 판단, 실제 브라우저 시각 확인이다. PR #25를 만든 codex 세션은 브라우저 연결 목록이 비어 있어 시각 검증을 하지 못했고, HTTP 경계와 오프라인 JavaScript 렌더링만 따로 검사했다. 병합한 claude 세션도 브라우저로 보지 않았다. 기본 상태 조회는 여전히 모든 실행을 읽으므로, 이력이 커질 때 목록 페이지화/선택 실행 상세를 먼저 잰다.

순서표 4 안팎의 남은 A1 범위:

- 사용량 두 층(K23): 실행별 CLI 보고값과 계정 전체 한도 관측을 구분한다. Claude `rate_limit_event`는 기존 2단계 stream-json 관측에 있다. 참여자 argv를 바꾸면 명세 판과 관측을 다시 맞춘다. 표시를 위해 모델을 더 부르지 않는다.
- 공통 자료 첨부(순서표 5와 함께 설계), 결과 폴더 감시. 새 입력은 manifest에 고정하고 경로 허용 목록과 `never`를 유지한다.
- 사용자가 채택한 뒤 TM 적용 계획 A. 현재 UI의 주기 조회 경쟁·재접속 개선은 이번 수정에 포함하지 않았다.
- 편의 후보(2절 20): 공개된 결정 카드·요약만 새 실행의 고정 입력으로 넘기고 이전 run ID를 기록; 공개 뒤 controller가 중개하는 교차검토 한 라운드; 상급 모델의 다음 행동 제안. 모두 기본 끔/실행별 opt-in/추가 호출 예산 표시. 대화 전체·공개 전 초안 전달, CLI 자체 resume, 무제한 합의 루프, 모델이 승인·예산을 넘는 동작은 하지 않는다.

### K46 실제 확인과 C3 — 새 승인 뒤에만

K46은 K09보다 먼저다. 이 호출의 요약을 저장소로 옮기므로 먼저 하기로 한 순서표 1의 가림 통합(G2)은 PR #22로 끝났다. adapter profile과 합성 HOME 진단은 끝났으나 **실제 exec에서 모델 명령이 인증 파일 읽기를 거절당하는지는 아직 모른다.** `codex exec`에는 `-P`가 없고 `-c default_permissions=…`를 쓴다. 옛 `--sandbox read-only`와 함께 주지 않는다.

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
| K18 | **모의 흐름 구현:** 공개 뒤 발췌 합성·원문 대조·조건부 결정 카드·Q4 두 배치 미리보기. 실제 모델 합성·외부 사실 검증·Q4 사용자 선택은 남음 |
| K19 | **구현:** `runs.cancel_requested` 영속화 후 신호, 신규 시작/수동 제출/공개 차단, 늦은 답 배제, 재시작 유지. 예약 예산·미확인 종료 자리 유지. 시작 전/청크 사이 취소 확인이며 이미 진행 중인 OS 쓰기나 외부 앱 작업의 즉시 중단 보장은 아님 |
| K20 | 한 기기 파일 잠금/한 원장. 다중 기기 공유 미지원, 실행별 사건 순번. 거래 실패 복구 보강은 분산 원장 보장이 아님 |
| K21 | 수동 입력 일치/원본 앱 사용은 증명 불가. 다른 실행 표식은 거절하나 표식 없음도 받음; 사용자 확인은 별도 기록 |
| K22 | 수동 독립성 미확인. 고정 정책 `independent_only`/`include_unverified`와 표시를 구분 |
| K23 | 계정 잔여 두 층 표시·실행 간 누적 예산 없음. 보고서도 `account_remaining: unknown`으로 유지 |
| K24 | 대비 미달 토큰 조합 있음. 화면은 글자에 그 조합을 피함. 토큰 수정 시 발행 아티팩트 동기화 필요 |
| K25 | 화면은 HTML/JS, TypeScript 이행 미정(Q3). 분석 컨테이너의 Node 존재는 사용자 PC 설치 관측이 아님 |
| K26 | 토큰은 데이터 폴더와 서버 출력에 있음. 격리 밖 동일 사용자 프로세스는 신뢰 범위; POSIX 폴더 0700/파일 0600 |
| K27 | **부분 진행:** Chromium 오프라인 DOM/취소·보고서 다운로드·한글·390px 배치 확인. 실제 브라우저 localhost 탐색은 관리 정책으로 차단되어 미검증; 사용자 PC/접근성/교차 브라우저도 미검증 |
| K28 | journal 스키마 4: 기존 명단에서 공개 단계를 한 번 이전. 참여자 상태는 행에서만 파생. 단계 누락/오류는 전체 롤백. 상향 이전만 지원하므로 새 코드 사용 전 백업 필요 |
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

기존에 닫힌 ID도 지우지 않는다: K12·K29·K33·K36은 [2단계 기록](docs/experiments/w2-isolation/stage2-aux-pc-wsl.md), K37은 사용자의 gh 로그인 후 claude가 CI 로그를 읽은 기록이다. 로그인이 풀리면 익명 API로 결과만 본다. CI 성공은 실제 CLI 인증/모델 품질 검증이 아니다.

낮은 우선순위 후보는 그대로다: 가림의 `Bearer` 최소 길이(PR #22 뒤 help 문장의 "Bearer token"도 가린다, [병합 기록](docs/reviews/2026-09-24-merge-22-25/README.md)), 토큰 대비 수정, `quota_projection`의 실제 응답 대조, Hermes HP-04–HP-10, 원장 `recheck`, 외부 리뷰 L1–L4, 개수 lint SHA 범위, Actions Node 경고, 저장소 설명·토픽. 다른 리뷰가 오면 원문을 고치지 말고 반례 재현/원본 수정/회귀 시험/반영 기록 순으로 처리한다.

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
