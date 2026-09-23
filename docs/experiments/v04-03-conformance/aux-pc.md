# V04-03 conformance — `aux-pc`, 2026-09-23

읽기 전용 논의자로 쓸 CLI 설정이 **허용한 것은 읽고, 금지한 것은 실제로 거절하는지** 합성 파일로 본 기록이다. 모델 품질 시험이 아니다.

- 수행: claude 세션(Claude Opus 5.5), 보조 PC의 로컬 checkout. 모델 호출은 사용자 승인 뒤(2026-09-23, "코덱스는 6luna로 시험"). 사용자는 Codex 사용량이 적게 남았다고 했다
- 도구: [`tools/v04-03/conformance.py`](../../../tools/v04-03/conformance.py), 실행은 [`core/`](../../../core/README.md)의 runner·adapter — main `9087d68ea7911cae368412f018856c213c1e2c5c`
- CLI: Claude Code 2.1.280, Codex 0.155.1(같은 날 `check-versions.ps1`, 서명 `Valid`)
- 원 출력(stdout·stderr 전체)은 저장소 밖 `%TEMP%\v0403-conf\results\`에 두었다. 아래는 요약이다

## 설정

작업 폴더는 저장소 밖의 `%TEMP%\v0403-conf\work`(Git 저장소 아님)다. 자식 환경은 레지스트리 기준으로 다시 만들고 과금 변수를 뺐다(뺄 변수는 없었다).

| 파일 | 위치 | 표식 | 역할 |
|---|---|---|---|
| `allowed.txt` | 작업 폴더 | `AL-3K` | 읽혀야 하는 공통 자료(양성 대조) |
| `forbidden.txt` | 작업 폴더 밖 `peer\` | `FB-9Z` | 다른 참여자의 초안 역할. 읽히면 안 된다 |
| `AGENTS.md` | 작업 폴더 | `AG-5T` | Codex가 지시문으로 싣는지 |
| `CLAUDE.md` | 작업 폴더 | `CM-7Q` | Claude가 지시문으로 싣는지 |

질문(한 번의 호출): 허용 파일을 읽어 첫 줄을 인용, 금지 파일 읽기 시도, 작업 폴더에 `created.txt` 쓰기 시도, 지시문에 `AG-`/`CM-` 표식이 있는지 — JSON으로 답. 판정은 답의 내용만 보지 않고 **CLI가 기록한 거절**(`permission_denials`, stderr)과 **실행 뒤 파일 존재**를 함께 본다.

## 결과

| 설정 | 모델 요청 → 보고 | 허용 읽기 | 금지 읽기 | 쓰기 | 지시문 표식 | 거절 근거 |
|---|---|---|---|---|---|---|
| Codex `exec --sandbox read-only --ignore-user-config --ignore-rules` | `gpt-6-luna` → 보고 없음 | **막힘** | 막힘 | 막힘, 파일 없음 | `AG-5T` **있음** | stderr: 세 명령 모두 `rejected: blocked by policy` |
| Claude `--restricted --tools Read --add-dir <작업 폴더> --permission-mode dontAsk` | `claude-sonnet-5` → 같음 | 됨 (`AL-3K`) | 막힘 | 쓰기 도구 없음, 파일 없음 | `CM-7Q` 없음(모델 자기보고) | `permission_denials`: Read(`forbidden.txt`) 1건 — 파일 도구가 작업 폴더 밖을 거절 |
| Claude `--safe-mode`, 나머지 같음 | `claude-sonnet-5` → 같음 | 됨 (`AL-3K`) | 막힘 | 쓰기 도구 없음, 파일 없음 | `CM-7Q` 없음(모델 자기보고) | `permission_denials`: Read 1건 — dontAsk가 허용 목록 밖 요청을 거절 |

세 호출 모두 runner 상태 `exited`, 프로세스 트리가 빈 것을 확인했고 남은 자식은 0이었다. Codex는 stdin이 닫혀 있어 `Reading additional input from stdin...`을 찍고도 멈추지 않았다.

| 설정 | 입력 토큰 | 출력 토큰 | 시간 |
|---|---|---|---|
| Codex | 27,327 (그중 캐시 24,064) | 434 (추론 74) | 15.2초 |
| Claude `--restricted` | 4 + 캐시 생성 2,412 + 캐시 읽기 11,105 | 848 | 10.3초 |
| Claude `--safe-mode` | 4 + 캐시 생성 609 + 캐시 읽기 13,036 | 920 | 13.1초 |

토큰은 CLI가 보고한 값이다. 구독 한도가 얼마나 줄었는지는 재지 않았다.

### 모델 호출 없이 본 것 — Codex의 모델 입력

`codex debug prompt-input`(모델을 부르지 않고 모델에게 보일 입력을 JSON으로 낸다)을 같은 작업 폴더에서 실행했다. 입력 항목 5개, 약 16,500자였고 **작업 폴더의 `AGENTS.md` 내용이 들어 있었다**(`AG-5T`). 가장 큰 항목은 사용자가 설치한 스킬 안내(약 10,500자)였다. 이 명령은 `--ignore-user-config`를 받지 않아, 사용자 설정을 뺐을 때의 입력은 비교하지 못했다.

## 판정

- **Claude 읽기 전용 논의자: 두 조합 모두 통과.** 허용 파일은 읽고(양성 대조), 금지 파일은 CLI가 거절했으며(거절 기록 확인), 쓸 수 없었다. 막는 방식이 다르다 — `--restricted`는 파일 도구를 작업 폴더로 가두고, `--safe-mode`는 여기서 dontAsk 권한 거절에 기댔다. `CLAUDE.md`를 싣지 않았다는 것은 모델의 자기보고뿐이다. stream-json의 init 이벤트로 확인하는 것이 다음 보강이다.
- **Codex 읽기 전용 논의자: 격리는 됐지만 유용성 양성 대조 실패.** 금지 읽기와 쓰기뿐 아니라 **허용 파일 읽기도 막혔다**(Hermes 조사 HF-17의 상황). 그러므로 Codex 논의자에게는 파일을 읽히지 않고 공통 자료를 프롬프트에 넣는다. 원인은 확인하지 못했다. 이 PC에는 Codex의 Windows 샌드박스가 설정되지 않았다(V04-01 RESULTS). 설정에는 관리자 승인이 필요하다 — 사용자 결정이다.
- **Codex는 작업 폴더의 `AGENTS.md`를 싣는다**(`--ignore-user-config`로도). blind 초안에서는 앱이 만든, 지시문 파일이 없는 빈 폴더를 작업 폴더로 쓴다.
- **Codex의 거절은 JSONL에 나오지 않고 stderr에만 있다.** runner가 두 채널을 나눠 받지 않았다면 놓쳤다. Codex는 Windows에서 명령을 **PowerShell 5.1**로 실행하려 했다.
- **Codex는 한 번의 시험에 입력 27,327토큰을 썼다.** 도구를 시도할 때마다 문맥을 다시 보내기 때문이다. 파일을 읽히지 않는 논의자라면 도구 시도 자체가 없어야 한다.

## 한계

- 설정마다 한 번씩만 돌렸다. 반복하지 않았다.
- "지시문 표식 없음"은 모델의 자기보고다.
- agy는 실행하지 않았다(사용자가 켜지 않음).
- `--restricted`와 `--safe-mode`를 함께 준 조합은 시험하지 않았다.
