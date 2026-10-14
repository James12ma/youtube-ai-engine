"""Provider-specific configuration. No secrets are stored here."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping
@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    env_var: str
    model_env_var: str
    default_model: str
    rpm: int
    rpd: int
    request_timeout: float = 30.0
    max_retries: int = 3
    backoff_base: float = 1.5
    extra_headers: Mapping[str, str] = field(default_factory=dict)
GROQ_CONFIG = ProviderConfig(
    name="groq", base_url="https://api.groq.com/openai/v1",
    env_var="GROQ_API_KEY", model_env_var="GROQ_MODEL",
    default_model="openai/gpt-oss-120b", rpm=30, rpd=1_000,
    request_timeout=30.0,
)
GEMINI_CONFIG = ProviderConfig(
    name="gemini", base_url="https://generativelanguage.googleapis.com/v1beta/openai",
    env_var="GEMINI_API_KEY", model_env_var="GEMINI_MODEL",
    default_model="gemini-2.5-flash", rpm=15, rpd=1_500,
    request_timeout=30.0,
)
OPENROUTER_CONFIG = ProviderConfig(
    name="openrouter", base_url="https://openrouter.ai/api/v1",
    env_var="OPENROUTER_API_KEY", model_env_var="OPENROUTER_MODEL",
    default_model="meta-llama/llama-3.3-70b-instruct:free", rpm=20, rpd=50,
    request_timeout=45.0,
)
