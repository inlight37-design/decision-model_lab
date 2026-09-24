# 순서 5 실행 계약(G4·G6) 구현 — 2026-09-24

작성: claude 세션, 사용자 PC `aux-pc`의 Windows Python 3.12.6과 WSL `aux-pc-wsl` Ubuntu-24.04 Python 3.12.3. 모델 호출·실제 인증 폴더 연결은 하지 않았다. 사용자가 이 세션에서 GPT(codex) 세션의 권고 "실행 계약 정리"를 포함한 다음 일을 진행하라고 했다. 설계는 [병합 뒤 재검토](../2026-09-24-post-merge-verification/README.md)의 제안 1–4를 따랐다. 시작 main은 `af474278bb9031a9e5d52c3778b23f27db3f0f8f`다.

## 무엇이 틀려 있었나(재현)

- **G4.** `describe()`와 `execute()`가 계획을 따로 만들었다. 관측 도구는 `prepare()` 뒤에 argv를 바꿨다(b1의 stream-json, `--keep-session`, P3의 틀린 값). 판은 손으로 쓰는 `SPEC_REVISION`이었다. 그래서 공통 자료가 있든 없든, 출력 형식이 무엇이든 같은 `discussant-1`이었다.
  - 기록의 Claude 관측은 2단계 b1이다(stream-json·Read 도구·공통 자료). controller는 json·`--tools ""`·자료 없음으로 부른다. 그런데도 두 계획이 같은 판으로 셌다.
- **G6.** 화면은 모든 CLI 참여자에 "모의 CLI — 모델 호출 없음"을 붙였다. 보고서의 출처는 지금 controller에 붙은 실행기 이름이었다. 과거 시도가 무엇으로 돌았는지는 보지 않았다.

## 바꾼 것

| 범위 | 주인 모듈 | 부류 제거·국소 수정 | 내용 |
|---|---|---|---|
| 최종 계획 | [`core/contract.py`](../../../core/contract.py) (새로) | 부류 제거 | `Plan`이 최종 argv·입력·격리 경계·요청 모델·stderr 표식·실행 종류·판·변형 목록을 고정한다. `record()`에는 질문 본문이 없다 |
| 판 | `core/contract.py` | 부류 제거 | 계획의 틀에서 계산한다. 실행 파일 경로·모델·HOME·자료 경로·질문은 역할(`<exe>`, `<model>`, `<home>`, `<input>`, `<prompt>`)로 바꾼다. 출력 형식·도구·권한 profile·세션 보존·연결 역할과 ro/rw·stderr 표식은 남긴다. `SPEC_REVISION`은 없앴다 |
| 옛 판 대응 | `contract.LEGACY`, `core/eligibility.py` | 명시적 대응 | 실행 허가는 기록의 판이 지금 계획의 판과 같거나, 검토해 대응시킨 옛 이름일 때만 그 관측을 쓴다(`contract.covers`). 계획 없이 계산하면(판 없음) 판이 맞는 관측이 없다 |
| 실행기 계약 | `app/cli_executor.py`, `app/controller.py` | 부류 제거 | `plan()` → 기록 → `run(plan)`. controller는 계획 기록과 실행 종류를 시도 ID와 함께 저장한 뒤에만 실행한다. 계획이 거절되면 아무것도 시작하지 않고 `failed_to_start`다. 실행 허가도 계획의 판으로 계산한다 |
| 관측 변형 | `tools/w2/observe.py`, `codex_profile.py` | 부류 제거 | 변형을 계획을 만들 때 넣는다. 요약의 `spec`은 실제로 돈 계획이고 판은 변형을 반영한다. `plan` 명령도 probe별 판을 보인다 |
| 실행 종류 | `app/store.py` 스키마 5, `app/controller.py`, `app/report.py` | 부류 제거 | `participants.kind`에 mock/real/synthetic을 저장한다. 화면 표시와 보고서(`a1-draft-report/3`의 참여자 `execution`)는 이 값을 읽는다. controller는 모의 실행기의 `FLAVOR` 대신 실행기가 알리는 `adapter_ids`로 참여자를 받는다 |

## 옛 증거를 어떻게 대응시켰나

대응은 "최종 argv와 연결이 실제로 돈 계획과 같은가"만 봤다. 비슷한 것은 대응시키지 않았다.

