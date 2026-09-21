# v0.2 — 사례에서 배워 구체화한 저비용 협업 설계

**2026-09-21 / 현재 제안.** 사용자의 후속 요청에 따라 실제 성과와 공개 사양·코드를 조사하고 v0.1을 다듬었습니다. 성과 표의 숫자는 외부 연구/제작자의 결과이며 이 저장소의 실측이 아닙니다.

## 먼저 읽는 순서

[01. 사례 연구](01-case-studies.md) → [02. 구체 설계](02-concrete-blueprint.md) → [03. 실험과 백로그](03-experiments-and-backlog.md)

핵심 근거는 다음과 같습니다. 상세 출처·버전·한계는 01에 있습니다.

| 배울 대상 | 이번 설계에 반영한 것 |
|---|---|
| Cursor Router / Switchyard | 실제 작업 결과로 선택을 평가하고 전환·judge 비용까지 계산 |
| 서로 다른 Switchyard 실험 | 고가 대비 절감뿐 아니라 저가 단독 대비 추가 이득도 평가 |
| SWE-Pruner / JevGrep | 원본 코드와 행을 보존하는 read-only 선택부터 시험 |
| Symphony | 기존 작업 실행/세션/재조정 구조를 먼저 재사용 검토 |
| mini-swe-agent | 하네스가 고정된 경제성 대조 실험 |
| Attractor / 대규모 agent 실험 | 자유로운 회의 대신 고정된 실행 절차·독립 검증·한정된 수리 |

## 설계의 구체 모습

```text
승인된 task + 기준 snapshot
           │
     manifest / 정책 검사
           │
  기존 실행기에서 worker 하나
           │
  원문 참조 + patch 후보 + usage
           │
 독립 verifier가 실제 후보에 결합한 증거
           │
       REVIEW_READY
           │
          사용자
```

실제 운영 경로와 경제성 실험 경로를 분리합니다. 전자는 기존 하네스를 유지하고, 후자는 모델·문맥·router만 바꾸어 효과를 비교합니다. 공통 계약을 사용하되 서로 다른 하네스를 동일 조건의 모델 비교라고 부르지 않습니다.

초기 작업 절차는 `bounded_patch` 하나입니다. 사전 검사 → 문맥 선택 → 구현 → 검증 → 최대 한 번의 수리 → 검토 인계로 한정합니다. 자동 merge·배포는 없고, Jev와 원격 의미 검색은 예제 설정에서 비활성입니다.

## 실제로 추가한 것

사례 연구, v0.1 변경표, 구체적인 실행/증거 계약, 코드·사양의 재사용 지도, 비교 실험군, 구현 ticket 8개를 작성했습니다. 추가로 [합성 pilot 계약](../../../contracts/v0.2/README.md)과 검사기를 넣었습니다.

```bash
python tools/validate_v02.py
python -m unittest discover -s tests -p 'test_v02.py' -v
```

v0.2의 28개 오프라인 검사를 실행·재실행하여 통과했습니다. 검사 파일 5개의 Git blob을 원격 tree와 대조했습니다. 자세한 결과는 [VALIDATION](VALIDATION.md), 커밋과 인수인계는 [WORKLOG](WORKLOG.md)입니다.

## 아직 없는 것

실제 task resolver, 하네스 adapter, verifier 프로세스, 권한 sandbox, 모델 연결, 비용 제한 강제, 장기 복구, 실제 절감률은 구현/실험하지 않았습니다. `passed`라고 적힌 fixture는 합성 데이터이며 실제 코드 테스트 PASS가 아닙니다.

다음 실제 구현 단위는 03의 V02-01–04입니다. 먼저 한 작업의 manifest와 독립 검증 증거를 연결하고 고가/저가 단독을 비교합니다. 데이터를 보기 전에 router·메모리 DB·다중 manager를 한꺼번에 추가하지 않습니다.
