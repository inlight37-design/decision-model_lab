# Codex Bridge 해체분석

2026-09-26 · upstream **`eb7cec1da0b13d2765eaab770c58d177024f423e` / v0.1.103**. 이 글의 평가는 이 판에 한정한다. 경로·함수는 실제 소스에서 확인했고, 실행 관측과 한계는 [EVIDENCE](EVIDENCE.md)에 분리한다. 사용자 첨부 PDF의 설명을 제품 성능으로 확대하지 않는다.

## 1. 먼저 결론

**설치해서 우리 실행 엔진 옆에 붙일 제품보다는, 장기 작업의 검증·기억·승인 절차를 배울 사례로 가치가 크다.** 특히 배울 것은 다음 다섯 가지다.

- 검증을 했다는 말 대신 **어느 입력·코드·역할·규칙 판을 검증했는지 결속된 영수증**을 남기는 것.
- 검토자가 지적할 때마다 무조건 고치는 대신 **사실 오류 수정 / 보강 요구 수용 / 근거 있는 반박 / 범위 밖 보관 / 사용자 판단**으로 처리하는 것.
- 대화 요약을 곧바로 사실이나 정책으로 만들지 않고 **약한 관찰 → 근거 확인 → 변경 제안 → 사용자 승인**을 분리하는 것.
- 수칙을 모두 매번 넣지 않고 **항상 적용되는 작은 코어와 필요할 때 고르는 서고**로 나누고, 실제 주입한 목록을 기록하는 것.
- 긴 실행을 다시 시작하지 않고 **같은 job을 조회·복구**하고, 상한에 닿으면 통과로 위장하지 않은 마감문을 남기는 것.

반면 영속 검증 세션, 공유 홈의 훅, 자동 Scout/보강/선별/큐레이션, 대형 VS Code 화면을 함께 들이면 우리 봉인·독립 정족수·예산·최소 구조와 충돌한다. 이것은 단순한 연결 UI가 아니라 상당한 정책 엔진이다. **좋은 개념을 골라 기존 controller·원장에 넣는 것과 제품 전체를 채택하는 것은 다른 결정**이다.

## 2. 제품을 층별로 나누면

| 층 | 실제 주인 파일 | 책임과 연결 |
|---|---|---|
| 배포 | `install.js`, `out/hook-setup.js`, `codex-plugin-install.js` | 운영 사본 복사, CLI 훅·확장 등록, 설정 백업, 배포 파일 일치 점검 |
| 구현자 접점 | `contract-inject.js`, `session-start.js`, `codex-hook.js`, `verify-guard.js`, `preview-gate.js` | 시작·재개·압축·입력·도구·종료 경계에서 규약 전달 및 재검증 안내 |
| 검증 작업 | `codex-bridge.js`, `ask-job-worker.js` | 연결 세션, 모델/추론 설정, 비동기 ask job, deadline, 중복 실행 방지, 결과 회수 |
| 운영·판정 상태 | `contract-lib.js`, `verify-cap-handoff.js` | 계약·proof·지적 원장·처분·회차·수칙 승인·동결 스냅샷·잠금·복구 |
| 지도·기억 | `project-map.js`, `map-*`, `scope-*`, `scout-*`, `ledger-events-core.js` | 코드 구조/변경 범위의 투영, 정찰, 관찰 및 근거, 요청별 제한 검색 |
| 기억 보강·수칙 | `map-enrich.js`, `map-provenance.js`, `evidence-challenge.js`, `curation.js`, `selector-runner.js` | 근거 대조·재확인, 출처 추적, 후보·승인, 관련 수칙 선별 |
| 표시 | `out/extension.js`, `rules-flow.js` | VS Code 대시보드·상태·세션·사용량·규칙·제안함의 투영 |

