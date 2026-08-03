import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from exchangelib.errors import ErrorInvalidPropertyRequest

from app.core.exceptions import ExchangeTimeoutError
from app.services.exchange.email_service import (
    DETAIL_FIELDS,
    DETAIL_FIELDS_WITHOUT_UNIQUE_BODY,
    EmailService,
)


@pytest.fixture
def email_service():
    return EmailService()


@pytest.fixture
def mock_exchange_connection():
    with patch("app.services.exchange.email_service.get_exchange_connection") as mock:
        mock_conn = AsyncMock()
        mock.return_value.__aenter__.return_value = mock_conn
        mock_conn.account = MagicMock()
        yield mock_conn


@pytest.fixture(autouse=True)
def mock_classes():
    with patch("app.services.exchange.email_service.FileAttachment", new=MagicMock) as mock_file_attachment:
        yield mock_file_attachment


def _email_item(*, attachments=None):
    item = MagicMock()
    item.id = "test_id"
    item.subject = "Test Subject"
    item.body = '<html><body>Test Image: <img src="cid:12345"></body></html>'
    item.unique_body = '<html><body>Latest update: <img src="cid:12345"></body></html>'
    item.sender = None
    item.to_recipients = []
    item.cc_recipients = []
    item.datetime_received = SimpleNamespace(isoformat=lambda: "2023-01-01T12:00:00")
    item.is_read = False
    item.attachments = attachments or []
    item.conversation_id = SimpleNamespace(id="conversation-123")
    item.conversation_index = b"\x01\x02\x03"
    item.message_id = "<message-003@example.com>"
    item.in_reply_to = "<message-002@example.com>"
    item.references = "<message-001@example.com> <message-002@example.com>"
    return item


@pytest.mark.asyncio
async def test_get_email_returns_conversation_contract_and_keeps_unique_body_raw(
    email_service,
    mock_exchange_connection,
    mock_classes,
):
    test_content = b"hello world image content"
    expected_content_b64 = base64.b64encode(test_content).decode("utf-8")

    inline_attachment = mock_classes()
    inline_attachment.name = "image.png"
    inline_attachment.content_type = "image/png"
    inline_attachment.size = 1234
    inline_attachment.content = test_content
    inline_attachment.content_id = "12345"
    inline_attachment.is_inline = True

    regular_attachment = mock_classes()
    regular_attachment.name = "doc.pdf"
    regular_attachment.content_type = "application/pdf"
    regular_attachment.size = 5678
    regular_attachment.content = b"pdf content"
    regular_attachment.content_id = None
    regular_attachment.is_inline = False

    item = _email_item(attachments=[inline_attachment, regular_attachment])
    query = mock_exchange_connection.account.inbox.all.return_value
    query.only.return_value.get.return_value = item

    result = await email_service.get_email(account_id=1, email_id="test_id")
    assert result["success"] is True
    data = result["data"]

    expected_data_uri = f"data:image/png;base64,{expected_content_b64}"
    assert expected_data_uri in data["body"]
    assert 'src="cid:12345"' not in data["body"]
    assert data["unique_body"] == item.unique_body
    assert 'src="cid:12345"' in data["unique_body"]
    assert expected_data_uri not in data["unique_body"]

    assert data["conversation_id"] == "conversation-123"
    assert data["conversation_index"] == base64.b64encode(b"\x01\x02\x03").decode("ascii")
    assert data["internet_message_id"] == "<message-003@example.com>"
    assert data["in_reply_to"] == "<message-002@example.com>"
    assert data["references"] == ["<message-001@example.com>", "<message-002@example.com>"]
    assert data["references_raw"] == "<message-001@example.com> <message-002@example.com>"

    assert len(data["attachments"]) == 2
    assert data["attachments"][0]["content"] == expected_content_b64
    assert data["attachments"][1]["content"] == base64.b64encode(b"pdf content").decode("utf-8")
    query.only.assert_called_once_with(*DETAIL_FIELDS)


@pytest.mark.asyncio
async def test_get_email_degrades_when_unique_body_is_unsupported(email_service, mock_exchange_connection):
    item = _email_item()
    item.unique_body = None
    item.conversation_id = None
    item.conversation_index = None
    item.message_id = None
    item.in_reply_to = None
    item.references = None

    query = mock_exchange_connection.account.inbox.all.return_value
    full_contract_query = MagicMock()
    fallback_query = MagicMock()
    full_contract_query.get.side_effect = ErrorInvalidPropertyRequest("UniqueBody is unsupported")
    fallback_query.get.return_value = item
    query.only.side_effect = [full_contract_query, fallback_query]

    result = await email_service.get_email(account_id=1, email_id="test_id")
    assert result["success"] is True
    data = result["data"]

    assert data["unique_body"] is None
    assert data["conversation_id"] is None
    assert data["conversation_index"] is None
    assert data["internet_message_id"] is None
    assert data["in_reply_to"] is None
    assert data["references"] == []
    assert data["references_raw"] is None
    assert query.only.call_args_list == [
        call(*DETAIL_FIELDS),
        call(*DETAIL_FIELDS_WITHOUT_UNIQUE_BODY),
    ]


@pytest.mark.asyncio
async def test_get_email_turns_executor_timeout_into_gateway_504(email_service, mock_exchange_connection):
    with patch(
        "app.services.exchange.email_service.run_sync_with_timeout",
        new=AsyncMock(side_effect=TimeoutError),
    ):
        with pytest.raises(ExchangeTimeoutError, match="获取邮件详情超时"):
            await email_service.get_email(account_id=1, email_id="test_id")
