import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.exchange.email_service import EmailService
import base64


@pytest.fixture
def email_service():
    return EmailService()


@pytest.fixture
def mock_exchange_connection():
    with patch("app.services.exchange.email_service.get_exchange_connection") as mock:
        mock_conn = AsyncMock()
        mock.return_value.__aenter__.return_value = mock_conn
        yield mock_conn


@pytest.fixture(autouse=True)
def mock_classes():
    # Use MagicMock class itself so isinstance(obj, FileAttachment) works
    # when obj is an instance of MagicMock.
    with patch("app.services.exchange.email_service.FileAttachment", new=MagicMock) as mock_file_cls:
        yield mock_file_cls


@pytest.mark.asyncio
async def test_get_email_with_attachments(email_service, mock_exchange_connection, mock_classes):
    mock_file_cls = mock_classes

    # 1. Setup Mock Item with Attachments
    mock_item = MagicMock()
    mock_item.id = "test_id"
    mock_item.subject = "Test Subject"
    mock_item.datetime_received = MagicMock()
    mock_item.datetime_received.isoformat.return_value = "2023-01-01T12:00:00"

    # Create valid dummy content
    test_content = b"hello world image content"
    expected_content_b64 = base64.b64encode(test_content).decode("utf-8")

    # Mock Attachment 1: Inline Image
    att1 = MagicMock()
    # We must ensure isinstance(att1, FileAttachment) returns True.
    # Since we use autospec=False or just MagicMock, isinstance might fail if not careful.
    # However, in the code: `if isinstance(att, FileAttachment):`
    # We need to make sure the mock registers as FileAttachment.
    # The patch `app.services.exchange.email_service.FileAttachment` replaces the class.
    # So if we say att1 is an instance of that mock class, it should work?
    # Or strict check?

    # In the code: `from exchangelib import FileAttachment`
    # `isinstance(att, FileAttachment)`
    # The `email_service.FileAttachment` is patched.
    # So `isinstance` will check against the Mock object returned by patch?
    # No, `patch` replaces the name in the module.
    # So `email_service.FileAttachment` IS the mock.
    # So `isinstance(att1, email_service.FileAttachment)` should be true if att1 is created from it?
    # Easier way: `spec=FileAttachment` or just ensure the loop works.

    # Actually, let's use a real FileAttachment purely for type checking if possible,
    # but `exchangelib` might be complex.
    # Let's rely on the patched class being the one checked against.

    # Important: The code under test imports FileAttachment from exchangelib.
    # `from exchangelib import FileAttachment`
    # Our patch `app.services.exchange.email_service.FileAttachment` intercepts that import in `email_service.py`.
    # So `email_service.FileAttachment` refers to the Mock.
    # So we just need `att1` to be an instance of that Mock.

    mock_FileAttachment = mock_classes
    att1 = mock_FileAttachment()  # Instance of the mock class
    att1.name = "image.png"
    att1.content_type = "image/png"
    att1.size = 1234
    att1.content = test_content
    att1.content_id = "12345"
    att1.is_inline = True

    # Mock Attachment 2: Regular File
    att2 = mock_FileAttachment()
    att2.name = "doc.pdf"
    att2.content_type = "application/pdf"
    att2.size = 5678
    att2.content = b"pdf content"
    att2.content_id = None
    att2.is_inline = False

    att2.content_id = None
    att2.is_inline = False

    mock_item.attachments = [att1, att2]
    # Set body with cid reference
    mock_item.body = '<html><body>Test Image: <img src="cid:12345"></body></html>'

    # Setup connection return
    mock_exchange_connection.account = MagicMock()
    mock_exchange_connection.account.inbox.get.return_value = mock_item

    # 2. Call Method
    result = await email_service.get_email(account_id=1, email_id="test_id")

    # 3. Assertions
    assert result["success"] is True
    data = result["data"]
    assert data["id"] == "test_id"

    # Verify Body Replacement
    expected_data_uri = f"data:image/png;base64,{expected_content_b64}"
    assert expected_data_uri in data["body"]
    assert 'src="cid:12345"' not in data["body"]

    assert len(data["attachments"]) == 2

    # Verify Attachment 1 (Inline)
    res_att1 = data["attachments"][0]
    assert res_att1["name"] == "image.png"
    assert res_att1["content"] == expected_content_b64
    assert res_att1["content_id"] == "12345"  # Raw content_id without cid: prefix
    assert res_att1["is_inline"] is True

    # Verify Attachment 2 (Regular)
    res_att2 = data["attachments"][1]
    assert res_att2["name"] == "doc.pdf"
    assert res_att2["content"] == base64.b64encode(b"pdf content").decode("utf-8")
    assert res_att2["is_inline"] is False
