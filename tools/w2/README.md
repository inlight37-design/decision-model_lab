# tools/w2 — 격리 백엔드(bubblewrap) 관측

| 파일 | 무엇 |
|---|---|
| [`cli_boundary.py`](cli_boundary.py) | 설치된 Claude Code·Codex를 [`core/isolation.py`](../../core/isolation.py)의 참여자 경계 안에서 실행한다. `--version`, 로그인 상태(모델 호출 아님), 다른 CLI 인증·HOME·`/mnt/c`가 보이는지. 계정 이메일·조직 ID·요금제는 출력에서 버린다. WSL·Linux에서 저장소 루트로 `python3 tools/w2/cli_boundary.py` |
| [`auth_mounts.py`](auth_mounts.py) | N3(K09). 인증·설정 연결 조합을 바꿔 가며 격리 안에서 `--version`과 로그인 상태만 실행한다 — 모델 호출 없음. 좁힌 조합은 모두 읽기 전용. 이메일·긴 토큰 모양 문자열은 출력에서 지운다. 결과: [auth-mounts-aux-pc-wsl.md](../../docs/experiments/w2-isolation/auth-mounts-aux-pc-wsl.md) |
| [`observe.py`](observe.py) | 2단계 관측(tier 2, B1·B2). [`CliExecutor`](../../app/cli_executor.py)와 같은 argv·격리 경계로 실제 CLI를 한 번씩 부른다 — **모델 호출**. `plan`(호출 없음), `approve`(사용자 승인의 provider별 상한·timeout·메모), `status`, `call <probe> <전체 모델 이름>`. 승인이 없거나 상한을 다 썼거나 앞 호출이 기대와 달랐으면 부르지 않는다. 원 출력은 저장소 밖 `~/.local/state/dml-observe/`. 요약은 파일 이름·stderr의 UUID와 긴 16진수 ID를 가리지만 옮기기 전에 한 번 더 읽는다. WSL에서는 로그인 셸(`bash -l`)에서. 결과: [stage2-aux-pc-wsl.md](../../docs/experiments/w2-isolation/stage2-aux-pc-wsl.md) |
| [`codex_sandbox.py`](codex_sandbox.py) | K12. 참여자 경계 안에서 `codex sandbox -- /bin/sh -c …`로 Codex 자체 Linux 샌드박스가 중첩돼 서는지, 작업 폴더 쓰기를 막는지 본다 — 모델 호출 없음. exec가 모델의 명령을 돌린 관측은 아니다 |

합성 파일 경계 시험은 도구가 아니라 회귀 시험([`tests/test_core_isolation.py`](../../tests/test_core_isolation.py))이다. 결과: [docs/experiments/w2-isolation/](../../docs/experiments/w2-isolation/aux-pc-wsl.md).
