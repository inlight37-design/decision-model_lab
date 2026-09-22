# decision-model_lab 정밀 리뷰

**대상:** https://github.com/inlight37-design/decision-model_lab
**검토 기준 commit:** `c1605f90` (main tip, 2026-09-22)
**검토일:** 2026-09-22
**검토자:** Claude Opus 5 (외부 리뷰)

---

## 0. 검토 범위와 방법 — 실제로 한 것과 하지 않은 것

이 저장소 자신의 기록 원칙(주장·검증·미검증을 분리)을 이 리뷰에도 적용한다.

### 실제로 수행한 것

| 작업 | 결과 |
|---|---|
| 원격 snapshot 전체 다운로드 (`codeload` zip, main tip) | 51개 파일 확보 |
| Python 코드 3개 + 테스트 3개 전문 정독 | 아래 §3·§5 |
| 격리 venv(Python 3.12.6 / jsonschema 4.26.0)에서 전체 테스트 실행 | **71/71 통과** |
| `tools/validate_design.py` 실행 | **25/25 통과** |
| `tools/validate_v02.py`, `tools/check_frontier_protocol.py` 실행 | 각 PASS |
| 의존성 미설치 상태 재현 | **26 errors / 71** (§6 H2) |
| 저장소 밖 디렉터리에서 테스트 실행 | `ModuleNotFoundError` (§6 M3) |
| 두 Python 파일의 Git blob SHA 직접 계산 | VALIDATION.md 기록값과 불일치 (§6 M5) |
| `sources.json` 2개(E01–E31, F01–F24) 필드 완전성 프로그램 감사 | §6 M1·M2 |
| GitHub API로 PR #1/#2, commit 이력, 저장소 메타데이터 조회 | §2 |
| 외부 근거 대조 검색 3건 | §7 |
| v0.1–v0.4 설계 문서 정독 (약 340KB 중 핵심 문서 전량) | §4 |

### 수행하지 않은 것

실제 Codex/Claude Code/`agy` 설치·호출, 구독 과금·quota 계측, OS sandbox 시험, 원장 F/E 출처 원문 전수 재확인, 논문 재현, 모든 문서의 문장 단위 사실 확인. **이 리뷰는 정적 검토와 오프라인 실행 검증이며, 저장소가 미검증으로 표시한 항목을 검증한 것이 아니다.**

### 주의: 로컬 사본이 낡음

`C:\ai\decision-model_lab`은 **v0.3 상태**이며 원격의 v0.4(`docs/architecture/v0.4/`, `tools/check_frontier_protocol.py`, `tests/test_frontier_protocol.py`, `tests/test_research_integrity.py`)가 없다. 또한 이 PC에 `git`이 설치되어 있지 않아 로컬 사본은 Git checkout도 아니다. 이 리뷰는 전부 **원격 main 기준**이다. 로컬에서 이어서 작업한다면 먼저 동기화가 필요하다.

---

## 1. 한 줄 요약

> **오케스트레이터를 만든 저장소가 아니라, 오케스트레이터가 지켜야 할 인식론적 불변식을 실행 가능한 코드로 못 박은 저장소다.** 그 일을 매우 잘했다. 남은 약점은 설계가 아니라 **저장소 위생(CI·라이선스·패키징)과 원장 스키마**에 있다.

---

## 2. 저장소 정체성

| 항목 | 값 |
|---|---|
| 생성 / 최종 push | 2026-09-21 08:57Z / 2026-09-22 11:17Z (**약 26시간**) |
| commit 수 | 51 |
| 주 언어 | Python (실제로는 문서 ~92%) |
| description / topics / license | **모두 없음** |
| PR | #1 merged(`2885bf81`, 32 commits/25 files/+2979-36), #2 merged(`c1605f90`) |
| issues / stars / CI | 0 / 0 / **워크플로 없음** |

문서 약 340KB, 실행 코드 약 33KB. **비율 10:1**. 이것은 결함이 아니라 의도된 형태다 — 저장소 스스로 "research and architecture repository, not an implemented orchestrator"(AGENTS.md)라고 선언한다.

26시간에 51 commit, +2979 라인. 밀도가 매우 높은 단기 스프린트이며, 아래 §6의 스테일 참조들은 대부분 이 속도의 부산물이다.

---

## 3. 뼈대 분석 — 실제로 존재하는 것

### 3.1 물리적 구조

```
decision-model_lab/
├─ AGENTS.md                 에이전트 오리엔테이션 (11줄, 밀도 높음)
├─ README.md                 v0.4 진입점
├─ requirements-design.txt   jsonschema==4.26.0  ← 유일한 외부 의존성
├─ contracts/                합성 JSON 계약 (wire schema)
│  ├─ v0.1.schema.json           task/decision/worker_result 패킷
│  └─ v0.2/pilot.schema.json     plan/proof
├─ examples/                 합성 fixture (실제 키·명령 없음)
├─ tools/                    검사기 3개
│  ├─ validate_design.py         v0.1 계약, jsonschema 사용
│  ├─ validate_v02.py            v0.2 plan/proof 결합
│  └─ check_frontier_protocol.py v0.4 협업 기록, 표준 라이브러리만
├─ tests/                    unittest 71개
└─ docs/architecture/        v0.1 → v0.2 → v0.3 → v0.4 누적 보존
```

**핵심 관찰:** 버전이 올라가도 이전 버전을 삭제하지 않는다. v0.4는 v0.3 위에 얹히고, v0.2 계약은 "변경하지 않는다"가 명시적 제약이다(HANDOFF §3). 이것은 연구 저장소로서 올바른 선택 — 근거의 계보를 추적 가능하게 유지한다.

### 3.2 실행 코드의 3층 구조

세 검사기는 **서로 다른 시점의 서로 다른 계약**을 담당하며, 의존성 정책도 다르다.

| 층 | 파일 | 대상 | 의존성 | 규모 |
|---|---|---|---|---|
| v0.1 | `validate_design.py` | task/decision/worker_result 패킷 | jsonschema | 25 검사 |
| v0.2 | `validate_v02.py` | pilot plan ↔ proof 결합 | jsonschema | 28 테스트 |
| v0.4 | `check_frontier_protocol.py` | 상급 모델 협업 완료 기록 | **표준 라이브러리만** | 40 테스트 |
| 문서 | `test_research_integrity.py` | 원장 ↔ ADR ↔ 링크 | (strict_load 경유) | 3 테스트 |

