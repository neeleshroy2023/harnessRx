"""PII / secret detection. Regex-based, deterministic, runs in CI without API calls."""

from __future__ import annotations

import re

PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone_us": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "anthropic_key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
}

NAME = "pii"


def check(text: str) -> "GuardrailResult":  # type: ignore[name-defined]
    from . import GuardrailResult

    hits: list[str] = []
    for kind, pat in PATTERNS.items():
        matches = pat.findall(text)
        if matches:
            hits.append(f"{kind}: {len(matches)} match(es)")
    passed = not hits
    return GuardrailResult(
        name=NAME,
        passed=passed,
        score=1.0 if passed else 0.0,
        reasons=hits,
    )
