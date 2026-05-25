"""Results persistence: flat JSON files under results/."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parents[3] / "results"


def ensure_dir() -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR


def new_run_path(label: str | None = None) -> Path:
    ensure_dir()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"{ts}-{label}.json" if label else f"{ts}.json"
    return RESULTS_DIR / name


def write(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return path


def list_runs() -> list[dict]:
    ensure_dir()
    out = []
    for p in sorted(RESULTS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            out.append({
                "id": p.stem,
                "path": str(p),
                "started_at": data.get("started_at"),
                "overall": data.get("overall"),
                "features": {k: v.get("score") for k, v in data.get("features", {}).items()},
            })
        except Exception:
            continue
    return out


def read_run(run_id: str) -> dict | None:
    p = RESULTS_DIR / f"{run_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
