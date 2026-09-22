# 아키텍처 버전 지도

**현재 제안은 [v0.4](v0.4/README.md)입니다.** 공식 구독 CLI·native 하네스 우선 기반 위에 상급 모델의 독립 추론·교차검토·근거 기반 합성을 추가했습니다. [v0.4 HANDOFF](v0.4/HANDOFF.md)에서 완료 결과와 다음 작업을 확인합니다. 기존 v0.3 운영/회계 원칙과 v0.2의 합성 계약·bounded_patch 절차는 유지합니다.

## 현재 읽을 문서

| 문서 | 역할 |
|---|---|
| [v0.4 사례와 반례](v0.4/01-cases-and-findings.md) | 실제 council/critique 제품, 공개 코드 검토, 성과와 실패 근거 |
| [v0.4 상급 협업 설계](v0.4/02-frontier-architecture.md) | 네 실행 모드, 독립 초안·제한 검토·검증·미합의, D10–D18 |
| [v0.4 평가·ticket](v0.4/03-evaluation-and-roadmap.md) | 같은 예산 단일 모델/ensemble 대조군, 오류 전이, 단계별 구현 |
| [v0.4 출처](v0.4/sources.json) / [검증 범위](v0.4/VALIDATION.md) | F01–F24, 원문 검토 범위, 합성 검사와 runtime 미검증 구분 |

오케스트레이션은 저가 모델 분업만을 뜻하지 않습니다. 어려운 계획과 검토에는 상급 모델을 사용할 수 있고, 일반 코드는 상태·권한·예산을 관리합니다. 합의는 검증이 아니므로 미해결 반례를 삭제하지 않습니다. 경제성 경로와 품질 강화 경로를 각각 평가합니다.

## v0.3 — 계속 사용하는 기반

| 문서 | 역할 |
|---|---|
| [개요](v0.3/README.md) / [시스템](v0.3/01-system.md) | native 하네스와 task controller, 문맥·상태·권한 경계 |
| [어댑터](v0.3/02-adapters.md) | Codex/Claude Code/Antigravity agy의 구독·인증·이벤트·권한 차이 |
| [근거](v0.3/03-evidence.md) / [출처](v0.3/sources.json) | E01–E31의 수치·분모·제한 |
| [결정·평가](v0.3/04-decisions-and-evaluation.md) | D01–D09, cash/quota/token 분리, 첫 단일 작업의 완료 조건 |
| [검증](v0.3/VALIDATION.md) / [이전 인계](v0.3/HANDOFF.md) | 당시 검사와 다음 단계의 이력 |

구독 CLI 우선·API 선택·추가 청구 자동 전환 금지 조건은 유지합니다. v0.4는 '한 task 한 worker'를 경제형 기본값으로 남기면서 요청된 상급 협업을 정식 전략으로 추가합니다. 과거 문서의 '현재'는 해당 버전 당시를 뜻합니다. 실제 provider 정책은 구현 직전에 다시 확인합니다.

## v0.2 및 9월 22일 후속 조사

| 문서 | 역할 |
|---|---|
| [v0.2 사례 연구](v0.2/01-case-studies.md) | 실제 성과와 적용 조건 |
| [v0.2 구체 설계](v0.2/02-concrete-blueprint.md) | 당시 변경점과 bounded_patch 실행 절차 |
| [v0.2 실험·백로그](v0.2/03-experiments-and-backlog.md) | 경제성 실험과 구현 순서 |
| [v0.2 검증](v0.2/VALIDATION.md) / [작업 기록](v0.2/WORKLOG.md) | 과거 합성 검사와 중간 commit |
| [v0.2 계약](../../contracts/v0.2/README.md) | 변경하지 않은 합성 schema·fixture |
| [팀워크 후속 조사](../research-2026-09-22/README.md) | Jev·wrapper·팀워크·로컬 후보의 추가 근거 |
| [Codex 연결](../research-2026-09-22/codex-bridge.md) / [측정·도입](../research-2026-09-22/measurement-and-rollout.md) | bridge 선택과 총비용 평가 |

Symphony 등의 운영 명세, 작은 고정 하네스의 경제성 실험, 저가 단독/router 비교, Jev shadow와 read-only 문맥 선별은 보존한 참고·실험 방향입니다. 모두 설치·재현·채택을 완료했다는 뜻은 아닙니다.

## v0.1 보존 자료

| 문서 | 내용 |
|---|---|
| [01. 근거 지도](01-evidence-and-landscape.md) | 초기 Jev·로컬 대안·Antigravity·관련 연구 조사 |
| [02. 기본 아키텍처](02-reference-architecture.md) | 책임 경계·상태 전이·권한·복구·통합의 상세 원칙 |
| [03. 계약·문맥](03-protocol-and-context.md) | task/result 계약, 문맥·캐시·메모리 원칙 |
| [04. 비용·평가](04-evaluation-and-economics.md) | 총비용·보정·장애 평가의 기본식 |
| [05. 도구·도입](05-tooling-and-roadmap.md) | 도구 후보와 초기 ADR·단계 |
| [검증 기록](VALIDATION.md) / [작업 기록](WORKLOG.md) | 당시 수행 범위와 commit |
| [v0.1 계약](../../contracts/README.md) | 당시 합성 JSON 예제와 검사 |

어느 버전도 실제 모델 연결·운영 보안·장기 협업·사용자 프로젝트의 품질/절감률을 이미 검증한 것으로 읽지 않습니다. 각 검증 기록의 범위를 따릅니다. v0.4의 새 오프라인 checker도 운영 orchestrator나 진실 판정기가 아닙니다.
