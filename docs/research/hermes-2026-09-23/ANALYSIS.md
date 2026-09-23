# Hermes 패턴 상세 분석

2026-09-23 · [요약](README.md) · [적용 계획](ADOPTION_PLAN.md) · [근거/범위](EVIDENCE.md)

이 문서의 사실은 고정 판본의 소스 또는 문서에 연결하고, **우리 제안**은 별도로 표시한다. 전체 제품 감사를 주장하지 않는다. 기반 판본과 접근 제한은 [근거표](EVIDENCE.md)에 있다.

## 1. 먼저 맞춰야 하는 제품의 경계

Hermes는 자체 agent loop, provider routing, 도구 실행, 기억·스킬, 세션, 여러 입구를 가진 범용 agent 제품이다. 우리 프로젝트는 **각 회사의 native 하네스를 보존한 채** 실행 순서·권한·예산·근거를 통제하는 앱을 만들려 한다. 경제성뿐 아니라 상급 모델의 독립 검토도 목표다. 따라서 같은 이름의 ‘agent’, ‘provider’, ‘session’이 곧 같은 책임을 뜻하지 않는다. [H02](EVIDENCE.md#h02), [P01–P04](EVIDENCE.md#project)

| 책임 | 유지할 소유자 | Hermes에서 참고할 부분 | 넘기면 안 되는 것 |
|---|---|---|---|
| 로그인·실제 native 내부 도구 루프 | 각 공식 CLI | native transport/session 연결 패턴 | 인증 파일 복사, 다른 API로 조용히 바꾸기 |
| 실행 구성·권한·예산·종료 | 우리 controller | 세션 수명주기, typed result, 요청별 라우팅 | child별 무제한 추가 호출, 모델의 자기 권한 승인 |
| 공통 자료·독립 초안·근거·미합의 | 우리 evidence/claim 계층 | snapshot, lineage, 원문 검색 | 하나의 합성 summary를 유일한 사실로 저장 |
| 사용자 화면 | 우리 Ledger 셸 | 연결/실행 상태 분리와 필요한 상세 공개 | 모델이 추측한 진행률·사용량·검증 표시 |
| 재사용 절차 | 우리 승인된 skill catalog | 목록/본문/참조 분리, 경험의 절차화 | 검토 없는 전역 자기수정, 과거 답안 자동 주입 |

**우리 제안:** Hermes를 필수 dependency나 최상위 orchestrator로 두지 않는다. 필요한 패턴을 작은 모듈로 재구현하고, 실제 코드를 가져올 때만 해당 파일의 의존성과 고지를 추적한다. 라이브러리 채택 비용은 파일 길이가 아니라 provider·설정·환경·plugin·DB·callback에 대한 결합까지 포함한다. 예를 들어 `delegate_tool.py`는 여러 sibling과 `AIAgent`에 연결되어 있어 독립적인 작은 멀티모델 라이브러리처럼 떼어 쓰기 어렵다. [H07](EVIDENCE.md#h07), [H16](EVIDENCE.md#h16)

## 2. 스킬: 통째 프롬프트보다 ‘필요할 때 꺼내는 절차’

### 관측

Hermes는 작은 skill 목록에서 시작해 선택한 SKILL.md, 이어서 필요한 참조 파일을 읽는 progressive disclosure를 제공한다. `/learn`도 원자료를 바탕으로 절차와 참조 문서를 만드는 경로로 설명된다. 실제 skill discovery 코드는 프로필 위치를 조회하고, 플랫폼/사용 중지 조건을 적용하며, 검색 결과를 cache한다. 절대 경로나 traversal 검사도 존재한다. [H03](EVIDENCE.md#h03)

### 우리에게 유용한 이유

현재 저장소는 근거와 인계 문서가 풍부하지만, 이를 모든 모델의 모든 호출에 넣는 것은 목적과 다르다. 예를 들어 `bounded_patch` 구현자는 변경 범위·검사 명령·완료 조건이 필요하고, 독립 설계 논의자는 공통 문제·제약·근거만 필요하다. 둘에게 같은 archive 전체를 주면 token뿐 아니라 이전 결론에 묶이는 문제가 생긴다. 프로젝트도 archive 전체를 prompt에 넣지 않는 원칙을 갖고 있다. [P03–P04](EVIDENCE.md#project)

**우리 제안:** 아래 형태의 작고 역할별인 catalog를 만든다. 이는 후보 예시이며 이번 PR에서 skill을 설치한 것이 아니다.

| 후보 skill | 넣을 내용 | 넣지 않을 내용 |
|---|---|---|
| `source-verification` | 주장 종류, 1차 출처 찾기, 날짜/판본 기록, 접근 실패 처리 | 특정 과제의 정답·동료 초안 |
| `bounded-patch` | 허용 경로, diff 제한, 승인된 검사, rollback 조건 | 전체 저장소 쓰기 권한·임의 shell 허용 |
| `counterexample-review` | 가정·경계값·반례·미확인 사항을 확인하는 절차 | 의무적으로 반대하거나 합의를 강제하는 지시 |
| `evidence-synthesis` | 원 claim 연결, 반대 근거 보존, 검증 수준 표시 | 다수결을 진실로 승격하는 규칙 |

### 그대로 이식하지 않을 부분

Hermes 검색은 여러 위치에서 동일 이름이 나오면 first-wins 방식으로 선택하는 코드가 있다. 우리는 **source namespace + skill ID + revision/hash**로 구분하고 충돌 시 선택을 요구하거나 실패시킨다. 별도 프로젝트의 동명 skill이 현재 실행을 바꾸면 안 된다. 디렉터리 mtime/TTL cache는 편의 기능이지 실행 중 내용 불변의 증거가 아니다. [H03](EVIDENCE.md#h03)

시작할 때 승인된 skill 본문과 참조 목록의 hash를 manifest에 고정한다. 실행 중 새 버전을 발견해도 조용히 교체하지 않는다. 중요한 보안 수정으로 기존 판본을 중단해야 한다면 manifest를 폐기하고 새 실행으로 시작한다. catalog 자체가 거대해지면 이름 목록도 비용이 있으므로 작업/역할별로 좁힌다. 간단한 선택에 별도의 저가 LLM router를 의무적으로 추가하지 않는다.

**적용 접점:** v0.4 Context builder와 immutable evidence manifest. **수용 기준:** HP-04. 권한은 skill 문구가 아니라 controller/runner가 강제한다.

## 3. 경험에서 배우기: 자동 승격 대신 검토 가능한 변경

### 관측

README의 학습 루프와 skills 안내는 경험을 기억·절차 문서로 축적하는 접근을 강조한다. 이 경로에서 저장되는 것은 재사용 문서다. 이를 모델 가중치 재학습이나 우리 작업군에서 입증한 지속적 품질 개선으로 바꿔 설명하면 안 된다. [H01](EVIDENCE.md#h01), [H03](EVIDENCE.md#h03)

**우리 제안:** `실행 → 결과 검증 → lesson 후보 → skill 변경안 → 회귀/반례 시험 → 승인 → 다음 실행 사용`으로 바꾼다.

가령 ‘어떤 CLI 옵션을 함께 써야 독립 문맥이 된다’는 lesson은 help에 옵션이 있다는 사실만으로 게시하지 않는다. 해당 버전·호스트·허용 파일 양성 대조·금지 파일 접근 거절·MCP/shell 제한의 관측을 붙인다. 이미 V04-01 리뷰가 설정 성공과 권한 conformance를 구분했으므로 같은 원칙을 학습 경로에 적용하는 것이다. [P02](EVIDENCE.md#project)

| lesson의 내용 | 승격 조건 |
|---|---|
| 일반적인 절차 개선 | 재현 가능한 완료 결과, 관련 실패 사례, 적용 범위 |
| CLI/version별 우회 없는 사용법 | 공식 근거 + 해당 환경의 실제 conformance |
| 모델별 품질 선택 | 비교 과제/예산/평가 기준을 고정한 반복 관측 |
| 과거 정답·개별 claim | skill이 아니라 출처가 있는 evidence artifact로 보관 |
| 권한/과금 경로 변경 | 모델이 자동 게시하지 못함. 별도 사용자 결정과 재검증 |

실패한 스킬을 삭제해 흔적을 없애기보다 `revoked`로 남기고 어떤 실행에서 사용했는지 추적한다. 평가용 정답이나 동료 결과가 일반 스킬에 섞여 다음 blind 비교를 오염시키지 않게 한다. 게시된 버전을 바꾸어도 이미 실행 중인 참여자의 입력은 바꾸지 않는다.

**적용 접점:** 기존 review/실험 결과에서 절차만 추출하는 작은 catalog. **수용 기준:** HP-06. 초기 pilot 전에 자동 curator부터 만들지 않는다.

## 4. 기억: 유용한 사실과 독립성을 해치는 답안을 분리

### 관측

Hermes memory 문서는 제한된 MEMORY/USER 저장소, 세션 시작 시 고정 snapshot, 초과 시 명시적인 오류, 프로필 분리를 설명한다. 같은 home을 여러 writer가 공유하지 말라고 경고한다. tool을 호출해 실제로 저장하지 않은 ‘기억했다’는 답변은 persistence가 아니라는 점도 분명히 한다. [H04](EVIDENCE.md#h04)

### 우리 제안

기억을 단일 파일의 무차별 주입으로 취급하지 않고 다음처럼 구분한다.

| 저장 범위 | 독립 초안 단계의 기본 처리 |
|---|---|
| 사용자 확정 제약, 공통 과제 사실 | 출처·판본을 고정한 공통 pack으로 제공 |
| 일반 작업 절차 | 해당 실행에서 승인된 skill만 제공 |
| 참여자 자신의 해당 실행 기록 | 명시 resume 정책에서만 사용 |
| 동료 초안·과거 팀 합성 결론 | 봉인 해제 전 비공개. 평가 과제의 과거 답안도 별도 차단 |
| 사용자 일반 선호·다른 프로젝트 기억 | 자동 주입하지 않음. 필요성과 허용 범위를 별도 판단 |
| 토큰·인증·민감 원 trace | 모델 memory 및 Git 문서 대상이 아님 |

고정 snapshot의 장점은 실행 도중 자료가 바뀌지 않는다는 점이다. 그러나 **freeze는 내용이 올바르다는 증명도, 모든 native 전역 기억을 끈다는 증명도 아니다.** 실제 native CLI의 instruction/plugin/memory 로딩 경로를 관측하고 manifest에 conformance 상태를 기록해야 한다. HOME 하나를 바꾸는 것으로 인증 유지·문맥 격리가 동시에 해결된다고 가정하지 않는다. [H06](EVIDENCE.md#h06), [P02](EVIDENCE.md#project)

우선순위는 현재 사용자 지시와 해당 task manifest가 과거 memory보다 높도록 명시한다. 과거 설정을 이유로 현재 금지사항을 바꾸지 않는다. 모델이 ‘저장 완료’라고 말한 상태와, 저장소가 write·readback·digest 확인을 끝낸 상태를 UI에서 구별한다.

**적용 접점:** Context builder, V04-03 context conformance. **수용 기준:** HP-02/HP-05.

## 5. 세션 검색: 저렴한 찾기와 안전한 열람은 별개

### 관측

검토한 session search 코드는 DB 메시지를 대상으로 discovery/scroll/read/browse를 제공하며 별도 LLM 호출이 없다고 명시한다. lineage 중복, cron 순위, active/compacted 구분을 다룬다. `_shape_message`는 긴 메시지를 잘라 표시하고 원래 길이를 알려 준다. README/안내의 모든 표현이 현재 코드와 일치하지는 않는다. [H05](EVIDENCE.md#h05)

### 가져올 부분

원문을 찾을 때마다 모델에게 archive 전체를 요약시키지 않고, 먼저 식별자·소량의 검색 결과를 반환한 뒤 해당 원문 범위를 읽게 하는 구조다. 원래 저장된 메시지의 위치와 출처를 유지하는 편이 검증 가능한 회상에 맞다. SQLite 저장 문서에는 trigram/CJK 검색 경로도 나오지만, 한국어 검색 품질이 검증됐다는 뜻은 아니다. [H06](EVIDENCE.md#h06)

**우리 제안:** 검색 권한을 필터 UI에만 두지 않는다. query/discovery, 직접 artifact ID, scroll, lineage 확장, export 등 모든 접근 경로에 `project + run + actor + phase + visibility`를 적용한다. 가능하면 권한이 없는 자료는 ranking 전 후보에서 제외한다. 봉인된 원문이 snippet·제목·길이·cache hit·이전 압축 summary로 새어 나오지 않도록 부정 시험을 한다.

잘린 경우에는 `truncated`, 원문 위치, 다음 조회 방법을 함께 반환한다. 필요한 대목이 잘려 있으면 그 주장을 ‘확인됨’으로 올리지 않는다. 한국어 조사/어절 변화, 짧은 식별자, 코드 심볼, 같은 단어가 많은 cron 로그, 오래된 수정 전 문서로 test corpus를 만든다.

추가 검색 LLM 호출이 없어도 **결과를 읽는 native 모델의 입력 token과 시간은 발생한다**. 캐시·원문 크기·후속 조회를 포함해 측정한다. source 숨김 목록이나 BM25 순위 조정은 권한 제어의 대체물이 아니다.

**적용 접점:** 후속 EvidenceStore 검색 API. 초기에는 파일 ID 기반 열람만으로 시작 가능. **수용 기준:** HP-05.

## 6. Subagent: 작업 분리는 참고하되 blind 보증으로 오해하지 않기

### 코드에서 확인한 것

`_build_child_agent`는 fresh child와 task/session 식별, `skip_context_files=True`, `skip_memory=True`를 사용한다. 동시에 부모의 `prefill_messages`, task goal/context를 전달할 수 있고, child별 iteration budget을 새로 둔다. `_run_single_child`는 실패·중단·반복 상한을 구분하고 schema 확인/완료 이벤트 등의 경로를 갖는다. DB 파일은 공유하되 child 전용 handle을 열어 부모 생명주기 종료가 자식 기록을 끊지 않도록 하는 처리도 있다. [H07](EVIDENCE.md#h07)

### 가져올 부분과 바꿀 부분

| Hermes 패턴 | 우리에게 적용할 변경 |
|---|---|
| task/session별 구분 | `run/participant/attempt/epoch`를 분리하고 재시도마다 새 attempt 생성 |
| focused goal/context | controller가 만든 공통 pack만 P1 입력으로 사용. 부모의 해석·결론·prefill 상속 금지 |
| child 실패 사유 분리 | 출력이 존재해도 오류/상한/중단을 완료로 승격하지 않음 |
| parent 취소 전파 연결 | 취소 요청과 실제 종료 관측을 별도 상태로 유지 |
| child별 iteration budget | 전체 run의 호출 예약/회계 안에서 배정. 자식이 새 무제한 budget을 만들 수 없음 |
| 부모에게 summary 전달 | summary와 함께 불변 초안·근거·실패 원문의 ID를 보관. 요약만으로 검증하지 않음 |
| parent-child DB handle ownership | 실행/저장 핸들 소유권을 명시하고 종료 순서·late event 시험 |

새 conversation이더라도 같은 파일을 읽거나 부모 답안을 prefill로 받으면 독립성이 깨진다. 반대로 코드에 `skip_memory`가 있으므로 Hermes가 기억 격리를 전혀 고려하지 않았다고 평가해서도 안 된다. 이 보고서의 판단은 ‘불충분한 제품’이라는 일반 평가가 아니라 **우리의 독립 교차검증 계약에 맞추려면 추가 경계가 필요하다**는 것이다.

**적용 접점:** deterministic scheduler와 native adapters. **수용 기준:** HP-01/HP-02/HP-03.

## 7. Native Codex bridge: 가장 구체적인 실행기 참고점

### 관측

`CodexAppServerClient`는 `codex app-server`를 argv 배열로 실행하고 stdio JSON-RPC·초기 handshake·응답/notification/server request·stderr reader를 나눈다. session adapter는 native thread/turn과 승인·취소·재개를 다루며, 명시적으로 다른 thread/turn의 알림을 배제하는 함수를 갖는다. [H08–H09](EVIDENCE.md#h08)

### 지금 참고할 설계

첫째, shell 문자열 조립이 아니라 고정 executable과 argv 배열을 사용한다. **exec one-shot에서 입력 작성 후 stdin을 닫는 것과, 지속 연결인 App Server의 stdio를 매 요청마다 닫지 않는 것은 구분해야 한다.** 같은 runner 계약을 공유하되 전송 수명주기는 adapter별로 다르다.

둘째, stdout의 구조화 이벤트와 stderr의 진단 로그를 섞지 않는다. 코드의 auth 분류가 본 요청 실패와 주변 plugin stderr를 구분하는 이유도 여기에 있다. stderr에 인증 관련 단어가 있다는 이유만으로 해당 작업의 인증 실패라고 판정하지 않는다. 비밀 값은 진단을 저장하기 전에 가린다. [H08](EVIDENCE.md#h08)

셋째, 프로세스 정리는 부모 PID만 죽이는 것으로 끝내지 않는다. Hermes client는 부모가 사라지기 전에 descendants를 snapshot하고 뒤에서 정리한다. 그러나 snapshot helper가 실패하거나 `psutil`이 없으면 비어 있을 수 있으므로 그 코드만으로 전부 종료됐다고 선언할 수 없다. Windows에서도 우리 소유 프로세스만 추적·종료하고, 확인할 수 없으면 UNKNOWN으로 남겨야 한다. [H09](EVIDENCE.md#h09)

### 그대로 복사하면 충돌하는 부분

session adapter의 기본 권한 매핑에는 workspace-write가 있고 표식 없는 이벤트는 호환성을 위해 받아들이는 분기가 있다. 우리 논의자는 read-only conformance를 먼저 만족해야 한다. 연결/스폰 소유권으로 신뢰할 수 있게 scope를 결합한 경우와, 여러 실행의 무표식 이벤트를 임의로 현재 작업에 붙이는 경우를 구분해야 한다. 후자는 격리하거나 오류 처리한다. [H08](EVIDENCE.md#h08)

transport 환경 helper는 provider credential 상속을 허용한다. 우리의 구독-only pilot은 인증 소유권을 native CLI에 남기고, 과금 경로를 바꿀 수 있는 변수·다른 도구 비밀을 넣지 않는 최소 환경을 버전별로 확인해야 한다. 무작정 환경 전체를 지워 실행이 안 되는 상태도 성공으로 간주하지 않는다. [H09–H10](EVIDENCE.md#h09)

**판정:** 오류 분류와 수명주기 패턴은 지금 exec runner 설계에 참고. App Server 자체는 HP-10 후속 선택 전송. 기존 Q1을 다시 열지 않는다.

## 8. MoA: 참고할 협업 편의 기능과 유지해야 할 검증 규칙

### 관측

Hermes MoA는 reference 모델들의 조언을 aggregator에 주고, aggregator가 실제 응답과 도구 루프를 수행하는 selectable provider/preset이다. 문서와 config는 `user_turn`을 기본 조언 주기로 설명한다. per_iteration/every_n도 표현한다. reference별 사용량·rate 출처를 기록하는 코드와, 일부 reference 실패를 표시하는 구조가 있다. [H11–H12](EVIDENCE.md#h11)

### 우리 프로젝트와 다른 지점

**가장 큰 차이는 ‘여러 모델이 관여함’과 ‘독립 결과가 검증됨’의 차이**다. 합성자가 여러 의견을 보았다는 사실만으로 공통 자료의 동등성·독립 초안·주장별 외부 확인·미합의 보존이 증명되지는 않는다. 우리의 네 모드와 P0–P5를 이 virtual provider 하나로 감추지 않는다. [P04](EVIDENCE.md#project)

reference에게 전달하는 자료도 확인해야 한다. 안내는 user/assistant text 중심으로 설명하지만 검토한 코드에는 조언용 tool-result preview 예산과 주석이 있다. 전체 payload builder를 실행 확인한 것이 아니므로 정확한 입력은 미확인으로 둔다. **같은 질문 문자열을 전달했다고 같은 자료로 독립 실험했다고 쓰지 않는다.** [H11–H12](EVIDENCE.md#h11)

### 선별할 기능

역할 슬롯을 이름으로 저장하고, 조언 호출 주기를 명시하며, 실제 도구 실행자와 비용 부담 경로를 화면에서 구분하는 편의는 유용하다. 다만 우리 기본은 승인된 역할·구독 route의 명시적 조합이다. 기존 main 모델이 구독이라고 해서 외부 aggregator의 비용까지 그 구독에 포함된다고 추정하지 않는다.

실패한 reference를 빼고 계속하는 처리는 사전 승인된 구성 축소 정책·정족수·단계와 연결한다. 초안 공개 후 새 참여자를 끼워 넣고 ‘독립 초안’으로 취급하지 않는다. 합성자가 실패한 경우도 조용히 다른 모델로 바꾸지 않는다. invalid 설정을 싼 기본값으로 보정하는 방식보다, 우리 실행 설정은 사전 검증에서 거절하는 편이 적합하다. [P02](EVIDENCE.md#project), [H12](EVIDENCE.md#h12)

### 성과 해석

HermesBench 표는 제작자의 특정 구성 자체 보고다. 같은 총비용의 강한 단독 모델, 추가 자기검토, 여러 독립 답변 중 선택과 비교한 우리 실험이 아니다. ‘여러 관점이 유용할 수 있다’는 실험 동기로만 쓰고 우리 예상 개선률로 옮기지 않는다. [H11](EVIDENCE.md#h11)

**판정:** HP-08에서 역할/주기/회계 패턴만 실험. v0.4 프로토콜을 대체하지 않음.

## 9. Context compression: native 문맥과 근거 원장을 혼동하지 않기

### 관측

Hermes는 ContextEngine 인터페이스와 lossy compressor, gateway 사전 처리 및 agent 내부 압축을 설명한다. usage anchor는 provider 보고량과 이후 메시지의 추정을 결합한다. 반복 실패 cooldown과 제한된 overflow 복구도 존재한다고 안내한다. [H13](EVIDENCE.md#h13)

**우리 제안:** controller가 native CLI의 비공개 내부 문맥을 다시 구성·압축하지 않는다. native는 자신의 실행 대화를 관리하고, controller는 별도로 **원문 자료·초안·claim·반례·검증 결과**를 불변 artifact로 가진다. 모델에게 전달하는 digest는 검색/탐색용 projection이다.

압축 후에도 보존할 것은 결론만이 아니다. 적용 조건, 숫자의 단위·분모, source revision, 미확인 상태, 가장 강한 반례, 다음 조회할 원문 위치를 명시한다. 누락되면 검증된 결론으로 내보내지 않는다. digest를 새로 만들더라도 원문 hash와 어떤 자료에서 만들었는지를 남긴다.

압축 실패 때 같은 호출을 계속 반복하거나 고정 fallback 문구만 남겨 사실상 근거를 버리는 경로는 피한다. 요약 비용·실패 호출도 전체 run에 포함한다. 모델이 다르면 token 추정·cache 동작도 같다고 보지 않으며 Hermes의 threshold 숫자를 최적값으로 복사하지 않는다.

**판정:** 안정된 prefix, 출처가 붙은 관측량, 한정 복구라는 원칙을 참고한다. 별도 compressor/LCM plugin 전체는 현재 보류. HP-02/HP-03/HP-05의 불변 artifact와 누락 검사가 먼저다.

## 10. 세션 저장·재개: 기록 보존과 동작 재실행을 분리

### 관측

저장 문서는 profile별 SQLite/WAL/FTS, parent lineage, compaction generation, 모델별 usage, outbox 역할의 delivery obligation을 설명한다. accepted input과 native echo를 중복으로 기록하지 않는 소유권 처리는 동일 텍스트를 무조건 지우는 것과 다르다. 원문도 이를 universal exactly-once로 주장하지 않는다. [H06](EVIDENCE.md#h06)

**우리 제안:** 초기에는 저장 파일과 append-only journal로 필요한 계약을 시험한다. artifact 본문을 원자적으로 기록·검증한 다음 journal에 참조를 남긴다. crash로 생긴 미참조 artifact와 본문 없는 journal entry는 복구 시 따로 처리한다. 이는 모든 filesystem에 분산 transaction이 있다는 선언이 아니다. 동시 읽기·검색·복구 요구가 생기면 SQLite를 index/projection부터 추가한다.

| 이름 | 우리 의미 | 자동으로 해서는 안 되는 것 |
|---|---|---|
| reconnect | 기존 실행과 연결을 다시 확인 | 새 모델 호출을 시작한 것처럼 처리 |
| resume | 같은 native session/thread를 확인하고 이어감 | 다른 thread가 왔는데 같은 실행이라고 표시 |
| retry | 새 attempt와 예산 예약으로 다시 호출 | 기존 비용을 없애거나 이전 output 덮어쓰기 |
| replay | 저장된 이벤트로 화면/상태를 재구성 | 외부 도구의 부작용까지 다시 실행 |
| fork | 새 실행 관계를 명시적으로 만듦 | peer를 본 fork를 blind 초안으로 분류 |

모든 결과는 ‘저장 성공’, ‘프로세스 종료’, ‘요청된 작업 완료’, ‘근거 검증’을 분리한다. hash는 무결성 확인 수단이지 내용이 참이라는 증명이나 접근권한이 아니다. 내부 native reasoning payload를 다른 provider 형식으로 옮겨 저장하거나 공유하지 않는다.

**적용 접점:** controller journal/evidence store, 후속 HP-09. Hermes의 DB schema 전체를 먼저 이식하지 않는다.

## 11. MCP·보안·과금: 편의가 권한을 넓히지 않게

### MCP 카탈로그에서 가져올 것

연결 카드에서 인증 성공과 도구 발견 실패를 구분하고, 어떤 서버/명령/설치 원문/도구를 쓰는지 보여 주는 방식은 adapter inventory에도 유용하다. 하지만 Hermes 문서에는 default 선택이 없으면 모든 도구를 허용하는 구성과 exclude-only의 새 도구 허용 가능성도 나온다. 설치 자체가 bootstrap 코드를 실행할 수 있다는 trust 경계도 설명한다. [H15](EVIDENCE.md#h15)

**우리 제안:** read-only discussant에는 명시 allowlist, schema digest, 서버/transport revision, 허용 자원 범위를 고정한다. 발견 실패는 설치/인증 성공과 별개이며 `eligible_for_run`으로 승격하지 않는다. 서버가 도구를 추가하거나 schema가 바뀌면 재승인/재검증한다. 도구 이름과 description만 보고 실제 read-only라고 신뢰하지 않는다. 모델이 요청한 `allowed_tools` 필드가 자체 권한을 만들게 하지 않는다.

### 보안 정책에서 가져올 것

headless 승인 timeout을 거절로 처리하고, shell 패턴 검사와 OS sandbox를 구분하는 원칙은 맞는다. 반면 smart approval은 보조 LLM 평가를 사용할 수 있다. 우리 제어 계층에서 모델 분류는 설명/검토 보조일 뿐, capability 제한·사용자 승인·비용 상한을 뒤집는 최종 권한이 되어서는 안 된다. [H14](EVIDENCE.md#h14)

승인은 작업 종류만이 아니라 target·scope·attempt·유효기간·config revision에 묶는다. 취소되거나 다른 실행에 속한 승인 응답을 재사용하지 않는다. native/OS에서 실제로 차단되는지 conformance로 확인한다. 패턴 스캔만 통과한 tool description, skill, 외부 문서를 신뢰된 시스템 지시로 승격하지 않는다.

### 과금과 자격증명에서 가져올 것

provider/model/route를 분리하고 사용량 출처를 남기는 구조는 좋다. 하지만 provider resolver·보조 모델·fallback이 원래 선택과 다른 경로를 사용할 수 있는 제품의 편의를 우리 기본 정책으로 옮기지 않는다. [H10–H12](EVIDENCE.md#h10)

**우리 제안:** 실행 전 funding profile을 확인하고, 보조 요약·skill 생성·추가 검토·실패 재시도까지 같은 예산 장부에 넣는다. 사용량 값이 없으면 unknown으로 남긴다. API 가격표를 대입한 추정 금액을 구독 청구액으로 표시하지 않는다. 구독 CLI가 사용할 수 없으면 해당 provider를 제외하거나 BLOCKED로 보고하며, 대체 구성은 사용자 정책에 따라 명시한다.

**수용 기준:** HP-03/HP-07. 연결 완료·인증 완료·문맥 적합·권한 적합·실행 적격은 별도 상태다.

## 12. UI: 기존 Ledger에 연결하고 Hermes 외형은 복제하지 않기

Hermes의 native session/result, MCP 연결 상태, MoA의 실제 실행 모델 표시에서 읽을 수 있는 교훈은 **상태의 의미를 나누는 것**이다. 이번 조사에서 데스크톱 화면을 렌더링하거나 사용성 평가를 한 것은 아니다. UI 권고는 source와 문서의 상태 구조에 근거한 제안이다. [H08](EVIDENCE.md#h08), [H11](EVIDENCE.md#h11), [H15](EVIDENCE.md#h15)

우리 `review_boundary.py`는 이미 이벤트 세대/순서, terminal 불변, UNKNOWN 예산 점유, 봉인된 allowlist 투영, 계정 한도 관측/만료를 나눈다. 이를 버리고 새로운 상태 표시 시스템부터 만들 필요가 없다. 입력은 신뢰된 adapter 관측이어야 한다는 기존 경고를 유지한다. [P05–P06](EVIDENCE.md#project)

**우리 제안:** 기본 화면에는 구성·제출 상태·승인 대기·중단/UNKNOWN·최종 확인이 필요한 쟁점만 둔다. 필요할 때 실행·도구·근거 상세를 펼친다. 봉인 중에는 다른 참여자의 답안 preview뿐 아니라 길이·token·원문 경로도 노출하지 않는다. 로컬 사용량과 계정 전체 잔량을 합치지 않는다. 상태 색을 계산하려고 LLM을 별도로 호출하지 않는다.

실제 design source나 Claude 아티팩트는 이번 PR에서 바꾸지 않는다. 첫 화면의 결정 우선/대조표 우선에 대한 열린 결정을 Hermes UI라는 이유로 닫지 않는다.

## 13. 현재 보류할 기능과 재검토 조건

| 기능군 | 보류 이유 | 다시 볼 조건 |
|---|---|---|
| Hermes 전체 AIAgent/도구 loop | native loop와 controller 책임이 겹침 | 별도 Hermes worker가 필요한 명확한 과제와 독립 계약이 있을 때 |
| 무인 skill/memory 자동 갱신 | 잘못된 성공 경험·과거 답안이 다음 실행을 오염 | 후보/승인/rollback·회귀 평가가 먼저 갖춰질 때 |
| 외부 사용자 모델링/Honcho | blind·개인정보 범위와 외부 전송 비용이 달라짐 | 목적/데이터 경계/동의/삭제 정책이 구체화될 때 |
| messaging gateway/상시 cron | 인증·중복 전달·중단·예산·운영면을 늘림 | 안정된 수동 pilot 뒤 실제 반복 요구가 생길 때 |
| 다수 terminal/backend 전체 | 초기 Windows native CLI pilot의 범위를 크게 벗어남 | 원격 실행/OS 격리 등 특정 backend 필요가 관측될 때 |
| execute-code/RPC 파이프라인 | 도구 효율과 별개로 임의 코드·권한 경계 추가 | 제한된 trusted runner로 해결 안 되는 측정된 병목이 있을 때 |
| RL/trajectory 도구 전체 | 현재 orchestration 수용 기준과 별도 과제 | 재현 가능한 평가·데이터 권리·학습 목적을 정할 때 |

이 기능군의 존재는 README/architecture 문서 수준에서 확인했으며 내부를 전수 검토하지 않았다. ‘가치가 없다’가 아니라 ‘지금 비용과 위험을 감수할 근거가 부족하다’는 프로젝트 순서 판단이다. [H01–H02](EVIDENCE.md#h01)

## 14. 최종 판단

**먼저 실행을 신뢰할 수 있게 만들고, 다음으로 문맥을 덜 읽게 만들며, 마지막으로 검증된 경험만 재사용한다.** 이것이 Hermes에서 가져올 가치와 우리 프로젝트의 원칙을 함께 살리는 순서다.

실제 다음 변경은 [ADOPTION_PLAN](ADOPTION_PLAN.md)의 mock/native gate를 충족하는 작은 작업이어야 한다. 이 문서를 읽었다는 이유로 provider 연결 성공·독립성·품질 향상·안전한 자동 실행이 이미 검증됐다고 쓰지 않는다.
