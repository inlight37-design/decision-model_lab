# 비교 근거와 재검증 범위

2026-09-26 · [비교와 판단](README.md)의 근거 기록. 이전 리뷰가 보고한 결과, 이번에 읽어 확인한 코드, 이번에 재실행한 결과를 구분한다.

## 1. 자료 보존과 기준선

- A는 PR #102 head `173715a5813ac4a8d946e2e78afc90d5fcd2db0d`의 날짜 기록이다. 원문을 수정하지 않고 새 비교 문서와 상위 리뷰 목록에서 연결한다.
- B는 사용자 지정 outputs의 [독립 리뷰](codex-peek-independent-review-ko.md), [증거 ZIP](review-evidence.zip), [원 manifest](review-manifest.json)이다. import 전에 manifest에 적힌 본문·ZIP SHA256이 실제 파일과 같은지 확인했다.
- 독립 리뷰 본문과 ZIP은 바이트가 그대로다. manifest는 저장소 규칙에 맞춰 CRLF만 LF로 바꿨다. 원본/저장본의 해시와 바이트 수는 [import-manifest.json](import-manifest.json)에 기록했다. JSON의 당시 시험·환경 수치는 역사 기록이며 이번 실행 실적으로 재사용하지 않는다.
- B의 `prior_reviews_consulted: false`는 **B 작성 당시**에 관한 사실이다. 이번 비교는 A/B 모두를 읽었다. 이것을 새로운 blind review라고 부르지 않는다.
- 두 리뷰의 외부 대상은 `eb7cec1da0b13d2765eaab770c58d177024f423e`로 같다. 우리 앱의 B 기준은 `435ba02f50d287f62dce7512a0ceae9b9c2f164b`, A의 선행 역할판은 `8fc945d410bec31d7f104199a684e9aab4f5b9a3`다. #101→#102 사이 `app/`, `core/`, `contracts/`, `tests/` 차이는 없다.
- 이번 브랜치는 공유 인계·리뷰 목록을 함께 수정하므로 협업 규칙에 따라 #102의 고정 head에서 분기했다. PR 대상은 main이다. #101·#102가 병합되기 전에는 main diff에 선행 변경도 보인다. 이번 고유 범위는 이 비교 폴더, 리뷰 목록, 인계 문서다.

접근 범위는 Codex 데스크톱의 현재 Windows PC 파일·PowerShell·Git/GitHub CLI와 GitHub 플러그인이다. 사용자가 지정한 로컬 자료와 별도 작업 clone을 사용했다. 현재 PC를 과거 관측 기록의 `aux-pc`와 같다고 추정하지 않았다. 앱 UI 자동화는 필요 없어 사용하지 않았다. 실제 모델 CLI 설치·로그인·WSL 격리는 이번에 확인하지 않았다.

## 2. 주장별 원문·소스 위치

모든 외부 소스 링크는 같은 고정 commit이다. 아래 표의 코드 열은 정적 확인 위치이며 그 자체가 전체 실행 재현을 뜻하지 않는다.

