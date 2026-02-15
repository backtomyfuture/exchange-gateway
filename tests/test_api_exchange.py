"""
Exchange API 路由集成测试
测试账户、API Key、邮件和模板相关的 API 端点
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime


# ========================================
# 账户管理 API 测试
# ========================================

@pytest.mark.asyncio
async def test_list_accounts_superuser(client, superuser_token):
    """测试超管获取账户列表"""
    with patch("app.api.v1.exchange.accounts.get_account_service") as mock_svc:
        mock_service = MagicMock()
        mock_svc.return_value = mock_service
        mock_service.list_accounts = AsyncMock(return_value={
            "success": True,
            "total": 2,
            "items": [
                {"id": 1, "email": "a@test.com", "is_active": True},
                {"id": 2, "email": "b@test.com", "is_active": True},
            ]
        })
        
        response = await client.get(
            "/api/v1/exchange/accounts/list",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200


@pytest.mark.asyncio
async def test_create_account(client, superuser_token):
    """测试创建账户"""
    with patch("app.api.v1.exchange.accounts.get_account_service") as mock_svc:
        mock_service = MagicMock()
        mock_svc.return_value = mock_service
        mock_service.create_account = AsyncMock(return_value={
            "success": True,
            "message": "创建成功",
            "data": {"id": 1}
        })
        
        response = await client.post(
            "/api/v1/exchange/accounts/create",
            json={
                "email": "new@test.com",
                "username": "newuser",
                "password": "secret123"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200


@pytest.mark.asyncio  
async def test_update_account(client, superuser_token):
    """测试更新账户"""
    with patch("app.api.v1.exchange.accounts.get_account_service") as mock_svc:
        mock_service = MagicMock()
        mock_svc.return_value = mock_service
        mock_service.update_account = AsyncMock(return_value={
            "success": True,
            "message": "更新成功"
        })
        
        response = await client.post(
            "/api/v1/exchange/accounts/update",
            json={"id": 1, "display_name": "New Name"},
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_account(client, superuser_token):
    """测试删除账户"""
    with patch("app.api.v1.exchange.accounts.get_account_service") as mock_svc:
        mock_service = MagicMock()
        mock_svc.return_value = mock_service
        mock_service.delete_account = AsyncMock(return_value={
            "success": True,
            "message": "删除成功"
        })
        
        response = await client.delete(
            "/api/v1/exchange/accounts/delete?account_id=1",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_test_account_connection(client, superuser_token):
    """测试账户连接测试"""
    with patch("app.api.v1.exchange.accounts.get_account_service") as mock_svc:
        mock_service = MagicMock()
        mock_svc.return_value = mock_service
        mock_service.test_account = AsyncMock(return_value={
            "success": True,
            "message": "连接成功"
        })
        
        response = await client.post(
            "/api/v1/exchange/accounts/test?account_id=1",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200


# ========================================
# API Key 管理测试
# ========================================

@pytest.mark.asyncio
async def test_list_api_keys(client, superuser_token):
    """测试获取 API Key 列表"""
    with patch("app.api.v1.exchange.api_keys.get_account_service") as mock_svc:
        mock_service = MagicMock()
        mock_svc.return_value = mock_service
        mock_service.list_api_keys = AsyncMock(return_value={
            "success": True,
            "total": 1,
            "items": [
                {"id": 1, "name": "Test Key", "key_prefix": "abc123", "is_active": True}
            ]
        })
        
        response = await client.get(
            "/api/v1/exchange/api-keys/list",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_api_key(client, superuser_token):
    """测试创建 API Key"""
    with patch("app.api.v1.exchange.api_keys.get_account_service") as mock_svc:
        mock_service = MagicMock()
        mock_svc.return_value = mock_service
        mock_service.create_api_key = AsyncMock(return_value={
            "success": True,
            "api_key": "full_key_value_xxx",
            "id": 1,
            "message": "创建成功"
        })
        
        response = await client.post(
            "/api/v1/exchange/api-keys/create",
            json={
                "name": "New Key",
                "permissions": ["send"],
                "allowed_accounts": [1]
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_revoke_api_key(client, superuser_token):
    """测试撤销 API Key"""
    with patch("app.api.v1.exchange.api_keys.get_account_service") as mock_svc:
        mock_service = MagicMock()
        mock_svc.return_value = mock_service
        mock_service.revoke_api_key = AsyncMock(return_value={
            "success": True,
            "message": "撤销成功"
        })
        
        response = await client.post(
            "/api/v1/exchange/api-keys/revoke?key_id=1",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200


# ========================================
# 模板管理 API 测试
# ========================================

@pytest.mark.asyncio
async def test_list_templates(client, superuser_token):
    """测试获取模板列表"""
    with patch("app.api.v1.exchange.templates.get_template_service") as mock_svc:
        mock_service = MagicMock()
        mock_svc.return_value = mock_service
        mock_service.list_templates = AsyncMock(return_value={
            "success": True,
            "total": 1,
            "items": [
                {"id": 1, "name": "Welcome", "is_active": True}
            ]
        })
        
        response = await client.get(
            "/api/v1/exchange/templates/list",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_template(client, superuser_token):
    """测试创建模板"""
    with patch("app.api.v1.exchange.templates.get_template_service") as mock_svc:
        mock_service = MagicMock()
        mock_svc.return_value = mock_service
        mock_service.create_template = AsyncMock(return_value={
            "success": True,
            "id": 1,
            "message": "创建成功"
        })
        
        response = await client.post(
            "/api/v1/exchange/templates/create",
            json={
                "name": "New Template",
                "subject": "Subject {{name}}",
                "body": "Body {{name}}",
                "body_type": "html"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_preview_template(client, superuser_token):
    """测试模板预览"""
    with patch("app.api.v1.exchange.templates.get_template_service") as mock_svc:
        mock_service = MagicMock()
        mock_svc.return_value = mock_service
        mock_service.preview_template = AsyncMock(return_value={
            "success": True,
            "data": {
                "subject": "Hello 张三",
                "body": "Welcome 张三"
            }
        })
        
        response = await client.post(
            "/api/v1/exchange/templates/preview?template_id=1",
            json={"name": "张三"},
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200


# ========================================
# 健康检查 API 测试
# ========================================

@pytest.mark.asyncio
async def test_health_check(client):
    """测试健康检查端点（无需认证）"""
    response = await client.get("/api/v1/exchange/health")
    
    assert response.status_code == 200
    data = response.json()
    # 健康检查应该返回成功状态
    assert data.get("code") == 200 or "status" in data
