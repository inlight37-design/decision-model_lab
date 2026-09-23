# tmux에서 배울 것 — decision-model_lab 적용 조사

작성: **ChatGPT · GPT-6 Astra Pro · 2026-09-23**  
요청: [tmux 공식 위키](https://github.com/tmux/tmux/wiki)에서 우리 프로젝트에 가져올 개념·기능·구현 방식을 찾아 문서화. 제출: [PR #8](https://github.com/inlight37-design/decision-model_lab/pull/8).

**결론: 배울 점은 많지만, 지금 tmux를 참여자 실행 엔진으로 넣을 필요는 없다.** 가장 유용한 것은 화면 분할이 아니라 **화면 연결과 실행 수명의 분리, 공통 제어 진입점, 상태 재동기화, 안정된 작업 식별자, 느린 화면과 실행 수집의 분리, 실패 기록 탐색**이다. 이 개념을 기존 controller·SQLite·HTTP 화면에 작게 적용하는 편이 현재 방향과 맞는다. 이는 설계 권고이며 새 사용자 결정이나 구현 완료가 아니다.

## 먼저 읽을 것: 조사 기준과 동시 작업

초기 분석과 출처 표는 프로젝트 **`cd94190bf10b1bacc812ee698e4c6dc6a86260ca`**(A1 반영 이후)에 고정했다. 조사 중 main이 진행되어 다음도 확인했다.

| 대조한 revision | 확인한 변화 | 이 조사에 미치는 영향 |
|---|---|---|
| [`e37d7d3cc290024483569ac5acf41b386ffba6b6`](https://github.com/inlight37-design/decision-model_lab/commit/e37d7d3cc290024483569ac5acf41b386ffba6b6) | N1 실행기와 사용자 확정 18·19 | [실행기 소스](https://github.com/inlight37-design/decision-model_lab/blob/e37d7d3cc290024483569ac5acf41b386ffba6b6/app/cli_executor.py)를 직접 읽었다. 이미 있는 실행기를 다시 만들지 않는다. Q6은 두 수를 구분하기로 정했고, Q5 화면 자동화는 하지 않으며 C2는 꺼 둔다 |
| [`f231a220358aa386960fb6a95b23790517ff4da4`](https://github.com/inlight37-design/decision-model_lab/commit/f231a220358aa386960fb6a95b23790517ff4da4) | N2 WSL 관측 도구 추가 | merge diff와 [인계](https://github.com/inlight37-design/decision-model_lab/blob/f231a220358aa386960fb6a95b23790517ff4da4/NEXT-SESSION.md)를 확인했다. N1·N2는 가짜 CLI 시험 단계라는 기록이며, 이 세션이 새 관측 도구를 실행하거나 전수 감사한 것은 아니다 |

**상세 분석의 초기 시점 설명과 현재 작업 지시를 구분한다.** ANALYSIS/ADOPTION_PLAN의 'N1–N4를 완성'은 이미 구현된 부분을 재사용하고 최신 인계의 남은 준비를 진행한다는 뜻으로 읽는다. Q5·Q6·C2를 미정으로 돌리지 않는다. 후속 구현자는 최신 NEXT-SESSION을 기준으로 삼는다. 조사 중 진행된 코드는 보존하고 이 PR이 과거 상태로 되돌리지 않는다.

## 문서 지도

| 문서 | 내용 |
|---|---|
| [ANALYSIS.md](ANALYSIS.md) | TM-01–09의 근거·적용 방식, 이미 있는 기능, 피할 결합, PTY/pipe와 신뢰 경계, 직접 도입 topology |
| [ADOPTION_PLAN.md](ADOPTION_PLAN.md) | 작은 적용 순서, 완료 조건, 중복 호출·재접속·봉인·느린 화면·socket·PTY에 대한 **미실행 수용 시험 제안** |
| [EVIDENCE.md](EVIDENCE.md) | 1차 출처 T01–T15, 초기 프로젝트 코드 P01–P07, 고정 SHA·읽은 위치·버전 차이·접근 한계 |
| [WORKLOG.md](WORKLOG.md) | 조사 시작 체크포인트. 후속 진행은 Git 커밋과 PR에서 확인 |

**tmux 기준:** 2026-09-23에 release API로 확인한 최신 안정 릴리스는 **3.7c**, 소스 commit은 [`e476c1230b958df0cb12977517d24b3dc931375b`](https://github.com/tmux/tmux/tree/e476c1230b958df0cb12977517d24b3dc931375b)이다. 반환된 Home에는 3.7b 안내가 남아 있었고 Formats/Events에는 3.8 대상 내용도 있다. 안정 버전과 개발 문서를 섞지 않는다. Events는 검색 설명만 확인했고 본문 직접 열기는 실패했다. 자세한 범위는 EVIDENCE에 적었다.

## 가져올 가치가 있는 패턴

| 패턴 | 우리 프로젝트에 적용할 구체적인 방향 |
|---|---|
| **TM-01 연결과 실행 분리** | UI 재접속이 모델 재호출로 이어지지 않게 한다. 화면 연결 불가와 실행 UNKNOWN을 다르게 표시한다 |
| **TM-02 공통 명령 진입점** | UI·관측 도구가 같은 controller/실행기를 쓰고 성공·예산 판정을 복제하지 않는다 |
| **TM-03 접수와 완료 구분** | HTTP/tmux 명령 성공과 결과 수용을 구분한다. 같은 명령 재전송과 새 예산을 쓰는 시도를 나눈다 |
| **TM-04 안정 식별자** | 정렬·표시 이름 변경·pane 재사용이 다른 실행의 결과나 명령으로 연결되지 않게 한다 |
| **TM-05 상태 재동기화** | 오래된 응답이 최신 상태를 덮지 않게 하고, 알림을 놓쳐도 현재 상태를 다시 확인한다 |
| **TM-06 느린 화면 분리** | UI가 느려도 stdout/stderr 수집과 완료·예산 기록은 막지 않는다. 화면용 갱신만 제한한다 |
| **TM-07 실패 기록 탐색** | 종료 미확인·수동 응답 대기·정족수 보류·마지막 실패로 빠르게 이동한다 |
| **TM-08 문맥적 화면 구성** | 상태 목록과 선택 상세를 나누고 공개 후에만 답 비교를 펼친다. 패널 닫기와 참여자 이탈을 구분한다 |
| **TM-09 적용 설정 설명** | 모델·입력 전달·격리 profile·관측 유효성·실행 거절 이유를 비밀 없이 설명한다 |

근거와 한계는 상세 분석의 같은 번호에 있다. 이 이득은 **목표**이지 측정된 개선량이 아니다. tmux가 모델 품질이나 구독 토큰 효율을 높였다는 증거를 얻은 것은 아니다.

## 직접 도입과 개념 이식을 구분한다

**기본 권고는 개념 이식이다.** 기존 `화면 → Python controller/SQLite → runner·adapter·bubblewrap → CLI` 경계를 유지한다. A1의 원장 소유권·조건부 완료·입력/모델 관문·복구·봉인을 다시 만들지 않는다. 초기 코드 대조는 EVIDENCE P02–P06에 있다. 구현된 실행기·관측 도구를 재사용하고, 인증·실행 적격성·화면 보강을 최신 계획대로 진행한다. 별도 workflow engine이나 tmux parser가 선행 조건은 아니다.

**조건부로 유용한 직접 사용은 개발자의 controller 터미널 유지다.** 전용 tmux server에 신뢰한 운영자만 접속하여 terminal/SSH 연결을 끊어도 다시 작업을 보는 용도다. 전용 socket·환경·config·scrollback·토큰 출력의 신뢰 범위를 확인해야 하며, 이번에 설치하거나 시험한 것은 아니다.

**현재 보류할 것은 참여자를 pane으로 조종하는 방식이다.** `send-keys`/`capture-pane`은 현재의 stdin·분리된 stdout/stderr·구조화 결과·자손 종료 계약에 PTY와 추가 server 계층을 더한다. 실제 PTY 요구가 관측될 때만 별도 후보로 검증한다. 특히 **bubblewrap 안의 tmux client가 밖의 tmux server에 실제 CLI 실행을 맡기는 구성**은 피한다. client의 격리와 종료가 외부 server의 작업에 대한 증거가 아니기 때문이다(T10·T12, P06, 추론).

## 그대로 가져오면 안 되는 것

**세션/창/read-only 접속은 보안 격리가 아니다.** 공식 FAQ는 socket 접근자를 완전히 신뢰해야 한다고 설명한다. `no-output`도 출력 억제이지 접근 권한 제거가 아니다(T03·T04). `pane-dead`, 명령 성공, `wait-for` 신호로 유효한 답·정족수·전체 자손 종료를 인정하지 않는다(T03·T10–T14, P02).

**터미널 화면은 결과 원장이 아니고 hidden 변수는 비밀 저장소가 아니다.** PTY·escape·붙여넣기·EOF·stderr 채널을 따로 검증해야 한다. debug 경로에 인자·환경값이 기록될 수 있음도 고정 소스에서 확인했다(T07·T11–T13). 실제 토큰 유출을 재현한 것은 아니다.

**detach는 영구 checkpoint가 아니다.** tmux server·WSL·호스트 종료 이후의 복구나 AI 서비스 내부의 생각실패를 해결하지 않는다. GitHub 중간 커밋과 원장 복구는 계속 필요하다(T02·T10, 적용 범위).

## 변경·검증 범위

이번 변경은 **조사 문서와 인계 연결**이다. 제품 코드·시험·workflow·의존성·설정·디자인 원본을 바꾸지 않았고, 모델 호출·로그인·사용자 PC 조작도 하지 않았다. GitHub와 공식 문서를 읽었으며 이 웹 컨테이너에서는 git의 DNS 오류와 tmux 실행 파일 부재로 실제 통합 시험을 하지 못했다. CI는 저장소 변경의 검사이지 tmux 통합·성능·보안 검증이 아니다.

직접 C 코드를 복사하거나 바이너리를 배포하지 않았다. 향후 복사한다면 실제 파일별 copyright/permission notice와 포함된 제3자 파일의 조건을 확인·보존한다(T15). 제안된 다음 구현은 가짜 CLI와 임시 원장으로 먼저 검증하고, 측정 이득이나 실제 PTY 요구가 없으면 tmux 의존성은 추가하지 않는다.
