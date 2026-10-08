"use strict";
const RESPONSE_LABEL = {addressed: "반영했다고 판단", retained: "기존 입장 유지", unresolved: "미해결",
                       still_open: "아직 남음", uncertain: "판단 불확실"};
function revisionFailure(item, route) {
  return h("div", {class: "stack"}, h("p", {class: "sm muted"},
    item.state === "running" ? "진행 중…" : `${item.state} · ${item.reason || item.status || ""}`),
    item.raw ? h("pre", {class: "input-full"}, item.raw.text) : null,
    item.state === "unknown" ? h("button", {class: "btn btn-danger", type: "button", onclick: () => {
      if (window.confirm("이 호출의 모든 프로세스가 끝난 것을 직접 확인했습니까? 호출은 돌려받지 않습니다.")) act(route);
    }}, "종료를 직접 확인했음") : null);
}
function responseList(items) {
  return h("ul", {class: "stack"}, items.map(x => h("li", {class: "sm"},
    `${x.finding} · ${RESPONSE_LABEL[x.status] || x.status}: ${x.detail}`)));
}
async function previewRevision(run, pid) {
  const body = h("div", {class: "stack", role: "status"}, "수정에 보낼 입력을 준비하는 중…");
  catalogFrame("수정 입력 확인", body);
  const request = catalogRequest.begin();
  try {
    const preview = await api(`/api/runs/${run.run_id}/revisions/preview`, {pid}, {signal: request.signal});
    if (!request.current()) return;
    const start = h("button", {class: "btn btn-brand", type: "button", onclick: async () => {
      start.disabled = true;
      try {
        await api(`/api/runs/${run.run_id}/revisions`, {pid, revision_id: preview.revision_id, confirmation: preview.confirmation});
        if (request.current()) closeCatalog();
        await refresh();
      } catch (error) { if (request.current()) body.append(h("p", {class: "cell cell-alert"}, error.message)); }
      // Starting is single use. Prepare again after an error or ambiguous response.
    }}, "이 입력으로 수정 답 받기 · 호출 1회");
    const snap = preview.snapshot, general = snap.mode === "general";
    body.replaceChildren(h("p", {class: "sm"}, `${preview.author.label} · 원본과 지적을 읽고 별도 판을 씁니다. 기존 답은 보존됩니다.`),
      general ? h("p", {class: "sm"}, `맡은 일: ${snap.task} · 다시 붙이는 자료(자기 것만): ` +
        (snap.sources.length ? snap.sources.map(s => s.name).join(", ") : "없음") + " · 다른 팀원 자료와 자동 기억은 보내지 않습니다.") : null,
      h("pre", {class: "input-full"}, preview.prompt), start);
  } catch (error) { if (request.current()) body.replaceChildren(h("p", {}, error.message)); }
}
async function downloadRevisions(run) {
  try {
    const data = await api(`/api/runs/${run.run_id}/revision-report`);
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: "application/json"}));
    const link = h("a", {href: url, download: `${run.run_id}-revisions.json`});
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { toast(error.message, true); }
}
function revisionIsland(run) {
  if (!run.cross_review) return null;
  const general = run.mode === "general";
  const variants = run.answer_revisions || [];
  const authors = run.participants.filter(p => p.state === "accepted" && p.transport === "cli");
  const ready = !run.cross_review.reviews.some(r => ["queued", "running", "unknown"].includes(r.state));
  return island("수정 답과 재검토", [h("p", {class: "sm muted"}, general
    ? "원래 결과는 보존합니다. 수정은 자기 맡은 일과 자기 자료만으로 하고, 재검토는 다른 팀원이 자료 본문 없이 합니다. 수정은 팀원마다 최대 2회, 재검토는 판마다 최대 2회이며 실패도 포함합니다. 사실 검증이나 독립 답이 아니고, 결과 모으기는 원래 결과를 사용합니다."
    : "원래 답은 보존합니다. 수정은 팀원마다 최대 2회, 재검토는 판마다 최대 2회이며 실패도 포함합니다. 공개 뒤의 판단으로 사실 검증이나 독립 답이 아닙니다. 합성은 원래 초안을 사용합니다."),
    h("div", {class: "row"}, authors.map(p => h("button", {type: "button", class: "btn",
      disabled: !ready || variants.filter(v => v.pid === p.pid).length >= 2,
      onclick: () => previewRevision(run, p.pid)}, `${p.label} 수정 입력 확인`))),
    ...variants.map(v => h("section", {class: "cell stack"},
      h("h3", {class: "sm strong"}, `${v.author.label} · 수정 ${variants.filter(x => x.pid === v.pid).indexOf(v) + 1} · ${v.state}`),
      h("p", {class: "cap muted"}, `이전 판: ${v.parent_id || "원래 초안"} · ${v.revision_id}`),
      v.snapshot.task ? h("p", {class: "sm muted"}, "맡은 일: " + v.snapshot.task) : null,
      v.reply ? [h("div", {class: "task-grid"},
        h("section", {class: "stack"}, h("p", {class: "strong"}, "수정 전"), h("pre", {class: "input-full"}, v.snapshot.base.text)),
        h("section", {class: "stack"}, h("p", {class: "strong"}, "수정 후"), h("pre", {class: "input-full"}, v.reply.answer))),
        h("details", {}, h("summary", {}, "근거 지적과 당시 처분"), h("pre", {class: "input-full"}, JSON.stringify(v.snapshot.findings, null, 2))),
        responseList(v.reply.responses), h("div", {class: "row"}, authors.filter(p => p.pid !== v.pid).map(p =>
          h("button", {type: "button", class: "btn", disabled: v.rechecks.length >= 2 || v.rechecks.some(c => ["running", "unknown"].includes(c.state)), onclick: () => {
            if (window.confirm(`${p.label}에게 이 수정 판과 원래 지적을 재검토하게 합니다. 호출 1회를 씁니다.`))
              act(`/api/revisions/${v.revision_id}/recheck`, {reviewer_pid: p.pid});
          }}, `${p.label}에게 재검토 받기`)))] : revisionFailure(v, `/api/revisions/${v.revision_id}/acknowledge`),
      ...v.rechecks.map(c => h("section", {class: "cell stack"}, h("p", {class: "strong"}, `재검토 · ${c.reviewer.label} · ${c.state}`),
        c.reply ? [responseList(c.reply.assessments), h("p", {class: "sm muted"}, "새 지적도 모델의 판단입니다. 인용 일치는 사실 검증이 아닙니다."),
          ...c.reply.findings.map(f => h("p", {class: "sm"}, `“${f.quote}” · ${f.source_check}: ${f.detail}`))]
          : revisionFailure(c, `/api/rechecks/${c.check_id}/acknowledge`))))),
    variants.length ? h("button", {type: "button", class: "btn", onclick: () => downloadRevisions(run)}, "원본·수정·재검토 이력 저장(JSON)") : null]);
}
