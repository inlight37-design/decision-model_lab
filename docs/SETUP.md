# 새 컴퓨터에서 시작하기

이 저장소를 다른 컴퓨터에서 처음 열 때 한 번 하는 준비다. **스크립트 둘이 설치를 맡고, 로그인 셋과 WSL 설치만 사람이 한다.** 끝나면 확인 도구가 "필수 항목 모두 준비됨"을 출력한다. 준비가 끝나면 [NEXT-SESSION.md](../NEXT-SESSION.md)부터 읽는다.

| 무엇 | 파일 | 하는 일 |
|---|---|---|
| Windows 준비 | [`tools/setup/setup-windows.ps1`](../tools/setup/setup-windows.ps1) | winget으로 Git·GitHub CLI·Python·Node를 설치하고, 검사 의존성과 commit hook을 켜고, WSL을 확인한다. `-Wsl`이면 아래 WSL 준비까지 부른다 |
| WSL 준비 | [`tools/setup/setup-wsl.sh`](../tools/setup/setup-wsl.sh) | apt 패키지(bubblewrap 등)와 공식 Codex·Claude Code CLI를 관측 기록과 같은 판으로 설치한다 |
| 확인 | [`tools/setup/check_setup.py`](../tools/setup/check_setup.py) | 무엇이 준비됐고 무엇이 빠졌는지, 고치는 명령과 함께 보인다. 설치·변경·모델 호출을 하지 않는다 |

세 파일 모두 다시 돌려도 안전하다. `-CheckOnly`(Windows)·`--check`(WSL)는 아무것도 바꾸지 않고 보고만 한다.

## 1. 필요한 것

| 어디 | 무엇 | 왜 | 누가 설치 |
|---|---|---|---|
| Windows | Git | 저장소 | 스크립트(winget `Git.Git`) — 처음 clone 전에는 직접 |
| Windows | GitHub CLI + 로그인 | PR·작업 카드 보드 | 스크립트(`GitHub.cli`) + 로그인은 사람 |
| Windows | Python 3.12 이상 + `jsonschema` | 오프라인 검사 전체 | 스크립트(`Python.Python.3.13`, `requirements-design.txt`) |
| Windows | Node LTS (선택) | 화면 JavaScript 시험. 없으면 그 시험은 skip되고 CI만 돈다 | 스크립트(`OpenJS.NodeJS.LTS`) |
| Windows | WSL2 Ubuntu 24.04 | 실제 CLI 실행은 WSL에서만 한다(인계 2절 15) | **사람**(관리자 창, 재부팅) |
| WSL | bubblewrap, python3, python3-jsonschema, git, curl | 참여자 격리와 시험 | 스크립트(apt, sudo 비밀번호는 사람) |
| WSL | Codex CLI, Claude Code | 실제 참여자 | 스크립트(공식 설치 스크립트, 관측 판 고정) |
| WSL | Codex·Claude 구독 로그인 | 구독 사용(유료 API 아님) | **사람** |
| — | Antigravity `agy` | 기본 꺼짐(인계 2절 14) | 설치하지 않는다 |

## 2. 순서

1. **Git과 clone.** Git이 없으면 PowerShell에서 `winget install --id Git.Git -e`를 먼저 한다. clone은 **AppData 밖**에 둔다(아래 함정 1).

   ```powershell
   git clone https://github.com/inlight37-design/decision-model_lab.git C:\ai\decision-model_lab
   cd C:\ai\decision-model_lab
   ```

2. **Windows 준비.** 일반 PowerShell 창에서 실행한다. 새로 설치한 것이 있으면 스크립트가 멈추고 새 창을 열라고 한다 — 새 창에서 같은 명령을 다시 실행한다.

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File tools\setup\setup-windows.ps1
   ```

3. **WSL이 없으면** 관리자 PowerShell에서 설치하고 재부팅한 뒤, 시작 메뉴의 Ubuntu를 한 번 열어 Linux 사용자를 만든다.

   ```powershell
   wsl --install -d Ubuntu-24.04
   ```

4. **WSL 준비.** 아래 둘 중 하나. sudo가 Linux 비밀번호를 묻는다.

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File tools\setup\setup-windows.ps1 -Wsl
   ```

   ```bash
   cd /mnt/c/ai/decision-model_lab && bash tools/setup/setup-wsl.sh
   ```

