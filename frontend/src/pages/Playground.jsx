import { useEffect, useState } from "react";
import { api } from "../api.js";

const PRESETS = {
  summarize: { text: "In Q3 2025, Acme Corp reported revenue of $4.2 billion, up 18% year-over-year, driven by enterprise AI platform demand." },
  classify: { message: "Why was I charged twice this month? Please refund the duplicate." },
  rag: { question: "How long is the refund window for a monthly plan?" },
  extract: {
    text: "Order #A-1029 placed by Jane Smith on 2026-02-14 for $129.99 (3 items).",
    schema: {
      type: "object",
      required: ["order_id", "customer", "date", "total", "item_count"],
      properties: {
        order_id: { type: "string" },
        customer: { type: "string" },
        date: { type: "string" },
        total: { type: "number" },
        item_count: { type: "integer" },
      },
    },
  },
};

function Rail({ rail }) {
  const cls = rail.passed ? "good" : "bad";
  return (
    <div className="kv">
      <span className="k">{rail.name}</span>
      <span className={`badge ${cls}`}>{rail.passed ? "passed" : "blocked"}</span>
      {rail.reasons?.length > 0 && <span className="muted">({rail.reasons.join(", ")})</span>}
    </div>
  );
}

export default function Playground() {
  const [features, setFeatures] = useState([]);
  const [feature, setFeature] = useState("classify");
  const [inputJson, setInputJson] = useState(JSON.stringify(PRESETS.classify, null, 2));
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.listFeatures().then((r) => setFeatures(r.features)).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    setInputJson(JSON.stringify(PRESETS[feature] ?? {}, null, 2));
    setResult(null);
  }, [feature]);

  const run = async () => {
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const input = JSON.parse(inputJson);
      const r = await api.invokeFeature(feature, input);
      setResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Playground</h2>
        <div className="muted">Invoke a feature live. Input + output run through guardrails.</div>
        <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center" }}>
          <select value={feature} onChange={(e) => setFeature(e.target.value)}>
            {features.map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
          <button onClick={run} disabled={loading}>{loading ? "Running…" : "Invoke"}</button>
        </div>
        <div style={{ marginTop: 12 }}>
          <div className="score-label">Input (JSON)</div>
          <textarea value={inputJson} onChange={(e) => setInputJson(e.target.value)} rows={10} />
        </div>
      </div>

      {error && <div className="panel" style={{ color: "var(--bad)" }}>Error: {error}</div>}

      {result && (
        <div className="grid-2">
          <div className="panel">
            <h3 style={{ marginTop: 0 }}>Input guardrails</h3>
            {result.input_guardrails.length === 0 ? <div className="muted">— skipped —</div> :
              result.input_guardrails.map((r, i) => <Rail key={i} rail={r} />)}
            {result.blocked_input && <div className="badge bad" style={{ marginTop: 10 }}>Input blocked — feature not invoked</div>}
          </div>
          <div className="panel">
            <h3 style={{ marginTop: 0 }}>Output guardrails</h3>
            {result.output_guardrails.length === 0 ? <div className="muted">— skipped —</div> :
              result.output_guardrails.map((r, i) => <Rail key={i} rail={r} />)}
          </div>
          <div className="panel" style={{ gridColumn: "span 2" }}>
            <h3 style={{ marginTop: 0 }}>Output</h3>
            <pre>{JSON.stringify(result.output, null, 2)}</pre>
          </div>
        </div>
      )}
    </>
  );
}
