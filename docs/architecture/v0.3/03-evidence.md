# 근거 평가: 무엇이 확인됐고 어디까지 적용되는가

확인 기준일 2026-09-22. **아래 성과는 외부 저자/제작자의 결과이며 이 저장소에서 재현하지 않았다.** 논문·제품 기능·제작자 benchmark·우리 추론을 구분한다. 수치와 제한을 함께 읽는다. 원문 버전·locator·decision 연결은 [sources.json](sources.json)에 있다.

## 1. 근거를 읽는 방법

- peer-reviewed 연구도 실험한 task/model/가격 범위 밖의 효과를 보장하지 않는다.
- 공개 논문과 코드가 있으면 실험 조건을 검토할 수 있지만 재현했다는 뜻은 아니다.
- 실제 production 사례는 현실성의 근거지만 비공개 traffic·평가지표·자체 보고의 한계가 있다.
- 공식 문서는 **기능·인증·과금 의미**의 근거이지 성능 우월성의 근거가 아니다.
- X는 새로운 글을 발견하는 경로로 사용했다. 앞선 조사에서 관련 원문 직접 접근은 403이었으며, 검색 snippet이나 재인용을 성과 검증 근거로 채택하지 않았다. 상세 접근 기록은 [첫 조사](../../research-2026-09-22/README.md)를 본다.

## 2. 전체 구조를 지지하는 논문과 반례

