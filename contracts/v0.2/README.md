# v0.2 오프라인 pilot 계약

이 디렉터리는 실행 프로그램 설정이 아니라 **합성 설계 fixture의 계약**이다. 기존 v0.1 TaskSpec을 대체하거나 특정 공급자의 API schema로 사용하는 것이 아니다.

```bash
python -m pip install -r requirements-design.txt
python tools/validate_v02.py
python -m unittest discover -s tests -p 'test_v02.py' -v
```

검사 환경은 Python 3.13.5 / jsonschema 4.26.0이다. 모델·하네스 설치나 API 키가 필요하지 않다. `pilot.json`의 backend는 unconfigured이며 원격 전송과 Jev shadow도 꺼져 있다. script는 외부 프로그램이나 모델을 실행하지 않는다.

`pilot.schema.json`은 plan/proof의 구조를 확인하고, `validate_v02.py`는 단일 상태 소유자, 모델 선택 책임, 원문 복구, remote approval 표시, 비용 한도의 의미, candidate/base/policy/acceptance/verifier 결합을 검사한다. JSON을 compact하게 저장한 것은 기계 계약의 표현이며 실제 LLM 토큰 절감 측정이 아니다.

## 신뢰 경계

`proof-fixture.json`의 반복 숫자 hash와 passed 값은 모두 합성이다. 실제 파일·테스트 실행·검증자 인증을 뜻하지 않는다. `expected`는 실제 통합 시 trusted host가 제공해야 하며 worker의 출력에서 그대로 가져오면 안 된다.

`remote_approved`나 `preadmission_verified`를 true/문자열로 적는 행위는 승인이나 예산 강제를 구현하지 않는다. 실제 코드에서는 승인 주체와 경로, 예약 원장, 프로세스 권한, resolver를 별도로 검증해야 한다. 이 validator를 운영 보안·재시작·동시성·비용 통제 구현으로 사용하지 않는다.

검사의 `REVIEW_READY` 설계도 자동 merge·최종 사용자 수용이 아니다. 부분 성공, 다른 후보의 PASS, 모르는 비용을 0으로 바꾸는 표현을 거부한다.

설계: [v0.2 구체 설계](../../docs/architecture/v0.2/02-concrete-blueprint.md).
