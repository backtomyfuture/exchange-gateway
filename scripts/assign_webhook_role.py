import asyncio
from tortoise import Tortoise
from app.settings import settings
from app.models.admin import Role, Menu

async def assign_menu():
    # Initialize Tortoise ORM manually
    await Tortoise.init(config=settings.TORTOISE_ORM)
    print("Tortoise-ORM initialized successfully.")
    
    # 1. Get the Role
    role_name = "邮箱用户"
    role = await Role.filter(name=role_name).first()
    if not role:
        print(f"Error: Role '{role_name}' not found!")
        return

    # 2. Get the Menu
    # Convert 'Webhook 订阅' to whatever name is actually in DB. 
    # Based on logs, superuser sees "Webhook服务" or similar? 
    # Wait, logs said "Webhook服务". Let's try to match partial name to be sure.
    menus = await Menu.filter(name__contains="Webhook").all()
    if not menus:
         print(f"Error: No menu found containing 'Webhook'")
         return
    
    target_menu = menus[0]
    print(f"Found menu: {target_menu.name} (ID: {target_menu.id})")

    # 3. Assign Menu to Role
    await role.menus.add(target_menu)
    print(f"Success: Added '{target_menu.name}' to role '{role.name}'")

    # 4. Verify
    current_menus = await role.menus.all()
    print(f"Current menus for '{role.name}': {[m.name for m in current_menus]}")

    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(assign_menu())
