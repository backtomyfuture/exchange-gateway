"""Async helpers for running blocking operations safely."""

import asyncio
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

# 专用 EWS 线程池，大小与连接池对齐
# 默认 20 线程 = max_connections_per_account(5) * 预期活跃账户数(4)
EWS_MAX_WORKERS: int = int(os.getenv("EWS_MAX_WORKERS", "20"))
EWS_MAX_CONCURRENT: int = int(os.getenv("EWS_MAX_CONCURRENT", "20"))

_ews_executor = ThreadPoolExecutor(
    max_workers=EWS_MAX_WORKERS,
    thread_name_prefix="ews",
)

# 信号量限制并发 EWS 操作数，防止线程池 + 连接池同时过载
_ews_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    """懒加载信号量，确保在事件循环启动后创建。"""
    global _ews_semaphore
    if _ews_semaphore is None:
        _ews_semaphore = asyncio.Semaphore(EWS_MAX_CONCURRENT)
    return _ews_semaphore


async def run_sync_with_timeout(func: Callable[..., Any], *args: Any, timeout: float = 30.0, **kwargs: Any) -> Any:
    """在专用 EWS 线程池中运行同步函数，带超时和并发保护。"""
    loop = asyncio.get_running_loop()
    bound = partial(func, *args, **kwargs)
    async with _get_semaphore():
        return await asyncio.wait_for(
            loop.run_in_executor(_ews_executor, bound),
            timeout=timeout,
        )
