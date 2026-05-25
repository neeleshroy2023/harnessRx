"""Eval run management API."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.runner.runner import ALL_FEATURES, run_eval
from app.storage import results as results_store

router = APIRouter(prefix="/eval", tags=["eval"])

_RUNS: dict[str, dict[str, Any]] = {}


class StartRunBody(BaseModel):
    features: list[str] | None = None
    use_judge: bool = True
    label: str | None = None


class StartRunResponse(BaseModel):
    run_id: str
    status: str


async def _execute(run_id: str, body: StartRunBody) -> None:
    _RUNS[run_id]["status"] = "running"
    try:
        feats = body.features or ALL_FEATURES
        out_path = results_store.new_run_path(body.label or run_id)
        data = await run_eval(
            feats,
            use_judge=body.use_judge,
            label=body.label,
            out_path=out_path,
        )
        _RUNS[run_id].update({
            "status": "completed",
            "result_path": str(out_path),
            "overall": data["overall"],
            "features": {k: v["score"] for k, v in data["features"].items()},
        })
    except Exception as e:
        _RUNS[run_id].update({"status": "failed", "error": str(e)})


@router.post("/run", response_model=StartRunResponse)
async def start_run(body: StartRunBody) -> StartRunResponse:
    run_id = uuid.uuid4().hex[:12]
    _RUNS[run_id] = {"status": "pending", "features": body.features or ALL_FEATURES}
    asyncio.create_task(_execute(run_id, body))
    return StartRunResponse(run_id=run_id, status="pending")


@router.get("/runs")
def list_runs() -> dict:
    return {"in_memory": _RUNS, "persisted": results_store.list_runs()}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    if run_id in _RUNS:
        live = _RUNS[run_id]
        path = live.get("result_path")
        full = results_store.read_run(Path(path).stem) if path else None
        return {"live": live, "data": full}
    data = results_store.read_run(run_id)
    if data is None:
        raise HTTPException(404, "run not found")
    return {"live": None, "data": data}
