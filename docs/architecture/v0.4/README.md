# v0.4 — 구독 우선 + 상급 모델 협업

기준일 **2026-09-22**. v0.3의 native 하네스·공식 구독 CLI 우선 구조를 유지하고, **회사별 상급 모델의 독립 추론·교차검토·근거 확인**을 정식 실행 모드로 확장한다.

> 현재는 연구·설계와 합성 기록 검사 단계다. 실제 세 provider를 연결한 orchestrator, 사용자 환경의 과금·권한 검증, 모델 협업의 품질 향상률은 아직 없다. 오프라인 검사와 실제 실행을 구분한다.

## 무엇을 바꾸었는가

기존의 '요구 품질을 유지하며 비용을 낮추기'에 더해, **중요한 문제에서는 상급 모델 여러 개를 써서 오류·누락을 줄이고 불확실성을 드러내는 경로**를 추가했다. 오케스트레이터가 반드시 작은 모델일 필요는 없다. 상태·권한·예산은 일반 코드가 관리하고, 어려운 계획·검토·합성에는 적합한 상급 모델을 사용한다.

| 모드 | 흐름 | 목적 |
|---|---|---|
| single | 적합한 단일 모델 + 검사 | 간단한 작업, 경제성, 비교 기준선 |
| cross_check | 상급 2–3개 독립 답변 → 비교·합성 | 다른 관점·누락 발견 |
| deliberate | 독립 답변 → 제한된 교차검토 → 근거 확인 → 합성 | 어려운 쟁점·추론 검토 |
| build_review | 설계 → 단일 구현자 → 독립 검토자·시험 | 복잡한 변경의 품질과 책임 분리 |

**공통 원칙은 합의가 아니라 근거다.** 초기 답변을 보존하고, 미해결 반례·조건 차이를 지우지 않는다. 추가 호출과 실패 비용도 포함하며, 상급 협업을 모든 작업의 기본값으로 만들지 않는다.

## 읽기 지도

| 문서 | 내용 |
|---|---|
| [01 사례와 반례](01-cases-and-findings.md) | Perplexity/Microsoft의 실제 모드, Karpathy/PAL 정적 검토, ReConcile/MoA, 강한 모델 분업, debate 실패와 judge 편향 |
| [02 아키텍처](02-frontier-architecture.md) | 네 실행 모드, P0–P5 절차, profile·주장/근거·권한·예산·복구 계약, 결정 D10–D18 |
| [03 평가·구현 순서](03-evaluation-and-roadmap.md) | compute-aware 대조군, 오류 전이·합성 손실, 8가지 적용 recipe, V04-01–06 ticket |
| [근거 원장](sources.json) | F01–F21의 원문·날짜/버전·확인 범위·한계·설계 결정 연결 |
| [검증 범위](VALIDATION.md) | 실제 실행한 합성 검사와 하지 않은 검증 |
| [다음 세션 인계](HANDOFF.md) | 완료 결과, 중간 commit, 다음 작업과 금지할 가정 |

짧게 이어갈 때는 HANDOFF와 필요한 설계 절만 읽는다. 모델마다 모든 논문·이전 문서를 반복 투입하지 않는다.

## 이번 근거 보강에서 특히 중요한 것

Perplexity의 2026-09-04 Model Council 문서(F02)는 세 회사 frontier 구성과 독립 조사·소수 발견 보존을 설명한다. 2026-09-18 effort 문서(F03)는 추론 강도와 지출/호출 상한이 다르다고 구분한다. Microsoft는 Critique와 Council을 다른 방식으로 설명한다(F01).

반대로 공개 prototype의 익명 순위 평가에는 자기 답변·공통 순서가 남아 있었고(F04), PAL의 Codex preset은 sandbox/approval 우회 옵션을 포함했다(F05). 논문들도 무조건적인 debate 우월성을 지지하지 않는다(F10–F12). 그래서 참고할 원리와 즉시 도입할 코드를 구분했다. 자세한 원문과 제한은 01과 sources.json에 있다.

F01–F21은 21개의 독립 실험이 아니다. 제품·코드·논문·정책 재확인 기록이며 F17–F19는 기존 E02/E05/E08 재확인이다. 외부 성과를 이 프로젝트의 실측 결과로 사용하지 않는다.

## 실제로 실행할 수 있는 작은 뼈대

저장소 루트에서 Python 표준 라이브러리만으로 실행한다.

```bash
python tools/check_frontier_protocol.py
python -m unittest discover -s tests -p 'test_frontier_protocol.py' -v
```

첫 명령은 내장 합성 기록을 검사한다. 사용자가 준비한 같은 실험 형식의 JSON은 다음처럼 검사할 수 있다.

```bash
python tools/check_frontier_protocol.py path/to/synthetic-record.json
```

`frontier-record-experiment/0`은 **닫힌 합성 기록을 다루는 축소 실험 포맷**이다. 실제 provider record는 `synthetic=false`에서 거절한다. 현재 checker는 cross_check/deliberate, 서로 다른 provider로 선언한 상급 구성, 완료된 draft/review/synthesis와 claim disposition의 기본 일관성만 검사한다. build_review runner·MCP bridge·완전한 JSON Schema·artifact resolver가 아니다. 알 수 없는 추가 필드를 전부 금지하거나 모든 운영 의미를 검증하는 도구도 아니다.

내장 예시의 모델 이름은 A/B/C, provider 표시는 설명용이며 실제 model ID·credential·실행 명령이 없다. `synthetic://` 증거와 0으로 채운 digest는 실물이 아니다. 세 모델의 찬성표가 있어도 근거 없는 주장은 unresolved로 남는다. **검사 통과는 인용의 의미·OS 격리·모델 능력·실제 구독 과금의 증명이 아니다.**

## 다음에 실제로 연결할 최소 단위

첫 작업은 V04-01의 **실제 설치 버전·로그인 방식·지원 모델/권한 확인**이다. 이어서 두 native 경로의 read-only 독립 답변을 비교한다. 세 모델 토론·자동 수정·학습 router·Jev·장기 DB를 동시에 붙이지 않는다. 추가 지출 자동 전환은 계속 금지한다.

## 이전 설계와 호환 범위

[v0.3](../v0.3/README.md)의 adapter·회계·상태 관리와 D01–D09는 기반으로 남긴다. [v0.2 계약](../../../contracts/v0.2/README.md)과 검사는 변경하지 않는다. v0.4는 '한 task 한 worker'를 경제형 기본값으로 남기면서, 사용자 요청에 따라 상급 협업을 선택 가능한 전략으로 추가한 것이다. 이전 문서·원시 연구 노트는 [버전 지도](../README.md)에서 계속 찾을 수 있다.
