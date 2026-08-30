import asyncio
import threading

import pytest

from app.utils import async_helpers
from app.utils.async_helpers import run_sync_with_timeout


async def _wait_for_thread_event(event: threading.Event, timeout: float = 1.0):
    async with asyncio.timeout(timeout):
        while not event.is_set():
            await asyncio.sleep(0.001)


@pytest.mark.asyncio
async def test_run_sync_basic():
    def add(a, b):
        return a + b

    result = await run_sync_with_timeout(add, 2, 3, timeout=5.0)
    assert result == 5


@pytest.mark.asyncio
async def test_run_sync_timeout():
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def slow():
        started.set()
        release.wait()
        finished.set()

    task = asyncio.create_task(run_sync_with_timeout(slow, timeout=0.01))
    await _wait_for_thread_event(started)
    try:
        with pytest.raises(asyncio.TimeoutError):
            await task
    finally:
        release.set()
        await _wait_for_thread_event(finished)


@pytest.mark.asyncio
async def test_timeout_keeps_ews_capacity_until_blocking_work_exits(monkeypatch):
    semaphore = asyncio.Semaphore(1)
    monkeypatch.setattr(async_helpers, "_ews_semaphore", semaphore)
    started = threading.Event()
    release = threading.Event()

    def blocked():
        started.set()
        release.wait()

    first = asyncio.create_task(run_sync_with_timeout(blocked, timeout=0.01))
    await _wait_for_thread_event(started)
    with pytest.raises(asyncio.TimeoutError):
        await first

    second = asyncio.create_task(run_sync_with_timeout(lambda: "second", timeout=1.0))
    await asyncio.sleep(0.01)
    assert not second.done()

    release.set()
    assert await second == "second"
