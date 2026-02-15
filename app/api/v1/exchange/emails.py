"""
Exchange 邮件 API 路由
"""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.encoders import jsonable_encoder

from app.core.api_key_auth import (
    ApiKeyAuth,
    DependApiKeySend,
    DependApiKeyReceive,
    DependApiKeySearch,
    DependApiKeyDelete,
    DependApiKeyFolders,
    DependApiKeyDrafts,
    DependApiKeySync,
    DependApiKeyRead,
    get_client_ip,
    DependApiKeyReply,
    DependApiKeyForward,
)
from app.models.exchange import ExchangeApiKey
from app.schemas.base import Success, Fail
from app.schemas.exchange import (
    EmailSendRequest,
    EmailDraftRequest,
    EmailSendResponse,
    EmailListRequest,
    EmailSearchRequest,
    TemplateSendRequest,
    EmailSyncRequest,
    EmailReplyRequest,
    EmailForwardRequest,
)
from app.services.exchange import get_email_service, get_template_service

from app.core.dependency import AuthControl, DependPermission


router = APIRouter(dependencies=[DependPermission])





@router.post("/send", summary="发送邮件")
async def send_email(
    request: Request,
    data: EmailSendRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeySend),
):
    """
    发送邮件
    
    需要 `send` 权限
    """
    # 验证账户权限
    if api_key.allowed_accounts and data.account_id not in api_key.allowed_accounts:
        return Fail(code=403, msg="无权使用该邮箱账户")
    
    service = get_email_service()
    result = await service.send_email(
        request=data,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )
    
    if result["success"]:
        return Success(msg=result["message"], data={"log_id": result.get("log_id")})
    else:
        return Fail(code=500, msg=result["message"])


@router.post("/drafts", summary="创建草稿")
async def create_draft(
    request: Request,
    data: EmailDraftRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeyDrafts),
):
    """
    创建草稿
    
    需要 `drafts` 权限
    """
    if api_key.allowed_accounts and data.account_id not in api_key.allowed_accounts:
        return Fail(code=403, msg="无权使用该邮箱账户")
    
    service = get_email_service()
    result = await service.create_draft(
        request=data,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )
    
    if result["success"]:
        return Success(msg=result["message"], data=result)
    else:
        return Fail(code=500, msg=result["message"])


@router.post("/reply", summary="回复邮件")
async def reply_email(
    request: Request,
    data: EmailReplyRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeyReply),
):
    """
    回复邮件
    
    需要 `reply` 权限
    """
    if api_key.allowed_accounts and data.account_id not in api_key.allowed_accounts:
        return Fail(code=403, msg="无权使用该邮箱账户")
    
    service = get_email_service()
    result = await service.reply_email(
        request=data,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )
    
    if result["success"]:
        return Success(msg=result["message"])
    else:
        return Fail(code=500, msg=result["message"])


@router.post("/forward", summary="转发邮件")
async def forward_email(
    request: Request,
    data: EmailForwardRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeyForward),
):
    """
    转发邮件
    
    需要 `forward` 权限
    """
    if api_key.allowed_accounts and data.account_id not in api_key.allowed_accounts:
        return Fail(code=403, msg="无权使用该邮箱账户")
    
    service = get_email_service()
    result = await service.forward_email(
        request=data,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )
    
    if result["success"]:
        return Success(msg=result["message"])
    else:
        return Fail(code=500, msg=result["message"])


@router.post("/send-template", summary="按模板发送邮件")
async def send_email_from_template(
    request: Request,
    data: TemplateSendRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeySend),
):
    """
    使用模板发送邮件
    
    需要 `send` 权限
    """
    # 验证账户权限
    if api_key.allowed_accounts and data.account_id not in api_key.allowed_accounts:
        return Fail(code=403, msg="无权使用该邮箱账户")
    
    # 获取模板（支持 id 或 name）
    template_service = get_template_service()
    template = None
    
    if data.template_id:
        template = await template_service.get_template_for_send(data.template_id)
    elif data.template_name:
        template = await template_service.get_template_by_name(data.template_name)
    else:
        return Fail(code=400, msg="必须提供 template_id 或 template_name")
    
    if not template:
        return Fail(code=404, msg="模板不存在或已禁用")
    
    # 替换变量
    subject = template_service._replace_variables(template.subject, data.variables)
    body = template_service._replace_variables(template.body, data.variables)
    
    # 构建发送请求
    send_request = EmailSendRequest(
        account_id=data.account_id,
        to=data.to,
        subject=subject,
        body=body,
        body_type=template.body_type,
        cc=data.cc,
        bcc=data.bcc,
        attachments=data.attachments,
    )
    
    # 发送邮件
    email_service = get_email_service()
    result = await email_service.send_email(
        request=send_request,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )
    
    if result["success"]:
        return Success(
            msg=result["message"],
            data={
                "log_id": result.get("log_id"),
                "template_id": template.id,
                "template_name": template.name,
            }
        )
    else:
        return Fail(code=500, msg=result["message"])


@router.get("/list", summary="获取邮件列表")
async def list_emails(
    request: Request,
    account_id: int = Query(..., description="账户ID"),
    folder: str = Query("INBOX", description="文件夹"),
    limit: int = Query(20, ge=1, le=100, description="数量"),
    offset: int = Query(0, ge=0, description="偏移"),
    unread_only: bool = Query(False, description="仅未读"),
    api_key: ExchangeApiKey = Depends(DependApiKeyReceive),
):
    """
    获取邮件列表
    
    需要 `receive` 权限
    """
    if api_key.allowed_accounts and account_id not in api_key.allowed_accounts:
        return Fail(code=403, msg="无权使用该邮箱账户")
    
    service = get_email_service()
    result = await service.list_emails(
        request=EmailListRequest(
            account_id=account_id,
            folder=folder,
            limit=limit,
            offset=offset,
            unread_only=unread_only,
        ),
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )
    
    if result["success"]:
        return Success(data={
            "total": result["total"],
            "items": [item.model_dump(mode="json") for item in result["items"]],
        })
    else:
        return Fail(code=500, msg=result.get("message", "获取失败"))


