# core — V04-03 실행 코어

**모델을 부르지 않고도 시험할 수 있는 부분부터 만든 실행 코어다.** 아직 앱이 아니다. 화면도, 저장소도, 여러 참여자를 도는 controller도 없다. 표준 라이브러리만 쓴다.

| 모듈 | 하는 일 | 하지 않는 일 |
|---|---|---|
| [`runner.py`](runner.py) | CLI 한 번을 셸 없이 실행한다. stdin 닫기, stdout·stderr 분리와 상한, 제한 시간, 취소, 추적 단위가 비었는지 확인. 확인하지 못하면 `unknown`. 정리 단계에도 상한(`CLEANUP_LIMIT`)이 있다 | 인증·과금·권한이 옳은지 판단 |
| [`adapters.py`](adapters.py) | Claude Code·Codex·agy의 읽기 전용 논의자 실행 명세(`ExecutionSpec`) 조립 — argv에는 옵션만, 질문은 stdin(agy만 아직 명령줄), 기록에는 입력 digest와 크기만. 위험 플래그 거절, 실제 출력 해석 | 권한 제한이 실제로 지켜지는지 증명 — V04-03 conformance가 한다 |
| [`env.py`](env.py) | 자식 환경(과금 변수 제거, 새 터미널 기준 정리), 실행 파일 찾기. WSL에서는 Windows 드라이브의 PATH 항목을 빼고 Windows 실행 파일을 거절한다. `tools/runtime_inventory.py`가 이 모듈의 변수 목록을 쓴다 | 인증 파일이나 환경변수 값 읽기·기록 |
| [`membership.py`](membership.py) | 실행 중 참여자가 빠지거나 바뀔 때의 결정. 조용히 채우지 않고, 공개 전에는 구성이 바뀔 때마다 정족수를 다시 보고 미달이면 막는다 | 실행, 초안이 다 들어왔는지 판단 — controller의 단계 관문이 한다 |

## 지키는 규칙

- **시간 초과는 성공이 아니다.** 답 텍스트가 있어도 `timed_out`이다.
- **끝났는지 확인하지 못하면 `unknown`이다.** 예산을 돌려받지 않는다.
- **추적 단위가 빈 것과 자손 전체가 끝난 것은 다르다.** Windows는 job object(`containment="job_object"`)라 자손이 떠날 수 없고, 그 밖은 프로세스 그룹(`"process_group"`)이라 새 세션을 만든 자손이 보이지 않는다. 그래서 `unit_confirmed_empty`(추적 단위)와 `tree_confirmed_empty`(자손 전체)를 따로 돌려준다. 프로세스 그룹에서 뒤쪽은 `None`이다. **자원·예산 반환은 `tree_confirmed_empty`가 True일 때만 한다.** Linux에서 이것을 True로 만드는 것은 격리 백엔드(bubblewrap의 PID namespace)의 몫이다([경계 리뷰 반영](../docs/reviews/2026-09-23-wsl2-boundary/RESPONSE.md)).
- **exit 0은 성공이 아니다.** 성공은 `adapters.interpret()`가 CLI별 규칙으로 정한다. Claude는 `is_error`, Codex는 `turn.completed`와 stderr의 명령 거절(stderr가 잘렸으면 받지 않는다), agy는 JSON 형식까지 본다. 출력 모양이 예상과 다르면 예외가 아니라 `format_error`다.
- **명단에 받는 것과 진행 허가는 다르다.** membership은 바뀐 명단(`roster`)과, 그 뒤 같은 정족수 규칙으로 다시 정한 판정(`action`)을 따로 준다. 대체자가 들어와도 인원이 모자라면 `blocked`다. 단계는 한 칸씩 가고, 초안 단계 진입과 공개에는 정족수(`quorum_met`)가 있어야 한다. 초안이 다 들어왔는지는 controller의 단계 관문이 본다.
- **모델은 반드시 이름으로 지정한다.** 기본값도 fallback도 없다. 보고된 모델이 다르면 표시한다.
- **agy는 꺼져 있다.** 사용자가 켜야 쓴다(약관 판단, F31).
- **과금 경로를 바꾸는 환경변수는 자식에게 넘기지 않는다.** 인증은 각 CLI의 로그인을 쓴다.

검사: [`tests/test_core_runner.py`](../tests/test_core_runner.py), [`test_core_adapters.py`](../tests/test_core_adapters.py), [`test_core_membership.py`](../tests/test_core_membership.py), [`test_core_env.py`](../tests/test_core_env.py). 파서 검사는 aux-pc V04-01에서 실제로 받은 출력을 쓴다. CI는 Linux라서 Windows job object 경로는 로컬 Windows에서 확인한다.
