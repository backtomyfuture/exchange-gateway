"""
Exchange 连接池管理
复用连接以提高性能，支持自动重连和健康检查
"""

import asyncio
import time
from contextlib import asynccontextmanager

import urllib3
from exchangelib import (
    DELEGATE,
    NTLM,
    Account,
    Configuration,
    Credentials,
)
from exchangelib.errors import ErrorTimeoutExpired, TransportError
from exchangelib.protocol import BaseProtocol, FaultTolerance

from app.log import logger
from app.models.exchange import ExchangeAccount
from app.services.exchange.circuit_breaker import CircuitBreaker
from app.settings import settings
from app.utils.crypto import get_crypto
from app.utils.exchange_adapter import LegacySSLAdapter

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 使用自定义 Adapter 解决 SSLEOFError 和主机名不匹配
BaseProtocol.HTTP_ADAPTER_CLS = LegacySSLAdapter


class ExchangeConnection:
    """
    Exchange 连接封装
    """

    def __init__(self, account: Account, account_id: int):
        self.account = account
        self.account_id = account_id
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.in_use = False
        self._lock = asyncio.Lock()

    def is_expired(self, max_age: int = 3600) -> bool:
        """检查连接是否过期（默认1小时）"""
        return time.time() - self.created_at > max_age

    def touch(self):
        """更新最后使用时间"""
        self.last_used_at = time.time()

    async def is_healthy(self) -> bool:
        """检查连接是否健康"""
        try:
            # 尝试获取收件箱信息来验证连接
            # 使用 run_in_executor 避免阻塞事件循环
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: self.account.inbox.total_count)
            return True
        except Exception as e:
            logger.warning(f"连接健康检查失败: {e}")
            return False


