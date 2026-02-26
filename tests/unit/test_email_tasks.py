from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_send_email_task_skips_non_pending(init_test_db):
    """If log status is not pending, task skips gracefully."""
    from app.models.exchange import ExchangeMailLog
    from app.tasks.email_tasks import send_email_task

    log = await ExchangeMailLog.create(
        account_id=1,
        action="send",
        status="success",
        recipients=["a@b.com"],
        subject="test",
        request_body={"account_id": 1, "to": ["a@b.com"], "subject": "test", "body": "hi", "body_type": "text"},
    )
    result = await send_email_task({"job_try": 1}, log.id)
    assert result["skipped"] is True


@pytest.mark.asyncio
async def test_send_email_task_fails_without_request_body(init_test_db):
    """If log has no request_body, task marks it failed."""
    from app.models.exchange import ExchangeMailLog
    from app.tasks.email_tasks import send_email_task

    log = await ExchangeMailLog.create(
        account_id=1,
        action="send",
        status="pending",
        recipients=["a@b.com"],
        subject="test",
        request_body=None,
    )
    result = await send_email_task({"job_try": 1}, log.id)
    assert "error" in result
    await log.refresh_from_db()
    assert log.status == "failed"


@pytest.mark.asyncio
async def test_send_email_task_raises_retry_on_transport_error(init_test_db):
    """TransportError should raise arq.Retry."""
    from arq import Retry
    from exchangelib.errors import TransportError

    from app.models.exchange import ExchangeMailLog
    from app.tasks.email_tasks import send_email_task

    log = await ExchangeMailLog.create(
        account_id=1,
        action="send",
        status="pending",
        recipients=["a@b.com"],
        subject="test",
        request_body={"account_id": 1, "to": ["a@b.com"], "subject": "test", "body": "body", "body_type": "text"},
    )
    with patch("app.tasks.email_tasks.get_email_service") as mock_svc:
        instance = AsyncMock()
        instance._execute_send.side_effect = TransportError("timeout")
        mock_svc.return_value = instance
        with pytest.raises(Retry):
            await send_email_task({"job_try": 1}, log.id)
