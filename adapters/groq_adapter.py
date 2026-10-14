"""Groq adapter. OpenAI-compatible transport with a json-mode guard."""
from __future__ import annotations
import json
from typing import Any
from .base import BaseAdapter, LLMRequest
from .config import GROQ_CONFIG, ProviderConfig
from .errors import ConfigurationError
class GroqAdapter(BaseAdapter):
    def __init__(self, config: ProviderConfig = GROQ_CONFIG, **kwargs: Any) -> None:
        super().__init__(config, **kwargs)
    _APPROVED_MODELS = frozenset({
        "openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b",
    })

    def _resolve_model(self, request: LLMRequest) -> str:
        model = super()._resolve_model(request)
        if model not in self._APPROVED_MODELS:
            raise ConfigurationError("Groq model is not in the reviewed free-model allowlist")
        return model

    def _build_payload(self, request: LLMRequest) -> dict[str, Any]:
        payload = super()._build_payload(request)
        if request.schema is not None:
            blob = json.dumps(payload["messages"]).lower()
            if "json" not in blob:
                raise ConfigurationError("Groq json_object mode requires the word 'json' in messages")
            payload["response_format"] = {"type": "json_object"}
        return payload
