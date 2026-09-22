# concept — 작업 개념도

[`control-plane.html`](control-plane.html)은 이 저장소가 정의한 작업 구조와, 그 위에 올릴 앱의 5계층 골격을 한 장으로 모은 문서다. 브라우저에서 파일을 직접 열면 된다.

[발행본](https://claude.ai/artifact/AZJfdnmMBjpEAtqsSHzjp8)도 같은 내용이며, 이 파일이 소스다. 한쪽만 고치고 두지 않는다.

## 담고 있는 것

| 절 | 내용 |
|---|---|
| 01 | **지금 실제로 존재하는 것** — 구현·설계·미검증을 색으로 구분 |
| 02 | 제어 평면 개념도, `deliberate`의 blind barrier 타임라인 |
| 03 | 앱 5계층과 무엇을 만들고 무엇을 흡수할지, 생태계 라이선스 |
| 04 | 열린 결정 Q1–Q4 |

## 그림에서 가장 중요한 한 가지

첫 다이어그램의 점선은 **실행 경로가 아니라 기록 경로**를 감싼다. `tools/check_frontier_protocol.py`는 파이프라인을 돌리지 않는다 — 끝난 뒤 제출된 JSON이 자기 모순인지 사후 검사할 뿐이다.

초록으로 칠해진 영역이 지금 코드가 지키는 전부이고, 주황은 설계만 있다.

## 정정 이력

4층의 "worktree로 격리"는 **틀렸다.** worktree는 `refs/` 아래 모든 ref를 공유하므로 격리 경계가 아니다([F27](../architecture/v0.4/sources.json)). 페이지에 정정과 함께 표시돼 있다.
