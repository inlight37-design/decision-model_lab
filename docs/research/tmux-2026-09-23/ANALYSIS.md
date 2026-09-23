# tmux에서 가져올 설계와 가져오지 않을 실행 방식

작성: ChatGPT (GPT-6 Astra Pro) · 2026-09-23. 프로젝트 기준 `cd94190bf10b1bacc812ee698e4c6dc6a86260ca`; tmux 기준 3.7c의 `e476c1230b958df0cb12977517d24b3dc931375b`. T/P 참조의 원문·위치·한계는 [EVIDENCE.md](EVIDENCE.md)에 있다. 아래 **프로젝트 제안은 구현 완료나 사용자 확정 결정이 아니다.**

## 1. 먼저 구분할 것: tmux는 무엇을 해결하는가

tmux는 프로그램의 터미널을 server가 유지하고, client가 붙었다 떨어지며 화면을 보는 도구다. pane은 PTY이고, window/session은 이를 배치·묶는 단위다. control mode에서는 사람이 키를 누르는 대신 다른 프로그램이 tmux 명령과 알림을 주고받을 수 있다. 핵심 가치는 분할 화면 자체보다 **실행 객체가 특정 화면 연결보다 오래 살 수 있는 구조**에 있다. [T02·T03·T10]

우리 프로젝트의 핵심은 다르다. 구독 CLI의 동일 입력·권한·독립성을 관리하고, 수용할 수 있는 답만 봉인하며, 정족수와 공개 순서를 판정한다. terminal pane이 존재한다는 사실로는 이 판단을 할 수 없다. tmux를 사용해도 판단·원장·격리의 책임은 controller에 남아야 한다. [P01–P07, 설계 판단]

### 현재 코드에 이미 있는 것

| 개념 | 현재 상태 | tmux 조사로 추가할 수 있는 것 |
|---|---|---|
| 화면과 controller 분리 | HTTP 화면과 Python controller가 이미 분리돼 있음 | 재접속 상태를 실행 상태와 더 명확히 분리하는 UX·시험 |
| 원장 단일 소유권 | Store의 OS 파일 잠금이 있음 | tmux wait channel로 바꾸지 않고 유지 |
| 정확한 완료 수용 | `_verdict()`가 입력 complete·빈 답·모델 불일치·자손 종료를 검사 | tmux 알림을 연결하더라도 이 관문을 우회하지 않는 계약 |
| 늦은 완료 방지 | RUNNING과 attempt에 조건부 갱신 | 향후 외부 세션 연결에는 transport identity를 별도로 둘 수 있음 |
| 재시작 | 복구와 queued 명시적 재개가 있음 | 화면 재접속과 controller 재시작의 구분을 사용자가 이해하도록 표시 |
| 봉인·예산·실패 기록 | 수정된 허용 목록 투영과 SQLite 기록이 있음 | 상태 탐색·필요한 항목만 갱신·실패 위치로 이동 |

앞선 A1 리뷰의 누락을 현행 미수정 결함으로 다시 적지 않는다. 이 조사는 후속 반영 전체를 다시 검증한 감사도 아니다. 위 판단은 읽은 현재 코드의 범위다. [P02–P06]

## 2. 가져올 가치가 큰 패턴

### TM-01 · 화면 연결과 실행 수명을 분리한다

**tmux에서 본 것:** server는 터미널 상태를 보유하고 client detach는 세션을 없애는 동작과 다르다. [T02·T10]

**우리에게 옮길 것:** 사용자가 탭을 닫거나 UI가 잠시 끊겨도 그것을 취소나 실패로 기록하지 않는다. 다시 열면 기존 run을 조회해야지 새 모델 호출을 시작하면 안 된다. controller가 살아 있다면 계속 진행한 결과를 다시 보여 주고, controller도 죽었다면 기존 복구 정책을 적용한다.

다음은 서로 다른 상태다.

