# 작업 카드 시범 — GitHub 이슈 (2026-09-25)

작성: claude 세션(Claude 데스크톱 앱, `aux-pc` Windows). 기준 main `c83ee3f`(PR #57 병합).

**보는 것:** 사용자가 AI 사이에서 글을 옮기지 않아도, 여러 AI 세션이 GitHub 이슈의 "카드"에서 일을 찾아 이어받을 수 있는지. [여러 AI 작업 방식 조사](../../research/multi-ai-workflow-2026-09-25/README.md)와 [후속 검토](../../reviews/2026-09-25-workflow-evaluation/README.md), [#56 병합 검토](../../reviews/2026-09-25-merge-56/README.md)가 모두 권한 "작은 카드 시범"이다. 시범이므로 운영 규칙([AGENTS.md](../../../AGENTS.md))은 바꾸지 않는다. 인계([NEXT-SESSION.md](../../../NEXT-SESSION.md))는 보드를 가리키기만 한다.

## 사용자 결정 (2026-09-25)

- 카드는 GitHub 이슈로 해 봐도 된다. 저장 공간이 꼭 필요하면 Google Drive도 써도 된다.
- Claude Code Projects: claude.ai 채팅 쪽에는 Projects가 보이지만 Code 쪽에는 보이지 않는다(사용자 확인). 채팅 쪽 Projects는 대화와 파일을 묶는 예전 기능이라 스레드·조정자가 없다. [공식 문서](https://code.claude.com/docs/en/claude-projects)는 Code Projects를 클라우드 세션을 써 봤고 채팅·Cowork에 기존 프로젝트가 없는 계정부터 푼다고 적는다. 그래서 Projects 시험은 지금 할 수 없다. 대기자 등록은 사용자가 원할 때 직접 한다.

## 보드 규칙

| 무엇 | 어떻게 |
|---|---|
| 카드 | `card` 라벨이 붙은 이슈 하나. 새 카드는 [카드 양식](../../../.github/ISSUE_TEMPLATE/card.md)으로 만든다 — 목표, 범위(하지 않는 것도), 완료 조건, 입력, 모델 호출 상한, 체크포인트 |
| 상태 | 라벨은 하나만: `status: ready`(누구든), `status: in-progress`(한 세션이 잡음), `status: needs-user`(사용자의 선택·전달 필요), `status: review`(PR 열림) |
| 담당 | 모든 세션이 같은 GitHub 계정을 쓰므로 담당자 칸 대신 `agent: claude`·`agent: codex`·`agent: chatgpt` 라벨 |
| 가져가기 | `status: in-progress`가 없는지 먼저 본다. 상태·담당 라벨을 바꾸고 세션·기기·브랜치를 댓글로 남긴다. 두 세션이 겹치면 먼저 댓글을 단 쪽이 갖고 다른 쪽은 물러나며 겹친 일을 기록한다 |
| 멈추거나 넘길 때 | 커밋을 먼저 push한다. 체크포인트 댓글(마지막 원격 커밋, 한 일, 다음 행동, 근거, 남은 질문)을 남기고 `status: ready`나 `status: needs-user`로 되돌린다 |
| 끝낼 때 | PR 본문에 `Closes #번호`. 병합되면 이슈가 닫힌다. 닫힌 이슈에 근거(PR·CI) 댓글 |
| 세션이 바뀌면 | 같은 카드·브랜치·PR을 이어 간다. 세션마다 새 카드나 PR을 만들지 않는다 |
| 보기 | `gh issue list --label card`. 상태를 확인하려고 모델을 부르지 않는다 |
| 공개 저장소 | 인증 값, 원장 원문, 계정 식별자, 개인 정보를 이슈에 적지 않는다 |

인계 문서에는 카드와 같은 현황을 다시 적지 않는다. 기존 규칙(브랜치·PR, CI 녹색 뒤 병합, 호출마다 상한과 기록)은 그대로다.

## 시작할 때의 카드

| 카드 | 종류 | 시작 상태 | 이 카드로 보는 것 |
|---|---|---|---|
| [#58](https://github.com/inlight37-design/decision-model_lab/issues/58) 준비 조회 거절의 종료 코드 분리 | 변경 | 진행, claude | 한 세션이 구현하고 Codex CLI가 읽기 전용으로 검토한다 — 사용자 중계 없는 한 바퀴 |
| [#59](https://github.com/inlight37-design/decision-model_lab/issues/59) ChatGPT 웹의 이슈 읽기·댓글 | 조사 | 사용자, chatgpt | 사용자 한 번 전달로 ChatGPT 웹이 보드에 닿는가 |
| [#60](https://github.com/inlight37-design/decision-model_lab/issues/60) D 후속 비교 | 실험 | 누구든 | 다음 세션이 카드와 인계만 보고 재설명 없이 시작하는가 |
| [#61](https://github.com/inlight37-design/decision-model_lab/issues/61) 공통 자료 합계 1 MiB | 실험 | 누구든 | 우선순위가 낮은 일이 보드에 남아 잊히지 않는가 |

## 판정 기준 — 사전 등록

결과를 보기 전에 적는다. 효과를 수치로 증명하려는 것이 아니라 지금 방식보다 편한지 보는 것이다.

1. **사용자 중계:** 카드마다 사용자가 AI 사이에 글을 옮긴 횟수. 변경 카드는 0, #59는 1 이하.
2. **이어받기:** 다른 세션이 #60이나 #61을 카드와 인계만 보고, 사용자의 재설명 없이 시작한다.
3. **중복 없음:** 같은 카드를 두 세션이 동시에 잡지 않는다.
4. **검토 왕복:** 변경 카드는 교차검토 1회와 지적 해결 확인으로 끝난다.
5. **호출:** 카드의 상한 안에서만 부르고, 상태 확인용 호출은 0이다.
6. **불편하면 줄인다:** 시범이 지금 방식보다 불편하면 기능을 더하지 않고 카드와 규칙을 줄인다.

끝: 네 카드가 닫히거나 사용자가 그만하자고 할 때. 채택 여부는 사용자가 정한다.

## 결과

카드가 끝날 때마다 한 줄씩 더한다.

| 카드 | 사용자 중계 | 이어받기 | 교차검토 | 모델 호출 | 메모 |
|---|---|---|---|---|---|
| [#58](https://github.com/inlight37-design/decision-model_lab/issues/58) 준비 조회 거절 종료 코드 | 0 | 해당 없음(한 세션이 끝냄) | 1회. 지적 둘(`--check-config` 거절 시험 누락 — 중간, 보관된 옛 안내의 "거절 2" — 낮음)을 모두 반영했고 다시 검토하지 않았다 | Codex 1(WSL `codex exec`, `gpt-6-luna`, 읽기 전용·연결 앱 끔·세션 저장 안 함, 42초, 추론 강도는 CLI 기본값 none). 검토 사본은 GitHub에서 새로 받은 해당 브랜치였고, 실행 기록에서 명령은 저장소 안의 `git`·`rg`뿐이었다. 첫 시도는 로그인 셸이 아니라 `codex`를 찾지 못해 시작 전에 끝났다(모델 호출 없음) | 구현 세션이 놓친 경로를 교차검토가 찾았다. 반대로 이 세션은 전체 시험 실패 하나를 push 뒤에야 봤다 — 결과를 `tail`로 걸러 종료 상태를 놓쳤다. 로컬 검사는 종료 상태를 직접 본다 |
| [#59](https://github.com/inlight37-design/decision-model_lab/issues/59) ChatGPT 웹의 이슈 읽기·댓글 | 1 — 사용자가 요청문을 ChatGPT에 한 번 붙여 넣었다. 결과도 채팅으로 전해 주었지만 댓글이 GitHub에 남아 있어 그 전달은 필요하지 않았다 | 해당 없음 | 해당 없음 | 앱·CLI 호출 없음(사용자의 ChatGPT 사용) | 사용자에 따르면 ChatGPT에 GitHub 플러그인을 붙인 상태(`+` 버튼 또는 `@GitHub`)였다. ChatGPT가 `card` 이슈 #59·#60·#61을 읽고 #59에 "읽음: #59, #60, #61" 댓글을 남겼다(07:00 UTC, GitHub에서 확인). **이슈 보드는 ChatGPT에도 닿는다 — GitHub 플러그인을 붙이는 것이 조건이다.** 계정 플러그인이 앱의 Codex 참여자에게 닿는지는 [플러그인 기록](../../reviews/2026-09-25-plugin-surface/README.md)에서 따로 봤다(지금은 닿지 않음, 보강은 [카드 #64](https://github.com/inlight37-design/decision-model_lab/issues/64)) |
| [#60](https://github.com/inlight37-design/decision-model_lab/issues/60) D 후속 비교 | 0 | **예.** 카드를 만든 세션과 다른 claude 세션이 카드와 인계만 보고 시작했다(사용자는 보드 규칙대로 가져가라고만 했다). 모자랐던 정보: ① 실행 설정(provider·모델·manifest·빈 입력 폴더)을 어디에 어떻게 만드는지 카드·인계에 없어 옛 상태 폴더를 보고 따라 만들었다 ② 드라이버에 단독(S) 조건이 없어 더했다 ③ 합성 이름표가 참여자 ID 순이라 D1이 늘 Claude라는 점은 코드를 읽고 알았다(실험 설계의 한계가 됐다) ④ WSL 로그인 셸 함정은 #58 기록에만 있어 같은 실수를 했고, Git Bash가 `/mnt/c/...` 인자를 바꾸는 일(`MSYS_NO_PATHCONV=1`로 막음)은 어디에도 없었다. ①④는 인계 6절에 더했다 | 해당 없음(실험 카드) | Codex 8·Claude 5 — 사전 등록 상한 13 그대로, 상태 확인용 0 | 사전 등록(`86fc5ee`) → 실행 → 이 세션의 blind 채점 커밋(`173d6f7`) → 대응표 공개 순서를 git 이력에 남겼다. 모델 채점은 Claude 채점자가 180초를 넘겨 공개되지 않았다([결과](../2026-09-25-d-followup/RESULTS.md)). 같은 시간에 다른 claude 세션이 #59·#64·PR #65를 진행했다. 겹친 파일(인계·이 표)은 main을 병합해 합쳤고 카드가 달라 충돌은 없었다. 후속은 [카드 #66](https://github.com/inlight37-design/decision-model_lab/issues/66) |
| [#66](https://github.com/inlight37-design/decision-model_lab/issues/66) 합성 실패 원문·이름표 순서 | 0 | **예.** #60 세션은 PR #67 병합 뒤 앱 설정(`auto_archive_on_close`)으로 자동 보관됐고, 사용자는 세션이 지워진 줄 알았다. 새 claude 세션이 GitHub(PR·미병합 브랜치·카드 라벨·카드 댓글)과 인계만으로 상태를 되살렸고, 사용자가 "이어서 하면 되나"고 묻자 카드만 보고 시작했다(재설명 없음). 카드 체크포인트에 남은 설계 결정 하나(무작위냐 실행 ID냐)를 바로 정할 수 있었다 | 1회. **지적 없음** — 추론 강도가 CLI 기본값 none이라 약한 근거다. 이 세션이 스스로 본 것: 고립 surrogate가 원장 쓰기를 깨뜨리는 길(원문을 `\uXXXX`로 바꿔 막음), 옛 사건 호환, Windows에서 Python이 쓴 CRLF(저장소 규칙이 LF로 바꿔 커밋에는 없음) | Codex 1(WSL `codex exec`, `gpt-6-luna`, 읽기 전용·연결 앱 끔·`--ephemeral`, 88초). 검토 사본은 GitHub에서 새로 받은 브랜치였고 명령은 `git`·`nl`·`sed`·`rg`뿐, 사본은 바뀌지 않았다. 상태 확인용 0 | 칩으로 따로 띄운 다른 claude 세션(Windows 시험 흔들림)과 같은 시간에 진행했다. 이 PC에는 Node가 없어 화면 JavaScript 시험은 CI에서만 돌았다 |
| [#70](https://github.com/inlight37-design/decision-model_lab/issues/70) 고립 surrogate로 실행이 멈춤 | 0 | 해당 없음(카드를 만든 세션이 정리 작업 중에 가져감) | ChatGPT 외부 검토(#75)가 이 카드의 범위를 넓혔다(R05: 메타데이터·저장 예외 종결) — 카드와 검토가 같은 보드에서 이어졌다. 코드 교차검토는 따로 하지 않았다 | 0 | 카드 본문의 재현 방법 그대로 먼저 재현하고 고친 뒤 같은 스크립트로 다시 확인했다. 사용자가 카드용 작업 칩을 누르기 전에 이 세션이 가져가 칩을 거뒀다 |
| [#71](https://github.com/inlight37-design/decision-model_lab/issues/71) 관측 기록을 기기와 묶기 | 0 | 해당 없음(카드를 만든 세션이 정리 작업 중에 가져감) | 설계는 ChatGPT 외부 검토(#75) R06의 로컬 등록안을 따랐다 — 카드가 적은 두 후보(이름표 대조·공개 해시)보다 나은 안을 검토가 냈다 | 0 | 실제 기록을 이 기기에 등록해 거절→허가를 모델 없이 확인했다. 재관측은 새 카드 #82로 나눴다 |
| [#64](https://github.com/inlight37-design/decision-model_lab/issues/64) Codex 참여자의 계정 플러그인 | 0 | 해당 없음(정리를 마친 세션이 보드 순서대로 가져감) | 카드의 두 안 가운데 (a)를 골랐다 — 합성 대조가 연결 앱 끄기의 빈틈을 보여 줬고, 실행마다 조회하는 (b)보다 장치가 적다 | 0 | 카드가 적은 키(`features.remote_plugin`)로는 막히지 않았다. 문서에 없는 `features.plugins`를 대조로 확인했다. 재관측은 #82 |

## 한계

- 같은 GitHub 계정이라 누가 라벨을 바꿨는지 GitHub 기록으로 가를 수 없다. 댓글에 세션을 적는 규칙에 기댄다.
- 가져가기는 원자적이지 않다 — 두 세션이 동시에 라벨을 붙이면 둘 다 붙는다. 세션 수가 적어 댓글 규칙으로 충분하다고 보고, 겹치면 기록한다.
- ChatGPT 웹이 이슈를 읽고 쓸 수 있는지는 #59 전까지 모른다. 안 되면 ChatGPT 웹에는 지금처럼 저장소 파일로 전한다.
- 이슈는 저장소 파일과 달리 CI 검사를 받지 않는다.
- Google Drive는 쓰지 않았다. 이슈와 저장소로 충분했고, 이 세션에는 드라이브 연결 도구가 없다.
