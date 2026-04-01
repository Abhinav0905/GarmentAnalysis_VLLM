from __future__ import annotations

from dataclasses import dataclass

from app.llm_clients.base import LLMUsage


@dataclass(slots=True)
class ModelPricing:
    input_cost_per_million: float
    output_cost_per_million: float
    cached_input_cost_per_million: float | None = None


@dataclass(slots=True)
class TokenUsageSummary:
    source: str
    model_name: str
    token_estimate: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_input_tokens: int
    input_cost_usd: float | None
    output_cost_usd: float | None
    total_cost_usd: float | None


KNOWN_MODEL_PRICING: dict[str, ModelPricing] = {
    # Source: OpenAI model page for GPT-4o mini and the official API pricing page.
    "gpt-4o-mini": ModelPricing(input_cost_per_million=0.15, cached_input_cost_per_million=0.075, output_cost_per_million=0.60),
    "gpt-4o-mini-2024-07-18": ModelPricing(input_cost_per_million=0.15, cached_input_cost_per_million=0.075, output_cost_per_million=0.60),
    "gpt-5.4": ModelPricing(input_cost_per_million=2.50, cached_input_cost_per_million=0.25, output_cost_per_million=15.00),
    "gpt-5.4-mini": ModelPricing(input_cost_per_million=0.75, cached_input_cost_per_million=0.075, output_cost_per_million=4.50),
    "gpt-5.4-nano": ModelPricing(input_cost_per_million=0.20, cached_input_cost_per_million=0.02, output_cost_per_million=1.25),
}


class TokenCalculator:
    """Use exact OpenAI usage when available, and heuristics only as a fallback."""

    def estimate_text_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    def estimate_image_tokens(self, size_in_bytes: int) -> int:
        if size_in_bytes <= 0:
            return 0
        return max(50, size_in_bytes // 800)

    def estimate_total(self, prompt_text: str, size_in_bytes: int) -> int:
        return self.estimate_text_tokens(prompt_text) + self.estimate_image_tokens(size_in_bytes)

    def pricing_for_model(
        self,
        model_name: str,
        input_cost_per_million: float | None = None,
        output_cost_per_million: float | None = None,
        cached_input_cost_per_million: float | None = None,
    ) -> ModelPricing | None:
        if input_cost_per_million is not None and output_cost_per_million is not None:
            return ModelPricing(
                input_cost_per_million=input_cost_per_million,
                output_cost_per_million=output_cost_per_million,
                cached_input_cost_per_million=cached_input_cost_per_million,
            )
        return KNOWN_MODEL_PRICING.get(model_name)

    def build_usage_summary(
        self,
        model_name: str,
        usage: LLMUsage | None,
        token_estimate: int,
        pricing: ModelPricing | None,
    ) -> TokenUsageSummary:
        if usage is None:
            return TokenUsageSummary(
                source="estimate",
                model_name=model_name,
                token_estimate=token_estimate,
                input_tokens=0,
                output_tokens=0,
                total_tokens=token_estimate,
                cached_input_tokens=0,
                input_cost_usd=None,
                output_cost_usd=None,
                total_cost_usd=None,
            )

        input_cost_usd = None
        output_cost_usd = None
        total_cost_usd = None
        if pricing is not None:
            cached_input_tokens = usage.cached_input_tokens
            uncached_input_tokens = max(usage.input_tokens - cached_input_tokens, 0)
            uncached_input_cost = (uncached_input_tokens / 1_000_000) * pricing.input_cost_per_million
            cached_rate = pricing.cached_input_cost_per_million
            cached_input_cost = 0.0
            if cached_rate is not None:
                cached_input_cost = (cached_input_tokens / 1_000_000) * cached_rate
            else:
                cached_input_cost = (cached_input_tokens / 1_000_000) * pricing.input_cost_per_million
            output_cost = (usage.output_tokens / 1_000_000) * pricing.output_cost_per_million
            input_cost_usd = round(uncached_input_cost + cached_input_cost, 8)
            output_cost_usd = round(output_cost, 8)
            total_cost_usd = round(input_cost_usd + output_cost_usd, 8)

        return TokenUsageSummary(
            source="openai_usage",
            model_name=model_name,
            token_estimate=token_estimate,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            cached_input_tokens=usage.cached_input_tokens,
            input_cost_usd=input_cost_usd,
            output_cost_usd=output_cost_usd,
            total_cost_usd=total_cost_usd,
        )
