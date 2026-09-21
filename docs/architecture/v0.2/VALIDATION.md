# v0.2 검증 기록

기준일 2026-09-21. **외부 모델 성능 재현이 아니라 이 저장소에 새로 작성한 합성 계약의 검사**다.

## 실제 실행

환경: 작업용 Linux 컨테이너, Python 3.13.5, jsonschema 4.26.0.

```text
python tools/validate_v02.py
PASS: synthetic pilot and proof bindings are internally consistent.

python -m unittest discover -s tests -p 'test_v02.py' -v
Ran 28 tests
OK
```

JSON 표현을 compact하게 저장한 뒤 같은 검사와 unittest를 다시 실행해 28개 모두 통과했다. 기존 v0.1의 25개 검사는 이번 회차에 재실행하지 않았으므로 합쳐서 53개 통합 검증을 했다고 표시하지 않는다.

## 검사한 범위

단일 task 상태 소유자, 자동 merge 금지, 제한된 시도/병렬 수, 판단 사건의 범위, 불명확한 요청의 보류, 승인 표시 없는 원격 검색/Jev shadow, 원문 확장 읽기, 모델 선택 책임 중복, 사후 비용 측정과 hard cap의 구별을 검사했다.

증거에서는 trusted host의 기대값과 candidate/base/acceptance/verifier ID, policy fingerprint를 대조했다. 부분 성공, 빠진 회귀 검사, 실패한 추가 검사, 건강하지 않은 baseline, 미확인 비용의 0 치환, NaN, 중복 JSON 키도 시험했다. 필드 순서가 바뀌어도 canonical fingerprint가 같음을 확인했다.

세부 입력과 결과 판정은 `tests/test_v02.py`에 있다. 이 검사에서 승인 표시나 verifier ID가 일치했다는 것은 실제 승인 주체 인증을 수행했다는 뜻이 아니다.

## 원격 파일과 동일성

테스트 자산 커밋: `77c8ca05f92087f54d8cd784d53e3c37b824ef43`.

로컬 파일의 Git blob SHA를 계산하고 원격 tree가 반환한 값과 프로그램으로 대조했다. 5개 모두 일치했다.

| 파일 | Git blob SHA |
|---|---|
| `contracts/v0.2/pilot.schema.json` | `776a96bdde3797c66679f61b5245f5bfd1666b4e` |
| `examples/v0.2/pilot.json` | `8c4312c3cb02f787752aa41b41c86b82dc9c7085` |
| `examples/v0.2/proof-fixture.json` | `c83aef064164672d0b3d6d6629dcf54680eb412c` |
| `tests/test_v02.py` | `fc23a4ec8ed7f30a415339c511910ffe084e0797` |
| `tools/validate_v02.py` | `933bf819f6932d094df4b4613fa86c9d074df4db` |

이 hash는 동일성 확인이며 안전성·정확성 인증은 아니다.

## 산술 점검

외부 보고 수치를 사용한 차이 계산을 Python으로 확인했다. Switchyard의 $98.06→$85.00은 약 13.3% 감소, 76.0→75.7은 0.3%p 차이다. LangChain 표의 $3.00/$0.72는 약 4.17배다. SWE-Pruner의 500개 중 353→351은 −0.4%p다. 숫자 계산을 확인한 것이지 benchmark를 재현한 것은 아니다.

## 하지 않은 것

- 실제 repository commit·파일·artifact resolver 및 OS sandbox 확인.
- 사용자 또는 verifier의 암호학적/운영적 인증, 승인 위조 방지.
- 실제 예산 예약, provider 청구 정산, 취소·중복 실행·장애 복구.
- Symphony, Switchyard, mini-swe-agent, SWE-Pruner, JevGrep 설치·실행.
- 유료 모델 호출, 사용자 PC 변경, 실제 코드 과제의 성공률·토큰·금액 측정.
- 외부 실험의 통계적 재현이나 한국어 작업 품질 검증.

컨테이너의 외부 DNS 연결은 실패했으므로 자료 조사는 웹/GitHub 연결 도구로 수행했다. 로컬에 테스트 코드를 작성하고 설치되어 있던 jsonschema로 검사했다. 사용자 PC나 실제 연결된 하네스에서 실행했다고 말하지 않는다.
