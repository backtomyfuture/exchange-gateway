import asyncio
from tortoise import Tortoise
from app.models.admin import Menu
from app.settings.config import settings

async def list_menus():
    print("Initializing database connection...")
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    print("\n--- All Menus ---")
    menus = await Menu.all().order_by('order')
    for m in menus:
        print(f"ID: {m.id} | Name: {m.name} | Path: {m.path} | Order: {m.order} | Parent: {m.parent_id} | Hidden: {m.is_hidden}")

if __name__ == "__main__":
    asyncio.run(list_menus())
