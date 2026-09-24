# Windows 검사 복구·계정 한도·실제 Codex/Claude 병렬 응답

2026-09-24 · Codex 데스크톱 · 사용자 Windows PC와 로컬 Ubuntu-24.04 WSL 직접 관측. [PR #39](https://github.com/inlight37-design/decision-model_lab/pull/39)는 PR #38 head `b5014de1b5cfeebbf42667f8f4582c44bdad946a` 위에서 시작했다. main·다른 세션의 브랜치는 수정하지 않았다.

## 결과와 범위

실제 구독 Codex·Claude Code를 동시에 실행해 양쪽 답을 수용하고 함께 공개했다. 진행 중에는 초안이 API에 나오지 않았고, 브라우저에서 원문·모의 대조표·계정 한도·문맥 미확인 표시를 확인했다. **독립성 확인은 0이며 `include_unverified`로 답 2개를 센 것이다.** 실제 모델 합성·외부 사실 검증·품질 향상은 주장하지 않는다.

| 증거 | 직접 확인한 것 | 남는 한계 |
|---|---|---|
| [Claude 권한](claude-permission.json) | 설치판 2.1.280, 같은 `claude-code@126be128bed7`, argv 변형 없음, init의 Read만 노출·MCP 없음·dontAsk, 지정한 합성 peer 파일의 Read 거절, 정상 입력 전달·namespace 종료 | Write/Bash가 노출되지 않은 구성이다. 사용 가능한 Write 도구가 거절됐다는 주장은 하지 않는다. plugins/agents 잔존, 최종 문맥 전체는 미확인 |
| [병렬 실행](parallel-observation.json) | 두 provider 동시 running, 봉인 중 API 검사, 양쪽 accepted/revealed, 각 1/1·전체 2/2 상한 소진 | 합성 질문 한 건이다. 독립성·답 품질의 통계적 증거가 아니다. Codex 제공 모델은 미보고 |
| Codex 계정 응답 | 격리 app-server의 구독 계정 확인 뒤 한도 창 메타데이터 수신, 화면 표시와 오래된 관측값 전환 | 계정 식별자·실제 잔여 비율·원시 응답은 공개 기록에서 제외. Claude 계정 한도는 미연결 |
| [종료 확인](cleanup.json) | 참여자 PID namespace 종료, 서버 프로세스/포트 닫힘, 원장 잠금 재획득 | 검증 스크립트 종료 경로의 예외와 별도 확인은 아래 기록 |

WSL native Codex 0.156.1, Claude Code 2.1.280을 사용했다. Windows에서도 별도 Codex 0.155.1과 Claude Code 2.1.280 설치를 확인했으나 실제 참여자는 WSL Linux 실행 파일만 사용했다. Codex 요청은 `gpt-6-luna`(제공 모델 미보고), Claude 요청/보고는 `claude-sonnet-5`였다. 서로 다른 모델을 자동으로 선택하거나 유료 API로 대체하지 않았다.

## 수정한 동작

1. PR #38의 `WINDOWS-CONSOLE.patch`를 PC에서 적용했다. `tools/check_encoding.py` stdout을 UTF-8로 설정하고 CP1252 성공/실패 출력을 회귀 검사한다. 원 패치 작성은 ChatGPT 웹 세션, 적용은 이 Codex 세션이다.
2. Python 3.13의 Windows `isabs('/home/...')` 변화 때문에 Linux 계획 fixture가 잘못 실패하던 시험을 POSIX 경로 정책으로 고정했다. Windows 임시 경로의 `RUNNER~1`/긴 이름 비교도 resolve 뒤 검사한다. 실제 격리·권한 검사나 CI job을 완화하지 않았다.
3. Codex 계정 helper는 격리에 연결한 실제 실행 파일 경로로 자식을 실행한다. 호스트 symlink만 넘겨 격리 내부에서 파일을 찾지 못하던 문제를 고쳤다. 제품 구현은 `app/codex_account.py`, 투영은 `core/quota.py`, 관측 CLI는 얇은 진입점으로 정리해 app에서 tools를 import하지 않는다.
4. 계정 UI는 사용자가 누른 조회만 metadata 프로세스를 시작한다. 인증된 GET은 캐시, POST 갱신은 single-flight·60초 간격, 관측 120초 초과/창 만료/조회 실패는 stale, 누락은 unknown이다. 남은 비율을 질문 횟수·토큰으로 환산하지 않는다. 같은 표시를 매초 다시 그리지 않아 live region 재안내도 줄였다.
5. Claude의 현재 실행을 `--output-format stream-json --verbose`로 바꾸고 init과 마지막 result를 함께 수용 검사한다. 허용 도구·dontAsk·MCP·실제 사용 도구가 계획과 다르면 답이 있어도 거절한다. 빠진 init/결과, 중복·뒤따르는 사건도 거절한다. b1 권한 probe가 같은 계획을 쓰는지 확인하고 지정 파일의 실제 CLI denial만 증거로 쓴다.
6. `LEGACY`를 확장하지 않았다. [새 manifest](manifest.v2.json)는 새 권한 관측의 정확한 판만 포함하고 Codex K46과 C3 failed를 보존한다. Claude 입력 폴더 없음/다른 옵션은 관측 범위 밖이다. 실제 모드의 기본 최소 인원은 설정된 CLI 참여자 수에 맞춘다.

## 실제 호출 회계와 재현 조건

사용자의 현 요청과 NEXT-SESSION §2.22의 승인으로 필요한 구독 호출만 했다. 모델 호출은 **Claude 권한 probe 2회, 최종 병렬 Codex 1회·Claude 1회**다. 각 권한 probe는 자기 상태 폴더와 상한 1을 사용했다. 첫 관측 요약은 보존했으나 WSL `/tmp`의 원시 기록이 세션 종료 뒤 사라져, 지정 peer 파일의 거절을 영속 상태 폴더에서 확인하는 두 번째 관측을 별도로 수행했다. 이미 쓴 상한을 초기화하거나 같은 상태에 approve를 다시 쓰지 않았다.

최종 실행은 새 원장, provider별 cap 1, 전체 cap 2, timeout 180초로 한정했다. 두 provider는 별도의 빈 읽기 전용 입력 폴더 하나씩을 받았다. 질문은 문서 검색의 키워드 개선과 벡터 검색 전환 중 무엇을 먼저 할지 묻는 가상 사례로, 개인 자료와 외부 도구 없이 답하게 했다. controller HTTP API로 시작·진행·공개·모의 합성을 실행했고 봉인 중 초안 키가 없음을 검사했다. Codex 약 11.3초, Claude 약 20.1초였고 둘 다 stdin complete·exit 0·tree empty였다. 모의 합성에는 추가 모델 호출이 없었다. CLI 토큰과 `client_estimate_usd`는 계정 실제 차감이나 API 청구가 아니다.

새로 실행할 때는 [app 안내](../../../app/README.md)의 설정과 준비 조회를 사용한다. 이번 manifest를 두 provider에 지정하되 각자 빈 input_dir 하나, 명시적 전체 모델 이름·provider별 상한·새 원장을 둔다. 날짜·CLI 버전·판이 달라져 준비 조회가 막히면 관측부터 갱신한다. 이번 소진 원장으로 재실행하지 않는다. 공통 자료가 있는 실제 질문까지 검증한 것은 아니다.

계정 조회는 initialize→account/read(`refreshToken=false`)→account/rateLimits/read만 허용했다. thread/turn 시작·로그인 변경·추가 크레딧 요청은 없고 inference 요청 수는 0이다. actual quota, raw stream, 인증 내용과 개인 경로는 저장소에 넣지 않았다. 최종 합성 질문의 원문 보고는 사용자 PC의 로컬 산출물로 보관했다.

## 실패·정정·종료

- 앞선 CI에서 runtime이 tools 진단을 import하는 구조, Windows Python 3.13 POSIX fixture, b1의 빠진 증거를 성공으로 보던 판정, Windows 짧은 경로 비교가 드러났다. 제품 주인 모듈 분리와 음성 회귀로 수정했으며 실패 run은 GitHub 이력에 남긴다. 마지막 정확한 head의 결과는 [PR Checks](https://github.com/inlight37-design/decision-model_lab/pull/39/checks)와 job 로그가 기준이다.
- 검증용 임시 스크립트가 종료 때 공개된 run을 cancel하려다 controller의 정상 거절을 받았다. 프로세스는 종료됐지만 정상 shutdown 함수까지 도달하지 못했으므로 완료로 간주하지 않고, 별도로 포트·남은 프로세스·원장 잠금 해제를 확인했다. 임시 스크립트도 공개 상태를 확인하고 finally에서 서버를 정리하도록 수정했다. 참여자는 그 전에 이미 namespace 종료를 확인한 상태였다. 이 오류로 추가 모델을 호출하지 않았다.
- [PR #38 기록](../2026-09-24-cli-unblock/README.md)의 Windows 패치 미적용·계정/병렬 응답 미관측은 당시 기록으로 보존한다. 현재 안내인 app/README·NEXT-SESSION·tools/w2/README·AGENTS와 색인은 이번 관측으로 정정했다. NEXT-SESSION 이전 원문을 보관했고 사용자 결정/금지 절은 유지했다.

## 검증과 미완료

Windows Python 3.12 전체 시험, WSL Python 3.12 전체 시험(`DML_REQUIRE_BWRAP=1`), 인코딩·설계 토큰·frontier·inventory dry-run·계약/출처·compile 검사를 사용한다. WSL에는 Node가 없어 JavaScript 시험은 skip이며 Windows와 CI의 Node에서 실행한다. OS 전용 skip은 구별한다. CI의 Linux Python 3.12/3.13·Windows Python 3.13 결과는 PR에 연결한다. 소스 변경 뒤 전체 검사를 다시 실행하며 통과한 head를 PR 본문에 명시한다.

브라우저는 Codex in-app browser에서 실제 응답 화면, 최소 인원 2, 상한 2/2, 독립성 확인 0, 모델 미보고, 계정 stale/unknown을 확인했다. 접근성 전수·다른 브라우저·대규모 원장 비용은 검증하지 않았다. 실제 모델 합성, C3 최종 문맥, 품질/비용 대조, 공통 자료 스냅샷은 후속이다.

공식 문서는 [Codex app-server](https://learn.chatgpt.com/docs/app-server)와 [Claude CLI reference](https://code.claude.com/docs/en/cli-reference), [headless 실행](https://code.claude.com/docs/en/headless)을 직접 확인했다. 문서의 지원과 위 설치판의 실제 관측을 구분한다.
