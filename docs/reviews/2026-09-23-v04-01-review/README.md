# V04-01(aux-pc) 및 협업 가드 검토 — 2026-09-23

작성: ChatGPT, GPT-6 Astra Pro. 접근 범위: **GitHub만**. 사용자 PC의 CLI·로그인·설정·청구 내역에는 접근하지 않았다. 공개 코드의 순수 함수 발췌본을 별도 웹 컨테이너에서 합성 입력으로 실행한 것은 아래에 따로 표시한다.

검토 기준은 `main`의 **`47934759c5d59cc5940aeb32687d00de25e57180`**이다. 요청된 시작점 `c109840890bd72cbe5135f14c4d90c54c9039f0f`과 GitHub compare로 변경 파일을 확인했다. PR #3의 MCP·UI 검토를 다시 수행하지 않고 그 이후의 inventory, 관측 기록, 협업 가드와 V04-03 진입 조건에 집중했다. 기준 SHA 뒤의 변경을 검토했다고 주장하지 않는다.

[검토 요청](../2026-09-23-review-request/README.md) · [원 출력 선검토 메모](preliminary-observations.md) · [재현 스크립트](reproduce_findings.py) · [합성 재현 결과](reproduction-output.json)

**검토 방법의 한계:** NEXT-SESSION.md의 2절 위치를 찾으려고 1–75줄을 요청하면서 1절의 결론 요약도 먼저 반환받았다. 따라서 이 리뷰를 완전한 맹검 독립 평가라고 부르지 않는다. 원 출력 메모를 별도로 남긴 뒤 상세 RESULTS와 manifest를 대조했지만, 최초 요약 노출은 취소할 수 없다. 리뷰어 자신에게도 D11의 기준을 적용한다.

## 요약

1. **Claude Code·Codex로 adapter 골격과 제한된 conformance 준비를 진행하는 것에는 동의한다. 이미 blind·읽기 전용 실행 조건이 충족됐다는 해석에는 동의하지 않는다.** 원 출력의 성공, 옵션 값 검증, 문맥·권한 격리는 별개다. 현 로드맵은 이를 이미 구분하지만 runbook의 통과 조건과 일부 RESULTS/manifest 표현이 더 강하다(R02).
2. **코드에서 고칠 수 있는 구체적인 결함을 확인했다.** `configured=true`가 인증·과금 필드 누락/`null`과 함께 통과하고, `fresh-env`는 영구 설정과 같은 이름의 주입 값을 남긴다. 가림·요약·정규식에도 재현 가능한 누락이 있다. 현재 사용자 계정에서 유출·추가 과금·권한 침해가 발생했다는 발견은 아니다(R01, R03–R05, R08).
3. **공식 문서로 좁힐 수 있는 불확실성이 있다.** Claude `--restricted` locator를 찾았다. Antigravity headless의 없는 모델 이름은 문서상 오류 종료이며, 명시 모델의 stream init 관측 경로도 있다. 반면 공식 CLI를 감싸는 우리 앱의 약관상 허용 여부를 확정하는 Google 답변은 확인하지 못했다. Antigravity를 자동 활성화할 근거는 아직 없다(R07, 질문 3).

## 발견

근거 등급: **관측**은 공개 원 출력·코드에서 직접 확인한 내용이다. 저장소에 기록된 PC 관측은 해당 수행자의 기록이지 리뷰어의 PC 재실험이 아니다. **문서**는 아래 공식 1차 출처, **추론**은 그 근거에서 도출한 위험·제안이다. 합성 재현은 별도 범위로 표시한다. 심각도는 현재 연구 저장소의 결함이 실제 runner의 승인 조건으로 사용될 때의 영향을 포함한다.

### R01 — 높음: manifest의 `configured` 검사가 누락값을 알려진 인증·과금으로 통과시킨다

