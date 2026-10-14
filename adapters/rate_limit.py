"""Thread-safe sliding-window rate limiter with cooldown support."""
from __future__ import annotations
import threading
import time
from collections import deque
from typing import Callable, Optional

from .errors import RateLimitError
class RateLimiter:
    MINUTE = 60.0
    DAY = 86_400.0
    def __init__(self, rpm: int, rpd: int, *, monotonic: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep) -> None:
        if rpm <= 0 or rpd <= 0:
            raise ValueError("rpm and rpd must be positive")
        self._rpm = rpm
        self._rpd = rpd
        self._minute: deque[float] = deque()
        self._day: deque[float] = deque()
        self._cooldown_until = 0.0
        self._lock = threading.Lock()
        self._monotonic = monotonic
        self._sleep = sleep
    def _evict(self, now: float) -> None:
        while self._minute and now - self._minute[0] >= self.MINUTE:
            self._minute.popleft()
        while self._day and now - self._day[0] >= self.DAY:
            self._day.popleft()
    def _wait_time(self, now: float) -> float:
        if now < self._cooldown_until:
            return self._cooldown_until - now
        if len(self._minute) >= self._rpm:
            return self.MINUTE - (now - self._minute[0])
        if len(self._day) >= self._rpd:
            return self.DAY - (now - self._day[0])
        return 0.0
    def acquire(self, *, max_wait_seconds: Optional[float] = None) -> None:
        """Reserve one request; optionally refuse to wait through long exhaustion."""
        while True:
            with self._lock:
                now = self._monotonic()
                self._evict(now)
                wait = self._wait_time(now)
                if wait <= 0:
                    self._minute.append(now)
                    self._day.append(now)
                    return
            if max_wait_seconds is not None and wait > max_wait_seconds:
                raise RateLimitError(
                    "Local provider quota/cooldown exhausted",
                    retry_after=wait,
                )
            self._sleep(max(wait, 0.01))
    def penalize(self, seconds: float) -> None:
        with self._lock:
            self._cooldown_until = max(self._cooldown_until, self._monotonic() + max(seconds, 0.0))
