# 근거·읽은 범위·재현 기록

2026-10-04 클라우드 컨테이너에서 공개 소스를 고정 commit으로 읽었다. 사용자 PC·공식 모델 CLI·로그인/구독 상태는 이번에 확인하지 않았다. 외부 서버를 띄우거나 모델을 추가 호출하지 않았다. 이 문서의 ID는 연구 로컬 ID이며 아키텍처 출처 원장의 새 항목이 아니다.

## 고정한 판과 라이선스

| 프로젝트 | commit | 루트 라이선스 |
|---|---|---|
| anchormind | `cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb` | [Apache-2.0](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/LICENSE) |
| hermes-agent | `55bea1ddf1754dcacb87f13185df1eb1273c0a6e` | [MIT](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/LICENSE) |
| codex-peek | `1baf5ccd360b50da57911401aeca1388e1b0c05e` | [MIT](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/LICENSE) |
| worktrail | `3fb48f980133fd2fb458362648c7bb04cfdbea2b` | [FSL-1.1-ALv2](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/LICENSE) |

AnchorMind의 이전 [v6.0.0 검토](../../reviews/2026-10-04-anchormind/README.md)는 `bf7a9c57f06586ebf61ec56751a9b7d40b08f202` 기준이다. 이번은 v6.1.0의 별도 스냅샷이며, 두 판 전체의 변경 내역 감사를 했다는 뜻은 아니다. 프로젝트의 최초 개발일/연속 개발 기간은 조사하지 않았으므로 오래 개발됐다는 평판을 검증 사실로 기록하지 않는다.

## 파일·모듈 목록의 읽는 법

- [anchormind-inventory.tsv](anchormind-inventory.tsv)는 `git ls-files -z`의 모든 추적 경로를 누락 없이 한 번씩 싣는다. 경로 중심 subsystem은 탐색 분류이며 런타임 아키텍처의 완전한 의존성 모델이 아니다.
- `inventory-only`: 경로만 분류. `interface-inventory`: 주로 헤더와 함수 목록 확인. `selected-source`: 아래 표시한 범위의 소스 검토. `whole`인 파일만 전체 내용을 읽었다는 뜻이다.
- [anchormind-modules.json](anchormind-modules.json)은 `lib/` JavaScript 파일의 줄 수·import·이름 있는 export를 정규식으로 추출했다. 주석의 참조가 섞이거나 동적 import/re-export를 놓칠 수 있으며 AST 분석이나 실행 의존성 추적이 아니다.
- [source-map.json](source-map.json)은 읽은 경로와 범위, SHA 고정 링크를 담는다. 문서의 주요 주장은 아래 묶음 ID로 연결한다.
- tests 디렉터리 파일을 목록에 넣었어도 upstream 전체 테스트를 실행한 것은 아니다. 종속 패키지의 구현·모델 가중치·전체 인증 경로도 전수 감사하지 않았다.

## 이번 순수 함수 시험

```bash
node docs/research/component-comparison-2026-10-04/probes.mjs /path/to/anchormind
```

[probes.mjs](probes.mjs)는 고정 SHA와 clean checkout을 먼저 확인한다. 별도 설치 없이 읽은 순수 모듈을 import한다. 출력은 [probe-results.json](probe-results.json)에 저장했다. 관측 runtime은 Node v24.19.0, 12개 probe 모두 pass다. 이 연구 probe는 저장소 CI가 upstream clone을 받아 실행하는 자동 회귀가 아니며 이번 조사에서 직접 실행한 기록이다.

