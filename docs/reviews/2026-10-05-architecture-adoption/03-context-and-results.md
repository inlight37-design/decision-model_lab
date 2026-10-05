# 입력·기억·검토·수정·결과의 일관성

검토 기준은 **`48ab4bd6f0e297587707aecb83ebc0cd9968892f`**이다. ChatGPT 웹 컨테이너에서 이 tree의 코드를 직접 읽고, 임시 SQLite 원장과 저장소의 합성 실행기만 사용해 경계 사례를 재현했다. 사용자 PC·실제 Codex/Claude CLI·실제 계정·모델 품질은 이 검토에서 관측하지 않았다. 이 문서는 제품 코드 변경이나 외부 프로젝트 실행 결과가 아니다. 아래 링크는 모두 같은 SHA에 고정했다.

## 1. 판단

현재 입력 계층은 자료 사본, 입력 hash, 작업/역할, 승인한 질문, 고정 기억을 상당히 잘 결속한다. 수정도 원래 답을 덮어쓰지 않고 별도 판으로 남기며, 미리보기 이후 지적·처분이 바뀌면 시작을 거절한다. 새로운 프레임워크를 넣어 얻을 가치보다 **이미 있는 경계를 모든 소비 경로에 동일하게 적용하고, 수정한 결과가 다음 판단에 정확히 이어지게 하는 가치가 먼저**다. [E01] [E02] [E03] [E04]

가장 먼저 손볼 실제 불일치는 **교차검토와 일반 취합이 저장된 답의 hash를 다시 확인하지 않고 본문을 소비한다는 점**이다. 같은 손상 원장을 `build_report`는 거절하지만 교차검토·취합은 호출을 진행하는 것을 재현했다. 이어서 기억에 과거 판단의 유효 범위를 표시하고, 수정 답을 검색·발췌·후속 소비까지 연결해야 한다. [E05] [E06] [E07] [E08]

일반 팀원 검토의 GR-1 → GR-2 → GR-3 설계는 이 방향과 맞는다. 이미 입력 미리보기, 자료 범위, 모드별 공개, 실패 시 중단, 선택 판 취합을 설계했으므로 새로 발견한 미설계 영역처럼 취급하지 않는다. 이번 추가 제안은 **그 계약을 격리 합성·다음 단계 제안·기억에도 연결하고, 구현 전에 이미 있는 읽기 검증의 불일치를 해결하는 것**이다. [E09]

자동 기억은 최신 사용자 결정대로 **같은 원장·같은 작업의 일반 팀원과 지정 상위 역할에 기본 켬**을 유지한다. 격리 초안·교차검토·수정/재검토에 pack을 새로 전달하지 않는 현 경계도 유지한다. 기억을 수동 첨부 우선으로 되돌리거나 전역 프로필을 자동 주입하는 제안은 하지 않는다. [E10]

## 2. 실제 데이터 흐름과 소비 범위

### 2.1 입력 생성

| 단계 | 현재 구현 | 판단 |
|---|---|---|
| 자료 검사 | 파일 이름/장치 이름/중복/Unicode/NUL/개수/개별·합계 바이트 상한을 검사하고, 추출 자료이면 내부 metadata와 선택 글의 hash도 검사 | 단순 파일 첨부를 넘어선 입력 계약이 이미 있음. [E01] [E11] |
| 격리 입력 | 질문과 공통 자료 이름·바이트·hash·고정 폴더를 같은 prompt에 포함. 승인 다듬기 원문/대화는 manifest에 남기고 참여자에게는 승인 문장만 전달 | 질문·자료의 실험 조건을 보존. 상위 모델이 질문을 다듬었다는 사실과 초안 간 blind 조건은 별개로 설명해야 함. [E01] [E12] |
| 일반 입력 | 팀원별 과제·자료 목록·기억을 prompt와 hash에 넣고 전체 실행은 팀원별 hash를 다시 묶음. 아무도 받지 않은 자료를 거절 | 서로 다른 과제를 같은 공통 입력으로 가장하지 않음. 한 팀원 행만 일관되게 바꿔도 전체 bundle hash가 감지. [E02] |
| 실행 생성 | 검사한 동일 자료 바이트를 사용하고, 계획/선행 결과를 생성 거래에서 재검사. 다듬기·다음 단계·분담 제안은 조건부 UPDATE로 한 실행에만 소비 | 승인 사본과 실제 생성의 결속, 중복 소비 방어가 존재. [E03] |
| 시도 직전 | 질문/자료 또는 배정 prompt를 재구성하고 hash·크기·자료 목록을 확인. 자료는 임시 폴더 작성 후 rename, 파일 내용 hash 재검사 | 실행 전 사본 무결성 방어가 존재. 실행 중 호스트에서 파일을 바꾸는 경우는 코드가 명시한 잔여 한계. [E02] |

### 2.2 역할별 실제로 받는 자료

