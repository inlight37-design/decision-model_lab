# 재현한 발견과 수정의 경계

코드 링크는 제품 코드가 동일한 검토 head `a232de7`에 고정했다. 원장·응답·환경은 모두 synthetic fixture다. 아래의 재현 성공은 **결함이 고쳐졌다는 뜻이 아니라, 검토한 반례가 나타났다는 뜻**이다. [방법·원문 결과](EVIDENCE.md)를 함께 읽는다.

## AH-01 · P2 · 사람 판단 완료가 결과 판에 묶이지 않는다

**#101에서 추가된 문제.** [view의 reviewed](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/controller.py#L962)는 과거 `human_reviewed` 사건 하나라도 있으면 참이다. [mark_reviewed](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/controller.py#L1011)는 한 번만 사건을 남긴다. 반면 공개한 실행에는 합성을 반복할 수 있다.

- 재현: 합성 1 완료(seq 7) → 판단 완료(seq 8) → 다른 문장을 가진 합성 2 완료(seq 10). 새 결과를 본 사건은 없는데 `reviewed=true`, task=`done`이다.
- 영향: 새 답이 생겨도 ‘내 차례’로 돌아오지 않는다. 수용·봉인·호출 예산 우회는 아니다.
- 수정: 검토 사건에 결과 generation 또는 최신 합성 attempt/결과 사건 seq를 묶고 현재 결과와 비교한다. 새 테이블은 필수가 아니다. 사람이 “초안만 읽었다”는 뜻이라면 label도 그 범위로 좁혀야 한다.
- 완료 조건: 새 합성 뒤 재검토가 필요하고, 검토 사건을 다시 남길 수 있다. 동시에 종료가 확인된 형식 실패를 사람이 확인한 경우 어떤 조치가 남았는지도 명시한다.

