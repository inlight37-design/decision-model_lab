# 비공개 제품의 편의 흐름과 연구형 후보

여기의 근거는 **공식 문서 또는 업체의 보고**다. 제품을 로그인해 사용하거나 내부 코드를 해체한 결과가 아니다. URL·조회일·본문 hash는 [public-source-manifest](public-source-manifest.json)에 보존한다. 문서에 공개되지 않은 큐·DB·재시도·보안 구현을 추측해 기능으로 세지 않는다.

## 1. Conductor — 작업 공간에서 검토 가능한 변경으로

읽은 원문: [workflow](https://www.conductor.build/docs/concepts/workflow), [cloud workspaces](https://www.conductor.build/docs/cloud/working-with-cloud-workspaces), [diff viewer](https://www.conductor.build/docs/reference/diff-viewer).

**흐름:** 독립적으로 검토·병합할 작업 → workspace/branch → agent/terminal/app → diff의 줄별 피드백 → checks/PR → merge → archive/history. 문서가 강조하는 단위는 worker 수가 아니라 **같이 검토하고 병합할 변경의 단위**다. 같은 branch와 코드 상태를 공유해야 하는 일과 독립 workspace로 나눌 일을 구분한다.

Diff Viewer의 unified view, commit filter, 특정 파일 바로 열기, 줄별 코멘트를 composer 첨부로 보내기는 단독으로 참고할 수 있는 편의다. 우리 답변·검토도 `source_hash + locator`에 결속한 부분 피드백을 제공할 수 있다. GitHub review thread resolved와 현재 코드가 지적을 해결했다는 판정은 따로 표시한다.

cloud 문서는 workspace 상태/CPU/메모리, SSH, 로컬 sync, 포트 전달을 한 곳에서 보여준다. **sync는 cloud→Mac 단방향이며 로컬 변경이 되돌아가지 않고 덮어써질 수 있다.** 또 파일·chat history와 실행 중 프로세스의 수명이 다르다. 조회 당시 문서는 비활동 4시간 sleep과 최대 23시간 50분 sandbox 수명을 설명한다. 앱을 다시 열었다고 중단된 프로세스가 복구된다는 뜻이 아니다.

우리 OP02/OP12에 이 차이를 반영한다: `workspace available`, `execution alive`, `cached view`, `artifact saved`를 독립 표시. 원격 터미널/포트 제공은 서비스 운영이 필요한 큰 기능이고, 상태와 링크 모음은 작은 기능이다. worktree 자체가 OS 보안 sandbox인 것도 아니다.

## 2. Kiro — 명세와 작업 간 추적

읽은 원문: [specs](https://kiro.dev/docs/specs/). 요구사항 → 설계 → 작업 목록이 연결되는 흐름, feature/bugfix/Quick Spec 구분, 의존성을 고려한 작업 진행, 플랫폼별 기능 차이를 확인했다.

재사용할 단위는 고정 문서 세 개를 강제로 만드는 절차보다 **요구 ID→설계 결정→작업→완료 증거**다. 간단한 수정은 한 카드에서 끝나고 큰 작업은 단계별 문서를 펼치는 방식이 적합하다. 사용자에게 매 단계 새 승인을 받는 정책은 이번 요청과 맞지 않으므로 가져오지 않는다. Quick Spec처럼 작업 크기에 맞게 형식을 줄일 수 있게 한다. OP05는 모델이 작성한 계획과 사용자 확정 제약도 구별한다.

## 3. Cursor — 여러 후보와 한곳의 검토

읽은 원문: [2.0 changelog](https://cursor.com/changelog/2-0), 2025-10-29 발표 내용. 이는 2026-10-04 전체 최신 기능의 전수 목록이 아니다.

문서에는 단일 prompt에 여러 agent, worktree/remote machine 기반 사본, agents/plans sidebar, 여러 파일 변경의 통합 검토, plan/build 모델 분리, background 실행, inline context pills, voice input, 공유 team commands가 나온다. 재사용 후보는 다음과 같다.

- **계획과 실행을 따로 보기:** 비싼 모델의 계획을 다른 실행 모델로 이어가되 입력·모델·설정 버전을 고정한다. 현재 상위/일반 역할 기반과 연결한다.
- **답 후보 병렬 비교:** 모델/지연/완료 상태를 열로 보여주고 근거와 검토를 옆에서 펼친다. 먼저 도착한 답을 자동 정답으로 고르지 않는다.
- **자료 pill과 복사 보존:** 어떤 파일·기억·규칙이 붙었는지 보이고 복사/재실행에서도 참조가 유지되게 한다.
- **음성 입력·키보드 명령:** 편의 후보로 보관하되 음성 인식 서비스·브라우저 권한·비용은 별도 선택이다.

macOS sandbox 설명이나 “4x faster”, cloud reliability 홍보 수치를 우리 환경의 검증으로 사용하지 않는다. 문서의 플랫폼·발표 시점과 적용 범위를 그대로 남긴다.

## 4. Devin — 조정자 아래 작은 세션의 가시성

읽은 원문: [Devin can now manage Devins](https://cognition.com/blog/devin-can-now-manage-devins). 조정자가 하위 세션을 만들고 각 세션 링크/VM/사용량을 보며 직접 메시지를 보내거나 pause/sleep/terminate하는 흐름이 소개된다. 긴 작업을 trajectory로 살피고 다시 나누는 효과는 업체 설명이며 품질을 재측정하지 않았다.

우리 역할판에도 개별 실행을 열고 질문·막힘·사용량·종료 원인을 보는 흐름이 유용하다. 그러나 하위 세션의 별도 VM과 예산은 우리 thread 하나와 같지 않다. OP12는 parent/child와 호출 cap을 함께 보여주고, OP07은 전달 대기 메시지를 분리한다. 무제한 spawn이나 자동 재귀 분업은 제안하지 않는다. 현재 task에는 실제 sub-agent를 사용하지 않았다.

## 5. Copilot cloud agent와 Jules — 작업에서 산출물까지

읽은 원문: [Copilot cloud agent](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent), [Jules getting started](https://jules.google/docs/).

| 비교축 | Copilot 공식 문서 | Jules 시작 문서 | 우리 후보 |
|---|---|---|---|
| 시작 | repo 연구/계획/branch 변경, 필요할 때 PR; 진입점마다 기능 차이 | repo/branch/prompt, VM clone·의존성 setup | 작업 카드에서 실행 설정으로 이동 |
| 계획 | GitHub.com에서 PR 전 연구·반복 가능 | “Give me a plan”, 코드 변경 전 검토·승인 흐름 | OP05, 사용자 기존 승인 범위를 존중 |
| 실행 공간 | GitHub Actions 기반 ephemeral 환경 | 자체 VM | PC/클라우드/관측 기기를 표시 |
| 결과 | branch diff 반복→PR; 한 task 한 branch/PR 제약 | 완료·입력 필요 notification 안내 | OP11, 원장→산출물→검토 링크 |
| 지침 | instructions/MCP/custom agents/hooks/skills | root AGENTS.md 탐색 안내 | 규칙/도구 provenance와 실제 적용 버전 |
| 운영·비용 | Actions minutes+AI credits, 조회 문서상 session 최대 59분 | 시작 페이지에는 상세 비용·실패 계약 없음 | 별도 계약 확인 없이 구독 무료로 계산하지 않음 |

Copilot의 최신 문서는 “항상 즉시 draft PR부터 생성”만 가능한 제품으로 설명하지 않는다. GitHub.com의 research/plan/edit 흐름과 다른 integration의 즉시 PR 흐름을 구별한다. Jules의 오류·예약·API 링크는 발견했지만 이번에는 세부 문서 전체를 읽지 않았으므로 재시도 보증이나 최신 한도까지 확인한 것으로 쓰지 않는다.

편의 패턴은 **다음에 할 행동이 연결된 상태**다. “끝남”만 표시하지 않고 결과 열기/검토 필요/질문 답하기/실패 원인 보기를 나눈다. 새 알림 채널 연결과 실제 메시지 전송은 별도 기능이다. 이번에는 서비스에 일을 맡기거나 외부로 메시지를 보내지 않았다.

## 6. Amp — 원격 조작과 압축 중심 thread

읽은 원문: [Amp, Rebuilt](https://ampcode.com/news/neo), 본문 주요 Remote Control/Context/Plugins 절. 새 CLI architecture의 remote control은 web에서 live update, 메시지 queue/dequeue, 현재 작업 cancel을 제공한다고 설명한다. thread 문맥이 차면 summary로 새 window를 시작하며 본문은 90% 기준을 제시한다. 이 비율을 우리 모델 공통값으로 복사하지 않는다.

plugin API는 lifecycle/tool event, tools, command palette, 선택/입력 UI, AI classification 등 서로 다른 비용의 기능을 함께 제공한다. 모든 plugin event를 모델 호출로 구현해야 하는 것은 아니다. `ask_user_choice`가 나중에 built-in으로 옮겨졌다는 본문 갱신도 있어, 중복 확장을 계속 유지하기보다 capability를 보고 대체하는 편의를 참고할 수 있다.

OP07의 대기 메시지와 OP08의 압축 미리보기, OP03의 명령 palette, 이전 D07의 템플릿 서랍으로 나눠 보관한다. 원격 조작 자체의 인증·권한 구현과 실제 압축 품질은 이번 공개 글만으로 확인할 수 없다.

## 7. Jev와 Fusion — 사용 조건을 가진 실험 후보

읽은 원문: [TypeSafe Jev compaction](https://docs.litellm.ai/blog/typesafe-jev-compaction), [Fusion benchmark](https://docs.litellm.ai/blog/fusion-terminal-bench-benchmark). 두 글의 모델명·결과는 원문 업체 보고이며 이번 조사에서 존재·성능을 독립 실측한 값이 아니다.

**Jev:** 과거 tool result가 최신 질문에 필요한지 별도 모델로 점수화하고 낮은 항목을 삭제 안내로 바꾼다. 문서는 tool call/ID 구조, system/user, 마지막 assistant exchange 보호를 설명한다. 기본 0.2 threshold, 200자 minimum, unavailable 때 original request를 보내는 fail-open은 그 문서의 설정이다. 삭제할 때마다 원문을 잃는 기억 DB 정책과는 다르다.

우리 적용은 먼저 오프라인 평가다: 필요한 반례·출처·제약이 사라졌는지, call/result 쌍이 맞는지, 답변 품질·지연·총 호출비용이 어떻게 바뀌는지 비교한다. Jev 자신의 비용과 외부로 전달되는 system/latest user/tool exchanges를 포함해야 한다. native subscription CLI 밖의 TypeSafe/LiteLLM API를 기본 경로로 붙이지 않는다.

**Fusion:** 여러 모델의 후보를 합성하는 방식이다. 글은 같은 Terminal-Bench subset에서 단독 9/21, Fusion 14/21, 총비용 증가와 지연 증가, 단독만 해결한 한 작업의 timeout 회귀를 함께 보고한다. 한 번씩 실행한 작은 subset이므로 전체 벤치마크·일반 신뢰성·우리 작업의 향상으로 확대하지 않는다. 후보보다 synthesizer가 비용 대부분을 차지한다는 관측은 우리 합성 비용을 따로 기록할 이유다.

우리에는 독립 초안·공개 후 교차검토·합성이 이미 있다. 새 “Fusion 모드” 이름을 붙이기보다 단독/독립 비교/합성의 paired task 평가와 회귀표를 먼저 만든다. 정답수뿐 아니라 timeout, unknown, 전체 호출 수, 재시도, 지연, synthesizer 비용까지 함께 본다. 이것은 OP08/OP09의 검증 설계와 이전 D05 평가 fixture를 공유할 수 있다.

## 남은 자료의 경계

AnchorMind·Hermes·Peek·WorkTrail은 [이전 부품 분석](../component-comparison-2026-10-04/README.md), 기존 논문·모델 비교는 [v0.4 출처](../../architecture/v0.4/sources.json)와 [9월 추가 조사](../../research-2026-09-22/README.md)가 기준이다. ai_unslop/island-ui는 현재 적용 중인 [부품 README](../../../app/static/island-ui/README.md)를 따른다. 이번 조사에서 그 논문 전체나 디자인 원본을 새로 해체했다고 세지 않는다. 이후 특정 후보를 구현할 때, 이 기록의 미검토 helper/테스트/실제 제품 흐름을 좁혀 검증하면 된다.
