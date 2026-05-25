"""Eval orchestrator.

Per case: input guardrails -> feature invoke -> output guardrails -> heuristic + judge scoring -> persist.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from app.features import FEATURES
from app.guardrails import INPUT_GUARDRAILS, OUTPUT_GUARDRAILS
from app.guardrails import toxicity as toxicity_rail
from app.llm.anthropic_client import DEFAULT_CONCURRENCY
from app.scoring import aggregate, judge
from app.scoring.heuristic import SCORERS
from app.storage import results as results_store

ROOT = Path(__file__).resolve().parents[3]
DATASETS_DIR = ROOT / "datasets"
GUARDRAIL_DATASETS_DIR = DATASETS_DIR / "guardrails"

ALL_FEATURES = ["summarize", "classify", "rag", "extract"]


def load_yaml(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def _flatten_for_text(payload: dict) -> str:
    return " ".join(str(v) for v in payload.values() if isinstance(v, (str, int, float)))


async def _run_input_guardrails(payload: dict) -> list[dict]:
    text = _flatten_for_text(payload)
    out: list[dict] = []
    for rail in INPUT_GUARDRAILS:
        if rail.NAME == "toxicity":
            r = await toxicity_rail.acheck(text)
        else:
            r = rail.check(text)
        out.append(r.to_dict())
    return out


async def _run_output_guardrails(output_text: str) -> list[dict]:
    out: list[dict] = []
    for rail in OUTPUT_GUARDRAILS:
        if rail.NAME == "toxicity":
            r = await toxicity_rail.acheck(output_text)
        else:
            r = rail.check(output_text)
        out.append(r.to_dict())
    return out


def _output_text(feature: str, output: dict) -> str:
    if feature == "summarize":
        return output.get("summary", "")
    if feature == "classify":
        return output.get("label", "")
    if feature == "rag":
        return output.get("answer", "")
    if feature == "extract":
        return json.dumps(output.get("extracted", {}))
    return json.dumps(output)


async def _run_case(
    feature: str,
    case: dict,
    sem: asyncio.Semaphore,
    use_judge: bool,
) -> dict:
    async with sem:
        case_id = case.get("id", "?")
        payload = case["input"]
        expected = case.get("expected", {})

        # Input guardrails
        in_rails = await _run_input_guardrails(payload)
        in_blocked = any(not r["passed"] for r in in_rails)
        if in_blocked and case.get("expected_block_input"):
            # Adversarial case: blocking is the correct behavior.
            return _result(
                case_id, blended=1.0, heuristic=1.0, judge=None,
                guardrails_passed=True, in_rails=in_rails, out_rails=[],
                output={"blocked": True}, notes=["input correctly blocked"],
            )
        if in_blocked:
            return _result(
                case_id, blended=0.0, heuristic=0.0, judge=None,
                guardrails_passed=False, in_rails=in_rails, out_rails=[],
                output={"blocked": True}, notes=["input blocked unexpectedly"],
            )

        # Feature invoke
        try:
            output = await FEATURES[feature].invoke(payload)
        except Exception as e:
            return _result(
                case_id, blended=0.0, heuristic=0.0, judge=None,
                guardrails_passed=False, in_rails=in_rails, out_rails=[],
                output={"error": str(e)}, notes=[f"invoke_error: {e}"],
            )

        out_text = _output_text(feature, output)
        out_rails = await _run_output_guardrails(out_text)
        out_blocked = any(not r["passed"] for r in out_rails)

        heur, sub = SCORERS[feature](output, expected)

        judge_score: float | None = None
        judge_reason: str | None = None
        if use_judge and "judge_rubric" in expected:
            task_desc = f"Feature: {feature}\nInput: {json.dumps(payload)[:600]}"
            judge_score, judge_reason = await judge.judge(
                task_desc, out_text, expected["judge_rubric"]
            )

        if judge_score is not None:
            blended = 0.5 * heur + 0.5 * judge_score
        else:
            blended = heur

        guardrails_passed = (not out_blocked) and (not in_blocked)
        if out_blocked:
            blended = min(blended, 0.0)

        return _result(
            case_id, blended=blended, heuristic=heur, judge=judge_score,
            guardrails_passed=guardrails_passed, in_rails=in_rails, out_rails=out_rails,
            output=output, notes=[], sub=sub, judge_reason=judge_reason,
        )


def _result(case_id: str, **kw: Any) -> dict:
    return {"id": case_id, **kw}


async def _run_feature(feature: str, cases: list[dict], concurrency: int, use_judge: bool) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)
    coros = [_run_case(feature, c, sem, use_judge) for c in cases]
    return await asyncio.gather(*coros)


async def _run_guardrail_set(name: str, cases: list[dict]) -> dict:
    """Adversarial-input cases: rail should block. Counts pass-rate of correct blocks."""
    from app.guardrails import ALL_GUARDRAILS

    rail = ALL_GUARDRAILS[name]
    correct = 0
    details = []
    for case in cases:
        text = case["input"]
        should_block = case.get("expected_block", True)
        if hasattr(rail, "acheck"):
            r = await rail.acheck(text)
        else:
            r = rail.check(text)
        blocked = not r.passed
        ok = blocked == should_block
        if ok:
            correct += 1
        details.append({
            "id": case.get("id"),
            "expected_block": should_block,
            "blocked": blocked,
            "reasons": r.reasons,
            "ok": ok,
        })
    n = len(cases)
    return {"n": n, "pass_rate": (correct / n) if n else 1.0, "details": details}


async def run_eval(
    features: list[str],
    *,
    use_judge: bool = True,
    concurrency: int = DEFAULT_CONCURRENCY,
    label: str | None = None,
    out_path: Path | None = None,
) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    feat_results: dict[str, dict] = {}
    case_dumps: dict[str, list[dict]] = {}
    for feat in features:
        path = DATASETS_DIR / f"{feat}.yaml"
        if not path.exists():
            continue
        cases = load_yaml(path)
        per_case = await _run_feature(feat, cases, concurrency, use_judge)
        case_dumps[feat] = per_case
        feat_results[feat] = aggregate.aggregate_cases(per_case)

    guardrail_results: dict[str, dict] = {}
    if GUARDRAIL_DATASETS_DIR.exists():
        for path in sorted(GUARDRAIL_DATASETS_DIR.glob("*.yaml")):
            name = path.stem
            mapping = {"pii": "pii", "injection": "prompt_injection", "toxicity": "toxicity"}
            rail_name = mapping.get(name)
            if rail_name is None:
                continue
            cases = load_yaml(path)
            guardrail_results[rail_name] = await _run_guardrail_set(rail_name, cases)

    finished = datetime.now(timezone.utc).isoformat()
    overall_score = aggregate.overall(feat_results)
    data = {
        "started_at": started,
        "finished_at": finished,
        "features": feat_results,
        "guardrails": {k: {"n": v["n"], "pass_rate": v["pass_rate"]} for k, v in guardrail_results.items()},
        "overall": overall_score,
        "cases": case_dumps,
        "guardrail_details": guardrail_results,
        "config": {"use_judge": use_judge, "concurrency": concurrency},
    }
    if out_path is None:
        out_path = results_store.new_run_path(label)
    results_store.write(out_path, data)
    data["path"] = str(out_path)
    return data


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run eval suite.")
    ap.add_argument(
        "--features",
        default="all",
        help=f"Comma-separated subset of: {','.join(ALL_FEATURES)}, or 'all'.",
    )
    ap.add_argument("--no-judge", action="store_true", help="Skip Claude-as-judge scoring.")
    ap.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    ap.add_argument("--out", type=str, default=None, help="Output JSON path.")
    ap.add_argument("--label", type=str, default=None, help="Label appended to result filename.")
    return ap.parse_args()


def main() -> None:
    args = _parse_args()
    feats = ALL_FEATURES if args.features == "all" else [f.strip() for f in args.features.split(",")]
    out_path = Path(args.out) if args.out else None
    result = asyncio.run(
        run_eval(
            feats,
            use_judge=not args.no_judge,
            concurrency=args.concurrency,
            label=args.label,
            out_path=out_path,
        )
    )
    print(json.dumps({
        "overall": result["overall"],
        "features": {k: v["score"] for k, v in result["features"].items()},
        "guardrails": result["guardrails"],
        "path": result.get("path"),
    }, indent=2))


if __name__ == "__main__":
    main()
