# 합본 재평가 — 사전 등록 (2026-10-08)

[첫 평가](../2026-10-08-synthesis-eval/RESULTS.md)는 판단 불가였다. 두 초안이 갈린 과제가 하나뿐이었고, 합성 16번 가운데 4번이 형식 실패였다. 그 뒤 [PR #190](https://github.com/inlight37-design/decision-model_lab/pull/190)이 합성 형식을 고쳤다(질문의 출력 형식 지시를 따르지 않게 하고, 인용의 escape 누락을 고쳐 읽는다). 이번에는 더 어려운 새 과제로 두 가지를 한 번에 묻는다. **첫 모델 호출 전에 이 폴더를 커밋하고 push한다.** 결과를 본 뒤 이 파일과 [questions.json](questions.json), [answers.json](answers.json), [rubric.md](rubric.md), [evaluate.py](evaluate.py)를 바꾸지 않는다. 결과는 같은 폴더의 `RESULTS.md`에 따로 쓴다.

작성: claude 세션(웹 컨테이너, 브랜치 `claude/synthesis-reeval-v5we3j`, 기준 main `2e47554`). 사용자 PC와 CLI는 이 문서를 쓸 때 보지 않았다. 실제 호출은 주 PC `main-pc-wsl`에서 한다. 이 컨테이너에서는 `check-key`와 가짜 답으로 `grade`·`format`의 판정을 확인했다(모델 호출 없음).

## 묻는 것

1. **형식 수정이 통했나.** 합성 16번 가운데 형식 실패가 몇 번인가. 첫 평가는 4번이었다.
2. **합본이 더 좋은 단독 답보다 나은가, 맞는 초안을 잃는가, 합성자가 제 계열에 기우는가.** [첫 평가](../2026-10-08-synthesis-eval/README.md)의 1–3과 같다.

첫 평가와 다른 점은 셋이다. 과제를 새로 만들었다(첫 과제는 다시 쓰지 않는다). 모든 과제에 정답 값이 있어 스크립트가 채점한다(첫 평가의 서술형 Q7·Q8은 모든 답이 만점이라 변별력이 없었다). 형식 실패를 따로 센다(`evaluate.py format`). 모델, 조건, 상한, 멈춤 조건, 결정 규칙은 그대로다.

## 조건

과제마다 헤드리스 실행 한 번(`python -m app.run`)이다. strict(`independent-only`, 최소 2명), 참여자 `claude,codex`, Codex `gpt-6-luna`·Claude `claude-sonnet-5`, 빈 입력 폴더, 공통 자료 없음, 제한 시간 180초. 관측 기록은 실행하는 날 주 PC에 등록된 main-pc-wsl 기록이다(아래 "관측 기록").

| 조건 | 무엇 | 호출 |
|---|---|---|
| S-codex | Codex 초안(봉인 안에서 혼자 쓴 답) | 1 |
| S-claude | Claude 초안 | 1 |
| 대조표 | 모델 없는 발췌 대조(`--synthesize mock`) | 0 |
| X-codex | Codex가 두 초안을 합친 합본 | 1 |
| X-claude | Claude가 두 초안을 합친 합본 | 1 |

합성 순서는 홀수 과제 `codex,claude-code`, 짝수 과제 `claude-code,codex`다. 두 번째 합성에 첫 합성 결과는 들어가지 않는다. 이름표 순서는 앱이 실행마다 섞는다.

## 과제와 정답

질문 글은 [questions.json](questions.json), 정답은 [answers.json](answers.json)이다. `evaluate.py check-key`가 질문 글 안의 코드를 그대로 실행하거나(Q1–Q4) 따로 계산해(Q5–Q8) 대조한다. 모두 마지막 줄에 `답: <값>`을 쓰라고 한다.

| 과제 | 종류 | 정답 | 고른 이유 |
|---|---|---|---|
| Q1 | 클래스 본문의 리스트 컴프리헨션이 클래스 변수를 보는가 | `이름 오류` | 3.12의 컴프리헨션 인라인(PEP 709) 뒤에도 클래스 범위는 보이지 않는다 |
| Q2 | `True`·`1`·`1.0` 키를 가진 dict | `{True: 'c'} 1` | 키는 처음 것, 값은 마지막 것 |
| Q3 | `round`와 `.2f` 서식의 반올림 | `2.67 -2 0.12 0.38` | 이진 표현과 짝수 반올림이 섞인다 |
| Q4 | SQLite의 `NOT IN`과 NULL | `0, 2, 2` | `NOT IN`과 `NOT EXISTS`가 NULL에서 갈린다 |
| Q5 | 2026!을 12진법으로 쓸 때 끝의 0 | `1009` | 2의 몫(1009)과 3의 몫(1010)이 하나 차이다 |
| Q6 | 2026 이하에서 두 양의 제곱수의 차로 쓰이는 수 | `1517` | 1과 4가 빠지는 경계 |
| Q7 | 2026–2035년의 13일의 금요일 | `17` | 10년치 요일 계산 |
| Q8 | 주사위 합이 처음 10 이상이 될 때 정확히 10일 확률 | `17492167/60466176` | 손으로 하는 점화식 |

두 모델이 갈릴지는 미리 알 수 없다. 첫 평가보다 손 계산과 경계 사례가 많은 과제를 골랐을 뿐이다. 참여자가 봉인 안에서 코드를 실행해 답을 확인하는지는 이 등록에서 통제하지 않는다.

## 채점

- **자동 채점**(`evaluate.py grade`). 초안은 마지막 `답:` 줄을 정답과 비교한다(공백·백틱·굵게 표시만 무시). 합본은 권고와 주장 문장에서 `답:`을 찾고, 없으면 정답 값과 틀린 초안의 값 가운데 무엇이 나오는지 본다. 숫자 값은 앞뒤가 숫자가 아닐 때만 나온 것으로 센다(정답 17이 2017에 들어 있다고 보지 않는다). 하나만 나오면 그것으로 판정하고, 둘 다 나오거나 둘 다 없으면 "사람 확인"이다. 갈리는 점·반례·미해결 칸은 판정에 쓰지 않는다. PR #190 뒤의 합성은 `답:` 줄을 쓰지 않으므로 합본은 대부분 값으로 판정된다.
- **사람 확인**은 `evaluate.py pack`이 만든 blind 묶음으로 이 세션(Claude 계열)이 [rubric.md](rubric.md)대로 `correct`·`wrong`·`held` 가운데 하나를 고른다. 이름표는 무작위, 모델·회사 이름은 `[가림]`, 합본은 인용 없이 합성자가 쓴 문장만 싣는다. 대응표 `key.json`은 묶음 밖에 두고, 채점 JSON을 커밋·push한 뒤에야 연다.
- 모델 채점자는 쓰지 않는다. 점수는 맞음 1·그 밖 0이다. 실패한 합성과 빠진 답은 0이다.

## 지표와 결정 규칙

`evaluate.py analyze`의 지표(합계, 갈린 과제, 이득, 손실, 형식 실패)와 합성자별 결정 규칙은 [첫 평가](../2026-10-08-synthesis-eval/README.md)의 "지표"·"결정 규칙"과 같다. 줄이면: 갈린 과제가 3개 미만이면 판단 불가, 이득 2개 이상·손실 0·형식 실패 1번 이하·합계가 더 좋은 단독 답 이상이면 권고 후보, 손실만 있고 이득이 없으면 기본 끔 유지, 그 밖은 미확립이다. 기본값은 이 표본만으로 바꾸지 않는다.

형식 수정의 판정(`evaluate.py format`)은 따로 낸다.

- 합성 16번이 모두 불렸고 형식 실패가 1번 이하면 **형식 수정이 통했다**고 적는다.
- 형식 실패가 2번 이상이면 **통하지 않았다**고 적고, 실패마다 원인을 저장소 밖의 원문(`raw`)에서 확인해 종류만 적는다.
- 고쳐 읽은 곳(`checks.format_repairs`)과 백슬래시로 되돌려 찾은 인용(`checks.backslash_matches`)의 수를 함께 적는다. 고쳐 읽은 합성은 수정이 있어서 통과한 것이다.
- 멈춤 조건으로 16번을 다 부르지 못하면 판정하지 않고 부른 만큼만 적는다.

## 관측 기록

main-pc-wsl 기록([2026-09-26](../../reviews/2026-09-26-main-pc-observe/manifest.v2.json))은 2026-10-27부터 만료다. 실행 전에 주 PC에서 `python3 -m app.registration status`와 `python3 tools/setup/check_setup.py`로 등록·CLI 판을 본다.

- 등록이 유효하고 판이 관측 판과 같으면 그 기록으로 이 평가를 돌리고, 끝난 뒤 [SETUP 4절](../../SETUP.md)의 절차로 다시 관측해 별도 PR로 올린다.
- 판이 바뀌었거나 등록이 무효면 먼저 다시 관측·등록하고(별도 PR), 그 새 기록을 `configs --manifest`로 준다. 어느 기록을 썼는지 `RESULTS.md`에 적는다.

## 실행 순서·상한·멈춤

주 PC WSL(`Ubuntu-24.04`)의 로그인 셸에서, 이 브랜치를 사용자 clone과 따로 받은 폴더에서 돌린다(앱 아이콘이 쓰는 clone은 건드리지 않는다).

```bash
python3 -m app.registration status docs/reviews/2026-09-26-main-pc-observe/manifest.v2.json
E=docs/experiments/2026-10-08-synthesis-reeval
R=~/.local/state/dml-synth-reeval-20261008
python3 $E/evaluate.py check-key
python3 $E/evaluate.py configs --root $R          # 새 기록이면 --manifest <새 기록>
python3 $E/evaluate.py run --root $R
python3 $E/evaluate.py grade --root $R
python3 $E/evaluate.py format --root $R
python3 $E/evaluate.py pack --root $R --out $R/blind
# 사람 확인 답이 있으면 채점 JSON을 커밋·push한 뒤 key.json을 연다. 없으면 빈 {}를 쓴다
python3 $E/evaluate.py analyze --root $R --manual <채점 JSON> --key $R/blind/key.json
```

- **상한**: 과제마다 새 원장, Codex 2·Claude 2. 전체 최대 Codex 16·Claude 16. 구독 CLI만 쓴다. 승인은 인계 2절 22와 사용자의 "나머지 다 일시키면" 요청(2026-10-08, 이 프로젝트 스레드)이다.
- **멈춤** (`run`이 스스로 멈춘다): 과제마다 시작 전 Codex 계정 조회(모델 호출 없음)가 실패하거나 어느 창이든 80% 이상, 헤드리스 종료 코드가 0이 아님(준비 조회 거절 포함), 참여자가 수용되지 않음, 종료 미확인 시도, 합성 시작 거절, 원장의 Claude 한도 상태가 `allowed`가 아님.
- 원장 폴더가 이미 있는 과제는 다시 부르지 않는다. 형식 실패한 합성도 다시 부르지 않는다. Codex 창 때문에 멈추면 창이 초기화된 뒤 남은 과제만 이어 간다.
- 끝나면 `app.run`·`codex`·`claude`·`bwrap` 프로세스가 남지 않았는지 확인한다. 서버는 띄우지 않는다.

## 기록하는 것

공개(이 폴더): `RESULTS.md`, `grades-auto.json`, 사람 확인 채점 JSON(있으면), `key.json`, `analysis.json`, `format.json`(실패 이유는 이름을 가린 앞 300자), 실행 요약 `run-log.jsonl`(답 원문 없음). 계정 한도는 수치 없이 멈춤 기준 아래였는지만 적는다.

저장소 밖(`~/.local/state/dml-synth-reeval-20261008/`): 원장, 결과 JSON, 답 원문, blind 묶음, 계정 조회 원본.

## 알려진 한계

- 과제 8개, 조건마다 한 번이다. 큰 차이만 보이고 통계적 결론이 아니다.
- 두 모델이 다시 거의 같은 답을 내면 판단 불가로 끝난다(규칙 1). 둘 다 틀린 과제도 갈린 과제가 아니다.
- 정답이 값 하나라서 "합본이 맞는 값을 골랐는가"만 본다. 설명의 질, 반례를 남겼는지는 채점하지 않는다.
- 사람 확인 채점자는 과제를 만든 Claude 계열 한 세션이다. 판정의 무게는 자동 채점에 둔다.
- Codex는 답한 모델을 보고하지 않는다(K32). 두 참여자의 문맥 독립성은 [E2](../../reviews/2026-09-25-context-independence/README.md)의 범위다.
