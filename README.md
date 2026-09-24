# decision-model_lab

Antigravity·ChatGPT·Claude의 **native 하네스와 공식 구독 CLI**를 연결하는 작업 구조를 연구합니다. 두 가지 목적을 함께 다룹니다.

- **경제성:** 필요한 품질을 유지하면서 구독 한도·token 낭비·수용 결과당 비용을 줄입니다.
- **상급 모델 협업:** 어려운 문제는 각 회사의 상급 모델이 독립적으로 풀고 교차검토하여 오류·누락·불확실성을 더 잘 다룹니다.

Jev류 판단 모델은 교체 가능한 선택 부품이며, 전체 시스템의 필수 지휘자가 아닙니다.

> **현재: v0.4 상급 모델 협업 확장 (2026-09-22).** 실제 제품·공개 구현·논문과 반례를 F01–F31로 정리하고, 네 실행 모드·P0–P5 프로토콜·D10–D18 결정·비교 실험을 추가했습니다. 이후 외부 검토와 추가 검토에서 CI·원장 계약·오프라인 경계 실험을 보강했습니다([검토 기록](docs/reviews/README.md)). 현재 검사 수와 결과는 [CI 실행 기록](https://github.com/inlight37-design/decision-model_lab/actions/workflows/checks.yml)이 기준입니다. **실제 세 모델 연결·사용자 환경의 권한/과금·품질 향상률을 검증한 상태는 아닙니다.** v0.3 기반과 v0.2 계약은 유지합니다. [최종 검토와 수정 내역](docs/architecture/v0.4/FINAL_REVIEW.md). 이후 남은 출처 27개와 최근 논문 4개를 확인한 [후속 근거 검토](docs/architecture/v0.4/EVIDENCE_FOLLOWUP.md)에서 PAL 설명을 수정하고 평가 기준을 보강했습니다.

사용자 PC의 WSL에서 **Codex·Claude의 실제 동시 응답을 받아 봉인 후 공개**했고, Codex 계정 한도 조회를 화면에 연결했습니다([관측 기록](docs/reviews/2026-09-24-windows-live-completion/README.md), [실행 안내](app/README.md)). 이어서 실행별 공통 자료, Claude 계정 한도 표시, 공개 뒤 실제 합성 1회(원문 인용 대조)를 붙여 실제로 확인했습니다([공통 자료](docs/reviews/2026-09-24-source-snapshot/README.md), [실제 합성](docs/reviews/2026-09-24-model-synthesis/README.md)). 개인 문맥 독립성과 품질 향상은 미확인이며, 합성은 사실 검증이 아닙니다.

## 이어서 작업한다면

**[NEXT-SESSION.md](NEXT-SESSION.md)부터 읽습니다.** 환경, 확정된 방침, 열린 결정, 다음 작업이 한 장에 있습니다. 다른 기기에서 clone 한 경우에도 그 문서 하나로 이어갈 수 있습니다.

| 갈래 | 위치 |
|---|---|
| 작업 개념도 (한 장) | [docs/concept/](docs/concept/README.md) |
| 셸 디자인 시스템 | [design/](design/README.md) |
| 외부 검토 원문 | [docs/reviews/](docs/reviews/README.md) |
| Hermes 패턴 선별 조사 (2026-09-23) | [요약·상세 분석·적용 시험·고정 근거](docs/research/hermes-2026-09-23/README.md) · [Claude 교차 확인](docs/research/hermes-2026-09-23/CROSSCHECK.md) |
| tmux 설계 패턴 조사 (2026-09-23) | [요약·상세 분석·적용 계획·출처](docs/research/tmux-2026-09-23/README.md) (ChatGPT, [PR #8](https://github.com/inlight37-design/decision-model_lab/pull/8)) |
| 첫 cross_check 실험 기록 | [docs/experiments/2026-09-22-cross-check/](docs/experiments/2026-09-22-cross-check/README.md) |

## 지금 읽을 문서

**[v0.4 개요](docs/architecture/v0.4/README.md)**에서 시작합니다. 다른 세션에서 이어갈 때는 **[v0.4 HANDOFF](docs/architecture/v0.4/HANDOFF.md)**를 먼저 읽습니다.

| 문서 | 내용 |
|---|---|
| [사례와 반례](docs/architecture/v0.4/01-cases-and-findings.md) | Perplexity/Microsoft, Karpathy/PAL, ReConcile/MoA, 상급 모델 분업, debate 실패와 judge 편향 |
| [상급 모델 협업 아키텍처](docs/architecture/v0.4/02-frontier-architecture.md) | 단일 실행·독립 교차검증·제한 토론·구현/검토, 주장/근거·권한·예산·복구 |
| [평가와 구현 순서](docs/architecture/v0.4/03-evaluation-and-roadmap.md) | 같은 예산의 강한 단독/ensemble 대조군, 오류 전이·합성 손실, 8개 적용 예시와 ticket |
| [근거 원장](docs/architecture/v0.4/sources.json) | F01–F31의 원문·날짜/버전·검토 범위·한계·관련 결정 |
| [검증 범위](docs/architecture/v0.4/VALIDATION.md) | 실제 오프라인 검사, 코드 hash 대조, 미실시한 runtime 검증 |

**다수결은 진실 판정이 아닙니다.** 초기 독립 답변을 보존하고, 근거로 해결되지 않은 소수 반례·의견 차이는 최종 결과에도 남깁니다. 상급 모델이 계획·검토·합성하는 것도 지원할 설계이며, 모든 역할을 저가 모델로 채우는 구조가 아닙니다. 추가 호출이 실제로 도움이 되는지는 작업군별로 평가합니다.

## 실행 가능한 오프라인 뼈대

저장소 루트에서 실행합니다. 새 검사는 Python 표준 라이브러리만 사용합니다.

```bash
python tools/check_frontier_protocol.py
python -m unittest discover -s tests -p 'test_frontier_protocol.py' -v
```

이 도구는 **합성 완료 기록의 일부 일관성을 검사**합니다. 정족수 부족, peer에 오염된 초기 입력, 호출/라운드 상한, 자기 평가, funding 정책, 근거 없는 검증 승격, 미합의 누락 등을 검사합니다. 실제 모델·API·shell 작업을 실행하지 않으며 OS sandbox, 인용의 의미, 실제 사용량, 진실을 검증하지 않습니다. 상세 제한은 [v0.4 안내](docs/architecture/v0.4/README.md)에 있습니다.

v0.2 계약 검사, 근거 원장 구조 검사, 문서 참조 회귀 검사까지 실행하려면 다음을 사용합니다. 전체 검사 수는 문서에 적지 않고 CI 로그를 기준으로 합니다. 여러 세션이 고치는 문서에 적은 숫자는 매번 어긋났습니다.

```bash
python -m pip install -r requirements-design.txt
python tools/validate_design.py     # v0.1 계약 25개
python tools/validate_v02.py        # v0.2 plan/proof 결합
python tools/validate_sources.py    # E01–E31 / F01–F31 원장 구조
python -m unittest discover -s tests -v
```

jsonschema를 설치하지 않으면 해당 검사는 실패가 아니라 skip으로 표시됩니다. 미설치와 계약 위반은 다른 상태입니다. 위 검사는 [GitHub Actions](.github/workflows/checks.yml)에서 push·PR마다 Python 3.12/3.13으로 실행됩니다.

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

adapter inventory(V04-01)는 보조 PC에서 끝났고, 지금은 두 native 경로의 읽기 전용 independent pilot(V04-03)을 준비합니다. 첫 실행 코어는 [`core/`](core/README.md)에 있고, 현재 할 일은 [NEXT-SESSION.md](NEXT-SESSION.md)가 기준입니다. 전체 팀·DB·학습 router를 한꺼번에 구현하지 않고, 단계별 산출물·실패 이유·다음 작업을 HANDOFF와 commit에 남깁니다. 모든 과거 문서를 매번 agent prompt에 넣지 않습니다.

## 라이선스

Copyright 2026 inlight37-design.

이 저장소는 **코드와 연구 자료에 서로 다른 라이선스**를 적용합니다. 연구 자료의 가치는 출처·검토 범위·한계를 추적한 작업에 있으므로, 인용할 때 출처 표기를 요구하는 쪽을 택했습니다.

| 대상 | 라이선스 |
|---|---|
| `tools/`, `tests/`, `contracts/`의 코드와 schema | [Apache License 2.0](LICENSE) |
| `docs/`의 문서, 근거 원장(`sources.json`), `README`·`AGENTS` | [CC BY 4.0](LICENSE-DOCS) |

근거 원장이 인용하는 **외부 자료는 각 저작권자의 것**입니다. 원장에는 URL·판본·확인 범위·한계만 기록하며 원문을 재배포하지 않습니다. 외부 수치를 이 저장소의 실측 결과로 사용하지 않는다는 [기록 원칙](#기록-원칙)이 라이선스와 별개로 계속 적용됩니다.
