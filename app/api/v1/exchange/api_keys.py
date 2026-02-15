"""
Exchange API 密钥管理路由
"""
from fastapi import APIRouter, Depends, Query

from app.core.dependency import AuthControl, DependPermission
from app.models import User
from app.schemas.base import Success, Fail
from app.schemas.exchange import ApiKeyCreate
from app.services.exchange import get_account_service

router = APIRouter(dependencies=[DependPermission])


@router.get("/list", summary="获取API密钥列表")
async def list_api_keys(
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    获取当前用户的API密钥列表
    """
    service = get_account_service()
    result = await service.list_api_keys(
        owner_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    
    if result["success"]:
        return Success(data=result["items"], total=result["total"])
    else:
        return Fail(code=500, msg=result.get("message", "获取失败"))


@router.post("/create", summary="创建API密钥")
async def create_api_key(
    data: ApiKeyCreate,
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    创建新的API密钥
    
    **注意：密钥只会显示一次，请妥善保存！**
    """
    service = get_account_service()
    result = await service.create_api_key(
        data=data,
        owner_id=current_user.id,
    )
    
    if result["success"]:
        return Success(msg=result["message"], data=result.get("data"))
    else:
        return Fail(code=400, msg=result["message"])


@router.post("/revoke", summary="撤销API密钥")
async def revoke_api_key(
    key_id: int = Query(..., description="密钥ID"),
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    撤销API密钥（禁用但不删除）
    """
    service = get_account_service()
    result = await service.revoke_api_key(
        key_id=key_id,
        owner_id=current_user.id,
    )
    
    if result["success"]:
        return Success(msg=result["message"])
    else:
        return Fail(code=400, msg=result["message"])


@router.delete("/delete", summary="删除API密钥")
async def delete_api_key(
    key_id: int = Query(..., description="密钥ID"),
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    永久删除API密钥
    """
    service = get_account_service()
    result = await service.delete_api_key(
        key_id=key_id,
        owner_id=current_user.id,
    )
    
    if result["success"]:
        return Success(msg=result["message"])
    else:
        return Fail(code=400, msg=result["message"])


@router.get("/stats", summary="获取使用统计")
async def get_usage_stats(
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    获取邮件服务使用统计
    """
    service = get_account_service()
    result = await service.get_usage_stats(
        owner_id=current_user.id,
    )
    
    if result["success"]:
        return Success(data=result["stats"])
    else:
        return Fail(code=500, msg=result.get("message", "获取失败"))


@router.get("/logs", summary="获取邮件日志")
async def list_mail_logs(
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
    action: str = Query(None, description="操作类型"),
    status: str = Query(None, description="状态"),
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    获取邮件操作日志
    """
    service = get_account_service()
    result = await service.list_mail_logs(
        owner_id=current_user.id,
        page=page,
        page_size=page_size,
        action=action,
        status=status,
    )
    
    if result["success"]:
        return Success(data=result["items"], total=result["total"])
    else:
        return Fail(code=500, msg=result.get("message", "获取失败"))
