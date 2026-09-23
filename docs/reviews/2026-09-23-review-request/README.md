# 리뷰 요청 — 2026-09-23 정렬 작업과 V04-01(aux-pc)

다른 AI 세션에게 이 저장소의 2026-09-23 작업을 검토받기 위한 요청서다. 요청한 쪽: claude 세션(Claude Opus 5.5, 사용자 보조 PC의 로컬 checkout). 리뷰어는 **GitHub만 볼 수 있다고 가정한다.**

## 사용자가 리뷰어에게 붙여 넣을 요청문

> 저장소 https://github.com/inlight37-design/decision-model_lab 의 `main` 브랜치에서 `docs/reviews/2026-09-23-review-request/README.md`를 읽고 그대로 따라 검토해 줘. 결과는 그 문서의 "결과를 남기는 방법"대로 남겨 줘. GitHub에 쓸 수 없으면 결과 전문을 답으로 줘.

## 검토 범위

- 커밋 범위: `c109840890bd72cbe5135f14c4d90c54c9039f0f`(2026-09-23 작업 시작 전 main) → 현재 `main`. GitHub의 compare 화면이나 `git log c109840..main`으로 본다.
- 여기에는 다른 AI 세션이 만든 [PR #3](https://github.com/inlight37-design/decision-model_lab/pull/3)(MCP·UI 검토)이 포함돼 있다. PR #3 자체는 이미 한 번 검토 기록이 있으니 **그 뒤의 작업**에 집중한다.
- 사용자 PC의 상태(설치된 CLI, 로그인, 설정 파일)는 리뷰어가 볼 수 없다. 그 부분은 저장소에 옮겨 둔 기록으로만 판단하고, **기록과 다르다고 단정하지 않는다** — 의심되면 "확인 필요"로 적는다.

## 읽는 순서

결론에 끌려가지 않도록 **원 출력과 도구를 먼저, 우리의 판정을 나중에** 읽는다.

1. [`AGENTS.md`](../../../AGENTS.md), [`docs/COLLABORATION.md`](../../COLLABORATION.md) — 이 저장소에서 여러 AI가 지키는 규칙. 리뷰 결과를 남길 때도 따른다.
2. [`NEXT-SESSION.md`](../../../NEXT-SESSION.md)의 **2절(사용자가 확정한 것)만** — 논쟁하지 않는 전제다.
3. 원 출력: [`hosts/aux-pc/tier2/`](../../experiments/v04-01-inventory/hosts/aux-pc/tier2/)의 각 `.txt`(첫머리에 실행 명령이 있다)와 [`help/`](../../experiments/v04-01-inventory/hosts/aux-pc/help/). **여기서 스스로 판단을 적어 둔다.**
4. 도구: [`tools/runtime_inventory.py`](../../../tools/runtime_inventory.py)와 [테스트](../../../tests/test_runtime_inventory.py), [`tools/v04-01/`](../../../tools/v04-01/README.md), [`tests/test_research_integrity.py`](../../../tests/test_research_integrity.py)의 새 검사, [`tools/check_encoding.py`](../../../tools/check_encoding.py).
5. 절차서: [`docs/experiments/v04-01-inventory/README.md`](../../experiments/v04-01-inventory/README.md).
6. 우리의 판정: [aux-pc `RESULTS.md`](../../experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md), [`manifest.tier2.json`](../../experiments/v04-01-inventory/hosts/aux-pc/manifest.tier2.json). 3에서 적은 판단과 비교한다.
7. 설계 반영: [v0.4 원장](../../architecture/v0.4/sources.json)의 F30·F31, [`02-frontier-architecture.md`](../../architecture/v0.4/02-frontier-architecture.md)의 D15·D18 행, 나머지 `NEXT-SESSION.md`.

## 검토 질문 — 중요한 순서

각 질문에 "동의 / 부분 동의 / 반대"와 근거를 적는다. 근거가 없으면 "판단 보류"라고 쓴다.

1. **관측과 판정이 맞물리는가.** tier 2 원 출력만 보고 내린 판단이 RESULTS의 판정(V04-03은 Claude Code·Codex로 진행 가능, Antigravity는 조건부)과 같은가. `manifest.tier2.json`에서 `observed`·`configured=true`로 적은 것 중 원 출력이 뒷받침하지 않는 것이 있는가.
2. **Claude의 깨끗한 문맥 조합(P4b)이 blind 초안 조건을 충분히 만족하는가.** `--restricted --strict-mcp-config --disable-slash-commands --tools ""` 뒤에도 남는 것(내장 플러그인 2개, 기본 에이전트 목록, 시스템 프롬프트)이 초안을 오염시킬 수 있는가. `--restricted`는 help에서만 확인했다 — 공식 문서 locator가 있으면 알려 준다.
3. **Antigravity 약관 6조(F31)의 해석.** 우리 앱이 공식 `agy`를 하위 프로세스로 실행하고 로그인·토큰은 건드리지 않는 방식이 "제3자 소프트웨어로 서비스에 접근"에 해당하는가. 1차 출처(약관, Google의 공식 안내, 공식 저장소 이슈의 Google 측 답변)로만 답한다. 커뮤니티 글은 단서로만 쓴다.
4. **Antigravity가 잘못된 옵션 값을 조용히 무시한 관측(P3)의 범위.** 다른 값 옵션(`--model`, `--effort`)에도 같을 가능성과, adapter가 막아야 할 방법에 대한 의견. 특히 없는 `--model` 값이 기본 Flash 모델로 바뀌는 경로.
5. **`tools/runtime_inventory.py` 코드 리뷰.** 비밀·개인 경로 가림의 누락, `--fresh-env`의 정확성(무엇을 지우고 무엇을 남기는가), 검사기가 막지 못하는 잘못된 manifest, 테스트의 빈틈.
6. **협업 규칙과 CI 가드.** 살아 있는 문서의 개수 금지 정규식(`RESTATED_COUNT`)의 오탐·미탐, 인계 문서 절 구성 검사, 제어 문자 검사. 과하거나 빠진 규칙.
7. **다음 단계의 위험.** 사용자 원칙 "모델은 붙였다 뗐다 하고, 한도를 다 쓰면 그 provider만 뺀다"(2절 13번)가 정족수·blind·예산 규칙(D11·D13·D18)과 충돌하는 지점. V04-03 계획에서 빠진 위험.
8. **exec 우선 결정(Q1)의 반례.** ACP를 먼저 붙였어야 할 이유가 관측으로 있는가.

질문 밖이라도 **틀린 사실, 깨진 링크, 원 출력과 다른 기록**을 찾으면 적는다.

## 결과를 남기는 방법

- 새 브랜치 `chatgpt/review-v04-01-<YYYYMMDD>`(리뷰어가 ChatGPT가 아니면 그 이름)를 만들고, `docs/reviews/<YYYY-MM-DD>-v04-01-review/README.md`에 리뷰를 쓴 뒤 PR을 연다. [PR 템플릿](../../../.github/pull_request_template.md)을 채운다. 접근 범위에는 "GitHub만"이라고 적는다.
- 리뷰 문서의 형식:

| 절 | 내용 |
|---|---|
| 요약 | 가장 중요한 발견 세 개 이내 |
| 발견 | 번호, 심각도(높음·중간·낮음), 위치(`파일:줄` 또는 URL), 근거 등급(**관측**: 원 출력·코드에서 직접 확인 / **문서**: 공식 문서 / **추론**), 내용, 제안 |
| 질문별 답 | 위 1–8에 대한 동의·부분 동의·반대·보류와 근거 |
| 확인하지 못한 것 | 접근할 수 없었거나 읽지 않은 것 |

- **명백한 오류**(오타, 깨진 링크, 원 출력과 다른 숫자)는 같은 PR에서 원본을 고쳐도 된다. 커밋 메시지에 무엇이 왜 틀렸는지 적는다. **판단이 갈리는 것은 고치지 말고 리뷰에만 적는다** — 사용자와 다음 세션이 판단한다.
- 근거 원장(`sources.json`)에 항목을 추가하는 것은 1차 출처를 직접 읽은 경우만이다. 리뷰 안의 참조 번호는 원장 번호가 아니다.
- 살아 있는 문서에 검사 수·원장 건수를 적지 않는다(CI가 막는다). `NEXT-SESSION.md`는 절 구성을 유지한 채 3절에 리뷰 브랜치를 적는다.
- 병합은 하지 않는다. 사용자 또는 claude 세션이 CI를 확인한 뒤 병합한다.

## 이미 알고 있는 한계

리뷰어가 같은 지적을 반복하지 않도록 적어 둔다. 다르게 판단하면 그 근거를 적는다.

- 모든 관측은 **보조 PC 한 대, 2026-09-23 하루**의 결과다. 운용 PC와 다른 버전에서는 다를 수 있다.
- tier 2의 호출은 "OK" 한 단어짜리였다. 품질·긴 작업·취소(P6)·한도 조회(P7)는 보지 않았다.
- Antigravity의 데이터 사용 끄기(`enableTelemetry=false`)는 로컬 설정 파일로 했고, 계정 쪽 반영은 화면에서만 확인할 수 있다.
- 공식 문서는 WebFetch 요약으로 먼저 읽고, 판단에 쓴 문장은 원문으로 다시 확인했다. 그래도 요약 단계의 오독이 한 번 있었다(크레딧 기본값 — RESULTS 정책 표에 정정 기록).