| 사건 | 화면이 할 일 | 하면 안 되는 일 |
|---|---|---|
| UI 연결만 끊김 | 연결 불가와 마지막 확인 상태의 오래됨을 표시 | 참여자를 실패/성공으로 재판정 |
| UI 재접속 | 기존 run·선택 위치·안전한 snapshot 복원 | create_run 자동 재전송 |
| controller 재시작 | 원장 회복, 이전 RUNNING은 종료 미확인으로 취급 | 살아 있던 모델 요청의 결과를 추측해 수용 |
| queued 재개 | 현재의 명시적 재개 동작을 사용 | 재접속 자체로 대기 시도 시작 |
| 새 호출/재시도 | 별도 승인·새 attempt·예산 소모 | 같은 attempt를 재사용하거나 예산 환급 |

tmux detach는 프로세스 메모리·원격 모델 내부 추론을 영구 보존하는 checkpoint가 아니다. server나 WSL이 종료된 뒤 과거 실행 중간으로 되돌리는 기능과도 다르다. ChatGPT의 생각실패를 tmux가 복구해 주는 것은 아니다. 지금처럼 **원문·진행 상태를 GitHub에 중간 저장하는 일은 별도로 계속 필요**하다. [T02·T10, 프로젝트 적용상의 구분]

### TM-02 · UI·자동화가 같은 제어 함수를 사용한다

**tmux에서 본 것:** control mode는 UI 자동화를 위한 별도 의미 체계를 만들지 않고 기존 tmux 명령을 재사용한다. 입력은 공통 parser/command queue로 들어간다. [T03·T11]

**우리에게 옮길 것:** 브라우저 버튼, 향후 CLI, 관측 도구가 서로 다른 성공 판정을 구현하지 않도록 한다. N2 도구도 N1 실행기를 재사용하고, 취소·수동 제출·축소 승인 같은 명령은 동일 controller 진입점을 탄다.

다만 tmux의 전체 문자열 명령 언어는 복사하지 않는다. 우리 명령은 좁고 타입이 정해진 요청이어야 한다. 버튼에 임의 shell 문자열을 넣거나 모델에게 범용 tmux 명령 실행 권한을 주는 것은 이 패턴의 반대다. 초기에는 현재 Python 함수와 HTTP endpoint의 공통 검증이면 충분하며, 범용 command bus가 꼭 필요한 것은 아니다. [P01·P02·P04, 제안]

### TM-03 · 명령 접수와 실행 완료를 별개로 보여 준다

**tmux에서 본 것:** control mode의 명령 응답 블록과 pane 출력/상태 알림은 다른 종류다. `new-session` 명령 성공과 그 안에서 실행한 프로그램의 최종 결과를 같은 것으로 읽을 수 없다. [T03·T11·T12]

**우리에게 옮길 것:** '요청 접수 → 시도 예약 → 프로세스 종료 확인 → 결과 수용 → 초안 공개'를 분리한다. `HTTP 200`, tmux 명령 성공, pane 종료, 유효한 모델 결과는 서로 대체하지 않는다.

향후 연결이 끊긴 뒤 명령을 다시 보내야 한다면 사용자 명령의 `command_id`와 실행의 `attempt_id`도 분리한다. 같은 명령을 재전송하는 것은 중복 실행을 막기 위한 것이고, 새 attempt는 새로운 예산 소비다. **tmux의 명령 번호가 영속적 idempotency key를 제공한다는 뜻은 아니다.** 우리에게 필요한 영속 중복 방지는 우리가 설계해야 한다. [P02·P03, 제안]

### TM-04 · 표시 위치가 아니라 안정 ID로 작업을 가리킨다

**tmux에서 본 것:** control mode 위키는 이름·index보다 session/window/pane ID를 권한다. [T03]

**우리에게 옮길 것:** '두 번째 카드', '현재 창', 'Claude'라는 표시 이름으로 제출·취소·승인을 연결하지 않는다. 이미 존재하는 run/participant/attempt ID를 유지한다. 화면 정렬이나 label 변경은 원장의 실행 identity를 바꾸지 않는다.

