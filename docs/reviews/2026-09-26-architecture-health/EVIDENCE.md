# 범위·재현·검증 근거

## 무엇을 직접 확인했나

2026-09-26, 현재 Windows PC에서 별도 clone을 읽었다. 제품 기준은 `a232de7d4ae7de097dd014be5a791348b7881ea3`이며 #101 `8fc945d410bec31d7f104199a684e9aab4f5b9a3`와 `app/`, `core/`가 동일하다. main 비교 기준은 `435ba02f50d287f62dce7512a0ceae9b9c2f164b`다. 최신 원격 상태와 이 고정 코드의 관측은 구분한다.

실행 제어/원장, core/허가, 화면/API/launcher를 나눠 소스를 독립 점검하고, 본문에서 교차 확인했다. 이전 리뷰는 현재 동작의 증거로 대신 쓰지 않았다. 특히 `core → tools` 의존, 전체 event tail 조회, 중복 roster 상태 권위라는 예전 설명은 현행 코드에 그대로 적용하지 않았다. 독립 초안 검토에서 “모델 일치가 필수”라는 표현도 `False`만 거절하고 `None`은 허용하는 실제 acceptance에 맞게 좁혔다.

| 증거 | 입증하는 범위 | 입증하지 않는 것 |
|---|---|---|
| 고정 소스·AST·main 대조 | 실제 분기·호출·의존 방향, 기존/신규 구분 | 모든 동적 경로의 도달성·성능 |
| 임시 SQLite + synthetic Executor | controller의 결과 판·실패 기록·slot 투영 | 실제 provider 응답 특성, 모델 품질 |
| Popen/Tree/격리 대역 | 특정 예외에서 정리/예약 함수를 호출하는지 | 실제 OS orphan, WSL containment 재검증 |
| 제품 JS 함수 + Promise 대역 | 응답 순서·조회 실패의 상태 적용 | 실제 브라우저 사용성·네트워크 장애 빈도 |
| launcher 함수 + 임시 파일 + thread 대역 | 허용된 경쟁 순서에서 상태 소유권 상실 | 실제 바탕화면 두 프로세스 부하 실험 |
| 합성 원장 조회 측정 | 데이터 규모에 따른 SQL·payload·함수 시간 | 사용자 원장의 응답 지연·모델 비용 |
| 기존 저장소 검사/CI | 그 suite가 검증하는 계약과 회귀 | 새 발견의 수정 완료, 실제 계정·구독·격리·품질 보증 |

사용자 로그인 HOME, 실제 원장, 실제 모델 CLI와 WSL 설정은 건드리지 않았다. 새 리뷰 probe는 HTTP 서버나 실제 provider subprocess를 시작하지 않는다. Python/Node 및 읽기 전용 Git은 probe 실행과 코드 확인에 사용한다. 기존 전체 suite는 자체 fixture/가짜 CLI/루프백 서버 등을 실행하므로 probe와 별도 검증으로 구분한다.

## 재현 파일

| 파일 | 내용 |
|---|---|
| [probes/run_probes.py](probes/run_probes.py) | 소스 일치 확인 → 단계별 probe 실행 → 결과 기록 |
| [probes/source-manifest.json](probes/source-manifest.json) | 검토 commit의 app/core 파일 SHA256, raw Git blob 기준 |
| [probes/make_source_manifest.py](probes/make_source_manifest.py) | 고정 commit에서 manifest 생성, 실행 전후 파일 변경/추가 확인 |
| [probes/controller-probes.py](probes/controller-probes.py) | 판단 판·합성 저장·폴더 실패 반례 |
| [probes/core-probe.py](probes/core-probe.py) | 스레드 시작 정리, manifest 경쟁, Plan 불변성, 예약 전 검증 |
| [probes/surface_probe.py](probes/surface_probe.py), [surface_probe.cjs](probes/surface_probe.cjs) | launcher·없는 report·화면 응답 순서·생성 영수증 |
| [probes/projection_probe.py](probes/projection_probe.py) | 임시 원장 규모별 조회 측정 |
| [probes/measure_structure.py](probes/measure_structure.py) | AST 함수 크기와 내부 import, JS 파일 크기. 건강성 점수 아님 |

저장소 루트에서 Python과 Node가 있는 환경으로 실행한다. 별도 Python 패키지는 이 probe에 필요하지 않다. 전체 저장소 검사 의존성과는 다르다.

```bash
python -B docs/reviews/2026-09-26-architecture-health/probes/run_probes.py . --output-dir ../architecture-probe-output
```

Node가 PATH에 없으면 `--node /path/to/node`를 추가한다. output은 제품 저장소 밖의 새 디렉터리 또는 빈 디렉터리여야 한다. 생략하면 별도 임시 결과 디렉터리를 만들고 경로를 출력한다. 실행용 임시 SQLite/파일은 정리하고 결과 JSON은 남긴다. 기록된 절대 경로는 실행 위치를 보여 줄 뿐 재현 명령의 필수 경로가 아니다.

**종료 코드 0은 반례가 재현됐다는 뜻이다.** 고친 제품에서 계속 0이 되기를 기대하는 회귀 시험이 아니다. 후속 수정에서는 필요한 반례를 `tests/`로 옮겨 기대값을 정상 동작으로 바꾼다. 제품 코드가 달라지면 통합 runner는 실행 전에 멈춘다. 리뷰 문서만 추가한 후속 commit은 제품 파일이 같으면 실행할 수 있다. 개별 probe를 직접 부르면 통합 소스 가드를 우회하므로 배포된 runner를 입구로 사용한다.

