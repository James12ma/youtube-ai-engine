"""Router V3.1: controlled, resumable, provider failover.

Uses the previously validated Task 1 StateStore and Task 2 adapters. Calls
can be retried after crashes; exactly-once external execution is impossible.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Optional, Sequence, Type
from pydantic import BaseModel
from adapters import (AdapterError, AuthError, ClientError, LLMRequest,
                      RateLimitError, SchemaValidationError, ServerError)
from state_store import StateStore, compute_task_id
from .circuit import CircuitBreaker, CircuitState
from .errors import (AllProvidersFailed, BillableModelRejected, LiveAPINotAuthorized,
                     RouterError, RouterPaused)
from .policy import require_free_model
from .runtime import RouterRuntimeStore
DEFAULT_PROVIDER_ORDER = ('groq', 'gemini', 'openrouter')
DEFAULT_RPD = {'groq': 1000, 'gemini': 100, 'openrouter': 50}
DEFAULT_RPM = {'groq': 30, 'gemini': 10, 'openrouter': 20}

@dataclass
class RouterConfig:
    provider_order: Sequence[str] = field(default_factory=lambda: DEFAULT_PROVIDER_ORDER)
    failure_threshold: int = 3
    recovery_timeout: float = 900.0
    all_failed_pause: float = 3600.0
    rate_limit_default_cooldown: float = 60.0
    lease_seconds: float = 900.0
    schema_version: str = '1.1'
    rpd: Mapping[str, int] = field(default_factory=lambda: dict(DEFAULT_RPD))
    rpm: Mapping[str, int] = field(default_factory=lambda: dict(DEFAULT_RPM))

class Router:
    def __init__(self, state_store: StateStore, adapters: dict[str, Any],
                 config: Optional[RouterConfig] = None, *, clock=time.time):
        self._state = state_store
        self._runtime_store = RouterRuntimeStore(state_store)
        self._adapters = adapters
        self._config = config or RouterConfig()
        self._clock = clock

    @staticmethod
    def _fingerprint(request: LLMRequest, schema: Type[BaseModel]) -> dict[str, Any]:
        # Keep task IDs sensitive-free in persisted state (only digest stored).
        try:
            payload = {'messages': request.messages, 'model': request.model,
                       'temperature': request.temperature, 'max_tokens': request.max_tokens,
                       'schema': schema.model_json_schema()}
            data = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
        except Exception as exc:
            raise RouterError('Request cannot be fingerprinted') from exc
        return {'request_sha256': hashlib.sha256(data).hexdigest()}

    def _model(self, adapter: Any, request: LLMRequest) -> str:
        # Use the same model resolution logic that Task 2 uses for the outbound HTTP payload.
        if hasattr(adapter, '_resolve_model'):
            return adapter._resolve_model(request)
        if request.model:
            return request.model
        model_env = getattr(adapter.config, 'model_env_var', '')
        return (os.environ.get(model_env) if model_env else None) or getattr(adapter.config, 'default_model', '')

    def _breaker(self, provider: str, runtime: dict[str, Any]) -> CircuitBreaker:
        return CircuitBreaker.from_dict(runtime.get('circuit_breakers', {}).get(provider, {}),
                     failure_threshold=self._config.failure_threshold,
                     recovery_timeout=self._config.recovery_timeout)

    def _task_lease(self, task_id: str, owner: str, now: float) -> None:
        def claim(rt):
            until = rt.get('paused_until', 0)
            if isinstance(until, (int, float)) and now < until:
                raise RouterPaused(f'Router paused until {until}')
            leases = rt.setdefault('leases', {})
            # Expire crashed jobs; active jobs are protected across runners.
            for key in list(leases):
                if leases[key].get('until', 0) <= now:
                    del leases[key]
            if task_id in leases:
                raise RouterPaused('Task already being processed; wait for lease expiry')
            # Clear half-open probe ownership left by a killed runner.
            probes = rt.setdefault('half_open_probes', {})
            for provider in list(probes):
                if probes[provider] not in leases:
                    del probes[provider]
            leases[task_id] = {'owner': owner, 'until': now + self._config.lease_seconds}
        self._runtime_store.transact(claim, operation_id='claim-task')

    def _release(self, task_id: str, owner: str) -> None:
        def unlock(rt):
            leases = rt.get('leases', {})
            if leases.get(task_id, {}).get('owner') == owner:
                del leases[task_id]
                for provider in list(rt.get('half_open_probes', {})):
                    if rt['half_open_probes'][provider] == task_id:
                        del rt['half_open_probes'][provider]
        self._runtime_store.transact(unlock, operation_id='release-task')

    def _reserve_provider(self, provider: str, task_id: str, now: float, reservation_id: str, attempts: int) -> bool:
        """Pessimistically reserve full retry budget *before* network use."""
        def reserve(rt):
            cb = self._breaker(provider, rt)
            if not cb.is_call_permitted(now):
                return False
            if rt.get('cooldowns', {}).get(provider, 0) > now:
                return False
            quotas = rt.setdefault('quotas', {})
            q = quotas.setdefault(provider, {})
            reservations = rt.setdefault('reservations', {})
            # Retain reservation IDs only long enough to resolve an uncertain
            # push. Stale IDs otherwise grow forever on a long-running agent.
            for key in list(reservations):
                if reservations[key].get('at', 0) < now - 86400:
                    del reservations[key]
            if reservation_id in reservations:
                return True
            probe = rt.setdefault('half_open_probes', {})
            if cb.state is CircuitState.HALF_OPEN and provider in probe and probe[provider] != task_id:
                return False
            # Persistent rolling windows across CI runs; default caps are conservative.
            minute = [x for x in q.get('minute', []) if x > now - 60]
            day = [x for x in q.get('day', []) if x > now - 86400]
            cap_minute = int(self._config.rpm.get(provider, 0))
            cap_day = int(self._config.rpd.get(provider, 0))
            if cap_minute < 1 or cap_day < 1:
                return False
            if len(minute) + attempts > cap_minute or len(day) + attempts > cap_day:
                q['minute'] = minute
                q['day'] = day
                return False
            q['minute'] = minute + [now] * attempts
            q['day'] = day + [now] * attempts
            q['date'] = time.strftime('%Y-%m-%d', time.gmtime(now))
            q['count'] = len(q['day'])
            reservations[reservation_id] = {'provider': provider, 'task_id': task_id, 'at': now}
            rt.setdefault('circuit_breakers', {})[provider] = cb.to_dict()
            if cb.state is CircuitState.HALF_OPEN:
                probe[provider] = task_id
            return True
        return self._runtime_store.transact(reserve, operation_id='reserve-'+provider)

    def _record(self, provider: str, kind: str, now: float, retry_after: float | None = None) -> None:
        def apply(rt):
            cb = self._breaker(provider, rt)
            if kind == 'success':
                cb.record_success()
                rt.setdefault('cooldowns', {}).pop(provider, None)
            else:
                cb.record_failure(now)
                if kind == 'limit':
                    wait = retry_after if retry_after is not None else self._config.rate_limit_default_cooldown
                    rt.setdefault('cooldowns', {})[provider] = now + max(wait, 0)
                if kind == 'auth':
                    rt.setdefault('cooldowns', {})[provider] = now + 86400
            rt.setdefault('circuit_breakers', {})[provider] = cb.to_dict()
            rt.setdefault('half_open_probes', {}).pop(provider, None)
        self._runtime_store.transact(apply, operation_id=kind+'-'+provider)

    def execute(self, task_type: str, input_data: Any,
                request: LLMRequest, schema: Type[BaseModel]) -> BaseModel:
        task_id = compute_task_id(task_type, {'input': input_data,
                **self._fingerprint(request, schema)}, self._config.schema_version)
        # Never call an API for a durable completed task.
        self._state.pull()
        cached = self._state.get_cached_result(task_id)
        if cached is not None:
            return schema.model_validate(cached)
        if os.environ.get('ROUTER_ALLOW_LIVE_API') != '1':
            raise LiveAPINotAuthorized('ROUTER_ALLOW_LIVE_API=1 is required')
        owner = uuid.uuid4().hex
        self._task_lease(task_id, owner, self._clock())
        try:
            # Another process may have completed between our first read and lease.
            self._state.pull()
            cached = self._state.get_cached_result(task_id)
            if cached is not None:
                return schema.model_validate(cached)
            last_error: Optional[Exception] = None
            for provider in self._config.provider_order:
                adapter = self._adapters.get(provider)
                if adapter is None:
                    continue
                try:
                    resolved = self._model(adapter, request)
                    require_free_model(provider, resolved)
                except (BillableModelRejected, AdapterError) as exc:
                    last_error = exc
                    continue
                send = replace(request, schema=schema, model=resolved)
                cfg = getattr(adapter, 'config', None)
                max_attempts = int(getattr(cfg, 'max_retries', 1))
                if not 1 <= max_attempts <= 5:
                    raise RouterError('Unsafe adapter retry configuration')
                reservation_id = uuid.uuid4().hex
                if not self._reserve_provider(provider, task_id, self._clock(), reservation_id, max_attempts):
                    continue
                try:
                    response = adapter.complete(send)
                except RateLimitError as exc:
                    last_error = exc
                    self._record(provider, 'limit', self._clock(), exc.retry_after)
                    continue
                except (AuthError, ClientError) as exc:
                    last_error = exc
                    self._record(provider, 'auth', self._clock())
                    continue
                except (ServerError, AdapterError) as exc:
                    last_error = exc
                    self._record(provider, 'failure', self._clock())
                    continue
                parsed = getattr(response, 'parsed', None)
                if parsed is None:
                    last_error = RouterError('Provider returned no parsed data')
                    self._record(provider, 'failure', self._clock())
                    continue
                try:
                    verified = schema.model_validate(parsed.model_dump())
                except Exception as exc:
                    last_error = exc
                    self._record(provider, 'failure', self._clock())
                    continue
                self._record(provider, 'success', self._clock())
                self._state.record_completion(task_id, task_type, verified.model_dump())
                # If a concurrent owner completed first, return the durable
                # result, not an uncommitted result from our own provider.
                durable = self._state.get_cached_result(task_id)
                if durable is None:
                    raise RouterError('Completion is missing after state commit')
                return schema.model_validate(durable)
            self._runtime_store.transact(
                lambda rt: rt.update(paused_until=self._clock() + self._config.all_failed_pause),
                operation_id='all-failed')
            raise AllProvidersFailed('No available approved provider. Last error: ' + repr(last_error))
        finally:
            self._release(task_id, owner)
