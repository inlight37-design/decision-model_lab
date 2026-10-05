"use strict";
const extractionRequest = new LatestRequest();
function clearExtraction() {
  extractionRequest.cancel();
  $("extractResult").replaceChildren();
  $("extractRun").disabled = false;
}
function resetExtraction() {
  clearExtraction();
  for (const id of ["extractPdf", "extractUrl", "extractLastPage", "extractLastLine"]) $(id).value = "";
  $("extractFirstPage").value = "1"; $("extractFirstLine").value = "1";
}
function sourceProvenance(p) {
  return h("div", {class: "stack sm"}, h("p", {}, `출처: ${p.origin}`),
    p.final_url ? h("p", {}, `받은 주소: ${p.final_url}`) : null,
    p.pages ? h("p", {}, `페이지 ${p.pages.first}–${p.pages.last}/${p.pages.total} · 제외 ${p.omitted_pages}쪽` +
      (p.pages_without_text?.length ? ` · 글이 없는 쪽 ${p.pages_without_text.join(", ")}` : "")) : null,
    h("p", {}, `추출 글 ${p.lines.first}–${p.lines.last}/${p.lines.total}줄 · 제외 ${p.omitted_lines}줄`),
    h("p", {class: "muted"}, (p.omissions || []).join(" · ")),
    h("p", {class: "cap muted"}, "원본 파일/응답은 보관하지 않습니다. 원본 해시와 추출 사본만 남으며 출처의 진위는 검증하지 않습니다."),
    h("details", {}, h("summary", {}, "출처·변환 해시 보기"), h("pre", {class: "input-full"}, JSON.stringify(p, null, 2))));
}
async function extractSource() {
  clearExtraction();
  const request = extractionRequest.begin(), target = $("extractResult"), submit = $("extractRun");
  const number = id => $(id).value === "" ? null : Number($(id).value);
  const kind = $("extractKind").value;
  const body = {kind, first_line: number("extractFirstLine"), last_line: number("extractLastLine")};
  let filename = "url-extract.txt";
  submit.disabled = true; target.replaceChildren(h("p", {}, "추출 중…"));
  try {
    if (kind === "pdf") {
      const file = $("extractPdf").files[0];
      if (!file || file.size > 1024 * 1024) throw new Error("1 MiB 이하의 PDF 파일을 고르세요.");
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = "";
      for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
      Object.assign(body, {name: file.name, data: btoa(binary), first_page: number("extractFirstPage"), last_page: number("extractLastPage")});
      filename = sourceName(file.name.replace(/\.pdf$/i, "") + "-extract.txt", new Set());
    } else body.url = $("extractUrl").value.trim();
    if (!request.current()) return;
    const result = await api("/api/sources/extract", body, {signal: request.signal});
    if (!request.current()) return;
    const attach = h("button", {class: "btn btn-brand", type: "button", onclick: () => {
      if (!request.current()) return;
      const file = new File([result.text], filename, {type: "text/plain;charset=utf-8"});
      addFiles([file]);
      if (picked.includes(file)) {
        attach.disabled = true;
        target.append(h("p", {}, "추출 사본을 넣었습니다. 보낼 입력을 확인한 뒤 시작하세요."));
      }
    }}, "이 추출 사본을 자료에 넣기");
    target.replaceChildren(sourceProvenance(result.provenance), h("pre", {class: "input-full"}, result.preview), attach);
  } catch (error) { if (request.current() && error.name !== "AbortError") target.replaceChildren(h("p", {class: "cell cell-alert"}, error.message)); }
  finally { if (request.current()) submit.disabled = false; }
}
async function openSource(run, source) {
  const body = h("div", {class: "stack"}, "자료를 읽는 중…");
  catalogFrame("저장한 자료 사본", body);
  const request = catalogRequest.begin();
  try {
    const result = await api(`/api/runs/${run.run_id}/sources/${encodeURIComponent(source.name)}`, undefined, {signal: request.signal});
    if (!request.current()) return;
    const separator = "\n--- EXTRACTED TEXT ---\n";
    const shown = result.provenance ? result.text.slice(result.text.indexOf(separator) + separator.length) : result.text;
    body.replaceChildren(h("p", {class: "strong"}, source.name),
      ...(result.provenance ? [sourceProvenance(result.provenance)] : []), h("pre", {class: "input-full"}, shown),
      h("button", {class: "btn", type: "button", onclick: () => {
        const url = URL.createObjectURL(new Blob([result.text], {type: "text/plain;charset=utf-8"}));
        const link = h("a", {href: url, download: source.name}); document.body.append(link);
        try { link.click(); } finally { link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
      }}, "이 사본을 텍스트 파일로 받기"));
  } catch (error) { if (request.current()) body.replaceChildren(h("p", {}, error.message)); }
}
window.addEventListener("DOMContentLoaded", () => {
  const changeKind = () => {
    clearExtraction();
    const pdf = $("extractKind").value === "pdf";
    $("extractPdfRow").hidden = !pdf; $("extractPages").hidden = !pdf; $("extractUrlRow").hidden = pdf;
  };
  $("extractKind").addEventListener("change", changeKind);
  for (const id of ["extractPdf", "extractUrl", "extractFirstPage", "extractLastPage", "extractFirstLine", "extractLastLine"])
    $(id).addEventListener("input", clearExtraction);
  $("extractRun").addEventListener("click", extractSource);
  $("composeDialog").addEventListener("close", clearExtraction);
  changeKind();
});
