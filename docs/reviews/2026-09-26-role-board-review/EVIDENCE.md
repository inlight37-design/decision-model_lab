# 역할판 검토 — 근거 대조

2026-09-26 · [검토 본문](README.md)의 근거. 이 문서는 검토 내부의 출처표이며 sources.json의 새 항목이 아니다.

기준 코드는 `9526bbe382b68c74bd7d784c09af3e02f55393ca`. **코드·기록을 직접 읽은 것과 사용자 PC에서 실행한 것은 다르다.** 이번에는 사용자 PC·WSL·실제 모델 CLI에 접근하지 않았다. 아래 외부 문서는 이 날짜에 직접 열었다. ‘전문 해당 절’은 그 논문의 초록·방법/결과 중 필요한 절을 대조했다는 뜻이며 전체 부록·코드·실험을 재현했다는 뜻은 아니다. ‘초록’은 저자 초록만 확인한 것으로 수치의 표·분모·실험 조건까지 검증하지 않았다. 원문 미확인은 마지막 절에 따로 남긴다.

## A. 저장소의 코드·기록

| ID | 직접 읽은 위치·관측 | 요청 연결·해석 |
|---|---|---|
| C1 | `core/contract.py`, `template`·`revision`: --model 값은 가리지만 다른 실행 옵션과 ro/rw 연결은 판에 포함 | P4·G1 / 질문4. 모델 이름을 가린다는 사실이 모든 effort의 경계 동등성을 증명하지 않음 |
| C2 | `core/adapters.py`, `build_spec`·`_check`: Claude·Codex는 effort가 None이 아니면 거절. Codex -c도 정확한 허용 조각만 수용 | P4·G1 / 질문4·8. 공식 옵션이 존재해도 연결·검사·관측이 별도로 필요 |
| C3 | `app/live_config.py`, `Provider`·`validate`: provider당 모델 하나, 서로 다른 provider 1–2개. `app/cli_executor.py`가 모델을 최종 계획에 전달 | W1–W5 / P4·P10·G1 / 질문1·8. 역할 인스턴스의 설정과 provider의 공유 예산을 분리해야 함 |
| C4 | `app/controller.py`의 `pump`는 work_root/run_id/pid. 실제 `app/cli_executor.py`의 HOME은 `self.home`, `core/isolation.py`의 `plan`은 그 HOME 경로를 상자 안에 재구성 | G1·P7 / 질문5·7. 실제 CLI HOME이 작업 폴더 옆 -home이라는 설명은 틀림. 작업 폴더가 시도별로 다른 것은 맞음 |
| C5 | `app/codex_account.py`, `query`: 모델 없는 model/list 조회가 이미 있으며 현재는 모델 ID 목록을 투영 | W1·P4·G4 / 질문4·8. supportedReasoningEfforts 등을 호환성 확인 후 허용 목록으로 투영할 후보가 있음. 사용자 설치판의 실제 반환값은 이번에 관측하지 않음 |
| C6 | 아래 세 기록의 지정된 실행·초안 | G2·P7 / 질문5·7. 전사 수치는 일치. 어떤 문서·prefix가 캐시됐는지는 합계만으로 확정 불가 |
| C7 | [v0.4 설계](../../architecture/v0.4/02-frontier-architecture.md) §1–5, [app 안내](../../../app/README.md)의 파일 책임·실제 실행·공개 정책 | P1–P6·G1·G8 / 질문1–3. v0.4는 설계 제안이며 일반 모드 전체가 구현됐다는 뜻이 아님 |
| C8 | [토큰 낭비 측정](../../research-2026-09-22/measurement-and-rollout.md) §1–3, [작업 방식 조사](../../research/multi-ai-workflow-2026-09-25/README.md) §1–3, [후속 검토](../2026-09-25-workflow-evaluation/README.md) §1–2 | G8·P7 / 질문5·7. 기존에도 입력 길이·비용·품질·지연의 구분과 개발 기억/독립 실행의 분리가 있음. 새 프레임워크부터 만들 필요가 없다는 설계 근거 |

C1–C5 고정 소스: [contract](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/core/contract.py), [adapters](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/core/adapters.py), [live_config](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/app/live_config.py), [cli_executor](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/app/cli_executor.py), [isolation](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/core/isolation.py), [controller](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/app/controller.py), [account](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/app/codex_account.py).

### C6 — G2의 세 행을 실제 기록과 대조

