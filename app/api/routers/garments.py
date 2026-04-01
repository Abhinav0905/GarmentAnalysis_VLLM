from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.data_models.request_models import AnnotationCreateRequest, SearchRequest, UploadMetadataRequest
from app.data_models.response_models import GarmentResponse, SearchResponse

router = APIRouter(tags=["garments"])


def _services(request: Request) -> dict[str, object]:
    return request.app.state.services


@router.post("/garments/upload", response_model=GarmentResponse)
async def upload_garment(
    request: Request,
    file: UploadFile = File(...),
    designer: str | None = Form(default=None),
    captured_at: str | None = Form(default=None),
    location_hint: str | None = Form(default=None),
) -> GarmentResponse:
    payload = UploadMetadataRequest(
        designer=designer,
        captured_at=captured_at,
        location_hint=location_hint,
    )
    service = _services(request)["classification_service"]
    try:
        return await service.classify_and_store(file=file, metadata=payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/garments", response_model=SearchResponse)
def search_garments(
    request: Request,
    query: str | None = None,
    garment_type: str | None = None,
    style: str | None = None,
    material: str | None = None,
    color: str | None = None,
    pattern: str | None = None,
    occasion: str | None = None,
    consumer_profile: str | None = None,
    season: str | None = None,
    designer: str | None = None,
    continent: str | None = None,
    country: str | None = None,
    city: str | None = None,
    year: int | None = None,
    month: int | None = None,
) -> SearchResponse:
    payload = SearchRequest(
        query=query,
        garment_type=garment_type,
        style=style,
        material=material,
        color=color,
        pattern=pattern,
        occasion=occasion,
        consumer_profile=consumer_profile,
        season=season,
        designer=designer,
        continent=continent,
        country=country,
        city=city,
        year=year,
        month=month,
    )
    service = _services(request)["search_service"]
    return service.search(payload)


@router.get("/filters")
def list_filters(request: Request) -> dict[str, list[str]]:
    service = _services(request)["search_service"]
    return service.list_filters()


@router.post("/garments/{garment_id}/annotations", response_model=GarmentResponse)
def add_annotation(
    garment_id: int,
    payload: AnnotationCreateRequest,
    request: Request,
) -> GarmentResponse:
    service = _services(request)["annotation_service"]
    try:
        return service.add_annotation(garment_id=garment_id, payload=payload)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

