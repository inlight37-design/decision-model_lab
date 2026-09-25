# 새 컴퓨터 준비 도구

순서와 사람이 할 일은 [docs/SETUP.md](../../docs/SETUP.md)에 있다. 여기 파일은 그 절차를 한 번에 하게 해 준다.

| 파일 | 하는 일 |
|---|---|
| [`setup-windows.ps1`](setup-windows.ps1) | winget으로 Git·GitHub CLI·Python·Node를 설치하고 검사 의존성·commit hook을 켠 뒤 WSL을 확인한다. `-Wsl`이면 WSL 준비까지, `-CheckOnly`면 보고만 한다. Windows PowerShell 5.1이 읽도록 ASCII로만 쓴다 |
| [`setup-wsl.sh`](setup-wsl.sh) | apt 패키지와 공식 Codex·Claude Code를 관측 판으로 설치한다. 설치 스크립트의 SHA-256이 읽어 둔 값과 다르면 멈춘다. `--check`면 보고만 한다 |
| [`check_setup.py`](check_setup.py) | 준비 상태를 보이고 필수 항목이 빠지면 1로 끝난다. 설치·변경·모델 호출이 없고, 로그인은 여부와 방식만 읽으며 계정 식별 값을 출력하지 않는다 |

시험: [`tests/test_check_setup.py`](../../tests/test_check_setup.py).