| 쟁점 | 두 리뷰에서 읽을 곳 | 코드와 판정 범위 |
|---|---|---|
| proof의 가치와 한계 | A ANALYSIS §4.1; B 한계 §1 | [proof 기록·job 결속](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/codex-bridge.js#L377-L457), [응답 후처리](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/codex-bridge.js#L4825-L4867), [Codex Stop](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/codex-hook.js#L553-L592). 응답 완료와 의미상 통과는 다름 |
| 내용 변경 탐지 | A ANALYSIS §4.1·ADOPTION §3.1; B 한계 §2 | [변경 관측](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/codex-hook.js#L172-L186), [proof 최신성](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/contract-lib.js#L1665-L1695). tracked 양성 대조와 non-Git/untracked 반례를 함께 유지 |
| 인용·경보 해소 | A ANALYSIS §4.2; B 한계 §3 | [citation-check](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/citation-check.js). `citationCheck`의 위치 검사와 `resolvedByNext`의 경보 처리. 의미/사실/원 지적 해결은 별도 |
| 직접 호출 가드 | A EVIDENCE P01–P03; B 한계 §4 | [codex-guard](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/codex-guard.js). 문자열을 데이터로 넣은 국소 반례이며 명령을 실행한 공격이 아님 |
| 수칙 자동 공급 폐지 | A EVIDENCE '현행 코드'; B 기억 권위 관련 절 | [reconcileMemoryCandidates/ruleProposeCandidate](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/contract-lib.js#L4835-L5063), [memory-authority 시험](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/tests/memory-authority.test.js#L50-L104). 자동 MAP 처리와 다른 권위 층 |
| MAP의 자동 처리 | A ANALYSIS §6; B 한계 §6 | [관찰 신호](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/ledger-events-core.js#L57-L109), [MAP 분류](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/map-pipeline.js#L399-L409). 사람 승인 없는 추론 경로가 있다고 모든 수칙이 자동 채택되는 것은 아님 |
| 실제 선택 영수증 | A ANALYSIS §8·EVIDENCE P04–P05; B 관련 기억·단계 표시 | [rules-flow](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/rules-flow.js#L1-L55). repo/workspace scope와 verify receipt를 확인. 실제 독해까지 증명하지 않음 |
| 예산 `untracked` | A ANALYSIS §7; B 한계 §9 | [예약](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/contract-lib.js#L765-L833), [호출 계속 경로](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/codex-bridge.js#L4029-L4068). 이번 비교에서 저장 실패를 새로 주입해 실행한 시험은 아님 |
| 운영 문서 불일치 | A 설치 분석과 별개; B 한계 §7 | [SECURITY](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/SECURITY.md), [DeepSeek fetch](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/deepseek-bridge.js#L76-L90), [PRIVACY](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/PRIVACY.md). 기능·문서 불일치이지 악성 행위 판정 아님 |
| 기존 실행 계약/자료 | A ADOPTION §§1–3; B '이미 있는 것' | [Plan](https://github.com/inlight37-design/decision-model_lab/blob/173715a5813ac4a8d946e2e78afc90d5fcd2db0d/core/contract.py#L1-L96), [보고서](https://github.com/inlight37-design/decision-model_lab/blob/173715a5813ac4a8d946e2e78afc90d5fcd2db0d/app/report.py#L34-L79). 새 검토 receipt의 재료와 새 검토 실행은 구분 |
| #101에서 추가된 입력 확인 | B는 이전 main을 분석; A는 #101을 반영 | [prepare_run/confirmation](https://github.com/inlight37-design/decision-model_lab/blob/173715a5813ac4a8d946e2e78afc90d5fcd2db0d/app/controller.py#L310-L417), [tasks schema](https://github.com/inlight37-design/decision-model_lab/blob/173715a5813ac4a8d946e2e78afc90d5fcd2db0d/app/store.py#L29-L66). 전체 TaskSpec 구현은 아님 |
| 합성에 이미 있는 상태 | B의 지적별 처리 제안을 현재 코드와 대조 | [claim/quote/disposition/factual_check](https://github.com/inlight37-design/decision-model_lab/blob/173715a5813ac4a8d946e2e78afc90d5fcd2db0d/app/synthesis.py#L203-L271), [human_reviewed](https://github.com/inlight37-design/decision-model_lab/blob/173715a5813ac4a8d946e2e78afc90d5fcd2db0d/app/controller.py#L1010-L1019). 읽었다는 사건/인용 일치/지적 해결/사실 판정은 다름 |

A 원문: [ANALYSIS](../2026-09-26-codex-peek/ANALYSIS.md), [ADOPTION](../2026-09-26-codex-peek/ADOPTION.md), [EVIDENCE](../2026-09-26-codex-peek/EVIDENCE.md). B 원문: [독립 리뷰](codex-peek-independent-review-ko.md).

## 3. 과거 검증과 이번 검증의 구분

| 구분 | 확인한 것 | 여기서 주장하지 않는 것 |
|---|---|---|
| A의 과거 기록 | Node v22.16.0, 제한된 probe와 배포 JS 구문 검사. 원본 JSON·스크립트와 결과 해석을 대조 | 이번 PC에서 배포물의 모든 JS를 다시 검사했다는 주장 |
| B의 과거 기록 | Windows·Node v24.19.0의 선택 upstream 시험과 우리 선택 시험, 별도 engine/citation 반례. 제공 manifest·ZIP 보존 | 그 선택 시험을 이번에 전부 반복했다는 주장. B의 미완료/미실행 검사를 성공으로 변경하지 않음 |
| A의 과거 PR CI | GitHub API에서 [run 36222890168](https://github.com/inlight37-design/decision-model_lab/actions/runs/36222890168)의 head가 `173715a5813ac4a8d946e2e78afc90d5fcd2db0d`, event가 `pull_request`, conclusion이 `success`임을 이번에 확인 | 그 CI를 이번 새 비교 PR의 CI로 재사용하지 않음 |
| 이번 경계 재실행 | 같은 upstream SHA에서 가짜 provider를 사용한 engine 사례, citation 경계, A의 source-only probe를 확인 | 실제 모델 평가, 전역 설치, 전체 upstream 시험, 제품 전체 보안 합격 |

경계 재실행의 정확한 명령·결과·제외는 아래 기록을 따른다. 숫자는 서로 단위가 다른 시험의 합격 점수로 합산하지 않는다. 같은 fixture 반복이므로 독립된 과제 표본을 늘린 실험도 아니다.

## 4. 이번 경계 재실행 결과와 재현 방법

Windows·Node v24.19.0, 위 고정 upstream source checkout에서 실행했다. [engine/citation 결과](verification/current-verification.json)와 [A의 source-only probe 결과](verification/pr102-current-verification.json)를 보존한다.

| 재현 | 이번 관측 | 제한 |
|---|---|---|
| 유효한 fail 답 | `machineEffective: fail`, `proofStatus: success`, 판단 대기 빈 목록, Stop 차단 없음 | 합성 설정의 Codex 구현/core/승인 envelope 없는 경로 |
| 전체 durable 작업 흐름 | `ask-start → worker → fake provider → ask-wait → Stop`, job `succeeded`, job/wait exit 0, 반환문에 실패 verdict 유지, Stop 차단 없음 | 실제 provider가 아닌 고정 응답 Node 대역. 실패를 통과 verdict로 바꾼 실험이 아님 |
| proof 뒤 내용 변경 | non-Git와 `?? newcode/` 내부 파일 변경은 미차단, tracked 대조는 `proof-stale` 차단 | 내부 파일 내용 변경과 폴더 mtime 불변 조건. 모든 untracked 변경의 일반화 금지 |
| 인용의 의미 | 덧셈 함수에 대한 거짓 암호화 설명도 위치 검사 `ok` | 위치 검사 자체의 계약 위반은 아님 |
| 빈 인용 지적 | 정상 파싱된 빈 목록에 `resolvedByNext`가 `recheck-clean` | 함수의 경보 해소 반환이며 원 지적의 수정/반박 증명은 아님 |
| A의 probe | 원래 10개 assertion과 6개 source blob pin을 바꾸지 않은 재실행에서 같은 관측 | 반례의 예상 재현도 `pass`에 포함. 제품 안전성 합격 개수가 아님 |
| A의 구문 분석 | 이번 source의 bridge JS 53개 파싱 | 과거 배포물 bridge/out 71개 검사와 다른 범위 |

A 원본 probe는 풀어 둔 VSIX extension을 인자로 요구한다. source clone에서 그대로 실행한 첫 시도는 모든 assertion 뒤 마지막 `out/` 구문 탐색에서 ENOENT로 종료했다. 전체 성공으로 세지 않았다. 재실행용 wrapper는 구문 탐색 배열만 `bridge/out`에서 `bridge`로 좁히고 제한 문구를 바꿨다. 기대 assertion은 그대로이며 변경 전후 스크립트 해시를 결과에 기록했다.

B의 engine fixture는 원본 ZIP에서 읽고 source 위치와 임시 결과 위치만 바꿨다. wrapper는 가짜 provider와 반환값을 검사한다. [추가 preload](verification/synthetic-process-guard.cjs)는 자식 Node에도 상속해 감사한 코드의 주요 동기 파일 접근·실행 파일·네트워크 모듈 사용을 제한한다. 이는 방어 보조이며 OS 보안 sandbox가 아니다. 원본 Peek checkout의 추적 파일은 재실행 전후 변경이 없었다.

Node와 Git이 있는 별도 작업 폴더에서 ZIP을 풀고, 동일 upstream SHA의 source checkout을 준비한 뒤 실행할 수 있다. 설치기나 실제 모델 CLI는 필요 없다. 출력 폴더는 별도의 새 임시 위치로 지정한다.

```text
node verification/run-boundary-repros.cjs <고정-Peek-source> <review-evidence.zip-추출폴더> <새-출력폴더>
node verification/run-pr102-probes.cjs <기존-102-probes.cjs> <고정-Peek-source> <새-출력폴더>
```

첫 wrapper와 preload는 같은 폴더에 둔다. 기존 probe는 [../2026-09-26-codex-peek/probes.cjs](../2026-09-26-codex-peek/probes.cjs)다. 결과의 시각·작업 ID·임시 경로는 실행마다 달라질 수 있다. 원본 fixture와 wrapper를 실행 전에 읽는 절차는 생략하지 않는다. 다른 OS에서 같은 결과가 나는지는 이번에 검증하지 않았다.

## 5. 실행하지 않은 것과 남은 판단

실제 Codex/Claude/DeepSeek provider 호출, 설치기·VSIX 활성화, 사용자 로그인 폴더를 연결한 진단, 실제 WSL 격리/계정 한도 관측, 원시 벤치 trial 재판정, 새 UI 실사용과 품질 비교는 하지 않았다. 제품 코드·운영 원장·관측 허가를 바꾸지 않았다. 분석에서 제시한 TaskSpec·receipt·기억·교차검토 확장은 모두 후보이며 이번 문서의 실행 결과가 아니다.

다른 작업의 원본 clone과 outputs는 읽기만 했다. 재현은 이번 작업의 별도 임시 폴더에서 실행했고, fixture의 home 경로는 합성 경로로 지정했다. 이를 OS 보안 격리 검증이라고 주장하지 않는다. PR은 main을 대상으로 올리되 다른 세션 브랜치와 main에는 직접 쓰지 않는다.
