import asyncio
import logging
from datetime import datetime
from enum import Enum

from app.core.exceptions import CircuitOpenError

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, rate: float, capacity: int) -> None:
        self.rate = rate
        self.capacity = capacity
        self._tokens = capacity
        self._last_update = datetime.now()
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: float = 30.0) -> bool:
        start_time = asyncio.get_event_loop().time()

        while True:
            async with self._lock:
                now = datetime.now()
                elapsed = (now - self._last_update).total_seconds()
                self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
                self._last_update = now

                if self._tokens >= 1:
                    self._tokens -= 1
                    return True

            elapsed = asyncio.get_event_loop().time() - start_time
            wait_time = (1 - self._tokens) / self.rate
            if elapsed + wait_time > timeout:
                raise asyncio.TimeoutError("Rate limiter acquisition timeout")

            await asyncio.sleep(wait_time)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: datetime | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def call(self, func, *args, **kwargs):
        async with self._lock:
            await self._check_state_transition()

            if self._state == CircuitState.OPEN:
                raise CircuitOpenError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            logger.warning(f"Circuit breaker error in {func.__name__}: {e}")
            raise

    async def _check_state_transition(self) -> None:
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    logger.info("Circuit breaker transitioning to CLOSED")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()

            if (
                self._state == CircuitState.HALF_OPEN
                or self._failure_count >= self.failure_threshold
            ):
                logger.warning("Circuit breaker transitioning to OPEN")
                self._state = CircuitState.OPEN


__all__ = [
    "RateLimiter",
    "CircuitState",
    "CircuitBreaker",
]
