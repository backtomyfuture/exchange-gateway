import asyncio
import logging
import signal
import sys
import threading
import time
import json
import hmac
import hashlib
from typing import Dict, List, Optional
import httpx
from datetime import datetime
from tortoise import Tortoise

# Init logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("webhook-worker")

from app.settings import settings
from app.models.exchange import ExchangeAccount
from app.models.webhook import WebhookSubscription
from app.services.exchange.connection_pool import get_exchange_connection

from exchangelib.protocol import BaseProtocol
from app.utils.exchange_adapter import LegacySSLAdapter
# 使用自定义 Adapter 解决 SSLEOFError 和主机名不匹配
BaseProtocol.HTTP_ADAPTER_CLS = LegacySSLAdapter

# Global flag for shutdown
SHUTDOWN = False

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class WebhookDispatcher:
    """
    负责将事件分发给 Webhook
    """
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException))
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
                    "X-Exchange-Event": event_type
                },
                timeout=10.0
            )
            response.raise_for_status()
            return response

    async def dispatch(self, webhook: WebhookSubscription, event_data: dict):
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
            signature = hmac.new(
                secret.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            
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
                
        except Exception as e:
            logger.error(f"Webhook dispatch error: {webhook.url} - {e}")


class AccountListener:
    """
    监听单个 Exchange 账户
    """
    def __init__(self, account_id: int):
        self.account_id = account_id
        self.webhooks: List[WebhookSubscription] = []
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._dispatcher = WebhookDispatcher()
        self.last_sync_time = datetime.now()
    
    def update_webhooks(self, webhooks: List[WebhookSubscription]):
        """
        更新该账户需要触发的 Webhook 列表
        """
        self.webhooks = webhooks
        
    def start(self):
        if self._thread and self._thread.is_alive():
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_listen_loop, daemon=True, name=f"Listener-{self.account_id}")
        self._thread.start()
        logger.info(f"Started listener thread for account {self.account_id}")
        
    def stop(self):
        if not self._thread:
            return
            
        logger.info(f"Stopping listener for account {self.account_id}...")
        self._stop_event.set()
        # Thread might be blocked on IO, so we can't force kill it easily without closing socket
        # But we can assume connection pool or timeout handles it?
        # Exchangelib streaming is blocking.
        # We rely on thread daemon to be killed when main process exits, 
        # or we hope connection times out.
        # For clean shutdown, we might just let it run until next heartbeat?
        
    def _run_listen_loop(self):
        """
        运行在独立线程中的监听循环
        """
        # Create a new event loop for this thread if needed for async DB ops?
        # Actually dispatching needs async.
        # So we should run an async loop in this thread?
        # Or dispatch back to main thread?
        # Simpler: run asyncio.run(self._listen()) inside the thread.
        try:
            asyncio.run(self._listen())
        except Exception as e:
            logger.error(f"Thread loop crash account {self.account_id}: {e}")
            
    async def _listen(self):
        # We need Tortoise initialized in this thread? No, Tortoise is global but connections might be thread-bound?
        # Tortoise logic should be fine if we use new context or ensure connection pool is thread-safe.
        # Actually asyncmy/asyncpg are async, so they run on the loop.
        # We already have a loop for this thread.
        # Only issue is if Tortoise was initialized in main loop.
        # We should NOT use DB in this thread if possible, OR re-init Tortoise?
        # Re-init is bad.
        
        # Better approach: This thread only does blocking Exchange IO.
        # When event arrives, it puts it in a thread-safe Queue.
        # Main loop consumes Queue and does DB/HTTP ops.
        # This keeps threading model clean.
        pass

# Refactored Approach:
# Main Loop (Async):
#   - Refreshes subscriptions from DB.
#   - Manages AccountListener threads.
#   - Consumes a common `event_queue`.
#   - Dispatches webhooks.
#
# AccountListener (Thread):
#   - Connects to Exchange (Blocking).
#   - Pushes events to `event_queue`.

event_queue = asyncio.Queue()

