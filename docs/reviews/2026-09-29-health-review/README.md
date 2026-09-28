# 전체 점검 — 구조·파이프라인·문서·코드가 건강한가

2026-09-29 · claude(Claude Code 데스크톱, Fable 5.1) · 사용자 PC `DESKTOP-T0UDE01`의 Windows 쪽 · 모델 호출 0 · 기준 main `1d248ed`. WSL·참여자 CLI는 보지 않았다.

사용자 요청: 아키텍처·파이프라인·문서 구조·코드 구조를 전체적으로 점검하고, 흩어졌거나 쓸모없거나 중복이거나 빙 돌아가는 것을 찾아 고친다. 이 기록은 무엇을 봤고, 무엇을 고쳤고, 무엇을 일부러 두었는지 적는다. 고친 코드 자체는 [PR #155](https://github.com/inlight37-design/decision-model_lab/pull/155)에 있다.

## 1. 판단

**뼈대는 건강하다. 다시 만들 것은 없다.** 실행·격리·수용·봉인·원장·호출 상한의 경계는 [2026-09-26 구조 검토](../2026-09-26-architecture-health/README.md)가 본 그대로 튼튼하고, 그때의 S1–S6은 모두 main에 있다. 이번에 찾은 것은 **같은 일을 여러 곳에 손으로 복사한 자국**(다섯 상위 자리가 각자 검증 함수·오류 문구 바꿔치기·관문 검사를 갖고 있던 것, 서버와 헤드리스가 배선을 나눠 쓰려고 서버 모듈을 import하던 것, 검사 도구 넷이 같은 JSON 로더를 갖고 있던 것)과 **살아 있는 문서에 남은 그날의 상태 서술**이다. 모두 고쳤다.

## 2. 어떻게 봤나

세 갈래로 보고 겹치는 것만 믿었다.

- 내가 직접: 모듈 크기·import 그래프·같은 이름의 헬퍼·문서 배치·고아 문서·CI 쌓임 검사.
- 부하 에이전트(읽기 전용): controller·server·store·state·roles·report·run·readiness 전부와 core 요약. 11개 지적.
- Codex(gpt-6-astra, medium, 읽기 전용; 보고서 원문은 저장소에 올리지 않고 요약만 여기 적는다): 전체 저장소. 10개 지적.

셋이 같이 짚은 것: 상위 호출 관문 복사, 자리 모듈의 검증 함수·`.replace()` 바꿔치기, run→server 배선 의존, 죽은 상수, 살아 있는 문서의 낡은 상태. 한쪽만 짚은 것은 내가 코드로 확인한 뒤 골랐다.

## 3. 고친 것 (PR #155)

| 무엇 | 전 | 후 |
|---|---|---|
| 상위 자리 답 검사 | refine·next_step·split·collate·cross_review·synthesis 여섯 곳에 같은 `_text`/`_list`, 같은 경계 블록 f-string, `str(exc).replace("synthesis", …)`로 오류 문구 바꿔치기 | [`app/reply.py`](../../../app/reply.py) 하나(boundary·block·json_object·check_text·check_items·failed_reply). 자리마다 자기 오류 종류와 주어를 넘긴다 |
| 서버·헤드리스 배선 | `app.run`이 `app.server`(HTTP 서버 모듈)를 import해 참여자 명단·실행기 조립을 빌려 씀 | [`app/wiring.py`](../../../app/wiring.py)로 옮기고 둘이 같이 쓴다. `pid_of`는 모르는 adapter를 codex로 바꾸지 않고 명단에서 찾는다 |
| 상위 호출 관문 | 다듬기·제안·분담·모으기·교차검토가 같은 네 검사를 각자, 순서도 제각각 | `Controller._upper_call_gate()` 하나(한 번에 하나 → 멈춤·종료 미확인 → 자리 → 진행 중 실행), `_cli_card()`로 "설정된 CLI 카드" 검사 |
| 자리 투영 | 제안·모음·분담·다듬기·검토 투영이 같은 네 칸 카드와 결과 꼬리를 손으로 복사 | `_card()`·`_seat_result()` |
| 빙 도는 곳 | `create_run`이 `prepare_run`이 막 검사한 자료를 다시 검사, `pump`가 대기 참여자마다 합성 이력을 다시 읽음, 교차검토 투영이 view가 이미 읽은 초안을 다시 조회 | 한 번 검사해 넘기고(`checked=`), 한 번 읽어 넘기고, 이미 읽은 것을 넘긴다 |
| 흩어진 상수 | `("cancelled_before_start", "process_failed_to_start")` 리터럴 셋, roles의 `"cli"` 리터럴, store의 `PRAGMA table_info` 일곱 번 | `state.NOT_STARTED`, `CLI`, `Store._columns()` |
| 죽은 것 | `runner.STATES`, `contract.KINDS`, controller의 안 쓰는 `DONE` import, `check_setup.cli_row`의 안 읽는 인자, assemble의 안 쓰는 `import os` | 지움 |
| 검사 도구의 JSON 로더 | validate_sources·validate_v02·validate_design·check_frontier_protocol이 각자 중복 키·비표준 상수 거절 로더 | [`tools/strict_json.py`](../../../tools/strict_json.py) 하나 |
| 살아 있는 문서 | README의 2026-09-22 기준 "현재" 문단·V04-03 준비 중 문장·인계 6절과 겹치는 검사 목록, 버전 지도·v0.4 개요가 날짜 박힌 HANDOFF를 "완료 결과와 다음 작업"으로 안내, core/README가 옛 Codex 권한 경계(auth.json만 금지), app/README·next_step docstring의 "교차검토는 아직 없는 단계", tools/w2 README의 "최신 관측"(2026-09-25) | 지금 맞는 말만 남기고 상태는 [NEXT-SESSION.md](../../../NEXT-SESSION.md)로 링크 |

줄 수: 29개 파일 +147/−418, 새 모듈 셋 220줄. 동작·API·원장 스키마·참여자 계획(argv)은 바뀌지 않았다 — 판(revision)이 그대로라 재관측이 필요 없다.

## 4. 일부러 두는 것과 이유

- **합성이 여섯째 상위 자리인데 자기 생명주기(사건 기반)를 따로 가진다**(부하 지적 3). `_Seat` 표 기반과 합쳐야 한 곳이 되지만 원장 스키마·복구·자리 세기가 함께 바뀌는 큰 일이다. 지금 두 경로는 각자 시험돼 있고 어긋난 동작을 찾지 못했다. 필요해지면 카드로 연다.
- **`core/membership.py`의 `decide`·`advance`는 시험만 쓴다**(부하 지적 7). `app/state.gate`가 수동 답 정책 때문에 자기 관문을 갖는다는 이유가 `state.py` 머리에 적혀 있고, AGENTS.md가 v0.3 기반을 보존하라고 한다. 지우지 않았다. 같은 지적의 작은 어긋남 — `state.gate`는 phase `"synthesis"`를 공개로 보지만 `report.py`는 `"revealed"`만 받는다 — 은 스키마 4 이전 원장에만 해당하고 지금 코드는 `"synthesis"`를 쓰지 않는다. 그대로 둔다.
- **server의 긴 elif 사다리**(부하 지적 10). 라우팅 표로 바꾸면 보기 좋지만 동작 이득이 없고 시험이 많이 묶여 있다.
- **refine()과 _approved_refinement()의 비슷한 검사**(부하 지적 6). 문구가 상황별로 다르고(새로 다듬으세요 / 같은 승인으로 두 번 만들지 않습니다) 합치면 그 차이가 사라진다.
- **자리 밖 조사 문서** `docs/research-2026-09-22/`·`docs/research-notes-2026-09-21.md`. 고치면 안 되는 날짜 기록들이 그 경로로 링크하고 VALIDATION이 그 경로의 blob SHA를 적어 두었다. 옮기지 않는다.
- **`core.adapters`의 `BILLING_VARS`·`KEEP_VARS`·`child_env` 재노출**은 시험만 쓴다(Codex). 주석이 이유를 적고 `resolve`는 실제 사용처가 있다.
- **`app/README.md`(약 33,000자)**는 크지만 앱 사용 안내라 내용은 살아 있다. 이번에는 낡은 문장 하나만 고쳤다. 크기 상한을 두려면 협업 규칙 7절대로 정한다.
- **"JSON만" 지시를 CLI 스키마 출력으로**는 [프롬프트 감사](../2026-09-29-prompt-audit/README.md) F1 그대로 미룸.

## 5. 검증

- Windows Python 3.12: `python -m unittest discover -s tests` 750개 — OK(Linux 전용 격리 시험 64개 skip, 통과 아님). `python -m compileall -q app core tools tests`, `tools/check_encoding.py`, `validate_design.py`·`validate_v02.py`·`validate_sources.py`·`check_frontier_protocol.py`·`validate_design_tokens.py` 직접 실행 모두 통과.
- 전체 시험 한 번에서 `test_app_integrity`의 HTTP 경계 시험이 `WinError 10053`(소켓 중단)으로 오류 났고, 그 파일만 따로 세 번 돌리면 모두 통과했다 — Windows 소켓 흔들림으로 본다(인계 6절의 Windows 러너 주의와 같은 종류). 서버 변경은 import 이동뿐이다.
- 실제 CLI로 돌리지 않았다. 참여자 argv·판이 그대로라 재관측은 필요 없고, 다음 실제 실행이 상위 자리 다섯을 한 번씩 지나면 관문 통합의 실제 확인이 된다.
