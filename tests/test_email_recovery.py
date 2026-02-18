
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.exchange.email_service import recover_pending_emails
from app.models.exchange import ExchangeMailLog


@pytest.mark.asyncio
async def test_recover_pending_emails_reenqueues_with_request_body():
    """Logs with request_body are re-enqueued into ARQ."""
    mock_log = MagicMock(spec=ExchangeMailLog)
    mock_log.id = 123
    mock_log.status = "pending"
    mock_log.request_body = {"account_id": 1, "to": ["a@b.com"], "subject": "s", "body": "b", "body_type": "text"}

    mock_filter = AsyncMock()
    mock_filter.all.return_value = [mock_log]

    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock()

    with patch("app.models.exchange.ExchangeMailLog.filter", return_value=mock_filter), \
         patch("app.services.exchange.email_service.get_arq_pool", return_value=mock_pool):
        await recover_pending_emails()

    mock_pool.enqueue_job.assert_called_once_with("send_email_task", 123)


@pytest.mark.asyncio
async def test_recover_pending_emails_marks_failed_without_request_body():
    """Logs without request_body (pre-ARQ) are marked failed."""
    mock_log = MagicMock(spec=ExchangeMailLog)
    mock_log.id = 456
    mock_log.request_body = None
    mock_log.update_from_dict = MagicMock()
    mock_log.save = AsyncMock()

    mock_filter = AsyncMock()
    mock_filter.all.return_value = [mock_log]

    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock()

    with patch("app.models.exchange.ExchangeMailLog.filter", return_value=mock_filter), \
         patch("app.services.exchange.email_service.get_arq_pool", return_value=mock_pool):
        await recover_pending_emails()

    mock_pool.enqueue_job.assert_not_called()
    mock_log.update_from_dict.assert_called_once()
    mock_log.save.assert_called_once()
