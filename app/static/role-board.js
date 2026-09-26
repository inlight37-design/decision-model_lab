"use strict";
// A 단계 화면만의 상태. 저장된 작업·역할은 /api/state에서 받으며 브라우저에 보관하지 않는다.
const ROLE_LABELS = { supervisor: "슈퍼바이저", orchestrator: "오케스트레이터", isolated: "팀원(격리)", general: "팀원(일반)" };
const TASK_LABELS = { working: "작업 중", my_turn: "내 차례", done: "끝남", problem: "문제" };
let roleOptions = null, roleBoard = null, chosenCard = null, previewRequest = null, composeTask = null;
let previewGeneration = 0;
let taskSelected = new URLSearchParams(location.search).get("task"), taskPageSig = null;

function emptyBoard() { return { supervisor: [], orchestrator: [], isolated: [], general: [], input_mode: "original" }; }
function placeRole(board, pid, slot) {
  if (!Object.hasOwn(ROLE_LABELS, slot)) return board;
  return { ...board, [slot]: board[slot].includes(pid) ? [...board[slot]] : [...board[slot], pid] };
}
function roleSummary(config) {
  if (!config) return "역할 구성 없음";
  const name = p => p ? p.label : "나";
  return `슈퍼바이저 ${name(config.supervisor)} · 오케스트레이터 ${name(config.orchestrator)} · 격리 ${(config.isolated || []).map(name).join(", ") || "없음"}` +
    (config.source === "legacy" ? " · 기존 실행" : "");
}
function boardWarnings(board, roster) {
  const warnings = [];
  if (board.supervisor.length) warnings.push("슈퍼바이저 모델은 D 단계에서 지원합니다.");
  if (board.general.length) warnings.push("팀원(일반)은 C 단계에서 지원합니다.");
  if (!board.isolated.length) warnings.push("격리 팀원을 한 명 이상 배치하세요.");
  if (board.orchestrator.length > 1) warnings.push("오케스트레이터는 한 장만 배치하세요.");
  const assigned = Object.keys(ROLE_LABELS).flatMap(slot => board[slot]).map(id => roster.find(p => p.pid === id));
  if (assigned.some(p => !p)) warnings.push("현재 명단에 없는 카드가 있습니다.");
  const known = assigned.filter(Boolean);
  if (new Set(known.map(p => p.provider)).size < known.length) warnings.push("같은 provider 두 장은 아직 지원하지 않습니다. provider당 한 장만 배치하세요.");
  if (board.orchestrator.some(id => roster.find(p => p.pid === id)?.transport === "manual"))
    warnings.push("A 단계 오케스트레이터는 CLI 합성자만 지원합니다. 원본 앱은 격리 칸에 놓으세요.");
  return warnings;
}
function invalidatePreview() {
  previewGeneration += 1;
  previewRequest = null;
  $("inputPreview").replaceChildren(); $("inputPreview").hidden = true;
}
function chooseRole(pid, slot) {
  if (!roleOptions.participants.some(p => p.pid === pid)) return;
  roleBoard = placeRole(roleBoard, pid, slot); chosenCard = null;
  invalidatePreview(); renderRoleBoard(); updateSourceNote();
  $("roleNotice").textContent = `${roleOptions.participants.find(p => p.pid === pid).label} → ${ROLE_LABELS[slot]}`;
  $("slot-" + slot).focus();
}
function renderRoleBoard() {
  const roster = roleOptions.participants;
  $("roleSlots").replaceChildren(...Object.entries(ROLE_LABELS).map(([slot, label]) => {
    const ids = roleBoard[slot], upper = ["supervisor", "orchestrator"].includes(slot);
    const place = h("button", { type: "button", id: "slot-" + slot, class: "role-target",
      "aria-label": label + " 칸에 선택한 카드 놓기", onclick: () => {
        if (chosenCard) chooseRole(chosenCard, slot);
        else $("roleNotice").textContent = "먼저 참여자 카드를 누른 뒤 칸을 누르세요.";
      }, ondragover: e => { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; },
      ondrop: e => { e.preventDefault(); chooseRole(e.dataTransfer.getData("text/role-card"), slot); }
    }, h("span", { class: "strong" }, label),
    h("span", { class: "cap muted" }, !ids.length ? (upper ? "나 · 직접 판단" : "카드를 놓으세요") : "카드 추가"));
    return h("div", { class: "role-slot cell" }, place,
      ids.map(pid => {
        const p = roster.find(p => p.pid === pid);
        return h("div", { class: "row between role-assignment" }, h("span", { class: "sm" }, p.label,
          p.transport === "manual" ? h("span", { class: "cap muted" }, " · 독립 미확인") : null),
        h("button", { type: "button", class: "btn", "aria-label": `${label}에서 ${p.label} 빼기`, onclick: () => {
          roleBoard = { ...roleBoard, [slot]: ids.filter(id => id !== pid) };
          invalidatePreview(); renderRoleBoard(); updateSourceNote(); $("slot-" + slot).focus();
        } }, "빼기"));
      }));
  }));
  $("roleWarnings").textContent = boardWarnings(roleBoard, roster).join(" ");
  for (const p of roster) $("card-" + p.pid).setAttribute("aria-pressed", String(chosenCard === p.pid));
  pressAll($("roleSlots"));
}
function roleCard(p, opt) {
  const kind = p.transport === "manual" ? "원본 앱 · 독립 미확인" : opt.live ? `실제 CLI · ${p.model}` : "모의 CLI · 모델 호출 없음";
  return h("div", { class: "cell role-card" },
    h("button", { type: "button", class: "role-pick", id: "card-" + p.pid, draggable: "true", "aria-pressed": "false",
      onclick: () => { chosenCard = chosenCard === p.pid ? null : p.pid; renderRoleBoard();
        $("roleNotice").textContent = chosenCard ? `${p.label} 선택됨. 배치할 칸을 누르세요.` : "선택을 해제했습니다."; },
      ondragstart: e => { e.dataTransfer.setData("text/role-card", p.pid); e.dataTransfer.effectAllowed = "copy"; }
    }, h("span", { class: "strong" }, p.label), h("span", { class: "cap muted" }, kind)),
    p.transport === "cli" && !opt.live ? h("select", { id: "b-" + p.pid, "aria-label": p.label + " 모의 행동" },
      opt.behaviors.map(b => h("option", { value: b }, BEHAVIOR_LABEL[b] || b))) : null);
}
function showInputPreview(preview, body) {
  previewRequest = { ...body, run_id: preview.run_id, confirmation: preview.confirmation };
  const calls = preview.calls, orchestrator = preview.role_config.orchestrator;
  $("inputPreview").hidden = false;
  $("inputPreview").replaceChildren(h("h3", { class: "block-title" }, "보낼 입력 확인"),
    h("p", { class: "sm strong" }, roleSummary(preview.role_config)),
    h("p", { class: "sm" }, `입력 모드: 원문 · ${preview.quorum_policy === "independent_only" ? "독립성이 확인된 참여자만" : "미확인 답도 포함"} · 최소 ${preview.min_independent}명`),
    h("p", { class: "sm" }, `이번 실행: CLI 시작 최대 ${calls.draft_cli}회 · 수동 답 ${Object.keys(preview.manual_packets).length}개`),
    h("p", { class: "sm" }, calls.model_calls === 0 ? "모의 모드 · 실제 모델 호출 상한 0" :
      `이 원장의 실제 호출 상한 ${calls.live_cap} · ${Object.entries(calls.provider_caps).map(([p, n]) => `${p} ${n}회`).join(" · ")}`),
    h("p", { class: "cap muted" }, orchestrator ? `${orchestrator.label}: 공개 뒤 기존 합성을 직접 눌러 실행합니다. ${calls.model_calls === 0 ? "모의 합성도 모델 호출 없음." : "누를 때마다 같은 원장 상한에서 1회 사용."}` :
      "오케스트레이터는 나입니다. 합성을 부르지 않고 원문 대조표를 읽습니다."),
    h("p", { class: "sm strong" }, "공통 자료 · 모든 격리 팀원이 받음"),
    preview.sources.length ? h("ul", { class: "stack" }, preview.sources.map(s => h("li", { class: "sm" }, `${s.name} · ${fmtSize(s.bytes)} · sha256 ${s.sha256}`))) : h("p", { class: "sm muted" }, "자료 없음"),
    h("p", { class: "cap muted" }, "원본 앱에는 아래 전달문과 자료를 직접 옮깁니다. 입력·역할·자료는 시작할 때 고정됩니다."),
    h("p", { class: "sm strong" }, "질문 전문"), h("pre", { class: "input-full" }, preview.question),
    collapsible("preview-prompt", "CLI에 보낼 전달문 전문", h("pre", { class: "input-full" }, preview.prompt), { open: true }),
    Object.entries(preview.manual_packets).map(([pid, packet]) => collapsible("packet-" + pid,
      `${pid}에 옮길 전달문 전문`, h("pre", { class: "input-full" }, packet))),
    h("button", { type: "button", id: "confirmStart", class: "btn btn-brand", onclick: confirmRun },
      liveMode ? "확인한 입력으로 시작 — 실제 CLI 호출" : "확인한 입력으로 시작 (모의)"));
  pressAll($("inputPreview")); $("confirmStart").focus();
}
async function confirmRun() {
  if (!previewRequest) return;
  const button = $("confirmStart"), body = previewRequest;
  button.disabled = true; $("formErr").textContent = "";
  try {
    const created = await api("/api/runs", body);
    closeNewRun(); picked = []; renderPicked("");
    await refresh();
    const run = state.runs.find(r => r.run_id === created.run_id);
    navigateTask(run.task_id, run.run_id);
    toast("실행을 시작했습니다. 모두 끝나면 한꺼번에 공개합니다.");
  } catch (e) { $("formErr").textContent = e.message; }
  finally { button.disabled = false; }
}
function closeNewRun() {
  $("composeDialog").close(); $("newRunBtn").setAttribute("aria-expanded", "false");
  invalidatePreview();
}
function navigateTask(taskId = null, runId = null) {
  taskSelected = taskId; selected = runId; taskPageSig = null; runSig = null; listSig = null;
  const query = new URLSearchParams();
  if (taskId) query.set("task", taskId);
  if (runId) query.set("run", runId);
  history.replaceState(null, "", "/" + (query.size ? "?" + query : ""));
  render();
}
function taskCard(task) {
  return h("button", { type: "button", class: "task-card cell", onclick: () => navigateTask(task.task_id) },
    h("span", { class: "row between" }, h("span", { class: "strong lg" }, task.title), badge(TASK_LABELS[task.status])),
    h("span", { class: "sm muted" }, roleSummary(task.role_config)),
    h("span", { class: "cap muted" }, `실행 ${task.runs.length}개 · 쓴 CLI 호출 ${task.calls_used} · 구독 차감량이 아님`));
}
function renderTaskNavigation() {
  const tasks = state.tasks || [], task = tasks.find(t => t.task_id === taskSelected);
  const sig = JSON.stringify([taskSelected, selected, tasks]);
  if (sig === listSig) return;
  listSig = sig;
  $("runTabs").replaceChildren(h("button", { type: "button", class: "btn", onclick: () => navigateTask() }, "홈"),
    task ? h("button", { type: "button", class: "btn", onclick: () => navigateTask(task.task_id) }, task.title) : null,
    selected ? h("span", { class: "cap muted" }, "실행 결과") : null);
  $("runListIsland").replaceChildren(h("h2", { class: "block-title" }, "작업"),
    tasks.length ? tasks.map(t => h("button", { type: "button", class: "run-row", "aria-current": String(t.task_id === taskSelected),
      onclick: () => navigateTask(t.task_id) }, h("span", { class: "sm strong" }, t.title), h("span", { class: "cap muted" }, TASK_LABELS[t.status]))) :
      h("p", { class: "sm muted" }, "새 작업에서 첫 질문을 시작하세요."));
  pressAll($("runTabs")); pressAll($("runListIsland"));
}
function renderTaskPage() {
  const tasks = state.tasks || [], task = tasks.find(t => t.task_id === taskSelected);
  const sig = JSON.stringify([taskSelected, tasks]);
  if (sig === taskPageSig) return;
  taskPageSig = sig; runSig = null; $("asideCol").replaceChildren();
  if (!task) {
    const turns = tasks.filter(t => t.runs.some(r => r.status === "my_turn"));
    $("mainCol").replaceChildren(island("내 차례", [h("p", { class: "sm muted" }, "원본 앱 답을 붙여넣거나, 공개된 답을 보고 다음 일을 정하세요."),
      h("div", { class: "task-grid island-part" }, turns.length ? turns.map(taskCard) : h("p", { class: "sm muted" }, "지금 기다리는 일이 없습니다."))]),
    island("모든 작업", [h("div", { class: "row between" }, h("p", { class: "sm muted" }, "질문부터 결과까지, 한 작업에서 이어 갑니다."),
      h("button", { type: "button", class: "btn btn-brand", onclick: () => openNewRun() }, "새 작업")),
      h("div", { class: "task-grid island-part" }, tasks.length ? tasks.map(taskCard) : h("p", { class: "sm muted" }, "아직 작업이 없습니다."))]));
  } else {
    $("mainCol").replaceChildren(island(task.title, [h("p", { class: "sm muted" }, roleSummary(task.role_config)),
      h("div", { class: "row island-part" }, badge(TASK_LABELS[task.status]), h("span", { class: "sm" }, `쓴 CLI 호출 ${task.calls_used}`),
        h("button", { type: "button", class: "btn btn-brand", onclick: () => openNewRun(task.task_id) }, "이 작업에 새 실행"))]),
    island("실행 타임라인", h("ol", { class: "task-timeline stack-lg" }, task.runs.map((run, i) => h("li", {},
      h("button", { type: "button", class: "task-card cell", onclick: () => navigateTask(task.task_id, run.run_id) },
        h("span", { class: "row between" }, h("span", { class: "strong" }, `실행 ${i + 1} · ${run.question}`), badge(TASK_LABELS[run.status])),
        h("span", { class: "cap muted" }, `${fmtTime(run.created_at)} · CLI 호출 ${run.calls_used}`),
        h("span", { class: "sm muted" }, roleSummary(run.role_config)),
        run.action ? h("span", { class: "sm strong" }, run.action + " →") : null))))));
  }
  pressAll($("mainCol"));
}
function humanComparison(run) {
  return island("원문 대조표 · 오케스트레이터는 나", [h("p", { class: "sm muted" }, "합성 호출 없이 공개된 답을 그대로 나란히 봅니다. 판단과 다음 실행은 내가 정합니다."),
    h("div", { class: "task-grid island-part" }, run.participants.filter(p => p.draft !== undefined).map(p =>
      h("section", { class: "cell stack" }, h("h3", { class: "sm strong" }, p.label),
        p.independence === "unverified" ? badge("독립 미확인") : null, h("pre", { class: "input-full" }, p.draft))))]);
}
