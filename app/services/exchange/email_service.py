"""
Email service – core send, receive, search and sync operations via exchangelib.
"""
import base64
import asyncio
import uuid
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional
import re

from exchangelib import (
    UTC,
    FileAttachment,
    HTMLBody,
    Message,
)

from app.log import logger
import binascii
import gzip
from exchangelib.errors import TransportError, ErrorTimeoutExpired, ErrorInvalidSyncStateData
from app.models.exchange import ExchangeMailLog
from app.schemas.exchange import (
    EmailItem,
    EmailListRequest,
    EmailSendRequest,
    EmailDraftRequest,
    EmailSearchRequest,
    FolderItem,
    EmailReplyRequest,
    EmailForwardRequest,
)

from .connection_pool import get_exchange_connection


def _resolve_folder(account, folder_name: str):
    """
    Resolve a folder name to an exchangelib Folder object.

    Recognises the common well-known names (case-insensitive) and falls back
    to a path lookup under the inbox for custom folder names.
    """
    name_upper = folder_name.upper()
    if name_upper == "INBOX":
        return account.inbox
    if name_upper == "SENT":
        return account.sent
    if name_upper == "DRAFTS":
        return account.drafts
    if name_upper in ("TRASH", "DELETED", "DELETEDITEMS"):
        return account.trash
    if name_upper in ("JUNK", "SPAM", "JUNKEMAIL"):
        return account.junk
    # Arbitrary custom folder – look up relative to inbox
    return account.inbox / folder_name


