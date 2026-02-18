# Production Reliability Upgrade Design

**Date:** 2026-02-18
**Author:** Architecture Review
**Status:** Approved
**Scope:** Exchange-Gateway — 方案B：生产就绪升级

## Problem Statement

The exchange-gateway project has a solid foundation (A- overall architecture grade) but three critical reliability gaps prevent it from being safely deployed in enterprise production environments:

1. **Email loss risk**: `BackgroundTasks` (in-process, in-memory) means any email being sent when the process restarts is permanently lost. The `ExchangeMailLog` table can accumulate `pending` records with no mechanism to resume them across restarts.

2. **Webhook unreliability**: The `webhook_listener.py` fires HTTP POST to target URLs once; on failure it only logs, never retries. Exchange subscriptions also expire (~1 hour) with no automatic renewal.

3. **Exchange connection fragility**: Transient network errors cause immediate failures with no retry. There is no per-account circuit breaker at the connection pool level to prevent resource exhaustion when an account becomes unreachable.

Additionally, the system lacks observability (no metrics, no structured logs) making it difficult to diagnose production incidents.

## Goals

- Zero email loss on process restart
- At-least-once webhook delivery with auditable status tracking
- Graceful degradation when Exchange server is unavailable
- Operator-visible metrics and structured logs for production diagnosis
- No breaking changes to existing API contracts

## Non-Goals

- Distributed / multi-instance deployment coordination (single-machine scope)
- TypeScript frontend migration
- Kubernetes manifests
- Python SDK / client libraries

## Architecture Overview

### Component Changes

```
Before:
  POST /emails/send → BackgroundTask (memory) → EmailService.send()

After:
  POST /emails/send → ARQ enqueue_job() → Redis → ARQ Worker → EmailService.send()
                                                               ↓
                                                    ExchangeMailLog update
```

```
Before:
  Exchange Event → WebhookListener → HTTP POST (once)

After:
  Exchange Event → WebhookListener → WebhookDelivery(DB) → ARQ enqueue_job()
                                                          ↓
                                               ARQ Worker → HTTP POST
                                               ├─ success: mark delivered
                                               └─ failure: retry (up to 5×)
```

### New Docker Compose Service

```yaml
arq-worker:
  build: .
  command: python -m arq app.tasks.worker.WorkerSettings
  depends_on: [mysql, redis]
  environment: *app-env
  volumes:
    - logs:/app/logs
  restart: unless-stopped
```

### New Directory Structure

```
app/
├── tasks/
│   ├── __init__.py
│   ├── worker.py           # ARQ WorkerSettings (job list, Redis settings)
│   ├── email_tasks.py      # send_email_task()
│   └── webhook_tasks.py    # deliver_webhook_task(), renew_subscriptions_task()
├── utils/
│   └── retry.py            # @retry decorator with exponential backoff
└── services/exchange/
    └── circuit_breaker.py  # Extracted/generalized CircuitBreaker class
```

## Detailed Design

### 1. ARQ Persistent Task Queue

**Package:** `arq` (async Redis Queue, FastAPI-ecosystem native)

**Worker configuration** (`app/tasks/worker.py`):
```python
class WorkerSettings:
    functions = [send_email_task, deliver_webhook_task, renew_subscriptions_task]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300        # 5 minutes max per job
    keep_result = 3600       # Keep results 1 hour for debugging
    retry_jobs = True
```

**Email task** (`app/tasks/email_tasks.py`):
```python
async def send_email_task(ctx, mail_log_id: int) -> dict:
    """Idempotent: mail_log_id binds task to specific log record."""
    log = await ExchangeMailLog.get(id=mail_log_id)
    if log.status != MailStatus.pending:
        return {"skipped": True}  # Already processed

    try:
        await email_service.do_send(log)
        await log.update(status=MailStatus.success)
    except (TransportError, TimeoutError) as e:
        raise Retry(defer=ctx["job_try"] ** 2 * 30)  # 30s, 120s, 270s backoff
    except Exception as e:
        await log.update(status=MailStatus.failed, error=str(e))
        raise
```

