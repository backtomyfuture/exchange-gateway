from app.core.exceptions import (
    AccountNotFoundError, ExchangeConnectionError, EWSGatewayException
)


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