v0.4가 표준 라이브러리만 쓰는 것은 의도적 설계다(README: "새 검사는 Python 표준 라이브러리만 사용합니다"). 덕분에 `python tools/check_frontier_protocol.py`는 clone 직후 바로 돌아간다. **좋은 판단이다.** 다만 이 정책이 v0.2 층에는 적용되지 않아 §6 H2의 문제가 생긴다.

### 3.3 v0.4 checker의 불변식 — 저장소의 진짜 산출물

`check_frontier_protocol.py:47-147`의 `validate()`는 약 100줄에 다음을 강제한다. 이 목록이 이 저장소가 무엇을 만들고 있는지를 가장 정확히 보여준다.

**구성 무결성**
- `synthetic is True`가 아니면 거부 (`:54`) — 실제 운영 기록을 이 도구로 승인할 수 없다
- 참여자 수 = 선언 정족수, provider가 대소문자 무시 기준으로 전부 상이 (`:69-71`)
- 모든 참여자 `quality == "frontier"` — 상급 자리를 조용히 저가 모델로 바꿀 수 없음 (`:69`)

**독립성 장벽 (blind barrier)**
- 모든 초안의 `peer_inputs == []` (`:80`) — 초기 답변의 동료 오염 차단
- 모든 초안의 `input_digest`가 동일 (`:81`) — 서로 다른 입력을 준 뒤 "독립 비교"라 부를 수 없음
- review 호출 시점에 이미 모든 초안이 확보되어 있어야 함 (`:95`)
- 자기 초안 검토 금지 (`:100`)

**예산 정직성**
- 실패·거부·timeout 호출도 `max_calls`에서 차감 (`:84` — `len(calls)` 기준)
- `cross_check`는 review 라운드 0, `deliberate`는 최대 1 (`:63`)
- `outcome == "unknown"`인 호출이 남아 있으면 완료 기록으로 인정하지 않음 (`:110`)
- `funding.mode == "subscription_only"` 및 `paid_fallback is False` 강제 (`:58`)

**근거 규율 — 가장 중요한 부분**
- `supported` 승격에는 `test`/`source`/`calculation` 중 **passed**가 최소 1건 필요 (`:133`)
  → `vote`와 `self_report`는 kind로 허용되지만 **승격 근거가 될 수 없다**
- 같은 claim에 `failed` check가 하나라도 있으면 `supported` 불가 (`:134`)
- **claim은 자신을 target으로 기록된 모든 check를 참조해야 한다** (`:131`)
  → 불리한 검사를 `check_refs`에서 빼서 숨기는 경로를 막는다
- `report`의 4개 disposition 목록이 claims와 정확히 일치해야 함 (`:140`)
  → 최종 보고서에서 반대 의견을 지울 수 없다
- `unresolved` 또는 `qualified`가 있으면 status는 반드시 `qualified` (`:143`)
  → 미해결이 남은 결과를 `review_ready`로 라벨링할 수 없다

**입력 경계 방어**
- 중복 JSON 키 거부 (`:25`) — `"paid_fallback": true, "paid_fallback": false` 같은 상충 정책 기록 차단
- `NaN`/`Infinity` 리터럴 거부 (`:30`), `1e999` float 오버플로도 `json.dumps(allow_nan=False)`로 차단 (`:52`)
- `type(x) is int`로 bool 차단 (`:61`, `:65`, `:92`) — `max_calls: true`가 정수 1로 통과하는 것을 막음

`demo()`(`:150-166`)는 이 철학을 한 문장으로 요약한다: **세 모델이 전원 동의한 claim `c2`도 근거가 없으면 `unresolved`로 남는다.** 그리고 `test_demo_keeps_unanimous_unverified_claim_unresolved`가 그것을 테스트로 고정한다.

### 3.4 설계된 아키텍처 (미구현)

`v0.4/02-frontier-architecture.md` §3의 제어 흐름:

```
입구(Codex/MCP/CLI/UI)
  → Task controller + policy      (상태·권한·예산·종료의 단일 소유자)
  → Strategy planner / scheduler
  → Context builder + evidence manifest
  → [Codex | Claude | Antigravity] adapter — 각 native 하네스 유지
  → 독립 artifact
  → Claim ledger / targeted cross-review
  → Verifier (source/test/experiment)
  → Strong synthesis + report gate
  → 지원된 결론 | 반례 | 미합의 | 다음 검증 | 사용량
```

네 실행 모드: `single` / `cross_check` / `deliberate` / `build_review`.
`deliberate` 프로토콜 P0–P5: 고정 → 독립 초안 → 주장별 대조 → 제한 교차검토 → 외부 확인 → 합성/인계.
결정 D10–D18이 근거 F01–F24에 연결됨.

**이 전체가 설계 제안이며 코드가 아니다.** 문서 스스로 `:5`에서 "상태: 설계 제안. 아래 모듈·상태·상한은 실제 CLI runner가 구현한 기능이 아니다"라고 선언한다. §3.3의 checker는 이 설계 중 **완료 기록의 형식적 일관성**이라는 얇은 단면만 구현한 것이다.

---

## 4. 문서 아키텍처

### 4.1 버전 누적 구조

| 버전 | 성격 | 현재 지위 |
|---|---|---|
| v0.1 | 초기 참조 아키텍처 5부작 + 계약 | 보존, 참고 |
| v0.2 | bounded_patch 실험 설계 + **합성 계약(동결)** | 계약은 현행 유지 |
| v0.3 | 구독 CLI 우선, adapter, E01–E31, D01–D09 | **현행 기반** |
| v0.4 | 상급 모델 협업 확장, F01–F24, D10–D18 | **현행 제안** |

"아키텍처 버전"과 "wire schema 버전"을 분리한 것이 중요한 설계 결정이다. v0.4는 아키텍처 v0.4지만 계약은 여전히 v0.2다(HANDOFF §3: "v0.4는 production wire-schema 업그레이드가 아니다").

### 4.2 근거 원장 — 이 저장소의 차별점

`sources.json` 2개, 총 55개 항목. v0.4 원장의 구조:

```json
{
  "id": "F01",
  "title": "Microsoft Researcher: Critique and Council",
  "url": "https://...",
  "published": "2026-03-30",
  "kind": "official_product_report",
  "inspection": "article sections on Researcher",
  "locator": "Multi-model intelligence in Researcher",
  "claim": "...",
  "limits": "...",
  "decisions": ["D10", ...]
}
```