| 소비자 | 현재 답/자료 | 기억·판의 범위 |
|---|---|---|
| 격리 초안 작성자 | 고정 질문, 공통 읽기 전용 자료 | 자동 기억 footer를 받지 않음. [E01] |
| 일반 팀원 | 전체 목표, 자기 과제, 자기 배정 자료 | 실행 생성 때 고정한 작업 기억. [E02] |
| 다듬기 슈퍼바이저 | 사용자 원문, 기존 다듬기 차례, 이번 답 | 첫 차례의 기억 사본을 계속 재사용. 실행에 사용한 다듬기는 재사용 불가. [E12] |
| 분담 오케스트레이터 | 목표, 팀원 목록, 첨부 자료 전체 | 분담 요청 때 고정한 기억. 승인 후 팀원별 과제·자료가 바뀌면 `as_proposed=false`로 보존. [E12] [E03] |
| 공개 후 교차검토자 | 자기 원래 답과 다른 팀원 원래 답, 질문. 자료 본문은 제공하지 않음 | 모든 검토 입력을 라운드 생성 시 고정. 앞 검토 결과와 자동 기억은 추가하지 않음. [E05] [E13] |
| 수정 작성자 | 원래 답, 앞 수정 판, 대상 지적, 당시 사람 처분, 앞 재검토, 원래 자료 사본 | 원래 작성자만 허용. 새 자동 기억 없음. [E04] |
| 수정 재검토자 | 수정 때 고정한 근거와 수정 답 | 다른 원래 CLI 작성자만 허용. 자료 폴더와 새 기억 pack은 제공하지 않음. [E04] |
| 격리 모델 합성 | 공개된 원래 초안으로 만든 보고서에서 질문·초안을 구성 | 실행 생성 때의 기억을 추가. 원래 자료 폴더는 plan에 전달하지만 합성 prompt는 원문 자료 목록/폴더를 별도로 안내하지 않음. 인용 검사 대상은 원래 초안. [E07] [E14] |
| 다음 단계 제안 | 사용자 원래 목표/승인 질문, 공개된 원래 초안 | 실행 생성 때의 기억. 교차검토·수정 결과는 이 prompt 구성에 포함하지 않음. [E12] |
| 일반 취합 | 전체 목표, 각 팀원의 과제와 원래 답. 실패 팀원은 결과 없음 | 실행 생성 때의 기억. 현재 구현은 원래 답을 사용하며 GR-3이 선택 판 소비를 제안. [E06] [E09] |
| 후속 기억 | 적격 공개 실행의 질문·판단·검토·답, 선택된 실행의 수정/재검토 발췌 | 검색 점수는 질문·판단·검토·원래 답으로 계산. 수정은 후보 선정 뒤 읽음. [E08] |

이 표의 각 경계는 목적이 다르다. 예를 들어 검토자가 원문 자료를 받지 않는다는 것은 모델 간 논리/누락 검토의 범위를 설명한다. 그 검토 결과로 자료 자체의 진위를 검증했다고 표시할 수 없다. 격리 합성에는 파일 접근 권한이 주어져도 현재 출력 형식에는 자료 파일을 직접 인용하는 참조 계약이 없다. **파일을 전달했는지, 모델이 실제 읽었는지, 인용이 맞는지, 주장을 뒷받침하는지는 각각 확인해야 한다.** [E13] [E14] [E15]

### 2.3 서로 다른 네 종류의 판

| 판 | 현재의 정본 | 의미와 한계 |
|---|---|---|
| 실행 입력 | prompt/input hash, 역할·자료 manifest, 고정 memory pack | 무엇을 보냈는가. 사실이 맞는지는 말하지 않음 |
| 답의 판 | 원래 draft hash, 별도 `revision_id`/parent/hash | 어느 본문인가. 수정 수용은 사실 확인이 아님 |
| 결과 판 | 사람에게 새로 보여 줄 사건의 `seq`에서 계산한 `result_revision` | 새 합성·검토·수정·재검토가 생겼는가. `mark_reviewed`가 예상 판을 확인함 |
| 사람 판단/처분 | `human_reviewed` 사건, 지적별 `review_dispositions`와 사건 | 사람이 무엇을 판단했는가. 처분 편집 자체는 현재 결과 판을 올리지 않음 |

이 구분은 이미 코드에 반영되어 있다. 다만 후속 기억과 최종 소비가 네 판을 모두 충분히 드러내지는 않는다. 수정 preview는 지적 처분까지 hash에 결속하므로 처분 변경 뒤 오래된 수정 입력으로 호출하는 문제는 막는다. 사람 판단 버튼도 새 결과가 나온 뒤의 오래된 결과 판을 거절한다. 아래 개선은 이 보호를 인정한 상태에서 **기억과 최종 산출물의 해석 범위**를 보완한다. [E03] [E04] [E16]

## 3. 우선 개선 항목

| ID | 구분·우선순위 | 개선 | 첫 도입 범위 |
|---|---|---|---|
| CR-01 | 재현한 결함 · P1 | 교차검토·취합의 답 읽기 무결성 일치 | 기존 저장소 읽기 helper와 시작 전 검사 |
| CR-02 | 재현한 표현/문맥 손실 · P1 | 기억에 현재 결과 판과 과거 판단의 적용 판 표시 | pack 새 버전의 최소 상태·출처 필드 |
| CR-03 | 이미 설계된 후속 + 확장 제안 · P1/P2 | 사람이 선택한 답 판을 최종 소비자에 전달 | GR-3와 격리 합성/다음 단계의 공통 선택 계약 |
| CR-04 | 알려진 한계 재현 · P2 | 수정·재검토 검색과 실제 일치 구간 발췌 | 현재 선택기 안의 필드/발췌 개선 |
| CR-05 | 제품 계약 개선 · P2 | 답 인용과 외부 근거 검증을 별도 증거로 연결 | 요구가 분명한 주장부터 수동/결정적 검사 |
| CR-06 | 기존 완화 권고의 구체화 · P2 | 자료·기억·모델 답의 지시 경계를 역할별로 일치 | prompt 정책과 제한된 회귀/실측 비교 |
| CR-07 | 재현성 개선 · P2/P3 | 추출 변환기·범위·선택의 재현 정보 보강 | 기존 `DECISION-SOURCE` 형식 확장 |
| CR-08 | 비용·효용 검증 · P2 | 검토 루프의 실제 개선량과 검토 부담 측정 | 같은 과제의 단계별 비교, 별도 실행 엔진 없음 |

