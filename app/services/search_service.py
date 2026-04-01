from __future__ import annotations

from app.data_models.request_models import SearchRequest
from app.data_models.response_models import GarmentResponse, SearchInterpretation, SearchResponse
from app.guardrails.search_guardrails import sanitize_search_interpretation
from app.llm_clients.base import BaseLLMClient
from app.repositories.garment_repository import GarmentRepository
from app.utils.file_store import FileStore
from app.utils.helpers import extract_json_object


class SearchService:
    def __init__(
        self,
        repository: GarmentRepository,
        file_store: FileStore,
        llm_client: BaseLLMClient,
    ) -> None:
        self.repository = repository
        self.file_store = file_store
        self.llm_client = llm_client

    def search(self, payload: SearchRequest) -> SearchResponse:
        available_filters = self.list_filters()
        interpretation = self._interpret_query(payload, available_filters)
        resolved_payload = self._merge_with_interpretation(payload, interpretation)
        items = self.repository.search(resolved_payload.full_text_query(), resolved_payload.filters())
        return SearchResponse(
            items=[self.to_response(item) for item in items],
            total=len(items),
            filters=available_filters,
            search_interpretation=interpretation,
        )

    def get_by_id(self, garment_id: int) -> GarmentResponse:
        item = self.repository.get_garment(garment_id)
        if item is None:
            raise ValueError(f"Garment {garment_id} was not found.")
        return self.to_response(item)

    def list_filters(self) -> dict[str, list[str]]:
        return self.repository.list_filter_values()

    def _interpret_query(
        self,
        payload: SearchRequest,
        available_filters: dict[str, list[str]],
    ) -> SearchInterpretation | None:
        if not payload.query:
            return None
        llm_response = self.llm_client.interpret_search_query(
            query=payload.query,
            available_filters=available_filters,
        )
        if llm_response is None:
            return None
        try:
            raw_output = extract_json_object(llm_response.raw_text)
        except ValueError:
            return None
        return sanitize_search_interpretation(
            raw_output=raw_output,
            original_query=payload.query,
            available_filters=available_filters,
        )

    def _merge_with_interpretation(
        self,
        payload: SearchRequest,
        interpretation: SearchInterpretation | None,
    ) -> SearchRequest:
        if interpretation is None:
            return payload

        update: dict[str, str | int | None] = {}
        inferred_filters = interpretation.filters()
        for field, value in inferred_filters.items():
            explicit_value = getattr(payload, field)
            if explicit_value in (None, ""):
                update[field] = value

        if interpretation.full_text_query not in (None, ""):
            update["query"] = interpretation.full_text_query
        elif inferred_filters:
            update["query"] = None
        return payload.model_copy(update=update)

    def to_response(self, item: dict) -> GarmentResponse:
        return GarmentResponse(
            **{
                **item,
                "image_url": self.file_store.public_url(item["image_path"]),
            }
        )
