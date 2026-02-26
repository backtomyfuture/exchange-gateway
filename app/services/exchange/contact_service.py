import asyncio

from app.log import logger
from app.services.exchange.connection_pool import get_exchange_connection


class ContactService:
    # ... (existing code)

    async def resolve_names(self, query: str, account_id: int) -> list[dict]:
        try:
            async with get_exchange_connection(account_id) as conn:

                def resolve_ops():
                    # Debug: Check Account capabilities
                    if not hasattr(resolve_ops, "_logged_account_dir"):
                        logger.info(f"Account Attributes: {dir(conn.account)}")
                        resolve_ops._logged_account_dir = True

                    # 1. 优先搜索个人通讯录
                    local_matches = []
                    try:
                        # 简化本地搜索，避免复杂 filter 报错
                        local_matches = list(conn.account.contacts.filter(display_name__icontains=query))
                    except Exception as e:
                        logger.warning(f"Local contacts search failed: {e}")

                    if local_matches:
                        return [
                            {
                                "name": getattr(c, "display_name", None) or getattr(c, "complete_name", None),
                                "email": getattr(c, "email_addresses", [None])[0].email_address
                                if getattr(c, "email_addresses", None)
                                else None,
                                "mailbox_type": "Contact",
                                "item_id": str(c.id) if c.id else None,
                            }
                            for c in local_matches
                        ]

                    # 2. 尝试 GAL (ResolveNames)
                    results = conn.account.protocol.resolve_names(names=[query], return_full_contact_data=True)

                    contacts = []
                    for item in results:
                        # item 可能是 Mailbox, Contact, 或者是包含 error 的对象
                        if isinstance(item, Exception):
                            continue

                        # Handle tuple if necessary
                        if isinstance(item, tuple):
                            mailbox, contact = item

                            if contact:
                                # Use contact details (DisplayName, etc.)
                                name = (
                                    getattr(contact, "display_name", None)
                                    or getattr(contact, "complete_name", None)
                                    or getattr(mailbox, "name", None)
                                )
                                email = getattr(mailbox, "email_address", None)
                                item_id = str(contact.item_id) if getattr(contact, "item_id", None) else None
                                item_type = "Contact"
                            else:
                                # Only Mailbox available
                                name = getattr(mailbox, "name", None)
                                email = getattr(mailbox, "email_address", None)
                                item_id = str(mailbox.item_id) if getattr(mailbox, "item_id", None) else None
                                item_type = "Mailbox"
                        else:
                            # Single item (Mailbox or Contact)
                            # Prefer display_name if available (Contact), else name (Mailbox)
                            name = getattr(item, "display_name", None) or getattr(item, "name", None)
                            email = getattr(item, "email_address", None)
                            item_id = str(getattr(item, "item_id", "")) if getattr(item, "item_id", None) else None
                            item_type = getattr(item, "mailbox_type", "Unknown")

                        # Fallback for name if still empty
                        if not name and email:
                            name = email.split("@")[0]

                        contact_data = {"name": name, "email": email, "mailbox_type": item_type, "item_id": item_id}
                        contacts.append(contact_data)
                    return contacts

                loop = asyncio.get_running_loop()
                contacts = await loop.run_in_executor(None, resolve_ops)
                return contacts

        except Exception as e:
            logger.error(f"解析联系人失败: {e}")
            return []


# 全局服务实例
_contact_service: ContactService | None = None


def get_contact_service() -> ContactService:
    """获取通讯录服务实例"""
    global _contact_service
    if _contact_service is None:
        _contact_service = ContactService()
    return _contact_service
