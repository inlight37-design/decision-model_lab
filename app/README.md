# app — A1 controller와 모의 화면

**모델을 부르지 않는 모의 모드**의 첫 세로 기능이다(인계 4절 1). 흐름은 한 줄이다.

고정 입력(질문 → 프롬프트, sha256) → 시도 예약 → 실행 → 결과 수용 관문 → 초안 봉인 → controller가 공개 → 카드

| 파일 | 하는 일 |
|---|---|
| [`controller.py`](controller.py) | 상태를 가진 유일한 곳. 자리·예산, 결과 수용 관문, 봉인과 공개, 수동 참여자, 다시 시작, 화면용 투영 |
| [`store.py`](store.py) | 작은 SQLite journal. 사건은 덧붙이기만 한다. 초안도 여기에 봉인한다 |
| [`fake_cli.py`](fake_cli.py) | Claude·Codex 출력 형식을 흉내 내는 가짜 CLI. 행동: 정상, 느림, CLI 오류, 입력 일부만 읽음, 멈춤 |
| [`server.py`](server.py) | 127.0.0.1 화면 서버. 모든 `/api` 요청에 토큰 |
| [`static/index.html`](static/index.html) | 화면. [Ledger](../design/README.md)의 토큰과 규칙을 따른다 |

## 실행

```bash
python -m app.server --port 8765
```

출력된 주소(`http://127.0.0.1:8765/#token=…`)를 연다. 데이터는 `~/.decision-model-lab/mock/`(journal과 토큰 파일)에 쌓인다. 모의 CLI는 Windows에서는 job object로, Linux·WSL2에서는 [`core.isolation`](../core/isolation.py)의 bubblewrap으로 실행한다. 그래서 결과 수용 관문이 실제 종료 확인을 받는다. bubblewrap을 못 쓰는 Linux에서는 종료를 확인하지 못해 결과가 `unknown`으로 남는다 — 의도한 동작이다.

## 참여자 두 종류

- **CLI(자동).** 지금은 모의 CLI만 있다. 실제 CLI 실행기는 실제 호출 전 확인 단계에서 붙인다.
- **원본 앱(수동).** ChatGPT·Claude·Antigravity 앱에서 사용자가 직접 돌린다.
  1. 화면이 질문을 복사해 준다.
  2. 사용자가 원본 앱에 붙여 넣고, 받은 답을 화면에 붙여 넣는다.
  3. controller가 답을 받기 전에 확인하는 것: 입력 sha256이 이 실행의 것과 같은지, 늦게 온 답이나 중복 제출이 아닌지.
     - **주의:** 화면은 그 카드가 속한 실행의 sha256을 자동으로 넣어 보낸다. 그래서 이 검사는 **다른 실행에 잘못 넣는 것**만 막는다. 사용자가 원본 앱에 정말 그 질문을 넣었는지는 확인하지 못하고, 사용자의 확인에 기댄다(인계 4절 K 표).
  - 원본 앱의 기능(메모리, 컴퓨터 사용, 세션 기능)을 그대로 쓰는 대신, blind와 사용량은 "관측 안 됨"으로 표시한다. 원본 앱의 메모리나 다른 대화를 이 앱이 통제하지 못하기 때문이다.

## 지키는 규칙

- **결과 수용.** 받으려면 셋이 모두 맞아야 한다: `interpret()`의 ok, 입력 전달 `complete`, 자손 전체 종료 확인.
  - 종료를 확인하지 못하면 `unknown`이다. 초안을 받지 않고 실행 자리를 풀지 않으며, 다시 부르지 않는다.
  - 사용자가 "종료를 직접 확인했음"을 누르면 자리만 푼다. 예산은 돌려받지 않는다.
- **봉인.** 공개 전에는 초안의 내용·길이·digest, 토큰 수, 걸린 시간을 화면에 넘기지 않는다(Ledger BlindBarrier).
- **공개.** 화면에 공개 버튼이 없다. 남은 참여자가 모두 끝났고 정족수가 있으면 controller가 연다.
  - 누가 빠졌으면 자동으로 진행하지 않고 사용자의 **축소 승인**을 기다린다.
  - 정족수가 모자라면 승인해도 열지 않는다. 유료로 채우지 않는다.
- **자리와 상한.** 동시 실행 자리는 `running`과 `unknown`이 차지한다. 정리되지 않은 시도(`unknown` + `runner.lingering()`)가 상한에 닿으면 새 시도를 시작하지 않는다.
- **다시 시작.** 이전 controller가 돌리던 시도는 `unknown`이 된다. 다시 부르지 않는다.
- **제어 API.** 참여자는 격리 안에서도 localhost를 공유한다. 그래서 모든 `/api` 요청(읽기 포함)에 토큰을 요구하고, Host 머리글이 우리 주소가 아니면 거절한다.
  - 토큰은 URL의 `#` 뒤로만 브라우저에 준다. 페이지 자체에는 토큰이 없다.
  - 토큰 파일은 controller 데이터 폴더에 있고, 이 폴더는 참여자 격리에 연결하지 않는다(`never`).

## 아직 없는 것

- 실제 CLI 실행기(`env.resolve` → `build_spec` → `isolation.run`과 `cli_mounts`). 모델 호출 전 확인 단계에서 붙인다.
- 합성, 주장 대조, 첫 화면 Q4(결정 우선·대조표 우선) 비교. 초안 공개까지만 있다.
- 취소 버튼과 취소 중 입력 전송 시험.
- TypeScript 화면. node가 없어서 지금은 빌드 없는 HTML·JS다.
- 입력 manifest의 공통 자료(파일) 첨부. 지금은 질문 한 개다.

검사: [`tests/test_app_controller.py`](../tests/test_app_controller.py). 대부분은 프로세스 없는 합성 실행기로 보고, 한 묶음은 모의 CLI를 실제 실행 경로(Windows job object, Linux bubblewrap)로 돌린다.
