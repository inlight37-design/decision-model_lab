# 검증 기록 — 2026-09-21

## 1. 실제 실행한 검사

실행 환경: 작업용 Linux 컨테이너, Python **3.13.5**, `jsonschema` **4.26.0**.

```text
python tools/validate_design.py
25/25 offline checks passed.
```

동일 검사를 재실행해서도 25개 모두 통과했습니다. 이 결과는 **합성 JSON 계약과 일부 순수 데이터 불변 조건의 검사**입니다. 유료 API·로컬 모델·coding CLI를 실행한 것이 아닙니다.

### 검사 항목과 결과

| 범위 | 사례 | 결과 |
|---|---|---|
| 정상 계약 | task, decision, worker_result | 기대대로 허용 |
| 경로 표현 | `../`, absolute path, Windows drive | 기대대로 거부 |
| task 제약 | 미정의 권한 필드, 자기 의존성, state_version=0, 빈 목표 | 기대대로 거부 |
| 확률 | 합계 오류, 범위 초과, NaN confidence, 알 수 없는 후보 | 기대대로 거부 |
| 보류 | 일관된 abstain / 모순된 abstain | 각각 허용 / 거부 |
| 완료 권한 | worker의 accepted 상태, 산출물 없는 candidate_ready | 기대대로 거부 |
| usage | cached > total, infinite cost | 기대대로 거부 |
| 모름의 표현 | null usage | 0으로 바꾸지 않고 허용 |
| 의미 구별 | provider confidence와 최대 확률이 다름 | 기대대로 허용 |
| 읽기 전용 | 빈 write_paths | 기대대로 허용 |
| 엄격한 JSON | 중복 key, 비표준 NaN | 기대대로 거부 |

정확한 25개 case 이름과 입력은 [검사 코드](../../tools/validate_design.py)에 있습니다. `state_version=0` 검사는 필드 범위 검사이지 실제 최신 상태와의 비교가 아닙니다.

## 2. 검사한 파일과 커밋된 파일의 동일성

검사에 쓴 로컬 파일의 Git blob SHA-1을 직접 계산하고 GitHub 원격 tree의 해당 파일 SHA와 대조했습니다. 아래 세 파일 모두 일치했습니다.

검사 자산을 추가한 커밋: `06705cea858de6f8e07f08069b843bb0d4cff34c`.

| 파일 | 일치한 Git blob SHA |
|---|---|
| `contracts/v0.1.schema.json` | `57e4bf34311ce9a0ab63217a9c54f0381420d22f` |
| `examples/contracts-v0.1.json` | `6693c0a0ea1f57f65a701133d524e50ab21a4a4b` |
| `tools/validate_design.py` | `90137df470b1d88f0e4b2db43ee01891e876c9a2` |

이 hash는 파일 동일성 확인이지 코드의 안전성 인증이 아닙니다. schema의 공급자별 지원 여부는 별도입니다.

## 3. 확인한 산술

[평가 문서](04-evaluation-and-economics.md)의 다음 계산을 Python으로 확인했습니다.

- 공식 공개 입력 단가를 적용한 가정 예시: `5,000 × 10,000 / 1,000,000 × 0.042 = US$2.10`.
- 가상 비용 단위 cascade: 상향 비율 25%에서 `5.77`, 80%에서 `11.82`.
- 같은 가정의 손익분기 상향 비율: 약 `72.55%`.

이는 산술의 확인입니다. 실제 사용자 청구액·모델 성공률·가격 조건을 실험한 결과가 아닙니다. JSON/자연어/TOON 간 tokenizer 벤치마크는 이번 작업에서 실행하지 않았습니다.

## 4. 저장소 보존 확인

원격 tree에서 기존 `docs/research-notes-2026-09-21.md`의 blob SHA가 원래 값 `30704b03b86770cafc6fa4494860ed9ea94ea144`로 유지됨을 확인했습니다. 오래된 내용은 삭제하거나 최신 실험처럼 덮어쓰지 않았습니다. 후속 변화는 새 조사 지도에 분리했습니다.

## 5. 아직 검증하지 않은 것

아래 항목은 설계에 포함되었더라도 구현 또는 실행 검증은 하지 않았습니다.

- 실제 artifact와 commit의 존재, task/context 교차 참조, symlink·ACL·프로젝트 경계.
- 영속 원장, 동시 claim, lease/fencing, budget reservation, outbox, crash recovery.
- API timeout 후 unknown outcome 조정, 외부 동작 중복 방지, 실제 취소 및 자식 프로세스 종료.
- Antigravity/Codex/Claude의 계정 인증, headless 동작, 버전별 이벤트 정규화, 재개.
- Jev 또는 로컬 decision model 추론, 확률 보정, 한국어/OOD 라우팅, VRAM·RAM·latency.
- 실제 코드 작업·테스트·merge queue·권한 격리·공급망 보안.
- 품질을 맞춘 절감률, 구독 quota 변화, 병렬화 이익, 장기 무인 실행.

25개 검사를 통과했다는 이유로 위 항목이 구현되었다고 간주하면 안 됩니다. 다음 단계에서 실제 구현할 때 별도의 integration/fault-injection/evaluation suite가 필요합니다.

## 6. 자료 확인의 한계

사용자 제공 haejoe 원문은 직접 접근·검색·대체 경로 시도에도 확보하지 못했습니다. X의 관련 게시물은 검색으로 식별했지만 본문 직접 접근이 실패한 사례가 있어 기술 사실의 확정 근거로 사용하지 않았습니다. 관련 Antigravity 구조는 공식 자료에서 독립적으로 확인했습니다.

공개 저장소의 README·모델 카드·관련 코드/문서 확인은 해당 저장소 전체의 보안 감사나 성능 재현을 뜻하지 않습니다. 커뮤니티 사례는 사용자 서술이며 대표 표본이나 통제 실험으로 취급하지 않았습니다.