`kind` 분류가 정교하다 — v0.4에서 17종: `official_product_report`, `public_prototype`, `research_paper`, `peer_reviewed_abstract`, `workshop_research`, `exploratory_preprint` 등. **"논문"과 "워크숍 채택작"과 "abstract만 읽음"을 구별한다.** 이 구별은 EVIDENCE_FOLLOWUP.md에서 실제로 작동한다 — F24를 "ICML 2026 **워크숍** 채택작"으로 표시하고, F09/F10/F11/F20은 "abstract 수준 확인"으로 한정한다.

`limits` 필드가 v0.4 24개 전부에 비어 있지 않게 채워져 있다. 예: F24는 "SWE-bench Verified 500개에서 75.2% 대 단독 71.6%를 보고하지만 token은 약 4.5배였다"를 기록하고, 도입 범위를 "수치나 추가 round를 복제하지 않는다"로 명시한다.

**결정 근거 밀도** (출처 → 결정 역인덱스, 직접 계산):

| v0.3 | D01:11 D02:8 D03:6 D04:7 D05:8 D06:4 D07:10 D08:11 D09:5 |
|---|---|
| **v0.4** | D10:7 D11:7 D12:9 D13:7 D14:5 D15:5 **D16:1** D17:13 D18:6 |

D17(대조군 설계)이 13건으로 가장 두껍고, **D16(단일 controller + durable journal)은 F14 하나뿐**이다. §6 L5 참조.

---

## 5. 강점 — 정밀 평가

### S1. 인식론적 규율이 문장이 아니라 테스트로 존재한다 ★★★

대부분의 "AI 협업" 저장소는 README에 "다수결은 진실이 아니다"라고 쓰고 끝난다. 이 저장소는 그것을 실행 가능한 실패로 만든다:

```python
def test_votes_are_not_verification(self):
    self.assert_invalid(lambda r: r["checks"][0].update(kind="vote"))

def test_final_loses_dissent(self):
    self.assert_invalid(lambda r: r["report"]["unresolved"].clear())

def test_unlinked_counterevidence_cannot_be_hidden(self):
    self.assert_invalid(lambda r: r["checks"].append({
        "id": "hidden-failure", "target": "c1", "kind": "test",
        "status": "failed", "log_ref": "synthetic://failure"}))

def test_skipped_check_is_not_pass(self):
    self.assert_invalid(lambda r: r["checks"][0].update(status="skipped"))

def test_silent_quality_downgrade(self):
    self.assert_invalid(lambda r: r["participants"][1].update(quality="economy"))
```

이 다섯 개가 저장소 전체의 논지를 압축한다. **원칙이 회귀 테스트로 고정되어 있으면 나중에 편의를 위해 조용히 포기할 수 없다.** 이것이 이 저장소의 가장 큰 기여다.

### S2. 입력 경계 방어 수준이 연구 저장소 기준으로 이례적 ★★★

- 중복 JSON 키를 파싱 단계에서 거부 — 상충하는 정책 기록의 은폐 차단
- `parse_constant`로 `NaN`/`Infinity` 리터럴 차단, 추가로 `json.dumps(allow_nan=False)`로 `1e999` 오버플로까지 차단 (두 방어가 서로 다른 벡터를 막는다)
- `type(x) is int`로 `isinstance` 우회(bool은 int의 서브클래스) 차단
- 이 세 가지 전부에 대응 테스트가 있고, 중복 키와 비표준 수는 **실제 subprocess CLI 호출로** 검증한다 (`FrontierCliTests`)

그리고 `validate()`의 예외 처리(`:144-147`)가 `KeyError`/`TypeError`/`AttributeError`/`ValueError`를 `ProtocolError`로 변환해 CLI가 traceback 없이 `INVALID:`를 출력하게 한다 — 테스트가 `assertNotIn("Traceback", result.stderr)`로 이것까지 고정한다.

### S3. 문서-코드 양방향 정합성을 테스트가 강제 ★★

`test_adr_and_registry_mappings_are_bidirectional`은 `sources.json`의 `decisions` 역인덱스와 Markdown ADR 표의 `| D17 | ... | F07–F12/F15/... |` 행을 파싱해 **완전 일치**를 요구한다. `evidence_ids()`는 `F07–F12` 같은 en-dash 범위까지 전개한다.

문서 저장소에서 이런 장치는 드물다. FINAL_REVIEW에 따르면 이 테스트는 실제로 결함을 잡아 D01/D02/D10/D11의 누락 연결을 고치게 했다.

### S4. 스코프 정직성이 출력에까지 배어 있다 ★★★

```python
print("PASS: synthetic record consistency only; no model or evidence executed.")
print("Not executed: models, commands, real tests, authentication, sandboxing, recovery.")
```

**성공 메시지에 "무엇을 검증하지 않았는가"가 붙는다.** VALIDATION.md는 §5·§6을 통째로 "checker가 보장하지 않는 것"과 "아직 하지 않은 검증"에 할애한다. FINAL_REVIEW는 "GitHub Actions 실행 기록은 0건이므로 이 결과를 CI 성공이라고 부르지 않는다"고 스스로 못 박는다.

숫자에 대한 규율도 일관된다 — "71은 테스트 메서드 수이며 사용자 과제·모델 호출 수가 아니다", "F01–F24는 24개의 독립 실험이 아니다".

### S5. 평가 설계 Q0–Q6이 실제 인과추론으로 타당 ★★★

`03-evaluation-and-roadmap.md` §2의 대조군 설계는 이 분야 문헌의 가장 흔한 오류를 정면으로 피한다:

| | |
|---|---|
| Q1 | 같은 상급 모델 단독 + **늘어난 추론 예산** → 단순 compute 증가 효과 분리 |
| Q2 | 같은 모델 독립 3회 + 같은 합성 → **모델 다양성 없는** ensemble 이득 분리 |
| Q3 | 세 회사 독립 생성 + 합성, **토론 없음** → 이종 구성 효과 분리 |
| Q4 | Q3 + 한 라운드 교차검토 → **토론 자체**의 증분 효과 |

