import asyncio

import pytest

from app.services.exchange.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


@pytest.mark.asyncio
async def test_starts_closed():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    async def fail():
        raise ValueError("fail")

    for _ in range(3):
        with pytest.raises(ValueError):
            await cb.call(fail, retryable_exceptions=(ValueError,))

    assert cb.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_open_raises_circuit_open_error():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)

    async def fail():
        raise ValueError("fail")

    with pytest.raises(ValueError):
        await cb.call(fail, retryable_exceptions=(ValueError,))  # Opens

    with pytest.raises(CircuitOpenError):
        await cb.call(fail, retryable_exceptions=(ValueError,))  # Rejects immediately


@pytest.mark.asyncio
async def test_recovers_after_timeout():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)

    async def fail():
        raise ValueError("fail")

    with pytest.raises(ValueError):
        await cb.call(fail, retryable_exceptions=(ValueError,))  # Opens

    await asyncio.sleep(0.1)

    async def succeed():
        return "ok"

    result = await cb.call(succeed, retryable_exceptions=(ValueError,))
    assert result == "ok"
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_success_resets_failure_count():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    async def fail():
        raise ValueError("fail")

    async def succeed():
        return "ok"

    for _ in range(2):
        with pytest.raises(ValueError):
            await cb.call(fail, retryable_exceptions=(ValueError,))

    await cb.call(succeed, retryable_exceptions=(ValueError,))
    assert cb.failure_count == 0
    assert cb.state == CircuitState.CLOSED
