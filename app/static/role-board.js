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
  const warnings = [], general = board.general.length > 0, find = id => roster.find(p => p.pid === id);
  if (board.supervisor.length > 1) warnings.push("슈퍼바이저는 한 장만 배치하세요.");
  if (board.supervisor.some(id => find(id)?.transport === "manual")) warnings.push("슈퍼바이저에는 CLI 카드만 놓을 수 있습니다.");
  if (board.supervisor.length && general) warnings.push("일반 팀원 작업의 다듬기는 아직 지원하지 않습니다. 격리 칸을 쓰거나 슈퍼바이저 칸을 비우세요.");
  const leaning = board.supervisor.map(find).filter(Boolean).filter(s => board.isolated.some(id => find(id)?.provider === s.provider));
  if (leaning.length) warnings.push(`주의: 슈퍼바이저(${leaning[0].label})와 같은 회사의 격리 팀원이 있습니다. 다듬은 질문이나 다음 단계 제안이 그쪽으로 기울 수 있습니다 — 막지는 않습니다.`);
  if (general && board.isolated.length) warnings.push("격리 칸과 일반 칸은 한 실행에 함께 쓰지 않습니다(E 단계). 한쪽만 채우세요.");
  if (board.general.some(id => roster.find(p => p.pid === id)?.transport === "manual"))
    warnings.push("팀원(일반)에는 CLI 카드만 놓을 수 있습니다. 원본 앱은 격리 칸에 놓으세요.");
  if (!board.isolated.length && !general) warnings.push("팀원을 한 명 이상 배치하세요 — 격리 칸 또는 일반 칸.");
  if (board.orchestrator.length > 1) warnings.push("오케스트레이터는 한 장만 배치하세요.");
  const assigned = Object.keys(ROLE_LABELS).flatMap(slot => board[slot]).map(id => roster.find(p => p.pid === id));
  if (assigned.some(p => !p)) warnings.push("현재 명단에 없는 카드가 있습니다.");
  // 슈퍼바이저는 팀원과 같은 카드여도 된다(위의 주의). provider당 한 장 규칙은 격리 실행에서는 팀원·오케스트레이터에,
  // 일반 작업에서는 팀원에만 적용한다 — 일반 작업의 오케스트레이터는 분담만 제안하고 팀원과 같은 카드여도 된다(#135).
  const known = (general ? ["general"] : ["orchestrator", "isolated"]).flatMap(slot => board[slot]).map(find).filter(Boolean);
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
  syncInputMode();
  renderAssignments();
  renderRefine();
}
// 다듬기는 슈퍼바이저 칸에 CLI 카드가 있을 때만 고를 수 있다. 조건이 사라지면 원문으로 돌아가고 진행 중인 다듬기를 놓는다.
function syncInputMode() {
  const ready = roleBoard.supervisor.length === 1 &&
    roleOptions.participants.find(p => p.pid === roleBoard.supervisor[0])?.transport === "cli";
  if (!ready && roleBoard.input_mode === "refine") { roleBoard = { ...roleBoard, input_mode: "original" }; resetRefine(); }
  $("modeRefine").disabled = !ready;
  $("modeRefine").checked = roleBoard.input_mode === "refine";
  $("modeOriginal").checked = roleBoard.input_mode !== "refine";
}
function chooseInputMode(mode) {
  if (mode !== "refine") resetRefine();
  roleBoard = { ...roleBoard, input_mode: mode === "refine" ? "refine" : "original" };
  invalidatePreview(); renderRoleBoard();
}

