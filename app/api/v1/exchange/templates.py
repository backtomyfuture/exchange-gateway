"""
Exchange 邮件模板 API 路由
"""

from fastapi import APIRouter, Depends, Query

from app.core.dependency import AuthControl, DependPermission
from app.models import User
from app.schemas.base import Fail, Success
from app.schemas.exchange import TemplateCreate, TemplateUpdate
from app.services.exchange import get_template_service

router = APIRouter(dependencies=[DependPermission])


@router.get("/list", summary="获取模板列表")
async def list_templates(
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
    category: str = Query(None, description="分类筛选"),
    active_only: bool = Query(False, description="仅显示启用的"),
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    获取当前用户的邮件模板列表
    """
    service = get_template_service()
    result = await service.list_templates(
        owner_id=current_user.id,
        page=page,
        page_size=page_size,
        category=category,
        active_only=active_only,
    )

    if result["success"]:
        return Success(data=result["items"], total=result["total"])
    else:
        return Fail(code=500, msg=result.get("message", "获取失败"))


@router.get("/get", summary="获取模板详情")
async def get_template(
    template_id: int = Query(..., description="模板ID"),
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    获取单个模板详情
    """
    service = get_template_service()
    result = await service.get_template(
        template_id=template_id,
        owner_id=current_user.id,
    )

    if result["success"]:
        return Success(data=result["data"])
    else:
        return Fail(code=404, msg=result.get("message", "模板不存在"))


@router.post("/create", summary="创建模板")
async def create_template(
    data: TemplateCreate,
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    创建新的邮件模板
    """
    service = get_template_service()
    result = await service.create_template(
        data=data,
        owner_id=current_user.id,
    )

    if result["success"]:
        return Success(msg=result["message"], data=result.get("data"))
    else:
        return Fail(code=400, msg=result["message"])


@router.post("/update", summary="更新模板")
async def update_template(
    data: TemplateUpdate,
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    更新邮件模板
    """
    service = get_template_service()
    result = await service.update_template(
        data=data,
        owner_id=current_user.id,
    )

    if result["success"]:
        return Success(msg=result["message"], data=result.get("data"))
    else:
        return Fail(code=400, msg=result["message"])


@router.delete("/delete", summary="删除模板")
async def delete_template(
    template_id: int = Query(..., description="模板ID"),
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    删除邮件模板
    """
    service = get_template_service()
    result = await service.delete_template(
        template_id=template_id,
        owner_id=current_user.id,
    )

    if result["success"]:
        return Success(msg=result["message"])
    else:
        return Fail(code=400, msg=result["message"])


@router.post("/preview", summary="预览模板")
async def preview_template(
    template_id: int = Query(..., description="模板ID"),
    variables: dict = None,
    current_user: User = Depends(AuthControl.is_authed),
):
    """
    预览模板（变量替换后）
    """
    service = get_template_service()
    result = await service.preview_template(
        template_id=template_id,
        owner_id=current_user.id,
        variables=variables or {},
    )

    if result["success"]:
        return Success(data=result["data"])
    else:
        return Fail(code=400, msg=result["message"])
