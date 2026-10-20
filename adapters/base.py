"""Shared adapter logic: HTTP, retries, Retry-After, JSON extraction, validation."""
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError
from .config import ProviderConfig
from .errors import (AdapterError, AuthError, ClientError, ConfigurationError,
                     RateLimitError, SchemaValidationError, ServerError)
from .rate_limit import RateLimiter
T = TypeVar("T", bound=BaseModel)
@dataclass
class LLMRequest:
    messages: list[dict[str, Any]]
    schema: Optional[Type[BaseModel]] = None
    model: Optional[str] = None
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)
@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    usage: dict[str, Any]
    raw: dict[str, Any]
    parsed: Optional[BaseModel] = None
    attempts_used: Optional[int] = None

def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1:]
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
    return stripped.strip()

def _json_instruction(schema: Type[BaseModel]) -> str:
    schema_json = json.dumps(schema.model_json_schema(), separators=(",", ":"), sort_keys=True)
    return ("Respond with a single json object only. Do not include prose, "
            "markdown, or code fences. It must validate against this JSON Schema: " + schema_json)

def _inject_system_instruction(messages: list[dict[str, Any]], instruction: str) -> list[dict[str, Any]]:
    if messages and messages[0].get("role") == "system":
        head = dict(messages[0]); head["content"] = str(head.get("content", "")).rstrip() + "\n\n" + instruction
        return [head, *messages[1:]]
    return [{"role": "system", "content": instruction}, *messages]