"세 모델을 썼더니 좋아졌다"를 (a) 이종성 (b) 3배 compute (c) 토론 (d) 더 나은 도구 로 분해하려는 시도다. 대부분의 multi-agent 논문이 (b)를 통제하지 않아 과대평가된다는 점을 고려하면, 이 설계는 문헌 평균보다 엄격하다.

추가로 **Synthesis loss**(독립 후보에는 정답이 있는데 최종 답이 틀린 비율)와 **correct→wrong 전이**를 별도 지표로 둔 것이 특히 좋다. 합의율 상승을 개선으로 읽지 않겠다는 의지다.

### S6. 계약과 실제의 간극을 언어로 구분 ★★

`configured` vs `documented_supported` (v0.3 §2), `passed`는 "CheckResult의 특정 검사 상태이며 모든 claim의 정답 표시가 아니다"(v0.4 §7), "`exit 0`과 task 성공은 다르다"(v0.3 §5), "prompt의 '수정 금지'는 OS 쓰기 차단을 대신하지 않는다"(v0.4 §8).

특히 v0.3 §5의 **"모델의 success 문자열 → 실제 artifact → 독립 검사"** 3층 분리는 에이전트 시스템 설계의 핵심 함정을 정확히 짚는다.

---

## 6. 발견한 문제

### 🔴 H1 — CI가 없다. 저장소의 핵심 규율이 저장소 자신에게 적용되지 않는다

**사실:** 원격에 `.github/` 디렉터리가 없다. 워크플로 0개, Actions 실행 0건.

**왜 중요한가:** 이 저장소의 논지는 "검증되지 않은 주장을 검증된 것처럼 기록하지 말라"이고, 그것을 71개 테스트로 강제한다. 그런데 **그 71개가 깨졌는지 확인하는 자동 장치가 없다.** README·VALIDATION·FINAL_REVIEW·EVIDENCE_FOLLOWUP 네 문서가 "71개 통과"를 주장하지만, 그 주장의 갱신은 전적으로 사람의 기억에 의존한다.

특히 `test_research_integrity.py`는 문서 편집만으로도 깨진다 — 누군가 Markdown 링크를 옮기거나 ADR 표 행을 수정하면 테스트가 실패하는데, 그 사실을 아무도 알 수 없다. **문서 중심 저장소일수록 이 테스트의 CI 가치가 크다.**

FINAL_REVIEW가 "CI 성공이라 부르지 않는다"고 정직하게 적은 것은 좋지만, 그것은 문제의 인식이지 해결이 아니다.

**권고 (최우선, 10분 작업):**

```yaml
# .github/workflows/checks.yml
name: checks
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: python -m pip install -r requirements-design.txt
      - run: python -m unittest discover -s tests -v
      - run: python tools/validate_design.py
      - run: python tools/validate_v02.py
      - run: python tools/check_frontier_protocol.py
```

배지를 README에 달면 "71개 통과"라는 주장이 자기 검증적이 된다. 이 저장소의 철학에 가장 잘 맞는 단일 개선이다.

---

### 🔴 H2 — 의존성 없는 clone에서 71개 중 26개가 에러로 터진다

**재현 (실측):**

```
# jsonschema 미설치 상태
python -m unittest discover -s tests
→ Ran 71 tests ... FAILED (errors=26)
→ ModuleNotFoundError: No module named 'jsonschema'
```

**원인:** `tools/validate_v02.py:36`에서 `jsonschema`를 **함수 내부에서 lazy import**하며 `ImportError`를 처리하지 않는다.

```python
def shape_errors(value: Any, kind: str) -> list[str]:
    from jsonschema import Draft202012Validator   # ← 여기서 ModuleNotFoundError
```

대조적으로 `tools/validate_design.py:17-20`은 모듈 상단에서 잡아 친절한 메시지를 낸다:

```python
try:
    from jsonschema import Draft202012Validator, ValidationError
except ImportError as exc:
    raise SystemExit("jsonschema가 필요합니다. 검사에 사용한 버전은 4.26.0입니다.") from exc
```

**같은 저장소 안에 좋은 패턴과 나쁜 패턴이 공존한다.**

**영향:** README는 `pip install -r requirements-design.txt`를 먼저 안내하므로 절차를 따르면 문제가 없다. 그러나 v0.4 README가 "새 검사는 Python 표준 라이브러리만 사용합니다"라고 강조하기 때문에, 신규 사용자가 `python -m unittest discover -s tests -v`를 그냥 실행할 유인이 크다. 그 결과는 26개의 traceback이며, 이는 "이 저장소는 깨져 있다"는 잘못된 첫인상을 준다.

**권고:** `tests/test_v02.py`에 skip 가드를 추가한다.

```python
import unittest
try:
    import jsonschema  # noqa: F401
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

@unittest.skipUnless(HAS_JSONSCHEMA, "requires jsonschema (pip install -r requirements-design.txt)")
class DesignContracts(unittest.TestCase):
    ...
```

이렇게 하면 의존성 없는 환경에서 `45 tests OK, 26 skipped`가 되어 **상태가 정직하게 표현된다** — 이 저장소의 철학과 정확히 일치하는 처리다.

---

### 🟡 M1 — 두 근거 원장의 필드 스키마가 서로 호환되지 않는다

**실측 감사 결과:**

| | v0.3 (E01–E31) | v0.4 (F01–F24) |
|---|---|---|
| 한계 기록 | `limitations` | **`limits`** |
| 검토 범위 | `verification` | **`inspection`** |
| 확인 시각 | 항목별 `checked_on` | 원장 최상위 `checked_at`만 |
| 재확인 조건 | `recheck` | **없음** |
| 필드 완전성 | **31개 전부 13필드 완비** | 9필드 공통, 6필드 선택적 |
| `published` 결측 | 0 | **8 / 24** |
| `revision_date` 결측 | — | 22 / 24 |

같은 개념에 다른 이름을 썼다. `limitations` ↔ `limits`, `verification` ↔ `inspection`. 두 원장을 함께 읽는 도구(향후 resolver, HANDOFF 생성기, 또는 `test_research_integrity`의 확장)는 반드시 버전 분기를 해야 한다.

더 실질적인 문제는 **v0.3 원장이 더 엄격했다는 점**이다. v0.3은 31개 전부가 13개 필드를 완비하고 `recheck`(재확인 조건)까지 갖췄는데, v0.4에서 `recheck`가 사라지고 `published`가 8건 비었다. 저장소가 "제품 정책은 구현 시점에 다시 확인한다"(EVIDENCE_FOLLOWUP §4)고 반복 강조하는데, **그 재확인 조건을 기계가 읽을 수 있는 필드로 갖고 있던 것이 v0.3이고 v0.4는 잃었다.**

