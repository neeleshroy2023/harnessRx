"""Prompt-injection / jailbreak detection. Heuristic patterns, deterministic."""

from __future__ import annotations

import re

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("override_instructions", re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.I)),
    ("reveal_system_prompt", re.compile(r"(reveal|show|print|repeat)\s+(your\s+)?(system|initial)\s+prompt", re.I)),
    ("role_flip", re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.I)),
    ("dan_jailbreak", re.compile(r"\b(DAN|do\s+anything\s+now)\b", re.I)),
    ("developer_mode", re.compile(r"developer\s+mode|jailbreak\s+mode", re.I)),
    ("disregard_rules", re.compile(r"(disregard|forget|bypass)\s+(your\s+)?(rules|guidelines|safety)", re.I)),
    ("act_as_unfiltered", re.compile(r"act\s+as\s+(an?\s+)?(unfiltered|uncensored|unrestricted)", re.I)),
    ("end_marker_inject", re.compile(r"</?\s*(system|instructions?|prompt)\s*>", re.I)),
]

NAME = "prompt_injection"


def check(text: str) -> "GuardrailResult":  # type: ignore[name-defined]
    from . import GuardrailResult

    hits = [name for name, pat in PATTERNS if pat.search(text)]
    passed = not hits
    return GuardrailResult(
        name=NAME,
        passed=passed,
        score=1.0 if passed else 0.0,
        reasons=hits,
    )
