from __future__ import annotations

import json
import re
from pathlib import Path

from app.llm_clients.base import BaseLLMClient, LLMRequest, LLMResponse
from app.utils.helpers import list_from_text, parse_location_hint


class MockFashionLLMClient(BaseLLMClient):
    """Deterministic local client for zero-setup demos and tests."""

    def classify_image(self, request: LLMRequest) -> LLMResponse:
        filename = request.image_path.name.lower()
        location = parse_location_hint(request.metadata.get("location_hint"))
        payload = {
            "description": self._build_description(filename),
            "garment_type": self._pick_value(
                filename,
                {
                    "dress": "dress",
                    "jacket": "jacket",
                    "coat": "coat",
                    "jean": "jeans",
                    "pant": "pants",
                    "shirt": "shirt",
                    "skirt": "skirt",
                    "hoodie": "hoodie",
                },
                default="fashion look",
            ),
            "style": self._pick_value(
                filename,
                {
                    "street": "streetwear",
                    "tailor": "tailored",
                    "leather": "edgy",
                    "formal": "formal",
                    "sport": "sporty",
                    "vintage": "vintage",
                },
                default="contemporary",
            ),
            "material": self._pick_value(
                filename,
                {
                    "leather": "leather",
                    "denim": "denim",
                    "wool": "wool",
                    "linen": "linen",
                    "knit": "knit",
                },
                default="mixed fabric",
            ),
            "color_palette": list_from_text(
                self._pick_value(
                    filename,
                    {
                        "black": "black, white",
                        "white": "white, beige",
                        "blue": "blue, white",
                        "red": "red, black",
                        "green": "green, tan",
                    },
                    default="black, neutral",
                )
            ),
            "pattern": self._pick_value(
                filename,
                {
                    "stripe": "striped",
                    "check": "checked",
                    "print": "printed",
                    "floral": "floral",
                    "plain": "solid",
                },
                default="solid",
            ),
            "season": self._pick_value(
                filename,
                {
                    "coat": "winter",
                    "knit": "winter",
                    "dress": "spring",
                    "linen": "summer",
                    "hoodie": "fall",
                },
                default="transitional",
            ),
            "occasion": self._pick_value(
                filename,
                {
                    "formal": "event dressing",
                    "street": "street style",
                    "sport": "active casual",
                    "dress": "day-to-night",
                },
                default="everyday fashion",
            ),
            "consumer_profile": self._pick_value(
                filename,
                {
                    "kids": "youth",
                    "men": "menswear shopper",
                    "women": "womenswear shopper",
                },
                default="trend-aware shopper",
            ),
            "trend_notes": [
                "strong silhouette",
                "commercial styling",
            ],
            "location_context": location,
        }
        return LLMResponse(
            raw_text=json.dumps(payload),
            raw_payload=payload,
            model="mock-fashion-client",
        )

    def interpret_search_query(
        self,
        query: str,
        available_filters: dict[str, list[str]] | None = None,
        trace_id: str | None = None,
    ) -> LLMResponse:
        available_filters = available_filters or {}
        lowered_query = query.lower()
        payload = {
            "full_text_query": query,
            "garment_type": self._match_filter(lowered_query, available_filters.get("garment_type", [])),
            "style": self._match_filter(lowered_query, available_filters.get("style", [])),
            "material": self._match_filter(lowered_query, available_filters.get("material", [])),
            "color": self._match_filter(lowered_query, available_filters.get("color", [])),
            "pattern": self._match_filter(lowered_query, available_filters.get("pattern", [])),
            "occasion": self._match_filter(lowered_query, available_filters.get("occasion", [])),
            "consumer_profile": self._match_filter(lowered_query, available_filters.get("consumer_profile", [])),
            "season": self._match_filter(lowered_query, available_filters.get("season", [])),
            "designer": self._match_filter(lowered_query, available_filters.get("designer", [])),
            "continent": self._match_filter(lowered_query, available_filters.get("continent", [])),
            "country": self._match_filter(lowered_query, available_filters.get("country", [])),
            "city": self._match_filter(lowered_query, available_filters.get("city", [])),
            "year": self._match_year(lowered_query, available_filters.get("year", [])),
            "month": self._match_month(lowered_query, available_filters.get("month", [])),
        }
        payload["full_text_query"] = self._remaining_query_text(query, payload)
        return LLMResponse(
            raw_text=json.dumps(payload),
            raw_payload=payload,
            model="mock-fashion-search-client",
        )

    def _build_description(self, filename: str) -> str:
        stem = Path(filename).stem.replace("-", " ").replace("_", " ")
        return f"Fashion reference image with a {stem or 'styled garment'}."

    def _pick_value(self, text: str, choices: dict[str, str], default: str) -> str:
        for key, value in choices.items():
            if key in text:
                return value
        return default

    def _match_filter(self, lowered_query: str, choices: list[str]) -> str | None:
        for choice in sorted(choices, key=len, reverse=True):
            if choice.lower() in lowered_query:
                return choice
        return None

    def _match_year(self, lowered_query: str, choices: list[str]) -> int | None:
        match = re.search(r"\b(20\d{2})\b", lowered_query)
        if not match:
            return None
        value = int(match.group(1))
        if choices and str(value) not in {str(choice) for choice in choices}:
            return None
        return value

    def _match_month(self, lowered_query: str, choices: list[str]) -> int | None:
        month_names = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }
        for name, number in month_names.items():
            if name in lowered_query:
                if choices and str(number) not in {str(choice) for choice in choices}:
                    return None
                return number
        return None

    def _remaining_query_text(self, query: str, payload: dict) -> str | None:
        text = f" {query.lower()} "
        for key, value in payload.items():
            if key == "full_text_query" or value in (None, ""):
                continue
            text = text.replace(f" {str(value).lower()} ", " ")
        for stop_word in (" in ", " from ", " by ", " during ", " for ", " with ", " and "):
            text = text.replace(stop_word, " ")
        cleaned = " ".join(text.split())
        return cleaned or None
