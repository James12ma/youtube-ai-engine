"""OpenRouter adapter. Adds the recommended attribution headers."""
from __future__ import annotations
import os
from typing import Any
from .base import BaseAdapter, LLMRequest
from .errors import ConfigurationError
from .config import OPENROUTER_CONFIG, ProviderConfig
class OpenRouterAdapter(BaseAdapter):
    def __init__(self, config: ProviderConfig = OPENROUTER_CONFIG, **kwargs: Any) -> None:
        super().__init__(config, **kwargs)
    def _resolve_model(self, request: LLMRequest) -> str:
        model = super()._resolve_model(request)
        if not model.endswith(":free"):
            raise ConfigurationError("OpenRouter model must explicitly end with :free")
        return model

    def _headers(self) -> dict[str, str]:
        headers = super()._headers()
        headers["HTTP-Referer"] = os.environ.get("OPENROUTER_HTTP_REFERER", "https://github.com/")
        headers["X-Title"] = os.environ.get("OPENROUTER_X_TITLE", "Router-V3")
        return headers
    def _build_payload(self, request: LLMRequest) -> dict[str, Any]:
        payload = super()._build_payload(request)
        # Cohere free currently lacks response_format in the live catalog.
        # BaseAdapter still injects the schema and strictly validates actual JSON.
        if request.schema is not None and payload["model"] != "cohere/north-mini-code:free":
            payload["response_format"] = {"type": "json_object"}
        return payload
