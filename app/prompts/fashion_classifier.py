from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ClassificationPrompt:
    system_prompt: str
    user_prompt: str


def build_classification_prompt(location_hint: str | None, captured_at: str | None) -> ClassificationPrompt:
    system_prompt = (
        "You are a careful fashion archivist. "
        "Look at the garment image and return one JSON object only. "
        "Describe the look in plain English and extract structured attributes."
    )
    location_line = location_hint or "Unknown"
    captured_line = captured_at or "Unknown"
    user_prompt = f"""
Return valid JSON with these keys:
- description
- garment_type
- style
- material
- color_palette (array of short color names)
- pattern
- season
- occasion
- consumer_profile
- trend_notes (array of short strings)
- location_context (object with continent, country, city)

Rules:
- Use null when you cannot infer a scalar value.
- Keep color_palette to 1-4 values.
- Keep trend_notes to 1-3 values.
- Do not wrap the JSON in markdown.

Context from the uploader:
- location_hint: {location_line}
- captured_at: {captured_line}
""".strip()
    return ClassificationPrompt(system_prompt=system_prompt, user_prompt=user_prompt)