**권고:**
1. `contracts/sources.schema.json`을 추가한다. 이 저장소는 이미 `contracts/`에 JSON Schema 문화가 있으므로 자연스럽다.
2. v0.4 원장에 `recheck`를 복원하고 `published` 8건을 채우거나, 명시적으로 `"published": null` + 사유를 기록한다(저장소의 "모르는 것은 null/unknown" 원칙에 부합).
3. 필드명을 한쪽으로 통일하거나, 최소한 `docs/architecture/README.md`에 매핑 표를 남긴다.

---

### 🟡 M2 — 원장 정합성 테스트가 원장의 인식론적 가치를 검사하지 않는다

`test_registry_ids_and_decisions`가 검사하는 것은 전부 4가지다:

```python
self.assertEqual(len(sources), len(numbers))            # 개수
self.assertEqual({s["id"] for s in sources}, {...})     # ID 집합
self.assertTrue(set(source["decisions"]) <= allowed)    # 결정 ID 유효성
self.assertTrue(source["url"].startswith("https://"))   # URL 접두사
```

**검사하지 않는 것:** `limits`, `inspection`, `locator`, `claim`, `kind`, `published`의 존재·비어있지 않음.

즉 **이 원장을 가치 있게 만드는 바로 그 필드들이 무방비다.** `limits`가 빈 문자열인 출처, `locator`가 없는 논문 인용, `kind`가 누락된 항목이 전부 테스트를 통과한다. 실제로 `published` 결측 8건이 현재 통과하고 있다(M1).

이것은 저장소의 자기 규율에서 가장 아쉬운 지점이다 — "원문 URL·버전·locator·확인일·한계·관련 결정"을 기록하겠다고 README가 약속하는데, 그 약속을 강제하는 테스트가 없다.

**권고 (매우 저렴, 큰 효과):**

```python
REQUIRED = ("title", "url", "kind", "inspection", "locator", "claim", "limits")

for source in sources:
    for field in REQUIRED:
        with self.subTest(id=source["id"], field=field):
            self.assertTrue(str(source.get(field, "")).strip(),
                            f"{source['id']}: empty {field}")
```

M1의 스키마 통일과 함께 하면 10줄 미만으로 원장 품질이 구조적으로 보장된다.

---

### 🟡 M3 — 테스트가 CWD에 결합되어 있고 패키징 메타데이터가 없다

**재현 (실측):**

```
# 저장소 루트에서
python -m unittest discover -s tests          → Ran 71 tests, OK

# 한 단계 위 디렉터리에서
python -m unittest discover -s decision-model_lab-main/tests
→ ModuleNotFoundError: No module named 'tools'
```

`tests/*.py`가 `from tools.check_frontier_protocol import ...`를 하는데, `tools/`에 `__init__.py`가 없어 PEP 420 네임스페이스 패키지로 해석되고, 이는 **저장소 루트가 `sys.path[0]`일 때만** 작동한다. `python -m unittest`가 CWD를 `sys.path`에 넣어주는 덕분에 우연히 동작하는 구조다.

`pyproject.toml`, `setup.cfg`, `conftest.py`, `tox.ini` 중 무엇도 없다. pytest로 실행하면(많은 사용자의 기본 습관) 역시 실패한다.

**완화 요인:** README와 v0.4 README가 "저장소 루트에서 실행한다"를 명시한다. 그래서 H가 아니라 M이다.

**권고:** 최소한의 `pyproject.toml` 추가로 CWD 의존과 pytest 비호환을 동시에 해결한다.

```toml
[project]
name = "decision-model-lab"
version = "0.4.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
pythonpath = ["."]
```

---

### 🟡 M4 — F22–F24 추가 후 갱신되지 않은 현행 안내 문서

`EVIDENCE_FOLLOWUP.md`가 F22–F24를 추가하면서 `test_research_integrity.py`의 `range(1, 25)`는 갱신했지만, 문서 일부가 따라가지 못했다.

| 위치 | 현재 | 실제 |
|---|---|---|
| `docs/architecture/README.md:12` | "F01–F21" | **F01–F24** |
| `v0.4/FINAL_REVIEW.md:45` | "E01–E31/F01–F21" | E01–E31/F01–F24 |
| `v0.4/FINAL_REVIEW.md:51` | "전체 원장 52개 기록" | **55개** (31+24) |
| `v0.4/VALIDATION.md:51,60` | "F01–F21", "21개 기록" | (§9가 1–4절을 역사적 기록으로 선언 → **문제 없음**) |

**FINAL_REVIEW는 날짜가 박힌 PR #1 검토 스냅샷**이므로 그 시점의 숫자를 유지하는 것이 오히려 정확하다는 해석이 가능하다. VALIDATION도 §9에서 명시적으로 면책된다.

**그러나 `docs/architecture/README.md:12`는 다르다.** 이 줄은 "## 현재 읽을 문서" 섹션 안에 있는 **현행 안내**이며, 역사적 기록이라는 라벨이 없다. 명백한 스테일이다.

**아이러니:** 이 저장소는 "F01–F24는 24개의 독립 실험이 아니다" 같은 숫자 해석 오류를 막는 데 엄청난 주의를 기울이는데, 정작 숫자 자체의 동기화가 어긋났다. 그리고 이것은 **자동으로 잡을 수 있는 유형의 결함**이다.

**권고:**
1. 즉시 `docs/architecture/README.md:12`를 "F01–F24"로 수정.
2. 구조적 해결 — 현행 안내 문서에 원장 범위를 하드코딩하지 않거나, `test_research_integrity`에 회귀 검사를 추가한다:

```python
def test_current_guidance_states_actual_registry_range(self):
    text = (ROOT / "docs/architecture/README.md").read_text(encoding="utf-8")
    self.assertIn("F01–F24", text)   # 원장 크기에서 생성하면 더 좋음
```

---

### 🟡 M5 — 코드 hash 대조 경로가 저장소 안에 없다

`v0.4/VALIDATION.md:34-38`은 blob hash 표를 기록한다:

