import asyncio
from tortoise import Tortoise

from app.models.admin import Menu
from app.schemas.menus import MenuType
from app.settings.config import settings

async def add_exchange_menus():
    print("Initializing database connection...")
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    # Check if root menu exists
    root_menu = await Menu.get_or_none(name="Exchange 邮件网关")
    if root_menu:
        print("Exchange menu 'Exchange 邮件网关' already exists.")
    else:
        print("Creating 'Exchange 邮件网关' menu...")
        # Create Root Menu
        root_menu = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="Exchange 邮件网关",
            path="/exchange",
            order=2,
            parent_id=0,
            icon="material-symbols:mail-outline",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/exchange/accounts",
        )
        print(f"Created root menu: {root_menu.name} (ID: {root_menu.id})")

    # Define children menus
    children_data = [
        {
            "name": "账号管理",
            "path": "accounts",
            "order": 1,
            "icon": "material-symbols:supervisor-account-outline",
            "component": "/exchange/accounts",
        },
        {
            "name": "API 密钥",
            "path": "keys",
            "order": 2,
            "icon": "material-symbols:key-outline",
            "component": "/exchange/keys",
        },
        {
            "name": "邮件模板",
            "path": "templates",
            "order": 3,
            "icon": "material-symbols:drafts-outline",
            "component": "/exchange/templates",
        },
        {
            "name": "操作日志",
            "path": "logs",
            "order": 4,
            "icon": "material-symbols:history",
            "component": "/exchange/logs",
        },
        {
            "name": "使用统计",
            "path": "stats",
            "order": 5,
            "icon": "material-symbols:analytics-outline",
            "component": "/exchange/stats",
        },
    ]

    for item in children_data:
        # Check if child menu exists
        child = await Menu.get_or_none(name=item["name"], parent_id=root_menu.id)
        if child:
             print(f"  - Menu '{item['name']}' already exists.")
        else:
            print(f"  - Creating menu '{item['name']}'...")
            await Menu.create(
                menu_type=MenuType.MENU,
                name=item["name"],
                path=item["path"],
                order=item["order"],
                parent_id=root_menu.id,
                icon=item["icon"],
                is_hidden=False,
                component=item["component"],
                keepalive=False,
            )
    
    print("Exchange menus setup completed!")

if __name__ == "__main__":
    asyncio.run(add_exchange_menus())
