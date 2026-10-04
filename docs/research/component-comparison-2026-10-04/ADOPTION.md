# 우리 코드에 넣기 위한 부품별 적용 설계

이 문서는 구현 전 설계 후보다. 새 API·테이블·파일명이 등장하면 **제안**이며 이미 존재하는 기능이 아니다. 현재 앱은 [memory](../../../app/memory.py), [controller](../../../app/controller.py), [store](../../../app/store.py), [server](../../../app/server.py), [화면](../../../app/static/index.html), [report](../../../app/report.py)를 기준으로 검토했다.

현재 동작: 동일 task의 취소되지 않은 공개 단계 실행 중 최신 후보를 고르고, 질문 단어/한국어 2-gram과 최신순으로 정렬한다. 검토·처분을 답변보다 먼저 싣고, 답변 hash와 UTF-8 크기를 확인한 pack을 고정한다. 일반 팀원·상위 역할은 자동 기억을 쓰며 격리 팀원 초안에는 붙이지 않는다. 이 기반을 폐기하고 외부 서버부터 설치할 이유는 아직 없다.

## 선택 지도

| ID | 사용자에게 보이는 변화 | 참고 부품 | 재사용 방식 | 모델 호출/추가 운영 |
|---|---|---|---|---|
| D01 | “왜 이 기억을 골랐지?” 서랍 | Anchor rank evidence + Peek provenance | 현재 pack에 설명 projection | 없음 |
| D02 | 이전 질문·답·검토를 검색해 원문 열기 | Hermes/WorkTrail FTS + Peek freshness | SQLite 검색 인덱스 독자 구현 | 없음, 인덱스 버전 관리 |
| D03 | 현재 결정·남은 문제·다음 행동 한눈에 | WorkTrail state + Anchor history | 기존 원장 projection와 명시 선언 | 기본 없음 |
| D04 | 기억 핀·제외·교체·변경 이력 | Anchor lifecycle + Hermes matched entry | 별도 사용자 설정/수정 이벤트 | 없음 |
| D05 | 무관한 기억 줄이고 검색 개선 근거 남기기 | Anchor metrics/RRF + Peek exact seeds | 평가 fixture·선택기 독자 구현 | 오프라인은 없음 |
| D06 | 작업 간 기억을 골라 공유·이동 | Anchor scope/transfer | 선택 bundle과 명시 import | 없음, 포맷 관리 |
| D07 | 자주 쓰는 팀·작업·자료 양식 저장 | Hermes skills + curator | 버전 있는 템플릿 | 기본 없음 |
| D08 | 충돌하는 결정 후보를 모아 비교 | Anchor contradiction + 우리 unresolved | 충돌 후보함, 사용자 처분 | 구조 비교는 없음, 의미 비교 별도 |
| D09 | 완료/대기 알림·인덱싱 재시도 상태 | Anchor outbox + 현재 controller | 필요 작업만 durable queue | 없음, worker 수명 관리 |
| D10 | 의미 검색·회고·그래프를 선택적으로 확장 | Anchor embedding/reflect/relations | 독립 실험 후 모듈 또는 외부 서비스 | 기능별 모델/패키지/서버 비용 |

## D01. 선택 이유와 실제 입력 미리보기

**사용 흐름:** 실행 준비 → “이전 작업 기억” 열기 → 각 항목의 날짜·원문·선택 이유·포함 부분 확인 → 그 고정 입력으로 실행. 현재 자동 기억 기본값은 유지한다.

제안 설명 레코드는 `source_run_id`, `source_hash`, `reason_codes`, `overlap_terms`, `recency_rank`, `included_sections`, `excluded_reason`, `selected_bytes`다. 점수를 정확도 백분율로 보여주지 않는다. `reason_codes` 예시는 `same_task`, `query_overlap`, `recent_fallback`, `user_pinned`이며 마지막 값은 D04를 구현한 뒤에만 생긴다.

`app/memory.py`에서 후보 평가 이유를 pack 본문과 분리해 만들고, controller의 확인 명세에 설명과 실제 pack hash를 함께 묶는다. 화면·report는 이 고정 결과만 렌더링한다. 설명 UI 때문에 원문이 모델 prompt에 두 번 붙거나 격리 초안에 새로 섞이지 않게 한다.

