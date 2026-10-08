# 합본(실제 합성) 품질 평가 — 사전 등록 (2026-10-08)

[인계](../../../NEXT-SESSION.md) 1절이 "합성이 품질을 올린다는 근거는 아직 없다"고 적은 질문에 같은 기준의 답을 낸다. **첫 모델 호출 전에 이 폴더를 커밋하고 push한다.** 결과를 본 뒤 이 파일과 [questions.json](questions.json), [answers.json](answers.json), [rubric.md](rubric.md), [evaluate.py](evaluate.py)를 바꾸지 않는다. 결과는 같은 폴더의 `RESULTS.md`에 따로 쓴다.

작성: claude 세션(웹 컨테이너, 브랜치 `claude/project-thread-tlfcdm`, 기준 main `128e4b8`). 사용자 PC는 보지 않았고 CLI도 보지 않았다. 실제 호출은 주 PC `main-pc-wsl`에서 한다. 이 컨테이너에서는 bubblewrap을 설치하고 `evaluate.py run --mock`으로 여덟 과제가 모두 공개까지 도는 것, 그리고 가짜 답을 넣어 `grade`·`pack`·`analyze`가 도는 것을 확인했다(모델 호출 없음).

## 묻는 것

1. **합본이 더 좋은 단독 답보다 나은가.** 과제 8개 점수 합이 더 높은 provider 하나와 비교한다. "한 모델만 쓸까, 호출을 네 배 쓸까"에 맞는 비교다.
2. **합본이 맞는 초안을 잃는가.** 과제마다 두 초안 중 나은 점수(사후 최선)와 비교한다.
3. **합성자가 제 계열 초안에 기우는가.** 같은 초안에 Codex 합성과 Claude 합성을 붙여 비교한다.

앞선 비교([D](../2026-09-24-comparison-pilot/RESULTS.md), [D 후속](../2026-09-25-d-followup/RESULTS.md), [L1](../2026-09-25-l1/RESULTS.md))과 다른 점: 정답 대부분을 스크립트가 채점하고, 두 합성자를 모든 과제의 같은 초안에 붙이고, 결정 규칙을 미리 정한다. 앞선 질문은 다시 쓰지 않는다.

## 조건

과제마다 헤드리스 실행 한 번(`python -m app.run`)이다. strict(`independent-only`, 최소 2명), 참여자 `claude,codex`, Codex `gpt-6-luna`·Claude `claude-sonnet-5`, 관측 기록 [main-pc-wsl manifest](../../reviews/2026-09-26-main-pc-observe/manifest.v2.json), 빈 입력 폴더, 공통 자료 없음, 제한 시간 180초.

| 조건 | 무엇 | 호출 |
|---|---|---|
| S-codex | Codex 초안(봉인 안에서 혼자 쓴 답) | 1 |
| S-claude | Claude 초안 | 1 |
| 대조표 | 모델 없는 발췌 대조(`--synthesize mock`) | 0 |
| X-codex | Codex가 두 초안을 합친 합본 | 1 |
| X-claude | Claude가 두 초안을 합친 합본 | 1 |

- `--synthesize mock,<순서>`로 부른다. 홀수 과제는 `codex,claude-code`, 짝수 과제는 `claude-code,codex` 순서다. 두 번째 합성에 첫 합성 결과는 들어가지 않는다(`app.synthesis.model_prompt`). 이름표 순서는 앱이 실행마다 섞고 결과의 `labels`에 남는다.
- 대조표는 결론을 내지 않는 형식이라 채점하지 않고 결과에만 남긴다.

## 과제와 정답

질문 글은 [questions.json](questions.json)이다. Q1–Q6은 마지막 줄에 `답: <값>`을 쓰라고 하고, 정답은 [answers.json](answers.json)이며 `evaluate.py check-key`가 코드로 다시 계산해 대조한다.

| 과제 | 종류 | 정답 |
|---|---|---|
| Q1 | 3^1000의 마지막 다섯 자리 | 20001 |
| Q2 | 세 아이 중 화요일생 남아가 있을 때 셋 다 남아일 확률 | 127/547 |
| Q3 | 튜플 안 목록에 `+=` | `오류 ([1, 2, 3], 3)` |
| Q4 | 같은 반복자 셋을 `zip` | `3 끝` |
| Q5 | 이분 탐색 경계 오류의 반환값 | `1, 3, 0` |
| Q6 | 같은 시간대 aware datetime 빼기(서머타임 시작일) | `2:00:00` |
| Q7 | 탈퇴 삭제 30일과 1년 WORM 백업의 충돌 | [rubric.md](rubric.md) 0–5 |
| Q8 | 회의록의 증가율 모순 | [rubric.md](rubric.md) 0–5 |

## 채점

- **Q1–Q6 자동 채점**(`evaluate.py grade`). 초안은 마지막 `답:` 줄을 정답과 비교한다(공백·백틱·굵게 표시만 무시). 합본은 권고와 주장 문장에서 `답:`을 찾고, 없으면 정답 값과 틀린 초안의 값 가운데 무엇이 나오는지 본다. 하나만 나오면 그것으로 판정하고, 둘 다 나오거나 둘 다 없으면 "사람 확인"이다. 갈리는 점·반례·미해결 칸은 판정에 쓰지 않는다.
- **사람 확인 답과 Q7·Q8**은 `evaluate.py pack`이 만든 blind 묶음으로 이 세션(Claude 계열)이 채점한다. 이름표는 무작위, 모델·회사 이름은 `[가림]`, 합본은 인용 없이 합성자가 쓴 문장만 싣는다. 대응표 `key.json`은 묶음 밖에 두고, 채점 JSON을 커밋·push한 뒤에야 연다. 사람 확인 답의 판정은 `correct`·`wrong`·`held`(결론 보류) 가운데 하나이고 이유를 한 줄 적는다.
- **모델 채점자는 쓰지 않는다.** D 후속에서 읽기 오류 둘과 180초 초과가 있었다.
- 점수: Q1–Q6은 맞음 1·그 밖 0, Q7·Q8은 합/5. 실패한 합성과 빠진 답은 0이다.

