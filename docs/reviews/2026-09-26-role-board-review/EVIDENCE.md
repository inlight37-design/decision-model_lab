# 역할판 검토 — 근거 대조

2026-09-26 · 검토 내부 근거이며 sources.json의 새 항목이 아니다. 이 파일은 검토 진행 중이며 후속 커밋에서 대조표를 완성한다.

기준 코드는 `9526bbe382b68c74bd7d784c09af3e02f55393ca`. **코드를 직접 읽었다는 것은 사용자 PC에서 실행했다는 뜻이 아니다.** 외부 문서는 이날 직접 열었고, 논문은 아래에 전문/해당 절/초록을 구분한다. 모든 수치는 저자·공급자의 보고이며 이번 세션의 재현 결과가 아니다.

## A. 저장소 직접 대조

| ID | 위치·관측 | 요청 연결·정정 |
|---|---|---|
| C1 | `core/contract.py:59–91`, `template`는 --model 값을 가리지만 그 밖의 실행 옵션과 ro/rw 연결을 revision에 포함한다 | P4·G1 / 질문4: 모델 이름이 이미 가려진다는 사실은 맞다. 추론 강도의 모든 값이 동등한 권한·문맥 경계를 가진다는 증거는 아니다 |
| C2 | `core/adapters.py:201–275`, Claude·Codex는 effort가 None이 아니면 거절한다. Codex -c는 허용한 정확한 설정 조각만 받는다 | P4·G1 / 질문4·8: 공식 옵션을 알아도 실제 연결·검사·관측이 필요하다 |
| C3 | `app/live_config.py:10–49`, provider 설정 하나에 model 하나, 서로 다른 provider 1–2개. `app/cli_executor.py:128–165`는 그 model을 최종 계획에 넣는다 | W1–W5 / P4·P10 / 질문1·8: 역할별 모델 선택은 화면의 드롭다운만으로 완료되지 않는다. provider의 공유 한도와 역할 인스턴스의 모델 설정을 구별해야 한다 |
| C4 | `app/controller.py:466–526`은 work_root/run_id/pid를 만든다. 반면 실제 CLI의 HOME은 `app/cli_executor.py:88,151`의 self.home이고, `core/isolation.py:188–221`이 같은 HOME 경로를 빈 상자에 재구성한다 | G1 / P7 / 질문5·7: 작업 폴더가 참여자마다 다른 것은 맞지만, 실제 CLI HOME이 작업 폴더 옆 -home이라는 설명은 틀리다. 모의 실행과 혼동하지 않는다 |
| C5 | `app/codex_account.py:27,116–138`의 모델 없는 model/list 조회는 이미 있다. 현재 투영은 모델 ID 목록이다 | W1 / P4 / G4 / 질문4·8: 공식 supportedReasoningEfforts/defaultReasoningEffort를 호환성 확인 후 허용 목록으로 투영할 후보가 있다. 계정에서 실제 받았는지는 이번에 관측하지 않았다 |
| C6 | strict ledger-summary의 Codex 12524/9984/0, Claude 2/753/5728; L1 analysis T1의 Codex 12597/9984/0, Claude 2/2021/4587 | G2 / 질문5·7: 요청서의 해당 전사 수치와 일치한다. 캐시 토큰 수만으로 어느 문서가 캐시됐는지, 새 질문 전체가 캐시되지 않았는지는 확정할 수 없다 |

