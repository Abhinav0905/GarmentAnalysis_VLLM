from __future__ import annotations

from app.data_models.response_models import ClassificationAttributes, LocationContext
from app.utils.helpers import list_from_text, parse_location_hint

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def validate_upload(filename: str, content_type: str | None, size_in_bytes: int, max_size_bytes: int) -> None:
    suffix = f".{filename.rsplit('.', 1)[-1].lower()}" if "." in filename else ""
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("Upload must be a jpg, jpeg, png, or webp image.")
    if content_type and not content_type.startswith("image/"):
        raise ValueError("Upload must be an image.")
    if size_in_bytes > max_size_bytes:
        raise ValueError("Upload is too large for the local demo limit.")


def sanitize_classification_output(raw_output: dict, location_hint: str | None) -> ClassificationAttributes:
    location_context = raw_output.get("location_context") or {}
    fallback_location = parse_location_hint(location_hint)
    location = LocationContext(
        continent=_clean_text(location_context.get("continent") or fallback_location["continent"]),
        country=_clean_text(location_context.get("country") or fallback_location["country"]),
        city=_clean_text(location_context.get("city") or fallback_location["city"]),
    )
    return ClassificationAttributes(
        description=_clean_text(raw_output.get("description"), default="Fashion image"),
        garment_type=_clean_text(raw_output.get("garment_type")),
        style=_clean_text(raw_output.get("style")),
        material=_clean_text(raw_output.get("material")),
        color_palette=_clean_list(raw_output.get("color_palette")),
        pattern=_clean_text(raw_output.get("pattern")),
        season=_clean_text(raw_output.get("season")),
        occasion=_clean_text(raw_output.get("occasion")),
        consumer_profile=_clean_text(raw_output.get("consumer_profile")),
        trend_notes=_clean_list(raw_output.get("trend_notes")),
        location_context=location,
        ai_tags=_build_ai_tags(raw_output),
    )


def _clean_text(value: object, default: str | None = None) -> str | None:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text[:300]


def _clean_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = list_from_text(str(value))
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _clean_text(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned[:6]


def _build_ai_tags(raw_output: dict) -> list[str]:
    source = [
        raw_output.get("garment_type"),
        raw_output.get("style"),
        raw_output.get("material"),
        raw_output.get("pattern"),
        raw_output.get("season"),
        raw_output.get("occasion"),
        raw_output.get("consumer_profile"),
        *(raw_output.get("trend_notes") or []),
    ]
    return _clean_list(source)

