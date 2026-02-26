from unittest.mock import AsyncMock

import pytest

from app.utils.migration_lock import MigrationLock


@pytest.fixture
def mock_redis():
    return AsyncMock()


@pytest.fixture
def lock(mock_redis):
    return MigrationLock(mock_redis, lock_key="test:lock", ttl=60)


@pytest.mark.asyncio
async def test_acquire_success(lock, mock_redis):
    mock_redis.set.return_value = True
    result = await lock.acquire()
    assert result is True
    mock_redis.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_acquire_already_held(lock, mock_redis):
    mock_redis.set.return_value = None
    result = await lock.acquire()
    assert result is False


@pytest.mark.asyncio
async def test_release(lock, mock_redis):
    await lock.release()
    mock_redis.delete.assert_awaited_once_with("test:lock")


@pytest.mark.asyncio
async def test_wait_for_completion(lock, mock_redis):
    mock_redis.get.return_value = None
    await lock.wait_for_completion(poll_interval=0.01, max_wait=1.0)
    mock_redis.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_wait_for_completion_timeout(lock, mock_redis):
    mock_redis.get.return_value = b"some-worker"
    await lock.wait_for_completion(poll_interval=0.01, max_wait=0.05)
    assert mock_redis.get.await_count >= 2
