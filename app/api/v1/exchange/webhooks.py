"""
Exchange Webhook 管理 API 路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, HTTPException

from app.core.dependency import AuthControl, DependPermission
from app.core.api_key_auth import OptionalApiKeyWebhook
from app.models import User, ExchangeApiKey
from app.schemas.base import Success, Fail
from app.schemas.webhook import WebhookCreate, WebhookUpdate, WebhookResponse
from app.services.exchange.webhook_service import get_webhook_service

router = APIRouter(dependencies=[DependPermission], tags=["Webhook 管理"])


async def get_current_actor(
    request: Request,
    current_user: Optional[User] = Depends(AuthControl.is_authed),
    api_key: Optional[ExchangeApiKey] = Depends(OptionalApiKeyWebhook),
) -> int:
    """
    获取当前操作者 ID
    
    支持:
    1. 管理后台用户 (JWT) -> 返回 user.id
    2. API Key (Webhook 权限) -> 返回 api_key.owner_id
    
    如果两者都没有，抛出 401
    """
    # 优先检查 API Key
    # OptionalApiKeyWebhook 已经验证了 key 的有效性和权限
    if api_key:
        request.state.current_api_key = api_key
        return api_key.owner_id
        
    # 如果 AuthControl 已经验证了 API Key (通过 header)，但 OptionalApiKeyWebhook 没拿到 (理论上不应该，除非 header 不同)
    # 但由于 AuthControl 和 ApiKeyAuth 都检查 X-Api-Key，如果 header 存在，两者都会尝试验证。
    # AuthControl 验证成功会设置 state.is_api_key_auth 和 state.api_key
    if getattr(request.state, "is_api_key_auth", False) and getattr(request.state, "api_key", None):
        key: ExchangeApiKey = request.state.api_key
        # Check permissions specifically if AuthControl let it through but OptionalApiKeyWebhook didn't run?
        # No, OptionalApiKeyWebhook runs as dependency.
        
        # Double check permission here just in case AuthControl logic bypassed ApiKeyAuth
        if "webhook" not in key.permissions:
             raise HTTPException(status_code=403, detail="缺少 webhook 权限")
             
        request.state.current_api_key = key
        return key.owner_id

    # 检查 JWT 用户
    if current_user:
        return current_user.id
        
    raise HTTPException(status_code=401, detail="未认证")


@router.get("/list", summary="获取 Webhook 列表")
async def list_webhooks(
    request: Request,
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
    account_id: Optional[int] = Query(None, description="筛选账户ID"),
    owner_id: int = Depends(get_current_actor),
):
    """
    获取 Webhook 订阅列表
    """
    # 如果是 API Key，检查 account_id 是否在 allowed_accounts
    api_key: Optional[ExchangeApiKey] = getattr(request.state, "current_api_key", None)
    if api_key and api_key.allowed_accounts:
        # 如果指定了 account_id，检查是否有权
        if account_id and account_id not in api_key.allowed_accounts:
             return Fail(code=403, msg="无权访问该账户")
        
        # 如果没指定，或者用于过滤，Service 层会处理 created_by=owner_id
        # 但 API Key 只能看到自己创建的？是的，owner_id 是 API Key 的 owner
    
    service = get_webhook_service()
    result = await service.list_webhooks(
        owner_id=owner_id,
        page=page,
        page_size=page_size,
        account_id=account_id
    )
    
    if result["success"]:
        return Success(data=result["items"], total=result["total"])
    else:
        return Fail(code=500, msg=result.get("message", "获取失败"))


@router.post("/create", summary="创建 Webhook")
async def create_webhook(
    request: Request,
    data: WebhookCreate,
    owner_id: int = Depends(get_current_actor),
):
    """
    创建 Webhook 订阅
    """
    # 如果是 API Key，检查权限
    api_key: Optional[ExchangeApiKey] = getattr(request.state, "current_api_key", None)
    if api_key and api_key.allowed_accounts:
        if data.account_id not in api_key.allowed_accounts:
            return Fail(code=403, msg="无权使用该邮箱账户")

    service = get_webhook_service()
    result = await service.create_webhook(
        data=data,
        owner_id=owner_id,
    )
    
    if result["success"]:
        return Success(msg=result["message"], data=result.get("data"))
    else:
        return Fail(code=400, msg=result["message"])


@router.post("/update", summary="更新 Webhook")
async def update_webhook(
    request: Request,
    data: WebhookUpdate,
    id: int = Query(..., description="Webhook ID"),
    owner_id: int = Depends(get_current_actor),
):
    """
    更新 Webhook 订阅
    """
    service = get_webhook_service()
    result = await service.update_webhook(
        webhook_id=id,
        data=data,
        owner_id=owner_id,
    )
    
    if result["success"]:
        return Success(msg=result["message"], data=result.get("data"))
    else:
        return Fail(code=400, msg=result["message"])


@router.delete("/delete", summary="删除 Webhook")
async def delete_webhook(
    request: Request,
    id: int = Query(..., description="Webhook ID"),
    owner_id: int = Depends(get_current_actor),
):
    """
    删除 Webhook 订阅
    """
    service = get_webhook_service()
    result = await service.delete_webhook(
        webhook_id=id,
        owner_id=owner_id,
    )
    
    if result["success"]:
        return Success(msg=result["message"])
    else:
        return Fail(code=400, msg=result["message"])


@router.post("/test/{id}", summary="触发测试事件")
async def test_webhook(
    request: Request,
    id: int,
    owner_id: int = Depends(get_current_actor),
):
    """
    触发 Webhook 测试事件
    """
    service = get_webhook_service()
    result = await service.trigger_test_event(
        webhook_id=id,
        owner_id=owner_id,
    )
    
    if result["success"]:
        return Success(msg="测试请求发送成功", data=result.get("data"))
    else:
        return Fail(code=400, msg=result["message"])
