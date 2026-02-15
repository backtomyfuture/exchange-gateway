import asyncio
import os
import sys
from tortoise import Tortoise

sys.path.append(os.getcwd())
os.environ.setdefault("DEV_MODE", "true")

from app.settings import settings
from app.models.admin import Menu

async def fix():
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    # 1. Find the parent menu "邮件服务"
    parent = await Menu.filter(name="邮件服务").first()
    if not parent:
        print("❌ '邮件服务' menu not found!")
        return

    # 2. Check for any menus with "webhook" in name or path under this parent
    target_menus = await Menu.filter(parent_id=parent.id, path__contains="webhook").all()
    
    if not target_menus:
        # Check if it exists elsewhere
        target_menus = await Menu.filter(path__contains="webhook").all()
    
    if len(target_menus) > 1:
        print(f"⚠️ Found {len(target_menus)} potential webhook menus. Consolidating...")
        # Keep the first one, delete others
        primary = target_menus[0]
        for other in target_menus[1:]:
            print(f"Deleting duplicate menu ID: {other.id}")
            await other.delete()
        target = primary
    elif target_menus:
        target = target_menus[0]
    else:
        print("Creating new Webhook menu...")
        target = Menu(parent_id=parent.id)

    # Standardize fields based on "API密钥" pattern
    target.name = "Webhook 订阅"
    target.path = "webhooks"
    target.component = "/exchange/webhooks"
    target.parent_id = parent.id
    target.menu_type = "menu"
    target.icon = "connection"
    target.is_hidden = False
    target.keepalive = True
    target.order = 99
    
    await target.save()
    print(f"✅ Menu fixed: ID={target.id}, Name={target.name}, Path={target.path}, Component={target.component}")
    
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(fix())
