"use strict";
// Templates restore editable settings only. Fresh preview owns every execution.
let templateItems = [];
const templateReads = new LatestRequest();
async function refreshTemplates() {
  const request = templateReads.begin();
  try {
    const data = await api('/api/templates', undefined, {signal: request.signal});
    if (!request.current() || !$('composeDialog').open) return;
    templateItems = data.templates;
    $('templateChoice').replaceChildren(h('option', {value: ''}, '저장한 템플릿 선택'),
      ...templateItems.map(t => h('option', {value: t.template_id}, t.name)));
  } catch (e) {
    if (request.current()) $('templateStatus').textContent = e.message;
  }
}
async function templateDraft() {
  const files = [...picked], board = JSON.parse(JSON.stringify(roleBoard));
  const draft = {question: $('question').value, task_title: $('taskTitle').value.trim(),
    role_board: board, models: chosenModels(board), use_memory: $('autoMemory').checked,
    min_independent: +$('min').value, quorum_policy: $('policy').value};
  const assignments = Object.fromEntries(Object.entries(assignDraft).map(([pid, d]) =>
    [pid, {task: d.task, off: new Set(d.off)}]));
  draft.sources = await sourceFiles(files);
  if (board.general.length) {
    const built = buildAssignments(board.general, files, draft.sources, assignments);
    if (built.missing.length || built.unused.length) throw new Error('팀원별 맡길 일과 자료 배정을 먼저 채워 주세요.');
    draft.assignments = built.assignments;
  }
  return draft;
}
async function saveTemplate() {
  const generation = previewGeneration, name = $('templateName').value;
  $('templateSave').disabled = true;
  try {
    const draft = await templateDraft();
    if (generation !== previewGeneration || !$('composeDialog').open) return;
    clearExtraction();
    await api('/api/templates', {name, draft});
    if (generation !== previewGeneration || !$('composeDialog').open) return;
    await refreshTemplates();
    $('templateStatus').textContent = '설정과 자료 사본을 저장했습니다. 실행은 시작하지 않았습니다.';
  } catch (e) { $('templateStatus').textContent = e.message; }
  finally { $('templateSave').disabled = false; }
}
async function loadTemplate() {
  const id = $('templateChoice').value, generation = previewGeneration;
  if (!id) return;
  $('templateLoad').disabled = true;
  try {
    const item = await api('/api/templates/' + encodeURIComponent(id));
    if (generation !== previewGeneration || !$('composeDialog').open) return;
    const draft = item.draft;
    initNewRun(roleOptions); invalidatePreview();
    $('question').value = draft.question;
    $('taskTitle').value = draft.task_title || '';
    $('autoMemory').checked = draft.use_memory !== false;
    $('min').value = draft.min_independent || 1;
    $('policy').value = draft.quorum_policy || 'independent_only';
    roleBoard = JSON.parse(JSON.stringify(draft.role_board));
    picked = (draft.sources || []).map(s => new File([s.text], s.name, {type: 'text/plain'}));
    assignDraft = Object.fromEntries(Object.entries(draft.assignments || {}).map(([pid, a]) =>
      [pid, {task: a.task, off: new Set(picked.filter(f => !a.sources.includes(f.name)))}]));
    for (const [pid, model] of Object.entries(draft.models || {})) {
      if ($('m-' + pid)) $('m-' + pid).value = model;
    }
    renderPicked(''); renderRoleBoard(); syncInputMode();
    $('templateName').value = item.name;
    $('templateStatus').textContent = '불러왔습니다. 설정을 고친 뒤 보낼 입력을 새로 확인하세요.';
    $('question').focus();
  } catch (e) {
    if (generation === previewGeneration) $('templateStatus').textContent = e.message;
  } finally { $('templateLoad').disabled = false; }
}
async function deleteTemplate() {
  const item = templateItems.find(t => t.template_id === $('templateChoice').value);
  if (!item || !window.confirm(`“${item.name}” 템플릿을 삭제할까요? 이미 만든 실행은 유지됩니다.`)) return;
  try {
    await api('/api/templates/' + encodeURIComponent(item.template_id) + '/delete', {sha256: item.sha256});
    await refreshTemplates();
    $('templateStatus').textContent = '템플릿을 삭제했습니다.';
  } catch (e) { $('templateStatus').textContent = e.message; }
}
async function exportTemplate() {
  const id = $('templateChoice').value;
  if (!id) return;
  try {
    const item = await api('/api/templates/' + encodeURIComponent(id) + '/export');
    const url = URL.createObjectURL(new Blob([JSON.stringify(item, null, 2)], {type: 'application/json'}));
    const link = h('a', {href: url, download: 'decision-template.json'});
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    $('templateStatus').textContent = '질문과 자료 사본이 포함된 템플릿 파일을 받았습니다.';
  } catch (e) { $('templateStatus').textContent = e.message; }
}
async function importTemplate(file) {
  if (!file) return;
  try {
    if (file.size > 2 * 1024 * 1024) throw new Error('템플릿 파일은 2 MiB까지 읽습니다.');
    const item = JSON.parse(await file.text());
    await api('/api/templates/import', {item});
    await refreshTemplates();
    $('templateStatus').textContent = '템플릿을 가져왔습니다. 목록에서 골라 불러오세요.';
  } catch (e) { $('templateStatus').textContent = e.message; }
}