class BlockingAccountListener:
    def __init__(self, account_id: int, queue: asyncio.Queue):
        self.account_id = account_id
        self.queue = queue
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.account_email = ""
        
    def start(self, account_email: str):
        self.account_email = account_email
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"Listener-{self.account_id}")
        self._thread.start()
        
    def stop(self):
        self._stop_event.set()

    def _serialize_id(self, obj):
        """Helper to serialize ItemId/FolderId objects"""
        if not obj:
            return None
        return {
            "id": getattr(obj, "id", None),
            "changekey": getattr(obj, "changekey", None)
        }

    def _serialize_value(self, val):
        """Helper to serialize values strictly to JSON-compatible types"""
        if val is None:
            return None
        if isinstance(val, (str, int, float, bool)):
            return val
        if hasattr(val, "isoformat"):
            return val.isoformat()
        if hasattr(val, "__dict__"):
            return self._serialize_exchange_event(val)
        # Fallback for things like enums or unknown objects
        return str(val)

    def _serialize_exchange_event(self, event):
        """
        Serialize exchangelib Event object (or any object) to a dictionary by walking its attributes.
        """
        data = {}
        # Use dir() to find all relevant attributes, public ones only
        # exchangelib objects usually hold data in __dict__ or slots, but vars() is safer if available
        # However, to be "raw", we should look for pulic attributes.
        
        # Strategy: iterate over instance __dict__ keys + class __slots__ if any?
        # Simpler: inspect public attributes that are not callables.
        
        keys = []
        if hasattr(event, "__dict__"):
            keys.extend(event.__dict__.keys())
        # Also check slots if no dict? exchangelib uses simple classes usually.
        # Let's trust standard dir() but filter heavily.
        
        # Actually, exchangelib events are simple classes. vars(event) should work for instance chars.
        # But some are properties.
        # Let's try to get all public non-callable attributes.
        
        import inspect
        
        # If it has __key__, it might be an EWS ItemId
        if hasattr(event, "id") and hasattr(event, "changekey"):
             return {
                 "id": event.id,
                 "changekey": event.changekey
             }

        for key in dir(event):
            if key.startswith("_"):
                continue
            val = getattr(event, key)
            if callable(val):
                continue
            data[key] = self._serialize_value(val)
            
        return data

    def _iter_stream_notifications(self, account, event_types: Optional[List[str]] = None):
        """
        按 exchangelib 5.x 标准流程读取全邮箱事件：
        1) subscribe_to_streaming 获取 subscription_id
        2) get_streaming_events 拉取通知并展开为事件
        """
        with account.streaming_subscription(event_types=event_types) as subscription_id:
            # exchangelib 5.6.0 on production returns the ID string directly (confirmed by source inspection)
            for notification in account.inbox.get_streaming_events(
                subscription_id_or_ids=subscription_id,
                connection_timeout=settings.EXCHANGE_STREAM_CONNECTION_TIMEOUT_MINUTES,
            ):
                for event in getattr(notification, "events", []) or []:
                    yield event
        
    def _run(self):
        logger.info(f"[{self.account_id}] Connecting to Exchange...")
        # Since we are in a thread, we can't easily use the async `get_exchange_connection` context manager
        # directly if it relies on async loop.
        # But `get_exchange_connection` uses `ExchangeConnectionPool` which returns an async context manager.
        # `conn.account` is the exchangelib Account object.
        # We need to bridge async retrieval of account credentials with blocking usage.
        
        # ACTUALLY: `get_exchange_connection` requires async loop.
        # We can't call it from a sync thread easily without `asyncio.run_coroutine_threadsafe` pointing to main loop.
        # But main loop is busy.
        
        # Alternative: Pass credentials to this thread, and let it build its own `exchangelib.Account`.
        # This is safer for isolation.
        
        from app.utils.crypto import get_crypto
        from exchangelib import Credentials, Configuration, Account, DELEGATE, NTLM
        from exchangelib.protocol import BaseProtocol, FaultTolerance
        from app.utils.exchange_adapter import LegacySSLAdapter
        import urllib3
        urllib3.disable_warnings() 
        
        # 使用自定义 Adapter 解决 SSLEOFError 和主机名不匹配
        BaseProtocol.HTTP_ADAPTER_CLS = LegacySSLAdapter 
        
        # We need to fetch credentials from DB in main loop and pass here.
        # Assume we have them in `self.credentials`.
        
        # Setup retry loop
        while not self._stop_event.is_set():
            try:
                # We need credentials provided by management layer
                if not hasattr(self, 'config'):
                    time.sleep(1)
                    continue
                    
                cfg = self.config
                
                # Use settings defaults if not provided in account config
                server = cfg.get('server') or settings.EXCHANGE_SERVER
                domain = cfg.get('domain') or settings.EXCHANGE_DOMAIN
                
                # Format username with domain
                username = cfg['username']
                if domain:
                    username = f"{domain}\\{username}"
                
                creds = Credentials(username, cfg['password'])
                
                # Manual configuration to avoid autodiscover
                config = Configuration(
                    server=server, 
                    credentials=creds,
                    auth_type=NTLM,
                    retry_policy=FaultTolerance(max_wait=60),
                )

                account = Account(
                    primary_smtp_address=cfg['email'],
                    config=config,
                    autodiscover=False,
                    access_type=DELEGATE
                )
                
                # Streaming
                logger.info(f"[{self.account_id}] Starting streaming subscription...")
                
                # folders = [account.inbox] # Default to Inbox
                # We can monitor all folders or specific.
                # For now MVP: Inbox (incoming mail)
                
                # subscription = account.inbox.streaming_subscription()
                # with subscription:
                #    for notification in subscription:
                #        ...
                
                # Using explicit context
                # streaming_subscription returns a context manager that yields a generator
                
                event_types = cfg.get("event_types")
                for event in self._iter_stream_notifications(account, event_types=event_types):
                    if self._stop_event.is_set():
                        break

                    try:
                        # Event 类型使用类名（如 NewMailEvent）
                        event_cls = event.__class__.__name__
                        event_type = event_cls

                        item_id = getattr(getattr(event, "item_id", None), "id", None)
                        folder_id = getattr(getattr(event, "folder_id", None), "id", None)

                        # 跳过不含目标实体的状态事件
                        if not item_id and not folder_id:
                            continue

                        logger.info(f"[{self.account_id}] Event: {event_type}")

                        # Serialize full event data raw
                        raw_data = self._serialize_exchange_event(event)

                        # Construct final payload
                        # Base required fields
                        payload = {
                            "account_id": self.account_id,
                            # We can override event/event_type from raw data if present, or set them if missing
                            # But webhook expects "event": "NewMailEvent"
                        }
                        
                        # Merge raw data (this puts all event fields at top level)
                        payload.update(raw_data)
                        
                        # Ensure our tracking timestamps/IDs are present if not in raw?
                        # Actually raw data *is* the payload now + account_id.
                        # But we enforce 'event' name presence.
                        if "event" not in payload:
                            payload["event"] = event_type
                        if "event_type" not in payload:
                            payload["event_type"] = event_type
                        
                        # Timestamp override to be processing time? 
                        # Or keep event time if available? 
                        # The user wants "original information", so event.timestamp is better.
                        # But we add a processing timestamp if missing?
                        if "timestamp" not in payload:
                             payload["timestamp"] = time.time()
                             
                        # Explicitly ensure account_id is there (it was added first)

                        # Send to Main Loop
                        loop = self.loop # Reference to main loop
                        asyncio.run_coroutine_threadsafe(
                            self.queue.put(payload),
                            loop
                        )
                    except Exception as e:
                        logger.error(f"[{self.account_id}] Error processing notification: {e}")
                        continue
                logger.info(f"[{self.account_id}] Streaming connection closed, reconnecting immediately...")
                
            except Exception as e:
                logger.error(f"[{self.account_id}] Listener crashed: {e}")
                time.sleep(settings.EXCHANGE_STREAM_ERROR_RETRY_SECONDS)


