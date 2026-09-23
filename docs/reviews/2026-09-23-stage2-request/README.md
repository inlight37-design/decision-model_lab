# 리뷰 요청 — 2단계 모델 호출과 그 과정의 실패·시행착오 (2026-09-23)

다른 AI 세션에게 검토를 받기 위한 요청서다. 요청한 쪽은 claude 세션(Claude Opus 5.5)이다. 작업은 사용자 보조 PC(`aux-pc`)의 로컬 checkout과 그 안의 WSL2 배포판(`aux-pc-wsl`)에서 했다. 리뷰어는 **GitHub만 볼 수 있다고 가정한다.**

이번 요청의 중심은 세 가지다.
- 2단계의 실제 호출 다섯 번으로 **기록에 적은 판정이 증거로 뒷받침되는가.** 특히 모델의 보고에 기댄 칸과 모델 없는 진단에 기댄 칸.
- 그 과정의 **실패·실수·시행착오**(아래 "잘 안 된 것")가 빠짐없이 정직하게 적혔는가. 고친 방식은 맞는가.
- 관측 도구([`observe.py`](../../../tools/w2/observe.py))의 수정과 새 진단 도구([`codex_sandbox.py`](../../../tools/w2/codex_sandbox.py))가 맞는가.

## 사용자가 리뷰어에게 붙여 넣을 요청문

> 저장소 https://github.com/inlight37-design/decision-model_lab 에서 `docs/reviews/2026-09-23-stage2-request/README.md`를 읽고 그대로 따라 검토해 줘. main에 없으면 브랜치 `claude/stage2-observe-20260923`에 있다. 결과는 그 문서의 "결과를 남기는 방법"대로 남겨 줘. GitHub에 쓸 수 없으면 결과 전문을 답으로 줘.

## 검토 범위

