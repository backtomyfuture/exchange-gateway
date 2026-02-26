"""Generic async circuit breaker for Exchange EWS operations.

States:
  CLOSED    → calls pass through; failures increment counter
  OPEN      → calls immediately raise CircuitOpenError
  HALF_OPEN → probe call; success→CLOSED, failure→OPEN
"""

import asyncio
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is OPEN and rejects the call."""


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 1
    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    failure_count: int = field(default=0, init=False)
    last_failure_time: float = field(default=0.0, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def _should_attempt_reset(self) -> bool:
        return (time.monotonic() - self.last_failure_time) >= self.recovery_timeout

    async def _on_success(self) -> None:
        async with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED

    async def _on_failure(self) -> None:
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.monotonic()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

    async def call(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
        **kwargs: Any,
    ) -> Any:
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    remaining = self.recovery_timeout - (time.monotonic() - self.last_failure_time)
                    raise CircuitOpenError(f"Circuit OPEN. Retry in {remaining:.1f}s")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except retryable_exceptions:
            await self._on_failure()
            raise
