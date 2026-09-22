# v0.4 인계 — 상급 모델 협업 확장

기준일 **2026-09-22 (Asia/Seoul)**. 개발 브랜치: `docs/jev-free-codex-bridge-20260922`.
초기 v0.4 작업 시작 head: `634d34b2b6639ef60bd6469190cec053826b4385`.

**최종 검토 보강:** [FINAL_REVIEW](FINAL_REVIEW.md)를 먼저 확인한다. Windows Python 3.12에서 전체 71개 테스트를 통과했고, 출처 양방향 연결·누락된 반대 근거·모호한 JSON 입력을 수정했다. 사용자가 최종 검토 후 main 병합을 명시적으로 요청했다. 현재 병합 상태와 최종 commit은 [PR #1](https://github.com/inlight37-design/decision-model_lab/pull/1)이 기준이다. 아래 7–8절의 컨테이너/30개 검사/미병합 기록은 초기 작업 당시의 이력이다.

**후속 근거 검토:** [EVIDENCE_FOLLOWUP](EVIDENCE_FOLLOWUP.md)에 남은 27개 출처의 재확인 범위와 최근 논문 4개의 채택/보류 판단을 기록했다. F22–F24를 추가했고, F06은 provider 경로 및 문서/코드 차이를 확인했다. 새로운 실모델 실험 결과는 없다.

## 1. 현재 결과

**[v0.4 개요](README.md)**가 현재 읽기 시작점이다. 비용/구독 한도 최적화뿐 아니라 상급 모델의 독립 추론·교차검토·근거 확인을 정식 모드로 추가했다. 실제 구독 모델을 연결해 실행한 것은 아니다.

| 완료한 산출물 | 위치 |
|---|---|
| 제품·공개 코드·논문·반례의 사례 정리 | [01-cases-and-findings](01-cases-and-findings.md) |
| 네 모드, P0–P5, profile/claim/evidence/권한/예산/복구, D10–D18 | [02-frontier-architecture](02-frontier-architecture.md) |
| Q0–Q6 대조군, 오류 전이·합성 손실·총비용, 8개 적용 recipe, V04-01–06 | [03-evaluation-and-roadmap](03-evaluation-and-roadmap.md) |
| F01–F24 원문·날짜/버전·검토 범위·한계·결정 연결 | [sources.json](sources.json) |
| 합성 완료 기록 checker와 내장 demo | [tools/check_frontier_protocol.py](../../../tools/check_frontier_protocol.py) |
| frontier/CLI 테스트 40개 | [tests/test_frontier_protocol.py](../../../tests/test_frontier_protocol.py) |
| 출처 양방향 연결·상대 링크 검사 3개 | [tests/test_research_integrity.py](../../../tests/test_research_integrity.py) |
| 실행 환경·검사 결과·원격 hash 대조·미검증 범위 | [VALIDATION](VALIDATION.md) |

root README·AGENTS·architecture 버전 지도와 기존 PR #1은 v0.4 기준이다. 최종 head와 병합 상태는 PR에서 확인한다. 이 문서 자체의 미래 commit SHA를 추정하지 않는다.

## 2. 다음 세션의 최소 읽기 순서

이 문서 → 필요한 mode의 02 절 → 03의 해당 ticket을 읽는다. 결정 이유는 D10–D18에서 F ID를 찾고 sources.json의 정확한 version/locator/limits로 이동한다. 공식 연결/회계는 [v0.3 adapter](../v0.3/02-adapters.md)와 [결정/평가](../v0.3/04-decisions-and-evaluation.md)를 필요한 만큼만 읽는다. 모든 과거 문서를 한꺼번에 prompt에 넣지 않는다.

## 3. 유지할 요구와 바꾸면 안 되는 의미

- 공식 구독 CLI와 native 하네스를 우선한다. API/extra credits는 명시 opt-in이며 조용한 전환은 금지한다. 사용자 실제 요금제·모델 가용성·CLI 버전은 아직 모른다.
- Antigravity `agy`는 Gemini CLI와 다르다. PAL이 Gemini CLI를 지원한다는 이유로 agy 호환을 주장하지 않는다.
- 경제성 경로와 상급 협업을 나란히 둔다. 고급 계획·검토·합성도 상급 모델에게 맡길 수 있다. 일반 코드는 상태·횟수·권한을 관리한다.
- Jev/저가 classifier는 선택 부품이다. 상급 reviewer, 최종 수용 기준, 권한, 예산을 대신 결정하지 않는다.
- 독립 초안은 다른 모델 답변/부모의 결론에 오염시키지 않는다. 새 프로세스도 history/memory가 전달되면 blind가 아니다.
- 투표·자기 확신·익명화는 진실의 증명이 아니다. claim/evidence를 대조하고 중요한 소수 반례·미합의를 최종 보고서에 남긴다.
- 초기 review는 0/1 round. 추가 planner/extractor/retry도 총예산에 포함한다. 외부 invocation 수는 native 내부 model turn/token 상한이 아니다.
- 논의자는 read-only, 구현자는 한 writer를 기본값으로 한다. prompt의 수정 금지 문장은 OS sandbox를 대신하지 않는다.
- v0.2 schema/fixture를 변경하지 않는다. v0.4는 production wire-schema 업그레이드가 아니다.

## 4. 가장 먼저 수행할 다음 작업

**V04-01: 실제 실행 환경과 adapter inventory.** 연결 가능한 사용자 실행 환경에서 OS, 실제 CLI 설치/버전, 해당 버전의 help, native 로그인 방식, 사용 가능한 상급 모델/effort, output/schema/session/권한/cancel 기능을 확인한다. API key·인증 token·전체 환경 변수를 문서나 Git에 출력하지 않는다. 현재 문서만 보고 configured=true로 만들지 않는다.

아직 CLI adapter·MCP bridge가 구현된 경로는 없다. 첫 구현 파일 경로/언어 구조는 실제 저장소 상태와 환경 확인 후 정한다. 단순 문서의 함수 이름을 이미 동작하는 API로 호출하지 않는다. native 도구의 실제 입출력 fixture와 공통 capability/preflight/start/events/collect/cancel 계약을 작은 단위로 연결한다.

이후 **V04-03: 두 native 경로의 읽기 전용 독립 답변 pilot**을 구현한다. 필요한 입력과 승인 범위를 고정하고, 실제 두 모델의 별도 session/artifact, 사용량 관측 범위, 거절·실패·timeout/취소 상태를 기록한다. 모델 부족·funding 불명·읽기 전용 보장 실패를 성공으로 넘기지 않는다. 실제 endpoint 호출 전에 효과적인 계정별 설정을 확인한다.

그 다음 Q0/Q1/Q3/Q5의 작은 비교에서 유망한 task군을 찾고 **V04-04의 세 모델 + 제한 교차검토**로 간다. 토론 없는 독립 합성과 비교하지 않은 채 토론 이득을 주장하지 않는다. build_review, Jev shadow, 장기 journal/SQLite는 해당 ticket 조건이 충족될 때 추가한다.

## 5. checker를 이어서 개발할 때 주의

```bash
python tools/check_frontier_protocol.py
python -m unittest discover -s tests -p 'test_frontier_protocol.py' -v
```

현재 도구는 Python 표준 라이브러리만 사용하는 **축소 합성 완료 기록 검사**다. `frontier-record-experiment/0`, synthetic=true, cross_check/deliberate에 한정한다. 40개 frontier/CLI 테스트는 기록의 불변식과 입력 처리를 검사하며 모델 능력·출처 의미·실제 정책 강제를 검증하지 않는다. 모든 운영 schema 필드를 검사하지도 않는다. 각 claim은 그 claim을 대상으로 기록한 모든 check를 참조해야 한다.

후속 구현은 기록에 적힌 provider/quality/digest/check 상태를 실제 계정·artifact·검증 로그와 대조해야 한다. 현재 `supported`의 최소 참조 조건을 운영 진실 판정 gate로 사용하지 않는다. 별도 합성 profile, partial/degraded 결과의 승인/표시, signature/provenance, timeout/cancellation reconciliation, native 내부 usage는 아직 필요하다. 전체 범위는 VALIDATION 5–6절에 있다.

## 6. 확인한 중요한 사실과 미완료 조사

F02의 Perplexity Model Council 문서는 2026-09-04, F03 effort 문서는 2026-09-18 갱신이다. 독립 상급 모델 협업이 실제 제품에 존재하지만 사용자의 세 구독을 재사용하는 bridge는 아니다. F01 Microsoft는 Critique와 Council을 구분한다. 제품 기능을 정확도 비교 실험으로 부르지 않는다.

F04의 Karpathy 코드에서는 자기 답변 포함·공통 순서·합성 단계 모델 이름 노출·실패 초기 응답 제외를 확인했다. F05 PAL의 고정 Codex preset에는 승인/sandbox 우회 옵션이 있다. 그대로 도입하지 않는다. 후속 정적 감사에서 PAL consensus는 API/custom provider 경로이며 thinking_mode=medium을 전달함을 확인했다(F06). 현재 agy/CLI 호환성·실제 과금·실행 동작은 미검증이다.

F09/F10/F11/F20은 abstract 수준 확인이다. 관련 수치나 세부 방법이 필요하면 전체 원문을 추가로 읽어야 한다. F10 PDF와 Microsoft 연결 기술 글 접근은 실패했다. F13 제목/날짜/v1 이력은 후속 확인해 원장에 반영했다. F07의 자신감 가중치를 검증된 보편적 확률로 취급하지 않는다.

F17/F18/F19는 기존 E02/E05/E08 재확인이다. Claude SDK 정책의 상단 보류 안내와 하단 과거표, agy headless 쓰기 허용/soft-denial exit 0, Codex read-only 기본값의 의미를 실제 설치 설정과 대조해야 한다. 전체 source URL 자동 점검·전체 논문 재현·커뮤니티 전수 조사는 하지 않았다.

## 7. 초기 v0.4 작업 당시의 검사와 환경 경계

대화 컨테이너 Python 3.13.5에서 새 unit test **30개 OK**, demo/파일 입력·정상/오류 exit code·문법 컴파일을 확인했다. 테스트한 코드와 GitHub snapshot `8025e1dde0195f3a0992f8a65fada4545e438eda`의 두 Python blob hash가 일치한다. 정확한 값은 VALIDATION에 있다.

컨테이너 GitHub clone/raw 다운로드는 DNS 실패였다. 로컬 snapshot은 Git checkout이 아니며 원격 저장은 GitHub connector로 수행했다. 사용자 PC의 도구·설정을 변경하지 않았다. 기존 v0.2 전체 테스트, CI, 실제 모델 연결·과금·권한·취소/복구·품질 향상은 미검증이다.

시작 head 대비 `407eb9e...`까지 compare 결과는 12 commits/11 changed files이며 기존 v0.2 계약·기존 상세 문서/검사 파일 변경은 없었다. 그 후 VALIDATION과 이 HANDOFF를 저장한다. PR 조회 시 open/merged=false, mergeable=false였으나 원인은 조사하지 않았다. merge 충돌을 단정하거나 임의로 해결/재배치하지 않는다.

## 8. 중간 checkpoint 기록

| Commit | 보존한 진행 |
|---|---|
| `472d2dd5691b85a9c70a73213f1d24f6faaa4ff9` | 조사 범위·요구·재개 순서의 첫 checkpoint |
| `4fba79de16d352b9090e1d8610cabc64d129559d` | F01–F21 근거 원장 첫 게시 |
| `86e1d6e676446bc0f68ba33ee7884ca62badd993` | 사례와 반례, 공개 코드 채택 경계 |
| `79dcf5b838c3a6395e3d34ec4c88631ae7207651` | 상급 협업 아키텍처·P0–P5·D10–D18 |
| `fce1a5dcfcadd156cc928c7fd4f91764dcaa2038` | 평가/recipe/구현 ticket |
| `ed7c76db34ae7b0113b0d96e242c61b495007db6` | 논문 제목·버전·calibration 한계 보정 |
| `ea9e9758e64c1e6139dd500e80e75c5e846b57bd` | 오프라인 checker |
| `8025e1dde0195f3a0992f8a65fada4545e438eda` | 30개 테스트; 코드 blob 대조 기준 |
| `e337737a1d1428f9a7a4beca1f5dba1ed19bcc40` | v0.4 읽기 시작점 |
| `d917cb2670b14f5df4d0afc0d90d094f596bf06f` | root README 갱신 |
| `22e63271aa9d93e309748172bbddf76fa5656a88` | AGENTS 갱신 |
| `407eb9e029404430c56de4c465b58a574a179dfe` | architecture 버전 지도 갱신 |
| `7a0a5ed47715cc598512c4dba83f74392eb46327` | 실제 검증 결과·미실시 범위 게시 |

PR #1의 제목/본문도 v0.4로 수정했다. 이 최종 인계 파일의 commit은 Git history에서 확인한다. 후속 작업은 신규 사실을 확인하면 해당 F/D와 검증 범위를 함께 갱신하고, 실패와 다음 행동까지 작은 checkpoint로 남긴다.
