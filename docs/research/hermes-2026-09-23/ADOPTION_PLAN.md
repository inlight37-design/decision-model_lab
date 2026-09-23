# 적용 계획·최소 계약·수용 시험

2026-09-23 · [요약](README.md) · [상세 분석](ANALYSIS.md) · [근거](EVIDENCE.md)

**아래는 구현 제안과 시험 명세다. 실행한 결과가 아니다.** 기존 v0.2/v0.4 wire schema를 변경하지 않았고 runner·skill catalog·DB를 구현하지 않았다. `HP-` 티켓은 이번 조사 로컬 ID이며 GitHub issue를 자동 생성한 것이 아니다.

## 1. 순서: 기존 pilot을 가로막지 않기

```text
기존 V04-01 관측/리뷰 결과
        |
        v
Gate A: 모델 호출 없는 mock runner
        HP-01 실행 수명주기 + HP-02 문맥 manifest + HP-03 회계/상태
        |
        v
Gate B: 사용자 승인 후 native conformance와 V04-03
        실제 CLI 문맥·권한·취소·출력/모델 식별 검증
        두 native 경로의 읽기 전용 독립 초안
        |
        v
Gate C: 기존 기준선에 기능 하나씩 추가
        HP-04 승인된 skill의 필요 시 로딩
        HP-05 범위 있는 recall
        HP-06 검증된 lesson의 skill 변경안
        |
        +--> HP-07 필요한 MCP만 연결
        +--> HP-08 MoA에서 배운 역할/주기 실험
        +--> HP-09 실제 수요가 생긴 저장/검색 확장
        +--> HP-10 exec와 동일 계약의 App Server 선택 전송
```

