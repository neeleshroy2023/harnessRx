"""JSON Schema validation guardrail. Used for structured-extraction outputs."""

from __future__ import annotations

import json
from typing import Any

import jsonschema

NAME = "schema"


def check_obj(obj: Any, schema: dict) -> "GuardrailResult":  # type: ignore[name-defined]
    from . import GuardrailResult

    try:
        jsonschema.validate(instance=obj, schema=schema)
        return GuardrailResult(name=NAME, passed=True, score=1.0, reasons=[])
    except jsonschema.ValidationError as e:
        return GuardrailResult(
            name=NAME, passed=False, score=0.0, reasons=[f"validation: {e.message}"]
        )
    except jsonschema.SchemaError as e:
        return GuardrailResult(
            name=NAME, passed=False, score=0.0, reasons=[f"bad schema: {e.message}"]
        )


def check(text: str, schema: dict | None = None) -> "GuardrailResult":  # type: ignore[name-defined]
    """Parse text as JSON then validate. If schema omitted only checks parseability."""
    from . import GuardrailResult

    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        return GuardrailResult(name=NAME, passed=False, score=0.0, reasons=[f"json parse: {e}"])
    if schema is None:
        return GuardrailResult(name=NAME, passed=True, score=1.0, reasons=[])
    return check_obj(obj, schema)
