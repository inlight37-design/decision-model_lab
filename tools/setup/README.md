# 새 컴퓨터 준비 도구

순서와 사람이 할 일은 [docs/SETUP.md](../../docs/SETUP.md)에 있다. 여기 파일은 그 절차를 한 번에 하게 해 준다.

| 파일 | 하는 일 |
|---|---|
| [`setup.ps1`](setup.ps1) | **원터치 진입점.** winget 도구 → clone·검사 의존성·hook → WSL·Ubuntu(관리자 승인, 필요하면 재부팅 뒤 이어가기) → Linux 사용자 → Ubuntu의 apt(root)·CLI → 로그인 셋 → 양쪽 확인을 순서대로 한다. 된 단계는 건너뛴다. `-CheckOnly`면 보고만 한다. Windows PowerShell 5.1이 읽도록 ASCII로만 쓴다 |
| [`setup-wsl.sh`](setup-wsl.sh) | Ubuntu 쪽 준비. apt 패키지와 공식 Codex·Claude Code를 관측 판으로 설치한다. 설치 스크립트의 SHA-256이 읽어 둔 값과 다르면 멈춘다. `setup.ps1`이 root로 `--apt-only`, 사용자로 `--no-final`을 부른다. 혼자 돌리면 sudo로 전부 한다. 관측 판을 못 읽으면 멈추고(`--latest`만 최신판), 바뀐 설치 파일은 `--accept-installer-sha <이름>=<sha256>`로 승인한 바로 그 파일만 실행한다. `--check`면 보고만 한다 |
| [`check_setup.py`](check_setup.py) | 준비 상태를 보이고 필수 항목이 빠지면 1로 끝난다. 설치·변경·모델 호출이 없고, 로그인은 여부와 방식만 읽으며 계정 식별 값을 출력하지 않는다 |

시험: [`tests/test_check_setup.py`](../../tests/test_check_setup.py).