| 파일 | 기록된 byte | 기록된 blob SHA |
|---|---:|---|
| `tools/check_frontier_protocol.py` | 9,970 | `ac5ea12a9b0b...` |
| `tests/test_frontier_protocol.py` | 4,825 | `51126c641e44...` |

**직접 계산한 현재 값:**

| 파일 | 현재 byte | 현재 blob SHA |
|---|---:|---|
| `tools/check_frontier_protocol.py` | **10,898** | `b768305c42c8...` |
| `tests/test_frontier_protocol.py` | **9,318** | `8c940eca54dd...` |

불일치는 예상된 것이다 — FINAL_REVIEW 이후 코드가 수정되었고, VALIDATION `:9`가 §1–4를 "역사적 기록"으로 선언한다. **거짓 주장이 아니다.**

문제는 다른 데 있다. 이 저장소는 "검사한 코드와 게시한 코드의 동일성"을 검증 항목으로 삼을 만큼 중요하게 여기는데, **현재 코드에 대해 그 검증을 재현할 경로가 저장소 안에 없다.** 다음 세션의 에이전트는 문서의 hash가 낡았다는 것만 알 뿐, 새 hash를 얻으려면 절차를 처음부터 재발명해야 한다.

**권고:** hash를 문서에 박는 대신 생성 도구를 둔다.

```python
# tools/print_code_hashes.py — 표준 라이브러리만
import hashlib, pathlib
for rel in ("tools/check_frontier_protocol.py", "tests/test_frontier_protocol.py"):
    data = pathlib.Path(rel).read_bytes()
    blob = b"blob %d\0" % len(data) + data
    print(f"{rel}  bytes={len(data)}  blob={hashlib.sha1(blob).hexdigest()}")
```

H1의 CI에서 이것을 출력하면 모든 실행이 현재 hash를 기록으로 남긴다.

---

### 🟡 M6 — LICENSE와 `.gitignore`가 없다

**LICENSE 없음:** 공개 저장소이지만 라이선스가 없으면 법적으로 **모든 권리 유보**다. 타인이 인용·포크·재사용할 수 없다. 이 저장소가 연구 자료로 참조되기를 의도한다면(README의 기록 원칙, 근거 원장 구조가 그것을 시사한다) 실질적 차단 요인이다.

문서(CC BY 4.0 등)와 코드(MIT/Apache-2.0)를 나누는 것도 가능하다.

**`.gitignore` 없음:** `__pycache__/`, `.venv/`, `*.pyc`가 실수로 커밋될 위험이 상시 존재한다. 현재 main에는 없지만 보호 장치가 없다. 3줄이면 해결된다.

**description / topics 없음:** GitHub 검색으로 발견될 가능성이 0에 가깝다. `llm-orchestration`, `multi-agent`, `evidence-based`, `research` 정도면 충분하다.

---

### 🟢 L1 — `required_participants`는 정족수가 아니라 정확 일치다

```python
require(type(required) is int and required >= 2, "invalid quorum")
require(len(participants) == required, "configured quorum mismatch")
require(len(drafts) == required, "missing draft quorum")
```

`required_participants`가 참여자 수와 **정확히 같아야** 한다. 즉 "3명 구성, 최소 2명이면 진행"을 표현할 수 없다.

그런데 설계 문서 `02-frontier-architecture.md:127`은 "**불충분한 정족수**에서는 추가 모델 호출을 막고 상태를 명시한다"고 쓴다 — 부분 정족수 개념을 전제한다. **설계 어휘와 checker 어휘가 어긋난다.**

에러 메시지가 `"configured quorum mismatch"`로 "configured"를 붙여 구별하려 한 흔적이 있고, VALIDATION §5가 "부분 결과/축소 승인"을 다음 구현 범위로 명시하므로 **의도된 한계**다. 다만 필드명이 `required_participants`인 한 다음 구현자가 오해할 여지가 있다.

**권고:** 필드명을 `configured_participants`로 바꾸거나, docstring에 "이 필드는 최소 정족수가 아니라 선언 구성 인원이며, 축소 승인은 미구현"을 한 줄 추가.

---

### 🟢 L2 — provider 구별이 단순 문자열 비교

```python
require(len({p["provider"].lower() for p in participants.values()}) == required,
        "distinct providers required")
```

`openai` vs `azure-openai`, `anthropic` vs `bedrock-anthropic`는 다른 문자열이므로 "서로 다른 회사"로 통과한다. 유니코드 동형이의어(그리스 문자 Ο vs 라틴 O)도 마찬가지다.

**저장소가 이 한계를 정확히 인지하고 있다** — `02-frontier-architecture.md:72`: "같은 backend를 여러 alias로 등록한 것을 여러 회사로 집계하지 않는다", VALIDATION §5: "participant의 provider/quality는 모두 입력 기록의 선언이다. 이를 실제 계정·모델·파일과 대조하지 않는다."

**권고 (선택):** `.lower()` → `unicodedata.normalize("NFKC", s).casefold()`로 한 줄 강화. 근본 해결은 아니지만 동형이의어 벡터는 닫힌다.

---

### 🟢 L3 — ID 네임스페이스가 리스트별로 분리

`indexed()`는 리스트 내부 중복만 막는다. claim `c1`과 check `c1`이 공존할 수 있다. 현재 검증 로직에서는 `check_refs`가 checks를, `target`이 claims를 가리키므로 모호성이 생기지 않는다. 로그·디버깅 혼동 가능성만 있다. 정보용.

---

### 🟢 L4 — `shape_errors`가 호출마다 스키마를 재파싱

`validate_v02.py:42`가 매 호출마다 `pilot.schema.json`을 다시 읽고 `check_schema`를 다시 돌린다. `validate_proof` 한 번에 3회 발생. 현재 규모에서 무해하지만 `functools.lru_cache` 한 줄이면 제거된다.

---

### 🟢 L5 — D16의 근거가 1건뿐

D16(단일 controller + durable artifact/journal, 명시 session 재개)이 F14 하나에만 연결된다. D10–D18 중 유일한 단일 출처 결정이다(D17은 13건).

D16은 아키텍처의 **구조적 중심**(§3의 "제어권은 하나로")을 규정하는 결정이므로 근거 밀도가 가장 낮은 것이 어색하다. ADR 표는 "기존 D03/D06"도 참조하지만 원장 역인덱스에는 F14만 잡힌다.

