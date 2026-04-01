from __future__ import annotations

from app.data_models.response_models import SearchInterpretation

FILTER_FIELDS = (
    "garment_type",
    "style",
    "material",
    "color",
    "pattern",
    "occasion",
    "consumer_profile",
    "season",
    "designer",
    "continent",
    "country",
    "city",
)

CONVERSATIONAL_STOP_WORDS = {
    "a",
    "an",
    "and",
    "any",
    "at",
    "by",
    "can",
    "find",
    "for",
    "from",
    "give",
    "i",
    "image",
    "images",
    "in",
    "look",
    "looking",
    "me",
    "need",
    "of",
    "on",
    "photo",
    "photos",
    "picture",
    "pictures",
    "please",
    "show",
    "some",
    "the",
    "to",
    "want",
    "with",
    "you",
    "nice",
}


def sanitize_search_interpretation(
    raw_output: dict,
    original_query: str,
    available_filters: dict[str, list[str]] | None = None,
) -> SearchInterpretation:
    available_filters = available_filters or {}
    values: dict[str, str | int | None | bool] = {
        "original_query": original_query,
        "full_text_query": _normalize_free_text(raw_output.get("full_text_query")),
        "used_llm": True,
    }

    for field in FILTER_FIELDS:
        values[field] = _match_available_value(raw_output.get(field), available_filters.get(field, []))

    values["year"] = _clean_int(raw_output.get("year"), available_filters.get("year", []))
    values["month"] = _clean_int(raw_output.get("month"), available_filters.get("month", []))

    interpretation = SearchInterpretation(**values)
    if interpretation.full_text_query in {"", original_query}:
        interpretation.full_text_query = _clean_text(interpretation.full_text_query)
    return interpretation


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:250]


def _match_available_value(value: object, choices: list[str]) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    if not choices:
        return text
    for choice in choices:
        if choice.lower() == text.lower():
            return choice
    return None


def _clean_int(value: object, choices: list[str]) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if choices and str(parsed) not in {str(choice) for choice in choices}:
        return None
    return parsed


def _normalize_free_text(value: object) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    words = [word for word in text.split() if word.lower() not in CONVERSATIONAL_STOP_WORDS]
    if not words:
        return None
    cleaned = " ".join(words)
    return cleaned or None
