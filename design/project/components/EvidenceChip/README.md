# EvidenceChip

주장에 붙은 검사 하나를 나타내는 칩. `kind`와 `status`를 **함께** 싣는다.

## 왜 둘을 분리하지 않는가

`passed`만 보여주면 화면이 거짓말을 한다. 모델 두 개가 동의했다는 `vote`의 `passed`와, 테스트가 통과한 `test`의 `passed`는 같은 글자지만 전혀 다른 근거다. checker는 이 구분을 강제한다 — `supported` 승격에는 `test`·`source`·`calculation` 중 `passed`가 필요하고 `vote`·`self_report`는 세지 않는다. 화면도 같은 구분을 유지해야 한다.

그래서 칩은 항상 `kind:status` 꼴로 읽힌다. `kind`를 접거나 아이콘으로만 표시하지 않는다.

## 규칙

- **승격 불가 종류는 시각적으로 낮춘다.** `vote`와 `self_report`는 `passed`여도 긍정색을 쓰지 않는다. 외곽선만 그린 중립 칩이다.
- **`skipped`는 통과가 아니다.** `passed`와 다른 색, 다른 글자. 비워 두지 않는다.
- **`log_ref`가 없는 칩은 없다.** 모든 칩은 검사 기록으로 이동하는 링크를 갖는다. 갈 곳이 없으면 그 칩은 만들어지면 안 된다.
- **`failed`를 숨기지 않는다.** 한 주장에 실패한 검사가 있으면 접힌 상태에서도 보인다.

## 소비자가 제공하는 것

`{ id, kind, status, log_ref }`. 칩은 `log_ref`의 유효성을 검사하지 않는다 — 실제 기록으로 해소되는지는 resolver의 일이다.
