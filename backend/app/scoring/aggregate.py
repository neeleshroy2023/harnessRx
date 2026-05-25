"""Per-feature and overall aggregate scoring."""

from __future__ import annotations

from statistics import mean


def aggregate_cases(case_results: list[dict]) -> dict:
    """Aggregate scores across cases for a feature.

    case_results items: {id, blended, heuristic, judge, guardrails_passed}
    """
    if not case_results:
        return {"n": 0, "score": 0.0, "heuristic": 0.0, "judge": 0.0, "guardrail_pass_rate": 0.0}

    heur = mean(c["heuristic"] for c in case_results)
    judge_vals = [c["judge"] for c in case_results if c.get("judge") is not None]
    judge_score = mean(judge_vals) if judge_vals else 0.0
    blended = mean(c["blended"] for c in case_results)
    gpr = mean(1.0 if c["guardrails_passed"] else 0.0 for c in case_results)
    return {
        "n": len(case_results),
        "score": blended,
        "heuristic": heur,
        "judge": judge_score,
        "guardrail_pass_rate": gpr,
    }


def overall(features: dict[str, dict]) -> float:
    scores = [f["score"] for f in features.values() if f.get("n", 0) > 0]
    return mean(scores) if scores else 0.0
