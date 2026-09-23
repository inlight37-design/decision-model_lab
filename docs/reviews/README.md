# reviews — 외부 검토 기록

저장소 밖에서 수행된 검토의 원문을 보존한다. 요약으로 대체하지 않는다.

| 파일 | 무엇 |
|---|---|
| [`2026-09-22-external-review.md`](2026-09-22-external-review.md) | 첫 외부 정밀 검토. 코드·문서·근거 원장 전체를 읽고 검사를 재실행한 기록 |
| [`2026-09-23-mcp-ui-runtime/`](2026-09-23-mcp-ui-runtime/README.md) | MCP 구성·기존 앱 8사례·Ledger UI 검토, 오프라인 경계 실험(`tools/review_boundary.py`), 대비 감사. [PR #3](https://github.com/inlight37-design/decision-model_lab/pull/3) |
| [`2026-09-23-review-request/`](2026-09-23-review-request/README.md) | V04-01 검토 요청서. 질문·읽는 순서·결과 형식은 원문을 보존하고 결과는 아래 리뷰로 연결한다 |
| [`2026-09-23-v04-01-review/`](2026-09-23-v04-01-review/README.md) | GitHub 기록·코드·공식 문서 대조. 실행 준비와 blind/권한 통과의 구분, manifest·환경·가림 가드의 합성 반례와 재현 자료. 원본 수정 전 검토 결과 |

## 읽는 순서

이 저장소의 검토 기록은 아래 시간순으로 읽는다. **뒤로 갈수록 최신이며, 앞의 것은 그 시점의 기록으로 남긴다.**

1. [`v0.4/FINAL_REVIEW.md`](../architecture/v0.4/FINAL_REVIEW.md) — PR #1 최종 검토
2. [`v0.4/EVIDENCE_FOLLOWUP.md`](../architecture/v0.4/EVIDENCE_FOLLOWUP.md) — 남은 출처 재확인, F22–F24
3. `2026-09-22-external-review.md` (이 폴더) — 외부 검토 원문
4. [`v0.4/REVIEW_FIXES.md`](../architecture/v0.4/REVIEW_FIXES.md) — 3의 반영 결과와 그 뒤 cross_check, F25–F27
5. [`2026-09-23-mcp-ui-runtime/`](2026-09-23-mcp-ui-runtime/README.md) — MCP·앱·UI 검토. `validate()`는 판정을 *검사*할 뿐 *계산*하지 않는다는 정정 포함
6. [`2026-09-23-v04-01-review/`](2026-09-23-v04-01-review/README.md) — aux-pc 원 출력과 후속 도구·판정·진입 조건 검토. 재현 범위와 원 출력 선검토의 한계도 명시

## 5번 기록에 대한 단서

- 본문의 "루트의 날짜 붙은 파일"은 이후 [`docs/handoff/`](../handoff/README.md)로 옮겼다. 내용은 바이트 그대로다.
- 이 검토는 웹 컨테이너에서 수행됐고 사용자 PC·CLI에 접근하지 않았다. 환경 사실은 그 한계 안에서 읽는다.

## 3번 문서에 대한 단서

이 판본은 **두 건의 지적이 정정되기 전** 상태다. 확인 결과 저장소 쪽이 옳았다.

- `published` 결측 8건은 결함이 아니었다 — 살아있는 문서는 `revised`, 고정 commit은 `revision`을 쓴다. 실제 결함은 F17/F18/F19만 날짜 필드가 없던 것
- 날짜의 축소 정밀도(`2025`, `2024-07`)도 정상이다 — 아는 것보다 정밀하게 적지 않은 처리다

정정 내역은 `REVIEW_FIXES.md` §2에 있다. 원문을 고치지 않고 남기는 이유는 **검토자가 무엇을 틀렸는지도 기록이기 때문**이다.
