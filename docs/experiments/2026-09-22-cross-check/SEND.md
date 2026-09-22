독립 검토를 부탁드립니다. 제가 원하는 것은 동의가 아니라 서로 다른 관점, 그리고 제가 놓쳤을 반례입니다.

원문을 직접 조사하셔도 됩니다.

## 배경

공개 저장소: https://github.com/inlight37-design/decision-model_lab

연구·설계 저장소이며 아직 동작하는 orchestrator가 없습니다. 읽으신다면 `docs/architecture/v0.4/README.md` → `02-frontier-architecture.md` → `03-evaluation-and-roadmap.md` 순서를 권합니다.

**목표:** OpenAI Codex / Claude Code / Google Antigravity(`agy`) 세 제품의 native 하네스를 **사용자 본인의 구독으로** 구동하는 데스크톱 앱을 만듭니다. 단순 병렬 실행기가 아니라, 각 모델의 독립 답변을 받아 주장·근거 단위로 대조하고 미해결 반례를 최종 결과에 남기는 구조입니다.

**이미 확정된 제약** — 바꾸자는 제안이 아니라 전제입니다:

- 구독 우선. 유료 API·추가 크레딧으로의 **조용한 전환 금지**, 명시적 opt-in만 허용
- 초기 답변은 blind. 전원 제출 전에는 서로의 답을 볼 수 없음
- 합의는 검증이 아님. 투표·자기확신으로 주장을 `verified`로 승격하지 않음
- 미해결 반례·소수 의견을 최종 보고서에 보존
- 상태·권한·예산·종료의 소유자는 **하나**
- 논의자는 read-only, 구현자는 writer 하나

**현재 있는 것:** 문서 약 340KB, 실행 코드 약 33KB(오프라인 검사기 4개), 테스트 74개, 근거 원장 55건. **실제 모델 연결은 0건.**

**유지보수자는 1인입니다.** 이 조건을 판단에 반영해주세요.

## 확인된 사실

2026-09-22 GitHub API와 공식 문서로 확인한 것입니다. **순위가 아니라 목록입니다.**

| 항목 | 확인된 내용 |
|---|---|
| Orca (stablyai) | MIT, TypeScript, 75,150 stars, 활발. 에이전트별 git worktree 격리, 헤드리스 모드, "자기 구독으로 실행" |
| AionUi (iOfficeAI) | Apache-2.0, TypeScript, 33,036 stars, 활발. 설치된 CLI 자동 탐지, 로컬 SQLite, topics에 `acp` |
| ACP (Agent Client Protocol) | Zed 발. JSON-RPC 2.0 over stdio, 에디터↔에이전트 표준. JetBrains·Google·GitHub 등 채택 |
| Paseo | AGPL-3.0. worktree, 데몬, 모바일 |
| Superset | Elastic License 2.0 (비 OSS) |
| 제약 | ACP는 전송 규격이며 quota·과금·entitlement 정보를 포함하지 않음 |

## 질문

각 질문에 **권고 + 그 권고가 틀릴 조건**을 함께 주세요.

### 1. 기존 오픈소스를 어디까지 의존할 것인가

Orca는 MIT라 법적 제약이 없고 worktree 격리와 어댑터 배선이 이미 되어 있습니다. 그 위에 얹을 것인가, 패턴만 참고하고 직접 쓸 것인가? 판단 근거는 무엇입니까?

"상태·권한·예산의 단일 소유자" 제약과 외부 스케줄러가 충돌하는지도 봐주세요.

### 2. 언어와 런타임 경계

기존 검사기·계약은 Python입니다. 생태계(Orca·AionUi·ACP SDK)는 TypeScript입니다. 단일 언어로 갈지, 나눌지, 나눈다면 경계를 어디에 둘지.

### 3. 첫 화면이 무엇을 보여줘야 하는가

이 앱의 정체성이 여기서 갈립니다. 사용자가 처음 열었을 때 무엇이 보여야 이 도구가 기존 병렬 실행기들과 **다른 물건**이 됩니까?

### 4. 이 접근의 가장 큰 설계 결함은 무엇입니까

위 제약이나 전체 방향에서 실패할 지점을 찾아주세요. 예를 들어 구독 기반 비대화형 접근이 계속 허용된다는 전제, 서로 다른 회사의 모델이 통계적으로 독립인 오류를 낸다는 가정, 합성 단계에서 맞던 답이 사라지는 문제 등. 무엇이든 좋습니다.

**동의하는 답보다 반례가 유용합니다.**

## 출력 형식

```
answer            결론 요약
claims            주장 목록. 각각 factual / derived / value_judgment 로 분류
assumptions       당신이 전제한 것
evidence_refs     근거. 원문을 읽었으면 어느 부분인지, 못 읽었으면 그렇다고 표시
counterexamples   당신 자신의 결론에 대한 반례
unknowns          확인하지 못해 모르는 것
checks_proposed   이 판단을 검증할 방법
```

읽지 않은 문서를 읽은 것처럼 쓰지 마세요. 확인하지 못한 수치는 모른다고 적어주세요. 검색 결과 요약과 원문 확인을 구분해주세요.