### CR-01 — 교차검토·취합에 저장된 답의 무결성 검사를 공통 적용

**사실.** `ReviewService.cross_review`는 `drafts.text, sha256`을 읽어 그대로 targets에 복사한다. 본문의 hash를 계산하지 않는다. `collate`는 `text`만 읽는다. `REVIEW_SEAT`와 `COLLATE_SEAT`의 응답 검사는 그때 복사한 본문을 원문으로 사용한다. 반면 `build_report`/합성 `_sources`/수정 `_context`/기억 `_answers`에는 본문 hash 확인이 있다. 공개 검토의 `fresh`는 저장된 두 hash 필드의 동등성만 비교한다. [E05] [E06] [E07] [E04] [E08] [E17]

**재현.** 임시 원장에서 정상 공개/수집된 답을 만든 뒤 `drafts.text`만 `CORRUPTED-CONTENT`로 바꾸고 기존 sha256을 유지했다. 격리 교차검토와 일반 취합 모두 변경 본문을 prompt에 넣고 합성 실행기의 응답을 `accepted`로 저장했다. 교차검토 대상은 `fresh=true`로 표시되었다. 같은 격리 원장의 `build_report`는 `public draft does not match its sealed digest`로 거절했다. 실제 CLI나 모델은 부르지 않았다.

**영향.** 저장 손상, 잘못된 이행/수선 코드 등으로 본문과 hash가 어긋났을 때 소비자마다 다른 결론을 낸다. hash 검증 실패 원문을 대상으로 검토 호출을 소비하고, 그 검토가 손상 이전 원본을 가리키는 것처럼 보일 수 있다. 이것은 정상 UI가 원본을 덮어쓴다는 주장이나, 임의로 DB 전체를 다시 쓸 수 있는 공격자에 대한 보안 보장 주장이 아니다. 기존 무결성 계약을 적용하는 읽기 경로의 결함이다.

**최소 구현.** 수용 상태와 본문/hash를 확인해 `(pid, text, sha256, source_version)`을 주는 저장소 helper를 두고 교차검토·취합·수정·후속 선택이 재사용한다. 교차검토는 자기 답을 포함한 모든 입력을 확인한다. 취합은 과제/배정 결속도 기존 assignment 계약과 일치시키고, 정상적인 미수용 팀원은 기존처럼 결과 없음으로 남긴다. 검사 실패는 **예약/라운드 저장/모델 시작 전**에 거절한다. 새 입력 hash는 전달한 손상 본문도 완전하게 hash할 수 있으므로, 입력 hash 생성만으로 원래 답의 검증을 대체하지 않는다.

**실패 확인.** 본문만 수정, hash만 수정, 없는 답, 자기 답 손상, 대상 답 손상, 배정 과제 변경을 각각 주입해 새 호출과 성공 검토가 생기지 않는지 본다. 실제 라운드 고정 후 원본과 대상 snapshot의 hash가 다르면 조회에서 손상/이전 판을 구별한다. 정상 격리 공개·일반 수집·실패 팀원 경로는 유지한다.

**효용.** 새 기능 없이 현재 검토 결과의 원문 추적 신뢰도를 높인다. GR-1에서 계획한 모든 답 hash 확인도 같은 helper로 구현할 수 있다. [E09]

### CR-02 — 새 기억에 과거 판단이 어느 결과 판을 보았는지 보존

**사실.** `_review_state`는 새 수정/재검토 등의 사건이 생기면 과거 판단을 현재 판의 완료로 보지 않는다. 그러나 `memory._context`는 가장 최근 `human_reviewed` 사건의 payload를 가져오고, 발췌에는 그 메모만 넣는다. 새 기억 entry에는 현재 `result_revision`이나 `reviewed` 여부가 없다. 과거 payload의 revision은 source hash 계산에 들어갈 수 있어도 전달 발췌에서 그 판단의 적용 판을 복원할 수 없다. [E16] [E08]

**재현.** 정상 교차검토 뒤 `OLD-JUDGMENT`로 판단 완료하고 새 수정 답을 생성했다. 공개 view는 `reviewed=false`가 되었지만 새 memory pack에는 `사람의 판단 메모: OLD-JUDGMENT`가 들어갔다. 이것은 봉인 본문 유출이 아니다. 공개된 이력을 읽으면서 **그 메모가 최신 수정 전에 쓰였다는 의미를 잃는 경우**다.

**최소 구현.** 새 pack의 canonical context와 entry에 `result_revision`, `human_judgment.revision`, `judgment_is_current`, 필요하면 `active_postprocessing`을 담는다. 이전 판단은 지우지 않고 “이전 결과 판에 대한 판단”으로 표시한다. 후속 작업이 진행 중인 공개 이력을 후보로 유지할지는 task-local 정책으로 명시하되, 최신 판을 판단 완료했다는 표현은 만들지 않는다. 기존 repository의 판 계산을 공유하고, memory에 별도 완료 판정 SQL을 복제하지 않는다.

