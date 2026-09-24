# Claude 계정 한도 표시(A)와 Codex 가용 모델 확인(F) — 2026-09-24

claude 세션이 [인계 4절](../../../NEXT-SESSION.md)의 A와 F를 구현했다. 사용자는 “차례대로 진행하고 결과랑 다른 오류나 못고치는거 등등해서 잘 정리해줘”라고 요청했다. F는 A와 같은 계정 패널·계정 조회 코드를 고치므로 한 PR에 묶었다.

## 작성·접근 범위

- `aux-pc`의 Windows(Python 3.12.6)와 WSL `aux-pc-wsl`(Ubuntu-24.04, Python 3.12.3, bubblewrap 0.9.0). Node는 이 PC에 없어 화면 함수 시험은 CI에서 돈다.
- **모델 호출 0회.** 실제 Codex app-server 메타데이터 조회 1회(추론 없음, 아래 3절). 실제 Claude 실행은 없다 — A의 실제 화면 확인은 B의 실행에 묻어 간다.
- 공식 문서는 in-app 브라우저로 직접 읽었다: [Agent SDK TypeScript 참조](https://code.claude.com/docs/en/agent-sdk/typescript)의 `SDKRateLimitEvent`, [Codex app-server](https://learn.chatgpt.com/docs/app-server)의 `model/list`.

## 1. 바꾼 것

| 할 일 | 구현 |
|---|---|
| A. Claude 한도 추출 | `core/quota.claude_limit`이 `rate_limit_info`에서 `status`(`allowed`·`allowed_warning`·`rejected`)와 창별 `utilization`(0–1)·`resetsAt`만 남긴다. 문서의 모양(`utilization`·`resetsAt` 하나)과 2026-09-23 관측의 모양(`unifiedWindows`의 `five_hour`·`seven_day`)을 모두 받는다. `errorCode`·`canUserPurchaseCredits`·`hasChargeableSavedPaymentMethod`·초과 사용 칸과 `uuid`·`session_id`는 버린다. `core/adapters.claude_rate_limit`이 stream의 **마지막** 사건을 이것으로 거른다. 모양이 다르면 미확인(None)이고 답의 수용에는 영향이 없다 |
| A. 저장·봉인 | 시도 결과 요약에 `rate_limit`을 넣는다. 봉인 투영의 허용 칸이 아니므로 공개 전 화면에 나오지 않는다. `Controller.claude_account_limit`은 **끝난(settled) 실행의 실제(REAL) 시도**에서만 가장 최근 값을 돌려준다 — 봉인 중인 실행의 계정 비율 변화도 초안 길이의 단서이고(2026-09-24 리뷰 8번), 모의·합성 실행기의 값은 계정 값이 아니다. 보고서(`a1-draft-report/3`)는 허용 목록이라 이 값을 싣지 않는다 |
| A. 화면 | 계정 패널에 “Claude — 마지막으로 끝난 실제 Claude 실행이 받은 값” 구역. 비율을 사용 %로 보이되 Codex 값과 더하지 않는다. 120초가 지나거나 초기화 시각이 지나면 과거 관측값, `allowed_warning`·`rejected`는 따로 알린다. Claude에는 조회 버튼이 없다(2절 5) |
| F. 가용 모델 | 계정 조회가 `account/rateLimits/read` 뒤에 `model/list`(`includeHidden: false`)를 부르고 모델 이름만 남긴다(`core/quota.model_ids`). 화면은 설정한 Codex 모델이 그 목록에 있는지만 보인다. 목록 메서드만 거절되면(`MethodRefused`) 한도는 남기고 목록을 미확인으로 둔다. 시간 초과·서버 요청·에이전트 활동은 여전히 조회 전체를 멈춘다 |
| 화면 정리 | 패널의 문구 계산을 순수 함수(`quotaPeriod`·`quotaRows`·`quotaLines`)로 나눠 Node로 실제 함수를 시험한다. 조회 요청이 실패한 뒤 버튼 글자가 “조회 중…”으로 남던 것([병합 기록 N5](../2026-09-24-merge-39/README.md))을 고쳤다 |

## 2. 계획에서 바꾼 것

- **두 번 온 사건.** 인계 4절 A의 완료 조건은 “두 번 온 사건은 미확인”이었다. 문서는 이 사건을 세션이 한도 확인을 만날 때 보낸다고 적는다. 도구를 여러 번 쓰는 실행은 모델 요청이 여럿이라 사건도 여럿일 수 있다. 그러면 그런 실행은 늘 미확인이 된다. 그래서 **마지막 사건**을 쓰고, 마지막 사건의 모양이 다르면 앞선 사건으로 대신하지 않고 미확인으로 둔다. 몇 번 왔는지(`events`)는 남긴다.
- **F의 자리.** 인계는 “준비 조회에 더한다”였다. 준비 조회(`--check-cli`·`--check-config`)는 프로세스를 띄우지 않는 조회라 그 성격을 바꾸지 않았다. 이미 격리 안에서 app-server를 여는 명시적 계정 조회에 붙였다.

## 3. 확인한 것

- 새 시험: `tests/test_claude_limits.py`(추출·투영·봉인·실제 시도만), `tests/test_quota_render.py`(화면 함수, Node), `tests/test_account_quota.py`·`tests/test_codex_account.py` 추가분. Windows 전체 `OK (skipped=48)`, WSL `DML_REQUIRE_BWRAP=1` 전체 `OK (skipped=3)`(Windows 전용 하나와 Node 없음 둘).
- 변이(매번 원래 바이트로 복구): 봉인 중 값 노출(A1), 모의 값 노출(A2), 결제 칸 유지(A3), 모양이 다른 마지막 사건을 앞 사건으로 대신(A4), 한도 모양 때문에 답 거절(A5), 오래됨 무시(A6), 목록 거절이 조회를 멈춤(F1), 표시 이름 유출(F2) — 모두 새 시험이 잡는다. F2는 처음에 잡히지 않았다. 가짜 서버의 표시 이름에 공백이 있어 이름 형식 검사에서 먼저 걸러졌기 때문이다. 이름처럼 보이는 표시 이름으로 바꿔 시험을 강화했다.
- **실제 F 조회(추론 없음).** WSL의 native Codex 0.156.1로 `tools/w2/codex_account.py --probe`를 한 번 돌렸다. `schema: codex-account-observation/2`, `inference_requests_sent: 0`, `tree_confirmed_empty: true`, 한도 `observed`(행 둘), `model/list` `observed`(목록 잘림 없음), **요청 모델 `gpt-6-luna`가 가용 목록에 있음.** 실제 잔여 비율과 모델 목록 원본은 요금제를 짐작하게 할 수 있어 저장소에 옮기지 않았고, 그 로컬 보고 파일도 지웠다.

## 4. 남은 한계

- **A의 실제 화면 확인은 아직이다.** B의 실제 실행에서 Claude 참여자의 stream에 사건이 오는지, 패널에 뜨는지 본다.
- Claude 값은 “마지막 실제 실행 때” 값이라 실행이 없으면 갱신되지 않고 대부분 과거 관측값으로 보인다. 따로 조회하는 통로는 쓰지 않는다(2절 5).
- `rateLimitType`·`unifiedWindows`는 문서에 없는 칸이다. CLI 판이 바뀌면 사라질 수 있고, 그때는 문서의 칸(`utilization` 하나)만 보인다.
- 가용 모델 목록은 실제로 답한 모델의 보고가 아니다(K32는 그대로).
