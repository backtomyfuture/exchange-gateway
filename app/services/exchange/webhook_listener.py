"""
Exchange Webhook Listener - 重构版
使用 asyncio.to_thread 简化架构，添加断路器模式
"""

import asyncio
import hashlib
import hmac
import json
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Optional

import httpx
from exchangelib.protocol import BaseProtocol
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from tortoise import Tortoise

from app.core.arq_pool import get_arq_pool
from app.models.exchange import ExchangeAccount
from app.models.webhook import WebhookDelivery, WebhookSubscription
from app.services.exchange.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.settings import settings
from app.utils.exchange_adapter import LegacySSLAdapter

# Init logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("webhook-worker")

# 使用自定义 Adapter 解决 SSLEOFError 和主机名不匹配
BaseProtocol.HTTP_ADAPTER_CLS = LegacySSLAdapter

# Global flag for shutdown
SHUTDOWN = False

# Backward-compat alias for existing imports
CircuitBreakerOpen = CircuitOpenError


class WebhookDispatcher:
    """
    负责将事件分发给 Webhook
    带有断路器保护的重试机制
    """

    def __init__(self):
        # 每个 webhook URL 一个断路器
        self.circuit_breakers: dict[str, CircuitBreaker] = {}

    def _get_circuit_breaker(self, url: str) -> CircuitBreaker:
        """获取或创建断路器"""
        if url not in self.circuit_breakers:
            self.circuit_breakers[url] = CircuitBreaker(failure_threshold=5, recovery_timeout=60, half_open_max_calls=2)
        return self.circuit_breakers[url]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
    )
    async def _send_request(self, url: str, payload: str, signature: str, event_type: str):
        """
        发送请求 (带重试)
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Exchange-Signature": signature,
                    "X-Exchange-Event": event_type,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            return response

    async def dispatch(self, webhook: WebhookSubscription, event_data: dict):
        """Persist the event and enqueue an ARQ delivery job.
        No longer fires HTTP directly — the ARQ worker handles delivery.
        """
        event_type = event_data.get("event_type", "UnknownEvent")
        try:
            delivery = await WebhookDelivery.create(
                subscription_id=webhook.id,
                event_type=event_type,
                payload=event_data,
                status="pending",
            )
            redis = get_arq_pool()
            await redis.enqueue_job("deliver_webhook_task", delivery.id)
            logger.info(
                "Webhook dispatch: created delivery %d for subscription %d event %s",
                delivery.id,
                webhook.id,
                event_type,
            )
        except Exception as exc:
            logger.error(
                "Failed to enqueue webhook delivery for subscription %d: %s",
                webhook.id,
                exc,
            )

    async def _do_dispatch(self, webhook: WebhookSubscription, event_data: dict):
        """实际执行分发"""
        try:
            # 1. 解密密钥
            from app.utils.crypto import get_crypto

            crypto = get_crypto()
            try:
                secret = crypto.decrypt(webhook.secret)
            except Exception as e:
                logger.error(f"Failed to decrypt secret for webhook {webhook.id}: {e}")
                return

            # 2. 构造 Payload 和签名
            payload = json.dumps(event_data)
            signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

            # 3. 发送请求
            try:
                event_name = event_data.get("event") or event_data.get("event_type") or "Unknown"
                await self._send_request(webhook.url, payload, signature, event_name)

                logger.info(f"Webhook success: {webhook.url}")
                # Reset failure count if needed
                if webhook.failure_count > 0:
                    webhook.failure_count = 0
                    webhook.last_success_at = datetime.now()
                    await webhook.save()

            except Exception as e:
                logger.warning(f"Webhook failed after retries: {webhook.url} - {e}")
                webhook.failure_count += 1
                webhook.last_failure_at = datetime.now()
                await webhook.save()
                # 重新抛出异常，让断路器捕获
                raise

        except Exception as e:
            logger.error(f"Webhook dispatch error: {webhook.url} - {e}")
            raise


class AsyncAccountListener:
    """
    异步账户监听器
    使用 asyncio.to_thread 替代 threading
    """

    def __init__(self, account_id: int, queue: asyncio.Queue, config: dict):
        self.account_id = account_id
        self.queue = queue
        self.config = config
        self.account_email = config.get("email", "")
        self.event_types = config.get("event_types", ["NewMailEvent"])
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None

        # 断路器保护 EWS 连接
        self.connection_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=30, half_open_max_calls=1)

    async def start(self):
        """启动监听任务"""
        if self._task is not None and not self._task.done():
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(self._listen_loop())
        logger.info(f"Started listener task for account {self.account_id} ({self.account_email})")

    async def stop(self):
        """停止监听任务"""
        if self._task is None:
            return

        logger.info(f"Stopping listener for account {self.account_id}...")
        self._stop_event.set()

        # 给任务一些时间优雅退出
        try:
            await asyncio.wait_for(self._task, timeout=5.0)
        except TimeoutError:
            logger.warning(f"Listener task for account {self.account_id} did not stop gracefully, cancelling...")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._task = None
        logger.info(f"Listener for account {self.account_id} stopped")

    async def _listen_loop(self):
        """
        主监听循环
        使用 asyncio.to_thread 执行阻塞的 EWS 操作
        """
        while not self._stop_event.is_set():
            try:
                await self.connection_circuit.call(self._connect_and_listen)
            except CircuitBreakerOpen:
                logger.warning(f"Account {self.account_id} connection circuit open, waiting...")
                await asyncio.sleep(settings.EXCHANGE_STREAM_ERROR_RETRY_SECONDS)
            except Exception as e:
                logger.error(f"[{self.account_id}] Listener error: {e}")
                await asyncio.sleep(settings.EXCHANGE_STREAM_ERROR_RETRY_SECONDS)

    async def _connect_and_listen(self):
        """
        连接 EWS 并监听事件
        在后台线程执行阻塞操作
        """
        logger.info(f"[{self.account_id}] Connecting to Exchange...")

        # 在线程池中创建 EWS 连接（阻塞操作）
        account = await asyncio.to_thread(self._create_account)

        logger.info(f"[{self.account_id}] Starting streaming subscription...")

        # 使用异步生成器包装同步的流式事件
        event_generator = self._stream_events(account)

        async for event in event_generator:
            if self._stop_event.is_set():
                break

            try:
                payload = self._process_event(event)
                if payload:
                    await self.queue.put(payload)
            except Exception as e:
                logger.error(f"[{self.account_id}] Error processing event: {e}")

    def _create_account(self):
        """
        创建 EWS 账户连接（同步方法，在线程中执行）
        """
        import urllib3
        from exchangelib import DELEGATE, NTLM, Account, Configuration, Credentials
        from exchangelib.protocol import FaultTolerance

        urllib3.disable_warnings()

        server = self.config.get("server") or settings.EXCHANGE_SERVER
        domain = self.config.get("domain") or settings.EXCHANGE_DOMAIN
        username = self.config["username"]
        password = self.config["password"]
        email = self.config["email"]

        if domain:
            username = f"{domain}\\{username}"

        creds = Credentials(username, password)
        config = Configuration(
            server=server,
            credentials=creds,
            auth_type=NTLM,
            retry_policy=FaultTolerance(max_wait=60),
        )

        return Account(primary_smtp_address=email, config=config, autodiscover=False, access_type=DELEGATE)

    async def _stream_events(self, account):
        """
        Wrap the synchronous EWS streaming subscription as an async generator.

        Threading note: Python generators are NOT thread-safe.  The previous
        implementation called ``next(iterator)`` from a *new* thread on every
        iteration via ``asyncio.to_thread``, which created a data race because
        the generator's frame was being resumed from different OS threads.

        The correct pattern is to run the *entire* blocking iteration inside a
        single ``asyncio.to_thread`` call and push each event onto an
        ``asyncio.Queue`` from that one thread.  The async generator then
        drains the queue on the event-loop side.
        """
        event_buffer: asyncio.Queue = asyncio.Queue()
        _sentinel = object()

        def _run_blocking_stream():
            """Runs entirely in one thread – no cross-thread generator access."""
            loop = asyncio.get_event_loop()
            try:
                with account.streaming_subscription(event_types=self.event_types) as subscription_id:
                    for notification in account.inbox.get_streaming_events(
                        subscription_id_or_ids=subscription_id,
                        connection_timeout=settings.EXCHANGE_STREAM_CONNECTION_TIMEOUT_MINUTES,
                    ):
                        if self._stop_event.is_set():
                            break
                        for event in getattr(notification, "events", []) or []:
                            # put_nowait is safe here because Queue has no maxsize limit
                            asyncio.run_coroutine_threadsafe(event_buffer.put(event), loop).result()
            except Exception as e:
                logger.error(f"[{self.account_id}] Streaming error: {e}")
                raise
            finally:
                asyncio.run_coroutine_threadsafe(event_buffer.put(_sentinel), loop).result()

        asyncio.get_event_loop()
        stream_future = asyncio.get_event_loop().run_in_executor(None, _run_blocking_stream)

        try:
            while True:
                item = await event_buffer.get()
                if item is _sentinel:
                    break
                yield item
        finally:
            # Ensure the background thread is awaited even if the consumer exits early
            try:
                await stream_future
            except Exception:
                pass

    def _process_event(self, event) -> dict | None:
        """处理单个事件"""
        try:
            event_cls = event.__class__.__name__
            event_type = event_cls

            item_id = getattr(getattr(event, "item_id", None), "id", None)
            folder_id = getattr(getattr(event, "folder_id", None), "id", None)

            # 跳过不含目标实体的状态事件
            if not item_id and not folder_id:
                return None

            logger.info(f"[{self.account_id}] Event: {event_type}")

            # 序列化事件数据
            raw_data = self._serialize_exchange_event(event)

            payload = {
                "account_id": self.account_id,
            }
            payload.update(raw_data)

            if "event" not in payload:
                payload["event"] = event_type
            if "event_type" not in payload:
                payload["event_type"] = event_type
            if "timestamp" not in payload:
                payload["timestamp"] = time.time()

            return payload

        except Exception as e:
            logger.error(f"[{self.account_id}] Error processing notification: {e}")
            return None

    def _serialize_exchange_event(self, event) -> dict:
        """序列化 Exchange 事件对象"""
        data = {}

        # 处理 ItemId 对象
        if hasattr(event, "id") and hasattr(event, "changekey"):
            return {"id": event.id, "changekey": event.changekey}

        for key in dir(event):
            if key.startswith("_"):
                continue
            val = getattr(event, key)
            if callable(val):
                continue
            data[key] = self._serialize_value(val)

        return data

    def _serialize_value(self, val):
        """序列化值"""
        if val is None:
            return None
        if isinstance(val, str | int | float | bool):
            return val
        if hasattr(val, "isoformat"):
            return val.isoformat()
        if hasattr(val, "__dict__"):
            return self._serialize_exchange_event(val)
        return str(val)


class WebhookManager:
    """
    Webhook 管理器（重构版）
    使用 asyncio.Task 管理监听器，替代 threading
    """

    EVENT_NAME_MAP = {
        "copied": "CopiedEvent",
        "created": "CreatedEvent",
        "deleted": "DeletedEvent",
        "modified": "ModifiedEvent",
        "moved": "MovedEvent",
        "newmail": "NewMailEvent",
        "copiedevent": "CopiedEvent",
        "createdevent": "CreatedEvent",
        "deletedevent": "DeletedEvent",
        "modifiedevent": "ModifiedEvent",
        "movedevent": "MovedEvent",
        "newmailevent": "NewMailEvent",
        "freebusychanged": "FreeBusyChangedEvent",
        "freebusychangedevent": "FreeBusyChangedEvent",
    }
    DEFAULT_EVENT_WHITELIST = ["NewMailEvent"]
    _instance: Optional["WebhookManager"] = None

    def __init__(self):
        WebhookManager._instance = self
        self.listeners: dict[int, AsyncAccountListener] = {}
        self.account_subscriptions: dict[int, list[WebhookSubscription]] = {}
        self.dispatcher = WebhookDispatcher()

    @classmethod
    def get_instance(cls) -> Optional["WebhookManager"]:
        return cls._instance

    @classmethod
    def _normalize_event_name(cls, event_name: str) -> str | None:
        value = str(event_name).strip()
        if not value:
            return None
        return cls.EVENT_NAME_MAP.get(value.lower())

    @classmethod
    def _resolve_exchange_event_types(cls, subscriptions: list[WebhookSubscription]) -> list[str]:
        """
        将 webhook 配置的事件名称映射为 exchangelib 期望的 Event 类型。
        """
        from exchangelib.services import SubscribeToStreaming

        supported = set(SubscribeToStreaming.EVENT_TYPES)
        resolved: set[str] = set()
        for sub in subscriptions:
            events = sub.events or cls.DEFAULT_EVENT_WHITELIST
            if any(str(event).strip() == "*" for event in events):
                return list(SubscribeToStreaming.EVENT_TYPES)

            for event in events:
                normalized = cls._normalize_event_name(event)
                if not normalized:
                    continue
                if normalized in supported:
                    resolved.add(normalized)
                else:
                    logger.warning(f"Unsupported webhook event '{event}' on account {sub.account_id}; ignored.")

        if not resolved:
            return cls.DEFAULT_EVENT_WHITELIST.copy()
        return list(resolved)

    @classmethod
    def _should_dispatch_event(cls, sub: WebhookSubscription, event_type: str) -> bool:
        events = sub.events or cls.DEFAULT_EVENT_WHITELIST
        if any(str(event).strip() == "*" for event in events):
            return True

        allowed: set[str] = set()
        for event in events:
            normalized = cls._normalize_event_name(event)
            if normalized:
                allowed.add(normalized)
        return event_type in allowed

    async def refresh(self):
        """
        Refresh active subscriptions from DB
        管理监听器生命周期
        """
        subs = await WebhookSubscription.filter(is_active=True).all()

        # Group by account
        new_account_map: dict[int, list[WebhookSubscription]] = {}
        for sub in subs:
            if sub.account_id not in new_account_map:
                new_account_map[sub.account_id] = []
            new_account_map[sub.account_id].append(sub)

        self.account_subscriptions = new_account_map

        # 1. 启动新的监听器
        for acc_id, subs in new_account_map.items():
            if acc_id not in self.listeners:
                await self._start_listener(acc_id, subs)

        # 2. 停止已移除的监听器
        for acc_id in list(self.listeners.keys()):
            if acc_id not in new_account_map:
                await self._stop_listener(acc_id)

    async def _start_listener(self, acc_id: int, subs: list[WebhookSubscription]):
        """启动单个监听器"""
        acc = await ExchangeAccount.get_or_none(id=acc_id)
        if not acc:
            logger.warning(f"Account {acc_id} not found, skipping listener")
            return

        # 解密密码
        from app.utils.crypto import get_crypto

        crypto = get_crypto()
        try:
            password = crypto.decrypt(acc.encrypted_password)
        except Exception as e:
            logger.error(f"Failed to decrypt password for account {acc.email}: {e}")
            return

        event_types = self._resolve_exchange_event_types(subs)

        config = {
            "email": acc.email,
            "password": password,
            "server": acc.server,
            "username": acc.username,
            "domain": acc.domain,
            "event_types": event_types,
        }

        listener = AsyncAccountListener(acc_id, event_queue, config)
        await listener.start()
        self.listeners[acc_id] = listener
        logger.info(f"Started listener for account {acc_id} ({acc.email})")

    async def _stop_listener(self, acc_id: int):
        """停止单个监听器"""
        logger.info(f"Stopping listener for account {acc_id}")
        listener = self.listeners.pop(acc_id, None)
        if listener:
            await listener.stop()

    async def process_queue(self):
        """
        Process events from queue
        使用 TaskGroup 控制并发
        """
        # 限制并发 dispatch 数量
        semaphore = asyncio.Semaphore(10)

        async def dispatch_with_limit(sub, event):
            async with semaphore:
                await self.dispatcher.dispatch(sub, event)

        while True:
            try:
                event = await event_queue.get()
                acc_id = event["account_id"]
                event_type_raw = event.get("event") or event.get("event_type")
                event_type = self._normalize_event_name(event_type_raw) if event_type_raw else None

                if not event_type:
                    event_queue.task_done()
                    continue

                event["event"] = event_type
                event["event_type"] = event_type

                # Find matching webhooks
                if acc_id in self.account_subscriptions:
                    tasks = []
                    for sub in self.account_subscriptions[acc_id]:
                        if self._should_dispatch_event(sub, event_type):
                            # 使用限制并发的 dispatch
                            task = asyncio.create_task(dispatch_with_limit(sub, event))
                            tasks.append(task)

                    if tasks:
                        # 等待所有 dispatch 完成，但不让异常影响其他任务
                        await asyncio.gather(*tasks, return_exceptions=True)

                event_queue.task_done()

            except Exception as e:
                logger.error(f"Error processing queue: {e}")
                # 确保 task_done 被调用，避免队列阻塞
                try:
                    event_queue.task_done()
                except ValueError:
                    pass


# 全局事件队列
event_queue: asyncio.Queue = asyncio.Queue()


async def main():
    """主入口"""
    await Tortoise.init(config=settings.TORTOISE_ORM)

    manager = WebhookManager()

    # Start queue processor
    queue_task = asyncio.create_task(manager.process_queue())

    logger.info("Webhook Worker Started (Refactored with asyncio)")

    # Main loop for refresh
    try:
        while not SHUTDOWN:
            try:
                await manager.refresh()
            except Exception as e:
                logger.error(f"Refresh error: {e}")

            await asyncio.sleep(60)  # Check DB every minute
    except asyncio.CancelledError:
        logger.info("Main loop cancelled")
    finally:
        # 优雅关闭
        logger.info("Shutting down...")
        queue_task.cancel()
        try:
            await queue_task
        except asyncio.CancelledError:
            pass

        # 停止所有监听器
        for acc_id in list(manager.listeners.keys()):
            await manager._stop_listener(acc_id)

        await Tortoise.close_connections()
        logger.info("Shutdown complete")


def signal_handler(sig, frame):
    """信号处理"""
    global SHUTDOWN
    logger.info(f"Received signal {sig}, shutting down...")
    SHUTDOWN = True


if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
