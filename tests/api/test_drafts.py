import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.models.exchange import ExchangeApiKey
from app.utils.crypto import hash_api_key

@pytest.mark.asyncio
async def test_create_draft_success(client):
    from app.models.admin import User
    user = await User.create(username="test_owner", password="pwd", email="owner@test.com")

    # Setup API Key
    raw_key = "test_draft_key_secret"
    await ExchangeApiKey.create(
        name="Test Draft Key",
        key_hash=hash_api_key(raw_key),
        key_prefix=raw_key[:8],
        owner_id=user.id,
        permissions=["drafts"],
        is_active=True
    )

    # Mock Service
    with patch("app.api.v1.exchange.emails.get_email_service") as mock_svc_cls:
        mock_service = MagicMock()
        mock_svc_cls.return_value = mock_service
        mock_service.create_draft = AsyncMock(return_value={
            "success": True,
            "message": "Draft created",
            "id": "draft_123",
            "changekey": "ckpt_123"
        })

        # Call API
        response = await client.post(
            "/api/v1/exchange/emails/drafts",
            json={
                "account_id": 1,
                "to": ["test@example.com"],
                "subject": "Test Draft",
                "body": "Body content"
            },
            headers={"X-API-KEY": raw_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["id"] == "draft_123"
        
        # Verify service called correctly
        mock_service.create_draft.assert_called_once()
        call_args = mock_service.create_draft.call_args
        request_obj = call_args.kwargs["request"]
        assert request_obj.subject == "Test Draft"
        assert request_obj.body == "Body content"

@pytest.mark.asyncio
async def test_create_draft_forbidden(client):
    from app.models.admin import User
    # Check if user exists or create new
    user = await User.filter(username="test_owner").first()
    if not user:
        user = await User.create(username="test_owner", password="pwd", email="owner@test.com")
        
    # Setup API Key WITHOUT drafts permission
    raw_key = "test_no_perm_key"
    await ExchangeApiKey.create(
        name="No Perm Key",
        key_hash=hash_api_key(raw_key),
        key_prefix=raw_key[:8],
        owner_id=user.id,
        permissions=["send"], # Only send, not drafts
        is_active=True
    )

    response = await client.post(
        "/api/v1/exchange/emails/drafts",
        json={
            "account_id": 1,
            "subject": "Test"
        },
        headers={"X-API-KEY": raw_key}
    )
    
    # ApiKeyAuth raises 403 if permission missing
    assert response.status_code == 403
    data = response.json()
    # It might vary depending on exception handlers (detail for HTTPException, msg for custom Fail response)
    message = data.get("detail") or data.get("msg") or str(data)
    assert "权限" in message or "Forbidden" in message
