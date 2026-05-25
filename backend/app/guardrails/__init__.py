"""Input/output guardrails. Each module exports check(text) -> GuardrailResult."""

from dataclasses import asdict, dataclass, field


@dataclass
class GuardrailResult:
    name: str
    passed: bool
    score: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


from . import pii, prompt_injection, schema, toxicity  # noqa: E402

INPUT_GUARDRAILS = [pii, prompt_injection]
OUTPUT_GUARDRAILS = [pii, toxicity]

ALL_GUARDRAILS = {
    "pii": pii,
    "prompt_injection": prompt_injection,
    "schema": schema,
    "toxicity": toxicity,
}

__all__ = [
    "GuardrailResult",
    "INPUT_GUARDRAILS",
    "OUTPUT_GUARDRAILS",
    "ALL_GUARDRAILS",
    "pii",
    "prompt_injection",
    "schema",
    "toxicity",
]
