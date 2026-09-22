# 후속 근거 검토와 반영 후보

기준일: **2026-09-22 (Asia/Seoul)**. 기준 main: `2885bf8187ab0854549c736ce742c2050490f4b7` ([PR #1](https://github.com/inlight37-design/decision-model_lab/pull/1) 병합 결과).

사용자 요청은 나머지 자료와 최신·신뢰할 만한 근거를 더 조사해 병합할 내용을 찾는 것이다. 조회한 원격에는 main과 이미 병합된 기존 docs 브랜치만 있었다. 이번 작업은 새 기능 실행보다 **근거의 정정과 평가 설계 보강**을 대상으로 한다.

지난 [최종 검토](FINAL_REVIEW.md)에서 재열람하지 않은 **27개 출처 기록**의 관련 원문 절을 확인했다. 최근 논문 네 편도 방법·결과·한계를 살펴봤고 세 편을 F22–F24로 등록했다. “원문 확인”은 아래에 적힌 절의 정적 검토이며 전체 논문 재현, 독립 실험 27회, 문헌 전수조사를 뜻하지 않는다. 검색·커뮤니티 글은 발견 경로로만 사용했다.

## 1. 지금 반영할 내용

| 후보 | 판단 근거 | 반영 범위 |
|---|---|---|
| PAL capability 설명 정정 | 고정 코드에서 문서와 다른 추론 설정 및 API/custom provider 경로 확인 | F06과 사례/HANDOFF 수정. native 구독 bridge로 채택하지 않음 |
| 모델별 캐시 회계 | E28 공식 API 문서의 write/read 구분 | 비용 평가 지침에 가격 revision·cache write·전환/만료 비용을 추가 |
| judge 역할 편향 검사 | F22는 합의와 사람 기준 일치가 다름을 보여주는 반례 | 중립 기준선·역할 교환·사람 reference 비교를 실험에 추가 |
| 근거가 있는 리뷰 반론 | F24는 과잉 지적·거짓 합의·범위 밖 수정도 보고 | frozen diff, 코드 근거/미확인 우려 구분, scope와 비용 평가를 보강 |
| 비교 가능한 실험 기록 | F23의 프로토콜 분류와 F15의 자원 제한 실험 | 참여자·교환·합성 규칙 및 보장 자원/hard limit을 각각 기록 |

새 runtime·gateway·모델·과금 경로를 도입하는 변경은 아니다. v0.2 계약과 v0.4 checker의 검증 범위를 확대했다고 주장하지 않는다. 결정 D12/D13/D15/D17의 근거 연결만 보강한다.

## 2. 실제 정정: PAL 문서와 구현

F06은 이제 문서만 확인한 기록이 아니다. commit `7afc7c1cc96e23992c8f105f960132c657883bb1`을 기준으로 다음 경로를 읽었다.

| 위치 | 확인 결과 |
|---|---|
| [consensus 문서](https://github.com/BeehiveInnovations/pal-mcp-server/blob/7afc7c1cc96e23992c8f105f960132c657883bb1/docs/tools/consensus.md) | 시연은 hypothetical이며 thinking mode 선택을 안내 |
| [consensus.py](https://github.com/BeehiveInnovations/pal-mcp-server/blob/7afc7c1cc96e23992c8f105f960132c657883bb1/tools/consensus.py#L298) | schema에서 thinking_mode 제외; `_consult_model`은 `medium`을 전달 |
| [base_tool.py](https://github.com/BeehiveInnovations/pal-mcp-server/blob/7afc7c1cc96e23992c8f105f960132c657883bb1/tools/shared/base_tool.py#L731) | 모델 선택을 ModelProviderRegistry에 위임 |
| [registry.py](https://github.com/BeehiveInnovations/pal-mcp-server/blob/7afc7c1cc96e23992c8f105f960132c657883bb1/providers/registry.py#L83) | API key/provider 또는 custom endpoint 초기화 |

따라서 `consensus`의 inspected path는 `clink`를 이용한 구독 CLI 호출이 아니다. custom endpoint는 로컬일 수도 있어 “반드시 유료”라고도 단정하지 않는다. 원문과 파일을 읽었으며 설치·인증·모델 호출은 하지 않았다. 이 정정으로 문서상 지원을 실제 capability로 잘못 등록하는 위험을 줄인다.

## 3. 최근 논문 네 편의 채택 범위

### F22 — 주관적 채점의 역할 편향, 2026-08-31

[Beyond Consensus v1](https://arxiv.org/html/2608.30373v1)의 방법, Tables 1–3, limitations를 확인했다. 한국어 글 평가 600개와 SummEval 700개, 여섯 judge 모델에서 strict/lenient 조합의 평균 사람 기준 일치가 단독보다 나빴다. 중립 대칭 역할과 역할 교환 비교가 있어 단순 합의율보다 유용한 반례다.

두 주관적 과제·한 역할 쌍·네 번의 조정 round라는 한계가 있다. 모든 코드 비판이나 다중 모델을 금지할 근거는 아니다. 후속 교환에서 점수를 가리는 실험을 초기 독립 초안 보존과 혼동하지 않는다. 우리 채택은 중립 기준선 및 역할 편향 검사를 추가하는 것이다.

### F23 — debate 프로토콜 분류, 2026-07-28

[141개 연구의 survey v1](https://arxiv.org/html/2607.26212v1)은 참여자, 상호작용, 합의 규칙을 구분한다. 방법·taxonomy·validity 절을 확인했다. 여기서 가져오는 것은 재현 가능한 manifest의 기록 항목이다. 가장 좋은 모델 조합이나 구조를 입증한 비교 실험으로 인용하지 않는다. 좁은 Scopus 출발 검색, citation 확장, 자연어 과제 범위라는 제약도 유지한다.

### F24 — 근거 중심 코드 리뷰, 2026-08-16

[Adversarial Review v1](https://arxiv.org/html/2608.18167v1)은 arXiv 메타데이터상 ICML 2026 **워크숍** 채택작이다. 프로토콜, 실험표, 실패 사례, 비용, Appendix의 변형 구분을 확인했다. SWE-bench Verified 500개에서 75.2% 대 단독 71.6%를 보고하지만 token은 약 4.5배였다. SWE-PRBench의 prompt 보강 결과와 이 SWE-bench 실행은 같은 프로토콜 변형이 아니다.

도입할 부분은 고정 산출물에 대한 코드 근거 확인과 범위 관리다. 수치나 추가 round를 복제하지 않는다. review F1은 LLM이 사람 코멘트와 매칭한 지표이며 모든 결함의 정답표가 아니다. 관찰한 실패로 prompt를 바꾼 효과는 새 hold-out에서 다시 확인해야 한다.

### 채택 보류 — SatCom 다중 모델 연구, 2026-08-13

[Journal of Intelligent Information Systems 논문](https://link.springer.com/article/10.1007/s10844-026-01086-z)의 실험 방법, 세 단계 rubric, 결과, data availability를 읽었다. 213개 분야 질문과 두 judge 비교, 코드 공개는 장점이다. 다만 rubric 단계별로 승자가 달라지고 사실성 penalty는 최종 평가에서 제외됐으며 RAG corpus는 재배포되지 않는다.

**검토자의 판단:** 이 결과를 일반 코드 정확도나 “이종 모델 우월”의 직접 근거로 합치지 않는다. rubric과 데이터 접근성에 민감한 분야별 사례로만 남긴다. 학술지 게재나 최신 날짜만으로 전이 가능성을 높게 평가하지 않는다.

## 4. 남은 27개 출처의 재확인 기록

아래 “유지”는 현재 저장소의 제한된 주장과 해당 절이 부합한다는 뜻이다. 제품 정책은 구현 시점에 다시 확인한다. E 기록은 [v0.3 원장](../v0.3/sources.json), F 기록은 [v0.4 원장](sources.json)에 있다.

| ID / 원문 | 이번 확인 범위 | 판정 |
|---|---|---|
| [E01 Codex auth](https://learn.chatgpt.com/docs/auth) | 로그인 경로·status·API 청구 구분 | 유지. 사용자 entitlement는 미확인 |
| [E04 Claude 구독](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan) | API key 우선 인증 안내 | 유지. key 값이나 사용자 설정은 읽지 않음 |
| [E06 Claude headless](https://code.claude.com/docs/en/headless) | 출력·resume·client cost estimate | 유지. 누계 비용을 turn delta/실청구로 취급 금지 |
| [E07 agy 설치/인증](https://www.antigravity.google/docs/cli/install/) | 계정 및 modelProvider/API key 조건 | 유지. 키 하나로 모든 CLI의 funding을 판정하지 않음 |
| [E09 agy credits](https://www.antigravity.google/docs/cli/credits/) | quota 표시·useG1Credits fallback 설정 | 유지. 안정적 quota API의 증거는 아님 |
| [E10 agy SDK](https://www.antigravity.google/docs/sdk/overview/) | quickstart·Gemini API/Vertex | 유지. 개인 구독 재사용 증거로 쓰지 않음 |
| [E11 Teamwork](https://www.antigravity.google/docs/teamwork/) | 역할·handoff·독립 검증·파일 소유 | 유지. 제품 설명과 성능 실험 구분 |
| [E12 FrugalGPT v1](https://arxiv.org/html/2305.05176v1) | Section 4 / Table 3 비용 분모 | 유지. 2023 API QA 결과이며 현재 CLI 절감률 아님 |
| [E13 RouteLLM v4](https://arxiv.org/html/2406.18665v4) | 사전 라우팅·평가 범위·2배 비용 주장 | 유지. 상태 있는 agent 전체 성공과 구분 |
| [E14 MAST v3](https://arxiv.org/abs/2503.13657v3) | abstract·revision | 유지. abstract만 확인한 범위를 유지 |
| [E15 Scaling v3](https://arxiv.org/html/2512.08296v3) | 260설정·6 benchmark·robustness·Appendix | 유지. 예전 v1 및 제한된 모델 혼합과 구분 |
| [E17 Aider](https://aider.chat/2024/09/26/architect.html) | architect/editor 역할·결과표 | 유지. 당시 제작자 benchmark |
| [E18 Cursor swarm](https://cursor.com/blog/agent-swarm-model-economics) | SQLite·역할별 token/비용 비교 | 유지. 단일 장기 과제의 보고 |
| [E20 Anthropic research](https://www.anthropic.com/engineering/multi-agent-research-system) | 내부 평가·token 비교·신뢰성 | 유지. 15배의 기준은 일반 chat |
| [E23 Symphony](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/SPEC.md) | 고정 SPEC과 README: 상태 소유·DB 없는 복구·신뢰 경계 | 유지. preview 전체를 세 구독 runtime으로 취급하지 않음 |
| [E24 Jev 발표](https://typesafe.ai/blog/introducing-system-one-models-and-jev) | early access·typed output·workflow reference | 보강. 형식 보장과 의미 정답을 구분 |
| [E25 Jev benchmark](https://docs.litellm.ai/blog/jev-auto-router-benchmark) | 80과제×3, expected-tier match와 classifier agreement | 용어 명확화. 서로 다른 두 지표이며 전체 작업 품질 아님 |
| [E26 Jev compaction](https://docs.litellm.ai/blog/typesafe-jev-compaction) | weather/shop 예제·보존·실패 fallback | 유지. toy 사례이고 추가 외부 전송/비용도 고려 |
| [E27 Context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | 식별자 기반 필요한 시점의 조회 | 유지. 실제 문맥 절감과 정확도는 함께 측정 |
| [E28 Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) | 모델별 write/read·TTL·usage·가격 계산 | 보강. 비용 항목을 분리하고 API/구독 경계 유지 |
| [E29 MCP code execution](https://www.anthropic.com/engineering/code-execution-with-mcp) | 도구 발견·예시 150k→2k의 대상 | 유지. 전체 coding task의 98.7% 절감으로 인용 금지 |
| [E30 Cursor Router](https://cursor.com/blog/how-cursor-router-works) | 품질 proxy·실traffic·model switch cache | 유지. 사용자 행동 proxy와 검증된 정답 구분 |
| [E31 LiteLLM capability](https://docs.litellm.ai/blog/auto-router-capability-benchmark) | 25과제·실패 비용·성공 과제 교집합·한계 | 유지. 같은 해결 개수가 동등 품질 증거는 아님 |
| [F06 PAL](https://github.com/BeehiveInnovations/pal-mcp-server/blob/7afc7c1cc96e23992c8f105f960132c657883bb1/tools/consensus.py) | 문서 및 provider resolution/call 코드 | 정정. 상세는 2절 |
| [F09 DMAD](https://proceedings.iclr.cc/paper_files/paper/2025/hash/3de667dab3b3d812583abc0a786139a0-Abstract-Conference.html) | ICLR proceedings abstract | 유지. 풀이 방법 다양성의 제한된 근거 |
| [F14 Managed Agents](https://www.anthropic.com/engineering/managed-agents) | session/harness/sandbox·복구·credential 경계 | 유지. hosted 구조 참고이며 native 구현 완료 아님 |
| [F15 Infrastructure noise](https://www.anthropic.com/engineering/infrastructure-noise) | 자원 보장/상한·인프라 실패와 성공 변화 | 보강. 자원 여유가 해결 가능한 전략도 바꿈 |

## 5. 보류할 도입과 다음 실험

Jev 자동 라우팅, 공격적인 compaction, PAL/Symphony 전체 채택, 무조건적인 3모델 debate는 이번 근거만으로 도입하지 않는다. 기존 V04-01의 실제 capability 확인 후 V04-03의 작은 독립 비교를 수행하는 순서는 유지한다.

첫 실험에는 사전에 고정한 acceptance와 hold-out, 단독/독립 합성/제한 리뷰 비교, 전체 사용량과 사람 수정 시간을 포함한다. API 문서와 논문만으로 사용자의 구독 quota·runtime 안전성·성능 개선을 검증할 수는 없다.

## 6. 이 변경의 검증

Windows Python 3.12 환경에서 `python -m unittest discover -s tests -v`를 실행해 **71개 전부 통과**했다. 이 중 연구 정합성 검사 3개는 출처 ID·ADR 양방향 연결·상대 문서 링크를 확인한다. 추가한 F22–F24에 맞춰 기존 ID 범위 assertion만 갱신했으며 runtime 코드는 변경하지 않았다. 외부 링크 내용의 진실성은 자동 테스트의 검증 대상이 아니다.