class EmailService:
    """
    邮件服务
    封装 exchangelib 的邮件操作
    """
    
    async def send_email(
        self,
        request: EmailSendRequest,
        api_key_id: Optional[int] = None,
        request_ip: Optional[str] = None
    ) -> dict:
        """
        发送邮件（异步）
        
        1. 创建发送日志（状态：pending）
        2. 添加后台任务进行实际发送
        3. 立即返回日志ID
        """
        request_id = str(uuid.uuid4())[:8]

        try:
            # 1. Create audit log entry (pending state – updated after send completes)
            log_entry = await ExchangeMailLog.create(
                api_key_id=api_key_id,
                account_id=request.account_id,
                action="send",
                recipients=request.to,
                cc_recipients=request.cc,
                bcc_recipients=request.bcc,
                subject=request.subject,
                has_attachments=bool(request.attachments),
                status="pending",
                request_ip=request_ip,
                request_id=request_id,
            )
            
            # 2. 添加后台任务
            from app.core.bgtask import BgTasks
            await BgTasks.add_task(
                self._send_email_bg_task,
                log_id=log_entry.id,
                request=request
            )
            
            return {
                "success": True,
                "message": "邮件已加入发送队列",
                "log_id": log_entry.id,
                "status": "queued"
            }
                
        except Exception as e:
            logger.error(f"邮件入队失败: {e}")
            return {
                "success": False,
                "message": f"邮件入队失败: {str(e)}",
                "log_id": None,
            }
    
    async def create_draft(
        self,
        request: EmailDraftRequest,
        api_key_id: Optional[int] = None,
        request_ip: Optional[str] = None
    ) -> dict:
        """
        创建草稿
        """
        try:
            async with get_exchange_connection(request.account_id) as conn:
                def draft_ops():
                    # 构建邮件正文
                    if request.body_type == "html":
                        from .format_utils import process_inline_images
                        processed_body, inline_attachments = process_inline_images(request.body)
                        body = HTMLBody(processed_body) if processed_body else None
                    else:
                        body = request.body
                        inline_attachments = []
                    
                    # 创建邮件
                    message = Message(
                        account=conn.account,
                        subject=request.subject,
                        body=body,
                        to_recipients=request.to or [],
                        cc_recipients=request.cc or [],
                        bcc_recipients=request.bcc or [],
                        folder=conn.account.drafts,
                    )
                    # 添加附件
                    if request.attachments:
                        for att in request.attachments:
                            content = base64.b64decode(att.content)
                            file_attachment = FileAttachment(
                                name=att.filename,
                                content=content,
                                content_type=att.content_type,
                            )
                            message.attach(file_attachment)
                    
                    # 添加处理后的内嵌图片附件
                    for att_data in inline_attachments:
                        content = base64.b64decode(att_data["content"])
                        inline_att = FileAttachment(
                            name=att_data["filename"],
                            content=content,
                            content_type=att_data["content_type"],
                            content_id=att_data["content_id"],
                            is_inline=True
                        )
                        message.attach(inline_att)
                    
                    # 保存到草稿箱
                    message.save()
                    return message.id, message.changekey

                loop = asyncio.get_running_loop()
                item_id, changekey = await loop.run_in_executor(None, draft_ops)
                
                await ExchangeMailLog.create(
                    api_key_id=api_key_id,
                    account_id=request.account_id,
                    action="create_draft",
                    recipients=request.to,
                    subject=request.subject,
                    status="success",
                    request_ip=request_ip,
                )
                
                return {
                    "success": True,
                    "message": "草稿已创建",
                    "id": item_id,
                    "changekey": changekey
                }
                
        except Exception as e:
            logger.error(f"创建草稿失败: {e}")
            return {
                "success": False,
                "message": f"创建草稿失败: {str(e)}",
            }

    async def _send_email_bg_task(self, log_id: int, request: EmailSendRequest):
        """
        Background task that executes the actual EWS send with up to 3 retries.

        Transient network errors (TransportError, ErrorTimeoutExpired) are retried
        with linear back-off.  All other errors are considered non-retryable.
        """
        from exchangelib.errors import TransportError, ErrorTimeoutExpired

        max_retries = 3
        retry_delay = 2  # seconds between attempts

        log_entry = await ExchangeMailLog.get_or_none(id=log_id)
        if not log_entry:
            logger.error(f"Mail log not found: {log_id}")
            return

        for attempt in range(1, max_retries + 1):
            try:
                async with get_exchange_connection(request.account_id) as conn:
                    # Define sync operation for sending email
                    def send_ops():
                        # 构建邮件正文
                        inline_attachments = []
                        if request.body_type == "html":
                            from .format_utils import process_inline_images
                            processed_body, inline_attachments = process_inline_images(request.body)
                            body = HTMLBody(processed_body)
                        else:
                            body = request.body
                        
                        # 创建邮件
                        message = Message(
                            account=conn.account,
                            subject=request.subject,
                            body=body,
                            to_recipients=request.to,
                            cc_recipients=request.cc or [],
                            bcc_recipients=request.bcc or [],
                        )
                        # 添加附件
                        if request.attachments:
                            for att in request.attachments:
                                content = base64.b64decode(att.content)
                                file_attachment = FileAttachment(
                                    name=att.filename,
                                    content=content,
                                    content_type=att.content_type,
                                )
                                message.attach(file_attachment)
                        
                        # 添加处理后的内嵌图片附件
                        for att_data in inline_attachments:
                            content = base64.b64decode(att_data["content"])
                            inline_att = FileAttachment(
                                name=att_data["filename"],
                                content=content,
                                content_type=att_data["content_type"],
                                content_id=att_data["content_id"],
                                is_inline=True
                            )
                            message.attach(inline_att)
                        
                        # 发送邮件
                        if request.save_to_sent:
                            message.send_and_save()
                        else:
                            message.send()

                    # Execute in thread pool
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, send_ops)
                    
                    # 更新日志为成功
                    log_entry.status = "success"
                    log_entry.error_message = None
                    await log_entry.save()
                    
                    logger.info(f"邮件发送成功 (LogID: {log_id})")
                    return  # 成功退出
                    
            except (TransportError, ErrorTimeoutExpired) as e:
                # 网络/连接错误，进行重试
                error_msg = f"发送尝试 {attempt}/{max_retries} 失败: {str(e)}"
                logger.warning(error_msg)
                
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * attempt)
                    continue
                else:
                    # 最终失败
                    log_entry.status = "failed"
                    log_entry.error_message = f"最终失败: {str(e)}"
                    await log_entry.save()
            
            except Exception as e:
                # 其他错误（如认证失败、数据格式错误），不重试
                error_msg = f"发送失败(不可重试): {str(e)}"
                logger.error(error_msg)
                
                log_entry.status = "failed"
                log_entry.error_message = str(e)
                await log_entry.save()
                return
    
    async def list_emails(
        self,
        request: EmailListRequest,
        api_key_id: Optional[int] = None,
        request_ip: Optional[str] = None
    ) -> dict:
        """
        获取邮件列表
        """
        try:
            async with get_exchange_connection(request.account_id) as conn:
                def list_ops():
                    try:
                        folder = _resolve_folder(conn.account, request.folder)
                        
                        # 构建查询
                        if request.unread_only:
                            qs = folder.filter(is_read=False)
                        else:
                            qs = folder.all()
                        
                        # 获取总数 (Blocking I/O)
                        total_count = qs.count()
                        
                        # 分页获取 (Blocking I/O)
                        fetched_items = qs.order_by('-datetime_received')[request.offset:request.offset + request.limit]
                        
                        # 转换为响应格式
                        email_list = []
                        for item in fetched_items:
                            # 将 EWSDateTime 转换为 Python datetime
                            received_time = None
                            if item.datetime_received:
                                received_time = datetime(
                                    item.datetime_received.year,
                                    item.datetime_received.month,
                                    item.datetime_received.day,
                                    item.datetime_received.hour,
                                    item.datetime_received.minute,
                                    item.datetime_received.second,
                                )
                            
                            email_list.append(EmailItem(
                                id=item.id,
                                subject=item.subject,
                                sender=str(item.sender) if item.sender else None,
                                received_time=received_time,
                                is_read=item.is_read,
                                has_attachments=item.has_attachments,
                            ))
                        return total_count, email_list
                    except Exception as e:
                        logger.error(f"List ops error: {e}")
                        raise

                loop = asyncio.get_running_loop()
                total, email_items = await loop.run_in_executor(None, list_ops)
                
                # 记录日志
                await ExchangeMailLog.create(
                    api_key_id=api_key_id,
                    account_id=request.account_id,
                    action="receive",
                    status="success",
                    request_ip=request_ip,
                )

                return {
                    "success": True,
                    "total": total,
                    "items": email_items,
                }
                
        except Exception as e:
            logger.error(f"获取邮件列表失败: {e}")
            return {
                "success": False,
                "total": 0,
                "items": [],
                "message": str(e),
            }
    
    async def get_email(
        self,
        account_id: int,
        email_id: str,
        folder: str = "INBOX",
        api_key_id: Optional[int] = None,
    ) -> dict:
        """
        Retrieve full email details including body, attachments and inline images.
        Supports any folder, not just INBOX.
        """
        try:
            async with get_exchange_connection(account_id) as conn:
                def get_ops():
                    target_folder = _resolve_folder(conn.account, folder)
                    item = target_folder.get(id=email_id)
                    
                    if not item:
                        return None
                    
                    # 获取附件信息
                    attachments = []
                    if item.attachments:
                        for att in item.attachments:
                            if isinstance(att, FileAttachment):
                                content = None
                                if att.content:
                                    try:
                                        content = base64.b64encode(att.content).decode('utf-8')
                                    except Exception as e:
                                        logger.error(f"Failed to encode attachment {att.name}: {e}")
                                
                                attachments.append({
                                    "name": att.name,
                                    "content_type": att.content_type,
                                    "size": att.size,
                                    "content": content,
                                    "content_id": att.content_id,
                                    "is_inline": att.is_inline
                                })
                    
                    # Log extracted attachments count
                    # logger.info(f"Extracted {len(attachments)} attachments for email {email_id}")

                    # 处理内嵌图片引用 (cid: -> data uri)
                    body_content = item.body if hasattr(item, 'body') else None
                    if body_content and attachments:
                        for att in attachments:
                            # 只有内嵌图片且有内容ID和内容的才处理
                            if att.get("is_inline") and att.get("content_id") and att.get("content"):
                                cid = att["content_id"]
                                # EWS content_id 经常带有 <>，例如 <foo.bar@baz>
                                # HTML 中引用通常是 src="cid:foo.bar@baz"
                                # 我们尝试移除 <> 来匹配
                                clean_cid = cid.strip("<>")
                                
                                # 构建 Data URI
                                data_uri = f"data:{att['content_type']};base64,{att['content']}"
                                
                                # 替换 body 中的引用 (简单的字符串替换，或更复杂的正则)
                                # 常见格式: src="cid:xyz"
                                # 我们替换 "cid:xyz" -> "data:image/png;base64,..."
                                # 注意正则转义
                                try:
                                    # 使用正则替换，匹配 cid:{clean_cid}
                                    # 必须转义 custom_cid 中的特殊字符
                                    pattern = f"cid:{re.escape(clean_cid)}"
                                    body_content = re.sub(pattern, data_uri, body_content, flags=re.IGNORECASE)
                                    
                                    # 有些情况可能 cid 没有被转义或者引用方式不同，尝试原始 cid
                                    if cid != clean_cid:
                                        pattern_raw = f"cid:{re.escape(cid)}"
                                        body_content = re.sub(pattern_raw, data_uri, body_content, flags=re.IGNORECASE)
                                except Exception as e:
                                    logger.error(f"Failed to replace cid for {clean_cid}: {e}")

                    return {
                        "id": item.id,
                        "subject": item.subject,
                        "body": body_content,
                        "sender": str(item.sender) if item.sender else None,
                        "to_recipients": [str(r) for r in item.to_recipients] if item.to_recipients else [],
                        "cc_recipients": [str(r) for r in item.cc_recipients] if item.cc_recipients else [],
                        "received_time": item.datetime_received.isoformat() if item.datetime_received else None,
                        "is_read": item.is_read,
                        "attachments": attachments,
                    }

                loop = asyncio.get_running_loop()
                data = await loop.run_in_executor(None, get_ops)
                
                if not data:
                    return {
                        "success": False,
                        "data": None,
                        "message": "邮件不存在",
                    }

                return {
                    "success": True,
                    "data": data,
                }
                
        except Exception as e:
            logger.error(f"获取邮件详情失败: {e}")
            return {
                "success": False,
                "data": None,
                "message": str(e),
            }

    async def reply_email(
        self,
        request: EmailReplyRequest,
        api_key_id: Optional[int] = None,
        request_ip: Optional[str] = None
    ) -> dict:
        """
        回复邮件 (Outlook 风格)
        """
        try:
            from app.services.exchange.format_utils import build_outlook_reply_header, process_inline_images
            
            async with get_exchange_connection(request.account_id) as conn:
                def reply_ops():
                    # 查找原邮件
                    import exchangelib.items
                    
                    try:
                        item = conn.account.inbox.get(id=request.reference_item_id)
                    except Exception:
                        item = conn.account.fetch(ids=[request.reference_item_id])[0]

                    if not item:
                        raise ValueError("Original email not found")

                    # 处理用户回复中可能包含的 Base64 图片 -> CID 附件
                    # 注意：我们只处理用户的新回复内容，不包含原文
                    # 原文由 Exchange Server 自动附加
                    reply_body_html, user_inline_attachments = process_inline_images(request.body)
                    
                    # 创建回复
                    if request.reply_all:
                        reply_item = item.create_reply_all(
                            subject=request.subject if request.subject else None,
                            body=HTMLBody(reply_body_html)
                        )
                    else:
                        reply_item = item.create_reply(
                            subject=request.subject if request.subject else None,
                            body=HTMLBody(reply_body_html),
                            to_recipients=request.to if request.to else None
                        )
                    
                    # 设置 CC/BCC
                    if request.cc:
                        reply_item.cc_recipients = request.cc
                    if request.bcc:
                        reply_item.bcc_recipients = request.bcc

                    # 添加新附件 (用户上传的)
                    if request.attachments:
                        for att in request.attachments:
                            content = base64.b64decode(att.content)
                            file_attachment = FileAttachment(
                                name=att.filename,
                                content=content,
                                content_type=att.content_type,
                            )
                            reply_item.attach(file_attachment)
                            
                    # 添加用户回复中提取的内嵌图片附件 (Base64 -> CID)
                    for att_data in user_inline_attachments:
                        content = base64.b64decode(att_data["content"])
                        inline_att = FileAttachment(
                            name=att_data["filename"],
                            content=content,
                            content_type=att_data["content_type"],
                            content_id=att_data["content_id"],
                            is_inline=True
                        )
                        reply_item.attach(inline_att)

                    # 发送
                    reply_item.send()
                    
                    return True

                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, reply_ops)

                await ExchangeMailLog.create(
                    api_key_id=api_key_id,
                    account_id=request.account_id,
                    action="reply",
                    recipients=request.to,
                    cc_recipients=request.cc,
                    subject=request.subject,
                    has_attachments=bool(request.attachments),
                    status="success",
                    request_ip=request_ip,
                )

                return {"success": True, "message": "回复已发送"}

        except Exception as e:
            logger.error(f"回复邮件失败: {e}")
            return {"success": False, "message": str(e)}

    async def forward_email(
        self,
        request: EmailForwardRequest,
        api_key_id: Optional[int] = None,
        request_ip: Optional[str] = None
    ) -> dict:
        """
        转发邮件 (Outlook 风格)
        """
        try:
            from app.services.exchange.format_utils import build_outlook_reply_header, process_inline_images
            
            async with get_exchange_connection(request.account_id) as conn:
                def forward_ops():
                    # 查找原邮件
                    try:
                        item = conn.account.inbox.get(id=request.reference_item_id)
                    except Exception:
                        item = conn.account.fetch(ids=[request.reference_item_id])[0]

                    if not item:
                        raise ValueError("Original email not found")

                    # 处理转发附言中可能包含的 Base64 图片 -> CID 附件
                    # 注意：我们只处理用户的新附言内容，不包含原文
                    forward_body_html, user_inline_attachments = process_inline_images(request.body)

                    # 创建转发
                    # create_forward 会自动附加原邮件附件 (包括内嵌图片)
                    # 也会自动引用原文
                    forward_item = item.create_forward(
                        subject=request.subject if request.subject else None,
                        body=HTMLBody(forward_body_html),
                        to_recipients=request.to
                    )
                    
                    if request.cc:
                        forward_item.cc_recipients = request.cc
                    if request.bcc:
                        forward_item.bcc_recipients = request.bcc

                    # 添加用户附言中提取的内嵌图片附件
                    for att_data in user_inline_attachments:
                        content = base64.b64decode(att_data["content"])
                        inline_att = FileAttachment(
                            name=att_data["filename"],
                            content=content,
                            content_type=att_data["content_type"],
                            content_id=att_data["content_id"],
                            is_inline=True
                        )
                        forward_item.attach(inline_att)

                    # 添加额外附件 (新上传的)
                    if request.attachments:
                        for att in request.attachments:
                            content = base64.b64decode(att.content)
                            file_attachment = FileAttachment(
                                name=att.filename,
                                content=content,
                                content_type=att.content_type,
                            )
                            forward_item.attach(file_attachment)

                    # 发送
                    forward_item.send()
                    
                    return True

                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, forward_ops)

                await ExchangeMailLog.create(
                    api_key_id=api_key_id,
                    account_id=request.account_id,
                    action="forward",
                    recipients=request.to,
                    cc_recipients=request.cc,
                    subject=request.subject,
                    has_attachments=bool(request.attachments),
                    status="success",
                    request_ip=request_ip,
                )

                return {"success": True, "message": "转发已发送"}

        except Exception as e:
            logger.error(f"转发邮件失败: {e}")
            return {"success": False, "message": str(e)}
    
    async def delete_email(
        self,
        account_id: int,
        email_id: str,
        folder: str = "INBOX",
        api_key_id: Optional[int] = None,
        request_ip: Optional[str] = None,
    ) -> dict:
        """
        Delete an email from the specified folder (defaults to INBOX).
        """
        try:
            async with get_exchange_connection(account_id) as conn:
                def delete_ops():
                    target_folder = _resolve_folder(conn.account, folder)
                    item = target_folder.get(id=email_id)
                    if item:
                        item.delete()
                        return item, True
                    return None, False

                loop = asyncio.get_running_loop()
                item, deleted = await loop.run_in_executor(None, delete_ops)

                if deleted:
                    # 记录日志 (Async operation outside executor)
                    await ExchangeMailLog.create(
                        api_key_id=api_key_id,
                        account_id=account_id,
                        action="delete",
                        subject=item.subject if hasattr(item, 'subject') else None,
                        status="success",
                        request_ip=request_ip,
                    )
                    
                    return {"success": True, "message": "邮件已删除"}
                else:
                    return {"success": False, "message": "邮件不存在"}

                    
        except Exception as e:
            logger.error(f"删除邮件失败: {e}")
            return {"success": False, "message": str(e)}

    async def mark_as_read(
        self,
        account_id: int,
        email_id: str,
        is_read: bool = True,
        folder: str = "INBOX",
        api_key_id: Optional[int] = None,
        request_ip: Optional[str] = None,
    ) -> dict:
        """
        Toggle the read/unread flag on an email in the specified folder.
        """
        try:
            async with get_exchange_connection(account_id) as conn:
                def mark_ops():
                    target_folder = _resolve_folder(conn.account, folder)
                    item = target_folder.get(id=email_id)
                    if not item:
                        return None, False
                    
                    # 只有状态不一致时才更新
                    if item.is_read != is_read:
                        item.is_read = is_read
                        item.save(update_fields=['is_read'])
                        return item, True
                    
                    return item, True # 已经是一样状态，视为成功

                loop = asyncio.get_running_loop()
                item, success = await loop.run_in_executor(None, mark_ops)

                if item:
                    # 记录日志 (可选，如果不希望记录太多可以跳过，或者记录为 update)
                    # 这里为了审计完整性，记录一下
                    if success: # 只有真正存在才记录
                         # 注意：ExchangeMailLog 表结构也许没有 update 动作，但 action 是 varchar，应该可以
                        await ExchangeMailLog.create(
                            api_key_id=api_key_id,
                            account_id=account_id,
                            action="mark_read" if is_read else "mark_unread",
                            subject=item.subject if hasattr(item, 'subject') else None,
                            status="success",
                            request_ip=request_ip,
                        )
                    
                    return {"success": True, "message": f"邮件已标记为{'已读' if is_read else '未读'}"}
                else:
                    return {"success": False, "message": "邮件不存在"}
                    
        except Exception as e:
            logger.error(f"标记邮件状态失败: {e}")
            return {"success": False, "message": str(e)}

    
    async def search_emails(
        self,
        request: EmailSearchRequest,
        api_key_id: Optional[int] = None,
        request_ip: Optional[str] = None,
    ) -> dict:
        """
        搜索邮件
        """
        try:
            from exchangelib import Q
            
            async with get_exchange_connection(request.account_id) as conn:
                def search_ops():
                    folder = _resolve_folder(conn.account, request.folder)

                    query_filter = Q(subject__icontains=request.query) | Q(body__icontains=request.query)
                    items = folder.filter(query_filter)

                    if request.date_from:
                        date_from = request.date_from
                        # Ensure datetime is timezone-aware for EWS comparison
                        if date_from.tzinfo is None:
                            date_from = date_from.replace(tzinfo=UTC)
                        items = items.filter(datetime_received__gte=date_from)
                    if request.date_to:
                        date_to = request.date_to
                        if date_to.tzinfo is None:
                            date_to = date_to.replace(tzinfo=UTC)
                        items = items.filter(datetime_received__lte=date_to)
                    
                    fetched_items = list(items[:request.limit])
                    
                    # 转换结果
                    email_result = []
                    for item in fetched_items:
                        # 将 EWSDateTime 转换为 Python datetime
                        received_time = None
                        if item.datetime_received:
                            received_time = datetime(
                                item.datetime_received.year,
                                item.datetime_received.month,
                                item.datetime_received.day,
                                item.datetime_received.hour,
                                item.datetime_received.minute,
                                item.datetime_received.second,
                            )
                        
                        email_result.append(EmailItem(
                            id=item.id,
                            subject=item.subject,
                            sender=str(item.sender) if item.sender else None,
                            received_time=received_time,
                            is_read=item.is_read,
                            has_attachments=item.has_attachments,
                        ))
                    return email_result

                loop = asyncio.get_running_loop()
                email_items = await loop.run_in_executor(None, search_ops)
                
                await ExchangeMailLog.create(
                    api_key_id=api_key_id,
                    account_id=request.account_id,
                    action="search",
                    status="success",
                    request_ip=request_ip,
                )

                return {
                    "success": True,
                    "total": len(email_items),
                    "items": email_items,
                }
                
        except Exception as e:
            logger.error(f"搜索邮件失败: {e}")
            return {
                "success": False,
                "total": 0,
                "items": [],
                "message": str(e),
            }
    

    async def get_all_folders(
        self,
        account_id: int,
        api_key_id: Optional[int] = None,
        request_ip: Optional[str] = None,
    ) -> dict:
        """
        获取所有文件夹列表（递归）
        """
        try:
            from app.schemas.exchange import FolderDetailItem
            
            async with get_exchange_connection(account_id) as conn:
                def folder_ops():
                    # 获取根目录下的所有文件夹（递归）
                    # msg_folder_root 通常对应 'Top of Information Store' (IPM_SUBTREE)
                    # 直接遍历 account.msg_folder_root 即可包含所有用户可见文件夹
                    
                    root = conn.account.msg_folder_root
                    
                    # 使用 walk() 遍历
                    # walk() 返回 (folder, path_depth, folder_depth)
                    # 但我们需要构建树状结构或者返回带 parent_id 的扁平列表
                    # exchangelib 的 folder 对象有 parent_id 属性吗？
                    # Folder 对象有 parent 属性，但它是一个对象。
                    
                    all_folders = []
                    
                    # 首先添加 Top of Information Store 本身 (可选，通常不需要)
                    # all_folders.append(root)
                    
                    # 使用 walk() 获取所有子文件夹
                    for folder in root.walk():
                        all_folders.append(folder)
                        
                    # 转换为 Schema
                    result_list = []
                    for f in all_folders:
                        try:
                            parent_id = f.parent.id if f.parent else None
                            # 如果 parent 是 root，可能需要特殊处理，但这里直接返回即可
                            
                            result_list.append(FolderDetailItem(
                                id=f.id,
                                changekey=f.changekey,
                                name=f.name,
                                parent_id=parent_id,
                                folder_class=f.folder_class,
                                total_count=f.total_count or 0,
                                unread_count=f.unread_count or 0,
                                child_folder_count=f.child_folder_count or 0
                            ))
                        except Exception as e:
                            logger.warning(f"Error processing folder {f.name}: {e}")
                            continue
                            
                    return result_list

                loop = asyncio.get_running_loop()
                folders = await loop.run_in_executor(None, folder_ops)
                
                await ExchangeMailLog.create(
                    api_key_id=api_key_id,
                    account_id=account_id,
                    action="folders_all",
                    status="success",
                    request_ip=request_ip,
                )

                return {
                    "success": True,
                    "folders": folders,
                }
                

        except Exception as e:
            logger.error(f"获取所有文件夹失败: {e}")
            return {
                "success": False,
                "folders": [],
                "message": str(e),
            }

    async def list_folders(
        self,
        account_id: int,
        api_key_id: Optional[int] = None,
    ) -> dict:
        """
        获取文件夹列表 (Legacy for backward compatibility)
        """
        try:
            from app.schemas.exchange import FolderItem
            
            async with get_exchange_connection(account_id) as conn:
                def folder_ops():
                    f_list = []
                    # 添加常用文件夹
                    for name, folder in [
                        ("INBOX", conn.account.inbox),
                        ("SENT", conn.account.sent),
                        ("DRAFTS", conn.account.drafts),
                        ("TRASH", conn.account.trash),
                    ]:
                        try:
                            f_list.append(FolderItem(
                                name=name,
                                total_count=folder.total_count or 0,
                                unread_count=folder.unread_count or 0,
                            ))
                        except Exception:
                            pass
                    return f_list

                loop = asyncio.get_running_loop()
                folders = await loop.run_in_executor(None, folder_ops)
                
                # 记录日志
                await ExchangeMailLog.create(
                    api_key_id=api_key_id,
                    account_id=account_id,
                    action="folders",
                    status="success",
                    request_ip=None, 
                )

                return {
                    "success": True,
                    "folders": folders,
                }
                
        except Exception as e:
            logger.error(f"获取文件夹列表失败: {e}")
            return {
                "success": False,
                "folders": [],
                "message": str(e),
            }

    async def sync_emails(
        self,
        request,  # Type: EmailSyncRequest
        api_key_id: Optional[int] = None,
        request_ip: Optional[str] = None,
    ) -> dict:
        """
        同步邮件
        """
        try:
            from app.schemas.exchange import EmailSyncItem, EmailItem
            from app.models.exchange import ExchangeMailLog
            
            async with get_exchange_connection(request.account_id) as conn:
                def sync_ops():
                    folder = _resolve_folder(conn.account, request.folder)
                    
                    # 执行同步 (Blocking)
                    # max_changes_returned controls page size
                    try:
                        changes = list(folder.sync_items(
                            sync_state=request.sync_state,
                            max_changes_returned=request.limit,
                            only_fields=request.only_fields,
                        ))
                    except (binascii.Error, gzip.BadGzipFile, ErrorInvalidSyncStateData, ValueError) as e:
                        # 捕获 sync_state 反序列化错误
                        # 如果 sync_state 无效（例如被截断、编码错误），记录日志并抛出更友好的错误
                        # 有时客户端传递的 Base64 字符串可能包含空格而不是加号，尝试修复（虽然 requests 通常处理）
                        # 但如果仍然失败，则视为状态过期或无效
                        logger.error(f"Sync state processing error: {e}. State prefix: {str(request.sync_state)[:20] if request.sync_state else 'None'}")
                        
                        # 可以选择抛出特定异常，或者在这里决定如何处理
                        # 如果是同步状态错误，通常意味着客户端需要重置 sync_state (即传 None 进行全量同步)
                        # 这里我们抛出一个ValueError，外层会捕获并返回错误信息
                        raise ValueError(f"Invalid sync_state: {str(e)}")
                    
                    # 获取新的 sync_state
                    new_sync_state = folder.item_sync_state
                    
                    result_items = []
                    for change_type, item in changes:
                        # change_type: 'create', 'update', 'delete', 'read_flag_change'
                        
                        # Ensure item_id is extracted as a string
                        item_id = None
                        target_item = item
                        
                        # Handle tuple case (e.g. read_flag_change yields (ItemId, is_read))
                        if isinstance(item, (list, tuple)) and len(item) > 0:
                            target_item = item[0]
                            
                        if hasattr(target_item, 'id'):
                             item_id = target_item.id
                        elif hasattr(target_item, 'item_id') and hasattr(target_item.item_id, 'id'):
                             item_id = target_item.item_id.id
                        else:
                             # Fallback
                             item_id = str(target_item)
                             
                        # Force string conversion to avoid ItemId objects
                        if item_id is not None:
                            item_id = str(item_id)
                        
                        sync_item = {
                            "change_type": change_type,
                            "id": item_id,
                            "item": None
                        }
                        
                        # 如果是 create 或 update，item 是 Message 对象
                        # 如果是 delete 或 read_flag_change，item 是 ItemId (或类似包含ID的对象)
                        if change_type in ('create', 'update'):
                            # 转换为 EmailItem
                            received_time = None
                            if hasattr(item, 'datetime_received') and item.datetime_received:
                                received_time = datetime(
                                    item.datetime_received.year,
                                    item.datetime_received.month,
                                    item.datetime_received.day,
                                    item.datetime_received.hour,
                                    item.datetime_received.minute,
                                    item.datetime_received.second,
                                )
                            
                            sync_item["item"] = {
                                "id": item_id,
                                "subject": item.subject if hasattr(item, 'subject') else None,
                                "sender": str(item.sender) if hasattr(item, 'sender') and item.sender else None,
                                "received_time": received_time,
                                "is_read": item.is_read if hasattr(item, 'is_read') else False,
                                "has_attachments": item.has_attachments if hasattr(item, 'has_attachments') else False,
                            }
                        
                        result_items.append(sync_item)
                        
                    return new_sync_state, result_items

                loop = asyncio.get_running_loop()
                new_state, items = await loop.run_in_executor(None, sync_ops)
                
                # 记录审计日志
                await ExchangeMailLog.create(
                    api_key_id=api_key_id,
                    account_id=request.account_id,
                    action="sync",
                    status="success",
                    request_ip=request_ip,
                )
                
                return {
                    "success": True,
                    "sync_state": new_state,
                    "items": items,
                }
                
        except Exception as e:
            logger.error(f"同步邮件失败: {e}")
            return {
                "success": False,
                "sync_state": request.sync_state, # Return old state on error? Or just fail.
                "items": [],
                "message": str(e),
            }


