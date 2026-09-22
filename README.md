# decision-model_lab

Jev류 판단 모델과 기존 코딩 에이전트를 조합하여, **품질을 유지하면서 프론티어 사용량과 수용 결과당 비용을 줄이는 방법**을 연구합니다.

> **현재: 사례 기반 설계 v0.2 + 2026-09-22 후속 조사.** Jev 없이 시작하는 다중 모델 협업, 최신 Codex 연결 방식, 토큰·비용 측정을 보강했습니다. 기존 v0.2의 합성 계약 검사 28개 통과 기록은 보존합니다. 실제 모델·하네스 연결이나 사용자 프로젝트의 절감률을 검증한 상태는 아닙니다.

## 지금 읽을 문서

**[9월 22일 조사·권고](docs/research-2026-09-22/README.md)**에서 시작합니다. 기존 계약과 실행 절차는 [v0.2 전체 안내](docs/architecture/v0.2/README.md)를 함께 봅니다.

| 새 문서 | 핵심 내용 |
|---|---|
| [최신 팀워크 방식과 근거](docs/research-2026-09-22/README.md) | Cursor 역할 분리, Lite-Harness, Jev 분류/compaction, Fusion, 로컬 대안, X 접근 한계 |
| [Codex 하네스 연결 설계](docs/research-2026-09-22/codex-bridge.md) | MCP bridge, SDK/exec/App Server 구분, task/result packet, adapter와 검증 경계 |
| [토큰·비용 평가와 구현 순서](docs/research-2026-09-22/measurement-and-rollout.md) | 낭비 진단, parent 포함 총비용, 캐시, 비교 실험, 첫 구현의 완료 조건 |

이번 보강은 문서 제안입니다. bridge·로컬 모델을 설치하거나 기존 계약 버전을 변경하지 않았습니다.

| 문서 | 핵심 내용 |
|---|---|
| [01. 실제 성과와 설계 사례](docs/architecture/v0.2/01-case-studies.md) | Cursor Router·Switchyard·SWE-Pruner·Symphony·mini-swe-agent·Attractor·JevGrep 등의 근거와 적용 한계 |
| [02. 구체 설계](docs/architecture/v0.2/02-concrete-blueprint.md) | v0.1에서 바꾼 점, 실용/실험 두 경로, bounded_patch 절차, 실제 코드 경계 |
| [03. 평가·구현 백로그](docs/architecture/v0.2/03-experiments-and-backlog.md) | 고가/저가 단독 기준선, 문맥·router 대조군, milestone 검증, 구현 ticket 8개 |
| [검증 기록](docs/architecture/v0.2/VALIDATION.md) / [작업 기록](docs/architecture/v0.2/WORKLOG.md) | 실제 검사 범위·파일 동일성·중간 커밋·미실시 항목 |

## 현재 설계의 중심

기존 실행기를 활용하고, 우리가 직접 정의하는 부분은 작업·문맥·권한·검증·비용의 경계로 제한합니다. 실용 경로는 native coding 하네스와 Symphony의 운영 구조를 참고하고, 경제성 실험은 mini-swe-agent 같은 고정된 작은 하네스에서 수행하는 방향입니다.

Jev는 필수 지휘자가 아닙니다. 실제 배정에 영향을 주지 않는 shadow 판단이나 원문 코드 후보 선별부터 비교합니다. 기존 router보다 나은지뿐 아니라 **저가 모델만 사용해도 충분한지**를 확인합니다. 자동 main merge와 무제한 AI 관리자 회의는 초기 범위에서 제외합니다.

이것은 도구 전체를 설치한다는 결정이 아닙니다. **한 task, 한 worker, 독립 검증, 사람에게 인계**하는 bounded_patch부터 실제 성과를 측정할 계획입니다.

## 오프라인 검사

```bash
python -m pip install -r requirements-design.txt
python tools/validate_v02.py
python -m unittest discover -s tests -p 'test_v02.py' -v
```

[계약 설명](contracts/v0.2/README.md)을 먼저 확인하세요. 합성 fixture에는 실제 API 키·모델 설정·실행 명령이 없고 backend는 `unconfigured`입니다. 모델 실행, 보안 인증, 취소·복구, 비용 제한 강제 기능을 구현한 것이 아닙니다.

## 보존한 v0.1 자료

[아키텍처 버전 지도](docs/architecture/README.md)에 기존 다섯 문서와 이전 검증 기록을 연결했습니다. v0.2는 초기 구현 순서를 구체화한 후속 제안이며, 기존 상세 설계와 source-only 노트를 삭제하지 않았습니다.

- [원래 Jev / 공개 decision-model 조사](docs/research-notes-2026-09-21.md)
- [v0.1 기본 아키텍처](docs/architecture/02-reference-architecture.md)
- [v0.1 계약 검사](contracts/README.md)

후속 실행에서는 9월 22일 보강 문서와 v0.2의 구체 결정을 읽고, 이전 문서는 근거·상세 원칙을 확인할 때 사용합니다. 문서 전체를 매번 agent 프롬프트에 넣지 않습니다.

## 기록 원칙

공식 사양·논문·실제 코드, 제작자 자체 보고, 커뮤니티 경험, 우리 설계 제안을 구분합니다. 다른 과제·장비·캐시·분모의 성능 수치를 합치지 않습니다. 원문 접근 실패, 실측하지 않은 비용·품질, 모르는 사용량은 그대로 표시합니다. API 키와 민감 raw trace를 코드 Git에 자동 저장하지 않습니다.
