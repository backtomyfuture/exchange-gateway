"""
Exchange email API routes.
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
    verify_account_access,
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


@router.post("/send", summary="Send email")
async def send_email(
    request: Request,
    data: EmailSendRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeySend),
):
    """
    Send an email via the specified Exchange account.

    Requires the `send` permission.  The message is queued as a background
    task and this endpoint returns immediately with a ``log_id`` that can be
    used to track delivery status.
    """
    verify_account_access(api_key, data.account_id)

    service = get_email_service()
    result = await service.send_email(
        request=data,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )

    if result["success"]:
        return Success(msg=result["message"], data={"log_id": result.get("log_id")})
    return Fail(code=500, msg=result["message"])


@router.post("/drafts", summary="Create draft")
async def create_draft(
    request: Request,
    data: EmailDraftRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeyDrafts),
):
    """
    Save an email as a draft in the Drafts folder.

    Requires the `drafts` permission.
    """
    verify_account_access(api_key, data.account_id)

    service = get_email_service()
    result = await service.create_draft(
        request=data,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )

    if result["success"]:
        return Success(msg=result["message"], data=result)
    return Fail(code=500, msg=result["message"])


@router.post("/reply", summary="Reply to email")
async def reply_email(
    request: Request,
    data: EmailReplyRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeyReply),
):
    """
    Reply to an existing email.

    Requires the `reply` permission.
    """
    verify_account_access(api_key, data.account_id)

    service = get_email_service()
    result = await service.reply_email(
        request=data,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )

    if result["success"]:
        return Success(msg=result["message"])
    return Fail(code=500, msg=result["message"])


@router.post("/forward", summary="Forward email")
async def forward_email(
    request: Request,
    data: EmailForwardRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeyForward),
):
    """
    Forward an existing email to new recipients.

    Requires the `forward` permission.
    """
    verify_account_access(api_key, data.account_id)

    service = get_email_service()
    result = await service.forward_email(
        request=data,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )

    if result["success"]:
        return Success(msg=result["message"])
    return Fail(code=500, msg=result["message"])


@router.post("/send-template", summary="Send email from template")
async def send_email_from_template(
    request: Request,
    data: TemplateSendRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeySend),
):
    """
    Render a template with caller-supplied variables and send the result.

    Requires the `send` permission.  Supply either ``template_id`` or
    ``template_name`` to identify the template.
    """
    verify_account_access(api_key, data.account_id)

    if not data.template_id and not data.template_name:
        return Fail(code=400, msg="Provide either template_id or template_name")

    template_service = get_template_service()
    template = None

    if data.template_id:
        template = await template_service.get_template_for_send(data.template_id)
    else:
        template = await template_service.get_template_by_name(data.template_name)

    if not template:
        return Fail(code=404, msg="Template not found or disabled")

    subject = template_service._replace_variables(template.subject, data.variables)
    body = template_service._replace_variables(template.body, data.variables)

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
            },
        )
    return Fail(code=500, msg=result["message"])


@router.get("/list", summary="List emails")
async def list_emails(
    request: Request,
    account_id: int = Query(..., description="Account ID"),
    folder: str = Query("INBOX", description="Folder name (INBOX, SENT, DRAFTS, TRASH, or custom)"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    unread_only: bool = Query(False, description="Return only unread messages"),
    api_key: ExchangeApiKey = Depends(DependApiKeyReceive),
):
    """
    Return a paginated list of emails from the specified folder.

    Requires the `receive` permission.
    """
    verify_account_access(api_key, account_id)

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
        return Success(
            data={
                "total": result["total"],
                "items": [item.model_dump(mode="json") for item in result["items"]],
            }
        )
    return Fail(code=500, msg=result.get("message", "Failed to list emails"))


@router.get("/folders/all", summary="List all folders")
async def get_all_folders(
    request: Request,
    account_id: int = Query(..., description="Account ID"),
    api_key: ExchangeApiKey = Depends(DependApiKeyFolders),
):
    """
    Return all folders (standard and custom) for the account as a flat list.

    Each entry includes ``id``, ``changekey``, ``parent_id``, counts, etc.
    Requires the `folders` permission.
    """
    verify_account_access(api_key, account_id)

    service = get_email_service()
    result = await service.get_all_folders(
        account_id=account_id,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )

    if result["success"]:
        return Success(data={"folders": [f.model_dump() for f in result["folders"]]})
    return Fail(code=500, msg=result.get("message", "Failed to list folders"))


@router.get("/{email_id:path}", summary="Get email detail")
async def get_email(
    email_id: str,
    account_id: int = Query(..., description="Account ID"),
    folder: str = Query("INBOX", description="Folder containing the email"),
    api_key: ExchangeApiKey = Depends(DependApiKeyReceive),
):
    """
    Retrieve the full content of a single email, including body and attachments.

    Inline images (``cid:`` references) are resolved to data-URIs automatically.
    Requires the `receive` permission.
    """
    verify_account_access(api_key, account_id)

    service = get_email_service()
    result = await service.get_email(
        account_id=account_id,
        email_id=email_id,
        folder=folder,
        api_key_id=api_key.id,
    )

    if result["success"]:
        return Success(data=result["data"])
    return Fail(code=404, msg=result.get("message", "Email not found"))


@router.put("/{email_id:path}/read", summary="Mark email read/unread")
async def mark_email_read(
    request: Request,
    email_id: str,
    account_id: int = Query(..., description="Account ID"),
    folder: str = Query("INBOX", description="Folder containing the email"),
    is_read: bool = Query(True, description="True = mark as read, False = mark as unread"),
    api_key: ExchangeApiKey = Depends(DependApiKeyRead),
):
    """
    Toggle the read flag on an email.

    Requires the `read` permission.
    """
    verify_account_access(api_key, account_id)

    service = get_email_service()
    result = await service.mark_as_read(
        account_id=account_id,
        email_id=email_id,
        is_read=is_read,
        folder=folder,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )

    if result["success"]:
        return Success(msg=result["message"])
    return Fail(code=500, msg=result["message"])


@router.delete("/{email_id:path}", summary="Delete email")
async def delete_email(
    request: Request,
    email_id: str,
    account_id: int = Query(..., description="Account ID"),
    folder: str = Query("INBOX", description="Folder containing the email"),
    api_key: ExchangeApiKey = Depends(DependApiKeyDelete),
):
    """
    Permanently delete an email from the specified folder.

    Requires the `delete` permission.
    """
    verify_account_access(api_key, account_id)

    service = get_email_service()
    result = await service.delete_email(
        account_id=account_id,
        email_id=email_id,
        folder=folder,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )

    if result["success"]:
        return Success(msg=result["message"])
    return Fail(code=500, msg=result["message"])


@router.post("/search", summary="Search emails")
async def search_emails(
    request: Request,
    data: EmailSearchRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeySearch),
):
    """
    Full-text search across subject and body within the specified folder.

    Supports optional date range filters.  Requires the `search` permission.
    """
    verify_account_access(api_key, data.account_id)

    service = get_email_service()
    result = await service.search_emails(
        request=data,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )

    if result["success"]:
        return Success(
            data={
                "total": result["total"],
                "items": [item.model_dump(mode="json") for item in result["items"]],
            }
        )
    return Fail(code=500, msg=result.get("message", "Search failed"))


@router.post("/sync", summary="Incremental sync")
async def sync_emails(
    request: Request,
    data: EmailSyncRequest,
    api_key: ExchangeApiKey = Depends(DependApiKeySync),
):
    """
    Return incremental changes (create / update / delete) since the last sync.

    Pass the ``sync_state`` returned by the previous call to receive only new
    changes.  Omit it (or send ``null``) for a full initial sync.
    Requires the `sync` permission.
    """
    verify_account_access(api_key, data.account_id)

    service = get_email_service()
    result = await service.sync_emails(
        request=data,
        api_key_id=api_key.id,
        request_ip=get_client_ip(request),
    )

    if result["success"]:
        return Success(
            data=jsonable_encoder(
                {
                    "sync_state": result["sync_state"],
                    "items": result["items"],
                }
            )
        )
    return Fail(code=500, msg=result.get("message", "Sync failed"))
