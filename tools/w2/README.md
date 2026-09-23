# tools/w2 — 격리 백엔드(bubblewrap) 관측

| 파일 | 무엇 |
|---|---|
| [`cli_boundary.py`](cli_boundary.py) | 설치된 Claude Code·Codex를 [`core/isolation.py`](../../core/isolation.py)의 참여자 경계 안에서 실행한다. `--version`, 로그인 상태(모델 호출 아님), 다른 CLI 인증·HOME·`/mnt/c`가 보이는지. 계정 이메일·조직 ID·요금제는 출력에서 버린다. WSL·Linux에서 저장소 루트로 `python3 tools/w2/cli_boundary.py` |

합성 파일 경계 시험은 도구가 아니라 회귀 시험([`tests/test_core_isolation.py`](../../tests/test_core_isolation.py))이다. 결과: [docs/experiments/w2-isolation/](../../docs/experiments/w2-isolation/aux-pc-wsl.md).
