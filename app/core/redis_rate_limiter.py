"""Redis 滑动窗口速率限制器。

使用有序集合（ZSET）实现 O(log N) 的每请求速率限制。
每个请求以时间戳为 score 存储，窗口清理删除超出时间范围的条目。
"""

import time
import uuid

import structlog

logger = structlog.get_logger(__name__)


class RedisRateLimiter:
    """基于 Redis 有序集合的分布式滑动窗口速率限制器。"""

    def __init__(self, redis):
        self._redis = redis

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int]:
        """检查请求是否在速率限制内。

        Returns:
            (is_allowed, current_count, remaining)
        """
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key}"

        # 清理窗口外的旧条目
        await self._redis.zremrangebyscore(redis_key, "-inf", window_start)

        # 统计当前窗口内的请求数
        current_count = await self._redis.zcard(redis_key)

        if current_count >= limit:
            return False, current_count, 0

        # 记录本次请求（用 uuid 防止重复 member）
        member = f"{now}:{uuid.uuid4().hex[:8]}"
        await self._redis.zadd(redis_key, {member: now})
        await self._redis.expire(redis_key, window_seconds + 10)

        current_count += 1
        remaining = max(0, limit - current_count)
        return True, current_count, remaining


# 模块级实例，在应用启动时设置
_rate_limiter: RedisRateLimiter | None = None


def get_rate_limiter() -> "RedisRateLimiter":
    """获取已初始化的速率限制器。必须在 init_rate_limiter() 之后调用。"""
    if _rate_limiter is None:
        from app.core.rate_limiter import get_rate_limiter as get_mem_limiter

        return get_mem_limiter()
    return _rate_limiter


async def init_rate_limiter() -> None:
    """初始化 Redis 速率限制器。在应用启动时调用。"""
    global _rate_limiter
    try:
        import redis.asyncio as aioredis

        from app.settings.config import settings

        redis_client = aioredis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        _rate_limiter = RedisRateLimiter(redis=redis_client)
        logger.info("Redis 速率限制器已初始化")
    except Exception as e:
        logger.warning("Redis 不可用，使用内存速率限制器作为回退", error=str(e))
        _rate_limiter = None
