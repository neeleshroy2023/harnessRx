"""FastAPI entrypoint for harnessRx."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import datasets, eval, features, guardrails

app = FastAPI(title="harnessRx API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(eval.router)
app.include_router(features.router)
app.include_router(datasets.router)
app.include_router(guardrails.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
