"""Production-style Claude features under test.

Each feature exposes async invoke(input: dict) -> dict.
"""

from . import classify, extract, rag, summarize

FEATURES = {
    "summarize": summarize,
    "classify": classify,
    "rag": rag,
    "extract": extract,
}

__all__ = ["FEATURES", "summarize", "classify", "rag", "extract"]