**실패 확인.** 판단 뒤 합성 실패/수정 성공/재검토 unknown/지적 처분 변경을 각각 거친 원장으로 현재 판단 여부와 발췌 표시를 대조한다. 지적 처분 편집은 현재 결과 판을 올리지 않는 설계이므로 필요하면 별도 판단/처분 revision을 사용한다. 옛 pack은 당시 필드 그대로 읽고 새 의미를 소급 추정하지 않는다.

**효용.** 자동 기억을 계속 켜 두어도 “이전에 동의한 결론”과 “새 지적 때문에 다시 보는 결론”을 다음 역할이 구별할 수 있다. 모델이 그 구분을 실제 활용하는 효과는 별도 평가가 필요하다.

### CR-03 — 선택한 답 판과 처분을 최종 합성·취합·다음 단계에 연결

**사실.** 수정 판은 별도 이력/보고서에 보존된다. 현재 합성과 다음 단계 제안은 `build_report`의 원래 초안을 사용한다. 합성 prompt에는 그 보고서에 있는 교차검토 섹션조차 추가하지 않는다. 일반 취합도 원래 draft를 읽는다. 이 동작은 `revision_report`의 `synthesis_scope=original_drafts_only` 및 기존 GR-3 설계에 명시되어 있다. [E07] [E12] [E14] [E09]

**문제의 형태.** 사용자가 반례를 수용해 새 판을 만들었어도 다음 모델은 원래 답을 다시 합칠 수 있다. 이는 현재 계약 위반으로 단정할 결함이 아니라 **교정한 결과가 최종 판단에 반영되는 경로가 아직 연결되지 않은 기능 한계**다. 자동으로 가장 최근 판을 택하면 실패한 수정이나 사람이 채택하지 않은 수정까지 반영할 수 있으므로 명시적인 판 선택이 필요하다.

**최소 구현.** 소비 입력에 팀원별 `original/revision`, `revision_id`, 본문 hash, 부모 판, 관련 지적/처분/재검토, 미해결/미참여 범위를 고정한다. 소비자 종류와 원래 실행 모드도 넣고 확인 hash를 발급한다. 사람 판단에는 채택한 판 목록/소비 입력 hash를 함께 연결한다. 이미 저장한 합성/취합 입력은 바꾸지 않는다. 옛 보고서의 의미를 유지하면서 선택 판을 지원하는 새 보고 형식을 추가한다.

일반 작업은 예정된 GR-1 → GR-2 → GR-3 순서를 유지한다. 격리 작업은 원래 초안의 독립 비교와 교정 후 판단을 모두 볼 수 있게 하고, 선택 판을 사용한 합성에는 공개 후 교정본을 사용했다는 출처를 남긴다. 판을 전달했다고 원래 초안의 독립 정족수를 다시 계산하거나 교정본을 독립 초안으로 세지 않는다.

**실패 확인.** preview 뒤 수정 판·처분·재검토가 바뀐 경우, 다른 실행의 revision ID를 넣은 경우, 실패/unknown 판을 선택한 경우, 혼합된 원본/수정 선택, 일부 팀원 누락을 확인한다. 최종 답의 각 근거가 실제 소비한 판의 hash로 이어져야 한다. 수정 전에 생성한 합성은 원래 입력을 그대로 재현해야 한다.

**효용.** 이미 소비한 수정/재검토 호출의 결과를 사용자가 최종 판단에 활용할 수 있다. GR-3에서 만드는 선택 계약을 상위 역할마다 따로 구현하는 중복도 줄인다.

### CR-04 — 수정에만 있는 내용도 찾고, 찾은 근거를 실제 전달

**사실.** 검색 점수는 `_context`의 질문·판단·검토 및 `_answers`의 원래 답으로 계산한다. 수정 답/응답/재검토는 후보 선정 뒤 읽는다. `_fair_parts`는 섹션을 공평하게 나누되 각 항목의 앞 바이트를 자르므로, 긴 답 뒤쪽의 일치 표현이 선정 이유가 되어도 발췌에는 빠질 수 있다. 이 한계는 현재 기능 안내에도 적혀 있다. [E08] [E10]

**재현.** 실제 수정 흐름으로 만든 합성 fixture의 수정 답에만 `quartzneedle`을 넣고 그 답의 hash를 맞췄다. 같은 작업에 후속 무관 공개 실행을 추가한 뒤 검색하니 `matched_runs=0`이었고 최근 이력 fallback이 선택되며 수정 실행은 선택되지 않았다. 부정확한 embedding 모델의 문제가 아니라 현재 검색 대상 필드의 한계다.

**최소 구현.** 수용되고 hash가 맞는 수정 답·수정 대응·재검토를 후보 점수 필드에 추가하되, 원래 답과 판 관계를 함께 남긴다. 발췌는 실제 일치한 문장/문단과 바로 붙은 조건·부정문을 우선 포함한다. 현재 섹션별 공간·미해결 우선·누락 바이트·출처 hash·전체 pack 상한은 유지한다. `matched_in_source`와 `included_in_excerpt`를 구별해 “골랐지만 모델에게 그 근거는 전달하지 못함”을 표시한다.

