from app.core.exceptions import AccountNotFoundError, EWSGatewayException, ExchangeConnectionError


def test_account_not_found_error_code():
    exc = AccountNotFoundError("Account 42 not found")
    assert exc.error_code == "ACCOUNT_NOT_FOUND"
    assert exc.http_status == 404
    assert exc.message == "Account 42 not found"


def test_exchange_connection_error():
    exc = ExchangeConnectionError("timeout")
    assert exc.error_code == "EXCHANGE_CONNECTION_ERROR"
    assert exc.http_status == 503


def test_ews_exception_handler_returns_structured_response():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core.exceptions import ews_exception_handler

    app = FastAPI()
    app.add_exception_handler(EWSGatewayException, ews_exception_handler)

    @app.get("/test")
    async def endpoint():
        raise AccountNotFoundError("Account 99 not found")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test")
    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "ACCOUNT_NOT_FOUND"
    assert "Account 99" in body["message"]


def test_does_not_exist_no_leak():
    import asyncio
    from unittest.mock import MagicMock

    from tortoise.exceptions import DoesNotExist

    from app.core.exceptions import does_not_exist_handle

    req = MagicMock()
    exc = DoesNotExist("SELECT * FROM secret_table WHERE id=42")
    resp = asyncio.get_event_loop().run_until_complete(does_not_exist_handle(req, exc))
    body = resp.body.decode()
    assert "secret_table" not in body
    assert "SELECT" not in body


def test_integrity_no_leak():
    import asyncio
    from unittest.mock import MagicMock

    from tortoise.exceptions import IntegrityError

    from app.core.exceptions import integrity_handle

    req = MagicMock()
    exc = IntegrityError("UNIQUE constraint failed: users.email")
    resp = asyncio.get_event_loop().run_until_complete(integrity_handle(req, exc))
    body = resp.body.decode()
    assert "UNIQUE constraint" not in body
    assert "users.email" not in body


def test_new_exception_types():
    from app.core.exceptions import (
        AttachmentTooLargeError,
        EmailNotFoundError,
        WebhookDeliveryError,
    )

    att = AttachmentTooLargeError("too big")
    assert att.error_code == "ATTACHMENT_TOO_LARGE"
    assert att.http_status == 413

    wh = WebhookDeliveryError("failed")
    assert wh.error_code == "WEBHOOK_DELIVERY_ERROR"
    assert wh.http_status == 502

    enf = EmailNotFoundError("gone")
    assert enf.error_code == "EMAIL_NOT_FOUND"
    assert enf.http_status == 404


def test_backward_compat_aliases():
    from app.core.exceptions import (
        DoesNotExistHandle,
        EWSGatewayError,
        EWSGatewayException,
        SettingNotFound,
        SettingNotFoundError,
        does_not_exist_handle,
    )

    assert EWSGatewayException is EWSGatewayError
    assert DoesNotExistHandle is does_not_exist_handle
    assert SettingNotFound is SettingNotFoundError
