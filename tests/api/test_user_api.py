import pytest


@pytest.mark.asyncio
async def test_list_users(client, superuser_token):
    resp = await client.get(
        "/api/v1/user/list",
        headers={"token": superuser_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_user_info(client, superuser_token):
    resp = await client.get(
        "/api/v1/base/userinfo",
        headers={"token": superuser_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert data["data"]["username"] == "admin"


@pytest.mark.asyncio
async def test_create_user(client, superuser_token):
    resp = await client.post(
        "/api/v1/user/create",
        headers={"token": superuser_token},
        json={
            "username": "api_test_user",
            "email": "api_test_user@test.com",
            "password": "testpass123",
            "is_active": True,
            "is_superuser": False,
            "role_ids": [],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
