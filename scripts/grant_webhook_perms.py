import asyncio
import os
import sys
from tortoise import Tortoise

sys.path.append(os.getcwd())
os.environ.setdefault("DEV_MODE", "true")

from app.settings import settings
from app.models.admin import Role, Menu, Api

async def grant():
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    # 1. Find Role
    role = await Role.filter(name="邮箱用户").first()
    if not role:
        print("❌ Role '邮箱用户' not found!")
        return
    
    # 2. Find Webhook Menu
    webhook_menu = await Menu.filter(name="Webhook 订阅").first()
    if not webhook_menu:
        print("❌ Menu 'Webhook 订阅' not found!")
        return
    
    # 3. Assign Menu to Role
    print(f"Assigning menu '{webhook_menu.name}' to role '{role.name}'...")
    await role.menus.add(webhook_menu)
    
    # 4. Find all Webhook APIs
    webhook_apis = await Api.filter(path__contains="webhook").all()
    print(f"Found {len(webhook_apis)} webhook APIs. Assigning to role...")
    for api in webhook_apis:
        await role.apis.add(api)
    
    print("✅ Permissions granted successfully.")
    
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(grant())
