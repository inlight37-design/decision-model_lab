# app — A1 controller와 명시적 CLI 실측

기본은 **모델을 부르지 않는 모의 모드**다. `--live-cli`로 명시한 경우에만 실제 구독 CLI를 연결한다. 첫 실측 경로는 서버당 CLI 하나와 수동 참여자로 제한한다. 흐름은 한 줄이다.

고정 입력(질문 → 프롬프트, sha256) → 시도 예약 → 실행 → 결과 수용 관문 → 초안 봉인 → controller가 공개 → 모의 합성 → 원문 대조 → 결정 카드/JSON 보고

| 파일 | 하는 일 |
|---|---|
| [`controller.py`](controller.py) | 상태를 가진 유일한 곳. 자리·예산, 결과 수용 관문, 봉인과 공개, 수동 참여자, 지속 취소, 다시 시작, 화면용 투영 |
| [`store.py`](store.py) | 작은 SQLite journal. 사건은 덧붙이기만 한다. 초안도 여기에 봉인한다 |
| [`state.py`](state.py) | 참여자 행에서 취소·정족수·축소 승인·공개 관문을 계산. 별도 참여자 명단을 동기화하지 않는다 |
| [`fake_cli.py`](fake_cli.py) | Claude·Codex 출력 형식을 흉내 내는 가짜 CLI. 행동: 정상, 느림, CLI 오류, 입력 일부만 읽음, 멈춤 |
| [`cli_executor.py`](cli_executor.py) | 실제 CLI 실행기(Linux·WSL). `plan()`이 `env.resolve` → `build_spec` → 격리 경계(`cli_mounts`, `never`) → 판 계산으로 최종 계획을 한 번 만들고, `run()`이 그 계획 그대로 `isolation.run` → `interpret`한다([실행 계약](../core/contract.py)). **모델을 부른다 — 승인 뒤에만.** 서버의 `--live-cli` 경로가 사용한다. 이 기기의 기록(`runtime-inventory/2`)과 계획의 판으로 시도마다 실행 허가를 계산한다 — 기록 없이 부르는 것은 관측 도구와 시험(`unchecked`)뿐이다 |
| [`report.py`](report.py) | 공개된 실행의 합성 없는 보고. 원문·출처·정족수·예산을 투영하며 모델 호출·원장 변경 없음 |
| [`synthesis.py`](synthesis.py) | 모의 발췌 합성, 원문 위치·저장 해시 대조, 조건부 결정 카드. 사실 검증과 의미상 합의 판정은 하지 않는다 |
| [`server.py`](server.py) | 127.0.0.1 화면 서버. 모든 `/api` 요청에 토큰 |
| [`static/index.html`](static/index.html) | 화면. [Ledger](../design/README.md)의 토큰과 규칙을 따른다 |

## 실행

```bash
python -m app.server --port 8765
```

출력된 주소(`http://127.0.0.1:8765/#token=…`)를 연다. 데이터는 `~/.decision-model-lab/mock/`(journal과 토큰 파일)에 쌓인다. 모의 CLI는 Windows에서는 job object로, Linux·WSL2에서는 [`core.isolation`](../core/isolation.py)의 bubblewrap으로 실행한다. 그래서 결과 수용 관문이 실제 종료 확인을 받는다. bubblewrap을 못 쓰는 Linux에서는 종료를 확인하지 못해 결과가 `unknown`으로 남는다 — 의도한 동작이다.

## 참여자 두 종류

- **CLI(자동).** 기본은 모의 실행이다. `--live-cli`, 전체 모델 이름, 관측 기록, 별도 데이터 폴더, 호출 예산을 명시해야 실제 실행으로 연결된다. 문맥 미확인 실행은 별도 opt-in이고 독립 정족수에 세지 않는다. aux-pc WSL에서 [첫 Codex 응답의 수용·공개](../docs/reviews/2026-09-24-live-cli-pilot/README.md)를 확인했다. 독립성·제공 모델 확인과 복수 실제 CLI·실제 합성은 남았다.
  - 실행 명세(`ExecutionSpec.record()` — 질문 본문 없이 digest와 크기)는 시작 사건에 시도 ID와 함께 남는다.
  - 프로세스를 만들기 전에 거절하면(실행 파일 없음, 모델 이름 없음, 경로 충돌) `failed_to_start`로 끝난다. 시작한 것이 없으므로 `unknown`이 아니다.
