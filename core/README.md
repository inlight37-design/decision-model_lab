# core — V04-03 실행 코어

**모델을 부르지 않고도 시험할 수 있는 부분부터 만든 실행 코어다.** 아직 앱이 아니다. 화면도, 저장소도, 여러 참여자를 도는 controller도 없다. 표준 라이브러리만 쓴다.

| 모듈 | 하는 일 | 하지 않는 일 |
|---|---|---|
| [`runner.py`](runner.py) | CLI 한 번을 셸 없이 실행한다. 입력을 쓰고 닫되 다 썼는지를 `input_delivery`로 남긴다. stdout·stderr 분리와 상한, 제한 시간, 취소, 추적 단위가 비었는지 확인. 확인하지 못하면 `unknown`. 명시적 정리 대기에 상한(`CLEANUP_LIMIT`)이 있고, 돌아온 뒤에도 남은 입출력 스레드는 `lingering()`이 센다. 호출자가 준 표식은 보관 상한과 상관없이 stderr 전체에서 센다(`stderr_counts`, K02) | 인증·과금·권한이 옳은지 판단 |
| [`adapters.py`](adapters.py) | Claude Code·Codex·agy의 읽기 전용 논의자 실행 명세(`ExecutionSpec`) 조립 — argv에는 옵션만, 질문은 stdin(agy만 아직 명령줄), 기록에는 `ExecutionSpec.record()`만 쓴다(입력 digest와 크기, 본문 없음). 위험 플래그 거절(Codex `-c`는 그 실행에 허용한 값만), 실제 출력 해석 — 입력 전달이 완전하지 않으면 `input_error`. Linux Codex에는 옛 `--sandbox read-only` 대신 로그인 파일(`~/.codex/auth.json`)만 읽기 금지한 권한 profile을 준다(K46, `codex_permissions`) | 권한 제한이 실제로 지켜지는지 증명 — V04-03 conformance가 한다 |
| [`isolation.py`](isolation.py) | 참여자 한 번의 실행을 bubblewrap으로 가둔다(Linux·WSL2). 허용한 폴더만 연결하고, HOME·`/tmp`는 빈 tmpfs, 별도 PID namespace. `cli_mounts()`가 CLI별로 실행 파일과 자기 설정·인증 폴더만 고른다. 진입점은 `isolation.run()` 하나다 — 경로 충돌을 거절하고, root 소유 `/usr/bin/bwrap`인지 확인한 뒤 실행하며, 그때만 자손 전체의 종료를 확인한다. 환경변수 값은 명령 인자에 싣지 않고, 인증 토큰은 넘기지 않는다. [W2 기록](../docs/experiments/w2-isolation/aux-pc-wsl.md) | 네트워크 격리(모델 API 때문에 공유한다), 메모리·CPU 상한 |
| [`env.py`](env.py) | 자식 환경(과금 변수 제거, 새 터미널 기준 정리), 실행 파일 찾기. WSL에서는 Windows 드라이브의 PATH 항목을 빼고 Windows 실행 파일(경로·링크·`MZ` 내용)을 거절한다. 자식 PATH가 없거나 비면 이 프로세스의 PATH로 되돌아가지 않는다. `tools/runtime_inventory.py`가 이 모듈의 변수 목록을 쓴다 | 인증 파일이나 환경변수 값 읽기·기록 |
| [`membership.py`](membership.py) | 실행 중 참여자가 빠지거나 바뀔 때의 결정. 조용히 채우지 않고, 공개 전에는 구성이 바뀔 때마다 정족수를 다시 보고 미달이면 막는다 | 실행, 초안이 다 들어왔는지 판단 — controller의 단계 관문이 한다 |
| [`contract.py`](contract.py) | 실행 계약(순서 5, G4·G6). 한 시도의 최종 계획(`Plan`: 최종 argv·입력·격리 경계·요청 모델·stderr 표식·실행 종류)을 한 번 만들어 기록과 실행에 같이 쓴다. 판(`revision`)은 실행 틀의 지문이다 — 실행 파일 경로·모델·HOME·자료 경로·질문은 역할로 바꾸고, 출력 형식·도구·권한 profile·세션 보존·연결 역할은 남긴다. 옛 이름 판은 검토해 같은 계획으로 확인한 것만 `LEGACY`로 대응시킨다 | 관측이 사실인지, 두 판이 "비슷하면" 같다고 보는 것 |
| [`eligibility.py`](eligibility.py) | 실행 허가(`eligible_for_run`)를 실행 직전에 계산한다(N4). 기본은 기록 `runtime-inventory/2`의 다섯 칸과 지금 계획의 판·설치판·관측일·구독을 검사한다. `allow_context_unverified` opt-in은 문맥 칸의 의미상 합격만 제외한다. 구조 검사와 다른 관문은 그대로다. 호출자는 미확인 등급을 저장하며 독립 정족수에 세지 않는다. 허가나 허위 관측을 manifest에 저장하지 않는다 | 기록된 관측이 사실인지 |

