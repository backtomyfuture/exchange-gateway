"""ARQ webhook delivery and subscription renewal tasks."""

import hashlib
import hmac
import json
import logging
import time

import httpx
from arq import Retry

from app.core.metrics import webhook_delivery_total
from app.models.webhook import WebhookDelivery

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
    delivery = await WebhookDelivery.get_or_none(id=delivery_id).select_related("subscription")
    if not delivery:
        logger.error("deliver_webhook_task: delivery %d not found", delivery_id)
        return {"error": f"delivery {delivery_id} not found"}

    if delivery.status == "delivered":
        return {"skipped": True}

    sub = delivery.subscription
    attempt = ctx["job_try"]

    try:
        # 数据库存储的是密文；签名必须始终使用创建时提供的原始密钥。
        from app.utils.crypto import get_crypto

        secret = get_crypto().decrypt(sub.secret)
        await _http_post_webhook(sub.url, delivery.payload, secret)
        delivery.update_from_dict(
            {
                "status": "delivered",
                "attempt_count": attempt,
                "last_error": None,
            }
        )
        await delivery.save()
        webhook_delivery_total.labels(status="delivered").inc()
        logger.info("deliver_webhook_task: delivery %d delivered (attempt %d)", delivery_id, attempt)
        return {"success": True, "delivery_id": delivery_id}

    except Exception as exc:
        delivery.update_from_dict({"attempt_count": attempt, "last_error": str(exc)})
        await delivery.save()

        if attempt >= MAX_DELIVERY_ATTEMPTS:
            delivery.update_from_dict({"status": "dead"})
            await delivery.save()
            webhook_delivery_total.labels(status="dead").inc()
            logger.error(
                "deliver_webhook_task: delivery %d dead after %d attempts: %s",
                delivery_id,
                attempt,
                exc,
            )
            return {"dead": True, "delivery_id": delivery_id, "error": str(exc)}

        delay = _RETRY_DELAYS[min(attempt - 1, len(_RETRY_DELAYS) - 1)]
        logger.warning(
            "deliver_webhook_task: delivery %d failed (attempt %d), retry in %ds: %s",
            delivery_id,
            attempt,
            delay,
            exc,
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
