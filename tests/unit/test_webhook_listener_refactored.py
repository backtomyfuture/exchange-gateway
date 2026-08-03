"""
测试重构后的 Webhook 监听器
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.exchange.webhook_listener import (
    AsyncAccountListener,
    CircuitBreaker,
    WebhookDispatcher,
    WebhookManager,
)


class TestAsyncAccountListener:
    """测试异步账户监听器"""

    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return {
            "email": "test@example.com",
            "password": "password123",
            "server": "mail.example.com",
            "username": "testuser",
            "domain": "example",
            "event_types": ["NewMailEvent"],
        }

    @pytest.fixture
    def listener(self, config):
        """创建测试监听器"""
        queue = asyncio.Queue()
        return AsyncAccountListener(1, queue, config)

    @pytest.mark.asyncio
    async def test_listener_start_stop(self, listener):
        """测试监听器启动和停止"""

        async def _fake_listen():
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                return

        with patch.object(listener, "_connect_and_listen", side_effect=_fake_listen):
            await listener.start()
            assert listener._task is not None
            assert not listener._task.done()

            await asyncio.sleep(0.1)

            await listener.stop()
            # Give cancelled task time to finish
            await asyncio.sleep(0.1)
            assert listener._task is None or listener._task.done()

    @pytest.mark.asyncio
    async def test_process_event_valid(self, listener):
        """测试处理有效事件"""
        # 创建模拟事件
        mock_event = MagicMock()
        mock_event.__class__.__name__ = "NewMailEvent"
        mock_event.item_id.id = "item123"
        mock_event.folder_id = None
        mock_event.subject = "Test Subject"

        result = listener._process_event(mock_event)

        assert result is not None
        assert result["account_id"] == 1
        assert result["event"] == "NewMailEvent"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_process_event_no_item_id(self, listener):
        """测试处理无 item_id 的事件"""
        mock_event = MagicMock()
        mock_event.__class__.__name__ = "StatusEvent"
        mock_event.item_id = None
        mock_event.folder_id = None

        result = listener._process_event(mock_event)

        assert result is None  # 应该被跳过

    def test_serialize_exchange_event(self, listener):
        """测试事件序列化"""
        mock_event = MagicMock()
        mock_event.id = "test-id"
        mock_event.changekey = "test-changekey"

        result = listener._serialize_exchange_event(mock_event)

        assert result["id"] == "test-id"
        assert result["changekey"] == "test-changekey"

    def test_serialize_value(self, listener):
        """测试值序列化"""
        # 测试字符串
        assert listener._serialize_value("test") == "test"
        # 测试整数
        assert listener._serialize_value(42) == 42
        # 测试 None
        assert listener._serialize_value(None) is None

    def test_serialize_exchange_event_uses_allowlist(self, listener):
        class ItemId:
            id = "item-123"
            changekey = "change-key"

        class Event:
            item_id = ItemId()
            timestamp = "2026-08-03T00:00:00Z"
            subject = "不应投递的邮件主题"
            secret = "不应投递的密钥"

        result = listener._serialize_exchange_event(Event())

        assert result == {
            "item_id": {"id": "item-123", "changekey": "change-key"},
            "timestamp": "2026-08-03T00:00:00Z",
        }


class TestWebhookDispatcher:
    """测试 Webhook 分发器"""

    @pytest.fixture
    def dispatcher(self):
        """创建测试分发器"""
        return WebhookDispatcher()

    @pytest.fixture
    def mock_webhook(self):
        """创建模拟 webhook"""
        webhook = MagicMock()
        webhook.id = 1
        webhook.url = "https://example.com/webhook"
        webhook.secret = "encrypted_secret"
        webhook.failure_count = 0
        return webhook

    @pytest.mark.asyncio
    async def test_dispatch_enqueues_arq_job(self, dispatcher, mock_webhook):
        """dispatch() persists a WebhookDelivery and enqueues an ARQ job."""
        event_data = {"event_type": "NewMailEvent", "account_id": 1}

        mock_delivery = MagicMock()
        mock_delivery.id = 42
        mock_pool = MagicMock()
        mock_pool.enqueue_job = AsyncMock()

        with (
            patch("app.services.exchange.webhook_listener.WebhookDelivery") as mock_delivery_cls,
            patch("app.services.exchange.webhook_listener.get_arq_pool", return_value=mock_pool),
        ):
            mock_delivery_cls.create = AsyncMock(return_value=mock_delivery)
            await dispatcher.dispatch(mock_webhook, event_data)

        mock_delivery_cls.create.assert_called_once()
        mock_pool.enqueue_job.assert_called_once_with("deliver_webhook_task", 42)

    @pytest.mark.asyncio
    async def test_dispatch_handles_error_gracefully(self, dispatcher, mock_webhook):
        """dispatch() logs errors without raising."""
        event_data = {"event_type": "NewMailEvent"}

        with patch("app.services.exchange.webhook_listener.WebhookDelivery") as mock_delivery_cls:
            mock_delivery_cls.create.side_effect = Exception("DB error")
            # Should not raise
            await dispatcher.dispatch(mock_webhook, event_data)

    def test_get_circuit_breaker(self, dispatcher):
        """测试获取断路器"""
        cb1 = dispatcher._get_circuit_breaker("https://example.com/1")
        cb2 = dispatcher._get_circuit_breaker("https://example.com/1")
        cb3 = dispatcher._get_circuit_breaker("https://example.com/2")

        assert cb1 is cb2  # 相同 URL 返回相同断路器
        assert cb1 is not cb3  # 不同 URL 返回不同断路器


class TestWebhookManager:
    """测试 Webhook 管理器"""

    @pytest.fixture
    def manager(self):
        """创建测试管理器"""
        return WebhookManager()

    @pytest.fixture
    def mock_subscription(self):
        """创建模拟订阅"""
        sub = MagicMock()
        sub.account_id = 1
        sub.events = ["NewMailEvent"]
        sub.is_active = True
        return sub

    def test_normalize_event_name(self, manager):
        """测试事件名称规范化"""
        assert manager._normalize_event_name("NewMail") == "NewMailEvent"
        assert manager._normalize_event_name("newmail") == "NewMailEvent"
        assert manager._normalize_event_name("NewMailEvent") == "NewMailEvent"
        assert manager._normalize_event_name("Unknown") is None

    def test_should_dispatch_event(self, manager, mock_subscription):
        """测试是否应该分发事件"""
        # 订阅 NewMailEvent，接收 NewMailEvent
        assert manager._should_dispatch_event(mock_subscription, "NewMailEvent") is True
        # 订阅 NewMailEvent，接收 CreatedEvent
        assert manager._should_dispatch_event(mock_subscription, "CreatedEvent") is False

        # 测试通配符
        mock_subscription.events = ["*"]
        assert manager._should_dispatch_event(mock_subscription, "AnyEvent") is True

    @pytest.mark.asyncio
    async def test_resolve_exchange_event_types(self, manager, mock_subscription):
        """测试解析 Exchange 事件类型"""
        with patch("exchangelib.services.SubscribeToStreaming") as mock_service:
            mock_service.EVENT_TYPES = ["NewMailEvent", "CreatedEvent", "DeletedEvent"]

            result = manager._resolve_exchange_event_types([mock_subscription])
            assert "NewMailEvent" in result


class TestCircuitBreaker:
    """测试断路器模式"""

    @pytest.mark.asyncio
    async def test_initial_state(self):
        """测试初始状态"""
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state.name == "CLOSED"
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """测试成功重置失败计数"""
        cb = CircuitBreaker(failure_threshold=3)

        # 模拟一些失败
        cb.failure_count = 2

        async def success_func():
            return "ok"

        await cb.call(success_func)
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_concurrent_calls(self):
        """测试并发调用断路器"""
        cb = CircuitBreaker(failure_threshold=10)

        async def success_func():
            await asyncio.sleep(0.01)
            return "ok"

        # 并发调用
        tasks = [cb.call(success_func) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 所有调用都应该成功
        assert all(r == "ok" for r in results)


class TestEventQueue:
    """测试事件队列"""

    @pytest.mark.asyncio
    async def test_queue_operations(self):
        """测试队列基本操作"""
        queue = asyncio.Queue()

        # 放入事件
        await queue.put({"account_id": 1, "event": "TestEvent"})

        # 取出事件
        event = await queue.get()
        assert event["account_id"] == 1
        assert event["event"] == "TestEvent"

        queue.task_done()

    @pytest.mark.asyncio
    async def test_queue_multiple_events(self):
        """测试多个事件"""
        queue = asyncio.Queue()

        # 放入多个事件
        for i in range(5):
            await queue.put({"account_id": i, "event": f"Event{i}"})

        assert queue.qsize() == 5

        # 取出所有事件
        events = []
        for _ in range(5):
            event = await queue.get()
            events.append(event)
            queue.task_done()

        assert len(events) == 5
