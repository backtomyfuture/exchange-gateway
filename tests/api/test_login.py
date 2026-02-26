import pytest


@pytest.mark.asyncio
async def test_login_success(client):
    resp = await client.post(
        "/api/v1/base/access_token",
        json={"username": "admin", "password": "123456"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert "access_token" in data["data"]
    assert data["data"]["username"] == "admin"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post(
        "/api/v1/base/access_token",
        json={"username": "admin", "password": "wrong_password"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    resp = await client.post(
        "/api/v1/base/access_token",
        json={"username": "nonexistent_user", "password": "whatever"},
    )
    assert resp.status_code == 400
