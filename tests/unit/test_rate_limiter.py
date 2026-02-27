import asyncio

import pytest

from app.core.rate_limiter import RateLimiter


@pytest.fixture
def limiter():
    return RateLimiter()


@pytest.mark.asyncio
async def test_allows_within_limit(limiter):
    allowed, count, remaining = await limiter.is_allowed("key1", limit=5, window_seconds=60)
    assert allowed is True
    assert count == 1
    assert remaining == 4


@pytest.mark.asyncio
async def test_blocks_over_limit(limiter):
    for _ in range(3):
        await limiter.is_allowed("key2", limit=3, window_seconds=60)

    allowed, count, remaining = await limiter.is_allowed("key2", limit=3, window_seconds=60)
    assert allowed is False
    assert count == 3
    assert remaining == 0


@pytest.mark.asyncio
async def test_window_expiry(limiter):
    for _ in range(2):
        await limiter.is_allowed("key3", limit=2, window_seconds=0.1)

    allowed, _, _ = await limiter.is_allowed("key3", limit=2, window_seconds=0.1)
    assert allowed is False

    await asyncio.sleep(0.15)

    allowed, count, remaining = await limiter.is_allowed("key3", limit=2, window_seconds=0.1)
    assert allowed is True
    assert count == 1
    assert remaining == 1


@pytest.mark.asyncio
async def test_get_status(limiter):
    await limiter.is_allowed("key4", limit=10, window_seconds=60)
    await limiter.is_allowed("key4", limit=10, window_seconds=60)

    status = await limiter.get_status("key4", window_seconds=60)
    assert status["key"] == "key4"
    assert status["current_count"] == 2
    assert status["window_seconds"] == 60
    assert status["oldest_request"] is not None
