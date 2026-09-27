# Windows 쪽 보조 스크립트

**Claude 데스크톱 앱 같은 AI 도구 안의 세션이** 사용자의 실제 PowerShell 환경을 보려고 쓰는 스크립트다. 사람이 일반 PowerShell 창에서 직접 할 때는 없어도 된다. 쓰는 곳은 [SETUP](../../docs/SETUP.md)의 함정 절과 "어댑터를 붙이거나 모델을 바꾸기 전" 절, [AGENTS.md](../../AGENTS.md), `tools/setup/check_setup.py`다.

이름의 V04-01은 처음 만든 [날짜 기록](../../docs/experiments/v04-01-inventory/README.md)에서 왔다. 그 기록의 Windows 네이티브 CLI 조사 도구(`probe.ps1`·`summarize_claude_init.py`)는 카드 #149에서 은퇴시켰다 — Windows 네이티브 경로는 제품으로 쓰지 않는다(인계 2절 15). 다시 조사할 일이 생기면 git 이력에서 되살린다.

| 파일 | 하는 일 |
|---|---|
| [`fresh-shell.ps1`](fresh-shell.ps1) | AI 도구 변수와 PATH를 레지스트리(사용자 > 시스템) 값으로 다시 만든 뒤 스크립트를 실행한다. 셸에만 있던 AI 변수는 빠지고, 셸이 덮어쓴 값은 설정 값으로 돌아간다. 다른 변수는 그대로이므로 새 창과 같지는 않다. 설정은 바꾸지 않는다 |
| [`check-versions.ps1`](check-versions.ps1) | 세 CLI가 PATH 어디로 풀리는지, 버전, 서명자와 서명 상태(`Valid` 등)를 보여 준다. Claude 앱 전용 가상 공간에 빠진 설치가 있으면 경고한다 |

저장소 루트에서 실행한다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\v04-01\fresh-shell.ps1 -Script tools\v04-01\check-versions.ps1
```

- 스크립트는 ASCII로만 쓴다. Windows PowerShell 5.1은 BOM 없는 UTF-8 `.ps1`을 ANSI로 읽는다.