class BaseAdapter:
    def __init__(self, config: ProviderConfig, *, api_key: Optional[str] = None,
                 transport: Optional[httpx.BaseTransport] = None, client: Optional[httpx.Client] = None,
                 sleep: Callable[[float], None] = time.sleep,
                 monotonic: Callable[[], float] = time.monotonic) -> None:
        if config.max_retries < 1 or config.max_retries > 5:
            raise ConfigurationError("max_retries must be between 1 and 5")
        if transport is None and client is None and os.environ.get("ENABLE_LIVE_LLM") != "1":
            raise ConfigurationError(
                "Live API calls are disabled. Set ENABLE_LIVE_LLM=1 only after "
                "verifying the account has no paid billing and the selected model is free."
            )
        self.config = config
        resolved = api_key if api_key is not None else os.environ.get(config.env_var)
        if not resolved:
            raise ConfigurationError(f"Missing API key for {config.name}: set {config.env_var}")
        self._api_key = resolved
        self._sleep = sleep
        self._monotonic = monotonic
        self._client = client if client is not None else httpx.Client(transport=transport)
        self.rate_limiter = RateLimiter(config.rpm, config.rpd, monotonic=monotonic, sleep=sleep)
    def close(self) -> None:
        self._client.close()
    def __enter__(self) -> "BaseAdapter":
        return self
    def __exit__(self, *exc: Any) -> None:
        self.close()
    def _endpoint(self) -> str:
        return self.config.base_url.rstrip("/") + "/chat/completions"
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json", "Accept": "application/json"}
    def _resolve_model(self, request: LLMRequest) -> str:
        if request.model:
            return request.model
        env_model = os.environ.get(self.config.model_env_var)
        return env_model or self.config.default_model
    def _build_payload(self, request: LLMRequest) -> dict[str, Any]:
        messages = list(request.messages)
        if request.schema is not None:
            messages = _inject_system_instruction(messages, _json_instruction(request.schema))
        payload: dict[str, Any] = {"model": self._resolve_model(request),
                                   "messages": messages, "temperature": request.temperature}
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        return payload
    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ServerError(f"Malformed response body: {exc}") from exc
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str): parts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("text"), str): parts.append(item["text"])
            content = "".join(parts)
        if not isinstance(content, str):
            raise ServerError("Response content is not text")
        return content
    @staticmethod
    def _extract_usage(data: dict[str, Any]) -> dict[str, Any]:
        usage = data.get("usage")
        return dict(usage) if isinstance(usage, dict) else {}
    def _extract_model(self, data: dict[str, Any]) -> str:
        model = data.get("model")
        return model if isinstance(model, str) else self.config.default_model
    def _error_message(self, response: httpx.Response) -> str:
        try:
            body = response.json()
            if isinstance(body, dict):
                err = body.get("error")
                if isinstance(err, dict) and "message" in err:
                    return str(err["message"])
                if isinstance(err, str): return err
            return json.dumps(body)[:300]
        except Exception:
            return response.text[:300]
    def _parse_retry_after(self, response: httpx.Response) -> Optional[float]:
        raw = response.headers.get("retry-after") or response.headers.get("Retry-After")
        if not raw:
            return None
        raw = raw.strip()
        try:
            value = float(raw)
            if 0 <= value < float("inf"):
                return value
        except ValueError:
            pass
        try:
            when = parsedate_to_datetime(raw)
            if when.tzinfo is None: when = when.replace(tzinfo=timezone.utc)
            delta = (when - datetime.now(timezone.utc)).total_seconds()
            return max(delta, 0.0)
        except Exception: return None
    def _backoff(self, attempt: int) -> float:
        return self.config.backoff_base ** attempt
    def _parse_and_validate(self, text: str, schema: Type[T]) -> T:
        cleaned = _strip_markdown_fences(text)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise SchemaValidationError(f"Non-JSON response ({exc}); first 200 chars: {text[:200]!r}") from exc
        try:
            return schema.model_validate(data)
        except ValidationError as exc:
            raise SchemaValidationError(str(exc)) from exc
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Complete a request; charge each retry against local rate limits.

        Safety: fail over rather than sleep within one CI run for a long provider
        cooldown. A future router coordinates provider choice and persistent quota.
        """
        if request.max_tokens is not None and not 1 <= request.max_tokens <= 4096:
            raise ConfigurationError("max_tokens must be 1..4096")
        payload = self._build_payload(request)
        headers = self._headers()
        url = self._endpoint()
        last_error: Optional[AdapterError] = None
        MAX_RETRY_SLEEP = 60.0
        for attempt in range(1, self.config.max_retries + 1):
            # Each HTTP attempt consumes request quota, not just the task.
            self.rate_limiter.acquire(max_wait_seconds=MAX_RETRY_SLEEP)
            try:
                response = self._client.post(
                    url, json=payload, headers=headers,
                    timeout=self.config.request_timeout,
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = ServerError(f"{self.config.name}: transport or timeout failure")
                if attempt < self.config.max_retries:
                    self._sleep(self._backoff(attempt))
                    continue
                raise last_error from exc

            status = response.status_code
            if status == 200:
                try:
                    data = response.json()
                except ValueError as exc:
                    raise ServerError(f"{self.config.name}: invalid JSON response envelope") from exc
                if not isinstance(data, dict):
                    raise ServerError(f"{self.config.name}: non-object JSON response envelope")
                text = self._extract_text(data)
                parsed: Optional[BaseModel] = None
                if request.schema is not None:
                    try:
                        parsed = self._parse_and_validate(text, request.schema)
                    except SchemaValidationError as exc:
                        if attempt >= self.config.max_retries:
                            raise
                        # One corrective message instead of repeating an identical prompt.
                        # Errors are shortened before being re-sent to a provider.
                        correction = (
                            "Previous output failed JSON Schema validation: "
                            + str(exc)[:600]
                            + ". Return ONLY a corrected json object."
                        )
                        payload = dict(payload)
                        payload["messages"] = _inject_system_instruction(
                            payload["messages"], correction
                        )
                        continue
                return LLMResponse(
                    text=text, provider=self.config.name,
                    model=self._extract_model(data), usage=self._extract_usage(data),
                    raw=data, parsed=parsed, attempts_used=attempt,
                )

            if status == 429:
                retry_after = self._parse_retry_after(response)
                wait = retry_after if retry_after is not None else self._backoff(attempt)
                self.rate_limiter.penalize(wait)
                last_error = RateLimitError(
                    f"{self.config.name}: rate limit exceeded",
                    retry_after=retry_after,
                )
                if attempt < self.config.max_retries and wait <= MAX_RETRY_SLEEP:
                    self._sleep(wait)
                    continue
                raise last_error

            if 500 <= status < 600:
                wait = self._parse_retry_after(response) if status == 503 else None
                if wait is None:
                    wait = self._backoff(attempt)
                last_error = ServerError(f"{self.config.name}: server returned HTTP {status}")
                if attempt < self.config.max_retries and wait <= MAX_RETRY_SLEEP:
                    self._sleep(wait)
                    continue
                raise last_error

            if status in (401, 403):
                raise AuthError(f"{self.config.name}: authentication/permissions error {status}")
            # Fixed vocabulary only: never echo provider bodies, prompts or keys.
            reason = "unclassified_client_error"
            try:
                error = response.json().get('error', {})
                code = error.get('code') or error.get('status')
                if code in ('json_validate_failed', 'context_length_exceeded', 'model_not_found',
                            'INVALID_ARGUMENT', 'PERMISSION_DENIED', 'unsupported_parameter'):
                    reason = code
                message = str(error.get('message', '')).lower()
                for label, phrase in (
                    ('invalid_json_generation', 'failed to generate json'),
                    ('unsupported_response_format', 'response_format'),
                    ('invalid_max_tokens', 'max_tokens'),
                    ('insufficient_tokens', 'too many tokens'),
                    ('unsupported_schema', 'schema'),
                    ('missing_json_instruction', 'json')):
                    if phrase in message:
                        reason = label
                        break
            except (ValueError, TypeError, AttributeError):
                pass
            if reason in ('invalid_json_generation', 'json_validate_failed'):
                # Groq reports invalid generated JSON as HTTP 400. This is
                # content failure, not an invalid key or infrastructure outage.
                if attempt < self.config.max_retries:
                    payload = dict(payload)
                    payload['messages'] = _inject_system_instruction(
                        payload['messages'],
                        'Previous generation failed JSON validation. Return ONLY a valid json object matching the supplied schema; no markdown or commentary.')
                    continue
                raise SchemaValidationError(f"{self.config.name}: provider rejected generated JSON after bounded retries")
            raise ClientError(f"{self.config.name}: non-retryable HTTP {status}; reason={reason}")

        assert last_error is not None
        raise last_error
