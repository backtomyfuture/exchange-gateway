import pytest


@pytest.mark.asyncio
async def test_list_menus(client, superuser_token):
    resp = await client.get(
        "/api/v1/menu/list",
        headers={"token": superuser_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1
