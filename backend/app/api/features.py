"""Live feature invocation for the playground UI."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.features import FEATURES
from app.guardrails import toxicity as toxicity_rail
from app.guardrails.pii import check as pii_check
from app.guardrails.prompt_injection import check as injection_check
from app.guardrails.schema import check_obj as schema_check_obj

router = APIRouter(prefix="/features", tags=["features"])


class InvokeBody(BaseModel):
    input: dict
    skip_guardrails: bool = False


def _flatten(payload: dict) -> str:
    return " ".join(str(v) for v in payload.values() if isinstance(v, (str, int, float)))


def _output_text(feature: str, output: dict) -> str:
    if feature == "summarize":
        return output.get("summary", "")
    if feature == "classify":
        return output.get("label", "")
    if feature == "rag":
        return output.get("answer", "")
    if feature == "extract":
        import json
        return json.dumps(output.get("extracted", {}))
    return ""


@router.post("/{name}/invoke")
async def invoke(name: str, body: InvokeBody) -> dict:
    if name not in FEATURES:
        raise HTTPException(404, f"unknown feature: {name}")

    in_rails: list[dict] = []
    if not body.skip_guardrails:
        text = _flatten(body.input)
        in_rails.append(pii_check(text).to_dict())
        in_rails.append(injection_check(text).to_dict())
        if any(not r["passed"] for r in in_rails):
            return {
                "blocked_input": True,
                "input_guardrails": in_rails,
                "output": None,
                "output_guardrails": [],
            }

    output = await FEATURES[name].invoke(body.input)

    out_rails: list[dict] = []
    if not body.skip_guardrails:
        text = _output_text(name, output)
        out_rails.append(pii_check(text).to_dict())
        out_rails.append((await toxicity_rail.acheck(text)).to_dict())
        if name == "extract" and isinstance(body.input.get("schema"), dict):
            extracted = output.get("extracted") or {}
            out_rails.append(schema_check_obj(extracted, body.input["schema"]).to_dict())

    return {
        "blocked_input": False,
        "input_guardrails": in_rails,
        "output": output,
        "output_guardrails": out_rails,
    }


@router.get("")
def list_features() -> dict:
    return {"features": list(FEATURES.keys())}
