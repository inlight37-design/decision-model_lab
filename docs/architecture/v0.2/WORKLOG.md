# v0.2 사례 기반 구체화 — 작업 기록 / 인수인계

**2026-09-21. 이번 후속 요청의 조사·설계 구체화·합성 계약 검사 완료. 실제 협업 런타임과 성능 평가는 미실시.**

## 시작점과 요청

시작 main: `f20922dc915a74568dbdcb3c00ed13673d0c9871`.
요청: 가시적인 성과가 있거나 구조가 구체적인 시스템을 심층 조사하고 기존 설계를 다듬는다. ‘성과 → 구조 → 재사용 경계 → 적용 조건 → 설계 변경’으로 연결했다.

## 이번 커밋

| 순서 | commit | 내용 |
|---|---|---|
| 1 | `0fe5f4c44e7298f692121321aa2067c6b0274d25` | 조사 범위와 첫 근거 체크포인트 |
| 2 | `f8d43cfd8f326c8b32128ce6720b116f69e43194` | 실제 성과·한계·사양/코드 출처의 사례 연구 |
| 3 | `43905f0e7bd8b97a5a79e9e071f47733a8b0f158` | 두 실행 경로, bounded_patch, 원문/증거/상태 소유자 구체화 |
| 4 | `6c1871cc0cd4b19db1f66cfe40da15bc4bf0d15c` | 비교 실험과 구현 ticket 8개 |
| 5 | `77c8ca05f92087f54d8cd784d53e3c37b824ef43` | v0.2 schema·fixture·검사기·28개 단위 검사 |
| 최종 | 이 문서를 포함하는 `docs: publish v0.2 navigation and verified research handoff` | 현재 문서 지도·검증 결과·인수인계 |

최종 SHA는 자기 참조 대신 Git 이력에서 확인한다. main을 부모로 이어서 갱신했고 force update를 사용하지 않았다.

## 새로 배운 것

- Cursor Router는 운영 데이터 기반 선택과 실제 비용을 다룬다. 사용자 만족도 지표와 코드 정답률을 구분해야 한다.
- Switchyard의 공개 결과는 workload별로 tradeoff가 다르다. 어떤 평가에서는 저가 단독 대비 router의 추가 이득이 입증되지 않았고 judge 비용도 컸다.
- SWE-Pruner의 고정 논문 Table 1은 토큰 감소와 작은 성공률 감소를 함께 보인다. README 최대 절감 문구를 일반 기대값으로 쓰지 않는다.
- Symphony는 구체적인 운영 사양·참고 구현이며 DB를 무조건 요구하지 않는다. 그래서 자체 전체 제어부부터 만든다는 순서를 수정했다.
- mini-swe-agent의 실제 query/execute/save 코드는 대조 실험 경계를 제공한다. 사후 cost limit를 선불 hard cap으로 오해하면 안 된다.
- Attractor는 상세 명세이지 설치 가능한 완제품이 아니다. 그래프/검증 개념만 작은 고정 절차로 우선 반영했다.
- JevGrep은 Jev를 read-only 코드 후보 선택에 적용한 구체 예다. benchmark와 실제 클라이언트 검증 범위가 제한적임도 README에서 확인했다.

## 현재 설계 결정

실용 경로와 경제성 실험 경로를 분리한다. 첫 과제는 단일 worker의 bounded_patch이며 독립 검증 후 REVIEW_READY로 인계한다. 자동 merge·배포는 범위 밖이다.

상태 소유자는 하나다. 작업 manifest/tracker와 run journal의 역할을 나누고, concurrency·예산 예약 문제가 실제로 필요해질 때 DB를 추가한다. Jev는 shadow 또는 read-only 선택 실험부터, router는 고가/저가 단독과 기존 공개 경로 모두와 비교한다.

원문과 hash를 보존하고 expand를 제공한다. 모델 선택·문맥 선별·병렬화를 한꺼번에 켜서 어떤 기능이 이득인지 모르게 만들지 않는다.

## 보존과 실제 검증

기존 v0.1 상세 문서·계약·원래 source-only 노트는 삭제하지 않았다. 루트 README와 아키텍처 목차는 v0.2를 현재 제안으로 안내하도록 갱신했다.

합성 계약 28개 검사와 fixture 검사를 실행·재실행했다. 5개 검사 자산의 Git blob SHA를 원격 tree와 대조해 일치를 확인했다. 자세한 범위는 [VALIDATION](VALIDATION.md)에 있다.

## 접근/실행 한계

Stripe Minions 원문 상세 본문은 웹 파서에서 확보되지 않았다. 제목·날짜·공식 요약 이상을 직접 읽었다고 표시하지 않았다. haejoe 원문의 기존 접근 한계도 해소되지 않았다. Reddit 교차 게시 두 건은 같은 작성자의 사례로 처리했다.

컨테이너 네트워크 DNS는 실패했지만 웹/GitHub 커넥터로 조사를 계속했다. 유료 API·로컬 모델·외부 하네스 설치·사용자 PC 수정은 하지 않았다. 공개 코드 전체의 보안 감사, 비용 절감 재현, 장기 무인 실행 검증도 하지 않았다.

## 다음 개발자가 시작할 곳

[구체 설계](02-concrete-blueprint.md)의 입력/출력 경계와 [백로그](03-experiments-and-backlog.md)의 V02-01–04부터 읽는다. 실제 과제·환경·권한·예산을 고정하고 한 실행의 독립 증거를 수집한 뒤 A0/A1을 비교한다.

현재 fixture의 반복 숫자 hash, passed 값, 승인 표시를 실제 실행 데이터로 사용하지 않는다. 소스의 blob SHA는 설치 commit이 아니다. 특정 model/threshold/최종 도구 채택은 여전히 실험과 적합성 확인 대상이다.
