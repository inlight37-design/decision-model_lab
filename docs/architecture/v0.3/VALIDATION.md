# v0.3 검증 범위

2026-09-22 문서 작업. 실제 모델이나 CLI를 실행한 검증이 아니다.

최종 검토에서 기존 검사는 출처와 결정의 **존재 여부**를 확인했지만 모든 연결의 양방향 동일성까지 보장하지 못했음을 확인했다. D01/D02와 E06의 연결을 보정하고 전체 D01–D18 ↔ E/F 연결 회귀 검사를 추가했다. 최신 결과는 [v0.4 최종 검토](../v0.4/FINAL_REVIEW.md)를 따른다. 아래 숫자는 최초 작업 당시 기록이다.

## 수행한 검토

- 원문 공식 문서, 논문 판본, 공개 benchmark와 소스 코드를 읽고 source registry에 종류·위치·확인일·한계·관련 결정을 기록했다.
- SWE-Pruner v1/v4와 Scaling Agent Systems v1/v3의 수치 차이를 확인하고 최신판을 현재 근거로 반영했다.
- Lite-Harness와 Symphony의 코드/명세 근거를 immutable commit URL로 고정했다. 실행시험은 하지 않았다.
- 로컬 Markdown 상대 링크, 코드 fence, JSON 예시/registry, 근거 ID와 결정 ID의 참조 일관성을 Python 3.12의 pathlib/re/json으로 오프라인 검사했다.

## 결과

- 검사 범위: root README/AGENTS, architecture README, v0.3 Markdown 전체, 기존 9월 22일 후속 조사 문서.
- Markdown **13개**, 상대 링크 **85개**, JSON code block **3개**, source record **31개**, ADR **9개**의 검사에서 오류가 없었다.
- source ID 중복/미정의 참조, decision 참조, 필수 provenance 필드, ISO 날짜, UTF-8 replacement character, code fence 균형을 확인했다.
- 외부 URL 전체에 일괄 HTTP 가용성 검사를 했다는 뜻은 아니다. 실제 주장에 사용한 원문의 확인 범위와 제한은 source registry를 따른다. 향후 URL/정책 변경 가능성은 남는다.
- 게시 후 원격 파일의 Git blob SHA를 로컬 UTF-8 내용과 대조하고 결과를 PR 본문에 기록한다. commit 자체의 GitHub 상태는 PR에서 확인한다.

## 이번에 하지 않은 검증

CLI 설치·로그인·구독 잔량 확인, 모델/API 호출, 실제 patch 작업, test runner 결과의 진위 검사, MCP bridge 실행, 취소/복구·권한 sandbox 시험, token/비용 절감 실험은 하지 않았다. Mermaid 도표는 텍스트 구조를 확인했으며 별도 렌더러의 시각 검수는 하지 않았다.

기존 contracts/examples/tests/tools 실행 코드는 변경하지 않았다. v0.2의 과거 합성 검사 28개 통과 기록은 보존하며, 이번 문서 작업의 재실행 결과라고 표시하지 않는다. 이번 검증으로 운영 안전성·실제 품질·경제성이 입증됐다고 주장하지 않는다.

## 확인 경로

현재 연구의 주장·한계는 [sources.json](sources.json), 설계 추론은 [ADR](04-decisions-and-evaluation.md), 외부 성과의 적용 범위는 [근거 평가](03-evidence.md), 다음 구현 완료 조건은 [adapter conformance](02-adapters.md)에 있다.
