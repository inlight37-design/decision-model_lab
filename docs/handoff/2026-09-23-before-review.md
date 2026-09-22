# 다음 세션 인계 — decision-model_lab

최종 갱신 **2026-09-23**. 이 파일이 시작점이다. 전체 문서를 다시 읽지 말고 여기서 출발한다.

---

## 0. 환경

| 사실 | 값 |
|---|---|
| 저장소 | https://github.com/inlight37-design/decision-model_lab · **공개** |
| 로컬 | `C:\ai\decision-model_lab` — 정상 Git checkout, 원격과 동기화 |
| git | 2.55.0 (`C:\Program Files\Git\cmd\git.exe`). 자격증명 저장됨 → AI가 직접 push 가능 |
| CI | push·PR마다 Python 3.12/3.13. 지금까지 전부 green |
| 라이선스 | 코드 Apache-2.0 / 문서·원장 CC BY 4.0 |
| 이 PC | 사용자의 **보조 기기**. 세 CLI 미설치 |

새 기기에서 시작한다면 이것만 하면 된다.

```bash
git clone https://github.com/inlight37-design/decision-model_lab
cd decision-model_lab
git config core.hooksPath .githooks          # 인코딩 사고 방지. 아래 경고 참조
python -m pip install -r requirements-design.txt

python -m unittest discover -s tests -v      # 75개
python tools/validate_sources.py             # 근거 원장
python tools/validate_design_tokens.py       # 디자인 토큰
python tools/check_encoding.py               # BOM/UTF-8
```

`jsonschema` 를 설치하지 않으면 해당 검사는 실패가 아니라 skip 으로 표시된다. **skip 은 통과가 아니다.**

### ⚠️ 절대 하지 말 것

**PowerShell `Get-Content`/`Set-Content` 로 이 문서들을 일괄 치환하지 않는다.**
PS 5.1에서 BOM 없는 UTF-8을 ANSI(CP949)로 읽고 BOM을 붙여 되쓰므로 한글이 `?`로 사라진다. **실제로 문서 3개를 날렸다.** git에서 복구했다.

- 편집은 편집 도구로 한다
- 꼭 PowerShell이어야 하면 `[IO.File]::WriteAllText($p, $t, [Text.UTF8Encoding]::new($false))`
- 방어는 3중: `pre-commit` hook → `tools/check_encoding.py` → CI
- hook 설치: `git config core.hooksPath .githooks` (이 PC엔 완료)
- **한계:** CP949 오독으로 생긴 *그럴듯한 다른 한글*은 못 잡는다

---

## 1. 지금 상태

**저장소:** commit 63, 검사 75개, 근거 원장 59건(E01–E31 / F01–F28), 결정 D01–D18.
**실제 provider 연결은 여전히 0건.**

**모든 산출물이 저장소 안에 있다.** 다른 기기에서 clone 하면 이 파일 하나로 이어갈 수 있다.