| 근거 | 실험/관찰과 결과 | 이 설계로 가져올 것 | 가져오면 안 되는 주장 |
|---|---|---|---|
| E12 [FrugalGPT v1](https://arxiv.org/html/2305.05176v1), 2023 | HEADLINES·OVERRULING·COQA의 학습 cascade. Table 3의 같은 정확도 비용 절감은 각각 98.3%, 73.3%, 59.2% | task별 작은 모델 적합성과 실패 시 상향의 경제성을 측정 | ‘여러 CLI를 묶으면 98% 절약’ |
| E13 [RouteLLM v4](https://arxiv.org/html/2406.18665v4), [ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/5503a7c69d48a2f86fc00b3dc09de686-Abstract-Conference.html) | 선호 데이터로 strong/weak 응답 routing. 공개 평가의 품질/비용 trade-off 및 2배 이상 절감 보고 | 가능한 한 작업 시작 전에 한 후보를 고르는 낮은 overhead routing, calibration/held-out 평가 | QA/chat router의 점수가 coding trajectory 성공 확률이라는 주장 |
| E14 [MAST v3](https://arxiv.org/abs/2503.13657v3), 2025 | 7 framework의 1600+ annotated trace, 14 failure mode, 설계·정렬·검증의 3범주 | 역할·소유권·중단 조건·검증 결과를 명시적 계약으로 만듦 | agent를 많이 두면 스스로 오류를 고친다는 가정 |
| E15 [Scaling Agent Systems v3](https://arxiv.org/html/2512.08296v3), 2026-04-08 | 6개 benchmark·260설정으로 확대. 분해 가능한 task와 순차 의존 task의 결과가 다름 | 독립성 확인 후 병렬화, single-agent 기준선과 전체 비용 비교 | 복잡한 task일수록 큰 팀이 항상 유리하다는 규칙 |
| E16 [SWE-Pruner v4](https://arxiv.org/html/2601.16746v4), 2026-05-07 | SWE-bench Verified 500문항. Sonnet 353→360 해결/token -23.1%; GLM 277→283/token -38.3% | 원문 trace를 남기는 좁은 read-only context 선택 실험 | 모든 task에서 손실 없는 압축, pruning 계산이 공짜라는 가정 |

FrugalGPT는 생성 후 점수로 다음 모델을 호출하는 **cascade**, RouteLLM은 생성 전 후보를 고르는 **router**다. 두 구조는 추가 호출 수와 지연이 다르다. 우리는 초기에는 규칙으로 한 worker를 고르고 실제 검증 실패 때만 한 번 수리하는 흐름을 쓴다. 학습 router의 이익은 그 단순한 기준선을 넘어야 한다.

**개정판 차이를 실제로 확인했다.** E15 [v1](https://arxiv.org/html/2512.08296v1)은 180설정, v3는 SWE-bench Verified·Terminal-Bench를 포함한 260설정이다. 최신판도 모델군 내부의 제한된 이질성에 대한 실험이며 제품 세 개의 협업을 직접 검증한 것은 아니다. 특정 성공률 임계값을 모든 작업의 팀 생성 규칙으로 옮기지 않는다.

E16 [v1](https://arxiv.org/html/2601.16746v1)은 pruning 후 351/274 해결, v4는 360/283 해결이다. 이전 저장소 문서의 수치는 v1의 역사적 기록이며 현재 검토는 v4를 기준으로 한다. 이 변경 원인을 별도로 재현·규명한 것은 아니다. 최신판도 SWE-QA의 일부 GLM 평가에서는 점수가 낮아져 모든 작업의 무손실을 주장하지 않는다. 논문의 API token 감소를 구독 quota 감소로 자동 환산하지 않는다. E14의 수치는 v3 abstract에서 확인한 범위다.

## 3. 실제 제작·운영에서 얻은 것

| 근거 | 보고된 성과와 조건 | 의미 |
|---|---|---|
| E17 [Aider architect/editor](https://aider.chat/2024/09/26/architect.html), 2024-09-26 | o1-preview + o1-mini 또는 DeepSeek 편집 조합 85%. 당시 code-editing benchmark이며 최고 조합은 whole-file 출력 때문에 느리다고 저자가 설명 | 추론 능력과 편집 형식 준수 능력은 다른 역할이다. 두 단계 비용/지연도 측정해야 함 |
| E18 [Cursor agent swarm](https://cursor.com/blog/agent-swarm-model-economics), 2026-07-20 | Rust로 SQLite를 만드는 장기 과제. planner/worker 분리 및 모델 조합을 비교. 혼합 조합 $1,339와 GPT-5.5 전체 조합 $10,565 등의 결과 보고 | 역할별 능력 차이와 하네스 개선이 모두 중요. 특정 과제·실험 시간·성공 기준의 회사 자체 결과 |
| E30 [Cursor Router](https://cursor.com/blog/how-cursor-router-works), 2026-08-06 | production traffic에서 품질 proxy·비용·cache switching을 평가한 routing 설명 | 단순 token 단가보다 사용자 수용과 전환 비용을 함께 최적화. 비공개 router를 그대로 재현할 수는 없음 |
| E20 [Anthropic multi-agent research](https://www.anthropic.com/engineering/multi-agent-research-system), 2025-06-13 | 내부 research 평가의 상대 개선 90.2%, 높은 token 소비도 보고. multi-agent의 약 15배는 일반 chat 대비 | 넓게 독립 조사할 때 유용할 수 있으나 작은 coding task의 기본 팀 구성 근거는 아님 |
| E11 [Antigravity Teamwork](https://www.antigravity.google/docs/teamwork/), 확인 2026-09-22 | 공식 paid-plan preview가 탐색·구현·critic/challenger/auditor, milestone·격리 디렉터리를 설명 | 사용 가능한 native 팀 구조의 참고. 공개 비용 대조 실험이 아니므로 경제성 확정 불가 |

위 사례에서 추출하는 공통점은 **모든 agent가 같은 긴 대화를 공유하지 않고, 역할·산출물·검증을 분리한다**는 것이다. 이것은 우리 설계적 해석이다. 각 사례의 85%, 90.2%, 비용 차이를 평균내어 ‘팀워크 효율’ 하나로 만들지 않는다.

## 4. 비용 절약처럼 보이지만 기준선에 따라 달라지는 결과

### E19 — 저가 단독과 비교해야 한다

[Switchyard benchmark](https://www.langchain.com/blog/switchyard-agent-routing-benchmark)의 145개 multi-turn 과제에서 frontier는 86%/$11.45, routed는 80%/$3, cheap은 77.7%/$0.72로 보고됐다. router의 judge 비용 비중은 21.2%였다. cheap 대비 routed의 2.3 percentage-point 개선은 보고된 약 2.7pp run 변동보다 작다.

우리 해석: frontier보다 싸다는 사실만으로 router 채택을 결정하면 안 된다. **cheap 단독이 이미 충분한지**를 먼저 봐야 한다. 이 결과를 ‘routing은 쓸모없다’고 일반화할 수도 없다. task군·품질 기준·분산을 같이 비교한다.

### E21 — 해결당 비용과 전체 지출은 다른 지표다

[Fusion Terminal-Bench](https://docs.litellm.ai/blog/fusion-terminal-bench-benchmark)의 21과제에서 single은 9해결/$67.13, Fusion은 14해결/$91.64였다. 총지출은 약 36% 늘지만 해결당 비용은 약 12% 줄었다. 지연도 늘었다.

우리 해석: 어려운 작업의 최종 성공이 더 중요한 경우 선택할 수 있으나 ‘token과 총지출을 줄이는 기본 경로’로 넣을 근거는 부족하다. 여러 후보를 항상 실행한 뒤 합성하는 정책은 별도 예산이 있는 실험군으로 둔다.

### E31 — 같은 해결 수가 같은 품질은 아니다

[LiteLLM Auto Router](https://docs.litellm.ai/blog/auto-router-capability-benchmark)의 SWE-bench Verified 25과제에서는 router와 Opus가 각각 23개를 해결했고 비용은 $11.15/$20.27이었다. 설정당 1회이며 해결한 과제들이 같지 않았다. 저비용 가능성을 보여주지만 일반화·분산·regression 분석을 대신하지 못한다.

## 5. context와 Jev의 근거를 과장하지 않기

E27 [context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)은 필요한 원문을 식별자로 나중에 읽는 구조를 뒷받침한다. E29 [MCP code execution](https://www.anthropic.com/engineering/code-execution-with-mcp)의 150k→2k, 98.7% 감소는 도구 정의·데이터 처리의 특정 예다. 원문을 저장하고 코드로 선별하는 방향은 채택하되 전체 작업 절감률로 인용하지 않는다.

E24 [Jev 소개](https://typesafe.ai/blog/introducing-system-one-models-and-jev)는 typed decision 부품의 가능성을 제시한다. E25 [Jev router benchmark](https://docs.litellm.ai/blog/jev-auto-router-benchmark)는 80 synthetic prompt × 3 반복의 분류 성능·비용을 비교했고, E26 [compaction](https://docs.litellm.ai/blog/typesafe-jev-compaction)은 짧은 tool-result 정리 사례다. 모두 현재 사용자의 coding 작업 성공과 구독 한도 절감을 입증한 실험이 아니다.

그래서 Jev를 지금 핵심 router로 고정하지 않는다. 먼저 규칙·직접 실행 기준선을 만들고, 나중에 **실제 배정에 영향을 주지 않는 shadow 판단**을 수집한다. classifier의 label agreement뿐 아니라 잘못 낮은 모델로 보냈을 때의 실패 비용·추가 호출·지연까지 평가한다. 로컬 가중치·장비 성능·한국어/코드 혼합 입력 적합성은 별도 미확인 항목이다.

## 6. 적용할 수 있는 결론의 강도

| 결론 | 판정 |
|---|---|
| 공식 CLI의 native 실행을 감싸면서 하네스를 유지하는 구조는 가능한가 | 공식 인터페이스 근거 있음. 사용자 환경 conformance는 미실시 |
| 역할별 다른 모델 배정이 좋은 결과를 낸 사례가 있는가 | 있음. 과제·하네스·평가 범위가 제한됨 |
| 다중 agent가 단일 agent보다 항상 좋은가 | 근거가 지지하지 않음 |
| JSON을 쓰면 token이 자동으로 줄어드는가 | 근거 없음. 반복 문맥/로그·조정 호출을 줄이는 실제 설계가 필요 |
| 이 사용자의 구독 세 개로 실제 얼마를 아낄 수 있는가 | 아직 모름. 계정별 quota와 동일 과제의 paired 실험 필요 |
| Jev를 로컬에 붙여야 시작할 수 있는가 | 아님. native adapter·task 계약·검증·회계를 먼저 만들 수 있음 |

이 표가 현재 결론이다. 이후 실측이 생기면 외부 성과를 덮어쓰지 말고 별도 `runs/` 결과와 실험 manifest를 추가한다.
