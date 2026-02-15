"""
API 速率限制器
基于内存的滑动窗口算法实现
"""
import asyncio
import time
from collections import defaultdict
from typing import Optional
from app.log import logger


class RateLimiter:
    """
    滑动窗口速率限制器
    
    使用时间窗口内的请求计数来限制请求频率
    """
    
    def __init__(self, cleanup_interval: int = 60):
        """
        初始化速率限制器
        
        Args:
            cleanup_interval: 清理过期记录的间隔（秒）
        """
        # 存储格式: {key: [(timestamp1, count1), (timestamp2, count2), ...]}
        self._requests: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int = 60
    ) -> tuple[bool, int, int]:
        """
        检查请求是否被允许
        
        Args:
            key: 限制的键（如 API Key ID）
            limit: 窗口内允许的最大请求数
            window_seconds: 时间窗口大小（秒）
            
        Returns:
            (是否允许, 当前请求数, 剩余配额)
        """
        now = time.time()
        window_start = now - window_seconds
        
        async with self._lock:
            # 清理过期的请求记录
            self._requests[key] = [
                (ts, count) for ts, count in self._requests[key]
                if ts > window_start
            ]
            
            # 计算窗口内的请求总数
            current_count = sum(count for _, count in self._requests[key])
            
            if current_count >= limit:
                # 超出限制
                remaining = 0
                logger.warning(f"速率限制触发: key={key}, count={current_count}, limit={limit}")
                return False, current_count, remaining
            
            # 记录本次请求
            self._requests[key].append((now, 1))
            current_count += 1
            remaining = max(0, limit - current_count)
            
            # 定期清理所有过期记录
            if now - self._last_cleanup > self._cleanup_interval:
                await self._cleanup()
                self._last_cleanup = now
            
            return True, current_count, remaining
    
    async def _cleanup(self):
        """清理所有过期的请求记录"""
        now = time.time()
        window_start = now - 60  # 默认清理 1 分钟前的记录
        
        keys_to_delete = []
        for key, requests in self._requests.items():
            self._requests[key] = [
                (ts, count) for ts, count in requests
                if ts > window_start
            ]
            if not self._requests[key]:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self._requests[key]
        
        if keys_to_delete:
            logger.debug(f"速率限制器清理: 移除 {len(keys_to_delete)} 个过期键")
    
    async def get_status(self, key: str, window_seconds: int = 60) -> dict:
        """
        获取指定键的速率限制状态
        
        Args:
            key: 限制的键
            window_seconds: 时间窗口大小
            
        Returns:
            状态信息字典
        """
        now = time.time()
        window_start = now - window_seconds
        
        async with self._lock:
            current_requests = [
                (ts, count) for ts, count in self._requests.get(key, [])
                if ts > window_start
            ]
            current_count = sum(count for _, count in current_requests)
            
            return {
                "key": key,
                "current_count": current_count,
                "window_seconds": window_seconds,
                "oldest_request": min((ts for ts, _ in current_requests), default=None),
            }


# 全局速率限制器实例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取全局速率限制器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
