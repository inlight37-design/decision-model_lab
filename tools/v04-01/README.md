# V04-01 보조 스크립트 (Windows)

[V04-01 절차서](../../docs/experiments/v04-01-inventory/README.md)를 **AI 세션이 대신 실행할 때** 쓰는 스크립트다. 사람이 일반 PowerShell 창에서 직접 할 때는 없어도 된다. tier 1 기록은 [`../runtime_inventory.py`](../runtime_inventory.py)가 한다.

| 파일 | 하는 일 |
|---|---|
| [`fresh-shell.ps1`](fresh-shell.ps1) | AI 도구 변수와 PATH를 레지스트리(사용자 > 시스템) 값으로 다시 만든 뒤 스크립트를 실행한다. 셸에만 있던 AI 변수는 빠지고, 셸이 덮어쓴 값은 설정 값으로 돌아간다. 다른 변수는 그대로이므로 새 창과 같지는 않다. 설정은 바꾸지 않는다 |
| [`check-versions.ps1`](check-versions.ps1) | 세 CLI가 PATH 어디로 풀리는지, 버전, 서명자와 서명 상태(`Valid` 등)를 보여 준다. Claude 앱 전용 가상 공간에 빠진 설치가 있으면 경고한다 |
| [`probe.ps1`](probe.ps1) | 절차서 4절의 관측 **하나**를 저장소 밖 빈 폴더에서 실행하고, 가린 출력을 `hosts/<이름표>/tier2/`에 저장한다. 제한 시간이 없고 stdout·stderr를 합친다 — adapter runner가 아니다(파일 첫머리) |
| [`summarize_claude_init.py`](summarize_claude_init.py) | P4-claude 원본을 개수·상태만 남긴 요약으로 바꾼다. 없는 필드는 0이 아니라 null이다 |

저장소 루트에서 실행한다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\v04-01\fresh-shell.ps1 -Script tools\v04-01\check-versions.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools\v04-01\fresh-shell.ps1 -Script tools\v04-01\probe.ps1 P3-agy aux-pc
```

- 관측은 한 번에 하나씩 실행하고, 결과를 읽은 뒤 다음으로 간다. 예상과 다르면 멈추고 기록한다.
- 모델을 부르는 관측은 사용자의 승인이 먼저다.
- 스크립트는 ASCII로만 쓴다. Windows PowerShell 5.1은 BOM 없는 UTF-8 `.ps1`을 ANSI로 읽는다.