**위치:** [tools/runtime_inventory.py:346–406](../../../tools/runtime_inventory.py#L346-L406), `validate_manifest`; [tests/test_runtime_inventory.py](../../../tests/test_runtime_inventory.py).

**근거: 관측(코드), 합성 재현.** 조건은 `"unknown" in (row.get("auth_mode"), row.get("funding_mode"))`이다. 키가 없거나 값이 `null`/빈 문자열이면 문자열 `unknown`이 아니므로, tier 2와 observed capability 하나만 있으면 통과한다. 다음 경우도 확인했다.

| 합성 입력 | 현재 관측 결과 | 필요한 처리 |
|---|---|---|
| auth/funding 모두 누락, `null`, 또는 빈 문자열 | 오류 목록이 비어 있음 | 누락·타입·허용값 오류 |
| `configured=true`, `installed=false` | 통과 | 상태 모순 거절 |
| `evidence=true`, `observed_at=true` | 통과 | 근거 참조·날짜의 타입 검사 |
| `adapter_id=[]` | `TypeError` | 정형 validation 오류 |
| `env_presence=["bad"]` | `AttributeError` | 정형 validation 오류 |
| presence 항목에 `value: "FAKE_NON_TOKEN_SECRET"` 추가 | 통과 | 허용되지 않은 값 필드 거절 |

이는 실제 collector가 비밀을 넣었다는 뜻이 아니다. **수동 보완한 manifest도 검사기가 차단한다는 보장이 성립하지 않는다는 뜻**이다. 현재 aux-pc의 auth/funding 값은 채워져 있으므로, 이 코드 결함만으로 그 관측을 거짓으로 재분류하지 않는다.

**제안:** 필수 키·정확한 타입·버전별 enum을 먼저 검사하고, 그 뒤 `configured` 교차 필드 불변식을 검사한다. 문자열 `unknown`뿐 아니라 모든 미확인 상태를 명시적으로 거절한다. evidence는 비어 있지 않은 참조와 관측 시점을 요구하되, 형식 검증을 사실 검증으로 부르지 않는다. presence 객체는 `present/adapter/why` 같은 선언된 키만 허용한다. 배열·숫자·bool·null을 포함한 표 기반 부정 테스트를 추가한다. `configured`를 곧 실행 허가로 쓰지 않고 별도의 conformance gate를 둔다.

### R02 — 높음: 실행 성공과 옵션 검증이 blind·권한 격리의 통과 증거로 확대된다

**위치:** [runbook](../../experiments/v04-01-inventory/README.md)의 tier 2 판정, [RESULTS:67–78](../../experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md#L67-L78), [manifest.tier2.json](../../experiments/v04-01-inventory/hosts/aux-pc/manifest.tier2.json)의 Claude `permission_mode`와 끝의 `tier2_rule`, [V04-03/격리 검사](../../architecture/v0.4/03-evaluation-and-roadmap.md).

**근거: 관측 + 문서 S1/S4 + 추론.** Claude P3는 잘못된 permission-mode 값을 parser가 거절했다는 증거다. P1은 `dontAsk`를 준 상태에서 도구가 필요 없는 OK 응답을 얻었다. **금지한 도구 호출을 실제로 차단했다는 실험은 아니다.** 그런데 `permission_mode`는 `observed`이고, manifest 자신의 규칙은 값 검증만 된 플래그를 `in_help`에 남기라고 한다. `value_validation=observed`와 `permission_enforcement=unverified`를 구분해야 한다. Codex `sandbox`를 `in_help`로 남긴 처리는 적절하다.

Claude P4b는 공개 요약상 도구·MCP·스킬·슬래시 명령이 줄고 호출이 성공했다. 이것은 유용한 관측이다. 그러나 사용자/관리자 지시문·자동 메모리·부모 문맥·미공개 peer 초안이 입력에 없었다는 증명은 아니다. **내장 플러그인과 기본 agent 목록이 남았다는 사실만으로 오염됐다고 단정하는 것도 잘못**이다. 필요한 것은 '모든 vendor 시스템 프롬프트 제거'가 아니라 '이 과제의 답/peer 정보를 유입시키는 경로의 통제'다.

Codex `--ignore-user-config`는 config.toml, `--ignore-rules`는 execpolicy `.rules`를 대상으로 한다(S4). 그 이름을 모든 AGENTS.md·메모리·지시문 제외로 읽을 근거는 없다. 입력 토큰 감소도 각 경로 차단을 단독으로 입증하지 못한다.

**제안:** 현 로드맵에 이미 있는 '권한 검사 통과 후 연결' 조건을 runbook/다음 작업에서도 유지한다. `installed`, `auth_observed`, `transport_observed`, `context_conformance`, `permission_conformance`, `eligible_for_run`을 별도로 다루고 마지막 값은 실행 직전 계산한다. P1/P3/P4만으로 마지막 두 항목을 통과시키지 않는다. 사용자 승인 뒤의 작은 시험에는 통제된 marker와 양성 대조, 금지 파일/peer 초안의 읽기 시도, 허용 파일 읽기, workspace 밖 쓰기·shell/MCP 실행 거절을 넣는다. marker가 답에 안 나왔다는 것만 보지 말고 접근 거절과 유효 권한을 확인한다. 사용자 원본이 아닌 합성 파일로 시작한다.

**진행 판정:** 문서·오프라인 adapter 배선은 진행 가능하다. 실제 독립 초안 수집은 이 conformance를 완료한 경로에 한한다. 저장소 전체를 멈추거나 기존 aux-pc 설치 관측을 취소하라는 지적이 아니다.

### R03 — 중간: `fresh-env`는 새 터미널 환경을 재구성하지 않는다

**위치:** [runtime_inventory.py:184–204](../../../tools/runtime_inventory.py#L184-L204), [fresh-shell.ps1](../../../tools/v04-01/fresh-shell.ps1), [probe.ps1](../../../tools/v04-01/probe.ps1)의 환경 표기.

**근거: 관측(코드), 합성 재현.** 현재 구현은 AI 접두사 변수 중 **동일 이름이 시스템/사용자 설정에 없을 때만** process 값을 지운다. 이름이 있으면 그 설정의 값으로 덮어쓰지 않고 현재 process 값을 유지한다. 영구 설정에 새로 생긴 변수도 추가하지 않는다. PATH만 별도로 합친다.

예컨대 base의 `ANTHROPIC_BASE_URL=https://injected.invalid`, 사용자 설정의 같은 키 `https://expected.invalid`를 넣으면 전자가 남는다. 사용자 설정에만 있는 새 `CODEX_API_KEY`는 결과에 없다. 모두 합성 값으로 확인했으며 실제 사용자 설정을 읽지 않았다.

함수 주석의 '새 터미널에 가까운'이라는 제한은 적절하지만, 이를 실제 새 터미널과 동일하다고 쓰면 안 된다. `probe.ps1`의 `fresh user/system PATH and env` 표기도 호출자가 fresh-shell을 거쳤는지 자체 검증하지 않는다. 명시한 접두사 밖의 proxy/cloud/runtime 변수는 그대로 남는다. registry 값을 프로세스 메모리에 읽는 것과 Git에 값을 기록하는 것도 구분해야 한다.

**제안:** 이 동작을 '상속 AI 변수 정리'로 정확히 부르거나, 사용자 범위 우선·대소문자 무시·REG_EXPAND_SZ 처리까지 정의한 영구 환경 재구성을 구현한다. 구독 전용 실행은 별도 environment allowlist와 과금 경로 preflight로 차단한다. 새로 추가·수정·삭제한 변수, 같은 이름의 process override, 빈 값, PATH 대소문자 조합을 Python/PowerShell 양쪽에서 시험한다. 실제 환경의 값은 로그에 남기지 않는다.

### R04 — 중간: 가림과 presence 검사는 비밀·개인 경로의 완전한 출판 경계가 아니다

**위치:** [runtime_inventory.py:140–175](../../../tools/runtime_inventory.py#L140-L175) 및 `validate_manifest`, [probe.ps1](../../../tools/v04-01/probe.ps1)의 `Mask`와 출력 저장.

**근거: 관측(코드), 합성 재현.** `github_pat_` 접두사의 합성 문자열은 Python SECRET 정규식에 걸리지 않는다. 자신의 home이 아닌 `C:\Users\Jane Doe\notes.txt`는 `C:\Users\<user> Doe\notes.txt`로 일부만 가려지고, 재검사 정규식도 남은 부분을 문제로 잡지 않는다. 이것은 유효 토큰의 실사용 시험이 아니라 가림 규칙의 입력 범위 시험이다. 기존 Google 형태 문자열 가림은 합성 시험에서 동작했다.

PowerShell 가림은 Python과 별개이고 처리하는 토큰 종류도 더 좁다. 현재 `--help` 수집을 credential 조회로 확대하지 않은 점, 인증 파일 내용을 열지 않는 collector, 수동 검토를 요구하는 절차는 바람직하다. 다만 향후 stderr/실패 로그에도 동일한 공개 안전성을 가정할 수 없다. JSON으로 이스케이프된 경로·공백·UNC·다른 OS 경로도 fixtures가 필요하다.

**제안:** 공개 artifact는 필요한 필드만 고르는 projection을 먼저 만들고 가림은 보조로 쓴다. raw 로그는 기본적으로 저장소 밖에 두고, 정제·검사된 사본만 복사한다. presence에 값 필드를 허용하지 않는 R01 수정과 함께 Python/PowerShell 가림의 공통 fixtures를 둔다. 정규식 통과를 비밀 없음의 증명으로 표시하지 않는다. 이번 리뷰에서 실제 사용자 비밀이 유출됐다고 확인한 것은 없다.

### R05 — 중간: 공개 요약과 tier 2 metadata가 판정의 출처·시점을 충분히 보존하지 못한다

**위치:** [summarize_claude_init.py](../../../tools/v04-01/summarize_claude_init.py), [P4b-claude.txt](../../experiments/v04-01-inventory/hosts/aux-pc/tier2/P4b-claude.txt), [manifest.tier2.json](../../experiments/v04-01-inventory/hosts/aux-pc/manifest.tier2.json).

**근거: 관측(코드/공개 기록).** 요약기는 `len(init.get(..., []))`로 누락된 목록도 0으로 만든다. 따라서 다른 버전에서 필드가 빠지거나 일부만 추출된 경우가 '아무것도 로드되지 않음'으로 표현될 수 있다. 공개 P4b 요약에는 plugin 수만 있고 `@builtin` origin, memory 경로의 확인 여부는 없다. RESULTS의 수행자 관측을 부정하는 것은 아니지만, 그 부분을 독립적으로 재검사할 공개 근거는 빠져 있다. `loaded_into_context`라는 이름 역시 init metadata를 실제 전송 프롬프트 전체와 동일시할 여지가 있다.

또한 tier 2 manifest의 `scope.executed`는 여전히 help/version만, `scope.not_checked`는 auth·구조화 출력 등이 미확인이라고 한다. 뒤의 observed 필드와 같은 층에 있으므로 소비자가 서로 다른 뜻으로 읽을 수 있다. agy `resolved_path`도 tier 1의 옛 위치를 유지한다. RESULTS에 재설치 과정과 `derived_from` 설명이 있으므로 이를 '실제로 재설치하지 않았다'는 근거로 삼지 않는다. 문제는 **baseline 수집값과 후속 관측값의 기계적 구분**이다. UTC 수집 시각이 한국 날짜보다 하루 앞선 것 자체는 결함이 아니다.

**제안:** 필드 누락은 `unknown`으로, 확인된 빈 목록만 0으로 기록한다. raw/sanitized digest, 요약기 revision, 필수 필드 확인 여부, 허용된 origin 분류를 공개 요약에 보존한다. 개인 plugin 이름을 전부 공개할 필요는 없다. tier 1 baseline과 tier 2 observations를 나누고 각각의 시각·실행 파일·명령·근거를 연결한다. 날짜 붙은 원 기록을 소급 덮어쓰지 말고 후속 판정/정정 artifact를 추가한다.

### R06 — 중간: probe helper는 timeout·출력 채널·완전한 종료의 재현 가능한 계약이 없다

**위치:** [tools/v04-01/probe.ps1](../../../tools/v04-01/probe.ps1), [runtime_inventory.py](../../../tools/runtime_inventory.py)의 `run_probe`, [로드맵 V04-03/§9](../../architecture/v0.4/03-evaluation-and-roadmap.md).

**근거: 관측(코드) + 추론.** tier 1 Python helper는 timeout과 stdin DEVNULL을 사용한다. 반면 tier 2 PowerShell helper는 native 실행에 외부 deadline을 적용하지 않고 `2>&1 | Out-String`으로 채널을 합쳐 끝까지 버퍼링한다. 이 파일만으로는 stdout의 JSON과 stderr의 권한 경고를 다시 구별할 수 없고, hang/부분 출력/자식 잔존을 종료 상태와 함께 보존하는 계약도 없다. 이 때문에 현재 기록된 성공·실패 결과가 틀렸다는 뜻은 아니다.

P6/P7 미실시는 요청서가 이미 밝힌 한계다. 그것을 새 발견으로 세지 않는다. 지적은 **현재 helper를 그대로 production runner로 옮기면 known limitation이 그대로 실행 경계가 된다**는 점이다. 로드맵 §9도 이미 자식 잔존·event 유실을 검사하라고 한다.

**제안:** mock executable로 stdin EOF, stderr-only denial, 부분 JSON, 장시간 대기, cancel 후 늦은 응답, 자식 프로세스 잔존을 먼저 검사한다. argv 배열, 명시 stdin 종료, stdout/stderr 분리, deadline, 프로세스 트리 종료 확인, 최대 출력 크기를 runner 계약에 둔다. timeout은 성공이 아니며 종료 미확인은 `UNKNOWN`; 재시도 전에 실행 상태와 소모 예산을 조정한다. 모델 호출 없이 준비할 수 있는 부분이다.

### R07 — 중간: 모델 선택에 대한 관측 범위와 새 공식 문서의 정보를 분리해야 한다

**위치:** [RESULTS:71 및 설계 입력 8](../../experiments/v04-01-inventory/hosts/aux-pc/RESULTS.md#L71), [P5-agy.txt](../../experiments/v04-01-inventory/hosts/aux-pc/tier2/P5-agy.txt), [NEXT-SESSION.md §4](../../../NEXT-SESSION.md), 공식 문서 S2.

**근거: 관측 + 문서.** P5는 모델 목록이다. 첫 행이 Flash라는 것만으로 기본 선택값을 입증하지 못하고, 목록의 각 모델을 실제 호출해 성공했다는 뜻도 아니다. 별도로 기본값을 관측했다면 해당 근거를 연결해야 한다. 응답 품질이나 모델 자체의 자기소개로 모델 ID를 검증해서도 안 된다.

새로 확인한 S2의 `Select a model, effort, or agent`와 `Handle exit codes and errors`는 **headless에서 없는 `--model`을 주면 비영 종료/ERROR가 나며 조용히 대체하지 않는다고 명시**한다. P3의 output-format fallback을 모든 옵션에 일반화할 수 없다는 적극적 근거다. `Streaming JSON`에는 명시 모델의 `init.model`도 설명돼 있다. 따라서 '현재 P1 JSON에는 모델이 없다'는 맞지만 '관측할 방법이 없다'로 확대하면 안 된다.

단, 이는 2026-09-23에 읽은 살아 있는 문서다. aux-pc의 agy 1.2.8에서 해당 동작을 재실험한 것이 아니다. 실제 help의 timeout 기본값과 현재 웹 문서도 차이가 있으므로 버전 일치 검사가 필요하다.

**제안:** 현재 output-format 결함은 유지하고, unknown-model 문제는 '문서상 거절, 설치 버전 확인 필요'로 좁힌다. 모델/effort/format을 버전별 allowlist로 사전 검증하고 요청값과 init metadata를 대조한다. init가 실제 backend provenance까지 보증하는지는 별도 한계로 남긴다. `requested_model`, `reported_model`, `model_origin_provider`, `transport`, `funding_profile`, `quota_pool`을 분리한다. agy를 통해 Claude 계열을 선택했다고 Claude Code의 구독 한도와 동일하다고 가정하지 않는다. `--effort`의 invalid-value 동작은 이번 근거로 확정하지 못했다.

### R08 — 낮음: 개수 금지 regex는 의미가 아니라 표현을 잡고, SHA 예외는 줄 전체를 면제한다

**위치:** [tests/test_research_integrity.py](../../../tests/test_research_integrity.py)의 `RESTATED_COUNT`·`living_lines`·인계 검사, [tools/check_encoding.py](../../../tools/check_encoding.py).

**근거: 관측(코드), regex 합성 재현.** `전체 3개 provider를 지원한다`는 검사/원장/commit 수가 아닌데 매치된다. 반면 `검사 총 120개`, `tests: 120`, `63 commits`는 매치되지 않는다. 같은 줄에 관련 없는 40자리 SHA가 있어도 그 줄 전체를 제외하므로 수치를 해당 revision에 실제로 귀속시켰는지는 확인하지 못한다. 이것은 정책 자체의 오류가 아니라 lint의 범위와 메시지 문제다.

인계 제목·절 이름·순서의 고정 검사는 문서 구조를 안정화한다. 그러나 '병합되지 않은 브랜치: 없음'이라는 내용이 원격 상태와 맞는지는 검사하지 않는다. 모든 `##`를 고정하는 방식은 이후 필요한 절 추가를 막을 수 있으므로 하위 내용은 `###`로 확장하는 규칙을 유지하면 된다.

제어 문자 검사는 UTF-8 decode/BOM/C0·DEL에 대해 타당하다. 탭·개행·CR 허용도 정상이다. 모든 Unicode 제어문자/양방향 제어, 문자열 안에 escape로 쓰인 문자의 런타임 의미까지 검증하는 것은 아니다. 선택 확장자가 대상이며, 현재 TS/TSX 등은 포함되지 않는다. 명시한 경로가 존재하지 않으면 대상에서 빠질 수 있는 점도 보완할 수 있다. 인코딩 가드를 범용 보안 검사로 만들 필요는 없다.

**제안:** 검사·원장·commit이라는 대상 명사와 숫자의 관계를 좁히고 실제 한영 문장 fixtures로 FP/FN을 관리한다. 정확한 의미 판정이 안 되는 lint임을 명시한다. revision 예외는 명시적인 표기 문법/좁은 suppression으로 제한한다. 원격 PR 상태는 CI의 정적 제목 검사와 별개로 인계/병합 시 재확인한다. 제어 문자 가드는 검사 범위를 명시하고 실제 사용하는 확장자·존재하지 않는 명시 경로를 테스트한다.

### R09 — 중간: provider를 빼는 원칙은 옳지만 '언제, 어떤 결과 상태로' 빼는지 시험이 필요하다

**위치:** [02-frontier-architecture.md §2/§6/§9/D11·D13·D18](../../architecture/v0.4/02-frontier-architecture.md), [03-evaluation-and-roadmap.md V04-03](../../architecture/v0.4/03-evaluation-and-roadmap.md), [NEXT-SESSION.md §2.13/§4](../../../NEXT-SESSION.md).

**근거: 관측(설계 내용) + 추론.** 로드맵에는 정족수·재시도 예산·초기 peer 차단·UNKNOWN 처리가 이미 있다. 새 대규모 설계 문서가 없다는 결함을 주장하지 않는다. 다만 adapter 구현에서 아래 전이를 하나의 결정표와 mock trace로 고정하지 않으면, provider 제거가 성공 조건의 사후 완화가 될 수 있다.

| 사건 | 필요한 실행 처리 |
|---|---|
| 시작 전 provider 사용 불가 | 사전 허용 구성 중 선택하고 manifest 고정. 필수 모델/정족수 부족이면 BLOCKED |
| 독립 초안 단계에서 한 경로 한도 소진 | 실패 attempt와 소모를 보존. 남은 구성이 사전 조건을 만족할 때만 부분/축소 모드로 진행 |
| peer 초안 공개 뒤 대체 경로 추가 | 같은 blind round의 독립 참여자로 편입하지 않음. 새 run으로 격리하거나 독립성 상실을 명시 |
| cancel/timeout인데 종료가 불명 | 해당 호출을 UNKNOWN으로 유지. 'provider 제거=호출 취소 완료'로 처리하지 않음 |
| 합성자만 사용 불가 | 이미 모은 원문·반례를 결정적 보고서로 반환할 수 있으나 완성된 합성 성공으로 표시하지 않음 |
| provider가 회복됨 | 진행 중 membership을 조용히 바꾸지 않고 다음 run/preflight에서 다시 편입 |

재시도·형식 복구·합성 호출도 공통 예산에 포함한다. 동일 quota pool을 공유하는 경로는 독립된 잔여 한도라고 보지 않는다. 단, 서로 다른 앱이라는 이유만으로 quota가 공유된다고 추측해서도 안 된다. 제거 정책은 실패 원인별로 나누어 syntax/config 오류를 quota 소진과 혼동하지 않게 한다.

**제안:** 이 표를 구현 부정 fixtures로 먼저 옮기고 V04-03의 결과 상태에 `requested/actual participants`, 축소 승인, missing coverage, 실패 원인, budget reservations를 남긴다. 사용자 원칙인 **유료 API 전환 금지**는 그대로다. 원칙을 바꾸는 제안이 아니라 D11/D13/D18을 함께 만족시키는 실행 순서의 명시다.

## 질문별 답

### 1. 원 출력과 RESULTS/manifest 판정이 맞물리는가 — 부분 동의

P1의 응답과 형식, P2의 bare 인증 실패, P3/P3b의 이름·값 구분은 공개 기록과 맞는다. Claude/Codex의 adapter 준비를 먼저 하는 판단도 합리적이다. 구독 로그인 상태는 해당 PC 수행자의 별도 기록을 근거로 존중하되, OK 응답이나 `apiKeySource=none`만으로 독립 검증했다고 하지 않는다.

Claude `permission_mode=observed`는 자체 tier2_rule과 맞지 않고, Codex `ignore_user_config`는 성공 실행/토큰 변화 관측과 실제 문맥 격리 효과를 구분해야 한다. 두 `configured=true`는 '기본 연결 확인'이라는 제한된 의미로만 읽는다. 모든 conformance 완료를 뜻하면 반대한다(R01/R02). bare의 실패 동작을 observed로 기록한 것 자체는 괜찮지만 usable subscription capability로 오독하지 않게 해야 한다. Antigravity `configured=false` 보류에는 동의한다.

### 2. P4b가 blind 조건을 충분히 만족하는가 — 부분 동의, 충분성에는 반대

사용자 설치 도구/스킬/MCP 유입을 크게 줄인 증거로는 유용하다. 남은 built-in scaffold는 그 자체로 오염의 증거도, 무해함의 증명도 아니다. R02/R05의 통제된 실험이 필요하다.

공식 locator는 **S1의 CLI flags → `--restricted`**다. v2.1.248 이상, user/project settings 제외와 managed/명시 settings 유지가 설명돼 있다. 같은 표의 **`--safe-mode`**는 CLAUDE.md·자동 메모리 등을 더 넓게 제외하면서 인증을 유지하는 후속 시험 후보다. 다만 관리 정책 일부는 남고, 이 조합이 해당 계정에서 blind+구독을 실제로 충족했는지는 시험하지 않았다. `--bare`나 권한 우회로 바꾸라고 제안하지 않는다.

### 3. 공식 agy subprocess 방식이 약관 위반인가 — 판단 보류

**S3 §6은 토큰 탈취만 금지하는 좁은 문장이 아니다.** 제3자 도구를 통한 접근을 넓게 금지하고 계정 정지 가능성을 적는다. OAuth 사용 사례는 예시이므로 '토큰을 안 만지면 반드시 허용'은 도출되지 않는다. 반대로 S2는 프로그램/CI 통합을 직접 안내하므로 '모든 subprocess/스크립트가 금지'라고 단정하는 것도 지나치다. 기술적 headless 지원과 우리 제3자 앱의 허용 범위 사이를 잇는 명시적인 Google 해석이 부족하다. 사용자 동의가 약관 예외를 만들어 주지는 않는다.

Google 공식 안내에서 연결한 저장소의 **이슈 #711**에는 native auth를 보존한 local PTY/stdio wrapper에 대한 거의 같은 질문이 있다(S6). 확인한 댓글은 질문자의 재문의뿐이었다. 이는 **허용 근거가 아니라 미해결 질문의 위치**이며, 커뮤니티 주장으로 정책을 판정하지 않았다. 이번 검색·확인 범위 밖에 Google 답변이 전혀 없다는 주장도 하지 않는다.

운영 제안은 조건부 adapter를 비활성 상태로 보존하고, 적용 계정의 약관과 공식 서면 답변/명확한 예외가 확보된 뒤 활성화하는 것이다. 위험 표시만으로 `policy_verified=true`를 만들지 않는다. 법률 자문이나 계정 제재 예측은 아니다. S3 상단에는 별도 기업 계약 적용 시의 예외도 있으나 이를 사용자의 계정에 임의 적용하지 않는다. **F30의 소비자 Gemini CLI 경로 종료는 S5 원문과 부합**하며 agy 종료와 혼동해서는 안 된다.

### 4. 잘못된 옵션 값이 전부 조용히 fallback하는가 — 일반화에는 반대

직접 관측은 `--output-format notaformat`에 한정된다. unknown-model에 관해서는 오히려 S2의 명시적 오류 종료 설명을 확인했다(R07). `--effort`와 설치 버전의 실제 행위는 판단 보류다. 사전 allowlist, model/effort 호환성, argv 직렬화, requested/reported 대조, terminal status·exit·stderr의 복합 판정이 필요하다. P2의 `subtype=success`와 `is_error=true` 조합도 parser fixture로 유지한다.

### 5. inventory 코드와 테스트가 충분한가 — 부분 동의

표준 라이브러리, help/version 한정, 자격증명 파일 내용 비열람, presence 기록, timeout, shell=False 성격의 argv 실행은 좋은 경계다. 그러나 R01/R03/R04의 명확한 반례가 있고 기존 테스트는 이를 막지 못한다. 원본 함수를 import하는 동봉 스크립트로 재현을 다시 확인한 뒤 production 코드와 회귀 테스트를 함께 수정하는 것이 우선이다. 새 모델 호출은 필요 없다.

### 6. 협업 규칙과 CI 가드가 적절한가 — 부분 동의

살아 있는 문서의 가변 숫자 복제 방지, 인계 절 구성, UTF-8/제어 문자 보호라는 목적에 동의한다. lint가 의미 검증이나 원격 상태 검증을 대신하지는 않는다(R08). 추가로 `check-versions.ps1`은 signer subject를 출력하지만 그 자체로 `Get-AuthenticodeSignature(...).Status == Valid`를 검사하지 않는다. 기존 수행자가 서명 유효성을 별도로 확인했다는 기록을 부정하지 않으며, 다음 실행에서는 Status도 비밀 없이 남기는 보완이 적절하다.

### 7. provider 탈착과 정족수·blind·예산이 충돌하는가 — 원칙에 동의, 실행 규칙은 보완 필요

run 시작 전 구성 선택과 실행 중 참가자 제거를 분리하면 충돌하지 않는다. 실행 후 성공 기준을 바꾸거나 이미 동료 답을 본 대체 모델을 독립 초안으로 세면 충돌한다. R09의 전이 fixtures가 필요하다. V04-03은 문서 추가보다 R01의 fail-closed 검사, 입력/권한 conformance, 종료/부분 출력 계약, 고정 membership을 먼저 구현할 단계다. 로드맵에 이미 있는 미해결 항목을 '새롭게 발견한 결함'으로 중복 집계하지 않았다.

### 8. ACP를 먼저 붙여야 한다는 관측이 있는가 — exec 우선에 동의

제공된 help와 P1에는 exec/print의 실제 성공이 있고, 같은 조건의 ACP conformance/우월성을 입증한 관측은 없다. help에 ACP가 없다는 사실은 외부 bridge가 존재하지 않는다는 증거가 아니다. S6의 ACP wrapper 문의도 성능·정책 적합성의 관측이 아니다. 첫 pilot에서 확인할 auth·문맥·권한·모델·취소 문제는 transport를 바꿔도 남으므로, 구현 범위를 줄이는 exec 우선을 뒤집을 근거를 찾지 못했다. 실제 resume/cancel/permission 요구를 native exec가 충족하지 못하고 특정 ACP 경로가 같은 구독·격리 조건에서 충족하는 관측이 나오면 재검토한다.

## 공식 출처와 확인 위치

아래 S 번호는 **이 리뷰 안의 참조 번호**이며 sources.json의 E/F 번호가 아니다. 모두 2026-09-23에 해당 본문 또는 API 댓글을 직접 확인했다. 살아 있는 웹 문서를 aux-pc 설치 버전의 실측으로 치환하지 않는다.

| ID | 출처 | 사용한 locator / 한계 |
|---|---|---|
| S1 | [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference) | CLI flags의 `--restricted`, `--safe-mode`, `--strict-mcp-config`. 인증/관리 정책 잔여와 별도 conformance 필요 |
| S2 | [Antigravity Headless mode](https://www.antigravity.google/docs/cli/headless/) | Overview; Streaming JSON의 init metadata; Select a model, effort, or agent; Handle exit codes and errors. 설치 버전 재현 아님 |
| S3 | [Google Antigravity Additional Terms](https://antigravity.google/terms) | 적용 범위 첫 문단, §5·§6. 특정 wrapper를 허용하는 개별 답변 아님 |
| S4 | [Codex Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode) | Permissions and safety의 read-only default, ignore-user-config/ignore-rules 범위 |
| S5 | [Gemini Code Assist consumer accounts](https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals) | 본문 첫 문단 및 FAQ. 시행 2026-06-18, 페이지 갱신 2026-09-02; Standard/Enterprise 예외 |
| S6 | [공식 CLI 저장소 #711](https://github.com/google-antigravity/antigravity-cli/issues/711), [확인한 댓글](https://github.com/google-antigravity/antigravity-cli/issues/711#issuecomment-5211506808) | 같은 wrapper 질문의 위치와 답변 상태만 확인. 질문자 의견은 정책의 1차 근거로 채택하지 않음 |
| S7 | [Claude Agent SDK와 구독](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) | 상단 June 15 보류 안내. 하단의 중단된 credit 변경 설명을 현재 정책으로 쓰지 않은 기존 처리는 맞음 |

## 확인하지 못한 것과 검증 범위

**직접 읽은 것:** 요청서/협업 규칙, 지정 aux-pc tier2 txt와 help, runtime_inventory와 테스트, v04-01 보조 도구, runbook, RESULTS/manifest, 새 연구 정합성 검사와 인코딩 가드, F30/F31, D15/D18 및 관련 blind/예산/로드맵, PR 템플릿과 offline workflow. 모든 과거 연구 논문·PR #3의 전체 구현을 재감사한 것은 아니다.

**실행한 것:** 별도 Linux 웹 컨테이너의 Python 3.13.5에서 공개 순수 함수/정규식을 수동 전사한 발췌본에 합성 manifest·환경·문자열을 넣었다. `reproduction-output.json`은 이 제한된 실행의 결과다. 원본 저장소 전체를 clone해 suite를 돌린 결과가 아니다. Git clone은 이 컨테이너의 DNS 오류로 실패했다. 동봉 `reproduce_findings.py`는 실제 checkout에서는 원본 모듈을 import하며 CLI를 호출하지 않는다. 발췌 실행과 실제 checkout 실행을 구분하기 위해 출력에 범위를 남겼다.

**실행하지 않은 것:** 사용자 PC 접근, CLI 설치/모델 호출/로그인/설정 수정, Windows PowerShell·레지스트리 실제 동작, auth·과금 경로 재확인, 권한 탈출/읽기 차단, 장시간·취소·quota 실제 소진, ACP 설치/성능 비교. P4/P4b 원 stream은 PC에 남아 있어 읽지 못했다. 코드 정적 분석으로 실제 비밀 유출이나 추가 과금이 있었다고 단정하지 않는다.

**CI:** 이 리뷰 작성 시점에 이후 최종 commit의 CI 통과를 미리 선언하지 않는다. PR의 실제 check runs 및 그 SHA에 대한 후속 검증 댓글을 기준으로 한다. 기존 full suite가 녹색이어도 R01 등의 부정 사례나 실제 provider 안전성이 검증됐다는 뜻은 아니다.

**이번 변경의 경계:** 리뷰·재현 자료·검토 목록·NEXT-SESSION 3절만 추가/정리한다. 판단이 갈리는 runtime 코드, 날짜 붙은 RESULTS/manifest, 사용자 확정 원칙, 원장 항목은 덮어쓰지 않는다. 원본 수정은 다음 구현자가 finding별 재현·반박을 거쳐 진행하며 이 PR은 병합하지 않는다.