**Startup recovery**: On `lifespan` startup, scan `ExchangeMailLog` for `pending` records and enqueue them. Idempotency ensures no double-sends.

**Retry policy**: max 3 attempts, exponential backoff (30s / 120s / 270s). After exhaustion: status → `failed`, error recorded.

---

### 2. Webhook Reliable Delivery

**New model** (`models/webhook.py` — `WebhookDelivery`):

| Field | Type | Description |
|-------|------|-------------|
| `subscription_id` | FK → WebhookSubscription | Parent subscription |
| `event_type` | VARCHAR | e.g., NewMail, Created |
| `payload` | JSON | Full event payload |
| `status` | ENUM | pending / delivered / failed / dead |
| `attempt_count` | INT | How many delivery attempts |
| `last_error` | TEXT | Last failure reason |
| `next_retry_at` | DATETIME | Scheduled retry time |

**Webhook delivery task** (`app/tasks/webhook_tasks.py`):
```python
async def deliver_webhook_task(ctx, delivery_id: int) -> dict:
    delivery = await WebhookDelivery.get(id=delivery_id)
    if delivery.status == DeliveryStatus.delivered:
        return {"skipped": True}

    try:
        await http_post_with_hmac(delivery.subscription, delivery.payload)
        await delivery.update(status=DeliveryStatus.delivered)
    except httpx.HTTPError as e:
        attempt = ctx["job_try"]
        if attempt >= 5:
            await delivery.update(status=DeliveryStatus.dead, last_error=str(e))
            raise  # No more retries
        await delivery.update(attempt_count=attempt, last_error=str(e))
        raise Retry(defer=60 * (2 ** attempt))  # 2m, 4m, 8m, 16m, 32m
```

**Subscription auto-renewal** (`renew_subscriptions_task`):
- ARQ cron job every 30 minutes
- Calls `exchangelib` subscription refresh on all active subscriptions
- On failure: logs warning, circuit breaker records failure for that account

**New admin API**:
- `GET /api/v1/webhooks/{id}/deliveries` — list delivery attempts
- `POST /api/v1/webhooks/deliveries/{id}/retry` — manually re-enqueue dead letter

---

### 3. Exchange Connection Resilience

**Extracted `CircuitBreaker`** (`app/services/exchange/circuit_breaker.py`):

The circuit breaker already exists in `webhook_listener.py`. Extract it to a standalone class reused by both the connection pool and the webhook listener.

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60): ...

    async def call(self, func, *args) -> Any:
        if self.state == State.OPEN:
            if time.time() - self.last_failure > self.recovery_timeout:
                self.state = State.HALF_OPEN
            else:
                raise CircuitOpenError(f"Circuit open, retry after {self.recovery_timeout}s")
        try:
            result = await func(*args)
            self._on_success()
            return result
        except RETRYABLE_EXCEPTIONS as e:
            self._on_failure()
            raise
```

**Per-account circuit breakers** in `ExchangeConnectionPool`:
```python
self._circuit_breakers: dict[int, CircuitBreaker] = {}  # account_id → breaker
```

**Retry decorator** (`app/utils/retry.py`):
```python
@retry(max_attempts=3, exceptions=(TransportError, TimeoutError), base_delay=1.0)
async def get_connection(account_id: int) -> Account: ...
```

Retry schedule: 1s, 2s, 4s (exponential backoff with jitter).

**Error classification**:
```python
RETRYABLE_EXCEPTIONS = (TransportError, TimeoutError, ConnectionResetError)
NON_RETRYABLE_EXCEPTIONS = (UnauthorizedError, CertificateError, AccountDisabledError)
```

Non-retryable exceptions bypass retry and circuit breaker counting.

**Proactive health check**: ARQ cron task `ping_all_accounts()` every 5 minutes performs a lightweight EWS `GetFolder` call per account. Failed pings increment circuit breaker failure count.

---

### 4. Observability

#### 4a. Structured JSON Logging (structlog)

Replace `logging.basicConfig` with `structlog` configured in `app/core/logging.py`:

```python
# Production: JSON output
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,  # Injects request_id
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

