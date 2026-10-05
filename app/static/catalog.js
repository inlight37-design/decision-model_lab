"use strict";
// Search and invocation/source navigation use public queries, never mutate a run.
const CATALOG_KIND = {question: "질문·작업", answer: "답변", review: "교차검토", decision: "사람의 판단",
                      synthesis: "합성·결과 모음", source: "자료 이름·해시"};
const CALL_KIND = {draft: "팀원 답변", refine: "질문 다듬기", next_step: "다음 단계", split: "분담 제안",
                   collate: "결과 모음", cross_review: "교차검토", synthesis: "합성",
                   answer_revision: "수정 답", revision_recheck: "수정 답 재검토"};
const CALL_STATE = {running: "실행 중", accepted: "수용", rejected: "실패·거절", unknown: "종료 미확인",
                    completed: "완료", failed: "실패", acknowledged: "종료를 사람이 확인함"};
const catalogRequest = new LatestRequest();

function closeCatalog() {
  catalogRequest.cancel();
  $("catalogDialog").close();
}
function catalogFrame(title, ...content) {
  catalogRequest.cancel();
  const dialog = $("catalogDialog");
  dialog.replaceChildren(h("div", {class: "stack"},
    h("div", {class: "row between"}, h("h2", {id: "catalogTitle"}, title),
      h("button", {type: "button", class: "btn", onclick: closeCatalog}, "닫기")), ...content));
  dialog.oncancel = () => catalogRequest.cancel();
  dialog.onclose = () => catalogRequest.cancel();
  if (!dialog.open) dialog.showModal();
}
function openCatalog() {
  const query = h("input", {type: "search", id: "catalogQuery", maxlength: "200", required: true,
    placeholder: "전에 쓴 질문, 답변의 문구, 자료 이름"});
  const kind = h("select", {id: "catalogKind"}, h("option", {value: ""}, "모든 종류"),
    Object.entries(CATALOG_KIND).map(([value, label]) => h("option", {value}, label)));
  const task = h("select", {id: "catalogTask"}, h("option", {value: ""}, "모든 작업"),
    (state?.tasks || []).map(t => h("option", {value: t.task_id, selected: t.task_id === taskSelected}, t.title)));
  const results = h("div", {class: "stack", role: "status", "aria-live": "polite"});
  const submit = h("button", {type: "submit", class: "btn btn-brand"}, "찾기");
  const form = h("form", {class: "stack", onsubmit: async event => {
    event.preventDefault();
    const request = catalogRequest.begin();
    const params = new URLSearchParams({q: query.value.trim()});
    if (kind.value) params.set("kind", kind.value);
    if (task.value) params.set("task", task.value);
    results.replaceChildren(h("p", {}, "찾는 중…"));
    try {
      const data = await api("/api/search?" + params, undefined, {signal: request.signal});
      if (!request.current()) return;
      results.replaceChildren(h("p", {class: "sm muted"}, data.total
        ? `${data.total}개 결과${data.truncated ? " · 앞부분만 표시합니다. 검색어를 더 좁혀 보세요." : ""}`
        : "일치하는 공개 기록이 없습니다."),
        ...data.items.map(item => h("section", {class: "stack island-part"},
          h("p", {class: "cap muted"}, `${CATALOG_KIND[item.kind]} · ${item.task_title}`),
          h("p", {class: "strong"}, item.title), h("p", {class: "sm input-full"}, item.snippet),
          h("button", {type: "button", class: "btn", onclick: () => {
            closeCatalog(); navigateTask(item.task_id, item.run_id);
          }}, "원래 실행 보기"))));
    } catch (error) {
      if (request.current() && error.name !== "AbortError") results.replaceChildren(h("p", {}, error.message));
    }
  }}, h("label", {for: "catalogQuery"}, "검색어"), query,
    h("div", {class: "row"}, h("label", {for: "catalogKind"}, "종류"), kind,
      h("label", {for: "catalogTask"}, "작업"), task, submit));
  catalogFrame("기록 찾기", h("p", {class: "sm muted"},
    "질문·자료 이름과 공개된 답·검토·판단을 찾습니다. 봉인된 답은 검색하지 않습니다."), form, results);
  query.focus();
}

async function openActivity(run) {
  const body = h("div", {class: "stack", role: "status"}, "불러오는 중…");
  catalogFrame("이 실행의 호출 기록", h("p", {class: "sm muted"},
    "역할이 달라도 같은 호출 상한을 사용합니다. 종료를 확인한 기록이 성공이나 환불을 뜻하지는 않습니다."), body);
  const request = catalogRequest.begin();
  try {
    const data = await api(`/api/runs/${encodeURIComponent(run.run_id)}/activity`, undefined, {signal: request.signal});
    if (!request.current()) return;
    body.replaceChildren(...(data.invocations.length ? data.invocations.map(item => h("section", {class: "island-part"},
      h("p", {class: "strong"}, `${CALL_KIND[item.purpose]} · ${CALL_STATE[item.state] || item.state}`),
      h("p", {class: "cap muted"}, `${item.adapter_id || "제공자 기록 없음"} · ${item.execution || "실행 종류 기록 없음"}`)))
      : [h("p", {}, "아직 시작한 모델 시도가 없습니다. 수동 답변과 모델 없는 대조는 여기에 세지 않습니다.")]));
  } catch (error) {
    if (request.current() && error.name !== "AbortError") body.replaceChildren(h("p", {}, error.message));
  }
}
