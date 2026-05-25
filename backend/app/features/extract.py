"""Structured extraction feature: text + JSON schema -> JSON object."""

from __future__ import annotations

import json
import re

from app.llm.anthropic_client import FEATURE_MODEL, acomplete

SYSTEM = """You extract structured data from unstructured text.
You will receive a JSON Schema and a text. Return ONLY a valid JSON object that conforms to the schema.

Rules:
- Output a single JSON object. No prose, no markdown fences, no commentary.
- If a required field is not present in the text, use null.
- Preserve numeric types (numbers vs strings) as the schema dictates.
"""


def _extract_json(raw: str) -> dict:
    """Tolerant JSON parser: strips fences, finds first { ... } block."""
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", s, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


async def invoke(payload: dict) -> dict:
    text = payload["text"]
    schema = payload["schema"]
    user_prompt = (
        f"JSON Schema:\n{json.dumps(schema, indent=2)}\n\nText:\n{text}\n\nReturn the JSON object."
    )
    raw = await acomplete(
        model=FEATURE_MODEL,
        system=SYSTEM,
        user=user_prompt,
        max_tokens=600,
    )
    parsed = _extract_json(raw)
    return {"extracted": parsed, "raw": raw}