향후 tmux를 선택 transport로 실험할 때도 pane ID를 attempt ID로 대신 쓰면 안 된다. `respawn-pane`은 pane을 재활성화하므로 같은 pane 객체가 새로운 실행을 담을 수 있다. server 교체 전후까지 ID의 유일성을 확장해서도 안 된다. 필요하다면 `(backend instance, pane ID, generation) → attempt`의 명시적 binding을 둔다. 지금 독립 실행 경로에 외부 transport가 없는데 미리 범용 ID 계층을 추가하지는 않는다. [T10·T12, P02, 제안]

### TM-05 · 상태 조회와 사건 원장을 구분한다

**tmux에서 본 것:** list/format은 현재 상태를 조회하고 알림·format subscription은 변화 인지를 돕는다. 구독은 일정 주기로 계산하므로 모든 순간의 전이를 영구 보존한다고 볼 수 없다. [T03·T05]

**우리에게 옮길 것:** 지금의 snapshot 조회는 유지해도 된다. 사건 스트림을 넣더라도 원장의 현재 상태가 기준이고, 화면은 연결 후 snapshot으로 동기화해야 한다. '알림을 못 받았으니 변화가 없었다'고 판단하지 않는다.

현재 HTML은 `setInterval(refresh, 1000)`으로 요청하고, 돌아온 응답을 곧바로 전역 state에 넣는다. 코드상으로는 느린 응답과 새 요청이 겹칠 수 있다. **현재 실제 화면에서 역전 현상을 관측했다는 뜻은 아니지만**, 확장 전에 in-flight 제한·오래된 응답 무시·연결 stale 표시를 작은 시험으로 확인할 가치가 있다. 전체 상태 조회의 비용 역시 아직 측정하지 않았다. [P05]

추후 SSE 등이 필요해지면 `snapshot + cursor`의 원자적 일관성, 재연결 gap, 중복·역순 처리부터 정한다. UI용 공개 cursor를 raw journal seq와 무조건 같게 만들지 않는다. 봉인 대상 사건의 개수나 빈도도 단서가 될 수 있으므로 현재 투영 정책을 통과한 상태만 보낸다. tmux 알림을 영속 event sourcing 시스템으로 오해하거나 UI를 두 번째 상태 권위로 만들지 않는다. [P03·P07, 제안]

### TM-06 · 느린 화면 때문에 실행을 막지 않는다

**tmux에서 본 것:** control mode에는 client/pane별 큐, 출력 흐름 제어, pause·재동기화 장치가 있다. 다만 출력을 off로 하면 tmux가 pane에서 읽기를 멈출 수 있다는 문서 설명도 있다. [T03·T11]

**우리에게 옮길 것:** '실행 결과를 수집하는 경로'와 '화면에 보내는 경로'를 다르게 취급한다. UI가 느리면 안전한 최신 상태로 합치거나 오래된 화면 갱신을 버릴 수 있지만, CLI 파이프를 비우는 작업이나 완료·취소·예산 사건을 조용히 버려서는 안 된다.

모델 출력 원문은 봉인 저장소로, 화면은 허용된 상태만 받는다. 모든 출력 토큰마다 화면을 다시 그리는 구조는 필요 없다. 많은 run이 쌓일 때 목록·선택 run 상세를 나누거나, 바뀐 상태만 렌더링하는 방식부터 측정한다. tmux의 큐 상수나 libevent 구조를 Python에 그대로 옮기지 않는다. [P03·P05·P07, 제안]

### TM-07 · 실패한 작업은 없애지 말고 조사할 수 있게 남긴다

**tmux에서 본 것:** `remain-on-exit`과 관련 표시·재활성화는 종료된 pane을 살펴보게 한다. [T10, 온라인 매뉴얼의 해당 절]

