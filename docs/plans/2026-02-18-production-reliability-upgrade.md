# Production Reliability Upgrade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace in-memory BackgroundTasks with ARQ persistent task queue, add webhook delivery guarantees with DB persistence, integrate per-account circuit breakers, and add structured logging + Prometheus metrics.

**Architecture:** ARQ (async Redis Queue) replaces Starlette BackgroundTasks for email sending and webhook delivery. A new `WebhookDelivery` DB model tracks every delivery attempt. `CircuitBreaker` is extracted from `webhook_listener.py` to a shared module and integrated into the connection pool. `structlog` replaces standard `logging` for structured JSON output. Prometheus metrics expose Exchange-specific telemetry.

**Tech Stack:** arq ^0.26, structlog ^24.4, prometheus-fastapi-instrumentator ^7.0, fakeredis (tests), Tortoise ORM (existing), Redis (existing but commented out in docker-compose), exchangelib (existing)

---

## Phase 1: Core Reliability (P0)

### Task 1: Add Dependencies and Activate Redis

**Files:**
- Modify: `pyproject.toml`
- Modify: `docker-compose.yml`

**Step 1: Add to pyproject.toml `[project] dependencies`**

Add these four lines inside the `dependencies = [...]` list:
```
"arq>=0.26",
"structlog>=24.4",
"prometheus-fastapi-instrumentator>=7.0",
"httpx>=0.28",
```

Add to `[dependency-groups] dev` (or wherever pytest lives):
```
"fakeredis>=2.26",
```

**Step 2: Install**
```bash
pip install arq structlog "prometheus-fastapi-instrumentator>=7.0" fakeredis
```
Expected: No dependency conflicts.

**Step 3: Uncomment/add Redis in docker-compose.yml**

The redis service is commented out. Enable it and add a healthcheck:
```yaml
redis:
  image: redis:7-alpine
  restart: unless-stopped
  networks:
    - backend
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

Also add `redis` to `depends_on` of the `app` service.

**Step 4: Verify REDIS_URL in `app/settings/config.py`**

Confirm `REDIS_URL` has a dev default. If missing, add:
```python
REDIS_URL: str = "redis://localhost:6379"
```

**Step 5: Verify imports work**
```bash
python -c "import arq; import structlog; import prometheus_fastapi_instrumentator; print('OK')"
```
Expected: `OK`

**Step 6: Commit**
```bash
git add pyproject.toml docker-compose.yml app/settings/config.py
git commit -m "chore: add arq/structlog/prometheus deps, activate redis in docker-compose"
```

---

### Task 2: Add `request_body` Field to ExchangeMailLog

**Context:** `ExchangeMailLog` (`app/models/exchange.py`) stores email metadata but NOT the request body. The ARQ task needs the full `EmailSendRequest` to retry a send after a restart. We add `request_body: JSONField(null=True)`.

**Files:**
- Modify: `app/models/exchange.py`
- Run: aerich migration

**Step 1: Add field to ExchangeMailLog**

In `app/models/exchange.py`, inside `class ExchangeMailLog(BaseModel, TimestampMixin):`, add after the `request_id` field:
```python
request_body: fields.JSONField(null=True, default=None)  # Serialized EmailSendRequest for ARQ retry
```

**Step 2: Create migration**
```bash
aerich migrate --name add_mail_log_request_body
```
Expected: Creates a file in `migrations/models/` like `N_20260218_add_mail_log_request_body.py`.

Open the migration file and verify it adds a `request_body JSON NULL` column to `exchange_mail_log`.

**Step 3: Apply migration**
```bash
aerich upgrade
```
Expected: `Success N_20260218...`

**Step 4: Commit**
```bash
git add app/models/exchange.py migrations/
git commit -m "feat: add request_body field to ExchangeMailLog for ARQ retry"
```

---

### Task 3: Create Async Retry Decorator

**Files:**
- Create: `app/utils/retry.py`
- Create: `tests/unit/test_retry.py`

**Step 1: Write the failing test**

Create `tests/unit/test_retry.py`:
```python
import asyncio
import pytest
from app.utils.retry import async_retry


@pytest.mark.asyncio
async def test_succeeds_on_first_try():
    call_count = 0

    @async_retry(max_attempts=3, exceptions=(ValueError,), base_delay=0.01)
    async def func():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await func()
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retries_on_matching_exception():
    call_count = 0

    @async_retry(max_attempts=3, exceptions=(ValueError,), base_delay=0.01)
    async def func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("transient")
        return "ok"

    result = await func()
    assert result == "ok"
    assert call_count == 3


@pytest.mark.asyncio
async def test_raises_after_max_attempts():
    @async_retry(max_attempts=3, exceptions=(ValueError,), base_delay=0.01)
    async def func():
        raise ValueError("always fails")

    with pytest.raises(ValueError):
        await func()


@pytest.mark.asyncio
async def test_does_not_catch_non_matching_exception():
    @async_retry(max_attempts=3, exceptions=(ValueError,), base_delay=0.01)
    async def func():
        raise TypeError("wrong type")

    with pytest.raises(TypeError):
        await func()
```

**Step 2: Run to verify it fails**
```bash
pytest tests/unit/test_retry.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.utils.retry'`

**Step 3: Implement `app/utils/retry.py`**
```python
"""Async retry decorator with exponential backoff."""
import asyncio
import functools
import logging
from typing import Type

logger = logging.getLogger(__name__)


def async_retry(
    max_attempts: int = 3,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
):
    """Retry an async function on specified exceptions with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = base_delay
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    logger.warning(
                        "Retry %d/%d for %s after %s: %s",
                        attempt, max_attempts, func.__name__, type(exc).__name__, exc,
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            raise last_exc
        return wrapper
    return decorator
```

**Step 4: Run tests**
```bash
pytest tests/unit/test_retry.py -v
```
Expected: 4 tests PASS.

**Step 5: Commit**
```bash
git add app/utils/retry.py tests/unit/test_retry.py
git commit -m "feat: add async_retry decorator with exponential backoff"
```

---

### Task 4: Create ARQ Pool Singleton

**Context:** The FastAPI process needs a persistent ARQ Redis connection to enqueue jobs. This module manages that singleton, initialized at app startup.

**Files:**
- Create: `app/core/arq_pool.py`

**Step 1: Create `app/core/arq_pool.py`**
```python
"""
ARQ Redis connection pool — app-level singleton for job enqueueing.
Initialize via init_arq_pool() in app lifespan startup.
"""
from arq.connections import ArqRedis, RedisSettings, create_pool
from app.settings import settings

_arq_pool: ArqRedis | None = None


async def init_arq_pool() -> ArqRedis:
    """Create and store the ARQ pool. Call once on app startup."""
    global _arq_pool
    _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _arq_pool


async def close_arq_pool() -> None:
    """Close the ARQ pool. Call once on app shutdown."""
    global _arq_pool
    if _arq_pool:
        await _arq_pool.close()
        _arq_pool = None


def get_arq_pool() -> ArqRedis:
    """Get the ARQ pool. Raises RuntimeError if not initialized."""
    if _arq_pool is None:
        raise RuntimeError("ARQ pool not initialized. Call init_arq_pool() first.")
    return _arq_pool
```

