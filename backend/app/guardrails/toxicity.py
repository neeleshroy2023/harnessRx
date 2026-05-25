"""Toxicity guardrail. Claude Haiku judge with cached system prompt + fast keyword pre-filter."""

from __future__ import annotations

import asyncio
import re

from app.llm.anthropic_client import GUARDRAIL_MODEL, acomplete

NAME = "toxicity"

# Cheap pre-filter: obvious slurs / threats. Real classifier runs only on signal.
FAST_PATTERNS = [
    re.compile(r"\b(kill|murder|attack)\s+(yourself|him|her|them|all)\b", re.I),
    re.compile(r"\b(i\s+hate\s+you|you\s+are\s+(worthless|trash|garbage))\b", re.I),
]

SYSTEM = """You are a safety classifier. Decide whether the user's text is TOXIC.
Toxic = hate speech, harassment, threats, sexual content involving minors, self-harm encouragement, or instructions to harm others.
Reply with exactly one token: SAFE or TOXIC.
"""


def fast_screen(text: str) -> list[str]:
    return [p.pattern for p in FAST_PATTERNS if p.search(text)]


async def acheck(text: str) -> "GuardrailResult":  # type: ignore[name-defined]
    from . import GuardrailResult

    fast = fast_screen(text)
    if fast:
        return GuardrailResult(name=NAME, passed=False, score=0.0, reasons=["fast_pattern"])

    try:
        verdict = await acomplete(
            model=GUARDRAIL_MODEL,
            system=SYSTEM,
            user=text,
            max_tokens=5,
        )
    except Exception as e:
        return GuardrailResult(name=NAME, passed=True, score=1.0, reasons=[f"judge_error: {e}"])

    verdict_u = verdict.strip().upper()
    if "TOXIC" in verdict_u:
        return GuardrailResult(name=NAME, passed=False, score=0.0, reasons=["judge:TOXIC"])
    return GuardrailResult(name=NAME, passed=True, score=1.0, reasons=[])


def check(text: str) -> "GuardrailResult":  # type: ignore[name-defined]
    """Sync wrapper for UI quick-probes."""
    return asyncio.run(acheck(text))
