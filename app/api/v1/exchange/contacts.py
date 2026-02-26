from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.api_key_auth import DependApiKeyContact
from app.models.exchange import ExchangeApiKey
from app.services.exchange.contact_service import ContactService, get_contact_service

router = APIRouter()


class ContactInfo(BaseModel):
    name: str
    email: str
    mailbox_type: str | None = None
    item_id: str | None = None


class ContactResolveResponse(BaseModel):
    success: bool
    data: list[ContactInfo]
    message: str | None = None


@router.get("/resolve", response_model=ContactResolveResponse, summary="查找联系人")
async def resolve_contact(
    q: str = Query(..., description="查询关键词 (姓名或邮箱)"),
    account_id: int = Query(..., description="使用的账户ID"),
    service: ContactService = Depends(get_contact_service),
    api_key: ExchangeApiKey = Depends(DependApiKeyContact),
):
    """
    查找联系人 (GAL)

    需要 `contacts` 权限
    """
    # 验证账户权限
    if api_key.allowed_accounts and account_id not in api_key.allowed_accounts:
        raise HTTPException(status_code=403, detail="无权使用该邮箱账户")
    contacts = await service.resolve_names(q, account_id)
    return {"success": True, "data": contacts, "message": "查询成功"}
