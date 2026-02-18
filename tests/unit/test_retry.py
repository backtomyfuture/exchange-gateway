import pytest
from app.utils.retry import async_retry


@pytest.mark.asyncio
async def test_succeeds_on_first_try():
    call_count = 0

    @async_retry(max_attempts=3, exceptions=(ValueError,), base_delay=0.01)
    async def func():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await func()
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retries_on_matching_exception():
    call_count = 0

    @async_retry(max_attempts=3, exceptions=(ValueError,), base_delay=0.01)
    async def func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("transient")
        return "ok"

    result = await func()
    assert result == "ok"
    assert call_count == 3


@pytest.mark.asyncio
async def test_raises_after_max_attempts():
    @async_retry(max_attempts=3, exceptions=(ValueError,), base_delay=0.01)
    async def func():
        raise ValueError("always fails")

    with pytest.raises(ValueError):
        await func()


@pytest.mark.asyncio
async def test_does_not_catch_non_matching_exception():
    @async_retry(max_attempts=3, exceptions=(ValueError,), base_delay=0.01)
    async def func():
        raise TypeError("wrong type")

    with pytest.raises(TypeError):
        await func()