**실패 확인.** 수정에만 새 용어, 뒤쪽의 부정/예외, 숫자가 같은 무관 실행, 원래 답과 수정 답의 상충, 수용되지 않은 수정, 손상 hash를 고정 사례에 넣는다. 평가기는 이미 있으므로 기존/확장 fixture를 보존하면서 새 held-out 사례를 별도로 추가한다. 선택된 run의 recall뿐 아니라 **필요한 증거 span이 실제 pack에 들어온 비율**을 본다. [E18]

**효용.** 벡터 DB나 전역 기억을 도입하기 전에 현재 검색의 명확한 누락을 해결한다. 이 단계 뒤에도 동의어 검색이 실제 병목이면 task-local FTS/하이브리드 검색을 평가한다. 후보를 찾는 기술을 바꿔도 공개 범위·판·상한·고정 pack 계약은 유지해야 한다.

### CR-05 — 원문 일치·범위 일치·사실 근거·사람 판단을 각각 연결

**사실.** 교차검토는 인용의 문자열 포함을 확인하고, 일치하지 않으면 `not_found`를 남긴다. 수정/재검토는 모든 지적 ID에 정확히 한 번 대응하게 한다. 합성은 실제 일치 인용이 하나라도 있으면 `quoted`, 없으면 `unsupported_addition`으로 표시하되 모든 주장의 사실 확인은 미수행으로 남긴다. 이 정직한 분리는 유지할 자산이다. [E13] [E15] [E19]

**추가로 필요한 것.** 현재 합성의 “주장”과 “인용”은 별개의 문장이다. 정확한 인용이 주장과 관련 없는 문장이거나 일부 조건만 뒷받침해도 문자열 검사는 통과할 수 있다. `recommendation`, 미해결 목록, 취합의 gaps/next에도 주장과 근거 사이의 연결은 강제되지 않는다. 현재 코드가 이를 사실 검증으로 표시하지는 않으므로, 자동 신뢰 점수를 만드는 방향 대신 검사 종류를 확장하는 것이 적절하다. [E15] [E20]

**최소 구현.** 사용자가 결정에 쓸 핵심 주장에 `claim_id`, 대상 답/판, 원문 자료 ID/hash/쪽·줄, 검사 방식, 검사 결과, 검사자/시각, 미확인 범위를 연결하는 별도 evidence record를 둔다. 최초 범위는 사람이 원문을 대조한 기록이나 재현 가능한 계산/테스트의 결과다. 모델의 추가 검토는 의견으로 보존하고, `qualified` 처분을 자동 `supported`로 올리지 않는다. 원문 자료를 읽지 않은 검토에는 그 범위를 분명히 남긴다.

**실패 확인.** 정확하지만 무관한 인용, 일부만 뒷받침하는 인용, 수정된 판의 이전 근거, 출처가 취소/삭제/손상된 경우, 동일 모델의 동의만 있는 경우를 구분한다. 검사 결과가 달라져도 원래 초안/과거 판단은 보존하고 현재 주장에 걸린 판만 바꾼다.

**효용.** 모델 간 동의를 검증으로 착각하지 않으면서 연구·코드 검토처럼 실제 원문/시험에 닿을 수 있는 과제부터 결론의 근거를 강화한다. 모든 일반 질문에 새 검증 모델을 자동 호출하는 비용은 피한다.

### CR-06 — 역할별 자료 지시 경계를 공통 정책으로 정리

**사실.** 교차검토·취합·합성·수정 prompt는 모델 답 안의 지시를 따르지 말라고 명시하고, 호출마다 경계 표식을 붙인다. 기억 header도 이전 답/사람 판단은 검증되지 않은 참고자료라고 알린다. 반면 초안용 `PROMPT_SOURCES`는 자료 이름을 밝히고 자료 밖 판단을 표시하라고 하지만 자료 안 지시를 따르지 말라는 문장은 없다. [E01] [E13] [E15] [E19] [E20] [E08]

저장소의 2026-09-25 자료 주입 실험은 두 참여자가 해당 표본의 지시를 따르지 않았다고 기록하며, 짧은 한 표본의 한계와 “주입 문구를 답에 옮겨 적어 다음 합성자에게 전달할 수 있음”을 함께 남긴다. 본 검토는 그 기록을 읽었을 뿐 해당 PC 실험을 재실행하지 않았다. 실제 주입 성공을 새로 발견한 것으로 쓰지 않는다. [E21]

**최소 구현.** 자료 입력용 공통 정책에 외부 글/추출 metadata/이전 답은 자료이며 현재 사용자 질문을 대체하지 않는다는 경계를 넣고, 원문 prompt와 일반 prompt, 분담 prompt에서 적용 범위를 확인한다. 코드 구조화와 host 권한 제한이 실제 강제 경계이고, 이 문장은 모델의 해석을 돕는 완화다. 자료가 스스로 선언한 역할·정책·평가 기준을 controller 설정으로 읽지 않는다.

**실패 확인.** 자료 파일명 `AGENTS.md`/`CLAUDE.md`, 숨긴 지시, 인용된 지시가 초안→검토→기억으로 전달되는 경우, JSON/string 경계를 모방하는 본문을 사용한다. 모의 테스트는 prompt 구성/경계 구분만 확인한다. 실제 따름 여부는 제한된 별도 구독 실험으로만 판단한다. 실제 CLI 계획의 문맥/권한 옵션을 바꾸면 그 계획에 대한 재관측이 필요하다.

