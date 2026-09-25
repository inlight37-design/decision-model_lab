# app — controller·원장·명시적 CLI 연결

기본은 **모델 호출 없는 모의 모드**다. 실제 구독 CLI는 Linux/WSL에서 `--live-cli`(단일) 또는 `--live-config`(명시적 provider 설정)로만 연결한다. 자동 모델·provider·유료 API 대체는 없다. Windows 수정·실제 계정 한도·구독 CLI 병렬 응답은 [직접 관측 기록](../docs/reviews/2026-09-24-windows-live-completion/README.md), 앞선 구현은 [PR #38 기록](../docs/reviews/2026-09-24-cli-unblock/README.md)에 있다.

고정 입력(공통 자료 포함) → 계획·시도 예약 → 실행 → 결과 수용 → 초안 봉인 → controller 공개 → 모의 발췌 대조 또는 실행마다 켜는 실제 합성 1회(원문 인용 대조) → 조건부 카드/JSON 보고의 흐름이다. 의미상 합의 판정·외부 사실 검증은 없다.

## 파일과 책임

| 파일 | 책임 |
|---|---|
| [controller.py](controller.py) | 상태 전이·원자적 예약·자리/상한·수용·봉인/공개·취소/재시작·화면 투영 |
| [store.py](store.py) | SQLite 원장, 배타 잠금, 스키마 이전, 첫 호출 상한 고정, 실행별 공통 자료 |
| [state.py](state.py) | 참여자 행에서 정족수·축소 승인·공개 가능 여부 계산, 합성 사건을 시도별 상태로 투영해 자리·복구·화면이 함께 사용 |
| [cli_executor.py](cli_executor.py) | provider별 입력·inventory로 최종 계획을 만들고 같은 계획을 기존 격리 경계에서 실행 |
| [live_config.py](live_config.py) | 명시적 provider 설정 파싱·검사. 새 실행 엔진이 아님 |
| [codex_account.py](codex_account.py), [account_quota.py](account_quota.py) | 격리된 무모델 계정 조회·명시적 갱신·캐시/오래된 관측 표시 |
| [server.py](server.py) | localhost API·인증·전체 준비 조회·화면 연결 |
| [report.py](report.py), [synthesis.py](synthesis.py) | 공개 원문의 허용 목록 투영, 모의 발췌/참조 검사, 실제 합성의 질문 만들기와 인용 대조(이 파일들은 모델을 부르지 않는다) |
| [fake_cli.py](fake_cli.py), [static/index.html](static/index.html) | 가짜 CLI와 빌드 없는 HTML/JS 화면 |

## 모의 실행과 화면

```bash
python -m app.server --port 8765 --data-dir /path/new-mock-ledger
```

출력된 `http://127.0.0.1:8765/#token=...` 주소를 연다. 질문·참여자·최소 인원·정족수 정책을 고르고 시작한다. 모의 CLI는 실제 공급자를 부르지 않는다. 원본 앱 참여는 질문 복사→사용자가 외부 앱에서 받은 답 붙여넣기이며 화면 자동화는 없다.

수동 질문의 첫 줄에는 실행/참여자/입력 해시 표식이 있고 답에서 되말하도록 안내한다. 다른 실행·참여자 표식, 잘못된 입력 해시, 중복·늦은 제출, 빈 답은 거절한다. 올바른 표식과 사용자 확인은 독립성 증명이 아니다. 공개 전에는 초안 내용·길이·토큰 수·시간·모델 보고를 내보내지 않으며 오류 자유 텍스트는 모든 참여자가 끝난 뒤에만 보인다.

`independent_only`는 독립성이 확인된 참여자만 정족수에 센다. `include_unverified`는 미확인 CLI·수동 앱 답도 세지만 독립 정족수 충족이라고 표시하지 않는다. 정책은 실행마다 고정되며 재시작으로 바뀌지 않는다. 자료·사용자 문맥이 미확인인 답을 전송 방식이 CLI라는 이유로 confirmed로 표시하지 않는다.

## 단일 실제 CLI와 준비 조회

```bash
# 서버/원장/CLI/모델을 시작하지 않는 준비 조회
python -m app.server --check-cli codex --model <전체-요청-모델> --inventory <관측-json> --input-dir <빈-입력-폴더> --data-dir <원장> --allow-context-unverified
# 준비 조회가 현재 설치판·계획에서 허용됐을 때만
python -m app.server --live-cli codex --model <전체-요청-모델> --inventory <관측-json> --input-dir <빈-입력-폴더> --data-dir <원장> --allow-context-unverified --call-budget 1 --timeout 180
```

위 모델/경로는 자리표시자이며 실제 관측값을 쓴다. 지금 계획은 입력 폴더 하나의 `codex@bba3751a36f3`·`claude-code@a35129c5a1dc`(E2)이고, 그 [관측 manifest](../docs/reviews/2026-09-25-context-independence/manifest.v2.json)로 aux-pc-wsl에서는 `--allow-context-unverified` 없이도(strict) 준비 조회가 허가됐다. 옛 계획 `codex@8a0128d4c791`(K46)·`codex@5a77e0b7dc7f`(연결 앱 끄기)·`claude-code@126be128bed7`(#39)의 기록으로는 지금 계획이 거절된다. 자료 없음/복수 폴더는 다른 판이다. 과거 [첫 실측](../docs/reviews/2026-09-24-live-cli-pilot/README.md)과 [재현](../docs/reviews/2026-09-24-live-pilot-replication/README.md)은 그대로 보존하며 소진 원장을 다시 쓸 목적으로 상한을 바꾸지 않는다.

준비 조회의 종료 코드는 허가 0, 거절 3이다. 명령줄 인자 오류는 argparse의 2라서 스크립트가 거절과 가를 수 있다. 실제 모드(`--live-cli`·`--live-config`)도 시작 전 준비 조회가 거절하면 3으로 끝나고 서버를 띄우지 않는다.

서버 기동 자체는 질문을 시작하지 않는다. 화면에서 시작하면 실제 구독 사용량을 쓴다. 준비 조회는 실행 승인/계정 잔여나 현재 namespace 생성 가능성의 증명이 아니다. 실행기는 시작 직전에 같은 최종 계획의 허가를 다시 계산한다.

`--allow-context-unverified`는 문맥 기록(C3)이 없거나 판이 맞지 않는 기기에서 쓰는 명시적 예외다. C3 의미상 합격만 실행 필수 조건에서 제외한다. 설치·구독·전송·권한·판/버전/날짜 검사는 유지하고 결과를 독립 정족수에 세지 않는다. 관련 옵션만 주고 실제 모드를 생략하면 모의 모드로 조용히 대체하지 않고 거절한다. 실제 실행은 별도 명시적 원장을 사용한다.

## provider별 설정과 동시 실행

설정은 다음처럼 각 provider의 전체 모델 이름·관측 기록·입력 폴더·최대 시작 예약 수를 명시한다. 상대 경로는 JSON 파일 위치를 기준으로 한다. 지원 provider는 `codex`와 `claude-code`이며 중복·오타·불리언 상한·빈 모델 이름을 거절한다.

```json
{
  "providers": [
    {"adapter_id":"codex", "model":"<관측한-모델>", "inventory":"codex.json", "input_dir":"codex-empty", "call_budget":1},
    {"adapter_id":"claude-code", "model":"<관측한-모델>", "inventory":"claude.json", "input_dir":"claude-empty", "call_budget":1}
  ]
}
```

```bash
python -m app.server --check-config /path/live.json --data-dir /path/new-ledger --allow-context-unverified
python -m app.server --live-config /path/live.json --data-dir /path/new-ledger --allow-context-unverified --timeout 180
```

양쪽 준비 조회를 모두 통과해야 서버를 시작한다. 한쪽이 막혔다고 자동으로 빼거나 다른 모델을 넣지 않는다. 두 provider를 설정하면 두 실행 자리와 provider별 상한을 둔다. 각 상한은 1..10, 전체 합은 최대 10이다. 기존 controller의 스레드와 봉인/공개 관문을 재사용한다. 한쪽 초안이 먼저 끝나도 다른 쪽이 진행 중이면 공개하지 않는다.

**실제 Codex·Claude 동시 응답을 별도 상한 원장에서 수용·공개했다.** 현재 Claude는 stream-json/verbose로 init과 최종 결과를 함께 검사한다. 한 입력 폴더의 `claude-code@126be128bed7`에서 Read만 노출, MCP 없음, dontAsk와 금지된 합성 peer 파일의 Read 거절을 새로 관측했다. no-input/다른 옵션 판의 권한까지 입증한 것은 아니다. Codex 참여자는 계정의 연결 앱(`-c features.apps=false`)을 끈 계획이며, 그 판 `codex@5a77e0b7dc7f`의 K46을 다시 관측했다([연결 앱 끄기 기록](../docs/reviews/2026-09-24-codex-apps-off/README.md)). 지금 쓰는 [관측 manifest](../docs/reviews/2026-09-24-codex-apps-off/manifest.v2.json)를 두 설정에 쓰되 각자 빈 입력 폴더 하나가 필요하고, 설치판·관측일·계획이 바뀌면 준비 조회를 다시 한다. 연결 앱을 켠 옛 계획의 [#39 manifest](../docs/reviews/2026-09-24-windows-live-completion/manifest.v2.json)로는 지금 Codex 계획이 거절된다. 그때는 문맥 독립성이 미확인이라 실제 실험이 명시적 `include_unverified` 정책을 썼다.

**E2(2026-09-25)에서 두 참여자 계획의 문맥 통로를 좁히고 문맥 기록(C3)을 관측했다**([기록](../docs/reviews/2026-09-25-context-independence/README.md)). Claude는 `--restricted --safe-mode`, Codex는 모델의 명령에게 `~/.codex` 전체를 막고 실행 파일을 격리 안 `/opt/dml-codex`에서 돌리며 `-c project_doc_max_bytes=0`으로 작업 폴더 AGENTS.md를 싣지 않는다. `~/.codex`에 비어 있지 않은 AGENTS.md·AGENTS.override.md가 있으면 실행기가 시작 전에 거절한다. 작업 폴더의 지시문 파일로 한 양성·음성 행동 대조와 모델 없는 입력 렌더링을 근거로 [새 manifest](../docs/reviews/2026-09-25-context-independence/manifest.v2.json)는 두 provider의 C3를 observed로 적었고, 앱의 준비 조회가 strict에서 두 provider를 허가했다(모델 호출 없음). 이 판정은 그 PC·판·설치판·30일에 묶이고, 최종 요청 전체를 본 것은 아니다. 같은 날 앱에서 strict 정책으로 두 참여자를 부른 [첫 실제 실행](../docs/reviews/2026-09-25-strict-live-run/README.md)이 독립 정족수를 채웠고(Codex 합성 포함), 실제 CLI 중도 취소도 자손 종료 확인과 함께 끝났다.

## 공통 자료

실행을 만들 때 텍스트 파일을 붙이면(화면의 “공통 자료”, API의 `sources: [{name, text}]`) controller가 내용·크기·sha256을 원장(스키마 7)에 고정하고 목록을 질문 본문에 넣는다. 그래서 입력 digest가 모든 파일을 묶는다. 이름은 영문·숫자·점·밑줄·하이픈, 파일 20개·파일당 256 KiB·합계 1 MiB까지다. 화면은 파일 이름의 다른 글자를 `_`로 바꾼다. 서버는 끝이 점인 이름·장치 이름·경로 구분자·대소문자 중복도 거절한다.

시도마다 원장의 사본을 데이터 폴더 밖(`<work_root>/_sources/<run>`)에 두고 목록·크기·sha256을 다시 맞춘다. 다르면 그 시도를 시작 전에 거절한다. 자료 목록과 제공 폴더가 원래 고정 질문에 적힌 것과 같은지도 계획·예약 전에 확인한다. 복원 시 `work_root`만 바꾸어 옛 질문으로 다른 폴더를 주지 않는다. 기존 경로로 복원하거나 새 실행을 만들며 원래 질문을 덮어쓰지 않는다. CLI 참여자는 provider별 빈 입력 폴더 대신 이 폴더 하나를 읽기 전용으로 받으므로 계획의 판(입력 폴더 하나)이 그대로다. 수동 참여자는 같은 목록을 받지만 파일 첨부 여부는 확인하지 못한다(K21). 시도 도중의 바꿔치기(K14)는 막지 못한다. 실제 확인은 [공통 자료 기록](../docs/reviews/2026-09-24-source-snapshot/README.md)에 있다.

## 회계와 원장

스키마 6은 첫 전체·provider별 상한을 `live_budget`에 저장한다. 첫 호출 전에 고정되며 다른 상한으로 다시 켜면 거절한다. 상한 옵션을 생략해도 저장된 값을 읽는다. 구형 원장은 기존 예약의 일관된 cap으로 복원하고 모순된 이력은 거절한다. 기존 사건·초안을 지우지 않는다. 새 스키마로 열기 전 백업하며 하향 이전은 없다.

화면의 **CLI 실행·진행**은 구독 차감량이 아니다. 시작 전 거절은 실행 수에서 빼고 별도 표시한다. **실제 CLI 예약**은 시작 전 원장에 남기는 보수적인 상한이며 실패·취소·재시작으로 환불하지 않는다. 예약 뒤 시작 직전 허가가 철회됐다면 예약은 남고 실제 시작은 0이다. provider 간 예산은 빌려 쓰지 못한다. CLI 토큰과 계정 한도도 별개다.

원장 하나를 여는 controller는 하나다. 같은 데이터 폴더를 다른 포트에서 열어도 잠금에서 멈춘다. 상태 변경은 기대한 상태·시도 ID에 조건을 걸며 늦은 결과는 사건만 남긴다. 스키마 4는 공개 단계, 5는 시도 실행 종류를 이전했으며 과거 실행을 현재 붙은 실행기로 추정하지 않는다. 근거 없는 옛 실행 종류는 미기록으로 표시한다.

## 수용·취소·재시작

초안은 자손 전체 종료 확인, interpret 성공, stdin 끝까지 전달(`complete`), 비어 있지 않은 답, 보고된 모델의 명시적 불일치 없음이 모두 충족돼야 받는다. 모델 보고가 없으면 미확인이며 요청 이름으로 채우지 않는다. 실패·누락은 거절하며 자동 재호출하지 않는다.

`running`·`unknown`이 자리를 차지하고 정리되지 않은 시도가 상한에 닿으면 새 실행을 막는다. 재시작 당시 running은 unknown이며 다시 부르지 않는다. 사용자의 종료 확인은 자리만 풀고 예산을 환불하거나 답을 수용하지 않는다. queued 작업은 명시적 재개까지 멈춘다.

실제 합성도 같은 pause·병렬 자리·미종료 상한을 따른다. 시작 사건이 있으면 성공·실패·재시작 뒤에도 같은 실행에서 재호출하지 않는다. 합성의 종료 미확인은 사건에 남아 재시작 뒤에도 자리를 차지한다. 화면의 종료 확인 또는 인증된 `POST /api/runs/<run_id>/acknowledge-synthesis`에 `{"attempt": "<시도 ID>"}`를 보내면 해당 미확인 시도의 자리만 푼다. 종료를 실제로 확인한 사용자의 선언이지 서버가 외부 프로세스를 검사하는 기능이 아니다. 다른 시도 ID·중복 확인은 거절하며 환불·재시도는 없다. `wait_idle()`도 합성 작업을 포함한다.

초안 작성 중 취소는 원장에 먼저 저장한 뒤 worker에 신호를 보낸다. API 성공은 취소 요청 저장이지 자손 종료 확인이 아니다. 시작 전 대기는 거절하고, 이미 시작된 취소/실패/종료 미확인은 환불하지 않는다. 늦은 정상 답도 버린다. 기존 봉인 초안은 비공개로 보존하며 수동 답·축소 승인·보고/공개는 막는다. 이미 공개된 실행을 다시 숨기는 취소는 없다. 원본 앱 작업은 별도 중단이 필요하다.

공개는 controller가 상태 변경과 같은 거래에서 결정한다. 참여자가 빠지면 자동 축소하지 않고 명시적 축소 승인을 기다리며, 최소 정족수가 안 되면 승인해도 공개하지 않는다. 서버·자손은 작업한 세션이 종료 확인 후 정리한다.

## API·보고·모의 합성

모든 `/api` 읽기/쓰기는 토큰이 필요하다. 토큰은 URL fragment로만 전달하고 페이지에 포함하지 않는다. Host·Origin 검사, JSON 타입·본문 크기·framing 검사, 프레임 삽입 차단을 유지한다. 인증 전 연결도 상한과 I/O 기한을 적용하지만 CPU/메모리 전체 제한은 아니다. 원장은 참여자의 `never` 경로이며 토큰 파일은 POSIX 0600, 데이터 폴더는 0700이다. localhost 네트워크 공유를 파일 격리만으로 안전하다고 가정하지 않는다.

공개 뒤 `GET /api/runs/<run_id>/report`는 `a1-draft-report/4` 원문 보고다. 질문/입력 해시, 공통 자료 목록(이름·크기·sha256), 초안/해시, 출처·독립성·시도 종류, 정책·탈락·축소 승인·회계를 내보낸다. 보고의 회계는 실행 원장의 값이다. 계정 전체 잔여는 아래 별도 계정 API와 화면에서 관측 시각을 붙여 제공하며 과거 실행의 사용량으로 소급하지 않는다. 해시 불일치·초안 누락·공개 전 요청은 거절한다. 원문이 들어가므로 공개 저장소에 자동 업로드하지 않는다.

`POST /api/runs/<run_id>/synthesize`(본문 없음 또는 `{"mode": "mock"}`)는 공개 원문의 줄을 발췌·중복 묶기하고 참조 위치만 검사한다. 모델 호출·외부 사실 검증은 없고 주장은 unresolved, 카드는 qualified다. 실패하면 unavailable과 원문 보고를 남긴다.

`{"mode": "model", "adapter_id": …}`는 **실제 합성 1회**다(실제 CLI 연결에서만, 실행마다 사용자가 켠다). 공개 초안을 이름표 D1·D2로 바꿔 그 실행의 CLI provider 하나에 참여자와 같은 계획으로 보내고, 같은 원장의 전체·provider 상한에서 예약한다. 답의 인용은 초안에 글자 그대로 있어야 원문 일치이고, 일치하는 인용이 없는 주장은 추가 주장으로 표시되지만, 이는 **일치 인용을 확보하지 못했다**는 뜻이다. 바꿔 쓴 문장이 원문에 없는 사실인지 판정한 것은 아니다. 모든 주장은 미해결이며 사실 검증은 없다. 실패하면 원문 보고와 모의 대조표를 쓰고 시작한 호출은 환불하지 않는다([실제 합성 기록](../docs/reviews/2026-09-24-model-synthesis/README.md)). 형식 검사에 실패한 합성 답의 원문은 지금 원장에 남지 않고 이유만 남는다. 합성 질문의 이름표는 참여자 ID 순이라 D1이 늘 Claude 초안이다. 둘 다 [D 후속 비교](../docs/experiments/2026-09-25-d-followup/RESULTS.md)에서 드러났고 [카드 #66](https://github.com/inlight37-design/decision-model_lab/issues/66)이 다룬다.

결정 보고는 `GET /api/runs/<run_id>/decision-report`의 `a1-decision-report/2`이며 합성의 `schema`(모의 `a1-mock-synthesis/1`, 실제 `a1-model-synthesis/1`)로 종류를 가른다. Q4의 A 결정 우선/B 대조표 우선은 같은 결과의 표시 순서만 바꾸며 사용자 선호를 확정하지 않는다.

## 계정 한도와 문맥 진단

`python tools/w2/codex_account.py`는 `app/codex_account.py`의 진단 진입점이며 기본은 무프로세스 계획 조회다. 사용자 PC에서 명시적으로 `--probe --data-dir <원장>`을 주면 기존 Linux 격리 안의 Codex app-server로 계정 메타데이터를 조회한다. 질문·로그인 변경·유료 API 대체·추가 크레딧 요청은 없고, 식별자·인증 값·원시 프로토콜은 내보내지 않는다. 시간/출력 제한과 자손 종료 확인을 적용한다. 사용자 WSL의 native Codex에서 실제 구독 계정 응답과 화면 연결을 확인했다. 실행 파일의 symlink 대상이 격리에 연결되는 경로와 자식 실행 경로가 달랐던 오류도 수정했다.

화면의 **조회** 또는 인증된 `POST /api/account-quota/refresh`만 프로세스를 시작한다. `GET /api/account-quota`는 캐시만 읽으며, 동시 갱신은 합치고 재조회는 60초 간격으로 제한한다. 120초 초과·초기화 시각 경과·조회 실패는 과거 관측값으로 표시한다. 없는 값은 미확인이며, 모델 호출이나 추가 크레딧 사용은 없다.

같은 조회가 `model/list`(추론 없음)로 이 계정의 가용 모델 이름도 받는다. 화면은 설정한 Codex 모델이 그 목록에 있는지만 보인다. 가용 목록이지 실제로 답한 모델의 보고가 아니다(K32). 목록 메서드만 거절되면 한도는 그대로 두고 목록을 미확인으로 둔다. 시간 초과·서버 요청·에이전트 활동은 여전히 조회 전체를 멈춘다. 표시 이름·설명은 버린다.

Claude에는 따로 조회할 통로를 쓰지 않는다. 실제 Claude 참여자의 stream-json에 오는 `rate_limit_event`에서 상태(`allowed`·`allowed_warning`·`rejected`)와 창별 사용 비율(0–1)·초기화 시각만 남기고, 결제·크레딧 칸은 버린다. 마지막 사건의 모양이 다르면 미확인으로 취급하고 답 수용과 분리하는 것이 계약이다. 극단적으로 큰 JSON 정수가 파서를 중단하던 경계는 [후속 감사](../docs/reviews/2026-09-25-runtime-audit-finish/README.md)가 재현했고 [병합 검토](../docs/reviews/2026-09-25-merge-46-47/README.md)에서 고쳤다. 같은 검토에서 시도 결과의 사용량 칸도 NaN·무한대·음수·불리언을 버리게 했다 — 그런 값 하나가 화면 응답 전체를 깨뜨렸다. 계정 패널은 **마지막으로 끝난 실제 실행**의 값만 보인다 — 봉인 중인 실행의 값은 계정 비율의 변화로 초안 길이를 짐작하게 하므로 내보내지 않고, 모의·합성 실행기의 값은 계정 값이 아니므로 쓰지 않는다. 비율은 사용 %로 보일 뿐 Codex 값과 더하지 않는다.

계정 한도 창 사용 비율을 남은 토큰·질문 횟수로 환산하지 않는다. 제공 모델 재지정 사건이나 최소 설정 프로필은 [한계 재검토](../docs/reviews/2026-09-24-cli-unblock/README.md)의 후속 후보다. 문맥 비노출이나 모델 자기 보고를 개인 문맥 부재의 증명으로 삼지 않는다. 관측 없이 C3/permission을 합격으로 바꾸거나 새 옵션을 기존 판에 섞지 않는다.

## 검사와 남은 범위

`python -m unittest discover -s tests -v`를 실행한다. Linux 격리 검증은 `DML_REQUIRE_BWRAP=1`을 사용하며 OS 전용 skip을 구분한다. 실제 JavaScript 함수 회귀에는 Node가 필요하다. 테스트 파일은 `test_cli_unblock.py`, `test_live_config.py`, `test_codex_account.py`와 기존 `test_app_*.py`, `test_runner_cancel.py`, `test_server_limits.py`를 본다.

Windows stdout 수정과 Python 3.13/짧은 임시 경로 회귀를 반영했다. 교차 플랫폼 CI의 정확한 head 결과는 PR Checks가 기준이다. 사용자 PC에서의 두 provider 응답·현재 Claude 판의 제한된 권한 증거·계정 한도 화면·공통 자료·실제 합성은 각 날짜의 관측 기록에 있다. 이를 새 웹 세션이 재실측한 것은 아니다. 남은 것은 원본 앱 사용량 비교, Q3 TypeScript와 접근성 전수 검사, 공통 자료 합계 1 MiB의 실제 확인이다. 파일 수 상한과 긴 파일은 [긴 자료 실험](../docs/experiments/2026-09-25-long-sources/RESULTS.md)에서, 합성자를 Codex로 바꾼 비교·조건이 충돌하는 과제·blind 채점은 [D 후속 비교](../docs/experiments/2026-09-25-d-followup/RESULTS.md)에서 한 번씩 봤다. 짧은 자료 속 지시문(숨긴 지시, `AGENTS.md`·`CLAUDE.md` 이름의 자료)은 [한 번 시험](../docs/experiments/2026-09-25-source-injection/RESULTS.md)해 두 참여자 모두 따르지 않았다. strict 두 참여자 실행과 실제 중도 취소는 [2026-09-25 기록](../docs/reviews/2026-09-25-strict-live-run/README.md)에 있다. 문맥 독립성(C3)은 [E2 기록](../docs/reviews/2026-09-25-context-independence/README.md)의 범위에서 관측됐다. [후속 감사](../docs/reviews/2026-09-25-runtime-audit-finish/README.md)가 원격 미반영으로 남긴 사용량 파서는 [병합 검토](../docs/reviews/2026-09-25-merge-46-47/README.md)에서 반영했다.
