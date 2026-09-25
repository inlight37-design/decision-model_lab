# 협업 규칙 — 여러 AI 세션이 같은 저장소를 고칠 때

이 저장소는 사용자 한 명과 여러 AI 세션(Claude, Codex, ChatGPT 등)이 번갈아 고친다. 각 세션은 서로의 대화를 보지 못하고 **저장소만 공유한다.** 그래서 어긋남은 대부분 같은 방식으로 생겼다.

| 실제로 있었던 어긋남 | 원인 | 이제 막는 장치 |
|---|---|---|
| 검사 수가 문서마다 71·74·75·112로 달랐다 | 여러 문서에 같은 숫자를 손으로 적음 | 살아 있는 문서에 개수 금지 — CI 검사 |
| 원장이 F29까지 늘었는데 범위 표기는 F24에서 멈춘 문서가 남았다 | 범위 검사가 일부 문서·en dash만 봄 | 모든 살아 있는 문서, hyphen까지 — CI 검사 |
| main의 인계 문서가 열린 PR의 작업을 몰랐다 | 인계를 PR 밖에서 따로 갱신 | 인계는 작업과 **같은 PR**에서 갱신, 열린 작업 절 필수 |
| 루트에 인계 파일이 둘 | 새 판을 쓰며 옛 판을 옆에 둠 | 인계는 루트에 하나, 옛 판은 [`docs/handoff/`](handoff/README.md) |
| "`validate()`가 계산한다"는 과장이 원본에 남음 | 다른 AI가 검토 문서에서만 정정 | 정정은 **원본에서**, 정정 사실은 기록에 |
| 웹 세션이 사용자 PC 사실을 "이력"으로 격하 | 접근 범위가 세션마다 다름 | 사실마다 출처 등급, PR에 접근 범위 명시 |

## 1. 역할

- **사용자**가 방향을 정하고 **main 병합을 결정한다.**
- **AI 세션**은 브랜치에서 작업하고 PR로 제안한다. 사용자가 그 세션에서 명시적으로 지시하지 않으면 main에 직접 push하지 않는다. 예외는 하나다: CI 녹색을 확인한 claude 세션은 끝난 작업을 main에 병합해도 된다(사용자 허락, [`NEXT-SESSION.md`](../NEXT-SESSION.md) 2절 8).
- 한 PR은 한 주제다. 서로 다른 일을 한 PR에 섞으면 병합 판단을 할 수 없다.

### GitHub이 유일한 공유 지점이다

웹 채팅 세션(예: ChatGPT 웹)은 사용자 PC를 보지 못하고 **GitHub만 본다.** 로컬에만 있는 커밋·결과·결정은 그 세션에게 없는 것과 같다. 그래서:

- **커밋하면 바로 브랜치를 push한다.** 작업 단위를 로컬에 쌓아 두지 않는다.
- **끝난 작업은 CI 녹색을 확인한 뒤 지체 없이 main에 병합한다.** 웹 세션은 보통 main의 `NEXT-SESSION.md`부터 읽는다. main이 낡으면 그 세션은 낡은 전제로 일한다.
- **병합 전의 작업은 `NEXT-SESSION.md` 3절에 브랜치 이름으로 적는다.** 그 브랜치를 병합하기 직전 커밋에서 그 줄을 지운다 — 병합 뒤 main에서 읽어도 맞는 문장만 남긴다. 그 인계 갱신 자체도 main에 들어가야 웹 세션이 본다 — 3절을 고친 커밋이 병합되기 전이면 웹 세션에게 브랜치 이름을 직접 알려 준다.
- **사용자 PC에서만 관측할 수 있는 결과**(CLI 버전, 로그인 상태, 실행 기록)는 AI 세션이 저장소 파일로 옮겨 push해야 웹 세션이 쓸 수 있다.
- 웹 세션에 일을 넘길 때는 저장소 링크, 읽을 브랜치, 시작 파일(`NEXT-SESSION.md`)을 함께 준다.
- **ChatGPT의 플러그인은 닿는 범위를 넓힌다(2026-09-25).** GitHub 플러그인을 붙이면(`+` 버튼 또는 `@GitHub`) ChatGPT가 이슈를 읽고 댓글을 단다 — [카드 #59](https://github.com/inlight37-design/decision-model_lab/issues/59)에서 확인했다. 말로만 해도 설치된 도구를 고르지만 붙이는 쪽이 확실하다. ChatGPT 데스크톱 앱의 컴퓨터 조작(Computer Use)·브라우저 플러그인은 사용자 PC의 화면과 브라우저를 직접 다룬다. 그렇게 쓴 세션은 "GitHub만 본다"가 아니므로 접근 범위(2절 4)에 표면과 붙인 플러그인을 적고, 사용자 PC 규칙(인증 값을 읽지 않기, 띄운 것 끄기)을 따른다. 쓰기 권한이 생겨도 병합 규칙(5절)은 그대로다. [플러그인 기록](reviews/2026-09-25-plugin-surface/README.md).

## 2. 세션을 시작할 때

1. `git fetch --all --prune` 후 현재 브랜치와 `git status`를 확인한다.
2. **열린 PR과 병합되지 않은 원격 브랜치를 확인한다** (`git branch -r --no-merged origin/main`, GitHub의 PR 목록). [`NEXT-SESSION.md`](../NEXT-SESSION.md)의 "진행 중인 작업" 절과 다르면 인계 문서가 낡은 것이다. 실제 상태를 기준으로 한다.
3. `NEXT-SESSION.md` → [`AGENTS.md`](../AGENTS.md) 순서로 읽는다. 과거 문서 전체를 prompt에 넣지 않는다.
4. **이 세션의 접근 범위를 적어 둔다.** 사용자 PC인가(어느 기기인가), 웹 컨테이너인가, CLI가 설치·로그인돼 있는가, GitHub만 보는가. PR 본문에 옮긴다.
5. 다른 세션의 열린 PR과 같은 파일을 고칠 예정이면 **그 브랜치 위에서 시작하거나 병합을 기다린다.** 남의 브랜치에 직접 push하지 않는다. 그 브랜치 위에서 시작해도 **PR은 main을 대상으로 연다.** PR의 대상을 그 브랜치로 하면, 그 브랜치의 PR이 병합될 때 브랜치 자동 삭제로 이 PR이 닫힐 수 있다(2026-09-24 PR #19). **쌓인 브랜치들에 같은 수정이 필요하면 가장 아래 브랜치에 한 번 커밋하고, 위 브랜치는 그것을 병합으로 받는다.** 층마다 따로 커밋하면 위 브랜치가 아래 브랜치의 head를 품지 않아, 순서대로 병합할 때 인계 문서가 충돌한다(2026-09-24 PR #22–#24, [병합 기록](reviews/2026-09-24-merge-22-25/README.md)).

## 3. 작업하는 동안

**브랜치 이름**은 `<agent>/<주제>-<YYYYMMDD>`다. `agent`는 `claude`, `codex`, `chatgpt`, `agy`, `human` 중 하나. 누가 무엇을 하는지 브랜치 목록만 보고 알 수 있어야 한다.

**커밋**은 작업 단위마다 한다. 제목은 `type: 무엇을` (`feat`/`fix`/`docs`/`test`/`ci`/`chore`), 본문은 왜.

**사실의 출처를 구분한다.**

| 등급 | 뜻 | 적는 법 |
|---|---|---|
| 관측 | 이 세션이 직접 실행하거나 읽어서 확인 | 명령·파일·commit을 함께 |
| 문서 | 공식 문서·원문에서 읽음 | URL·locator·확인일. 실제 동작은 미확인 |
| 전달 | 다른 세션·AI가 적은 것 | 그대로 옮겨 적지 않는다. 확인했으면 관측으로, 못 했으면 "전달, 미확인" |

환경 사실(설치 버전, 로그인 상태, 로컬 경로)은 **그 기기에서 관측한 세션만** 적는다. 접근하지 못한 세션은 "미확인"이라고 쓰고, 기존 기록을 이력으로 격하하거나 지우지 않는다.

**다른 세션의 주장을 정정할 때**

- 틀린 문장은 **원본 파일에서** 고친다. 검토 문서에만 적으면 원본을 읽는 다음 세션이 다시 틀린다.
- 무엇이 왜 틀렸는지 커밋 본문과 해당 기록(검토 문서의 정정 절, 또는 인계 문서)에 남긴다. 조용히 덮어쓰지 않는다.
- 날짜가 박힌 기록은 고치지 않는다(아래 4절). 그 목록 README에 단서를 단다.
- 두 세션의 판단이 근거로 갈리지 않으면 둘 다 남기고 `unresolved`로 둔다. 이 프로젝트의 원칙과 같다 — 합의는 검증이 아니다.

**숫자를 다시 적지 않는다.** 살아 있는 문서에 검사 수·원장 건수·commit 수를 쓰지 않는다. 기준은 CI 로그와 원장 파일이다. 원장 범위는 `F01–F<마지막 번호>` 형태로 적으면 CI가 실제 원장과 대조한다. 그 시점의 숫자가 꼭 필요하면 commit SHA(40자)와 같은 줄에 적는다 — CI는 그 줄을 이력으로 본다.

**근거 원장(`sources.json`)에는** 1차 출처를 직접 읽은 경우만 추가한다. 검토 문서 안의 참조 ID(`R01` 등)나 절차서의 출처 표는 원장 항목이 아니다.

**디자인(`design/`)은 claude.ai 아티팩트와 1:1이다.** 아티팩트는 Claude 세션만 발행할 수 있다. 다른 세션이 `design/`을 고쳤다면 PR과 인계 문서에 "아티팩트 미동기화"라고 적어 다음 Claude 세션이 맞추게 한다.

**비밀 값**(API 키, 토큰, 인증 파일 내용, 환경변수 전체 출력)은 어떤 형태로도 커밋하지 않는다.

**쓰기 권한이 있는 workflow로 코드를 들이지 않는다.** 파일을 직접 고치기 어려운 세션(웹 세션 등)은 변경을 patch 파일(`git diff` 결과)로 자기 브랜치에 올리고 PR 본문에 적는다. 그러면 PC 세션이 적용해 커밋하고, 커밋 본문에 원래 작성 세션을 밝힌다. `contents: write` workflow가 대신 커밋하면 세 가지가 깨진다. 작성자가 `github-actions[bot]`으로 남아 누가 썼는지 흐려진다. bot 토큰으로 push한 커밋에는 CI가 돌지 않는다. 그리고 검토 없이 브랜치를 바꾸는 통로가 하나 생긴다. 2026-09-24 PR #34가 이 방식을 썼다([기록 N4](reviews/2026-09-24-live-pilot-replication/README.md)).

**인코딩.** Windows PowerShell 5.1의 `Get-Content`/`Set-Content`로 문서를 일괄 치환하지 않는다. [`AGENTS.md`](../AGENTS.md)의 경고를 따른다.

## 4. 문서의 두 종류

| 종류 | 파일 | 규칙 |
|---|---|---|
| **살아 있는 안내** | `README.md`, `AGENTS.md`, `NEXT-SESSION.md`, 이 문서, `docs/architecture/README.md`, v0.4 `README.md`, `docs/reviews/README.md`, `docs/handoff/README.md`, `design/README.md` | 항상 현재 기준. 개수 금지, 원장 범위는 실제와 일치. CI 검사 대상(`tests/test_research_integrity.py`의 `LIVING_DOCS`) |
| **날짜가 박힌 기록** | `docs/reviews/*`, `docs/handoff/*`, `docs/experiments/*`, v0.4 `FINAL_REVIEW`·`EVIDENCE_FOLLOWUP`·`REVIEW_FIXES`·`VALIDATION`·`HANDOFF`(2026-09-22 판) | 그 시점 그대로 둔다. 틀린 곳은 새 기록이나 목록 README에서 정정 |

새 살아 있는 문서를 만들면 `LIVING_DOCS`에 추가한다.

## 5. 세션을 끝낼 때

1. 검사를 실행한다 — 명령은 [`NEXT-SESSION.md`](../NEXT-SESSION.md)의 검사 절.
2. **`NEXT-SESSION.md`를 같은 PR 안에서 갱신한다.** 절 구성은 고정이고 CI가 확인한다. **3절에는 진행 중인 일과 마지막 병합 하나만 둔다** — 자기 PR을 "마지막 병합"으로 적고 이전 것은 지운다. 이력은 PR 목록과 git이 갖는다. 이력을 쌓으면 인계가 커지고, 동시에 일하는 세션끼리 같은 줄에서 충돌한다(2026-09-25 PR #68·#69·#74, 줄이기 전 판은 원문의 약 세 배). 통째로 새로 쓰면 이전 판을 `docs/handoff/YYYY-MM-DD-<사유>.md`로 옮긴다.
3. PR 본문의 [템플릿](../.github/pull_request_template.md)을 채운다 — 작성 세션, 접근 범위, 검증한 것과 하지 않은 것.
4. PR을 연 뒤 **PR의 CI**를 확인한다. CI는 PR(main과 합친 결과)과 main에서만 돈다 — PR을 열기 전에 돌려 보려면 Actions 탭에서 `offline-checks`를 손으로 실행한다. **녹색을 보기 전에는 "통과"라고 적지 않는다.**
5. 병합은 사용자가 하거나, CI 녹색을 확인한 claude 세션이 한다(`NEXT-SESSION.md` 2절 8).
6. **병합된 PR의 브랜치는 GitHub이 지운다**(저장소 설정 "Automatically delete head branches", 2026-09-25 확인). 병합한 쪽이 따로 지우지 않는다. **`gh pr merge --delete-branch`는 쓰지 않는다** — 그 브랜치가 이 PC의 다른 worktree에 checkout돼 있으면 gh(2.101)가 **그 worktree를 지우려 한다.** 2026-09-25 PR #69 병합에서 다른 claude 세션의 worktree 파일이 지워졌다(그 세션의 커밋은 모두 main에 있었고 세션은 이미 보관돼 잃은 것은 없었다). PR 없이 main에 들어간 브랜치처럼 남은 것은 [`prune-merged-branches`](../.github/workflows/prune-merged-branches.yml)(Actions, 손으로만 돈다)로 지운다. `dry_run`을 켜면 지울 목록만 보인다. 실행할 수단이 없는 세션은 PR에 적고, 사용자가 GitHub 웹(Actions 탭 → prune-merged-branches → Run workflow)에서 돌리거나 PC에서 아래 명령을 돌린다(Git Bash나 WSL, 저장소 루트). 어느 쪽이든 main에 모두 들어간 브랜치만 지운다. 목록을 가져온 뒤 누가 push한 브랜치는 `--force-with-lease`가 거절한다 — 다시 돌리면 새로 판정한다.

   ```bash
   git fetch --all --prune
   git branch -r --merged origin/main | sed 's/^ *//' | grep -v -e '^origin/main$' -e '^origin/HEAD' | sed 's#^origin/##' | xargs -r git push --force-with-lease origin --delete
   ```

## 6. 이 규칙을 지키게 하는 장치

| 장치 | 무엇을 막는가 |
|---|---|
| `.githooks/pre-commit` | BOM·깨진 UTF-8이 커밋에 들어가는 것 (`git config core.hooksPath .githooks`) |
| CI `offline-checks`(PR·main·손으로) | 인코딩, 살아 있는 문서의 개수·원장 범위, 인계 문서 절 구성, 상대 링크, 원장 계약, 모든 테스트 |
| PR 템플릿 | 접근 범위·미검증 범위·인계 갱신 누락 |
| 저장소 설정: 병합된 PR 브랜치 자동 삭제 | 병합된 브랜치가 원격에 쌓여 진행 중인 일이 가려지는 것 |
| Actions `prune-merged-branches`(손으로 실행) | 자동 삭제가 닿지 않은 브랜치(PR 밖에서 main에 들어간 것 등) — main에 모두 들어간 브랜치만 지운다 |
| [`CLAUDE.md`](../CLAUDE.md) | Claude Code가 `AGENTS.md`를 자동으로 읽게 한다. 규칙은 `AGENTS.md` 한 곳에만 쓴다 |