- **원본 앱(수동).** ChatGPT·Claude·Antigravity 앱에서 사용자가 직접 돌린다.
  1. 화면이 질문을 복사해 준다. 첫 줄은 실행 표식 `[Ledger <실행 ID>/<참여자> · <입력 sha256 앞 8자>]`이고, 답 첫 줄에 그 줄을 되말해 달라는 부탁이 붙는다.
  2. 사용자가 원본 앱에 붙여 넣고, 받은 답을 화면에 붙여 넣는다. "원본 앱에 이 질문을 넣어 받은 답이다"를 체크할 수 있다.
  3. controller가 답을 받기 전에 확인하는 것: 늦게 온 답이나 중복 제출이 아닌지, 빈 답이 아닌지, **답의 표식이 다른 실행이나 다른 참여자의 것이 아닌지** — 다른 카드에 붙여 넣은 답은 받지 않는다. 표식이 맞으면 그 줄을 빼고 초안으로 받는다.
     - 표식을 되말했는지(`marker_echo`)와 사용자 확인(`user_confirmed`)은 따로 기록한다. **둘 다 약한 증거일 뿐이다.** 원본 앱에 정말 이 질문을 넣었는지, 다른 답을 보지 않았는지는 확인하지 못한다(인계 4절 K21·K22). 표식을 되말하지 않은 답도 받는다.
     - 화면은 그 카드가 속한 실행의 입력 sha256을 자동으로 넣어 보내므로, sha256 검사는 화면을 거치지 않은 요청의 불일치만 막는다.
  - 원본 앱의 기능(메모리, 컴퓨터 사용, 세션 기능)을 그대로 쓰는 대신, blind와 사용량은 "관측 안 됨"으로 표시한다. 원본 앱의 메모리나 다른 대화를 이 앱이 통제하지 못하기 때문이다.

## 정족수 정책(Q6)

실행을 만들 때 고르고 바꾸지 않는다(journal의 `runs.quorum_policy`).

- **`independent_only`(기본)** — 엄격한 문맥 관문을 요구하는 CLI만 센다. 문맥 미확인 CLI와 원본 앱 답은 정족수에 세지 않고 보조 근거로 함께 공개한다. 확인 가능한 인원이 최소보다 적으면 실행을 만들지 않는다.
- **`include_unverified`** — 문맥 미확인 CLI와 원본 앱 답도 센다. 공개된 실행은 "미확인 참여 포함 정족수"로 표시하고, "독립 정족수 충족"이라고 쓰지 않는다.
- 이 정책을 두기 전(스키마 1)의 실행은 원본 앱 답을 셌으므로 `include_unverified`로 올린다.

## 지키는 규칙

- **결과 수용.** 받으려면 모두 맞아야 한다: 자손 전체 종료 확인, `interpret()`의 ok, 질문을 stdin으로 끝까지 보낸 기록(`complete`), 비어 있지 않은 답, 보고된 모델이 요청과 다르지 않음.
  - 종료를 확인하지 못하면 `unknown`이다. 초안을 받지 않고 실행 자리를 풀지 않으며, 다시 부르지 않는다.
  - 사용자가 "종료를 직접 확인했음"을 누르면 자리만 푼다. 예산은 돌려받지 않는다.
  - 입력 전달 기록이 없거나(`input_error`), 답이 비었거나(`empty_answer`), 모델이 다르면(`model_mismatch`) 받지 않는다. 모델 보고가 없는 CLI(Codex)는 불일치가 아니다. 모델은 전체 이름으로 요청한다 — aux-pc 관측에서 Claude는 전체 이름을 보고했다.
- **원장 소유.** 원장(journal)은 한 번에 하나의 controller만 연다. 같은 데이터 폴더로 서버를 하나 더 띄우면 원장과 토큰 파일을 건드리기 전에 멈춘다. 시도의 시작과 결과 반영은 기대한 상태와 시도 ID가 맞을 때만 한다. 그 뒤에 온 결과는 사건으로만 남는다.
- **봉인.** 공개 전 화면에는 제출 여부와 실행 상태의 고정된 필드만 넘긴다(Ledger BlindBarrier). 초안의 내용·길이·digest, 토큰 수, 걸린 시간, 보고된 모델은 공개 뒤에, CLI가 쓴 오류 원문과 실행 메모는 모든 참여자가 끝난 뒤에 넘긴다.
- **공개.** 화면에 공개 버튼이 없다. 남은 참여자가 모두 끝났고 정족수가 있으면 controller가 연다. 판정은 상태를 바꾼 같은 거래 안에서 한다.
  - 누가 빠졌으면 자동으로 진행하지 않고 사용자의 **축소 승인**을 기다린다. 승인은 그것을 기다릴 때만 받는다 — 미리 한 승인은 받지 않는다.
  - 정족수가 모자라면 승인해도 열지 않는다. 유료로 채우지 않는다.