**Step 2: Register in app lifespan**

In `app/core/init_app.py`, find where the app's lifespan or startup event is configured. Add:
```python
from app.core.arq_pool import init_arq_pool, close_arq_pool
```

In the startup block, add:
```python
await init_arq_pool()
```

In the shutdown block, add:
```python
await close_arq_pool()
```

If using `@asynccontextmanager` lifespan pattern:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_arq_pool()
    # ... existing startup code ...
    yield
    # ... existing shutdown code ...
    await close_arq_pool()
```

**Step 3: Verify**
```bash
python -c "from app.core.arq_pool import init_arq_pool, get_arq_pool, close_arq_pool; print('OK')"
```
Expected: `OK`

**Step 4: Commit**
```bash
git add app/core/arq_pool.py app/core/init_app.py
git commit -m "feat: add ARQ Redis pool singleton with lifespan init/close"
```

---

### Task 5: Extract `_execute_send` and Create ARQ Email Task

**Context:** `EmailService._send_email_bg_task()` mixes retry loop and EWS logic. Extract the single-attempt EWS send into `_execute_send()`, then create the ARQ task that uses it.

**Files:**
- Modify: `app/services/exchange/email_service.py`
- Create: `app/tasks/__init__.py`
- Create: `app/tasks/email_tasks.py`
- Create: `tests/unit/test_email_tasks.py`

**Step 1: Write failing tests**

Create `tests/unit/test_email_tasks.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_send_email_task_skips_non_pending(init_test_db):
    """If log status is not pending, task skips gracefully."""
    from app.tasks.email_tasks import send_email_task
    from app.models.exchange import ExchangeMailLog

    log = await ExchangeMailLog.create(
        account_id=1, action="send", status="success",
        recipients=["a@b.com"], subject="test",
        request_body={"account_id": 1, "to": ["a@b.com"],
                      "subject": "test", "body": "hi", "body_type": "text"},
    )
    result = await send_email_task({"job_try": 1}, log.id)
    assert result["skipped"] is True


@pytest.mark.asyncio
async def test_send_email_task_fails_without_request_body(init_test_db):
    """If log has no request_body, task marks it failed."""
    from app.tasks.email_tasks import send_email_task
    from app.models.exchange import ExchangeMailLog

    log = await ExchangeMailLog.create(
        account_id=1, action="send", status="pending",
        recipients=["a@b.com"], subject="test", request_body=None,
    )
    result = await send_email_task({"job_try": 1}, log.id)
    assert "error" in result
    await log.refresh_from_db()
    assert log.status == "failed"


@pytest.mark.asyncio
async def test_send_email_task_raises_retry_on_transport_error(init_test_db):
    """TransportError should raise arq.Retry."""
    from arq import Retry
    from app.tasks.email_tasks import send_email_task
    from app.models.exchange import ExchangeMailLog
    from exchangelib.errors import TransportError

    log = await ExchangeMailLog.create(
        account_id=1, action="send", status="pending",
        recipients=["a@b.com"], subject="test",
        request_body={"account_id": 1, "to": ["a@b.com"],
                      "subject": "test", "body": "body", "body_type": "text"},
    )
    with patch("app.tasks.email_tasks.get_email_service") as mock_svc:
        instance = AsyncMock()
        instance._execute_send.side_effect = TransportError("timeout")
        mock_svc.return_value = instance
        with pytest.raises(Retry):
            await send_email_task({"job_try": 1}, log.id)
```

**Step 2: Run to verify it fails**
```bash
pytest tests/unit/test_email_tasks.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.tasks'`

**Step 3: Add `_execute_send` to EmailService**

In `app/services/exchange/email_service.py`, add this method to the `EmailService` class (after `create_draft`, before `_send_email_bg_task`). It contains only the EWS logic extracted from `_send_email_bg_task` — one attempt, no retry loop:

```python
async def _execute_send(self, account_id: int, request: EmailSendRequest) -> None:
    """Execute a single EWS send attempt. Raises on any failure.
    Called by the ARQ send_email_task. No retry logic here — ARQ handles retries.
    """
    async with get_exchange_connection(account_id) as conn:
        def send_ops():
            inline_attachments = []
            if request.body_type == "html":
                from .format_utils import process_inline_images
                processed_body, inline_attachments = process_inline_images(request.body)
                body = HTMLBody(processed_body)
            else:
                body = request.body

            message = Message(
                account=conn.account,
                subject=request.subject,
                body=body,
                to_recipients=request.to or [],
                cc_recipients=request.cc or [],
                bcc_recipients=request.bcc or [],
            )
            if request.attachments:
                for att in request.attachments:
                    content = base64.b64decode(att.content)
                    message.attach(FileAttachment(
                        name=att.filename,
                        content=content,
                        content_type=att.content_type,
                    ))
            for att_data in inline_attachments:
                message.attach(FileAttachment(
                    name=att_data["filename"],
                    content=base64.b64decode(att_data["content"]),
                    content_type=att_data["content_type"],
                    content_id=att_data["content_id"],
                    is_inline=True,
                ))
            message.send(save_copy=request.save_to_sent)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, send_ops)
```

**Step 4: Create `app/tasks/__init__.py`**
```python
# ARQ persistent task queue for exchange-gateway
```

