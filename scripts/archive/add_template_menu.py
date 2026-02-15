"""
添加邮件模板菜单到数据库
"""
import asyncio
from app.models.admin import Menu
from tortoise import Tortoise
from app.settings import settings

async def main():
    print("Initializing Database...")
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    # 查找 Exchange 服务父菜单
    exchange_menu = await Menu.filter(path="exchange").first()
    
    if not exchange_menu:
        print("Error: Exchange 父菜单不存在!")
        await Tortoise.close_connections()
        return
    
    print(f"Found parent menu: {exchange_menu.name} (ID: {exchange_menu.id})")
    
    # 检查模板菜单是否已存在
    existing = await Menu.filter(path="exchange/templates").first()
    if existing:
        print(f"模板菜单已存在: {existing.name}")
        await Tortoise.close_connections()
        return
    
    # 创建模板菜单
    template_menu = await Menu.create(
        name="邮件模板",
        path="exchange/templates",
        order=40,  # 排在日志后面
        parent_id=exchange_menu.id,
        icon="mdi:file-document-outline",
        is_hidden=False,
        component="/exchange/templates/index",
        redirect="",
        menu_type="menu",
        keepalive=True,
    )
    
    print(f"Created template menu: {template_menu.name} (ID: {template_menu.id})")
    
    print("Done!")
    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(main())
