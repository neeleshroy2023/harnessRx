"""Deterministic heuristic scorers per feature.

Each returns a float in [0, 1] plus a dict of sub-metrics.
"""

from __future__ import annotations

import re
from typing import Any

from rouge_score import rouge_scorer

from app.guardrails import schema as schema_rail

_rouge = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


def _f1(pred: str, ref: str) -> float:
    p, r = _tokens(pred), _tokens(ref)
    if not p or not r:
        return 0.0
    common = p & r
    if not common:
        return 0.0
    prec = len(common) / len(p)
    rec = len(common) / len(r)
    return 2 * prec * rec / (prec + rec)


def score_summarize(output: dict, expected: dict) -> tuple[float, dict]:
    summary = output.get("summary", "")
    contains = expected.get("contains", [])
    if contains:
        hits = sum(1 for needle in contains if needle.lower() in summary.lower())
        contains_score = hits / len(contains)
    else:
        contains_score = 1.0
    rouge_score_val = 0.0
    if "reference" in expected:
        rouge_score_val = _rouge.score(expected["reference"], summary)["rougeL"].fmeasure
    blend = 0.6 * contains_score + 0.4 * rouge_score_val if "reference" in expected else contains_score
    return blend, {"contains": contains_score, "rougeL": rouge_score_val}


def score_classify(output: dict, expected: dict) -> tuple[float, dict]:
    pred = (output.get("label") or "").strip().lower()
    gold = (expected.get("label") or "").strip().lower()
    correct = 1.0 if pred == gold else 0.0
    return correct, {"accuracy": correct, "pred": pred, "gold": gold}


def score_rag(output: dict, expected: dict) -> tuple[float, dict]:
    answer = output.get("answer", "")
    f1 = _f1(answer, expected.get("answer", ""))
    expected_cites = set(expected.get("citations", []))
    got_cites = set(output.get("citations", []))
    if expected_cites:
        cite_recall = len(expected_cites & got_cites) / len(expected_cites)
        cite_precision = (len(expected_cites & got_cites) / len(got_cites)) if got_cites else 0.0
        cite_f1 = (
            2 * cite_precision * cite_recall / (cite_precision + cite_recall)
            if (cite_precision + cite_recall) > 0
            else 0.0
        )
    else:
        cite_f1 = 1.0 if not got_cites else 0.5
    # I-don't-know cases: gold answer literally "I don't know."
    if expected.get("answer", "").strip().lower().startswith("i don't know"):
        f1 = 1.0 if "don't know" in answer.lower() or "do not know" in answer.lower() else 0.0
    blend = 0.6 * f1 + 0.4 * cite_f1
    return blend, {"answer_f1": f1, "citation_f1": cite_f1}


def score_extract(output: dict, expected: dict) -> tuple[float, dict]:
    extracted = output.get("extracted") or {}
    schema = expected.get("schema")
    fields = expected.get("fields", {})
    schema_pass = 1.0
    if schema is not None:
        r = schema_rail.check_obj(extracted, schema)
        schema_pass = 1.0 if r.passed else 0.0
    if not fields:
        return schema_pass, {"schema": schema_pass, "field_acc": 1.0}
    correct = 0
    for k, v in fields.items():
        if _values_equal(extracted.get(k), v):
            correct += 1
    field_acc = correct / len(fields)
    blend = 0.4 * schema_pass + 0.6 * field_acc
    return blend, {"schema": schema_pass, "field_acc": field_acc}


def _values_equal(a: Any, b: Any) -> bool:
    if a is None and b is None:
        return True
    if isinstance(a, str) and isinstance(b, str):
        return a.strip().lower() == b.strip().lower()
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < 1e-6
    if isinstance(a, list) and isinstance(b, list):
        return [str(x).strip().lower() for x in a] == [str(x).strip().lower() for x in b]
    return a == b


SCORERS = {
    "summarize": score_summarize,
    "classify": score_classify,
    "rag": score_rag,
    "extract": score_extract,
}
