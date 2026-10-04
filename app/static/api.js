"use strict";
// Transport and request ownership only. Rendering and application state live elsewhere.
function controlToken() {
  const match = location.hash.match(/token=([A-Za-z0-9_-]+)/);
  try {
    if (match) {
      sessionStorage.setItem("ledger-token", match[1]);
      history.replaceState(null, "", location.pathname + location.search);
      return match[1];
    }
    return sessionStorage.getItem("ledger-token");
  } catch (error) { return match ? match[1] : null; }
}

function createAPI(token, transport = fetch) {
  return async function api(path, body, {signal} = {}) {
    // Never send the control credential to an external host or redirect.
    if (!path.startsWith("/api/") || path.includes("\\")) throw new Error("잘못된 요청 경로입니다.");
    const res = await transport(path, {method: body === undefined ? "GET" : "POST",
      headers: {"Authorization": "Bearer " + token, "Content-Type": "application/json"},
      body: body === undefined ? undefined : JSON.stringify(body), signal, redirect: "error", cache: "no-store"});
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || String(res.status));
    return data;
  };
}

class LatestRequest {
  constructor() { this.generation = 0; this.controller = null; }
  cancel() { this.generation++; this.controller?.abort(); this.controller = null; }
  begin() {
    this.cancel();
    this.controller = new AbortController();
    const generation = this.generation;
    return {signal: this.controller.signal, current: () => this.generation === generation};
  }
}
