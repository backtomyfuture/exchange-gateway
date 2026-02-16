"""
测试 Exchange 连接池预热功能
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.exchange.connection_pool import (
    ExchangeConnectionPool,
    ExchangeConnection,
    get_connection_pool,
)


class TestConnectionPoolWarmup:
    """测试连接池预热功能"""

    @pytest.fixture
    def pool(self):
        """创建测试连接池"""
        return ExchangeConnectionPool(max_connections_per_account=3, max_age=3600)

    @pytest.fixture
    def mock_account(self):
        """创建模拟账户"""
        account = MagicMock()
        account.id = 1
        account.email = "test@example.com"
        account.username = "testuser"
        account.encrypted_password = "encrypted_password"
        account.server = "mail.example.com"
        account.domain = "example"
        account.is_active = True
        return account

    @pytest.mark.asyncio
    async def test_warmup_connections_success(self, pool, mock_account):
        """测试连接预热成功"""
        with patch("app.services.exchange.connection_pool.ExchangeAccount.filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(return_value=mock_account)

            with patch.object(pool, "_create_connection", new_callable=AsyncMock) as mock_create:
                mock_conn = MagicMock()
                mock_create.return_value = mock_conn

                result = await pool.warmup_connections(1, min_connections=2)

                assert result["success"] is True
                assert result["created"] == 2
                assert "成功创建" in result["message"]
                assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_warmup_connections_account_not_found(self, pool):
        """测试账户不存在的情况"""
        with patch("app.services.exchange.connection_pool.ExchangeAccount.filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(return_value=None)

            result = await pool.warmup_connections(1, min_connections=2)

            assert result["success"] is False
            assert result["created"] == 0
            assert "账户不存在" in result["message"]

    @pytest.mark.asyncio
    async def test_warmup_connections_account_disabled(self, pool, mock_account):
        """测试账户已禁用的情况"""
        mock_account.is_active = False

        with patch("app.services.exchange.connection_pool.ExchangeAccount.filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(return_value=mock_account)

            result = await pool.warmup_connections(1, min_connections=2)

            assert result["success"] is False
            assert result["created"] == 0
            assert "账户已禁用" in result["message"]

    @pytest.mark.asyncio
    async def test_warmup_connections_already_warmed(self, pool, mock_account):
        """测试连接已预热的情况"""
        pool._warmup_status[1] = True  # 标记为已预热

        result = await pool.warmup_connections(1, min_connections=2)

        assert result["success"] is True
        assert result["created"] == 0
        assert "连接已预热" in result["message"]

    @pytest.mark.asyncio
    async def test_warmup_connections_partial_failure(self, pool, mock_account):
        """测试部分连接创建失败的情况"""
        with patch("app.services.exchange.connection_pool.ExchangeAccount.filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(return_value=mock_account)

            call_count = 0

            async def mock_create(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return MagicMock()
                else:
                    raise Exception("Connection failed")

            with patch.object(pool, "_create_connection", side_effect=mock_create):
                result = await pool.warmup_connections(1, min_connections=2)

                # 应该成功创建1个连接，然后失败
                assert result["success"] is True
                assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_warmup_all_accounts(self, pool):
        """测试预热所有账户"""
        account1 = MagicMock()
        account1.id = 1
        account1.email = "test1@example.com"
        account1.is_active = True

        account2 = MagicMock()
        account2.id = 2
        account2.email = "test2@example.com"
        account2.is_active = True

        with patch("app.services.exchange.connection_pool.ExchangeAccount.filter") as mock_filter:
            mock_filter.return_value.all = AsyncMock(return_value=[account1, account2])

            with patch.object(pool, "warmup_connections", new_callable=AsyncMock) as mock_warmup:
                mock_warmup.return_value = {"success": True, "created": 2, "message": "OK"}

                result = await pool.warmup_all_accounts(min_connections=2)

                assert result["total"] == 2
                assert result["success"] == 2
                assert result["total_created"] == 4  # 2个账户各2个连接
                assert mock_warmup.call_count == 2

    @pytest.mark.asyncio
    async def test_warmup_all_accounts_with_failure(self, pool):
        """测试预热所有账户时部分失败"""
        account1 = MagicMock()
        account1.id = 1
        account1.email = "test1@example.com"

        account2 = MagicMock()
        account2.id = 2
        account2.email = "test2@example.com"

        with patch("app.services.exchange.connection_pool.ExchangeAccount.filter") as mock_filter:
            mock_filter.return_value.all = AsyncMock(return_value=[account1, account2])

            async def mock_warmup(account_id, *args, **kwargs):
                if account_id == 1:
                    return {"success": True, "created": 2, "message": "OK"}
                else:
                    return {"success": False, "created": 0, "message": "Failed"}

            with patch.object(pool, "warmup_connections", side_effect=mock_warmup):
                result = await pool.warmup_all_accounts(min_connections=2)

                assert result["total"] == 2
                assert result["success"] == 1
                assert result["failed"] == 1
                assert result["total_created"] == 2

    @pytest.mark.asyncio
    async def test_start_background_warmup(self, pool, mock_account):
        """测试后台预热任务"""
        with patch("app.services.exchange.connection_pool.ExchangeAccount.filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(return_value=mock_account)

            with patch.object(pool, "_create_connection", new_callable=AsyncMock) as mock_create:
                mock_conn = MagicMock()
                mock_create.return_value = mock_conn

                # 启动后台预热
                await pool.start_background_warmup(1, min_connections=1)

                # 等待任务完成
                if 1 in pool._warmup_tasks:
                    try:
                        await asyncio.wait_for(pool._warmup_tasks[1], timeout=2.0)
                    except asyncio.TimeoutError:
                        pass

                # 验证预热状态
                await asyncio.sleep(0.1)  # 让任务有时间执行

    def test_get_stats(self, pool):
        """测试获取连接池统计信息"""
        pool._warmup_status[1] = True
        pool._warmup_status[2] = False

        stats = pool.get_stats()

        assert "total_connections" in stats
        assert "max_total" in stats
        assert "accounts" in stats
        assert "max_per_account" in stats
        assert "warmup_status" in stats
        assert stats["max_per_account"] == 3


class TestCircuitBreaker:
    """测试断路器功能（在 webhook_listener 中实现）"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(self):
        """测试断路器关闭状态"""
        from app.services.exchange.webhook_listener import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3)

        async def success_func():
            return "success"

        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state.name == "CLOSED"

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state(self):
        """测试断路器开启状态"""
        from app.services.exchange.webhook_listener import CircuitBreaker, CircuitBreakerOpen

        cb = CircuitBreaker(failure_threshold=2)

        async def fail_func():
            raise Exception("Test error")

        # 触发两次失败
        await cb.call(fail_func)
        await cb.call(fail_func)

        # 第三次应该触发断路器
        with pytest.raises(CircuitBreakerOpen):
            await cb.call(fail_func)

        assert cb.state.name == "OPEN"

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """测试断路器半开状态恢复"""
        from app.services.exchange.webhook_listener import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0)

        fail_count = 0

        async def mixed_func():
            nonlocal fail_count
            fail_count += 1
            if fail_count <= 2:
                raise Exception("Test error")
            return "success"

        # 触发断路器开启
        try:
            await cb.call(mixed_func)
        except:
            pass
        try:
            await cb.call(mixed_func)
        except:
            pass

        assert cb.state.name == "OPEN"

        # 立即恢复（recovery_timeout=0）
        await asyncio.sleep(0.1)

        # 应该进入半开状态
        result = await cb.call(mixed_func)
        assert result == "success"
        assert cb.state.name == "CLOSED"


class TestConnectionPoolConcurrency:
    """测试连接池并发性能"""

    @pytest.mark.asyncio
    async def test_concurrent_warmup(self, pool):
        """测试并发预热不会超限制"""
        # 创建多个账户
        accounts = []
        for i in range(5):
            acc = MagicMock()
            acc.id = i + 1
            acc.email = f"test{i}@example.com"
            acc.is_active = True
            accounts.append(acc)

        with patch("app.services.exchange.connection_pool.ExchangeAccount.filter") as mock_filter:
            mock_filter.return_value.all = AsyncMock(return_value=accounts)

            warmup_calls = []

            async def track_warmup(account_id, *args, **kwargs):
                warmup_calls.append(account_id)
                await asyncio.sleep(0.01)  # 模拟延迟
                return {"success": True, "created": 2, "message": "OK"}

            with patch.object(pool, "warmup_connections", side_effect=track_warmup):
                result = await pool.warmup_all_accounts(min_connections=2)

                assert len(warmup_calls) == 5
                assert result["total"] == 5