| 산출물 | 저장소 경로 | 발행본 |
|---|---|---|
| 작업 개념도 | [`docs/concept/`](docs/concept/README.md) | [아티팩트](https://claude.ai/artifact/AZJfdnmMBjpEAtqsSHzjp8) |
| 셸 디자인 시스템 `Ledger` | [`design/`](design/README.md) | [아티팩트](https://claude.ai/artifact/8tq8q5P8Pj7bpUtCF77FZA) |
| 외부 검토 반영 기록 | [`v0.4/REVIEW_FIXES.md`](docs/architecture/v0.4/REVIEW_FIXES.md) | — |
| 외부 검토 원문 | [`docs/reviews/`](docs/reviews/README.md) | — |
| 첫 cross_check 실험 | [`docs/experiments/2026-09-22-cross-check/`](docs/experiments/2026-09-22-cross-check/README.md) | — |

개념도와 디자인 시스템은 **저장소가 소스이고 아티팩트가 발행본**이다. 한쪽만 고치고 두지 않는다 — 각 폴더의 README에 동기화 절차가 있다.

---

## 2. 사용자가 확정한 것

**이것들은 논쟁하지 말고 전제로 삼는다.**

1. **앱을 직접 만들어 붙여 쓴다.** 셸(1층) + 오케스트레이션 코어(2층) + 근거 저장소(5층)가 우리 것.
2. **Q2 결론 — "한 제품을 기반으로 채택"이 아니다.** 사용자는 협업앱 경험이 거의 없고, **여러 앱의 장점과 노하우를 뽑아 최신 이론과 결합**하기를 원한다. 검증을 통한 신뢰성 확보도 같은 비중.
   → 즉 "Orca를 쓸까 말까"는 틀린 질문이었다. 올바른 질문은 **"각 제품에서 무엇을 배울 것인가"**.
3. **CLI가 전제다.** GUI/확장은 비대화형 실행·구조화 출력·session resume/cancel·권한 분리를 안 준다. 근거 `F17`/`E06`/`F19`가 전부 headless CLI에 관한 것.
4. **구독 사용량을 화면에 띄운다.** 한도 소모를 알 수 없는 것이 실제 불편.
5. **상태 표시에 과도한 자원을 쓰지 않는다.**

---

## 3. 사용자의 세 질문에 대한 답

### 3-1. 구독 사용량을 실시간으로 볼 수 있는가 — **부분적으로만**

Claude Code 공식 문서(`/docs/en/costs`) 확인 결과:

| 가능 | 방법 |
|---|---|
| 세션 단위 토큰·비용 | `--output-format json` → `total_cost_usd` + 모델별 내역 (**client-side 추정치**) |
| 요금제 사용량 막대 | `/usage` — Pro/Max/Team/Enterprise. `d`/`w`로 24시간/7일 전환 |
| 귀속 분석 | skill·subagent·plugin·**MCP 서버별** 사용 비중 |
| 실시간 스트림 | **OpenTelemetry 내보내기** — "per-user 토큰·비용을 near real time으로 내보내는 유일한 방법" |
| 캐시 상태 | `prompt_cache` 객체 (요청 수, 캐시 적중률, warm/cold) |

**결정적 한계 (원문):** `/usage` 수치는 *"computed from local session history on this machine, so usage from other devices or claude.ai is not included."* 게다가 plan limits를 가져오는 usage endpoint는 **rate limit에 걸린다**.

→ **설계 결론:** 사용량을 **두 줄로 나눈다.** ① 이 기기에서 관측한 값 ② 계정 전체 잔여(불완전). ②는 확정값으로 쓰지 않고 파선 처리한다. 이건 `Ledger`의 `unknown` 규칙과 정확히 같은 처리다.

**미확인:** Codex와 Antigravity의 잔여 한도 조회 경로. `V04-01`에서 확인할 것.

### 3-2. MCP는 이 프로젝트에 어떻게 쓰이는가

MCP = AI 앱과 외부 시스템을 잇는 공개 표준. 서버가 **tools / resources / prompts**를 노출하고 클라이언트가 붙는다.

**여기서의 쓸모 — 하나뿐이지만 핵심이다.**

> **verifier를 MCP 서버로 노출한다.** `run_test`, `resolve_source`, `record_check`.

그러면 모델이 "검증했습니다"라고 *말하는* 대신 **도구를 호출하고, 결과를 우리 코드가 기록한다.** `check.kind`와 `check.status`가 모델의 자기 보고가 아니라 실행 결과가 되는 지점이 바로 이것이다.

**주의 (공식 문서):**
- MCP 도구 정의는 이제 **기본적으로 지연 로딩**된다 — 이름과 서버 설명만 문맥에 들어간다
- 그래도 *"CLI 도구가 MCP 서버보다 문맥 효율이 좋다"* — per-tool listing이 없기 때문
- `/usage`가 MCP 서버별 사용 비중을 보여주므로 **우리 서버의 비용을 측정할 수 있다**

→ **결론:** 검증 도구는 MCP로, 단순 조회는 CLI로. 처음부터 MCP를 많이 붙이지 않는다.

### 3-3. 이 상태들을 실제로 어떻게 구분하는가 — **거의 전부 공짜다**

**색을 칠하려고 모델을 더 부르지 않는다.** 신호의 출처는 셋뿐이다.

| 층 | 무엇이 정하는가 | 추가 비용 |
|---|---|---|
| **A. 코드가 계산** | `disposition`, 호출 수, 정족수, blind 상태 | **0** |
| **B. 실행 결과** | `check.kind`, `check.status` | 그 검사 자체뿐 |
| **C. 모델** | 초안 → claim 추출 | 기존 호출에 구조화 출력을 얹음 |

- **A는 이미 있다.** `tools/check_frontier_protocol.py`의 `validate()`가 순수 함수로 계산한다. 화면은 표시만 한다.
- **B는 자기 보고가 아니다.** 테스트 러너가 돌면 `test`, source resolver가 원문 위치를 찾으면 `source`. 모델이 "확인했다"고 쓴 건 `self_report`이고 승격에 안 쓰인다.
- **C만 모델이 필요하고 호출을 추가하지 않는다.** `--output-format json --json-schema`로 초안을 받을 때 같이 받는다. 별도 extractor는 예산에서 차감되므로(`D13`) 만들지 않는다.

**남는 위험은 C의 추출 손실 하나.** 초안에 있던 조건이 claim이 안 되면 원장이 완벽해도 결과가 틀린다. → `Extraction loss` 지표가 그래서 있다.

---

## 4. 생태계 — 무엇을 배울 것인가

사용자 방침(§2-2)에 맞춰 **"채택 여부"가 아니라 "추출할 패턴"**으로 정리한다.
라이선스·규모는 2026-09-22-23 GitHub API 직접 확인.

| 프로젝트 | 라이선스 | 규모 | **가져올 것** |
|---|---|---|---|
| **Orca** (stablyai) | MIT | TS · 75.2k★ | 참여자별 worktree 격리, 헤드리스 모드, "자기 구독으로 실행" 모델 |
| **herdr** (herdrdev) | Apache-2.0 | **Rust · 40.2k★** | **세션이 재부팅을 넘어 생존, 어디서든 재접속, pane을 working/blocked/idle로 표시, 소켓 API.** `D16`과 `UNKNOWN` 문제의 정답 후보 |
| **AionUi** (iOfficeAI) | Apache-2.0 | TS · 33.0k★ | 설치된 CLI 자동 탐지, 로컬 SQLite, **ACP 실사용** |
| **Paseo** (getpaseo) | **Apache-2.0** | TS · 18.1k★ | 자체 호스팅 데몬 + 다중 클라이언트(데스크톱/웹/모바일), 텔레메트리 없음 |
| **ACP** (Zed) | Apache-2.0 | 표준 | 에디터↔에이전트 JSON-RPC/stdio. **공식 Python 라이브러리 있음** |
| Superset | Elastic-2.0 | — | 비 OSS. 참고만 |

**⚠️ 이전 세션의 오류 두 건을 정정했다:**
- Paseo는 **AGPL-3.0이 아니다.** Apache-2.0이다(GitHub는 third-party 조항 때문에 `NOASSERTION` 반환). "전염성이라 피하라"고 한 것은 틀렸다.
- ACP는 과금 정보가 **전혀 없는 게 아니다.** 세션 누적 `Cost`(amount+currency)가 있다. 단 **구독 잔여 한도·entitlement는 없다.**

**아무도 다루지 않는 것:** claim ledger, 미합의 보존, 근거 회계. 조사 범위에서 발견되지 않았다 → 우리의 고유 기여는 정확히 거기고, **배선은 재발명하지 않는다.**

---

## 5. 디자인 시스템 `Ledger`

소스 [`design/`](design/README.md) · 발행본 [아티팩트](https://claude.ai/artifact/8tq8q5P8Pj7bpUtCF77FZA) · 브랜드북 [`design/project/README.md`](design/project/README.md)부터 읽는다.

### 지배 규칙 셋

1. **미검증이 검증처럼 보이면 안 된다** — 투표는 회색 캡션, `unknown`은 파선(0이 아님), 취소 버튼은 종료를 선언하지 않음
2. **전부 보여주지 않는다** — 1층: 결정 + 뒤집을 조건 / 2층: 미해결 + 다음 검사 / 3층: 대조표. 근거는 `F28`
3. **채움이 아니라 괘선** — 알약 배지를 쓰면 네 상태가 같은 크기 색 덩어리가 되어 무게 차이가 사라진다

### 색 — 흔한 반사를 뒤집었다

| | 보통 | 여기 | 왜 |
|---|---|---|---|
| `rejected` | 빨강 | **회색** | 반박은 검증이 제 일을 한 결과. 끝난 일 |
| `unresolved` | 회색 | **붉은 잉크 + 3px 괘선** | 사람이 봐야 하는 일 |
| `unknown` | 빈칸/0 | **파선** | 빈칸은 "없음"으로 읽힌다 |

팔레트는 **교정 잉크** 계열(승인 도장 녹색 / 오커 / 흑연 / 교정 붉은색), 모서리 2–3px, 그림자는 팝오버에만.

### 컴포넌트 5개

| | 무엇을 강제하는가 |
|---|---|
| `DispositionBadge` | 괘선 두께가 무게를 나른다 |
| `EvidenceChip` | `kind:status` 동시 표기 — `vote:passed`≠`test:passed` |
| `BlindBarrier` | 제출 여부만. **내용을 전달조차 하지 않는다**(블러는 복사·스크린샷에 남음) |
| `BudgetMeter` | 소진량이지 진척도가 아니다. 실패·종료불명도 칸을 차지 |
| `DecisionCard` | **첫 화면.** "뒤집을 조건"은 비울 수 없는 슬롯 |

### 고친 문제 (2026-09-23)

- `display` 30px의 line-height 36→44px — 디센더(g, y) 잘림
- 미리보기 `height` 전부 상향 — 설명이 잘려 보임
- AI 슬롭 느낌 제거: 알약 배지 → 괘선, 반경 6→2~3px, 일반적 teal/amber → 교정 잉크 팔레트
- [`tools/validate_design_tokens.py`](tools/validate_design_tokens.py)를 CI에 연결했다 — 잘못된 hex 하나가 토큰을 통째로 드롭시키는데 화면에서는 티가 안 난다(실제로 두 번 발생). 행간이 글자 크기의 1.25배 미만이면 디센더 잘림으로 잡는다

---

## 6. 열린 결정

| ID | 질문 | 상태 |
|---|---|---|
| Q1 | 어댑터 전송 | **ACP 우선 + exec 폴백.** Python 라이브러리 있음. 도구별 지원은 `V04-01` |
| Q2 | 의존 범위 | **확정 — 여러 제품에서 패턴 추출 + 최신 이론 결합**(§2-2) |
| Q3 | 언어/런타임 | **Python 코어 유지, TS는 화면 경계만.** "ACP 때문에 TS 필요" 전제는 무너짐 |
| Q4 | 첫 화면 | **`unresolved`.** 두 AI가 claim ledger로 합의했으나 `F28`이 반대 방향 실증 근거. 판정은 Q8 화면 비교 실험 이후 |

---

## 7. 다음 작업 — `V04-01` 런타임 인벤토리

**실제로 운용할 기기(메인 컴퓨터)에서** 수행한다. 인벤토리 결과는 호스트마다 다르다.

기록할 것 (비밀 값 없이):

- [ ] 세 CLI의 설치 버전 · help · 로그인 방식 · 사용 가능한 상급 모델
- [ ] **ACP 지원 여부** (Q1을 결정한다)
- [ ] 구조화 출력 · session resume · cancel 지원
- [ ] **깨끗한 초기 문맥과 구독 인증을 동시에 만족하는 조합이 있는가** — `F25`의 `--bare` 함정
- [ ] **필수 제한이 적용됐는지 실행 *전에* 확인할 방법** — `F26`의 강등 경로
- [ ] 잔여 한도 조회 경로 (Codex · Antigravity)
- [ ] 구독 인증 경로의 **정책 변경 이력**과 닫혔을 때의 대안
- [ ] 요금제별 **동시 기기 제한** 유무 — 가정하지 말 것

문서만 보고 `configured = true`로 만들지 않는다.

그 다음 `V04-03`: 두 native 경로의 **읽기 전용** 독립 답변 비교.

---

## 8. 이 프로젝트에서 배운 교훈

저장소가 설계한 `cross_check`를 실제로 한 번 돌렸고, 프로토콜 자체에 대해 네 가지가 관측됐다. 전부 `REVIEW_FIXES.md` §6에 있다.

1. **공통 입력의 오류는 모두에게 전파된다.** `P0`의 "같은 버전으로 제공한다"는 **같은 오류를 함께 받는다**는 뜻이기도 하다. (ACP 과금, Paseo 라이선스 — 두 건)
2. **빠진 선택지는 반례가 나올 수 없다.** herdr를 목록에 안 넣어서 상대도 못 잡았다.
3. **합의가 근거를 뜻하지 않는다.** 같은 결론이어도 한쪽만 코드를 읽었을 수 있다.
4. **locator를 정확히 따라가지 않으면 옳은 주장을 기각한다.** `--bare` 건은 첫 조회 페이지에 없어서 기각할 뻔했다.

그리고 **교차검토를 한 번 돌렸다는 것이 이 방식이 단독보다 낫다는 증거는 아니다.** 대조군 없이 한 번 실행했을 뿐이고, 판정은 Q0–Q7 실험 몫이다.
