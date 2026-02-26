import asyncio
import time

import pytest

from app.utils.async_helpers import run_sync_with_timeout


@pytest.mark.asyncio
async def test_run_sync_basic():
    def add(a, b):
        return a + b

    result = await run_sync_with_timeout(add, 2, 3, timeout=5.0)
    assert result == 5


@pytest.mark.asyncio
async def test_run_sync_timeout():
    def slow():
        time.sleep(10)

    with pytest.raises(asyncio.TimeoutError):
        await run_sync_with_timeout(slow, timeout=0.1)
