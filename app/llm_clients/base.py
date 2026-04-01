from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from app.prompts.fashion_classifier import ClassificationPrompt


@dataclass(slots=True)
class LLMRequest:
    image_path: Path
    prompt: ClassificationPrompt
    metadata: dict[str, str | None] = field(default_factory=dict)
    trace_id: str | None = None


@dataclass(slots=True)
class LLMResponse:
    raw_text: str
    raw_payload: dict
    model: str
    usage: "LLMUsage | None" = None


@dataclass(slots=True)
class LLMUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_input_tokens: int = 0


class BaseLLMClient(ABC):
    @abstractmethod
    def classify_image(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError

    def interpret_search_query(
        self,
        query: str,
        available_filters: dict[str, list[str]] | None = None,
        trace_id: str | None = None,
    ) -> LLMResponse | None:
        return None
