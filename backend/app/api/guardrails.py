"""Probe individual guardrails for the UI."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.guardrails import ALL_GUARDRAILS
from app.guardrails import schema as schema_rail
from app.guardrails import toxicity as toxicity_rail

router = APIRouter(prefix="/guardrails", tags=["guardrails"])


class CheckBody(BaseModel):
    text: str
    json_schema: dict | None = None


@router.get("")
def list_guardrails() -> dict:
    return {"guardrails": list(ALL_GUARDRAILS.keys())}


@router.post("/{name}/check")
async def check(name: str, body: CheckBody) -> dict:
    if name not in ALL_GUARDRAILS:
        raise HTTPException(404, f"unknown guardrail: {name}")
    if name == "toxicity":
        r = await toxicity_rail.acheck(body.text)
        return r.to_dict()
    if name == "schema":
        r = schema_rail.check(body.text, body.json_schema)
        return r.to_dict()
    return ALL_GUARDRAILS[name].check(body.text).to_dict()


@router.post("/check-all")
async def check_all(body: CheckBody) -> dict:
    results = {
        "pii": ALL_GUARDRAILS["pii"].check(body.text).to_dict(),
        "prompt_injection": ALL_GUARDRAILS["prompt_injection"].check(body.text).to_dict(),
        "toxicity": (await toxicity_rail.acheck(body.text)).to_dict(),
    }
    if body.json_schema is not None:
        results["schema"] = schema_rail.check(body.text, body.json_schema).to_dict()
    return results
