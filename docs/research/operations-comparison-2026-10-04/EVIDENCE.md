# 근거·범위·검증 기록

관측일 2026-10-04. 접근 범위는 Linux 클라우드 컨테이너와 GitHub다. 사용자 PC, Windows/WSL launcher, 로그인된 Codex/Claude CLI, 유료 모델/API, 외부 제품 계정은 이번에 관측하지 않았다. 공개 source/docs만 읽고 모델 없는 작은 probe를 실행했다. 제품 코드·설정·기능 기본값은 수정하지 않았다.

## 고정 소스

| 대상 | commit | 전체 tracked 경로 | 라이선스 관측 |
|---|---|---:|---|
| [tmux](https://github.com/tmux/tmux/tree/e476c1230b958df0cb12977517d24b3dc931375b) | `e476c1230b958df0cb12977517d24b3dc931375b` | 326 | COPYING 및 각 파일 고지; 일괄 MIT로 표시하지 않음 |
| [Beads](https://github.com/steveyegge/beads/tree/2f1e8be3ca1fe990727858ccd8e4a78461b39c7c) | `2f1e8be3ca1fe990727858ccd8e4a78461b39c7c` | 4,325 | root LICENSE, MIT |
| [Backlog.md](https://github.com/MrLesk/Backlog.md/tree/69e7b15362337d6712783d9a685f6e4bb693fa9d) | `69e7b15362337d6712783d9a685f6e4bb693fa9d` | 1,346 | root LICENSE, MIT |
| [Gas Town](https://github.com/gastownhall/gastown/tree/649b832b7672bc7a2dbef26f5983aba6198b819b) | `649b832b7672bc7a2dbef26f5983aba6198b819b` | 1,563 | root LICENSE, MIT |
| [Cline](https://github.com/cline/cline/tree/39ff2359f7e08231281539696e48a166ce49270c) | `39ff2359f7e08231281539696e48a166ce49270c` | 4,179 | root LICENSE identifies Apache-2.0 |
| [Lite-Harness](https://github.com/LiteLLM-Labs/lite-harness/tree/dd99cfdfc68dbb6b3f7f986d54efd42572373a6c) | `dd99cfdfc68dbb6b3f7f986d54efd42572373a6c` | 89 | Python pyproject declares MIT; tracked LICENSE/COPYING 부재, 복사 허여/고지 미확정 |
| [Symphony](https://github.com/openai/symphony/tree/be10a1b79df723d6d7612b5651c8522704dafb2e) | `be10a1b79df723d6d7612b5651c8522704dafb2e` | 132 | root LICENSE identifies Apache-2.0 |

[source-map.json](source-map.json)은 읽은 파일의 고정 URL·SHA-256·줄 범위·인터페이스 검토 여부를 기록한다. `full`은 해당 파일 본문을 읽었다는 뜻이며 시스템 전체 실행 검증과 다르다. selected 범위, symbol/interface만 본 범위는 그 수준으로 적었다. 특히 Symphony SPEC은 heading inventory, Gas Town pidtrack은 symbol inventory다.

전체 경로별 파일 hash/크기/읽은 범위는 [tmux](inventory/tmux.tsv), [beads](inventory/beads.tsv), [backlog](inventory/backlog.tsv), [gastown](inventory/gastown.tsv), [cline](inventory/cline.tsv), [lite-harness](inventory/lite-harness.tsv), [symphony](inventory/symphony.tsv)에 있다. `git ls-files -z`로 추적 경로를 뽑았으며 대부분은 `inventory-only`다. 저장소를 빠짐없이 **찾아갈 지도**이지 모든 줄을 분석했다는 증거가 아니다. 상대 경로는 해당 upstream root 기준이다.

## 분석의 핵심 근거 연결

| 주장/비교축 | 원본 locator; 정확한 URL은 source-map | 확인 수준 |
|---|---|---|
| `%end`와 WAIT continuation 분리 | tmux `cmd-queue.c` 597–682, 730–835 | 소스 + T03 |
| client별 backpressure·출력 생략 | tmux `control.c` 435–584 | 소스만, stress 미실행 |
| 변경 없으면 subscription 알림 생략 | tmux `control.c` 859–879, 1042–1138 | 소스만 |
| screen은 raw stdout/stderr가 아님 | tmux `cmd-capture-pane.c` 200–290 | 소스 + T05 |
| claim CAS/동일 actor idempotence | Beads `issueops/claim.go` 1–210 | 선택 소스, Dolt 경쟁 미실행 |
| SQL commit 뒤 history commit 경계 | Beads `dolt/issue_operations_tx.go` | 전체 파일 읽기, 장애 주입 미실행 |
| missing/ambiguous dependency 차단 | Backlog `readiness.ts`, `task-record-index.ts` | 전체 파일 + B01–B03 |
| dependency cycle와 큰 ID | Backlog `dependency-graph.ts`, `task-id.ts` | 선택 소스 + B04–B05 |
| 실행 성공 뒤 후처리 실패 | Gas Town `capacity/dispatch.go` | 선택 소스, 실제 worker 미실행 |
| idle와 safe-to-delete 구별 | Gas Town `polecat/workstate.go` | 선택 pure policy 읽기 |
| checkpoint preimage와 rollback | Cline SDK `session/checkpoint-restore.ts` | 1–175; 파일 복원 미실행 |
| overflow mode의 deterministic fallback 설계 | Cline SDK `extensions/context/compaction.ts` | 선택 분기/설명, 전체 helper 미검증 |
| 빈 runtime에도 기본 success | Lite-Harness `session.mjs`, `protocol.mjs` | 전체 파일 + L01/L03/L04 |
| Codex 변환기의 event 누락 | Lite-Harness `providers/codex/transformation.mjs` | 전체 파일 + L05/L06 |
| workflow invalid reload 시 last-good 유지 | Symphony `workflow_store.ex` | 선택 소스, running server 미실행 |
| reconcile/claim/slot/retry 세대 | Symphony `orchestrator.ex` | 선택 소스, Linear/App Server 미실행 |

## 실제 실행한 작은 시험

### tmux 3.7c

공식 [release archive](https://github.com/tmux/tmux/releases/download/3.7c/tmux-3.7c.tar.gz)를 `/tmp`에 풀어 `--disable-utf8proc`로 빌드했다. Debian libevent/ncurses header와 bison package를 임시 prefix에 추출했다. 시스템 package install은 하지 않았다. 처음에는 권한 없는 apt update와 configure의 yacc 탐지가 실패했고, 임시 prefix를 PATH에 넣어 빌드했다. 인증 정보는 조회/저장하지 않았다.

archive hash는 [tmux-build.json](tmux-build.json), 실행 binary hash는 [tmux-probe-results.json](tmux-probe-results.json)에 있다. clone과 release에 공통으로 있는 tracked C 파일 190개가 byte 일치했고 차이는 없었다. generated parser/configure와 toolchain까지 동일한 재현 빌드를 증명한 것은 아니다.

[tmux-probes.py](tmux-probes.py)는 고유 임시 socket, `-f /dev/null`, 최소한의 기존 환경 키, bounded subprocess timeout을 사용한다. fixture는 sleep과 로컬 Python 출력뿐이다. 마지막에 서버를 kill하고 client 종료와 해당 socket의 `has-session` 실패를 확인한다.

```bash
python docs/research/operations-comparison-2026-10-04/tmux-probes.py /path/to/tmux-3.7c/tmux
```

T01–T08 통과: begin/end correlation, parse error block, WAIT receipt/continuation 구별, detach/reconnect/rename ID, 화면 overwrite와 stdout/stderr 합류, exit 7 dead pane, signal-before-wait, test server/client 정리. fixture 작성 중 visible screen에 첫 줄이 남지 않는 사례를 확인해 최종 시험은 `capture-pane -S -`로 history를 포함했다. 최종 결과 JSON은 수정 후 실행한 결과다.

한계: Linux cloud ASCII fixture. Windows/WSL, 한글/emoji 셀 폭, terminal multiplexing UI, 큰 출력/backpressure stress, 서버 crash 복구, 실제 모델 CLI, 전체 OS 자손 종료 증명은 시험하지 않았다.

### Backlog.md와 Lite-Harness

[probes.mjs](probes.mjs)는 upstream HEAD와 tracked worktree가 고정판인지 확인한 뒤 실제 모듈을 import한다. Backlog용 Markdown import는 Bun의 text import와 같은 역할로 문자열을 돌려주는 Node loader를 사용한다. upstream 함수를 재작성하거나 결과를 stub한 것은 아니다. Lite-Harness Session의 runtime만 의도적으로 가짜 iterator를 넣어 빈 출력/예외 경계를 시험한다.

```bash
node --experimental-transform-types docs/research/operations-comparison-2026-10-04/probes.mjs /path/to/research-sources
```

Node v24.19.0에서 B01–B06, L01–L06 통과. [결과 JSON](probe-results.json)에 각 assertion 목적이 있다. 초기 script의 Bun Markdown import 호환과 graph 호출 인자를 수정한 뒤 재실행했다. Bun 앱/브라우저/외부 SDK 동작 시험은 아니며 clone 경로를 준비해야 재현할 수 있다. 이 probe는 앱 runtime이나 CI 필수 도구로 등록하지 않는다.

## 공개 제품 자료

[public-source-manifest.json](public-source-manifest.json)은 공식 URL·2026-10-04 조회·HTML/text hash·추출 길이를 담는다. script/style을 제외한 HTML text 중 관련 본문을 읽었다. Conductor workflow/cloud/diff, Jules getting started, Kiro specs, Cursor 2.0, Amp Neo, Copilot cloud agent, Devin managed sessions, Jev compaction/Fusion benchmark가 대상이다. hash는 조회한 페이지 식별용이며 원문 자체가 영구 보존되거나 사실이 검증됐다는 뜻은 아니다. 동적 navigation과 본문 변경으로 hash는 달라질 수 있다.

Jules 첫 fetch는 압축된 응답을 UTF-8로 직접 해석해 실패했고 `curl --compressed`로 다시 받아 성공했다. 실패를 서비스 접근 불가로 오인하지 않았다. 업체 수치는 업체 보고로만 적었고 검색 결과 snippet을 코드 검증 증거로 사용하지 않았다.

## 우리 저장소 검증과 남은 한계

문서·근거 파일·조사용 probe만 추가하고 navigation/인계를 연결했다. 상대 링크/인코딩/쌓임 규칙과 기존 오프라인 검사를 실행한다. 최종 head의 실제 CI 상태와 링크는 [PR #159](https://github.com/inlight37-design/decision-model_lab/pull/159)가 관리한다. 이 문서를 먼저 썼다는 이유로 아직 보지 않은 CI를 통과라고 기록하지 않는다.

이 컨테이너의 이전 기준 실행에서는 PID 1의 자손 회수 방식 때문에 `test_children_left_behind_are_counted_and_ended`가 `unknown != exited`로 실패했다. 이번 최종 검사 결과도 PR에 구별해 기록하며, 문서 작업에서 이를 숨기려고 runner/test를 바꾸지 않는다. 격리 도구/OS 차이로 skip된 항목을 성공으로 세지 않는다.

모델 품질, 실제 사용자 편의 향상, 라이선스 법률 검토, 제품 보안, 분산 정확히 한 번 실행, source 전체 감사는 이번 결과가 보장하지 않는다. OP 적용 조각을 고른 뒤 그 계약에 맞춰 필요한 시험 범위를 확장한다.