**효용.** 자료 입력 형식마다 다른 해석 안내를 줄이고, PDF/URL·후속 기억이 늘어날 때 같은 규칙을 적용할 수 있다. 이 변경만으로 prompt injection이 해결됐다고 표현하지 않는다.

### CR-07 — 외부 추출 자료를 다시 대조할 수 있는 최소 재현 정보

**사실.** `DECISION-SOURCE/1`은 원본/변환/선택 hash, 출처, 추출 시각, 선택 쪽·줄, 누락 정보를 글과 결속한다. 원본 바이트는 보존하지 않고 `authenticity=not_verified`로 명시한다. PDF는 Poppler, URL은 텍스트 decode/HTMLParser이며 도구 설명은 기록하지만 실제 Poppler/Python 버전이나 변환 정책 판은 고정하지 않는다. HTML의 링크 주소·표 구조, PDF의 이미지/수식/배치 손실도 누락으로 기록한다. [E11] [E22] [E23]

URL 경로에는 HTTP(S)/기본 포트, 모든 hop의 공개 주소 검사, 검사한 IP로 연결, 원래 host의 TLS 검증, redirect/본문/시간 제한, 인증·쿠키·JavaScript 미사용이 이미 구현되어 있다. 새 자료 기능을 제안하면서 이 방어가 없는 것처럼 설명해서는 안 된다. [E23]

**최소 구현.** 먼저 변환 정책 판과 관측된 도구 버전, 추출 글의 논리적 locator를 metadata에 넣는다. 기본 안내는 실제로 선택된 쪽/줄과 누락을 사용자가 알아보기 쉽게 보여 준다. 정밀 검증 과제에서 원본 재현이 필요한 경우에만 원본 파일 또는 사용자가 정한 보관 위치의 content hash를 별도 artifact로 연결한다. 현재 파일 크기·임시 처리 정책을 몰래 넓히지 않는다.

**실패 확인.** 같은 원본과 같은 변환기로 선택 범위를 다시 만들었을 때 converted/selected hash가 맞는지, 도구 판이 바뀌면 다른 변환으로 구별되는지, PDF 페이지 표식이 선택 시작 이전에 잘린 경우에도 locator를 찾을 수 있는지 본다. 원본 없는 과거 문서는 재현 불가 범위를 표시한다. URL 출처 문자열과 hash가 있다는 사실을 저자/진위 증명으로 쓰지 않는다.

**효용.** 전면 크롤러/OCR/외부 문서함 도입 전에 연구 자료의 “내가 실제로 어떤 부분을 읽게 했는가”를 나중에도 대조할 수 있다. OCR·표 해석·스크린샷은 그 결과가 필요한 과제에서 독립된 변환기로 추가하고 동일한 provenance 계약을 지키게 한다.

### CR-08 — 검토 호출의 효과를 단계별로 측정

**사실.** 한 라운드 검토, 앞 검토 실패 때 남은 검토 중단, 원래 작성자 수정, 다른 작성자 재검토, 각각의 횟수 상한은 이미 구현되어 있다. GR 설계는 초기 답 이후의 추가 호출을 `n + r × v × (1 + c) + k`로 설명하고 실제 개선 효과를 별도로 평가하도록 요구한다. [E05] [E04] [E09]

**최소 평가.** 같은 과제에서 초안만, 취합/합성 추가, 교차검토 추가, 수정·재검토 추가를 비교한다. 가능한 비교는 같은 예산에서도 수행한다. 좋은 지적 수만 세지 말고 잘못된 지적·정당한 분담 차이를 오류로 지적한 경우·수정 중 새 오류·남겨야 할 반례의 소실·최종 채택 판·사람이 대조한 시간을 함께 기록한다. 호출/입력량/실패/지연은 기존 원장으로 계산한다.

**멈춤 조건.** 수정으로 해소할 구체 지적이 없거나, 추가 단계가 동일 예산의 단일 강한 답보다 도움이 되는지 입증되지 않으면 더 많은 loop/agent를 기본값으로 늘리지 않는다. 자료가 없는 사실 문제는 모델을 더 부르는 것보다 검증 가능한 자료를 넣는 것이 먼저인지 판단한다. 이것은 자동 모델 품질 점수나 실제 구독 사용량 추정의 도입 제안이 아니다.

**효용.** 외부 프로젝트의 multi-agent/critic/reflection 기능 중 어느 단계까지 이식할지 사용자 과제의 결과로 결정할 수 있다. 기능을 보유하는 것과 기본적으로 매번 실행하는 것을 구분한다.

## 4. 외부 기능의 이식 범위

여기서는 외부 저장소를 새로 검증한 것으로 주장하지 않는다. 전체 검토의 외부 출처/라이선스 분석과 연결할 **현재 코드의 수용 경계**를 정한다.

