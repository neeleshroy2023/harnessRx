"""Read-only access to YAML datasets and the last run's per-case results."""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from app.storage import results as results_store

router = APIRouter(prefix="/datasets", tags=["datasets"])

DATASETS_DIR = Path(__file__).resolve().parents[3] / "datasets"


def _list_yaml(dir_path: Path) -> list[str]:
    if not dir_path.exists():
        return []
    return sorted(p.stem for p in dir_path.glob("*.yaml"))


@router.get("")
def list_all() -> dict:
    return {
        "features": _list_yaml(DATASETS_DIR),
        "guardrails": _list_yaml(DATASETS_DIR / "guardrails"),
    }


@router.get("/{name}")
def get_dataset(name: str) -> dict:
    candidates = [DATASETS_DIR / f"{name}.yaml", DATASETS_DIR / "guardrails" / f"{name}.yaml"]
    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                cases = yaml.safe_load(f) or []
            return {"name": name, "n": len(cases), "cases": cases}
    raise HTTPException(404, f"dataset not found: {name}")


@router.get("/{name}/last-results")
def last_results(name: str) -> dict:
    runs = results_store.list_runs()
    for run in runs:
        data = results_store.read_run(run["id"])
        if data and name in data.get("cases", {}):
            return {"run_id": run["id"], "cases": data["cases"][name]}
    raise HTTPException(404, f"no recent run with cases for {name}")
