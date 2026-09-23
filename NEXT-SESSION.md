# 다음 세션 인계 — decision-model_lab

최종 갱신 **2026-09-23** · 작성 세션: claude (Claude Opus 5.5, 보조 PC의 로컬 checkout) · 브랜치 `claude/v04-01-agy-tier2-aux-pc-20260923`

이 파일 하나에서 시작한다. 절 구성은 고정이고 CI가 확인한다. 규칙은 [AGENTS.md](AGENTS.md)와 [협업 규칙](docs/COLLABORATION.md)에 있다.

## 0. 먼저 확인할 것

1. `git fetch --all --prune` 후 GitHub의 열린 PR과 원격 브랜치를 본다. **아래 3절에 없는 PR이 있으면 이 문서가 낡은 것이다.** 실제 상태를 기준으로 한다.
2. 지금 어느 기기인지 확인한다. 이 저장소를 편집해 온 **보조 PC(`aux-pc`)**에는 세 CLI가 설치돼 있다(아래 1절 관측).
3. 이 세션이 무엇에 접근할 수 있는지(사용자 PC / 웹 컨테이너 / GitHub만) 정하고 PR에 적는다.
4. **GitHub만 보는 세션**(ChatGPT 웹 등)이라면 main이 아직 이 파일의 최신판이 아닐 수 있다. 3절의 브랜치에서 이 파일을 다시 읽는다.

## 1. 지금 상태

