"""
ARQ Redis connection pool — app-level singleton for job enqueueing.
Initialize via init_arq_pool() in app lifespan startup.
"""
from arq.connections import ArqRedis, RedisSettings, create_pool
from app.settings import settings

_arq_pool: ArqRedis | None = None


async def init_arq_pool() -> ArqRedis:
    """Create and store the ARQ pool. Call once on app startup."""
    global _arq_pool
    _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _arq_pool


async def close_arq_pool() -> None:
    """Close the ARQ pool. Call once on app shutdown."""
    global _arq_pool
    if _arq_pool:
        await _arq_pool.close()
        _arq_pool = None


def get_arq_pool() -> ArqRedis:
    """Get the ARQ pool. Raises RuntimeError if not initialized."""
    if _arq_pool is None:
        raise RuntimeError("ARQ pool not initialized. Call init_arq_pool() first.")
    return _arq_pool
