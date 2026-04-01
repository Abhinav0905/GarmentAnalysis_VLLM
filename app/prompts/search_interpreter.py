from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(slots=True)
class SearchInterpretationPrompt:
    system_prompt: str
    user_prompt: str


def build_search_interpretation_prompt(
    query: str,
    available_filters: dict[str, list[str]] | None = None,
) -> SearchInterpretationPrompt:
    system_prompt = (
        "You are a fashion search assistant. "
        "Read the user's natural-language query and return one JSON object only. "
        "Split the query into structured filters and a short remaining text query for full-text search."
    )
    filter_context = json.dumps(available_filters or {}, ensure_ascii=True)
    user_prompt = f"""
Return valid JSON with these keys:
- full_text_query
- garment_type
- style
- material
- color
- pattern
- occasion
- consumer_profile
- season
- designer
- continent
- country
- city
- year
- month

Rules:
- Use null when a field is not present.
- Use year as a number.
- Use month as a number from 1 to 12.
- Keep full_text_query short and focused on descriptive details that should hit descriptions, notes, or annotations.
- Prefer exact values from available_filters when they match the user's wording.
- Do not wrap the JSON in markdown.

available_filters:
{filter_context}

query:
{query}
""".strip()
    return SearchInterpretationPrompt(system_prompt=system_prompt, user_prompt=user_prompt)