**연구·설계와 오프라인 검사 저장소다. 실제 provider 연결은 아직 없다.** 근거 원장은 E01–E31 / F01–F31, 결정은 D01–D18이다. 검사 수와 결과는 [CI 실행 기록](https://github.com/inlight37-design/decision-model_lab/actions/workflows/checks.yml)이 기준이다.

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

**aux-pc의 V04-01은 끝났다** — 설치, tier 1, tier 2(세 CLI), 정책 확인, 판정. 상세는 [aux-pc 결과](docs/experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md)와 [tier 2 manifest](docs/experiments/v04-01-inventory/hosts/aux-pc/manifest.tier2.json).

- 설치 위치: Claude Code 2.1.280 `~\.local\bin`, Codex 0.155.1 `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin`(→ `~\.codex`), agy 1.2.8 **`~\.local\agy\bin`**. 셋 다 설치 스크립트가 해시를 검증했고 제조사 서명이 유효하다. `gemini`, `node`, `gh`는 없다.
- **agy는 처음에 Claude 데스크톱 앱의 가상 공간에 설치돼 사용자 터미널에서 보이지 않았다.** AppData 밖으로 재설치했다. 원인과 대처는 절차서의 "AI 세션이 Claude 데스크톱 앱 안에서 대신 실행할 때" 절.
- PATH: Claude 설치 프로그램이 등록하지 않아 `%USERPROFILE%\.local\bin`을 추가했고, agy의 옛 항목을 지우고 새 폴더가 등록됐다(백업: `%TEMP%\v0401-user-path-backup.txt`, `...-backup-2.txt`).
- 로그인: Claude Code는 claude.ai 구독(`firstParty`), Codex는 ChatGPT 로그인 — 둘 다 데스크톱 앱의 기존 자격증명으로 이미 로그인돼 있었다. agy는 사용자가 앱 밖 터미널에서 Google 계정으로 로그인했다. 첫 실행 때 상호작용 데이터 수집 동의가 미리 체크돼 있었다.
- 과금 경로를 바꾸는 환경변수는 사용자·시스템 설정에 없다. Claude 데스크톱 앱의 셸에는 앱이 넣은 변수 26개(`CLAUDECODE`, `ANTHROPIC_BASE_URL` 등)가 있어서, AI 세션이 기록할 때는 `--fresh-env`를 쓴다.
- tier 1: 문서의 플래그는 모두 help에 있다. **ACP는 세 CLI 모두 help에 없다.**
- tier 2: 세 CLI 모두 구독 인증으로 비대화형 JSON 호출 성공, 오타 옵션은 셋 다 실행 전 거절. **agy는 `--output-format`의 없는 값을 조용히 무시하고 실행했다.** `--bare`는 구독 불가(F25 재현). Claude `-p`는 빈 폴더에서도 사용자 전역 플러그인·MCP 연결을 싣는다. Codex는 사용자 설정을 무시해도 구독으로 돈다. agy 기본 모델은 Flash이고, agy로 Claude·GPT-OSS 모델도 부를 수 있다. 결과에 모델 이름을 주는 것은 Claude뿐이다.
- 정책: Gemini CLI 소비자 인증은 2026-06-18에 실제로 닫혔다(F30). Antigravity 약관은 제3자 소프트웨어를 통한 접근을 위반으로 규정한다(F31) — 우리 앱의 `agy` 구동이 해당하는지 불명확. agy의 `useG1Credits`(한도 소진 후 유료 크레딧)는 기본 켜짐으로 읽힌다.
- 운용 PC는 아직 관측한 세션이 없다.

### 열린 결정

| ID | 질문 | 상태 |
|---|---|---|
| Q1 | 어댑터 전송 | **exec 우선을 제안**(aux-pc V04-01): 세 CLI 모두 help에 ACP가 없고, 비대화형 실행이 세 CLI 모두 구독으로 동작했다. ACP는 adapter 계층의 선택지로 남긴다. **사용자 확인 대기** |
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
8. **여러 AI가 함께 작업한다.** [협업 규칙](docs/COLLABORATION.md)을 따른다. main 병합은 사용자가 하거나, CI 녹색을 확인한 claude 세션이 한다(사용자 허락). (2026-09-23)
9. **V04-01은 절차서로 진행한다.** 로그인은 사용자가 직접 한다. 설치는 사용자 승인을 받고 AI 세션이 실행해도 된다. (2026-09-23)
10. **첫 V04-01은 보조 PC(`aux-pc`)에서 한다.** 사양이 크게 필요하지 않다는 판단. 운용 PC는 필요할 때 따로 기록한다. (2026-09-23)
11. **GitHub이 유일한 공유 지점이다.** ChatGPT 웹 세션은 GitHub만 보므로 커밋은 바로 push하고, 끝난 작업은 제때 main에 반영한다. (2026-09-23)

## 3. 진행 중인 작업

2026-09-23의 모든 작업(PR #3 포함)은 main에 병합됐다. 사용자는 **CI 녹색을 확인한 claude 세션이 main에 직접 병합하는 것**을 허락했다(2026-09-23).

**지금 병합되지 않은 브랜치: 없음.** 새 작업을 시작하면 여기에 브랜치를 적고, 병합하는 커밋에서 이 줄을 다시 "없음"으로 돌린다. `git fetch` 결과와 다르면 git이 맞다.

## 4. 다음 작업

**V04-01(aux-pc)은 끝났다.** 판정: V04-03은 **Claude Code·Codex 두 경로로 진행 가능**, Antigravity는 조건부. 근거는 [aux-pc RESULTS](docs/experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md)의 판정 표.

**① 사용자 결정 — 다음 작업 전에 필요하다** (결정되면 이 목록과 2절을 고친다)

| 결정 | 선택지 | 근거 |
|---|---|---|
| Q1 어댑터 전송 | exec 우선(제안) / ACP 우선 유지 | RESULTS 판정 표 |
| agy를 이 프로젝트에서 구동할지 | 쓴다 / 약관 해석이 정리될 때까지 제외 / 사용자가 직접 실행한 결과만 넣는다 | F31(약관 6조) |
| agy의 `useG1Credits`(한도 소진 후 유료 크레딧) | 끈다(D18과 맞음) / 그대로 둔다 | E09, 정책 표 |
| agy의 상호작용 데이터 사용 동의 | 유지 / 설정에서 끈다 | F31(약관 5조), 첫 실행 관측 |
| 구독 경로가 닫혔을 때 | 유료 API 전환 / 해당 provider 제외 / 기능 축소 | F30 |

**② AI 세션 — V04-03 준비** (결정 뒤. 모델 호출은 사용자 승인 후)

1. Claude 논의자의 실행 조합을 문서와 대조한다: `--restricted --strict-mcp-config --disable-slash-commands --tools ""`(P4b). 파일을 읽어야 하는 논의자는 `--tools Read`와 `--add-dir`로 범위를 좁혀 한 번 더 관측한다.
2. agy를 쓰기로 했다면: 다른 값 옵션(`--model`, `--effort`)도 없는 값을 조용히 무시하는지 P3처럼 확인한다 — 특히 없는 `--model`이 기본 Flash로 바뀌면 상급 모델 배정이 조용히 무너진다.
3. adapter 공통 규칙으로 옮길 것: stdin 닫기, 옵션 값 사전 검증, 요청한 출력 형식 사후 확인, `is_error`와 exit code 함께 보기, 참여자의 회사는 모델 ID로 세기(RESULTS 설계 입력 3·4·6·7).
4. 그 다음 V04-03(두 native 경로의 읽기 전용 독립 답변) → 승인된 테스트만 실행하는 trusted runner → 필요한 만큼 MCP로 노출 → UI 연결.

보조 스크립트와 함정 목록: [`tools/v04-01/`](tools/v04-01/README.md), 절차서의 "AI 세션이 Claude 데스크톱 앱 안에서 대신 실행할 때" 절. 운용 PC를 따로 기록할 때도 같은 절차서를 쓴다.

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