// ---- 다듬기(카드 #130) ------------------------------------------------------------------------------------------
// 원장이 원문·차례·승인을 기록한다. 이 화면이 쥐는 것은 지금 다듬는 ID·승인하려고 고른 차례·쓰는 중인 말뿐이다.
let refineCurrent = null, refineApproved = null, refineNote = "", refineSig = null;
// 요청 중에는 버튼을 막는다. 원문으로 돌아가거나 창을 새로 열면 세대가 바뀌어, 늦게 온 옛 응답을 새 창에 붙이지 않는다.
let refineBusy = false, refineGeneration = 0;
const REFINE_STATE = { running: "다듬는 중", accepted: "받음", unknown: "종료 미확인" };
function currentRefinement() { return ((state && state.refinements) || []).find(r => r.refine_id === refineCurrent) || null; }
function resetRefine() {
  const ref = currentRefinement();
  if (ref) $("question").value = ref.original;   // 승인한 문장 대신 원문을 되돌려 놓는다
  refineCurrent = null; refineApproved = null; refineNote = ""; refineSig = null;
  refineBusy = false; refineGeneration += 1;
  $("question").readOnly = false;
}
function supervisorChoice() {
  const pid = roleBoard.supervisor[0], model = $("m-" + pid), behavior = $("b-" + pid);
  return { supervisor: pid, ...(model ? { model: model.value } : {}), ...(behavior ? { behavior: behavior.value } : {}) };
}
async function refineTurn() {
  if (refineBusy) return;
  const generation = refineGeneration;
  $("formErr").textContent = "";
  refineBusy = true; renderRefine(true);
  try {
    if (!refineCurrent) {
      const original = $("question").value.trim();
      if (!original) throw new Error("다듬을 원문을 먼저 질문 칸에 적어 주세요.");
      const made = await api("/api/refinements", { ...supervisorChoice(), original,
        task_id: composeTask, use_memory: $("autoMemory").checked });
      if (generation !== refineGeneration) return;   // 그 사이 원문으로 돌아갔거나 창을 새로 열었다
      refineCurrent = made.refine_id;
    } else {
      await api(`/api/refinements/${refineCurrent}/turn`, { ...supervisorChoice(), note: refineNote });
      if (generation !== refineGeneration) return;
      refineNote = "";
    }
    refineApproved = null; invalidatePreview();
    await refresh().catch(() => false);
  } catch (e) {
    if (generation === refineGeneration) $("formErr").textContent = e.message;
  } finally {
    if (generation === refineGeneration) { refineBusy = false; renderRefine(true); }
  }
}
function approveTurn(turn) {
  refineApproved = turn.turn; $("question").value = turn.reply.refined;
  invalidatePreview(); renderRefine(true);
}
// 차례 카드: 기계적 진행 상태는 배지로, 슈퍼바이저가 나에게 묻는 말은 따로 표시한 칸으로 보인다.
function refineTurnCard(turn) {
  const approved = refineApproved === turn.turn;
  const label = turn.state === "rejected" ? (turn.status === "format_error" ? "형식 검사 실패" : "실패") : REFINE_STATE[turn.state] || turn.state;
  const body = turn.reply ? [
      h("p", { class: "cap muted" }, "다듬은 문장"), h("pre", { class: "input-full" }, turn.reply.refined),
      turn.reply.changes.length ? [h("p", { class: "cap muted" }, "원문에서 바뀐 점"),
        h("ul", { class: "stack" }, turn.reply.changes.map(item => h("li", { class: "sm" }, item)))] : null,
      turn.reply.ask ? h("div", { class: "cell ask-cell stack" }, h("p", { class: "cap strong" }, "슈퍼바이저가 나에게 묻는 말"),
        h("p", { class: "sm" }, turn.reply.ask)) : null,
      approved ? h("p", { class: "sm strong" }, "승인함 — 이 문장만 격리 팀원에게 보냅니다.")
        : h("button", { type: "button", class: "btn btn-brand", onclick: () => approveTurn(turn) }, "이 문장으로 승인")]
    : turn.state === "unknown" ? [h("p", { class: "sm cell cell-alert" }, "끝났는지 확인하지 못했습니다. 자리를 차지하고 있어 다음 차례를 부르지 않습니다."),
      h("button", { type: "button", class: "btn btn-danger", onclick: () => {
        if (window.confirm("이 다듬기 차례의 프로세스가 모두 끝난 것을 직접 확인했습니까? 호출은 돌려받지 않습니다."))
          act(`/api/refinements/${refineCurrent}/acknowledge`, { turn: turn.turn });
      } }, "종료를 직접 확인했음(호출은 돌려받지 않음)")]
    : turn.state === "rejected" ? [h("p", { class: "sm cell cell-alert" }, "이 차례는 승인할 수 없습니다 · " + (turn.reason || turn.status || "이유 미확인")),
      turn.raw ? h("pre", { class: "input-full" }, turn.raw.text) : null]
    : h("p", { class: "sm muted" }, "슈퍼바이저가 다듬는 중입니다.");
  return h("section", { class: "cell stack" },
    h("div", { class: "row between" }, h("span", { class: "sm strong" }, `차례 ${turn.turn}`), badge(label)),
    turn.note ? h("p", { class: "cap muted" }, "내가 쓴 말: " + turn.note) : null, body);
}
function renderRefine(force = false) {
  const box = $("refinePanel"), on = !!roleBoard && roleBoard.input_mode === "refine";
  box.hidden = !on;
  if (!on) { box.replaceChildren(); refineSig = null; return; }
  const ref = currentRefinement();
  const sig = JSON.stringify([refineCurrent, refineApproved, refineBusy, ref]);
  if (!force && sig === refineSig) return;
  refineSig = sig;
  $("question").readOnly = !!refineCurrent;   // 다듬기를 시작하면 원문을 고정한다
  const sup = roleOptions.participants.find(p => p.pid === roleBoard.supervisor[0]);
  const parts = [h("span", { class: "form-label" }, `다듬기 · 슈퍼바이저 ${sup ? sup.label : ""}`),
    h("p", { class: "sm muted" }, "슈퍼바이저가 원문을 다듬고 필요한 것을 묻습니다. 한 차례마다 호출 1회, 최대 3차례입니다. " +
      "내가 승인한 문장만 격리 팀원에게 가고 이 대화는 가지 않습니다. 답을 흘리지 않았는지는 기계가 판정하지 않으니 읽고 승인하세요.")];
  if (!refineCurrent) {
    parts.push(h("div", {}, h("button", { type: "button", class: "btn btn-primary", id: "refineGo", onclick: refineTurn,
      disabled: refineBusy }, refineBusy ? "요청하는 중…" : "질문 칸의 원문으로 다듬기 요청 · 호출 1회")));
  } else if (!ref) {
    parts.push(h("p", { class: "sm muted" }, "다듬기 상태를 받는 중입니다."));
  } else {
    parts.push(h("div", { class: "cell stack" }, h("p", { class: "cap muted" }, "원문(고정됨)"), h("p", { class: "sm" }, ref.original)),
      ...ref.turns.map(refineTurnCard));
    const busy = ref.turns.some(t => t.state === "running" || t.state === "unknown");
    if (!busy && ref.turns.length < ref.max_turns) {
      const note = h("textarea", { rows: 2, maxlength: "2000", "aria-label": "슈퍼바이저에게 쓰는 말",
        placeholder: "물음에 대한 답이나 바라는 점(선택)", oninput: e => { refineNote = e.target.value; } });
      note.value = refineNote;
      parts.push(note, h("div", {}, h("button", { type: "button", class: "btn", id: "refineGo", onclick: refineTurn,
        disabled: refineBusy }, refineBusy ? "요청하는 중…" : `한 번 더 다듬기 · 호출 1회 (${ref.turns.length + 1}/${ref.max_turns}차례)`)));
    } else if (!busy) parts.push(h("p", { class: "cap muted" }, `${ref.max_turns}차례를 모두 썼습니다. 한 차례를 승인하거나 원문으로 돌아가세요.`));
    parts.push(h("div", {}, h("button", { type: "button", class: "btn", onclick: () => { resetRefine(); invalidatePreview(); renderRefine(true); } },
      "원문으로 돌아가기(이 다듬기는 쓰지 않음)")));
  }
  box.replaceChildren(...parts.flat());
  pressAll(box);
}
// 일반 칸을 채우면 팀원마다 맡길 일과 받을 자료를 고른다. 정족수 설정은 격리 실행에만 보인다.
function renderAssignments() {
  const members = roleBoard.general, box = $("assignments");
  box.hidden = !members.length; $("advanced").hidden = members.length > 0;
  $("sourcesLabelText").textContent = members.length ? "자료 · 팀원마다 고름" : "공통 자료";
  if (!members.length) { box.replaceChildren(); splitSig = null; return; }
  const split = currentSplit();
  // 제안을 받는 동안 입력이 바뀌었으면 옛 입력으로 만든 제안을 칸에 덮어쓰지 않는다(Codex 교차검토, PR #136)
  if (split && split.state === "accepted" && splitApplied !== split.split_id && splitMatchesNow()) applySplit(split);
  splitSig = JSON.stringify([splitCurrent, splitBusy, split && split.state]);
  box.replaceChildren(h("span", { class: "form-label" }, "팀원별 맡길 일과 받을 자료"),
    h("p", { class: "sm muted" }, "내가 일을 나눕니다. 팀원은 받은 자료만 읽기 전용으로 보고, 파일을 고치지 않습니다. " +
      "결과는 끝나는 대로 보이며 봉인·독립·정족수 판정은 하지 않습니다."),
    ...splitSection(split),
    ...members.map(assignmentField));   // replaceChildren은 배열을 글자로 넣는다 — 펼쳐서 준다
  pressAll(box);
}
// ---- 분담 제안(카드 #135) --------------------------------------------------------------------------------------
// 오케스트레이터 칸에 CLI 카드가 있으면 분담을 제안받아 팀원별 칸을 채운다. 제안은 칸을 채우기만 하고, 시작은 내가 한다.
let splitCurrent = null, splitApplied = null, splitAsked = 0, splitBusy = false, splitGeneration = 0, splitSig = null;
let splitInputs = null;   // 제안을 요청할 때의 목표·팀원·파일(File 그대로)·오케스트레이터 카드와 모델
const SPLIT_LIMIT = 2;
function currentSplit() { return ((state && state.splits) || []).find(s => s.split_id === splitCurrent) || null; }
function resetSplit() {
  splitCurrent = null; splitApplied = null; splitAsked = 0; splitBusy = false; splitGeneration += 1; splitSig = null;
  splitInputs = null;
}
function splitSnapshot() {
  const pid = roleBoard.orchestrator[0], model = $("m-" + pid);
  return { goal: $("question").value.trim(), members: [...roleBoard.general], files: [...picked], orchestrator: pid,
           model: model ? model.value : null };
}
// 지금 입력이 제안을 요청할 때와 같은가. 파일은 이름이 아니라 File 그대로 견준다 — 같은 이름의 다른 내용으로 바꾸면
// 새 File이라 다르다. 다르면 제안을 칸에 채우지도, 실행에 붙이지도 않는다(서버도 해시로 다시 본다).
function splitMatchesNow() {
  if (!splitInputs) return false;
  const now = splitSnapshot();
  return now.goal === splitInputs.goal && now.orchestrator === splitInputs.orchestrator && now.model === splitInputs.model &&
    JSON.stringify(now.members) === JSON.stringify(splitInputs.members) &&
    now.files.length === splitInputs.files.length && now.files.every((file, i) => file === splitInputs.files[i]);
}
// 붙인 파일(File)의 보낼 이름. sourceFiles()와 같은 순서·규칙이다.
function pickedNames() { const taken = new Set(); return picked.map(f => sourceName(f.name, taken)); }
function applySplit(split) {
  const names = pickedNames();
  for (const pid of roleBoard.general) {
    const proposed = split.reply.assignments[pid];
    if (!proposed) continue;
    const draft = assignDraft[pid] ||= { task: "", off: new Set() };
    draft.task = proposed.task;
    draft.off = new Set(picked.filter((file, i) => !proposed.sources.includes(names[i])));
  }
  splitApplied = split.split_id;
}
function splitSection(split) {
  const orchestrator = roleOptions.participants.find(p => p.pid === roleBoard.orchestrator[0]);
  if (!orchestrator || orchestrator.transport !== "cli") return [];
  const running = split && split.state === "running";
  const state = !split ? null : split.state === "accepted" ? badge("제안대로 채움") : split.state === "unknown" ? badge("종료 미확인")
    : split.state === "rejected" ? badge(split.status === "format_error" ? "형식 검사 실패" : "실패") : badge("묻는 중");
  const detail = !split ? null
    : split.state === "accepted" ? h("div", { class: "cell ask-cell stack" }, h("p", { class: "cap strong" }, `${orchestrator.label}의 분담 제안`),
        h("p", { class: "sm" }, "나눈 이유: " + split.reply.reason),
        splitApplied === split.split_id && splitMatchesNow()
          ? h("p", { class: "cap muted" }, "아래 팀원별 칸을 제안대로 채웠습니다. 고쳐도 됩니다 — 시작하면 제안과 고쳤는지가 함께 남습니다.")
          : h("p", { class: "sm cell cell-alert" }, "제안을 요청한 뒤 목표·팀원·자료·오케스트레이터가 바뀌어 이 제안을 쓰지 않습니다. " +
              "칸은 내가 나눈 대로 보냅니다. 제안을 쓰려면 다시 제안받으세요."))
    : split.state === "unknown" ? h("div", { class: "stack" }, h("p", { class: "sm cell cell-alert" }, "끝났는지 확인하지 못했습니다. 자리를 차지하고 있어 새 호출을 막습니다."),
        h("div", {}, h("button", { type: "button", class: "btn btn-danger", onclick: () => {
          if (window.confirm("이 분담 제안 호출의 프로세스가 모두 끝난 것을 직접 확인했습니까? 호출은 돌려받지 않습니다."))
            act(`/api/splits/${split.split_id}/acknowledge`);
        } }, "종료를 직접 확인했음(호출은 돌려받지 않음)")))
    : split.state === "rejected" ? h("div", { class: "stack" }, h("p", { class: "sm cell cell-alert" }, "이 제안은 쓸 수 없습니다 · " + (split.reason || split.status || "이유 미확인")),
        split.raw ? h("pre", { class: "input-full" }, split.raw.text) : null)
    : h("p", { class: "sm muted" }, "오케스트레이터가 목표와 자료를 읽는 중입니다.");
  const blocked = splitBusy || running || (split && split.state === "unknown") || splitAsked >= SPLIT_LIMIT;
  return [h("div", { class: "cell stack" },
    h("div", { class: "row between" }, h("span", { class: "sm strong" }, `분담 제안 · 오케스트레이터 ${orchestrator.label}`), state),
    detail,
    h("div", {}, h("button", { type: "button", class: "btn", onclick: requestSplit, disabled: blocked },
      splitBusy ? "요청하는 중…" : `질문 칸의 목표와 붙인 자료로 분담 제안 받기 · 호출 1회 (${Math.min(splitAsked + 1, SPLIT_LIMIT)}/${SPLIT_LIMIT})`)))];
}
async function requestSplit() {
  if (splitBusy || splitAsked >= SPLIT_LIMIT) return;
  const generation = splitGeneration;
  $("formErr").textContent = "";
  splitBusy = true; renderAssignments();
  try {
    const asked = splitSnapshot();
    if (!asked.goal) throw new Error("전체 목표(질문 칸)를 먼저 적어 주세요.");
    const behavior = $("b-" + asked.orchestrator);
    const made = await api("/api/splits", { goal: asked.goal, orchestrator: asked.orchestrator,
      ...(asked.model ? { model: asked.model } : {}), ...(behavior ? { behavior: behavior.value } : {}),
      members: asked.members, sources: await sourceFiles(asked.files), use_memory: $("autoMemory").checked,
      ...(composeTask ? { task_id: composeTask } : {}) });
    if (generation !== splitGeneration) return;   // 그 사이 창을 새로 열었다
    splitCurrent = made.split_id; splitApplied = null; splitAsked += 1; splitInputs = asked;
    await refresh().catch(() => false);
  } catch (e) {
    if (generation === splitGeneration) $("formErr").textContent = e.message;
  } finally {
    if (generation === splitGeneration) { splitBusy = false; renderAssignments(); }
  }
}
// 제안과 같은 목표·팀원·자료로 보낼 때만 제안을 붙인다. 목표나 팀원·파일을 바꿨으면 내가 나눈 분담이다(서버도 다시 본다).
function splitBody() {
  const split = currentSplit();
  if (!split || split.state !== "accepted" || splitApplied !== split.split_id || !roleBoard.general.length) return {};
  return splitMatchesNow() ? { split: { id: split.split_id } } : {};
}
// 창이 열린 동안 제안 상태가 바뀌었을 때만 다시 그린다 — 맡길 일을 쓰는 중에 칸을 지우지 않는다.
function renderSplitIfChanged() {
  if (!roleBoard || !roleBoard.general.length) return;
  const split = currentSplit();
  if (JSON.stringify([splitCurrent, splitBusy, split && split.state]) !== splitSig) renderAssignments();
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
      : h("p", { class: "cap muted" }, "붙인 자료가 없습니다."));
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
  // 슈퍼바이저 칸만 쓰는 카드도 넣는다 — 빠지면 역할판에 기본 모델이 고정된다(Codex 교차검토, PR #134)
  for (const pid of [...(board.supervisor || []), ...board.isolated, ...(board.general || []), ...board.orchestrator]) {
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
function memoryPreview(config, id = "preview-memory", expanded = true) {
  const pack = config.memory;
  const entries = pack?.entries || [];
  return collapsible(id, "이전 작업 기억 · 격리 팀원 제외", h("div", { class: "stack" },
    h("p", { class: "sm" }, !pack?.enabled ? "자동 기억 꺼짐" : entries.length
      ? "일반 팀원·상위 역할에만 전달합니다. 과거 답의 사실 여부는 검증하지 않았습니다."
      : "같은 작업에 가져올 공개 이력이 없습니다."),
    ...entries.map((e, index) => h("section", { class: "stack" },
      h("p", { class: "sm strong" }, `이전 실행 · ${fmtTime(e.created_at)} · ${e.truncated ? "일부 발췌" : "전체 기록"}`),
      h("pre", { class: "input-full" }, e.excerpt),
      h("p", {class: "cap muted"}, !e.selection ? "선택 이유가 저장되기 전의 기록입니다."
        : e.selection.recent_fallback ? "질문에 일치하는 단어가 없어 최근 공개 기록을 참고로 골랐습니다."
        : `질문과 일치한 표현: ${e.selection.overlap_terms.join(", ")} · 같은 작업의 공개 기록`),
      collapsible(`${id}-source-${index}`, "출처 확인", h("div", {class: "stack"},
        h("p", { class: "cap muted input-full" }, `${e.run_id} · 원본 sha256 ${e.source_sha256}`),
        h("button", {type: "button", class: "btn", onclick: () => {
          if ($("composeDialog").open) closeNewRun();
          navigateTask(pack.task_id, e.run_id);
        }}, "원래 실행 보기")))))), { open: expanded && entries.length > 0 });
}
function generalPreview(preview) {
  const specs = Object.fromEntries(preview.role_config.general.map(p => [p.pid, p]));
  return [h("h3", { class: "block-title" }, "보낼 입력 확인"),
    h("p", { class: "sm strong" }, roleSummary(preview.role_config)),
    h("p", { class: "cap muted" }, MODEL_NOTE),
    h("p", { class: "sm" }, "입력 모드: 원문 · 일반 팀원 작업 — 내가 나누고 모읍니다. 끝나는 대로 결과가 보이고, 봉인·독립·정족수 판정은 하지 않습니다."),
    h("p", { class: "sm" }, `이번 실행: CLI 시작 최대 ${preview.calls.draft_cli}회(팀원마다 한 번) · 다시 부르지 않음`),
    callLimitLine(preview.calls),
    memoryPreview(preview.role_config),
    ...(preview.split ? [h("p", { class: "sm cell ask-cell" }, preview.split.as_proposed
      ? "분담은 오케스트레이터 제안 그대로입니다. 시작하면 그 제안이 이 실행 하나에 묶입니다."
      : "분담은 오케스트레이터 제안에서 시작해 내가 고쳤습니다. 시작하면 제안과 고쳤다는 것이 함께 남습니다.")] : []),
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
    memoryPreview(preview.role_config),
    h("p", { class: "sm strong" }, roleSummary(preview.role_config)),
    h("p", { class: "cap muted" }, MODEL_NOTE),
    h("p", { class: "sm" }, `입력 모드: ${preview.refinement ? `다듬기(${preview.refinement.turn}차례를 승인 · 승인한 문장만 보냄)` : "원문"} · ` +
      `${preview.quorum_policy === "independent_only" ? "독립성이 확인된 참여자만" : "미확인 답도 포함"} · 최소 ${preview.min_independent}명`),
    // replaceChildren은 null을 "null" 글자로 넣는다 — 다듬기가 없을 때는 아무것도 넣지 않는다(Codex 교차검토)
    ...(preview.refinement ? [refinementPair(preview.refinement.original, preview.question, true)] : []),
    ...(preview.proposal ? [h("p", { class: "sm cell ask-cell" }, "이 질문은 앞 실행의 슈퍼바이저 제안에서 왔습니다. 시작하면 그 제안이 이 실행 하나에 묶입니다.")] : []),
    h("p", { class: "sm" }, `이번 실행: CLI 시작 최대 ${calls.draft_cli}회 · 수동 답 ${Object.keys(preview.manual_packets).length}개`),
    callLimitLine(calls),
    h("p", { class: "cap muted" }, orchestrator ? `${orchestrator.label}: 공개 뒤 기존 합성을 직접 눌러 실행합니다. ${calls.model_calls === 0 ? "모의 합성도 모델 호출 없음." : "누를 때마다 같은 원장 상한에서 1회 사용."}` :
      "오케스트레이터는 나입니다. 합성을 부르지 않고 원문 대조표를 읽습니다."),
    h("p", { class: "sm strong" }, "공통 자료 · 모든 격리 팀원이 받음"),
    preview.sources.length ? h("ul", { class: "stack" }, preview.sources.map(s => h("li", { class: "sm" }, `${s.name} · ${fmtSize(s.bytes)} · sha256 ${s.sha256}`))) : h("p", { class: "sm muted" }, "자료 없음"),
    h("p", { class: "cap muted" }, "원본 앱에는 아래 전달문과 자료를 직접 옮깁니다. 입력·역할·자료는 시작할 때 고정됩니다."),
    h("p", { class: "sm strong" }, "질문 전문"), h("pre", { class: "input-full" }, preview.question),
    collapsible("preview-prompt", "CLI에 보낼 전달문 전문", h("pre", { class: "input-full" }, preview.prompt), { open: true }),
    ...Object.entries(preview.manual_packets).map(([pid, packet]) => collapsible("packet-" + pid,
      `${pid}에 옮길 전달문 전문`, h("pre", { class: "input-full" }, packet))),   // 배열째 넣으면 글자가 된다 — 펼친다
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
// 창을 닫아도 남는, 끝났는지 모르는 다듬기 차례. 자리를 쥐고 있으므로 홈에서도 정리할 수 있게 한다.
function stuckRefinements() {
  const stuck = ((state && state.refinements) || []).flatMap(r => r.turns.filter(t => t.state === "unknown").map(t => [r, t]));
  return stuck.length ? island("끝났는지 모르는 다듬기 차례", [h("p", { class: "sm muted" },
      "슈퍼바이저 차례의 프로세스가 끝났는지 확인하지 못했습니다. 자리를 쥐고 있어 새 실행·다듬기를 막습니다."),
    ...stuck.map(([r, t]) => h("div", { class: "row between island-part" },
      h("span", { class: "sm" }, `${r.original.slice(0, 40)} · 차례 ${t.turn}`),
      h("button", { type: "button", class: "btn btn-danger", onclick: () => {
        if (window.confirm("이 다듬기 차례의 프로세스가 모두 끝난 것을 직접 확인했습니까? 호출은 돌려받지 않습니다."))
          act(`/api/refinements/${r.refine_id}/acknowledge`, { turn: t.turn });
      } }, "종료를 직접 확인했음")))]) : null;
}
function renderTaskPage() {
  const tasks = state.tasks || [], task = tasks.find(t => t.task_id === taskSelected);
  const stuck = stuckRefinements();
  const sig = JSON.stringify([taskSelected, tasks, ((state && state.refinements) || []).map(r => r.turns.map(t => t.state))]);
  if (sig === taskPageSig) return;
  taskPageSig = sig; runSig = null; $("asideCol").replaceChildren();
  if (!task) {
    const turns = tasks.filter(t => t.runs.some(r => r.status === "my_turn"));
    $("mainCol").replaceChildren(island("내 차례", [h("p", { class: "sm muted" }, "원본 앱 답을 붙여넣거나, 공개된 답을 보고 다음 일을 정하세요."),
      h("div", { class: "task-grid island-part" }, turns.length ? turns.map(taskCard) : h("p", { class: "sm muted" }, "지금 기다리는 일이 없습니다."))]),
    island("모든 작업", [h("div", { class: "row between" }, h("p", { class: "sm muted" }, "질문부터 결과까지, 한 작업에서 이어 갑니다."),
      h("div", {class: "row"},
        h("button", {type: "button", class: "btn", onclick: () => openCatalog()}, "기록 찾기"),
        h("button", { type: "button", class: "btn btn-brand", onclick: () => openNewRun() }, "새 작업"))),
      h("div", { class: "task-grid island-part" }, tasks.length ? tasks.map(taskCard) : h("p", { class: "sm muted" }, "아직 작업이 없습니다."))]),
    island("프로젝트 안내", [h("p", { class: "sm muted" }, "현재 기능과 개편 제안, 참고 근거를 구분해 찾아봅니다."),
      h("div", { class: "row island-part" },
        h("a", { class: "btn", href: "https://github.com/inlight37-design/decision-model_lab/blob/main/docs/DOCUMENT-MAP.md", target: "_blank", rel: "noopener" }, "문서 지도 (새 탭)"),
        h("a", { class: "btn", href: "https://github.com/inlight37-design/decision-model_lab/blob/main/docs/FEATURES.md", target: "_blank", rel: "noopener" }, "기능·코드 안내 (새 탭)"),
        h("a", { class: "btn", href: "https://github.com/inlight37-design/decision-model_lab/blob/main/docs/REFERENCE-MAP.md", target: "_blank", rel: "noopener" }, "외부 참고 지도 (새 탭)"),
        h("a", { class: "btn", href: "https://github.com/inlight37-design/decision-model_lab/blob/main/docs/architecture/redesign-2026-10-04/PRIORITIES.md", target: "_blank", rel: "noopener" }, "개편 우선순위 (새 탭)"))]),
    ...(stuck ? [stuck] : []));
  } else {
    const tokens = usageLines(task.usage);
    $("mainCol").replaceChildren(island(task.title, [h("p", { class: "sm muted" }, roleSummary(task.role_config)),
      tokens.length ? h("p", { class: "cap muted" }, "토큰(이 작업 전체): " + tokens.join(" / ")) : null,
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
// ---- 다음 단계 제안(카드 #133) --------------------------------------------------------------------------------
// 제안에서 새 실행을 준비하면 그 제안을 기억한다. 보낼 질문이 제안한 질문 그대로일 때만 제안에 묶는다 — 고쳐 쓰면 내 질문이다.
let proposalLink = null;
const PROPOSAL_STATE = { running: "묻는 중", unknown: "종료 미확인" };
function proposalCard(run, p) {
  const label = p.state === "accepted" ? (p.reply.next === "again" ? "제안: 한 번 더" : "제안: 여기서 끝")
    : p.state === "rejected" ? (p.status === "format_error" ? "형식 검사 실패" : "실패") : PROPOSAL_STATE[p.state] || p.state;
  const body = p.reply ? h("div", { class: "cell ask-cell stack" },
      h("p", { class: "cap strong" }, p.reply.next === "again" ? "슈퍼바이저 제안 · 질문을 바꿔 한 번 더" : "슈퍼바이저 제안 · 여기서 끝"),
      h("p", { class: "sm" }, "이유: " + p.reply.reason),
      p.reply.open_points.length ? h("ul", { class: "stack" }, p.reply.open_points.map(x => h("li", { class: "sm" }, "남은 쟁점: " + x))) : null,
      p.reply.question ? [h("p", { class: "cap muted" }, "제안한 다음 질문"), h("pre", { class: "input-full" }, p.reply.question)] : null,
      p.reply.next !== "again" ? h("p", { class: "cap muted" }, "끝낼지는 내가 정합니다. 아래에서 판단 완료를 누르세요.")
        : p.used_by ? h("p", { class: "sm strong" }, "이 제안으로 새 실행을 만들었습니다.")
        : h("div", {}, h("button", { type: "button", class: "btn btn-brand", onclick: () => prepareFromProposal(run, p) },
            "이 질문으로 새 실행 준비(시작 전에 확인)")))
    : p.state === "unknown" ? [h("p", { class: "sm cell cell-alert" }, "끝났는지 확인하지 못했습니다. 자리를 차지하고 있어 새 호출을 막습니다."),
      h("div", {}, h("button", { type: "button", class: "btn btn-danger", onclick: () => {
        if (window.confirm("이 제안 호출의 프로세스가 모두 끝난 것을 직접 확인했습니까? 호출은 돌려받지 않습니다."))
          act(`/api/proposals/${p.proposal_id}/acknowledge`);
      } }, "종료를 직접 확인했음(호출은 돌려받지 않음)"))]
    : p.state === "rejected" ? [h("p", { class: "sm cell cell-alert" }, "이 제안은 쓸 수 없습니다 · " + (p.reason || p.status || "이유 미확인")),
      p.raw ? h("pre", { class: "input-full" }, p.raw.text) : null]
    : h("p", { class: "sm muted" }, "슈퍼바이저가 공개된 답을 읽는 중입니다.");
  return h("section", { class: "cell stack" }, h("div", { class: "row between" }, h("span", { class: "sm strong" }, "다음 단계 제안"), badge(label)), body);
}
// 공개된 격리 실행에서, 역할판에 슈퍼바이저 모델이 있을 때만 보인다. 제안은 실행을 시작하지 않는다.
function proposalIsland(run) {
  const sup = run.role_config && run.role_config.supervisor;
  if (!sup || run.mode === "general" || run.phase !== "revealed") return null;
  const items = run.proposals || [], busy = items.some(p => p.state === "running" || p.state === "unknown");
  return island(`슈퍼바이저 제안 · ${sup.label}`, [
    h("p", { class: "sm muted" }, "공개된 답을 이름표(D1·D2)로만 보여 주고 '한 번 더'나 '여기서 끝'을 제안받습니다. 제안은 실행을 시작하지 않습니다 — " +
      "'한 번 더'의 질문은 내가 확인하고 시작해야 새 실행이 됩니다."),
    ...items.map(p => proposalCard(run, p)),
    !busy && items.length < 2 ? h("div", { class: "island-part" }, h("button", { type: "button", class: "btn",
      onclick: () => act(`/api/runs/${run.run_id}/propose`) }, `다음 단계 제안 받기 · 호출 1회 (${items.length + 1}/2)`)) : null]);
}
// ---- 토큰 사용량(카드 #141) ------------------------------------------------------------------------------------
// provider끼리 더하지 않는다. 캐시로 읽은 몫은 따로, 값이 없으면 0이 아니라 "관측 안 됨", 정가 추정은 청구액이 아니다.
const PROVIDER_NAME = { "claude-code": "Claude", codex: "Codex", antigravity: "agy" };
const TOKEN_FIELD = { input_tokens: "입력", output_tokens: "출력", cache_creation_input_tokens: "캐시에 씀",
  cache_read_input_tokens: "캐시로 읽음", cached_input_tokens: "캐시로 읽음", reasoning_output_tokens: "추론",
  thinking_tokens: "생각", cache_read_tokens: "캐시로 읽음" };
function usageLines(u) {
  if (!u) return [];
  const lines = Object.entries(u.by_provider).map(([provider, e]) => {
    const tokens = Object.entries(e.tokens).map(([k, v]) => `${TOKEN_FIELD[k] || k} ${Number(v).toLocaleString()}`).join(" · ");
    return `${PROVIDER_NAME[provider] || provider} — 호출 ${e.calls}(관측 ${e.observed}${e.unobserved ? `, 관측 안 됨 ${e.unobserved}` : ""})` +
      (e.observed ? ` · ${tokens}` : "") +
      (e.list_price_estimate_usd != null ? ` · 정가 추정 $${e.list_price_estimate_usd}(청구액 아님)` : "");
  });
  if (u.unobserved.manual) lines.push(`원본 앱 답 ${u.unobserved.manual}건 — 사용량 관측 안 됨`);
  if (u.sealed_runs) lines.push(`봉인 중인 실행 ${u.sealed_runs}개는 공개 뒤에 더합니다`);
  return lines;
}
function usageIsland(run) {
  if (!run.usage) return null;
  const lines = usageLines(run.usage);
  return island("토큰 사용량", [h("p", { class: "cap muted" }, "CLI가 보고한 값을 provider별로 더했습니다. 회사끼리는 더하지 않습니다. " +
      "캐시로 읽은 몫은 같은 입력을 다시 읽은 양입니다. 계정 전체 한도와는 다른 숫자입니다."),
    lines.length ? h("ul", { class: "stack" }, lines.map(x => h("li", { class: "sm" }, x))) : h("p", { class: "sm muted" }, "아직 끝난 호출이 없습니다.")]);
}
// ---- 공개 뒤 한 라운드 교차검토(카드 #140) ----------------------------------------------------------------------
// 답을 낸 CLI 팀원이 다른 팀원의 답을 이름표로 읽고 지적한다. 인용이 대상 답과 글자 그대로 맞는지만 표시하고 맞는
// 말인지는 확인하지 않는다. 다른 답을 본 검토라 독립 정족수에 세지 않는다. 지적의 처분은 내가 고른다.
const FINDING_KIND = { counterexample: "반례", missing_condition: "빠진 조건", unsupported: "근거 없음", error: "틀림", other: "기타" };
const DISPOSITION_CHOICES = [["qualified", "받아들임"], ["rejected", "아님"], ["unresolved", "보류"]];
const REVIEW_SKIP = { cap_reached: "호출 상한에 닿음", earlier_reviewer_not_accepted: "앞 검토자가 받지 못함" };
const reviewQuestion = {};   // 실행 → 쓰던 검토 질문. 화면을 다시 그려도 지우지 않는다
function reviewCard(run, r) {
  const name = pid => (run.participants.find(p => p.pid === pid) || {}).label || pid;
  const label = r.state === "accepted" ? (r.reply.findings.length ? `지적 ${r.reply.findings.length}개` : "지적 없음")
    : r.state === "rejected" ? (r.status === "format_error" ? "판독 실패" : "실패")
    : { running: "검토 중", queued: "차례 기다림", unknown: "종료 미확인", skipped: "시작하지 않음" }[r.state] || r.state;
  const stale = Object.entries(r.targets).filter(([, t]) => !t.fresh).map(([l]) => l);
  const body = r.state === "accepted" ? [
      h("p", { class: "cap muted" }, "이름표: " + Object.entries(r.labels).map(([l, pid]) => `${l} = ${name(pid)}`).join(" · ")),
      stale.length ? h("p", { class: "sm cell cell-alert" }, `검토한 뒤 대상 답이 바뀌었습니다: ${stale.join(", ")}`) : null,
      r.reply.findings.length ? r.reply.findings.map((f, i) => h("div", { class: "cell stack" },
        h("div", { class: "row between" }, h("span", { class: "sm strong" }, `${f.target} ${name(f.target_pid)} · ${FINDING_KIND[f.kind] || f.kind}`),
          badge(f.source_check === "exact_match" ? "원문 일치" : "대상 원문에 없음")),
        h("p", { class: "sm" }, `"${f.quote}"`), h("p", { class: "sm" }, f.detail),
        h("div", { class: "row", role: "group", "aria-label": "이 지적의 처분" }, DISPOSITION_CHOICES.map(([value, text]) =>
          h("button", { type: "button", class: f.disposition === value ? "btn btn-brand" : "btn", "aria-pressed": String(f.disposition === value),
            onclick: () => act(`/api/reviews/${r.review_id}/disposition`, { finding: i, disposition: value }) }, text)))))
        : h("p", { class: "sm muted" }, "지적 없음 — 검토자가 형식에 맞게 빈 목록을 냈습니다.")]
    : r.state === "unknown" ? [h("p", { class: "sm cell cell-alert" }, "끝났는지 확인하지 못했습니다. 자리를 차지하고 있어 새 호출을 막습니다."),
      h("div", {}, h("button", { type: "button", class: "btn btn-danger", onclick: () => {
        if (window.confirm("이 검토 호출의 프로세스가 모두 끝난 것을 직접 확인했습니까? 호출은 돌려받지 않습니다."))
          act(`/api/reviews/${r.review_id}/acknowledge`);
      } }, "종료를 직접 확인했음(호출은 돌려받지 않음)"))]
    : r.state === "rejected" ? [h("p", { class: "sm cell cell-alert" }, "이 검토는 쓸 수 없습니다 — '지적 없음'이 아닙니다 · " + (r.reason || r.status || "이유 미확인")),
      r.raw ? h("pre", { class: "input-full" }, r.raw.text) : null]
    : r.state === "skipped" ? h("p", { class: "sm muted" }, "부르지 않았습니다 · " + (REVIEW_SKIP[r.status] || r.status || "이유 미확인"))
    : h("p", { class: "sm muted" }, r.state === "queued" ? "앞 검토자가 끝나면 부릅니다." : "다른 팀원의 답을 읽는 중입니다.");
  return h("section", { class: "cell stack" }, h("div", { class: "row between" },
    h("span", { class: "sm strong" }, `검토자 ${name(r.reviewer.pid)}`), badge(label)), body);
}
function crossReviewIsland(run) {
  if (run.mode === "general" || run.phase !== "revealed") return null;
  const answered = run.participants.filter(p => p.draft != null);
  const reviewers = answered.filter(p => p.transport === "cli");
  const round = run.cross_review;
  const intro = h("p", { class: "sm muted" }, "답을 낸 CLI 팀원이 다른 팀원의 답을 이름표로 읽고 반례·빠진 조건·근거 없는 주장을 지적합니다. " +
    "인용이 대상 답과 글자 그대로 맞는지만 확인하고, 맞는 말인지는 확인하지 않습니다. 다른 답을 본 검토라 독립 정족수에 세지 않습니다.");
  if (!round) {
    if (answered.length < 2 || !reviewers.length) return null;
    const box = h("textarea", { rows: 2, maxlength: "1000", "aria-label": "검토 질문(비우면 기본 질문)",
      placeholder: "비우면: 다른 팀원의 답에서 반례, 빠진 조건, 근거 없는 주장, 틀린 곳을 찾아라." });
    box.value = reviewQuestion[run.run_id] || "";
    box.oninput = () => { reviewQuestion[run.run_id] = box.value; };
    return island("교차검토 · 공개 뒤, 독립 아님", [intro, box,
      h("div", { class: "island-part" }, h("button", { type: "button", class: "btn", onclick: () => {
        if (window.confirm(`검토자 ${reviewers.length}명이 한 명씩 차례로 검토합니다. 호출 ${reviewers.length}회를 씁니다. 시작할까요?`))
          act(`/api/runs/${run.run_id}/cross-review`, { question: box.value });
      } }, `교차검토 받기 · 호출 ${reviewers.length}회(검토자 ${reviewers.length}명)`))]);
  }
  const name = pid => (run.participants.find(p => p.pid === pid) || {}).label || pid;
  const cov = round.coverage;
  return island("교차검토 · 공개 뒤, 독립 아님", [intro,
    h("p", { class: "sm" }, "검토 질문: " + round.question),
    h("p", { class: "cap muted" }, `검토한 관계 ${cov.reviewed}/${cov.pairs} · 사실 검증 안 함 · 한 라운드`),
    cov.missing.length ? h("ul", { class: "stack" }, cov.missing.map(m => h("li", { class: "sm" },
      `검토하지 않음: ${name(m.reviewer)} → ${name(m.target)} · ${REVIEW_SKIP[m.reason] || m.reason}`))) : null,
    ...round.reviews.map(r => reviewCard(run, r))]);
}
// 같은 작업의 새 실행 창을 같은 역할판·같은 모델·제안한 질문으로 연다. 시작은 내가 보낼 입력을 확인한 뒤에 한다.
function prepareFromProposal(run, p) {
  openNewRun(run.task_id);
  const rc = run.role_config, pick = spec => spec ? [spec.pid] : [];
  roleBoard = { ...emptyBoard(), supervisor: pick(rc.supervisor), orchestrator: pick(rc.orchestrator),
                isolated: (rc.isolated || []).map(spec => spec.pid), input_mode: "original" };
  for (const spec of [rc.supervisor, rc.orchestrator, ...(rc.isolated || [])].filter(Boolean)) {
    const select = $("m-" + spec.pid);
    if (select && spec.model) select.value = spec.model;
  }
  $("question").value = p.reply.question;
  proposalLink = { id: p.proposal_id, question: p.reply.question };
  renderRoleBoard(); updateSourceNote();
  $("roleNotice").textContent = "슈퍼바이저 제안의 질문과 앞 실행의 역할판으로 채웠습니다. 질문을 고치면 제안과 묶지 않고 내 질문으로 보냅니다.";
}
function proposalBody() {
  return proposalLink && roleBoard.input_mode === "original" && roleBoard.general.length === 0 &&
    $("question").value.trim() === proposalLink.question ? { proposal: { id: proposalLink.id } } : {};
}
// 원래 목표(원문)와 실제로 보낸 질문을 나란히(요청서 P9). 같은 쪽으로 끌려간 질문을 사람이 알아보게 한다.
function refinementPair(original, sent, before = false) {
  return h("div", { class: "task-grid" },
    h("section", { class: "cell stack" }, h("p", { class: "cap muted" }, "원래 목표 · 내가 쓴 원문"), h("pre", { class: "input-full" }, original)),
    h("section", { class: "cell stack" }, h("p", { class: "cap muted" }, before ? "보낼 질문 · 승인한 다듬기" : "실제로 보낸 질문 · 승인한 다듬기"),
      h("pre", { class: "input-full" }, sent)));
}
// 실행에 쓴 다듬기의 기록: 차례마다 내가 쓴 말·다듬은 문장·바뀐 점·물은 말·상태. 원장의 기록을 그대로 보인다.
function refinementLog(ref) {
  return ref.turns.map(t => h("div", { class: "stack" },
    h("p", { class: "sm strong" }, `차례 ${t.turn} · ${t.state === "accepted" ? "받음" : t.status || t.state}` +
      (ref.approved_turn === t.turn ? " · 승인함" : "")),
    t.note ? h("p", {}, "내가 쓴 말: " + t.note) : null,
    t.reply ? [h("p", {}, "다듬은 문장: " + t.reply.refined),
      t.reply.changes.length ? h("p", {}, "바뀐 점: " + t.reply.changes.join(" · ")) : null,
      t.reply.ask ? h("p", {}, "물은 말: " + t.reply.ask) : null] : h("p", {}, "답 없음 · " + (t.reason || "이유 미확인"))));
}
// 일반 팀원 작업의 결과 모음. 끝난 팀원의 답은 바로 보인다(봉인 없음). 독립·정족수 라벨을 붙이지 않는다.
function generalResults(run) {
  const collected = (run.gate || {}).collected, orch = run.role_config && run.role_config.orchestrator;
  return island(orch ? "팀원 결과" : "팀원 결과 · 오케스트레이터는 나", [h("p", { class: "sm muted" }, !collected
      ? "끝나는 대로 결과가 보입니다. 모두 끝나면 판단 완료를 할 수 있습니다."
      : orch ? "모든 팀원이 끝났습니다. 아래에서 오케스트레이터에게 결과 모으기를 맡길 수 있습니다. 판단은 내가 합니다."
      : "모든 팀원이 끝났습니다. 결과를 모아 보고 아래에서 판단 완료를 하세요. 합성은 부르지 않습니다."),
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
// ---- 결과 모으기(카드 #137) ----------------------------------------------------------------------------------
// 모두 끝난 일반 실행에서, 역할판에 오케스트레이터 모델이 있을 때만 보인다. 인용이 결과 원문과 글자 그대로 맞는지만
// 표시한다 — 맞는 말인지(사실)는 확인하지 않는다. 판단은 내가 한다.
const COLLATION_STATE = { running: "모으는 중", unknown: "종료 미확인" };
const QUOTE_CHECK = { exact_match: "원문 일치", not_found: "원문에 없음" };
function collationList(title, items) {
  return items.length ? [h("p", { class: "cap muted" }, title), h("ul", { class: "stack" }, items.map(x => h("li", { class: "sm" }, x)))] : null;
}
function collationCard(run, col) {
  const label = col.state === "accepted" ? "모음" : col.state === "rejected" ? (col.status === "format_error" ? "형식 검사 실패" : "실패")
    : COLLATION_STATE[col.state] || col.state;
  const who = tag => { const p = run.participants.find(x => x.pid === col.labels[tag]); return p ? `${tag} ${p.label}` : `${tag}(없는 이름표)`; };
  const r = col.reply;
  const body = r ? [h("p", { class: "cap muted" }, `인용 ${r.checks.quotes}개 중 원문 일치 ${r.checks.exact_matches}개 · ` +
        `원문에 없는 추가 주장 ${r.checks.unsupported_additions}개 · 사실 검증 안 함`),
      ...r.claims.map(cl => h("div", { class: "cell stack" },
        h("div", { class: "row between" }, h("p", { class: "sm strong" }, cl.statement),
          badge(cl.support === "quoted" ? "원문 인용 있음" : "원문에 없는 추가 주장")),
        cl.quotes.map(q => h("div", { class: "row" }, badge(QUOTE_CHECK[q.source_check] || q.source_check),
          h("span", { class: "sm" }, `${who(q.member)} · "${q.text}"`))))),
      collationList("겹침·어긋남", r.overlaps), collationList("빈 곳", r.gaps), collationList("다음 할 일(제안)", r.next)]
    : col.state === "unknown" ? [h("p", { class: "sm cell cell-alert" }, "끝났는지 확인하지 못했습니다. 자리를 차지하고 있어 새 호출을 막습니다."),
      h("div", {}, h("button", { type: "button", class: "btn btn-danger", onclick: () => {
        if (window.confirm("이 결과 모으기 호출의 프로세스가 모두 끝난 것을 직접 확인했습니까? 호출은 돌려받지 않습니다."))
          act(`/api/collations/${col.collation_id}/acknowledge`);
      } }, "종료를 직접 확인했음(호출은 돌려받지 않음)"))]
    : col.state === "rejected" ? [h("p", { class: "sm cell cell-alert" }, "이 모음은 쓸 수 없습니다 · " + (col.reason || col.status || "이유 미확인")),
      col.raw ? h("pre", { class: "input-full" }, col.raw.text) : null]
    : h("p", { class: "sm muted" }, "오케스트레이터가 팀원 결과를 읽는 중입니다.");
  return h("section", { class: "cell stack" }, h("div", { class: "row between" }, h("span", { class: "sm strong" }, "결과 모으기"), badge(label)), body);
}
function collationIsland(run) {
  const orch = run.role_config && run.role_config.orchestrator;
  if (!orch || run.mode !== "general" || !(run.gate || {}).collected) return null;
  const items = run.collations || [], busy = items.some(x => x.state === "running" || x.state === "unknown");
  return island(`결과 모으기 · ${orch.label}`, [
    h("p", { class: "sm muted" }, "오케스트레이터에게 팀원마다 맡긴 일과 결과 원문만 보냅니다(자료 원문은 보내지 않음). 주장마다 결과의 문장을 " +
      "그대로 인용하게 하고, 인용이 결과와 글자 그대로 맞는지만 확인합니다 — 맞는 말인지는 확인하지 않습니다. 판단은 내가 합니다."),
    ...items.map(x => collationCard(run, x)),
    !busy && items.length < 2 ? h("div", { class: "island-part" }, h("button", { type: "button", class: "btn",
      onclick: () => act(`/api/runs/${run.run_id}/collate`) }, `결과 모으기 · 호출 1회 (${items.length + 1}/2)`)) : null]);
}
function humanComparison(run) {
  return island("원문 대조표 · 오케스트레이터는 나", [h("p", { class: "sm muted" }, "합성 호출 없이 공개된 답을 그대로 나란히 봅니다. 판단과 다음 실행은 내가 정합니다."),
    h("div", { class: "task-grid island-part" }, run.participants.filter(p => p.draft !== undefined).map(p =>
      h("section", { class: "cell stack" }, h("h3", { class: "sm strong" }, p.label),
        p.independence === "unverified" ? badge("독립 미확인") : null, h("pre", { class: "input-full" }, p.draft))))]);
}
