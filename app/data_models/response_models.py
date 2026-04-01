from __future__ import annotations

from pydantic import BaseModel, Field


class LocationContext(BaseModel):
    continent: str | None = None
    country: str | None = None
    city: str | None = None


class ClassificationAttributes(BaseModel):
    description: str
    garment_type: str | None = None
    style: str | None = None
    material: str | None = None
    color_palette: list[str] = Field(default_factory=list)
    pattern: str | None = None
    season: str | None = None
    occasion: str | None = None
    consumer_profile: str | None = None
    trend_notes: list[str] = Field(default_factory=list)
    location_context: LocationContext = Field(default_factory=LocationContext)
    ai_tags: list[str] = Field(default_factory=list)


class AnnotationResponse(BaseModel):
    id: int
    note: str
    tags: list[str] = Field(default_factory=list)
    created_at: str


class TokenUsageResponse(BaseModel):
    source: str
    model_name: str
    token_estimate: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_input_tokens: int = 0
    input_cost_usd: float | None = None
    output_cost_usd: float | None = None
    total_cost_usd: float | None = None


class GarmentResponse(BaseModel):
    id: int
    image_url: str
    original_filename: str
    designer: str | None = None
    captured_at: str | None = None
    year: int | None = None
    month: int | None = None
    description: str
    garment_type: str | None = None
    style: str | None = None
    material: str | None = None
    color_palette: list[str] = Field(default_factory=list)
    pattern: str | None = None
    season: str | None = None
    occasion: str | None = None
    consumer_profile: str | None = None
    trend_notes: list[str] = Field(default_factory=list)
    location_context: LocationContext = Field(default_factory=LocationContext)
    ai_tags: list[str] = Field(default_factory=list)
    annotations: list[AnnotationResponse] = Field(default_factory=list)
    token_estimate: int
    token_usage: TokenUsageResponse
    trace_id: str
    created_at: str


class SearchInterpretation(BaseModel):
    original_query: str
    full_text_query: str | None = None
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
    used_llm: bool = False

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


class SearchResponse(BaseModel):
    items: list[GarmentResponse] = Field(default_factory=list)
    total: int
    filters: dict[str, list[str]] = Field(default_factory=dict)
    search_interpretation: SearchInterpretation | None = None


class HealthResponse(BaseModel):
    status: str
