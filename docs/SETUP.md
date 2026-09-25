# 새 컴퓨터에서 시작하기

이 저장소를 다른 컴퓨터에서 처음 열 때 한 번 하는 준비다. **명령 한 줄로 끝까지 순서대로 진행한다.** 사람이 손대는 곳은 관리자 승인(UAC) 한 번, WSL을 처음 켜는 PC의 재부팅 한 번(재부팅 뒤 저절로 이어진다), Ubuntu의 사용자 이름·비밀번호, 브라우저에서 승인하는 로그인 셋(GitHub·Claude·Codex)뿐이다. 준비가 끝나면 [NEXT-SESSION.md](../NEXT-SESSION.md)부터 읽는다.

## 1. 한 줄로 시작

새 PC의 **일반 PowerShell 창**(관리자 아님)에 붙여 넣는다.

```powershell
irm https://raw.githubusercontent.com/inlight37-design/decision-model_lab/main/tools/setup/setup.ps1 -OutFile "$env:TEMP\dml-setup.ps1"; powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\dml-setup.ps1"
```

이미 clone한 PC에서는 저장소 루트에서 `powershell -NoProfile -ExecutionPolicy Bypass -File tools\setup\setup.ps1`. 몇 번을 다시 돌려도 안전하다 — 단계마다 먼저 확인하고 된 것은 건너뛴다. 중간에 멈추면 원인을 고치고 같은 명령을 다시 실행한다. 진행 기록은 `%USERPROFILE%\dml-setup.log`에 남는다.

| 선택 | 뜻 |
|---|---|
| `-CheckOnly` | 아무것도 바꾸지 않고 단계마다 무엇을 할지 보인다 |
| `-SkipLogin` | 로그인 단계를 건너뛴다 |
| `-Apps` | Claude 데스크톱 앱(`Anthropic.Claude`)도 설치한다. ChatGPT 데스크톱 앱은 winget에 없어 Microsoft Store에서 직접 설치한다 |
| `-RepoDir <폴더>` | clone 위치(기본 `C:\ai\decision-model_lab`). AppData 아래는 거절한다(함정 1) |
| `-AcceptInstallerSha <이름>=<sha256>` | 바뀐 공식 설치 파일을 읽은 뒤 그 파일을 승인한다(3절) |

**종료 코드:** 0 준비됨, 1 어느 단계가 실패함, 2 아직 끝나지 않음(Windows 재시작이나 새 창이 필요 — 같은 명령을 다시 실행). 실패를 성공으로 보고하지 않는다. 관측 기록의 판을 읽지 못하면 최신판으로 넘어가지 않고 멈춘다(최신판은 Ubuntu에서 `--latest`로만 고른다).

## 2. 스크립트가 하는 일 — 순서대로

| 단계 | 하는 일 | 사람이 할 것 |
|---|---|---|
| 1 | winget으로 Git·GitHub CLI·Python 3.13·Node.js LTS 설치. 이미 있으면 건너뛴다 | 없음 — 이 명령을 실행하는 것이 패키지 약관 동의다 |
| 2 | 저장소 clone, 검사 의존성(`requirements-design.txt`), 인코딩 hook | 없음 |
| 3 | WSL과 Ubuntu 24.04 설치 | 관리자 승인(UAC). WSL을 처음 켜는 PC는 재부팅 — 스크립트가 로그인 뒤 저절로 이어지게 등록한다(RunOnce, 한 번 돌면 사라진다) |
| 4 | Linux 사용자 | Ubuntu가 묻는 사용자 이름·비밀번호. Ubuntu 프롬프트(`$`)가 보이면 `exit` |
| 5 | Ubuntu 안에서 apt 패키지(root로 — sudo 비밀번호 없음), 공식 Codex·Claude Code를 관측 판으로 고정 설치([`setup-wsl.sh`](../tools/setup/setup-wsl.sh)) | 없음. 공식 설치 스크립트가 2026-09-25에 읽은 것과 다르면 멈춘다(아래 3절) |
| 6 | 로그인을 하나씩: GitHub → Claude → Codex. GitHub 계정의 이름과 no-reply 주소로 git 커밋 이름을 정한다(비어 있을 때만) | 브라우저에서 승인 셋. Claude는 구독(claude.ai)으로, API 키가 아니다 |
| 7 | Windows와 Ubuntu 양쪽에서 [`check_setup.py`](../tools/setup/check_setup.py) — 준비된 것·빠진 것·고치는 명령 | 없음. "Setup is complete"(종료 코드 0)면 끝. 이것은 **도구 설치와 구독 로그인까지**다 — strict 실행 허가는 이 기기의 관측과 준비 조회가 따로 정한다(4절) |

스크립트는 비밀번호·토큰을 읽거나 저장하지 않고 모델을 부르지 않는다. 필요한 것의 전체 목록:

| 어디 | 무엇 | 왜 |
|---|---|---|
| Windows | Git, GitHub CLI + 로그인 | 저장소, PR·작업 카드 보드 |
| Windows | Python 3.12 이상 + `jsonschema` | 오프라인 검사 전체 |
| Windows | Node LTS | 화면 JavaScript 시험(없으면 그 시험만 skip, CI는 돈다) |
| Windows | WSL2 Ubuntu 24.04 | 실제 CLI 실행은 WSL에서만 한다(인계 2절 15) |
| Ubuntu | bubblewrap, python3, python3-jsonschema, git, curl | 참여자 격리와 시험 |
| Ubuntu | Codex CLI, Claude Code + 구독 로그인 | 실제 참여자(유료 API 아님) |
| — | Antigravity `agy` | 기본 꺼짐(인계 2절 14) — 설치하지 않는다 |

