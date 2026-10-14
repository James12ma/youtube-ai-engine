"""Per-provider circuit breaker with JSON-friendly serialization."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_timeout: float = 900.0
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    opened_at: Optional[float] = None
    def is_call_permitted(self, now: float) -> bool:
        if self.state is CircuitState.CLOSED: return True
        if self.state is CircuitState.OPEN:
            if self.opened_at is not None and now - self.opened_at >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True
    def record_success(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.opened_at = None
    def record_failure(self, now: float) -> None:
        self.failure_count += 1
        if self.state is CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = now
    def trip_permanently(self, now: float) -> None:
        self.state = CircuitState.OPEN
        self.opened_at = now
    def to_dict(self) -> dict:
        return {"state": self.state.value, "failure_count": self.failure_count, "opened_at": self.opened_at}
    @classmethod
    def from_dict(cls, data: Any, *, failure_threshold: int, recovery_timeout: float) -> "CircuitBreaker":
        if not isinstance(data, dict): return cls(failure_threshold=failure_threshold, recovery_timeout=recovery_timeout)
        try: state = CircuitState(data.get("state", "closed"))
        except ValueError: state = CircuitState.CLOSED
        return cls(failure_threshold=failure_threshold, recovery_timeout=recovery_timeout,
                   state=state, failure_count=int(data.get("failure_count", 0) or 0), opened_at=data.get("opened_at"))
