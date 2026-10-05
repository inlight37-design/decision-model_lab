// Plans are editable notes and prerequisites. Starting still uses the input preview.
let planDialog = null, editingPlan = null, planSaving = false;
function openTaskPlan(task = null) {
  if (planSaving) return;
  if (!planDialog) {
    planDialog = h("dialog", {class: "compose-dialog catalog-dialog", "aria-labelledby": "planHeading"});
    document.body.append(planDialog);
  }
  const plan = task?.plan;
  editingPlan = {task_id: task?.task_id || null, revision: plan?.revision || 0, choicesRequest: 0,
    dependencies: new Map((plan?.depends_on || []).map(id => [id, task.readiness?.dependencies.find(d => d.task_id === id)?.title || id]))};
  planDialog.replaceChildren(h("div", {class: "stack-lg"},
    h("div", {class: "row between"}, h("h2", {id: "planHeading"}, task ? "작업 계획 수정" : "작업 계획 만들기"),
      h("button", {type: "button", class: "btn", onclick: () => planDialog.close()}, "닫기")),
    h("label", {class: "stack"}, "제목", h("input", {id: "planTitle", maxlength: 120, value: task?.title || ""})),
    h("label", {class: "stack"}, "목표", h("textarea", {id: "planGoal", rows: 3, maxlength: 16000}, plan?.goal || "")),
    h("label", {class: "stack"}, "완료 기준", h("textarea", {id: "planDone", rows: 3, maxlength: 4000}, plan?.done_when || "")),
    h("p", {class: "sm muted"}, "완료 기준은 내가 판단할 기준입니다. AI 답이나 호출 성공만으로 완료 처리하지 않습니다."),
    h("fieldset", {id: "planDependencies", class: "stack"}, h("legend", {}, "먼저 끝낼 작업"),
      h("div", {id: "planChosen", class: "stack"}),
      h("label", {class: "stack"}, "작업 제목 검색", h("input", {id: "planTaskQuery", type: "search", maxlength: 120,
        oninput: () => loadPlanChoices()})), h("div", {id: "planChoices", class: "stack"})),
    task ? h("p", {class: "sm muted"}, "계획을 바꾸면 기존 결과는 남고 새 계획의 실행이 필요합니다. 이미 시작한 실행의 입력은 바뀌지 않습니다.") : null,
    h("p", {id: "planError", class: "sm", role: "alert"}),
    h("button", {id: "saveTaskPlan", type: "button", class: "btn btn-brand", onclick: saveTaskPlan}, "계획 저장")));
  if (!planDialog.open) planDialog.showModal();
  $("planTitle").focus();
  renderPlanChosen(); loadPlanChoices();
}
function renderPlanChosen() {
  $("planChosen").replaceChildren(...[...editingPlan.dependencies].map(([id, title]) =>
    h("div", {class: "row between"}, h("span", {class: "sm"}, title + " · 선택함"),
      h("button", {type: "button", class: "btn", onclick: () => {
        editingPlan.dependencies.delete(id); renderPlanChosen(); loadPlanChoices();
      }}, "선택 해제"))));
}
async function loadPlanChoices(after = null) {
  const owned = editingPlan, request = ++owned.choicesRequest;
  const query = new URLSearchParams(), value = $("planTaskQuery").value;
  $("planChoices").replaceChildren(h("p", {class: "sm muted", role: "status"}, "작업을 찾고 있습니다."));
  if (value) query.set("query", value);
  if (after) query.set("after", after);
  try {
    const data = await api("/api/task-choices" + (query.size ? "?" + query : ""));
    if (editingPlan !== owned || request !== owned.choicesRequest || !planDialog.open) return;
    $("planChoices").replaceChildren(...data.items.filter(t => t.task_id !== owned.task_id).map(t =>
      h("label", {class: "row"}, h("input", {type: "checkbox", value: t.task_id, checked: owned.dependencies.has(t.task_id),
        onchange: e => { if (e.target.checked) owned.dependencies.set(t.task_id, t.title); else owned.dependencies.delete(t.task_id); renderPlanChosen(); }}), t.title)),
      h("div", {class: "row"}, h("button", {type: "button", class: "btn", disabled: !after, onclick: () => loadPlanChoices()}, "처음"),
        h("button", {type: "button", class: "btn", disabled: !data.next, onclick: () => loadPlanChoices(data.next)}, "다음")));
  } catch (e) { if (editingPlan === owned && request === owned.choicesRequest) {
    $("planChoices").replaceChildren(); $("planError").textContent = e.message;
  } }
}
async function saveTaskPlan() {
  if (planSaving) return;
  const owned = editingPlan;
  const payload = {title: $("planTitle").value, goal: $("planGoal").value, done_when: $("planDone").value,
    depends_on: [...owned.dependencies.keys()], revision: owned.revision};
  planSaving = true; $("saveTaskPlan").disabled = true;
  try {
    const plan = await api(owned.task_id ? `/api/tasks/${encodeURIComponent(owned.task_id)}/plan` : "/api/tasks", payload);
    planDialog.close(); navigateTask(plan.task_id); await refresh();
    toast("계획을 저장했습니다. 실행은 입력을 확인한 뒤 시작합니다.");
  } catch (e) { if (editingPlan === owned) $("planError").textContent = e.message; }
  finally { planSaving = false; $("saveTaskPlan").disabled = false; }
}
function workInbox() {
  const entries = state?.inbox || [];
  const admission = state?.admission;
  return island("내 차례·막힌 일", [
    h("p", {class: "sm muted"}, "지금 필요한 행동을 골라 해당 작업으로 이동합니다. 읽는 것만으로 실행하거나 해결 처리하지 않습니다."),
    ...(admission?.reasons || []).map(r => h("p", {class: "sm cell cell-alert"}, r.message)),
    entries.length ? h("div", {class: "stack island-part"}, entries.map(item =>
      h("button", {type: "button", class: "task-card cell", onclick: () => {
        if (item.kind === "refine_unknown" || item.kind === "split_unknown") {
          if (!window.confirm("이 호출의 프로세스가 모두 끝난 것을 직접 확인했습니까? 호출은 돌려받지 않습니다.")) return;
          if (item.kind === "refine_unknown") act(`/api/refinements/${encodeURIComponent(item.refine_id)}/acknowledge`, {turn: item.turn});
          else act(`/api/splits/${encodeURIComponent(item.split_id)}/acknowledge`);
        } else if (item.kind === "prepare") navigateTask(item.task_id);
        else navigateTask(item.target_task || item.task_id, item.run_id);
      }}, h("span", {class: "strong"}, item.action + " · " + item.title),
      h("span", {class: "sm muted"}, item.reason)))) : h("p", {class: "sm muted"}, "이 위치에 기다리는 일이 없습니다."), pageControls("inbox")]);
}
function taskPlanPanel(task) {
  const plan = task.plan, ready = task.readiness;
  return island("목표·선행 조건", [
    plan ? [h("p", {class: "sm strong"}, "목표"), h("pre", {class: "input-full"}, plan.goal),
      h("p", {class: "sm strong"}, "완료 기준 · 사람이 판단"), h("pre", {class: "input-full"}, plan.done_when),
      !ready.plan_fresh && task.runs.length ? h("p", {class: "sm cell cell-alert"}, "계획 변경 뒤의 새 실행이 필요합니다. 이전 결과와 판단은 그대로 남아 있습니다.") : null] :
      h("p", {class: "sm muted"}, "필요하면 목표·완료 기준과 먼저 끝낼 작업을 연결하세요."),
    ...(ready?.dependencies || []).map(dep => h("div", {class: "row between cell"},
      h("span", {class: "sm"}, dep.title + (dep.complete ? " · 판단 완료" : " · 먼저 확인 필요")),
      h("button", {type: "button", class: "btn", onclick: () => navigateTask(dep.task_id)}, "선행 작업 보기"))),
    h("div", {class: "row"}, h("button", {type: "button", class: "btn", onclick: () => openTaskPlan(task)}, "계획·선행 조건 편집")),
    h("p", {class: "cap muted"}, "선행 작업의 현재 계획에 속한 실행들이 판단 완료되어야 새 실행을 준비할 수 있습니다. 종료 미확인 호출은 먼저 정리해야 합니다.")]);
}
function taskPlanPreview(config) {
  const plan = config.task_plan;
  return plan ? [h("section", {class: "cell stack"}, h("p", {class: "sm strong"}, `작업 계획 ${plan.revision}판 · ${plan.title}`),
    h("p", {class: "sm"}, "완료 기준: " + plan.done_when),
    h("p", {class: "cap muted"}, plan.dependency_evidence.length ? "판단 완료한 선행 작업: " + plan.dependency_evidence.map(d => d.title).join(" · ") : "선행 작업 없음"),
    h("p", {class: "cap muted"}, "이 계획과 선행 결과를 실행에 기록합니다. 실제 모델 입력은 아래 전달문 전문을 확인하세요."))] : [];
}
function workflowSteps(run) {
  const row = state?.focus_run || currentTask(run.task_id)?.runs.find(r => r.run_id === run.run_id);
  const labels = {done: "완료", blocked: "확인 필요", waiting: "기다리는 중", ready: "내 차례", optional: "선택 사항"};
  return row?.steps ? island("진행 순서", [h("ol", {class: "stack"}, row.steps.map(s => h("li", {class: "row between"},
    h("span", {class: "sm"}, s.label), badge(labels[s.state] || s.state)))),
    row.action ? h("p", {class: "sm strong"}, "다음 행동: " + row.action) : null,
    run.role_config?.task_plan ? h("p", {class: "cap muted"}, `이 실행은 작업 계획 ${run.role_config.task_plan.revision}판에서 준비했습니다.`) : null]) : null;
}