## 보존한 관측

정본 실행 기록은 [probe-run.json](evidence/probe-run.json)이다. Python/Node 버전, 실행 시각, 검토 SHA, 코드 확인, 각 probe 해시와 결과 파일, 종료 코드가 있다. 수정된 임시 제품 사본에서 실행 전 중단되는 가드 확인은 [runner-guard-results.json](evidence/runner-guard-results.json)에 남겼다. 실제 제품 파일은 바꾸지 않았다.

- [controller-probe-results.json](evidence/controller-probe-results.json): AH-01·02·04와 실패 결과의 판단 표시.
- [core-probe-results.json](evidence/core-probe-results.json): AH-03·08, R3/R4 계약 강화 후보.
- [surface-results.json](evidence/surface-results.json): AH-05·07, 없는 decision-report. Python/JS 개별 결과도 같은 폴더에 있다.
- [projection-results.json](evidence/projection-results.json): AH-06의 모든 fixture, SQL 반복 표본과 시간.
- [structure.json](evidence/structure.json): 정적 구조 목록. 함수 행 수는 중첩 함수까지 포함할 수 있으며 실행 복잡도 측정이 아니다.

이 자료의 값은 synthetic 질문·답·모델명과 임시 ID다. 실제 인증 정보·계정·원문 trace는 싣지 않았다. 랜덤 attempt ID와 시간 측정은 재실행마다 달라질 수 있다. 반례 핵심 값은 assert로 확인한다.

## 조회 측정의 조건

모든 원장은 TemporaryDirectory의 SQLite다. MockExecutor와 `max_parallel=0`을 사용해 실제 실행을 하지 않는다. fixture는 bulk SQL로 공개된 실행·수동 답·합성 완료 사건을 채운다. 이는 측정 데이터 준비이며 제품이 지원하는 쓰기 API를 뜻하지 않는다. 각 실행은 별도 task, 수동 답 8,192자 둘, 합성 결과 텍스트 8,192자를 가진다. 합성 이력 증가 사례는 한 실행에 50개 완료 결과를 넣었다.

SQL trace 한 번과 별개로, 예열된 view·JSON 직렬화를 7회 측정해 각각 중앙값을 냈다. SQLite 파일 시스템·Windows·Python 버전의 영향을 받으며 네트워크/DOM/모델 시간은 없다. 보고서 표는 보존한 `projection-results.json`의 값과 일치한다. 전체 응답 크기는 기본 공백을 포함한 `json.dumps(..., ensure_ascii=False)`의 UTF-8 바이트다.

이 fixture의 전체 조회 SELECT는 `9N+6`이고 lifecycle 조회는 `2N+2`다. lifecycle 전체 조회 두 번은 한 실행만 요청할 때도 남는다. 일반 event tail은 이미 제한되어 있으므로 그 비용과 혼동하지 않는다. 기본 live 호출 상한과 원장 교체가 있는 사용을 100-run fixture와 같다고 주장하지 않는다.

## 재현 도구 자체의 수정

통합 포장 뒤 첫 실행에서 launcher probe의 동시 파일 I/O 대역이 불안정하게 assertion에 실패했고, 실패 시 fixture FD 정리도 빠져 있었다. 첫 assertion 실패의 내부 원인까지 확정한 것은 아니며 제품의 두 프로세스 장애 빈도를 입증한 결과도 아니다. probe의 원하는 경쟁 순서를 Event로 고정하고 thread 예외를 수집하며 FD를 항상 정리하도록 고친 뒤 재검증했다. 최종 파일·결과만 정본으로 삼으며, 이 과정 때문에 launcher 문제를 실제 환경에서 재현했다고 격상하지 않는다.

## 저장소 검사

로컬 결과와 전체 suite 로그는 [local-check-results.json](evidence/local-check-results.json), [full-tests.log](evidence/full-tests.log)에 보존한다. Python 3.12.10, jsonschema 의존성을 설치한 전용 venv에서 인코딩·디자인 토큰·frontier·runtime inventory dry-run·v0.1/v0.2 계약·source registry·전체 unittest·compile이 모두 종료 코드 0이었다. 전체 597개 중 538개 통과, 플랫폼 조건의 59개 skip, 실패 0이다. Windows에서 적용할 수 없는 Linux 격리 시험 등을 통과로 세지 않는다. Node는 로컬 v24.19.0이며 PR CI의 Node 22와 구분한다.

문서를 조립하는 도중 시작한 첫 전체 검사는 아직 복사하지 않은 근거 파일의 링크 검사에서 실패했다. 자료와 인계 연결을 마친 뒤 다시 실행한 최종 로컬 결과를 위 파일에 보존한다. 제품 코드 변경으로 해결한 실패는 아니다.

최종 문서/인계 변경은 [PR #104](https://github.com/inlight37-design/decision-model_lab/pull/104)의 정확한 마지막 head에 연결된 `offline-checks`에서 다시 확인한다. PR 본문에 그 head와 CI 링크를 기록한다. 이 리뷰의 오프라인 반례 성공, 기존 suite의 성공, 제품 결함 수정 완료는 서로 다른 주장이다.
