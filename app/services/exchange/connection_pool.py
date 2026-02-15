"""
Exchange 连接池管理
复用连接以提高性能，支持自动重连和健康检查
"""
import asyncio
import time
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Optional

import urllib3
from exchangelib import (
    DELEGATE,
    NTLM,
    Account,
    Configuration,
    Credentials,
)
from exchangelib.protocol import BaseProtocol, FaultTolerance
from app.utils.exchange_adapter import LegacySSLAdapter

from app.log import logger
from app.models.exchange import ExchangeAccount
from app.settings import settings
from app.utils.crypto import get_crypto


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
            await loop.run_in_executor(
                None, 
                lambda: self.account.inbox.total_count
            )
            return True
        except Exception as e:
            logger.warning(f"连接健康检查失败: {e}")
            return False


class ExchangeConnectionPool:
    """
    Exchange 连接池
    管理多个账户的连接，支持连接复用和自动清理
    """
    
    def __init__(self, max_connections_per_account: int = 5, max_age: int = 3600):
        self._pools: dict[int, list[ExchangeConnection]] = {}
        self._max_per_account = max_connections_per_account
        self._max_age = max_age
        self._lock = asyncio.Lock()
        self._crypto = None
    
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
                    primary_smtp_address=db_account.email,
                    config=config,
                    autodiscover=False,
                    access_type=DELEGATE
                )
            
            account = await loop.run_in_executor(None, create_account_ops)
            
            logger.info(f"Exchange 连接创建成功: {db_account.email}")
            return ExchangeConnection(account, db_account.id)
            
        except Exception as e:
            logger.error(f"创建 Exchange 连接失败: {db_account.email}, 错误: {e}")
            raise
    
    async def get_connection(self, account_id: int) -> ExchangeConnection:
        """
        获取连接（优先复用现有连接）
        """
        async with self._lock:
            # 检查是否有可用连接
            if account_id in self._pools:
                pool = self._pools[account_id]
                for conn in pool:
                    # check if connection is in use
                    if conn.in_use:
                        continue
                        
                    # is_healthy 现在是异步的
                    if not conn.is_expired(self._max_age) and await conn.is_healthy():
                        conn.touch()
                        conn.in_use = True
                        return conn
                # 清理过期连接
                self._pools[account_id] = [
                    c for c in pool 
                    if not c.is_expired(self._max_age)
                ]
            
            # 创建新连接
            db_account = await ExchangeAccount.filter(id=account_id).first()
            if not db_account:
                raise ValueError(f"账户不存在: {account_id}")
            if not db_account.is_active:
                raise ValueError(f"账户已禁用: {db_account.email}")
            
            conn = await self._create_connection(db_account)
            
            conn.in_use = True
            
            # 添加到连接池
            if account_id not in self._pools:
                self._pools[account_id] = []
            if len(self._pools[account_id]) < self._max_per_account:
                self._pools[account_id].append(conn)
            
            return conn
    
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
        """
        清理所有过期连接
        """
        async with self._lock:
            for account_id in list(self._pools.keys()):
                self._pools[account_id] = [
                    c for c in self._pools[account_id]
                    if not c.is_expired(self._max_age)
                ]
                if not self._pools[account_id]:
                    del self._pools[account_id]


# 全局连接池实例
_connection_pool: Optional[ExchangeConnectionPool] = None


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