5. **로그인(사람).** 스크립트는 로그인하지 않고 인증 파일을 읽지 않는다.
   - Windows: `gh auth login`
   - Ubuntu 터미널: `claude auth login`(Claude 구독 — API 키가 아님), `codex login`(ChatGPT 로그인)

6. **확인.** 둘 다 "필수 항목 모두 준비됨"이면 끝이다. 빠진 항목은 고치는 명령이 함께 나온다.

   ```powershell
   python tools\setup\check_setup.py
   ```

   ```bash
   bash -lc 'cd /mnt/c/ai/decision-model_lab && python3 tools/setup/check_setup.py'
   ```

7. **오프라인 검사.** Windows에서 `python -m unittest discover -s tests`, WSL에서 `DML_REQUIRE_BWRAP=1 python3 -m unittest discover -s tests`. 종료 코드를 직접 본다(출력을 `tail`로 거르면 실패를 놓친다). skip은 통과가 아니다. 나머지 검증 도구는 [인계 6절](../NEXT-SESSION.md)에 있다.

## 3. 사람만 하는 것과 이유

| 일 | 이유 |
|---|---|
| WSL 설치 | 관리자 권한과 재부팅이 필요하다 |
| sudo 비밀번호, winget 약관 동의 | 스크립트가 대신 입력하거나 동의하지 않는다 |
| 로그인 셋(GitHub·Claude·Codex) | 인증 값을 AI 세션이나 저장소가 다루지 않는다. 인증 폴더를 다른 PC에서 복사하지 않는다 |
| 설치 스크립트가 바뀌었을 때 읽기 | `setup-wsl.sh`는 2026-09-25에 읽은 공식 설치 스크립트의 SHA-256과 비교하고, 다르면 멈추고 파일을 남긴다. 읽고 괜찮으면 `--accept-installer-change`로 다시 실행한다 |
| bubblewrap이 막힐 때의 보안 설정 | 일반 Ubuntu는 AppArmor가 권한 없는 user namespace를 막을 수 있다(K13, aux-pc-wsl은 해당 없음). 그 제한을 풀지는 사용자가 판단한다 — 스크립트는 바꾸지 않는다 |
| Codex 전역 `~/.codex/AGENTS.md` 처리 | 있으면 Codex 참여자 계획이 거절된다(E2). 옮길지는 사용자가 정한다 |

## 4. 새 컴퓨터로 옮겨지지 않는 것 — 중요

- **관측 기록은 기기의 것이다.** 지금 참여자 계획을 허가하는 [E2 manifest](reviews/2026-09-25-context-independence/manifest.v2.json)는 `aux-pc-wsl`에서 관측했다. **준비 조회는 기기를 비교하지 않는다** — 새 PC의 CLI 판이 같으면 그 기록으로 strict가 허가될 수 있지만, 그것은 다른 기기의 관측을 빌린 것이다. 새 PC에서는 [V04-01 절차서](experiments/v04-01-inventory/README.md)로 새 이름표의 기록을 만들고 [E2 절차](reviews/2026-09-25-context-independence/README.md)로 문맥 관측을 다시 한 뒤에만 strict로 실행한다. 그 전에는 `--allow-context-unverified`(독립 정족수에 세지 않음)만 쓴다. 기기와 묶는 보강은 작업 카드로 남겼다.
- **관측은 30일 동안만 유효하다.** E2 manifest에서 가장 이른 칸(로그인 방식, 2026-09-24 관측) 때문에 **2026-10-25부터** aux-pc-wsl에서도 준비 조회가 거절한다(`core.eligibility`로 10월 24일·25일을 계산해 확인). 그 전에 다시 관측한다.
- **CLI 판이 바뀌면 거절된다.** `setup-wsl.sh`는 관측 판(`check_setup.py --observed-versions`)으로 설치하지만 Claude Code 기본 설치는 백그라운드에서 스스로 업데이트된다. 판이 바뀌면 준비 조회가 거절한다 — 안전한 실패다. `--latest`로 새 판을 쓰려면 관측도 새로 한다.
- **원장은 옮기지 않는다.** `~/.local/state/dml-*`의 기존 원장은 aux-pc-wsl에 남는다. 새 실행은 새 원장·새 상한으로 한다(인계 0절 4). 원장·초안·계정 원시 응답은 저장소로 옮기지 않는다.
- **계정 플러그인.** 계정에 플러그인을 새로 설치했으면 [플러그인 기록](reviews/2026-09-25-plugin-surface/README.md)의 `probe.py`로 참여자에게 닿는지 다시 본다.

