"use strict";
// 역할판 화면만의 상태. 저장된 작업·역할은 /api/state에서 받으며 브라우저에 보관하지 않는다.
const ROLE_LABELS = { supervisor: "슈퍼바이저", orchestrator: "오케스트레이터", isolated: "팀원(격리)", general: "팀원(일반)" };
const TASK_LABELS = { working: "작업 중", my_turn: "내 차례", done: "끝남", problem: "문제" };
const MEMBER_STATE = { queued: "대기", running: "작업 중", accepted: "받음", rejected: "실패", unknown: "종료 미확인" };
let roleOptions = null, roleBoard = null, chosenCard = null, previewRequest = null, composeTask = null;
let previewGeneration = 0;
// 일반 팀원마다 맡길 일과 빼 둔 자료(File). 새로 붙인 자료는 모든 팀원이 받는 것으로 시작한다. 창을 새로 열면 비운다.
let assignDraft = {};
let taskSelected = new URLSearchParams(location.search).get("task"), taskPageSig = null;

function emptyBoard() { return { supervisor: [], orchestrator: [], isolated: [], general: [], input_mode: "original" }; }
function placeRole(board, pid, slot) {
  if (!Object.hasOwn(ROLE_LABELS, slot)) return board;
  return { ...board, [slot]: board[slot].includes(pid) ? [...board[slot]] : [...board[slot], pid] };
}
function memberName(p) { return p.transport === "cli" && p.model ? `${p.label}(${p.model})` : p.label; }
function roleSummary(config) {
  if (!config) return "역할 구성 없음";
  const name = p => !p ? "나" : memberName(p);
  const team = (config.general || []).length ? `일반 ${config.general.map(name).join(", ")}`
    : `격리 ${(config.isolated || []).map(name).join(", ") || "없음"}`;
  return `슈퍼바이저 ${name(config.supervisor)} · 오케스트레이터 ${name(config.orchestrator)} · ${team}` +
    (config.source === "legacy" ? " · 기존 실행" : "");
}
function boardWarnings(board, roster) {
  // 서버(app/roles.py freeze)가 같은 배치를 다시 거절한다. 여기서는 시작 전에 이유를 먼저 보인다.
  const warnings = [], general = board.general.length > 0;
  if (board.supervisor.length) warnings.push("슈퍼바이저 모델은 D 단계에서 지원합니다.");
  if (general && board.isolated.length) warnings.push("격리 칸과 일반 칸은 한 실행에 함께 쓰지 않습니다(E 단계). 한쪽만 채우세요.");
  if (general && board.orchestrator.length) warnings.push("일반 팀원 작업의 오케스트레이터 모델은 D 단계에서 지원합니다. 비우면 내가 나누고 모읍니다.");
  if (board.general.some(id => roster.find(p => p.pid === id)?.transport === "manual"))
    warnings.push("팀원(일반)에는 CLI 카드만 놓을 수 있습니다. 원본 앱은 격리 칸에 놓으세요.");
  if (!board.isolated.length && !general) warnings.push("팀원을 한 명 이상 배치하세요 — 격리 칸 또는 일반 칸.");
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
  renderAssignments();
}
// 일반 칸을 채우면 팀원마다 맡길 일과 받을 자료를 고른다. 정족수 설정은 격리 실행에만 보인다.
function renderAssignments() {
  const members = roleBoard.general, box = $("assignments");
  box.hidden = !members.length; $("advanced").hidden = members.length > 0;
  $("sourcesLabelText").textContent = members.length ? "자료 · 팀원마다 고름" : "공통 자료";
  if (!members.length) { box.replaceChildren(); return; }
  box.replaceChildren(h("span", { class: "form-label" }, "팀원별 맡길 일과 받을 자료"),
    h("p", { class: "sm muted" }, "내가 일을 나눕니다. 팀원은 받은 자료만 읽기 전용으로 보고, 파일을 고치지 않습니다. " +
      "결과는 끝나는 대로 보이며 봉인·독립·정족수 판정은 하지 않습니다."),
    ...members.map(assignmentField));   // replaceChildren은 배열을 글자로 넣는다 — 펼쳐서 준다
  pressAll(box);
}
function assignmentField(pid) {
  const p = roleOptions.participants.find(x => x.pid === pid);
  const draft = assignDraft[pid] ||= { task: "", off: new Set() };
  const task = h("textarea", { id: "task-" + pid, rows: 3, maxlength: "4000", "aria-label": `${p.label}에게 맡길 일`,
    placeholder: "예: 자료 A를 읽고 장단점을 정리해 주세요", oninput: e => { draft.task = e.target.value; } });
  task.value = draft.task;
  const files = picked.map((file, i) => {
    const box = h("input", { type: "checkbox", id: `src-${pid}-${i}`, onchange: e => {
      if (e.target.checked) draft.off.delete(file); else draft.off.add(file);
    } });
    box.checked = !draft.off.has(file);
    return h("label", { class: "checkbox-row sm", for: `src-${pid}-${i}` }, box, file.name);
  });
  const head = "assign-head-" + pid;
  return h("div", { class: "cell stack assignment", role: "group", "aria-labelledby": head },
    h("span", { class: "sm strong", id: head }, p.label), task,
    files.length ? [h("span", { class: "cap muted" }, "받을 자료 · 원문 파일 전체"), files]
      : h("p", { class: "cap muted" }, "붙인 자료가 없습니다. 맡길 일만 보냅니다."));
}
// 보낼 본문의 assignments. files는 붙인 순서의 File, sources는 sourceFiles()가 같은 순서로 만든 {name, text}다.
// 비었거나 아무도 받지 않는 자료는 서버도 거절하지만, 보내기 전에 이유를 먼저 알린다.
function buildAssignments(members, files, sources, drafts) {
  const nameOf = new Map(files.map((file, i) => [file, sources[i].name]));
  const assignments = Object.fromEntries(members.map(pid => {
    const draft = drafts[pid] || { task: "", off: new Set() };
    return [pid, { task: draft.task, sources: files.filter(f => !draft.off.has(f)).map(f => nameOf.get(f)) }];
  }));
  const used = new Set(Object.values(assignments).flatMap(a => a.sources));
  return { assignments, missing: members.filter(pid => !assignments[pid].task.trim()),
           unused: sources.map(s => s.name).filter(name => !used.has(name)) };
}
const FUNDING_LABEL = { credits: "막음 · 추가 크레딧 경로", unconfirmed: "막음 · 구독 포함 미확인" };
function modelSelect(p, choices) {
  // 허용 목록만 보인다. 막힌 모델은 고를 수 없게 두고 이유를 붙인다(카드 #119). 추론 강도는 아직 연결하지 않았다.
  if (!choices || !choices.length) return null;
  return h("label", { class: "cap muted" }, "모델 ",
    h("select", { id: "m-" + p.pid, "aria-label": p.label + " 모델" }, choices.map(c => h("option", {
      value: c.model, disabled: !c.usable, selected: c.model === p.model, title: c.basis },
      c.usable ? c.model : `${c.model} — ${FUNDING_LABEL[c.funding] || "막음"}`))));
}
function roleCard(p, opt) {
  const kind = p.transport === "manual" ? "원본 앱 · 독립 미확인" : opt.live ? "실제 CLI · 강도는 CLI 기본값" : "모의 CLI · 모델 호출 없음";
  return h("div", { class: "cell role-card" },
    h("button", { type: "button", class: "role-pick", id: "card-" + p.pid, draggable: "true", "aria-pressed": "false",
      onclick: () => { chosenCard = chosenCard === p.pid ? null : p.pid; renderRoleBoard();
        $("roleNotice").textContent = chosenCard ? `${p.label} 선택됨. 배치할 칸을 누르세요.` : "선택을 해제했습니다."; },
      ondragstart: e => { e.dataTransfer.setData("text/role-card", p.pid); e.dataTransfer.effectAllowed = "copy"; }
    }, h("span", { class: "strong" }, p.label), h("span", { class: "cap muted" }, kind)),
    p.transport === "cli" ? modelSelect(p, (opt.model_choices || {})[p.pid]) : null,
    p.transport === "cli" && !opt.live ? h("select", { id: "b-" + p.pid, "aria-label": p.label + " 모의 행동" },
      opt.behaviors.map(b => h("option", { value: b }, BEHAVIOR_LABEL[b] || b))) : null);
}
function chosenModels(board) {
  // 이번 실행에 놓은 CLI 카드의 모델. 서버가 허용 목록으로 다시 확인한다.
  const models = {};
  for (const pid of [...board.isolated, ...(board.general || []), ...board.orchestrator]) {
    const select = $("m-" + pid);
    if (select) models[pid] = select.value;
  }
  return models;
}
const MODEL_NOTE = "괄호 안의 모델을 그대로 요청합니다. 답한 모델의 보고가 다르면 받지 않고, 다른 모델로 바꾸지 않습니다. " +
  "추론 강도는 아직 연결하지 않았습니다(CLI 기본값).";
