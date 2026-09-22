# 다른 세션에서 이어가기

최종 조사 기준일: **2026-09-22**. 현재 설계는 [v0.3 README](README.md). 구체적인 첫 task 절차와 합성 schema는 [v0.2](../v0.2/README.md)를 유지한다.

## 확정된 사용자 요구

- 현재 Antigravity(제미나이), ChatGPT, Claude를 사용한다. 추가 서비스와 Jev류 부품이 생길 수 있다.
- 구독에 포함된 공식 CLI를 우선한다. API는 선택 사항이다.
- 가장 중요한 것은 전체 틀이다. native 하네스를 유지하고 모델을 역할에 맞게 배정하며 token/한도 낭비를 줄인다.
- 논문·실제 성과·공식 사양에 근거하고, 다른 세션에서도 결정 이유와 원문을 찾을 수 있어야 한다.

정확한 요금제, CLI 설치/버전, 로컬 장비, 모델 선택 목록, quota 상태는 미확인이다. 임의로 Pro/Max/Ultra라고 설정하지 않는다. 로컬 Jev는 관심 사항이며 공개 가중치 사용 가능성을 확정한 것이 아니다.

## 다음 세션의 짧은 읽기 경로

1. 이 파일과 [v0.3 개요](README.md)를 읽는다.
2. 구현 작업이면 [01 시스템](01-system.md)의 책임/상태, [02 adapter](02-adapters.md)의 해당 제품 행, [04](04-decisions-and-evaluation.md)의 I01–I03을 읽는다.
3. 특정 결정의 이유는 04의 `Dxx`에서 근거 `Exx`를 찾고 [sources.json](sources.json)의 URL·locator·version을 연다.
4. 숫자를 인용할 때는 [03 근거 평가](03-evidence.md)의 분모·대조군·한계를 같이 확인한다.
5. provider 인증/과금/flags를 구현할 때에는 원문을 다시 확인하고 실제 설치 버전과 대조한다. 정책 사실과 설계 제안을 구분한다.

모든 과거 문서를 매 worker prompt에 넣을 필요는 없다. 필요한 결정과 source section만 조회한다. 터미널에서 `rg 'D03|E22' docs/architecture/v0.3`처럼 찾을 수 있다. `rg`가 없으면 편집기 검색을 사용한다.

## 지금 존재하는 것과 없는 것

| 존재 | 아직 없음 |
|---|---|
| 논문·사례 검토, 전체 구조, native 연결표, ADR, source registry | 실제 CLI adapter·MCP bridge·scheduler |
| 기존 v0.2 합성 계약·fixture·offline 검사 도구 | 실제 candidate/test evidence·사용자 workload 결과 |
| 비교 실험 설계·adapter conformance 조건 | 절감률·구독 quota 변환식·자동 hard token cap 검증 |
| Lite-Harness/Symphony의 commit 고정 소스 검토 | 해당 프로젝트 설치·실행·세 구독 호환성 재현 |

문서의 `REVIEW_READY`, `passed`, 비용 예시는 동작하는 시스템/실험 결과가 아니다. v0.2의 28개 테스트는 과거 합성 계약 검사 기록이다. 이번 조사 검증은 [VALIDATION](VALIDATION.md)의 범위만 주장한다.

## 다음에 바로 할 수 있는 작업

전체 구조를 구현하기 시작한다면 I01에서 CLI별 **version·로그인 방식·지원 flags만** 확인하고, 이미 사용할 수 있는 하나의 native 하네스로 I02/I03을 완성한다. 세 CLI·Jev·학습 router·장기 DB를 동시에 붙이지 않는다. 첫 실제 결과는 단일 `bounded_patch`의 manifest, patch digest, 검증 명령/log, normalized usage, 취소/실패 상태여야 한다.

## 출처를 갱신하는 방법

`sources.json`은 `id`, `kind`, `url`, `supplemental_urls`, `published`, `checked_on`, `locator`, `claim`, `limitations`, `verification`, `decisions`, `recheck`를 가진다. 날짜가 명시되지 않은 mutable 문서는 published를 null로 둔다. `primary_source_read`는 독립 재현을 뜻하지 않는다. E14는 abstract 범위만 사용했다고 명시했다.

- 문서가 바뀌면 예전 주장을 조용히 덮어쓰기보다 변경 이유와 영향을 받는 Dxx/adapter를 함께 기록한다.
- GitHub 구현 근거는 가능하면 commit URL로 고정한다. 현재 E22/E23은 그러한 snapshot이다.
- E15는 최신 v3의 260설정, E16은 최신 v4의 해결 수를 사용한다. registry의 supplemental URL에 초기판을 남겼다. 이전 문서의 180설정·351/274 해결은 그 초기판의 수치다.
- CLI 정책은 구현/업그레이드 직전에 갱신한다. Claude E05의 상단 보류 안내와 하단 역사적 표를 혼동하지 않는다.
- source registry에 URL이 있다는 것과 실제 내용을 확인했다는 것은 다르다. 접근 실패는 `unverified` 등으로 별도 남기며 검증 근거로 사용하지 않는다.
- source 원문 전체를 복사할 필요는 없다. 짧은 주장·정확한 위치·version·한계를 남긴다. 재현 실험은 별도 manifest와 artifact로 보관한다.

## 변경 및 병합 경계

이번 보강은 기존 [PR #1](https://github.com/inlight37-design/decision-model_lab/pull/1)에 이어진 문서 작업이다. base 조사 시점은 main `244e8a1b3fef3a43263e9bff416c67f2cfc0b59f`. 이전 9월 22일 보강 head는 `61c1db1c2c5a2fbbb2410f1b719207a533ec711f`다. 최종 head·merge 가능 여부는 PR의 현재 상태가 기준이며 이 파일 안에 미래 commit을 추정해 적지 않는다.

로컬 `C:/ai/decision-model_lab`는 다운로드한 snapshot에서 문서를 편집한 디렉터리다. Git checkout/worktree라고 주장하지 않는다. 원격 GitHub API로 변경 내용을 저장하고 blob hash를 대조하는 방식으로 게시한다. 다른 세션은 실제 git clone 또는 현재 PR 파일을 기준으로 시작한다.