**Step 5: Create `app/tasks/email_tasks.py`**
```python
"""
ARQ email send task — persistent, retriable email sending.

Replaces the in-process BackgroundTask pattern. Idempotent: if the log
entry is not in 'pending' state, silently skips.
"""
import logging

from arq import Retry
from exchangelib.errors import TransportError, ErrorTimeoutExpired

from app.models.exchange import ExchangeMailLog
from app.schemas.exchange import EmailSendRequest
from app.services.exchange.email_service import get_email_service

logger = logging.getLogger(__name__)

# Retry delays in seconds: attempt 1→30s, 2→120s, 3→270s
_RETRY_DELAYS = [30, 120, 270]
_RETRYABLE = (TransportError, ErrorTimeoutExpired, ConnectionError, TimeoutError)


async def send_email_task(ctx: dict, mail_log_id: int) -> dict:
    """
    ARQ task: send a single email identified by ExchangeMailLog.id.

    Retry policy: up to 3 ARQ-level retries (30s / 120s / 270s backoff).
    Idempotent: skips if log status is not 'pending'.
    """
    log = await ExchangeMailLog.get_or_none(id=mail_log_id)
    if not log:
        logger.error("send_email_task: log %d not found", mail_log_id)
        return {"error": f"log {mail_log_id} not found"}

    if log.status != "pending":
        logger.info("send_email_task: log %d already %s, skipping", mail_log_id, log.status)
        return {"skipped": True, "status": log.status}

    if not log.request_body:
        logger.error("send_email_task: log %d has no request_body, marking failed", mail_log_id)
        await log.update_from_dict({"status": "failed", "error_message": "No request_body stored"})
        await log.save()
        return {"error": "no request_body"}

    request = EmailSendRequest(**log.request_body)
    service = get_email_service()

    try:
        await service._execute_send(request.account_id, request)
        await log.update_from_dict({"status": "success"})
        await log.save()
        logger.info("send_email_task: log %d sent successfully", mail_log_id)
        return {"success": True, "log_id": mail_log_id}

    except _RETRYABLE as exc:
        attempt = ctx["job_try"]
        if attempt > len(_RETRY_DELAYS):
            await log.update_from_dict({"status": "failed", "error_message": str(exc)})
            await log.save()
            raise
        delay = _RETRY_DELAYS[attempt - 1]
        logger.warning(
            "send_email_task: log %d transient error (attempt %d), retry in %ds: %s",
            mail_log_id, attempt, delay, exc,
        )
        raise Retry(defer=delay)

    except Exception as exc:
        await log.update_from_dict({"status": "failed", "error_message": str(exc)})
        await log.save()
        logger.error("send_email_task: log %d non-retryable error: %s", mail_log_id, exc)
        raise
```

**Step 6: Run tests**
```bash
pytest tests/unit/test_email_tasks.py -v
```
Expected: All 3 tests PASS.

**Step 7: Commit**
```bash
git add app/tasks/__init__.py app/tasks/email_tasks.py app/services/exchange/email_service.py tests/unit/test_email_tasks.py
git commit -m "feat: add ARQ send_email_task and extract _execute_send from email service"
```

---

### Task 6: Migrate `send_email()` to ARQ

**Context:** Replace `BgTasks.add_task(...)` in `send_email()` with ARQ enqueueing. Store `request_body` in the log. Update `recover_pending_emails()` to re-enqueue instead of marking failed.

**Files:**
- Modify: `app/services/exchange/email_service.py`

**Step 1: Update `send_email()` in EmailService**

In `app/services/exchange/email_service.py`, inside `send_email()`, replace the log creation + `BgTasks.add_task(...)` block with:

```python
# Serialize request for ARQ recovery across restarts
request_data = request.model_dump()

log_entry = await ExchangeMailLog.create(
    api_key_id=api_key_id,
    account_id=request.account_id,
    action="send",
    recipients=request.to,
    cc_recipients=request.cc,
    bcc_recipients=request.bcc,
    subject=request.subject,
    has_attachments=bool(request.attachments),
    status="pending",
    request_ip=request_ip,
    request_id=request_id,
    request_body=request_data,  # NEW
)

# Enqueue persistent ARQ job instead of BackgroundTask
from app.core.arq_pool import get_arq_pool
redis = get_arq_pool()
await redis.enqueue_job("send_email_task", log_entry.id)
```

**Step 2: Update `recover_pending_emails()`**

Replace the existing function body (currently marks pending as failed) with:

```python
async def recover_pending_emails():
    """Re-enqueue pending email logs into ARQ on startup.
    Logs without request_body (pre-ARQ entries) are marked failed.
    """
    from app.core.arq_pool import get_arq_pool
    try:
        redis = get_arq_pool()
        pending = await ExchangeMailLog.filter(action="send", status="pending").all()
        recovered, failed = 0, 0
        for log in pending:
            if log.request_body:
                await redis.enqueue_job("send_email_task", log.id)
                recovered += 1
            else:
                await log.update_from_dict({
                    "status": "failed",
                    "error_message": "No request_body; pre-ARQ entry cannot be retried",
                })
                await log.save()
                failed += 1
        logger.info("Email recovery: %d re-enqueued, %d marked failed", recovered, failed)
    except Exception as e:
        logger.error("Email recovery failed: %s", e)
```

**Step 3: Run the full test suite**
```bash
pytest tests/ --ignore=tests/manual -x -q
```
Expected: All tests pass.

**Step 4: Commit**
```bash
git add app/services/exchange/email_service.py
git commit -m "feat: migrate send_email() to ARQ, persist request_body, re-enqueue on recovery"
```

---

### Task 7: Add WebhookDelivery Model

**Files:**
- Modify: `app/models/webhook.py`
- Run: aerich migration

**Step 1: Add `WebhookDelivery` to `app/models/webhook.py`**

Add after the `WebhookSubscription` class:

```python
class WebhookDelivery(BaseModel, TimestampMixin):
    """Tracks a single webhook event delivery attempt.
    Created when an Exchange event is received; updated on delivery/failure.
    """
    subscription: fields.ForeignKeyRelation["WebhookSubscription"] = fields.ForeignKeyField(
        "models.WebhookSubscription",
        related_name="deliveries",
        on_delete=fields.CASCADE,
    )
    event_type: fields.CharField(max_length=100)
    payload: fields.JSONField()
    status: fields.CharField(max_length=20, default="pending", db_index=True)
    # pending | delivered | failed | dead
    attempt_count: fields.IntField(default=0)
    last_error: fields.TextField(null=True, default=None)
    next_retry_at: fields.DatetimeField(null=True, default=None)

    class Meta:
        table = "webhook_delivery"
```

**Step 2: Create and apply migration**
```bash
aerich migrate --name add_webhook_delivery
aerich upgrade
```
Expected: `Success ...add_webhook_delivery`

**Step 3: Commit**
```bash
git add app/models/webhook.py migrations/
git commit -m "feat: add WebhookDelivery model for at-least-once delivery tracking"
```

---

### Task 8: Create ARQ Webhook Tasks

**Files:**
- Create: `app/tasks/webhook_tasks.py`
- Create: `tests/unit/test_webhook_tasks.py`

**Step 1: Write failing tests**