class WebhookManager:
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

    def __init__(self):
        self.listeners: Dict[int, BlockingAccountListener] = {}
        self.account_subscriptions: Dict[int, List[WebhookSubscription]] = {}

    @classmethod
    def _normalize_event_name(cls, event_name: str) -> Optional[str]:
        value = str(event_name).strip()
        if not value:
            return None
        return cls.EVENT_NAME_MAP.get(value.lower())

    @classmethod
    def _resolve_exchange_event_types(cls, subscriptions: List[WebhookSubscription]) -> List[str]:
        """
        将 webhook 配置的事件名称映射为 exchangelib 期望的 Event 类型。
        例如：NewMail -> NewMailEvent
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
                    logger.warning(
                        f"Unsupported webhook event '{event}' on account {sub.account_id}; ignored."
                    )

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
        """
        subs = await WebhookSubscription.filter(is_active=True).all()
        
        # Group by account
        new_account_map: Dict[int, List[WebhookSubscription]] = {}
        for sub in subs:
            if sub.account_id not in new_account_map:
                new_account_map[sub.account_id] = []
            new_account_map[sub.account_id].append(sub)
            
        self.account_subscriptions = new_account_map
        
        # Manage listeners
        # 1. Start new
        for acc_id, subs in new_account_map.items():
            if acc_id not in self.listeners:
                # Need to fetch account credentials
                acc = await ExchangeAccount.get_or_none(id=acc_id)
                if not acc:
                    continue
                    
                # Decrypt password
                from app.utils.crypto import get_crypto
                crypto = get_crypto()
                try:
                    password = crypto.decrypt(acc.encrypted_password)
                except:
                    logger.error(f"Failed to decrypt password for account {acc.email}")
                    continue
                    
                event_types = self._resolve_exchange_event_types(subs)

                listener = BlockingAccountListener(acc_id, event_queue)
                listener.loop = asyncio.get_running_loop()
                listener.config = {
                    "email": acc.email,
                    "password": password,
                    "server": acc.server,
                    "username": acc.username,
                    "domain": acc.domain,
                    "event_types": event_types,
                }
                listener.start(acc.email)
                self.listeners[acc_id] = listener
                
        # 2. Stop removed
        for acc_id in list(self.listeners.keys()):
            if acc_id not in new_account_map:
                logger.info(f"Removing listener for account {acc_id}")
                self.listeners[acc_id].stop()
                del self.listeners[acc_id]

    async def process_queue(self):
        """
        Process events from queue
        """
        while True:
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
                for sub in self.account_subscriptions[acc_id]:
                    if self._should_dispatch_event(sub, event_type):
                        dispatcher = WebhookDispatcher()
                        # We fire and forget (or await)
                        asyncio.create_task(dispatcher.dispatch(sub, event))
            
            event_queue.task_done()

async def main():
    # Load settings
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    manager = WebhookManager()
    
    # Start queue processor
    asyncio.create_task(manager.process_queue())
    
    logger.info("Webhook Worker Started")
    
    # Main loop for refresh
    while not SHUTDOWN:
        try:
            await manager.refresh()
        except Exception as e:
            logger.error(f"Refresh error: {e}")
            
        await asyncio.sleep(60) # Check DB every minute

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