## 지표

`evaluate.py analyze`가 합성자마다 낸다.

- **합계**: 조건마다 8과제 점수 합. 비교 기준은 S-codex·S-claude 중 높은 합.
- **갈린 과제**: 두 초안 점수가 다른 과제.
- **이득**: 합본 점수가 두 초안보다 모두 높은 과제. **손실**: 합본 점수가 나은 초안보다 낮은 과제(보류·실패 포함).
- **형식 실패**: 합성이 검사를 통과하지 못한 과제.
- 함께 적는 것: 보류율, 틀린 설명의 전이(사람이 묶음에서 본 것), 인용 원문 일치(`checks`), 이름표 자리, 시간·CLI 보고 토큰.

## 결정 규칙

합성자 둘을 따로 판정한다.

1. 갈린 과제가 3개 미만이면 **판단 불가**. 같은 질문을 반복하지 않고 더 어려운 과제로 새로 등록한다.
2. 이득 2개 이상, 손실 0, 형식 실패 1번 이하, 합계가 더 좋은 단독 답 이상이면 **권고 후보**: "두 초안이 갈릴 때 이 합성자를 쓴다". 기본 켬은 이 표본만으로 바꾸지 않는다.
3. 손실이 1개 이상이고 이득이 없으면 **기본 끔 유지**, 화면에서 원문 대조표를 앞에 두는 쪽을 권한다.
4. 그 밖은 **미확립**으로 적고 어느 쪽으로도 일반화하지 않는다.

이번 PR에서는 앱 코드를 바꾸지 않는다. 권고는 결과 기록과 인계에만 쓴다.

## 실행 순서·상한·멈춤

주 PC WSL(`Ubuntu-24.04`)의 로그인 셸에서, 이 브랜치를 사용자 clone과 따로 받은 폴더에서 돌린다(앱 아이콘이 쓰는 clone은 건드리지 않는다).

```bash
python3 -m app.registration status docs/reviews/2026-09-26-main-pc-observe/manifest.v2.json
R=~/.local/state/dml-synth-eval-20261008
python3 docs/experiments/2026-10-08-synthesis-eval/evaluate.py check-key
python3 docs/experiments/2026-10-08-synthesis-eval/evaluate.py configs --root $R
python3 docs/experiments/2026-10-08-synthesis-eval/evaluate.py run --root $R
python3 docs/experiments/2026-10-08-synthesis-eval/evaluate.py grade --root $R
python3 docs/experiments/2026-10-08-synthesis-eval/evaluate.py pack --root $R --out $R/blind
```

- **상한**: 과제마다 새 원장, Codex 2·Claude 2. 전체 최대 Codex 16·Claude 16. 구독 CLI만 쓴다. 승인은 인계 2절 22와 이 스레드의 사용자 선택("실제 호출까지", 2026-10-08)이다.
- **멈춤** (`run`이 스스로 멈춘다): 과제마다 시작 전 Codex 계정 조회(모델 호출 없음)가 실패하거나 어느 창이든 80% 이상, 헤드리스 종료 코드가 0이 아님(준비 조회 거절 포함), 참여자가 수용되지 않음, 종료 미확인 시도, 합성 시작 거절, 원장의 Claude 한도 상태가 `allowed`가 아님.
- 원장 폴더가 이미 있는 과제는 다시 부르지 않는다. 형식 실패한 합성도 다시 부르지 않는다. 멈춘 뒤 이어서 할지는 원인을 기록한 뒤 남은 과제만 정한다.
- 끝나면 `app.run`·`codex`·`claude`·`bwrap` 프로세스가 남지 않았는지 확인한다. 서버는 띄우지 않는다.

## 기록하는 것

공개(이 폴더): `RESULTS.md`, 채점 JSON(점수·판정·이유 한 줄), `key.json`(이름표 → 과제·조건), `analysis.json`, 실행 요약(`run-log.jsonl`, 답 원문 없음). 계정 한도는 수치 없이 멈춤 기준 아래였는지만 적는다.

저장소 밖(`~/.local/state/dml-synth-eval-20261008/`): 원장, 결과 JSON, 답 원문, blind 묶음, 계정 조회 원본.

## 알려진 한계

- 과제 8개, 조건마다 한 번이다. 큰 차이만 보이고 통계적 결론이 아니다. 같은 초안을 다시 돌릴 때의 흔들림은 재지 않는다.
- 두 강한 모델이 대부분 맞히면 갈린 과제가 적어 판단 불가로 끝날 수 있다(규칙 1).
- Q7·Q8과 사람 확인 답의 채점자는 Claude 계열 한 세션이고 과제를 만든 쪽이다. 판정의 무게는 자동 채점에 둔다.
- 질문이 `답:` 줄을 요구하므로 평소 질문과 모양이 다르다. 합성 질문(앱의 고정 프롬프트)은 `답:`을 요구하지 않아, 합본은 자동 판정이 덜 된다.
- Codex는 답한 모델을 보고하지 않는다(K32). 두 참여자의 문맥 독립성은 [E2](../../reviews/2026-09-25-context-independence/README.md)의 범위다.
- 원본 앱 답, 일반 팀원 흐름(GR-3 취합)은 범위 밖이다.
