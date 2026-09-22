# 사례와 반례: 상급 모델 협업은 무엇을 더해 주는가

기준일 **2026-09-22**. [개요](README.md) · [설계](02-frontier-architecture.md) · [평가](03-evaluation-and-roadmap.md) · [출처 원장](sources.json).

**핵심 판단:** 상급 모델 협업은 저가 worker 배정의 변형만이 아니다. 서로 다른 해결 후보를 얻고, 중요한 오류를 찾아내고, 결정의 불확실성을 드러내기 위한 별도 품질 경로다. 다만 여러 답변이 존재한다는 것, 합의했다는 것, 정답이라는 것은 각각 다르다. 아래의 제품 기능·제작자 보고·연구 결과는 이 저장소에서 재현한 성과가 아니다.

## 1. 먼저 구분할 여섯 가지 패턴

| 패턴 | 작동 방식 | 얻으려는 것 | 추가 비용/실패 위험 |
|---|---|---|---|
| Routing / cascade | 한 모델을 고르거나 실패 때 상향 | 요구 품질을 더 적은 자원으로 충족 | 오배정·인계·재시도 비용 |
| Independent ensemble | 같은 문제를 독립적으로 풀고 후보를 비교 | 다른 오류·접근법 발견 | 오류 상관, 후보 선택 실패 |
| Council synthesis | 독립 결과의 공통점·차이·근거를 합성 | 넓은 검토와 읽기 쉬운 최종 결과 | 합성자가 맞는 소수 의견을 지움 |
| Cross-model critique | A의 산출물을 B가 검토·반증 | 누락·가정·실행 오류 탐지 | B가 A의 전제에 끌려감 |
| Bounded debate | 독립 초안 후 쟁점에 대해서만 상호 반론 | 이유를 비교하고 오해를 수정 | 설득에 의한 오답 전파·무한 회의 |
| Division of labour | 설계·구현·시험 등 다른 작업을 분담 | 전문성·병렬 처리 | 통합 충돌·검증 공백 |

이 분류는 우리 설계적 정리다. 한 제품이 둘 이상의 패턴을 구현할 수 있다. **고급 모델이 계획하고 고급 모델이 검토하는 구조도 정상적인 오케스트레이션**이며, 오케스트레이션이라는 말 자체가 저가 모델 사용을 뜻하지 않는다.

## 2. 실제 제품에서 확인한 상급 모델 협업

### 2.1 Perplexity Model Council — 이번 요구와 가장 직접적으로 닮은 제품

