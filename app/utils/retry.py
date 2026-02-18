"""Async retry decorator with exponential backoff."""
import asyncio
import functools
import logging
from typing import Type

logger = logging.getLogger(__name__)


def async_retry(
    max_attempts: int = 3,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
):
    """Retry an async function on specified exceptions with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = base_delay
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    logger.warning(
                        "Retry %d/%d for %s after %s: %s",
                        attempt, max_attempts, func.__name__, type(exc).__name__, exc,
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            raise last_exc
        return wrapper
    return decorator