Create `tests/unit/test_webhook_tasks.py`:
```python
import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_deliver_skips_already_delivered(init_test_db):
    from app.tasks.webhook_tasks import deliver_webhook_task
    from app.models.webhook import WebhookSubscription, WebhookDelivery

    sub = await WebhookSubscription.create(
        url="https://example.com/hook", secret="s", account_id=1,
        events=["NewMailEvent"], folders=[], is_active=True, created_by=1,
    )
    delivery = await WebhookDelivery.create(
        subscription_id=sub.id, event_type="NewMailEvent",
        payload={"type": "NewMailEvent"}, status="delivered",
    )
    result = await deliver_webhook_task({"job_try": 1}, delivery.id)
    assert result["skipped"] is True


@pytest.mark.asyncio
async def test_deliver_marks_delivered_on_success(init_test_db):
    from app.tasks.webhook_tasks import deliver_webhook_task
    from app.models.webhook import WebhookSubscription, WebhookDelivery

    sub = await WebhookSubscription.create(
        url="https://example.com/hook", secret="s", account_id=1,
        events=["NewMailEvent"], folders=[], is_active=True, created_by=1,
    )
    delivery = await WebhookDelivery.create(
        subscription_id=sub.id, event_type="NewMailEvent",
        payload={"type": "NewMailEvent"}, status="pending",
    )
    with patch("app.tasks.webhook_tasks._http_post_webhook") as mock_post:
        mock_post.return_value = None
        result = await deliver_webhook_task({"job_try": 1}, delivery.id)

    assert result["success"] is True
    await delivery.refresh_from_db()
    assert delivery.status == "delivered"


@pytest.mark.asyncio
async def test_deliver_marks_dead_after_max_retries(init_test_db):
    import httpx
    from app.tasks.webhook_tasks import deliver_webhook_task
    from app.models.webhook import WebhookSubscription, WebhookDelivery

    sub = await WebhookSubscription.create(
        url="https://example.com/hook", secret="s", account_id=1,
        events=["NewMailEvent"], folders=[], is_active=True, created_by=1,
    )
    delivery = await WebhookDelivery.create(
        subscription_id=sub.id, event_type="NewMailEvent",
        payload={"type": "NewMailEvent"}, status="pending",
    )
    with patch("app.tasks.webhook_tasks._http_post_webhook") as mock_post:
        mock_post.side_effect = httpx.ConnectError("refused")
        result = await deliver_webhook_task({"job_try": 5}, delivery.id)

    await delivery.refresh_from_db()
    assert delivery.status == "dead"
```

**Step 2: Run to verify it fails**
```bash
pytest tests/unit/test_webhook_tasks.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.tasks.webhook_tasks'`

**Step 3: Create `app/tasks/webhook_tasks.py`**
```python
"""ARQ webhook delivery and subscription renewal tasks."""
import hashlib
import hmac
import json
import logging
import time

import httpx
from arq import Retry

from app.models.webhook import WebhookDelivery, WebhookSubscription

logger = logging.getLogger(__name__)

MAX_DELIVERY_ATTEMPTS = 5
_RETRY_DELAYS = [120, 240, 480, 960, 1920]  # 2m, 4m, 8m, 16m, 32m


async def _http_post_webhook(url: str, payload: dict, secret: str) -> None:
    """POST webhook payload with HMAC-SHA256 signature. Raises on failure."""
    body = json.dumps(payload, ensure_ascii=False).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": f"sha256={signature}",
                "X-Webhook-Timestamp": str(int(time.time())),
            },
        )
        response.raise_for_status()


async def deliver_webhook_task(ctx: dict, delivery_id: int) -> dict:
    """ARQ task: deliver a single webhook event with HMAC signing.
    Idempotent. Retries up to MAX_DELIVERY_ATTEMPTS with exponential backoff.
    """
    delivery = await WebhookDelivery.get_or_none(
        id=delivery_id
    ).select_related("subscription")
    if not delivery:
        logger.error("deliver_webhook_task: delivery %d not found", delivery_id)
        return {"error": f"delivery {delivery_id} not found"}

    if delivery.status == "delivered":
        return {"skipped": True}

    sub = delivery.subscription
    attempt = ctx["job_try"]

    try:
        await _http_post_webhook(sub.url, delivery.payload, sub.secret)
        await delivery.update_from_dict({
            "status": "delivered",
            "attempt_count": attempt,
            "last_error": None,
        })
        await delivery.save()
        logger.info("deliver_webhook_task: delivery %d delivered (attempt %d)", delivery_id, attempt)
        return {"success": True, "delivery_id": delivery_id}

    except Exception as exc:
        await delivery.update_from_dict({"attempt_count": attempt, "last_error": str(exc)})
        await delivery.save()

        if attempt >= MAX_DELIVERY_ATTEMPTS:
            await delivery.update_from_dict({"status": "dead"})
            await delivery.save()
            logger.error(
                "deliver_webhook_task: delivery %d dead after %d attempts: %s",
                delivery_id, attempt, exc,
            )
            return {"dead": True, "delivery_id": delivery_id, "error": str(exc)}

        delay = _RETRY_DELAYS[min(attempt - 1, len(_RETRY_DELAYS) - 1)]
        logger.warning(
            "deliver_webhook_task: delivery %d failed (attempt %d), retry in %ds: %s",
            delivery_id, attempt, delay, exc,
        )
        raise Retry(defer=delay)


async def renew_subscriptions_task(ctx: dict) -> dict:
    """Cron: refresh Exchange EWS subscriptions every 30 minutes."""
    from app.services.exchange.webhook_listener import WebhookManager
    try:
        manager = WebhookManager.get_instance()
        if manager:
            await manager.refresh()
            logger.info("renew_subscriptions_task: subscriptions refreshed")
            return {"refreshed": True}
        return {"skipped": True, "reason": "no manager instance"}
    except Exception as exc:
        logger.error("renew_subscriptions_task failed: %s", exc)
        return {"error": str(exc)}


async def ping_all_accounts_task(ctx: dict) -> dict:
    """Cron: proactively check Exchange account connectivity every 5 minutes."""
    from app.services.exchange.connection_pool import get_connection_pool
    pool = get_connection_pool()
    stats = await pool.ping_all_accounts()
    logger.info("ping_all_accounts_task: %s", stats)
    return stats
```

**Step 4: Run tests**
```bash
pytest tests/unit/test_webhook_tasks.py -v
```
Expected: All 3 tests PASS.

**Step 5: Commit**
```bash
git add app/tasks/webhook_tasks.py tests/unit/test_webhook_tasks.py
git commit -m "feat: add ARQ webhook delivery and subscription renewal tasks"
```

---

### Task 9: Update WebhookDispatcher to Persist and Enqueue

**Files:**
- Modify: `app/services/exchange/webhook_listener.py`

**Step 1: Replace `dispatch()` in `WebhookDispatcher`**

Find `class WebhookDispatcher` in `app/services/exchange/webhook_listener.py`. Replace the `dispatch()` method body (keep the signature):

```python
async def dispatch(self, webhook: WebhookSubscription, event_data: dict):
    """Persist the event and enqueue an ARQ delivery job.
    No longer fires HTTP directly — the ARQ worker handles delivery.
    """
    from app.models.webhook import WebhookDelivery
    from app.core.arq_pool import get_arq_pool

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
            delivery.id, webhook.id, event_type,
        )
    except Exception as exc:
        logger.error(
            "Failed to enqueue webhook delivery for subscription %d: %s",
            webhook.id, exc,
        )
```

**Step 2: Add `get_instance()` classmethod to `WebhookManager`**

