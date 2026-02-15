import pytest
from pydantic import ValidationError

from app.schemas.webhook import WebhookCreate
from app.settings.config import settings


def test_private_webhook_url_allowed_when_feature_enabled(monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_ALLOW_PRIVATE_URLS", True)

    payload = WebhookCreate(
        account_id=1,
        url="http://10.78.14.164:15000/webhooks/exchange",
        secret="12345678",
    )

    assert payload.url.host == "10.78.14.164"


def test_private_webhook_url_blocked_when_feature_disabled(monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_ALLOW_PRIVATE_URLS", False)

    with pytest.raises(ValidationError, match="禁止使用内部网络地址"):
        WebhookCreate(
            account_id=1,
            url="http://10.78.14.164:15000/webhooks/exchange",
            secret="12345678",
        )


def test_webhook_events_default_is_new_mail_event():
    payload = WebhookCreate(
        account_id=1,
        url="http://example.com/webhook",
        secret="12345678",
    )
    assert payload.events == ["NewMailEvent"]


def test_webhook_events_aliases_are_normalized():
    payload = WebhookCreate(
        account_id=1,
        url="http://example.com/webhook",
        secret="12345678",
        events=["NewMail", "ModifiedEvent"],
    )
    assert payload.events == ["NewMailEvent", "ModifiedEvent"]


def test_webhook_events_invalid_value_rejected():
    with pytest.raises(ValidationError, match="不支持的事件类型"):
        WebhookCreate(
            account_id=1,
            url="http://example.com/webhook",
            secret="12345678",
            events=["UnknownEvent"],
        )
