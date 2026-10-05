# 기억·검색·스킬·인계 기능의 선택 이식 검토

검토일: **2026-10-05**. 우리 코드 기준: **`48ab4bd6f0e297587707aecb83ebc0cd9968892f`**. 접근 표면: 클라우드 checkout과 연결된 GitHub 도구. 사용자 PC, 실제 CLI 로그인, 외부 기억 서버, 실제 모델 품질은 이번에 관측하지 않았다. 이 문서는 날짜가 붙은 검토 기록이며 현재 제품 명세를 대체하지 않는다.

## 1. 결론

**현재 자동 기억을 유지하면서 원문을 찾고 필요한 부분을 전달하는 정확도를 먼저 높이는 것이 타당하다.** Hermes·AnchorMind·codex-peek·WorkTrail을 각각 설치하는 것은 현재 문제에 비해 운영 경로와 문맥 권한을 크게 늘린다. 이들에서 가져올 가치가 가장 큰 부분은 다음과 같다.

1. **Hermes:** 검색 결과에서 실제 원문 주변을 제한해서 펼치는 방식, 이름·설명만 먼저 보여 주는 스킬 선택, 세션 시작 때 기억 사본을 고정하는 방식. 고정 사본과 설정 템플릿의 핵심은 이미 있다.
2. **AnchorMind:** 검색 자격과 범위를 먼저 결정하고 순위를 매기는 책임 분리, 채널별 검색 이유, 예산 내 중복 억제, 같은 질의의 전후 평가. 현재 설명·예산·평가 기반을 확장할 수 있으며 외부 기억 서버가 선행 조건은 아니다.
3. **codex-peek:** 현재 소스의 일치 여부와 과거에 실제 사용한 증거를 구별하는 방식, 결정이 나온 이유를 검색하는 작은 색인. 전역 Stop 훅과 별도 proof 원장을 함께 들일 필요는 없다.
4. **WorkTrail:** 관측·해석·따르기로 한 결정·범위가 있는 배제 사유를 구별하는 기록. 작업 복귀 화면과 다음 행동은 이미 있어, 남은 가치는 장기 결정의 교체 관계와 다시 조사할 조건이다.

