# 출처와 확인 범위 — tmux 조사

확인일: **2026-09-23**. 작성: ChatGPT (GPT-6 Astra Pro). 아래 T/P 번호는 이 조사 안의 참조다. 아키텍처의 F/E 근거 원장에 새 항목을 추가한 것이 아니다.

## 기준과 증거 등급

- 프로젝트: [`cd94190bf10b1bacc812ee698e4c6dc6a86260ca`](https://github.com/inlight37-design/decision-model_lab/commit/cd94190bf10b1bacc812ee698e4c6dc6a86260ca). A1 리뷰 반영 이후다.
- tmux 안정 릴리스: **3.7c**, GitHub release API의 `published_at=2026-08-17T12:53:48Z`, `prerelease=false`를 확인했다.
- annotated tag 객체: `79072dd1a9f5fb437a5859e362a496fd57ec0981`. 실제 소스 commit: **`e476c1230b958df0cb12977517d24b3dc931375b`**. tag 객체 SHA와 commit SHA를 혼동하지 않는다.
- **문서:** 직접 받은 공식 페이지의 설명. **코드 관측:** 고정 commit의 구현을 직접 읽음. **추론/제안:** 이를 우리 프로젝트에 적용하는 설계 판단. **실행 재현:** 이번 tmux 조사에서는 없음.
- 웹 컨테이너의 `git ls-remote`는 GitHub DNS 해석 실패로 끝났고 `command -v tmux`는 경로를 반환하지 않았다. GitHub connector로 소스를 읽고 썼다. 사용자 PC·WSL·모델·로그인에 접근하지 않았다.

## T — tmux 1차 출처

### T01 · 릴리스와 소스 고정

- [최신 release API](https://api.github.com/repos/tmux/tmux/releases/latest), [3.7c release](https://github.com/tmux/tmux/releases/tag/3.7c).
- [tag ref](https://api.github.com/repos/tmux/tmux/git/ref/tags/3.7c), [annotated tag 객체](https://api.github.com/repos/tmux/tmux/git/tags/79072dd1a9f5fb437a5859e362a496fd57ec0981).
- **확인:** GitHub 연결에서 release와 tag→commit을 직접 확인. 최신 판정은 조사일 기준이며 설치 버전의 관측이 아니다.

### T02 · Home와 Getting Started

- [Home](https://github.com/tmux/tmux/wiki), [Getting Started](https://github.com/tmux/tmux/wiki/Getting-Started).
- **위치:** Basic concepts → server and clients / sessions, windows and panes; configuration; option types; embedded commands.
- **확인:** server/client 분리, detach/attach, 창·pane·layout, 설정의 범위와 상속, 상태줄이 계산한 값을 표시하는 방식.
- **한계:** 반환된 Home 본문에는 3.7b 링크가 남아 있었다. 최신 안정 릴리스의 근거로 쓰지 않는다. 긴 입문 문서는 프로젝트 관련 절 중심으로 읽었으며 모든 단축키를 감사하지 않았다.

### T03 · Control Mode

- [공식 위키](https://github.com/tmux/tmux/wiki/Control-Mode).
- **위치:** Commands / Getting information / Pane output / Notifications / Flow control / Format subscriptions / General notes.
- **확인:** 동일 tmux 명령 집합 재사용, 명령 응답 블록과 비동기 알림, 출력 바이트의 octal escape, ID 사용, `no-output`, `pause-after`, 상태 재조회와 구독.
- **한계:** 응답 블록의 완료는 tmux 명령 처리 결과다. AI 답의 성공·자손 종료·과금 완료가 아니다. 구독은 매 순간의 변경을 보존하는 영속 사건 원장이 아니다. 이 위키에는 예전 설명도 있으므로 실제 parser는 설치 버전 매뉴얼·소스로 고정해야 한다.

### T04 · FAQ의 신뢰 경계

- [공식 FAQ](https://github.com/tmux/tmux/wiki/FAQ).
- **위치:** socket 접근을 허용한 사용자에 대한 security 질문; UTF-8 관련 질문.
- **확인:** 같은 socket에 접근할 수 있는 사용자를 완전히 신뢰해야 한다. `server-access`와 read-only flag는 신뢰하는 사람의 실수를 줄이는 편의 기능이며 적대적 사용자 사이의 보안 경계가 아니다.
- **한계:** 이 설명은 격리 backend가 tmux가 아니라는 판단의 근거다. 사용자 PC의 socket 권한을 직접 검사한 것은 아니다.

### T05 · Formats

- [공식 위키](https://github.com/tmux/tmux/wiki/Formats).
- **위치:** 비교·조건부 형식, multiple expansion, choose-mode filtering, 기능별 Version 표.
- **확인:** 상태값을 조합해 표시·검색·정렬하는 접근과 재확장 구문. `m/z`, `m/p`, 일부 루프/client lookup은 표에서 3.8로 표시된다.
- **한계:** 3.8 항목을 3.7c의 지원 기능으로 권하지 않는다. tmux 형식 언어를 우리 API에 그대로 열어 주자는 제안도 아니다.

### T06 · Recipes

- [공식 위키](https://github.com/tmux/tmux/wiki/Recipes).
- **위치:** 작업 디렉터리를 유지하는 새 pane, 탐색, pane-border 메뉴.
- **확인:** 작고 문맥적인 조작과 탐색 개선 아이디어. 메뉴 control range 예제에는 3.7 이상이라는 전제가 있다.
- **한계:** 예제의 cwd 계승·실행 명령을 독립 참여자 생성에 그대로 복사하면 격리된 빈 작업 폴더 원칙과 다를 수 있다. UI 영감만 선별한다.

### T07 · Clipboard

- [공식 위키](https://github.com/tmux/tmux/wiki/Clipboard).
- **위치:** set-clipboard 동작과 Security concerns.
- **확인:** `on`은 pane 프로그램이 escape sequence를 통해 clipboard를 바꿀 통로를 허용한다. `external`과 `off`는 다른 정책이다. 출력은 단순한 글자가 아니라 부수효과를 유발할 수 있는 터미널 제어 데이터다.
- **한계:** 오래된 terminal별 지원·버그 목록은 현재 브라우저/Windows Terminal의 지원 여부로 일반화하지 않았다. 실제 OSC 52 시험도 하지 않았다.

### T08 · 설치·기여·modifier 문서

- [Installing](https://github.com/tmux/tmux/wiki/Installing), [Contributing](https://github.com/tmux/tmux/wiki/Contributing), [Modifier Keys](https://github.com/tmux/tmux/wiki/Modifier-Keys).
- **확인:** 플랫폼/빌드·termcap 계열 의존성, upstream OpenBSD와 portable GitHub의 관계, 파일별 ISC 고지, 터미널 키 전달의 별도 복잡성.
- **한계:** 설치 지시나 vendor 앱 자동화를 구현하지 않았다. 사용자 WSL의 tmux 버전·terminfo·IME·clipboard는 미확인이다. 기여 문서가 인용한 AI 업체 약관은 이 조사에서 법률적으로 재검토하지 않았다.

### T09 · 개발 문서의 Events

- [Events](https://github.com/tmux/tmux/wiki/Events).
- **접근 범위:** 공식 페이지의 검색 결과에서 2026-09-03 편집, 3.8 이상 대상이라는 설명과 `set-hook -B`, `wait-for -E` 등의 예시를 확인했다. 본문 직접 열기는 실패했다. 따라서 전체 문서를 읽었다고 주장하지 않는다.
- **용도:** 버전 혼합 경고만. 3.7c의 실제 구현 근거는 아래 T14다. 이 기능을 도입 필수 조건으로 삼지 않는다.

### T10 · 고정 3.7c 매뉴얼의 기본 경계

- [`tmux.1:50–215`](https://github.com/tmux/tmux/blob/e476c1230b958df0cb12977517d24b3dc931375b/tmux.1#L50-L215).
- **확인:** 별도 server/client process와 PTY, socket, `-L`/`-S`, 설정의 최초 로딩, 설정 오류 뒤 남은 명령 처리.
- **보완 자료:** [OpenBSD 온라인 매뉴얼](https://man.openbsd.org/tmux.1)의 명령 실행, 환경, hooks, remain-on-exit, capture-pane 절도 참고했다. 온라인 매뉴얼에는 개발 기능이 섞이므로 3.7c 전체 API 목록으로 취급하지 않는다.
- **한계:** 전체 매뉴얼 모든 줄을 읽은 것은 아니다. 동작상 중요한 부분은 아래 고정 소스로 재확인했다.

### T11 · Control mode의 실제 명령·출력 구현

- [`control.c:1–175`](https://github.com/tmux/tmux/blob/e476c1230b958df0cb12977517d24b3dc931375b/control.c#L1-L175), [`540–745`](https://github.com/tmux/tmux/blob/e476c1230b958df0cb12977517d24b3dc931375b/control.c#L540-L745).
- **코드 관측:** client/pane 출력 큐와 순서 유지, `control_read_callback()`의 LF 구분 및 `cmd_parse_and_append()`, 빈 줄 detach, octal escaping과 출력 chunk 처리.
- **blob:** `b88072d36445288df4447692cc351d1da722ca32`.
- **한계:** 모든 protocol 분기·fuzz 입력·backpressure를 실행 검증한 것은 아니다. 큐의 수치 상수를 우리 프로젝트 권장값으로 복사하지 않는다.

### T12 · PTY·명령 실행·환경·debug의 실제 구현

- [`spawn.c:280–545`](https://github.com/tmux/tmux/blob/e476c1230b958df0cb12977517d24b3dc931375b/spawn.c#L280-L545).
- **코드 관측:** `fdforkpty()`로 pane을 생성한다. 여러 argv는 직접 exec 경로, 단일 문자열은 선택된 shell의 `-c` 경로다. PATH와 SHELL을 설정하고 debug 경로에 argv/environment 로깅이 있다.
- **중요한 예외:** 빌드 조건에 따라 systemd-oomd용 cgroup 이동도 있다. 따라서 'tmux에는 cgroup 관련 코드가 전혀 없다'고 쓰면 틀린다. 이것이 우리 runner의 전체 자손 종료 증거·CPU/메모리 하드 상한 계약을 대신한다는 근거도 없다.
- **blob:** `3c9846e612706c767774d9372b19fd86556ec19d`.

### T13 · 환경 합성과 hidden 변수

- [`environ.c:205–295`](https://github.com/tmux/tmux/blob/e476c1230b958df0cb12977517d24b3dc931375b/environ.c#L205-L295).
- **코드 관측:** global/session 환경 합성, TERM 계열과 TMUX 파생 값, child에서 hidden 변수 제외. 반면 `environ_log()`는 값이 있는 환경 항목을 debug 경로로 기록한다.
- **결론의 범위:** hidden은 secret vault가 아니다. clean client 환경이나 attach의 환경 갱신 옵션만으로 기존 server의 환경을 지웠다고 가정하지 않는다. 실제 토큰 노출 사건을 확인한 것은 아니다.
- **blob:** `68e0417b0f7edcaae85cccae177727827dca81ff`.

### T14 · 3.7c wait-for

- [`cmd-wait-for.c:1–225`](https://github.com/tmux/tmux/blob/e476c1230b958df0cb12977517d24b3dc931375b/cmd-wait-for.c#L1-L225).
- **코드 관측:** 지원 옵션은 L/S/U이며 named channel 상태는 server 메모리의 자료구조다. 3.8 Events 문서의 `wait-for -E`가 이 release에도 있다고 가정하면 안 된다.
- **한계:** signal/lock primitive는 호출 예산·입력 binding·정족수·영속 복구를 검증하는 protocol이 아니다. 이를 SQLite 원장 잠금의 대체물로 제안하지 않는다.
- **blob:** `8a6aa259e62e4a23da97d41d1a89fb20a1f5303f`.

### T15 · CHANGES와 라이선스

- [`CHANGES:1–105`](https://github.com/tmux/tmux/blob/e476c1230b958df0cb12977517d24b3dc931375b/CHANGES#L1-L105): 3.7c bugfix, 3.7 floating panes, control-mode 종료/출력 관련 수정, paste 처리와 이름 처리 변경을 읽었다. floating pane 레이아웃 복원 등에 명시된 한계도 있다.
- [`COPYING`](https://github.com/tmux/tmux/blob/e476c1230b958df0cb12977517d24b3dc931375b/COPYING), 위에서 읽은 `.c` 파일 헤더: 사용·복제·수정·배포 허용과 copyright/permission notice 보존 조건을 확인했다.
- **재사용 방침:** 이번 변경은 개념 분석이며 tmux 코드를 복사하거나 바이너리를 배포하지 않는다. 나중에 파일을 복사하면 그 파일의 고지와 필요한 포함 파일의 별도 고지를 확인·보존한다. 저장소 전체에 단일 라이선스라고 추정해 제3자 파일까지 일괄 처리하지 않는다.

## P — 우리 프로젝트와의 연결

아래 경로는 모두 프로젝트 기준 commit에 고정해 읽는다. 새 전체 버그 감사나 사용자 PC 재현을 했다는 뜻이 아니다.

| ID | 읽은 위치 | 이번 조사에 필요한 사실 |
|---|---|---|
| P01 | [AGENTS](https://github.com/inlight37-design/decision-model_lab/blob/cd94190bf10b1bacc812ee698e4c6dc6a86260ca/AGENTS.md), [NEXT 2–4절](https://github.com/inlight37-design/decision-model_lab/blob/cd94190bf10b1bacc812ee698e4c6dc6a86260ca/NEXT-SESSION.md) | 사용자 확정 방향, A1 반영 뒤 상태, 남은 N1–N6 |
| P02 | [controller의 verdict/예약/완료](https://github.com/inlight37-design/decision-model_lab/blob/cd94190bf10b1bacc812ee698e4c6dc6a86260ca/app/controller.py#L126-L285) | complete·빈 답·모델 불일치 검사, attempt 조건부 갱신, queued 명시적 재개가 이미 있음 |
| P03 | [store](https://github.com/inlight37-design/decision-model_lab/blob/cd94190bf10b1bacc812ee698e4c6dc6a86260ca/app/store.py) | OS 파일 잠금, schema version, transaction과 실행별 seq가 이미 있음 |
| P04 | [server의 시작과 토큰 기록](https://github.com/inlight37-design/decision-model_lab/blob/cd94190bf10b1bacc812ee698e4c6dc6a86260ca/app/server.py#L120-L215) | 원장 잠금·bind·controller 순서, 제한된 파일 권한, 모의 server 실행과 토큰 출력 |
| P05 | [화면의 render/refresh](https://github.com/inlight37-design/decision-model_lab/blob/cd94190bf10b1bacc812ee698e4c6dc6a86260ca/app/static/index.html#L160-L292) | 1초 상태 조회, 현재 선택 실행, 수동 입력 보존, 상태·봉인·예산 표시 |
| P06 | [isolation의 plan/run](https://github.com/inlight37-design/decision-model_lab/blob/cd94190bf10b1bacc812ee698e4c6dc6a86260ca/core/isolation.py#L120-L191) | RO 하위 work와 자동 system mount의 never 검사 수정 확인. 환경 필터와 namespace 실행 유지 |
| P07 | [BlindBarrier](https://github.com/inlight37-design/decision-model_lab/blob/cd94190bf10b1bacc812ee698e4c6dc6a86260ca/design/project/components/BlindBarrier/README.md), [BudgetMeter](https://github.com/inlight37-design/decision-model_lab/blob/cd94190bf10b1bacc812ee698e4c6dc6a86260ca/design/project/components/BudgetMeter/README.md) | 제출 상태와 내용 노출을 구분하고, 호출 소진과 진척률을 구분하는 기존 규칙 |

## 확인하지 않은 것

실제 tmux detach/attach·crash·재부팅, 사용자 WSL 서비스 수명, PTY의 한글/큰 입력/EOF, control protocol 호환성·fuzz, 실제 shell/CLI의 stdout·stderr 분리, socket/clipboard 공격, 성능·메모리·토큰 절감량은 측정하지 않았다. tmux plugin이나 session 복원 addon은 범위 밖이다. GitHub CI 결과는 이 문서 변경의 저장소 검사 결과이며 tmux 통합 성공을 뜻하지 않는다.