- **자리와 상한.** 동시 실행 자리는 `running`과 `unknown`이 차지한다. 정리되지 않은 시도(`unknown` + `runner.lingering()`)가 상한에 닿으면 새 시도를 시작하지 않는다.
- **다시 시작.** 이전 controller가 돌리던 시도는 `unknown`이 된다. 다시 부르지 않는다. 초안 작성 중인 실행은 공개 관문을 다시 본다.
  - 시작하지 못한 시도는 저절로 시작하지 않는다. 화면의 "대기 중인 시도 이어서 시작"을 눌러야 시작한다. 원장에 취소가 기록된 실행은 재시작·재개 뒤에도 시작하지 않는다.
  - journal에는 스키마 버전이 있다. 예전 journal은 처음 열 때 올리고, 이 코드보다 새 journal은 열지 않는다. 스키마 4는 `runs.phase`를 기존 명단에서 이전한다. 누락되거나 잘못된 단계는 전체 롤백하며, 과거 roster/note는 더 이상 판정에 쓰지 않는다. 스키마 5는 시도마다 실행 종류(`participants.kind`: mock/real/synthetic)를 저장하고, 화면·보고는 지금 붙은 실행기가 아니라 이 값을 읽는다. 옛 시도는 시작 사건에 남은 실행기 이름으로 복원하며 근거가 없으면 "실행 종류 기록 없음"이다. 사용 중인 journal은 새 코드로 열기 전에 백업한다. 하향 이전은 없다.
- **제어 API.** 참여자는 격리 안에서도 localhost를 공유한다. 그래서 모든 `/api` 요청(읽기 포함)에 토큰을 요구하고, Host 머리글이 우리 주소가 아니면 거절한다.
  - Origin이 있으면 해당 서버 origin만 허용한다. JSON 객체·문자열/정수 타입·단일 길이를 검사하고, 모호한 framing·과대/미완성 본문을 거절한다. frame 삽입 거절 헤더와 소켓 유휴 5초 제한이 있다. 인증 전 연결까지 최대 16개, 연결별 I/O 기한 15초이며 느린 전송으로 늘릴 수 없다. 초과 연결은 닫는다. 이 기한은 Python 계산 전체의 실행 시간/CPU/메모리 상한이나 상태 변경 취소 보장이 아니다.
  - 토큰은 URL의 `#` 뒤로만 브라우저에 준다. 페이지 자체에는 토큰이 없다.
  - 토큰 파일은 controller 데이터 폴더에 있고, 이 폴더는 참여자 격리에 연결하지 않는다(`never`). 토큰 파일은 처음부터 0600으로 만들어 통째로 바꾸고, 데이터 폴더는 0700이다(POSIX).

## 실행 취소

초안 작성 중 **“이 실행 취소”**를 확인하면 `POST /api/runs/<run_id>/cancel`이 취소를 원장에 저장한다. 기존 인증·Origin 검사를 그대로 쓰며, 200은 요청 저장이지 모든 프로세스 종료 확인이 아니다.

- 취소 거래가 COMMIT된 뒤 기존 executor → isolation → runner 경로에 신호를 보낸다. 실행 단계(`phase`)는 마지막 단계를 보존하고 `cancel_requested`가 다시 시작할 수 없는 중단 여부를 나타낸다. 별도 취소 엔진은 없다.
- 아직 예약하지 않은 CLI와 수동 대기는 시작 전 취소로 끝난다. 이미 예약한 시도의 예산은 돌려주지 않는다. 종료 미확인은 `unknown`과 자리 점유로 남기고, 나중에 정상 답이 와도 받거나 공개하지 않는다.
- 취소 뒤 수동 답 제출·축소 승인·초안 공개·보고서 저장은 막는다. 이미 봉인한 초안은 지우지 않고 계속 비공개로 둔다. 공개된 실행을 취소해서 다시 숨기지는 못한다.
- runner는 프로세스 생성 전과 입력 청크 사이에 신호를 확인한다. 이미 OS에 넘긴 쓰기나 외부 서비스/원본 앱에서 사용자가 실행한 작업의 즉시 중단은 보장하지 않는다. 원본 앱 중단은 사용자가 따로 한다.

