from __future__ import annotations

import base64
import json
from pathlib import Path

import httpx

from app.llm_clients.base import BaseLLMClient, LLMRequest, LLMResponse, LLMUsage
from app.prompts.search_interpreter import build_search_interpretation_prompt


class OpenAIFashionLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, timeout_seconds: int = 60) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def classify_image(self, request: LLMRequest) -> LLMResponse:
        # Send text instructions plus the local image in one Responses API call.
        raw_payload = self._create_response(
            input_items=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": request.prompt.system_prompt,
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": request.prompt.user_prompt,
                        },
                        {
                            "type": "input_image",
                            "image_url": self._to_data_url(request.image_path),
                        },
                    ],
                },
            ],
            temperature=0.2,
            trace_id=request.trace_id,
        )
        raw_text = self._extract_text(raw_payload)
        if not raw_text:
            raise ValueError("Model did not return text output.")
        return LLMResponse(
            raw_text=raw_text,
            raw_payload=raw_payload,
            model=self.model,
            usage=self._extract_usage(raw_payload),
        )

    def interpret_search_query(
        self,
        query: str,
        available_filters: dict[str, list[str]] | None = None,
        trace_id: str | None = None,
    ) -> LLMResponse:
        prompt = build_search_interpretation_prompt(query=query, available_filters=available_filters)
        raw_payload = self._create_response(
            input_items=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": prompt.system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt.user_prompt}],
                },
            ],
            temperature=0.1,
            trace_id=trace_id,
        )
        raw_text = self._extract_text(raw_payload)
        if not raw_text:
            raise ValueError("Model did not return search interpretation text.")
        return LLMResponse(
            raw_text=raw_text,
            raw_payload=raw_payload,
            model=self.model,
            usage=self._extract_usage(raw_payload),
        )

    def _create_response(self, input_items: list[dict], temperature: float, trace_id: str | None) -> dict:
        payload = {
            "model": self.model,
            "input": input_items,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Reuse the app trace id as the client request id so local traces can be
        # correlated with API-side logs if needed.
        if trace_id:
            headers["X-Client-Request-Id"] = trace_id

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def _to_data_url(self, image_path: Path) -> str:
        # The API accepts a data URL, so we read the saved file and inline it.
        suffix = image_path.suffix.lower().lstrip(".") or "jpeg"
        mime_type = "image/jpeg" if suffix in {"jpg", "jpeg"} else f"image/{suffix}"
        encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _extract_text(self, payload: dict) -> str:
        # Keep extraction defensive because response shapes can vary slightly
        # between text and structured outputs.
        output = payload.get("output", [])
        for item in output:
            for content in item.get("content", []):
                if "text" in content:
                    return content["text"]
                if "json" in content:
                    return json.dumps(content["json"])
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"]
        return ""

    def _extract_usage(self, payload: dict) -> LLMUsage | None:
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return None
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))
        input_details = usage.get("input_tokens_details") or {}
        cached_input_tokens = int(input_details.get("cached_tokens") or 0)
        return LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cached_input_tokens=cached_input_tokens,
        )
