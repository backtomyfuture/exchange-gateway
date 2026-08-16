"""
ARQ email send task — persistent, retriable email sending.

Replaces the in-process BackgroundTask pattern. Idempotent: if the log
entry is not in 'pending' state, silently skips.
"""

import logging
import time

from arq import Retry
from exchangelib.errors import ErrorTimeoutExpired, TransportError

from app.core.metrics import email_duration_seconds, email_sent_total
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
        log.update_from_dict({"status": "failed", "error_message": "No request_body stored"})
        await log.save()
        return {"error": "no request_body"}

    request = EmailSendRequest(**log.request_body)
    service = get_email_service()

    try:
        start = time.monotonic()
        await service._execute_send(request.account_id, request)
        duration = time.monotonic() - start
        email_duration_seconds.labels(account_id=str(request.account_id)).observe(duration)
        email_sent_total.labels(account_id=str(request.account_id), status="success").inc()
        log.update_from_dict({"status": "success", "request_body": None})
        await log.save()
        logger.info("send_email_task: log %d sent successfully", mail_log_id)
        return {"success": True, "log_id": mail_log_id}

    except _RETRYABLE as exc:
        attempt = ctx["job_try"]
        if attempt > len(_RETRY_DELAYS):
            email_sent_total.labels(account_id=str(log.account_id), status="failed").inc()
            log.update_from_dict({"status": "failed", "error_message": str(exc)})
            await log.save()
            raise
        delay = _RETRY_DELAYS[attempt - 1]
        logger.warning(
            "send_email_task: log %d transient error (attempt %d), retry in %ds: %s",
            mail_log_id,
            attempt,
            delay,
            exc,
        )
        raise Retry(defer=delay)

    except Exception as exc:
        email_sent_total.labels(account_id=str(log.account_id), status="failed").inc()
        log.update_from_dict({"status": "failed", "error_message": str(exc)})
        await log.save()
        logger.error("send_email_task: log %d non-retryable error: %s", mail_log_id, exc)
        raise
