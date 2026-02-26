from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.api_key_auth import get_client_ip, verify_account_access


def _make_request(headers=None, client_host="127.0.0.1"):
    request = MagicMock()
    request.headers = headers or {}
    client = MagicMock()
    client.host = client_host
    request.client = client
    return request


def test_get_client_ip_forwarded():
    request = _make_request(headers={"X-Forwarded-For": "10.0.0.1, 10.0.0.2"})
    assert get_client_ip(request) == "10.0.0.1"


def test_get_client_ip_real_ip():
    request = _make_request(headers={"X-Real-IP": "192.168.1.1"})
    assert get_client_ip(request) == "192.168.1.1"


def test_get_client_ip_direct():
    request = _make_request(client_host="172.16.0.1")
    assert get_client_ip(request) == "172.16.0.1"


def test_verify_account_access_allowed():
    api_key = MagicMock()
    api_key.allowed_accounts = []
    verify_account_access(api_key, account_id=42)


def test_verify_account_access_denied():
    api_key = MagicMock()
    api_key.allowed_accounts = [1, 2, 3]
    with pytest.raises(HTTPException) as exc_info:
        verify_account_access(api_key, account_id=42)
    assert exc_info.value.status_code == 403
