from __future__ import annotations

from pydantic import BaseModel, Field

from app.data_models.full_text_search import FullTextSearchQuery
from app.utils.helpers import list_from_text


class UploadMetadataRequest(BaseModel):
    designer: str | None = None
    captured_at: str | None = None
    location_hint: str | None = None


class AnnotationCreateRequest(BaseModel):
    note: str = Field(min_length=1, max_length=1000)
    tags: list[str] = Field(default_factory=list)

    @classmethod
    def from_text(cls, note: str, tags: str | None) -> "AnnotationCreateRequest":
        return cls(note=note, tags=list_from_text(tags or ""))


class SearchRequest(BaseModel):
    query: str | None = None
    garment_type: str | None = None
    style: str | None = None
    material: str | None = None
    color: str | None = None
    pattern: str | None = None
    occasion: str | None = None
    consumer_profile: str | None = None
    season: str | None = None
    designer: str | None = None
    continent: str | None = None
    country: str | None = None
    city: str | None = None
    year: int | None = None
    month: int | None = None

    def full_text_query(self) -> FullTextSearchQuery:
        return FullTextSearchQuery(query=self.query)

    def filters(self) -> dict[str, str | int]:
        values: dict[str, str | int] = {}
        for name in (
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
            "year",
            "month",
        ):
            value = getattr(self, name)
            if value not in (None, ""):
                values[name] = value
        return values

