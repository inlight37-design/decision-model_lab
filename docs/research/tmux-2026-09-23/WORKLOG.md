# tmux 조사 작업 기록 — 2026-09-23

작성: ChatGPT (GPT-6 Astra Pro). 사용자의 tmux 공식 위키 조사·프로젝트 적용 후보 문서화 요청에 따라 별도 브랜치 `chatgpt/tmux-patterns-20260923`에서 작업한다. main에 직접 쓰거나 병합하지 않는다.

## 시작 기준

- 프로젝트 기준: `cd94190bf10b1bacc812ee698e4c6dc6a86260ca`.
- 시작 시 열린 PR은 없었다. PR #7 뒤 A1 반영 브랜치가 main에 병합된 상태다. 이전 리뷰의 결함을 현재 미수정 결함으로 재사용하지 않는다.
- 사용자 확정 사항: WSL2 controller, Linux-native 구독 CLI 직접 exec 우선, bubblewrap, controller 단일 상태 권위, 독립 초안 봉인, 유료 fallback 없음, 원본 앱 수동 참여 보존.
- 접근: GitHub 연결·공식 웹 문서·별도 웹 컨테이너. 사용자 PC/WSL/실제 모델/로그인은 접근하지 않음. 이 컨테이너의 GitHub git 접근은 DNS 오류로 실패했고 tmux 실행 파일도 발견되지 않았다. 현재까지 tmux 실행 검증은 하지 않았다.

## 1차 탐색에서 확인한 것

- 공식 위키 Home/Getting Started/Control Mode/FAQ/Formats/Recipes/Clipboard/Installing/Contributing을 탐색했다. 적용 판단은 이후 고정 release의 매뉴얼·소스와 대조한다.
- 최신 GitHub release API는 `3.7c`(2026-08-17 공개, prerelease=false)를 반환했다. 웹에서 반환된 위키 Home에는 `3.7b`가 적혀 있어 Home만으로 최신 버전을 정하지 않는다.
- Formats에는 3.8 기능이 섞여 있고 검색에서 노출된 Events 문서는 3.8 이상을 대상으로 한다. 안정 release와 개발 문서의 기능을 구분한다.
- 유망한 개념: 화면 연결과 실행 수명의 분리, 단일 server와 여러 client, 안정 식별자, 명령 응답/비동기 사건의 분리, 느린 화면의 출력 제어, 실패 기록 보존, 상태 중심 탐색.
- 중요한 경계: tmux socket 접근은 완전 신뢰를 전제로 하며 read-only/server-access는 적대적 사용자 격리 수단이 아니라는 공식 FAQ 설명을 확인했다. 독립 초안 격리에 세션/창 분할을 대신 쓰지 않는다.

## 다음 작업

1. 3.7c tag를 commit으로 고정하고 control protocol, 출력·자손 종료·환경·socket·명령 실행·라이선스 관련 매뉴얼과 소스를 확인한다.
2. 현재 controller/store/server/isolation과 A1 반영 기록을 읽어 이미 있는 것·가져올 것·가져오지 않을 것을 구분한다.
3. 원문 사실/코드 관측/프로젝트 제안을 분리한 분석과 작은 적용 순서·합성 검증 항목을 작성한다. tmux 도입 자체를 선행 의존성으로 만들지 않는다.
4. 조사 문서와 인계 연결을 같은 PR로 제출하고 최종 head CI를 확인한다. 실제 모델 호출과 운영 코드 변경은 하지 않는다.

이 파일은 첫 체크포인트다. 완료 상태는 이후 PR과 최종 기록으로 확인한다.