class ExchangeConnectionPool:
    """
    Exchange 连接池
    管理多个账户的连接，支持连接复用、自动清理和连接预热
    """

    # 全局连接池最大容量（防止内存泄漏）
    MAX_TOTAL_CONNECTIONS = 100
    # 全局连接统计
    _total_connections: int = 0

    def __init__(self, max_connections_per_account: int = 5, max_age: int = 3600):
        self._pools: dict[int, list[ExchangeConnection]] = {}
        self._max_per_account = max_connections_per_account
        self._max_age = max_age
        self._lock = asyncio.Lock()
        self._crypto = None
        # 预热状态追踪
        self._warmup_status: dict[int, bool] = {}
        # 预热任务
        self._warmup_tasks: dict[int, asyncio.Task] = {}
        # Per-account circuit breakers
        self._circuit_breakers: dict[int, CircuitBreaker] = {}

    @property
    def crypto(self):
        if self._crypto is None:
            self._crypto = get_crypto()
        return self._crypto

    async def _create_connection(self, db_account: ExchangeAccount) -> ExchangeConnection:
        """
        创建新的 Exchange 连接
        """
        try:
            # 解密密码
            password = self.crypto.decrypt(db_account.encrypted_password)

            # 获取配置
            server = db_account.server or settings.EXCHANGE_SERVER
            domain = db_account.domain or settings.EXCHANGE_DOMAIN

            # 构建完整用户名
            full_username = f"{domain}\\{db_account.username}"

            # 放到线程池中执行
            loop = asyncio.get_running_loop()

            def create_account_ops():
                # 创建凭据
                credentials = Credentials(full_username, password)

                # 创建配置
                config = Configuration(
                    server=server,
                    credentials=credentials,
                    auth_type=NTLM,
                    retry_policy=FaultTolerance(max_wait=60),
                )

                # 创建账户
                return Account(
                    primary_smtp_address=db_account.email, config=config, autodiscover=False, access_type=DELEGATE
                )

            account = await loop.run_in_executor(None, create_account_ops)

            logger.info(f"Exchange 连接创建成功: {db_account.email}")
            return ExchangeConnection(account, db_account.id)

        except Exception as e:
            logger.error(f"创建 Exchange 连接失败: {db_account.email}, 错误: {e}")
            raise

    def _get_circuit_breaker(self, account_id: int) -> CircuitBreaker:
        """Get or create per-account circuit breaker."""
        if account_id not in self._circuit_breakers:
            self._circuit_breakers[account_id] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60.0,
            )
        return self._circuit_breakers[account_id]

    async def get_connection(self, account_id: int) -> ExchangeConnection:
        """Get a connection, protected by per-account circuit breaker."""
        cb = self._get_circuit_breaker(account_id)
        return await cb.call(
            self._get_connection_inner,
            account_id,
            retryable_exceptions=(TransportError, ErrorTimeoutExpired, ConnectionError),
        )

    async def _get_connection_inner(self, account_id: int) -> ExchangeConnection:
        """
        Acquire a connection for *account_id*, preferring pool reuse.

        Design note – avoid holding the global lock during async I/O:
        The lock is only held long enough to inspect pool state and
        optimistically mark a candidate as in-use.  All actual network I/O
        (health-check, EWS Account creation) happens *outside* the lock so
        concurrent requests for different accounts are never serialised.
        """
        # ── Step 1: look for an idle, non-expired connection ──────────────
        candidate: ExchangeConnection | None = None
        async with self._lock:
            if account_id in self._pools:
                pool = self._pools[account_id]
                # Purge expired entries while we hold the lock
                self._pools[account_id] = [c for c in pool if not c.is_expired(self._max_age)]
                for conn in self._pools[account_id]:
                    if not conn.in_use:
                        # Optimistically reserve so no other coroutine steals it
                        conn.in_use = True
                        candidate = conn
                        break

        # ── Step 2: validate the candidate *outside* the lock ─────────────
        if candidate is not None:
            if await candidate.is_healthy():
                candidate.touch()
                return candidate
            # Unhealthy – remove from pool and fall through to create a new one
            candidate.in_use = False
            async with self._lock:
                if account_id in self._pools:
                    self._pools[account_id] = [c for c in self._pools[account_id] if c is not candidate]
                ExchangeConnectionPool._total_connections = max(0, ExchangeConnectionPool._total_connections - 1)

        # ── Step 3: create a new connection (DB + EWS I/O, no lock held) ──
        db_account = await ExchangeAccount.filter(id=account_id).first()
        if not db_account:
            raise ValueError(f"Account not found: {account_id}")
        if not db_account.is_active:
            raise ValueError(f"Account is disabled: {db_account.email}")

        new_conn = await self._create_connection(db_account)
        new_conn.in_use = True

        # ── Step 4: register connection in the pool ───────────────────────
        async with self._lock:
            if account_id not in self._pools:
                self._pools[account_id] = []
            if len(self._pools[account_id]) < self._max_per_account:
                self._pools[account_id].append(new_conn)
            ExchangeConnectionPool._total_connections += 1

        return new_conn

    async def release_connection(self, conn: ExchangeConnection):
        """
        释放连接（标记为可用）
        """
        conn.touch()
        conn.in_use = False

    async def close_account_connections(self, account_id: int):
        """
        关闭指定账户的所有连接
        """
        async with self._lock:
            if account_id in self._pools:
                del self._pools[account_id]
                logger.info(f"已关闭账户 {account_id} 的所有连接")

    async def cleanup_expired(self):
        """Remove all expired connections and update the global counter."""
        async with self._lock:
            for account_id in list(self._pools.keys()):
                before = len(self._pools[account_id])
                self._pools[account_id] = [c for c in self._pools[account_id] if not c.is_expired(self._max_age)]
                removed = before - len(self._pools[account_id])
                ExchangeConnectionPool._total_connections = max(0, ExchangeConnectionPool._total_connections - removed)
                if not self._pools[account_id]:
                    del self._pools[account_id]

    async def warmup_connections(self, account_id: int, min_connections: int = 2):
        """
        预热连接池：为指定账户预先创建连接

        Args:
            account_id: 账户ID
            min_connections: 最小连接数（默认2个）

        Returns:
            dict: 预热结果 {"success": bool, "created": int, "message": str}
        """
        if self._warmup_status.get(account_id, False):
            return {"success": True, "created": 0, "message": "连接已预热"}

        try:
            db_account = await ExchangeAccount.filter(id=account_id).first()
            if not db_account:
                return {"success": False, "created": 0, "message": f"账户不存在: {account_id}"}

            if not db_account.is_active:
                return {"success": False, "created": 0, "message": f"账户已禁用: {db_account.email}"}

            created = 0
            async with self._lock:
                # 检查现有连接数
                existing_count = len(self._pools.get(account_id, []))
                needed = min(min_connections - existing_count, self._max_per_account - existing_count)

                # 检查全局连接数限制
                if ExchangeConnectionPool._total_connections >= self.MAX_TOTAL_CONNECTIONS:
                    logger.warning(f"全局连接数已达上限，跳过预热: {account_id}")
                    return {"success": False, "created": 0, "message": "连接池已满"}

                # 创建新连接
                for _ in range(max(0, needed)):
                    if ExchangeConnectionPool._total_connections >= self.MAX_TOTAL_CONNECTIONS:
                        break

                    try:
                        conn = await self._create_connection(db_account)
                        conn.in_use = False  # 预热连接标记为未使用

                        if account_id not in self._pools:
                            self._pools[account_id] = []
                        self._pools[account_id].append(conn)
                        ExchangeConnectionPool._total_connections += 1
                        created += 1
                    except Exception as e:
                        logger.error(f"预热连接创建失败: {e}")
                        break

            self._warmup_status[account_id] = True
            logger.info(f"连接预热完成: account={account_id}, created={created}")
            return {"success": True, "created": created, "message": f"成功创建 {created} 个预热连接"}

        except Exception as e:
            logger.error(f"连接预热失败: {account_id}, 错误: {e}")
            return {"success": False, "created": 0, "message": str(e)}

    async def warmup_all_accounts(self, min_connections: int = 2):
        """
        预热所有活跃账户的连接池

        Args:
            min_connections: 每个账户的最小连接数

        Returns:
            dict: 预热统计
        """
        accounts = await ExchangeAccount.filter(is_active=True).all()
        results = {"total": len(accounts), "success": 0, "failed": 0, "total_created": 0, "details": []}

        # 使用 gather 并发预热所有账户
        tasks = [self.warmup_connections(acc.id, min_connections) for acc in accounts]

        warmup_results = await asyncio.gather(*tasks, return_exceptions=True)

        for account, result in zip(accounts, warmup_results):
            if isinstance(result, Exception):
                results["failed"] += 1
                results["details"].append(
                    {"account_id": account.id, "email": account.email, "success": False, "message": str(result)}
                )
            elif isinstance(result, dict):
                if result.get("success"):
                    results["success"] += 1
                    results["total_created"] += result.get("created", 0)
                else:
                    results["failed"] += 1
                detail = {"account_id": account.id, "email": account.email}
                detail.update(result)
                results["details"].append(detail)

        logger.info(f"全局连接预热完成: {results}")
        return results

    async def start_background_warmup(self, account_id: int, min_connections: int = 2):
        """
        启动后台预热任务

        Args:
            account_id: 账户ID
            min_connections: 最小连接数
        """
        # 取消现有预热任务
        if account_id in self._warmup_tasks:
            old_task = self._warmup_tasks[account_id]
            if not old_task.done():
                old_task.cancel()
                try:
                    await old_task
                except asyncio.CancelledError:
                    pass

        # 创建新的预热任务
        async def warmup_task():
            try:
                await asyncio.sleep(1)  # 延迟1秒执行，避免启动时资源竞争
                await self.warmup_connections(account_id, min_connections)
            except asyncio.CancelledError:
                logger.debug(f"预热任务取消: {account_id}")
            except Exception as e:
                logger.error(f"后台预热任务异常: {account_id}, {e}")

        self._warmup_tasks[account_id] = asyncio.create_task(warmup_task())

    async def ping_all_accounts(self) -> dict:
        """Proactively test all active Exchange accounts. Updates circuit breaker state."""
        accounts = await ExchangeAccount.filter(is_active=True).all()
        healthy, degraded, results = 0, 0, []
        for account in accounts:
            try:
                async with get_exchange_connection(account.id) as conn:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, lambda: conn.account.inbox.total_count)
                healthy += 1
                results.append({"id": account.id, "status": "healthy"})
            except Exception as exc:
                degraded += 1
                results.append({"id": account.id, "status": "degraded", "error": str(exc)})
        return {"healthy": healthy, "degraded": degraded, "accounts": results}

    def get_stats(self) -> dict:
        """获取连接池统计信息"""
        return {
            "total_connections": ExchangeConnectionPool._total_connections,
            "max_total": self.MAX_TOTAL_CONNECTIONS,
            "accounts": {account_id: len(connections) for account_id, connections in self._pools.items()},
            "max_per_account": self._max_per_account,
            "warmup_status": self._warmup_status.copy(),
        }


# 全局连接池实例
_connection_pool: ExchangeConnectionPool | None = None


def get_connection_pool() -> ExchangeConnectionPool:
    """获取全局连接池"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ExchangeConnectionPool()
    return _connection_pool


@asynccontextmanager
async def get_exchange_connection(account_id: int):
    """
    获取 Exchange 连接的上下文管理器

    使用示例:
        async with get_exchange_connection(account_id) as conn:
            inbox = conn.account.inbox
            ...
    """
    pool = get_connection_pool()
    conn = await pool.get_connection(account_id)
    try:
        yield conn
    finally:
        await pool.release_connection(conn)