**작은 시험/완료:** 한국어 질문에서 일치 단어를 정확히 표시하고, 같은 입력에 순서가 재현되며, 0점 최신 선택은 그렇게 표시한다. 크기 때문에 탈락한 내용과 실제 footer 바이트가 일치한다. 미리보기 후 원문 변경 시 예전 확인 명세로 새 내용을 실행하지 않는다. 모의 일반/격리 실행으로 입력 차이를 확인한다. 서버·모델 추가 없이 클라우드에서 완료 가능하다.

## D02. 원문 검색과 최신성

**사용 흐름:** 검색창 → 작업/기간/자료 종류 필터 → snippet → 원문 위치 → 선택하면 다음 실행 자료로 추가. 조회만 한 기록은 첨부 원장에 쓰지 않는다.

제안 검색 행은 `task_id`, `run_id`, `section_kind`, `source_hash`, `extractor_version`, `offset_or_locator`, `text`다. 대상은 공개 질문·답변·검토·처분이며 비공개 진행 중 초안은 제외한다. FTS5가 없는 SQLite 환경에서는 지원 상태와 제한된 대체 검색을 명시한다. 제목 검색만으로 답변 본문 검색을 했다고 하지 않는다.

`app/store.py`의 기존 DB migration 방식을 따라 파생 인덱스를 추가하고, `app/report.py`의 원문 참조를 재사용한다. 검색 모듈은 controller의 실행 생성과 분리하고 `app/server.py`에 읽기 endpoint를 붙일 수 있다. 원문 hash 또는 추출기 버전이 바뀌면 stale 표시/재구축 대상으로 삼는다. HTML snippet은 escaping하고 query는 SQL 인자로 처리한다.

**작은 시험/완료:** 한글 조사·숫자·파일 경로·코드 backtick, 오래된 실행, 빈 질의, 삭제/손상 원문, 다른 task 필터를 포함한다. 검색 결과를 클릭하면 같은 hash의 실제 원문이 열린다. 인덱스를 버리고 다시 만들 수 있고 원장 원본은 그대로 남는다. Hermes의 discover→read와 Peek의 freshness가 한 흐름으로 결합되는 후보다.

## D03. 작업 복귀 요약과 결정 이력

**사용 흐름:** 작업을 다시 열면 현재 결정, 미해결 문제, 다음 행동/담당, 근거 실행이 보인다. “왜 바뀌었지?”를 누르면 이전 결정과 변경 이유를 본다.

제안 이벤트는 `kind: decision|constraint|ruled_out|next_action`, `author_kind: user|agent`, `text`, `evidence_refs`, `supersedes_id`, `scope`, `created_at`다. 사용자 확인 여부는 독립 필드로 둔다. 모델 답변·합성 결과를 읽었다고 자동으로 확인된 결정으로 승격하지 않는다. 기존 검토 disposition에서 파생할 수 있는 사실은 새로 모델에게 요약시키지 않는다.

`app/store.py`와 controller에 명시 선언/교체 이벤트를 추가하고, report와 화면에서 현재 projection과 이력을 함께 표시한다. GitHub 카드의 상태·담당을 다른 DB에서 제멋대로 덮어쓰지 않고 링크·참조로 시작한다.

**작은 시험/완료:** A결정→B로 교체→B 보류, 동시 선언, 근거 누락, 다음 담당 미정 시 projection이 원문보다 강한 결론을 만들지 않는다. supersedes 순환은 거절한다. “현재 선언 없음”도 정상 결과로 보여준다. 자동 요약을 나중에 더한다면 원문/초안/사용자 확인을 따로 보존한다.

## D04. 기억 관리: 핀·제외·수정·되돌리기

**사용 흐름:** 기억 서랍에서 다음 실행에 자주 쓸 항목을 pin, 특정 항목을 자동 선택에서 제외, 새 결정으로 교체, 변경 이유 확인. 과거 실행 기록을 직접 고치지 않는다.

현재 pack은 실행 기록에서 만들어지므로, 우선 `memory_preferences` 같은 별도 선택 정책을 제안한다. 필드는 `task_id`, `source_run_id`, `source_hash`, `pinned`, `excluded`, `note`, `version`이다. D03의 구조화 결정 본문을 편집할 때도 원본 이벤트는 두고 교체 이벤트를 쌓는다.

