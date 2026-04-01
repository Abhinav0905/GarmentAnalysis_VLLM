from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def unique_filename(filename: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", Path(filename).name).strip("-")
    stem = Path(safe).stem or "upload"
    suffix = Path(safe).suffix.lower() or ".jpg"
    return f"{stem}-{uuid4().hex[:8]}{suffix}"


def list_from_text(value: str) -> list[str]:
    items = re.split(r"[,\n]", value)
    return [item.strip() for item in items if item.strip()]


def parse_location_hint(value: str | None) -> dict[str, str | None]:
    parts = [part.strip() for part in (value or "").split(",") if part.strip()]
    if len(parts) >= 3:
        city, country, continent = parts[0], parts[1], parts[2]
    elif len(parts) == 2:
        city, country, continent = parts[0], parts[1], None
    elif len(parts) == 1:
        city, country, continent = parts[0], None, None
    else:
        city, country, continent = None, None, None
    return {
        "continent": continent,
        "country": country,
        "city": city,
    }


def parse_timestamp(value: str | None) -> tuple[str | None, int | None, int | None]:
    if not value:
        return None, None, None
    text = value.strip()
    if not text:
        return None, None, None
    normalized = text.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return text, parsed.year, parsed.month


def dump_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True)


def load_json(value: str | None, default):
    if not value:
        return default
    return json.loads(value)


def extract_json_object(text: str) -> dict:
    stripped = text.strip()
    if not stripped:
        raise ValueError("Model output is empty.")
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model output did not contain a JSON object.")
        return json.loads(stripped[start : end + 1])
