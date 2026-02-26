from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.exchange import ExchangeMailLog
from app.schemas.exchange import EmailSendRequest
from app.services.exchange.email_service import EmailService


@pytest.fixture
def email_service():
    return EmailService()


@pytest.fixture
def mock_arq_pool():
    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock()
    with patch("app.services.exchange.email_service.get_arq_pool", return_value=mock_pool):
        yield mock_pool


@pytest.fixture
def mock_exchange_connection():
    with patch("app.services.exchange.email_service.get_exchange_connection") as mock:
        mock_conn = AsyncMock()
        mock.return_value.__aenter__.return_value = mock_conn
        yield mock_conn


@pytest.fixture(autouse=True)
def mock_exchangelib_classes():
    with (
        patch("app.services.exchange.email_service.Message") as mock_msg,
        patch("app.services.exchange.email_service.HTMLBody") as mock_html,
        patch("app.services.exchange.email_service.FileAttachment") as mock_file,
    ):
        yield mock_msg, mock_html, mock_file


@pytest.mark.asyncio
async def test_send_email_enqueues_task(email_service, mock_arq_pool):
    # Prepare request
    request = EmailSendRequest(account_id=1, to=["test@example.com"], subject="Test Subject", body="Test Body")

    # Call method
    result = await email_service.send_email(request)

    # Assertions
    assert result["success"] is True
    assert result["status"] == "queued"
    assert "log_id" in result

    # Verify log created with request_body persisted
    log = await ExchangeMailLog.get(id=result["log_id"])
    assert log.status == "pending"
    assert log.subject == "Test Subject"
    assert log.request_body is not None

    # Verify ARQ job enqueued
    mock_arq_pool.enqueue_job.assert_called_once_with("send_email_task", log.id)


@pytest.mark.asyncio
async def test_send_email_bg_task_success(email_service, mock_exchange_connection):
    # Create log entry
    log = await ExchangeMailLog.create(account_id=1, action="send", status="pending", subject="Test")

    request = EmailSendRequest(account_id=1, to=["test@example.com"], subject="Test", body="Test Body")

    # Execute background task
    await email_service._send_email_bg_task(log.id, request)

    # Verify success
    await log.refresh_from_db()
    assert log.status == "success"

    # Verify exchange call
    mock_exchange_connection.account.return_value = MagicMock()  # Mock account property


@pytest.mark.asyncio
async def test_send_email_bg_task_retry(email_service, mock_exchange_connection, mock_exchangelib_classes):
    from exchangelib.errors import TransportError

    mock_message_cls, _, _ = mock_exchangelib_classes

    # Create log entry
    log = await ExchangeMailLog.create(account_id=1, action="send", status="pending", subject="Retry Test")

    request = EmailSendRequest(account_id=1, to=["test@example.com"], subject="Retry Test", body="Test Body")

    # Setup mock to fail twice then succeed
    mock_msg_instance = mock_message_cls.return_value
    # Side effect: 2 failures, then success (return None)
    # Default is save_to_sent=True, so send_and_save is called
    mock_msg_instance.send_and_save.side_effect = [TransportError("Fail 1"), TransportError("Fail 2"), None]

    # We also need to speed up sleep for tests
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # Execute background task
        await email_service._send_email_bg_task(log.id, request)

        # Should have slept twice
        assert mock_sleep.call_count == 2

    # Verify success eventually
    await log.refresh_from_db()
    assert log.status == "success"
