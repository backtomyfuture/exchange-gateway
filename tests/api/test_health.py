import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_health_200_when_all_ok(client, init_test_db):
    with patch("app.api.v1.health.health._check_redis", new_callable=AsyncMock) as mr:
        mr.return_value = {"status": "ok", "latency_ms": 1}
        response = await client.get("/health")
    assert response.status_code in (200, 207)
    data = response.json()["data"]
    assert "checks" in data
    assert "database" in data["checks"]


@pytest.mark.asyncio
async def test_health_503_when_db_down(client, init_test_db):
    with patch("app.api.v1.health.health._check_database", new_callable=AsyncMock) as md:
        md.return_value = {"status": "error", "error": "refused"}
        with patch("app.api.v1.health.health._check_redis", new_callable=AsyncMock) as mr:
            mr.return_value = {"status": "ok", "latency_ms": 1}
            response = await client.get("/health")
    assert response.status_code == 503
