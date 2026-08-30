from datetime import datetime, timedelta

import pytest


@pytest.mark.asyncio
async def test_cleanup_sensitive_logs_removes_expired_audit_and_mail_content(init_test_db):
    from app.models.admin import AuditLog
    from app.models.exchange import ExchangeMailLog
    from app.settings import settings
    from app.tasks.cleanup_tasks import cleanup_sensitive_logs_task

    now = datetime.now()
    expired_audit = await AuditLog.create(user_id=1, path="/expired")
    fresh_audit = await AuditLog.create(user_id=1, path="/fresh")
    await AuditLog.filter(id=expired_audit.id).update(
        created_at=now - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS + 1)
    )

    expired_failed = await ExchangeMailLog.create(
        account_id=1,
        action="send",
        status="failed",
        request_body={"body": "expired"},
    )
    fresh_failed = await ExchangeMailLog.create(
        account_id=1,
        action="send",
        status="failed",
        request_body={"body": "fresh"},
    )
    expired_success = await ExchangeMailLog.create(
        account_id=1,
        action="send",
        status="success",
        request_body={"body": "expired success"},
    )
    await ExchangeMailLog.filter(id__in=[expired_failed.id, expired_success.id]).update(
        updated_at=now - timedelta(days=settings.MAIL_LOG_BODY_RETENTION_DAYS + 1)
    )

    result = await cleanup_sensitive_logs_task({})

    assert result["audit_logs_deleted"] >= 1
    assert result["mail_bodies_cleared"] >= 2
    assert await AuditLog.filter(id=expired_audit.id).exists() is False
    assert await AuditLog.filter(id=fresh_audit.id).exists() is True
    await expired_failed.refresh_from_db()
    await fresh_failed.refresh_from_db()
    await expired_success.refresh_from_db()
    assert expired_failed.request_body is None
    assert expired_success.request_body is None
    assert fresh_failed.request_body is not None