근거: [package.json](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/package.json), [bridge](https://github.com/kimbyungsu/codex-peek/tree/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge), [설치기](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/install.js#L37-L107). 표는 읽은 주요 경로의 책임 지도이지 모든 함수의 전수 감사 선언이 아니다.

### 핵심 흐름

구현자 입력 → 작업별 계약/승인 수칙 전달 → 변경·정찰·관련 기억 선택 → 검증 입력 동결 → `ask-start` → 같은 `ask-wait` 조회 → 실제 결과·proof 기록 → 지적별 재판단 → 필요 시 수정/재검증 → 상한 마감 및 다음 작업 기억.

첨부 PDF 6쪽도 변경 감지·영향지도·관찰 일지·확정 MAP, 검증과 재판단을 연결한다. 다만 도식의 '독립 검증'은 **구현자와 검증자 역할 분리**라는 제품 맥락이다. 우리 앱의 새 입력 공간·비공개 초안·문맥 관측·독립 정족수와 동등한 보안/실험 조건을 뜻하지 않는다.

## 3. 설치 명령이 실제로 바꾸는 것

사용자가 가져온 문자열은 `git clone …`과 `cd …` 사이의 명령 구분이 빠진 소개문이다. 이번 작업에서는 **실행하지 않았다**. 명령을 제대로 나누는 것보다 중요한 문제는 설치의 영향 범위다.

`install.js`는 기본 `~/.codex-bridge`에 엔진을 복사하고 기본 `~/.claude/settings.json`에 훅을 병합한다. `CODEX_BRIDGE_HOME`, `CLAUDE_CONFIG_DIR` 등으로 경로를 바꿀 수 있지만 이것만으로 모델·프로세스·계정까지 격리되지는 않는다. 확장 설치도 시도한다. 기존 설정의 읽기 실패와 JSON 손상을 구분하고, 백업 후 원자적 파일 교체를 하며, 자기 훅만 교체하려는 장치가 있다. `bridgeRuntimeParity()`는 소스/운영 파일의 내용과 배포 manifest를 비교한다. 이런 **'내가 본 코드와 실제 실행되는 사본이 같은가'** 점검은 유용하다.

그러나 복사 → 설정 변경 → 확장 설치 → doctor가 **전체 하나의 원자적 설치 거래는 아니다**. 뒤 단계가 실패하면 종료는 실패로 표시되더라도 앞의 훅·운영 사본 변경은 남을 수 있다. 설치기 안내 자체도 기존 세션이 설정을 감시하는 조건에 따라 다음 프롬프트부터 반영될 수 있다고 구분한다. 따라서 '서버를 켜지 않으면 진행 중인 작업에 영향이 없다'는 판단은 틀리다.

근거: [install.js 752–918](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/install.js#L752-L918), [제거·진입점](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/install.js#L930-L993). 설정 감시 설명은 upstream의 관측/안내이며 이번 세션에서 사용자의 CLI로 재현한 사실이 아니다.

**판정:** 실행 중인 환경에서는 설치 금지. 필요할 때도 별도 사용자/VM·홈·workspace·VS Code profile과 고정 버전으로 따로 관측해야 한다. 우리 프로젝트에는 설치기를 가져오기보다 배포/실행 판 일치와 실패 표시 원칙만 참고한다.

## 4. 검증 영수증: 좋은 점과 보장하지 않는 것

### 4.1 두 proof를 같은 수준으로 읽으면 안 된다

Claude 구현 경로의 proof v1은 구현 세션 키, 성공 종료·응답 길이, 시각을 남긴다. `verify-guard.checkProof()`는 현재 사용자 입력/마지막 변경 이후인지 확인하며 **workspace를 비교하지 않는다는 선택을 소스에 명시**한다. 삭제된 파일의 최신성을 조상 디렉터리 mtime으로 근사하는 부분도 있다.

Codex 구현 경로의 durable proof v2는 더 강하다. `jobId`, 구현 세션·turn·role revision, workspace, HEAD 상태/OID를 갖고, 복구 영수증의 proof SHA256과 시각까지 대조한다. 기록 직전 역할/turn이 바뀌면 stale로 거절한다. 정본 job 경로·ID·상태를 확인하며 직접 `ask`로 v2를 만드는 우회도 거절한다.

근거: [writeProof/readDurableEnvJob](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/codex-bridge.js#L377-L457), [v1 검사](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/verify-guard.js#L82-L104), [v2와 receipt](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/contract-lib.js#L1539-L1697).

여기서 proof는 **검증 실행의 결속 증거**이지 '그 코드가 옳다'는 수학적 증명도, 답변의 사실성 검증도 아니다. HEAD는 미커밋 파일 전체의 내용 지문을 대신하지 않고, mtime은 암호학적 내용 결속이 아니다. 또 같은 계정/파일 권한에서 수정 가능한 proof 파일 자체를 악의적 구현자로부터 보호하는 별도 신뢰 경계로 해석하면 안 된다.

### 4.2 인용 대조도 층을 나눠야 한다

`citation-check.js`는 파일 실존, 줄 범위, 근처 식별자를 비교하고 `outside-root`, `unresolved`, `no-token`, `token-not-near-line`을 구분한다. 문자열 속 식별자를 진짜 코드로 세지 않으려는 처리도 있다. `map-enrich.js`는 이번 발송 발췌에 없는 파일/줄을 인용한 후보를 제한하고 `sourceFp`, `excerptBase`, `excerptCfg`를 남긴다.

이것은 **엉뚱한 파일·없는 줄·보내지 않은 근거를 적발하는 장치**다. 정상 경로·식별자가 존재해도 인과 설명이나 수정 결론은 틀릴 수 있다. 우리 `synthesis.py`의 원문 인용 일치 검사와 마찬가지로 UI에 '사실 검증 완료'로 표시하면 안 된다.

근거: [citation-check.js](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/citation-check.js#L1-L50), [map-enrich.js](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/map-enrich.js#L158-L269).

## 5. 끝없는 검토 왕복을 다루는 설계

`contract-lib.js`의 처분은 `fix-fact`, `fix-gap`, `rebut`, `park`, `escalate`다. '실제로 틀린 것'과 '더 보강하라는 요구'를 가르는 것이 중요하다. 같은 지적이 후속 회차에 다시 등장하면 예전 처분을 영구 면허로 쓰지 않도록 활동 회차와 결속한다. 캠페인·승인 수칙 세대·선별 경계가 다르면 예전 통과를 같은 확인 회차로 재활용하지 않는다.

상한에 도달하면 수용/반박/보관/사용자 판단으로 마감하고, `held`, `cap-settled`, `incomplete`를 구분한다. **상한 소진을 '검증 통과'로 바꾸지 않는 것**이 좋다. 반대로 종료 훅은 무한 차단을 피하려고 일정 반복 뒤 종료를 허용하며 미검증 경보를 남기는 경로가 있다. 파싱·일부 상태 읽기 실패에는 fail-open 경로도 있다. '강제'라는 소개 표현을 모든 조건에서 종료를 막는 강한 접근통제로 읽으면 안 된다.

근거: [deriveRoundType·처분](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/contract-lib.js#L5293-L5367), [종료 훅과 마감](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/verify-guard.js#L140-L385).

**우리에게 적용:** 먼저 문서/검토 결과에 처분과 재검증 대상을 표시한다. 향후 기능화하더라도 현재 runner의 성공 판정·정족수·봉인을 약하게 바꾸지 않는다. 토론의 종료와 결과의 승인, 실행 프로세스의 종료는 서로 다른 상태다.

## 6. Project MAP·기억·수칙은 같은 저장물이 아니다

| 종류 | 의미 | 우리식 주의점 |
|---|---|---|
| 구조/영향지도 | 파일·관계·변경 지점 탐색 | 지도에 있다는 이유로 실제 코드 상태를 확인한 것으로 세지 않음 |
| Scout 결과 | 변경 영향에 대한 모델의 탐색 결과 | 보조 주장이다. 정답이나 다른 참여자의 독립 초안이 아님 |
| 관찰/설계 경위 | 과거 사건·근거·반박·결정의 출처 | 참고 자료와 강한 정책을 분리하고 최신성 검사 |
| 수칙 후보 | 사고나 사용자 요구에서 파생된 제안 | 자동 생성/채택 후보와 사용자 승인은 다름 |
| 승인 수칙 | 사용자가 확인한 범위·금지·환경 | 승인한 정확한 문안/판과 실제 주입본을 결속 |
| 선별 영수증 | 이번 요청에 실제 실린 항목 | 미리보기·큐레이션 목록·타 저장소 기록과 구별 |

### 6.1 단순 벡터 검색보다 배울 부분

`map-retrieval.selectCandidates()`는 의도·변경 파일·장부·이웃 축을 제한적으로 고르고 중복을 제거한다. 관련 후보가 없으면 빈 결과와 fallback을 반환하지, 상한을 채우려고 무관한 기억을 넣지 않는다. 초기에는 이런 결정론적 제한 검색을 그대로 **아이디어로** 활용하는 편이 모델 검색기나 벡터 DB를 먼저 만드는 것보다 적은 구조다.

`map-provenance.registerAutoEntries()`는 사건이 가리킨 저장소·앵커·내용 해시를 현재 원문과 비교한다. 원문이 바뀌면 옛 사건으로 새 내용을 재승인하지 않는다. 세대 순서·사건별 철회·주제 전체 철회·철회 취소, 사람의 명시적 덮어쓰기 우선순위가 있다. 설계 경위의 동봉 문구는 **참고이며 판정 기준이 아님**을 명시한다.

근거: [검색](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/map-retrieval.js#L220-L268), [참고 동봉](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/map-provenance.js#L133-L173), [세대·철회·원문 결속](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/map-provenance.js#L362-L474).

### 6.2 AI가 자기 말을 규칙으로 만드는 것을 막는 흐름

수칙은 `supportedEnv`, `alwaysBlocker`, `outOfScope` 세 축이다. 제안 전문의 필드·길이·개수·해시를 검사하고, 후보 → 초안 → 승인 전이를 분리한다. 승인 표면은 대시보드 쪽이며 구현자용 CLI에 approve 명령을 두지 않는 의도가 명시돼 있다. 이것은 좋은 **권한 설계 의도**지만 동일 OS 사용자 권한의 악성 코드까지 막는 인증 경계로 검증한 것은 아니다.

`curation.commitCuration()`은 제안을 임시 행 → 결과 행 → 노출 가능한 제안 행으로 기록하고 재읽기로 확인한다. 같은 입력에 다른 결과를 덮어쓰지 않는 충돌 검사, 제안함 상한, 수칙 변경 도중의 복구 상태도 있다. 우리 SQLite에서는 이를 별도 JSON 원장·WAL 파일로 복제하기보다 **기존 거래에 넣을 수 있는 최소 상태 전이**로 만드는 편이 맞다.

근거: [초안 검증·승인 전이](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/contract-lib.js#L3916-L3995), [큐레이션 기록](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/curation.js#L319-L377), [승인 사건과 도장 대조](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/map-provenance.js#L539-L584).

### 6.3 봉인된 논의에 이 기억을 그대로 넣으면 안 된다

영속 검증 세션과 구현/검증 대화에서 축적한 관찰은 장기 코딩에는 편리하지만, 같은 질문의 독립 평가에는 선행 답·평가자의 편향이 섞일 수 있다. 서로 다른 session ID만으로 이 문제가 해결되지는 않는다.

우리 격리 역할에는 **실행 전에 승인·고정한 공통 자료만** 넣어야 한다. 봉인 중 다른 참여자의 출력·길이·시간·지적을 기억 후보로 뽑거나 공유하면 안 된다. 공개 뒤 나온 교훈도 그 실행에 소급 적용하지 않고 다음 실행의 선택된 자료로만 사용할 수 있다. 일반 협업 역할의 개인 기억을 격리 팀원의 독립 정족수 근거로 세지 않는 구분이 필요하다.

## 7. 수명·예산·과금: 겉보기와 다른 중요한 차이

`ask-start`는 고정 job을 만들고 detached worker가 일한다. `ask-wait`는 같은 job을 조회한다. selector가 필요한 경우 selector와 verifier의 deadline을 분리하고, worker는 남은 시간을 계산한다. 손상 job 때문에 중복 실행 위험이 있으면 보수적으로 새 실행을 막는 경로도 있다. **조회 재시도와 모델 실행 재시도의 분리**는 채택 가치가 높다.

그러나 읽은 실행 경로에는 `spawnSync` timeout과 `child.kill()`이 보이며, 우리 `tree_confirmed_empty`에 해당하는 전체 자손 종료 증명을 확인하지 못했다. PID 생존 검사·TTL·부모 종료는 PID namespace/Windows job object의 전체 자손 수명 보장과 같지 않다. 또한 verifier의 답 없는 실패 때 제한적으로 **검증 회차를 환급**하는 분기가 있다. 이것은 모델 서비스의 실제 사용량 환불을 뜻하지 않는다. 우리에서는 이미 시작 예약한 CLI 호출을 환급하지 않는 원칙을 유지해야 한다.

추가 호출도 분리해야 한다. 정찰, 의미 보강, 수칙 선별, 근거 재확인, 정리 담당은 단순 UI가 아니라 조건에 따라 모델을 부르는 실행 경로다. '검증 1회'를 앱 전체 모델 호출 1회로 세면 비용이 숨는다. optional DeepSeek 경로도 있으므로 '기본 기능이 유용하다'와 '전부 구독만 쓴다'를 혼동하면 안 된다. 이번 검토는 provider에 실제 연결하지 않았다.

근거: [job 생성·조회](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/codex-bridge.js#L3100-L3268), [worker](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/ask-job-worker.js#L199-L278), [실행기](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/codex-bridge.js#L2730-L2868), [회차 환급](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/codex-bridge.js#L4958-L4976).

## 8. 화면에서 배울 것은 전체 대시보드보다 '표시의 근거'

PDF 8–18쪽에는 모델·역할·실시간 상황·세션 연결·MAP·통계·수칙·추론강도·대기시간을 나누는 화면이 있다. 사용자가 원하는 역할판과 일부 겹치지만 모양을 복제할 이유는 없다. 우리 island-ui와 홈→작업→역할판을 유지한다.

`rules-flow.lastSelectionOf()`는 **workspace와 repo가 모두 일치하는 실제 검증 영수증만** 고른다. 미리보기와 정리 담당의 후보 개수는 '실제로 주입한 수칙 수'가 아니다. 공통 코어의 `injectedChars` 역시 문자 길이이지 토큰 수나 구독 요금이 아니다. 이런 구분을 '선택한 모델 / 보낸 요청 / 보고된 모델 / 미확인', '후보 / 승인 / 이번 실행에 동봉'에 적용하면 좋다.

근거: [rules-flow.js](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/rules-flow.js#L1-L55), [모델/추론 인자](https://github.com/kimbyungsu/codex-peek/blob/eb7cec1da0b13d2765eaab770c58d177024f423e/bridge/codex-bridge.js#L2505-L2517). 우리의 봉인 중 메타데이터 비공개 정책은 유지한다.

## 9. 코드 품질 평가: 배울 만큼 진지하지만 작은 부품은 아니다

긍정적 근거는 많다. 순수 projection/reducer와 실행기를 나눈 일부 모듈, 고정 세대·원문 해시·scope 검사, 승인 초안의 엄격한 검증, 임시/미완료 상태의 구분, 중복·복구 테스트 목록, 실제 배포 내용 일치 점검은 단순 프롬프트 묶음보다 발전된 장치다.

동시에 배포물의 `contract-lib.js`는 638,244 bytes, `codex-bridge.js`는 503,066 bytes다. 함수 집합에 세션·계약·지도·정책·예산·수칙·원장이 모여 있으며 확장 표시부도 크다. 이 수치는 고정 커밋의 배포물 바이트 관측이고, 좋은/나쁜 코드의 단독 판정 기준은 아니다. 다만 **모듈 하나만 복사해도 상당한 의존 그래프를 함께 가져올 가능성**을 보여 준다. 생성된 `out/`와 배포용 `bridge/` 사본도 있어 파일 수나 줄 수를 독립 기능 수로 해석할 수 없다.

실제로 작은 직접 호출 가드에는 한계가 있다. 원본 `codex-guard.js`를 외부 실행 없는 대역 환경에서 평가하면 단순 `codex exec` 문자열은 차단하지만, 앞에 `echo codex-bridge;`라는 텍스트가 있으면 허용된다. 테스트 문자열은 **명령으로 실행하지 않았다**. 이는 검증 훅이 보안 격리기가 아님을 보여 주는 국소 반례이지, 운영 환경 침해나 모든 게이트 우회를 재현했다는 뜻이 아니다. 이를 정규식 한 줄씩 강화해 우리 보안 경계로 들이기보다 기존 shell-free runner와 격리를 보존하는 편이 맞다.

테스트 수가 많다는 사실만으로 모델 품질이나 운영 보안을 입증할 수 없다. 해당 upstream SHA의 CI 성공은 확인했고 별도 순수/대역 probe도 수행했지만, 우리 PC에서의 설치·모델·장시간·취소·전수 upstream 시험은 하지 않았다. 자세한 실행 범위와 검토 도구 자체의 수정은 [EVIDENCE](EVIDENCE.md)에 남긴다.

## 10. PDF 벤치마크를 어떻게 읽어야 하나

**게시자 보고**와 **이 검토의 해석**을 분리한다.

| 게시자 자료의 조건/결과 | 자료 위치 | 허용되는 해석 |
|---|---|---|
| 통제 비교: 순정 26/59, 2트랙 29/60, Cold 27/60, Warm 60/60 첫 구현 완결 | PDF 1–4쪽 | 이미 올바른 확인 기억이 있을 때 큰 차이가 나온 통제 사례 |
| 모호한 24개 대칭 제외, 순정 1건 외부 한도 무효 | PDF 2쪽 | 제외 기준/원자료를 보지 않고 독립 재계산했다고 할 수 없음 |
| Warm 재발 0/60, Wilson 상한 약 6.0% | PDF 3–4쪽 | 표본에서 0건이지 앞으로 사고가 없다는 보장이 아님 |
| Real Lite 16 run: 자동 포착만으로 기억 이점 미확인 | PDF 5쪽 | 좋은 기억을 자동으로 만드는 것 자체가 별도 난제 |
| F6 rebench 4 run, 한 사고 유형의 end-to-end 확인 | PDF 5쪽 | 승인→수칙→재발 차단의 좁은 작동 근거, 전체 과제 일반화는 불가 |
| 60/60은 정확한 기억이 이미 주어진 조건이며 v0.1.103 전체 제품 성능이 아님 | PDF 5쪽 | 소개 원문 자체가 명시한 한계이며 반드시 함께 전달 |

이 검토는 해당 통제 벤치의 원시 실행 trace·과제별 판정·제외 전 데이터 전체를 확보해 재판정하지 않았다. 공개 배포물·읽은 저장소 자료·PDF만으로 그런 재현이 끝났다고 말하지 않는다. 여러 variant가 같은 scenario를 공유한다면 표본 간 상관과 기억의 과제 특이성도 후속 실험에서 확인해야 한다. **이 제품을 붙이면 우리 정답률이 100%가 된다거나, 2트랙보다 3트랙이 일반적으로 우월하다는 결론은 나오지 않는다.**

## 11. 최종 평가

| 평가 대상 | 판정 |
|---|---|
| 장기 작업의 기억·검증·재판단 아이디어 | 적극 참고 |
| 실행·승인·출처·영수증의 세대 결속 | 작은 개념으로 재구현할 가치 높음 |
| 직접 설치·공유 훅 연결 | 지금은 하지 않음 — 현재 작업 영향과 문맥 오염 |
| 엔진·대시보드 통째 이식 | 채택하지 않음 — 기존 앱과 이중 책임 |
| 격리/독립성/사용량 보장 대체 | 불가 — 목적과 보장 범위가 다름 |
| 벤치 숫자에 근거한 성능 보증 | 불가 — 제품 전체·우리 과제에서 미검증 |

구체적 적용 위치와 모의 완료 조건은 [ADOPTION](ADOPTION.md)에 둔다. 이 검토는 제안이며 사용자 결정·실행 계약·관측 허가를 변경하지 않는다.
