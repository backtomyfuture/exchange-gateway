"""
Exchange 账户管理 API 路由
管理后台用户管理自己的邮箱账户
"""

from fastapi import APIRouter, Depends, Query

from app.core.dependency import AuthControl, DependPermission
from app.models import User
from app.schemas.base import Fail, Success
from app.schemas.exchange import AccountCreate, AccountUpdate
from app.services.exchange import get_account_service

router = APIRouter(dependencies=[DependPermission])


@router.get("/dashboard", summary="获取仪表盘数据")
async def get_dashboard_data(
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    获取仪表盘统计数据
    """
    service = get_account_service()
    result = await service.get_dashboard_data(
        owner_id=current_user.id,
    )

    if result["success"]:
        return Success(data=result["data"])
    else:
        return Fail(code=500, msg=result.get("message", "获取失败"))


@router.get("/list", summary="获取账户列表")
async def list_accounts(
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    获取当前用户的邮箱账户列表
    """
    service = get_account_service()
    result = await service.list_accounts(
        owner_id=current_user.id,
        page=page,
        page_size=page_size,
    )

    if result["success"]:
        return Success(data=result["items"], total=result["total"])
    else:
        return Fail(code=500, msg=result.get("message", "获取失败"))


@router.post("/create", summary="创建邮箱账户")
async def create_account(
    data: AccountCreate,
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    创建新的邮箱账户
    """
    service = get_account_service()
    result = await service.create_account(
        data=data,
        owner_id=current_user.id,
    )

    if result["success"]:
        return Success(msg=result["message"], data=result.get("data"))
    else:
        return Fail(code=400, msg=result["message"])


@router.post("/update", summary="更新邮箱账户")
async def update_account(
    data: AccountUpdate,
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    更新邮箱账户信息
    """
    service = get_account_service()
    result = await service.update_account(
        data=data,
        owner_id=current_user.id,
    )

    if result["success"]:
        return Success(msg=result["message"], data=result.get("data"))
    else:
        return Fail(code=400, msg=result["message"])


@router.delete("/delete", summary="删除邮箱账户")
async def delete_account(
    account_id: int = Query(..., description="账户ID"),
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    删除邮箱账户
    """
    service = get_account_service()
    result = await service.delete_account(
        account_id=account_id,
        owner_id=current_user.id,
    )

    if result["success"]:
        return Success(msg=result["message"])
    else:
        return Fail(code=400, msg=result["message"])


@router.post("/test", summary="测试账户连接")
async def test_account(
    account_id: int = Query(..., description="账户ID"),
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    测试邮箱账户连接是否正常
    """
    service = get_account_service()
    result = await service.test_account(
        account_id=account_id,
        owner_id=current_user.id,
    )

    if result["success"]:
        return Success(msg=result["message"])
    else:
        return Fail(code=400, msg=result["message"])
