# 다음 세션 인계 — decision-model_lab

최종 갱신 **2026-09-23** · 작성 세션: claude (Claude Opus 5.5, 보조 PC의 로컬 checkout) · 브랜치 `claude/align-and-v04-01-prep-20260923`

이 파일 하나에서 시작한다. 절 구성은 고정이고 CI가 확인한다. 규칙은 [AGENTS.md](AGENTS.md)와 [협업 규칙](docs/COLLABORATION.md)에 있다.

## 0. 먼저 확인할 것

1. `git fetch --all --prune` 후 GitHub의 열린 PR과 원격 브랜치를 본다. **아래 3절에 없는 PR이 있으면 이 문서가 낡은 것이다.** 실제 상태를 기준으로 한다.
2. 지금 어느 기기인지 확인한다. 이 저장소를 편집해 온 **보조 PC**에는 CLI가 없다(아래 1절 관측). V04-01은 **운용할 PC**에서 한다.
3. 이 세션이 무엇에 접근할 수 있는지(사용자 PC / 웹 컨테이너 / GitHub만) 정하고 PR에 적는다.

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

- `claude`, `codex`, `agy`, `gemini`, `node`, `gh`가 PATH에 없다. git과 Python 3.12는 있다.
- `~/.codex/auth.json`, `~/.claude/.credentials.json` 파일이 **있다.** 데스크톱 앱들이 남긴 것으로 보인다. 내용은 열지 않았다.
- Claude 데스크톱 앱 안의 셸에는 `ANTHROPIC_BASE_URL`이 설정돼 있었다. 앱이 넣은 값으로 보이며, 일반 터미널의 환경과 다를 수 있다.
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
9. **V04-01은 절차서로 진행한다.** 설치와 로그인은 사용자가 직접 한다. (2026-09-23)

## 3. 진행 중인 작업

| 브랜치 | 작성 | 내용 | 상태 |
|---|---|---|---|
| `review/mcp-ui-runtime-20260923` — [PR #3](https://github.com/inlight37-design/decision-model_lab/pull/3) | 다른 AI 세션(웹 컨테이너, 사용자 PC 접근 없음) | MCP·기존 앱·Ledger UI 검토, 경계 실험, 대비 감사 | 열림. 아래 브랜치가 이 위에 쌓였으므로 아래를 병합하면 함께 병합된다 |
| `claude/align-and-v04-01-prep-20260923` | claude | PR #3 정리, 문서 어긋남 수정, 협업 규칙, V04-01 도구와 절차서 | push 후 사용자가 PR 생성·검토. CI 결과는 PR에서 확인 |

## 4. 다음 작업

1. **(사용자)** `claude/align-and-v04-01-prep-20260923` PR을 검토하고 병합한다.
2. **(사용자, 운용 PC)** [V04-01 절차서](docs/experiments/v04-01-inventory/README.md) 0–3절: 브랜치 만들기, 설치, tier 1 기록, 로그인.
3. **(사용자 + AI 세션)** 4–6절: tier 2 관측과 정책 확인 → `RESULTS.md` → tier 2 manifest → 판정(V04-03 진행 가능 여부, Q1).
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