Hermes의 matched-entry 패턴을 적용해 화면이 읽은 `expected_version/hash`가 현재와 같은지 확인한다. pin도 전체 크기 상한과 격리 역할 제외를 우회하지 못한다. 우선순위 제안은 **범위·주입 자격 → 사용자 제외 → pin → 관련성/최신순 → 예산**이다. pin이 넘치면 조용히 무한 삽입하지 않고 누락 이유를 보여준다.

**작은 시험/완료:** 두 창에서 동시에 수정, 제외+pin 충돌, 삭제된 원문, 초과 pin, 되돌리기 이후 새 실행을 비교한다. 이전 실행의 입력 hash는 변하지 않는다. 처음에는 숨김/보관을 제공하고 자동 영구 삭제는 별도 필요가 생길 때 고른다.

## D05. 검색 평가와 단계적 개선

**사용 흐름:** 기억 항목에 “도움 됨/무관함”을 표시하거나 검색 실패를 남긴다. 개발자는 같은 질의셋으로 후보 선택기를 비교한다. 이 표시만으로 기억의 진실성을 바꾸지 않는다.

먼저 합성·허용된 비식별 자료로 질의, 관련 원문 ID, 제외해야 할 distractor, task, 크기 예산을 가진 fixture를 만든다. baseline은 현재 `app/memory.py` 그대로다. 후보 실험을 분리한다: (a) zero-overlap fallback 유지/비우기, (b) 오래된 관련 실행을 포함한 후보 범위, (c) 본문/검토 검색, (d) identifier exact 채널, (e) 한국어 형태소, (f) 여러 채널을 얻은 뒤에만 RRF. 모두 한 번에 바꾸지 않는다.

지표는 hit@k, reciprocal rank, distractor가 정답보다 위인지, 중복, 선택 바이트, 제한 초과, 다른 task 유입, 결정성이다. paired bootstrap은 같은 질의끼리 비교하고, 표본이 작거나 정답 라벨이 불확실하면 그 사실을 결과에 쓴다. 합성셋 이득만으로 실사용 품질을 주장하지 않는다.

**수정 위치/완료:** 평가 도구와 fixture는 실행기와 분리하고, 채택한 알고리즘만 memory 모듈에 들어간다. 실제 정답셋에서 더 좋아지는지 확인하기 전 후보 값을 기본 설정으로 바꾸지 않는다. 이번 기록의 `probes.mjs`는 upstream 경계 확인용이라 이 평가셋을 대신하지 않는다.

## D06. 명시적 공유와 이동 가능한 기억 묶음

**사용 흐름:** 선택한 결정/절차/실행을 export → 대상 작업에서 목록·출처·크기를 미리 보고 import → 새 원본 참조와 가져온 출처를 확인. 전역 자동 기억 확대와는 별도 기능이다.

제안 bundle은 `format_version`, `source_project`, `exported_at`, `items`, `relations`, `hashes`다. import 미리보기는 `new/duplicate/conflict/rejected`를 구별하고, 같은 ID에 다른 본문이면 조용히 덮어쓰지 않는다. 파일 경로를 따라 임의 파일을 읽거나 자동 실행하는 포맷으로 만들지 않는다. 외부 출처를 사용자가 보게 한 뒤 주입 가능 여부를 결정한다.

`app/report.py`의 근거/원문 내보내기와 store의 명시 import를 연결한다. AnchorMind의 workspace+global 기본값을 복사하지 않고 `target_task`를 필수로 한다. 논리 bundle은 CLI 인증·원장 전체 백업과 다르다고 표시한다.

**작은 시험/완료:** 왕복 보존, Unicode/hash, 중복, 손상, 부분 실패, 누락된 relation endpoint, 최신 포맷 거절을 확인한다. 우리 첫 dry-run은 쓰기 없는 계획 생성으로 만들 수 있다. AnchorMind의 DB rollback 방식이 필수는 아니다.

## D07. 팀·작업 양식과 스킬 서랍