이 순서는 우리의 `NEXT-SESSION.md`에 이미 있는 mock runner → 문맥/권한 conformance → 독립 답변 pilot을 구체화한 것이다. `HP-04` 이후를 끝내야 V04-03에 착수할 수 있다는 뜻이 아니다. Antigravity의 정책/계정 문제를 이번 Hermes 조사로 해결했다고 간주하지 않는다. [P02](EVIDENCE.md#project)

## 2. HP-01 — native 실행 수명주기와 실패 계약

**우선순위:** P0. **근거:** [H07–H09](EVIDENCE.md#h07). **접점:** 기존 `tools/review_boundary.py`의 상태 전이와 V04-03용 runner. 새 실행 모듈의 이름·경로는 구현 PR에서 정한다.

### 최소 구현

고정된 executable과 사전 검증한 argv 배열, 작업 디렉터리, 최소 환경, 입력/출력 제한, attempt 식별자를 받는다. exec one-shot은 입력 후 stdin을 닫는다. stdout 구조화 데이터와 stderr 진단을 별도로 처리한다. 종료 코드만으로 의미상 성공을 계산하지 않는다.

취소는 `cancel_requested` 관측 후 native 취소 요청/우리 소유 프로세스 종료를 시도한다. 실제 종료를 확인하기 전 `exited`로 만들지 않는다. 연결 단절은 `unknown`이며, 재연결 시 동일 프로세스·attempt인지 확인한다. 재시도는 새 attempt로 만든다. 광범위한 프로세스 이름 종료로 다른 사용자 작업을 죽이지 않는다.

### 수용 조건

| 시험 | 요구 결과 |
|---|---|
| 잘못된 옵션/출력 형식 | 실행 전 거절 또는 명시 형식 오류. 정상 결과로 파싱하지 않음 |
| exit 0 + 오류 JSON | 실패 상태를 보존. exit 0만으로 완료 판정하지 않음 |
| 정상 최종 텍스트 뒤 비정상 종료 | 부분 output과 실패를 함께 남김 |
| 큰 stdout/stderr·잘린 JSON | 상한에서 멈추고 잘림/프로토콜 오류 명시. 무한 메모리 증가 금지 |
| stdin 종료까지 기다리는 mock | one-shot 입력 종료가 보장되어 종료 가능 |
| 취소 도중 자식 프로세스 생성 | 소유 트리 추적 및 잔존 확인. 입증 불가하면 UNKNOWN |
| 재개 요청에 다른 thread 반환 | resume 실패/새 실행 여부를 명시. 동일 실행으로 숨기지 않음 |
| 뒤늦은 완료 이벤트 | 이미 종료한 다른 attempt를 되살리지 않음 |

mock 통과는 실제 Windows 프로세스 트리 종료의 증거가 아니다. Windows에서 소유권·PID 재사용·child cleanup을 실제로 확인해야 Gate B를 통과한다.

## 3. HP-02 — 불변 입력과 독립성 conformance

**우선순위:** P0. **근거:** [H03–H04](EVIDENCE.md#h03), [H07](EVIDENCE.md#h07), [P04](EVIDENCE.md#project). **접점:** Context builder/manifest와 inventory 상태 분리.

### 최소 입력 기록 — 개념 예시

아래 필드 묶음은 **proposal-only**다. 기존 production schema나 실제 run을 나타내지 않는다.

```text
run_id / participant_id / attempt_id
protocol_mode / phase / cohort_revision
project_revision
common_sources: artifact ID + revision + digest
skills: namespace + ID + revision + digest
permission_profile_revision / allowed_resources
funding_profile_id                       # 비밀 값이 아닌 정책 식별자
requested_model / reported_model         # 미보고 값은 unknown
native_runtime_version
context_conformance / permission_conformance
input_pack_digest / eligibility_checked_at
```

새 conversation을 만드는 것과 독립 문맥을 만드는 것은 구분한다. native 전역 memory/instruction/plugin/MCP, 공유 파일, prefill, 다른 참여자 결과 cache까지 관측한다. 참여자별 immutable 입력 manifest를 비교하고 서로 다른 자료가 있는 경우 그 차이를 실험 조건으로 남긴다.

### 양성·부정 대조

허용된 공통 파일에 무해한 marker를 두어 실제 읽기를 확인한다. 별도 금지 파일·다른 참여자의 초안·과거 합성 답안에는 다른 marker를 두고 읽기 요청이 backend에서 거절되는지 확인한다. **최종 답에 marker가 없다는 것만으로 격리 성공이라고 판단하지 않는다.** 도구 이벤트와 거절 결과도 확인한다. 실제 인증 값이나 민감 데이터는 fixture에 넣지 않는다.

같은 시험에서 허용 파일도 읽히지 않으면 ‘안전하게 모두 차단’했더라도 유용한 read-only 참여자 conformance를 통과한 것이 아니다. 같은 task로 설정된 두 모델이 서로 다른 기억/skill 판본을 자동 주입받지 않게 한다.

새 evidence/skill 버전은 다음 실행부터 적용한다. 중간의 임의 갱신은 manifest 위반으로 기록하고, 필요하면 새 run/cohort로 다시 시작한다.

### 종료 조건

실제 adapter의 `installed`, `auth_observed`, `transport_observed`, `context_conformance`, `permission_conformance`를 분리한다. 실행 직전에 정책과 관측 유효성을 결합해 `eligible_for_run`을 계산한다. 설정 파일에 `true`가 있다는 이유로 conformance를 승격하지 않는다. 기존 aux-pc 기록을 이번 세션의 새 관측으로 덮어쓰지 않는다.

## 4. HP-03 — 호출 회계와 화면 이벤트

**우선순위:** P0. **근거:** [H06](EVIDENCE.md#h06), [H08](EVIDENCE.md#h08), [H12](EVIDENCE.md#h12). **접점:** `advance`, `budget_projection`, `sealed_projection`, `quota_projection`.

실행 예약 시 슬롯을 원자적으로 기록한다. 실패/UNKNOWN/취소 요청만으로 이미 쓴 슬롯을 환급하지 않는다. 재시도·planner·요약·합성·skill 생성도 호출 목적을 구분해 기록한다. controller invocation 수와 native 하네스 내부 API/tool loop 수는 다른 단위다. 내부 사용량을 볼 수 없으면 **호출 상한 전체를 강제했다고 주장하지 않고 관측 불가 범위를 표시한다**.

| 필드군 | 의미 |
|---|---|
| run/participant/attempt/epoch/seq | 이벤트 소유권과 순서 |
| role/purpose | 독립 초안·검토·합성·요약·skill 후보 생성 등의 구분 |
| requested/reported provider/model | 설정 희망값과 실제 보고값. 미보고는 unknown |
| usage_value/unit/source/observed_at | 값, 단위, 출처, 시각을 함께 저장 |
| local_invocation vs account_limit | 이 앱의 관측과 계정 전체 잔량을 분리 |
| estimated vs provider_reported | 추정량과 공급자 보고를 섞지 않음 |
| outcome/process_state/verification | 내용 수용, 실행 상태, 근거 검증을 별도로 표시 |

소유권이 없는 이벤트는 현재 작업의 관측으로 만들지 않는다. native protocol이 ID를 생략하는 경우 신뢰된 single-session 연결 경계에서 scope를 붙이는 규칙을 정하고 그 근거를 기록한다. 다중 실행에서 출처를 가릴 수 없는 이벤트는 격리/오류 처리한다.

재생 이벤트가 예산을 두 번 쓰게 하거나, 새 attempt의 이벤트가 이전 draft를 덮어쓰게 하지 않는다. `exit 0`, 다수 모델의 동의, 형식 검사 통과를 `verified`로 바꾸지 않는다. 계정 전체 잔량을 읽는 별도 endpoint가 없으면 unknown이다. 화면을 갱신하려고 LLM을 호출하지 않는다.

## 5. HP-04 — 승인된 스킬의 단계적 로딩

**우선순위:** P1, Gate B 뒤 작은 실험부터. **근거:** [H03](EVIDENCE.md#h03).

최소 catalog에는 ID/namespace, 설명, 적용 조건, 허용 역할·도구, 출처/검토 시각, revision/digest, 검증 절차, 제한을 둔다. 본문과 참조 파일은 허용된 요청에만 반환한다. 단순히 파일을 읽는 것과 script를 실행하는 권한은 분리한다.

| 시험 | 요구 결과 |
|---|---|
| 같은 이름의 project/global skill | namespace 없이 조용히 우선 선택하지 않음 |
| root 밖 경로·symlink·Windows drive 경로 | 허용 root 밖 내용을 반환하지 않음 |
| 실행 중 파일 변경 | 기존 digest와 불일치하면 교체 로딩하지 않음 |
| 이전 단계 cache의 자료 | 새 actor/phase 권한에 맞지 않으면 재사용하지 않음 |
| 필요 없는 archive와 다수 skill | 전체 prompt에 자동 주입하지 않음 |
| skill 지침이 shell/네트워크 권한 요구 | controller 정책을 넘어갈 수 없음 |

처음부터 embedding DB나 학습 router를 추가하지 않는다. 작은 catalog와 명시적 선택으로 품질/입력량을 비교하고 검색 확장의 필요성을 판단한다.

## 6. HP-05 — 권한 있는 원문 recall

**우선순위:** P1. **근거:** [H04–H06](EVIDENCE.md#h04). **선행:** HP-02/HP-03, immutable artifact의 기본 저장/열람.

먼저 원문 ID를 통한 read/scroll 계약을 만든다. 이후 필요하면 SQLite FTS 등을 index로 붙인다. index가 근거 원본이 되지 않게 한다. 검색 결과에는 원래 artifact, revision/digest, 필요한 위치, 잘림 여부, 다음 조회 방법을 붙인다.

봉인된 자료의 권한은 discovery뿐 아니라 직접 ID 조회·parent lineage 확장·export·cache hit에도 동일하게 적용한다. 모델에게 결과를 보낸 뒤 가리겠다는 방식은 허용하지 않는다. undo된 자료, 압축 archive, 실제 새 버전은 구분한다.

한국어·코드 혼합 fixture에는 같은 어근의 다른 형태, 짧은 명칭, 비슷한 파일 이름, 반복적인 자동 로그를 포함한다. 성공 여부는 유명한 검색 알고리즘 이름이 아니라 관련 원문을 찾고 올바른 범위만 열었는지로 판정한다. 전체 원문을 반환할 수 없으면 부분 근거라고 표시하며, 조용히 잘린 내용을 완전한 검토로 보고하지 않는다.

## 7. HP-06 — lesson 후보에서 승인된 skill까지

**우선순위:** P1. **근거:** [H01](EVIDENCE.md#h01), [H03–H04](EVIDENCE.md#h03). **선행:** HP-04와 검증 결과 기록.

```text
candidate
   | 원 실행·증거·실패 범위 첨부
   v
reviewed
   | 회귀 시험 + 독립 검토/사용자 승인
   v
published  ---- 문제 발견 ----> revoked
   |
   +--> 다음 run만 새 revision 사용
```

후보에는 `source_run`, 검증 결과, 성공/실패 조건, 영향을 받는 CLI/version, 변경 diff, 기존 skill과의 관계, 되돌릴 판본을 남긴다. ‘모델이 완료라고 말함’만 근거로 후보를 게시할 수 없다. 게시 API는 일반 worker의 권한에 포함하지 않는다.

새 skill을 평가할 때 사용한 정답·동료 초안이 일반 절차에 섞이지 않는지 검사한다. 현재 실행의 독립 초안은 새 lesson을 역으로 주입받지 않는다. 실패한 판본의 과거 사용 이력은 남긴다. 초기 구현은 자동 작성 없이 사람이/AI가 PR로 후보를 제안하는 방식이어도 충분하다.

## 8. HP-07 — 필요한 MCP만, 발견과 허가를 분리

**우선순위:** P1, 실제 필요한 도구가 있을 때. **근거:** [H14–H15](EVIDENCE.md#h14).

MCP entry에는 서버/실행 source·판본, transport, 도구 allowlist, schema digest, 접근 자원, credential 소유자, 비용/네트워크 정책을 기록한다. 비밀 값 자체는 manifest/Git에 쓰지 않는다. install/bootstrap은 read-only 조회가 아니라 코드 실행이라는 별도 승인 대상이다.

`installed → auth_observed → tools_discovered → permission_conformant → eligible`는 개념상 분리된 관측이며, 단순 일방향 성공 사다리가 아니다. 만료·구성 변경·새 schema가 생기면 적격성을 다시 계산한다. 도구 목록을 못 받았으면 모든 도구를 허용하는 fallback을 만들지 않는다.

동일 이름의 read 도구가 쓰기 부작용을 내는 mock, schema에 도구가 추가되는 경우, 서버의 instructions가 허용 범위를 바꾸려는 경우, headless 승인 timeout을 시험한다. 실제 외부 시스템에 부작용을 내는 시험 대신 소유한 무해한 테스트 자원을 사용한다.

## 9. HP-08 — 역할 슬롯과 조언 주기의 비교 실험

**우선순위:** P2. **근거:** [H11–H12](EVIDENCE.md#h11). **선행:** 기존 cross_check pilot과 전체 회계.

Hermes virtual provider를 그대로 넣기보다 우리 `single/cross_check/deliberate/build_review` 안에서 역할 슬롯·조언 주기를 명시하는 실험을 한다. 매 iteration 조언을 기본값으로 만들지 않는다. 추가 조언의 이득을 비용/시간 증가와 함께 측정한다.

| 비교 조건 | 무엇을 비교하는가 |
|---|---|
| 강한 native 단독 | 기존 하네스의 기본 성능 |
| 같은 총예산의 단독 재검토/복수 초안 선택 | 단순 추가 연산과 협업 구조의 이득 분리 |
| 기존 independent cross_check | 우리 기본 협업 기준선 |
| 명시 슬롯·한정 조언 주기 추가 | Hermes에서 배운 편의/주기가 주는 추가 가치 |

자료 revision, prompt/skill 판본, 참여자, 추론 설정, 허용 도구, 전체 호출/시간/비용 정책을 고정한다. 과제 순서/답안 제시 순서와 평가자의 편향을 통제하며, blind 초기 결과와 최종 결과를 모두 남긴다. provider/model 가용성이 달라지면 같은 구성으로 묶어 평균 내지 않는다.

측정: 수용 가능한 결과당 전체 소비량, wall time, 실제 오류/반례 발견, 잘못된 주장 유입, 합성 중 핵심 반대 근거 손실, 출처 확인 가능성, 사용자 수정 부담. 합의율이나 답변 길이만 성공 지표로 쓰지 않는다. 반복 수·통계 판정은 과제군과 사용 가능한 예산을 정한 후 사전에 고정한다. 제작자 benchmark 수치를 목표 개선률로 미리 박지 않는다.

## 10. HP-09 — 저장소 확장과 복구

**우선순위:** P2. **근거:** [H06](EVIDENCE.md#h06), [H07](EVIDENCE.md#h07).

초기 artifact/journal이 필요한 불변성·재생을 만족한 뒤, 실제 동시 조회/검색/복구 요구가 생기면 SQLite를 추가한다. 서버·메신저를 안 쓰는 단계에서 outbox·다중 계정·모든 history schema부터 복제하지 않는다.

수용 시험: artifact 기록 직전/직후 crash, journal 기록 직전/직후 crash, orphan artifact, digest mismatch, duplicate event, 늦은 child flush, parent 종료, DB 잠김, schema upgrade 실패, replay 후 외부 action 중복 실행 방지. 복구 불가한 실행은 명시적 partial/UNKNOWN 상태로 보존한다.

테스트는 임시 root/DB만 사용하고 사용자의 live history를 건드리지 않게 별도 guard를 둔다. profile 선택에 실패하면 기본 profile로 조용히 돌아가지 않는다. 실제 개인정보 삭제/보존 정책이 필요해지면 audit 보존과 별도로 정한다.

## 11. HP-10 — App Server 선택 전송

**우선순위:** P2. **근거:** [H08–H09](EVIDENCE.md#h08). **선행:** exec 안정화, 동일 runner/visibility/회계 계약.

목표는 현재 exec 선택을 뒤집는 것이 아니라, 명시 thread/turn·native 이벤트·승인·resume가 필요한 작업에서 adapter를 추가할 가치가 있는지 판단하는 것이다. 공식 protocol과 실제 설치 버전의 기능을 구현 시 다시 확인한다. Hermes의 최소 버전 상수나 권한 profile 이름만 근거로 지원을 선언하지 않는다.

비교: 같은 작업의 시작 지연, 이벤트 품질, 사용량 관측, 취소/종료 확인, 재개 정확성, 상태 복구, 문맥/권한 conformance, 추가 유지보수 비용. native 자체 MCP와 controller 노출 도구가 이중 실행되지 않도록 도구 소유자를 명시한다.

같은 조건을 만족하지 못하면 App Server를 기본값으로 승격하지 않는다. exec 경로를 남기되 실패 시 자동 전환은 정책으로 승인된 경우만 허용하고 실제 전송/구성 변경을 표시한다.

## 12. 공통 부정 fixture 목록

아래는 **앞으로 구현할 우리 시스템의 수용 시험**이다. Hermes에서 이 문제가 재현됐다는 보고가 아니다.

| ID | 상황 | 기대되는 거절/보존 |
|---|---|---|
| HF-01 | 다른 참여자 draft가 검색 snippet으로 노출될 상황 | P1에서 조회 차단, scope 위반 기록 |
| HF-02 | parent prefill에 이전 결론 포함 | 입력 manifest/pack 검증에서 배제 |
| HF-03 | 실행 중 skill 교체·동명 shadowing | digest/namespace 불일치, 기존 run 입력 불변 |
| HF-04 | 같은 event 재전달·오래된 epoch | 중복 side effect 없음, 오래된 이벤트 거절 |
| HF-05 | scope 없는 다중 실행 notification | 소유권 확인 전 격리, 현재 run으로 추정하지 않음 |
| HF-06 | timeout인데 텍스트가 정상적으로 보임 | partial output + timeout/UNKNOWN, 정상 완료 아님 |
| HF-07 | root 종료 후 child 생존 | 종료 확인 실패/UNKNOWN, 예산 점유 유지 |
| HF-08 | stderr에 무관한 plugin 인증 오류 | 본 요청 결과와 구별, 비밀 값은 redaction |
| HF-09 | 구독 한도 소진·provider 불가 | API fallback 없음, 명시 구성 축소/BLOCKED |
| HF-10 | peer 공개 뒤 대체 참여자 요청 | 같은 blind cohort에 끼워 넣지 않음 |
| HF-11 | 합성자 실패·요약 실패 | 기존 원문 보존, 제한된 복구 또는 partial |
| HF-12 | usage 누락·만료된 계정 한도 | unknown/stale, 0 또는 무제한으로 보정하지 않음 |
| HF-13 | MCP 도구 추가·schema drift | 명시 재승인/재검증 전 미노출 |
| HF-14 | 승인 응답 재생·기한 만료 | 다른 attempt에 재사용 불가, 기본 거절 |
| HF-15 | memory/skill ‘저장했다’ 텍스트만 반환 | persistence 미완료, readback 이전 확정 표시 금지 |
| HF-16 | summary에서 치명적 반례만 사라짐 | 검증 gate 실패, 원문 연결과 미합의 보존 |
| HF-17 | 허용 자료도 전부 못 읽는 격리 설정 | 유용성 양성 대조 실패, conformance 통과 아님 |
| HF-18 | relay/replay가 외부 action을 다시 실행할 상황 | 상태 재구성만 수행, 부작용 자동 재실행 금지 |

## 13. Rollout·중단·되돌리기

기능은 작은 flag로 하나씩 켠다. 기본값은 없던 기능이 저절로 호출·전송·쓰기 권한을 늘리지 않는 쪽으로 둔다. 초기 스킬 로딩, recall, lesson 후보 생성, 새 전송은 독립적으로 끌 수 있어야 한다.

**중단 조건:** 봉인 정보 누출, 승인되지 않은 쓰기/네트워크/과금, 종료 확인 실패를 성공으로 표시, 원문 소실, 비용 관측 누락을 0으로 표시, 미합의 누락. 이를 품질 평균 향상으로 상쇄하지 않는다. 해당 기능을 끄고 기존 runner·frozen catalog로 되돌리며 관측 기록은 남긴다.

이미 실행된 외부 부작용은 software rollback으로 자동 취소되지 않는다. 쓰기 작업은 별도 승인과 작업별 보상/되돌리기 절차가 필요하다. 그래서 첫 pilot은 읽기 전용이다.

## 14. 다음 구현 PR에 남길 완료 보고

작성 세션/호스트·시작 commit, 변경한 책임과 유지한 책임, 실제 실행한 명령/fixture·CI 링크, skip/미실시 시험, 모델별 실제 입력/출력 형식 관측, 권한·문맥 conformance, 사용량 출처와 미관측 범위, 남은 실패·다음 작업을 기록한다. 비밀 값과 민감 raw trace는 Git에 올리지 않는다.

문서/코드 정적 검토, mock 통과, 실제 native 연결, 외부 사실 검증, 품질 개선은 각각 다른 증거 단계다. 앞 단계를 통과했다는 이유로 뒤 단계까지 완료했다고 보고하지 않는다.
