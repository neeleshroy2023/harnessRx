"""Shared Anthropic client with prompt caching helpers.

Uses claude-sonnet-4-6 for features and claude-haiku-4-5 for the judge.
Prompt caching applied to system prompts that repeat across cases.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from anthropic import Anthropic, AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

FEATURE_MODEL = os.getenv("HARNESS_FEATURE_MODEL", "claude-sonnet-4-6")
JUDGE_MODEL = os.getenv("HARNESS_JUDGE_MODEL", "claude-haiku-4-5-20251001")
GUARDRAIL_MODEL = os.getenv("HARNESS_GUARDRAIL_MODEL", "claude-haiku-4-5-20251001")
DEFAULT_CONCURRENCY = int(os.getenv("HARNESS_CONCURRENCY", "5"))


@lru_cache(maxsize=1)
def sync_client() -> Anthropic:
    return Anthropic()


@lru_cache(maxsize=1)
def async_client() -> AsyncAnthropic:
    return AsyncAnthropic()


def cached_system(text: str) -> list[dict[str, Any]]:
    """Wrap a system prompt for prompt caching."""
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


async def acomplete(
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 1024,
    temperature: float = 0.0,
) -> str:
    """Single-turn async completion. System prompt cached."""
    resp = await async_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=cached_system(system),
        messages=[{"role": "user", "content": user}],
    )
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()


def complete(
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 1024,
    temperature: float = 0.0,
) -> str:
    resp = sync_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=cached_system(system),
        messages=[{"role": "user", "content": user}],
    )
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()