2026-09-04 갱신된 [공식 설명 F02](https://www.perplexity.ai/help-center/en/articles/13641704-what-is-model-council)은 기본 구성을 Anthropic·OpenAI·Google의 frontier 모델 각 하나와 결과 합성으로 설명한다. Web/iOS는 세 모델, Computer는 2–8개 모델의 독립 병렬 조사와 개별 보고서·통합 보고서를 제공한다. 합의뿐 아니라 **불일치 이유와 한 모델만 발견한 내용**을 보여주는 것이 특징이다.

가져올 설계는 독립 초안 보존, 공통점/차이/소수 발견을 나누는 결과 화면, 모델별 산출물 열람이다. 가져오지 않을 주장은 '세 회사가 동의했으므로 사실이다'이다. 공식 문서는 기능의 근거이지 정확도 우월성의 대조 실험이 아니다. 또한 이것은 사용자의 기존 세 회사 구독을 재사용하는 bridge가 아니라 별도 상품이며, Computer credits와 web query 한도도 다르다.

2026-09-18 갱신된 [effort 설명 F03](https://www.perplexity.ai/help-center/en/articles/20260917-effort-mode-in-perplexity-computer)은 effort가 조정 모델과 추론 수준을 선택하지만 도구 호출 수·작업 단계·총지출 상한은 아니라고 구분한다. 따라서 우리도 `reasoning_effort`, `invocation_limit`, `deadline`, `funding_policy`를 하나의 '강도' 설정으로 합치지 않는다. 결정 D10/D13/D14.

### 2.2 Microsoft Researcher — Critique와 Council은 다른 실행 모드

2026-03-30 [공식 글 F01](https://www.microsoft.com/en-us/copilot/blog/2026/03/30/copilot-cowork-now-available-in-frontier/)은 OpenAI와 Anthropic을 이용한 생성/평가 분리인 **Critique**와 모델 결과를 나란히 비교하는 **Council**을 설명한다. DRACO 13.8% 개선은 Microsoft 자체 보고이며, percentage-point로 바꾸어 인용하지 않는다. 연결된 상세 기술 글은 이번 조회에서 읽지 못했으므로 실험 전 조건을 검증했다는 주장은 하지 않는다.

이 사례는 '서로 의견을 주고받기'를 하나의 무제한 채팅으로 구현할 필요가 없음을 보여준다. A 생성 → B 검토와 A/B 독립 생성 → 비교를 별도 모드로 둘 수 있다. 현재 상품별 이용 자격은 오래된 출시 본문이나 변경된 상단 안내만으로 확정하지 않는다. 결정 D10/D12.

## 3. 공개 구현: 참고할 부분과 그대로 도입하면 안 되는 부분

### 3.1 karpathy/llm-council — 단순한 3단계 원형

[F04 코드](https://github.com/karpathy/llm-council/blob/92e1fccb1bdcf1bab7221aa9ed90f9dc72529131/backend/council.py)의 실제 `stage1_collect_responses`, `stage2_collect_rankings`, `stage3_synthesize_final`을 읽었다. commit `92e1fccb1bdcf1bab7221aa9ed90f9dc72529131`, 2025-11-22 snapshot이다.

흐름은 독립 답변 → 익명 순위 평가 → 의장 모델의 합성이다. 구조가 간단해 학습용으로 좋지만 다음 사항이 코드에 보인다.

- Stage 2의 목록에는 평가자의 자기 답변도 들어가며, 모든 평가자가 같은 순서의 목록을 받는다. 익명 라벨은 있지만 순서 무작위화나 자기 답변 제외는 확인되지 않는다.
- Stage 3은 원래 모델 이름을 다시 제공한다. '익명 순위 평가'가 전체 과정의 브랜드·자기 선호 편향을 제거했다는 뜻은 아니다.
- 실패한 초기 호출은 성공 결과 목록에서 빠진다. 원래 세 모델을 요구했는데 두 결과만 왔을 때의 정족수·축소 정책을 별도로 설계해야 한다.

README는 유지보수를 약속하지 않는 주말 prototype임을 명시한다. OpenRouter API 경로를 사용하는 만큼 구독 CLI 우선 설계에 그대로 넣지 않는다. 프로토콜만 참고하고 예산·실패·권한·출처 계약은 따로 만든다. 정적 코드 검토이지 실행 재현은 아니다. 결정 D11/D12/D18.

### 3.2 PAL: `consensus`와 `clink`를 혼동하지 않기

[F06 고정 문서](https://github.com/BeehiveInnovations/pal-mcp-server/blob/7afc7c1cc96e23992c8f105f960132c657883bb1/docs/tools/consensus.md)는 입장별 의견 수집·순차 처리를 설명하며 시연은 **가상 예시**다. 후속 [코드 검토](https://github.com/BeehiveInnovations/pal-mcp-server/blob/7afc7c1cc96e23992c8f105f960132c657883bb1/tools/consensus.py#L574)에서 `ModelProviderRegistry`를 거쳐 `provider.generate_content`를 호출하는 API/custom endpoint 경로를 확인했다. `clink`나 native 구독 CLI를 호출하지 않는다. custom endpoint는 로컬일 수도 있으므로 모든 호출이 유료라는 뜻도 아니다.

문서의 추론 강도 선택 설명과 달리 해당 코드의 schema는 `thinking_mode`를 제외하고 호출에는 `medium`을 전달한다. 이 값의 실제 모델별 처리나 비용은 실행하지 않았다. 따라서 문서에 적힌 옵션을 구현된 capability로 등록하지 않는다.

별개의 [F05 clink](https://github.com/BeehiveInnovations/pal-mcp-server/blob/main/docs/tools/clink.md)는 Codex·Claude Code·Gemini CLI를 연결한다. **Gemini CLI 지원은 Antigravity `agy` 지원이 아니다.** 문맥을 넘기거나 대화를 계속할 수 있다는 편리함은 독립 초안 단계에서는 오염 경로가 되기도 한다. 새 프로세스라도 부모의 결론을 함께 전달하면 blind solve가 아니다.

더 중요한 문제는 실제 [고정 commit의 Codex 설정](https://github.com/BeehiveInnovations/pal-mcp-server/blob/7afc7c1cc96e23992c8f105f960132c657883bb1/conf/cli_clients/codex.json)에 승인·sandbox 우회 옵션이 들어 있다는 점이다. clink 문서도 기본 권한 완화를 경고한다. 이를 복사해서 읽기 전용 연구자에게 주지 않는다. 최신 CLI flag 호환성, 과금 경로, 자식 프로세스 취소, OS 격리는 미검증이다.

**판정:** 유용한 bridge/다중 관점 참고 구현이지만 현재 기본 의존성으로 채택하지 않는다. 제품 이름만 보고 하나의 안전하고 구독 호환적인 council이라고 간주하지 않는다. 결정 D11/D15/D18.

## 4. 성과가 보고된 연구: 적용 범위까지 함께 읽기

| 근거 | 실제로 살펴볼 메커니즘 | 우리 프로젝트에서의 한계 |
|---|---|---|
| [F07 ReConcile v3](https://arxiv.org/html/2309.13007v3), ACL 2024 | 다른 모델들의 독립 답변·설명·토론·confidence weighting, 일곱 benchmark | 당시 ChatGPT/Bard/Claude 계열 실험. 현재 구독 하네스나 최신 상급 모델 조합의 실측이 아님 |
| [F08 Mixture-of-Agents v1](https://arxiv.org/html/2406.04692v1), 2024 | 여러 proposer의 결과를 aggregator가 다음 층에서 활용 | AlpacaEval의 선호 지표를 사실 정확도나 코딩 성공률로 바꾸면 안 됨 |
| [F09 DMAD](https://proceedings.iclr.cc/paper_files/paper/2025/hash/3de667dab3b3d812583abc0a786139a0-Abstract-Conference.html), ICLR 2025 | 단순 인격 부여보다 풀이 방법의 다양성을 설계 | 이번에는 abstract 수준 확인. 수치·전체 실험표·코드 실행은 미검증 |

ReConcile의 자신감 가중치는 참고 대상이지 우리가 바로 사용할 신뢰도 공식이 아니다. 모델이 말하는 '90% 확신'은 자동으로 90% 정확한 확률이 되지 않는다. 현재 작업군의 별도 calibration 없이 합의 가중치나 수용 gate에 넣지 않는다. 예전 논문의 모델 접근 방식을 현재의 공식 구독 연결 정책으로 옮기지도 않는다.

MoA Table 2의 65.1%와 GPT-4 Omni의 57.5%는 **length-controlled 선호 승률**이다. 여러 호출·합성 비용을 쓰는 품질 실험이지, 단일 호출보다 항상 더 싸거나 사실 검증이 완료됐다는 결과가 아니다. 해당 논문의 다른 aggregator 변형과 첫 페이지 숫자를 섞지 않는다. 결정 D11/D14/D17.

## 5. 강한 모델끼리의 역할 분담 사례

### 5.1 Aider architect/editor — 추론과 편집은 다른 역할

기존 v0.3의 E17 [Aider 사례](https://aider.chat/2024/09/26/architect.html)를 계승한다. 설계를 잘하는 모델과 편집 형식을 잘 지키는 모델을 나누는 방식이다. 기존 문서의 85%는 2024년 당시 benchmark 결과이며 현재 모델에 대한 순위가 아니다. 이것은 '상급 모델 회의'와 다르지만, 상급 계획 → 적합한 구현 → 상급 검토라는 구조의 좋은 비교 대상이다.

### 5.2 병렬 Claude 컴파일러 — 강한 팀도 외부 검증이 핵심

2026-02-05 [F16 제작자 보고](https://www.anthropic.com/engineering/building-c-compiler)는 16개 Claude, 약 2,000 session, 약 2만 달러 API 지출의 대규모 컴파일러 실험을 설명한다. 강한 모델 팀의 작업 분담 사례이지 cross-vendor debate는 아니다. 검사·비교용 GCC, 작업 분리, 회귀 방지와 테스트 설계가 중요했다. 컴파일러의 남은 제약과 인간이 준비한 검증 환경도 함께 기록되어 있다.

우리가 가져올 것은 테스트 가능한 단위와 독립 작업 공간이다. 모델 수만 늘리거나 글의 장시간 실행 loop를 그대로 복제하는 것은 채택하지 않는다. 강한 모델 팀의 가능성을 보여주지만 저비용·무인 production을 입증하지는 않는다. 결정 D10/D15/D17.

### 5.3 생성자/평가자 분리 — 마지막 수정이 항상 최선은 아니다

2026-03-24 [F21 harness 실험](https://www.anthropic.com/engineering/harness-design-long-running-apps)은 생성과 평가를 나누고 명확한 기준 및 실제 브라우저 상호작용을 사용한다. 분리해도 평가가 관대할 수 있으며, 작성자가 마지막 결과보다 중간 결과를 선호하는 사례도 설명한다. 우리 설계에서는 초기 후보·중간 후보를 보존하고 검증된 후보를 선택한다. 라운드 수 증가 자체를 품질 개선으로 집계하지 않는다. 결정 D12/D13/D17.

## 6. 부정적인 결과를 설계의 입력으로 사용하기

| 근거 | 확인한 반례/쟁점 | 예방 또는 측정할 것 |
|---|---|---|
| [F10 ICML 2024](https://proceedings.mlr.press/v235/smit24a.html) | 기본 MAD가 단순 ensemble/self-consistency를 안정적으로 능가하지 않음. 조정된 설정에서는 개선 가능 | 같은 예산의 단일 모델·독립 다회 생성과 비교. 토론 전면 부정으로도 일반화하지 않음 |
| [F11 평가 비판 v3](https://arxiv.org/abs/2502.08788v3), 2025 | 약한 baseline·추가 compute를 간과한 평가 비판 | 단일 상급 모델에 같은 자원을 준 대조군, 이종 모델 효과와 토론 효과 분리 |
| [F12 Talk Isn't Always Cheap v2](https://arxiv.org/html/2509.05396v2), 2025 | 혼합 능력 토론에서 처음 맞던 답이 다른 모델의 오류에 영향을 받아 틀릴 수 있음 | 독립 초안 보존, correct-to-wrong 전이, 맞는 소수 의견이 합성에서 사라지는 비율 |
| [F13 Preserving Disagreement v1](https://arxiv.org/html/2604.26561v1), 2026-04-29 | 정책 시뮬레이션에서 다양성과 coherence weighting의 긴장 | 가치·목표 차이는 사실 오류와 다르게 처리. 미합의를 강제 삭제하지 않음 |
| [F20 LLM-as-a-Judge v4](https://arxiv.org/abs/2306.05685v4), 2023 | 위치·장황함·자기 선호 등 judge 편향 | 익명화, 순서 교환, 자기 평가 분리, 근거·시험 기반 확인 |

F10/F11/F20은 이번 조사에서 abstract 수준으로 사용한다. F12는 당시 소형/혼합 모델 조건이며 세 회사의 2026년 상급 모델 전체를 시험한 연구가 아니다. F13은 120회·두 정책 시나리오의 탐색적 연구이며 사실 문제 정답률 근거가 아니다. 이 차이를 지우고 '토론은 항상 실패한다' 또는 '회사만 다르면 해결된다'고 결론 내리지 않는다.

**설계상 결론:** 기본값은 끝없이 설득하는 팀이 아니라, 독립 해결 후보를 먼저 확보하고 필요한 쟁점만 검토하는 팀이다. 검증 못 한 의견 차이는 정상적인 산출물이다. 결정 D11–D13/D17.

## 7. 도입 판정과 조사 범위

| 대상 | 현재 판정 |
|---|---|
| 상급 모델 독립 초안과 교차검증 | v0.4의 정식 실행 모드로 설계. 품질 이득은 사용자 workload에서 검증 예정 |
| Perplexity / Microsoft | 기능·제품 구조의 reference. 사용자의 구독 bridge로 대체 도입하지 않음 |
| karpathy council | 간결한 프로토콜 reference. 운영 core로 그대로 채택하지 않음 |
| PAL consensus/clink | consensus의 API/custom 경로와 문서/코드 차이를 확인. 권한·실행·agy 호환성 미검증으로 필수 의존성 채택 보류 |
| 별도 hosted multi-agent 서비스 | [F14 Managed Agents](https://www.anthropic.com/engineering/managed-agents)의 상태/하네스/격리 분리는 참고. 구독 우선 core를 대체하지 않음 |
| Jev / 저가 분류 모델 | 작업 분류·중복 후보 선별·shadow 판단 후보. 상급 검증자의 판정을 대체하지 않음 |

24개 F 기록은 24개의 독립 실험을 뜻하지 않는다. F22–F24의 최근 연구와 보류한 SatCom 논문은 [후속 근거 검토](EVIDENCE_FOLLOWUP.md)에 별도로 정리했다. 제품 문서·코드·논문·정책 재확인을 합친 근거 원장이다. 기존 E01–E31 중 F17/F18/F19는 각각 E02/E05/E08의 재확인이다. X·커뮤니티·검색 결과는 발견 경로였으며 확인하지 못한 사용 후기, 인기, star 수를 성공률 근거로 쓰지 않았다. 전수 조사나 무결점 검증을 주장하지 않는다.