**사용 흐름:** “문서 검토”, “반례 찾기”, “개발 설계” 같은 저장된 양식 선택 → 역할·자료·출력 예시 확인 → 이번 입력에 맞게 수정 → 실행 확인. 목록에는 짧은 설명만 보이고 선택하면 본문과 자료를 펼친다.

제안 template은 `id`, `version`, `name`, `description`, `roles`, `source_slots`, `output_contract`, `skill_refs`, `pinned`, `last_used_at`다. 인증값·기기별 CLI 관측 기록은 템플릿에 넣지 않는다. 템플릿을 선택한 뒤에도 현재 controller의 실행 가능성·호출 상한 검사를 거친다.

첫 구현은 `app/static/index.html`의 현재 역할 설정 저장/불러오기와 controller 확인 명세의 버전 기록으로 충분하다. 스킬은 명시 선택한 본문·hash만 고정하고, 셸 전처리나 플러그인 설치는 별도 기능으로 분리한다. curator의 수명 분류를 써 “최근 안 쓴 양식” 정리 제안을 만들되 pin·다른 양식 참조는 보호한다.

**작은 시험/완료:** 삭제/비활성 역할이 든 오래된 양식, 바뀐 스킬 본문, missing source slot, pin 보호, 양식 수정 후 과거 실행 재조회. 스킬을 선택했다고 읽지 않은 파일 전체를 prompt에 넣지 않는다. 대부분 UI·데이터 작업으로 클라우드에서 가능하다.

## D08. 결정 충돌함

**사용 흐름:** 같은 대상을 다르게 정한 기록을 나란히 보고, 둘 다 유지/새 결정으로 교체/범위가 다름/판단 보류 중 선택한다. 원문 근거와 처분 이유를 남긴다.

제안 conflict는 `left_ref`, `right_ref`, `detector`, `reason`, `status`, `resolution_event`다. 구조화 결정의 같은 subject/property와 반대 값부터 찾을 수 있다. 자연어 모순 탐지는 별도 모델 후보이며, 그 점수만으로 자동 삭제·fact 승격을 하지 않는다.

`app/cross_review.py`의 unresolved와 disposition 의미를 재사용할 수 있지만, “검토 지적에 대한 처분”과 “서로 다른 시점의 결정 충돌”은 다른 객체다. UI 표현과 공통 evidence 참조를 공유하고 한 테이블에 의미를 섞지 않는다.

**작은 시험/완료:** 서로 다른 기간/범위의 값, 실제 모순, 단순 표현 차이, 근거 손상, 순환 교체를 포함한다. 모델 실험에는 별도 호출 ledger/cap과 구독 CLI가 필요하다. 오프라인 구조 규칙·화면은 먼저 만들 수 있다.

## D09. 필요한 백그라운드 작업만 관리하기

**사용 흐름:** 결과 준비·사용자 입력 대기·검색 인덱스 실패가 한 수신함에 보이고, 실패 작업은 이유를 보고 재시도한다. 다른 앱에 알림을 보내는 연동은 별도 선택이다.

추가 큐가 필요할 때 제안하는 job 필드는 `job_id`, `kind`, `payload_hash`, `dedup_key`, `status`, `attempts`, `next_attempt_at`, `lease_token`, `last_error`다. SQLite에는 PostgreSQL `SKIP LOCKED`를 그대로 옮기지 않고 현재 store의 트랜잭션 방식에 맞춘다. handler timeout이 부작용 취소를 보장하지 않으므로 멱등 처리를 먼저 정한다.

기존 controller가 이미 관리하는 CLI 실행 상태를 다른 큐로 다시 관리하지 않는다. D02 인덱싱·앱 내 알림처럼 부수 작업부터 사용한다. 모델 작업을 큐에 넣는다면 기존 호출 상한/원장·whole-tree 종료 계약을 그대로 거친다.

**작은 시험/완료:** 같은 이벤트 두 번, 처리 도중 종료/재시작, 오래된 lease의 완료 통지, dead 상태, 사용자가 눌러 재시도하는 경우. 서버 수명과 worker 정리도 함께 확인한다. 외부 서비스나 글로벌 Stop 훅은 첫 적용의 필수가 아니다.

## D10. 규모가 커질 때 선택하는 확장

