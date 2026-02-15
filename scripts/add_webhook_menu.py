import asyncio
import os
import sys
from tortoise import Tortoise

# Add project root to path
sys.path.append(os.getcwd())

# Set DEV_MODE to use default settings
os.environ.setdefault("DEV_MODE", "true")

from app.settings import settings
from app.models.admin import Menu

async def add_menu():
    # Initialize Tortoise
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    # 1. Find "邮件服务" menu
    exchange_menu = await Menu.filter(name="邮件服务").first()
    
    if not exchange_menu:
        print("❌ '邮件服务' menu not found! Creating it...")
        exchange_menu = await Menu.create(
            name="邮件服务",
            menu_type="catalog",
            icon="ph:envelope-simple-open-bold",
            path="/exchange",
            component="Layout",
            order=10,
            is_hidden=False,
            keepalive=True
        )
        print(f"✅ Created parent menu: {exchange_menu.name} (ID: {exchange_menu.id})")

    print(f"Found parent menu: {exchange_menu.name} (ID: {exchange_menu.id})")
    
    # 2. Check if "Webhook 订阅" exists
    webhook_menu = await Menu.filter(name="Webhook 订阅", parent_id=exchange_menu.id).first()
    
    if webhook_menu:
        print(f"✅ 'Webhook 订阅' menu already exists (ID: {webhook_menu.id}).")
        # Update path/component just in case
        webhook_menu.path = "/exchange/webhooks"
        webhook_menu.component = "exchange/webhooks/index"
        webhook_menu.icon = "connection"
        await webhook_menu.save()
        print("Updated menu configuration.")
    else:
        print("Creating 'Webhook 订阅' menu...")
        await Menu.create(
            name="Webhook 订阅",
            parent_id=exchange_menu.id,
            path="/exchange/webhooks",
            component="exchange/webhooks/index",
            icon="connection",
            order=99, # Put it at the end
            is_hidden=False,
            keepalive=True
        )
        print("✅ Menu created.")

    await Tortoise.close_connections()

    # Cleanup old menu
    await Tortoise.init(config=settings.TORTOISE_ORM)
    old_parent = await Menu.filter(name="Exchange 管理").first()
    if old_parent:
        # 1. Delete old "Webhook 订阅" under this parent
        old_webhook = await Menu.filter(name="Webhook 订阅", parent_id=old_parent.id).first()
        if old_webhook:
            print(f"Removing old 'Webhook 订阅' from 'Exchange 管理' (ID: {old_webhook.id})...")
            await old_webhook.delete()
        
        # 2. Check if parent is now empty
        children_count = await Menu.filter(parent_id=old_parent.id).count()
        if children_count == 0:
            print("Cleaning up empty 'Exchange 管理' menu...")
            await old_parent.delete()
            print("✅ Deleted old parent menu.")
        else:
            print(f"⚠️ 'Exchange 管理' menu has {children_count} children, skipping delete.")
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(add_menu())