- **Codex `discussant-2` → `codex@8a0128d4c791`만.** K46(2026-09-24)이 이 계획으로 돌았다. WSL에 보존된 원 결과에서 argv 필드만 읽어 대조했다. `argv_run`이 참여자 argv와 같고 `argv_changes`는 비었다. 공통 자료 하나가 읽기 전용으로 연결됐다. 자료 없는 controller 계획은 연결이 하나 적지만 같은 계획이 아니므로 대응시키지 않았다. 필요하면 동등성 근거와 함께 `LEGACY`에 더한다.
- **Claude `discussant-1` → 없음.** b1은 stream-json 출력·Read 도구·공통 자료로 본 변형이다. 지금의 어느 참여자 계획과도 같지 않다.
- 결과는 이렇다. 기록된 Claude 관측으로는 더 이상 허가가 나오지 않는다. Codex는 원래 문맥(C3) 때문에 허가가 없었다. 서버는 모의 실행기만 쓰므로 지금 막히는 기능은 없다. 실제 연결(순서 6) 전에 Claude를 controller 계획 그대로 다시 관측해야 한다.

## 설계만 한 것

- **공통 자료 첨부.** 실행을 만들 때 자료 파일을 controller 소유 폴더로 복사한다. 파일별 sha256 목록을 실행에 고정한다. 모든 CLI 참여자에게 같은 폴더를 읽기 전용 `input` 연결로 준다(Claude는 `--add-dir`·Read, Codex는 연결만). 자료 유무가 판에 들어가므로 자료 있는 계획은 그 판으로 관측해야 허가된다. 구현은 서버 연결 뒤 화면 작업과 함께 한다.
- **Claude 재관측 probe.** b1은 변형이라 참여자 계획의 근거가 되지 못한다. 문맥을 init 이벤트로 보려면 참여자 계획 자체를 stream-json으로 바꾸는 안이 있다. 해석기가 마지막 result를 읽으면 되고, 그러면 관측과 실행이 같은 판이 된다. 결정은 재관측 승인 전에 한다.

## 검증

- Windows `python -m unittest discover -s tests`와 WSL `DML_REQUIRE_BWRAP=1 python3 -m unittest discover -s tests`로 전체 시험을 돌렸다. 실제 bubblewrap 경로에서 가짜 CLI로 실제 실행기와 관측 도구를 돌리는 시험도 포함된다. OS 전용 skip은 구분했다.
- 새 시험은 이렇다.
  - [`test_core_contract.py`](../../../tests/test_core_contract.py): 시도마다 바뀌는 값은 판을 바꾸지 않는다. 자료·출력 형식·세션 보존은 판을 바꾼다. 옛 판 대응은 정확한 계획만 가리킨다.
  - [`test_app_contract.py`](../../../tests/test_app_contract.py): 계획 한 번과 같은 객체 실행, 거절된 계획, 실행기가 바뀐 재시작 뒤의 표시, 스키마 4→5 이전과 복원·미상 구분.
- 실행 허가 시험을 바꿨다. 커밋된 기록 둘(2단계, K46)이 지금 계획의 어떤 판을 뒷받침하는지 이유 문자열까지 고정했다.

## 브라우저 끝단 확인(K27 잔여)

codex 세션은 내장 브라우저 도구의 제약으로 취소 확인창과 파일 다운로드를 확인하지 못했다. 이 세션은 설치된 Edge 153.0.4234.48을 Playwright 1.63.0(`channel="msedge"`, headless)으로 조작했다. Playwright는 저장소 밖 임시 가상환경에 설치했고 브라우저는 새로 받지 않았다.

- 대상은 이 브랜치의 코드다. 새 임시 데이터 폴더로 모의 서버(Windows job object)를 띄웠고, 기존 원장은 열지 않았다.
- 실행 둘을 API로 만들었다. 수동 참여자 하나(`include_unverified`, 최소 1)에 합성 문자열 답을 넣어 공개한 실행과, 대기 중인 실행이다. 모델 호출은 없다.

| 확인 | 결과 |
|---|---|
| 원문 보고 버튼 | 실제 파일 저장(`…-without-synthesis.json`). `a1-draft-report/3`, 초안 원문과 sha256이 넣은 답과 일치, 수동 참여자의 `execution`은 null, 출처 키는 `run_id`·`created_at`·`phase`뿐 |
| 모의 합성 → 결정 보고 버튼 | 실제 파일 저장(`…-decision.json`). `a1-decision-report/1`, 합성 `completed`, 주장 2개, 안의 원문 보고는 판 3 |
| 취소 확인창 | `confirm` 대화상자를 거절하면 `cancel_requested=false`, 수락하면 `true`와 gate `cancelled`. 화면에 "취소 요청 저장됨"과 시작 전 취소가 보였다 |
| 페이지 오류 | 없음 |

headless 조작은 사람이 누른 것과 같지 않다. 다른 브라우저·접근성·좁은 화면의 새 확인은 하지 않았다.

## 하지 않은 것

- 모델 호출, 기록(manifest)의 관측값 변경, 실제 서버 연결(K17), 공통 자료 첨부 구현, 화면 변경.
- 운용 PC, 교차 브라우저.
