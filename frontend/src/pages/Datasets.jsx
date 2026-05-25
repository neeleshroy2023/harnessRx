import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Datasets() {
  const [list, setList] = useState(null);
  const [selected, setSelected] = useState(null);
  const [data, setData] = useState(null);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.listDatasets().then(setList).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setData(null); setResults(null);
    api.getDataset(selected).then(setData).catch((e) => setError(String(e)));
    api.lastResults(selected).then(setResults).catch(() => setResults(null));
  }, [selected]);

  if (error) return <div className="panel" style={{ color: "var(--bad)" }}>{error}</div>;
  if (!list) return <div className="panel">Loading…</div>;

  const allNames = [...(list.features || []), ...(list.guardrails || [])];

  return (
    <>
      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Test datasets</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {allNames.map((n) => (
            <button key={n} onClick={() => setSelected(n)} className={selected === n ? "" : "secondary"}>{n}</button>
          ))}
        </div>
      </div>

      {data && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>{data.name} — {data.n} cases</h3>
          {results && <div className="muted" style={{ marginBottom: 8 }}>Last run: {results.run_id}</div>}
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Input</th>
                <th>Expected</th>
                {results && <th>Score</th>}
                {results && <th>Guardrails</th>}
              </tr>
            </thead>
            <tbody>
              {data.cases.map((c) => {
                const r = results?.cases?.find((x) => x.id === c.id);
                return (
                  <tr key={c.id}>
                    <td>{c.id}</td>
                    <td><pre style={{ margin: 0, maxWidth: 360, whiteSpace: "pre-wrap" }}>{JSON.stringify(c.input).slice(0, 200)}</pre></td>
                    <td><pre style={{ margin: 0, maxWidth: 280, whiteSpace: "pre-wrap" }}>{JSON.stringify(c.expected ?? c.expected_block).slice(0, 200)}</pre></td>
                    {results && <td>{r ? r.blended?.toFixed(2) : "—"}</td>}
                    {results && <td>{r ? <span className={`badge ${r.guardrails_passed ? "good" : "bad"}`}>{r.guardrails_passed ? "ok" : "fail"}</span> : "—"}</td>}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