| 실제 위치 | Codex: input / cached / reasoning | Claude: 새 input / cache creation / cache read |
|---|---|---|
| [strict ledger-summary](../2026-09-25-strict-live-run/ledger-summary.json), `dml-live-strict-20260925.participants` | 12524 / 9984 / 0 | 2 / 753 / 5728 |
| [L1 analysis](../../experiments/2026-09-25-l1/analysis.json), `tasks[t1].drafts` | 12597 / 9984 / 0 | 2 / 2021 / 4587 |
| [D 후속 analysis](../../experiments/2026-09-25-d-followup/analysis.json), `runs.t4-px.participants` | 12707 / 9984 / 453 | 2 / 1048 / 5728 |

D의 단독 T4와 병렬 T4는 별도 실행이다. 위 행은 요청서와 같은 `t4-px`다. G2의 수치는 틀리지 않았지만 ‘질문·자료는 전부 새로 계산’과 ‘0이므로 effort none’은 이 기록이 직접 증명하지 않는다. 같은 캐시 크기의 반복은 관측이고 특정 prefix가 원인이라는 해석은 가설이다. 회사별 input 필드의 포함 관계와 reasoning/output 중복 가능성도 구분해야 한다.

## B. 공급자 공식 문서

| ID | 직접 연 원문·확인 위치 | 결과와 적용 범위 |
|---|---|---|
| O1 | [Codex App Server](https://learn.chatgpt.com/docs/app-server), model/list | supportedReasoningEfforts·defaultReasoningEffort·nextCursor를 설명. 실제 계정·클라이언트의 목록과 기본값은 관측 필요 |
| O2 | [Codex config reference](https://learn.chatgpt.com/docs/config-file/config-reference), model_reasoning_effort | 설정 통로가 존재. 별도 추론 플래그가 저장된 도움말에 없다는 사실만으로 기능 부재를 판단하지 않음 |
| O3 | [Codex pricing](https://learn.chatgpt.com/docs/pricing), credit prices 앞 주의문 | 크레딧 가격만으로 구독 포함 사용량이 결정되지 않는다고 명시. 캐시 입력 크레딧 할인율을 포함 한도의 같은 할인율로 옮길 수 없음 |
| O4 | [Claude Code prompt caching](https://code.claude.com/docs/en/prompt-caching), prefix·directory·effort·TTL·fork | 경로·도구·환경·앞부분이 영향을 줌. 같은 경로만 맞추면 충분하지 않음. effort별 캐시 구분은 모델 예외가 있고 -p·subagent·로그인 방식의 TTL도 구분. fork는 부모 문맥 상속을 포함하므로 독립 초안에 적용하지 않음 |
| O5 | [Claude model configuration](https://code.claude.com/docs/en/model-config), Adjust effort level·Organization effort limits | 지원 강도와 하향 적용을 명시. stream-json에서 조직 제한이 조용히 적용될 수 있음. ultracode는 단순 scalar가 아니라 내부 workflow도 켜므로 low–max와 일괄 동등 승인할 수 없음. 이 기능의 로컬 적용은 미관측 |
| O6 | [Claude Code costs](https://code.claude.com/docs/en/costs) | API 상당 비용과 구독 사용량은 별개. 팀의 약 7배는 특정 plan-mode 비교 조건이며 모든 팀의 고정 배율이 아님 |
| O7 | [Claude CLI reference](https://code.claude.com/docs/en/cli-reference), --exclude-dynamic-system-prompt-sections·--fork-session | 문서에 해당 옵션이 있음. 동적 구간 이동은 삭제/격리 증명이 아니고 fork는 새 ID여도 이력을 받음. 설치 CLI에서 옵션 지원·효과를 시험하지 않음 |
| O8 | [Claude subagents](https://code.claude.com/docs/en/sub-agents), fresh context·fork | 기본 새 문맥과 부모 이력을 받는 fork를 구분. -p에서 fork 기본 끔이라는 설명 확인. 새 문맥 자체가 우리 OS 경계·정족수의 증명은 아님 |
| O9 | [Claude API prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) | API cache creation/read/input 항목이 구분됨. API 가격과 생성·적중 시점의 설명은 포함 구독 한도 산식이 아님 |
| O10 | [OpenAI API prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching), 모델 세대별 동작·가격·minimum | 현재 문서는 GPT-5.6 이후와 이전 모델의 최소 길이·경계·쓰기 가격을 나눠 설명한다. ‘모든 모델이 1024 이상이면 같은 캐시 규칙’으로 단순화하지 않음. 최신 API의 명시적 breakpoint와 쓰기 가격이 Codex 구독 CLI에 그대로 노출된다는 뜻도 아님 |
| O11 | [Better prompt caching for GPT-6](https://openai.com/index/better-prompt-caching-for-gpt-6/), 2026-09-22 발표 | API의 캐시·가시성 개선을 추가 확인. 이를 근거로 구독 CLI의 prefix/예열을 제어할 수 있다고 가정하거나 유료 API·예열 호출을 도입하지 않음 |
| O12 | [Anthropic multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system), 2025-06-13 | 4배/15배는 각각 chat 대비 agent/multi-agent의 저자 보고. 상세 분담·외부 산출물 참조·의존성이 큰 작업의 한계를 설명. 우리 앱의 고정 소비 배율이나 품질 보장은 아님 |
| O13 | [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents), 2025-09-29 | 필요한 때 원문을 읽는 가벼운 참조와 구조화된 기록을 제안. 무조건 가장 짧은 요약이나 공통 필수 조건 삭제를 권한 것은 아님 |

### O14 — 모델 선택의 추가 과금 경계: RB-04·RB-05에 붙이는 구현 전 보강 [높음]

**연결: W1·W2·W10 / P4·P5·P10 / G1·G3·G4 / 질문 1·3·4·8.**

[Claude model configuration의 Fable and usage credits](https://code.claude.com/docs/en/model-config#fable-and-usage-credits)는 계정/좌석에 따라 Fable이 포함 한도가 아닌 usage credits를 사용하며, **-p·Agent SDK 비대화형 경로에서는 크레딧 청구 확인창을 띄우지 않는다**고 명시한다. 이것은 사용자 계정에 실제 청구가 생겼다는 관측이 아니라 공식 문서에 있는 동작이다.

따라서 모델 목록에 있거나 구독으로 로그인돼 있다는 조건만으로 새 모델의 ‘추가 크레딧 없음’을 승인하면 안 된다. 역할에 배정할 **모델별 funding 조건**을 확인하고, 현재 구독 전용 정책 아래에서는 추가 크레딧 경로 또는 그 여부가 미확인인 선택을 실행 전에 막아야 한다. 이름/과금 메타데이터를 모델 호출 없이 확인할 수 없는 경우에는 관측된 좁은 모델 목록을 유지한다. 실제 호출을 보내 보고 과금 여부를 알아내자는 제안이 아니다. 결과의 모델 불일치 검사도 이미 발생한 추가 소비를 되돌리지는 못한다.

이 보강은 모델 고르기 요구(W1)를 취소하는 것이 아니라 같은 요구 안에서 W10의 기존 비용 제한을 유지하는 조건이다. 이번에는 계정 설정이나 결제/크레딧을 조회·변경하지 않았다.

## C. G5 도구·프레임워크

모두 아이디어의 출처로 읽었으며 설치·채택·사용자 계정 연결을 하지 않았다.

| ID | 직접 연 원문·범위 | 확인과 한계 |
|---|---|---|
| T1 | [Aider repo map](https://aider.chat/docs/repomap.html), map 구성·token budget | 관련 기호/관계를 선별한 지도. 기본 1000은 조절되는 목표이며 모든 작업의 절대 상한이 아님 |
| T2 | [MetaGPT role.py](https://github.com/FoundationAgents/MetaGPT/blob/main/metagpt/roles/role.py), _watch·set_addresses·_think; 읽은 blob `49b1d1787ecf30616bd670b0e96dca676908ce5e` | 메시지 구독/주소 라우팅이 존재. 역할 이름이나 구독 필터 자체를 우리 파일 접근 경계로 보지 않음. 코드 실행은 하지 않음 |
| T3 | [MCP memory README](https://github.com/modelcontextprotocol/servers/blob/main/src/memory/README.md), core concepts·API; 읽은 blob `de7be2c060013ecf96e18f33ff8df7df700d09aa` | 개체·관계·관찰의 지속 기억이라는 설명은 맞음. 정보의 참/거짓 판정이나 독립 참여자 간 격리를 제공한다는 증거는 아님 |
| T4 | [OpenAI Agents SDK handoffs](https://openai.github.io/openai-agents-python/handoffs/), input filters·nested history | 기본 전체 이력 전달과 명시 필터가 구분됨. input_type은 이력 가림이 아니고 요약된 이력도 비밀 제거를 보장하지 않음. 구독 CLI 전용 앱에 SDK 통째 채택을 권하지 않음 |
| T5 | [LangGraph memory concepts](https://docs.langchain.com/oss/python/concepts/memory), long-term memory | namespace/key로 장기 기억을 구성. namespace가 OS 권한 경계인 것은 아님 |
| T6 | [CrewAI memory v1.15.22](https://docs.crewai.com/v1.15.22/en/concepts/memory) | 관련 기억 검색 외에 저장·정리·회상에 모델/embedding 비용이 들 수 있음. ‘파일보다 편하므로 공짜’로 평가하지 않음 |
| T7 | [Cognition 초기 글](https://cognition.com/blog/dont-build-multi-agents), [후속 글](https://cognition.com/blog/multi-agents-working), 후속 2026-04-22 | 문맥 분리로 암묵적 결정이 어긋나는 위험과 한 쓰기 흐름에 여러 지능을 보태는 조건부 활용을 함께 읽음. 모든 multi-agent를 금지한다는 결론으로 축약하지 않음 |

## D. G6·G7 연구 수치

아래 숫자는 **저자 보고**이며 우리 구독 CLI에서의 예상 절감률이 아니다. 초록만 읽은 행은 표의 수치 재계산·통계·재현을 하지 않았다.

| ID | 원문·확인 범위 | 대조 결과·조건 |
|---|---|---|
| R1 | [S2-MAD v1](https://arxiv.org/html/2502.04790v1), 전문의 초록·방법·결과 | 최대 94.5%와 일치. 정답 형식/동일성 검사를 자유 서술의 소수 반례 제거기로 쓰지 않음. 최대 절감률과 과제별 정확도를 함께 봐야 함 |
| R2 | [Single-agent or Multi-agent? v1](https://arxiv.org/html/2505.18286v1), 초록·서론·결론 | 본문에 최대 88.1%가 실제로 있음. 같은 판 초록은 최대 20%여서 내부 표기가 다름. 동일 분모로 표를 재계산해 해소하지 못했으므로 일반 기대치로 쓰지 않고 차이를 남김 |
| R3 | [Agentic Plan Caching v2](https://arxiv.org/html/2506.14852v2), §4.2 | 50.31%는 평균 비용 절감. 96.61%는 정확도가 가장 높은 기준선 대비 유지 성능 비율이지 절대 정답률이 아님. 계획 재사용은 일반 작업의 후보 |
| R4 | [When Single-Agent with Skills Replace Multi-Agent Systems and When They Fail v2](https://arxiv.org/html/2601.04748v2), Table 3·결과 | 평균 토큰 53.7% 감소·정확도 차이 약 +0.7%p. GSM8K는 -2%p. 실패 조건과 과제별 저하를 함께 기록 |
| R5 | [Rethinking the Evaluation of Efficiency Methods for Multi-Agent Systems v1](https://arxiv.org/html/2609.05933v1), 통제 평가·matched random pruning | 모델·과제·도구·예산을 맞춘 단일/무작위 대조가 필요하다는 근거. 실제 사용자가 배치한 팀원이나 검토를 무작위 삭제하라는 지침이 아님 |
| R6 | [AgentPrune](https://arxiv.org/abs/2410.02506), 저자 초록 | 28.1%–72.8%는 초록과 일치. 그래프 최적화 비용을 우리 작은 호출 예산에서 검증하지 않음 |
| R7 | [AgentDropout](https://arxiv.org/abs/2503.18891), 저자 초록 | 입력 21.6%·출력 18.4% 감소는 초록과 일치. 실시간 무료 가지치기라는 뜻은 아님 |
| R8 | [Sparse communication topology](https://arxiv.org/abs/2406.11776), 저자 초록 | 희소 통신으로 비용을 줄이면서 비교 가능한 성능이라는 연구. 이 앱의 토폴로지·품질에 대한 실증 아님 |
| R9 | [MetaGPT](https://arxiv.org/abs/2308.00352), 저자 초록; T2 코드 별도 | 역할·표준 절차·단계 산출물이 핵심. 역할 프롬프트만 추가하면 오케스트레이션과 격리가 생긴다는 뜻 아님 |
| R10 | [bMAS](https://arxiv.org/abs/2507.01701), 저자 초록 | 공유 보드와 제어 구조의 참고. 모든 정보/전체 문제를 공유하는 설계이므로 최소 권한·선택적 읽기 절약의 직접 근거로 삼지 않음 |
| R11 | [SupervisorAgent](https://arxiv.org/abs/2510.26585), 저자 초록 | 평균 29.68% 토큰 감소 보고. 무모델은 개입을 거르는 필터이며 감독자의 실제 추론까지 무료가 아님 |
| R12 | [Chain of Agents](https://arxiv.org/abs/2406.02818), 저자 초록 | 구간별 읽기·순차 전달과 취합의 참고. 보고된 성능 이득을 토큰 절감률로 바꾸지 않음 |
| R13 | [Towards a Science of Scaling Agent Systems](https://arxiv.org/abs/2512.08296), 저자 초록 | 과제·협업 구조·도구 의존성에 따른 결과. 에이전트 수 증가의 보편적 이득으로 해석하지 않음 |
| R14 | [Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657), 저자 초록 | 실패 분류를 평가표 후보로 참고. ‘종종 이득이 작다’가 모든 multi-agent의 실패 증명은 아님 |
| R15 | [KVCOMM](https://arxiv.org/abs/2510.12872), 저자 초록 | 학습 불필요여도 모델 내부 KV에 접근해야 함. 현재 구독 CLI에 직접 이식 가능한 기능으로 보지 않음 |
| R16 | [DroidSpeak](https://arxiv.org/abs/2411.02820), 저자 초록 | 호환 구조 모델의 중간 계산 재사용. 서로 다른 회사의 닫힌 CLI 사이 범용 KV 공유라는 뜻 아님 |
| R17 | [Cache-to-Cache](https://arxiv.org/abs/2510.03215), 저자 초록 | KV의 신경망 투영/게이팅이 필요. 현재 native CLI가 그 제어권을 노출하는지는 관측되지 않음 |
| R18 | [Optima](https://arxiv.org/abs/2410.08115), 저자 초록 | 반복 생성·선택·학습을 포함. 구독 CLI 설정 몇 개로 같은 효과를 내는 방법이 아님 |
| R19 | [DocuTeam](https://arxiv.org/abs/2609.29309), 2026-09-24 제출, 저자 초록만 | W7–W9에 가까운 문서 중심 혼합 주도 UI 연구. 20명 연구의 평가를 우리 앱의 검증·생산성 보장으로 옮기지 않음. 구현/부록은 미열람 |

## E. 확인하지 못했거나 이번 검토로 확정하지 않는 것

- G4의 특정 Codex HEAD `25270df`에서 `fork_context`·`fork_turns`·exec fork·부모 캐시 키 시험이 정확히 어떤 조건인지 **이번에는 해당 고정 소스를 재검증하지 않았다**. 요청서의 보조 조사 수준을 유지한다. 공식 API/CLI 문서 확인으로 그 테스트의 구독 경로 적용까지 증명했다고 하지 않는다.
- 사용자 PC에 있는 모든 모델/effort의 실제 가용성, 선택값의 실제 적용, 하향 적용·fallback의 차단, 모델별 추가 과금 여부는 미관측이다. O14 때문에 ‘구독 로그인 성공→아무 모델이나 포함 한도’라고 해석하면 안 된다.
- 캐시 입력이 Claude Pro/Max·ChatGPT 포함 사용량에서 정확히 얼마나 덜 차감되는지 계산할 수 있는 공개 계약은 확보하지 못했다. API·크레딧 가격과 관측 cache counters는 그 답의 대체물이 아니다.
- 요청서의 Claude 도움말에 없는 새 웹 문서 옵션을 aux-pc-wsl에서도 쓸 수 있다고 간주하지 않았다. 고정 실행 계획에 넣기 전 해당 설치판에서 확인할 사항이다.
- 논문 전체 실험의 재현, 저자 구현의 버그 검토, 제안된 UI의 실제 사용성 시험, 봉인 우회·권한 변경·새 역할 예약의 실행 시험은 수행하지 않았다. [검토 본문 §7](README.md#7-구현-시-필요한-수용-시험--이번에-실행한-시험이-아님)은 앞으로 구현할 때의 시험 제안이다.

기준 소스·기록과 실제 읽은 외부 자료에 근거해 설계를 평가한 문서다. 미확인을 ‘문제 없음’이나 ‘효과 없음’으로 바꾸지 않으며, 사용자 요구를 되돌리는 새 운영 규칙을 이번 PR에서 확정하지 않는다.