완료한 스레드 참조는 활성 작업 목록에서 제거한다. 조회는 사건 전체 payload 대신 마지막 사건 이름만 SQL에서 읽으며 보고서는 해당 실행만 투영한다. 기본 상태 조회는 아직 모든 실행을 읽으므로 큰 이력에서는 목록/상세 분리가 다음 측정 대상이다.

## 합성 없는 보고

공개 뒤 **“합성 없는 보고 저장(JSON · 원문 포함)”**을 누르면 `<run_id>-without-synthesis.json`을 내려받는다. API는 기존 토큰이 필요한 `GET /api/runs/<run_id>/report`이며, 아직 공개할 수 없으면 409다.

`a1-draft-report/3`은 고정 질문/프롬프트·입력 해시/크기, 수용된 초안 원문과 해시, 참여자 출처/독립성과 시도의 실행 종류(`execution`), 고정 정족수 정책, 탈락/축소 승인, 실패 포함 시도 예산을 담는다. 수동 독립성은 `unverified`, 계정 잔여는 `unknown`, 합성은 `not_included`, 검증은 `not_performed`다. 판 2의 출처에 있던 "지금 붙은 실행기"는 과거 시도의 출처가 아니어서 뺐다(판 3). 판 1의 `not_implemented`는 판 2에서 원문 전용 내보내기의 뜻에 맞게 바꿨다. 해시는 진실성이나 독립성의 증명이 아니다.

`report.py`는 controller의 공개 투영만 읽고 상태를 바꾸거나 모델을 부르지 않는다. 다른 실행/향후 자유 메타데이터는 허용 목록 밖이면 내보내지 않는다. 입력 해시/크기 또는 저장된 초안 해시 불일치, 공개 초안 누락은 거절한다. 내려받은 파일은 질문과 초안 원문을 포함하므로 공개 저장소에 자동으로 올리지 않는다.

## 모의 합성·주장 대조·Q4 비교

공개된 실행에서 **“모의 합성 · 주장 대조 만들기”**를 누르면 `POST /api/runs/<run_id>/synthesize`가 결과를 원장에 한 번 저장한다. 중복 요청·재시작은 같은 결과를 사용한다. 공개 전·취소·종료 미확인·축소 승인 대기에서는 실행하지 않는다. 모의 합성 실패나 발췌 불가 시 `unavailable`로 기록하고 기존 원문 보고서를 유지한다. 추가 모델 호출과 자동 재시도는 없다.

합성은 원문의 줄을 발췌해 같은 문장만 묶는 모의 구현이다. 실행 ID·참여자·문자 위치·저장 해시로 원문 일치를 검사하며, 문장의 의미나 진실은 판정하지 않는다. 모든 주장은 `unresolved`, 카드는 `qualified`다. 표시 한도와 같은 참여자의 반복 줄은 생략 수를 표시하고 전체 초안은 보존한다. 반례와 미합의를 해결했다고 주장하지 않는다.

같은 결과를 **A · 결정 우선 / B · 대조표 우선**으로 바꿔 볼 수 있다. Q4 선호를 저장하거나 확정하지 않는다. 결정 보고서 `GET /api/runs/<run_id>/decision-report`는 모의 결과와 원문 보고를 함께 내보낸다. 회귀 시험은 [`test_app_synthesis.py`](../tests/test_app_synthesis.py)에 있다. aux-pc의 실제 내장 Chromium에서 데스크톱/좁은 폭의 두 배치와 모의 흐름을 [확인했다](../docs/reviews/2026-09-24-post-merge-verification/README.md). 사용자 선택과 교차 브라우저·접근성 전수 검사는 남았다. 실제 다운로드 완료와 취소 확인창 수락/거절은 후속 claude 세션이 설치된 Edge로 [확인했다](../docs/reviews/2026-09-24-execution-contract/README.md).

## 실제 연결 전 준비 조회

WSL 로그인 셸에서 `python -m app.server --check-cli codex --model gpt-6-luna --inventory <manifest.v2.json>`처럼 provider·전체 모델 이름·기록을 지정한다. Claude는 `--check-cli claude-code`다. 이 명령은 자료 없는 현재 참여자 계획의 판과 설치 버전·관측 기록을 대조한 JSON만 출력하고 끝난다. 서버·원장·CLI 프로세스·모델을 시작하지 않으며 인증을 갱신하지 않는다. 허가되지 않으면 종료 코드 2, 관측 조건을 만족하면 0이다. 조회 결과는 실행 승인/예산이 아니고 bubblewrap namespace를 실제 만들 수 있다는 보장도 아니다. 실행기는 시작 직전에 허가를 다시 검사한다.