@router.get("/folders/all", summary="获取所有文件夹")
async def get_all_folders(
    account_id: int = Query(..., description="账户ID"),
    api_key: ExchangeApiKey = Depends(DependApiKeyFolders),
):
    """
    获取账户下所有文件夹（包括标准和自定义）
    返回扁平列表，包含 id, changekey, parent_id 等信息。
    
    需要 `folders` 权限
    """
    if api_key.allowed_accounts and account_id not in api_key.allowed_accounts:
        return Fail(code=403, msg="无权使用该邮箱账户")
    
    service = get_email_service()
    result = await service.get_all_folders(
        account_id=account_id,
        api_key_id=api_key.id,
    )
    
    if result["success"]:
        return Success(data={
            "folders": [f.model_dump() for f in result["folders"]],
        })
    else:
        return Fail(code=500, msg=result.get("message", "获取失败"))


@router.get("/folders/list", summary="获取文件夹列表")
async def list_folders(
    account_id: int = Query(..., description="账户ID"),
    api_key: ExchangeApiKey = Depends(DependApiKeyFolders),
):
    """
    [Legacy] 获取常用文件夹列表 (Inbox, Sent, Drafts, Trash)
    
    需要 `folders` 权限
    """
    if api_key.allowed_accounts and account_id not in api_key.allowed_accounts:
        return Fail(code=403, msg="无权使用该邮箱账户")
    
    return Fail(code=501, msg="此接口正在维护，请使用 /folders/all")


@router.get("/{email_id:path}", summary="获取邮件详情")
async def get_email(
    email_id: str,
    account_id: int = Query(..., description="账户ID"),
    api_key: ExchangeApiKey = Depends(DependApiKeyReceive),
):
    """
    获取邮件详情
    
    需要 `receive` 权限
    """
    if api_key.allowed_accounts and account_id not in api_key.allowed_accounts:
        return Fail(code=403, msg="无权使用该邮箱账户")
    
    service = get_email_service()
    result = await service.get_email(
        account_id=account_id,
        email_id=email_id,
        api_key_id=api_key.id,
    )
    
    if result["success"]:
        return Success(data=result["data"])
    else:
        return Fail(code=404, msg=result.get("message", "邮件不存在"))


@router.put("/{email_id:path}/read", summary="标记邮件已读")
async def mark_email_read(
    request: Request,
    email_id: str,
    account_id: int = Query(..., description="账户ID"),
    is_read: bool = Query(True, description="是否已读"),
    api_key: ExchangeApiKey = Depends(DependApiKeyRead),
):
    """
    标记邮件已读/未读
    
    需要 `receive` 权限
    """
    if api_key.allowed_accounts and account_id not in api_key.allowed_accounts:
        return Fail(code=403, msg="无权使用该邮箱账户")
    
    service = get_email_service()
    result = await service.mark_as_read(
        account_id=account_id,
        email_id=email_id,
        is_read=is_read,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )
    
    if result["success"]:
        return Success(msg=result["message"])
    else:
        return Fail(code=500, msg=result["message"])


@router.delete("/{email_id:path}", summary="删除邮件")
async def delete_email(
    request: Request,
    email_id: str,
    account_id: int = Query(..., description="账户ID"),
    api_key: ExchangeApiKey = Depends(DependApiKeyDelete),
):
    """
    删除邮件
    
    需要 `delete` 权限
    """
    if api_key.allowed_accounts and account_id not in api_key.allowed_accounts:
        return Fail(code=403, msg="无权使用该邮箱账户")
    
    service = get_email_service()
    result = await service.delete_email(
        account_id=account_id,
        email_id=email_id,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )
    
    if result["success"]:
        return Success(msg=result["message"])
    else:
        return Fail(code=500, msg=result["message"])


@router.post("/search", summary="搜索邮件")
async def search_emails(
    data: EmailSearchRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeySearch),
):
    """
    搜索邮件
    
    需要 `search` 权限
    """
    if api_key.allowed_accounts and data.account_id not in api_key.allowed_accounts:
        return Fail(code=403, msg="无权使用该邮箱账户")
    
    service = get_email_service()
    result = await service.search_emails(
        request=data,
        api_key_id=api_key.id,
    )
    
    if result["success"]:
        return Success(data={
            "total": result["total"],
            "items": [item.model_dump(mode="json") for item in result["items"]],
        })
    else:
        return Fail(code=500, msg=result.get("message", "搜索失败"))


@router.post("/sync", summary="同步邮件")
async def sync_emails(
    request: Request,
    data: EmailSyncRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeySync),
):
    """
    同步邮件
    
    获取自上次同步以来的增量变化。
    返回 changes (create, update, delete) 和新的 sync_state。
    
    需要 `receive` 权限
    """
    if api_key.allowed_accounts and data.account_id not in api_key.allowed_accounts:
        return Fail(code=403, msg="无权使用该邮箱账户")
    
    service = get_email_service()
    result = await service.sync_emails(
        request=data,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )
    
    if result["success"]:
        # 注意: items 列表里的 item 需要再 dump 一次，因为 Pydantic 嵌套模型处理
        # 使用 jsonable_encoder 处理 datetime 对象
        return Success(data=jsonable_encoder({
            "sync_state": result["sync_state"],
            "items": result["items"], # List of dicts matching EmailSyncItem
        }))
    else:
        return Fail(code=500, msg=result.get("message", "同步失败"))



pass