사용자가 확정한 **일반 팀원·상위 역할의 자동 기억 기본 켬, 격리 팀원 제외**를 전제로 한다. 과거 조사에 있던 수동 기억 우선 제안으로 되돌리지 않는다. 근거는 [현재 결정 27](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/NEXT-SESSION.md#L63)과 [실제 역할별 전달 범위](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/FEATURES.md#L72-L92)다.

이 문서의 **M01–M06은 검토 안의 개선 항목**이다. 기존 H/O/D 후보 ID를 함께 적으며 새로운 출처 원장 번호를 만들지 않았다. 외부 코드를 복사하거나 라이선스의 법적 적합성을 판정하지 않았다.

## 2. 먼저 인정해야 할 현재 구현

10월 4일 기능 목록·부품별 설계는 후보를 찾는 입구로 쓰고, 상태는 기준 SHA의 코드로 다시 판정했다. 다음 기능을 미구현이라고 반복해서 권고하면 중복 개발이 된다.

| 영역 | 기준 SHA에서 직접 확인한 동작 | 아직 같다고 볼 수 없는 것 |
|---|---|---|
| 자동 기억 선택 | 같은 task의 취소되지 않은 공개 실행 전체를 순회한다. 질문·사람 메모·수용 검토 지적·해시가 맞는 원래 답을 비교하며, 단어·한국어 부분 일치와 빈도 가중치, 결정적인 정렬을 쓴다. [memory.py 60–101](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/memory.py#L60-L101) | 의미 검색, 다른 task의 자동 기억, 수정 답 본문을 사용한 후보 순위 |
| 기억 예산·근거 | 후보/선택 상한, 섹션별 발췌, 미해결·조건부 지적 우선, 누락 바이트, 검색 이유, 전체 공개 문맥 해시와 pack 해시가 있다. [memory.py 103–164](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/memory.py#L103-L164), [192–243](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/memory.py#L192-L243) | 모든 반례 보존, 모델의 사실 검증, 토큰 수와 UTF-8 바이트 수의 동일성 |
| 입력 고정·격리 경계 | 일반 팀원의 prompt에 기억 footer를 붙이고 입력 hash를 계산한다. 격리 prompt는 질문·공통 자료로 만들며 기억을 붙이지 않는다. 재시작에도 기록된 입력과 묶음 hash를 확인한다. [inputs.py 165–190](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/context/inputs.py#L165-L190), [194–238](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/context/inputs.py#L194-L238), [272–300](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/context/inputs.py#L272-L300) | 기억 서버·전역 CLI 설정을 연결할 권한, 격리 역할의 자유로운 원장 조회 |
| 공개 검색 | task/kind/limit 필터, 질문·답·수정·검토·판단·합성·자료 메타데이터 검색과 snippet이 있다. 수정 답·재검토도 검색 대상이다. [catalog.py 7–78](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/catalog.py#L7-L78), [public.py 75–92](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L75-L92) | FTS 인덱스, 형태소·의미 검색, 날짜 필터, agent가 자율적으로 펼치는 원문 도구 |
| 기억 출처 조회 | 소비한 pack을 그대로 반환하며 과거 기억을 다시 선택하지 않는다. 출처의 현재 가용성과 당시 선택 근거 존재 여부를 표시한다. [public.py 115–139](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L115-L139) | `source_available`이 오늘의 원문과 당시 원문의 동일성을 증명하는 것 |
| 검색 평가 | 합성 fixture, 관련 기록 라벨, 무관 기록·금지 기록·발췌 누락·바이트 상한을 비교하는 도구가 있다. [evaluate_memory.py 53–99](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/tools/evaluate_memory.py#L53-L99), [검사](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/tests/test_memory_evaluation.py#L9-L40) | 실제 사용자 검색 품질이나 모델 답 품질의 독립 평가 |
| 반복 설정 | 질문·팀·모델·자료 사본·배정·기억 옵션 저장, 불러오기, 현재 모델 결속 확인, hash 검증 export/import, 확인한 hash로 삭제한다. 승인·실행 권한은 복사하지 않는다. [templates.py 15–124](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/templates.py#L15-L124) | 도구가 실행되는 스킬 라이브러리, 스킬의 자동 생성·배포·의존 패키지 설치 |
| 복귀·인계 | 목표·완료 기준·선행 작업·계획 판과 CAS가 있고, 작업 단계·차단 원인·수신함을 공개 상태에서 계산한다. [tasks.py 14–92](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/tasks.py#L14-L92), [workflow.py 24–148](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/workflow.py#L24-L148) | 범위·근거가 있는 장기 결정의 `supersedes`, 개인 선호 기억, 자동 완료·자동 실행 |
| 검토 왕복 | 지적별 처분, 원본·수정 판·앞 판·재검토 연결 및 bounded 수정 계약이 있다. [reviews.py 84–214](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/reviews.py#L84-L214), [revisions.py 23–83](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/revisions.py#L23-L83) | 일반 팀원 전체의 GR-1/2/3 흐름 완료, 코드 변경을 자동 검토하는 전역 훅 |

특히 D01·D02·D05·D07은 **이미 기반이 반영된 후보**다. D03/D09의 작업 복귀·수신함도 일부 반영됐다. 남은 세부를 별도 확장으로 정의해야 한다.

## 3. 원본을 다시 읽어서 구분한 차이

### Hermes: 기억 고정과 스킬 읽기 사이에도 실행 권한 차이가 있다

[memory_tool.py 1–180](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/tools/memory_tool.py#L1-L180)는 MEMORY/USER를 세션 시작 snapshot으로 사용한다는 계약과, replace/remove 승인 대상의 **전체 기존 항목**을 고정하는 `_pin_matched_entries`를 갖는다. 우리 입력 hash와 템플릿 CAS가 이미 비슷한 문제를 해결한다. 가져올 것은 원래 승인 대상과 실제 바꾸는 대상이 같아야 한다는 원리다. Hermes처럼 시스템 prompt에 기억을 넣는 우선순위까지 복제하면 우리 `참고 자료이며 명령이 아니다` 계약과 어긋난다.

[session_search_tool.py 1–175](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/tools/session_search_tool.py#L1-L175)는 discover/read/scroll을 구별하고, 반복 cron 기록의 순위를 낮추며, lineage 중복과 메시지별 크기 상한을 다룬다. 우리에게 필요한 것은 **검색 결과 전체를 보내기 전에 맞는 원문 구간을 고르는 구조**다. 다만 우리 실행은 Hermes의 압축 대화 계보와 같지 않다. `run_id`가 다르다는 이유만으로 모두 별도 증거로 세거나, 같은 task라는 이유만으로 모든 반례를 중복 제거하면 안 된다.

스킬은 더 주의해서 나눠야 한다. [skills_list 248–277](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/tools/skills_tool.py#L248-L277)는 이름·설명 중심 목록이다. 반면 [skill_view 550–630](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/tools/skills_tool.py#L550-L630)는 기본적으로 template/inline shell 전처리를 하고 선언된 도구 의존성에 `pm.ensure`를 호출한다. **목록→선택 본문 고정**은 작게 이식할 수 있지만, 그 함수 전체를 단순 읽기 도구라고 연결해서는 안 된다.

### AnchorMind: 검색 순위·예산·범위는 각각 가져올 수 있다

[RankFusion.js 전체](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/RankFusion.js)는 여러 채널의 순위를 합치고 ID 전용 결과를 본문 결과로 승격하며 검색 이유를 보존한다. **아직 독립적인 여러 후보 채널이 없으면 RRF부터 넣을 효용이 작다.** 우선 현재 ASCII 식별자·한국어 표현·수정 근거를 어디서 놓치는지 평가하는 편이 구체적이다.

[BudgetSelector.js 1–180](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/BudgetSelector.js#L1-L180)는 검색 순서의 기준해, 구획 배분, 중복을 줄이는 점수, 추정치와 최종 예산 확인의 분리를 설명·구현한다. 이번에 전체 selector나 tokenizer를 실행한 것은 아니다. 우리에게는 현재 섹션별 바이트 예산 위에 **중복 답이 반례를 밀어내는 경우**만 겨냥하는 작은 개선이 먼저다. 원본의 토큰 추정/캐시를 복사하면 CLI별 실제 입력 사용량을 정확히 안다는 잘못된 인상을 줄 수 있다.

[WorkspaceScope.js 전체](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/WorkspaceScope.js)는 여러 진입점에서 같은 범위 결정을 사용하며, 명시 workspace 조회에도 global(NULL) 기록을 포함한다. 이 기본값은 우리 **같은 task만 자동 선택**과 다르다. 공통 범위 함수의 분리 원리만 가져오고 global 포함은 복제하지 않는다.

전체 패키지는 [package.json](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/package.json)에 Node, PostgreSQL·Redis client, transformer·언어 처리·토큰화 라이브러리를 포함한다. Redis 등은 설정에 따라 선택적일 수 있으므로 전부 필수 서비스라고 단정하지 않는다. 그렇더라도 Python/SQLite 앱의 작은 recall 수정과 전체 서버 운영은 비용이 전혀 다르다. [AutoReflect 37–153](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/processors/AutoReflect.js#L37-L153)는 Gemini CLI를 이용한 요약·reflect 경로다. **현재의 모델 없는 기억 선택과 같은 비용으로 묶으면 안 된다.** 이 경로의 전부를 우리 지원 provider·회계·종료 계약 밖에서 호출하지 않는다.

### codex-peek: 조회했다는 사실, 주입했다는 사실, 현재와 맞는다는 사실을 구별한다

[map-provenance.js 1–150](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/bridge/map-provenance.js#L1-L150)는 결정 이유를 별도 어휘로 찾고, 조회 영수증과 실제 첨부 기록을 구별한다. 검색했는데 0건인 것도 조회한 사실이며, 그 자체가 답변에 증거를 넣었다는 뜻은 아니다. 이 구별은 향후 검색 사용 흔적 화면에서 유용하다.

[map-freshness.js 1–170](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/bridge/map-freshness.js#L1-L170)는 기준선과 비권위 캐시를 구별하고, 기준선은 해당 검증 전이와 연결한다. 우리도 `pack.sha256`으로 과거 입력이 보존됐다는 사실과, 최신 원문이 그 사본과 같다는 사실을 분리해야 한다. 별도 파일 잠금·LRU·proof 생태계를 들이는 대신 기존 SQLite와 hash 계약에 표현을 추가하면 된다.

[verify-guard.js 1–120](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/bridge/verify-guard.js#L1-L120)는 Claude Stop 훅에서 변경·proof·시도 수를 검사한다. 이는 우리 bounded controller 안의 요청별 검토와 수명 주기가 다르다. 이미 있는 원문 결속·처분·수정 판을 활용하고, 전역 훅은 이번 이식 대상에서 보류한다. 이 파일 일부를 읽은 것으로 최신 Peek 전체의 검토 보증을 평가한 것은 아니다.

### WorkTrail: 자주 바뀌는 상태를 또 저장하기보다 판단의 종류를 보존한다

[state.py 1–190](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/state.py#L1-L190)는 관측 evidence, 반박 가능한 hypothesis, 따르기로 한 decision/constraint, 범위·증거가 필요한 ruled-out을 구별한다. 결정에는 작성 주체·근거·교체 대상을 남긴다. 이는 모델 합의나 사람의 선택을 사실 검증과 혼동하지 않는 우리 원칙과 잘 맞는다.

[search.py 전체](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/search.py)는 FTS 파생 색인과 원문 inspect를 분리한다. 원본 evidence가 append-only여서 INSERT trigger 하나로 색인이 따라가는 설계다. 우리 원장은 검토 처분·계획·수정 판이 더해지며 공개 자격도 변하므로 같은 trigger를 그대로 복사할 수 없다. 공개 자격 재확인과 파생 자료의 갱신 계약을 먼저 정해야 한다.

[recording.py 전체](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/recording.py)는 외부 관측·호스트의 결론 기록 경로에 모델을 호출하지 않는다. 우리 역시 이미 아는 상태·다음 행동을 보이기 위해 새 요약 모델을 매번 부를 이유가 없다. GitHub 카드·현재 앱 원장이 각자 맡은 사실의 기준점이며 WorkTrail DB를 두 번째 기준점으로 만들지 않는다.

## 4. 항목별 도입 판정

`좁혀 도입`은 실제 구현을 이번 문서에서 완료했다는 뜻이 아니라 아래 계약으로 범위를 제한한 권고다. 기능별로 필요한 호출만 계산하며, 표시·검색이 0회여도 검색 결과를 모델에 붙이면 입력 사용량은 늘 수 있다.

| 기존 후보 | 판정 | 가져올 범위·가치 | 추가 호출·의존성·운영 | 최소 시험·중단 조건 |
|---|---|---|---|---|
| H12·O02/O03·D01 | **이미 있음 + 좁혀 도입** | 기존 snapshot/출처/이유/누락 유지. 선호·명시 결정 편집은 M05로 분리 | 선택 0회. 현재 SQLite 재사용 | 격리 prompt에 기억이 섞이면 중단. 과거 pack이 다시 계산되면 거절 |
| H13/H14·O01·D02 | **좁혀 도입** | 기존 공개 검색에 원문 위치·일치 주변 발췌·날짜 조건부터 | 사용자 조회 0회. 첫 단계 외부 DB 없음 | 오래된 반례·긴 꼬리·한국어·코드 ID. 검색 결과와 열리는 hash가 다르면 사용하지 않음 |
| H16·O03 | **이미 있음, 그래프는 조건부** | 선택 이유·출처 링크를 유지. 그래프보다 사용한 기억 목록부터 | 표시 0회 | 단순 연관을 근거·인과로 그리면 보류. 표보다 탐색 개선이 없으면 그래프 중단 |
| O02·D05 | **좁혀 도입** | 기존 섹션 예산 위에 중복 억제와 수정 근거 탐색, M01/M02 | 0회, 외부 tokenizer 불필요 | 중요한 반례의 원문 포함률이 떨어지거나 바이트 상한이 깨지면 미채택 |
| O01·O09·D05/D10 | **조건부** | exact 식별자·한국어 검색 실패에 대해 형태소/FTS/다중 채널 순서로 실험. RRF는 채널이 생긴 뒤 | 어휘·FTS/RRF 0회. 형태소는 패키지·배포 비용, embedding은 계산·모델 자산 비용 | 같은 고정 질의셋에서 이득 없이 지연/설치 부담만 증가하면 중단 |
| O04·H17·D06 | **조건부** | 사용자가 선택한 작업/프로젝트 자료 묶음의 미리보기·import | 0회, 포맷·범위 관리. 전역 자동 검색 없음 | 다른 task/비공개 자료 유입, ID 충돌 덮어쓰기, 출처 상실이면 거절 |
| O05/O06·H12/H15·D03/D04 | **좁혀 도입, GR 뒤** | 명시 결정·제약·교체·제외와 출처. 과거 실행 원문은 그대로 | 수동 기록 0회. 후보 자동 작성은 별도 호출 | 두 창 수정·supersedes 순환·scope 변경·과거 pack 불변 시험 |
| O07·D08 | **조건부** | 같은 대상·조건의 결정 충돌 후보함. 처분은 근거와 함께 기록 | 구조 비교 0회, 자연어 판정 추가 호출 | 다른 기간·범위를 모순으로 합치거나 자동으로 정답을 고르면 중단 |
| O08·H22·D04/D10 | **좁혀 도입/보류** | 최근 미사용·중복 표시와 복원 가능한 보관은 좁혀 도입. 자동 망각·의미 통합은 보류 | 규칙형 0회, 의미 통합 추가 호출 | pin/참조 중인 절차·희귀 반례를 잃으면 미채택 |
| O10·D09 | **조건부** | 외부 인덱싱/알림이 생길 때 멱등 job·재시도만 | 관리 0회, worker·복구 비용 | CLI 실행을 두 큐가 소유하거나 중복 부작용이 생기면 중단 |
| H02/H20·O26·D07 | **이미 있음 + 좁혀 도입** | 현재 템플릿을 유지. 선택적 완료 기준·자료 자리·절차 참조 추가 | 저장/복원 0회. 단계 실행 수는 따로 계산 | 낡은 모델을 조용히 대체하거나 승인/예산이 복사되면 거절 |
| H19/H23·HP-04 | **좁혀 도입** | 이름·설명 목록과 선택한 정적 절차 본문·참조 hash를 입력에 고정 | 목록·고정 0회, 입력 증가. 스킬 서버·자동 설치 없음 | 선택/열기만으로 shell·패키지 설치가 발생하면 범위 재설계 |
| H21·HP-06 | **조건부** | 성공·실패가 남은 반복 작업에서 절차 초안 만들기, 사용자가 편집 후 저장 | 생성에 별도 bounded CLI 호출 | 한 번의 성공을 일반 규칙으로 승격하거나 원본 실패 조건을 잃으면 중단 |
| H18·O31 | **보류** | 긴 일반 대화가 실제로 필요할 때 원문 anchor 있는 압축을 비교 | 요약 호출·입력·cache 비용 | 현재 짧은 실행에 상시 압축을 추가하지 않음. 반례·제약 누락이 커지면 중단 |
| O11/O13/O14 | **이미 있음, 일반 팀원 후속에 재사용** | 지적별 처분·판 연결·요청/보고 정보·실제 상태 표시 | 표시 0회. 검토·수정 자체는 추가 호출 | 검토 이행을 사실 검증으로 승격하거나 판을 잘못 결속하면 거절 |
| O12/O15 | **조건부** | 검토 목적별 제한된 profile, 요청 ID 기반 장기 작업 찾기 | 실제 검토 추가 호출·수명 관리 | 기존 원장/종료·상한 밖 세션을 만들거나 blind 세션을 재사용하면 중단 |
| O16·D02/D03 | **좁혀 도입** | 선택된 소스의 가용성/변경 여부와 결정 이유를 연결, M03 | 0회, 기존 이벤트·hash | 검색 조회를 실제 첨부로 기록하거나 캐시를 fresh 증명으로 쓰면 거절 |
| O17/O20/O21·D03/D09 | **이미 있음 + 좁혀 도입** | 현재 workflow·수신함·카드 유지. 복귀 화면에서 근거로 이동하는 흐름 보강 | projection 0회 | 상태를 별도 수동 필드/AI 요약으로 중복 저장하면 보류 |
| O18/O19·D03 | **좁혀 도입** | 관측/해석/결정과 범위 있는 배제 사유·재검토 조건, M05 | 기본 0회 | 이전 OS/commit의 실패가 전역 영구 금지로 변하면 거절 |
| AnchorMind/Hermes/Peek/WorkTrail 엔진 전체 | **보류** | 여러 클라이언트 공통 기억·앱 밖 개발 왕복이라는 별도 요구가 생긴 뒤 비교 | 서버·저장·백업·권한·upgrade, 기능별 호출 | 기존 구독 경로·원장·한 writer·격리 경계를 유지할 수 없으면 채택하지 않음 |

## 5. 구체적으로 먼저 고칠 부분

### M01 — 수정 답이 선택된 뒤 보이는 것과 수정 답으로 찾을 수 있는 것은 다르다

**판정: 코드 확인 + 합성 재현. 우선순위: 일반 팀원 검토·수정 경로를 확장할 때 함께 처리할 검색 완전성 개선.** 현재 제품이 약속한 원래 답 검색의 범위를 넘어서는 개선이며, 기존 hash 검증이 없다는 지적이 아니다.

`memory.select`는 [75–95행](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/memory.py#L75-L95)에서 순위를 정한다. 수정 답·재검토는 순위가 정해진 뒤 [113–125행](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/memory.py#L113-L125)에 더해진다. 따라서 수정 답에만 있는 식별자는 검색 이유가 될 수 없다. 반면 화면의 공개 검색은 [catalog.py 58–64](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/catalog.py#L58-L64)에서 수정·재검토를 찾는다. **화면에서 찾을 수 있는 자료와 자동 기억이 찾는 자료가 다르다.**

2026-10-05 이 세션은 임시 SQLite 원장에 다음 합성 자료를 만들고 `memory.select`만 호출했다. 모델·네트워크·실제 사용자 원장은 사용하지 않았다. `tools.evaluate_memory.seed_case`로 공개 실행을 생성하고, 현재 `answer_revisions` 스키마에 해시가 맞는 수용 수정 답을 넣었다. 이 재현은 controller가 수정 답을 수용하는 전체 경로를 시험한 것이 아니다.

| 입력 | 관측 |
|---|---|
| 오래된 `wanted`: 원래 질문 `initialcase`, 수용 수정 답에만 `REVISION_ONLY_X`, 뒤에 무관 실행 | `REVISION_ONLY_X` 질의에서 `matched_runs=0`, `noise-4`, `noise-3`, `noise-2` 선택. `wanted` 제외 |
| 동일 원장을 `initialcase`로 질의 | `wanted` 선택. 발췌에 `REVISION_ONLY_X`와 `revision_sources`의 판·sha256 포함 |

같은 기준 checkout의 저장소 루트에서 재현할 수 있는 최소 코드다. 임시 원장만 만들며 앱 데이터와 제품 코드는 수정하지 않는다.

```python
import json
import tempfile
from pathlib import Path
from app import memory
from app.store import Store
from tools.evaluate_memory import seed_case

with tempfile.TemporaryDirectory(prefix='dml-recall-review-') as directory:
    store = Store(Path(directory) / 'journal.db')
    try:
        seed_case(store, {'history': [
            {'id': 'wanted', 'question': 'initialcase'},
            {'id': 'noise', 'question': 'unrelated topic', 'repeat': 5}]})
        answer = 'REVISION_ONLY_X correction with supporting detail'
        reply = {'answer': answer, 'sha256': memory.digest(answer.encode()), 'responses': []}
        with store.tx() as tx:
            tx.execute('INSERT INTO answer_revisions '
                '(revision_id,run_id,pid,parent_id,created_at,author,snapshot,snapshot_sha256,'
                'prompt,input_sha256,attempt,state,result) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                'rev-wanted', 'wanted', 'a', None, 7, '{}', '{}', '', '', '',
                'attempt-1', 'accepted', json.dumps({'reply': reply}))
        for query in ('REVISION_ONLY_X', 'initialcase'):
            pack = memory.select(store, 'task', query)
            print(query, pack['selection_scope']['matched_runs'],
                  [(e['run_id'], 'REVISION_ONLY_X' in e['excerpt']) for e in pack['entries']])
    finally:
        store.close()
```

**개선 경계:** 수용된 수정 답과 hash가 결속된 재검토의 검색 텍스트를 공통 공개 근거 추출 함수로 만들고, 순위 계산에도 사용한다. 기존 원래 답은 유지한다. 수정 응답의 `addressed`나 검토자의 평가를 진실로 가중하지 않는다. 일반 팀원 GR 구현이 더하는 판도 같은 자료 계약을 통과하게 한다. `PublicQueries.view` 전체를 선택기 안에서 호출해 조회 비용을 키우기보다 필요한 공개 필드만 추출한다.

**완료 시험:** 수정에만 있는 표현, 재검토에만 있는 반례, 원래 답의 여전히 유효한 반례, 손상 수정 hash, 다른 task, 취소·봉인 실행을 함께 검사한다. 새 `matched_fields`와 source format/policy 버전을 기록하고 옛 pack을 다시 만들지 않는다. 예산·격리·금지 자료 회귀가 생기면 이 확장은 채택하지 않는다.

### M02 — 찾은 위치를 보내지 못하는 발췌와 일치 없음 대체를 별도로 평가한다

**판정: 이미 명시된 한계 + 후속 설계.** 추가 fixture의 [semantic-alias-remains / no-evidence-fallback / late-answer-excerpt](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/tests/fixtures/memory_expanded_cases.json#L22-L24)는 알려진 한계다. 이를 새로 발견한 오류라고 셀 필요는 없다. 현재 섹션별 배분과 누락 표시는 좋은 기반이지만, [_fair_parts](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/memory.py#L211-L243)는 각 문자열의 앞부분을 잘라 쓰므로 본문 끝에서 질의가 맞아도 그 맞은 문장은 전달되지 않을 수 있다.

Hermes의 원문 주변 읽기를 적용해 **문서 선택과 문장 선택을 분리**하는 것이 작은 다음 단계다. 각 섹션에 `locator`, `start/end`, `text_sha256`, `source_sha256`, `omitted_before/after`를 기록하고, 일치 주변 구간과 미해결 지적 구간에 예산을 배정한다. 부정어를 지워 연결하거나 떨어진 문장을 하나의 연속 인용처럼 합치지 않는다. 원문이 아닌 새 요약은 이 단계에 필요 없다.

일치가 0인 경우에는 자동 기억 기본값을 끄는 대신 **현재 fallback 유지 / 빈 결과 / 최소 최근 결정만**을 따로 비교한다. zero-match를 숨기지 않고, 결과가 없음을 정상적인 출력으로 받아들이는 후보를 평가한다. 사용자가 명시적으로 유지한 기억 옵션을 몰래 바꾸는 일이 아니다.

완료 기준은 run 적중률에 더해 **질의에 필요한 원문 구간 포함률, 반례 보존, 무관 발췌량**이다. 현재 `evaluate_memory`가 `missing_text`를 이미 측정하므로 그 도구를 확장한다. 파라미터를 맞춘 fixture는 회귀용이 되고, 새 고정 질의셋을 별도로 두어야 한다. AnchorMind의 [paired bootstrap](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/signals/PairedBootstrap.js#L1-L145)은 비교의 불확실성을 표시하는 참고이며 작은 합성셋을 실사용 효과로 바꾸는 장치는 아니다.

### M03 — 현재 가용성 표시 위에 변경 여부를 붙인다

**판정: 현재 경계를 유지하는 편의 확장.** [memory_sources](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L115-L139)는 주석과 코드에서 `source_available`을 현재 내용의 동일성과 명확히 구별한다. pack 해시를 검증하지 않는다는 문제가 아니다.

필요한 추가 정보는 `current_source_status: same|changed|unavailable|not_checked`, 당시 `source_format/source_sha256`, 현재 검사한 format/hash다. 사용자가 원문을 펼칠 때에만 동일한 canonical 추출기로 비교하고, format이 바뀌었으면 단순 불일치를 변조라고 단정하지 않는다. 변경된 최신 문서를 과거 snapshot인 것처럼 덮어 보여 주지 않는다. Peek의 기준선/캐시 구별을 이 작은 계약으로 가져온다.

첫 시험은 메모·처분·새 수정 판이 나중에 추가된 정상 변경, 원문 이동/없음, 옛 source format을 포함한다. 비교 때문에 매 polling마다 전체 이력을 다시 해시하면 M04와 충돌하므로 선택 시 조회로 한정한다.

### M04 — 기억 검색의 비용을 측정하고, 필요할 때 파생 색인을 둔다

**판정: 정적으로 확인한 선형 비용·공유 잠금 의존성. 실제 사용자 원장의 체감 지연은 미측정.** 선택기는 전체 적격 이력을 순회하고 run별 문맥·답을 읽으며, 입력 경로는 [runtime lock 안에서 선택](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/context/inputs.py#L336-L344)한다. `CANDIDATES=24`는 최종 후보 수의 상한이며 검색할 전체 원문 바이트의 상한이 아니다. 이를 최근 24개만 본다고 설명해서도 안 되고, 출력이 작으니 비용도 일정하다고 가정해서도 안 된다.

현재 [아키텍처의 benchmark 명령](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/ARCHITECTURE.md#L118-L120)을 재사용한다. 실제 사용하는 규모에서 준비 응답·취소/상태 처리 지연을 함께 보고 요구 예산을 정한 뒤 개선한다. 첫 변경은 DB round-trip·동일 공개 문맥 재추출을 줄이는 것이다. 그다음 필요하면 SQLite 파생 색인을 둔다.

색인을 만들 때의 최소 계약은 `task_id`, `run_id`, `section_kind`, `entity_id`, `source_hash`, `extractor_version`, `visibility_revision`, `locator`, `text`다. 색인은 후보를 제안할 뿐, 반환/첨부 직전 task·공개 자격·hash를 다시 확인한다. 과거 pack은 색인에서 복원하지 않는다. 색인이 없거나 낡았으면 제한된 원본 조회 또는 명시적 재구축 상태로 돌아가며, stale 결과를 현재 증거로 간주하지 않는다. 공유 lock 밖에서 검색하려면 DB snapshot/revision을 잡고 결과 반영 시 재검사하는 설계가 필요하다. 단순히 lock을 제거하는 수정은 권고하지 않는다.

이 단계까지는 Redis·벡터 DB·remote worker가 필요 없다. 실제 지연 개선이 없거나 공개 자격·복구 계약이 불안정해지면 색인 확장을 중단하고 기존 경로를 유지한다.

### M05 — 명시 결정과 기억 선택 정책을 작은 별도 객체로 둔다

**판정: 후속 기능 설계. GR의 선행 조건이 아니다.** 현재 계획·workflow·판단 메모를 다시 만드는 것이 아니라, 작업을 오래 이어갈 때 필요한 **무엇을 따르기로 했는가 / 왜 안 했는가 / 무엇이 바뀌면 다시 보는가**를 추가한다.

가장 작은 기록은 `id`, `task_id`, `kind: decision|constraint|ruled_out`, `text`, `reason`, `evidence_refs`, `author_kind`, `supersedes`, `applicable_scope`, `revisit_when`, `revision`이다. `ruled_out`에는 범위와 증거를 요구한다. AI가 작성한 해석을 기계 관측으로 바꾸지 않으며, 사람의 결정을 외부 사실로 분류하지 않는다. WorkTrail을 참고하되 구체 객체·검증은 기존 Store 트랜잭션에 맞춘다.

핀·제외는 원문 수정 대신 선택 정책에 둔다. **범위/공개 자격 → 사용자 제외 → pin → 관련성·중복 → 크기 예산** 순서가 적절하다. pin도 격리 역할이나 바이트 예산을 우회하지 못한다. 결정 교체는 새 이벤트이며, 예전 실행의 pack과 원래 근거는 보존한다. 초과 pin은 누락 이유를 표시한다. 저장·교체는 이미 쓰는 expected revision/hash 패턴으로 두 창의 덮어쓰기를 막는다.

원문을 통째로 다시 읽어야만 다음 행동을 정할 수 있다는 불편이 반복되면 착수한다. 사용자에게 모든 기록을 승인하라고 요구하는 별도 절차는 만들지 않는다. 기존 작업 지시로 허용된 기록은 남기고, 사실·제안·선택의 종류를 정확히 표시한다.

### M06 — 스킬은 정적 절차 선택부터, 자동 학습은 나중에

**판정: 템플릿 위의 선택적 확장.** 현재 `TemplateService`를 버리고 새 workflow DSL을 만들 필요가 없다. 우선 template에 `procedure_refs` 또는 동등한 별도 참조를 붙이되, 각 항목은 `id/version/description/body_sha256/allowed_roles/source_refs`를 가진다. 사용자는 짧은 목록에서 고르고 실제 전달할 본문·자료·출력 형태를 확인한다.

이 단계는 **선택한 읽기 전용 텍스트 절차**다. Hermes `skill_view`의 shell 전처리·의존성 설치·plugin 발견은 붙이지 않는다. 나중에 실행 스킬이 필요하면 필요한 filesystem/tool/network 권한과 현재 CLI 관측 계약을 별도로 정의한다. 지원 여부를 알아내기 위해 전역 참여자 문맥을 바꾸지 않는다.

첫 시험은 오래된 procedure hash, 없는 자료 슬롯, 모델/역할 변경, 격리 역할 제외, procedure와 사용자 질문의 충돌 표시, 과거 실행 재조회다. 자동 절차 생성은 같은 작업이 반복되어 재사용 가치가 확인된 경우에만 bounded CLI로 초안을 만들고, 성공 사례뿐 아니라 실패 범위·검증 조건·되돌리기를 남긴다. Hermes [curator의 pin·예약 참조 보호](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/agent/curator.py#L208-L262)를 참고할 수 있지만, 미사용이라는 이유만으로 중요한 예외 절차를 자동 삭제하지 않는다.

## 6. 이식 후에도 하나로 유지할 계약

| 책임 | 유일한 기준 | 확장에 요구할 계약 |
|---|---|---|
| 자료의 공개 자격 | 현재 원장·역할/공개 정책 | 검색, 원문 직접 조회, export, 기억 첨부가 같은 자격을 확인. UI를 거쳤다는 이유로 허용하지 않음 |
| 후보·순위·발췌 | memory/전용 순수 추출기 | 순위 점수는 관련성. 사실 신뢰도나 독립 정족수로 쓰지 않음 |
| 실행 입력 | InputBuilder가 만든 manifest·hash | 선택한 기억/절차를 호출 전에 고정. 실행 중 메모리 갱신이 이미 보낸 입력을 바꾸지 않음 |
| 예산·종료·재시도 | 기존 호출/실행 경로 | 회고·절차 생성도 새 호출로 기록. 검색/알림은 표시용 모델 호출을 만들지 않음 |
| 파생 검색 자료 | 다시 만들 수 있는 인덱스 | 원장·과거 pack·결정 원문을 덮어쓰지 않음. stale/누락/손상을 구별 |
| 현재 결정 | 범위·근거·교체 관계가 있는 선언 | 모델 답/검토/인간 선택의 종류를 유지. 의미 합의로 사실 확정하지 않음 |

비용은 호출 수와 입력량을 함께 본다. 현재 footer 상한은 [12,000 UTF-8 바이트](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/memory.py#L15-L23)이며 호출에 실제 붙은 기억의 합은 `각 호출의 footer bytes 합`이다. 일반 팀원·상위 역할이 같은 pack을 반복 사용해도 입력량은 역할별로 발생한다. 이것을 토큰 수로 동일하게 간주하거나 provider cache로 무료라고 추정하지 않는다. 자동 회고를 추가하면 별도의 호출·생성 입력·결과 검토 비용까지 더해진다.

## 7. 권고 순서와 완료 기준

1. **현재 GR-1→GR-2→GR-3 계획을 유지한다.** 기억/검색 때문에 일반 팀원 검토 기능 구현을 다시 미룰 필요는 없다. M01의 공통 공개 근거 범위는 GR의 검색·기억 연결을 만들 때 같이 설계한다.
2. **M01/M02를 한 번에 모두 튜닝하지 말고 각각 비교한다.** 먼저 수정·재검토 검색 누락을 해결하고, 그다음 일치 주변 발췌와 fallback 선택을 비교한다. 기존 합성 회귀와 새 holdout을 구별한다.
3. **M03은 작은 읽기 기능으로, M04는 측정에 따른 성능 기능으로 분리한다.** 현재 hash 방어를 유지하면서 사용자가 최신/당시 자료를 구분할 수 있게 한다. 실측 근거가 생기기 전 외부 DB를 먼저 도입하지 않는다.
4. **반복 설정·장기 작업 불편에 맞춰 M05 또는 M06을 선택한다.** 둘 모두 0회 관리 경로부터 시작할 수 있다. 자동 회고·semantic ranking·full memory service는 이 경로의 효과와 비용을 확인한 뒤 비교한다.

각 구현의 종료 기준은 사용자가 해당 기능을 사용해 목적을 달성할 수 있고, 과거 원문·봉인·호출 상한·입력 고정이 유지되는 것이다. 필요하지 않은 기능을 많이 구현한 것은 이식 성공의 기준이 아니다. 라이브 모델 효과는 기능의 오프라인 완료와 별도로 같은 과제·같은 자료·별도 원장과 호출 상한으로 측정한다.

## 8. 원문 근거와 읽은 범위

아래 고정 판을 **2026-10-05 GitHub 도구로 직접 다시 읽었다.** 이전 조사 요약의 주장을 독립 근거로 승격하지 않았다. 최신 release/HEAD 전체 변경 감사를 한 것은 아니며, 이 날짜에 해당 고정 파일이 존재하고 아래 내용이 담겼다는 확인이다. 줄 범위 밖의 호출자·종속물·전송 인증은 별도로 읽지 않은 한 검증했다고 하지 않는다.

| 구분 | 원본 commit·파일 | 이번에 읽은 범위·한계 |
|---|---|---|
| HM-memory | `55bea1ddf1754dcacb87f13185df1eb1273c0a6e` · [tools/memory_tool.py](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/tools/memory_tool.py#L1-L180) | 1–180. snapshot 계약·matched-entry·write gate. MemoryStore 전체·실제 동시 쓰기 미실행 |
| HM-search | 같은 판 · [tools/session_search_tool.py](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/tools/session_search_tool.py#L1-L175) | 1–175. 모드/상한·source 분류·lineage/시간 helper. 전체 FTS query와 runtime 검색 품질 미검증 |
| HM-skill | 같은 판 · [tools/skills_tool.py](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/tools/skills_tool.py#L240-L290) | 240–290, 550–630. 목록과 선택·전처리·의존성 설치의 경계. 전체 스킬·스크립트 미감사 |
| HM-curator | 같은 판 · [agent/curator.py](https://github.com/NousResearch/hermes-agent/blob/55bea1ddf1754dcacb87f13185df1eb1273c0a6e/agent/curator.py#L200-L282) | 200–282. 자동 상태 전이·pin/예약 보호·preview 문구. curator 모델 호출 미실행 |
| AM-budget | `cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb` · [BudgetSelector.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/BudgetSelector.js#L1-L180) | 1–180. 알고리즘 계약·상한/계수·토큰 계산 helper. 전체 예산 selector 미실행 |
| AM-rank | 같은 판 · [RankFusion.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/RankFusion.js) | 전체 1–101. RRF·ID 승격·채널 이유·hydration 순서. DB 검색 미실행 |
| AM-scope | 같은 판 · [WorkspaceScope.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/read/WorkspaceScope.js) | 전체 1–102. effective scope·global 포함·all-workspace 조건. 모든 인증 진입점 미감사 |
| AM-eval | 같은 판 · [PairedBootstrap.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/signals/PairedBootstrap.js#L1-L145) | 1–145. 짝지은 차이·seed·표본 부족·묶음 계약. 실제 검색 이득이나 통계적 검정력 미측정 |
| AM-reflect | 같은 판 · [AutoReflect.js](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/lib/memory/processors/AutoReflect.js#L1-L165) | 1–165. CLI 요약/reflect·skip·오류 경로. 전체 LLM fallback 체인 미감사 |
| AM-deps | 같은 판 · [package.json](https://github.com/JinHo-von-Choi/anchormind/blob/cdcdfaab9d1b9a64fa5f6af23354ac730c24c9fb/package.json) | 전체 1–93. 선언된 6.1.0과 의존성. 실제 설치·모든 선택 설정 미검증 |
| PK-provenance | `1baf5ccd360b50da57911401aeca1388e1b0c05e` · [map-provenance.js](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/bridge/map-provenance.js#L1-L150) | 1–150. 결정 이유 파서·어휘 매칭·조회 영수증. 후반 자동층 전체 미감사 |
| PK-freshness | 같은 판 · [map-freshness.js](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/bridge/map-freshness.js#L1-L170) | 1–170. 기준선/캐시·세대·잠금·예산. 별도 최종 freshness 판정기 미실행 |
| PK-hook | 같은 판 · [verify-guard.js](https://github.com/kimbyungsu/codex-peek/blob/1baf5ccd360b50da57911401aeca1388e1b0c05e/bridge/verify-guard.js#L1-L120) | 1–120. Stop 훅·변경/시간/proof·시도 상한. 최신 전체 검토 규칙 미감사 |
| WT-state | `3fb48f980133fd2fb458362648c7bb04cfdbea2b` · [state.py](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/state.py#L1-L190) | 1–190. 선언·결정/제약·근거 범위·교체·배제. 다중 사용자 서비스 미실행 |
| WT-search | 같은 판 · [search.py](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/search.py) | 전체 1–87. FTS 파생 색인·소유자 필터·원문 inspect. 서비스 전체 접근 제어 미감사 |
| WT-record | 같은 판 · [recording.py](https://github.com/jasonethicseo/worktrail/blob/3fb48f980133fd2fb458362648c7bb04cfdbea2b/casebook/core/recording.py) | 전체 1–62. 모델 없는 기록 경로·조건부 상태 변경. Worker 경쟁/트랜잭션 전체 미검증 |

우리 코드의 직접 검토 범위는 `app/memory.py`, `app/application/templates.py`, `app/queries/catalog.py` 전체, `app/context/inputs.py`의 준비/일반 manifest/자료 검증/기억/승인 결속 경로, `app/queries/public.py`의 search/memory_sources, `app/application/tasks.py`와 `app/workflow.py`의 계획/단계/의존성/수신함, `app/revisions.py`의 prompt/응답 계약, `tools/evaluate_memory.py`와 추가 fixture/검사다. 검토·수정 서비스 전체의 실행 수명과 모든 UI 경로를 이 문서가 재감사한 것은 아니다.

기존 후보와 상세한 과거 원문 범위는 [기능 목록](../../research/feature-catalog-2026-10-04/README.md), [부품별 분석](../../research/component-comparison-2026-10-04/README.md), [참고 지도](../../REFERENCE-MAP.md)로 연결한다. 이 기록은 그 자료를 지우거나 현재 구현 상태를 과거 문서에 덧씌우지 않는다.
