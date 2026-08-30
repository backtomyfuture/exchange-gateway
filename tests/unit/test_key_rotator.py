import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utils.key_rotator import KeyRotator


def _make_valid_key() -> str:
    return base64.b64encode(os.urandom(32)).decode("utf-8")


def test_verify_keys_valid():
    old_key = _make_valid_key()
    new_key = _make_valid_key()
    rotator = KeyRotator(old_key, new_key)
    result = rotator.verify_keys()
    assert result["old_key_valid"] is True
    assert result["new_key_valid"] is True


def test_verify_keys_invalid():
    valid_key = _make_valid_key()
    invalid_key = "not-a-valid-base64-key"
    rotator = KeyRotator(valid_key, valid_key)

    result = rotator.verify_keys()
    assert result["old_key_valid"] is True
    assert result["new_key_valid"] is True

    try:
        rotator_bad = KeyRotator(invalid_key, valid_key)
        result_bad = rotator_bad.verify_keys()
        assert result_bad["old_key_valid"] is False
    except ValueError:
        pass


@pytest.mark.asyncio
async def test_rotate_all_reencrypts_accounts_and_webhook_secrets():
    old_key = _make_valid_key()
    new_key = _make_valid_key()
    rotator = KeyRotator(old_key, new_key)

    account = MagicMock(email="account@example.com")
    account.encrypted_password = rotator.old_crypto.encrypt("account-password")
    account.save = AsyncMock()

    webhook = MagicMock(url="https://example.com/webhook")
    webhook.secret = rotator.old_crypto.encrypt("webhook-secret")
    webhook.save = AsyncMock()

    with (
        patch("app.utils.key_rotator.ExchangeAccount.all", new=AsyncMock(return_value=[account])),
        patch("app.utils.key_rotator.WebhookSubscription.all", new=AsyncMock(return_value=[webhook])),
    ):
        result = await rotator.rotate_all()

    assert result["total"] == 2
    assert result["success"] == 2
    assert result["failed"] == 0
    assert rotator.new_crypto.decrypt(account.encrypted_password) == "account-password"
    assert rotator.new_crypto.decrypt(webhook.secret) == "webhook-secret"
    account.save.assert_awaited_once()
    webhook.save.assert_awaited_once()