| 외부 기능 유형 | 지금 가져올 범위 | 뒤로 미룰 범위 | 들어갈 자리·완료 기준 |
|---|---|---|---|
| 작업 기억·대화 검색 | 작업 범위 검색, 판/출처, 실제 일치 span, 누락/선택 이유 | 전역 프로필 자동 병합, 원문을 없애는 자동 요약, 무제한 재주입 | `memory.py`/InputBuilder. CR-02·04 및 옛 pack 호환 |
| critique/reflection loop | 기존 한 라운드, 지적 ID별 대응, 명시적 수정·재검토, 선택 판 취합 | 동의할 때까지 자동 반복, 새 모델 자동 충원 | 기존 Review/Revision service와 SEATS. GR-1~3, 실패 포함 비용 |
| evidence/citation UI | 주장→답 판→원문 자료 locator→검사 결과 탐색 | 인용 수/모델 투표를 신뢰 점수로 사용 | `report`/공개 projection과 CR-05의 별도 증거 계약 |
| PDF/URL/문서함 | 명시적 준비, bounded 변환, 원본/선택 범위와 누락 결속 | 로그인 자료 자동 전송, 자동 크롤링/OCR 전면 적용 | 기존 ingestion/source_document. CR-07 및 승인한 입력 확인 |
| supervisor/planner | 현재 목표·완료 기준·앞 결과에 근거한 제안, 사람이 시작 | 전역 기억을 가진 planner가 질문·배정·완료를 조용히 수정 | PlanningService와 기존 CAS/입력 고정 |

이식 성공의 기준은 외부 화면이나 prompt가 비슷하게 보이는지가 아니다. **그 기능이 실제 받은 입력과 자료 범위, 사용한 답 판, 결과의 미해결, 호출 비용이 기존 원장에서 이어지는가**로 판단한다. 이 조건은 현재 코드의 강점을 보존하면서 기능 사이의 빈틈을 메우는 기준이다.

## 5. 이번 검증과 남은 미확인

### 5.1 직접 실행한 모델 없는 재현

임시 원장마다 저장소의 `Base` fixture를 만들고 `doCleanups()`로 controller/원장을 닫았다. 사용한 fixture는 `test_cross_review.CrossReviewTests/Reviewer`, `test_collate.CollateTests/Collator`, `test_revisions.Revisions/RevisionExecutor`다. 제품 코드·기존 테스트·실제 원장은 수정하지 않았다. [E24]

| 재현 | 관측 결과 | 확인하지 않은 것 |
|---|---|---|
| 공개 답의 text만 변경, hash 유지 → 교차검토 | 변경 본문 전달, 검토 수용, `fresh=true`; 동일 원장의 draft report는 거절 | 실제 사용자 원장에 손상이 발생했는지, 실제 모델의 판단 |
| 일반 답의 text만 변경, hash 유지 → 취합 | 변경 본문 전달, 취합 수용 | 실제 계정 호출·비용 |
| 판단 완료 → 새 수정 → 새 기억 | view는 `reviewed=false`; memory에 예전 메모가 적용 판 설명 없이 포함 | 모델이 실제로 옛 판단을 최신으로 오해하는 비율 |
| 수정 답에만 고유 용어 → 뒤에 무관 실행 → 기억 검색 | `matched_runs=0`, 최근 fallback, 수정 실행 누락 | 전체 실사용 recall/precision |

CR-01을 재현하는 핵심 순서는 아래와 같다. 기존 fixture를 이용한 경계 재현이며 일반 서비스의 정상 입력 API로 원본을 바꾸는 절차가 아니다.

```python
import sys
sys.path.insert(0, "tests")
from test_cross_review import CrossReviewTests, Reviewer
from app.report import build_report, ReportError

case = CrossReviewTests()
case.setUp()
try:
    ctl = case.controller(Reviewer())
    rid = case.revealed(ctl)
    with case.store.tx() as tx:
        tx.execute("UPDATE drafts SET text = ? WHERE run_id = ? AND pid = ?",
                   "CORRUPTED-CONTENT", rid, "codex")
    ctl.cross_review(rid)
    assert ctl.wait_idle()
    review = case.round(ctl, rid)["reviews"][0]
    assert review["state"] == "accepted"
    assert "CORRUPTED-CONTENT" in review["prompt"]
    assert review["targets"]["D1"]["fresh"] is True
    try:
        build_report(ctl.view(rid), rid)
    except ReportError:
        pass  # 기존 보고 경로는 같은 손상을 거절한다.
    else:
        raise AssertionError("report unexpectedly accepted the changed draft")
finally:
    case.doCleanups()
```

### 5.2 미확인으로 남기는 것

- 저장 파일을 시작 뒤 다른 호스트 프로세스가 바꾸는 범위는 `_snapshot` 주석의 K14와 동일하다. 이번 검토에서 실제 재현하거나 해결하지 않았다.
- `accepted`는 실행/응답 형식 수용이며 사실 정답률이 아니다. 인용·출처 hash도 원문의 진위나 의미적 뒷받침을 증명하지 않는다.
- source prompt의 완화 문구를 넣었을 때 실제 주입 저항성이 얼마나 달라지는지, 수정/합성이 실제로 나아지는지는 별도 PC/모델 평가가 필요하다.
- 같은 task 안의 검색 확장은 읽는 이력 바이트에 비례하는 비용을 더할 수 있다. 기존 평가/벤치마크를 사용해 현재 이력 크기에서 실익을 확인해야 한다.
- 일반 팀원 검토/수정/선택 판 취합은 기준 tree에서 설계이며 구현되지 않았다. 이 문서는 기존 GR 완료 조건을 구현 완료로 바꾸지 않는다.

## 6. 고정 SHA 근거 색인