In `class WebhookManager`, add a class variable and classmethod so `renew_subscriptions_task` can reach the running instance:

```python
_instance: ClassVar[Optional["WebhookManager"]] = None

def __init__(self):
    WebhookManager._instance = self
    # ... rest of existing __init__ ...

@classmethod
def get_instance(cls) -> Optional["WebhookManager"]:
    return cls._instance
```

**Step 3: Run existing webhook tests**
```bash
pytest tests/unit/test_webhook_listener_refactored.py -v
```
Expected: All existing tests PASS.

**Step 4: Commit**
```bash
git add app/services/exchange/webhook_listener.py
git commit -m "feat: webhook dispatcher persists WebhookDelivery and enqueues ARQ job"
```

---

### Task 10: Create ARQ WorkerSettings and Update docker-compose

**Files:**
- Create: `app/tasks/worker.py`
- Modify: `docker-compose.yml`

**Step 1: Create `app/tasks/worker.py`**
```python
"""
ARQ Worker entry point for exchange-gateway.

Run with:  python -m arq app.tasks.worker.WorkerSettings
"""
from arq import cron
from arq.connections import RedisSettings
from tortoise import Tortoise

from app.settings import settings
from app.tasks.email_tasks import send_email_task
from app.tasks.webhook_tasks import (
    deliver_webhook_task,
    renew_subscriptions_task,
    ping_all_accounts_task,
)


async def startup(ctx: dict) -> None:
    """Initialize Tortoise ORM for the ARQ worker process."""
    from app.settings.config import TORTOISE_ORM
    await Tortoise.init(config=TORTOISE_ORM)
    ctx["db_initialized"] = True


async def shutdown(ctx: dict) -> None:
    """Close Tortoise ORM connections."""
    await Tortoise.close_connections()


class WorkerSettings:
    functions = [send_email_task, deliver_webhook_task]
    cron_jobs = [
        cron(renew_subscriptions_task, minute={0, 30}),            # Every 30 min
        cron(ping_all_accounts_task, minute=set(range(0, 60, 5))), # Every 5 min
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 300   # 5 minutes max per job
    keep_result = 3600  # Keep results 1 hour for debugging
    retry_jobs = True
    queue_name = "exchange-gateway"
```

**Step 2: Add `arq-worker` service to docker-compose.yml**

Add after the `webhook-worker` service:
```yaml
arq-worker:
  build: .
  command: python -m arq app.tasks.worker.WorkerSettings
  depends_on:
    mysql:
      condition: service_healthy
    redis:
      condition: service_healthy
  environment: *app-env
  volumes:
    - ./logs:/app/logs
  restart: unless-stopped
  networks:
    - backend
```

**Step 3: Verify WorkerSettings is importable**
```bash
python -c "from app.tasks.worker import WorkerSettings; print('OK')"
```
Expected: `OK`

**Step 4: Commit**
```bash
git add app/tasks/worker.py docker-compose.yml
git commit -m "feat: add ARQ WorkerSettings with cron jobs and arq-worker docker service"
```

---

### Task 11: Add Webhook Delivery Admin API

**Files:**
- Modify: `app/api/v1/exchange/webhooks.py` (find with: `grep -r "WebhookSubscription" app/api/ -l`)

**Step 1: Add two endpoints to the webhook router**

Find the webhook API router file and add:

```python
from app.models.webhook import WebhookDelivery


@router.get("/{webhook_id}/deliveries", summary="查看投递历史")
async def list_webhook_deliveries(
    webhook_id: int,
    page: int = 1,
    size: int = 20,
    _: dict = Depends(DependAuthPermission),
):
    """List all delivery attempts for a webhook subscription."""
    offset = (page - 1) * size
    total = await WebhookDelivery.filter(subscription_id=webhook_id).count()
    deliveries = await WebhookDelivery.filter(subscription_id=webhook_id) \
        .order_by("-created_at").offset(offset).limit(size) \
        .values("id", "event_type", "status", "attempt_count",
                "last_error", "next_retry_at", "created_at")
    return Success(data={"items": deliveries, "total": total, "page": page, "size": size})


@router.post("/deliveries/{delivery_id}/retry", summary="手动重投递")
async def retry_webhook_delivery(
    delivery_id: int,
    _: dict = Depends(DependAuthPermission),
):
    """Re-enqueue a dead or failed webhook delivery."""
    from app.core.arq_pool import get_arq_pool
    delivery = await WebhookDelivery.get_or_none(id=delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    if delivery.status not in ("dead", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Status is '{delivery.status}'; only dead/failed can be retried",
        )
    await delivery.update_from_dict({"status": "pending", "attempt_count": 0, "last_error": None})
    await delivery.save()
    redis = get_arq_pool()
    await redis.enqueue_job("deliver_webhook_task", delivery_id)
    return Success(data={"delivery_id": delivery_id, "status": "re-enqueued"})
```

**Step 2: Run existing webhook tests**
```bash
pytest tests/ -k "webhook" -v
```
Expected: All PASS.

**Step 3: Commit**
```bash
git add app/api/v1/exchange/webhooks.py
git commit -m "feat: add webhook delivery history and manual retry API endpoints"
```

---

## Phase 2: Resilience (P1)

### Task 12: Extract CircuitBreaker to Shared Module

**Files:**
- Create: `app/services/exchange/circuit_breaker.py`
- Modify: `app/services/exchange/webhook_listener.py`
- Create: `tests/unit/test_circuit_breaker.py`

**Step 1: Write failing tests**

Create `tests/unit/test_circuit_breaker.py`:
```python
import asyncio
import pytest
from app.services.exchange.circuit_breaker import CircuitBreaker, CircuitState, CircuitOpenError


@pytest.mark.asyncio
async def test_starts_closed():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    async def fail():
        raise ValueError("fail")

    for _ in range(3):
        with pytest.raises(ValueError):
            await cb.call(fail, retryable_exceptions=(ValueError,))

    assert cb.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_open_raises_circuit_open_error():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)

    async def fail():
        raise ValueError("fail")

    with pytest.raises(ValueError):
        await cb.call(fail, retryable_exceptions=(ValueError,))  # Opens

    with pytest.raises(CircuitOpenError):
        await cb.call(fail, retryable_exceptions=(ValueError,))  # Rejects immediately


@pytest.mark.asyncio
async def test_recovers_after_timeout():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)

    async def fail():
        raise ValueError("fail")

    with pytest.raises(ValueError):
        await cb.call(fail, retryable_exceptions=(ValueError,))  # Opens

    await asyncio.sleep(0.1)

    async def succeed():
        return "ok"

    result = await cb.call(succeed, retryable_exceptions=(ValueError,))
    assert result == "ok"
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_success_resets_failure_count():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    async def fail():
        raise ValueError("fail")

    async def succeed():
        return "ok"

    for _ in range(2):
        with pytest.raises(ValueError):
            await cb.call(fail, retryable_exceptions=(ValueError,))

    await cb.call(succeed, retryable_exceptions=(ValueError,))
    assert cb.failure_count == 0
    assert cb.state == CircuitState.CLOSED
```