| probe | 확인한 경계 | 확인하지 않은 것 |
|---|---|---|
| P01–P03 | unranked 순서 재현, ID→본문 승격, 채널/최대 점수 보존, hydration 순서 | DB 후보 생성 정확도·검색 품질 |
| P04–P05 | 범위 우선순위, master 조건, workspace+global SQL | 실제 전송 인증·전체 쿼리 접근 제어 |
| P06 | 작성자 recall과 주입 조건 차이, master point clause | 모든 admin/transport 읽기 경로 |
| P07–P08 | policy tier 의미, legacy NULL과 metadata 누락 차이 | 내용의 진실성·오염 방어 효과 |
| P09 | fullwidth 정규화와 같은 규칙 매칭 | 모든 공격·오탐·한국어 표현의 탐지율 |
| P10 | bootstrap 입력·빈 값·고정 seed·차이 산술 | 검색 효과·통계적 표본 적절성 |
| P11–P12 | 행 변경 감지, 재계산한 전체 체인의 자기 일관성 | 독립 신뢰 기준점 없는 전체 재작성 방어 |

이전 조사 probe는 AnswerPack/egress 등 별도 범위를 다뤘다. 이번 결과를 그 부분의 재실행 결과로 합치지 않는다. 제품 코드 변경 없이 연구 파일과 안내 문서만 추가했다. 저장소 정합성 검사와 정확한 PR head의 CI는 PR #159의 검증 절에서 확인한다.

## 우리 코드 기준

현재 동작의 기준 SHA는 `6cfb78c5a91dc26a46d95229c89f6e2bbfb6830c`다.