**우리에게 옮길 것:** 실패/종료 미확인 카드를 자동 삭제하지 않는다. 안전한 상태 코드, 입력 식별자, attempt, 사용한 예산을 남기고 원문 진단은 공개 정책 뒤에 둔다. '마지막 실패로 이동', '사용자 응답 대기만 보기', '정족수 때문에 멈춘 실행 보기' 같은 탐색을 넣는다.

이미 SQLite 기록과 실패 예산이 있으므로 저장 계층을 새로 만들 필요는 없다. UI의 문제 위치 탐색과 기록 보존 정책이 추가 가치다. tmux의 respawn 편의는 자동 재호출로 가져오지 않는다. '재접속', '대기 시도 이어서 시작', '새 시도 승인'을 서로 다른 동작으로 남긴다. [P02·P03·P05·P07, 제안]

### TM-08 · 상태 중심 탐색과 문맥적 조작을 가져온다

**tmux에서 본 것:** tree 선택, filtering, zoom, pane border와 메뉴는 많은 실행을 한 화면에서 탐색하도록 돕는다. [T02·T05·T06]

**우리에게 옮길 것:** run 목록 → 선택한 run의 참여자 상태 → 허용된 원문 상세라는 구조다. '전체 터미널을 항상 나란히 띄우기'가 아니라 현재 해결할 문제를 빠르게 찾는다. 공개 전에는 상태만, 공개 후에는 읽기 전용 비교 공간에서 두 답을 고정해 비교할 수 있다.

패널의 크기·정렬·접힘·선택은 UI 상태이며 실행 policy와 분리한다. 화면에서 패널을 닫는 행위가 참여자를 빼는 명령이어서는 안 된다. 별도 읽기 화면이 생겨도 민감한 API의 권한 확인은 서버에서 한다. 여러 운영자에 대한 실제 RBAC는 현재 없는 기능이므로 'tmux read-only처럼 이미 된다'고 쓰지 않는다.

Ledger의 결정/반례/근거 중심 방향과 Q4는 유지한다. floating panes를 그대로 구현하거나 브라우저·한국어 IME와 충돌할 tmux prefix 키를 표준으로 강요할 필요는 없다. 키보드 탐색은 입력 중인 textarea를 건드리지 않는 작은 기능부터 검토한다. Modifier Keys 문서 자체도 3.5 이후 낡았다고 경고한다. [P01·P05·P07, T08·T15, 제안]

### TM-09 · 적용된 설정을 설명할 수 있게 한다

**tmux에서 본 것:** 옵션은 범위와 상속이 있고 show 명령으로 실제 적용값을 읽는다. 동시에 기존 server 환경·session 환경·client 환경 갱신이 상호작용한다. 설정 파일도 최초 server 시작 때 로딩되므로 새 client가 바뀐 환경을 가졌다는 것만으로 전체 상태가 초기화되지는 않는다. [T02·T10·T12·T13]

**우리에게 옮길 것:** N4에는 설치 버전, 사용 transport, 요청 모델, 입력 전달 방식, 적용 권한/마운트 profile, 관측 유효성, 실행 허가·거절 이유를 설명하는 작은 effective-config view가 유용하다. 값이 어디서 결정됐는지까지 추적하되 비밀 환경값·인증 파일 내용은 포함하지 않는다.

단, tmux의 느슨한 설정 상속과 오류 후 계속 처리까지 복사하지 않는다. 각 attempt의 실행 명세와 policy는 승인 시점에 고정하고, 필수 격리·모델·자격 조건이 없으면 시작을 거절한다. hidden 환경변수와 user option은 비밀 저장소가 아니다. [P01·P02·P06, 제안]

## 3. 그대로 가져오면 프로젝트를 약화시키는 것

