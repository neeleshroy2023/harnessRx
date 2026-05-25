const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function req(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export const api = {
  health: () => req("/health"),
  listFeatures: () => req("/features"),
  invokeFeature: (name, input, skipGuardrails = false) =>
    req(`/features/${name}/invoke`, {
      method: "POST",
      body: JSON.stringify({ input, skip_guardrails: skipGuardrails }),
    }),
  listDatasets: () => req("/datasets"),
  getDataset: (name) => req(`/datasets/${name}`),
  lastResults: (name) => req(`/datasets/${name}/last-results`).catch(() => null),
  startRun: (body) =>
    req("/eval/run", { method: "POST", body: JSON.stringify(body) }),
  getRun: (id) => req(`/eval/runs/${id}`),
  listRuns: () => req("/eval/runs"),
  listGuardrails: () => req("/guardrails"),
  checkAll: (text) =>
    req("/guardrails/check-all", { method: "POST", body: JSON.stringify({ text }) }),
};
