# 다음 세션 인계 — decision-model_lab

최종 갱신 **2026-09-23** · 작성 세션: claude (Claude Opus 5.5, 보조 PC의 로컬 checkout) · 브랜치 `claude/v04-01-agy-fix-aux-pc-20260923`

이 파일 하나에서 시작한다. 절 구성은 고정이고 CI가 확인한다. 규칙은 [AGENTS.md](AGENTS.md)와 [협업 규칙](docs/COLLABORATION.md)에 있다.

## 0. 먼저 확인할 것

1. `git fetch --all --prune` 후 GitHub의 열린 PR과 원격 브랜치를 본다. **아래 3절에 없는 PR이 있으면 이 문서가 낡은 것이다.** 실제 상태를 기준으로 한다.
2. 지금 어느 기기인지 확인한다. 이 저장소를 편집해 온 **보조 PC(`aux-pc`)**에는 세 CLI가 설치돼 있다(아래 1절 관측).
3. 이 세션이 무엇에 접근할 수 있는지(사용자 PC / 웹 컨테이너 / GitHub만) 정하고 PR에 적는다.
4. **GitHub만 보는 세션**(ChatGPT 웹 등)이라면 main이 아직 이 파일의 최신판이 아닐 수 있다. 3절의 브랜치에서 이 파일을 다시 읽는다.

## 1. 지금 상태