**Step 2: Run to verify fails**
```bash
pytest tests/unit/test_circuit_breaker.py -v
```
Expected: `ModuleNotFoundError`

**Step 3: Create `app/services/exchange/circuit_breaker.py`**
```python
"""Generic async circuit breaker for Exchange EWS operations.

States:
  CLOSED    → calls pass through; failures increment counter
  OPEN      → calls immediately raise CircuitOpenError
  HALF_OPEN → probe call; success→CLOSED, failure→OPEN
"""
import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Tuple, Type


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is OPEN and rejects the call."""


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 1
    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    failure_count: int = field(default=0, init=False)
    last_failure_time: float = field(default=0.0, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def _should_attempt_reset(self) -> bool:
        return (time.monotonic() - self.last_failure_time) >= self.recovery_timeout

    async def _on_success(self) -> None:
        async with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED

    async def _on_failure(self) -> None:
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.monotonic()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

    async def call(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        **kwargs: Any,
    ) -> Any:
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    remaining = self.recovery_timeout - (time.monotonic() - self.last_failure_time)
                    raise CircuitOpenError(f"Circuit OPEN. Retry in {remaining:.1f}s")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except retryable_exceptions:
            await self._on_failure()
            raise
```

**Step 4: Update webhook_listener.py to import from new module**

In `app/services/exchange/webhook_listener.py`:
1. Remove the `CircuitState` enum definition
2. Remove the `CircuitBreaker` dataclass definition
3. Add at the top of the file:
```python
from app.services.exchange.circuit_breaker import CircuitBreaker, CircuitState, CircuitOpenError
```

**Step 5: Run all tests**
```bash
pytest tests/unit/test_circuit_breaker.py tests/unit/test_webhook_listener_refactored.py -v
```
Expected: All tests PASS.

**Step 6: Commit**
```bash
git add app/services/exchange/circuit_breaker.py app/services/exchange/webhook_listener.py tests/unit/test_circuit_breaker.py
git commit -m "refactor: extract CircuitBreaker to shared module"
```

---

### Task 13: Integrate CircuitBreaker into Connection Pool

**Files:**
- Modify: `app/services/exchange/connection_pool.py`

**Step 1: Add imports at top of `connection_pool.py`**
```python
from app.services.exchange.circuit_breaker import CircuitBreaker, CircuitOpenError
from exchangelib.errors import TransportError, ErrorTimeoutExpired
```

**Step 2: Add `_circuit_breakers` dict to `__init__`**

Inside `ExchangeConnectionPool.__init__`, add:
```python
self._circuit_breakers: dict[int, CircuitBreaker] = {}
```

**Step 3: Add `_get_circuit_breaker()` method**
```python
def _get_circuit_breaker(self, account_id: int) -> CircuitBreaker:
    """Get or create per-account circuit breaker."""
    if account_id not in self._circuit_breakers:
        self._circuit_breakers[account_id] = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
        )
    return self._circuit_breakers[account_id]
```

**Step 4: Wrap connection acquisition with circuit breaker**

Rename the current `get_connection()` to `_get_connection_inner()`.

Create a new `get_connection()`:
```python
async def get_connection(self, account_id: int) -> ExchangeConnection:
    """Get a connection, protected by per-account circuit breaker."""
    cb = self._get_circuit_breaker(account_id)
    return await cb.call(
        self._get_connection_inner,
        account_id,
        retryable_exceptions=(TransportError, ErrorTimeoutExpired, ConnectionError),
    )
```

**Step 5: Add `ping_all_accounts()` method**
```python
async def ping_all_accounts(self) -> dict:
    """Proactively test all active Exchange accounts. Updates circuit breaker state."""
    from app.models.exchange import ExchangeAccount
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
```

**Step 6: Run tests**
```bash
pytest tests/unit/test_connection_pool.py tests/unit/test_connection_pool_warmup.py -v
```
Expected: All PASS.

**Step 7: Commit**
```bash
git add app/services/exchange/connection_pool.py
git commit -m "feat: add per-account circuit breakers and ping_all_accounts to connection pool"
```

---

## Phase 3: Observability (P1)

### Task 14: Add structlog Structured Logging

**Files:**
- Create: `app/core/logging.py`
- Modify: `app/log.py`
- Modify: `app/core/middlewares.py`
- Modify: `app/core/init_app.py`

**Step 1: Create `app/core/logging.py`**
```python
"""Structured logging configuration using structlog.

Production (ENV=prod): JSON output for log aggregation.
Development (ENV=dev): Colored human-readable console output.
"""
import logging
import sys
import structlog
from app.settings import settings


def configure_logging() -> None:
    """Configure structlog. Call once at application startup."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,   # Injects request_id automatically
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.ENV == "prod":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)


def get_logger(name: str):
    """Get a structlog logger. Prefer this over logging.getLogger()."""
    return structlog.get_logger(name)
```

**Step 2: Update `app/log.py`**

Replace its entire content:
```python
from app.core.logging import get_logger
logger = get_logger("exchange-gateway")
```

**Step 3: Call `configure_logging()` at app startup**

In `app/core/init_app.py`, at the very beginning of the app factory function (before creating the FastAPI instance or any other initialization), add:
```python
from app.core.logging import configure_logging
configure_logging()
```

**Step 4: Bind `request_id` into structlog context**

In `app/core/middlewares.py`, find `RequestIDMiddleware.dispatch()`. After the line that sets the request ID, add:
```python
import structlog
structlog.contextvars.bind_contextvars(request_id=request_id)
```

At the end of the method (after `response = await call_next(request)`), add:
```python
structlog.contextvars.clear_contextvars()
```

**Step 5: Verify**
```bash
python -c "
from app.core.logging import configure_logging, get_logger
configure_logging()
log = get_logger('test')
log.info('structured log test', key='value', number=42)
"
```
Expected: JSON or colored output with `key`, `number`, `timestamp`, `level` fields.

**Step 6: Run full test suite**
```bash
pytest tests/ --ignore=tests/manual -x -q
```
Expected: All tests PASS (structlog is backward-compatible with standard logging calls).

**Step 7: Commit**
```bash
git add app/core/logging.py app/log.py app/core/middlewares.py app/core/init_app.py
git commit -m "feat: add structlog structured JSON logging with request_id context propagation"
```

---

### Task 15: Add Prometheus Metrics Endpoint

**Files:**
- Create: `app/core/metrics.py`
- Modify: `app/core/init_app.py`
- Modify: `app/tasks/email_tasks.py`
- Modify: `app/tasks/webhook_tasks.py`

