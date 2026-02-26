import logging
from typing import Any

from app.models.exchange import ExchangeAccount
from app.models.webhook import WebhookSubscription
from app.schemas.webhook import WebhookCreate, WebhookUpdate

from .audit_service import get_audit_service

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Webhook 订阅服务
    负责订阅的增删改查
    """

    async def list_webhooks(
        self,
        owner_id: int,
        page: int = 1,
        page_size: int = 20,
        account_id: int | None = None,
    ) -> dict[str, Any]:
        """
        获取 Webhook 订阅列表
        """
        try:
            # 构建查询
            query = WebhookSubscription.filter(created_by=owner_id)

            if account_id:
                query = query.filter(account_id=account_id)

            # 计算总数
            total = await query.count()

            # 分页查询
            items = await query.offset((page - 1) * page_size).limit(page_size).order_by("-id")

            # 转换为字典以便序列化
            serialized_items = [await item.to_dict() for item in items]

            return {"success": True, "items": serialized_items, "total": total}
        except Exception as e:
            logger.error(f"获取 Webhook 列表失败: {e}")
            return {"success": False, "message": str(e)}

    async def create_webhook(
        self,
        data: WebhookCreate,
        owner_id: int,
    ) -> dict[str, Any]:
        """
        创建 Webhook 订阅
        """
        try:
            # 1. 检查账户是否存在且属于当前用户 (或用户有权限)
            # 这里简化逻辑，只允许关联到自己拥有的账户，或者通过权限检查在上层做
            # Service 层假定上层已经做了基本的权限校验，或者在这里再做一次
            account = await ExchangeAccount.get_or_none(id=data.account_id)
            if not account:
                return {"success": False, "message": "关联账户不存在"}

            # 简单检查归属权，如果是管理员可能需要更复杂的逻辑，这里暂定只能关联自己的账户或者有权限的账户
            # 如果是 API Key 调用，owner_id 可能是 API Key 的 owner_id

            # 2. 创建订阅
            # Encrypt secret
            from app.utils.crypto import get_crypto

            crypto = get_crypto()
            encrypted_secret = crypto.encrypt(data.secret)

            webhook = await WebhookSubscription.create(
                url=str(data.url),
                secret=encrypted_secret,
                account_id=data.account_id,
                events=data.events,
                folders=data.folders,
                is_active=data.is_active,
                remark=data.remark,
                created_by=owner_id,
            )

            # 3. 记录审计日志
            audit_service = get_audit_service()
            await audit_service.log(
                operator_id=owner_id,
                action="create_webhook",
                resource_type="webhook",
                resource_id=webhook.id,
                resource_name=str(webhook.url),
                details=data.model_dump(exclude={"secret"}, mode="json"),  # 不记录 secret
                status="success",
            )

            return {"success": True, "message": "创建成功", "data": await webhook.to_dict()}

        except Exception as e:
            logger.error(f"创建 Webhook 失败: {e}")
            return {"success": False, "message": f"创建失败: {str(e)}"}

    async def update_webhook(
        self,
        webhook_id: int,
        data: WebhookUpdate,
        owner_id: int,
    ) -> dict[str, Any]:
        """
        更新 Webhook 订阅
        """
        try:
            webhook = await WebhookSubscription.get_or_none(id=webhook_id, created_by=owner_id)
            if not webhook:
                return {"success": False, "message": "订阅不存在或无权修改"}

            # 更新字段
            update_data = data.dict(exclude_unset=True)
            if "url" in update_data:
                update_data["url"] = str(update_data["url"])

            if "secret" in update_data:
                from app.utils.crypto import get_crypto

                crypto = get_crypto()
                update_data["secret"] = crypto.encrypt(update_data["secret"])

            await webhook.update_from_dict(update_data)
            await webhook.save()

            # 审计
            audit_service = get_audit_service()
            await audit_service.log(
                operator_id=owner_id,
                action="update_webhook",
                resource_type="webhook",
                resource_id=webhook.id,
                resource_name=str(webhook.url),
                details=update_data,
                status="success",
            )

            return {"success": True, "message": "更新成功", "data": await webhook.to_dict()}
        except Exception as e:
            logger.error(f"更新 Webhook 失败: {e}")
            return {"success": False, "message": f"更新失败: {str(e)}"}

    async def delete_webhook(
        self,
        webhook_id: int,
        owner_id: int,
    ) -> dict[str, Any]:
        """
        删除 Webhook 订阅
        """
        try:
            webhook = await WebhookSubscription.get_or_none(id=webhook_id, created_by=owner_id)
            if not webhook:
                return {"success": False, "message": "订阅不存在或无权删除"}

            resource_name = str(webhook.url)
            await webhook.delete()

            # 审计
            audit_service = get_audit_service()
            await audit_service.log(
                operator_id=owner_id,
                action="delete_webhook",
                resource_type="webhook",
                resource_id=webhook_id,
                resource_name=resource_name,
                status="success",
            )

            return {"success": True, "message": "删除成功"}
        except Exception as e:
            logger.error(f"删除 Webhook 失败: {e}")
            return {"success": False, "message": f"删除失败: {str(e)}"}

    async def trigger_test_event(self, webhook_id: int, owner_id: int) -> dict[str, Any]:
        """
        触发测试事件
        """
        import hashlib
        import hmac
        import json
        import time

        import httpx

        try:
            webhook = await WebhookSubscription.get_or_none(id=webhook_id, created_by=owner_id)
            if not webhook:
                return {"success": False, "message": "订阅不存在或无权操作"}

            # 构造测试 Payload
            payload = {
                "event": "TestEvent",
                "timestamp": int(time.time()),
                "account_id": webhook.account_id,
                "message": "This is a test event from Exchange Gateway.",
            }
            payload_json = json.dumps(payload)

            # 计算签名
            # Decrypt secret
            from app.utils.crypto import get_crypto

            crypto = get_crypto()
            try:
                secret = crypto.decrypt(webhook.secret)
            except Exception:
                logger.error(f"Failed to decrypt webhook secret for {webhook.id}")
                return {"success": False, "message": "密钥解密失败"}

            signature = hmac.new(secret.encode("utf-8"), payload_json.encode("utf-8"), hashlib.sha256).hexdigest()

            # 发送请求
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook.url,
                    content=payload_json,
                    headers={
                        "Content-Type": "application/json",
                        "X-Exchange-Signature": signature,
                        "X-Exchange-Event": "TestEvent",
                    },
                    timeout=10.0,
                )

            return {
                "success": response.is_success,
                "message": f"HTTP Status: {response.status_code}",
                "data": {"status_code": response.status_code, "response_body": response.text[:1000]},
            }

        except Exception as e:
            return {"success": False, "message": f"测试失败: {str(e)}"}


def get_webhook_service() -> WebhookService:
    return WebhookService()