## 5. 이미 겪은 함정

1. **Claude 데스크톱 앱(Windows, MSIX) 안의 AI 세션이 `%LOCALAPPDATA%` 아래에 만든 폴더는 앱 전용 공간에 들어가** 사용자 터미널에서 안 보일 수 있다. 설치는 AppData 밖에 두고, `check_setup.py`가 그 공간에 새 폴더가 있으면 알린다(도구가 자기 상태 폴더를 만든 경우도 보인다). CLI 위치는 `tools\v04-01\check-versions.ps1`로 본다.
2. **Windows PowerShell 5.1의 `Get-Content`/`Set-Content`로 문서를 고치지 않는다** — 한글이 `?`로 깨진다([AGENTS.md](../AGENTS.md)). commit hook(`git config core.hooksPath .githooks`)이 막아 준다.
3. **WSL의 CLI는 로그인 셸에서 부른다**(`bash -lc '…'`). 아니면 `~/.local/bin`이 PATH에 없다.
4. **Git Bash에서 `wsl.exe`를 부를 때** `/mnt/c/…` 인자가 `C:/Program Files/Git/mnt/c/…`로 바뀐다 — `MSYS_NO_PATHCONV=1`을 붙인다. 작은따옴표 안의 `$변수`도 바깥 셸이 먼저 풀 수 있어 경로를 직접 적는다(인계 6절).
5. **`codex exec`는 stdin을 기다릴 수 있다** — `< /dev/null`로 부른다.
6. **Claude 앱이 만든 git worktree**는 `.git` 파일이 Windows 경로를 가리켜 WSL의 git이 읽지 못한다. WSL에서는 시험만 돌리고 git은 Windows 쪽에서 쓴다. 보통 clone은 해당 없다.
7. **Microsoft Store의 `python` 별칭**은 찾아지지만 실행되지 않는다. `setup-windows.ps1`은 실제로 실행해 본다.
8. **AI 도구 안의 오래된 PATH.** 설치 직후 AI 세션의 셸은 새 PATH를 모른다. `tools\v04-01\fresh-shell.ps1`로 레지스트리의 PATH를 다시 읽는다.

## 6. 이 문서의 근거와 한계

- 2026-09-25 `aux-pc`(Windows)와 `aux-pc-wsl`에서 두 스크립트의 확인 모드와 `check_setup.py`를 돌렸다. 이 PC에는 Node만 없었고, WSL은 모든 필수 항목이 준비돼 있었다.
- **빈 컴퓨터에서 처음부터 설치해 본 것은 아니다.** winget 패키지 네 개는 `winget show`로 있는 것만 확인했고, 설치 경로는 실행하지 않았다. 새 PC에서 처음 쓴 세션은 막힌 곳을 이 문서에 고쳐 적는다.
- 설치 스크립트의 SHA-256은 2026-09-25에 받은 공식 파일의 값이다(2026-09-23 V04-01 기록과 같다). 공식 스크립트는 예고 없이 바뀔 수 있다.
