# handoff — 지난 인계 문서 보관

현재 인계는 루트의 [`NEXT-SESSION.md`](../../NEXT-SESSION.md) **하나뿐**이다. 이 폴더는 교체된 인계 문서를 원문 그대로 보관한다.

| 파일 | 무엇 | 교체한 곳 |
|---|---|---|
| [`2026-09-23-before-review.md`](2026-09-23-before-review.md) | MCP·UI 검토([PR #3](https://github.com/inlight37-design/decision-model_lab/pull/3)) 전의 전체 인계. 환경, 사용자 결정, 디자인 규칙, 생태계 표 | PR #3이 루트에 날짜를 붙여 보존했고, 인계 파일을 하나로 두기 위해 이 폴더로 옮겼다 |
| [`2026-09-23-after-mcp-ui-review.md`](2026-09-23-after-mcp-ui-review.md) | PR #3 세션이 쓴 인계. MCP·UI 검토의 정정 사항과 다음 실행 순서 | 협업 규칙의 고정 절 구성으로 새로 쓰면서 옮겼다. 정정 사항은 새 인계와 [검토 기록](../reviews/2026-09-23-mcp-ui-runtime/README.md)에 이어진다 |
| [`2026-09-23-before-consolidation.md`](2026-09-23-before-consolidation.md) | 경계 리뷰, WSL2 이전, W2, WSL2 리뷰(PR #6) 반영, A1을 차례로 덧붙인 인계. 병합 목록이 길어지고 끝난 항목과 남은 항목이 4절에 섞였다 | 지금 상태·한계·다음 일만 두도록 통째로 다시 쓰면서 옮겼다. 한계와 못 고친 문제는 새 인계 4절의 한 표(K 번호)로 모았다. 이 판 4절 "지금 단계"의 "controller와 화면이 없다"는 A1 병합 뒤 낡은 문장이다(1절의 같은 문장은 옮기기 전에 정정했다) |
| [`2026-09-23-before-v04-03-cleanup.md`](2026-09-23-before-v04-03-cleanup.md) | 2026-09-23 하루 동안 PR #4·#5 반영, V04-03 실행 코어, 첫 conformance를 차례로 덧붙인 인계. 4절에 시간순 논의와 이미 끝난 항목이 섞여 있다 | 남은 일을 A(바로)·B(승인 뒤)·C(사용자 결정)·D(알려진 문제)·E(급하지 않음)로 다시 짜면서 옮겼다. 이 판의 5번 항목 "실제 CLI로는 아직 돌리지 않았다"는 옮기기 전에 이미 낡은 문장이었다(같은 날 conformance에서 실제로 돌렸다) |
| [`2026-09-23-before-stage2.md`](2026-09-23-before-stage2.md) | A1 리뷰 반영, 사용자 결정(Q5·Q6·C2), 1단계 N1–N6을 차례로 덧붙인 인계. 4절에 N0–N6 항목별 경위(무엇을 했고 무엇을 시험했는지)가 있고, 3절의 병합 이력이 한 문단으로 길어졌다 | 1단계를 마친 뒤 새 세션이 2단계(승인된 모델 호출)부터 이어받도록 통째로 다시 쓰면서 옮겼다. 2단계 절차를 명령 단위로 적고, 열린 PR #8(tmux 조사)을 3절에 넣었다. 이 판은 PR #8을 모른다 |
| [`2026-09-24-before-a1-integrity.md`](2026-09-24-before-a1-integrity.md) | main `28a18676842f31cd25a0629b2efdc8c3686b46df`의 전체 인계. 2단계·후속 리뷰·브랜치 정리 이력과 상세 K 표 | PR #18의 A1 모의 후속 뒤 현재 상태/다음 작업 중심으로 정리하면서 원문 바이트를 보관했다. 기존 관측·사용자 결정은 유지했고 K18·K27·K42 부분 진행과 새 PR은 현재 인계가 기준 |
| [`2026-09-24-before-cli-unblock.md`](2026-09-24-before-cli-unblock.md) | main `16646b3`(PR #37 병합)의 인계 원문. 구현 순서 5–7, 사용자 판단 표, 한계와 정리 후보 목록이 있다 | PR #38(ChatGPT 웹)이 인계를 다시 쓰면서 옮겼다. 사용자 결정·금지 사항은 유지. 색인 행은 PR #39 병합 검토에서 채웠다 |
| [`2026-09-24-before-cli-unblock-app.md`](2026-09-24-before-cli-unblock-app.md) | 같은 main의 `app/README.md` 원문 — 인계가 아니라 app 안내다. 단일 `--live-cli` 실측 기준 | PR #38이 app 안내를 provider별 설정 기준으로 다시 쓰면서 옮겼다. 색인 행은 PR #39 병합 검토에서 채웠다 |
| [`2026-09-24-before-windows-live-completion.md`](2026-09-24-before-windows-live-completion.md) | PR #38 인계 원문. Windows 패치 적용·계정 조회·실제 병렬 응답 전 상태 | PR #39에서 사용자 결정·금지 사항을 유지하며 현재 상태를 갱신했다 |
| [`2026-09-24-before-merge-39-next-steps.md`](2026-09-24-before-merge-39-next-steps.md) | PR #39(codex) 인계 원문. 3절이 #39를 진행 중으로 적은 병합 전 상태 | #39 병합 뒤 claude 세션이 0·1·3·4·6절을 병합 뒤 상태와 구체적인 다음 작업(A–F)으로 다시 쓰면서 옮겼다. 2·5절은 그대로 |

## 규칙

이번 최신 보관본은 위 `2026-09-24-before-merge-39-next-steps.md`다. 표에 행이 없는 이전 보관본 [`2026-09-24-before-post-merge-verification.md`](2026-09-24-before-post-merge-verification.md)는 main `eec60e93ef6c95639181eb8cd251506c16290075`의 인계를 병합 재검토·실제 브라우저·K46 관측 뒤 축소하면서 바이트 그대로 보관했다. 사용자 결정과 금지 사항은 현재 인계에도 유지했다. 이 보관본의 K46 미관측·브라우저 미검증 표현은 [후속 기록](../reviews/2026-09-24-post-merge-verification/README.md)이 갱신한다.

- **바이트 그대로 둔다.** 내용을 고치지 않는다. 틀린 내용이 있으면 현재 `NEXT-SESSION.md`나 해당 검토 기록에서 정정한다. 무엇이 틀렸는지도 기록이다.
- **링크는 저장소 루트 기준으로 작성됐다.** 원래 루트에 있던 파일이라 이 폴더에서 열면 상대 링크가 맞지 않는다. 같은 이유로 링크 회귀 검사는 이 폴더를 건너뛴다.
- `NEXT-SESSION.md`를 통째로 새로 쓸 때만 이전 판을 `YYYY-MM-DD-<사유>.md`로 이 폴더에 옮긴다. 부분 갱신은 Git 이력으로 충분하다.
