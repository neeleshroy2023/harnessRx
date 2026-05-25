import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";

export default function Dashboard() {
  const [runs, setRuns] = useState(null);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(false);
  const [latest, setLatest] = useState(null);

  const refresh = () => {
    api.listRuns().then((r) => {
      setRuns(r);
      const top = (r.persisted || [])[0];
      if (top) api.getRun(top.id).then((d) => setLatest(d.data));
    }).catch((e) => setError(String(e)));
  };

  useEffect(() => { refresh(); }, []);

  const startRun = async (useJudge) => {
    setStarting(true);
    try {
      const { run_id } = await api.startRun({ use_judge: useJudge, label: useJudge ? "ui-full" : "ui-quick" });
      // poll
      const poll = setInterval(async () => {
        const d = await api.getRun(run_id);
        if (d.live?.status === "completed" || d.live?.status === "failed") {
          clearInterval(poll);
          setStarting(false);
          refresh();
        }
      }, 2000);
    } catch (e) {
      setError(String(e));
      setStarting(false);
    }
  };

  if (error) return <div className="panel" style={{ color: "var(--bad)" }}>API error: {error}<br /><span className="muted">Make sure the API is running at http://localhost:8000.</span></div>;
  if (!runs) return <div className="panel">Loading…</div>;

  const chartData = latest ? Object.entries(latest.features || {}).map(([k, v]) => ({ feature: k, score: Number((v.score ?? 0).toFixed(3)) })) : [];

  return (
    <>
      <div className="panel" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: 0 }}>Run an evaluation</h2>
          <div className="muted">Triggers the same harness CI uses.</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => startRun(false)} disabled={starting} className="secondary">Quick run (no judge)</button>
          <button onClick={() => startRun(true)} disabled={starting}>{starting ? "Running…" : "Full run + judge"}</button>
        </div>
      </div>

      {latest && (
        <div className="grid-3">
          <div className="panel">
            <div className="score-label">Overall score</div>
            <div className="score-big">{(latest.overall ?? 0).toFixed(3)}</div>
            <div className="muted">{Object.keys(latest.features || {}).length} features evaluated</div>
          </div>
          <div className="panel" style={{ gridColumn: "span 2" }}>
            <div className="score-label">Per-feature score</div>
            <div style={{ width: "100%", height: 180 }}>
              <ResponsiveContainer>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                  <XAxis dataKey="feature" stroke="#8b949e" />
                  <YAxis domain={[0, 1]} stroke="#8b949e" />
                  <Tooltip contentStyle={{ background: "#0d1117", border: "1px solid #30363d" }} />
                  <Bar dataKey="score" fill="#58a6ff" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {latest && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Guardrail pass-rates</h3>
          <table>
            <thead><tr><th>Guardrail</th><th>Cases</th><th>Pass-rate</th></tr></thead>
            <tbody>
              {Object.entries(latest.guardrails || {}).map(([k, v]) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td>{v.n}</td>
                  <td>
                    <span className={`badge ${v.pass_rate >= 0.9 ? "good" : v.pass_rate >= 0.7 ? "warn" : "bad"}`}>
                      {(v.pass_rate * 100).toFixed(1)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Recent runs</h3>
        {(runs.persisted || []).length === 0 ? (
          <div className="muted">No runs yet. Start one above.</div>
        ) : (
          <table>
            <thead><tr><th>Run</th><th>When</th><th>Overall</th></tr></thead>
            <tbody>
              {(runs.persisted || []).slice(0, 10).map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>{r.started_at}</td>
                  <td>{(r.overall ?? 0).toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