반대 방향도 관측됐다. 합성 JSON 형식이 실패한 뒤 `mark_reviewed`는 성공하지만 [task projection의 failed 우선순위](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/roles.py#L51)로 task는 계속 `problem`이다. 독립적인 고심각도 결함으로 중복 계산하지 않고, 실행 종료·결과 실패·사람 확인을 구분할 같은 정리 과제로 본다.

증거: `controller-probe-results.json`의 `human_review_after_new_synthesis`, `failed_synthesis_reviewed`.

## AH-02 · P2 · 시작 전 폴더 오류가 queue 선두에 남는다

**main에도 존재.** [pump](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/controller.py#L532)는 queued 순회 중 `os.makedirs(work)`를 실행한다. [시작 실패 try](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/controller.py#L544)는 그 뒤에 시작하므로 mkdir 오류는 `_not_started`를 거치지 않는다. create_run의 원장 거래는 이미 끝난 상태다.

- 재현: 첫 participant 작업 디렉터리 자리에 일반 파일을 둔다. 첫 create_run은 FileExistsError로 끝나지만 run/queued는 남는다. 다른 질문의 create_run도 첫 queued를 만나 같은 오류가 난다. 두 실행 모두 queued, 실패 사건 없음, executor 실행 0회다.
- 영향: 하나의 경로 준비 실패가 다른 작업 진행까지 막는다. 역할판은 drafting 중 새 실행을 제한하므로 그 화면에서는 미정리 실행이 남는 형태이며, controller/API 반례에서는 다음 queue도 막힌다. 모델 호출이나 예산 누수는 관측하지 않았다.
- 수정: 폴더 준비를 기존 시작 전 실패 경계 안으로 옮기고 개별 참여자의 실패를 기록한다. 다른 참여자는 계속 진행한다. 전체 work_root 장애의 표시와 개별 경로 충돌은 구분한다.
- 완료 조건: 충돌 참여자는 시작 실패, 다른 정상 참여자는 진행, API/view는 생성된 run과 시작 실패를 추적할 수 있다. 일반 retry 엔진을 추가할 필요는 없다.

증거: `controller-probe-results.json`의 `filesystem_head_of_line`.

## AH-03 · P1 · Popen 이후 예외에서 프로세스 정리를 건너뛴다

**main에도 존재.** [runner._execute](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/core/runner.py#L358)는 Popen 성공 후 Tree와 IO thread를 만든다. `out.start`, `err.start`, `writer.start`는 이후 정상 정리로 연결되는 `try/finally` 밖에 있다.

- 조건: 자원 부족 등으로 프로세스 생성 후 Thread.start가 RuntimeError를 던진다.
- 재현: Popen/Tree를 대역으로 하고 reader.start만 실패시켰다. Popen 1회 뒤 `tree.kill=0`, `tree.close=0`으로 예외가 빠져나갔다. 실제 OS 자식이 남는 모습이나 실제 모델 실행을 관측한 것은 아니다.
- 영향: controller가 unknown으로 처리해 수용을 막는 것은 옳지만, 이미 시작한 실행에 runner가 정리 신호를 보내지 못한다. 서버 자체는 살아 있으므로 die-with-parent만으로 이 예외를 즉시 정리할 수 있다고 가정하면 안 된다.
- 수정: Popen 성공 직후부터 cleanup 책임을 보장한다. 실제 시작된 thread만 추적하고 예외 때도 제한 시간 안에서 terminate/reap/close를 시도한다. 정리가 확인되지 않으면 unknown과 진단을 반환한다.
- 완료 조건: reader·writer 시작 실패 각각에 cleanup이 시도되고, 정리 실패도 끝없이 기다리거나 성공으로 둔갑하지 않는다. 자동 재호출은 하지 않는다.

P1은 실제 피해 관측이나 흔한 발생이라는 뜻이 아니라 **시작한 호출의 수명 책임이 빠지는 경계라 먼저 고쳐야 한다**는 우선순위다. 증거: `core-probe-results.json`의 `R1-post-spawn-thread-failure`.

## AH-04 · P2 · 초안과 합성의 저장 보호가 다르다

**main에도 존재.** [초안 저장](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/controller.py#L625)은 `_storable_meta`를 적용하고 저장 실패를 분리한다. [합성 저장](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/controller.py#L889)은 `reported_models` 등을 그대로 사건에 넣는다.

- 재현: Claude 형식의 ASCII JSON에 `modelUsage={"m":{},"\ud800":{}}`를 넣었다. 실제 parser가 이를 읽고 요청 모델 `m`과 일치한다고 판단한다. 답 본문은 정상 합성 JSON, 입력 완료, 전체 자손 종료 확인도 참이다.
- 관측: 초안은 `escaped_text=true`로 정상 저장한다. 합성은 SQLite 문자열 저장에서 UnicodeEncodeError가 나서 started 사건만 남고 unknown, 사용 슬롯 1이 된다.
- 영향: 표시용 metadata 때문에 정상 본문 결과와 확인된 종료 기록을 저장하지 못해 사용자가 불필요한 종료 확인을 해야 한다. 실제 공급자가 이 metadata를 냈다는 주장은 아니다.
- 수정: 기존 메타 정규화와 최소 종료 진단 기록을 합성에도 적용한다. 인용·주장 원문을 임의로 바꾸지 않고, 공통화는 진단 메타와 저장 실패 처리로 좁힌다.
- 완료 조건: 같은 metadata가 양쪽에서 저장되고 escaped 여부가 남는다. 진짜 DB 쓰기 불능에서는 여전히 보수적으로 unknown을 유지한다.

DB 장애로 종료 증거를 보존할 수 없을 때 unknown은 결함이 아니다. 이 반례는 DB가 정상이고 초안에서는 이미 저장 가능한 입력을 합성에서만 놓치는 비대칭이다. 증거: `controller-probe-results.json`의 `synthesis_surrogate_metadata`.

## AH-05 · P2 · 상태 조회의 순서와 생성 성공이 분리되지 않는다

**polling은 main부터, 생성 후 안내 소실은 #101의 회귀.** [refresh](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/static/index.html#L1138)는 state와 quota를 Promise.all로 묶고 [1초 interval](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/static/index.html#L1196)로 돈다. mutation 뒤 refresh도 별도로 호출한다. 진행 중 요청 보호나 응답 generation 확인은 없다.

- 재현 A: 먼저 보낸 요청을 늦게 끝내면 `state=new → old`로 되돌아간다. quota만 실패해도 성공한 state 응답이 적용되지 않는다.
- 재현 B: [confirmRun](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/static/role-board.js#L107)의 POST 생성 성공 뒤 refresh를 실패시켰다. 모달과 preview 영수증은 이미 닫혀 있고, 없는 run의 task_id를 읽어 TypeError가 닫힌 formErr에만 쓰인다. 새 작업으로 이동하지 않는다. 기존 main의 startRun은 응답 run_id를 refresh 전에 선택했다.
- 영향: 실행 상태가 후퇴해 보이거나 이미 시작한 작업을 사용자가 다시 만들 수 있다. controller의 동일 run_id 방어는 유지되지만 새 preview는 다른 ID다. 이중 실제 과금이나 봉인 우회를 재현한 것은 아니다.
- 수정: 단일 polling 책임과 응답 순서를 보장한다. mutation 직후 조회 요구는 pending/generation으로 보존한다. quota 실패를 실행 상태 실패와 분리한다. POST 성공의 run_id는 즉시 저장하고, 조회가 실패해도 ‘시작됨, 상태 확인 중’ 안내와 복구 경로를 유지한다.
- 완료 조건: 역순 응답이 최신 화면을 덮지 않고, quota 장애에서 run은 갱신되며, 생성 성공 뒤 재조회 실패가 새 생성 재시도로 이어지지 않는다.

기존 JSON signature와 textarea focus 보호는 DOM 교체를 줄이는 좋은 처리다. 네트워크/JSON/SQL 작업을 막지는 않는다. 증거: `surface-results.json`의 JS 세 사례.

## AH-06 · P2 · 투영 비용이 전체 이력과 함께 늘어난다

**기본 구조는 main부터, 측정값은 #101 제품 코드 기준.** [view](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/controller.py#L915), [합성 이력](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/controller.py#L462), [model_synthesis 상태](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/controller.py#L1021)가 같은 사건 payload를 반복해서 읽는다. `_slots_used`와 `unsettled`도 전역 합성 이력을 각기 재구성한다.

- 재현: [README 측정표](README.md#효율-어디가-실제로-돌아가는가)의 100개 실행 fixture는 전체 조회 906 SELECT, 약 3.7 MB다. 한 실행 조회는 15 SELECT로 줄지만 전역 이력 두 번은 남는다. 단일 실행의 합성 이력 50개도 payload를 키운다.
- 영향: 데이터가 커지면 매초 응답·해석 비용이 커지고, view가 쥔 controller lock 동안 mutation/worker 결과 반영도 기다릴 수 있다. 실제 사용자 부하에서 대기 시간을 측정하지는 않았다.
- 수정: 한 요청에서 lifecycle snapshot을 한 번 만들고 필요한 projections에 전달한다. 목록은 요약, 상세는 선택 실행 위주로 읽는다. unknown의 전역 슬롯 계산은 빠뜨리지 않는다. 먼저 측정 후 필요하면 페이지/변경분 조회를 더한다.
- 완료 조건: 동일 fixture의 결과 의미를 보존하면서 반복 SQL/파싱이 줄고, 목록 payload가 원문 전체 이력에 비례하지 않는다. 캐시를 도입한다면 먼저 무효화/일관성 계약이 필요하지만 요청 단위 공유에는 그 새 문제가 없다.

상한·원장 교체가 있는 현재 실사용을 거대 fixture와 동일시하지 않는다. 이 지적은 벤치마크 점수보다 **같은 질문을 원장에 여러 번 묻는 경로를 단순화하자**는 것이다. 증거: `projection-results.json`.

## AH-07 · P2 · launcher 상태 파일의 소유권이 없다

**main에도 존재.** [serve의 read_state→starting](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/launch.py#L173)와 [main의 실패 저장](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/launch.py#L329)이 같은 owner lock/nonce 조건으로 묶이지 않는다. 원장 lock은 다른 층이다.

- 재현: 두 시작이 아직 시작 전 상태를 함께 읽게 했다. 첫 owner가 running으로 대기 중일 때 두 번째에 LedgerBusy를 주입하면 launcher.json이 `failed`, 두 번째 nonce로 바뀐다.
- 영향: 원장 동시 writer는 막지만 정상 서버의 status/url/stop 정보를 잃을 수 있다. 실제 프로세스 경쟁을 실행한 것은 아니며, 함수·임시 파일·thread로 순서를 재현했다.
- 수정: launcher root의 owner lock으로 시작부터 종료까지 소유권을 유지하고, 경쟁 호출은 기존 owner를 찾도록 한다. 실패/종료 상태 쓰기에는 owner nonce 확인을 둔다. stop도 소유자와 결속한다.
- 완료 조건: 동시 시작의 패자가 첫 서버 상태를 덮지 못하고, 두 호출 모두 살아 있는 서버를 정확히 찾거나 명확히 거절된다. 서버/원장 레이어를 새로 복제하지 않는다.

증거: `surface-results.json`의 `launcher_race`.

## AH-08 · P3 · 한 허가 판단에 서로 다른 manifest 판이 들어갈 수 있다

**main에도 존재.** [CliExecutor._check_eligible](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/cli_executor.py#L99)는 JSON을 읽어 적격성을 판단한 뒤 [registration.problem](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/registration.py#L75)에서 파일을 다시 읽어 digest를 확인한다. readiness도 같은 방식이다.

- 조건: 그 두 읽기 사이에 관측 파일이 다른 판으로 교체된다. 앱 HTTP에는 이 파일을 쓰는 경로가 없고, 통상 runbook은 새 날짜 기록을 만든다. 같은 OS 사용자의 쓰기 권한으로 기존 파일을 교체하는 좁은 경쟁 구간이 필요하다. 일반 UI 사용에서 자연 발생한다는 근거는 없다.
- 재현: A는 eligible이지만 현재 기기에 미등록, B는 기기에 등록됐지만 permission_conformance가 unknown이다. 적격성 계산 직후 A→B를 바꾸자 각 검사 결과가 결합되어 `_check_eligible`가 승인 반환했다. 임시 manifest/registry와 대역 fingerprint만 사용했다.
- 영향: 같은 관측 증거에 대한 적격성·등록이라는 보장이 한 호출 안에서 성립하지 않는다. 실제 모델 실행 우회를 재현한 것은 아니다. 전체 plan/run 시점의 재검사가 존재하므로 한 번의 경쟁 성공을 실제 실행 성공과 동일시하지 않는다.
- 수정: 각 검사 시점마다 raw bytes를 한 번 읽고 parse+SHA256 snapshot으로 묶어 두 검사에 전달한다. plan과 run의 재검사는 유지한다. 무기한 캐시가 해법은 아니다.
- 완료 조건: 교체 전 또는 후의 일관된 판 하나만 검사해 두 반례 모두 거절한다. 철회·날짜·버전·revision 재검증은 유지한다.

증거: `core-probe-results.json`의 `R2-split-manifest-snapshot`.

## 낮은 우선순위와 확장 전에 정리할 계약

| 항목 | 확인한 것 | 적절한 조치와 한계 |
|---|---|---|
| 예약 전 격리 검증 | CliExecutor.plan이 존재하지 않는 input에도 반환하고, 실제 격리 거절은 예약 후 발생 가능. 임시 controller에서 reservation 1, rejected/process_failed_to_start를 관측(`R4`) | 이미 알 수 있는 경계 오류는 plan에서 거절. 실행 직전 재검사는 유지. 무환불 정책을 바꾸자는 뜻이 아니며 실제 Linux 격리는 대역이었다 |
| Plan의 얕은 불변성 | record.template 변경이 원 Plan.template에도 반영되고 Sandbox.env 변경은 revision에 안 들어감(`R3`) | 입력 mapping 불변화/복사와 record 사본, 실행 의미를 바꾸는 허용 env의 revision 포함 여부를 정의. 현재 UI 입력으로 조작 가능한 경로를 발견한 것은 아님 |
| 없는 decision-report | 없는 run에서 `/report`는 409지만 [decision-report](https://github.com/inlight37-design/decision-model_lab/blob/a232de7d4ae7de097dd014be5a791348b7881ea3/app/server.py#L182)는 runs[0]의 IndexError(`surface` 결과) | 공통 단일 run 검사 순서를 맞춰 404/409로 반환. 실제 HTTP listener를 띄운 재현은 아님 |
| headless 자료 읽기 | `app.run`은 read_text 뒤 controller의 자료 제한을 적용 | 대형 파일을 읽기 전에 count/size 제한. 이번에 메모리 부하 실험은 하지 않음 |
| 설정 helper 위치 | `app.run`이 `app.server`에서 공통 설정을 import | 입구 설정을 실제 손볼 때 작은 공용 모듈로 이동. 파일 분할 자체를 위한 작업은 낮은 우선순위 |
| 호환 재노출 | core.adapters의 환경 helper 재노출 중 현행 도구 사용자 존재 | 사용처를 canonical core.env로 옮긴 뒤 제거. 오래됐다는 이유만으로 삭제하지 않음 |

헤드리스 exit 0은 “공개됐고 요청 합성을 모두 시도함”이라는 명시된 계약이다. 합성 품질까지 성공했다는 뜻이 아니므로 이것을 즉시 버그로 분류하지 않았다. 성공한 합성이 필요한 자동화는 결과 JSON을 판단하거나 별도 엄격한 결과 계약이 필요하다.