## 지키는 규칙

- **시간 초과는 성공이 아니다.** 답 텍스트가 있어도 `timed_out`이다.
- **끝났는지 확인하지 못하면 `unknown`이다.** 예산을 돌려받지 않는다.
- **추적 단위가 빈 것과 자손 전체가 끝난 것은 다르다.** Windows는 job object(`containment="job_object"`)라 자손이 떠날 수 없고, 그 밖은 프로세스 그룹(`"process_group"`)이라 새 세션을 만든 자손이 보이지 않는다. 그래서 `unit_confirmed_empty`(추적 단위)와 `tree_confirmed_empty`(자손 전체)를 따로 돌려준다. 프로세스 그룹에서 뒤쪽은 `None`이다. **자원·예산 반환은 `tree_confirmed_empty`가 True일 때만 한다.** Linux에서는 `isolation.run()`으로 실행할 때만 추적 단위가 PID namespace(`"pid_namespace"`)가 되어 True가 된다. 그 보장은 확인한 bubblewrap과 이 모듈의 정책에 한정되고, 참여자가 네트워크로 다른 서비스에 시켜 만든 작업은 포함하지 않는다([경계 리뷰 반영](../docs/reviews/2026-09-23-wsl2-boundary/RESPONSE.md), [W2 기록](../docs/experiments/w2-isolation/aux-pc-wsl.md)).
- **exit 0은 성공이 아니다.** 성공은 `adapters.interpret()`가 CLI별 규칙으로 정한다. Claude는 `is_error`, Codex는 `turn.completed`와 stderr의 명령 거절(stderr가 잘렸으면 받지 않는다), agy는 JSON 형식까지 본다. 출력 모양이 예상과 다르면(빈 값과 잘못된 타입을 구분하고, 아주 깊은 중첩도) 예외가 아니라 `format_error`다. **질문을 다 보내지 못했으면 답이 그럴듯해도 `input_error`다.** 다시 부르지 않는다.
- **명단에 받는 것과 진행 허가는 다르다.** membership은 바뀐 명단(`roster`)과, 그 뒤 같은 정족수 규칙으로 다시 정한 판정(`action`)을 따로 준다. 대체자가 들어와도 인원이 모자라면 `blocked`다. 단계는 한 칸씩 가고, 초안 단계 진입과 공개에는 정족수(`quorum_met`)가 있어야 한다. 초안이 다 들어왔는지는 controller의 단계 관문이 본다.
- **모델은 반드시 이름으로 지정한다.** 기본값도 fallback도 없다. 보고된 모델이 다르면 표시한다.
- **agy는 꺼져 있다.** 사용자가 켜야 쓴다(약관 판단, F31).
- **과금 경로를 바꾸는 환경변수는 자식에게 넘기지 않는다.** 인증은 각 CLI의 로그인을 쓴다.

검사: [`tests/test_core_runner.py`](../tests/test_core_runner.py), [`test_core_adapters.py`](../tests/test_core_adapters.py), [`test_core_contract.py`](../tests/test_core_contract.py), [`test_core_membership.py`](../tests/test_core_membership.py), [`test_core_env.py`](../tests/test_core_env.py), [`test_core_isolation.py`](../tests/test_core_isolation.py)(bubblewrap을 쓸 수 있는 Linux에서만 돈다. CI는 bubblewrap을 설치하고 `DML_REQUIRE_BWRAP=1`로 건너뛰기를 막는다). 파서 검사는 aux-pc V04-01에서 실제로 받은 출력을 쓴다. CI는 Linux라서 Windows job object 경로는 로컬 Windows에서 확인한다.
