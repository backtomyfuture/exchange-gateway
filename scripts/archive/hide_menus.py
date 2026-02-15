
import asyncio
from app.models.admin import Menu
from tortoise import Tortoise
from app.settings import settings

async def main():
    print("Initializing Database...")
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    
    # Menus to unhide (Show Menu and API management)
    paths_to_show = ["menu", "api"]
    for path in paths_to_show:
        menu = await Menu.filter(path=path).first()
        if menu:
            menu.is_hidden = False
            await menu.save()
            print(f"Directory shown: {menu.name} ({menu.path})")

    # Menus to hide (Keep Dept hidden)
    paths_to_hide = ["dept"]
    for path in paths_to_hide:
        menu = await Menu.filter(path=path).first()
        if menu:
            menu.is_hidden = True
            await menu.save()
            print(f"Directory hidden: {menu.name} ({menu.path})")
    
    print("Done!")
    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(main())
