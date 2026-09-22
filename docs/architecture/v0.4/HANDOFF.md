# v0.4 작업 인계 — 상급 모델 협업 확장

기준일: 2026-09-22 (Asia/Seoul). 시작 원격 head: `634d34b2b6639ef60bd6469190cec053826b4385`.
브랜치: `docs/jev-free-codex-bridge-20260922`. main에 병합하지 않는다.

## 이번 사용자 요청

기존 오케스트레이션·저비용 역할 분담 연구를 확장하여, 회사별 상급 추론 모델들의 독립 답변·토론·교차검증을 조사한다. 실제 사례와 최신 1차 근거, 반례를 확인한 후 자료·뼈대·아키텍처를 단계적으로 구체화한다. 중단에 대비해 다음 작업까지 적고 중간 커밋한다.

## 유지할 제약

- v0.3의 공식 구독 CLI 우선, native 하네스 유지, API/추가 credits로 조용히 전환하지 않는 원칙을 유지한다.
- Jev는 교체 가능한 선택 부품이다. 핵심 추론·검증 권한을 필수적으로 맡기지 않는다.
- 상급 모델 협업은 비용 절감 모드와 목적함수가 다른 정식 모드로 검토한다. 다중 호출의 품질 이득은 아직 실측하지 않았다.
- 사용자 요금제·모델 가용성·CLI 설치 버전은 미확인이다. 최신 모델 이름이나 subscription entitlement를 추정해 확정하지 않는다.
- 기존 v0.2 계약·fixture를 깨뜨리지 않고, 신규 계약은 별도 버전/디렉터리에서 검토한다.
- 자료 조사, 설계 제안, 오프라인 검사, 실제 모델 실행을 엄격하게 구분한다.

## 시작 시 확인한 문서

README, v0.3 HANDOFF, 01-system, 02-adapters, 03-evidence를 GitHub 연결로 읽었다. 일부 긴 응답의 끝부분은 잘렸으므로 관련 부분은 범위 지정 재조회한다. v0.3 전체에 비용과 품질 경계는 있지만 별도 frontier deliberation protocol과 평가는 아직 이번 작업의 보강 대상이다.

## 현재 상태 (첫 checkpoint)

- 외부 사례 검색을 시작했으나 아직 채택·성과 판정을 확정하지 않았다.
- 후보: 실제 multi-model council 제품, 공개 council 구현, architect/reviewer 패턴, multi-agent debate 연구 및 실패 반례.
- 파일/실행 환경: 대화 컨테이너의 GitHub clone은 DNS 해석 실패. GitHub connector의 읽기·쓰기 경로를 사용한다. 로컬 clone 성공이나 원격 모델 실행을 주장하지 않는다.

## 재개 순서

1. v0.3의 남은 관련 부분, 결정/평가, 출처 레지스트리와 현재 tree를 확인한다.
2. 상급 모델 협업 제품·공개 구현·연구를 원문으로 확인한다. release/publish 날짜와 조회일, 코드 commit, 독립 재현 여부를 기록한다.
3. 반례: 독립성 상실, 설득에 의한 오답 전파, judge 편향, majority != truth, compute-matched baseline 부재를 검토한다.
4. 실행 모드를 single/economy, independent cross-check, bounded deliberation, implementation+review로 분리한다.
5. 독립 초안 → 주장/반례 정리 → 제한적 교차검토 → 도구 기반 검증 → 합성/미합의 인계를 설계한다. 임의로 모든 agent가 같은 긴 대화를 공유하지 않게 한다.
6. source registry·ADR·평가 계획·합성 계약과 오프라인 검사 범위를 작성한다. 실제 API/CLI 호출은 별도 미실시로 둔다.
7. README와 v0.3 읽기 경로를 연결하고 이 HANDOFF를 결과·검증·정확한 다음 단계로 갱신한다. 각 단계에서 원격 커밋을 확인한다.

미완료 작업을 완료라고 읽지 않도록 이 문서는 조사 단계마다 갱신한다.