function callLimitLine(calls) {
  return h("p", { class: "sm" }, calls.model_calls === 0 ? "모의 모드 · 실제 모델 호출 상한 0" :
    `이 원장의 실제 호출 상한 ${calls.live_cap} · ${Object.entries(calls.provider_caps).map(([p, n]) => `${p} ${n}회`).join(" · ")}`);
}
function sourceLine(s) {
  return h("li", { class: "sm" }, `${s.name} · ${fmtSize(s.bytes)} · sha256 ${s.sha256}` + (s.kind === "original" ? " · 원문 파일 전체" : ""));
}
function confirmButton() {
  return h("button", { type: "button", id: "confirmStart", class: "btn btn-brand", onclick: confirmRun },
    liveMode ? "확인한 입력으로 시작 — 실제 CLI 호출" : "확인한 입력으로 시작 (모의)");
}
// 일반 팀원 작업의 확인 화면: 팀원마다 실제로 보낼 입력 전문과 받을 자료 목록을 그대로 보인다.
function generalPreview(preview) {
  const specs = Object.fromEntries(preview.role_config.general.map(p => [p.pid, p]));
  return [h("h3", { class: "block-title" }, "보낼 입력 확인"),
    h("p", { class: "sm strong" }, roleSummary(preview.role_config)),
    h("p", { class: "cap muted" }, MODEL_NOTE),
    h("p", { class: "sm" }, "입력 모드: 원문 · 일반 팀원 작업 — 내가 나누고 모읍니다. 끝나는 대로 결과가 보이고, 봉인·독립·정족수 판정은 하지 않습니다."),
    h("p", { class: "sm" }, `이번 실행: CLI 시작 최대 ${preview.calls.draft_cli}회(팀원마다 한 번) · 다시 부르지 않음`),
    callLimitLine(preview.calls),
    h("p", { class: "sm strong" }, "전체 목표"), h("pre", { class: "input-full" }, preview.question),
    Object.entries(preview.assignments).map(([pid, a]) => h("section", { class: "cell stack" },
      h("h4", { class: "sm strong" }, specs[pid] ? memberName(specs[pid]) : pid),
      h("p", { class: "cap muted" }, "맡긴 일"), h("pre", { class: "input-full" }, a.task),
      h("p", { class: "cap muted" }, `받을 자료 ${a.sources.length}개 · 읽기 전용`),
      a.sources.length ? h("ul", { class: "stack" }, a.sources.map(sourceLine)) : h("p", { class: "sm muted" }, "자료 없음"),
      collapsible("preview-prompt-" + pid, `${specs[pid]?.label || pid}에 보낼 입력 전문 · sha256 ${a.input_sha256.slice(0, 12)}…`,
        h("pre", { class: "input-full" }, a.prompt), { open: true }))),
    h("p", { class: "cap muted" }, "입력·역할·팀원별 자료는 시작할 때 고정됩니다. 바꾸려면 새 실행을 만드세요."),
    confirmButton()].flat();   // replaceChildren에 펼쳐 넣으므로 팀원 칸의 배열을 한 겹으로 편다
}
function showInputPreview(preview, body) {
  previewRequest = { ...body, run_id: preview.run_id, confirmation: preview.confirmation };
  const calls = preview.calls, orchestrator = preview.role_config.orchestrator;
  $("inputPreview").hidden = false;
  if (preview.mode === "general") {
    $("inputPreview").replaceChildren(...generalPreview(preview));
    pressAll($("inputPreview")); $("confirmStart").focus();
    return;
  }
  $("inputPreview").replaceChildren(h("h3", { class: "block-title" }, "보낼 입력 확인"),
    h("p", { class: "sm strong" }, roleSummary(preview.role_config)),
    h("p", { class: "cap muted" }, MODEL_NOTE),
    h("p", { class: "sm" }, `입력 모드: 원문 · ${preview.quorum_policy === "independent_only" ? "독립성이 확인된 참여자만" : "미확인 답도 포함"} · 최소 ${preview.min_independent}명`),
    h("p", { class: "sm" }, `이번 실행: CLI 시작 최대 ${calls.draft_cli}회 · 수동 답 ${Object.keys(preview.manual_packets).length}개`),
    callLimitLine(calls),
    h("p", { class: "cap muted" }, orchestrator ? `${orchestrator.label}: 공개 뒤 기존 합성을 직접 눌러 실행합니다. ${calls.model_calls === 0 ? "모의 합성도 모델 호출 없음." : "누를 때마다 같은 원장 상한에서 1회 사용."}` :
      "오케스트레이터는 나입니다. 합성을 부르지 않고 원문 대조표를 읽습니다."),
    h("p", { class: "sm strong" }, "공통 자료 · 모든 격리 팀원이 받음"),
    preview.sources.length ? h("ul", { class: "stack" }, preview.sources.map(s => h("li", { class: "sm" }, `${s.name} · ${fmtSize(s.bytes)} · sha256 ${s.sha256}`))) : h("p", { class: "sm muted" }, "자료 없음"),
    h("p", { class: "cap muted" }, "원본 앱에는 아래 전달문과 자료를 직접 옮깁니다. 입력·역할·자료는 시작할 때 고정됩니다."),
    h("p", { class: "sm strong" }, "질문 전문"), h("pre", { class: "input-full" }, preview.question),
    collapsible("preview-prompt", "CLI에 보낼 전달문 전문", h("pre", { class: "input-full" }, preview.prompt), { open: true }),
    Object.entries(preview.manual_packets).map(([pid, packet]) => collapsible("packet-" + pid,
      `${pid}에 옮길 전달문 전문`, h("pre", { class: "input-full" }, packet))),
    confirmButton());
  pressAll($("inputPreview")); $("confirmStart").focus();
}
async function confirmRun() {
  if (!previewRequest) return;
  const button = $("confirmStart"), body = previewRequest;
  button.disabled = true; $("formErr").textContent = "";
  let created;
  try { created = await api("/api/runs", body); }
  catch (e) { $("formErr").textContent = e.message; return; }
  finally { button.disabled = false; }
  // 여기부터 실행은 이미 시작했다. 뒤이은 조회가 실패하거나 아직 새 실행을 모르더라도 응답의 run_id로 그 실행을
  // 고른다 — 창의 오류 칸에 쓰거나 다시 시작하게 하지 않는다(구조 검토 AH-05). 작업은 조회가 그 실행을 가져오면
  // render()가 채운다. 기존 작업에 붙인 실행이면 그 작업은 처음부터 안다.
  closeNewRun(); picked = []; renderPicked("");
  await refresh().catch(() => false);
  const run = ((state && state.runs) || []).find(r => r.run_id === created.run_id);
  navigateTask(run ? run.task_id : (body.task_id || null), created.run_id);
  toast(run ? (run.mode === "general" ? "실행을 시작했습니다. 팀원의 결과는 끝나는 대로 보입니다."
      : "실행을 시작했습니다. 모두 끝나면 한꺼번에 공개합니다.")
    : "실행을 시작했습니다 — 상태를 확인하는 중입니다. 다시 시작하지 마세요.");
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
  // replaceChildren은 h()와 달리 null·배열을 거르지 않고 글자("null", "[object HTMLButtonElement]")로 넣는다.
  $("runTabs").replaceChildren(...[h("button", { type: "button", class: "btn", onclick: () => navigateTask() }, "홈"),
    task ? h("button", { type: "button", class: "btn", onclick: () => navigateTask(task.task_id) }, task.title) : null,
    selected ? h("span", { class: "cap muted" }, "실행 결과") : null].filter(Boolean));
  $("runListIsland").replaceChildren(h("h2", { class: "block-title" }, "작업"),
    ...(tasks.length ? tasks.map(t => h("button", { type: "button", class: "run-row", "aria-current": String(t.task_id === taskSelected),
      onclick: () => navigateTask(t.task_id) }, h("span", { class: "sm strong" }, t.title), h("span", { class: "cap muted" }, TASK_LABELS[t.status]))) :
      [h("p", { class: "sm muted" }, "새 작업에서 첫 질문을 시작하세요.")]));
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
// 일반 팀원 작업의 결과 모음. 끝난 팀원의 답은 바로 보인다(봉인 없음). 독립·정족수 라벨을 붙이지 않는다.
function generalResults(run) {
  const collected = (run.gate || {}).collected;
  return island("팀원 결과 · 오케스트레이터는 나", [h("p", { class: "sm muted" }, collected
      ? "모든 팀원이 끝났습니다. 결과를 모아 보고 아래에서 판단 완료를 하세요. 합성은 부르지 않습니다."
      : "끝나는 대로 결과가 보입니다. 모두 끝나면 판단 완료를 할 수 있습니다."),
    h("div", { class: "task-grid island-part" }, run.participants.map(p => {
      const failed = p.state === "rejected" || p.state === "unknown";
      return h("section", { class: "cell stack" },
        h("div", { class: "row between" }, h("h3", { class: "sm strong" }, p.label), badge(MEMBER_STATE[p.state] || p.state)),
        p.assignment ? [h("p", { class: "cap muted" }, "맡긴 일"), h("p", { class: "sm" }, p.assignment.task)] : null,
        p.draft != null ? h("pre", { class: "input-full" }, p.draft)
          : failed ? h("p", { class: "sm cell cell-alert" }, "결과 없음 · " + (p.detail || p.status || "이유 미확인"))
          : h("p", { class: "sm muted" }, p.state === "queued" ? "시작을 기다립니다." : "작업 중입니다."));
    }))]);
}
function humanComparison(run) {
  return island("원문 대조표 · 오케스트레이터는 나", [h("p", { class: "sm muted" }, "합성 호출 없이 공개된 답을 그대로 나란히 봅니다. 판단과 다음 실행은 내가 정합니다."),
    h("div", { class: "task-grid island-part" }, run.participants.filter(p => p.draft !== undefined).map(p =>
      h("section", { class: "cell stack" }, h("h3", { class: "sm strong" }, p.label),
        p.independence === "unverified" ? badge("독립 미확인") : null, h("pre", { class: "input-full" }, p.draft))))]);
}
