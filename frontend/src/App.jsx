import { NavLink, Route, Routes, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Playground from "./pages/Playground.jsx";
import Datasets from "./pages/Datasets.jsx";
import Guardrails from "./pages/Guardrails.jsx";

export default function App() {
  return (
    <>
      <header className="app-header">
        <h1>harnessRx <span className="muted">— Claude eval + guardrails</span></h1>
        <nav className="app-nav">
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/playground">Playground</NavLink>
          <NavLink to="/datasets">Datasets</NavLink>
          <NavLink to="/guardrails">Guardrails</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/playground" element={<Playground />} />
          <Route path="/datasets" element={<Datasets />} />
          <Route path="/guardrails" element={<Guardrails />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
