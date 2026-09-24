# PR #46·#47 검토·병합 — 2026-09-25

작성: claude 세션(Claude 데스크톱 앱). 사용자 PC `aux-pc`(hostname `DESKTOP-L6EA2UJ`)의 Windows Python 3.12.6과 WSL `aux-pc-wsl`(Ubuntu-24.04, Python 3.12.3, bubblewrap 있음)에서 직접 실행했고, GitHub CLI로 PR·CI 로그를 직접 읽었다. 브랜치 `claude/runtime-audit-merge-20260925`는 #47 head `f80074f`에서 시작했다. 사용자 요청은 "확인하고 병합할 것은 병합하고 남은 일을 진행하라"였다. **모델 호출·CLI 로그인 관측·실제 인증 폴더 연결은 이 병합 작업에서 하지 않았다.**

## 결론

1. **#46은 #47의 조상이고, 이 PR은 #47 위에 두 커밋을 더했다.** #47의 [감사 기록](../2026-09-25-runtime-audit-finish/README.md) 결론대로 두 PR을 따로 병합하지 않고 이 PR 하나로 main에 넣는다. 병합하면 두 PR의 head가 main의 조상이 되어 GitHub이 둘 다 병합됨으로 표시한다(#38 때와 같다).
2. **#47의 CI 실패는 사용량 파서(R1)의 회귀 6개뿐이었다.** Linux 3.12·3.13과 Windows 세 job 모두 `OverflowError: int too large to convert to float` 6건만 났다(실행 `36033292418`·`36033298035`). #46 head `5d75bab`의 CI는 성공이다.
3. **R1은 새로 고쳤다.** ChatGPT 세션이 말한 패치 파일(`decision-model_lab-quota-fix.patch`)은 그 세션의 컨테이너에만 있어 이 세션은 볼 수 없었다. 기록에 적힌 원인과 시험만 보고 독립으로 고쳤다(`fde81fa`).
4. **같은 종류의 결함 하나를 더 찾아 고쳤다(U1, `eb4831e`).** CLI 결과의 사용량 칸에 NaN·무한대가 오면 그대로 저장되고, 공개 뒤 화면 응답(`/api/state`) 전체가 브라우저에서 읽히지 않게 된다.
5. **#46·#47의 나머지 코드는 동의한다.** 병합을 막는 문제는 찾지 못했다. 작은 주의점 셋은 아래 "코드 검토 메모"에 적었다.

## R1 — 큰 정수가 사용량 비율 검사를 중단시킴

`core/quota.py`의 `quota_projection`(Codex `usedPercent`)과 `claude_limit`(Claude `utilization`)은 `math.isfinite(used)`를 범위 비교보다 먼저 불렀다. `math.isfinite`는 정수를 float로 바꾸므로 `10 ** 400`(양·음)에서 `OverflowError`가 났다. Claude는 정상 답과 함께 온 선택적 계정 사건 하나 때문에 답 해석 전체가 멈췄다.

감사 기록의 로컬 해법은 두 검사의 순서를 바꾸는 것이었다. 이 세션은 `math.isfinite`를 **뺐다.** 연쇄 비교 `0 <= used <= 100`만으로 NaN(`0 <= nan`이 거짓)과 ±무한대가 모두 떨어지고, 정수와 float의 비교는 변환 없이 정확하게 되므로 범위 검사 뒤의 `isfinite`는 더 이상 거를 값이 없다. 불리언 거절(`type(used) in (int, float)`)은 그대로다. 명시적인 `isfinite`가 빠지므로 Claude의 잘못된 한도 시험에 무한대 경우를 더했다(Codex 쪽은 기존 시험이 NaN·±무한대를 이미 본다).

## U1 — 사용량 칸의 NaN이 화면 전체를 깨뜨림(새로 찾음)

**재현:** Python의 `json.loads`는 비표준 `NaN`·`Infinity` 글자를 받는다. `core/adapters._usage`는 `int`·`float`이면 무엇이든 남겼다(불리언 포함). Claude 결과 줄에 `"total_cost_usd": NaN`이 오면 `usage.client_estimate_usd`가 NaN으로 원장에 저장된다. 공개 뒤 `app/server.py`의 `json.dumps`(기본값 `allow_nan=True`)가 화면 응답에 `NaN` 글자를 그대로 쓰고, 브라우저의 `JSON.parse`는 이를 거절한다. `/api/state`는 모든 실행을 한 응답에 담으므로 값 하나가 화면 전체를 막는다. 이 세션이 합성한 Claude·Codex 출력으로 원장 전 단계(`interpret`의 `usage`)와 엄격한 JSON 해석의 실패를 확인했다. 실제 CLI 출력에서 NaN을 관측한 적은 없다 — R1과 같은 "선택적 부가 정보가 본 경로를 깨뜨리는" 경계다.

**수정:** `_amount`가 음수 아닌 유한수만 남긴다(`type(value) in (int, float) and 0 <= value < math.inf`). 비교만 쓰므로 큰 정수는 표준 JSON이라 남기고 float로 바꾸지 않는다. `client_estimate_usd`도 같은 검사를 쓴다. 합성자의 `synthesizer.usage`도 같은 `Outcome.usage`에서 오므로 함께 고쳐진다. 합성 답(JSON)은 문자열만 옮기므로(`app/synthesis._text`) 이 경로가 아니다.

