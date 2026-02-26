from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.lark import LarkTaskQueue
from app.services.lark.handlers.email_handler import EmailActionHandler


@pytest.fixture
def email_handler():
    return EmailActionHandler()


@pytest.fixture
def mock_context():
    return {
        "event_id": "evt_123",
        "app_token": "token_123",
        "table_id": "table_123",
        "record_id": "rec_123",
        "action": "edit",
        "operator_id": "user_123",
        "record_data": {
            "Subject": "Test Email",
            "To": "test@example.com",
            "CC": "cc@example.com",
            "Body": "Hello World",
            "Attachments": [{"file_token": "file_abc", "name": "doc.pdf"}],
        },
    }


@pytest.mark.asyncio
async def test_email_handler_execute_success(email_handler, mock_context):
    """Test successful email sending execution"""

    with (
        patch("app.services.lark.handlers.email_handler.get_email_service") as mock_get_email,
        patch("app.services.lark.handlers.email_handler.get_contact_client") as mock_get_contact,
    ):
        # 1. Mock Email Service
        mock_email_svc = AsyncMock()
        mock_get_email.return_value = mock_email_svc
        mock_email_svc.send_email.return_value = {"success": True, "log_id": 999}

        # 2. Mock Contact Client (not used in this path but needed for patch sanity)
        mock_contact_cli = AsyncMock()
        mock_get_contact.return_value = mock_contact_cli

        # 3. Context has Bitable Client
        mock_bitable_cli = AsyncMock()
        mock_bitable_cli.download_attachment.return_value = (b"fake_content", "doc.pdf")
        mock_context["bitable_client"] = mock_bitable_cli

        # 4. Mock Task Queue Config
        mock_queue = MagicMock(spec=LarkTaskQueue)
        mock_queue.app_id = 1
        mock_queue.default_account_id = 1
        mock_queue.field_mapping = {
            "subject": "Subject",
            "to": "To",
            "cc": "CC",
            "body": "Body",
            "attachments": "Attachments",
        }

        # Execute
        result = await email_handler.execute(mock_context["record_data"], mock_queue, mock_context)

        assert result["success"] is True
        assert result["log_id"] == 999

        # Verify Email Service Called
        mock_email_svc.send_email.assert_called_once()
        ca = mock_email_svc.send_email.call_args
        req = ca[0][0]  # First arg is request

        assert req.subject == "Test Email"
        assert req.to == ["test@example.com"]
        assert req.cc == ["cc@example.com"]
        assert req.body == "Hello World"
        assert len(req.attachments) == 1
        assert req.attachments[0].filename == "doc.pdf"
        assert req.attachments[0].content is not None  # Base64 encoded "fake_content"


@pytest.mark.asyncio
async def test_email_handler_recipient_parsing(email_handler, mock_context):
    """Test recipient parsing with Feishu User IDs"""

    mock_context["record_data"]["To"] = [{"id": "ou_123", "name": "User A"}, "manual@example.com"]

    with (
        patch("app.services.lark.handlers.email_handler.get_email_service") as mock_get_email,
        patch("app.services.lark.handlers.email_handler.get_contact_client") as mock_get_contact,
    ):
        mock_email_svc = AsyncMock()
        mock_get_email.return_value = mock_email_svc
        mock_email_svc.send_email.return_value = {"success": True, "log_id": 999}

        # Mock Contact Client
        mock_contact_cli = AsyncMock()
        mock_get_contact.return_value = mock_contact_cli
        mock_contact_cli.batch_get_emails.return_value = {"ou_123": "user_a@example.com"}

        # Mock Queue
        mock_queue = MagicMock(spec=LarkTaskQueue)
        mock_queue.app_id = 1
        mock_queue.default_account_id = 1
        mock_queue.field_mapping = {"to": "To", "subject": "Subject"}

        # Need context with bitable client to avoid error even if not used for attachments
        mock_context["bitable_client"] = AsyncMock()

        await email_handler.execute(mock_context["record_data"], mock_queue, mock_context)

        # Verify
        ca = mock_email_svc.send_email.call_args
        req = ca[0][0]
        assert "user_a@example.com" in req.to
        assert "manual@example.com" in req.to
        assert len(req.to) == 2