**끝난 뒤 오프라인 검사:** Windows에서 `python -m unittest discover -s tests`, Ubuntu에서 `DML_REQUIRE_BWRAP=1 python3 -m unittest discover -s tests`. 종료 코드를 직접 본다(출력을 `tail`로 거르면 실패를 놓친다). skip은 통과가 아니다. 나머지 검증 도구는 [인계 6절](../NEXT-SESSION.md)에 있다. Ubuntu 쪽만 따로 준비하거나 확인하려면 `bash tools/setup/setup-wsl.sh [--check]`, 확인만 하려면 `python tools\setup\check_setup.py`(Ubuntu에서는 `python3`).

## 3. 사람만 하는 것과 이유

| 일 | 이유 |
|---|---|
| 관리자 승인(UAC)과 재부팅 | Windows가 WSL 설치에 요구한다. 스크립트는 관리자 권한으로 통째로 돌지 않고 그 한 단계만 승인을 받는다 |
| Ubuntu 사용자 이름·비밀번호 | Ubuntu 자신이 묻는다. 비밀번호는 Ubuntu 안에만 있다 |
| 로그인 셋(GitHub·Claude·Codex) | 인증 값을 AI 세션이나 저장소가 다루지 않는다. 인증 폴더를 다른 PC에서 복사하지 않는다 |
| 설치 스크립트가 바뀌었을 때 읽기 | `setup-wsl.sh`는 승인한 SHA-256의 설치 파일만 실행한다(기본은 2026-09-25에 읽은 공식 파일). 받은 파일이 다르면 멈추고 그 파일을 `~/.cache/dml-setup/`에 남기며 SHA-256을 알려 준다. 읽고 괜찮으면 `-AcceptInstallerSha codex=<그 값>`(또는 `claude=`, Ubuntu에서 직접 돌릴 때는 `--accept-installer-sha`)으로 다시 실행한다 — **남겨 둔 바로 그 파일**이 실행되고, 그 사이 새로 받은 다른 파일은 실행되지 않는다(2026-09-25 외부 검토 R03) |
| bubblewrap이 막힐 때의 보안 설정 | 일반 Ubuntu는 AppArmor가 권한 없는 user namespace를 막을 수 있다(K13, aux-pc-wsl은 해당 없음). 그 제한을 풀지는 사용자가 판단한다 — 스크립트는 바꾸지 않는다 |
| Codex 전역 `~/.codex/AGENTS.md` 처리 | 있으면 Codex 참여자 계획이 거절된다(E2). 옮길지는 사용자가 정한다 |

## 4. 새 컴퓨터로 옮겨지지 않는 것 — 중요

- **관측 기록은 기기의 것이다.** 지금 참여자 계획을 허가하는 [E2 manifest](reviews/2026-09-25-context-independence/manifest.v2.json)는 `aux-pc-wsl`에서 관측했다. **실제 모드는 이 기기에 등록된 기록만 쓴다**(카드 #71). 준비 조회와 실행 직전 재검사가 사용자 상태 폴더의 로컬 등록(`~/.local/state/decision-model-lab/registrations.json`, 저장소 밖)을 보고, 등록되지 않은 기록이면 거절한다 — 문맥 미확인 허용(`--allow-context-unverified`)도 건너뛰지 않는다. 공개 저장소에는 기기 식별 값이 없다. 새 PC에서는 [V04-01 절차서](experiments/v04-01-inventory/README.md)로 새 이름표의 기록을 만들고 [E2 절차](reviews/2026-09-25-context-independence/README.md)로 관측을 다시 한 뒤, **그 PC에서** `python3 -m app.registration register <새 기록> --host-label <그 이름표>`로 등록한다. 다른 PC의 기록을 등록하지 않는다 — 명령은 기록의 이름표를 확인할 뿐 관측이 어디서 됐는지 증명하지 못한다. 호스트 이름을 바꾸거나 배포판을 다른 PC로 옮기면 다시 등록한다. `python3 -m app.registration status <기록>`으로 이 기기에서 쓸 수 있는지 본다.
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
7. **Microsoft Store의 `python` 별칭**은 찾아지지만 실행되지 않는다. `setup.ps1`은 실제로 실행해 보고, 설치 직후 PATH에 없으면 `py` 실행기를 쓴다.
8. **AI 도구 안의 오래된 PATH.** 설치 직후 AI 세션의 셸은 새 PATH를 모른다. `tools\v04-01\fresh-shell.ps1`로 레지스트리의 PATH를 다시 읽는다.

## 6. 이 문서의 근거와 한계

- 2026-09-25 `aux-pc`(Windows)와 `aux-pc-wsl`에서 `setup.ps1 -CheckOnly`, `setup-wsl.sh --check`, `check_setup.py`를 돌렸다. 이 PC에는 Node만 없었고 나머지 단계는 모두 "이미 됨"으로 건너뛰었다.
- **빈 컴퓨터에서 처음부터 돌려 본 것은 아니다.** 설치 경로 — winget 설치, WSL 설치와 재부팅 뒤 이어가기, Ubuntu 첫 실행의 사용자 만들기(첫 실행이 묻지 않으면 root로 만드는 대체 경로), root의 apt, CLI 설치, 로그인 셋 — 는 이 PC에서 실행되지 않았다. winget 패키지는 `winget show`로 있는 것만 확인했다. WSL 판에 따라 Ubuntu 첫 실행의 모양이 달라서 4단계가 가장 불확실하다. 새 PC에서 처음 쓴 세션은 막힌 곳을 이 문서와 스크립트에 고쳐 적는다.
- 설치 스크립트의 SHA-256은 2026-09-25에 받은 공식 파일의 값이다(2026-09-23 V04-01 기록과 같다). 공식 스크립트는 예고 없이 바뀔 수 있다.