| ID | 파일·함수·줄 | 확인한 사실 |
|---|---|---|
| E01 | [`app/context/inputs.py` 18–190][E01] | 초안/자료 prompt, 이름/바이트 검사, 역할·정족수, 격리 입력/확인 hash |
| E02 | [`app/context/inputs.py` 194–333][E02] | 일반 배정 manifest, bundle hash, 시도 전 prompt/자료 사본 검증 |
| E03 | [`app/application/work.py` 20–103][E03] | 자료 동일 바이트, 확인 hash, 계획 재검사, 승인 소비의 조건부 UPDATE |
| E04 | [`app/application/revisions.py` 21–165][E04] | 원본·앞 판·지적·처분 snapshot, stale preview, 수정/재검토 제한 |
| E05 | [`app/application/reviews.py` 84–175][E05] | 공개 후 한 라운드, 답 읽기, 입력 고정, 순차 시작/중단 |
| E06 | [`app/application/reviews.py` 26–73][E06] | 일반 취합 적격성, 과제·원래 답 읽기, 기억/입력 고정 |
| E07 | [`app/report.py` 44–164][E07] | 보고서의 input/draft hash 검증, 별도 수정 보고와 원래 초안 합성 범위 |
| E08 | [`app/memory.py` 15–243][E08] | task-local 선택/상한, 원래 답 검색, 후보 뒤 수정 읽기, 옛 판단, 균형 발췌 |
| E09 | [`general-team-review/README.md` 18–136][E09] | GR의 변경 지도·입력/판 계약·상한·선택 판 취합·검증 순서 |
| E10 | [`NEXT-SESSION.md` 63][E10] · [`docs/FEATURES.md` 72–94][E10b] | 최신 자동 기억 결정, 현재 역할 범위와 알려진 누락 |
| E11 | [`app/source_document.py` 21–93][E11] | provenance·변환/선택 hash·쪽/줄·진위 미검증 |
| E12 | [`app/application/planning.py` 28–202][E12] · [`app/context/inputs.py` 354–433][E12b] | 다듬기/분담/다음 단계 실제 입력, 기억, 일회 승인 검증 |
| E13 | [`app/cross_review.py` 23–82][E13] | 답 경계 표식, 자료 미제공, 정확 인용/미일치, 비독립/사실 미검사 |
| E14 | [`app/application/synthesis.py` 41–102][E14] · [`app/synthesis.py` 146–154][E14b] | 공개 보고→원래 초안 prompt, 고정 기억, 자료 mount, 예약 |
| E15 | [`app/synthesis.py` 169–238][E15] | 인용 위치/hash 대조, quoted/unsupported 구분, 의미·진위 미검사 |
| E16 | [`app/repository.py` 56–75][E16] · [`app/application/reviews.py` 196–246][E16b] | 결과 판과 사람 판단, 처분, stale 판단 거절 |
| E17 | [`app/execution/seats.py` 57–79][E17] · [`app/queries/public.py` 392–427][E17b] | snapshot 본문 응답 검사, 저장 hash 비교의 fresh 표시 |
| E18 | [`tools/evaluate_memory.py` 1–100][E18] | 모델/네트워크/실제 원장 없는 기존 고정 사례 평가기 |
| E19 | [`app/revisions.py` 23–83][E19] | 수정 지시문, 지적 ID별 정확한 대응, 재검토 형식 |
| E20 | [`app/collate.py` 18–88][E20] | 취합의 자료 경계/형식/인용, gaps/next 처리 |
| E21 | [`source-injection/RESULTS.md`][E21] | 이전 세션의 실제 실험 기록·미따름 관측·전달/일반화 한계 |
| E22 | [`app/ingestion/extract.py` 76–158][E22] | URL/PDF 변환·제한·누락·임시 원본 처리 |
| E23 | [`app/ingestion/url_fetch.py` 21–122][E23] | 주소 검증/IP 고정/TLS/redirect/본문·시간 상한 |
| E24 | [`test_cross_review.py` 26–75][E24] · [`test_collate.py` 33–75][E24b] · [`test_revisions.py` 19–59][E24c] | 이번 임시 재현에 사용한 합성 실행기와 fixture |

[E01]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/context/inputs.py#L18-L190
[E02]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/context/inputs.py#L194-L333
[E03]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/work.py#L20-L103
[E04]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/revisions.py#L21-L165
[E05]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/reviews.py#L84-L175
[E06]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/reviews.py#L26-L73
[E07]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/report.py#L44-L164
[E08]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/memory.py#L15-L243
[E09]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/architecture/general-team-review/README.md#L18-L136
[E10]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/NEXT-SESSION.md#L63
[E10b]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/FEATURES.md#L72-L94
[E11]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/source_document.py#L21-L93
[E12]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/planning.py#L28-L202
[E12b]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/context/inputs.py#L354-L433
[E13]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/cross_review.py#L23-L82
[E14]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/synthesis.py#L41-L102
[E14b]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/synthesis.py#L146-L154
[E15]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/synthesis.py#L169-L238
[E16]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/repository.py#L56-L75
[E16b]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/application/reviews.py#L196-L246
[E17]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/execution/seats.py#L57-L79
[E17b]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/queries/public.py#L392-L427
[E18]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/tools/evaluate_memory.py#L1-L100
[E19]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/revisions.py#L23-L83
[E20]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/collate.py#L18-L88
[E21]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/docs/experiments/2026-09-25-source-injection/RESULTS.md
[E22]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/ingestion/extract.py#L76-L158
[E23]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/app/ingestion/url_fetch.py#L21-L122
[E24]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/tests/test_cross_review.py#L26-L75
[E24b]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/tests/test_collate.py#L33-L75
[E24c]: https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/tests/test_revisions.py#L19-L59
