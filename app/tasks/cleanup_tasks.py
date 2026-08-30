"""Scheduled cleanup for persisted audit metadata and email request bodies."""

from datetime import datetime, timedelta

from app.log import logger
from app.models.admin import AuditLog
from app.models.exchange import ExchangeMailLog
from app.settings import settings

_BATCH_SIZE = 1000


async def _delete_expired_audit_logs(cutoff: datetime) -> int:
    deleted = 0
    while True:
        ids = await AuditLog.filter(created_at__lt=cutoff).order_by("id").limit(_BATCH_SIZE).values_list(
            "id", flat=True
        )
        if not ids:
            break
        count = await AuditLog.filter(id__in=ids).delete()
        deleted += count
        if count == 0:
            break
    return deleted


async def _clear_expired_mail_bodies(cutoff: datetime) -> int:
    cleared = 0
    while True:
        ids = await ExchangeMailLog.filter(
            status__in=["success", "failed"],
            request_body__isnull=False,
            updated_at__lt=cutoff,
        ).order_by("id").limit(_BATCH_SIZE).values_list("id", flat=True)
        if not ids:
            break
        count = await ExchangeMailLog.filter(id__in=ids).update(request_body=None)
        cleared += count
        if count == 0:
            break
    return cleared


async def cleanup_sensitive_logs_task(ctx: dict) -> dict:
    """Remove expired audit rows and email request bodies without crashing ARQ."""
    result = {"audit_logs_deleted": 0, "mail_bodies_cleared": 0}

    try:
        audit_cutoff = datetime.now() - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
        result["audit_logs_deleted"] = await _delete_expired_audit_logs(audit_cutoff)
    except Exception:
        logger.exception("cleanup_sensitive_logs_task: audit log cleanup failed")

    try:
        mail_cutoff = datetime.now() - timedelta(days=settings.MAIL_LOG_BODY_RETENTION_DAYS)
        result["mail_bodies_cleared"] = await _clear_expired_mail_bodies(mail_cutoff)
    except Exception:
        logger.exception("cleanup_sensitive_logs_task: mail body cleanup failed")

    logger.info(f"cleanup_sensitive_logs_task completed: {result}")
    return result