기본 strict 정책에서는 두 CLI 모두 허가가 없다. `--allow-context-unverified`는 C3의 의미상 합격만 실행의 필수 조건에서 제외한다. 기록의 구조 오류, 설치·구독·전송·권한, 판/버전/날짜 검사는 그대로다. `--inventory`/`--model`만 주면 모의 실행으로 조용히 대체하지 않고 거절한다.

## 첫 실제 실행: 기존 K46 계획을 그대로 사용

2026-09-24 사용자 요청으로 아래 경로의 [첫 실측을 완료했다](../docs/reviews/2026-09-24-live-cli-pilot/README.md). PR #34 head에서 `2+3`에 `5`를 받아 수용·공개했고, 원문 보고를 인증된 읽기 전용 API로 로컬 저장했다. 이번 단일 호출 상한은 소진됐다. claude 세션이 사용자 요청으로 별도 원장·상한 1에서 PR #35 head로 [한 번 더 재현](../docs/reviews/2026-09-24-live-pilot-replication/README.md)했고, 예산 소진 뒤 두 번째 실행이 시작 전에 거절되는 것도 확인했다. 아래 명령은 절차 참고이며 **재실행에는 새 호출 승인·상한이 필요하다.**

Codex K46 관측은 **읽기 전용 입력 폴더 하나**가 있는 `codex@8a0128d4c791` 계획에서 성공했다. 자료 없는 다른 계획으로 바꾼 뒤 같은 시험을 다시 요구하지 않는다. 첫 실측은 별도 빈 입력 폴더를 하나 연결해 기존 판을 그대로 사용한다. `contract.LEGACY`를 확대하거나 manifest의 C3 `failed`를 `observed`로 바꾸지 않았다. 이 판에서 C3 opt-in을 쓰면 기존 기록이 실행을 허용한다는 것은 오프라인으로 확인했다. 설치판·날짜·경로는 기동 시 다시 검사하며, Claude의 다른 전송·권한 판을 대신 허용하지 않는다.

사용자가 승인한 **구독 호출 실측**을 수행할 때, `aux-pc-wsl`의 로그인 셸에서 저장소 루트 기준으로 실행한다. 아래는 Codex만 최대 한 번, 180초 상한이다. 이전 `observe.py` 승인 원장을 초기화하지 않는다. 이 예산은 새 앱 실측의 별도 누적 상한이며 다른 앱/계정 전체 사용량의 잔여가 아니다.

```bash
input_dir="$(mktemp -d /tmp/dml-pilot-input.XXXXXX)"
inventory="docs/experiments/w2-isolation/2026-09-24-k46-confirmation/manifest.v2.json"
data_dir="$HOME/.local/state/dml-live-pilot"

# 프로세스·서버·모델·원장을 시작하지 않는 조회
python3 -m app.server --check-cli codex --model gpt-6-luna \
  --inventory "$inventory" --input-dir "$input_dir" --data-dir "$data_dir" \
  --allow-context-unverified

# 위 조회가 eligible=true일 때만. 기동 자체는 모델을 부르지 않고 화면의 시작 버튼이 호출한다.
python3 -m app.server --live-cli codex --model gpt-6-luna \
  --inventory "$inventory" --input-dir "$input_dir" --data-dir "$data_dir" \
  --allow-context-unverified --call-budget 1 --timeout 180
```

서버가 출력한 localhost 주소를 열고, 비민감한 짧은 질문으로 시작한다. 첫 화면은 실제 모드·전체 요청 모델·문맥 미확인·호출 예약 상한을 표시한다. 첫 실측에서 `gpt-6-luna` 요청은 응답을 받았지만 CLI가 제공 모델을 보고하지 않아 실제 모델 일치는 미확인이다(K32). 다른 모델로 자동 대체하지 않는다.

결과는 **실제 CLI / 문맥 미확인**, 정족수는 **확인 0 / 미확인 1**이어야 한다. 원문 JSON을 저장한다. 정족수 미달·실패·UNKNOWN이면 자동 재호출하지 않는다. 실제 시작 전 예약을 원장에 남기며 실패·취소·재시작으로 환불하지 않는다. 같은 원장에 같은 `--call-budget 1`로 다시 켜도 추가 호출은 차단된다. 새 폴더를 만들거나 상한을 올려 한도를 우회하지 않는다. **상한을 올리는 것은 코드가 막지 않는다.** 원장은 예약 건수만 세고, 상한은 기동할 때 준 `--call-budget` 값을 쓴다. 그래서 이것은 절차 규칙이다([N1](../docs/reviews/2026-09-24-live-pilot-replication/README.md)). 실행 카드의 "외부 호출 예산"은 시작 전 거절도 시도로 센다. 실제 호출 수는 상태줄의 `실제 호출 예약`으로 본다(N2). UNKNOWN은 실행 자리를 붙잡고 실측 서버의 다음 시작을 막는다.