@lru_cache(maxsize=1)
def get_email_service() -> EmailService:
    """获取邮件服务实例"""
    return EmailService()


async def recover_pending_emails():
    """
    Mark in-flight 'pending' send tasks as failed on service start-up.

    Email body content is intentionally NOT persisted to the mail-log table,
    so true re-delivery after a crash is impossible without the original
    caller retrying.  We therefore mark these records as 'failed' with a
    clear error message so operators know what happened, rather than
    silently dropping them or spinning forever.

    Returns:
        dict: {"recovered": int, "failed": int}
    """
    cutoff_time = datetime.now() - timedelta(hours=24)
    pending_logs = await ExchangeMailLog.filter(
        status="pending",
        action="send",
        created_at__gte=cutoff_time,
    ).all()

    if not pending_logs:
        return {"recovered": 0, "failed": 0}

    logger.warning(
        f"Found {len(pending_logs)} pending send task(s) from before restart. "
        "Email content is not persisted; marking as failed. "
        "Clients should retry these messages."
    )

    failed = 0
    for log in pending_logs:
        try:
            log.status = "failed"
            log.error_message = (
                "Service restarted before send completed. "
                "Email content not persisted – caller must retry."
            )
            await log.save()
            failed += 1
        except Exception as e:
            logger.error(f"Failed to update log {log.id}: {e}")

    logger.info(f"Startup recovery complete: {failed} task(s) marked as failed.")
    return {"recovered": 0, "failed": failed}
