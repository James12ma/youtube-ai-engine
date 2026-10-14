"""Adapter exception hierarchy. No provider SDK imports here."""
from __future__ import annotations
from typing import Optional
class AdapterError(RuntimeError):
    """Base class for all adapter failures."""
class ConfigurationError(AdapterError):
    """Missing/invalid configuration (e.g. absent API key)."""
class AuthError(AdapterError):
    """401/403 from the provider."""
class RateLimitError(AdapterError):
    """429 from the provider."""
    def __init__(self, message: str, *, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after
class ServerError(AdapterError):
    """5xx from the provider, or a transport/timeout failure."""
class ClientError(AdapterError):
    """Other 4xx that is not a rate limit or auth failure."""
class SchemaValidationError(AdapterError):
    """Provider returned text that could not be parsed/validated against schema."""
