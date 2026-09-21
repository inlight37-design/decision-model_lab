# 설계 계약 v0.1

`v0.1.schema.json`은 TaskSpec, DecisionAdvice, WorkerResult의 내부 계약 예시다. 특정 공급자의 API schema가 아니다. 이 계약을 그대로 모든 모델의 structured-output 옵션에 넣을 수 있다고 보장하지 않는다.

예제는 `../examples/contracts-v0.1.json`이며 모든 task/commit/usage/확률은 합성 데이터다. 실제 repository·artifact 존재 여부나 모델 실행 결과가 아니다.

저장소 루트에서:

```bash
python -m pip install -r requirements-design.txt
python tools/validate_design.py
```

검사에 사용한 jsonschema 버전은 4.26.0이다. 의존성 설치는 본 저장소의 모델 실행·계정 연결·하네스 설치를 의미하지 않는다.

검사는 schema 및 일부 순수 데이터 불변 조건만 다룬다. 실제 파일의 symlink/ACL, reference resolver, 다른 task의 context, state 최신성, lease, 사용자 승인, 예산 예약, crash recovery, 외부 동작 idempotency는 구현·검증하지 않는다. 이 검사를 운영 보안 경계로 사용하지 않는다.

실제 제어부에는 추가로 project/attempt/lease/approval/context hash/permission/profile/price/version의 관계 검사가 필요하다. 저장된 schema는 최소 교환 계약이며 완성된 데이터베이스 스키마도 아니다.

상세 설계: `../docs/architecture/03-protocol-and-context.md`
