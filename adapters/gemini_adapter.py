"""Gemini adapter via the OpenAI-compatibility endpoint."""
from __future__ import annotations
from typing import Any
from .base import BaseAdapter, LLMRequest
from .config import GEMINI_CONFIG, ProviderConfig
from .errors import ConfigurationError
class GeminiAdapter(BaseAdapter):
    def __init__(self, config: ProviderConfig = GEMINI_CONFIG, **kwargs: Any) -> None:
        super().__init__(config, **kwargs)
    _APPROVED_MODELS = frozenset({"gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite"})

    def _resolve_model(self, request: LLMRequest) -> str:
        model = super()._resolve_model(request)
        if model not in self._APPROVED_MODELS:
            raise ConfigurationError("Gemini model is not in the reviewed free-tier allowlist")
        return model

    def _build_payload(self, request: LLMRequest) -> dict[str, Any]:
        payload = super()._build_payload(request)
        if request.schema is not None:
            payload["response_format"] = {"type": "json_object"}
        return payload
