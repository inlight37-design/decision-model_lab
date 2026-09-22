# 다음 세션 인계 — decision-model_lab

최종 갱신 **2026-09-23** · 작성 세션: claude (Claude Opus 5.5, 보조 PC의 로컬 checkout) · 브랜치 `claude/v04-01-aux-pc-20260923`

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

- 설치: Claude Code 2.1.280, Codex 0.155.1, agy 1.2.8. 셋 다 설치 스크립트가 해시를 검증했고 제조사 서명이 유효하다. `gemini`, `node`, `gh`는 없다.
- Claude 설치 프로그램이 PATH를 등록하지 않아 사용자 PATH에 `%USERPROFILE%\.local\bin`을 추가했다(백업: `%TEMP%\v0401-user-path-backup.txt`).
- 로그인: Claude Code는 claude.ai 구독(`firstParty`), Codex는 ChatGPT 로그인 — 둘 다 데스크톱 앱의 기존 자격증명으로 이미 로그인돼 있었다. **agy는 미확인**(상태 명령 없음).
- 과금 경로를 바꾸는 환경변수는 사용자·시스템 설정에 없다. Claude 데스크톱 앱의 셸에는 앱이 넣은 변수 26개(`CLAUDECODE`, `ANTHROPIC_BASE_URL` 등)가 있어서, AI 세션이 기록할 때는 `--fresh-env`를 쓴다.
- tier 1: 문서의 플래그는 모두 help에 있다. **ACP는 세 CLI 모두 help에 없다.**
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

| 브랜치 | 작성 | 내용 | 상태 |
|---|---|---|---|
세 브랜치는 한 줄로 쌓여 있다: `review/mcp-ui-runtime-20260923`(PR #3) → `claude/align-and-v04-01-prep-20260923` → `claude/v04-01-aux-pc-20260923`. **맨 위 브랜치 하나를 main에 병합하면 셋이 모두 들어간다.**

| 브랜치 | 작성 | 내용 | 상태 |
|---|---|---|---|
| `review/mcp-ui-runtime-20260923` — [PR #3](https://github.com/inlight37-design/decision-model_lab/pull/3) | 다른 AI 세션(웹 컨테이너, 사용자 PC 접근 없음) | MCP·기존 앱·Ledger UI 검토, 경계 실험, 대비 감사 | 열림. 아래 브랜치에 포함됨 |
| `claude/align-and-v04-01-prep-20260923` | claude | PR #3 정리, 문서 어긋남 수정, 협업 규칙, V04-01 도구와 절차서 | CI 녹색. 아래 브랜치에 포함됨 |
| `claude/v04-01-aux-pc-20260923` | claude | aux-pc 설치·tier 1 기록, `--fresh-env`, 제어 문자 검사, GitHub 공유 규칙 | **main 병합 대기.** 이 앱의 권한 검사가 AI 세션의 main push를 막았다 — 사용자가 GitHub에서 병합하거나 권한을 준다 |

## 4. 다음 작업

1. **(사용자)** `claude/v04-01-aux-pc-20260923`을 main에 병합한다. 그래야 GitHub만 보는 세션이 최신 상태를 본다.
2. **(사용자)** aux-pc에서 `agy`에 로그인한다 — 일반 PowerShell 창에서 `agy`를 실행해 브라우저 로그인. Claude Code와 Codex는 이미 구독 로그인 상태다.
3. **(사용자 승인 후 AI 세션)** [절차서](docs/experiments/v04-01-inventory/README.md) 4–6절: tier 2 관측(소량 한도)과 정책 확인 → [aux-pc RESULTS](docs/experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md) → tier 2 manifest → 판정(V04-03 진행 가능 여부, Q1).
4. 그 다음 V04-03(두 native 경로의 읽기 전용 독립 답변) → 승인된 테스트만 실행하는 trusted runner → 필요한 만큼 MCP로 노출 → UI 연결.

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
