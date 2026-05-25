"""Classification / routing feature: text -> label from fixed set."""

from __future__ import annotations

from app.llm.anthropic_client import FEATURE_MODEL, acomplete

LABELS = ["billing", "technical_support", "account", "feedback", "sales", "other"]

SYSTEM = f"""You are a customer-support intent classifier.
Given a message, output exactly one label from this set:
{", ".join(LABELS)}

Rules:
- Output only the label, lowercase, no punctuation, no explanation.
- If unsure, output: other
"""


async def invoke(payload: dict) -> dict:
    message = payload["message"]
    raw = await acomplete(
        model=FEATURE_MODEL,
        system=SYSTEM,
        user=message,
        max_tokens=20,
    )
    label = raw.strip().lower().split()[0] if raw.strip() else "other"
    if label not in LABELS:
        label = "other"
    return {"label": label}
