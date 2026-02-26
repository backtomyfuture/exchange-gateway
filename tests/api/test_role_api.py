import pytest


@pytest.mark.asyncio
async def test_list_roles(client, superuser_token):
    resp = await client.get(
        "/api/v1/role/list",
        headers={"token": superuser_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_create_role(client, superuser_token):
    resp = await client.post(
        "/api/v1/role/create",
        headers={"token": superuser_token},
        json={"name": "测试角色_api", "desc": "API test role"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