**권고:** 정보용. 실제로는 v0.3의 D03/D06 근거(E-계열)가 뒷받침하므로, 원장에서 E 근거를 D16에 교차 연결하거나 ADR 표에 근거 계보를 명시하면 해소된다.

---

## 7. 외부 근거 대조 검색

저장소의 핵심 주장 3가지를 독립 검색으로 확인했다. **검색 결과 수준의 확인이며 원문 전수 검증이 아니다.**

### 7.1 Perplexity Model Council (F02) — 주장 타당, 해석도 정확

검색으로 확인: Model Council은 2026-02-05 출시된 실존 기능이며, 같은 질문을 여러 frontier 모델에 병렬로 보내고 **별도 모델이 합의·불일치·고유 발견을 합성**한다. 기본 구성은 GPT-5.6 Sol Thinking / Claude Opus 5 Thinking / Gemini 3.1 Pro Thinking. 웹·iOS는 3개, Computer에서는 2–8개. Max($200/월) 및 Enterprise Max 전용.

**저장소의 인용이 정확하다.** F02의 "세 회사 frontier 구성과 독립 조사·소수 발견 보존" 설명이 실제 제품 동작과 일치한다.

**더 중요한 것 — 저장소가 이미 올바르게 구분한 지점:** HANDOFF §6이 "독립 상급 모델 협업이 실제 제품에 존재하지만 **사용자의 세 구독을 재사용하는 bridge는 아니다**"라고 명시한다. 이것이 결정적이다. Perplexity는 자사 API 예산으로 모델을 호출하는 반면, 이 저장소는 사용자의 개별 구독 3개를 재사용하려 한다. **funding 구조가 근본적으로 다르며, 따라서 Model Council의 존재는 이 저장소 접근의 실현 가능성 근거가 아니다.** 저장소가 이 구별을 스스로 해낸 것은 근거 해석 규율이 실제로 작동한다는 증거다.

### 7.2 Multi-agent debate 문헌 — 저장소의 신중함이 정당

검색 결과가 양방향이었다:

**긍정 방향:** 어려운 문제나 소·중형 모델에서 MAD가 단독 대비 일관되게 개선. 한 연구는 21개 설정 중 19개에서 개선, 평균 +7.05%.

**부정 방향:** 쉬운 과제에서는 self-consistency나 parallel sampling이 MAD를 따라잡거나 능가. **이미 강한 단독 모델(Gemma2-9B, 80.0%)은 debate로 오히려 성능이 떨어졌다.** 그리고 "다중 에이전트 협업이 강한 단독 baseline을 이기는 실제 조건은 아직 잘 특성화되지 않았다"는 평가가 2026년 현재도 유효하다.

또한 debate 성공의 지배적 요인은 **내재적 추론 능력과 그룹 다양성**이며, 토론 순서나 confidence 노출 같은 구조적 파라미터의 기여는 미미하다는 결과가 있다.

**평가:** 저장소의 입장(D13 기본 0/1 라운드, Q1 compute-matched 대조군 필수, "debate 우월성을 무조건 지지하지 않는다")은 **문헌의 보수적 해석과 정확히 정합한다.** 특히 "이미 강한 단독 모델은 악화될 수 있다"는 발견은 저장소의 Q0(현재 사용자의 상급 native 단독) 기준선 설정을 강하게 정당화한다 — 사용자가 이미 frontier 모델을 단독으로 쓰고 있다면, 그것이 이기기 어려운 baseline일 수 있다.

**추가 제안:** "그룹 다양성이 지배적 요인"이라는 결과는 저장소의 `02-frontier-architecture.md:72`("vendor 다양성, 모델/학습 계열 다양성, 풀이 방법 다양성, 검색 출처 다양성은 별개로 기록한다")를 지지한다. 이 네 가지 다양성 축을 **측정 가능한 지표로 승격**할 근거가 된다 — 현재는 기록 항목일 뿐이다.

### 7.3 유사 프로젝트 지형 — 차별점과 중복 위험이 동시에 확인됨

검색으로 확인된 인접 프로젝트: **Every Code**(Codex CLI 포크, 멀티 프로바이더 오케스트레이션), **Claude Code Bridge(CCB)**(모델별 persistent daemon, 컨텍스트 오버헤드를 5,000–20,000 → 50–200 토큰으로 축소 주장), **claude-codex-gemini**(Gemini 오케스트레이터 / Claude 구현 / Codex 리뷰어), **Warp**(Rust 터미널, 다중 에이전트 동시 실행), **awesome-cli-coding-agents**(큐레이션 목록).

**차별점 (강함):** 이들은 거의 전부 **배선(wiring)**에 집중한다 — 어떻게 여러 CLI를 동시에 띄우고 결과를 모을 것인가. **근거 원장, 반례 보존, 투표≠검증, 회계 경계, 대조군 설계**를 다루는 프로젝트는 검색 범위에서 발견되지 않았다. decision-model_lab의 고유 기여는 정확히 그 지점에 있다.

**중복 위험 (실질적):** 반대로 **배선은 이미 여러 곳에서 해결되어 있다.** V04-01(inventory)과 V04-03(두 native 경로 read-only pilot)은 CCB나 claude-codex-gemini가 이미 한 일과 상당 부분 겹친다. 이 저장소의 희소 자원은 시간이므로, 배선을 처음부터 만들기 전에 **기존 구현을 adapter 계층으로 흡수할 수 있는지** 먼저 평가할 가치가 있다. 저장소의 기여는 배선 위에 얹는 **claim/evidence 계층**이지 배선 자체가 아니다.

**저장소가 다루지 않은 리스크 — 구독 인증 경로의 정책 소멸:** 검색 결과 중 "Google이 2026-06-18자로 Gemini CLI 소비자 인증을 종료했고, CLI는 Gemini Code Assist Standard/Enterprise 및 유료 API를 통해서만 이용 가능"이라는 서술이 있었다. **이것은 검색 결과 수준의 정보이며 원문 미확인이다 — 저장소의 기록 원칙대로 검증 전에는 사실로 취급하면 안 된다.**

다만 만약 사실이라면, 이는 이 저장소의 **가장 근본적인 전제("구독 우선, API 선택")에 대한 실증적 반례**다. 공급자는 구독 기반 프로그래매틱 접근을 언제든 닫을 수 있고, 실제로 닫은 사례가 있다는 뜻이 된다. 저장소는 `agy`와 Gemini CLI를 다른 도구로 정확히 구분하고 있으므로 이 사례가 직접 적용되지는 않지만, **"구독 인증 경로의 정책적 소멸"이라는 리스크 범주 자체가 현재 문서에 없다.**