| 유혹 | tmux에서 확인한 사실 | 우리 프로젝트에서의 판단 |
|---|---|---|
| 참여자마다 session을 만들면 독립적이다 | socket을 공유하는 사용자는 완전 신뢰 대상. 창 연결·session group은 공유 기능 | 세션/창은 격리 경계가 아님. bubblewrap과 API token을 유지 |
| read-only client에 worker를 연결하면 안전하다 | FAQ는 이것을 보안 메커니즘으로 보지 않음 | 참여자에게 controller tmux socket을 제공하지 않음 |
| `no-output`이면 봉인이다 | live pane 출력 억제 옵션이며 조회 명령 권한 자체를 없애지 않음 | capture/list/format/다른 접속을 통한 접근까지 막는 ACL이 아님 |
| pane-dead나 tmux 명령 성공이면 예산 자리를 풀어도 된다 | pane/명령/실제 프로그램의 계층이 다름 | 현재 whole-tree·input·semantic verdict를 그대로 요구 |
| `wait-for`가 정족수 barrier다 | named signal/lock이며 3.7c 상태는 server 메모리 | input binding·유효 초안·구성 승인·복구를 대체하지 않음 |
| 모든 pane에 같은 키를 보내면 같은 입력이다 | synchronize-panes는 키 입력 복제 | CLI마다 상태·line discipline·붙여넣기·EOF가 다를 수 있음. 고정 prompt를 기존 stdin 계약으로 보냄 |
| capture-pane 결과를 모델 답 원문으로 저장하면 된다 | PTY 출력/화면 상태를 다루는 도구 | stderr 분리·바이트 정확도·전체 기록·완료 증명을 복원한다고 가정하지 않음 |
| hook에서 자동 respawn하면 복구다 | hook/respawn은 명령을 실행하는 편의 | 새 호출·예산 승인과 충돌. unknown 자동 재실행 금지 |
| 풍부한 formats를 모델에게 입력시키면 유연하다 | 재확장·shell 실행 가능한 문맥이 있음 | 모델 텍스트를 명령/형식으로 평가하지 않음. allowlist와 literal data로 처리 |
| 디버그 로그는 안전한 기술 기록이다 | spawn/environ debug 경로에 명령 인자·환경값 기록 | 실제 인증·질문이 있는 실행에서 무분별한 verbose logging 금지 |

근거: [T03–T07·T10–T14], 프로젝트의 적용 판단: [P01–P07]. 위 표는 실제 침해나 누출을 재현했다는 보고가 아니다.

### 특히 PTY와 pipe를 혼동하면 안 된다

현재 runner/adapter 계약은 stdin과 분리된 stdout·stderr를 중심으로 만들어져 있다. tmux pane은 PTY다. pane에서 프로그램이 읽고 쓰는 terminal 모드, echo, 줄바꿈, resize, escape sequence는 별도의 계층을 만든다. 기본 PTY capture만으로 stderr의 거절 문구까지 원래 채널대로 복원했다고 할 수 없다. 프로세스가 stdout으로 JSON을 내도 tmux가 그 JSON의 의미를 검증하는 것은 아니다. [T03·T12, P01·P02]

tmux control mode의 `%output`은 바이트를 escape해 전달하며 올바른 UTF-8 텍스트라는 보장도 없다. 향후 parser가 필요하면 framing을 bytes 수준에서 처리하고 그 뒤 terminal/text decoder를 선택한다. 셸 명령을 보낼 때 `send-keys -l` 같은 문자 전달만으로 shell 해석·tmux 명령 구분·대상 혼동까지 사라진다고 가정하면 안 된다. [T03·T11]

shell 문자열을 피하려고 여러 argv를 주는 직접 exec 경로는 실제로 있지만, 그것도 **PTY라는 차이와 tmux parser를 제거하지 않는다**. 현재 exec 기반 입력·출력 계약의 간단한 대체재는 아니다. [T12]

## 4. tmux 바이너리를 실제로 쓴다면 어디에 둘 것인가

### A. 권장 기본: 아이디어만 이식

```text
Windows UI
    │ 제한된 HTTP 요청/안전한 상태 조회
WSL Python controller ─ SQLite journal
    │ existing runner / adapter / isolation
    ├─ attempt A: bubblewrap → native CLI
    └─ attempt B: bubblewrap → native CLI
```

