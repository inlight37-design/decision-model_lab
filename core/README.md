# core — V04-03 실행 코어

**모델을 부르지 않고도 시험할 수 있는 부분부터 만든 실행 코어다.** 아직 앱이 아니다. 화면도, 저장소도, 여러 참여자를 도는 controller도 없다. 표준 라이브러리만 쓴다.

| 모듈 | 하는 일 | 하지 않는 일 |
|---|---|---|
| [`runner.py`](runner.py) | CLI 한 번을 셸 없이 실행한다. stdin 닫기, stdout·stderr 분리와 상한, 제한 시간, 취소, 프로세스 트리 종료 확인. 확인하지 못하면 `unknown` | 인증·과금·권한이 옳은지 판단 |
| [`adapters.py`](adapters.py) | Claude Code·Codex·agy의 읽기 전용 논의자 argv 조립, 위험 플래그 거절, 과금 변수 제거, 실제 출력 해석 | 권한 제한이 실제로 지켜지는지 증명 — V04-03 conformance가 한다 |
| [`membership.py`](membership.py) | 실행 중 참여자가 빠지거나 바뀔 때의 결정. 조용히 채우지 않고, 최소 인원 미달이면 막는다 | 실행 |

## 지키는 규칙

- **시간 초과는 성공이 아니다.** 답 텍스트가 있어도 `timed_out`이다.
- **끝났는지 확인하지 못하면 `unknown`이다.** 예산을 돌려받지 않는다. Windows는 job object로, 그 밖은 프로세스 그룹으로 트리를 센다. 자기 그룹을 떠난 프로세스는 POSIX에서 추적하지 못한다.
- **exit 0은 성공이 아니다.** 성공은 `adapters.interpret()`가 CLI별 규칙으로 정한다. Claude는 `is_error`, Codex는 `turn.completed`, agy는 JSON 형식까지 본다.
- **모델은 반드시 이름으로 지정한다.** 기본값도 fallback도 없다. 보고된 모델이 다르면 표시한다.
- **agy는 꺼져 있다.** 사용자가 켜야 쓴다(약관 판단, F31).
- **과금 경로를 바꾸는 환경변수는 자식에게 넘기지 않는다.** 인증은 각 CLI의 로그인을 쓴다.

검사: [`tests/test_core_runner.py`](../tests/test_core_runner.py), [`test_core_adapters.py`](../tests/test_core_adapters.py), [`test_core_membership.py`](../tests/test_core_membership.py). 파서 검사는 aux-pc V04-01에서 실제로 받은 출력을 쓴다. CI는 Linux라서 Windows job object 경로는 로컬 Windows에서 확인한다.
