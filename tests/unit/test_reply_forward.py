"""回复/转发的文件夹查找、草稿及请求兼容性测试。"""

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.exchange import EmailForwardRequest, EmailReplyRequest
from app.services.exchange.email_service import _find_item, _send_via_draft


class TestFindItem:
    def test_finds_in_specified_folder(self):
        account = MagicMock()
        account.inbox.get.return_value = MagicMock(id="item-1")

        result = _find_item(account, "item-1", "INBOX")

        assert result.id == "item-1"
        account.inbox.get.assert_called_once_with(id="item-1")

    def test_falls_back_to_fetch(self):
        account = MagicMock()
        account.inbox.get.side_effect = Exception("Not found in inbox")
        fetched = MagicMock(id="fetched-1")
        account.fetch.return_value = [fetched]

        result = _find_item(account, "fetched-1", "INBOX")

        assert result.id == "fetched-1"
        account.fetch.assert_called_once_with(ids=["fetched-1"])

    def test_raises_when_not_found(self):
        account = MagicMock()
        account.inbox.get.side_effect = Exception("Not found")
        account.fetch.return_value = [None]

        with pytest.raises(ValueError, match="Original email not found"):
            _find_item(account, "missing-id", "INBOX")


class TestSendViaDraft:
    @staticmethod
    def _make_reply_item():
        reply_item = MagicMock()
        saved_id = MagicMock()
        saved_id.id = "draft-123"
        reply_item.save.return_value = saved_id
        return reply_item

    @staticmethod
    def _make_account(draft_message=None):
        account = MagicMock()
        if draft_message is None:
            draft_message = MagicMock(id="draft-123", changekey="ck-456")
        account.drafts.get.return_value = draft_message
        return account

    def test_send_mode(self):
        reply_item = self._make_reply_item()
        draft_message = MagicMock(id="draft-123", changekey="ck-456")
        account = self._make_account(draft_message)

        result = _send_via_draft(account, reply_item, send=True)

        reply_item.save.assert_called_once_with(account.drafts)
        account.drafts.get.assert_called_once_with(id="draft-123")
        draft_message.send.assert_called_once()
        assert result["sent"] is True

    def test_draft_mode_returns_id(self):
        reply_item = self._make_reply_item()
        draft_message = MagicMock(id="draft-123", changekey="ck-456")
        account = self._make_account(draft_message)

        result = _send_via_draft(account, reply_item, send=False)

        draft_message.send.assert_not_called()
        assert result == {"id": "draft-123", "changekey": "ck-456"}

    def test_attaches_files_before_send(self):
        reply_item = self._make_reply_item()
        draft_message = MagicMock(id="draft-123", changekey="ck-456")
        account = self._make_account(draft_message)
        attachment = MagicMock(filename="test.pdf", content="dGVzdA==", content_type="application/pdf")

        with patch("app.services.exchange.email_service._attach_files") as mock_attach:
            _send_via_draft(account, reply_item, attachments=[attachment], send=True)

        mock_attach.assert_called_once_with(draft_message, [attachment], None)


class TestSchemaDefaults:
    def test_reply_request_defaults(self):
        request = EmailReplyRequest(account_id=1, reference_item_id="id-1", body="<p>reply</p>")

        assert request.folder == "INBOX"
        assert request.save_as_draft is False
        assert request.body_type == "html"
        assert request.reply_all is False

    def test_reply_request_custom_folder(self):
        request = EmailReplyRequest(
            account_id=1,
            reference_item_id="id-1",
            body="<p>reply</p>",
            folder="SENT",
            save_as_draft=True,
        )

        assert request.folder == "SENT"
        assert request.save_as_draft is True

    def test_forward_request_defaults(self):
        request = EmailForwardRequest(account_id=1, reference_item_id="id-1", to=["user@example.com"])

        assert request.folder == "INBOX"
        assert request.save_as_draft is False
        assert request.body == ""