# Development: colored human-readable output
```

Every log line automatically includes `request_id` (from `RequestIDMiddleware` via `contextvars`).

#### 4b. Prometheus Metrics

New endpoint `GET /metrics` (restricted to internal network via nginx):

| Metric | Type | Labels |
|--------|------|--------|
| `exchange_email_sent_total` | Counter | `account_id`, `status` |
| `exchange_email_duration_seconds` | Histogram | `account_id` |
| `exchange_connection_pool_active` | Gauge | `account_id` |
| `exchange_circuit_breaker_state` | Gauge | `account_id`, `state` |
| `arq_queue_size` | Gauge | `queue` |
| `webhook_delivery_total` | Counter | `status` |

Implementation: `prometheus-fastapi-instrumentator` for HTTP metrics (automatic), manual metrics for Exchange-specific data.

#### 4c. Enhanced Health Check

`GET /health` returns multi-component status:
```json
{
  "status": "degraded",
  "version": "1.2.0",
  "checks": {
    "database": {"status": "ok", "latency_ms": 2},
    "redis": {"status": "ok", "latency_ms": 1},
    "exchange_accounts": {
      "status": "degraded",
      "total": 5,
      "healthy": 4,
      "circuit_open": 1,
      "accounts": [
        {"id": 3, "email": "service@corp.com", "circuit_state": "open"}
      ]
    }
  }
}
```

HTTP status: 200 (healthy), 207 (degraded — some accounts unavailable), 503 (unhealthy — DB or Redis down).

---

### 5. Code Quality

#### 5a. Domain Exception Hierarchy

```python
# app/core/exceptions.py additions

class EWSGatewayException(Exception):
    """Base class for all domain exceptions."""
    error_code: str = "INTERNAL_ERROR"
    http_status: int = 500

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
```

Global handler in `app/core/init_app.py` maps `EWSGatewayException` → structured error response.

#### 5b. Standardized Error Response

All error responses:
```json
{
  "error_code": "ACCOUNT_NOT_FOUND",
  "message": "Exchange account with id=42 not found",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Backward compatibility**: The existing `{"code": ..., "msg": ...}` format is deprecated but still returned for `HTTPException` instances until a future version removes it.

#### 5c. Pagination Standardization

```python
# app/schemas/common.py
class PageParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

class Page(GenericModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int
```

Backward compatibility: accept `skip` and `limit` query params as aliases (emit deprecation warning in response headers: `Deprecation: skip/limit params deprecated, use page/size`).

---

## Implementation Priority

| Phase | Components | P-level |
|-------|-----------|---------|
| **Phase 1** (Core Reliability) | ARQ task queue, email tasks, WebhookDelivery model, webhook tasks, retry decorator | P0 |
| **Phase 2** (Resilience) | CircuitBreaker refactor, connection pool integration, proactive health ping | P1 |
| **Phase 3** (Observability) | structlog, Prometheus metrics, enhanced health check | P1 |
| **Phase 4** (Code Quality) | Domain exceptions, error response standardization, pagination | P2 |

## Dependencies to Add

```toml
# pyproject.toml additions
arq = "^0.26"
structlog = "^24.4"
prometheus-fastapi-instrumentator = "^7.0"
httpx = "^0.28"  # Already present, verify version
```

## Migration Notes

- No database breaking changes in Phase 1-3
- `WebhookDelivery` table addition requires Aerich migration (new table, no column changes)
- `structlog` replaces standard `logging` in app code; existing log aggregation pipelines parse JSON by default

## Testing Requirements

- Unit tests for `CircuitBreaker` class (all state transitions)
- Unit tests for `@retry` decorator (backoff timing, exception filtering)
- Integration tests for `send_email_task` with mock Exchange (pending→success, pending→failed→retry)
- Integration tests for `deliver_webhook_task` (delivered, exhausted retries → dead)
- Health check endpoint tests (all three status codes: 200, 207, 503)
