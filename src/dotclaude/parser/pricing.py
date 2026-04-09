"""Pricing data and cost calculation, ported from TypeScript pricing.ts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    """Pricing per 1 million tokens in USD."""

    input: float
    output: float
    cache_write: float
    cache_read: float


MODEL_PRICING: dict[str, ModelPricing] = {
    "claude-opus-4-6": ModelPricing(input=15, output=75, cache_write=18.75, cache_read=1.5),
    "claude-opus-4-5-20250514": ModelPricing(input=15, output=75, cache_write=18.75, cache_read=1.5),
    "claude-sonnet-4-6": ModelPricing(input=3, output=15, cache_write=3.75, cache_read=0.3),
    "claude-sonnet-4-5-20250514": ModelPricing(input=3, output=15, cache_write=3.75, cache_read=0.3),
    "claude-haiku-4-5-20251001": ModelPricing(input=0.80, output=4, cache_write=1, cache_read=0.08),
}


def resolve_pricing(model: str) -> ModelPricing | None:
    """Resolve the pricing entry for a given model string.

    Tries exact match first, then prefix match (e.g. ``claude-opus`` → first
    model whose key starts with ``claude-opus``).
    Returns None when no pricing data is available.
    """
    # Exact match
    exact = MODEL_PRICING.get(model)
    if exact is not None:
        return exact

    # Prefix / fuzzy match — find first key that is a prefix of the model name
    # or whose model name is a prefix of the key.
    for key, pricing in MODEL_PRICING.items():
        if model.startswith(key) or key.startswith(model):
            return pricing

    # Partial substring match as last resort
    for key, pricing in MODEL_PRICING.items():
        if "opus" in model and "opus" in key:
            return pricing
        if "sonnet" in model and "sonnet" in key:
            return pricing
        if "haiku" in model and "haiku" in key:
            return pricing

    return None


@dataclass
class UsageForCost:
    """Token usage data needed for cost calculation."""

    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


def calculate_cost(model: str, usage: UsageForCost) -> float:
    """Calculate the cost in USD for a single assistant message.

    Returns 0.0 when no pricing data exists for the model.
    """
    pricing = resolve_pricing(model)
    if pricing is None:
        return 0.0

    M = 1_000_000
    input_cost = (usage.input_tokens / M) * pricing.input
    output_cost = (usage.output_tokens / M) * pricing.output
    cache_write_cost = (usage.cache_creation_input_tokens / M) * pricing.cache_write
    cache_read_cost = (usage.cache_read_input_tokens / M) * pricing.cache_read

    return input_cost + output_cost + cache_write_cost + cache_read_cost