현재 경계를 유지하고 TM-01–09 중 필요한 것만 이식한다. tmux 설치, PTY renderer, 새로운 runtime backend가 필요 없다. [P01–P06, 제안]

### B. 조건부 운영 보조: 신뢰한 개발자의 controller 터미널만 유지

```text
신뢰한 개발자 terminal ↔ 전용 tmux server
                             └─ controller 프로세스
                                  └─ 기존 bubblewrap 참여자
```

개발 중 terminal/SSH 창을 닫아도 controller를 유지하는 편의는 얻을 수 있다. 다만 설치·실행을 이번에 승인받거나 시험한 것은 아니다. 적용한다면 별도 socket·검토한 config·깨끗한 환경을 사용하고, 그 socket과 history·token 출력은 controller 권한 영역으로 취급한다. 참여자에게 이를 연결하지 않는다. debug log와 clipboard도 검토한다.

tmux server/WSL/호스트 재시작을 넘어 실행을 되살리는 보장, 로그 보관 정책, 서비스 자동 시작·복구 정책은 별도다. 일상 운영을 서비스 관리로 옮길 필요가 생기면 그때 한 가지 supervisor를 정한다. tmux와 서비스 관리자를 동시에 실행 권위로 쌓지 않는다. [T02·T04·T10·T12·T13, 설계 제안]

### C. 피할 결합: 격리 안 client가 격리 밖 server에 실행을 맡김

```text
controller → bubblewrap → tmux client ─ socket ─ 격리 밖 tmux server → CLI
```

이 경우 client를 가뒀다는 사실이 밖의 server가 생성한 CLI를 가뒀다는 뜻이 아니다. client 종료를 관측해 전체 실행 종료로 해석하면 runner 계약을 깨뜨릴 수 있다. **이 topology는 채택하지 않는 것을 권한다.** 네트워크 서비스에 작업을 대신 시키는 것과 같은 종류의 신뢰 경계 문제다. [T10·T12, P06, 추론]

### D. 후순위 실험: attempt 안에 독립 tmux server까지 포함

기술적으로 조사 가능한 구성이나, 지금 필요한 것은 아니다. 밖의 socket을 공유하지 않고 tmux server까지 같은 attempt namespace에 넣은 뒤 전체 종료·PTY·EOF·채널·입력·비밀 보호를 다시 관측해야 한다. 현재 read-only 구조화 CLI 실행에서는 비용에 비해 이득을 입증하지 못했다. 오직 **특정 CLI가 실제 PTY 상호작용을 요구한다는 관측**이 생겼을 때 별도 transport 후보로 비교한다. [T10–T13, 제안]

원본 ChatGPT·Claude·Antigravity GUI의 메모리·컴퓨터 사용·세션 기능을 tmux가 복제해 주는 것은 아니다. 사용자 확정 17의 수동 원본 앱 참여와 Q5는 그대로 유지한다. [P01, 적용 범위]

## 5. 이번 조사에서의 결론

가져올 것은 **접속과 실행의 분리, 공통 제어 진입점, 명령/사건/결과의 구분, 정확한 ID, 안전한 재동기화, 제한된 화면 갱신, 실패 탐색, 적용 설정 설명**이다. 이미 있는 원장·수용·봉인·복구를 새 도구로 바꾸지는 않는다.

직접 재사용한다면 먼저 개발자의 운영 터미널 유지 정도가 적정 후보이고, 참여자 실행 엔진으로 tmux를 넣는 것은 보류한다. C 코드를 가져오거나 control protocol parser를 미리 만들 근거도 아직 없다. '가능한 기능이 많다'보다 **현재 N1–N4를 더 간단하고 확실하게 완성하는가**로 판단한다. 구체적인 적용 단위와 모델 없는 검증은 [ADOPTION_PLAN.md](ADOPTION_PLAN.md)에 둔다.
