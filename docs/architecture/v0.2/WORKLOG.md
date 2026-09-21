# v0.2 사례 기반 구체화 — 작업 기록

기준일: 2026-09-21. 상태: 조사 진행 중 / 첫 체크포인트.

## 요청

이미 가시적인 성과가 있거나 구조가 구체적인 시스템을 심층 조사하여, 기존 v0.1을 다듬고 구현 경계를 더 구체화한다. 단순 후보 나열보다 **성과의 증거 → 실제 구조 → 재사용할 부분 → 적용 조건 → 설계 변경**을 연결한다.

## 시작점과 보존

시작 main: `f20922dc915a74568dbdcb3c00ed13673d0c9871`.
기존 파일 목록과 핵심 아키텍처를 GitHub에서 재확인했다. 기존 조사와 계약을 삭제하지 않고, v0.2 문서에서 변경/유지/보류 이유를 명시한다.

## 첫 확인

- OpenAI Symphony는 실제 README와 SPEC.md를 읽었다. 격리된 이슈 실행, WORKFLOW.md, bounded concurrency, retry/reconciliation을 명시한 공개 설계다. engineering preview이며, tracker/filesystem으로 복구할 수 있고 영속 DB를 필수로 요구하지 않는다. 이는 v0.1의 '항상 자체 원장부터 만든다'는 구현 우선순위를 다시 검토할 직접 근거다.
  - https://github.com/openai/symphony
  - https://github.com/openai/symphony/blob/main/SPEC.md
- OpenAI의 2026-02-11 harness engineering 글에서 내부 제품의 개발/사용 사례와 짧은 문서 지도·기계적 구조 검사·앱 검증 루프를 확인했다. 자체 보고이며 토큰 절감 대조 실험이 아니다.
  - https://openai.com/index/harness-engineering/
- Cursor의 2026-01-14, 2026-02-05 글을 확인했다. 대규모 연구용 코드 생성과 완성품·저비용 성과를 구별한다.
  - https://cursor.com/blog/scaling-agents
  - https://cursor.com/blog/self-driving-codebases
- Stripe Minions의 2026-02-09/19 공식 글은 제목·날짜·관련 글 요약은 확인했으나 웹 파서에서 본문이 비어 있다. 본문 확보 전에는 blueprint 상세를 읽은 사실로 기록하지 않는다.

## 예정 산출물

1. 성과 근거와 적용 조건을 비교한 사례 연구.
2. 실제 파일/함수/사양 수준 재사용 지도.
3. v0.1 변경사항과 더 작은 첫 실행 단위의 구체 설계.
4. 단계별 실험 구성 및 구현 backlog; 가능한 범위의 오프라인 계약 점검.

## 실행 한계

이 작업용 컨테이너는 외부 DNS 연결이 실패했다. GitHub 읽기/쓰기와 웹 조사는 연결 도구로 계속한다. 사용자의 로컬 PC나 유료 모델을 실행한 것으로 표시하지 않는다.
