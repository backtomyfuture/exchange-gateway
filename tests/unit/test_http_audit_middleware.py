import pytest


@pytest.mark.asyncio
async def test_http_audit_log_stores_metadata_without_bodies(client):
    from app.models.admin import AuditLog

    request_id = "audit-test-request-id"
    response = await client.get(
        "/api/v1/base/userinfo",
        headers={"token": "dev", "X-Request-ID": request_id},
    )

    assert response.status_code == 200
    audit_log = await AuditLog.filter(path="/api/v1/base/userinfo").order_by("-id").first()
    assert audit_log is not None
    assert audit_log.request_id == request_id
    assert audit_log.request_args is None
    assert audit_log.response_body is None
