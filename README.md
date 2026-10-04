# decision-model_lab

Antigravity·ChatGPT·Claude의 **native 하네스와 공식 구독 CLI**를 연결하는 작업 구조를 연구합니다. 두 가지 목적을 함께 다룹니다.

- **경제성:** 필요한 품질을 유지하면서 구독 한도·token 낭비·수용 결과당 비용을 줄입니다.
- **상급 모델 협업:** 어려운 문제는 각 회사의 상급 모델이 독립적으로 풀고 교차검토하여 오류·누락·불확실성을 더 잘 다룹니다.

Jev류 판단 모델은 교체 가능한 선택 부품이며, 전체 시스템의 필수 지휘자가 아닙니다.

설계는 [v0.4](docs/architecture/v0.4/README.md)입니다 — 실제 제품·공개 구현·논문과 반례(F01–F31), 네 실행 모드, P0–P5 프로토콜, D10–D18 결정. v0.3 기반과 v0.2 계약은 유지합니다. 실제로 도는 것은 사용자 PC의 WSL에서 두 구독 CLI(Codex·Claude Code)를 서로 못 보게 부르고(봉인), 함께 공개한 뒤 원문 대조·실제 합성·교차검토로 묶는 controller 앱입니다([app 안내](app/README.md), 실행 조각은 [core/](core/README.md)). **지금 상태·확인한 것·한계는 [NEXT-SESSION.md](NEXT-SESSION.md) 1절이 기준**입니다. 합성과 합의는 사실 검증이 아니고, 품질 향상은 미확립입니다. 검사 수와 결과는 [CI 실행 기록](https://github.com/inlight37-design/decision-model_lab/actions/workflows/checks.yml)이 기준입니다.

## 이어서 작업한다면

**[NEXT-SESSION.md](NEXT-SESSION.md)부터 읽습니다.** 환경, 확정된 방침, 열린 결정, 다음 작업이 한 장에 있습니다. **새 컴퓨터에서 처음 연다면 [docs/SETUP.md](docs/SETUP.md)를 먼저 합니다** — PowerShell 명령 한 줄이 도구·clone·WSL·Ubuntu·CLI·로그인·확인을 순서대로 진행하고, 사람은 관리자 승인·Ubuntu 사용자·브라우저 로그인 승인만 합니다. 남은 일·못 고치는 것·조사 거리는 [검토 요청서](docs/reviews/2026-09-25-review-request/README.md)에 모았습니다.

| 갈래 | 위치 |
|---|---|
| 목적별 문서 입구 | [문서 지도](docs/DOCUMENT-MAP.md) — 현재 동작·제안·근거·과거 기록 구별 |
| 대대적 개편 준비 | [통합 설계](docs/architecture/redesign-2026-10-04/README.md) · [우선순위·효용](docs/architecture/redesign-2026-10-04/PRIORITIES.md) — 현재 코드 대조·파이프라인·이행 계약 |
| 실제 기능과 코드 찾기 | [기능 안내](docs/FEATURES.md) — 기능·구현 파일·검사·자동 기억 범위 |
| 외부에서 찾아온 기능과 코드 찾기 | [참고 지도](docs/REFERENCE-MAP.md) — 출처·적용 상태·우리 코드·원본 분석 |
| 작업 개념도 (한 장) | [docs/concept/](docs/concept/README.md) |
| 셸 디자인 시스템 | [design/](design/README.md) |
| 외부 검토 원문 | [docs/reviews/](docs/reviews/README.md) |
| 첫 cross_check 실험 기록 | [docs/experiments/2026-09-22-cross-check/](docs/experiments/2026-09-22-cross-check/README.md) |

## 지금 읽을 문서

구조를 손볼 때는 **[통합 개편 준비서](docs/architecture/redesign-2026-10-04/README.md)**에서 시작합니다. 아래 [v0.4](docs/architecture/v0.4/README.md)는 협업 설계의 기반입니다. 지금 상태와 다음 일은 **[NEXT-SESSION.md](NEXT-SESSION.md)**에 있습니다([v0.4 HANDOFF](docs/architecture/v0.4/HANDOFF.md)는 2026-09-22 판).

| 문서 | 내용 |
|---|---|
| [사례와 반례](docs/architecture/v0.4/01-cases-and-findings.md) | Perplexity/Microsoft, Karpathy/PAL, ReConcile/MoA, 상급 모델 분업, debate 실패와 judge 편향 |
| [상급 모델 협업 아키텍처](docs/architecture/v0.4/02-frontier-architecture.md) | 단일 실행·독립 교차검증·제한 토론·구현/검토, 주장/근거·권한·예산·복구 |
| [평가와 구현 순서](docs/architecture/v0.4/03-evaluation-and-roadmap.md) | 같은 예산의 강한 단독/ensemble 대조군, 오류 전이·합성 손실, 8개 적용 예시와 ticket |
| [근거 원장](docs/architecture/v0.4/sources.json) | F01–F31의 원문·날짜/버전·검토 범위·한계·관련 결정 |
| [검증 범위](docs/architecture/v0.4/VALIDATION.md) | 실제 오프라인 검사, 코드 hash 대조, 미실시한 runtime 검증 |

**다수결은 진실 판정이 아닙니다.** 초기 독립 답변을 보존하고, 근거로 해결되지 않은 소수 반례·의견 차이는 최종 결과에도 남깁니다. 상급 모델이 계획·검토·합성하는 것도 지원할 설계이며, 모든 역할을 저가 모델로 채우는 구조가 아닙니다. 추가 호출이 실제로 도움이 되는지는 작업군별로 평가합니다.

## 검사

저장소 루트에서 실행합니다. 검사 전체 목록은 [NEXT-SESSION.md](NEXT-SESSION.md) 6절에 있고, [GitHub Actions](.github/workflows/checks.yml)가 PR과 main마다 같은 검사를 돌립니다. 검사 수는 문서에 적지 않습니다 — CI 로그가 기준입니다.

```bash
python -m pip install -r requirements-design.txt
python -m unittest discover -s tests -v
```

`jsonschema`가 없으면 그 검사는 실패가 아니라 skip입니다(skip은 통과가 아닙니다). `tools/check_frontier_protocol.py`는 합성 완료 기록의 일관성만 검사하며 실제 모델·API·sandbox·인용의 의미·진실은 검증하지 않습니다([v0.4 안내](docs/architecture/v0.4/README.md)).

## 계속 사용하는 기반 문서

| v0.3 기반 | 내용 |
|---|---|
| [개요](docs/architecture/v0.3/README.md) / [시스템](docs/architecture/v0.3/01-system.md) | native 하네스, 외부 controller, 역할·상태·문맥 경계 |
| [어댑터와 하네스](docs/architecture/v0.3/02-adapters.md) | Codex/Claude Code/Antigravity `agy`, 인증·과금·권한 차이 |
| [근거 평가](docs/architecture/v0.3/03-evidence.md) | 논문·실제 성과·반례와 수치 적용 범위 |
| [결정과 평가](docs/architecture/v0.3/04-decisions-and-evaluation.md) | D01–D09, cash/quota 회계, 단일 bounded_patch 완료 조건 |
| [출처 E01–E31](docs/architecture/v0.3/sources.json) / [검증](docs/architecture/v0.3/VALIDATION.md) | 기존 근거와 검증 범위 |

구독 우선·API 선택·추가 과금 자동 전환 금지 원칙은 그대로입니다. Antigravity와 Gemini CLI는 같은 도구로 가정하지 않습니다. 설치 버전·실제 모델 가용성·계정별 entitlement는 구현 전 확인합니다. v0.4의 F17–F19는 E02/E05/E08 재확인이므로 원장 수를 독립 실험 수로 합산하지 않습니다.

## 보존한 이전 조사

| 자료 | 내용 |
|---|---|
| [2026-09-22 추가 조사](docs/research-2026-09-22/README.md) | 팀워크 방식, Lite-Harness, Jev, Fusion, 로컬 대안 |
| [Codex bridge](docs/research-2026-09-22/codex-bridge.md) | MCP/SDK/exec/App Server, task/result packet과 검증 경계 |
| [토큰·비용 평가](docs/research-2026-09-22/measurement-and-rollout.md) | parent 포함 비용, cache, 비교 실험 |
| [v0.2 사례](docs/architecture/v0.2/01-case-studies.md) / [설계](docs/architecture/v0.2/02-concrete-blueprint.md) / [백로그](docs/architecture/v0.2/03-experiments-and-backlog.md) | 이전 상세 근거와 bounded_patch 실험 설계 |
| [v0.2 검증](docs/architecture/v0.2/VALIDATION.md) / [작업 기록](docs/architecture/v0.2/WORKLOG.md) / [계약](contracts/v0.2/README.md) | 기존 합성 schema·fixture와 역사적 검사 기록 |
| [버전 지도](docs/architecture/README.md) / [v0.1 구조](docs/architecture/02-reference-architecture.md) / [계약](contracts/README.md) | 초기 아키텍처와 보존한 문서 |
| [원래 Jev 조사](docs/research-notes-2026-09-21.md) | 초기 source-only 노트 |

## 기록 원칙

공식 사양·논문·정적 코드 검토, 제작자 자체 보고, 커뮤니티 경험, 우리 설계 제안을 구분합니다. 서로 다른 과제·장비·cache·분모의 성능 수치를 합치지 않습니다. 원문 접근 실패·부분 검토·실측하지 않은 품질과 비용은 명시합니다. API 키와 민감 raw trace는 Git에 자동 저장하지 않습니다.

전체 팀·DB·학습 router를 한꺼번에 구현하지 않고, 단계별 산출물·실패 이유·다음 작업을 [NEXT-SESSION.md](NEXT-SESSION.md)와 commit에 남깁니다. 모든 과거 문서를 매번 agent prompt에 넣지 않습니다.

## 라이선스

Copyright 2026 inlight37-design.

이 저장소는 **코드와 연구 자료에 서로 다른 라이선스**를 적용합니다. 연구 자료의 가치는 출처·검토 범위·한계를 추적한 작업에 있으므로, 인용할 때 출처 표기를 요구하는 쪽을 택했습니다.

| 대상 | 라이선스 |
|---|---|
| `tools/`, `tests/`, `contracts/`의 코드와 schema | [Apache License 2.0](LICENSE) |
| `docs/`의 문서, 근거 원장(`sources.json`), `README`·`AGENTS` | [CC BY 4.0](LICENSE-DOCS) |

근거 원장이 인용하는 **외부 자료는 각 저작권자의 것**입니다. 원장에는 URL·판본·확인 범위·한계만 기록하며 원문을 재배포하지 않습니다. 외부 수치를 이 저장소의 실측 결과로 사용하지 않는다는 [기록 원칙](#기록-원칙)이 라이선스와 별개로 계속 적용됩니다.