입력 폴더는 이 파일의 첫 시험에서는 빈 폴더다. 실제 공통 자료의 스냅샷·내용 해시·수동 참여자 전달 UI는 구현하지 않았으므로 자료 검증까지 했다고 해석하지 않는다. 합성은 계속 **모의 발췌**이며 실제 합성 모델/사실 검증을 호출하지 않는다.

### 문맥을 줄이는 후속 경로와 정정

“구독 로그인에 설정 폴더 전체가 필수”라는 설명은 Codex에는 맞지 않는다. [공식 인증 문서](https://developers.openai.com/codex/auth/)는 파일 저장 방식에서 `auth.json`만 headless 환경으로 옮기는 절차를 제공한다. 깨끗한 전용 로컬 인증 프로필을 만들 수 있다는 근거이지 계정 원격 도구나 최종 요청 전체가 깨끗하다는 증거는 아니다. 실제 토큰을 GitHub·웹 컨테이너로 가져오지 않는다. 갱신 경쟁/키체인 방식은 사용자 PC에서 따로 확인해야 하므로 이 변경은 인증 파일을 자동 복사하지 않는다.

[Claude `--bare`](https://code.claude.com/docs/en/headless)는 구독 OAuth·키체인을 사용하지 않고 API 인증을 요구하므로 이번 구독 전용 해결책으로 쓰지 않는다. [Codex 공식 설정](https://developers.openai.com/codex/config-reference/)의 앱/플러그인 제어는 전용 프로필 실측 후보다. 파일 격리와 원격 계정 문맥을 혼동하지 않는다. 이 변경은 환경·CLI 옵션을 추가로 바꾸지 않아 K46 계획을 유지한다. 확인일: 2026-09-24.

## 아직 없는 것

- 복수 실제 CLI 동시 참여와 실제 합성. 단일 Codex 경로의 첫 응답은 기록했다. 다음은 복수 참여 연결과 provider별 실행 조건·호출 상한을 준비하고, 새 승인 뒤 실측하는 단계다.
- 실제 모델 합성, 의미상 주장 대조·외부 사실 검증. Q4 두 배치의 사용자 선택.
- TypeScript 화면. 현재 제품 화면은 빌드 없는 HTML·JS이고 이행 시점은 Q3로 남아 있다.
- 입력 manifest의 공통 자료(파일) 첨부. 지금은 질문 한 개다.

검사: [`tests/test_app_controller.py`](../tests/test_app_controller.py). 대부분은 프로세스 없는 합성 실행기로 보고, 한 묶음은 모의 CLI를 실제 실행 경로(Windows job object, Linux bubblewrap)로 돌린다. 실제 CLI 실행기는 [`tests/test_app_cli_executor.py`](../tests/test_app_cli_executor.py)가 설치된 모양 그대로 만든 가짜 `claude`·`codex`로 격리 경로를 돌려 본다(Linux).

원장/HTTP 회귀는 [`test_app_integrity.py`](../tests/test_app_integrity.py), 보고서/인증 경계는 [`test_app_report.py`](../tests/test_app_report.py), 실행 계약(계획 한 번·저장한 실행 종류·스키마 5 이전)은 [`test_app_contract.py`](../tests/test_app_contract.py)에 있다. [2026-09-24 검증 기록](../docs/reviews/2026-09-24-a1-integrity/README.md)은 실제 HTTP 시험과 오프라인 DOM 시험을 구분한다.

지속 취소·재시작·예산·늦은 답은 [`test_app_cancel.py`](../tests/test_app_cancel.py), 입력 신호는 [`test_runner_cancel.py`](../tests/test_runner_cancel.py), 연결 상한은 [`test_server_limits.py`](../tests/test_server_limits.py), 조회/의존 방향은 [`test_app_lean.py`](../tests/test_app_lean.py)에서 확인한다. 간결성 측정과 브라우저 취소의 한계는 [후속 기록](../docs/reviews/2026-09-24-lean-lifecycle/README.md)에 있다.
