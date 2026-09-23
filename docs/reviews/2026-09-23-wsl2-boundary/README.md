# WSL2와 실행 경계 검토 — 2026-09-23

사용자가 받아 전달한 외부 AI 리뷰다. 작성한 모델·세션은 원문에 적혀 있지 않다. 원문에 따르면 GitHub connector로 저장소를 읽었고, 사용자 PC·CLI·모델에는 접근하지 않았으며, 코어 두 파일의 스냅숏으로 Linux(Python 3.13.5)에서 재현했다. 검토 기준은 `main`의 `d0678f4`다.

| 파일 | 무엇 |
|---|---|
| [`REVIEW.md`](REVIEW.md) | 리뷰 원문. 받은 그대로 두고 고치지 않는다 |
| [`membership_probe.py`](membership_probe.py), [`runner_probe.py`](runner_probe.py) | 리뷰어의 재현 스크립트. 스냅숏의 blob SHA를 먼저 확인한다. runner 쪽은 Linux 전용 |
| [`results/`](results/) | 리뷰어가 얻은 재현 결과(수정 전 관측) |
| [`snapshot/core/`](snapshot/core/) | 재현에 쓴 `runner.py`·`membership.py`. `d0678f4`의 파일과 바이트까지 같다 |
| [`RESPONSE.md`](RESPONSE.md) | claude 세션의 발견별 판정·반영·보류와 이유, 리뷰 밖에서 새로 찾은 것 |

## 읽을 때의 단서

- 리뷰는 **수정 전** 코드를 본다. 재현 스크립트는 번들의 스냅숏을 검사하므로 지금 실행해도 수정 전 동작이 나온다. 고친 동작은 `tests/`의 회귀 시험이 확인한다.
- R01·R02는 POSIX 경로의 결함이다. 보조 PC(Windows, job object)에서는 같은 시나리오를 정상 처리했다. 자세한 것은 [RESPONSE.md](RESPONSE.md).