- **커밋:** main `f044865`(2단계 직전) → 브랜치 `claude/stage2-observe-20260923`. `git log f044865..origin/claude/stage2-observe-20260923`으로 본다. 이 브랜치는 main에 아직 병합되지 않았을 수 있다(아래 S16).
- **범위 안의 작업:**
  1. 승인된 호출 다섯 번과 그 기록: [2단계 기록](../../experiments/w2-isolation/stage2-aux-pc-wsl.md), [`manifest.v2.json`](../../experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.v2.json)
  2. 관측 도구 수정: 요약의 ID 가림, 잘린 목록의 수, 실제로 돌린 argv(`argv_run`), 경계 위반을 잡는 멈춤 규칙(`boundary_violations`)
  3. 모델 없는 K12 진단 도구
  4. 인계 [`NEXT-SESSION.md`](../../../NEXT-SESSION.md)의 1·3·4절(K 표)
  5. [PR #8](https://github.com/inlight37-design/decision-model_lab/pull/8)(ChatGPT의 tmux 조사)의 코드 주장 대조 — 인계 3절
- **리뷰어가 볼 수 없는 것:** 원 출력(WSL의 `~/.local/state/dml-observe/results/`)과 사용자 PC의 설정 폴더. 기록으로만 판단하고, 다르다고 단정하지 말고 "확인 필요"로 적는다.
- **모델 호출:** Claude 3회(`claude-sonnet-5`), Codex 2회(`gpt-6-luna`)로 사용자가 승인한 상한을 모두 썼다. 그 밖의 실행은 `--version`, `--help`, 로그인 상태, `codex sandbox`(모델 호출 아님)뿐이다.

## 한 일 (요약)

| 무엇 | 어디 | 근거 |
|---|---|---|
| 승인 기록과 호출 다섯 번(`b1`, `b2`, `p3-claude`, `p3-codex`, `b1-combo`). 모두 도구의 기대대로, 한도 메시지 없음 | WSL 상태 폴더(저장소 밖), 요약은 [2단계 기록](../../experiments/w2-isolation/stage2-aux-pc-wsl.md) | 원 출력(PC) |
| 기록의 세 칸: Claude 전송·문맥·권한 `observed`. Codex 전송·권한 `observed`, **문맥 `failed`** → Claude만 실행 허가 | [`manifest.v2.json`](../../experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.v2.json) | `runtime_inventory.py --validate`, [`test_core_eligibility.py`](../../../tests/test_core_eligibility.py) |
| 요약의 ID 가림(UUID, 24자 이상 16진수), 잘린 목록의 전체 수와 폴더별 수, `argv_run` | [`observe.py`](../../../tools/w2/observe.py) | [`test_w2_observe.py`](../../../tests/test_w2_observe.py) — 고치기 전 코드에서 실패 확인 |
| 멈춤 규칙: 금지 표식이 답·출력에 보이거나 작업 폴더에 파일이 생기면 기대와 다름 | 같은 파일 | 같은 시험 — 고치기 전 코드에서 실패 확인 |
| K12 진단: Codex 자체 샌드박스가 우리 bubblewrap 안에서 서서 쓰기를 막는지 | [`codex_sandbox.py`](../../../tools/w2/codex_sandbox.py) | aux-pc-wsl 실행 결과(2단계 기록). 자동 시험은 없다 |
| K 표: K12·K29·K33·K36 닫음, K44·K45 추가, K01·K02·K09·K17·K23·K30·K31·K32·K38·K39·K43 갱신. 열린 결정 C3 추가 | [`NEXT-SESSION.md`](../../../NEXT-SESSION.md) 1·4절 | — |
| PR #8의 코드 주장 대조 | 인계 3절 | `app/static/index.html`, `tools/w2/observe.py` |

검사: Windows와 aux-pc-wsl(`DML_REQUIRE_BWRAP=1`)에서 전체 시험, `runtime_inventory.py --validate`, `check_encoding.py`, `validate_design_tokens.py`. `validate_sources.py`는 WSL에서만 돌렸다(S18). CI 결과는 브랜치 커밋의 check-runs로 본다 — claude 세션은 결과(녹색·실패)만 읽고 원문 로그는 읽지 못한다(K37).

## 잘 안 된 것 — 실패, 실수, 시행착오

번호(S)는 이 요청서 안에서만 쓴다.

### 이 세션의 실수

- **S01 큰 입력을 보내지 않았다(K01 미해결).**
  - `observe.py call`에는 `--pad-kb`가 있었는데 쓰지 않았다. 인계 4절 절차의 명령 예시(`call b1 <모델>`)를 그대로 따랐고, 같은 절 "관측할 것"의 B1 목록("큰 한글·선행 대시 입력", K01의 입력 토큰 대조)과 맞춰 보지 않았다.
  - 승인한 상한을 다 써서 다시 하려면 Claude 1회를 새로 승인받아야 한다.
  - 대응: 인계 절차에 "호출 전에 관측 목록과 옵션을 맞춰 본다"를 넣었다. 도구 쪽 대책은 질문 5.
- **S02 관측 요약에 조직 UUID가 찍혔다.**
  - 도구가 설정 폴더의 파일 이름을 그대로 옮겼다. Claude 2.1.280은 모델 목록 캐시 파일 이름에 조직 UUID를 넣는다. 세션이 원 출력을 읽다가 알아챘다(`~/.claude.json`의 `organizationUuid`와 같은지만 비교하고 값은 출력하지 않았다).
  - 로컬 세션 출력까지만 갔고 저장소에는 옮기지 않았다.
  - 기존 시험은 HOME 경로를 가렸는지만 봤다. 이제 도구가 모양으로 가린다. 새 모양의 식별자는 못 가리므로 "요약도 옮기기 전에 읽는다"를 인계 5절에 넣었다.
- **S03 낡은 하위 명령 형태로 `codex sandbox linux --help`를 불렀다.** 0.156.1은 `codex sandbox [COMMAND]...`라 `linux`를 실행하려다 panic이 났다. 모델 호출은 아니었다. help부터 봤어야 했다.
- **S04 셸 명령 안의 `cd`가 이 세션의 작업 폴더를 하위 폴더로 옮겼다.** 두 번 되돌렸다. 결과에는 영향이 없다.

### 계획대로 되지 않은 것

- **S05 K31을 init 이벤트로 닫는 계획이 성립하지 않았다.**
  - 2.1.280의 stream-json init에는 불러온 지시문·메모리 파일을 보여 주는 칸이 없다.
  - 계획은 aux-pc 기록의 한 줄("메모리 경로 없음 — 원 stream에서 수행자가 확인")에 기댔다. 그 필드가 이 버전의 init에 있는지 먼저 확인하지 않았다.
  - `CLAUDE.md`를 싣지 않았다는 근거는 여전히 모델의 보고다(두 조합 모두 "없음").
- **S06 Codex가 쓰기 단계를 시도하지 않고 답했다.**
  - `b2`에서 첫 메시지는 "쓰기를 해 보겠다"였지만 명령 없이 "읽기 전용이라 안 된다"고 답했다.
  - probe가 모델의 협조에 기대고 있어서 쓰기 차단, 중첩 샌드박스(K12), Linux의 거절 문자열(K30)을 그 호출로 보지 못했다.
  - K12는 모델 없는 진단으로 메웠다. K30은 남았다.
- **S07 Claude 쪽에서는 우리 bubblewrap 경계가 시험되지 않았다.** 금지 파일 읽기를 CLI의 `--restricted`가 먼저 거절했다. 경계 자체는 `b2`(Codex가 실제로 `head`를 돌려 "파일 없음")와 합성 시험이 본다.
- **S08 도구의 멈춤 규칙이 사용자의 규칙보다 약했다.**
  - `as_expected`는 답을 받았는지만 봤다. 경계가 깨져도 "기대대로"로 적고 다음 호출을 막지 않았을 것이다.
  - 이번 다섯 호출에서는 위반이 없었다. 세션이 답과 원 출력을 직접 읽어 확인했다.
  - 고쳤다(`boundary_violations`).
- **S09 `config_changes`의 이름 목록이 50개에서 잘려 Codex의 상태 DB가 빠졌다.** 호출 뒤 폴더 목록으로 찾았다. 전체 수와 폴더별 수를 더했다.
- **S10 요약의 `spec.argv`가 실제로 돌린 argv와 달랐다.** `p3-claude`에서 `dontAsk`를 보였다. `argv_run`을 더했다.
- **S11 `p3-*`에서 CLI가 stdin을 읽지 않고 끝났는데 `input_delivery`는 `complete`였다.** K01에 적힌 한계가 실제로 나타났다(22바이트가 파이프 버퍼에 다 들어감).
- **S12 Codex 문맥 판정은 판단이 갈릴 수 있다.** probe는 작업 폴더에 `AGENTS.md`를 두었고 참여자 구성은 빈 폴더다. 기록에는 CLI의 동작으로 보고 `failed`로 적었다(질문 1).
- **S13 Claude 문맥 판정도 판단이 갈릴 수 있다.** 모델의 보고와 init의 구조(사용자 확장 없음)에 기대어 `observed`로 적었다(질문 1).
- **S14 예상하지 못한 부수 효과: Codex가 계정의 원격 플러그인을 받았다.**
  - `--ignore-user-config`로도 계정의 원격 플러그인(사용자가 만든 것 포함)과 공급자 스킬을 `~/.codex`에 받았다.
  - 참여자 문맥에 들어가는지는 모른다(K44). 그 폴더는 모든 실행이 공유한다(K09).
- **S15 설명하지 못한 관측.** Claude `--safe-mode`를 더하면 init에 내장 플러그인 `agents-md`가 나타났다(K45).

### 작업 방식에서 막힌 것

- **S16 main 병합이 이 세션의 권한 확인에 막혔다.** 저장소 규칙(인계 2절 8)은 CI 녹색이면 claude 세션의 병합을 허락한다. 이 세션의 자동 권한 확인은 검토 없는 main 병합을 거절했다. 우회하지 않고 사용자에게 넘겼다. 그래서 이 요청서도 병합 전 브랜치에 있다.
- **S17 PR을 만들지 못했다.** 이 PC에는 `gh`도 GitHub 인증도 없다(이전과 같다). 사용자가 GitHub에서 브랜치로 PR을 열 수 있다.
- **S18 Windows Python에 `jsonschema`가 없어 원장 검사가 Windows에서 돌지 않았다.** WSL(4.10.3)과 CI에서는 돈다. skip은 통과가 아니다.
- **S19 커밋 훅의 통과 메시지가 cp949 콘솔에서 깨져 보인다.** 동작은 정상이다.
- **S20 실행 허가 시험이 기록의 상태를 고정하고 있었다.** "아직 허가 없음"을 고정해 두어 기록을 채우면서 시험도 바꿨다. 기록 변경을 의식적으로 하게 하는 의도된 설계로 보지만 확인을 부탁한다.
- **S21 Claude 모델을 세션이 골랐다.** 사용자는 "아무거나"라고 했다. 세션은 이 계정·버전에서 같은 이름으로 보고된 적이 있는 `claude-sonnet-5`를 골랐다 — 실패도 횟수에 들어가기 때문이다. 사용량이 더 적은 모델(Haiku 4.5)보다 많이 썼을 수 있다.

## 아직 모르는 것

- 토큰 갱신 때 CLI가 인증 파일을 어떻게 쓰는지. 이번 호출에서는 갱신이 없었다(K09).
- Codex의 계정 플러그인과 공급자 스킬이 문맥에 들어가는지(K44). `agents-md`가 무엇을 하는지(K45).
- Linux Codex가 실행 전 거절 문자열을 내는 경우가 있는지(K30). 실제로 어느 Codex 모델이 답했는지(K32).
- 실제 CLI에서 큰 입력이 끝까지 읽히는지(K01).
- `codex sandbox`의 기본 정책이 `codex exec --sandbox read-only`가 명령을 돌릴 때와 같은지. 두 변형의 결과가 같다는 데까지만 봤다.
- 다른 기기·버전에서도 같은지(K35).

## 읽는 순서

결론에 끌려가지 않도록 **코드·관측을 먼저, 우리의 판정을 나중에** 읽는다.

1. [`AGENTS.md`](../../../AGENTS.md), [`docs/COLLABORATION.md`](../../COLLABORATION.md).
2. [`NEXT-SESSION.md`](../../../NEXT-SESSION.md)의 **2절만**. 논쟁하지 않는 전제다. 그리고 [2단계 기록](../../experiments/w2-isolation/stage2-aux-pc-wsl.md)의 "승인" 절.
3. 코드와 시험:
   - [`tools/w2/observe.py`](../../../tools/w2/observe.py), [`tests/test_w2_observe.py`](../../../tests/test_w2_observe.py)
   - [`tools/w2/codex_sandbox.py`](../../../tools/w2/codex_sandbox.py)
   - [`app/cli_executor.py`](../../../app/cli_executor.py), [`core/adapters.py`](../../../core/adapters.py)의 `build_spec`·`interpret`, [`core/isolation.py`](../../../core/isolation.py)의 `cli_mounts`·`plan`
   - [`core/eligibility.py`](../../../core/eligibility.py)의 칸 정의
4. 관측: 2단계 기록의 "호출과 결과"부터 "설정 폴더에 쓴 것"까지. **"판정" 절은 아직 읽지 않는다.** 여기서 각 CLI의 세 칸(전송·문맥·권한)을 `observed`·`failed`·`unknown` 가운데 무엇으로 적겠는지 스스로 적어 둔다.
5. 우리의 판정: 2단계 기록의 "판정"과 "도구에서 고친 것", [`manifest.v2.json`](../../experiments/v04-01-inventory/hosts/aux-pc-wsl/manifest.v2.json), 인계 1·3·4절(K 표). 4에서 적은 판단과 비교한다.
6. 이 문서의 "잘 안 된 것".

## 검토 질문 — 중요한 순서

각 질문에 "동의 / 부분 동의 / 반대"와 근거를 적는다. 근거가 없으면 "판단 보류"라고 쓴다.

1. **기록의 판정.**
   - Claude `context_conformance: observed` — 지시문 파일이 실리지 않았다는 근거가 모델의 보고뿐이다. `observed`가 맞는가, `unknown`이어야 하는가.
   - Codex `context_conformance: failed` — probe 구성(작업 폴더에 `AGENTS.md`)과 참여자 구성(빈 폴더)이 다르다. `failed`가 맞는가, 참여자 구성으로 다시 봐야 하는가. 계정 플러그인(K44)은 어떻게 다뤄야 하는가.
   - Codex `permission_conformance: observed` — 쓰기 차단의 근거가 exec 호출이 아니라 `codex sandbox` 진단이다. 받아들일 만한가.
   - Claude `transport_observed` — 참여자 argv는 `--output-format json`인데 관측은 stream-json이었다(마지막 result 이벤트가 json 출력과 같은 객체라고 봤다).
2. **관측 도구의 수정.**
   - `_scrub`이 가리는 모양(UUID, 24자 이상 16진수)이 충분한가. 놓칠 만한 식별자가 있는가(이메일 모양 파일 이름, base64 세션 ID 등).
   - 새 멈춤 규칙이 맞는가. 빠진 위반이 있는가(허용 밖 경로에 대한 도구 시도 자체, 네트워크 시도 등). 지시문 표식을 뺀 판단은 맞는가.
   - `as_expected`의 뜻이 바뀌었다. 과거 호출 장부(`calls.jsonl`)를 읽을 때 문제가 되는가.
3. **K12 진단의 타당성.** `codex sandbox` 기본값을 `codex exec --sandbox read-only`의 명령 실행과 같은 정책으로 봐도 되는가. 더 나은 모델 없는 확인이 있는가.
4. **K 표.** 닫은 것(K12·K29·K33·K36)이 정말 닫혔는가. 새 K44·K45의 문장이 맞는가. K01·K31을 가장 싸게 닫는 방법은 무엇인가.
5. **실수의 재발 방지.** S01(옵션 누락)·S05(없는 필드에 기댄 계획)·S06(모델의 협조에 기댄 probe)을 도구나 절차로 막을 방법. 예: probe마다 관측 항목과 필요한 옵션을 도구에 적어 두고 `plan`이 보여 주기, `b1`의 기본 입력을 크게 하기.
6. **다음 단계 순서.** 열린 결정 C3의 (a)/(b), K01·K09 후속 호출, 3단계(A1 이어서) 가운데 무엇을 먼저 할지. B3 pilot 전에 꼭 필요한 것은 무엇인가.
7. **PR #8 대조.** 인계 3절의 대조에 동의하는가 — P05는 맞음, TM-01은 이미 성립, TM-02는 부분적으로 맞음.
8. **계정 한도 정보.** Claude stream-json의 `rate_limit_event`를 사용량 표시(2절 4)에 쓰려면 참여자 argv를 stream-json으로 바꿔야 한다. 그 변경의 위험은 무엇인가 — 출력 해석, 봉인 투영으로 새는 정보 등.

질문 밖이라도 **틀린 사실, 깨진 링크, 기록과 다른 코드**를 찾으면 적는다.

## 결과를 남기는 방법

- 새 브랜치 `<에이전트>/review-stage2-<YYYYMMDD>`를 만든다(예: `chatgpt/review-stage2-20260924`). 이 요청서가 main에 없으면 `claude/stage2-observe-20260923`을 base로 한다.
- 리뷰는 `docs/reviews/<YYYY-MM-DD>-stage2-review/README.md`에 쓰고 PR을 연다. [PR 템플릿](../../../.github/pull_request_template.md)을 채우고, 접근 범위에는 실제 범위를 적는다.
- 재현 코드를 돌렸다면 같은 폴더에 스크립트와 결과를 둔다. 무엇을 어디서 실행했는지 적는다. 검토 대상 파일의 해시를 고정해 두면 수정 뒤와 헷갈리지 않는다(앞 리뷰의 방식).
- 리뷰 문서의 형식:

| 절 | 내용 |
|---|---|
| 요약 | 가장 중요한 발견 세 개 이내 |
| 발견 | 번호, 심각도(높음·중간·낮음), 위치(`파일:줄` 또는 URL), 근거 등급(**관측** / **재현** / **문서** / **추론**), 내용, 제안 |
| 질문별 답 | 위 1–8에 대한 동의·부분 동의·반대·보류와 근거 |
| 확인하지 못한 것 | 접근할 수 없었거나 읽지 않은 것 |

- **명백한 오류**(오타, 깨진 링크, 기록과 다른 숫자)는 같은 PR에서 원본을 고쳐도 된다. 커밋 메시지에 무엇이 왜 틀렸는지 적는다. **판단이 갈리는 것은 고치지 말고 리뷰에만 적는다.**
- 살아 있는 문서에 검사 수·원장 건수를 적지 않는다(CI가 막는다). `NEXT-SESSION.md`는 절 구성을 유지한 채 3절에 리뷰 브랜치를 적는다.
- 병합은 하지 않는다. 사용자 또는 claude 세션이 CI를 확인한 뒤 병합한다.

## 이미 알고 있는 한계

리뷰어가 같은 지적을 반복하지 않도록 적어 둔다. 전체 목록은 인계 4절의 K 표다. 다르게 판단하면 그 근거를 적는다.

- 모든 관측은 보조 PC 한 대와 그 안의 WSL 배포판 하나, 2026-09-23 하루치다(K35).
- 원 출력은 PC에만 있다. 저장소에는 계정 이메일·조직 ID·토큰·세션 ID를 뺀 요약만 있다.
- claude 세션은 CI 원문 로그를 읽지 못한다(K37).
- A1 화면은 스크린샷으로 확인하지 못했다(K27).