| 확장 | 먼저 풀어야 할 구체적 불편 | 최소 실험 | 결정 기준 |
|---|---|---|---|
| 임베딩/재순위 | 같은 뜻 다른 표현을 lexical로 놓침 | D05 정답셋에 lexical vs local embedding 비교 | 검색 이득, 설치/메모리·지연, source freshness |
| 생성 질문 인덱스 | 본문 표현과 실제 질문 간격이 큼 | 원본 일부에서 질문 생성, 원문 anchor 보존, holdout 비교 | 검색 이득과 생성 호출·갱신 비용 |
| 자동 회고 | 사용자 확인할 후보 정리가 반복 부담 | 제한된 실행에서 결정/절차 후보 생성 후 확인 | 누락·환각·검토 시간, 새 호출 상한 |
| 관계 그래프 | 결정 간 근거·교체 관계를 자주 탐색 | D03의 명시 relation만 작은 그래프로 표시 | timeline보다 실제 탐색이 쉬운가 |
| 자동 수명 정리 | 오래된 중복 기억이 선택을 방해 | archive 제안만 만들고 원문 유지 | 잘못 제외한 중요 기록, 복구 가능성 |
| 외부 AnchorMind 연결 | 여러 클라이언트가 공통 기억 서버를 필요로 함 | 별도 fixture workspace에서 remember/recall/amend/export 왕복 | PostgreSQL·Redis·worker 운영 가치, 경계/실패 계약 |

우선 설치하지 않는 것은 기능을 버린다는 뜻이 아니다. 필요가 생기면 이 표에서 실험을 시작한다. 외부 모델 단계는 egress 허용과 구독 과금 조건을 별도로 확인하고, 공급자 fallback이 유료 API로 자동 전환되지 않게 우리 계약을 적용한다.

## 실제 코드를 가져오는 선택과 설계만 참고하는 선택

| 원본 | 작은 재사용 후보 | 우리 기본 제안 | 코드 복사 시 확인 |
|---|---|---|---|
| AnchorMind / Apache-2.0 | RankFusion, WorkspaceScope, ContextTrust, PairedBootstrap의 분리 방식 | Python/SQLite 계약으로 독자 구현. JS 그대로 유지할 때만 모듈 이식 검토 | 대상 파일과 종속물 license, 저작권·고지·변경 표시, NOTICE 존재/요구 확인 |
| Hermes / MIT | frozen snapshot, matched entry, skill progressive loading, curator 보호 조건 | 현재 manifest·화면에 패턴 적용 | 복사한 실질 코드의 저작권/허가문 보존, 종속 파일 조건 |
| codex-peek / MIT | exact seed, deterministic tie-break, baseline/evidence 구분 | 원본 fingerprint와 검색 이유 계약에 적용 | 같은 고지 보존, bridge 종속성/부작용 분리 |
| WorkTrail / FSL-1.1-ALv2 | state/evidence/supersedes 개념과 작업 복귀 UX | 독자 설계·직접 코드 복사 후보에서 제외 | 사용 목적/해당 버전의 허용 범위와 전환 조건 별도 검토 |

이번 연구 probe는 설치된 upstream 경로를 import하는 자체 작성 호출 코드이며 원본 제품 코드를 vendoring하지 않았다. 라이선스 표는 루트 파일 관측이며 종속 패키지 전체 허가 검토를 대신하지 않는다.

## 다음에 고를 순서

**편의부터 체감하려면 D01→D02→D03**, 반복 설정이 불편하면 D07을 먼저 고르면 된다. D04는 D01의 서랍 위에, D06/D08은 D03의 구조화 기록 위에 얹기 쉽다. D05의 baseline 평가를 만들어 두면 검색 알고리즘 변경의 효과를 비교할 수 있다. D09는 실제 비동기 부수 작업이 생길 때, D10은 lexical·기존 원장으로 해결하지 못한 불편이 확인될 때 구체화한다.

기능 하나의 구현 카드에는 이 문서의 ID, 사용자 흐름, 현재 코드 접점, 새 데이터 계약, 오프라인 완료 조건, 모델 호출 필요 여부를 그대로 가져갈 수 있다. PC 실측이 필요한 부분과 클라우드에서 구현 가능한 부분을 나눴으므로 이 조사 전체를 PC 작업 대기로 묶을 필요는 없다.
