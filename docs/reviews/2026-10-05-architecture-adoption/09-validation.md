# 검증·출처 범위·교차검토·보존 기록

2026-10-05 · 제품 코드 기준 [48ab4bd6f0e297587707aecb83ebc0cd9968892f](https://github.com/inlight37-design/decision-model_lab/commit/48ab4bd6f0e297587707aecb83ebc0cd9968892f) · [PR #184](https://github.com/inlight37-design/decision-model_lab/pull/184)

## 1. 검증 범위

이 검토는 웹 컨테이너에서 공개 저장소 사본과 연결된 GitHub를 읽고 수행했다. 사용자 PC, 해당 PC의 공식 CLI 설치·로그인·기기 관측·계정·브라우저에는 접근하지 않았다. 기존 관측 문서는 그 날짜·기기의 증거로 인용했다. 제품의 구독 CLI를 새로 실행한 횟수는 0이며, 합성 executor의 REAL 표시는 실행 계약 분기를 시험하는 태그일 뿐 실제 provider 호출이 아니다.

로컬 Python은 3.12.14, Node는 v24.19.0이었다. 저장소의 requirements-design.txt로 jsonschema 검증 의존성을 설치했다. 제품 의존성 파일이나 사용자 기기의 설치 상태는 바꾸지 않았다. CI는 자체 설정의 Python·Node·OS를 사용하므로 이 컨테이너와 같은 환경으로 취급하지 않는다. [CI 설정](https://github.com/inlight37-design/decision-model_lab/blob/48ab4bd6f0e297587707aecb83ebc0cd9968892f/.github/workflows/checks.yml)

읽은 코드의 구체적인 파일·함수·줄은 각 상세 보고서의 근거 색인에 있다. 모든 repository blob, 모든 조합의 입력, 모든 상위 프로젝트 코드를 전수 시험했다는 뜻은 아니다. 확정 관측, 합성 반례, 코드로 읽은 누락, 설계 권고, 추가 측정 가설을 본문에서 구분했다.

## 2. 모델 없는 직접 재현

### 실행 계약 — RT-01·RT-04

[02-runtime.md §4](02-runtime.md#4-재현-명령과-결과)의 Python 블록을 기준 코드에서 실행했다. 임시 DB·SyntheticExecutor·합성 RunResult만 사용한다. 담당 분석의 결과를 총괄 세션에서도 다시 실행해 아래 세 결과가 동일함을 확인했다.

| 경우 | 관측 |
|---|---|
| 빈 신규 원장·직접 Controller·cap 없음 | 합성 실행 2회, runtime used 0/cap null, 저장 cap null, 호출 예약 사건 0 |
| 저장 cap 1 이후 runtime setter를 3으로 변경 | 합성 실행 2회, runtime used 2/cap 3, 저장 cap 1, 예약 사건 2 |
| 답 A → turn.completed → 답 B | adapter ok=true, 최종 본문 B, controller acceptance=accepted |

정상 서버/헤드리스 배선의 cap 검증을 우회하는 HTTP 요청을 입증한 것이 아니다. 기존 원장에 cap을 생략해 연결하면 기존 cap을 상속한다. 세 번째는 의도적으로 만든 사건열이며 정상 native CLI가 이 사건열을 내는지는 관측하지 않았다. 이 한정을 제거한 요약은 본 검토의 주장과 다르다.

### 입력·기억·결과 판 — CR-01·CR-02·CR-04

[03-context-and-results.md §5](03-context-and-results.md#5-이번-검증과-남은-미확인)에 임시 DB 조작·핵심 재현과 입력을 기록했다. 총괄 세션도 담당자의 재현 코드를 다시 실행했으며, 경로를 checkout 상대 기준으로 바꾼 [repro_context_results.py](repro_context_results.py)를 보존했다. 저장소 루트에서 python docs/reviews/2026-10-05-architecture-adoption/repro_context_results.py로 실행한다.

| 경우 | 관측 |
|---|---|
| 저장 hash는 보존하고 초안 본문만 변경 | 교차검토 2건 accepted, 변경 본문이 prompt에 포함, 저장 hash 비교는 fresh=true; 같은 상태의 보고서 생성은 거절 |
| 같은 방식으로 취합 입력 확인 | 취합 accepted, 변경 본문이 prompt에 포함 |
| 판단 메모 뒤 새 수정 판 수용 | 공개 화면 reviewed=false, 새 memory pack에는 옛 메모 포함, 적용 판을 명시하는 필드 없음 |
| 수정 답에만 있는 질의 용어와 뒤의 무관한 실행 | matched_runs=0, 수정 실행 미선택, 최근 fallback 사용 |

이는 정상 사용자가 UI로 DB를 임의 변조할 수 있다는 주장이나, 공개 화면이 오래된 판단을 최신 완료로 인정한다는 주장이 아니다. 검색 fixture는 선택 알고리즘의 범위 대조이며 실제 모델의 답 품질 시험이 아니다. 기존 발췌 위치·무관 fallback의 알려진 한계도 새 발견으로 바꾸지 않았다.

### 준비 결과 조회·원장 선택 — WF-01·WF-03

재현 파일 [repro_workflow_projection.py](repro_workflow_projection.py)를 저장소 루트에서 아래처럼 실행한다. 기존 test_refine_mode의 합성 Refiner를 재사용하며 임시 파일은 종료 때 제거한다.

```bash
python docs/reviews/2026-10-05-architecture-adoption/repro_workflow_projection.py --preparations 5
python docs/reviews/2026-10-05-architecture-adoption/repro_workflow_projection.py --preparations 20
```

총괄 세션의 재실행 결과:

| 입력 | task page limit | task/inbox | 응답 크기 | 반복 조회 크기 | cold/warm 조회 |
|---|---:|---|---:|---:|---:|
| 7,800자 한국어 질문의 미연결 다듬기 5건 | 1 | 0 / 빈 목록 | 243,144 bytes | 243,144 bytes | 1.083 / 0.151 ms |
| 같은 다듬기 20건 | 1 | 0 / 빈 목록 | 970,792 bytes | 970,792 bytes | 2.552 / 0.464 ms |

시각·임의 ID 표현 때문에 담당자의 앞 재현과 몇 byte 차이가 날 수 있다. 이 시간은 작은 임시 원장에 대한 Python 조회 함수의 관측으로, 직렬화/전송/브라우저 렌더링과 실사용 원장의 지연을 뜻하지 않는다. warm 재계산이 빠르다는 것과 네트워크 응답 본문이 작아진다는 것은 별개다. 20건은 기본 한 provider 상한을 넘는 스트레스 fixture다.

원장 선택 부분은 cap 10·provider cap Codex 5/Claude 5와 Codex 예약 5개만 담은 최소 SQLite를 만들었다. pick_ledger는 다른 경로를 골랐고 옛 journal.db는 남았다. 실제 제품 원장의 migration, 실제 잔류 프로세스, 계정 전체 한도는 이 fixture에서 시험하지 않았다.

## 3. 기존 검사 실행과 완료 범위

각 결과의 OK/PASS는 해당 로컬 명령의 관측 문자열이다. 제품 전체의 품질·실행 경계가 검증됐다는 판정으로 확대하지 않는다. 최종 PR CI 녹색 여부는 아래 6절의 정확한 head 기준 기록을 사용한다.

| 묶음 | 명령/범위 | 이번 세션 결과 |
|---|---|---|
| 실행 수용 | test_app_contract | 완료, OK, 5 tests, skip 없음 |
| native parser·취소 | test_core_adapters + test_runner_cancel | 완료, OK, 42 tests, skip 없음 |
| 작업·화면·공개 조회 | test_workflow, test_pages, test_templates, test_api_client, test_query_projections, test_role_board_render | 각 기존 모듈 완료, OK, skip 없음. 실제 브라우저 조작은 아님 |
| 문서·축적 방지 | test_research_integrity + test_accumulation | 로컬 완료, OK. 최종 파일 집합도 원격 CI에서 검사 |
| 디자인 토큰 | python tools/validate_design_tokens.py | 완료, PASS; 시각 디자인 평가 아님 |
| v0.1 계약 | python tools/validate_design.py | 완료, 25/25 offline checks |
| v0.2 pilot/proof | python tools/validate_v02.py | 완료, PASS; 합성 데이터 결속 범위 |
| 출처 원장 schema | python tools/validate_sources.py | 완료, PASS; URL의 현재 가용성/원문의 진실성 보증 아님 |
| 인코딩 | python tools/check_encoding.py | 완료, PASS; BOM 없는 UTF-8·제어 문자 검사 |
| 컴파일 | python -m compileall -q tools tests core app 및 이 폴더의 재현 파일 | 완료, 종료 0 |
| 문서 연결·근거 위치 | 새 보고서 상대 파일/앵커·reference·기준 코드 줄 범위의 일회 검사 | 오류 없음; 원문의 의미·외부 URL 현재 가용성 검증을 대신하지 않음 |
| frontier 기록 | python tools/check_frontier_protocol.py | 완료, PASS; 기록 일관성 범위 |

런타임 담당의 정확한 timeout·faulthandler 명령과 결과는 [02 §4](02-runtime.md#4-재현-명령과-결과), 흐름 담당의 명령은 [04 §7](04-workflow-and-ui.md#7-이-세션의-검증과-재현-방법)에 있다. 문서 검사는 PYTHONPATH=.:tests에서 unittest의 두 모듈을 지정해 실행했다. 검사 수는 이 날짜의 실행 기록이며 살아 있는 안내에 재기재하지 않는다.

### 완료하지 못한 로컬 전체 suite

총괄의 python -m unittest discover -s tests -v는 수집 중 출력 없이 대기해 중단했다. 이 첫 실행 자체에서는 stack을 확보하지 않았으므로 특정 시험의 실패로 단정하지 않는다. 별도로 런타임 담당이 test_synthesis_lifecycle·test_claude_limits를 포함한 묶음을 실행했을 때 import 사슬이 test_app_cli_executor.bwrap_usable의 timeout 없는 subprocess.run에 머무르는 stack을 확보했다. 자세한 stack과 종료 조건은 02에 보존했다.

따라서 로컬 전체 suite, test_synthesis_lifecycle, test_claude_limits를 완료 목록에 넣지 않았다. 제품 격리를 해제하거나 시험의 skip을 pass로 바꾸지 않았다. 작은 도구 후속은 capability probe의 대기 상한과 import 단계 분리이며, 실제 bubblewrap·Poppler 검사는 CI의 기존 필수 gate에서 확인한다. 이 컨테이너의 제약을 사용자 PC 고장으로 해석하지 않는다.

## 4. 후보 누락 검사와 외부 1차 출처

기준 후보 파일은 docs/architecture/redesign-2026-10-04/capability-map.json이며 해당 바이트의 sha256은 08 JSON에 기록했다. 원본 JSON·원본 표·결과 JSON·결과 표의 118개 ID를 대조해 누락·중복·추가가 없음을 확인했다. 원래 순서·제목·조사 URL을 보존했고, 후보의 코드 근거·관련 ID·검증 게이트 연결을 검사했다. JSON과 Markdown은 같은 판단을 표현한다. [매트릭스](08-capability-matrix.md), [기계 판독 파일](08-capability-matrix.json)

원래 118개는 서로 중복되는 기능 후보다. 이 수를 독립 제품 수, 전체 upstream 기능 수, 코드 완성률, 미래 품질 향상률로 사용할 수 없다. 검증 게이트는 후속 구현의 합격 조건이며 이번에 그 기능을 구현·통과시켰다는 뜻이 아니다.

| 이번에 직접 다시 읽은 외부 출처 | 구체적인 범위의 기록 |
|---|---|
| Hermes·AnchorMind·codex-peek·WorkTrail의 고정 SHA 파일 | [05의 출처별 판단과 근거](05-memory-adoption.md) |
| tmux·Beads·Backlog.md·Gas Town·Cline·Lite-Harness·Symphony의 고정 SHA 파일 | [06의 1차 출처 색인](06-operations-adoption.md) |
| LangGraph 공식 Persistence 문서 | [06](06-operations-adoption.md); rolling 문서로 SHA 없음과 조회일 명시 |

11개 저장소의 지정 파일/줄을 재확인한 것이다. upstream 전체 파일이나 최신 release의 실행 호환성을 시험하지 않았다. 다른 제품군은 06의 별도 표에서 기존 조사만 대조했다고 표시했다. Beads는 기존 주소의 301 응답과 repository ID로 gastownhall/beads의 정식 경로를 확인해 같은 고정 SHA를 읽었다. 이전 날짜의 옛 주소 기록을 덮어쓰지 않았다. 이번 검토에서 upstream 실행 코드를 복사하거나 새 source registry 항목을 만들지 않았다.

## 5. 교차검토와 반영한 정정

문서 작성은 실행·문맥·워크플로우·기억 계열·운영 계열·후보 매트릭스로 나눠 읽고 총괄이 합쳤다. 이 분담은 ChatGPT 문서 분석 과정이며 제품 앱 안에서 수행한 native 다중 모델 실험이 아니다. 별도의 모델/추론 강도 override는 요청하지 않았고 상위 설정을 상속했다. 외부에 독립적으로 보고된 추론 강도 값은 없으므로 strong/medium 등의 관측값을 만들어 적지 않는다.

교차검토의 제품 기준은 공통으로 48ab4bd6f0e297587707aecb83ebc0cd9968892f다. 초안 보고서는 같은 작업 브랜치의 작성 중 파일로 검토했고 01–07의 중간 상태는 아래 세 번째 commit으로 보존했다. 최종 문서의 무오류나 모델 간 독립성을 이 절차만으로 보증하지 않는다.

반영한 중요한 교정:

- 기존 원장의 cap 미지정은 거절이 아니라 기존 cap 상속이다. cap 없는 재현은 빈 신규 원장으로 한정했다.
- model_match=False의 거절과 None의 미확인을 구별했다. 모든 모델 일치를 관측한 것처럼 설명하지 않았다.
- 원장 교체 시 확인 대상에 이번 원장뿐 아니라 이미 알려진 더 오래된 미해결 원장도 포함하도록 권고했다.
- invocation의 queued→running CAS와 다중 worker의 lease·heartbeat 작업 배정을 구별했다.
- 앱의 읽기 전용 참여자와 개발 운영의 한 writer 원칙을 구별했다.
- 현재 설치/인증/문맥/권한의 기기 관측 체계와 아직 없는 세부 resume/steer/stream 지원표를 구별했다.
- GR-1의 일반 검토와 GR-2의 일반 수정/재검토 범위를 다시 나눴다. 수정 검색의 재현된 누락 보완과 측정 후 ranking/발췌 튜닝도 나눴다. 원장 선택 시점은 예산 소진 즉시가 아니라 다음 앱 시작 때임을 종합 요약에 명시했다.
- 연속 reference 표기와 일부 표제·링크를 고쳤다. 원문 근거를 늘리지 않고 표현상의 과장을 줄였다.

현재 안내의 정정은 app/README.md와 NEXT-SESSION.md의 Claude 계정 한도 범위다. 종전의 “마지막으로 끝난 실제 실행”은 모든 역할을 포함하는 듯 읽혔지만, 현재 저장/조회 경로는 상위 역할의 한도 관측을 반영하지 않는다. 해당 원본 안내에 현재 범위를 적고 RT-03으로 연결했다. 실행 코드와 과거 관측 기록은 변경하지 않았다.

## 6. 원격 보존과 최종 판 확인

| 원격 commit | 보존 내용 |
|---|---|
| [34fea9f4c74dc26f11c0f42247cc68a3675f7bda](https://github.com/inlight37-design/decision-model_lab/commit/34fea9f4c74dc26f11c0f42247cc68a3675f7bda) | 기준 SHA·접근 범위·사용자 결정·검토 방법 고정 |
| [b15e8f240aec599739ae9a91ebd26e5260978ff2](https://github.com/inlight37-design/decision-model_lab/commit/b15e8f240aec599739ae9a91ebd26e5260978ff2) | 구조·실행·문맥/결과 판의 첫 분석과 합성 재현 |
| [cb8701c12f6cca844bc6fcf6b40082c8d40b567a](https://github.com/inlight37-design/decision-model_lab/commit/cb8701c12f6cca844bc6fcf6b40082c8d40b567a) | 워크플로우·외부 출처/이식·구현 순서와 재현 파일까지 보존 |

이후 종합 문서·후보 대조·최종 검증·현재 인계의 최종 commit은 [PR #184의 commit 목록](https://github.com/inlight37-design/decision-model_lab/pull/184/commits)에서 확인한다. 문서가 자기 commit SHA를 포함하면 commit이 다시 바뀌므로, 최종 head와 그 head의 CI run/job 결과는 PR 본문에 기록한다. [PR Checks](https://github.com/inlight37-design/decision-model_lab/pull/184/checks)는 정확한 최신 head를 기준으로 확인해야 한다.

일반 git push는 웹 컨테이너에서 인증 자격을 얻지 못해 실패했다. 그 로컬 commit을 원격 보존 완료로 세지 않았다. 연결된 GitHub의 Git object API로 tree→commit→검토 브랜치 ref를 순차 갱신했고, 해당 브랜치를 다시 fetch해 로컬 파일과 원격 tree를 대조한다. main에 직접 push하거나 다른 세션 브랜치를 변경하지 않았다.

보고서는 새 날짜 폴더에, 현재 진입점은 reviews 인덱스와 인계에 연결한다. 제품 파일 변경은 없으며 현재 상태를 정정한 app/README.md도 설명 문서다. 최종 CI와 검토 결과를 확인한 사용자 또는 저장소 규칙상 병합 담당 세션이 후속 판단할 수 있다. 이 문서가 병합을 미리 선언하지 않는다.