고정 코드 링크: [contract](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/core/contract.py), [adapters](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/core/adapters.py), [live_config](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/app/live_config.py), [cli_executor](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/app/cli_executor.py), [isolation](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/core/isolation.py), [controller](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/app/controller.py), [account](https://github.com/inlight37-design/decision-model_lab/blob/9526bbe382b68c74bd7d784c09af3e02f55393ca/app/codex_account.py).

기록 링크: [strict](../2026-09-25-strict-live-run/ledger-summary.json), [L1](../../experiments/2026-09-25-l1/analysis.json). 같은 캐시 크기가 반복된다는 관측과 특정 prefix가 원인이라는 해석을 분리한다.

## B. 공식 문서 직접 확인

| ID | 원문·확인 위치 | 확인 결과·한계 |
|---|---|---|
| O1 | [Codex App Server](https://learn.chatgpt.com/docs/app-server), model/list | 모델별 supportedReasoningEfforts·defaultReasoningEffort, nextCursor를 제공하는 문서가 있다. 모델·강도·기본값은 계정·클라이언트에 따라 달라진다. 현재 WSL 설치판의 반환 형태는 미관측 |
| O2 | [Codex config reference](https://learn.chatgpt.com/docs/config-file/config-reference), model_reasoning_effort | Codex 추론 설정은 존재한다. 저장된 도움말에 독립된 추론 플래그가 없다는 사실만으로 기능 부재를 추론하면 안 된다. 우리 adapter의 -c 허용 목록·계획 판·관측은 별도로 바뀌어야 한다 |
| O3 | [Codex pricing](https://learn.chatgpt.com/docs/pricing), credit prices 표 앞 주의문 | 공식 문서는 크레딧 가격만으로 구독 포함 사용량이 결정되지 않는다고 명시한다. 캐시 입력의 크레딧 할인율을 ChatGPT 포함 한도의 같은 할인율로 단정할 수 없다 |
| O4 | [Claude Code prompt caching](https://code.claude.com/docs/en/prompt-caching), prefix·directory·effort·TTL·fork | prefix의 정확 일치, 경로·도구·환경 등의 영향은 문서로 확인했다. 같은 경로만 맞추면 충분하다는 뜻이 아니다. 추론별 캐시 구분에는 모델별 예외가 있다. fork의 캐시 이점은 부모 문맥 상속을 포함하므로 격리 초안에 적용하지 않는다 |
| O5 | [Claude Code model configuration](https://code.claude.com/docs/en/model-config), Adjust effort level·Organization effort limits | 지원하지 않는 강도의 하향 적용 및 stream-json에서 조직 제한의 조용한 적용을 명시한다. 요청값과 실제 적용값을 나눠야 한다. 특히 --effort ultracode는 xhigh만 뜻하는 것이 아니라 내부 workflow orchestration도 켜는 설정이다. low/medium/high/xhigh/max와 동등한 실행 틀로 자동 승인하면 안 된다. 이 웹 문서의 기능을 사용자 CLI에서 시험하지 않았다 |

## C. 논문 직접 대조 — 우선 확인한 정정

| ID | 원문·읽은 범위 | 결과·우리에게 적용할 한계 |
|---|---|---|
| R1 | [S2-MAD v1 전문](https://arxiv.org/html/2502.04790v1), 초록·방법·실험 | 최대 94.5%는 저자 보고와 맞는다. 답 동일성 검사는 정답 형식·정규식 등에 의존한다. 자유 형식 설계 검토에서 비슷하게 말하는 참여자를 자동 제외해도 반례가 보존된다는 근거는 아니다 |
| R2 | [Single-agent or Multi-agent? v1 전문](https://arxiv.org/html/2505.18286v1), 초록·서론·결론 | 서론·결론에 최대 88.1%가 실제로 있다. 반면 초록은 최대 20%라 원문 내부 표기가 다르다. 요청서의 88.1%를 지어낸 수치로 판정하지 않으며, 비교 기준·실험 조건을 붙이지 않은 일반 기대치로도 쓰지 않는다 |
| R3 | [Agentic Plan Caching v2 전문](https://arxiv.org/html/2506.14852v2), §4.2 | 50.31%는 평균 비용 절감, 96.61%는 정확도가 가장 높은 기준선 대비 유지한 성능 비율이다. 절대 정답률 96.61%가 아니다. 계획 재사용용 메모리는 일반 작업 후보이지 독립 초안 입력이 아니다 |
| R4 | [When Single-Agent with Skills Replace Multi-Agent Systems and When They Fail v2 전문](https://arxiv.org/html/2601.04748v2), Table 3·결과 | 평균 토큰 53.7%와 정확도 차이 +0.7은 표에 있다. 정확도는 백분율 점수 차이의 평균으로 약 +0.7%p이고 GSM8K는 -2%p다. 제목의 실패 조건과 과제별 저하를 함께 남긴다 |
| R5 | [Rethinking the Evaluation… v1 전문](https://arxiv.org/html/2609.05933v1), 통제 평가·matched random pruning | 무작위 가지치기는 효율 주장을 평가하는 대조군이다. 실제 사용자가 정한 팀원·반례를 실행 중 무작위로 제거하라는 권고가 아니다. 동일 과제·모델·예산·도구와 품질을 통제한 비교가 필요하다 |

나머지 G5–G7 자료의 확인 수준과 최종 판단은 다음 체크포인트에서 보충한다. 이 시점까지 사용자 PC 모델 CLI 호출과 앱 코드 변경은 없다.
