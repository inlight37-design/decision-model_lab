# tools/w2 — 격리 백엔드(bubblewrap) 관측

| 파일 | 무엇 |
|---|---|
| [`cli_boundary.py`](cli_boundary.py) | 설치된 Claude Code·Codex를 [`core/isolation.py`](../../core/isolation.py)의 참여자 경계 안에서 실행한다. `--version`, 로그인 상태(모델 호출 아님), 다른 CLI 인증·HOME·`/mnt/c`가 보이는지. 계정 이메일·조직 ID·요금제는 출력에서 버린다. WSL·Linux에서 저장소 루트로 `python3 tools/w2/cli_boundary.py` |
| [`observe.py`](observe.py) | 2단계 관측(tier 2, B1·B2). [`CliExecutor`](../../app/cli_executor.py)와 같은 argv·격리 경계로 실제 CLI를 한 번씩 부른다 — **모델 호출**. `plan`(호출 없음), `approve`(사용자 승인의 provider별 상한·timeout·메모), `status`, `call <probe> <전체 모델 이름>`. 승인이 없거나 상한을 다 썼거나 앞 호출이 기대와 달랐으면 부르지 않는다. 원 출력은 저장소 밖 `~/.local/state/dml-observe/`. WSL에서는 로그인 셸(`bash -l`)에서 |

합성 파일 경계 시험은 도구가 아니라 회귀 시험([`tests/test_core_isolation.py`](../../tests/test_core_isolation.py))이다. 결과: [docs/experiments/w2-isolation/](../../docs/experiments/w2-isolation/aux-pc-wsl.md).
