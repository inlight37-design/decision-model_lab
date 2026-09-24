# PR #31 독립 안전성 재검토 — 2026-09-24

작성: ChatGPT 웹 세션. 후속 작업은 [PR #32](https://github.com/inlight37-design/decision-model_lab/pull/32), 브랜치는 `chatgpt/pr31-safety-review-20260924`다. [시작 체크포인트](CHECKPOINT.md)를 먼저 원격에 저장한 뒤 회귀시험을 추가했다.

## 결론

검토한 PR #31 변경과 그 주변 실행 계약·허가·진단 경로에서 **새로운 병합 차단 결함은 재현하지 못했다.** 이것은 저장소 전체의 무결함, 실제 모델의 문맥 독립성 또는 실서버 운용 준비를 보증하는 판정이 아니다. PR #31의 변경 방향은 타당하며, 이 후속 작업은 빠졌던 실패 경계의 회귀시험과 인계 구분을 보완한다.

**제품 실행 코드·의존성·아키텍처는 추가 변경하지 않았다.** 가짜 실행기로 문제를 확인하지 못한 상황에서 보호 장치나 추상화 계층을 더 얹지 않았다. 실제 모델 호출은 0회이고, 승인·예산·manifest·LEGACY 대응·main 보호 설정을 변경하지 않았다. 실제 서버 연결(순서 6)도 완료로 바꾸지 않았다.

## 기준과 접근 범위

| 항목 | 직접 확인한 기준 |
|---|---|
| main | `56bf5afcce385b8bec33f118421428af99944534` |
| PR #31 | `781412063bb7817062edd14609c5a167e3dcc003`, 시작 시 open·미병합 |
| 추가 시험 코드 | `b7d473bbdd60db84d51637f6938c57f39dfa1f46` |
| 접근 | GitHub 연결 도구로 원문·diff·PR·branch·CI를 읽고 별도 브랜치에 썼다. 웹 컨테이너에서는 추가 시험 파일의 문법 검사만 했다 |
| 접근하지 않은 것 | 사용자 PC의 Windows/WSL, 설치 CLI와 로그인, 실제 브라우저, 사용자가 붙인 PC 전용 보고서. 기존 PC 관측 기록은 그대로 보존한다 |

웹 컨테이너의 git clone은 DNS 오류로 실패했다. 따라서 로컬 전체 체크아웃·전체 시험을 했다고 쓰지 않는다. 전체 시험의 실제 실행 근거는 아래 GitHub Actions다. PR #31의 discussion 조회에는 기존 댓글이 없었다. 최종 병합 전에는 head와 리뷰/CI 상태를 다시 확인해야 한다.

## 대조 결과

| 구분 | 판단과 처리 |
|---|---|
| 실행 허가 철회 | PR #31의 `CliExecutor.run()`이 현재 기록을 다시 읽는 수정을 확인했다. 같은 계획을 실행하면서 허가만 재검사하는 방향을 유지한다. 기록 삭제·손상·만료 등도 시작을 막는지 추가 시험으로 보완했다 |
| 자료 연결 개수 | `core.contract.template()`이 mount 역할을 set으로 합치지 않고 목록의 중복 개수를 보존한다. K46의 자료 폴더 하나 관측을 여러 폴더의 허가로 넓히지 않는다. 기존 단일 자료 LEGACY 대응을 변경하지 않았다 |
| stdin과 옵션 기록 | 입력을 argv로 전달할 때만 질문 digest에 맞는 인자를 가린다. stdin 질문이 옵션 문자열과 같아도 실제 옵션 기록과 계약 지문을 보존한다 |
| 실행 종류 표시 | 화면 행이 저장된 시도의 mock/real/synthetic 종류를 읽는다. 현재 서버는 모의 전용이므로 실제 실행기 연결이나 실제 모델 합성 완료로 해석하지 않는다 |
| 무모델 조회와 진단 | readiness 조회는 실행 승인·호출 예산이 아니고, preflight의 준비 성공도 실행 허가가 아니다. `assess()`는 완전한 동일 판의 결과가 있어도 전송 증거만 지원하고 문맥·권한은 불충분으로 남긴다 |
| Q4 첫 화면 | 전달된 요약의 “A 확정”과 저장소의 “A 권고·사용자 선택 미확정”은 다르다. 이번 요청은 그 권고에 대한 명시적 선택이 아니므로 사용자 결정 절을 바꾸지 않았다. A 권고와 B 전환 유지, 선호 확정은 별개다 |
| main 보호 | branch API에서 protected=true, Python 3.12·3.13 필수 검사, Actions app_id=15368, enforcement_level=everyone을 확인했다. 세부 protection API는 이 연결에서 403이므로 전체 상세 설정을 이번 세션이 독립 재조회했다고 주장하지 않는다. PR #31의 PC 세션이 남긴 상세 설정·재조회 근거는 보존한다 |

main 보호의 승인 인원 0은 앞서 선택한 설정이지 이번에 발견한 구현 결함이 아니다. 다만 CI 성공은 독립적인 사람/다른 세션의 검토 자체를 강제하지 않는다. 사용자 또는 허락받은 Claude 세션이 검토 후 병합하는 협업 규칙은 계속 필요하다. 이 검토는 보호 설정을 완화하거나 재설정하지 않았다.

## 추가한 오프라인 회귀

[`tests/test_pr31_safety_review.py`](../../../tests/test_pr31_safety_review.py)는 초기 계획이 정상 허가된 뒤의 변화만 별도로 검사한다. 실제 CLI 대신 resolver·mount·실행 경계를 모의 처리하며, 차단 경로에서 `isolation.run()`이 호출되면 실패한다.

- **기록을 더 이상 신뢰할 수 없는 경우:** 파일 삭제, 깨진 JSON, 잘못된 UTF-8, null/배열/잘못된 schema, 중복 adapter.
- **관측이나 실행 환경이 바뀐 경우:** unknown/failed 칸, 빈 근거, 미래 관측일, 관측 만료, 명세 판 변경, 기록 버전 변경, 구독에서 API 과금으로의 변경, 실행 직전 실제 버전 변경/미확인.
- **양성 대조:** 유효한 현재 기록에서는 원래 계획을 다시 만들지 않고 정확히 한 번 실행한다. argv·입력·격리 경계·timeout·취소 신호·stderr 표식이 그대로 전달돼야 한다. 무조건 거절하는 구현은 이 시험을 통과할 수 없다.
- **증거 누락:** 정상 전송 요약의 필수 최상위 필드를 하나씩 빼면 전송 observed를 주지 않는다. 모델 자기 보고나 빈 tools/skills 목록을 더해도 문맥·권한·실행 허가를 승격하지 않는다.

이 시험들은 코드가 기록된 정책을 집행하는지 확인한다. manifest의 관측 주장이 사실인지, CLI가 실제로 개인 메모리를 제외하는지, 모델 출력이 정확한지는 증명하지 않는다.

## CI 근거

| 대상 | 정확한 head | 확인한 push CI |
|---|---|---|
| 원래 PR #31 | `781412063bb7817062edd14609c5a167e3dcc003` | [35972635875](https://github.com/inlight37-design/decision-model_lab/actions/runs/35972635875): Python 3.12·3.13 job 및 전체 시험·compile 단계 success |
| 추가 회귀 코드 | `b7d473bbdd60db84d51637f6938c57f39dfa1f46` | [35974593477](https://github.com/inlight37-design/decision-model_lab/actions/runs/35974593477): completed/success |

CI의 full test suite는 `DML_REQUIRE_BWRAP=1 python -m unittest discover -s tests -v`로 실행된다([워크플로](../../../.github/workflows/checks.yml)). 추가 시험이 임의의 별도 실행 목록에만 남지 않고 기본 discover에 포함된다. 사용자 PC의 Windows/WSL 재실행으로 바꾸어 표현하지 않는다. 위 표는 시험 코드 커밋까지의 근거이며, **최종 문서·인계 head의 별도 CI 결과는 PR #32 본문/검토 댓글에 정확한 SHA와 함께 남긴다.**

## 문맥 독립성: 다음에 확인할 것

기존 [C3 관측](../2026-09-24-cli-readiness/GITHUB-C3.md)은 `debug prompt-input`과 app-server 목록을 구분하고, 둘의 합집합을 exec 최종 요청이라고 부르지 않았다. 그 보수적인 결론을 유지한다.

공식 [Developer commands의 prompt-input 설명](https://learn.chatgpt.com/docs/developer-commands#codex-debug-prompt-input)과 [App Server의 instructionSources 설명](https://learn.chatgpt.com/docs/app-server)을 2026-09-24에 직접 읽었다. 전자는 모델에 보이는 입력 목록을 렌더링하는 진단이고, 후자는 thread 시작/재개/분기의 로드된 지시문 파일 경로다. 문서에서 이 설명을 확인한 것과 현재 설치판의 exec와 동일한 최종 요청이 만들어진다는 실측은 다르다. 이번에는 CLI나 thread를 시작하지 않았다.

다음 작업은 호출 횟수 확대가 아니라 **이미 있는 진단이 정확히 무엇을 관측하는지 확인하는 것**이다. 같은 설치판·계획·실행 옵션·설정 경계에 적용되는 증거인지 대조하고, 합성 개인 지시문·메모리 표식을 넣은 양성 대조에서 관측되는 경로와 제거한 음성 대조를 비교한다. 최종 문맥 또는 그 생성 경로를 충분히 보지 못하는 항목은 그대로 미확인으로 남긴다. 개인 데이터 원문 대신 합성 표식, 적용 옵션, 입력/출력 종류와 제한만 공유한다.

이후에도 전송·문맥·권한은 각각 증거를 요구한다. 다른 revision의 stream 진단을 controller의 json 참여자 허가에 재사용하지 않는다. 해당 선행 증거와 사용자 승인 범위가 마련되기 전에는 실제 서버를 unchecked 실행기에 연결하거나 모델을 반복 호출하지 않는다. 새 도구/프로토콜/하네스를 더 만드는 것으로 이 증거 부족을 대체하지 않는다.

## 인계와 병합

[PR #31](https://github.com/inlight37-design/decision-model_lab/pull/31) → [PR #32](https://github.com/inlight37-design/decision-model_lab/pull/32) 순서로, 병합할 시점의 정확한 head CI와 충돌 유무를 다시 본다. 두 PR 모두 main 대상이며, 다른 세션의 브랜치에는 쓰지 않는다. #31 head가 이후 바뀌면 #32가 그 변경을 포함하는지 다시 대조해야 한다.

이 세션은 병합하지 않는다. 명시적으로 허락받은 병합자가 인계 3절의 열린 상태를 실제와 맞추고, 변경했다면 새 head CI를 확인한 뒤 병합한다. 기존 사용자 결정(2절)·금지 사항(5절), C3 failed, 남은 호출 예산을 보존한다. merge 후 브랜치 정리는 협업 규칙대로 병합자가 수행한다.