**연구·설계와 오프라인 검사 저장소다. 실제 provider 연결은 아직 없다.** 근거 원장은 E01–E31 / F01–F29, 결정은 D01–D18이다. 검사 수와 결과는 [CI 실행 기록](https://github.com/inlight37-design/decision-model_lab/actions/workflows/checks.yml)이 기준이다.

| 오프라인 도구 | 무엇이고 무엇이 아닌가 |
|---|---|
| [`check_frontier_protocol.py`](tools/check_frontier_protocol.py) | 합성 완료 기록의 일관성 검사. 기록된 disposition이 규칙에 맞는지 **검사할 뿐 계산하지 않는다** |
| [`review_boundary.py`](tools/review_boundary.py) | PR #3의 순수 함수 경계 실험(이벤트 순서, UNKNOWN 예산, 봉인 화면, 한도 표시). 서버·프로세스 제어가 아니다 |
| [`audit_design_contrast.py`](tools/audit_design_contrast.py) | 디자인 토큰 대비 계산. 일반 글자 5쌍이 4.5:1 미만인 것을 기록한다 |
| [`runtime_inventory.py`](tools/runtime_inventory.py) | V04-01 tier 1. 각 CLI의 `--version`/`--help`만 실행해 기록한다. `observed`와 `configured=true`를 쓸 수 없다 |

| 산출물 | 원본 | 발행본 |
|---|---|---|
| 작업 개념도 | [docs/concept/](docs/concept/README.md) | [아티팩트](https://claude.ai/artifact/AZJfdnmMBjpEAtqsSHzjp8) |
| 디자인 시스템 `Ledger` | [design/](design/README.md) | [아티팩트](https://claude.ai/artifact/8tq8q5P8Pj7bpUtCF77FZA) — 2026-09-23 이 브랜치의 `design/`과 맞춤 |
| 검토 기록 | [docs/reviews/](docs/reviews/README.md) | — |
| 지난 인계 | [docs/handoff/](docs/handoff/README.md) | — |

### 관측한 환경 — 보조 PC, 2026-09-23, 이 세션

사용자 승인 후 이 세션이 세 CLI를 설치하고 tier 1을 기록했다. 상세는 [aux-pc 결과](docs/experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md).

- 설치 위치: Claude Code 2.1.280 `~\.local\bin`, Codex 0.155.1 `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin`(→ `~\.codex`), agy 1.2.8 **`~\.local\agy\bin`**. 셋 다 설치 스크립트가 해시를 검증했고 제조사 서명이 유효하다. `gemini`, `node`, `gh`는 없다.
- **agy는 처음에 Claude 데스크톱 앱의 가상 공간에 설치돼 사용자 터미널에서 보이지 않았다.** AppData 밖으로 재설치했다. 원인과 대처는 절차서의 "AI 세션이 Claude 데스크톱 앱 안에서 대신 실행할 때" 절.
- PATH: Claude 설치 프로그램이 등록하지 않아 `%USERPROFILE%\.local\bin`을 추가했고, agy의 옛 항목을 지우고 새 폴더가 등록됐다(백업: `%TEMP%\v0401-user-path-backup.txt`, `...-backup-2.txt`).
- 로그인: Claude Code는 claude.ai 구독(`firstParty`), Codex는 ChatGPT 로그인 — 둘 다 데스크톱 앱의 기존 자격증명으로 이미 로그인돼 있었다. **agy는 미확인**(상태 명령 없음).
- 과금 경로를 바꾸는 환경변수는 사용자·시스템 설정에 없다. Claude 데스크톱 앱의 셸에는 앱이 넣은 변수 26개(`CLAUDECODE`, `ANTHROPIC_BASE_URL` 등)가 있어서, AI 세션이 기록할 때는 `--fresh-env`를 쓴다.
- tier 1: 문서의 플래그는 모두 help에 있다. **ACP는 세 CLI 모두 help에 없다.**
- tier 2(Claude Code·Codex): 구독 인증으로 비대화형 호출 성공, 잘못된 제한 인자는 실행 전 거절, `--bare`는 구독 불가(F25 재현). Claude `-p`는 빈 폴더에서도 사용자 전역 플러그인·MCP 연결을 싣는다. Codex는 사용자 설정을 무시해도 구독으로 돈다.
- 운용 PC는 아직 관측한 세션이 없다.

### 열린 결정

| ID | 질문 | 상태 |
|---|---|---|
| Q1 | 어댑터 전송 | ACP 우선 + exec 폴백은 **가설**이다. V04-01 결과로 판정한다. 공통 계약과 모든 기능을 같은 wire protocol로 강제하는 것은 다르다(PR #3) |
| Q2 | 의존 범위 | **확정** — 여러 제품에서 패턴을 추출하고 최신 이론과 결합한다 |
| Q3 | 언어/런타임 | Python 코어, TypeScript는 화면 경계만 |
| Q4 | 첫 화면 | `unresolved`. 결정 우선과 대조표 우선을 같은 내용으로 비교하는 실험(Q8) 뒤에 판정한다 |

## 2. 사용자가 확정한 것

논쟁하지 않고 전제로 삼는다.

1. **앱을 직접 만들어 붙여 쓴다.** 셸, 오케스트레이션 코어, 근거 저장소가 이 프로젝트의 것이다.
2. **한 제품을 기반으로 채택하지 않는다.** 여러 앱의 장점을 뽑아 최신 이론과 결합하고, 검증으로 신뢰성을 확보하는 것에 같은 비중을 둔다.
3. **CLI가 전제다.** 비대화형 실행, 구조화 출력, resume/cancel, 권한 분리가 필요하다.
4. **구독 사용량을 화면에 띄운다.** 이 기기에서 관측한 값과 계정 전체 잔여(불완전, 파선)를 나눈다.
5. **상태 표시에 자원을 과하게 쓰지 않는다.** 사용량이나 색을 보여 주려고 모델을 더 부르지 않는다.
6. 공식 native 구독 CLI가 우선이다. API·추가 크레딧은 명시적 opt-in만. `agy`는 Gemini CLI가 아니다.
7. 논의자는 읽기 전용, 구현자는 한 writer. 합의는 검증이 아니다. blind 초안·반례·미합의·호출 예산을 보존한다.
8. **여러 AI가 함께 작업한다.** [협업 규칙](docs/COLLABORATION.md)을 따르고, main 병합은 사용자가 한다. (2026-09-23)
9. **V04-01은 절차서로 진행한다.** 로그인은 사용자가 직접 한다. 설치는 사용자 승인을 받고 AI 세션이 실행해도 된다. (2026-09-23)
10. **첫 V04-01은 보조 PC(`aux-pc`)에서 한다.** 사양이 크게 필요하지 않다는 판단. 운용 PC는 필요할 때 따로 기록한다. (2026-09-23)
11. **GitHub이 유일한 공유 지점이다.** ChatGPT 웹 세션은 GitHub만 보므로 커밋은 바로 push하고, 끝난 작업은 제때 main에 반영한다. (2026-09-23)

## 3. 진행 중인 작업

PR #3과 오늘의 claude 브랜치들은 사용자 요청으로 main에 병합됐다. 사용자는 **CI 녹색을 확인한 claude 세션이 main에 직접 병합하는 것**을 허락했다(2026-09-23). 병합 전 작업이 있으면 이 표에 브랜치로 적는다.

| 브랜치 | 작성 | 내용 | 상태 |
|---|---|---|---|
| `claude/v04-01-agy-fix-aux-pc-20260923` | claude | agy 재설치(가상화 문제), `tools/v04-01/` 보조 스크립트, 이어가기 지침 | CI 녹색 확인 후 main 병합 |

## 4. 다음 작업

**V04-01을 aux-pc에서 이어간다.** 남은 것은 Antigravity 로그인과 관측, 정책 확인, 판정이다. 아래 순서 그대로 한다. 명령은 저장소 루트 기준이다.

**① 사용자 — 앱 밖에서 세 CLI가 보이는지 확인하고 agy에 로그인** (한도 소모 없음)

새 PowerShell 창(시작 메뉴) 또는 앱의 터미널 탭에서:

```powershell
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User'); foreach ($c in 'claude','codex','agy') { $x = Get-Command $c -ErrorAction SilentlyContinue; if ($x) { "$c -> " + $x.Source } else { "$c -> NOT FOUND" } }
agy
```

첫 줄의 결과 세 개가 모두 경로로 나와야 한다(`NOT FOUND`면 멈추고 절차서의 "AI 세션이 Claude 데스크톱 앱 안에서 대신 실행할 때" 절). 둘째 줄의 `agy`는 브라우저 로그인을 연다. Antigravity용 Google 계정으로 로그인하고, 대화 화면이 뜨면 `Ctrl+C`로 나온다. API 키 방식은 고르지 않는다.

**② AI 세션 — Antigravity tier 2** (사용자 승인됨. P1만 모델 호출 1회)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/v04-01/fresh-shell.ps1 -Script tools/v04-01/check-versions.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/v04-01/fresh-shell.ps1 -Script tools/v04-01/probe.ps1 P3-agy aux-pc
powershell -NoProfile -ExecutionPolicy Bypass -File tools/v04-01/fresh-shell.ps1 -Script tools/v04-01/probe.ps1 P5-agy aux-pc
powershell -NoProfile -ExecutionPolicy Bypass -File tools/v04-01/fresh-shell.ps1 -Script tools/v04-01/probe.ps1 P1-agy aux-pc
```

한 줄씩 실행하고 결과를 읽은 뒤 다음으로 간다. P3는 모델 호출 없이 거절돼야 하고, P1이 로그인 여부를 간접 확인한다. 결과는 `hosts/aux-pc/tier2/`에 저장되니 [aux-pc RESULTS](docs/experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md)의 tier 2 표에 Antigravity 줄을 채운다. Git Bash에서 부를 때는 경로를 위처럼 슬래시로 쓴다.

**③ AI 세션 — 정리와 판정** (한도 소모 없음)

1. 절차서 5절 정책 확인(문서 읽기)을 RESULTS의 정책 표에 채운다.
2. tier 2 manifest를 만든다: `hosts/aux-pc/manifest.json`을 복사해 `tier: 2`로 두고, RESULTS에서 **관측한 기능만** `observed` + `observed_at` + 증거(P 번호)로 바꾼다. `python tools/runtime_inventory.py --validate <파일>`이 통과해야 한다.
3. RESULTS의 판정 표(V04-03 진행 가능 여부, Q1)를 갱신한다.
4. 커밋 → push → CI 녹색 → main 병합 → 이 문서 3·4절 갱신.

**④ 그 다음**

- **Claude Code의 깨끗한 blind 문맥 찾기** — `--bare`는 구독을 못 쓰고, 기본 `-p`는 사용자 플러그인·MCP 연결을 모두 싣는다(RESULTS의 설계 입력 1). 별도 `CLAUDE_CONFIG_DIR` 로그인과 `--strict-mcp-config`를 시험한다. V04-03 전에 풀어야 한다.
- V04-03(두 native 경로의 읽기 전용 독립 답변) → 승인된 테스트만 실행하는 trusted runner → 필요한 만큼 MCP로 노출 → UI 연결.

급하지 않은 것:

- 대비 미달 5쌍의 토큰 수정. `design/`과 아티팩트를 함께 고친다.
- `review_boundary.quota_projection`의 가정 확인 — `resetsAt` 단위와 한도 ID 형식. V04-01에서 받은 실제 응답으로 확인한다.
- v0.4 원장 대부분 항목의 `recheck` 미기입, 외부 리뷰의 저우선 지적 L1–L4, Actions의 Node 20 경고, GitHub 저장소 설명·토픽.

## 5. 하지 말 것

- **PowerShell `Get-Content`/`Set-Content`로 문서를 일괄 편집하지 않는다.** 한글이 `?`로 바뀐다. 실제로 문서 3개를 잃었다가 git에서 복구했다.
- 사용자 지시 없이 main에 push하지 않는다. 다른 세션의 브랜치에 push하지 않는다.
- 살아 있는 문서에 검사 수·원장 건수·commit 수를 적지 않는다(CI가 막는다).
- API 키 설정, 추가 크레딧, 권한 우회 플래그를 쓰지 않는다. 인증 파일과 환경변수 값을 기록하지 않는다.
- 문서만 보고 `configured = true`로 만들지 않는다.
- **백슬래시가 든 텍스트(Windows 경로 등)를 셸 heredoc 안의 파이썬으로 고치지 않는다.** 이 환경의 heredoc은 `\\`를 `\`로 바꿔 넘겨서 `\b`·`\v`가 제어 문자가 됐다(두 번 발생). 편집 도구를 쓴다. 인코딩 검사가 이제 제어 문자를 잡는다.
- **Claude 데스크톱 앱 안에서 `%LOCALAPPDATA%`에 새로 설치하지 않는다.** 앱 전용 가상 공간에 들어가 사용자 터미널에서 보이지 않는다(agy에서 발생). AppData 밖 경로(`--dir`)를 쓰고, 설치 확인은 `check-versions.ps1`과 사용자 터미널에서 한다.
- **실측 전에 설계 문서나 원장 항목을 더 늘리지 않는다.** 지금 막혀 있는 질문은 모두 실제 CLI 결과로만 풀린다.

## 6. 검사

```bash
git config core.hooksPath .githooks
python -m pip install -r requirements-design.txt
python -m unittest discover -s tests -v
python tools/validate_sources.py
python tools/validate_design_tokens.py
python tools/check_encoding.py
python tools/runtime_inventory.py --host-label <기기> --dry-run
```

`jsonschema`가 없으면 해당 검사는 skip된다. **skip은 통과가 아니다.** 로컬에서 skip이 있었다면 CI 로그로 확인한다.
