from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.exchange import ExchangeAccount
from app.models.webhook import WebhookSubscription
from app.schemas.webhook import WebhookCreate, WebhookUpdate
from app.services.exchange.webhook_service import WebhookService


async def _create_account(owner_id: int = 1) -> ExchangeAccount:
    return await ExchangeAccount.create(
        email=f"webhook-{owner_id}@example.com",
        username="webhook-user",
        encrypted_password="encrypted-password",
        owner_id=owner_id,
    )


@pytest.mark.asyncio
async def test_create_webhook_never_returns_or_audits_secret(init_test_db):
    account = await _create_account()
    crypto = MagicMock()
    crypto.encrypt.return_value = "encrypted-secret"
    audit = MagicMock(log=AsyncMock())

    with (
        patch("app.utils.crypto.get_crypto", return_value=crypto),
        patch("app.services.exchange.webhook_service.get_audit_service", return_value=audit),
    ):
        result = await WebhookService().create_webhook(
            WebhookCreate(account_id=account.id, url="https://example.com/hook", secret="original-secret"),
            owner_id=1,
        )

    assert result["success"] is True
    assert "secret" not in result["data"]
    webhook = await WebhookSubscription.get(id=result["data"]["id"])
    assert webhook.secret == "encrypted-secret"
    assert "secret" not in audit.log.await_args.kwargs["details"]


@pytest.mark.asyncio
async def test_update_webhook_keeps_secret_write_only(init_test_db):
    webhook = await WebhookSubscription.create(
        url="https://example.com/hook",
        secret="old-encrypted-secret",
        account_id=1,
        events=["NewMailEvent"],
        folders=["*"],
        is_active=True,
        created_by=1,
    )
    crypto = MagicMock()
    crypto.encrypt.return_value = "new-encrypted-secret"
    audit = MagicMock(log=AsyncMock())

    with (
        patch("app.utils.crypto.get_crypto", return_value=crypto),
        patch("app.services.exchange.webhook_service.get_audit_service", return_value=audit),
    ):
        result = await WebhookService().update_webhook(
            webhook.id,
            WebhookUpdate(secret="new-original-secret", remark="更新备注"),
            owner_id=1,
        )

    assert result["success"] is True
    assert "secret" not in result["data"]
    await webhook.refresh_from_db()
    assert webhook.secret == "new-encrypted-secret"
    assert audit.log.await_args.kwargs["details"] == {"remark": "更新备注", "secret_changed": True}


@pytest.mark.asyncio
async def test_list_webhooks_never_returns_secret(init_test_db):
    await WebhookSubscription.create(
        url="https://example.com/hook",
        secret="encrypted-secret",
        account_id=1,
        events=["NewMailEvent"],
        folders=["*"],
        is_active=True,
        created_by=1,
    )

    result = await WebhookService().list_webhooks(owner_id=1)

    assert result["success"] is True
    assert all("secret" not in item for item in result["items"])
