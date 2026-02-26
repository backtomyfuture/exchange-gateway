"""Redis 分布式迁移锁。

确保多 worker 启动时只有一个 worker 执行 Aerich 迁移，
其他 worker 等待完成后直接跳过。
"""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class MigrationLock:
    """基于 Redis SET NX 的数据库迁移分布式锁。"""

    def __init__(self, redis_client, lock_key: str = "exchange-gw:migration-lock", ttl: int = 120):
        self._redis = redis_client
        self._key = lock_key
        self._ttl = ttl
        self._lock_value = f"worker-{time.monotonic_ns()}"

    async def acquire(self) -> bool:
        """尝试获取锁。返回 True 表示获取成功，False 表示已被其他 worker 持有。"""
        result = await self._redis.set(self._key, self._lock_value, ex=self._ttl, nx=True)
        if result:
            logger.info("迁移锁已获取")
            return True
        logger.info("迁移锁被其他 worker 持有，等待中")
        return False

    async def release(self) -> None:
        """释放锁。"""
        await self._redis.delete(self._key)
        logger.info("迁移锁已释放")

    async def wait_for_completion(self, poll_interval: float = 1.0, max_wait: float = 120.0) -> None:
        """等待直到锁被释放（其他 worker 完成迁移）。"""
        start = time.monotonic()
        while time.monotonic() - start < max_wait:
            val = await self._redis.get(self._key)
            if val is None:
                logger.info("其他 worker 已完成迁移")
                return
            await asyncio.sleep(poll_interval)
        logger.warning("等待迁移锁超时 %.1fs", max_wait)
