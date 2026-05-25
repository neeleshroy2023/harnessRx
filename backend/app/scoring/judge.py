"""Claude-as-judge scorer. Returns 1-5 score per rubric, normalized to [0,1]."""

from __future__ import annotations

import re

from app.llm.anthropic_client import JUDGE_MODEL, acomplete

SYSTEM = """You are a strict evaluation judge.
Given a TASK, an OUTPUT, and a RUBRIC, score the output from 1 to 5:
1 = unacceptable, fails the rubric badly
2 = poor, major issues
3 = acceptable, minor issues
4 = good, meets the rubric
5 = excellent, fully meets the rubric

Reply with exactly this format:
SCORE: <integer 1-5>
REASON: <one sentence>
"""

_SCORE_RE = re.compile(r"SCORE\s*:\s*([1-5])", re.I)


async def judge(task: str, output: str, rubric: str) -> tuple[float, str]:
    user = f"TASK:\n{task}\n\nOUTPUT:\n{output}\n\nRUBRIC:\n{rubric}"
    try:
        raw = await acomplete(model=JUDGE_MODEL, system=SYSTEM, user=user, max_tokens=80)
    except Exception as e:
        return 0.6, f"judge_error: {e}"
    m = _SCORE_RE.search(raw)
    if not m:
        return 0.6, f"unparseable: {raw[:60]}"
    score = int(m.group(1))
    return (score - 1) / 4.0, raw.strip()