| 경로 | 이번 확인 범위 | 쓰임 |
|---|---|---|
| [app/memory.py](https://github.com/inlight37-design/decision-model_lab/blob/6cfb78c5a91dc26a46d95229c89f6e2bbfb6830c/app/memory.py) | 전체 | 후보 제한, 질문 lexical/2-gram, 0점 fallback, 검토 우선, hash·크기 상한 |
| [app/controller.py](https://github.com/inlight37-design/decision-model_lab/blob/6cfb78c5a91dc26a46d95229c89f6e2bbfb6830c/app/controller.py#L480-L546) | prepare/general 입력 경로·memory 관련 호출 위치 | 일반 기억 첨부와 격리 prompt 차이, 확인 명세 |
| [app/server.py](https://github.com/inlight37-design/decision-model_lab/blob/6cfb78c5a91dc26a46d95229c89f6e2bbfb6830c/app/server.py) | report/prepare/use_memory endpoint 위치 | 새 UI/API 적용 접점 탐색 |
| [현재 기능 안내](../../FEATURES.md), [참고 지도](../../REFERENCE-MAP.md) | 기존 기록 재사용 | 원장·검토·카드 등 이미 반영된 기능과 제안 구분 |

store/report/static/cross_review는 기존 기능과 파일 역할을 기준으로 제안 접점을 표시했다. 이번에 해당 파일 전체의 재감사를 했다는 의미가 아니다. 날짜 이후 구현이 바뀌면 이 기록을 현재 기능 명세로 쓰지 말고 최신 기능 안내와 소스를 확인한다.

## 고정 원문 위치와 읽은 범위

숫자는 읽은 줄 범위다. `selected policy functions`, `intro and symbol inventory` 등은 그 제한 그대로 해석한다. 여러 줄 범위를 읽은 파일의 링크는 첫 범위를 가리키며 나머지는 옆에 모두 기록한다.

### AM-WRITE

| 파일 | 읽은 범위 |
|---|---|
| [lib/memory/processors/MemoryRememberer.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/processors/MemoryRememberer.js#L1-L335) | 1-335,609-753 |
| [lib/memory/write/WriteGate.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/write/WriteGate.js#L1-L100) | 1-100 |
| [lib/memory/write/RememberPostProcessor.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/write/RememberPostProcessor.js#L121-L247) | 121-247 |

### AM-SEARCH

| 파일 | 읽은 범위 |
|---|---|
| [lib/memory/processors/MemoryRecaller.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/processors/MemoryRecaller.js#L118-L210) | 118-210,275-365 |
| [lib/memory/read/FragmentSearch.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/FragmentSearch.js#L213-L330) | 213-330,442-615 |
| [lib/memory/read/RankFusion.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/RankFusion.js) | whole |
| [lib/memory/read/BudgetSelector.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/BudgetSelector.js#L1-L160) | 1-160 |
| [lib/memory/read/HotCacheValidator.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/HotCacheValidator.js) | whole |

### AM-CONTEXT

| 파일 | 읽은 범위 |
|---|---|
| [lib/memory/read/ContextBuilder.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/ContextBuilder.js#L523-L680) | 523-680 |
| [lib/memory/read/ContextTrust.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/ContextTrust.js) | whole |
| [lib/memory/read/ReviewVisibility.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/ReviewVisibility.js) | whole |
| [lib/memory/provenance.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/provenance.js#L1-L230) | 1-230,255-279 |
| [lib/memory/write/reviewRules.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/write/reviewRules.js) | whole |

### AM-SCOPE

| 파일 | 읽은 범위 |
|---|---|
| [lib/memory/read/WorkspaceScope.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/WorkspaceScope.js) | whole |
| [lib/memory/read/workspace-read-policy.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/workspace-read-policy.js) | selected policy functions |
| [lib/memory/read/WorkspaceReadAuthz.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/WorkspaceReadAuthz.js#L1-L160) | 1-160 |

### AM-LIFECYCLE

| 파일 | 읽은 범위 |
|---|---|
| [lib/memory/consolidate/MemoryConsolidator.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/consolidate/MemoryConsolidator.js#L273-L488) | 273-488 |
| [lib/memory/processors/AutoReflect.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/processors/AutoReflect.js#L1-L165) | 1-165 |
| [lib/memory/link/ReconsolidationEngine.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/link/ReconsolidationEngine.js#L1-L110) | 1-110 |

### AM-RELATIONS

| 파일 | 읽은 범위 |
|---|---|
| [lib/memory/read/HistoryReconstructor.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/HistoryReconstructor.js#L1-L135) | 1-135 |
| [lib/memory/link/ContradictionDetector.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/link/ContradictionDetector.js#L1-L125) | 1-125 |
| [lib/symbolic/ClaimConflictDetector.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/symbolic/ClaimConflictDetector.js#L1-L110) | 1-110 |

### AM-LEARNING

| 파일 | 읽은 범위 |
|---|---|
| [lib/memory/signals/SearchParamAdaptor.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/signals/SearchParamAdaptor.js#L1-L105) | 1-105 |
| [lib/memory/signals/FeedbackSampler.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/signals/FeedbackSampler.js#L1-L110) | 1-110 |
| [lib/memory/embedding/SyntheticQueryGenerator.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/embedding/SyntheticQueryGenerator.js#L1-L105) | 1-105 |
| [lib/memory/embedding/MorphemeTokenizer.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/embedding/MorphemeTokenizer.js#L1-L105) | 1-105 |

### AM-EVAL

| 파일 | 읽은 범위 |
|---|---|
| [lib/memory/signals/RecallMetrics.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/signals/RecallMetrics.js#L1-L110) | 1-110 |
| [lib/memory/signals/PairedBootstrap.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/signals/PairedBootstrap.js) | whole |

### AM-ASYNC

| 파일 | 읽은 범위 |
|---|---|
| [lib/outbox/OutboxStore.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/outbox/OutboxStore.js#L1-L140) | 1-140 |
| [lib/outbox/OutboxWorker.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/outbox/OutboxWorker.js#L1-L100) | 1-100 |
| [lib/hooks/hook-contract.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/hooks/hook-contract.js#L1-L90) | 1-90 |
| [lib/hooks/hook-reflect-consumer.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/hooks/hook-reflect-consumer.js#L1-L100) | 1-100 |

### AM-TRANSFER

| 파일 | 읽은 범위 |
|---|---|
| [lib/memory/transfer/FragmentExporter.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/transfer/FragmentExporter.js#L1-L110) | 1-110 |
| [lib/memory/transfer/ImportRunner.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/transfer/ImportRunner.js#L1-L140) | 1-140 |

### AM-EGRESS

| 파일 | 읽은 범위 |
|---|---|
| [lib/llm/EgressPolicy.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/llm/EgressPolicy.js#L1-L110) | 1-110 |
| [lib/llm/index.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/llm/index.js#L162-L265) | 162-265 |

### AM-OPS

| 파일 | 읽은 범위 |
|---|---|
| [lib/admin/admin-memory.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/admin/admin-memory.js) | intro and symbol inventory |
| [lib/admin/ReviewStore.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/admin/ReviewStore.js) | intro and symbol inventory |
| [lib/admin/admin-auth.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/admin/admin-auth.js) | intro and symbol inventory |
| [lib/cli/init.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/cli/init.js) | intro and symbol inventory |
| [lib/cli/_fileTransaction.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/cli/_fileTransaction.js) | intro and symbol inventory |
| [assets/admin/modules/memory.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/assets/admin/modules/memory.js) | intro and symbol inventory |
| [assets/admin/modules/graph.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/assets/admin/modules/graph.js) | intro and symbol inventory |
| [assets/admin/modules/metrics.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/assets/admin/modules/metrics.js) | intro and symbol inventory |
| [lib/scheduler-registry.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/scheduler-registry.js) | intro and symbol inventory |
| [lib/logging/audit-chain.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/logging/audit-chain.js) | whole |

### AM-CONFIG

| 파일 | 읽은 범위 |
|---|---|
| [lib/config.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/config.js) | selected feature flag definitions |
| [config/memory.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/config/memory.js#L166-L195) | 166-195,350-370,400-420 |
| [package.json](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/package.json) | whole |
| [lib/memory/memory-schema.sql](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/memory-schema.sql#L1-L130) | 1-130 |

### HM-MEMORY

| 파일 | 읽은 범위 |
|---|---|
| [tools/memory_tool.py](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/tools/memory_tool.py#L1-L115) | 1-115 |

### HM-SEARCH

| 파일 | 읽은 범위 |
|---|---|
| [tools/session_search_tool.py](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/tools/session_search_tool.py#L1-L95) | 1-95 |

### HM-SKILLS

| 파일 | 읽은 범위 |
|---|---|
| [tools/skills_tool.py](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/tools/skills_tool.py#L248-L277) | 248-277,550-600 |
| [agent/curator.py](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/agent/curator.py#L200-L262) | 200-262 |

### PK-RETRIEVAL

| 파일 | 읽은 범위 |
|---|---|
| [bridge/map-retrieval.js](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/bridge/map-retrieval.js#L1-L150) | 1-150 |
| [bridge/map-provenance.js](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/bridge/map-provenance.js#L1-L100) | 1-100 |

### PK-FRESHNESS

| 파일 | 읽은 범위 |
|---|---|
| [bridge/map-freshness.js](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/bridge/map-freshness.js#L1-L75) | 1-75 |
| [bridge/map-reader.js](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/bridge/map-reader.js#L1-L50) | 1-50 |

### PK-VERIFY

| 파일 | 읽은 범위 |
|---|---|
| [bridge/verify-guard.js](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/bridge/verify-guard.js#L1-L120) | 1-120 |

### WT-RECORD

| 파일 | 읽은 범위 |
|---|---|
| [casebook/core/worktrail.py](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/worktrail.py#L1-L150) | 1-150 |
| [casebook/core/recording.py](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/recording.py#L1-L115) | 1-115 |

### WT-SEARCH

| 파일 | 읽은 범위 |
|---|---|
| [casebook/core/search.py](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/search.py) | whole |
| [casebook/core/prior.py](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/prior.py#L1-L110) | 1-110 |

### WT-STATE

| 파일 | 읽은 범위 |
|---|---|
| [casebook/core/state.py](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/state.py#L1-L130) | 1-130 |
| [casebook/core/threads.py](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/threads.py) | symbol inventory |

## 후속 실험이 필요한 경계

전체 설치·연결을 고를 때는 PostgreSQL/Redis 경쟁·복구, worker 재시도, 기본값과 실제 설정 차이, UI 동작, 클라이언트 훅 호환성, 모델 호출 원장/종료를 별도 관측한다. 검색 개선을 고를 때는 D05 정답셋과 실제 사용 피드백이 필요하다. 이 목록은 지금 연구를 미완료로 남기는 승인 대기가 아니라, 이후 구현 선택의 검증 범위를 보존한 것이다.
