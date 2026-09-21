# decision-model_lab

Jev / System-One 계열의 판단 모델과 기존 AI 에이전트를 결합하여, **품질을 유지하면서 프론티어 모델 사용량과 프로젝트 수행 비용을 줄이는 방법**을 조사하는 저장소입니다.

> **현재 상태 — 2026-09-21:** 공개 자료 조사와 아키텍처 제안 v0.1을 정리했습니다. 실행 가능한 협업 런타임, 실제 모델 비교, 비용 절감률 검증까지 완료한 상태는 아닙니다. JSON 계약 예시와 오프라인 검사 25개는 실행하여 통과를 확인했습니다.

## 먼저 읽을 문서

**[아키텍처 전체 안내](docs/architecture/README.md)** → **[핵심 구조](docs/architecture/02-reference-architecture.md)** 순서로 읽으면 됩니다.

| 문서 | 내용 |
|---|---|
| [01. 조사 결과와 근거 지도](docs/architecture/01-evidence-and-landscape.md) | Jev·로컬 대안·Antigravity·공개 구현·커뮤니티 조사, 출처별 한계 |
| [02. 제안 아키텍처](docs/architecture/02-reference-architecture.md) | 코드 기반 제어부, 선택적 판단 모델, 워커, 독립 검증, 재개·통합·보안 |
| [03. 계약과 문맥 관리](docs/architecture/03-protocol-and-context.md) | JSON 통신과 실제 토큰 절약의 구분, 데이터 계약, 산출물 참조, 메모리·캐시 |
| [04. 평가와 비용](docs/architecture/04-evaluation-and-economics.md) | 동일 품질 기준선, 실패·검증 포함 총비용, 확률 보정, 단계별 실험 |
| [05. 도구 재사용과 도입 순서](docs/architecture/05-tooling-and-roadmap.md) | LiteLLM·LangGraph·OpenHands·Gas Town·Beads 등의 비교, ADR, P0–P5 |
| [검증 기록](docs/architecture/VALIDATION.md) | 실제 실행한 검사, 커밋 파일과의 해시 일치, 아직 검증하지 않은 범위 |
| [작업 기록 / 인수인계](docs/architecture/WORKLOG.md) | 중간 커밋, 보존한 자료, 미확보 원문, 다음 구현의 시작점 |

## 핵심 설계 제안

코드가 상태·권한·예산·의존성을 관리하고, Jev류 모델은 좁은 판단을 제안합니다. 저비용 또는 프론티어 워커는 제한된 작업을 수행하며, 독립 검증과 통합 검사를 통과한 결과만 수용합니다.

Jev를 전체 프로젝트의 만능 지휘자로 고정하지 않습니다. JSON을 쓴다는 이유만으로 비용이 절감된다고 보지 않습니다. 작은 단일 워커 구성부터 측정하고, 라우팅과 병렬화를 각각 검증한 뒤 추가합니다. 이러한 결정은 **제안**이며 특정 모델의 최종 채택을 의미하지 않습니다.

## 계약 예시의 오프라인 검사

```bash
python -m pip install -r requirements-design.txt
python tools/validate_design.py
```

[계약 설명](contracts/README.md), [JSON Schema](contracts/v0.1.schema.json), [합성 예제](examples/contracts-v0.1.json)를 함께 확인하세요. 검사는 API 호출이나 로컬 모델 실행 없이 동작하며, 실제 운영 보안·장애 복구·모델 성능 검증을 대신하지 않습니다.

## 기존 Research notes

- [2026-09-21 — Jev 및 공개 decision-model 구현 조사](docs/research-notes-2026-09-21.md)

위 원래 조사 노트는 변경하지 않고 보존했습니다. 후속 조사에서 확인된 변경 사항은 새 조사 지도에 기록했습니다. 특히 Kev의 과거 0.5B 설명과 현재 0.8B/4B/9B 계열을 같은 스냅샷으로 혼용하지 않습니다.

## 기록 원칙

- 공식 문서·저장소·논문을 우선하고, 프로젝트 자체 성능 수치는 **self-reported**로 표시합니다.
- 다른 하드웨어·데이터·캐시·재시도 조건의 수치를 직접적인 순위로 바꾸지 않습니다.
- 확인된 사실, 커뮤니티 경험, 설계 제안, 미검증 가정을 구분합니다.
- 접근에 실패한 원문은 읽었다고 주장하지 않습니다. 사용자 제시 haejoe 원문과 일부 X 본문은 미확보 상태입니다.
- 특정 모델·라이브러리·플랜은 실행 전에 버전·권한·요금을 재확인합니다.
- API 키, 원본 실행 trace, 민감 데이터는 공개 코드 저장소에 자동 저장하지 않습니다.
