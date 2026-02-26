from unittest.mock import AsyncMock, patch

import pytest

from app.core.redis_rate_limiter import RedisRateLimiter, get_rate_limiter


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.zremrangebyscore = AsyncMock()
    r.zcard = AsyncMock(return_value=3)
    r.zadd = AsyncMock()
    r.expire = AsyncMock()
    return r


@pytest.fixture
def limiter(mock_redis):
    return RedisRateLimiter(redis=mock_redis)


@pytest.mark.asyncio
async def test_is_allowed_within_limit(limiter, mock_redis):
    mock_redis.zcard.return_value = 3
    allowed, count, remaining = await limiter.is_allowed("api:test", limit=10, window_seconds=60)
    assert allowed is True
    assert count == 4
    assert remaining == 6


@pytest.mark.asyncio
async def test_is_allowed_exceeds_limit(limiter, mock_redis):
    mock_redis.zcard.return_value = 10
    allowed, count, remaining = await limiter.is_allowed("api:test", limit=10, window_seconds=60)
    assert allowed is False
    assert count == 10
    assert remaining == 0


def test_fallback_to_memory():
    with patch("app.core.redis_rate_limiter._rate_limiter", None):
        limiter = get_rate_limiter()
        from app.core.rate_limiter import RateLimiter
        assert isinstance(limiter, RateLimiter)
