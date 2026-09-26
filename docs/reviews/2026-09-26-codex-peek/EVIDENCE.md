# 근거·재현·한계

2026-09-26 · ChatGPT 웹 검토 · [PR #102](https://github.com/inlight37-design/decision-model_lab/pull/102).

## 증거를 구분하는 법

- **게시자 자료:** 사용자 첨부 PDF의 설명·벤치 수치·화면. 저자의 보고이며 이번 세션에서 모델 벤치를 재실행하지 않았다.
- **소스 확인:** 고정 SHA의 코드·테스트·CI 정의를 직접 읽었다. 주석의 과거 관측은 현재 사용자 기기의 관측으로 올리지 않는다.
- **이번 실행 관측:** GitHub 배포 ZIP/원본 blob 대조, 제한된 원본 함수/훅의 대역 평가, JavaScript 구문 분석. 모델·설치·실제 훅 등록은 실행하지 않았다.
- **우리 제안:** ANALYSIS의 평가와 ADOPTION의 우선순위·수용 시험. 아직 우리 앱에 구현하거나 효용을 증명한 기능이 아니다.

## 고정 대상과 입수 경로

| 대상 | 정확한 값 |
|---|---|
| upstream | `kimbyungsu/codex-peek@eb7cec1da0b13d2765eaab770c58d177024f423e`, package 0.1.103 |
| 우리 main 시작점 | `435ba02f50d287f62dce7512a0ceae9b9c2f164b` |
| 진행 중 #101 기준점 | `8fc945d410bec31d7f104199a684e9aab4f5b9a3` |
| 분석 브랜치 | `chatgpt/codex-peek-review-20260926`, 위 #101 head에서 분기 |
| upstream CI run | [35617727790](https://github.com/kimbyungsu/codex-peek/actions/runs/35617727790), head가 위 upstream SHA와 일치, API에서 completed/success 확인 |
| 다운로드 artifact | ID `10647629094`, 이름 `vsix`, ZIP 2,584,439 bytes, 안에 `codex-bridge-0.1.103.vsix` |
| ZIP SHA256 | `b49aff89f98f4d281ac8e0e4169b830ac5168332dc13c72645d8944eef3ae5fe` — GitHub metadata와 로컬 계산 일치 |
| 원본 코드 교차 대조 | `bridge/codex-bridge.js` Git blob `481801fa92fda2b7422b49d83656187c9184adc2`; `bridge/contract-lib.js` `a08a1972d2ca3d94d31437c492eb7658912d3cb6`; package `424083a4475bd85462658497f071ddd1d6655112` |
| 라이선스 표기 | package 및 배포 `LICENSE.txt`에 MIT. 이번 PR은 외부 엔진·확장·PDF·이미지 원본을 재배포하지 않는다 |

독립 컨테이너의 git clone은 GitHub DNS 해석 실패로 중단됐다. 권한이 없다고 단정하거나 사용자 PC를 대신 건드리지 않고, **연결된 GitHub 도구로 고정 CI artifact를 내려받아 압축만 풀었다**. 경로 이탈 항목을 확인하고 설치 없이 읽었다. 이 경로는 전체 저장소 clone이나 설치 검증을 대체하지 않는다. 배포물에는 원본 bridge JS와 컴파일된 out JS가 함께 있다. out JS를 TS 원본과 바이트 동일하다고 주장하지 않는다.

## 읽은 핵심 근거

| 항목 | 파일·범위 또는 함수 |
|---|---|
| 설치/되돌림/실행 사본 | `install.js` 1–150, 752–993: OUR_HOOKS, cmdInstall, runDoctor, bridgeRuntimeParity, cmdUninstall |
| 실행·결과·연결 | `bridge/codex-bridge.js`: withContract, readCanonicalEnvJob, readDurableEnvJob, writeProof, modelArgs, runCodex/runClaudeVerifier, cmdAskStart/cmdAskWait, 환급 분기 |
| proof·계약·수칙 | `bridge/contract-lib.js`: strictProofV2/strictReceiptV1, durableProofGate, draft/approval 전이, freeze, deriveRoundType, 처분, 명시적 rule-propose |
| 종료/안내 경계 | `bridge/verify-guard.js`: checkProof, mtime 근사, cap closeout, 반복 차단 해제; `codex-guard.js` 전문 |
| job 복구 | `bridge/ask-job-worker.js` 199–278: selector/verifier deadline, primaryCheckpoint와 challenge 실패의 분리 |
| 기억/근거 | `map-provenance.js`: reducer·tombstone·registerAutoEntries·mergedEntriesFor·approval harvest; `map-enrich.js`: sourceFp/excerpt 결속과 후보/증거 관문 |
| 제한 검색 | `map-retrieval.js`: selectCandidates, 축별 선택·중복 방지·빈 관련성 결과 |
| 수칙/화면 | `curation.js`: 입력·결과 충돌·provisional/result/proposed·receipt; `rules-flow.js`: 순수 계산과 실제 verify selection 구분 |
| 인용 | `citation-check.js`: 허용 root·줄·식별자·약한/미확인 근거 구분 |
| upstream 시험 근거 | `package.json`의 test/pretest/posttest 목록, `.github/workflows/ci.yml`, `tests/memory-authority.test.js` 1–105. 시험 소스 전체를 로컬 실행하지 않았음 |
| 우리 기준 | `AGENTS.md`, `docs/COLLABORATION.md`, `NEXT-SESSION.md`, reviews index, core/app README, `core/contract.py` 1–96, `app/controller.py` 1–115, `app/synthesis.py` 1–110, #101 PR/branch |

정확한 upstream 링크는 [ANALYSIS](ANALYSIS.md) 각 절에, 우리 코드 링크는 [ADOPTION](ADOPTION.md) 1절에 있다. 이것은 **주요 경로의 심층 정적 검토**이지 모든 저장소 코드·OS·provider에 대한 전수 보안 감사가 아니다.

## 현행 코드에서 특히 주의할 것

**해소한 blocker를 자동으로 전부 수칙 후보로 만드는 것은 현행 동작이 아니다.** `reconcileMemoryCandidates()`의 본 스캔은 폐지돼 있고, `ruleProposeCandidate()`는 명시적 상신의 자격·세대·원문·askId 등을 검사한다. `tests/memory-authority.test.js`는 자동 스캔/공급 0, 비blocker·구형 무결속·다른 세대·중복의 거절을 직접 검사한다. 따라서 PDF의 '관찰→기억→수칙' 도식을 모든 대화를 자동 정책으로 승격하는 시스템으로 요약하면 부정확하다. 관찰 수집, 기억 참고, 수칙 후보 공급, 사용자 승인, 실제 주입은 서로 다른 경로다.

근거: [현행 코드](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/contract-lib.js#L4835-L5063), [원본 시험](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/tests/memory-authority.test.js#L50-L104). 읽은 시험은 코드 계약을 보여 주며 이번 실행에서 upstream 시험 전체를 재현했다는 뜻은 아니다.

또한 `ask-job-worker`의 checkpoint recovery는 **주 검증 결과/proof가 이미 기록됐는데 후속 challenge가 실패한 경우를 구분**한다. 이를 '아무 timeout이나 성공으로 인정한다'고 요약하면 틀리다. 우리에게도 하위 단계별 상태 분리는 유용하지만 프로세스 전체 종료 확인을 생략할 근거는 아니다.

## 이번 오프라인 probe

환경: 별도 웹 컨테이너 Node **v22.16.0**. [`probes.cjs`](probes.cjs)는 원본 파일의 고정 Git blob 해시를 확인한 후, 읽고 감사한 순수 함수와 mock stdin/exit의 훅만 VM에서 평가한다. 코드 조각의 `require`는 허용한 항목만 제공한다. **VM을 일반적인 악성 코드 보안 격리기로 주장하지 않는다.** CLI·네트워크·설정 파일·실제 사용자 홈에는 접근하지 않는다.

실행:

```bash
node probes.cjs /path/to/unpacked-vsix/extension
```

`npm install`이나 `node install.js`가 필요하지 않다. 원본 전체 contract/extension 엔트리포인트를 실행하지 않는다. 결과 정본은 [`probe-results.json`](probe-results.json)이다.

| probe | 실제 관측 | 해석 |
|---|---|---|
| P01 | `codex exec synthetic-input` 데이터에 exit 2 | 기본 직접 호출 차단의 양성 대조 |
| P02 | `echo codex-bridge; codex exec synthetic-input` 데이터에 exit 0 | `isBridge` 부분문자열이 직접 호출 검사를 면제하는 국소 반례. 명령 문자열은 실행하지 않았음 |
| P03 | malformed JSON 입력에 exit 0 | 훅 파싱 실패의 fail-open 확인 |
| P04 | preview/curate/다른 repo의 뒤쪽 행을 무시하고 `ask-real` 1건 선택 | 실제 검증 영수증의 scope/종류 분리 |
| P05 | repo scope 없으면 null | 불명확한 소속을 현재 기록으로 세지 않음 |
| P06 | 입력 순서를 뒤집어도 gen 10 선택 | 문자열 순서가 아닌 세대 숫자 선택 |
| P07 | 주제 철회로 0건, 철회 취소로 gen 10 복원 | 순수 reducer의 철회/복권 동작. 파일 거래 전체 시험은 아님 |
| P08 | 관련성 없는 노드만 주면 selected 0/fallback true | 무관 후보로 상한 채우기 방지 |
| P09 | 정상 proof v2 구조 수락 | strict schema 양성 대조. 실제 proof gate 전체 수용은 별도 |
| P10 | turnId 누락 또는 알 수 없는 키 추가 시 거절 | 구조 검사 확인. 내용의 사실성을 판정하지 않음 |
| 구문 분석 | 배포 bridge/out JS 71개 CommonJS 파싱 성공 | 함수 실행/통합 시험·타입 검사·설치 성공의 대체가 아님 |

**'10 probe pass'는 좋은 동작과 한계의 관측이 예상대로 재현됐다는 뜻**이다. P02/P03은 제품의 안전성 합격이 아니다. 초기 구문 분석기는 CommonJS 파일을 일반 script로 해석해 top-level return을 잘못 거절했다. 검사기를 CommonJS wrapper로 수정해 다시 실행했다. 이것을 upstream 구문 오류로 보고하지 않는다.

## PDF 근거 범위

첨부 제목: `[AI 코딩 하네스] Claude Code ↔ Codex Bridge - AI 활용 마이너 갤러리.PDF`, 21쪽. 게시 시각 표기는 2026-09-26 14:23. PDF는 사용자 제공 자료로 검토했으며 저장소에 전문/화면을 복제하지 않았다.

- 1–5쪽: 통제 조건·A/B/Cold/Warm·제외·Wilson 범위·Real Lite·F6·제품 전체 성능이 아니라는 단서.
- **6쪽 도식:** 변경 감지·영향지도·관찰 일지·확정 MAP, 검증·재판단·사용자 승인 경로. 글자 추출만 보지 않고 페이지 이미지를 확인했다.
- **7쪽 도식/FAQ:** 프로젝트 종류별 기대효용, 아직 실제로 확인하지 못한 유형, 모델 호출과 데이터 전송의 조건을 구분한다. 이를 모든 유형에서 실증됐다고 요약하지 않는다.
- 8–18쪽: 역할/언어·실시간 상황·수칙·MAP·세션 연결·통계·모델/추론·대기시간 화면. PDF 화면을 우리 앱의 구현 화면으로 사용하지 않는다.
- 19–21쪽: 게시판 주변 내용으로 핵심 근거에서 제외.

벤치 원시 trial 로그·제외 전 판정표·전체 과제/기억 pack을 확보해 독립 재판정하지 않았다. Wilson 구간의 소개 수치는 원문 설명으로 보고했으며, 표본 독립성·외부 과제 일반화·현재 제품의 효용을 검증한 것으로 쓰지 않는다.

## 하지 않은 것

upstream 설치/확장 활성화/로그인/doctor 실기동, 실제 Codex·Claude·DeepSeek 호출, 실행 중 사용자 앱의 상태 확인·중지·변경, 전체 upstream npm test, Windows/WSL 설치·병렬·자손 종료·장시간 시험, upstream 보안 전수 감사, PDF 벤치 재실행은 하지 않았다. 우리 제품의 새 기능·실행 허가·스키마도 이 검토에서 바꾸지 않았다. #101의 선행 변경은 그 PR의 작업이다.

## 체크포인트와 인계

- `fa4248b`: 안전 범위·고정 기준선·다음 분석 항목을 먼저 저장.
- `7ba3a46`: 실제 엔진·기억·수칙·영수증·설치/격리 경계·벤치 분석 저장.
- `5bce1eb`: 기존 주인 모듈 대응·작은 적용 순서·미실행 수용 시험 저장.
- 이 문서 뒤의 재현 파일·목록·인계·최종 확인은 같은 PR에서 완료한다. 최종 CI 상태와 정확한 head는 PR Checks가 기준이며 이 날짜 기록에 미래 성공을 미리 적지 않는다.

다음 작업자는 [ADOPTION](ADOPTION.md) 7절부터 판단한다. 분석 결과를 설치 승인이나 전부 구현하라는 요구로 해석하지 않는다. 원래 진행 중인 역할판 PR/카드와 실제 최신 main을 먼저 확인한다.
