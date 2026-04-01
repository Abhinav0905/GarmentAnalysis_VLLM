from __future__ import annotations

from app.data_models.request_models import AnnotationCreateRequest
from app.data_models.response_models import GarmentResponse
from app.repositories.garment_repository import GarmentRepository
from app.services.search_service import SearchService


class AnnotationService:
    def __init__(self, repository: GarmentRepository, search_service: SearchService) -> None:
        self.repository = repository
        self.search_service = search_service

    def add_annotation(self, garment_id: int, payload: AnnotationCreateRequest) -> GarmentResponse:
        self.repository.add_annotation(garment_id=garment_id, note=payload.note, tags=payload.tags)
        return self.search_service.get_by_id(garment_id)

