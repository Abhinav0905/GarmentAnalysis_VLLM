from __future__ import annotations

from fastapi import UploadFile

from app.data_models.request_models import UploadMetadataRequest
from app.data_models.response_models import GarmentResponse
from app.guardrails.upload_guardrails import sanitize_classification_output, validate_upload
from app.llm_clients.base import BaseLLMClient, LLMRequest
from app.prompts.fashion_classifier import build_classification_prompt
from app.repositories.garment_repository import GarmentRepository
from app.services.search_service import SearchService
from app.token_calculation.token_calculator import TokenCalculator
from app.agent_tracing.tracer import AgentTracer
from app.utils.config import Settings
from app.utils.file_store import FileStore
from app.utils.helpers import extract_json_object, now_iso, parse_timestamp


class ClassificationService:
    def __init__(
        self,
        repository: GarmentRepository,
        file_store: FileStore,
        llm_client: BaseLLMClient,
        tracer: AgentTracer,
        token_calculator: TokenCalculator,
        search_service: SearchService,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.file_store = file_store
        self.llm_client = llm_client
        self.tracer = tracer
        self.token_calculator = token_calculator
        self.search_service = search_service
        self.settings = settings

    async def classify_and_store(self, file: UploadFile, metadata: UploadMetadataRequest) -> GarmentResponse:
        content = await file.read()
        # Fail early on invalid uploads before we spend time tracing, saving, or
        # calling the model.
        validate_upload(
            filename=file.filename or "upload.jpg",
            content_type=file.content_type,
            size_in_bytes=len(content),
            max_size_bytes=self.settings.max_upload_size_bytes,
        )

        trace = self.tracer.start_trace("classify_garment")
        trace.add_event(
            "upload_received",
            {
                "filename": file.filename,
                "size_in_bytes": len(content),
            },
        )

        # Save first so the classifier and the UI can both reference the same
        # local file path.
        image_path = self.file_store.save_upload(file.filename or "upload.jpg", content)
        prompt = build_classification_prompt(
            location_hint=metadata.location_hint,
            captured_at=metadata.captured_at,
        )
        # This is only a rough estimate for visibility in the demo, not a billing
        # grade token count.
        token_estimate = self.token_calculator.estimate_total(
            prompt_text=f"{prompt.system_prompt}\n{prompt.user_prompt}",
            size_in_bytes=len(content),
        )
        trace.add_event("prompt_prepared", {"token_estimate": token_estimate})

        # The service only cares that the client returns text. The provider
        # details stay inside the llm_clients package.
        llm_response = self.llm_client.classify_image(
            LLMRequest(
                image_path=image_path,
                prompt=prompt,
                metadata={
                    "designer": metadata.designer,
                    "captured_at": metadata.captured_at,
                    "location_hint": metadata.location_hint,
                },
                trace_id=trace.trace_id,
            )
        )
        trace.add_event("model_completed", {"model": llm_response.model})
        pricing = self.token_calculator.pricing_for_model(
            model_name=llm_response.model,
            input_cost_per_million=self.settings.openai_input_cost_per_million,
            cached_input_cost_per_million=self.settings.openai_cached_input_cost_per_million,
            output_cost_per_million=self.settings.openai_output_cost_per_million,
        )
        token_summary = self.token_calculator.build_usage_summary(
            model_name=llm_response.model,
            usage=llm_response.usage,
            token_estimate=token_estimate,
            pricing=pricing,
        )
        trace.add_event(
            "usage_calculated",
            {
                "source": token_summary.source,
                "input_tokens": token_summary.input_tokens,
                "output_tokens": token_summary.output_tokens,
                "total_tokens": token_summary.total_tokens,
                "total_cost_usd": token_summary.total_cost_usd,
            },
        )

        # Models are inconsistent, so normalize everything into our internal
        # response shape before we persist it.
        raw_output = extract_json_object(llm_response.raw_text)
        attributes = sanitize_classification_output(raw_output, metadata.location_hint)
        captured_at, year, month = parse_timestamp(metadata.captured_at)

        garment_id = self.repository.save_garment(
            {
                "image_path": str(image_path),
                "original_filename": file.filename or image_path.name,
                "designer": metadata.designer,
                "captured_at": captured_at,
                "year": year,
                "month": month,
                "location_hint": metadata.location_hint,
                "description": attributes.description,
                "garment_type": attributes.garment_type,
                "style": attributes.style,
                "material": attributes.material,
                "color_palette": attributes.color_palette,
                "pattern": attributes.pattern,
                "season": attributes.season,
                "occasion": attributes.occasion,
                "consumer_profile": attributes.consumer_profile,
                "trend_notes": attributes.trend_notes,
                "continent": attributes.location_context.continent,
                "country": attributes.location_context.country,
                "city": attributes.location_context.city,
                "ai_tags": attributes.ai_tags,
                "raw_model_output": llm_response.raw_text,
                "token_estimate": token_summary.token_estimate,
                "model_name": token_summary.model_name,
                "token_source": token_summary.source,
                "input_tokens": token_summary.input_tokens,
                "output_tokens": token_summary.output_tokens,
                "total_tokens": token_summary.total_tokens,
                "cached_input_tokens": token_summary.cached_input_tokens,
                "input_cost_usd": token_summary.input_cost_usd,
                "output_cost_usd": token_summary.output_cost_usd,
                "total_cost_usd": token_summary.total_cost_usd,
                "trace_id": trace.trace_id,
                "created_at": now_iso(),
            }
        )
        # Persist the trace after the record exists so the trace can point at the
        # saved garment id.
        trace.finish({"garment_id": garment_id})
        return self.search_service.get_by_id(garment_id)