**Step 1: Create `app/core/metrics.py`**
```python
"""Prometheus metrics for exchange-gateway.

HTTP metrics: handled automatically by prometheus_fastapi_instrumentator.
Exchange-specific metrics: defined here, incremented manually.
"""
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

email_sent_total = Counter(
    "exchange_email_sent_total",
    "Total email send outcomes",
    ["account_id", "status"],  # status: success | failed
)

email_duration_seconds = Histogram(
    "exchange_email_duration_seconds",
    "Email send round-trip duration in seconds",
    ["account_id"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

connection_pool_active = Gauge(
    "exchange_connection_pool_active",
    "Active Exchange connections per account",
    ["account_id"],
)

circuit_breaker_state = Gauge(
    "exchange_circuit_breaker_state",
    "Circuit breaker state: 0=closed, 1=open, 2=half_open",
    ["account_id"],
)

webhook_delivery_total = Counter(
    "exchange_webhook_delivery_total",
    "Total webhook delivery outcomes",
    ["status"],  # delivered | dead
)


def setup_instrumentator(app) -> None:
    """Register Prometheus instrumentation. Call once after creating the FastAPI app."""
    Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/health", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics")
```

**Step 2: Call `setup_instrumentator` in `init_app.py`**

After creating the FastAPI `app` object, add:
```python
from app.core.metrics import setup_instrumentator
setup_instrumentator(app)
```

**Step 3: Increment metrics in `email_tasks.py`**

In `send_email_task()`, wrap the send call with timing:
```python
import time
from app.core.metrics import email_sent_total, email_duration_seconds

start = time.monotonic()
await service._execute_send(request.account_id, request)
duration = time.monotonic() - start
email_duration_seconds.labels(account_id=str(request.account_id)).observe(duration)
email_sent_total.labels(account_id=str(request.account_id), status="success").inc()
```

On failure path, add:
```python
email_sent_total.labels(account_id=str(log.account_id), status="failed").inc()
```

**Step 4: Increment metrics in `webhook_tasks.py`**

In `deliver_webhook_task()` on success:
```python
from app.core.metrics import webhook_delivery_total
webhook_delivery_total.labels(status="delivered").inc()
```

On dead:
```python
webhook_delivery_total.labels(status="dead").inc()
```

**Step 5: Run full test suite**
```bash
pytest tests/ --ignore=tests/manual -x -q
```
Expected: All PASS.

**Step 6: Commit**
```bash
git add app/core/metrics.py app/core/init_app.py app/tasks/email_tasks.py app/tasks/webhook_tasks.py
git commit -m "feat: add Prometheus metrics endpoint with Exchange-specific telemetry"
```

---

### Task 16: Enhance Health Check Endpoint

**Files:**
- Modify: `app/api/v1/health/health.py`
- Create: `tests/api/test_health.py`

**Step 1: Write failing tests**

Create `tests/api/test_health.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_health_200_when_all_ok(client, init_test_db):
    with patch("app.api.v1.health.health._check_redis", new_callable=AsyncMock) as mr:
        mr.return_value = {"status": "ok", "latency_ms": 1}
        response = await client.get("/api/v1/health")
    assert response.status_code in (200, 207)
    data = response.json()["data"]
    assert "checks" in data
    assert "database" in data["checks"]


@pytest.mark.asyncio
async def test_health_503_when_db_down(client, init_test_db):
    with patch("app.api.v1.health.health._check_database", new_callable=AsyncMock) as md:
        md.return_value = {"status": "error", "error": "refused"}
        with patch("app.api.v1.health.health._check_redis", new_callable=AsyncMock) as mr:
            mr.return_value = {"status": "ok", "latency_ms": 1}
            response = await client.get("/api/v1/health")
    assert response.status_code == 503
```

**Step 2: Run to verify fails**
```bash
pytest tests/api/test_health.py -v
```
Expected: Tests fail (current endpoint returns simple dict, not multi-component format).

**Step 3: Rewrite `app/api/v1/health/health.py`**
```python
"""Enhanced health check: 200 (healthy) / 207 (degraded) / 503 (unhealthy)."""
import time
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from tortoise import Tortoise
from app.settings import settings

router = APIRouter()


async def _check_database() -> dict:
    try:
        start = time.monotonic()
        conn = Tortoise.get_connection("default")
        await conn.execute_query("SELECT 1")
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def _check_redis() -> dict:
    try:
        from app.core.arq_pool import get_arq_pool
        start = time.monotonic()
        await get_arq_pool().ping()
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def _check_exchange_accounts() -> dict:
    try:
        from app.services.exchange.connection_pool import get_connection_pool
        from app.services.exchange.circuit_breaker import CircuitState
        breakers = get_connection_pool()._circuit_breakers
        open_ids = [aid for aid, cb in breakers.items() if cb.state == CircuitState.OPEN]
        return {
            "status": "degraded" if open_ids else "ok",
            "total_monitored": len(breakers),
            "circuit_open": len(open_ids),
            "open_account_ids": open_ids,
        }
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)}


@router.get("", summary="详细健康检查")
async def health_check():
    """Returns 200 (healthy), 207 (degraded), or 503 (unhealthy)."""
    db = await _check_database()
    redis = await _check_redis()
    exchange = await _check_exchange_accounts()

    critical_ok = db["status"] == "ok" and redis["status"] == "ok"
    fully_healthy = critical_ok and exchange.get("circuit_open", 0) == 0

    if not critical_ok:
        overall, http_status = "unhealthy", 503
    elif not fully_healthy:
        overall, http_status = "degraded", 207
    else:
        overall, http_status = "healthy", 200

    return JSONResponse(
        status_code=http_status,
        content={
            "code": 200,
            "msg": "success",
            "data": {
                "status": overall,
                "version": settings.VERSION,
                "checks": {"database": db, "redis": redis, "exchange_accounts": exchange},
            },
        },
    )


@router.get("/ready", summary="就绪检查")
async def readiness_check():
    db = await _check_database()
    code = 200 if db["status"] == "ok" else 503
    return JSONResponse(
        status_code=code,
        content={"code": 200, "msg": "success", "data": {"database": db}},
    )


@router.get("/live", summary="存活检查")
async def liveness_check():
    return {"code": 200, "msg": "success", "data": {"status": "alive"}}
```

**Step 4: Run tests**
```bash
pytest tests/api/test_health.py -v
```
Expected: Both tests PASS.

**Step 5: Commit**
```bash
git add app/api/v1/health/health.py tests/api/test_health.py
git commit -m "feat: enhance health check with multi-component status and 200/207/503 codes"
```

---

## Phase 4: Code Quality (P2)

### Task 17: Add Domain Exception Hierarchy

**Files:**
- Modify: `app/core/exceptions.py`
- Modify: `app/core/init_app.py`
- Create: `tests/unit/test_exceptions.py`

