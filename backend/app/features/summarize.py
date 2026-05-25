"""Summarization feature: text -> concise summary."""

from __future__ import annotations

from app.llm.anthropic_client import FEATURE_MODEL, acomplete

SYSTEM = """You are a precise summarizer. Produce a faithful summary of the user's text.
Rules:
- 2-3 sentences max.
- Preserve all proper nouns, numbers, and dates verbatim.
- Do not invent facts not present in the source.
- Do not add commentary or hedging.
Return only the summary, no preamble.
"""


async def invoke(payload: dict) -> dict:
    text = payload["text"]
    summary = await acomplete(
        model=FEATURE_MODEL,
        system=SYSTEM,
        user=text,
        max_tokens=300,
    )
    return {"summary": summary}
