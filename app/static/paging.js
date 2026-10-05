// Cursor positions are view state; completion and admission stay on the server.
let pageCursors = {tasks: null, runs: null, inbox: null};
let pageBack = {tasks: [], runs: [], inbox: []};
function currentTask(id = taskSelected) {
  return state?.focus_task?.task_id === id ? state.focus_task : (state?.tasks || []).find(t => t.task_id === id);
}
function resetPages(kind) { pageCursors[kind] = null; pageBack[kind] = []; }
function browseUrl() {
  const query = new URLSearchParams();
  if (selected) query.set("run", selected);
  if (taskSelected) query.set("task", taskSelected);
  for (const [kind, cursor] of Object.entries(pageCursors)) if (cursor) query.set(kind + "_after", cursor);
  return "/api/browse" + (query.size ? "?" + query : "");
}
function movePage(kind, direction) {
  if (direction === "next") {
    const next = state?.pages?.[kind]?.next;
    if (!next || next === pageCursors[kind]) return;
    pageBack[kind].push(pageCursors[kind]); pageCursors[kind] = next;
  } else if (direction === "previous") {
    pageCursors[kind] = pageBack[kind].pop() || null;
  } else resetPages(kind);
  return refresh();
}
function pageControls(kind) {
  const info = state?.pages?.[kind];
  if (!info) return null;
  return h("nav", {class: "row", "aria-label": {tasks: "작업 목록 페이지", runs: "실행 이력 페이지", inbox: "내 차례 페이지"}[kind]},
    h("span", {class: "cap muted"}, `전체 ${info.total}개 · 이 화면 ${info.count}개`),
    h("button", {type: "button", class: "btn", disabled: !pageCursors[kind], onclick: () => movePage(kind, "first")}, "처음"),
    h("button", {type: "button", class: "btn", disabled: !pageBack[kind].length, onclick: () => movePage(kind, "previous")}, "이전"),
    h("button", {type: "button", class: "btn", disabled: !info.next, onclick: () => movePage(kind, "next")}, "다음"));
}
