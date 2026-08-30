from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ExchangeTimeoutError
from app.schemas.exchange import EmailSyncRequest
from app.services.exchange.email_service import EmailService, _sync_folder_changes


def _mock_folder():
    folder = MagicMock()
    folder.account.version = "Exchange2016"
    folder.allowed_item_fields.return_value = []
    folder.item_sync_state = "stale-cached-state"
    return folder


def _completed_changes(*changes, state="server-state"):
    yield from changes
    from app.services.exchange.email_service import SyncCompleted

    raise SyncCompleted(sync_state=state)


def test_sync_folder_changes_does_not_use_cached_folder_state():
    folder = _mock_folder()
    sync_collection = MagicMock()
    sync_collection.sync_items.return_value = _completed_changes(("create", MagicMock()))

    with patch("app.services.exchange.email_service.FolderCollection", return_value=sync_collection):
        changes, new_state = _sync_folder_changes(
            folder,
            sync_state=None,
            max_changes_returned=3,
            only_fields=None,
        )

    call_kwargs = sync_collection.sync_items.call_args.kwargs
    assert call_kwargs["sync_state"] is None
    assert call_kwargs["max_changes_returned"] == 3
    assert changes
    assert new_state == "server-state"
    assert folder.item_sync_state == "stale-cached-state"


def test_sync_folder_changes_preserves_complete_exchangelib_sync():
    folder = _mock_folder()
    sync_collection = MagicMock()
    sync_collection.sync_items.return_value = _completed_changes(
        ("update", MagicMock()), ("delete", MagicMock()), state="next-state"
    )

    with patch("app.services.exchange.email_service.FolderCollection", return_value=sync_collection):
        changes, new_state = _sync_folder_changes(
            folder,
            sync_state="client-state",
            max_changes_returned=2,
            only_fields=None,
        )

    assert sync_collection.sync_items.call_count == 1
    assert sync_collection.sync_items.call_args.kwargs["sync_state"] == "client-state"
    assert len(changes) == 2
    assert new_state == "next-state"


@pytest.mark.asyncio
async def test_sync_emails_returns_compatible_sync_response():
    service = EmailService()
    request = EmailSyncRequest(account_id=1, sync_state=None, limit=1)

    exchange_connection = AsyncMock()
    exchange_connection.account = MagicMock()
    item = MagicMock()
    item.id = "item-1"
    item.subject = "Subject"
    item.sender = None
    item.datetime_received = None
    item.is_read = True
    item.has_attachments = False

    with (
        patch("app.services.exchange.email_service.get_exchange_connection", return_value=exchange_connection),
        patch(
            "app.services.exchange.email_service._sync_folder_changes",
            return_value=([("create", item)], "next-state"),
        ) as sync_page,
        patch("app.services.exchange.email_service.ExchangeMailLog.create", new_callable=AsyncMock),
    ):
        result = await service.sync_emails(request)

    sync_page.assert_called_once()
    assert result == {
        "success": True,
        "sync_state": "next-state",
        "items": [
            {
                "change_type": "create",
                "id": "item-1",
                "item": {
                    "id": "item-1",
                    "subject": "Subject",
                    "sender": None,
                    "received_time": None,
                    "is_read": True,
                    "has_attachments": False,
                },
            }
        ],
    }


@pytest.mark.asyncio
async def test_sync_emails_turns_executor_timeout_into_gateway_504():
    service = EmailService()
    request = EmailSyncRequest(account_id=1, sync_state=None, limit=50)
    exchange_connection = AsyncMock()
    exchange_connection.account = MagicMock()

    with (
        patch("app.services.exchange.email_service.get_exchange_connection", return_value=exchange_connection),
        patch(
            "app.services.exchange.email_service.run_sync_with_timeout",
            new=AsyncMock(side_effect=TimeoutError),
        ) as run_sync,
        pytest.raises(ExchangeTimeoutError, match="邮件同步超时"),
    ):
        await service.sync_emails(request)

    run_sync.assert_awaited_once()
