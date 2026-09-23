# tmux에서 배울 것 — decision-model_lab 적용 조사

작성: **ChatGPT · GPT-6 Astra Pro · 2026-09-23**  
요청: [tmux 공식 위키](https://github.com/tmux/tmux/wiki)에서 우리 프로젝트에 가져올 개념·기능·구현 방식을 찾아 문서화.

**결론: 배울 점은 많지만, 지금 tmux를 참여자 실행 엔진으로 넣을 필요는 없다.** 가장 유용한 것은 화면 분할이 아니라 **화면 연결과 실행 수명의 분리, 공통 제어 진입점, 상태 재동기화, 안정된 작업 식별자, 느린 화면과 실행 수집의 분리, 실패 기록 탐색**이다. 이 개념을 기존 controller·SQLite·HTTP 화면에 작게 적용하는 편이 현재 방향과 맞는다. 이는 아래 원문과 현행 코드를 대조한 **설계 권고**이며 새 사용자 결정이나 구현 완료가 아니다.

## 마감 시점 갱신 — 조사 중 main이 진행됐다

초기 분석·출처 표는 `cd94190bf10b1bacc812ee698e4c6dc6a86260ca`에 고정했다. PR 작성 중 main이 [`e37d7d3cc290024483569ac5acf41b386ffba6b6`](https://github.com/inlight37-design/decision-model_lab/commit/e37d7d3cc290024483569ac5acf41b386ffba6b6)로 진행된 것을 확인하고 그 변경을 **조사 브랜치로만** 반영했다. 새로운 main의 코드와 사용자 결정을 과거 인계로 덮어쓰지 않았다.

- **N1은 이제 있다.** 새 [`app/cli_executor.py`](https://github.com/inlight37-design/decision-model_lab/blob/e37d7d3cc290024483569ac5acf41b386ffba6b6/app/cli_executor.py)를 직접 읽었다. `describe()`는 기록용 명세를 반환하고 `execute()`는 resolve → build_spec → isolation → interpret 경로를 사용한다. 아직 서버에서 사용하지 않는다고 명시돼 있다. 가짜 CLI로만 시험했다는 범위와 남은 작업은 [해당 인계 N1–N4](https://github.com/inlight37-design/decision-model_lab/blob/e37d7d3cc290024483569ac5acf41b386ffba6b6/NEXT-SESSION.md#L124-L143)에 있다. 이번 세션이 실제 vendor CLI를 실행한 것은 아니다.
- **Q5·Q6·C2는 사용자 결정이 났다.** [인계 2절 18·19](https://github.com/inlight37-design/decision-model_lab/blob/e37d7d3cc290024483569ac5acf41b386ffba6b6/NEXT-SESSION.md#L97-L98): 답을 낸 수와 독립성이 확인된 수를 분리하고, 화면 조작 자동화는 하지 않으며, agy 자동 실행은 꺼 둔다. 결정과 코드 반영 완료는 다르며 수동 정족수의 N5 반영은 아직 남았다.
- **현재 적용 순서:** N1을 다시 만들지 않고 재사용하여 **N2·N3·N4**를 진행한다. TM-01–09의 설계 권고는 유지하되, 초기 ANALYSIS/ADOPTION_PLAN에 있는 'N1–N4를 완성'은 이 최신 상태로 읽는다. Q5를 아직 열린 결정으로 설명한 초기 문구 역시 확정 19가 우선한다. Q3·Q4는 별도다.

아래 상세 자료는 초기 소스와 연결된 분석을 보존한다. 현재 상태와 적용 순서는 이 갱신 및 최신 NEXT-SESSION이 우선이다. 이것은 새로운 전체 실행기 감사를 수행했다는 뜻이 아니다.

## 기준과 읽는 순서

| 항목 | 이번 조사 기준 |
|---|---|
| 초기 프로젝트 분석 | [`cd94190bf10b1bacc812ee698e4c6dc6a86260ca`](https://github.com/inlight37-design/decision-model_lab/commit/cd94190bf10b1bacc812ee698e4c6dc6a86260ca), A1 리뷰 반영 이후 |
| 마감 시점 대조 | `e37d7d3cc290024483569ac5acf41b386ffba6b6`, N1과 사용자 결정 반영 — 위 갱신 참조 |
| tmux | 2026-09-23에 확인한 최신 안정 릴리스 **3.7c**. 소스 commit [`e476c1230b958df0cb12977517d24b3dc931375b`](https://github.com/tmux/tmux/tree/e476c1230b958df0cb12977517d24b3dc931375b) |
| 확인 방법 | GitHub 소스·release API, 공식 위키·매뉴얼의 관련 절 대조 |
| 실행 범위 | tmux 실행·설치·성능 측정·실제 모델 호출 없음. 사용자 PC·WSL에 접근하지 않음 |
| 변경 범위 | 조사 문서와 인계 연결만. 제품 코드·설정·의존성·디자인 원본은 변경하지 않음 |

먼저 이 요약을 읽고, 설계 판단은 [ANALYSIS.md](ANALYSIS.md), 구현 순서와 시험 제안은 [ADOPTION_PLAN.md](ADOPTION_PLAN.md), 출처·버전·읽은 범위는 [EVIDENCE.md](EVIDENCE.md)에서 확인한다. [WORKLOG.md](WORKLOG.md)는 작업 시작 체크포인트다. 중간 결과는 같은 브랜치에 커밋해 두었다.

**버전 주의:** 반환된 위키 Home에는 3.7b 안내가 남아 있었지만 GitHub 최신 release는 3.7c였다. Formats와 Events에는 **3.8 대상 내용**도 섞여 있다. 안정 릴리스와 개발 문서를 섞어 설치된 기능처럼 권하지 않는다. Events는 검색에 노출된 공식 설명만 확인했고 본문 직접 열기는 실패했다. 버전 고정과 접근 한계는 EVIDENCE T01·T02·T05·T09·T14에 적었다.

## 무엇을 가져올 것인가

| 패턴 | 우리 프로젝트의 구체적인 이득 | 권고 시점 |
|---|---|---|
| **TM-01 연결과 실행 분리** | UI 재접속이 모델 재호출로 이어지지 않게 한다. 연결 불가와 실행 UNKNOWN을 다르게 표시한다 | 기존 화면 보강 |
| **TM-02 공통 명령 진입점** | UI·관측 도구가 같은 controller/실행기를 쓰고 성공·예산 판정을 복제하지 않는다 | 기존 N1을 N2에서 재사용 |
| **TM-03 접수와 완료 구분** | HTTP/tmux 명령 성공을 모델 결과 수용과 혼동하지 않는다. 재전송과 새 시도를 구별한다 | 기존 관문 유지, 명령 재전송 도입 시 |
| **TM-04 안정 식별자** | 정렬·이름 변경·pane 재사용이 다른 실행의 결과나 명령으로 연결되지 않게 한다 | 현재 ID 유지, 외부 transport 도입 시 보강 |
| **TM-05 상태 재동기화** | 오래된 응답이 최신 상태를 덮지 않게 하고, 사건을 놓쳐도 현재 상태로 돌아온다 | polling 보강부터 |
| **TM-06 느린 화면 분리** | UI가 느려도 stdout/stderr 수집과 완료·예산 기록을 막지 않는다 | 조회 비용 측정 후 |
| **TM-07 실패 기록 탐색** | 종료 미확인·수동 응답 대기·정족수 보류·마지막 실패로 빠르게 이동한다 | 화면 보강 |
| **TM-08 문맥적 화면 구성** | 상태 목록과 선택 상세를 나누고, 공개 후에만 답 비교를 펼친다 | 기존 Ledger·Q4 범위 안 |
| **TM-09 적용 설정 설명** | 실제 모델·입력·격리 profile·관측 유효성·실행 거절 이유를 비밀 없이 설명한다 | N4 |

각 행의 tmux 원문과 현재 코드 위치, 적용 시 주의점은 ANALYSIS의 같은 번호에 있다. 이 이득은 **목표**이지 이미 측정한 개선량이 아니다. 특히 tmux 자체가 모델 품질·독립성·구독 토큰 효율을 높였다는 증거를 얻은 것은 아니다.

## 이미 있는 것은 다시 만들지 않는다

초기 분석 기준에도 원장 단일 소유권, attempt에 묶인 조건부 완료, 입력 전달·빈 답·모델 불일치 수용 관문, 재시작 재조정과 queued 명시적 재개, 봉인 투영이 들어 있었다. 관련 코드를 직접 읽었다(EVIDENCE P02–P06). 따라서 앞선 A1 리뷰의 문제를 미수정 상태로 반복하거나 tmux가 그것을 대신 해결한다고 설명하지 않는다.

유지할 구조는 다음이다.

```text
Windows 화면
    │ 제한된 제어 요청 + 안전한 상태 조회
WSL Python controller ─ SQLite journal
    │ 기존 runner / adapters / isolation
    ├─ bubblewrap → 참여자 CLI A
    └─ bubblewrap → 참여자 CLI B
```

기존 N1 실행기를 재사용해 남은 N2–N4를 우선하고, 그 과정에서 재접속·적용 설정 설명 같은 작은 기능을 넣는다. 별도 workflow engine, event broker, PTY renderer, tmux control-mode parser를 먼저 만들 필요는 없다.

## tmux를 직접 도입하는 경우의 판단

**조건부로 유용:** 신뢰한 개발자가 전용 tmux 세션에서 **controller 터미널만** 유지하는 운영 보조. terminal/SSH 연결을 끊어도 작업을 이어 보는 목적에는 맞는다. 다만 전용 socket·환경·설정·scrollback·토큰 출력의 신뢰 범위를 확인해야 한다. 이번에 설치하거나 시험한 것은 아니다.

**현재는 보류:** 각 모델을 tmux pane에서 실행하고 `send-keys`/`capture-pane`으로 조종하는 방식. 현재의 분리된 stdin/stdout/stderr·구조화 결과·자손 종료 계약에 PTY와 추가 server의 복잡성을 더한다. 실제 PTY 요구가 확인될 때만 별도 후보로 검증한다.

**채택하지 않을 결합:** bubblewrap 안의 tmux client가 **밖의 tmux server socket**에 연결해 실제 CLI를 실행시키는 방식. client가 격리됐다는 사실은 외부 server가 만든 CLI의 격리·종료 증거가 아니다. 참여자에게 controller의 tmux socket을 제공하지 않는다. [근거·topology 분석](ANALYSIS.md)

## 가져오면 안 되는 오해

- **세션/창/read-only 접속은 보안 격리가 아니다.** 공식 FAQ는 socket 접근자를 완전히 신뢰해야 한다고 설명한다. `no-output`도 출력 억제이지 접근 권한 제거가 아니다(EVIDENCE T03·T04).
- **pane 종료·명령 성공·wait-for 신호는 유효한 답이나 정족수의 증거가 아니다.** 지금 controller의 입력·결과·자손 종료 관문을 유지한다(T03·T10–T14, P02).
- **터미널 화면은 원본 결과 원장이 아니다.** PTY·escape·붙여넣기·EOF·stderr 채널을 따로 검증해야 한다. hidden 변수나 verbose log를 비밀 저장소로 취급하지 않는다(T07·T11–T13).
- **detach는 영구 checkpoint가 아니다.** tmux server·WSL·호스트 종료 이후의 복구나 AI 서비스 내부의 생각실패를 해결하지 않는다. GitHub 중간 커밋과 원장 복구는 계속 필요하다(T02·T10, 적용 범위).

## 다음 작업 권고

**현재 N1을 재사용하여 N2–N4를 완성하면서, 재접속의 중복 호출 방지·적용 설정 설명·상태 탐색을 작은 작업으로 추가한다.** 먼저 가짜 CLI와 임시 원장으로 검증한다. 조회 성능이 문제가 되는지 측정한 뒤에만 상태 push를 검토하고, tmux 운영 보조나 PTY backend는 별도 필요성이 확인될 때 선택한다.

[적용 계획](ADOPTION_PLAN.md)에는 단계별 완료 조건과 수용 시험을 남겼다. 이 시험 목록을 실행된 결과로 읽지 않는다. tmux 코드의 직접 복사·바이너리 배포도 이번 범위가 아니다. 향후 복사한다면 실제 파일별 copyright/permission notice와 포함된 제3자 파일의 조건을 확인·보존한다(EVIDENCE T15).
