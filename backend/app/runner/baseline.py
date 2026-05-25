"""Baseline diff: compare a fresh run vs committed baseline.

Exit code 0 = no regression. Exit code 1 = regression detected.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_THRESHOLD = 0.03  # 3-point drop


def compare(baseline: dict, current: dict, threshold: float = DEFAULT_THRESHOLD) -> dict:
    regressions: list[dict] = []
    feature_deltas: dict[str, float] = {}
    base_features = baseline.get("features", {})
    cur_features = current.get("features", {})
    for name, base in base_features.items():
        cur = cur_features.get(name, {})
        base_s = base.get("score", 0.0)
        cur_s = cur.get("score", 0.0)
        delta = cur_s - base_s
        feature_deltas[name] = delta
        if base_s - cur_s > threshold:
            regressions.append({
                "kind": "feature_score",
                "name": name,
                "baseline": base_s,
                "current": cur_s,
                "delta": delta,
            })

    guardrail_deltas: dict[str, float] = {}
    base_g = baseline.get("guardrails", {})
    cur_g = current.get("guardrails", {})
    for name, base in base_g.items():
        cur = cur_g.get(name, {})
        base_p = base.get("pass_rate", 1.0)
        cur_p = cur.get("pass_rate", 1.0)
        delta = cur_p - base_p
        guardrail_deltas[name] = delta
        if cur_p < base_p:
            regressions.append({
                "kind": "guardrail_pass_rate",
                "name": name,
                "baseline": base_p,
                "current": cur_p,
                "delta": delta,
            })

    overall_delta = current.get("overall", 0.0) - baseline.get("overall", 0.0)
    return {
        "regressed": bool(regressions),
        "regressions": regressions,
        "feature_deltas": feature_deltas,
        "guardrail_deltas": guardrail_deltas,
        "overall_delta": overall_delta,
        "threshold": threshold,
    }


def render_markdown(diff: dict, baseline: dict, current: dict) -> str:
    lines = ["## Eval Run vs Baseline", ""]
    lines.append(f"**Overall**: {current.get('overall', 0):.3f} (baseline {baseline.get('overall', 0):.3f}, delta {diff['overall_delta']:+.3f})")
    lines.append("")
    lines.append("| Feature | Baseline | Current | Δ |")
    lines.append("|---|---|---|---|")
    for name in sorted(baseline.get("features", {}).keys()):
        b = baseline["features"][name].get("score", 0.0)
        c = current.get("features", {}).get(name, {}).get("score", 0.0)
        lines.append(f"| {name} | {b:.3f} | {c:.3f} | {c - b:+.3f} |")
    if baseline.get("guardrails"):
        lines.append("")
        lines.append("| Guardrail | Baseline pass-rate | Current | Δ |")
        lines.append("|---|---|---|---|")
        for name in sorted(baseline["guardrails"].keys()):
            b = baseline["guardrails"][name].get("pass_rate", 1.0)
            c = current.get("guardrails", {}).get(name, {}).get("pass_rate", 1.0)
            lines.append(f"| {name} | {b:.3f} | {c:.3f} | {c - b:+.3f} |")
    if diff["regressed"]:
        lines.append("")
        lines.append("### Regressions")
        for r in diff["regressions"]:
            lines.append(f"- **{r['kind']}**: `{r['name']}` baseline {r['baseline']:.3f} → current {r['current']:.3f} ({r['delta']:+.3f})")
    else:
        lines.append("")
        lines.append("**No regressions detected.**")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare run vs baseline.")
    ap.add_argument("baseline", type=Path)
    ap.add_argument("current", type=Path)
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--markdown", type=Path, default=None, help="Write a markdown report.")
    args = ap.parse_args()

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    current = json.loads(args.current.read_text(encoding="utf-8"))
    diff = compare(baseline, current, args.threshold)

    md = render_markdown(diff, baseline, current)
    print(md)
    if args.markdown:
        args.markdown.write_text(md, encoding="utf-8")
    sys.exit(1 if diff["regressed"] else 0)


if __name__ == "__main__":
    main()
