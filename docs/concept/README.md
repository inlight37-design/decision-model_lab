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

## 이 개념도는 2026-09-22 스냅숏이다

페이지 머리에 적힌 대로 `558cc42` 시점의 기록이다. 그 뒤 바뀐 것은 페이지를 고치지 않고 여기에 적는다. 현재 상태는 [`NEXT-SESSION.md`](../../NEXT-SESSION.md)가 기준이다.

| 페이지의 내용 | 이후 |
|---|---|
| Q1 "ACP 우선 + exec 폴백"에 기울어짐 | **exec 우선으로 확정**(2026-09-23). V04-01(aux-pc)에서 세 CLI 모두 help에 ACP가 없고 비대화형 실행이 구독으로 동작했다 |
| "Gemini CLI 소비자 인증 종료설은 원문 미확인" | 원문 확인 → [F30](../architecture/v0.4/sources.json). Antigravity 약관의 제3자 접근 조항 → F31 |
| "V04-01 이전까지 전부 미검증" | aux-pc에서 V04-01 완료 — [결과](../experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md) |
| 검사 수·원장 건수·근거 범위 | 그 시점의 숫자다. 현재 값은 CI 로그와 원장 파일 |
| 구독 경로가 닫혔을 때의 대안 미정 | 유료 API 전환 없이 그 provider를 뺀다(D18, 사용자 결정 2026-09-23) |

## 정정 이력

4층의 "worktree로 격리"는 **틀렸다.** worktree는 `refs/` 아래 모든 ref를 공유하므로 격리 경계가 아니다([F27](../architecture/v0.4/sources.json)). 페이지에 정정과 함께 표시돼 있다.