**Step 1: Write failing test**

Create `tests/unit/test_exceptions.py`:
```python
from app.core.exceptions import (
    AccountNotFoundError, ExchangeConnectionError, EWSGatewayException
)


def test_account_not_found_error_code():
    exc = AccountNotFoundError("Account 42 not found")
    assert exc.error_code == "ACCOUNT_NOT_FOUND"
    assert exc.http_status == 404
    assert exc.message == "Account 42 not found"


def test_exchange_connection_error():
    exc = ExchangeConnectionError("timeout")
    assert exc.error_code == "EXCHANGE_CONNECTION_ERROR"
    assert exc.http_status == 503


def test_ews_exception_handler_returns_structured_response():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.core.exceptions import ews_exception_handler

    app = FastAPI()
    app.add_exception_handler(EWSGatewayException, ews_exception_handler)

    @app.get("/test")
    async def endpoint():
        raise AccountNotFoundError("Account 99 not found")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test")
    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "ACCOUNT_NOT_FOUND"
    assert "Account 99" in body["message"]
```

**Step 2: Run to verify fails**
```bash
pytest tests/unit/test_exceptions.py -v
```
Expected: `ImportError: cannot import name 'AccountNotFoundError'`

**Step 3: Append to `app/core/exceptions.py`**

Keep all existing code intact. Append at the end:

```python
# =============================================================================
# Domain Exception Hierarchy
# =============================================================================

class EWSGatewayException(Exception):
    """Base class for all exchange-gateway domain exceptions."""
    error_code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class AccountNotFoundError(EWSGatewayException):
    error_code = "ACCOUNT_NOT_FOUND"
    http_status = 404


class AccountDisabledError(EWSGatewayException):
    error_code = "ACCOUNT_DISABLED"
    http_status = 403


class InvalidCredentialsError(EWSGatewayException):
    error_code = "INVALID_CREDENTIALS"
    http_status = 401


class ExchangeConnectionError(EWSGatewayException):
    error_code = "EXCHANGE_CONNECTION_ERROR"
    http_status = 503


class ExchangeTimeoutError(EWSGatewayException):
    error_code = "EXCHANGE_TIMEOUT"
    http_status = 504


class ExchangeAuthError(EWSGatewayException):
    error_code = "EXCHANGE_AUTH_FAILED"
    http_status = 502


class TemplateRenderError(EWSGatewayException):
    error_code = "TEMPLATE_RENDER_ERROR"
    http_status = 422


class CircuitOpenError(EWSGatewayException):
    error_code = "CIRCUIT_OPEN"
    http_status = 503


async def ews_exception_handler(request, exc: EWSGatewayException):
    from fastapi.responses import JSONResponse
    request_id = request.headers.get("X-Request-ID", "")
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error_code": exc.error_code,
            "message": exc.message or str(exc),
            "request_id": request_id,
        },
    )
```

**Step 4: Register handler in `init_app.py`**

In `register_exceptions(app)`, add:
```python
from app.core.exceptions import EWSGatewayException, ews_exception_handler
app.add_exception_handler(EWSGatewayException, ews_exception_handler)
```

**Step 5: Run tests**
```bash
pytest tests/unit/test_exceptions.py -v
```
Expected: All 3 tests PASS.

**Step 6: Commit**
```bash
git add app/core/exceptions.py app/core/init_app.py tests/unit/test_exceptions.py
git commit -m "feat: add domain exception hierarchy with semantic error codes"
```

---

### Task 18: Add Standardized Pagination Schema

**Files:**
- Create: `app/schemas/common.py`
- Create: `tests/unit/test_pagination.py`

**Step 1: Write failing tests**

Create `tests/unit/test_pagination.py`:
```python
from app.schemas.common import PageParams, Page


def test_page_params_defaults():
    p = PageParams()
    assert p.page == 1
    assert p.size == 20
    assert p.offset == 0


def test_page_params_offset():
    p = PageParams(page=3, size=10)
    assert p.offset == 20


def test_page_params_clamps_size():
    p = PageParams(size=200)
    assert p.size == 100  # max is 100


def test_page_total_pages():
    page = Page[str](items=["a", "b"], total=100, page=1, size=3)
    assert page.pages == 34  # ceil(100/3)


def test_page_params_skip_limit_backward_compat():
    """Legacy skip/limit are converted to page/size."""
    p = PageParams(skip=20, limit=10)
    assert p.size == 10
    assert p.offset == 20
```

**Step 2: Run to verify fails**
```bash
pytest tests/unit/test_pagination.py -v
```
Expected: `ModuleNotFoundError`

**Step 3: Create `app/schemas/common.py`**
```python
"""Common pagination schemas for all list endpoints.

Usage:
    @router.get("/items")
    async def list_items(params: Annotated[PageParams, Depends()]):
        items = await Item.all().offset(params.offset).limit(params.size)
        total = await Item.all().count()
        return Page(items=items, total=total, page=params.page, size=params.size)
"""
import math
from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")


class PageParams(BaseModel):
    """Standardized pagination query parameters."""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    size: int = Field(20, ge=1, le=100, description="Items per page (max 100)")

    # Backward-compat aliases: accept skip/limit and convert to page/size
    skip: int | None = Field(None, exclude=True, description="Deprecated: use page")
    limit: int | None = Field(None, exclude=True, description="Deprecated: use size")

    @model_validator(mode="after")
    def apply_legacy_params(self) -> "PageParams":
        if self.limit is not None:
            self.size = min(self.limit, 100)
        if self.skip is not None and self.size > 0:
            self.page = (self.skip // self.size) + 1
        return self

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Page(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    items: List[T]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return math.ceil(self.total / self.size) if self.size > 0 else 0
```

**Step 4: Run tests**
```bash
pytest tests/unit/test_pagination.py -v
```
Expected: All 5 tests PASS.

**Step 5: Commit**
```bash
git add app/schemas/common.py tests/unit/test_pagination.py
git commit -m "feat: add Page/PageParams pagination schemas with skip/limit backward compat"
```

---

## Final Verification

Run the complete test suite:
```bash
pytest tests/ --ignore=tests/manual -v --tb=short
```
Expected: All tests PASS.

Check coverage:
```bash
pytest tests/ --ignore=tests/manual --cov=app --cov-report=term-missing -q
```

Smoke-test the full stack:
```bash
docker compose up -d
sleep 15
curl -s http://localhost/health | python -m json.tool
curl -s http://localhost/metrics | grep "^exchange_" | head -10
```
Expected:
- Health returns `{"status": "healthy", ...}` with checks for database, redis, exchange_accounts
- Metrics returns lines like `exchange_email_sent_total`, `exchange_webhook_delivery_total`

Tag the release:
```bash
git tag v0.2.0-reliability
```
