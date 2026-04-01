from __future__ import annotations

from pydantic import BaseModel


class FullTextSearchQuery(BaseModel):
    query: str | None = None

    def sqlite_match(self) -> str | None:
        if not self.query:
            return None
        words = [word.strip() for word in self.query.split() if word.strip()]
        if not words:
            return None
        escaped = [word.replace('"', "").replace("'", "") for word in words]
        return " ".join(escaped)