**시험:** `tests/test_runtime_boundaries.OptionalMetadataTests`에 Claude·Codex 각각 NaN·무한대·음수·불리언이 섞인 사용량을 넣고, 답은 수용되고 그 칸만 빠지며 `allow_nan=False`로 직렬화되는지 본다. 고치기 전 코드로 되돌리면 두 경우 모두 실패하는 것을 확인했다.

## 이전 수정 재검토(#46·#47)

감사 기록 4절의 표를 코드로 다시 확인했다. 같은 결론이다.

| 경계 | 확인한 곳 | 판단 |
|---|---|---|
| 실행당 실제 합성 1회 | `synthesize_with_model`이 그 실행의 모델 합성 시도 사건이 하나라도 있으면 계획·예약 전에 거절 | 맞다. 시작 전 실패(`started: False`)도 다시 부르지 않는 보수적 선택이다 |
| 합성도 공통 상한 | 같은 함수가 일시정지·미종료 상한·병렬 자리를 참여자와 같은 값으로 검사 | 맞다 |
| 종료 미확인 복구 | `app/state.synthesis_attempts`가 사건만으로 시도별 상태를 계산하고, 결과 없는 시작·자손 종료 미확인은 `unknown`으로 자리를 잡는다. 진행 중인 시도만 `running`으로 덮는다 | 맞다. 결과 사건을 쓰지 못한 채 스레드가 끝나도 `unknown`으로 남는다 |
| 사용자 종료 확인 | 그 시도가 `unknown`일 때만 사건을 남기고 자리만 푼다. 예산 환불·재호출 없음 | 맞다 |
| 잠금 순서 | `unsettled()`가 controller 잠금을 새로 잡는다. 부르는 곳(`pump`·`synthesize_with_model`·`view`)은 이미 그 잠금 안이고 재진입 잠금이라 순서가 바뀌지 않는다 | 교착 없음 |
| 자료 복원(R2) | `_source_dir`가 원장의 자료 목록·현재 폴더로 질문 본문을 다시 만들어 고정 질문과 다르면 사본·계획·예약 전에 거절 | 맞다. 아래 메모 1 |
| 화면 | 과거 `unknown` 시도는 live 설정이 꺼져도 확인 버튼을 보이고, 완료된 모델 합성 화면에도 같은 조작을 붙였다 | 맞다. JavaScript 회귀는 CI(Node 22)에서 돌았다 |

### 코드 검토 메모(병합을 막지 않음)

1. **R2 검사는 `PROMPT`·`PROMPT_SOURCES` 문구와 묶인다.** 두 문구를 바꾸면 그 전에 만든 대기 실행은 재개 때 호출 없이 거절된다(닫힌 쪽으로 실패). 두 문구는 처음 만든 뒤 바뀐 적이 없어(`git log -G`) 지금 원장에는 영향이 없다. 문구 옆에 주석으로 남겼다.
2. **`gate`의 `quorum["policy"]` → `run["quorum_policy"]` 변경은 같은 값이다.** `quorum["policy"]`가 `run["quorum_policy"]`를 그대로 담는다. 동작 변화는 없다.
3. **`_slots_used()`가 호출마다 모든 실행의 합성 사건을 읽고 JSON으로 푼다.** 감사 기록 5절의 "원장 규모별 조회 비용 미측정"에 이것도 포함된다. 지금 원장 크기에서는 문제를 보지 못했고, 측정 전에 캐시를 더하지 않는다는 감사 판단에 동의한다.

## 검증

| 항목 | 결과 |
|---|---|
| CI `fde81fa`(R1) | 실행 `36034464619` — Linux 3.12·3.13, Windows 모두 성공 |
| CI `eb4831e`(U1) | 실행 `36034804710` — 세 job 모두 성공. 로그에서 R1·U1 회귀와 Node 화면 회귀 4개가 건너뛰지 않고 `ok`인 것을 확인 |
| Windows 로컬(`eb4831e`) | 508 tests OK. 건너뜀 51 — Linux 전용·bubblewrap·fcntl 시험, 그리고 이 PC의 Windows에 Node가 없어 화면 회귀 4개 |
| WSL 로컬(`eb4831e`) | `DML_REQUIRE_BWRAP=1`로 508 tests OK. 건너뜀 5 — WSL에 Node가 없어 화면 회귀 4개, Windows 레지스트리 1개 |
| 변이 | U1의 `core/adapters.py`를 고치기 전으로 되돌리면 새 시험이 두 경우 모두 실패 |
| 인계 2·5절 | #47의 두 절 SHA-256이 감사 기록의 값(`f2d945fa…`·`d867d5c2…`)과 같고 main과도 같다 |

로컬의 Node 부재로 건너뛴 화면 회귀는 통과로 세지 않았고, CI 로그에서 실행을 확인했다.

## 이번에 하지 않은 것

- 사용자 PC의 CLI·로그인·실제 모델을 이 병합 작업에서 다시 관측하지 않았다. #46·#47의 한계(문맥 독립성 C3 미확인, 실제 중도 취소 미관측, 자료 속 지시문·긴 자료 미시험, Codex 제공 모델 미보고)는 그대로다.
- #47 감사 기록은 날짜가 붙은 기록이라 고치지 않았다. 그 기록의 "R1 원격 미반영"은 이 PR로 해소됐다는 사실을 [검토 색인](../README.md)에 적었다.