**권고:** V04-01 inventory의 완료 조건에 다음을 추가한다 — 각 provider의 구독 기반 비대화형 접근에 대한 **정책 변경 이력과 공식 지원 보장 범위**를 기록하고, 경로가 닫혔을 때의 대체 계획(또는 명시적 포기)을 결정으로 남긴다. 이것은 새 ADR(D19) 감이다.

---

## 8. 종합 평가

### 잘 된 것

| | |
|---|---|
| **설계 품질** | ★★★★★ 인식론적 규율이 코드로 강제됨. 이 분야에서 드문 수준 |
| **근거 관리** | ★★★★☆ 55개 원장 + 양방향 ADR 연결 + `kind` 분류. 스키마 통일만 남음 |
| **평가 설계** | ★★★★★ Q0–Q6 대조군이 문헌 평균보다 엄격 |
| **코드 견고성** | ★★★★☆ 입력 경계 방어가 이례적으로 탄탄 |
| **범위 정직성** | ★★★★★ 성공 출력에 미검증 범위가 붙음. 모범적 |
| **인계 가능성** | ★★★★☆ HANDOFF/VALIDATION/FINAL_REVIEW 3층 구조가 실용적 |

### 남은 것

| | |
|---|---|
| **저장소 위생** | ★★☆☆☆ CI·LICENSE·`.gitignore`·`pyproject.toml` 전무 |
| **자기 검증** | ★★☆☆☆ 71개 테스트의 상태가 사람 기억에 의존 |
| **원장 스키마** | ★★★☆☆ v0.3→v0.4 드리프트, 핵심 필드 미검사 |
| **실제 구현** | ☆☆☆☆☆ 의도된 상태. 결함 아님 |

### 우선순위 권고

| 순위 | 작업 | 비용 | 근거 |
|---|---|---|---|
| **1** | GitHub Actions 워크플로 추가 | 10분 | H1. 저장소 철학과 가장 정합하는 단일 개선 |
| **2** | `test_v02.py`에 jsonschema skip 가드 | 10분 | H2. 첫인상 26개 traceback 제거 |
| **3** | `docs/architecture/README.md:12` F01–F21 → F01–F24 | 1분 | M4. 현행 안내의 명백한 스테일 |
| **4** | 원장 필수 필드 non-empty 테스트 | 20분 | M2. 10줄로 원장 품질 구조 보장 |
| **5** | LICENSE 추가 | 5분 | M6. 인용·재사용의 법적 차단 해소 |
| **6** | `contracts/sources.schema.json` + v0.4 `recheck` 복원 | 1–2시간 | M1. v0.3이 가졌던 엄격성 회복 |
| **7** | `pyproject.toml` (pythonpath) | 10분 | M3. pytest 호환 + CWD 결합 해소 |
| **8** | `tools/print_code_hashes.py` | 15분 | M5. hash 대조 재현 경로 |
| **9** | V04-01에 "구독 인증 경로 정책 리스크" 항목 추가 | 30분 | §7.3. 전제 자체의 최대 리스크 |
| **10** | 기존 orchestration 프로젝트의 adapter 흡수 가능성 평가 | 조사 | §7.3. 배선 재발명 회피 |

1–5번은 합쳐서 **1시간 미만**이며 저장소의 신뢰도를 구조적으로 끌어올린다.

### 마지막 판단

26시간 만에 340KB의 문서와 55개 근거 원장, 71개 테스트를 만들어낸 작업이다. 그 속도에서 나온 결함(M4의 스테일 참조, M1의 스키마 드리프트)은 있지만 **모두 사소하고 기계적으로 수정 가능하다.**

정작 어려운 부분 — "무엇을 검증했고 무엇을 검증하지 않았는가를 매 문장에서 구별하는 규율" — 은 이미 확보되어 있고, 그것을 테스트로 고정하는 데까지 성공했다. **이 저장소의 가치는 아직 만들지 않은 오케스트레이터가 아니라, 오케스트레이터를 만들 때 스스로를 속이지 않게 하는 장치에 있다.**

다음 단계(V04-01/V04-03)에서 실제 CLI를 연결하기 시작하면 "검증했다"는 유혹이 급격히 커진다. 그때 §3.3의 불변식들과 CI(H1)가 실제로 값을 한다. **CI를 먼저 켜고 나서 실제 연결로 넘어가기를 권한다.**

---

## 부록 A. 검증 명령 재현

```bash
# 저장소 루트에서
python -m pip install -r requirements-design.txt

python tools/check_frontier_protocol.py       # → PASS (stdlib only)
python tools/validate_design.py               # → 25/25 offline checks passed
python tools/validate_v02.py                  # → PASS
python -m unittest discover -s tests -v       # → Ran 71 tests, OK
```

검증 환경: Windows 11, Python 3.12.6, jsonschema 4.26.0, 격리 venv.

## 부록 B. 출처

- [Introducing Model Council — Perplexity](https://www.perplexity.ai/hub/blog/introducing-model-council)
- [Perplexity Model Council 2026 Guide](https://aifirstfounders.com/blog/perplexity-model-council-guide-2026.html)
- [Multi-Agent Debate: Framework & Applications](https://www.emergentmind.com/topics/multi-agent-debate-approach)
- [Multi-Agent Debate for LLM Judges with Adaptive Stability Detection](https://arxiv.org/html/2510.12697v1)
- [Single-Agent vs Multi-Agent Systems: When Coordination Helps, Hurts, and Pays Off](https://medium.com/@mjgmario/single-agent-vs-multi-agent-systems-when-coordination-helps-hurts-and-pays-off-57735ee7916d)
- [awesome-cli-coding-agents](https://github.com/bradagi/awesome-cli-coding-agents)
- [Open-Source Multi-Agent CLI Orchestration](https://agentmarketcap-1.onbex.co/blog/2026/04/06/open-source-multi-agent-cli-orchestration-parallel-code-claude-bridge-moonmind)
- [claude-codex-gemini](https://github.com/Z-M-Huang/claude-codex-gemini)
- [The 2026 Guide to Coding CLI Tools](https://www.tembo.io/blog/coding-cli-tools-comparison)
